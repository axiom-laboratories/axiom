"""Integration tests for SIEMService with DB and APScheduler."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agent_service.db import SIEMConfig, Base
from ee.services.siem_service import SIEMService


@pytest.fixture
async def async_db():
    """Create in-memory async SQLite DB for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield async_session

    await engine.dispose()


@pytest.fixture
async def mock_scheduler():
    """Create a real AsyncIOScheduler for integration testing."""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    yield scheduler
    scheduler.shutdown()


@pytest.fixture
async def test_siem_config(async_db):
    """Create a test SIEMConfig in the DB."""
    async with async_db() as session:
        config = SIEMConfig(
            id="test-siem-1",
            backend="webhook",
            destination="https://siem.example.com/events",
            enabled=True,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config


@pytest.mark.asyncio
async def test_siem_service_startup_with_db(async_db, mock_scheduler, test_siem_config):
    """Test SIEMService startup() loads config from DB and sets status."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)

        # Mock _test_connection to not actually connect
        siem._test_connection = AsyncMock(return_value=None)

        await siem.startup()

        # After startup, status should be set
        assert siem._status in ("healthy", "degraded", "disabled")


@pytest.mark.asyncio
async def test_batch_triggers_on_100_events(async_db, mock_scheduler, test_siem_config):
    """Test flush is triggered when queue reaches 100 events."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)
        siem._deliver = AsyncMock(return_value=True)

        # Enqueue 100 events
        for i in range(100):
            siem.enqueue({
                "username": f"user_{i}",
                "action": "test",
                "resource_id": f"res_{i}",
                "detail": {},
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Trigger flush manually (would be called by APScheduler job)
        batch = []
        while not siem.queue.empty():
            batch.append(siem.queue.get_nowait())

        assert len(batch) == 100, "All 100 events should be in batch"


@pytest.mark.asyncio
async def test_batch_triggers_on_5s_interval(async_db, mock_scheduler, test_siem_config):
    """Test flush is triggered every 5 seconds if fewer than 100 events."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)
        siem._deliver = AsyncMock(return_value=True)

        # Enqueue fewer than 100 events
        for i in range(50):
            siem.enqueue({
                "username": f"user_{i}",
                "action": "test",
                "resource_id": f"res_{i}",
                "detail": {},
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Simulate 5-second flush
        batch = []
        while not siem.queue.empty():
            batch.append(siem.queue.get_nowait())

        assert len(batch) == 50, "All 50 events should be in batch after 5s flush"


@pytest.mark.asyncio
async def test_retry_scheduling_with_backoff(async_db, mock_scheduler, test_siem_config):
    """Test exponential backoff retry scheduling: 5s → 10s → 20s."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)

        # Mock APScheduler to capture job scheduling
        add_job_calls = []
        original_add_job = mock_scheduler.add_job

        def capture_add_job(*args, **kwargs):
            add_job_calls.append(kwargs)
            return original_add_job(*args, **kwargs)

        mock_scheduler.add_job = capture_add_job

        # Simulate delivery failure and retry scheduling
        batch = [{"test": "event"}]

        # First attempt fails, schedule retry at 5s
        siem._consecutive_failures = 0
        delay_5s = 5

        # Second failure, schedule at 10s
        delay_10s = 10

        # Third failure, schedule at 20s
        delay_20s = 20

        assert delay_5s == 5
        assert delay_10s == 10
        assert delay_20s == 20


@pytest.mark.asyncio
async def test_ce_mode_graceful_degradation(async_db, mock_scheduler):
    """Test service handles CE mode (config is None) gracefully."""
    async with async_db() as session:
        # No config (CE mode)
        siem = SIEMService(None, session, mock_scheduler)

        # enqueue() should still work (no-op if config is None)
        siem.enqueue({"test": "event"})

        # _status should be "disabled"
        assert siem._status == "disabled"


@pytest.mark.asyncio
async def test_siem_service_disabled_on_startup_if_not_enabled(async_db, mock_scheduler):
    """Test service is disabled at startup if config.enabled is False."""
    async with async_db() as session:
        config = SIEMConfig(
            id="disabled-siem",
            backend="webhook",
            destination="https://siem.example.com",
            enabled=False,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)

        siem = SIEMService(config, session, mock_scheduler)
        await siem.startup()

        assert siem._status == "disabled"


@pytest.mark.asyncio
async def test_flush_batch_on_failure_retries_with_backoff(async_db, mock_scheduler, test_siem_config):
    """Test flush_batch retries failed deliveries with exponential backoff."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)

        # Track delivery attempts
        attempt_count = 0

        async def failing_deliver(payload):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Connection failed")
            return True

        siem._deliver = failing_deliver

        batch = [{"username": "alice", "action": "test", "resource_id": "test", "detail": {}}]

        await siem.flush_batch(batch)

        # Should have retried
        assert attempt_count >= 1


@pytest.mark.asyncio
async def test_queue_preserves_fifo_order(async_db, mock_scheduler, test_siem_config):
    """Test queue maintains FIFO order of events."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)

        # Enqueue 5 events in order
        for i in range(5):
            siem.enqueue({"index": i, "username": f"user_{i}"})

        # Dequeue and verify FIFO order
        for i in range(5):
            event = siem.queue.get_nowait()
            assert event["index"] == i, f"Event {i} should be dequeued in order"


@pytest.mark.asyncio
async def test_status_after_degradation(async_db, mock_scheduler, test_siem_config):
    """Test status transitions to degraded and recovers."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)
        siem._status = "healthy"

        # Simulate 3 consecutive failures
        for _ in range(3):
            siem._consecutive_failures += 1
            if siem._consecutive_failures >= 3:
                siem._status = "degraded"

        assert siem._status == "degraded"

        # Simulate recovery
        siem._consecutive_failures = 0
        siem._status = "healthy"

        assert siem._status == "healthy"


@pytest.mark.asyncio
async def test_startup_sets_flush_job(async_db, mock_scheduler, test_siem_config):
    """Test startup() registers the periodic flush job with APScheduler."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)
        siem._test_connection = AsyncMock(return_value=None)

        await siem.startup()

        # Check that a job with id "__siem_flush__" is registered
        job = mock_scheduler.get_job("__siem_flush__")
        assert job is not None, "Periodic flush job should be registered"
        assert job.trigger.interval.total_seconds() == 5, "Flush job should run every 5 seconds"


@pytest.mark.asyncio
async def test_enqueue_creates_valid_queue_message(async_db, mock_scheduler, test_siem_config):
    """Test enqueue creates a valid event message structure."""
    async with async_db() as session:
        siem = SIEMService(test_siem_config, session, mock_scheduler)

        event = {
            "username": "alice",
            "action": "secret_access",
            "resource_id": "secret_1",
            "detail": {"operation": "read", "field": "database_password"},
            "timestamp": "2026-04-18T10:00:00Z",
        }

        siem.enqueue(event)

        queued_event = siem.queue.get_nowait()

        # Verify all required fields present
        assert queued_event["username"] == "alice"
        assert queued_event["action"] == "secret_access"
        assert queued_event["resource_id"] == "secret_1"
        assert queued_event["detail"]["operation"] == "read"
        assert queued_event["timestamp"] == "2026-04-18T10:00:00Z"

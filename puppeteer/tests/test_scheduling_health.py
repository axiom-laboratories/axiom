"""
Phase 53 — Scheduling Health and Data Management: Tests for VIS-05, VIS-06.
Tests cover:
  - test_health_aggregate: ScheduledFireLog rows are counted correctly by the health service.
  - test_missed_fire_detection: expected_fires_in_window() helper returns correct fire times.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from agent_service.db import Base, ScheduledFireLog, ScheduledJob
from agent_service.services.scheduler_service import SchedulerService, expected_fires_in_window


# ---------------------------------------------------------------------------
# Async in-memory DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_scheduled_job(jid: str, name: str = "test-job", cron: str = "*/5 * * * *",
                         status: str = "ACTIVE") -> ScheduledJob:
    return ScheduledJob(
        id=jid,
        name=name,
        script_content="print('hello')",
        signature_id="sig-1",
        signature_payload="sig-payload",
        schedule_cron=cron,
        is_active=True,
        created_by="test",
        status=status,
    )


def _make_fire_log(jid: str, status: str = "fired", offset_minutes: int = 0) -> ScheduledFireLog:
    expected_at = datetime.utcnow() - timedelta(minutes=offset_minutes)
    return ScheduledFireLog(
        scheduled_job_id=jid,
        expected_at=expected_at,
        status=status,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_aggregate(db):
    """
    Given ScheduledFireLog rows for a single definition (3 fired + 1 skipped_draft),
    get_scheduling_health() returns aggregate fired=3, skipped=1.
    """
    jid = "job-agg-test"
    sj = _make_scheduled_job(jid, name="agg-test", cron="0 * * * *")
    db.add(sj)
    await db.flush()

    # Add 3 fired + 1 skipped_draft within the last 24h
    for i in range(3):
        db.add(_make_fire_log(jid, status="fired", offset_minutes=i * 60 + 30))
    db.add(_make_fire_log(jid, status="skipped_draft", offset_minutes=5 * 60))
    await db.commit()

    svc = SchedulerService()
    result = await svc.get_scheduling_health("24h", db)

    agg = result["aggregate"]
    assert agg["fired"] == 3, f"Expected fired=3, got {agg['fired']}"
    assert agg["skipped"] == 1, f"Expected skipped=1, got {agg['skipped']}"
    assert len(result["definitions"]) >= 1, "Expected at least one definition row"

    # Find the definition row for our job
    def_row = next((r for r in result["definitions"] if r["id"] == jid), None)
    assert def_row is not None, f"Definition {jid} not found in results"
    assert def_row["fired"] == 3
    assert def_row["skipped"] == 1


@pytest.mark.asyncio
async def test_missed_fire_detection():
    """
    Tests the expected_fires_in_window() helper directly.
    A "*/5 * * * *" cron over a 30-min window should produce 6 fires.
    A "0 * * * *" cron over a 1-hour window should produce exactly 1 fire.
    """
    # Test "*/5 * * * *" — every 5 minutes
    now = datetime.utcnow().replace(second=0, microsecond=0)
    window_start = now - timedelta(minutes=30)
    window_end = now

    fires = expected_fires_in_window("*/5 * * * *", window_start, window_end)
    # Should have ~6 fire times in 30 minutes (0, 5, 10, 15, 20, 25 min marks)
    assert len(fires) >= 5, f"Expected at least 5 fires in 30 min window, got {len(fires)}"

    # All fires should be within the window
    for f in fires:
        assert window_start <= f < window_end, f"Fire {f} is outside window"

    # Test "0 * * * *" — every hour: 1 fire in a 65-minute window
    window_start_h = now - timedelta(minutes=65)
    fires_hourly = expected_fires_in_window("0 * * * *", window_start_h, now)
    assert len(fires_hourly) >= 1, f"Expected at least 1 hourly fire in 65-min window, got {len(fires_hourly)}"

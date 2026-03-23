"""
Phase 53 — Scheduling Health and Data Management: Tests for SRCH-08, SRCH-09.
Tests cover:
  - test_pruner_respects_pinned: pruner deletes unpinned expired records, keeps pinned ones.
  - test_pin_unpin: PATCH /executions/{id}/pin and /unpin set the pinned flag correctly.
"""
import types
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from fastapi.testclient import TestClient

from agent_service.db import Base, ExecutionRecord, Config, Job
from agent_service.services.scheduler_service import SchedulerService
from agent_service.main import app
from agent_service.deps import get_current_user
from agent_service.db import get_db, AsyncSessionLocal


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

def _make_exec_record(job_guid="test-guid", pinned=False, days_old=20):
    completed = datetime.utcnow() - timedelta(days=days_old)
    return ExecutionRecord(
        job_guid=job_guid,
        status="COMPLETED",
        completed_at=completed,
        pinned=pinned,
    )


def _fake_user(username="admin", role="admin"):
    return types.SimpleNamespace(username=username, role=role, token_version=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pruner_respects_pinned(db):
    """
    Given 2 expired ExecutionRecords (one pinned, one not) and retention_days=14,
    prune_execution_history() deletes only the unpinned one.
    """
    # Insert retention config: 14 days
    db.add(Config(key="execution_retention_days", value="14"))

    pinned_rec = _make_exec_record(job_guid="job-pinned", pinned=True, days_old=20)
    unpinned_rec = _make_exec_record(job_guid="job-unpinned", pinned=False, days_old=20)
    db.add(pinned_rec)
    db.add(unpinned_rec)
    await db.commit()

    # Flush to get IDs
    await db.refresh(pinned_rec)
    await db.refresh(unpinned_rec)
    pinned_id = pinned_rec.id
    unpinned_id = unpinned_rec.id

    # Patch SchedulerService to use our test session
    import agent_service.db as db_module
    from unittest.mock import AsyncMock, patch, MagicMock
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session():
        yield db

    with patch.object(db_module, "AsyncSessionLocal") as mock_local:
        mock_local.return_value = mock_session()
        svc = SchedulerService.__new__(SchedulerService)
        await svc.prune_execution_history()

    # Pinned record must still exist
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == pinned_id))
    still_there = result.scalar_one_or_none()
    assert still_there is not None, "Pinned record must NOT be deleted"

    # Unpinned record must be gone
    result2 = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == unpinned_id))
    gone = result2.scalar_one_or_none()
    assert gone is None, "Unpinned expired record must be deleted"


def test_pin_unpin(db):
    """
    PATCH /executions/{id}/pin sets pinned=True.
    PATCH /executions/{id}/unpin sets pinned=False.
    """
    admin = _fake_user("admin", "admin")

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        # Insert an execution record
        async def _setup():
            rec = ExecutionRecord(
                job_guid="test-job-guid",
                status="COMPLETED",
                pinned=False,
            )
            async for session in override_db():
                session.add(rec)
                await session.commit()
                await session.refresh(rec)
                return rec.id

        import asyncio
        rec_id = asyncio.get_event_loop().run_until_complete(_setup())

        client = TestClient(app)

        # Pin the record
        pin_resp = client.patch(f"/executions/{rec_id}/pin")
        assert pin_resp.status_code == 200, f"Pin failed: {pin_resp.text}"
        assert pin_resp.json()["pinned"] is True

        # Verify DB state
        async def _check_pinned():
            async for session in override_db():
                r = await session.execute(select(ExecutionRecord).where(ExecutionRecord.id == rec_id))
                rec = r.scalar_one_or_none()
                return rec.pinned

        assert asyncio.get_event_loop().run_until_complete(_check_pinned()) is True

        # Unpin the record
        unpin_resp = client.patch(f"/executions/{rec_id}/unpin")
        assert unpin_resp.status_code == 200, f"Unpin failed: {unpin_resp.text}"
        assert unpin_resp.json()["pinned"] is False

        # Verify DB state
        async def _check_unpinned():
            async for session in override_db():
                r = await session.execute(select(ExecutionRecord).where(ExecutionRecord.id == rec_id))
                rec = r.scalar_one_or_none()
                return rec.pinned

        assert asyncio.get_event_loop().run_until_complete(_check_unpinned()) is False

    finally:
        app.dependency_overrides.clear()

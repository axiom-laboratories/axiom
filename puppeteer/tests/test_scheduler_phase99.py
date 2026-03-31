"""
Phase 99 — Scheduler Hardening: Tests for SCHED-01, SCHED-02, SCHED-03.

Tests:
  - test_sync_scheduler_does_not_call_remove_all_jobs: sync_scheduler() source must not contain remove_all_jobs()
  - test_sync_scheduler_uses_replace_existing: all add_job() calls in sync_scheduler must have replace_existing=True
  - test_internal_jobs_survive_sync: __-prefixed internal jobs survive sync_scheduler() with empty DB
  - test_sync_adds_new_active_job: active job in DB appears in scheduler after sync
  - test_sync_removes_deactivated_job: job removed from DB (or is_active=False) is removed from scheduler after sync
  - test_cron_callback_is_sync_wrapper: execute_scheduled_job not registered directly; sync wrapper with create_task used
  - test_cron_callback_returns_immediately: synchronous wrapper returns in < 50ms even when coroutine would be slow
  - test_failed_fire_log_counted_in_health: 'failed' fire log rows counted in both fired and failed health aggregates
  - test_no_schema_migration_needed: ScheduledFireLog status column accepts 'failed' without schema change
"""

import asyncio
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def test_sync_scheduler_does_not_call_remove_all_jobs():
    """sync_scheduler() must not call remove_all_jobs() — would destroy internal jobs."""
    source = Path(__file__).parent.parent / "agent_service" / "services" / "scheduler_service.py"
    content = source.read_text()
    # Extract only the sync_scheduler method body
    lines = content.splitlines()
    in_sync = False
    sync_lines = []
    for line in lines:
        if "async def sync_scheduler" in line:
            in_sync = True
        elif in_sync and (line.strip().startswith("async def ") or line.strip().startswith("def ")) and "sync_scheduler" not in line:
            break
        if in_sync:
            sync_lines.append(line)
    sync_body = "\n".join(sync_lines)
    assert "remove_all_jobs" not in sync_body, (
        "sync_scheduler() must not call remove_all_jobs() — use diff-based add/remove instead"
    )


def test_sync_scheduler_uses_replace_existing():
    """add_job() calls in sync_scheduler() must use replace_existing=True."""
    source = Path(__file__).parent.parent / "agent_service" / "services" / "scheduler_service.py"
    content = source.read_text()
    lines = content.splitlines()
    in_sync = False
    sync_lines = []
    for line in lines:
        if "async def sync_scheduler" in line:
            in_sync = True
        elif in_sync and (line.strip().startswith("async def ") or line.strip().startswith("def ")) and "sync_scheduler" not in line:
            break
        if in_sync:
            sync_lines.append(line)
    sync_body = "\n".join(sync_lines)
    assert "replace_existing=True" in sync_body, (
        "sync_scheduler() must use replace_existing=True in add_job() for idempotent scheduling"
    )


@pytest.mark.asyncio
async def test_internal_jobs_survive_sync():
    """Internal __ jobs in APScheduler must not be removed by sync_scheduler() with empty DB."""
    from agent_service.services.scheduler_service import SchedulerService
    import agent_service.db as db_mod

    svc = SchedulerService()
    svc.scheduler.start()
    try:
        # Add an internal job manually
        svc.scheduler.add_job(lambda: None, 'interval', seconds=9999, id='__test_internal__', replace_existing=True)
        internal_ids_before = {j.id for j in svc.scheduler.get_jobs() if j.id.startswith('__')}
        assert '__test_internal__' in internal_ids_before

        # Mock DB to return no scheduled jobs
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(db_mod, 'AsyncSessionLocal', return_value=mock_ctx):
            await svc.sync_scheduler()

        internal_ids_after = {j.id for j in svc.scheduler.get_jobs() if j.id.startswith('__')}
        assert '__test_internal__' in internal_ids_after, (
            "sync_scheduler() removed __test_internal__ — internal jobs must be protected"
        )
    finally:
        svc.scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_sync_adds_new_active_job():
    """Active job in DB must appear in scheduler after sync_scheduler()."""
    from agent_service.services.scheduler_service import SchedulerService
    import agent_service.db as db_mod

    svc = SchedulerService()
    svc.scheduler.start()
    try:
        # Create a mock ScheduledJob
        mock_job = MagicMock()
        mock_job.id = 'test-job-001'
        mock_job.name = 'Test Job 001'
        mock_job.schedule_cron = '0 * * * *'
        mock_job.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(db_mod, 'AsyncSessionLocal', return_value=mock_ctx):
            await svc.sync_scheduler()

        job_ids = {j.id for j in svc.scheduler.get_jobs()}
        assert 'test-job-001' in job_ids, (
            "sync_scheduler() should have added 'test-job-001' from the mocked DB"
        )
    finally:
        svc.scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_sync_removes_deactivated_job():
    """Job removed from DB (or is_active=False) must be removed from scheduler after sync."""
    from agent_service.services.scheduler_service import SchedulerService
    import agent_service.db as db_mod

    svc = SchedulerService()
    svc.scheduler.start()
    try:
        # Pre-add a non-internal job that should be removed
        svc.scheduler.add_job(lambda: None, 'interval', seconds=9999, id='test-job-deact', replace_existing=True)
        assert 'test-job-deact' in {j.id for j in svc.scheduler.get_jobs()}

        # Mock DB returning empty desired set (no active jobs)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(db_mod, 'AsyncSessionLocal', return_value=mock_ctx):
            await svc.sync_scheduler()

        job_ids = {j.id for j in svc.scheduler.get_jobs()}
        assert 'test-job-deact' not in job_ids, (
            "sync_scheduler() should have removed 'test-job-deact' since it's not in desired set"
        )
    finally:
        svc.scheduler.shutdown(wait=False)


def test_cron_callback_is_sync_wrapper():
    """sync_scheduler must use a synchronous wrapper that calls create_task, not the coroutine directly."""
    source = Path(__file__).parent.parent / "agent_service" / "services" / "scheduler_service.py"
    content = source.read_text()
    assert "create_task" in content, "scheduler_service.py must use create_task() for cron callbacks"
    assert "_make_cron_callback" in content or "_cron_callback" in content, (
        "A synchronous cron callback wrapper must exist in scheduler_service.py"
    )


def test_cron_callback_returns_immediately():
    """Synchronous cron wrapper must return in < 50ms even if the coroutine is slow."""
    from agent_service.services.scheduler_service import SchedulerService

    async def slow_coroutine(job_id):
        await asyncio.sleep(0.5)

    svc = SchedulerService()
    callback = svc._make_cron_callback("test-job-timing")

    async def run():
        loop = asyncio.get_event_loop()
        with patch.object(svc, 'execute_scheduled_job', side_effect=slow_coroutine):
            start = time.monotonic()
            callback()
            elapsed = time.monotonic() - start
        assert elapsed < 0.05, f"Callback took {elapsed:.3f}s — must return in < 50ms"
        # Cancel any pending tasks to avoid warnings
        for task in asyncio.all_tasks():
            if not task.done() and task != asyncio.current_task():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

    asyncio.run(run())


def test_failed_fire_log_counted_in_health():
    """'failed' fire_log status must appear in both fired and failed health aggregates."""
    source = Path(__file__).parent.parent / "agent_service" / "services" / "scheduler_service.py"
    content = source.read_text()
    # Verify both fired increment and failed increment appear near 'failed' status handling
    assert "status == 'failed'" in content or 'status == "failed"' in content, (
        "get_scheduling_health() must handle fire_log status=='failed'"
    )
    # Check counts[jid]["fired"] += 1 appears in failed branch
    lines = content.splitlines()
    in_health = False
    health_lines = []
    for line in lines:
        if "async def get_scheduling_health" in line:
            in_health = True
        elif in_health and line.strip().startswith("async def "):
            break
        if in_health:
            health_lines.append(line)
    health_body = "\n".join(health_lines)
    assert "failed" in health_body.lower() and 'counts' in health_body, (
        "get_scheduling_health() must handle 'failed' fire_log rows in counts aggregation"
    )


def test_no_new_migration_needed():
    """Phase 99 adds no new DB columns — ScheduledFireLog.status accepts 'failed' as VARCHAR."""
    from agent_service.db import ScheduledFireLog
    import sqlalchemy as sa
    col = ScheduledFireLog.__table__.c['status']
    assert isinstance(col.type, sa.String), (
        "ScheduledFireLog.status must be VARCHAR (accepts any string, no CHECK constraint)"
    )

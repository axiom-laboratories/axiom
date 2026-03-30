"""
Phase 98 — Dispatch Correctness: Tests for DISP-01, DISP-02, DISP-03, DISP-04, OBS-03.

Tests:
  - test_index_declared_in_job_model: Job.__table_args__ contains ix_jobs_status_created_at
  - test_migration_v44_exists_and_contains_index: migration_v44.sql exists with CONCURRENTLY index
  - test_skip_locked_in_job_service: job_service.py source contains with_for_update(skip_locked=True)
  - test_is_postgres_guard_in_job_service: IS_POSTGRES import and guard present in job_service.py
  - test_no_double_assignment_concurrent_pull_work: 5 concurrent pull_work() → exactly 1 ASSIGNED
    (SKIPPED unless IS_POSTGRES=True in test environment)
"""
import asyncio
import json
import pytest
from pathlib import Path
from agent_service.db import IS_POSTGRES


# ---------------------------------------------------------------------------
# DISP-01: Composite index declared on Job model
# ---------------------------------------------------------------------------

def test_index_declared_in_job_model():
    """Job model must declare Index('ix_jobs_status_created_at', 'status', 'created_at') in __table_args__."""
    from agent_service.db import Job
    assert hasattr(Job, "__table_args__"), "Job must have __table_args__ for index declaration"
    table_args = Job.__table_args__
    # __table_args__ may be a tuple of constraints/indexes or a dict
    if isinstance(table_args, dict):
        pytest.fail("Job.__table_args__ is a dict — expected a tuple with Index objects")
    index_names = []
    for arg in table_args:
        if hasattr(arg, "name"):
            index_names.append(arg.name)
    assert "ix_jobs_status_created_at" in index_names, (
        f"ix_jobs_status_created_at not found in Job.__table_args__. Found: {index_names}"
    )


# ---------------------------------------------------------------------------
# DISP-02: migration_v44.sql exists with CONCURRENTLY index creation
# ---------------------------------------------------------------------------

def test_migration_v44_exists_and_contains_index():
    """migration_v44.sql must exist and contain CREATE INDEX CONCURRENTLY ... ix_jobs_status_created_at."""
    migration = Path(__file__).parent.parent / "migration_v44.sql"
    assert migration.exists(), f"migration_v44.sql not found at {migration}"
    content = migration.read_text()
    assert "ix_jobs_status_created_at" in content, (
        "migration_v44.sql must reference ix_jobs_status_created_at"
    )
    assert "CONCURRENTLY" in content, (
        "migration_v44.sql must use CREATE INDEX CONCURRENTLY for zero-downtime index creation"
    )


def test_migration_v44_has_concurrently_caveat_comment():
    """migration_v44.sql must carry a warning comment about CONCURRENTLY and transaction blocks."""
    migration = Path(__file__).parent.parent / "migration_v44.sql"
    if not migration.exists():
        pytest.skip("migration_v44.sql not yet created")
    content = migration.read_text()
    # Must warn operators not to run inside BEGIN block
    assert "transaction" in content.lower() or "BEGIN" in content, (
        "migration_v44.sql must warn that CONCURRENTLY cannot run inside a transaction block"
    )


# ---------------------------------------------------------------------------
# DISP-03: SKIP LOCKED present in job_service.py source
# ---------------------------------------------------------------------------

def test_skip_locked_in_job_service():
    """job_service.py must contain with_for_update(skip_locked=True) for the Postgres dispatch path."""
    job_service_path = Path(__file__).parent.parent / "agent_service" / "services" / "job_service.py"
    assert job_service_path.exists(), f"job_service.py not found at {job_service_path}"
    content = job_service_path.read_text()
    assert "skip_locked=True" in content, (
        "job_service.py must use with_for_update(skip_locked=True) for DISP-03"
    )


# ---------------------------------------------------------------------------
# DISP-04: IS_POSTGRES guard in job_service.py
# ---------------------------------------------------------------------------

def test_is_postgres_guard_in_job_service():
    """job_service.py must import IS_POSTGRES and use it to guard the SKIP LOCKED path."""
    job_service_path = Path(__file__).parent.parent / "agent_service" / "services" / "job_service.py"
    assert job_service_path.exists(), f"job_service.py not found at {job_service_path}"
    content = job_service_path.read_text()
    assert "IS_POSTGRES" in content, (
        "job_service.py must import and use IS_POSTGRES to guard the SKIP LOCKED path"
    )


# ---------------------------------------------------------------------------
# OBS-03: Zero double-assignment under 5 concurrent pull_work() calls
# (Integration test — skipped unless Postgres is available)
# ---------------------------------------------------------------------------

def test_no_double_assignment_concurrent_pull_work():
    """5 concurrent pull_work() calls against 1 PENDING job must produce exactly 1 ASSIGNED result."""
    if not IS_POSTGRES:
        pytest.skip(
            "Double-assignment integration test requires Postgres (IS_POSTGRES=False — SQLite env)"
        )

    async def _run():
        import uuid
        from datetime import datetime
        from agent_service.db import AsyncSessionLocal, Job, Node
        from agent_service.services.job_service import JobService
        from sqlalchemy import select

        job_guid = f"test-disp-{uuid.uuid4()}"
        node_ids = [f"test-disp-node-{i}-{job_guid[:8]}" for i in range(5)]

        # Create 5 independent sessions — one per simulated node
        sessions = [AsyncSessionLocal() for _ in range(5)]

        try:
            # Use a unique capability to isolate this job from the live stack.
            # Real nodes don't have "test-dispatch-phase98" capability, so they
            # won't pick up this job even if the live puppeteer-agent is running.
            test_capability = json.dumps({"test-dispatch-phase98": "1.0"})

            # Setup: insert 1 PENDING job and 5 minimal nodes using session[0]
            setup_session = sessions[0]
            async with setup_session.begin():
                test_job = Job(
                    guid=job_guid,
                    task_type="script",
                    payload='{"script": "print(1)", "runtime": "python"}',
                    status="PENDING",
                    created_at=datetime.utcnow(),
                    capability_requirements=test_capability,
                )
                setup_session.add(test_job)
                for nid in node_ids:
                    node = Node(
                        node_id=nid,
                        hostname=nid,
                        ip="127.0.0.1",
                        status="ONLINE",
                        capabilities=test_capability,
                    )
                    setup_session.add(node)

            # Fire 5 concurrent pull_work() calls
            async def pull(session, node_id):
                try:
                    return await JobService.pull_work(
                        node_id=node_id,
                        node_ip="127.0.0.1",
                        db=session,
                    )
                except Exception as e:
                    return None

            results = await asyncio.gather(
                *[pull(sessions[i], node_ids[i]) for i in range(5)]
            )

            # Assert exactly 1 job assigned — check DB state
            check_session = AsyncSessionLocal()
            try:
                async with check_session.begin():
                    result = await check_session.execute(
                        select(Job).where(Job.guid == job_guid)
                    )
                    job = result.scalar_one_or_none()
                    assert job is not None, f"Test job {job_guid} not found after pull_work"
                    assert job.status == "ASSIGNED", (
                        f"Expected ASSIGNED, got {job.status}"
                    )
                    # Count how many nodes think they have this job
                    assignments = [
                        r for r in results
                        if r is not None and r.job is not None and r.job.guid == job_guid
                    ]
                    assert len(assignments) == 1, (
                        f"Expected exactly 1 assignment, got {len(assignments)}. "
                        f"Double-assignment detected!"
                    )
            finally:
                await check_session.close()

        finally:
            # Cleanup: remove test data
            cleanup_session = AsyncSessionLocal()
            try:
                async with cleanup_session.begin():
                    await cleanup_session.execute(
                        Job.__table__.delete().where(Job.guid == job_guid)
                    )
                    for nid in node_ids:
                        await cleanup_session.execute(
                            Node.__table__.delete().where(Node.node_id == nid)
                        )
            finally:
                await cleanup_session.close()
            for s in sessions:
                await s.close()

    asyncio.get_event_loop().run_until_complete(_run())

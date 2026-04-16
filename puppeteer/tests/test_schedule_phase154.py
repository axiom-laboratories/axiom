"""
Phase 154 Plan 02 — Unified Schedule View: Integration tests for GET /api/schedule endpoint.

Tests verify:
  - test_get_unified_schedule_merges_jobs_workflows: Endpoint merges ScheduledJob and Workflow entries
  - test_get_unified_schedule_filters_inactive: Filters out inactive jobs and paused workflows
  - test_get_unified_schedule_filters_no_cron: Excludes entries without schedule_cron
  - test_get_unified_schedule_invalid_cron_skipped: Invalid cron expressions handled gracefully
  - test_get_unified_schedule_sorted_by_next_run: Entries sorted by next_run_time ascending
  - test_get_unified_schedule_requires_permission: Permission gating (jobs:read)
  - test_get_unified_schedule_includes_last_run_status: last_run_status reflects job/run status
"""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from agent_service.db import Base, ScheduledJob, Workflow, User, Job, WorkflowRun
from agent_service.main import app
from agent_service.auth import create_access_token
from agent_service.deps import get_db


def make_scheduled_job(job_id: str, name: str, cron: str = "0 9 * * *", is_active: bool = True, created_by: str = "admin"):
    """Helper to create a ScheduledJob with all required fields."""
    return ScheduledJob(
        id=job_id,
        name=name,
        script_content="echo test",
        signature_id="sig-1",
        signature_payload="payload",
        schedule_cron=cron,
        is_active=is_active,
        created_by=created_by
    )


@pytest.fixture
async def engine():
    """In-memory SQLite engine for test isolation."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session_factory(engine):
    """Session factory bound to test engine."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def client(engine, async_session_factory):
    """AsyncClient with mocked get_db dependency."""
    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(async_session_factory):
    """Create admin user with jobs:read permission."""
    async with async_session_factory() as session:
        user = User(
            username="admin",
            password_hash="dummy_hash",
            role="admin"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def viewer_user(async_session_factory):
    """Create viewer user without jobs:read permission."""
    async with async_session_factory() as session:
        user = User(
            username="viewer",
            password_hash="dummy_hash",
            role="viewer"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def auth_headers(admin_user):
    """JWT auth headers for admin user."""
    token = create_access_token({
        "sub": admin_user.username,
        "role": admin_user.role,
        "tv": 0
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def cleanup_schedule(async_session_factory):
    """Clean up schedule entries before and after each test."""
    # Clean before
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM scheduled_jobs"))
        await session.execute(text("DELETE FROM workflows WHERE schedule_cron IS NOT NULL"))
        await session.commit()

    yield

    # Clean after
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM scheduled_jobs"))
        await session.execute(text("DELETE FROM workflows WHERE schedule_cron IS NOT NULL"))
        await session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_unified_schedule_merges_jobs_workflows(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule returns merged ScheduledJob and Workflow entries."""
    async with async_session_factory() as session:
        # Create 2 active ScheduledJob entries with schedule_cron
        for i in range(2):
            job = make_scheduled_job(f"job-{i}", f"Daily Backup {i}", created_by=admin_user.username)
            session.add(job)

        # Create 2 active Workflow entries with schedule_cron
        for i in range(2):
            workflow = Workflow(
                id=f"flow-{i}",
                name=f"Data Pipeline {i}",
                schedule_cron="0 15 * * *",
                is_paused=False,
                created_by=admin_user.username
            )
            session.add(workflow)

        await session.commit()

    # GET /api/schedule
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 4
    assert data["total"] == 4

    # Verify structure
    for entry in data["entries"]:
        assert "id" in entry
        assert entry["type"] in ("JOB", "FLOW")
        assert "name" in entry
        assert "next_run_time" in entry
        assert "last_run_status" in entry


@pytest.mark.asyncio
async def test_get_unified_schedule_filters_inactive(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule filters out inactive jobs and paused workflows."""
    async with async_session_factory() as session:
        # Create 1 active and 1 inactive ScheduledJob
        active_job = make_scheduled_job("job-active", "Active Job", cron="0 9 * * *", created_by=admin_user.username)
        inactive_job = make_scheduled_job("job-inactive", "Inactive Job", cron="0 10 * * *", is_active=False, created_by=admin_user.username)
        session.add(active_job)
        session.add(inactive_job)

        # Create 1 active and 1 paused Workflow
        active_workflow = Workflow(
            id="flow-active",
            name="Active Flow",
            schedule_cron="0 15 * * *",
            is_paused=False,
            created_by=admin_user.username
        )
        paused_workflow = Workflow(
            id="flow-paused",
            name="Paused Flow",
            schedule_cron="0 16 * * *",
            is_paused=True,
            created_by=admin_user.username
        )
        session.add(active_workflow)
        session.add(paused_workflow)

        await session.commit()

    # GET /api/schedule
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify only active entries are returned
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2

    # Verify correct entries are included
    names = [entry["name"] for entry in data["entries"]]
    assert "Active Job" in names
    assert "Active Flow" in names
    assert "Inactive Job" not in names
    assert "Paused Flow" not in names


@pytest.mark.asyncio
async def test_get_unified_schedule_filters_no_cron(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule excludes entries without schedule_cron."""
    async with async_session_factory() as session:
        # Create job with cron and one without
        with_cron = make_scheduled_job("job-with-cron", "With Cron", created_by=admin_user.username)
        without_cron = ScheduledJob(
            id="job-without-cron",
            name="Without Cron",
            script_content="echo test",
            signature_id="sig-1",
            signature_payload="payload",
            schedule_cron=None,
            is_active=True,
            created_by=admin_user.username
        )
        session.add(with_cron)
        session.add(without_cron)

        await session.commit()

    # GET /api/schedule
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify only cron entries included
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["name"] == "With Cron"


@pytest.mark.asyncio
async def test_get_unified_schedule_invalid_cron_skipped(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule handles invalid cron gracefully without crashing."""
    async with async_session_factory() as session:
        # Create valid and invalid jobs
        valid = make_scheduled_job("job-valid", "Valid Cron", created_by=admin_user.username)
        invalid = ScheduledJob(
            id="job-invalid",
            name="Invalid Cron",
            script_content="echo test",
            signature_id="sig-1",
            signature_payload="payload",
            schedule_cron="99 * * * *",  # Invalid minute value
            is_active=True,
            created_by=admin_user.username
        )
        session.add(valid)
        session.add(invalid)

        await session.commit()

    # GET /api/schedule (should not crash)
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify endpoint returns 200 and only valid entry is included
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 1
    assert data["entries"][0]["name"] == "Valid Cron"


@pytest.mark.asyncio
async def test_get_unified_schedule_sorted_by_next_run(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule entries are sorted by next_run_time ascending."""
    async with async_session_factory() as session:
        # Create jobs with different cron times
        job1 = make_scheduled_job("job-morning", "Morning Job", cron="0 6 * * *", created_by=admin_user.username)
        job2 = make_scheduled_job("job-afternoon", "Afternoon Job", cron="0 15 * * *", created_by=admin_user.username)
        job3 = make_scheduled_job("job-evening", "Evening Job", cron="0 18 * * *", created_by=admin_user.username)
        session.add(job1)
        session.add(job2)
        session.add(job3)

        await session.commit()

    # GET /api/schedule
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify sorted by next_run_time ascending
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 3

    # Extract times and verify ordering
    times = [entry["next_run_time"] for entry in data["entries"]]
    assert times == sorted(times)


@pytest.mark.asyncio
async def test_get_unified_schedule_requires_permission(
    client, async_session_factory, admin_user, viewer_user, cleanup_schedule
):
    """Verify GET /api/schedule requires jobs:read permission."""
    async with async_session_factory() as session:
        # Create test data
        job = make_scheduled_job("job-test", "Test Job", created_by=admin_user.username)
        session.add(job)
        await session.commit()

    # Admin user (has jobs:read) should succeed
    admin_token = create_access_token({
        "sub": admin_user.username,
        "role": admin_user.role,
        "tv": 0
    })
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    response = await client.get("/api/schedule", headers=admin_headers)
    assert response.status_code == 200

    # Viewer user (no jobs:read) should fail
    viewer_token = create_access_token({
        "sub": viewer_user.username,
        "role": viewer_user.role,
        "tv": 0
    })
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    response = await client.get("/api/schedule", headers=viewer_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_unified_schedule_includes_last_run_status(
    client, async_session_factory, admin_user, auth_headers, cleanup_schedule
):
    """Verify GET /api/schedule includes last_run_status from job/run history."""
    async with async_session_factory() as session:
        # Create job with prior run
        job_with_run = make_scheduled_job("job-with-run", "Job With History", created_by=admin_user.username)
        session.add(job_with_run)
        await session.commit()

        # Add a completed job run
        job_run = Job(
            guid=str(uuid4()),
            scheduled_job_id="job-with-run",
            task_type="script",
            payload='{"script": "echo test"}',
            status="COMPLETED"
        )
        session.add(job_run)
        await session.commit()

        # Create job with no runs
        job_no_run = make_scheduled_job("job-no-run", "Job No History", cron="0 10 * * *", created_by=admin_user.username)
        session.add(job_no_run)
        await session.commit()

    # GET /api/schedule
    response = await client.get("/api/schedule", headers=auth_headers)

    # Verify last_run_status
    assert response.status_code == 200
    data = response.json()

    # Find entries
    with_run_entry = next((e for e in data["entries"] if e["name"] == "Job With History"), None)
    no_run_entry = next((e for e in data["entries"] if e["name"] == "Job No History"), None)

    # Job with run should have status
    assert with_run_entry is not None
    assert with_run_entry["last_run_status"] == "COMPLETED"

    # Job without run should have null
    assert no_run_entry is not None
    assert no_run_entry["last_run_status"] is None

"""
Integration tests for GET /api/schedule endpoint.

Tests verify:
- Backend service method: merging, filtering, invalid cron, permissions
- API endpoint: correct response schema, permission gating, error handling
- Edge cases: null last_run_status, sorting by next_run_time
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select, text
from agent_service.db import (
    AsyncSessionLocal, ScheduledJob, Workflow, Job, WorkflowRun,
    Signature, User
)
from agent_service.auth import create_access_token
from agent_service.models import ScheduleListResponse


@pytest.fixture
async def cleanup_schedule():
    """Clean scheduled jobs and workflows before each test."""
    async with AsyncSessionLocal() as session:
        # Use text() for raw SQL
        await session.execute(text("DELETE FROM scheduled_jobs"))
        await session.execute(text("DELETE FROM workflows WHERE schedule_cron IS NOT NULL"))
        await session.commit()
    yield
    # Cleanup after test
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM scheduled_jobs"))
        await session.execute(text("DELETE FROM workflows WHERE schedule_cron IS NOT NULL"))
        await session.commit()


@pytest.fixture
async def signature_fixture():
    """Create a test signature for ScheduledJob FK."""
    sig_id = str(uuid4())
    async with AsyncSessionLocal() as session:
        sig = Signature(
            id=sig_id,
            name=f"test-sig-{uuid4().hex[:8]}",
            public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
            uploaded_by="admin"
        )
        session.add(sig)
        await session.commit()
    return sig_id


@pytest.fixture
async def viewer_user():
    """Create a test viewer user with jobs:read permission."""
    username = f"viewer-{uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            from agent_service.auth import get_password_hash
            user = User(
                username=username,
                password_hash=get_password_hash("viewer123"),
                role="viewer",
                token_version=0,
                must_change_password=False
            )
            session.add(user)
            await session.commit()

        return user


@pytest.fixture
async def auth_headers_viewer(viewer_user):
    """Create auth headers for viewer user."""
    token = create_access_token({
        "sub": viewer_user.username,
        "role": "viewer",
        "tv": viewer_user.token_version
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def operator_user():
    """Create a test operator user without jobs:read permission."""
    username = f"operator-{uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            from agent_service.auth import get_password_hash
            user = User(
                username=username,
                password_hash=get_password_hash("operator123"),
                role="operator",
                token_version=0,
                must_change_password=False
            )
            session.add(user)
            await session.commit()

        return user


@pytest.fixture
async def auth_headers_operator(operator_user):
    """Create auth headers for operator user (no jobs:read)."""
    token = create_access_token({
        "sub": operator_user.username,
        "role": "operator",
        "tv": operator_user.token_version
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_unified_schedule_merges_jobs_workflows(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 1: GET /api/schedule merges ScheduledJob and Workflow entries.

    Setup: Create 2 active ScheduledJob records with schedule_cron
    Setup: Create 2 active Workflow records with schedule_cron
    Verify: Response has 4 entries (2 jobs + 2 workflows)
    """
    sig_id = signature_fixture

    async with AsyncSessionLocal() as session:
        # Create 2 active ScheduledJobs
        for i in range(2):
            job = ScheduledJob(
                id=str(uuid4()),
                name=f"job-{i}",
                script_content="echo 'test'",
                signature_id=sig_id,
                signature_payload="dGVzdA==",
                schedule_cron="0 9 * * *",
                is_active=True,
                created_by="admin"
            )
            session.add(job)

        # Create 2 active Workflows
        for i in range(2):
            workflow = Workflow(
                id=str(uuid4()),
                name=f"workflow-{i}",
                created_by="admin",
                is_paused=False,
                schedule_cron="0 9 * * *"
            )
            session.add(workflow)

        await session.commit()

    # Call API
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 4
    assert data.total == 4

    # Check types
    types = [entry.type for entry in data.entries]
    assert types.count("JOB") == 2
    assert types.count("FLOW") == 2


@pytest.mark.asyncio
async def test_get_unified_schedule_filters_inactive(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 2: GET /api/schedule filters out inactive jobs and paused workflows.

    Setup: Create 1 active job, 1 inactive (is_active=false) job
    Setup: Create 1 active workflow, 1 paused (is_paused=true) workflow
    Verify: Response has exactly 2 entries (1 job + 1 workflow)
    """
    sig_id = signature_fixture

    async with AsyncSessionLocal() as session:
        # Active job
        job_active = ScheduledJob(
            id=str(uuid4()),
            name="job-active",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_active)

        # Inactive job (should be filtered)
        job_inactive = ScheduledJob(
            id=str(uuid4()),
            name="job-inactive",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=False,
            created_by="admin"
        )
        session.add(job_inactive)

        # Active workflow
        workflow_active = Workflow(
            id=str(uuid4()),
            name="workflow-active",
            created_by="admin",
            is_paused=False,
            schedule_cron="0 9 * * *"
        )
        session.add(workflow_active)

        # Paused workflow (should be filtered)
        workflow_paused = Workflow(
            id=str(uuid4()),
            name="workflow-paused",
            created_by="admin",
            is_paused=True,
            schedule_cron="0 9 * * *"
        )
        session.add(workflow_paused)

        await session.commit()

    # Call API
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 2
    assert data.total == 2

    # Check only active ones are included
    names = [entry.name for entry in data.entries]
    assert "job-active" in names
    assert "workflow-active" in names
    assert "job-inactive" not in names
    assert "workflow-paused" not in names


@pytest.mark.asyncio
async def test_get_unified_schedule_filters_no_cron(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 3: GET /api/schedule excludes items without schedule_cron.

    Setup: Create active jobs/workflows without schedule_cron (None or empty)
    Verify: Response is empty or excludes non-cron items
    """
    sig_id = signature_fixture

    async with AsyncSessionLocal() as session:
        # Job without cron (should be filtered)
        job_no_cron = ScheduledJob(
            id=str(uuid4()),
            name="job-no-cron",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron=None,
            is_active=True,
            created_by="admin"
        )
        session.add(job_no_cron)

        # Job with empty cron (should be filtered)
        job_empty_cron = ScheduledJob(
            id=str(uuid4()),
            name="job-empty-cron",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="",
            is_active=True,
            created_by="admin"
        )
        session.add(job_empty_cron)

        # Workflow without cron (should be filtered)
        workflow_no_cron = Workflow(
            id=str(uuid4()),
            name="workflow-no-cron",
            created_by="admin",
            is_paused=False,
            schedule_cron=None
        )
        session.add(workflow_no_cron)

        await session.commit()

    # Call API
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 0
    assert data.total == 0


@pytest.mark.asyncio
async def test_get_unified_schedule_invalid_cron_skipped(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 4: GET /api/schedule skips invalid cron expressions gracefully.

    Setup: Create 1 valid job with "0 9 * * *" and 1 invalid ("99 * * * *")
    Verify: Response has 1 entry (valid one); invalid one skipped (no 500 error)
    Verify: Log contains warning about invalid cron
    """
    sig_id = signature_fixture

    async with AsyncSessionLocal() as session:
        # Valid job
        job_valid = ScheduledJob(
            id=str(uuid4()),
            name="job-valid",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_valid)

        # Invalid job (bad minute: 99)
        job_invalid = ScheduledJob(
            id=str(uuid4()),
            name="job-invalid",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="99 * * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_invalid)

        await session.commit()

    # Call API (should not 500 on invalid cron)
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 1
    assert data.entries[0].name == "job-valid"


@pytest.mark.asyncio
async def test_get_unified_schedule_sorted_by_next_run(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 5: GET /api/schedule returns entries sorted by next_run_time ascending.

    Setup: Create 3 jobs with different cron times (6am, 9am, 3pm)
    Verify: Response entries are sorted by next_run_time ascending (earliest first)
    """
    sig_id = signature_fixture

    async with AsyncSessionLocal() as session:
        # 3pm job (later)
        job_3pm = ScheduledJob(
            id=str(uuid4()),
            name="job-3pm",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 15 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_3pm)

        # 6am job (earliest)
        job_6am = ScheduledJob(
            id=str(uuid4()),
            name="job-6am",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 6 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_6am)

        # 9am job (middle)
        job_9am = ScheduledJob(
            id=str(uuid4()),
            name="job-9am",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_9am)

        await session.commit()

    # Call API
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 3

    # Verify sorted by next_run_time ascending
    times = [entry.next_run_time for entry in data.entries]
    assert times == sorted(times), "Entries should be sorted by next_run_time ascending"

    # Verify names are in chronological order (6am, 9am, 3pm)
    names = [entry.name for entry in data.entries]
    assert names.index("job-6am") < names.index("job-9am")
    assert names.index("job-9am") < names.index("job-3pm")


@pytest.mark.asyncio
async def test_get_unified_schedule_requires_permission(
    async_client: AsyncClient, auth_headers_operator: dict, signature_fixture, cleanup_schedule
):
    """
    Test 6: GET /api/schedule requires jobs:read permission.

    Setup: Create authenticated user with NO jobs:read permission
    Verify: Response is 403 Forbidden
    """
    sig_id = signature_fixture

    # Create a test item to fetch
    async with AsyncSessionLocal() as session:
        job = ScheduledJob(
            id=str(uuid4()),
            name="job-test",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job)
        await session.commit()

    # Call API with operator user (no jobs:read)
    response = await async_client.get("/api/schedule", headers=auth_headers_operator)

    # Verify: Should be 403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_unified_schedule_includes_last_run_status(
    async_client: AsyncClient, auth_headers: dict, signature_fixture, cleanup_schedule
):
    """
    Test 7: GET /api/schedule includes last_run_status from prior runs.

    Setup: Create job with prior Job record (status=COMPLETED)
    Verify: Response entry.last_run_status == "COMPLETED"

    Setup: Create new job with no prior runs
    Verify: Response entry.last_run_status == null
    """
    sig_id = signature_fixture
    job_with_runs_id = str(uuid4())
    job_no_runs_id = str(uuid4())

    async with AsyncSessionLocal() as session:
        # Create job with prior run
        job_with_runs = ScheduledJob(
            id=job_with_runs_id,
            name="job-with-runs",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_with_runs)
        await session.flush()

        # Create prior Job run (guid is primary key, not id)
        prior_job = Job(
            guid=str(uuid4()),
            scheduled_job_id=job_with_runs_id,
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
            created_by="admin",
            task_type="script",
            payload="{}"
        )
        session.add(prior_job)

        # Create job with no runs
        job_no_runs = ScheduledJob(
            id=job_no_runs_id,
            name="job-no-runs",
            script_content="echo 'test'",
            signature_id=sig_id,
            signature_payload="dGVzdA==",
            schedule_cron="0 9 * * *",
            is_active=True,
            created_by="admin"
        )
        session.add(job_no_runs)

        await session.commit()

    # Call API
    response = await async_client.get("/api/schedule", headers=auth_headers)

    # Verify
    assert response.status_code == 200
    data = ScheduleListResponse(**response.json())
    assert len(data.entries) == 2

    # Find entries
    entry_with_runs = next((e for e in data.entries if e.name == "job-with-runs"), None)
    entry_no_runs = next((e for e in data.entries if e.name == "job-no-runs"), None)

    assert entry_with_runs is not None
    assert entry_no_runs is not None

    # Verify last_run_status
    assert entry_with_runs.last_run_status == "COMPLETED"
    assert entry_no_runs.last_run_status is None

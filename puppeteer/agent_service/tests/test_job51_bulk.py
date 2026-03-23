"""
Phase 51 — Wave 0 test stubs: Bulk job operations (BULK-02, BULK-03, BULK-04).

These tests define the contract for Plan 02 implementation.

Endpoint contracts:
  POST /jobs/bulk-cancel
    - Body: {"guids": [...]}
    - Returns {processed: N, skipped: M} where skipped = jobs not in cancellable state
    - Only PENDING and ASSIGNED jobs can be cancelled; terminal states are skipped

  POST /jobs/bulk-resubmit
    - Body: {"guids": [...]}
    - Resubmits each FAILED/DEAD_LETTER job; returns list of new job guids
    - Each new job has originating_guid set to its source guid

  DELETE /jobs/bulk
    - Body: {"guids": [...]}
    - Deletes only terminal-state jobs (COMPLETED, FAILED, CANCELLED, DEAD_LETTER, SECURITY_REJECTED)
    - Returns {deleted: N, skipped: [...guids...]} for non-terminal jobs
"""
import json
import pytest
import uuid
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from agent_service.main import app, get_db
from agent_service.deps import get_current_user
from agent_service.db import Job


def _make_admin_user():
    fake_user = MagicMock()
    fake_user.username = "test-admin"
    fake_user.role = "admin"
    return fake_user


@pytest.fixture
async def auth_client(db_session):
    """HTTP test client with admin user and test DB injected."""
    fake_user = _make_admin_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_job(db_session, status: str) -> str:
    """Insert a Job directly into the test DB and return its guid."""
    guid = str(uuid.uuid4())
    job = Job(
        guid=guid,
        task_type="script",
        payload=json.dumps({"script_content": "print('hello')"}),
        status=status,
        runtime="python",
    )
    db_session.add(job)
    await db_session.commit()
    return guid


@pytest.mark.anyio
async def test_bulk_cancel_pending(auth_client, db_session):
    """POST /jobs/bulk-cancel with PENDING job guids must return {processed: N, skipped: 0}.

    Setup:
      - Create N PENDING jobs
    Assert:
      - Response status 200
      - Response body: {processed: N, skipped: 0}
      - Each job has status == 'CANCELLED' afterwards
    """
    guid1 = await _create_job(db_session, "PENDING")
    guid2 = await _create_job(db_session, "PENDING")

    resp = await auth_client.post("/jobs/bulk-cancel", json={"guids": [guid1, guid2]})
    assert resp.status_code == 200

    data = resp.json()
    assert data["processed"] == 2
    assert data["skipped"] == 0
    assert data["skipped_guids"] == []

    # Verify jobs were cancelled
    result = await db_session.execute(select(Job).where(Job.guid.in_([guid1, guid2])))
    jobs = result.scalars().all()
    for job in jobs:
        assert job.status == "CANCELLED"


@pytest.mark.anyio
async def test_bulk_cancel_skips_terminal(auth_client, db_session):
    """POST /jobs/bulk-cancel with a mix of PENDING + COMPLETED must skip the COMPLETED ones.

    Setup:
      - Create 2 PENDING jobs and 1 COMPLETED job
      - Submit all 3 guids to bulk-cancel
    Assert:
      - Response status 200
      - Response body: {processed: 2, skipped: 1}
      - The COMPLETED job's status is unchanged
    """
    guid_pending1 = await _create_job(db_session, "PENDING")
    guid_pending2 = await _create_job(db_session, "PENDING")
    guid_completed = await _create_job(db_session, "COMPLETED")

    resp = await auth_client.post(
        "/jobs/bulk-cancel",
        json={"guids": [guid_pending1, guid_pending2, guid_completed]},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["processed"] == 2
    assert data["skipped"] == 1
    assert guid_completed in data["skipped_guids"]

    # COMPLETED job remains COMPLETED
    result = await db_session.execute(select(Job).where(Job.guid == guid_completed))
    job = result.scalar_one()
    assert job.status == "COMPLETED"


@pytest.mark.anyio
async def test_bulk_resubmit_creates_new_jobs(auth_client, db_session):
    """POST /jobs/bulk-resubmit must create N new jobs with originating_guids set.

    Setup:
      - Create 2 FAILED jobs and 1 COMPLETED job
      - Submit all 3 guids to bulk-resubmit
    Assert:
      - Response status 200
      - 2 new jobs are created (one per FAILED job)
      - Each new job has originating_guid == the corresponding source job guid
      - The COMPLETED job is skipped (not resubmitted)
      - Response body contains the list of new guids (or processed/skipped counts)
    """
    guid_failed1 = await _create_job(db_session, "FAILED")
    guid_failed2 = await _create_job(db_session, "FAILED")
    guid_completed = await _create_job(db_session, "COMPLETED")

    resp = await auth_client.post(
        "/jobs/bulk-resubmit",
        json={"guids": [guid_failed1, guid_failed2, guid_completed]},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["processed"] == 2
    assert data["skipped"] == 1
    assert guid_completed in data["skipped_guids"]

    # New jobs exist with correct originating_guid
    result = await db_session.execute(
        select(Job).where(Job.originating_guid.in_([guid_failed1, guid_failed2]))
    )
    new_jobs = result.scalars().all()
    assert len(new_jobs) == 2
    originating_guids = {j.originating_guid for j in new_jobs}
    assert guid_failed1 in originating_guids
    assert guid_failed2 in originating_guids
    for job in new_jobs:
        assert job.status == "PENDING"


@pytest.mark.anyio
async def test_bulk_delete_terminal_only(auth_client, db_session):
    """DELETE /jobs/bulk must delete only terminal-state jobs and skip non-terminal ones.

    Setup:
      - Create 1 COMPLETED job, 1 FAILED job, 1 PENDING job
      - Submit all 3 guids to bulk delete
    Assert:
      - Response status 200
      - Response body: {deleted: 2, skipped: [<pending_guid>]}
      - COMPLETED and FAILED jobs are removed from DB
      - PENDING job remains in DB with status == 'PENDING'
    """
    guid_completed = await _create_job(db_session, "COMPLETED")
    guid_failed = await _create_job(db_session, "FAILED")
    guid_pending = await _create_job(db_session, "PENDING")

    resp = await auth_client.request(
        "DELETE",
        "/jobs/bulk",
        json={"guids": [guid_completed, guid_failed, guid_pending]},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["processed"] == 2
    assert data["skipped"] == 1
    assert guid_pending in data["skipped_guids"]

    # Terminal jobs are gone
    result = await db_session.execute(select(Job).where(Job.guid.in_([guid_completed, guid_failed])))
    remaining = result.scalars().all()
    assert len(remaining) == 0

    # PENDING job still exists
    result2 = await db_session.execute(select(Job).where(Job.guid == guid_pending))
    pending_job = result2.scalar_one_or_none()
    assert pending_job is not None
    assert pending_job.status == "PENDING"

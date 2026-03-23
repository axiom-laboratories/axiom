"""
Phase 51 — Wave 0 test stubs: Job resubmit endpoint (JOB-05).

These tests define the contract for Plan 02 implementation.
All stubs fail immediately with pytest.fail("not implemented").

Endpoint contract:
  POST /jobs/{guid}/resubmit
    - Returns 200 + new job JSON when source job is FAILED or DEAD_LETTER
    - Returns 409 when source job is in a non-resubmittable state (PENDING, RUNNING, COMPLETED, CANCELLED)
    - New job gets a fresh guid, status=PENDING, retry_count=0
    - New job has originating_guid == source job guid
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


async def _create_job(db_session, status: str, retry_count: int = 0) -> str:
    """Insert a Job directly into the test DB and return its guid."""
    guid = str(uuid.uuid4())
    job = Job(
        guid=guid,
        task_type="script",
        payload=json.dumps({"script_content": "print('hello')"}),
        status=status,
        runtime="python",
        name="test-job",
        target_tags=json.dumps(["linux"]),
        retry_count=retry_count,
    )
    db_session.add(job)
    await db_session.commit()
    return guid


@pytest.mark.anyio
async def test_resubmit_creates_new_guid(auth_client, db_session):
    """POST /jobs/{guid}/resubmit on a FAILED job must return 200 with a NEW guid.

    Setup:
      - Create a job with status=FAILED
    Assert:
      - Response status 200
      - Response body contains a 'guid' field
      - The new guid is different from the original job guid
      - The new job's originating_guid equals the original job guid
    """
    original_guid = await _create_job(db_session, "FAILED")
    resp = await auth_client.post(f"/jobs/{original_guid}/resubmit")
    assert resp.status_code == 200

    data = resp.json()
    assert "guid" in data
    assert data["guid"] != original_guid
    assert data["originating_guid"] == original_guid


@pytest.mark.anyio
async def test_resubmit_sets_pending(auth_client, db_session):
    """POST /jobs/{guid}/resubmit must create a new job with status=PENDING and retry_count=0.

    Setup:
      - Create a job with status=FAILED, retry_count=3
    Assert:
      - The new job has status == 'PENDING'
      - The new job has retry_count == 0
      - The new job inherits task_type, payload, and target_tags from the original
    """
    original_guid = await _create_job(db_session, "FAILED", retry_count=3)
    resp = await auth_client.post(f"/jobs/{original_guid}/resubmit")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "PENDING"

    # Verify the new job in DB has retry_count=0 and inherits fields
    new_guid = data["guid"]
    result = await db_session.execute(select(Job).where(Job.guid == new_guid))
    new_job = result.scalar_one_or_none()
    assert new_job is not None
    assert new_job.retry_count == 0
    assert new_job.task_type == "script"
    assert new_job.target_tags == json.dumps(["linux"])


@pytest.mark.anyio
async def test_resubmit_rejects_non_failed(auth_client, db_session):
    """POST /jobs/{guid}/resubmit on a PENDING or COMPLETED job must return 409.

    Setup:
      - Create a job with status=PENDING
    Assert:
      - Response status 409

    Also check for status=COMPLETED:
      - Response status 409

    Rationale: only terminal error states (FAILED, DEAD_LETTER) are resubmittable.
    Active or successfully completed jobs must not be resubmitted.
    """
    pending_guid = await _create_job(db_session, "PENDING")
    resp = await auth_client.post(f"/jobs/{pending_guid}/resubmit")
    assert resp.status_code == 409

    completed_guid = await _create_job(db_session, "COMPLETED")
    resp2 = await auth_client.post(f"/jobs/{completed_guid}/resubmit")
    assert resp2.status_code == 409


@pytest.mark.anyio
async def test_resubmit_dead_letter_allowed(auth_client, db_session):
    """POST /jobs/{guid}/resubmit on a DEAD_LETTER job must return 200.

    Setup:
      - Create a job with status=DEAD_LETTER
    Assert:
      - Response status 200
      - New job created with originating_guid set to source job guid
      - New job has status=PENDING
    """
    original_guid = await _create_job(db_session, "DEAD_LETTER")
    resp = await auth_client.post(f"/jobs/{original_guid}/resubmit")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["originating_guid"] == original_guid

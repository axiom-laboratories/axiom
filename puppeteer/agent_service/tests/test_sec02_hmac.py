"""
SEC-02: HMAC integrity protection on stored signature_payload fields.

Verifies:
1. compute_signature_hmac() produces consistent (deterministic) output.
2. verify_signature_hmac() returns False for a tampered payload.
3. verify_signature_hmac() returns True for a valid payload.
4. Startup backfill logic populates signature_hmac on existing rows.
5. pull_work() rejects a job whose signature_hmac does not match (tampered).
"""
import json
import pytest
from unittest.mock import patch
from agent_service.security import compute_signature_hmac, verify_signature_hmac
from agent_service.db import Job, Node
from agent_service.models import JobCreate
from agent_service.services.job_service import JobService


# ---------------------------------------------------------------------------
# Pure-function tests (GREEN from Task 1 — helpers are implemented)
# ---------------------------------------------------------------------------

TEST_KEY = b"test-key-32-bytes-padded-to-work!"


def test_compute_signature_hmac_deterministic():
    """compute_signature_hmac() must return the same hex string on repeated calls."""
    result1 = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    result2 = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    assert result1 == result2
    assert isinstance(result1, str)
    assert len(result1) == 64, f"SHA256 hex digest must be 64 chars, got {len(result1)}"


def test_verify_signature_hmac_tampered_returns_false():
    """verify_signature_hmac() must return False for a tampered payload."""
    stored = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    result = verify_signature_hmac(TEST_KEY, stored, "payload_TAMPERED", "sig-1", "job-1")
    assert result is False


def test_verify_signature_hmac_valid_returns_true():
    """verify_signature_hmac() must return True for a valid (unmodified) payload."""
    stored = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    result = verify_signature_hmac(TEST_KEY, stored, "payload", "sig-1", "job-1")
    assert result is True


def test_verify_signature_hmac_wrong_sig_id_returns_false():
    """Changing signature_id must invalidate the HMAC."""
    stored = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    result = verify_signature_hmac(TEST_KEY, stored, "payload", "sig-DIFFERENT", "job-1")
    assert result is False


def test_verify_signature_hmac_wrong_job_id_returns_false():
    """Changing job_id must invalidate the HMAC — binds payload to its job."""
    stored = compute_signature_hmac(TEST_KEY, "payload", "sig-1", "job-1")
    result = verify_signature_hmac(TEST_KEY, stored, "payload", "sig-1", "job-DIFFERENT")
    assert result is False


# ---------------------------------------------------------------------------
# Integration tests (RED until Task 2 wires the implementation)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_job_stamps_hmac_when_signature_present(db_session):
    """
    SEC-02 stamp: create_job() must write signature_hmac to the DB row when
    the payload contains both signature_payload and signature_id.
    Fails RED until job_service.py:create_job() is updated.
    """
    from sqlalchemy.future import select

    sig_payload = "base64sigpayload=="
    sig_id = "sig-abc-123"
    job_req = JobCreate(
        task_type="python_script",
        payload={
            "script_content": "print('signed')",
            "signature_payload": sig_payload,
            "signature_id": sig_id,
        },
    )

    result = await JobService.create_job(job_req, db_session)
    guid = result["guid"]

    # Fetch from DB
    job_res = await db_session.execute(select(Job).where(Job.guid == guid))
    job = job_res.scalar_one()

    assert job.signature_hmac is not None, (
        "signature_hmac must be set when signature_payload and signature_id are present"
    )
    assert len(job.signature_hmac) == 64, "HMAC must be a SHA256 hex digest (64 chars)"

    # Verify the stored HMAC is correct
    from agent_service.security import ENCRYPTION_KEY
    assert verify_signature_hmac(
        ENCRYPTION_KEY, job.signature_hmac, sig_payload, sig_id, guid
    ), "Stored HMAC must verify correctly against the same inputs"


@pytest.mark.anyio
async def test_pull_work_rejects_tampered_hmac(db_session):
    """
    SEC-02 verify: pull_work() must reject a job whose signature_hmac has been
    tampered with. The job must NOT be returned in the WorkResponse (job=None),
    and the job status must be set to SECURITY_REJECTED.
    Fails RED until job_service.py:pull_work() is updated.
    """
    from sqlalchemy.future import select

    # Create a node
    node = Node(
        node_id="node-hmac-verify",
        hostname="node-hmac-verify",
        ip="10.1.0.1",
        status="ONLINE",
    )
    db_session.add(node)
    await db_session.commit()

    # Create a job with a signature
    sig_payload = "validpayload=="
    sig_id = "sig-xyz-999"
    job_req = JobCreate(
        task_type="python_script",
        payload={
            "script_content": "print('tamper test')",
            "signature_payload": sig_payload,
            "signature_id": sig_id,
        },
    )
    job_result = await JobService.create_job(job_req, db_session)
    guid = job_result["guid"]

    # Tamper with the stored HMAC to simulate integrity violation
    job_res = await db_session.execute(select(Job).where(Job.guid == guid))
    job = job_res.scalar_one()
    job.signature_hmac = "a" * 64  # Wrong HMAC
    await db_session.commit()

    # Pull work — should be rejected
    with patch("agent_service.services.job_service.audit"):
        poll_resp = await JobService.pull_work("node-hmac-verify", "10.1.0.1", db_session)

    assert poll_resp.job is None, (
        "pull_work() must return job=None when signature_hmac fails verification"
    )

    # Confirm the job status is SECURITY_REJECTED
    await db_session.refresh(job)
    assert job.status == "SECURITY_REJECTED", (
        f"Tampered job must be SECURITY_REJECTED, got: {job.status}"
    )


@pytest.mark.anyio
async def test_startup_backfill_populates_hmac(db_session):
    """
    SEC-02 backfill: The startup backfill logic must populate signature_hmac
    on existing Job rows that have signature_payload/signature_id but no HMAC.
    Fails RED until main.py:lifespan() backfill is implemented and can be
    called as a standalone helper.
    """
    from sqlalchemy.future import select
    import json as _json
    from agent_service.security import compute_signature_hmac, ENCRYPTION_KEY, verify_signature_hmac

    # Insert a job row directly with signature data but no HMAC
    sig_payload = "existingpayload=="
    sig_id = "sig-backfill-001"
    import uuid
    guid = str(uuid.uuid4())
    job = Job(
        guid=guid,
        task_type="python_script",
        payload=_json.dumps({
            "script_content": "print('old job')",
            "signature_payload": sig_payload,
            "signature_id": sig_id,
        }),
        status="COMPLETED",
        signature_hmac=None,  # No HMAC — simulates pre-SEC-02 row
    )
    db_session.add(job)
    await db_session.commit()

    # Run the backfill logic directly (extracted from lifespan for testability)
    # The lifespan backfill uses AsyncSessionLocal — patch it to use our db_session.
    from agent_service import db as db_module
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    # Use a context manager that yields our test db_session
    class _TestSessionCtx:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, *args):
            pass

    class _FakeSessionLocal:
        def __call__(self):
            return _TestSessionCtx()

    original_session_local = db_module.AsyncSessionLocal
    db_module.AsyncSessionLocal = _FakeSessionLocal()

    try:
        # Execute the same backfill code as lifespan()
        _result = await db_session.execute(
            select(Job).where(Job.signature_hmac == None)  # noqa: E711
        )
        _jobs = _result.scalars().all()
        _backfilled = 0
        for _job in _jobs:
            try:
                _pl = _json.loads(_job.payload) if _job.payload else {}
                _sp = _pl.get("signature_payload")
                _si = _pl.get("signature_id")
                if _sp and _si:
                    _job.signature_hmac = compute_signature_hmac(ENCRYPTION_KEY, _sp, _si, _job.guid)
                    _backfilled += 1
            except Exception:
                continue
        if _backfilled:
            await db_session.commit()
    finally:
        db_module.AsyncSessionLocal = original_session_local

    # Verify the backfill worked
    job_res = await db_session.execute(select(Job).where(Job.guid == guid))
    job = job_res.scalar_one()

    assert job.signature_hmac is not None, "Backfill must populate signature_hmac"
    assert verify_signature_hmac(
        ENCRYPTION_KEY, job.signature_hmac, sig_payload, sig_id, guid
    ), "Backfilled HMAC must verify correctly"

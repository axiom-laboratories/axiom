import pytest
import uuid
import json
from unittest.mock import AsyncMock, patch
from agent_service.services.scheduler_service import SchedulerService
from agent_service.models import JobDefinitionCreate, JobDefinitionUpdate
from agent_service.db import User, Signature, ScheduledJob, Job, Alert
from sqlalchemy.future import select
from sqlalchemy import text
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

@pytest.fixture
def test_user():
    return User(username="admin")

@pytest.fixture
async def valid_signature(db_session):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    sig = Signature(id=uuid.uuid4().hex, name="Test Sig", public_key=pub_pem, uploaded_by="admin")
    db_session.add(sig)
    await db_session.commit()
    return sig, private_key


def _sign(private_key, content: str) -> str:
    """Helper: sign a string, return base64-encoded signature."""
    return base64.b64encode(private_key.sign(content.encode())).decode()


async def _make_active_job(db_session, sig, private_key, name: str = "Test Job") -> ScheduledJob:
    """Helper: create and persist a signed ACTIVE ScheduledJob."""
    script = "print('hello')"
    sig_b64 = _sign(private_key, script)
    job = ScheduledJob(
        id=uuid.uuid4().hex,
        name=name,
        script_content=script,
        signature_id=sig.id,
        signature_payload=sig_b64,
        is_active=True,
        status="ACTIVE",
        created_by="admin",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job

@pytest.mark.anyio
async def test_create_job_definition(db_session, test_user, valid_signature):
    sig, private_key = valid_signature
    script = "print('hello')"
    signature_bytes = private_key.sign(script.encode())
    sig_b64 = base64.b64encode(signature_bytes).decode()

    def_req = JobDefinitionCreate(
        name="Scheduled Hello",
        script_content=script,
        signature_id=sig.id,
        signature=sig_b64,
        schedule_cron="0 * * * *",
        target_tags=["linux"]
    )

    scheduler_service = SchedulerService()
    new_def = await scheduler_service.create_job_definition(def_req, test_user, db_session)
    
    assert new_def.name == "Scheduled Hello"
    assert new_def.is_active is True

@pytest.mark.anyio
async def test_execute_scheduled_job(db_session, test_user, valid_signature):
    sig, private_key = valid_signature
    script = "print('scheduled')"
    signature_bytes = private_key.sign(script.encode())
    sig_b64 = base64.b64encode(signature_bytes).decode()

    # Manually insert a ScheduledJob for execution test
    s_job = ScheduledJob(
        id="test_sched_id",
        name="Test Execution",
        script_content=script,
        signature_id=sig.id,
        signature_payload=sig_b64,
        target_tags=json.dumps(["linux"]),
        is_active=True,
        created_by="admin"
    )
    db_session.add(s_job)
    await db_session.commit()

    scheduler_service = SchedulerService()
    # We need to mock AsyncSessionLocal if we want it to use our test db_session
    # For now, let's just test the logic if possible or rely on end-to-end
    # Actually scheduler_service uses AsyncSessionLocal() which might not be our test db
    # Let's verify if we can inject db into execute_scheduled_job or just use it as is

    # For unit testing the service logic, maybe refactor service to take db session?
    # But usually services handle their own sessions.

    # Let's just verify it runs without crashing for now.
    await scheduler_service.execute_scheduled_job("test_sched_id")

    # Check if a Job was created in the DB
    # Note: execute_scheduled_job uses its own session, so we need to refresh or re-query
    from sqlalchemy.future import select
    result = await db_session.execute(select(Job).where(Job.scheduled_job_id == "test_sched_id"))
    job = result.scalar_one_or_none()
    assert job is not None
    assert job.status == "PENDING"


# ---------------------------------------------------------------------------
# SCHED-01 / SCHED-02 / SCHED-04 — DRAFT transition + skip-log + alert tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_update_script_without_sig_transitions_to_draft(db_session, test_user, valid_signature):
    """PATCH with new script_content + no signature → status=DRAFT, HTTP 200 (no exception)."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="Draft Test 1")

    svc = SchedulerService()
    update_req = JobDefinitionUpdate(script_content="print('changed')")

    with patch("agent_service.services.scheduler_service.AlertService") as mock_alert_svc:
        mock_alert_svc.create_alert = AsyncMock(return_value=None)
        updated = await svc.update_job_definition(job.id, update_req, test_user, db_session)

    assert updated.status == "DRAFT"
    assert updated.script_content == "print('changed')"


@pytest.mark.anyio
async def test_update_script_with_sig_stays_active(db_session, test_user, valid_signature):
    """PATCH with new script_content + valid new signature → status stays ACTIVE."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="Active Stay Test")

    new_script = "print('updated with sig')"
    new_sig_b64 = _sign(private_key, new_script)

    svc = SchedulerService()
    update_req = JobDefinitionUpdate(
        script_content=new_script,
        signature=new_sig_b64,
        signature_id=sig.id,
    )

    updated = await svc.update_job_definition(job.id, update_req, test_user, db_session)

    assert updated.status == "ACTIVE"
    assert updated.script_content == new_script


@pytest.mark.anyio
async def test_draft_reedits_no_duplicate_alert(db_session, test_user, valid_signature):
    """PATCH a DRAFT job with new script_content again → only 1 Alert row total (no second alert)."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="No Dup Alert Test")

    svc = SchedulerService()

    # First edit — transitions ACTIVE → DRAFT, creates 1 alert
    with patch("agent_service.services.scheduler_service.AlertService") as mock_alert_svc:
        mock_alert_svc.create_alert = AsyncMock(return_value=None)
        await svc.update_job_definition(
            job.id,
            JobDefinitionUpdate(script_content="print('edit 1')"),
            test_user,
            db_session,
        )

    # Second edit — already DRAFT, should NOT create another alert
    with patch("agent_service.services.scheduler_service.AlertService") as mock_alert_svc:
        mock_alert_svc.create_alert = AsyncMock(return_value=None)
        await svc.update_job_definition(
            job.id,
            JobDefinitionUpdate(script_content="print('edit 2')"),
            test_user,
            db_session,
        )
        # create_alert must NOT have been called on the second DRAFT→DRAFT re-edit
        mock_alert_svc.create_alert.assert_not_called()


@pytest.mark.anyio
async def test_resign_without_script_change_reactivates(db_session, test_user, valid_signature):
    """PATCH with valid signature_id + signature but no script_content → status=ACTIVE."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="Resign Test")

    svc = SchedulerService()

    # First put it in DRAFT
    with patch("agent_service.services.scheduler_service.AlertService") as mock_alert_svc:
        mock_alert_svc.create_alert = AsyncMock(return_value=None)
        await svc.update_job_definition(
            job.id,
            JobDefinitionUpdate(script_content="print('unsigned edit')"),
            test_user,
            db_session,
        )

    # Re-fetch to get current script_content
    from sqlalchemy.future import select as sa_select
    result = await db_session.execute(sa_select(ScheduledJob).where(ScheduledJob.id == job.id))
    job_draft = result.scalar_one()
    assert job_draft.status == "DRAFT"

    # Now re-sign (no script_content change, just new signature)
    new_sig_b64 = _sign(private_key, job_draft.script_content)
    updated = await svc.update_job_definition(
        job.id,
        JobDefinitionUpdate(signature=new_sig_b64, signature_id=sig.id),
        test_user,
        db_session,
    )

    assert updated.status == "ACTIVE"


@pytest.mark.anyio
async def test_draft_skip_log_message(db_session, test_user, valid_signature):
    """execute_scheduled_job() on a DRAFT job → AuditLog row detail contains verbatim skip message."""
    sig, private_key = valid_signature
    draft_job_id = uuid.uuid4().hex
    script = "print('draft skip test')"
    sig_b64 = _sign(private_key, script)

    draft_job = ScheduledJob(
        id=draft_job_id,
        name="Draft Skip Log",
        script_content=script,
        signature_id=sig.id,
        signature_payload=sig_b64,
        is_active=True,
        status="DRAFT",
        created_by="admin",
    )
    db_session.add(draft_job)
    await db_session.commit()

    svc = SchedulerService()
    await svc.execute_scheduled_job(draft_job_id)

    # The AuditLog detail should contain the verbatim reason string
    result = await db_session.execute(
        text("SELECT detail FROM audit_log WHERE resource_id = :rid ORDER BY rowid DESC LIMIT 1"),
        {"rid": draft_job_id},
    )
    row = result.fetchone()
    assert row is not None, "Expected an AuditLog row for the DRAFT skip"
    detail = json.loads(row[0])
    assert detail.get("reason") == "Skipped: job in DRAFT state, pending re-signing"


@pytest.mark.anyio
async def test_draft_transition_creates_alert(db_session, test_user, valid_signature):
    """PATCH ACTIVE job with script without sig → Alert row with type=scheduled_job_draft, severity=WARNING."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="Alert Creation Test")

    svc = SchedulerService()
    update_req = JobDefinitionUpdate(script_content="print('trigger draft')")

    # Patch AlertService to actually write to the Alert table
    from agent_service.services.alert_service import AlertService
    original_create = AlertService.create_alert

    async def _real_create_alert(db, *, type, severity, message, resource_id=None):
        alert = Alert(type=type, severity=severity, message=message, resource_id=resource_id)
        db.add(alert)
        await db.flush()
        return alert

    with patch("agent_service.services.scheduler_service.AlertService") as mock_cls:
        mock_cls.create_alert = _real_create_alert
        await svc.update_job_definition(job.id, update_req, test_user, db_session)

    # Verify Alert row was created
    result = await db_session.execute(
        select(Alert).where(Alert.resource_id == job.id)
    )
    alerts = result.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].type == "scheduled_job_draft"
    assert alerts[0].severity == "WARNING"


@pytest.mark.anyio
async def test_signature_removal_transitions_to_draft(db_session, test_user, valid_signature):
    """PATCH ACTIVE job with a different signature_id but no signature payload → status=DRAFT."""
    sig, private_key = valid_signature
    job = await _make_active_job(db_session, sig, private_key, name="Sig Removal Test")

    # Create a second signature record to use as the "new" signature_id
    private_key2 = ed25519.Ed25519PrivateKey.generate()
    pub_pem2 = private_key2.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    sig2 = Signature(id=uuid.uuid4().hex, name="Sig 2", public_key=pub_pem2, uploaded_by="admin")
    db_session.add(sig2)
    await db_session.commit()

    svc = SchedulerService()
    # Replace signature_id without providing a valid signature payload → DRAFT
    update_req = JobDefinitionUpdate(signature_id=sig2.id)

    with patch("agent_service.services.scheduler_service.AlertService") as mock_alert_svc:
        mock_alert_svc.create_alert = AsyncMock(return_value=None)
        updated = await svc.update_job_definition(job.id, update_req, test_user, db_session)

    assert updated.status == "DRAFT"

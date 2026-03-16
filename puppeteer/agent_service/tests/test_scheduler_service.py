import pytest
import uuid
import json
from agent_service.services.scheduler_service import SchedulerService
from agent_service.models import JobDefinitionCreate
from agent_service.db import User, Signature, ScheduledJob, Job
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

@pytest.fixture
def test_user():
    return User(username="admin", role="admin")

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

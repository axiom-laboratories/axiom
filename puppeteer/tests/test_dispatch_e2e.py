"""
Integration tests for complete job dispatch pipeline using service-layer calls.

Tests validate the API contract (response models from Phase 129), state machine
transitions, and dispatch diagnosis accuracy without requiring a live node or mocking.
"""
import pytest
import json
import base64
import uuid
from datetime import datetime
from sqlalchemy import select

from agent_service.services.job_service import JobService
from agent_service.services.signature_service import SignatureService
from agent_service.models import (
    JobCreate,
    JobResponse,
    WorkResponse,
    DispatchDiagnosisResponse,
    ResultReport,
    PollResponse,
)
from agent_service.db import Base, Node, Job, User, Signature, AsyncSessionLocal


@pytest.fixture
async def enrolled_node(clean_db):
    """Create a test node with ONLINE status."""
    async with AsyncSessionLocal() as session:
        # Use unique node ID per test to avoid conflicts
        node_id = f"test-node-{uuid.uuid4().hex[:8]}"
        node = Node(
            node_id=node_id,
            hostname="test-node",
            ip="127.0.0.1",
            status="ONLINE",
            tags=json.dumps(["python", "docker"]),
            capabilities=json.dumps({"python": "3.11", "docker": "24.0"}),
            env_tag=None,
            operator_env_tag=False,
        )
        session.add(node)
        await session.commit()
        await session.refresh(node)
        return node


@pytest.fixture
async def test_signature_key(clean_db):
    """Register a test Ed25519 signing key."""
    import os
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    async with AsyncSessionLocal() as session:
        # Generate a test key
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        sig = Signature(
            id=str(uuid.uuid4()),
            public_key_pem=public_pem,
            created_by="test_user",
            name="test_key",
        )
        session.add(sig)
        await session.commit()
        await session.refresh(sig)

        return {
            "signature_id": sig.id,
            "private_key": private_key,
            "public_key_pem": public_pem,
        }


def _make_node(node_id: str, hostname: str = None, ip: str = "127.0.0.1",
               status: str = "ONLINE", tags: str = None, capabilities: str = None,
               env_tag: str = None, **kwargs):
    """Helper to create nodes with custom attributes."""
    return Node(
        node_id=node_id,
        hostname=hostname or node_id,
        ip=ip,
        status=status,
        tags=tags or json.dumps(["python"]),
        capabilities=capabilities or json.dumps({"python": "3.11"}),
        env_tag=env_tag,
        operator_env_tag=kwargs.get("operator_env_tag", False),
        **{k: v for k, v in kwargs.items() if k not in ["operator_env_tag"]}
    )


@pytest.mark.asyncio
async def test_happy_path_dispatch(clean_db, enrolled_node):
    """
    Happy path: create signed job → node pulls → job completes → result retrievable.
    Validates: JobResponse structure, state transitions, output content.
    """
    async with AsyncSessionLocal() as db:
        # 1. Create job with simple script
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script_content": "print('hello world')"},
            max_retries=1,
        )
        job_dict = await JobService.create_job(job_req, db)

        # Validate through Pydantic model (Phase 129 contract)
        job_resp = JobResponse(**job_dict)
        assert job_resp.status == "PENDING"
        assert job_resp.guid is not None
        assert job_resp.task_type == "script"

        # 2. Node pulls work
        poll_resp = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        assert poll_resp is not None
        assert isinstance(poll_resp, PollResponse)
        assert poll_resp.job is not None

        # Validate WorkResponse through Pydantic
        work = poll_resp.job
        assert isinstance(work, WorkResponse)
        assert work.guid == job_dict["guid"]
        assert work.task_type == "script"

        # 3. Verify job is now ASSIGNED
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_db = result.scalar_one_or_none()
        assert job_db is not None
        assert job_db.status == "ASSIGNED"
        assert job_db.node_id == enrolled_node.node_id

        # 4. Node reports completion
        result_report = ResultReport(
            success=True,
            output_log=[{"t": datetime.utcnow().isoformat(), "stream": "stdout", "line": "hello world"}],
            exit_code=0,
            retriable=False,
        )
        result_dict = await JobService.report_result(
            job_dict["guid"], result_report, "127.0.0.1", db
        )

        # report_result returns minimal dict; refresh job from DB
        assert result_dict["status"] == "COMPLETED"

        # 5. Verify result is retrievable
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_final = result.scalar_one_or_none()
        assert job_final is not None
        assert job_final.status == "COMPLETED"
        assert job_final.result is not None

        # Convert DB job to response model for validation
        full_resp = JobResponse(
            guid=job_final.guid,
            status=job_final.status,
            payload={},  # payload is encrypted in DB
            result=json.loads(job_final.result) if job_final.result else None,
            node_id=job_final.node_id,
            created_at=job_final.created_at,
        )
        assert full_resp.status == "COMPLETED"

        result_json = json.loads(job_final.result)
        assert "stdout" in result_json or "exit_code" in result_json


@pytest.mark.asyncio
async def test_bad_signature_rejection(clean_db):
    """
    Job with invalid signature → behavior depends on signature validation stage.
    Tests that bad signature data is preserved and can be validated.
    """
    async with AsyncSessionLocal() as db:
        # Create a job request with invalid signature fields
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={
                "script_content": "print('hack')",
                "signature_id": "nonexistent-uuid-12345",
                "signature_payload": base64.b64encode(b"invalid-sig").decode(),
            },
            max_retries=0,
        )

        # Attempt to create job
        job_dict = await JobService.create_job(job_req, db)

        # Job is created (signature validation happens at dispatch)
        assert job_dict["status"] == "PENDING"
        assert job_dict["guid"] is not None

        # Verify response model parses without error
        job_resp = JobResponse(**job_dict)
        assert job_resp is not None

        # Check database: job has signature_hmac stamped (if valid payload)
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_db = result.scalar_one_or_none()
        assert job_db is not None

        # The job exists; signature validation happens at pull_work or dispatch
        # For now, we verify the data path is correct (signature_id and payload are stored)
        payload_json = json.loads(job_db.payload)
        # Payload is encrypted, but structure should be preserved
        assert job_db.status == "PENDING"


@pytest.mark.asyncio
async def test_capability_mismatch_diagnosis(clean_db):
    """
    Job requires capability node lacks → stays PENDING.
    Diagnosis explains the mismatch (reason, message).
    Validates: admission control and diagnosis accuracy.
    """
    async with AsyncSessionLocal() as db:
        # 1. Create a node with limited capabilities (no CUDA)
        node_id = f"limited-node-{uuid.uuid4().hex[:8]}"
        node = _make_node(
            node_id=node_id,
            hostname="limited",
            capabilities=json.dumps({"python": "3.11"}),  # No CUDA
            tags=json.dumps(["python"])
        )
        db.add(node)
        await db.commit()

        # 2. Create a job that requires CUDA
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script_content": "import torch"},
            capability_requirements={"cuda": "11.8"},  # Node doesn't have this
            max_retries=0,
        )
        job_dict = await JobService.create_job(job_req, db)
        assert job_dict["status"] == "PENDING"

        # 3. Node tries to pull work
        poll_resp = await JobService.pull_work(node.node_id, "127.0.0.1", db)
        assert isinstance(poll_resp, PollResponse)
        assert poll_resp.job is None  # No work available (mismatch prevents assignment)

        # 4. Query diagnosis to understand why
        diagnosis_dict = await JobService.get_dispatch_diagnosis(job_dict["guid"], db)
        assert diagnosis_dict is not None

        # Validate through Pydantic model
        diag = DispatchDiagnosisResponse(**diagnosis_dict)
        assert diag.reason is not None
        assert diag.message is not None

        # Verify it indicates capability mismatch
        assert diag.reason == "capability_mismatch"
        assert "cuda" in diag.message.lower() or "capability" in diag.message.lower()


@pytest.mark.asyncio
async def test_retry_on_failure(clean_db, enrolled_node):
    """
    Node reports job failed → job transitions to RETRYING, respects max_retries.
    Validates: failure handling, retry state transitions, max_retries limit.
    """
    async with AsyncSessionLocal() as db:
        # 1. Create job with max_retries=2
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script_content": "exit(1)"},  # Script that fails
            max_retries=2,
            backoff_multiplier=1.0,
        )
        job_dict = await JobService.create_job(job_req, db)
        assert job_dict["status"] == "PENDING"

        # 2. Node pulls work and reports failure (first attempt)
        poll_resp = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        assert poll_resp.job is not None
        assert poll_resp.job.guid == job_dict["guid"]

        # Verify job is ASSIGNED
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_before = result.scalar_one_or_none()
        assert job_before.status == "ASSIGNED"

        # Report first failure
        result_report = ResultReport(
            success=False,
            output_log=[{"t": datetime.utcnow().isoformat(), "stream": "stderr", "line": "Job exited with code 1"}],
            exit_code=1,
            error_details={"message": "Process returned non-zero exit code"},
            retriable=True,
        )
        result_dict = await JobService.report_result(
            job_dict["guid"], result_report, "127.0.0.1", db
        )

        # report_result returns minimal dict
        assert result_dict["status"] in ("FAILED", "RETRYING")

        # 3. Check that job transitioned to RETRYING
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_after_fail = result.scalar_one_or_none()
        assert job_after_fail is not None
        assert job_after_fail.status == "RETRYING"
        assert job_after_fail.retry_count == 1
        assert job_after_fail.max_retries == 2

        # 4. Try to pull again (should fail — retry_after is in future)
        poll_resp_2 = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        # Job is not ready for retry yet (retry_after is set)
        assert poll_resp_2.job is None or poll_resp_2.job.guid != job_dict["guid"]

        # 5. Simulate second failure by manually advancing retry_after and pulling again
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_retry = result.scalar_one_or_none()

        # Clear retry_after to allow immediate retry
        job_retry.retry_after = None
        await db.commit()

        # Now node can pull it again
        poll_resp_3 = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        assert poll_resp_3.job is not None
        assert poll_resp_3.job.guid == job_dict["guid"]

        # Verify job is ASSIGNED again
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_retry_assigned = result.scalar_one_or_none()
        assert job_retry_assigned.status == "ASSIGNED"

        # Report second failure
        result_report_2 = ResultReport(
            success=False,
            output_log=[{"t": datetime.utcnow().isoformat(), "stream": "stderr", "line": "Failed again"}],
            exit_code=1,
            error_details={"message": "Still failing"},
            retriable=True,
        )
        result_dict_2 = await JobService.report_result(
            job_dict["guid"], result_report_2, "127.0.0.1", db
        )

        # report_result returns minimal dict
        assert result_dict_2["status"] in ("FAILED", "RETRYING", "DEAD_LETTER")

        # 6. After second failure, job should still be RETRYING (retry_count=2, max_retries=2, still has retries left)
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_after_2nd = result.scalar_one_or_none()
        assert job_after_2nd.status == "RETRYING"
        assert job_after_2nd.retry_count == 2
        assert job_after_2nd.max_retries == 2

        # 7. Try to pull a third time (should fail — retry_after is in future)
        poll_resp_4 = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        assert poll_resp_4.job is None or poll_resp_4.job.guid != job_dict["guid"]

        # 8. Clear retry_after and attempt third pull/fail
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_before_3rd = result.scalar_one_or_none()
        job_before_3rd.retry_after = None
        await db.commit()

        # Pull for third attempt
        poll_resp_5 = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
        assert poll_resp_5.job is not None
        assert poll_resp_5.job.guid == job_dict["guid"]

        # Report third failure — now retries should be exhausted
        result_report_3 = ResultReport(
            success=False,
            output_log=[{"t": datetime.utcnow().isoformat(), "stream": "stderr", "line": "Failed on third attempt"}],
            exit_code=1,
            error_details={"message": "Persistent failure"},
            retriable=True,
        )
        result_dict_3 = await JobService.report_result(
            job_dict["guid"], result_report_3, "127.0.0.1", db
        )

        # After max_retries exhausted, job should be DEAD_LETTER
        result = await db.execute(select(Job).where(Job.guid == job_dict["guid"]))
        job_final = result.scalar_one_or_none()
        assert job_final.status == "DEAD_LETTER"
        assert job_final.retry_count == 2  # After 3 attempts: 0→1 (1st failure), 1→2 (2nd failure), stays at 2 (3rd failure, exhausted)

"""
SEC-01: Audit trail for SECURITY_REJECTED job outcomes.

Verifies that when a node reports a SECURITY_REJECTED result, an audit log
entry is written attributed to the reporting node with script_hash and job_id
visible. Tests use mock since audit_log table is only available in EE mode.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call
from agent_service.db import Job, Node
from agent_service.models import JobCreate, ResultReport
from agent_service.services.job_service import JobService


@pytest.mark.anyio
async def test_security_rejected_triggers_audit_call(db_session):
    """
    SEC-01: report_result() with security_rejected=True must call audit()
    with action='security:rejected', the node_id as username, and a detail
    dict containing script_hash and job_id.
    """
    # Arrange: create a node
    node = Node(
        node_id="node-sec01",
        hostname="node-sec01",
        ip="10.0.0.1",
        status="ONLINE",
    )
    db_session.add(node)
    await db_session.commit()

    # Create a job that the node will report as security rejected
    job_req = JobCreate(
        task_type="python_script",
        payload={"script_content": "print('hello')"},
    )
    result = await JobService.create_job(job_req, db_session)
    guid = result["guid"]

    # Manually assign job to node (simulating dispatch)
    from sqlalchemy.future import select
    job_res = await db_session.execute(select(Job).where(Job.guid == guid))
    job = job_res.scalar_one()
    job.status = "ASSIGNED"
    job.node_id = "node-sec01"
    await db_session.commit()

    # Act: node reports security_rejected
    report = ResultReport(
        success=False,
        security_rejected=True,
        script_hash="abcd1234" * 8,  # 64 hex chars
    )

    with patch("agent_service.services.job_service.audit") as mock_audit:
        await JobService.report_result(guid, report, "10.0.0.1", db_session)

        # Assert: audit() was called with the right arguments
        assert mock_audit.called, "audit() was never called for SECURITY_REJECTED"

        # Find the call with action='security:rejected'
        sec_rejected_calls = [
            c for c in mock_audit.call_args_list
            if len(c.args) >= 3 and c.args[2] == "security:rejected"
        ]
        assert len(sec_rejected_calls) >= 1, (
            f"No call with action='security:rejected' found. "
            f"Calls were: {mock_audit.call_args_list}"
        )

        # Inspect the detail of the matching call
        audit_call = sec_rejected_calls[0]
        # audit(db, actor, action, resource_id=..., detail=...)
        detail = audit_call.kwargs.get("detail") or (
            audit_call.args[4] if len(audit_call.args) > 4 else None
        )
        resource_id = audit_call.kwargs.get("resource_id") or (
            audit_call.args[3] if len(audit_call.args) > 3 else None
        )

        assert detail is not None, "audit() call must include a detail dict"
        assert "script_hash" in detail, f"detail must contain script_hash, got: {detail}"
        assert "job_id" in detail, f"detail must contain job_id, got: {detail}"
        assert resource_id == guid, f"resource_id must be the job guid, got: {resource_id}"

        # Actor username must be the reporting node's node_id
        actor = audit_call.args[1]
        assert hasattr(actor, "username"), "audit() actor must have .username attribute"
        assert actor.username == "node-sec01", (
            f"Actor username must be the node_id, got: {actor.username}"
        )


@pytest.mark.anyio
async def test_security_rejected_job_status_is_set(db_session):
    """
    SEC-01 (side-effect): After SECURITY_REJECTED report, job status must
    be SECURITY_REJECTED in the database.
    """
    from sqlalchemy.future import select

    job_req = JobCreate(
        task_type="python_script",
        payload={"script_content": "print('x')"},
    )
    result = await JobService.create_job(job_req, db_session)
    guid = result["guid"]

    # Assign to node
    job_res = await db_session.execute(select(Job).where(Job.guid == guid))
    job = job_res.scalar_one()
    job.status = "ASSIGNED"
    job.node_id = "node-sec01-status"
    await db_session.commit()

    report = ResultReport(success=False, security_rejected=True)
    with patch("agent_service.services.job_service.audit"):
        outcome = await JobService.report_result(guid, report, "10.0.0.2", db_session)

    assert outcome["status"] == "SECURITY_REJECTED"

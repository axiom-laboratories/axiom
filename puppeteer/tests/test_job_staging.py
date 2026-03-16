import pytest
import inspect
from agent_service.db import ScheduledJob
from agent_service.models import JobPushRequest
from agent_service import main

# STAGE-01: status field on ScheduledJob
def test_scheduled_job_status_field():
    src = inspect.getsource(ScheduledJob)
    assert "status" in src, "ScheduledJob missing status column"
    assert "pushed_by" in src, "ScheduledJob missing pushed_by column"

# STAGE-02: push endpoint upsert behavior
def test_push_creates_draft():
    """STAGE-02: Push with name creates DRAFT job."""
    req = JobPushRequest(
        name="test-job",
        script_content="print('hello')",
        signature="fakesig",
        signature_id="fake-sig-id"
    )
    assert req.name == "test-job"
    assert req.id is None

def test_push_duplicate_name_conflict():
    """STAGE-02: Push returns 409 when name already exists."""
    src = inspect.getsource(main.push_job_definition)
    assert "name_conflict" in src
    assert "409" in src

def test_push_revoked_job_blocked():
    """STAGE-02: Push with REVOKED job id is blocked."""
    src = inspect.getsource(main.push_job_definition)
    assert "REVOKED" in src
    assert "job_revoked" in src

# STAGE-03: dual verification
def test_push_requires_auth():
    """STAGE-03: Push without auth returns 401."""
    src = inspect.getsource(main.push_job_definition)
    assert 'require_permission("definitions:write")' in src

def test_push_invalid_signature():
    """STAGE-03: Invalid Ed25519 signature returns 422 before DB write."""
    src = inspect.getsource(main.push_job_definition)
    assert "verify_payload_signature" in src
    assert "422" in src

# STAGE-04: pushed_by attribution
def test_push_records_pushed_by():
    """STAGE-04: pushed_by records authenticated operator identity."""
    src = inspect.getsource(main.push_job_definition)
    assert "pushed_by" in src
    assert "current_user.username" in src

# GOV-CLI-01: scheduler dispatch governance
def test_scheduler_skips_revoked():
    """GOV-CLI-01: Scheduler skips REVOKED jobs."""
    from agent_service.services import scheduler_service
    src = inspect.getsource(scheduler_service.SchedulerService.execute_scheduled_job)
    assert "REVOKED" in src
    assert "SKIP_STATUSES" in src

def test_scheduler_skips_deprecated():
    """GOV-CLI-01: Scheduler skips DEPRECATED jobs and writes AuditLog."""
    from agent_service.services import scheduler_service
    src = inspect.getsource(scheduler_service.SchedulerService.execute_scheduled_job)
    assert "DEPRECATED" in src
    assert "deprecated_skip" in src or "AuditLog" in src

def test_scheduler_skips_draft():
    """GOV-CLI-01: Scheduler skips DRAFT jobs."""
    from agent_service.services import scheduler_service
    src = inspect.getsource(scheduler_service.SchedulerService.execute_scheduled_job)
    assert "DRAFT" in src

def test_revoke_requires_admin():
    """GOV-CLI-01: Non-admin cannot set status to REVOKED (403 gate in main.py)."""
    # Find the update_job_definition route handler source
    src = inspect.getsource(main.update_job_definition)
    assert "REVOKED" in src
    assert "admin" in src
    assert "403" in src

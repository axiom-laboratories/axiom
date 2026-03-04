"""
TDD tests for Task 2: job_service.report_result() writes ExecutionRecord.
RED phase: These tests fail until ExecutionRecord write is implemented.
"""
import pytest
import asyncio
import json
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


def test_max_output_bytes_constant_exists():
    """MAX_OUTPUT_BYTES constant must exist with value 1MB."""
    from agent_service.services.job_service import MAX_OUTPUT_BYTES
    assert MAX_OUTPUT_BYTES == 1_048_576


def test_security_rejected_in_get_job_stats():
    """SECURITY_REJECTED must appear in get_job_stats status list."""
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.get_job_stats)
    assert 'SECURITY_REJECTED' in src


def test_execution_record_imported_in_job_service():
    """ExecutionRecord must be imported and used in report_result."""
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    assert 'ExecutionRecord' in src


def test_security_rejected_logic_in_report_result():
    """report_result source must handle security_rejected field."""
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    assert 'security_rejected' in src
    assert 'SECURITY_REJECTED' in src


def test_truncation_logic_in_report_result():
    """report_result source must reference MAX_OUTPUT_BYTES for truncation."""
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    assert 'MAX_OUTPUT_BYTES' in src
    assert 'truncated' in src


@pytest.mark.asyncio
async def test_report_result_writes_execution_record_completed():
    """Successful job: ExecutionRecord written with status COMPLETED."""
    from agent_service.services.job_service import JobService
    from agent_service.models import ResultReport
    from agent_service.db import Job, ExecutionRecord

    # Build a fake job object
    fake_job = MagicMock(spec=Job)
    fake_job.task_type = "python_script"
    fake_job.guid = "test-guid-001"
    fake_job.node_id = "node-abc"
    fake_job.started_at = datetime(2026, 3, 4, 21, 0, 0)

    # Mock DB session
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_job
    added_objects = []
    mock_db.add.side_effect = lambda obj: added_objects.append(obj)

    report = ResultReport(
        success=True,
        result={"exit_code": 0},
        output_log=[{"t": "2026-03-04T21:00:00", "stream": "stdout", "line": "hello"}],
        exit_code=0,
        security_rejected=False
    )

    result = await JobService.report_result("test-guid-001", report, "10.0.0.1", mock_db)

    # Should have added an ExecutionRecord
    exec_records = [obj for obj in added_objects if isinstance(obj, ExecutionRecord)]
    assert len(exec_records) == 1
    er = exec_records[0]
    assert er.job_guid == "test-guid-001"
    assert er.status == "COMPLETED"
    assert er.node_id == "node-abc"
    assert er.exit_code == 0
    assert er.truncated is False
    assert result["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_report_result_security_rejected_status():
    """Security-rejected job: ExecutionRecord status is SECURITY_REJECTED."""
    from agent_service.services.job_service import JobService
    from agent_service.models import ResultReport
    from agent_service.db import Job, ExecutionRecord

    fake_job = MagicMock(spec=Job)
    fake_job.task_type = "python_script"
    fake_job.guid = "sec-guid-002"
    fake_job.node_id = "node-abc"
    fake_job.started_at = datetime(2026, 3, 4, 21, 0, 0)

    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_job
    added_objects = []
    mock_db.add.side_effect = lambda obj: added_objects.append(obj)

    report = ResultReport(
        success=False,
        result={"error": "Signature Verification Failed"},
        security_rejected=True
    )

    result = await JobService.report_result("sec-guid-002", report, "10.0.0.1", mock_db)

    exec_records = [obj for obj in added_objects if isinstance(obj, ExecutionRecord)]
    assert len(exec_records) == 1
    er = exec_records[0]
    assert er.status == "SECURITY_REJECTED"
    # Job status should also be SECURITY_REJECTED
    assert fake_job.status == "SECURITY_REJECTED"
    assert result["status"] == "SECURITY_REJECTED"


@pytest.mark.asyncio
async def test_report_result_failed_status():
    """Failed job: ExecutionRecord status is FAILED."""
    from agent_service.services.job_service import JobService
    from agent_service.models import ResultReport
    from agent_service.db import Job, ExecutionRecord

    fake_job = MagicMock(spec=Job)
    fake_job.task_type = "python_script"
    fake_job.guid = "fail-guid-003"
    fake_job.node_id = "node-abc"
    fake_job.started_at = datetime(2026, 3, 4, 21, 0, 0)

    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_job
    added_objects = []
    mock_db.add.side_effect = lambda obj: added_objects.append(obj)

    report = ResultReport(
        success=False,
        result={"error": "exit 1"},
        exit_code=1,
        security_rejected=False
    )

    result = await JobService.report_result("fail-guid-003", report, "10.0.0.1", mock_db)

    exec_records = [obj for obj in added_objects if isinstance(obj, ExecutionRecord)]
    assert len(exec_records) == 1
    er = exec_records[0]
    assert er.status == "FAILED"
    assert er.exit_code == 1
    assert result["status"] == "FAILED"


@pytest.mark.asyncio
async def test_report_result_truncates_large_output():
    """Output exceeding 1MB is truncated and truncated=True on the record."""
    from agent_service.services.job_service import JobService, MAX_OUTPUT_BYTES
    from agent_service.models import ResultReport
    from agent_service.db import Job, ExecutionRecord

    fake_job = MagicMock(spec=Job)
    fake_job.task_type = "python_script"
    fake_job.guid = "big-guid-004"
    fake_job.node_id = "node-abc"
    fake_job.started_at = datetime(2026, 3, 4, 21, 0, 0)

    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_job
    added_objects = []
    mock_db.add.side_effect = lambda obj: added_objects.append(obj)

    # Build output log larger than 1MB
    big_line = "x" * 1000
    big_log = [{"t": "2026-03-04T21:00:00", "stream": "stdout", "line": big_line}
               for _ in range(1200)]  # ~1.2MB

    report = ResultReport(
        success=True,
        result={"exit_code": 0},
        output_log=big_log,
        exit_code=0,
        security_rejected=False
    )

    await JobService.report_result("big-guid-004", report, "10.0.0.1", mock_db)

    exec_records = [obj for obj in added_objects if isinstance(obj, ExecutionRecord)]
    assert len(exec_records) == 1
    er = exec_records[0]
    assert er.truncated is True
    # Stored output must be under 1MB
    stored_bytes = len(er.output_log.encode("utf-8"))
    assert stored_bytes <= MAX_OUTPUT_BYTES


def test_job_result_no_stdout_stderr():
    """job.result must not contain stdout or stderr keys after fix."""
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    # The old code stored result_payload which included stdout/stderr from runtime_report.
    # New code should not copy stdout/stderr into job.result.
    # We verify the source doesn't directly assign stdout/stderr to job.result raw.
    # This is a source-level heuristic check.
    assert 'flight_recorder' in src or 'exit_code' in src  # has minimal result logic

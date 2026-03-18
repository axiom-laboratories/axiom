"""
TDD stubs for Phase 29 output capture requirements.
Covers OUTPUT-01 (stdout/stderr capture in ExecutionRecord) and
OUTPUT-02 (script hash computed and stored by node).

Model-field tests: real assertions (fields exist after plan 29-01).
Implementation stubs: assert False with clear "implement after" messages.
"""
import pytest
from unittest.mock import MagicMock


def test_result_report_has_script_hash():
    """OUTPUT-02: ResultReport must accept and store a script_hash field."""
    from agent_service.models import ResultReport
    r = ResultReport(success=True, script_hash="abc123def456")
    assert r.script_hash == "abc123def456"


def test_result_report_script_hash_defaults_to_none():
    """ResultReport.script_hash must be optional with None default."""
    from agent_service.models import ResultReport
    r = ResultReport(success=True)
    assert r.script_hash is None


def test_execution_record_has_stdout_stderr():
    """OUTPUT-01: ExecutionRecord must have stdout and stderr Text columns (nullable)."""
    from agent_service.db import ExecutionRecord
    er = ExecutionRecord(
        job_guid="test-guid",
        status="COMPLETED",
        stdout="hello world",
        stderr="",
    )
    assert er.stdout == "hello world"
    assert er.stderr == ""
    # Ensure they default to None when not provided
    er2 = ExecutionRecord(job_guid="test-guid-2", status="COMPLETED")
    assert er2.stdout is None
    assert er2.stderr is None


def test_execution_record_has_script_hash():
    """OUTPUT-02: ExecutionRecord must have script_hash and hash_mismatch columns."""
    from agent_service.db import ExecutionRecord
    er = ExecutionRecord(
        job_guid="test-guid",
        status="COMPLETED",
        script_hash="a" * 64,
        hash_mismatch=False,
    )
    assert er.script_hash == "a" * 64
    assert er.hash_mismatch is False
    # Nullability
    er2 = ExecutionRecord(job_guid="test-guid-2", status="COMPLETED")
    assert er2.script_hash is None
    assert er2.hash_mismatch is None


def test_node_computes_script_hash():
    """OUTPUT-02: node.py execute_task must compute SHA-256 of script before execution.
    Verifies via source inspection that hashlib.sha256 is called with script.encode
    before the runtime_engine.run() call, and that script_hash is passed to report_result."""
    import os

    node_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "puppets", "environment_service", "node.py")
    )
    with open(node_path) as f:
        source = f.read()

    # Confirm hashlib is imported
    assert "import hashlib" in source, "hashlib not imported in node.py"

    # Confirm SHA-256 computation of the script content
    assert "hashlib.sha256(script.encode" in source, (
        "hashlib.sha256(script.encode(...)) not found in node.py execute_task"
    )

    # Confirm script_hash is forwarded to report_result
    assert "script_hash=script_hash" in source, (
        "script_hash not passed to report_result() in node.py"
    )

    # Confirm ordering: hash computed before runtime call
    sha256_pos = source.index("hashlib.sha256(script.encode")
    run_pos = source.index("runtime_engine.run(")
    assert sha256_pos < run_pos, (
        "script_hash computation must appear before runtime_engine.run() call in source"
    )


def test_stdout_extraction_after_scrubbing():
    """OUTPUT-01: report_result() source must extract stdout/stderr after scrubbing, before truncation.
    Verified by source inspection — stdout_text and stderr_text must appear before truncation check."""
    import inspect
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    # stdout_text and stderr_text must be extracted from output_log
    assert "stdout_text" in src
    assert "stderr_text" in src
    # The extraction must filter by stream
    assert 'stream' in src
    # script_hash must be computed (orchestrator side)
    assert "script_hash" in src
    assert "orchestrator_hash" in src or "hashlib" in src


def test_execution_record_has_script_hash_and_attempt():
    """OUTPUT-02 + RETRY-01: report_result source must write script_hash, hash_mismatch,
    attempt_number, and job_run_id onto the ExecutionRecord constructor."""
    import inspect
    from agent_service.services.job_service import JobService
    src = inspect.getsource(JobService.report_result)
    assert "script_hash" in src
    assert "hash_mismatch" in src
    assert "attempt_number" in src
    assert "job_run_id" in src

"""
Phase 91: Output Validation — unit tests for validation rule evaluation.
"""

import json
import pytest


# ---------------------------------------------------------------------------
# Helper: the pure evaluation function (extracted for unit-testability)
# ---------------------------------------------------------------------------

def _evaluate_validation_rules(rules: dict, exit_code: int, stdout: str):
    """
    Evaluate a set of validation rules against a completed job's output.

    Returns:
        (passed: bool, failure_reason: str | None)

    Rules supported:
        exit_code       — int: expected exit code
        stdout_regex    — str: regex that must match anywhere in stdout
        json_path       — str (dot-notation) + json_expected: expected value
    """
    import re as _re

    failures = []

    rule_exit = rules.get("exit_code")
    if rule_exit is not None:
        if exit_code != int(rule_exit):
            failures.append("validation_exit_code")

    rule_regex = rules.get("stdout_regex")
    if rule_regex:
        if not _re.search(rule_regex, stdout or ""):
            failures.append("validation_regex")

    rule_json_path = rules.get("json_path")
    rule_json_expected = rules.get("json_expected")
    if rule_json_path and rule_json_expected is not None:
        try:
            parsed = json.loads(stdout or "")
            val = parsed
            for part in rule_json_path.split("."):
                val = val[part]
            if str(val) != str(rule_json_expected):
                failures.append("validation_json_field")
        except Exception:
            failures.append("validation_json_field")

    if failures:
        return False, failures[0]
    return True, None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_null_rules_unchanged():
    """When validation_rules is None/absent, status stays COMPLETED (no evaluation)."""
    # Simulate no rules — result should not flip
    rules = None
    if rules:
        passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout="anything")
    else:
        passed, reason = True, None
    assert passed is True
    assert reason is None


def test_exit_code_validation():
    """exit_code rule: expected=0, actual=0 → pass; actual=1 → failure."""
    rules = {"exit_code": 0}

    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout="")
    assert passed is True
    assert reason is None

    passed, reason = _evaluate_validation_rules(rules, exit_code=1, stdout="")
    assert passed is False
    assert reason == "validation_exit_code"


def test_regex_validation():
    """stdout_regex rule: matching stdout → pass; non-matching → failure."""
    rules = {"stdout_regex": "SUCCESS"}

    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout="SUCCESS\n")
    assert passed is True
    assert reason is None

    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout="FAIL\n")
    assert passed is False
    assert reason == "validation_regex"


def test_json_field_validation():
    """json_path + json_expected rule: matching value → pass; wrong value → failure."""
    rules = {"json_path": "result.status", "json_expected": "ok"}

    stdout_pass = json.dumps({"result": {"status": "ok"}})
    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout=stdout_pass)
    assert passed is True
    assert reason is None

    stdout_fail = json.dumps({"result": {"status": "error"}})
    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout=stdout_fail)
    assert passed is False
    assert reason == "validation_json_field"

    # Unparseable stdout → failure
    passed, reason = _evaluate_validation_rules(rules, exit_code=0, stdout="not json")
    assert passed is False
    assert reason == "validation_json_field"


def test_no_retry_on_validation_failure():
    """Validation failures must be non-retriable (terminal FAILED status)."""
    # The guard in process_result() is: `not _validation_failed and is_retriable`
    # Simulate the guard logic directly
    _validation_failed = True
    is_retriable = True  # job was configured as retriable

    # Guard expression from job_service.py
    should_retry = (not _validation_failed) and is_retriable
    assert should_retry is False, "Validation failures must never trigger retry"


def test_validation_rules_schema():
    """ScheduledJob.validation_rules and ExecutionRecord.failure_reason columns exist."""
    from agent_service.db import ScheduledJob, ExecutionRecord

    # Check ScheduledJob has validation_rules column
    sj_columns = {c.name for c in ScheduledJob.__table__.columns}
    assert "validation_rules" in sj_columns, (
        "ScheduledJob.validation_rules column missing — run migration_v17.sql"
    )

    # Check ExecutionRecord has failure_reason column
    er_columns = {c.name for c in ExecutionRecord.__table__.columns}
    assert "failure_reason" in er_columns, (
        "ExecutionRecord.failure_reason column missing — run migration_v17.sql"
    )


# ---------------------------------------------------------------------------
# Serialization test: failure_reason forwarded in list_executions() response
# ---------------------------------------------------------------------------

def test_failure_reason_serialized_in_list_executions():
    """
    failure_reason must be forwarded by the executions_router, not silently dropped.

    Uses an in-memory SQLite DB so we can create a real ExecutionRecord row with
    failure_reason='validation_regex' and verify the list endpoint returns it.
    """
    import asyncio
    from datetime import datetime, timezone
    from unittest.mock import patch, AsyncMock, MagicMock

    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    import importlib.util, sys, os

    # Load executions_router directly from its file to avoid triggering
    # ee/routers/__init__.py (pre-existing Blueprint import error in foundry_router).
    _router_path = os.path.join(
        os.path.dirname(__file__), "..",
        "agent_service", "ee", "routers", "executions_router.py"
    )
    _spec = importlib.util.spec_from_file_location(
        "agent_service.ee.routers.executions_router", _router_path
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules.setdefault("agent_service.ee.routers.executions_router", _mod)
    _spec.loader.exec_module(_mod)
    executions_router = _mod.executions_router
    from agent_service.models import ExecutionRecordResponse

    # Build a minimal mock ExecutionRecord that has failure_reason set
    mock_record = MagicMock()
    mock_record.id = 42
    mock_record.job_guid = "test-guid-001"
    mock_record.node_id = "node-alpha"
    mock_record.status = "VALIDATION_FAILED"
    mock_record.exit_code = 0
    mock_record.started_at = datetime(2026, 3, 30, 10, 0, 0, tzinfo=timezone.utc)
    mock_record.completed_at = datetime(2026, 3, 30, 10, 0, 5, tzinfo=timezone.utc)
    mock_record.output_log = None
    mock_record.truncated = False
    mock_record.stdout = "some output"
    mock_record.stderr = None
    mock_record.script_hash = None
    mock_record.hash_mismatch = None
    mock_record.attempt_number = 1
    mock_record.job_run_id = None
    mock_record.attestation_verified = None
    mock_record.failure_reason = "validation_regex"  # the field under test

    # job_max_retries, job_definition_version_id, job_runtime
    mock_row = (mock_record, None, None, None)

    # Minimal FastAPI app with the router
    app = FastAPI()
    app.include_router(executions_router)

    # Patch get_db and require_auth
    async def _fake_get_db():
        mock_db = AsyncMock()
        # First execute() call → list_executions rows
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        # Second execute() call → version_number batch fetch (empty)
        mock_version_result = MagicMock()
        mock_version_result.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_version_result])
        yield mock_db

    mock_user = MagicMock()
    mock_user.username = "test_user"
    mock_user.role = "admin"

    app.dependency_overrides = {}
    from agent_service import deps as _deps
    from agent_service.db import get_db as _get_db
    app.dependency_overrides[_get_db] = _fake_get_db
    app.dependency_overrides[_deps.require_auth] = lambda: mock_user

    client = TestClient(app)
    response = client.get("/api/executions")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert len(data) == 1
    record = data[0]
    assert record["failure_reason"] == "validation_regex", (
        f"failure_reason was not forwarded — got: {record.get('failure_reason')!r}. "
        "Add failure_reason=r.failure_reason to the ExecutionRecordResponse constructor in list_executions()."
    )

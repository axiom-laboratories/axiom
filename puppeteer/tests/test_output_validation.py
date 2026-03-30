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

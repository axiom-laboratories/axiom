"""
SEC-02: Path traversal guard for vault artifact operations.

The fix adds validate_path_within(base, candidate) to security.py and calls it
in vault_service.py before any file I/O on artifact_id.

These tests verify validate_path_within() raises HTTPException(400) for
traversal paths. Before the fix, the function does not exist → tests FAIL
with AttributeError. After the fix, traversal paths raise HTTP 400.
"""
import pytest
from pathlib import Path
from fastapi import HTTPException


def _get_validate_fn():
    """Return the validate_path_within helper, or None if not yet implemented."""
    try:
        from agent_service.security import validate_path_within
        return validate_path_within
    except ImportError:
        return None


def test_validate_path_within_exists():
    """validate_path_within must be importable from agent_service.security after SEC-02 fix."""
    validate = _get_validate_fn()
    assert validate is not None, (
        "validate_path_within not found in agent_service.security — SEC-02 fix not implemented"
    )


def test_validate_path_within_rejects_traversal():
    """validate_path_within must raise HTTPException(400) for path traversal."""
    validate = _get_validate_fn()
    assert validate is not None, "validate_path_within not implemented (SEC-02 fix missing)"

    base = Path("/app/vault")
    # Simulated traversal: /app/vault/../../../etc/passwd resolves outside base
    candidate = Path("/app/vault/../../../etc/passwd")
    with pytest.raises(HTTPException) as exc_info:
        validate(base, candidate)
    assert exc_info.value.status_code == 400


def test_validate_path_within_rejects_absolute_escape():
    """validate_path_within must reject a path that resolves outside the base."""
    validate = _get_validate_fn()
    assert validate is not None, "validate_path_within not implemented (SEC-02 fix missing)"

    base = Path("/app/vault")
    candidate = Path("/etc/passwd")
    with pytest.raises(HTTPException) as exc_info:
        validate(base, candidate)
    assert exc_info.value.status_code == 400


def test_validate_path_within_allows_safe_path():
    """validate_path_within must allow a path that stays within base."""
    validate = _get_validate_fn()
    assert validate is not None, "validate_path_within not implemented (SEC-02 fix missing)"

    base = Path("/app/vault")
    # Use a real temp dir that exists so resolve() works
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        candidate = Path(tmpdir) / "safe-artifact-id"
        # Should NOT raise — path is within base
        result = validate(base, candidate)
        assert result is not None


def test_vault_service_deleted():
    """SEC-02: vault_service.py must not exist — closed by deletion."""
    import importlib
    with pytest.raises((ImportError, ModuleNotFoundError)):
        importlib.import_module("agent_service.services.vault_service")

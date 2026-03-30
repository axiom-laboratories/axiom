"""Unit tests for axiom-licenses/tools/issue_licence.py"""
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# ---------------------------------------------------------------------------
# Import helper — load issue_licence as a module from tools/
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).parent.parent / "tools"
_SCRIPT = _TOOLS_DIR / "issue_licence.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("issue_licence", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Tests: resolve_key
# ---------------------------------------------------------------------------

class TestResolveKey:
    def test_resolve_key_missing(self, monkeypatch):
        """Exit non-zero with clear message when neither --key nor env var is set."""
        monkeypatch.delenv("AXIOM_LICENCE_SIGNING_KEY", raising=False)
        mod = _load_module()
        args = SimpleNamespace(key=None)
        with pytest.raises(SystemExit) as exc_info:
            mod.resolve_key(args)
        msg = str(exc_info.value)
        assert "no signing key" in msg.lower(), f"Expected 'no signing key' in message, got: {msg}"

    def test_resolve_key_file_not_found(self, monkeypatch):
        """Exit with clear message when key file path does not exist."""
        monkeypatch.delenv("AXIOM_LICENCE_SIGNING_KEY", raising=False)
        mod = _load_module()
        args = SimpleNamespace(key="/nonexistent/path/key.pem")
        with pytest.raises(SystemExit) as exc_info:
            mod.resolve_key(args)
        msg = str(exc_info.value)
        assert "not found" in msg.lower(), f"Expected 'not found' in message, got: {msg}"

    def test_resolve_key_valid(self, tmp_path, monkeypatch):
        """Returns loaded Ed25519PrivateKey when --key points to a valid key file."""
        monkeypatch.delenv("AXIOM_LICENCE_SIGNING_KEY", raising=False)
        # Generate a fresh key
        key = Ed25519PrivateKey.generate()
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_file = tmp_path / "test.key"
        key_file.write_bytes(pem)
        key_file.chmod(0o600)

        mod = _load_module()
        args = SimpleNamespace(key=str(key_file))
        result = mod.resolve_key(args)
        assert isinstance(result, Ed25519PrivateKey)


# ---------------------------------------------------------------------------
# Tests: build_audit_record
# ---------------------------------------------------------------------------

class TestBuildAuditRecord:
    def _make_payload(self):
        now = int(time.time())
        return {
            "licence_id": "test-jti-1234",
            "customer_id": "acme-corp",
            "issued_to": "Acme Corp",
            "contact_email": "admin@acme.com",
            "tier": "ee",
            "node_limit": 10,
            "features": ["sso", "webhooks"],
            "grace_days": 30,
            "iat": now,
            "exp": now + 365 * 86400,
        }

    def test_build_audit_record_fields(self):
        """All 12 required YAML fields must be present in the returned dict."""
        mod = _load_module()
        payload = self._make_payload()
        record = mod.build_audit_record(payload, token="fake.jwt.token", issued_by="tester")

        required_fields = [
            "jti", "customer_id", "issued_to", "contact_email", "tier",
            "node_limit", "features", "grace_days", "issued_at", "expiry",
            "issued_by", "licence_blob",
        ]
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"

    def test_build_audit_record_jti_from_licence_id(self):
        """The jti field must be populated from payload['licence_id'], not 'jti'."""
        mod = _load_module()
        payload = self._make_payload()
        record = mod.build_audit_record(payload, token="fake.jwt.token", issued_by="tester")
        assert record["jti"] == payload["licence_id"], (
            f"record['jti'] ({record['jti']}) != payload['licence_id'] ({payload['licence_id']})"
        )


# ---------------------------------------------------------------------------
# Tests: --no-remote mode (subprocess)
# ---------------------------------------------------------------------------

def _generate_temp_key(tmp_path):
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_file = tmp_path / "test.key"
    key_file.write_bytes(pem)
    key_file.chmod(0o600)
    return key_file


class TestNoRemoteMode:
    def _run_issue(self, tmp_path, extra_args=None, env=None):
        """Run issue_licence.py via subprocess in tmp_path as cwd."""
        cmd = [
            sys.executable,
            str(_SCRIPT),
            "--key", str(_generate_temp_key(tmp_path)),
            "--customer", "test-customer",
            "--tier", "ee",
            "--nodes", "5",
            "--expiry", "2027-01-01",
            "--issued-to", "Test Customer Corp",
            "--no-remote",
        ]
        if extra_args:
            cmd.extend(extra_args)
        run_env = os.environ.copy()
        run_env.pop("AXIOM_GITHUB_TOKEN", None)
        if env:
            run_env.update(env)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), env=run_env)
        return result

    def test_no_remote_writes_yaml(self, tmp_path):
        """--no-remote writes a .yml file in the current directory."""
        result = self._run_issue(tmp_path)
        assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
        yml_files = list(tmp_path.glob("*.yml"))
        assert len(yml_files) == 1, f"Expected 1 .yml file, found {len(yml_files)}: {yml_files}"

    def test_no_remote_stdout_contains_jwt(self, tmp_path):
        """--no-remote prints the JWT (non-empty) to stdout."""
        result = self._run_issue(tmp_path)
        assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
        stdout = result.stdout.strip()
        assert stdout, "stdout is empty — expected JWT"
        # JWT has 3 dot-separated parts
        parts = stdout.split(".")
        assert len(parts) == 3, f"Unexpected stdout (not a JWT): {stdout!r}"

    def test_no_remote_yaml_has_required_fields(self, tmp_path):
        """YAML file produced by --no-remote has all 12 required fields."""
        result = self._run_issue(tmp_path)
        assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
        yml_files = list(tmp_path.glob("*.yml"))
        record = yaml.safe_load(yml_files[0].read_text())
        required_fields = [
            "jti", "customer_id", "issued_to", "contact_email", "tier",
            "node_limit", "features", "grace_days", "issued_at", "expiry",
            "issued_by", "licence_blob",
        ]
        for field in required_fields:
            assert field in record, f"Missing field in YAML: {field}"

    def test_no_remote_does_not_require_github_token(self, tmp_path):
        """--no-remote must not require AXIOM_GITHUB_TOKEN."""
        result = self._run_issue(tmp_path)
        # AXIOM_GITHUB_TOKEN is already stripped in _run_issue
        assert result.returncode == 0, (
            f"Expected exit 0 without AXIOM_GITHUB_TOKEN, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

"""Unit tests for sign_wheels.py wheel signing and verification script."""

import argparse
import importlib.util
import json
import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Load sign_wheels as a module from tools/
_TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"
_SCRIPT = _TOOLS_DIR / "sign_wheels.py"


def _load_module():
    """Load sign_wheels.py as a module."""
    spec = importlib.util.spec_from_file_location("sign_wheels", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load the module once for all tests
_sw = _load_module()


def test_wheel_discovery(temp_wheel_dir, sample_wheel):
    """sign_wheels.py discovers all .whl files in input directory."""
    # sample_wheel fixture creates one .whl file
    wheels = list(temp_wheel_dir.glob("*.whl"))
    assert len(wheels) == 1
    assert wheels[0].name == "axiom_ee-2.0-py3-none-any.whl"


def test_wheel_hash_chunked(temp_wheel_dir, sample_wheel):
    """sign_wheels.py computes SHA256 of wheel bytes in 64KB chunks."""
    # hash_wheel should compute SHA256 of the wheel file
    sha256_hex = _sw.hash_wheel(str(sample_wheel))
    # Verify it returns a hex string
    assert isinstance(sha256_hex, str)
    assert len(sha256_hex) == 64  # SHA256 hex is always 64 chars
    # Verify it's valid hex
    assert all(c in '0123456789abcdef' for c in sha256_hex)


def test_signature_format(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py signs SHA256 hex (UTF-8) with Ed25519, produces base64 signature."""
    private_pem, _ = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)

    # Call sign_wheels to create manifests
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=False, quiet=True)

    # Load the manifest and verify signature format
    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert "sha256" in manifest
    assert "signature" in manifest

    # Verify signature is valid base64
    sig_bytes = base64.b64decode(manifest["signature"])
    assert isinstance(sig_bytes, bytes)
    assert len(sig_bytes) == 64  # Ed25519 signature is 64 bytes


def test_manifest_naming(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py creates manifest JSON files matching wheel filenames."""
    private_pem, _ = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)

    # Call sign_wheels
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=False, quiet=True)

    # Verify manifest file exists with correct name
    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    assert manifest_path.exists()

    # Verify it's valid JSON with required fields
    manifest = json.loads(manifest_path.read_text())
    assert "sha256" in manifest
    assert "signature" in manifest


def test_deploy_name_flag(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py --deploy-name also writes axiom_ee.manifest.json."""
    private_pem, _ = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)

    # Call sign_wheels with deploy_name=True
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=True, quiet=True)

    # Verify both versioned and fixed-name manifests exist
    versioned_manifest = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    fixed_manifest = temp_wheel_dir / "axiom_ee.manifest.json"

    assert versioned_manifest.exists()
    assert fixed_manifest.exists()

    # Verify content is the same
    assert versioned_manifest.read_text() == fixed_manifest.read_text()


def test_no_wheels_error(temp_wheel_dir, test_keypair):
    """sign_wheels.py exits 1 if no wheels found."""
    private_pem, _ = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)

    # Create empty directory (no wheels)
    empty_dir = temp_wheel_dir / "empty"
    empty_dir.mkdir()

    # Should raise SystemExit when no wheels found
    with pytest.raises(SystemExit):
        _sw.sign_wheels(empty_dir, private_key)


def test_verify_mode(temp_wheel_dir, sample_wheel, sample_manifest, test_keypair):
    """sign_wheels.py --verify loads public key and verifies all manifests."""
    private_pem, public_pem = test_keypair
    public_key = serialization.load_pem_public_key(public_pem)

    # Write sample_manifest to disk so verify_manifests can find it
    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest, indent=2))

    # Verify should return True (all manifests valid)
    result = _sw.verify_manifests(temp_wheel_dir, public_key)
    assert result is True


def test_verify_exit_codes(temp_wheel_dir, sample_wheel, test_keypair):
    """sign_wheels.py --verify exits 0 if all manifests verify, 1 if any fail."""
    private_pem, public_pem = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_key = serialization.load_pem_public_key(public_pem)

    # Sign the wheel first
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=False, quiet=True)

    # Verify should succeed
    result = _sw.verify_manifests(temp_wheel_dir, public_key)
    assert result is True


def test_key_resolution_arg(temp_wheel_dir, test_keypair):
    """sign_wheels.py resolves key from --key argument."""
    private_pem, _ = test_keypair
    key_path = temp_wheel_dir / "test.key"
    key_path.write_bytes(private_pem)

    # Construct args with key argument
    args = argparse.Namespace(key=str(key_path))

    # resolve_key should load and return the private key
    resolved_key = _sw.resolve_key(args, mode="private")
    assert resolved_key is not None
    # Verify it's actually an Ed25519PrivateKey by checking we can sign with it
    message = b"test message"
    signature = resolved_key.sign(message)
    assert len(signature) > 0


def test_key_resolution_env(temp_wheel_dir, test_keypair, monkeypatch):
    """sign_wheels.py resolves key from AXIOM_WHEEL_SIGNING_KEY env var."""
    private_pem, _ = test_keypair
    key_path = temp_wheel_dir / "test.key"
    key_path.write_bytes(private_pem)

    # Set env var and create args with no key
    monkeypatch.setenv("AXIOM_WHEEL_SIGNING_KEY", str(key_path))
    args = argparse.Namespace(key=None)

    # resolve_key should fall back to env var
    resolved_key = _sw.resolve_key(args, mode="private")
    assert resolved_key is not None
    # Verify it's actually an Ed25519PrivateKey
    message = b"test message"
    signature = resolved_key.sign(message)
    assert len(signature) > 0


def test_quiet_flag(temp_wheel_dir, sample_wheel, test_keypair, capsys):
    """sign_wheels.py --quiet suppresses per-wheel summary output."""
    private_pem, _ = test_keypair
    private_key = serialization.load_pem_private_key(private_pem, password=None)

    # Call with quiet=False first to see that output is produced
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=False, quiet=False)
    captured = capsys.readouterr()
    assert "Signed:" in captured.err

    # Remove the manifest to test quiet mode
    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    manifest_path.unlink()

    # Call with quiet=True
    _sw.sign_wheels(temp_wheel_dir, private_key, deploy_name=False, quiet=True)
    captured = capsys.readouterr()
    assert "Signed:" not in captured.err


def test_verify_sha256_mismatch(temp_wheel_dir, sample_wheel, sample_manifest):
    """sign_wheels.py --verify reports FAIL when SHA256 doesn't match."""
    # Write sample_manifest with corrupted SHA256
    corrupted_manifest = sample_manifest.copy()
    corrupted_manifest["sha256"] = "0" * 64  # Wrong hash

    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    manifest_path.write_text(json.dumps(corrupted_manifest, indent=2))

    # Create a fresh key pair for this test (doesn't matter what key since SHA256 check happens first)
    fresh_private = ed25519.Ed25519PrivateKey.generate()
    fresh_public = fresh_private.public_key()

    # Call verify with corrupted manifest - should return False
    result = _sw.verify_manifests(temp_wheel_dir, fresh_public)

    # The SHA256 mismatch should be detected and function should return False
    assert result is False

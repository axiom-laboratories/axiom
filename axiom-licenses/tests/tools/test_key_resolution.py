"""Unit tests for key resolution pattern in wheel signing tools."""

import argparse
import pytest
import os
import sys
from pathlib import Path

# Add tools directory to path so we can import sign_wheels
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

from sign_wheels import resolve_key


def test_key_resolution_from_arg(temp_wheel_dir, test_keypair):
    """Key resolution follows issue_licence.py pattern: --key arg takes priority."""
    private_pem, _ = test_keypair

    # Write private key to temp file
    key_path = temp_wheel_dir / "test_key.pem"
    key_path.write_bytes(private_pem)

    # Create args with key argument
    args = argparse.Namespace(key=str(key_path))

    # Resolve the key
    result = resolve_key(args, mode="private")

    # Verify returned object is a key (has .sign method for private key)
    assert hasattr(result, 'sign'), "Private key should have .sign method"
    assert result is not None


def test_key_resolution_from_env(temp_wheel_dir, test_keypair, monkeypatch):
    """Key resolution falls back to AXIOM_WHEEL_SIGNING_KEY env var if no --key."""
    private_pem, _ = test_keypair

    # Write private key to temp file
    key_path = temp_wheel_dir / "test_key.pem"
    key_path.write_bytes(private_pem)

    # Set env var
    monkeypatch.setenv("AXIOM_WHEEL_SIGNING_KEY", str(key_path))

    # Create args with key=None (no --key argument)
    args = argparse.Namespace(key=None)

    # Resolve the key
    result = resolve_key(args, mode="private")

    # Verify returned object is a key
    assert result is not None
    assert hasattr(result, 'sign'), "Private key should have .sign method"


def test_key_resolution_missing(monkeypatch):
    """Key resolution exits with clear error if neither --key nor env var provided."""
    # Ensure env var is not set
    monkeypatch.delenv("AXIOM_WHEEL_SIGNING_KEY", raising=False)

    # Create args with no key
    args = argparse.Namespace(key=None)

    # Should exit with SystemExit
    with pytest.raises(SystemExit) as exc_info:
        resolve_key(args, mode="private")

    # Verify error message mentions key
    assert "no signing key" in str(exc_info.value).lower()


def test_key_file_not_found():
    """Key resolution exits with clear error if key file doesn't exist."""
    # Create args with nonexistent path
    args = argparse.Namespace(key="/nonexistent/path/to/key.pem")

    # Should exit with SystemExit
    with pytest.raises(SystemExit) as exc_info:
        resolve_key(args, mode="private")

    # Verify error message mentions file not found
    assert "not found" in str(exc_info.value).lower()


def test_key_load_failure(temp_wheel_dir):
    """Key resolution exits with clear error if PEM is malformed."""
    # Write invalid PEM data to temp file
    key_path = temp_wheel_dir / "invalid_key.pem"
    key_path.write_bytes(b"not a valid PEM format\n")

    # Create args with invalid key file
    args = argparse.Namespace(key=str(key_path))

    # Should exit with SystemExit
    with pytest.raises(SystemExit) as exc_info:
        resolve_key(args, mode="private")

    # Verify error message mentions load failure
    assert "failed to load" in str(exc_info.value).lower()


def test_key_resolution_private_to_public_fallback(temp_wheel_dir, test_keypair):
    """Key resolution in public mode falls back to public key if private key fails."""
    private_pem, _ = test_keypair

    # Write private key to temp file
    key_path = temp_wheel_dir / "test_key.pem"
    key_path.write_bytes(private_pem)

    # Create args with key argument
    args = argparse.Namespace(key=str(key_path))

    # Resolve in public mode (should accept private key as fallback)
    result = resolve_key(args, mode="public")

    # Verify returned object is not None
    assert result is not None

    # In public mode with a private key file, it returns the private key as fallback
    # Private key has .sign method, which is characteristic of Ed25519PrivateKey
    assert hasattr(result, 'sign'), "Fallback key should have .sign method (indicating private key)"

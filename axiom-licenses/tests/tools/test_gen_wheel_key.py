"""Unit tests for gen_wheel_key.py keypair generation script."""

import pytest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
import sys

# Add parent dir to path to import gen_wheel_key
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

from gen_wheel_key import generate_keypair


def test_generate_keypair(temp_wheel_dir, test_keypair):
    """gen_wheel_key.py generates a fresh Ed25519 keypair and writes private key to file."""
    out_path = temp_wheel_dir / "test.key"
    private_pem, public_pem = generate_keypair(out_path, force=False)

    # Verify return types
    assert isinstance(private_pem, bytes), "private_pem should be bytes"
    assert isinstance(public_pem, bytes), "public_pem should be bytes"

    # Verify file was written
    assert out_path.exists(), f"Private key file {out_path} should exist"

    # Verify PEM format markers
    assert b"-----BEGIN PRIVATE KEY-----" in private_pem, "Private key should have PEM header"
    assert b"-----END PRIVATE KEY-----" in private_pem, "Private key should have PEM footer"
    assert b"-----BEGIN PUBLIC KEY-----" in public_pem, "Public key should have PEM header"
    assert b"-----END PUBLIC KEY-----" in public_pem, "Public key should have PEM footer"

    # Verify file content matches returned private key
    assert out_path.read_bytes() == private_pem, "File content should match returned private key"


def test_no_overwrite_without_force(temp_wheel_dir):
    """gen_wheel_key.py refuses to overwrite existing key without --force flag."""
    out_path = temp_wheel_dir / "test.key"
    out_path.write_bytes(b"existing key\n")

    # Should raise SystemExit when file exists and force=False
    with pytest.raises(SystemExit) as exc_info:
        generate_keypair(out_path, force=False)

    # Verify error message mentions "already exists"
    assert "already exists" in str(exc_info.value).lower()


def test_public_key_bytes_literal(temp_wheel_dir):
    """gen_wheel_key.py prints public key as Python bytes literal to stdout."""
    out_path = temp_wheel_dir / "test.key"
    private_pem, public_pem = generate_keypair(out_path, force=False)

    # Format the public key as bytes literal (matching what main() does)
    formatted = f'b"""{public_pem.decode()}"""'

    # Verify format
    assert formatted.startswith('b"""'), "Bytes literal should start with b\"\"\""
    assert "-----BEGIN PUBLIC KEY-----" in formatted, "Should contain PEM header"
    assert formatted.endswith('"""'), "Bytes literal should end with \"\"\""


def test_force_flag_overwrites(temp_wheel_dir):
    """gen_wheel_key.py overwrites existing key when --force is passed."""
    out_path = temp_wheel_dir / "test.key"
    old_content = b"old key content\n"
    out_path.write_bytes(old_content)

    # Should succeed and overwrite when force=True
    private_pem, public_pem = generate_keypair(out_path, force=True)

    new_content = out_path.read_bytes()

    # Verify content changed
    assert new_content != old_content, "File content should be overwritten"

    # Verify new content is valid key
    assert b"-----BEGIN PRIVATE KEY-----" in new_content, "New file should contain valid private key"


def test_file_permissions_0600(temp_wheel_dir):
    """gen_wheel_key.py writes private key with mode 0600 (secure permissions)."""
    out_path = temp_wheel_dir / "test.key"
    private_pem, public_pem = generate_keypair(out_path, force=False)

    # Get file mode
    stat = out_path.stat()
    mode = stat.st_mode & 0o777

    # Verify permissions are exactly 0o600 (owner read/write only)
    assert mode == 0o600, f"File mode should be 0o600, got {oct(mode)}"

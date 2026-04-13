"""Shared test fixtures for axiom-licenses tools tests."""

import base64
import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


@pytest.fixture
def temp_wheel_dir():
    """Temporary directory for test wheel files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_keypair():
    """Generate a fresh Ed25519 keypair for tests.

    Returns:
        tuple[bytes, bytes]: (private_pem, public_pem)
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return (private_pem, public_pem)


@pytest.fixture
def sample_wheel(temp_wheel_dir):
    """Create a minimal test wheel file (1KB dummy bytes).

    Returns:
        Path: path to the created .whl file
    """
    wheel_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.whl"
    wheel_path.write_bytes(b"dummy wheel content" * 50)  # ~950 bytes
    return wheel_path


@pytest.fixture
def sample_manifest(sample_wheel, test_keypair):
    """Create a sample manifest dict with valid Ed25519 signature.

    Args:
        sample_wheel: path to test wheel file
        test_keypair: (private_pem, public_pem) tuple

    Returns:
        dict: manifest with "sha256" and "signature" fields
    """
    private_pem, _ = test_keypair

    # Compute SHA256 of sample wheel
    sha256_hash = hashlib.sha256()
    with open(sample_wheel, 'rb') as f:
        while chunk := f.read(65536):  # 64KB chunks
            sha256_hash.update(chunk)
    sha256_hex = sha256_hash.hexdigest()

    # Sign the UTF-8 hex string with Ed25519
    private_key = serialization.load_pem_private_key(
        private_pem, password=None
    )
    message = sha256_hex.encode('utf-8')
    signature_bytes = private_key.sign(message)
    signature_b64 = base64.b64encode(signature_bytes).decode('ascii')

    return {
        "sha256": sha256_hex,
        "signature": signature_b64
    }

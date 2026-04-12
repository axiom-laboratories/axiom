"""
Test suite for EE wheel manifest verification.

Tests cover:
- Manifest file existence checks
- JSON parsing and field validation
- SHA256 hash verification against wheel content
- Ed25519 signature verification
- Integration with _install_ee_wheel() and activate_ee_live()
- Error propagation and storage in app.state
- /admin/licence endpoint error exposure
"""

import pytest
import json
import base64
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from agent_service.ee import _verify_wheel_manifest, _install_ee_wheel, activate_ee_live


@pytest.fixture
def ed25519_test_keypair():
    """Generate a fresh Ed25519 keypair for tests.

    Returns a dict with 'private_key' and 'public_key_pem' for use in testing.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return {
        'private_key': private_key,
        'public_key_pem': public_key_pem,
        'public_key': public_key,
    }


@pytest.fixture
def temp_wheel_file():
    """Create a temporary wheel file with known content for SHA256 testing."""
    with tempfile.NamedTemporaryFile(suffix='.whl', delete=False) as f:
        wheel_path = Path(f.name)
        # Write test content
        f.write(b"fake wheel content for testing")
        f.flush()

    yield wheel_path

    # Cleanup
    wheel_path.unlink(missing_ok=True)


@pytest.fixture
def manifest_path_patcher():
    """Provides a context manager to patch MANIFEST_PATH in the ee module."""
    def patcher(manifest_path):
        return patch('agent_service.ee.MANIFEST_PATH', manifest_path)
    return patcher


class TestVerifyWheelManifestMissing:
    """Test 1: Manifest file missing."""

    def test_verify_wheel_manifest_raises_on_missing_manifest(self, temp_wheel_file, manifest_path_patcher):
        """_verify_wheel_manifest raises RuntimeError when manifest file does not exist."""
        missing_manifest = Path("/nonexistent/path/axiom_ee.manifest.json")

        with manifest_path_patcher(missing_manifest):
            with pytest.raises(RuntimeError, match="Manifest not found"):
                _verify_wheel_manifest(str(temp_wheel_file))


class TestVerifyWheelManifestMalformed:
    """Test 2: Manifest JSON is malformed."""

    def test_verify_wheel_manifest_raises_on_malformed_json(self, temp_wheel_file, manifest_path_patcher):
        """_verify_wheel_manifest raises RuntimeError when manifest JSON is malformed."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            f.write("{invalid json")
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with pytest.raises(RuntimeError, match="malformed|invalid"):
                    _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)


class TestVerifyWheelManifestMissingFields:
    """Test 3: Manifest is missing required fields."""

    def test_verify_wheel_manifest_raises_on_missing_sha256_field(self, temp_wheel_file, manifest_path_patcher):
        """_verify_wheel_manifest raises RuntimeError when manifest is missing sha256 field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({"signature": "base64encodedstring"}, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with pytest.raises(RuntimeError, match="sha256|required|missing"):
                    _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)

    def test_verify_wheel_manifest_raises_on_missing_signature_field(self, temp_wheel_file, manifest_path_patcher):
        """_verify_wheel_manifest raises RuntimeError when manifest is missing signature field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({"sha256": "abcd1234"}, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with pytest.raises(RuntimeError, match="signature|required|missing"):
                    _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)


class TestVerifyWheelManifestHashMismatch:
    """Test 5: Wheel SHA256 does not match manifest."""

    def test_verify_wheel_manifest_raises_on_hash_mismatch(self, temp_wheel_file, manifest_path_patcher, ed25519_test_keypair):
        """_verify_wheel_manifest raises RuntimeError when wheel SHA256 does not match manifest sha256."""
        # Compute actual SHA256 of wheel
        actual_sha256 = hashlib.sha256(b"fake wheel content for testing").hexdigest()

        # Create manifest with different SHA256
        wrong_sha256 = hashlib.sha256(b"different content").hexdigest()
        signature_msg = wrong_sha256.encode('utf-8')
        signature_bytes = ed25519_test_keypair['private_key'].sign(signature_msg)
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({
                "sha256": wrong_sha256,
                "signature": signature_b64
            }, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with patch('agent_service.ee._manifest_pub_key', ed25519_test_keypair['public_key']):
                    with pytest.raises(RuntimeError, match="hash|mismatch|does not match"):
                        _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)


class TestVerifyWheelManifestInvalidSignature:
    """Test 7-8: Signature verification failures."""

    def test_verify_wheel_manifest_raises_on_invalid_base64_signature(self, temp_wheel_file, manifest_path_patcher, ed25519_test_keypair):
        """_verify_wheel_manifest raises RuntimeError when signature is invalid base64."""
        actual_sha256 = hashlib.sha256(b"fake wheel content for testing").hexdigest()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({
                "sha256": actual_sha256,
                "signature": "not-valid-base64!!!@#$"
            }, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with patch('agent_service.ee._manifest_pub_key', ed25519_test_keypair['public_key']):
                    with pytest.raises(RuntimeError, match="base64|invalid|decode"):
                        _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)

    def test_verify_wheel_manifest_raises_on_invalid_ed25519_signature(self, temp_wheel_file, manifest_path_patcher, ed25519_test_keypair):
        """_verify_wheel_manifest raises RuntimeError when Ed25519 signature is invalid (correct base64, wrong signature bytes)."""
        actual_sha256 = hashlib.sha256(b"fake wheel content for testing").hexdigest()

        # Create a valid base64 signature but with wrong bytes
        bad_signature_bytes = b"0" * 64  # 64 bytes of zeros, but not a valid Ed25519 signature for the hash
        bad_signature_b64 = base64.b64encode(bad_signature_bytes).decode('utf-8')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({
                "sha256": actual_sha256,
                "signature": bad_signature_b64
            }, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with patch('agent_service.ee._manifest_pub_key', ed25519_test_keypair['public_key']):
                    with pytest.raises(RuntimeError, match="signature|verify|invalid"):
                        _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)


class TestVerifyWheelManifestSuccess:
    """Test 6: Valid manifest and wheel SHA256 with correct signature."""

    def test_verify_wheel_manifest_succeeds_with_valid_manifest(self, temp_wheel_file, manifest_path_patcher, ed25519_test_keypair):
        """_verify_wheel_manifest succeeds (no exception) when manifest and wheel SHA256 match and signature is valid."""
        # Compute actual SHA256 of wheel
        actual_sha256 = hashlib.sha256(b"fake wheel content for testing").hexdigest()

        # Sign the SHA256 hex string
        signature_msg = actual_sha256.encode('utf-8')
        signature_bytes = ed25519_test_keypair['private_key'].sign(signature_msg)
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            manifest_path = Path(f.name)
            json.dump({
                "sha256": actual_sha256,
                "signature": signature_b64
            }, f)
            f.flush()

        try:
            with manifest_path_patcher(manifest_path):
                with patch('agent_service.ee._manifest_pub_key', ed25519_test_keypair['public_key']):
                    # Should not raise any exception
                    _verify_wheel_manifest(str(temp_wheel_file))
        finally:
            manifest_path.unlink(missing_ok=True)


class TestInstallEEWheelIntegration:
    """Tests 9-10: _install_ee_wheel() integration with manifest verification."""

    def test_install_ee_wheel_calls_verify_wheel_manifest(self, manifest_path_patcher, ed25519_test_keypair):
        """_install_ee_wheel() calls _verify_wheel_manifest() before pip install."""
        verify_called = False

        def mock_verify(wheel_path):
            nonlocal verify_called
            verify_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake wheel file
            wheel_path = Path(tmpdir) / "axiom_ee-1.0.0-py3-none-any.whl"
            wheel_path.write_bytes(b"fake wheel")

            # Create valid manifest
            manifest_path = Path(tmpdir) / "axiom_ee.manifest.json"
            actual_sha256 = hashlib.sha256(b"fake wheel").hexdigest()
            signature_msg = actual_sha256.encode('utf-8')
            signature_bytes = ed25519_test_keypair['private_key'].sign(signature_msg)
            signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
            manifest_path.write_text(json.dumps({
                "sha256": actual_sha256,
                "signature": signature_b64
            }))

            with patch('agent_service.ee.glob.glob', return_value=[str(wheel_path)]):
                with patch('agent_service.ee._verify_wheel_manifest', side_effect=mock_verify):
                    with patch('agent_service.ee.subprocess.check_call'):
                        _install_ee_wheel()

            assert verify_called, "_verify_wheel_manifest was not called"

    def test_install_ee_wheel_propagates_runtime_error(self, manifest_path_patcher, ed25519_test_keypair):
        """_install_ee_wheel() raises RuntimeError when manifest verification fails (propagates exception)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "axiom_ee-1.0.0-py3-none-any.whl"
            wheel_path.write_bytes(b"fake wheel")

            with patch('agent_service.ee.glob.glob', return_value=[str(wheel_path)]):
                with patch('agent_service.ee._verify_wheel_manifest', side_effect=RuntimeError("Manifest verification failed")):
                    with pytest.raises(RuntimeError, match="Manifest verification failed"):
                        _install_ee_wheel()


class TestActivateEELiveErrorHandling:
    """Tests 11-12: activate_ee_live() error handling and state storage."""

    @pytest.mark.anyio
    async def test_activate_ee_live_catches_runtime_error(self):
        """activate_ee_live() catches RuntimeError from _install_ee_wheel() and stores error in app.state.ee_activation_error."""
        app = MagicMock()
        # Make getattr return None for 'ee' so we skip the "already active" check
        app.state = MagicMock()
        app.state.ee = None
        engine = MagicMock()

        with patch('agent_service.ee._install_ee_wheel', side_effect=RuntimeError("Test manifest error")):
            result = await activate_ee_live(app, engine)

        # Should store error in app.state
        assert app.state.ee_activation_error == "Test manifest error"
        # Should return None on failure
        assert result is None

    @pytest.mark.anyio
    async def test_activate_ee_live_returns_none_on_manifest_failure(self):
        """activate_ee_live() returns None (not EEContext) when manifest verification fails."""
        app = MagicMock()
        # Make getattr return None for 'ee' so we skip the "already active" check
        app.state = MagicMock()
        app.state.ee = None
        engine = MagicMock()

        with patch('agent_service.ee._install_ee_wheel', side_effect=RuntimeError("Invalid signature")):
            result = await activate_ee_live(app, engine)

        assert result is None


class TestLicenceEndpointEEActivationError:
    """Tests 13-14: /admin/licence endpoint includes ee_activation_error field."""

    @pytest.mark.anyio
    async def test_licence_endpoint_includes_ee_activation_error_null_on_success(self):
        """GET /admin/licence response includes ee_activation_error: null when activation succeeds or not attempted."""
        from agent_service.main import get_licence_status

        # Mock request with app state
        request = MagicMock()
        request.app = MagicMock()
        request.app.state = MagicMock()

        # Simulate successful activation (no error set)
        request.app.state.licence_state = None
        request.app.state.ee_activation_error = None

        current_user = MagicMock()

        # Call the endpoint
        response = await get_licence_status(request, current_user)

        # Response should include ee_activation_error field set to None
        assert "ee_activation_error" in response
        assert response["ee_activation_error"] is None

    @pytest.mark.anyio
    async def test_licence_endpoint_includes_ee_activation_error_string_on_failure(self):
        """GET /admin/licence response includes ee_activation_error: "{error_string}" when activation fails."""
        from agent_service.main import get_licence_status

        # Mock request with app state
        request = MagicMock()
        request.app = MagicMock()
        request.app.state = MagicMock()

        # Simulate activation failure with error message
        request.app.state.licence_state = None
        request.app.state.ee_activation_error = "Manifest verification failed: signature invalid"

        current_user = MagicMock()

        # Call the endpoint
        response = await get_licence_status(request, current_user)

        # Response should include ee_activation_error field with error message
        assert "ee_activation_error" in response
        assert response["ee_activation_error"] == "Manifest verification failed: signature invalid"


# Fixture for anyio backend support (async tests)
@pytest.fixture
def anyio_backend():
    return "asyncio"

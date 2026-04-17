"""
Phase 164 Integration Tests: mTLS Enforcement (SEC-01) and Public Key Externalization (QUAL-02)

Tests verify:
1. verify_client_cert rejects malformed CN (not starting with "node-")
2. verify_client_cert rejects unknown node
3. Public key env vars load correctly
4. Public key env vars are accessible as bytes
"""
import pytest
import os
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.security import verify_client_cert


# --- Test Fixtures ---

@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def valid_node_id():
    """A valid test node ID."""
    return "test-node-001"


@pytest.fixture
def valid_cn(valid_node_id):
    """Valid CN format: 'node-{node_id}'."""
    return f"node-{valid_node_id}"


# --- Test Functions ---

@pytest.mark.asyncio
async def test_verify_client_cert_malformed_cn(mock_request):
    """Test 1: Malformed CN (not starting with 'node-') raises 403."""
    db = AsyncMock(spec=AsyncSession)

    with pytest.raises(HTTPException) as exc_info:
        await verify_client_cert(
            request=mock_request,
            x_ssl_client_cn="invalid-format",
            db=db
        )

    assert exc_info.value.status_code == 403
    assert "Invalid certificate CN format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_client_cert_empty_node_id(mock_request):
    """Test 1b: Empty node ID after stripping 'node-' prefix raises 403."""
    db = AsyncMock(spec=AsyncSession)

    with pytest.raises(HTTPException) as exc_info:
        await verify_client_cert(
            request=mock_request,
            x_ssl_client_cn="node-",
            db=db
        )

    assert exc_info.value.status_code == 403
    assert "Invalid certificate CN format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_client_cert_node_not_found(mock_request, valid_cn, async_db_session):
    """Test 2: Unknown node in database raises 403."""
    # Use real async_db_session which is empty, so lookup will fail
    with pytest.raises(HTTPException) as exc_info:
        await verify_client_cert(
            request=mock_request,
            x_ssl_client_cn=valid_cn,
            db=async_db_session
        )

    assert exc_info.value.status_code == 403
    assert "Node not found" in exc_info.value.detail


def test_manifest_public_key_env_var_present():
    """Test 3: MANIFEST_PUBLIC_KEY environment variable is set (verified by conftest)."""
    # conftest.py sets MANIFEST_PUBLIC_KEY before importing agent_service
    # This test verifies the env var exists and can be loaded
    assert "MANIFEST_PUBLIC_KEY" in os.environ
    key_pem = os.environ["MANIFEST_PUBLIC_KEY"]
    assert key_pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert key_pem.endswith("-----END PUBLIC KEY-----\n")


def test_licence_public_key_env_var_present():
    """Test 3b: LICENCE_PUBLIC_KEY environment variable is set (verified by conftest)."""
    # conftest.py sets LICENCE_PUBLIC_KEY before importing agent_service
    # This test verifies the env var exists and can be loaded
    assert "LICENCE_PUBLIC_KEY" in os.environ
    key_pem = os.environ["LICENCE_PUBLIC_KEY"]
    assert key_pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert key_pem.endswith("-----END PUBLIC KEY-----\n")


def test_manifest_public_key_loader_function():
    """Test 4: _load_manifest_public_key() returns bytes when env var is set."""
    from agent_service.ee import _load_manifest_public_key

    # Call the loader function directly
    result = _load_manifest_public_key()

    # Should return bytes
    assert isinstance(result, bytes)
    assert result.startswith(b"-----BEGIN PUBLIC KEY-----")


def test_licence_public_key_loader_function():
    """Test 4b: _load_licence_public_key() returns bytes when env var is set."""
    from agent_service.services.licence_service import _load_licence_public_key

    # Call the loader function directly
    result = _load_licence_public_key()

    # Should return bytes
    assert isinstance(result, bytes)
    assert result.startswith(b"-----BEGIN PUBLIC KEY-----")

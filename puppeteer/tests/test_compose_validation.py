"""
Test compose generator validation of execution_mode parameter.

Tests verify that:
1. Compose generator rejects EXECUTION_MODE=direct with 400 error
2. Compose generator accepts docker/podman/auto modes with 200 response
3. Error message is actionable and suggests alternatives
"""
import pytest
from httpx import AsyncClient
from agent_service.main import app


@pytest.mark.asyncio
class TestComposeValidation:
    """Test compose generator validation of execution_mode."""

    async def test_compose_rejects_direct_mode(self, async_client: AsyncClient):
        """Compose generator rejects EXECUTION_MODE=direct."""
        response = await async_client.get(
            "/api/node/compose",
            params={"execution_mode": "direct", "token": "test-token"}
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "not supported" in detail.lower() or "direct" in detail.lower()

    async def test_compose_accepts_docker_mode(self, async_client: AsyncClient):
        """Compose generator accepts EXECUTION_MODE=docker."""
        response = await async_client.get(
            "/api/node/compose",
            params={"execution_mode": "docker", "token": "test-token"}
        )
        assert response.status_code == 200
        assert "EXECUTION_MODE" in response.text

    async def test_compose_accepts_podman_mode(self, async_client: AsyncClient):
        """Compose generator accepts EXECUTION_MODE=podman."""
        response = await async_client.get(
            "/api/node/compose",
            params={"execution_mode": "podman", "token": "test-token"}
        )
        assert response.status_code == 200
        assert "EXECUTION_MODE" in response.text

    async def test_compose_accepts_auto_mode(self, async_client: AsyncClient):
        """Compose generator accepts EXECUTION_MODE=auto (default)."""
        response = await async_client.get(
            "/api/node/compose",
            params={"token": "test-token"}
            # No execution_mode param — should default to "auto"
        )
        assert response.status_code == 200
        assert "EXECUTION_MODE" in response.text

    async def test_compose_error_message_helpful(self, async_client: AsyncClient):
        """Error message for direct mode is actionable."""
        response = await async_client.get(
            "/api/node/compose",
            params={"execution_mode": "direct", "token": "test-token"}
        )
        detail = response.json()["detail"]
        # Message should suggest alternatives or guidance
        assert any(x in detail.lower() for x in ["docker", "podman", "auto", "socket"])

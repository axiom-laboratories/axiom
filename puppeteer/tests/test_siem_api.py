"""API endpoint tests for SIEM routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from agent_service.main import app
from agent_service.db import SIEMConfig


@pytest.fixture
def client():
    """Create FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_admin_token():
    """Create a mock JWT token for admin user."""
    # In real tests, use the app's auth system to generate a valid token
    return "eyJ..."  # Placeholder — in practice, call auth.create_access_token()


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_get_siem_config_ee_mode(client, mock_admin_token):
    """Test GET /admin/siem/config returns 200 in EE mode."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}
    response = client.get("/admin/siem/config", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "backend" in data
    assert "destination" in data


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_get_siem_config_ce_mode(client):
    """Test GET /admin/siem/config returns 402 in CE mode."""
    response = client.get("/admin/siem/config")

    assert response.status_code == 402
    assert "Enterprise Edition" in response.json()["detail"]


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_patch_siem_config(client, mock_admin_token):
    """Test PATCH /admin/siem/config updates config."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    response = client.patch(
        "/admin/siem/config",
        headers=headers,
        json={
            "backend": "syslog",
            "destination": "siem.example.com",
            "syslog_port": 514,
            "enabled": True,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "syslog"
    assert data["destination"] == "siem.example.com"


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_post_test_connection(client, mock_admin_token):
    """Test POST /admin/siem/test-connection validates destination."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    response = client.post(
        "/admin/siem/test-connection",
        headers=headers,
        json={
            "backend": "webhook",
            "destination": "https://siem.example.com",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "status" in data


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_get_siem_status(client, mock_admin_token):
    """Test GET /admin/siem/status returns service status."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    response = client.get("/admin/siem/status", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "disabled")
    assert "consecutive_failures" in data


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_system_health_includes_siem(client):
    """Test GET /system/health includes siem field."""
    response = client.get("/system/health")

    assert response.status_code == 200
    data = response.json()
    assert "siem" in data
    assert data["siem"] in ("healthy", "degraded", "disabled")


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_siem_endpoints_require_admin_permission(client):
    """Test SIEM endpoints require admin:write permission."""
    # Without token, should get 403 or similar
    response = client.get("/admin/siem/config")
    assert response.status_code in (402, 403, 401)


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_siem_config_respects_enable_flag(client, mock_admin_token):
    """Test SIEM config respects enabled flag."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    # Update with enabled=False
    response = client.patch(
        "/admin/siem/config",
        headers=headers,
        json={"enabled": False}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False


@pytest.mark.skip(reason="Requires full app setup with DB + auth")
def test_siem_test_connection_with_webhook(client, mock_admin_token):
    """Test POST /admin/siem/test-connection with webhook backend."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    response = client.post(
        "/admin/siem/test-connection",
        headers=headers,
        json={
            "backend": "webhook",
            "destination": "https://siem.example.com/api/events",
            "enabled": True,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data or "status" in data

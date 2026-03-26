"""
SEC-06: GET /api/jobs/export must return X-Content-Type-Options: nosniff header.

The current StreamingResponse at the export endpoint sets only Content-Disposition
in the headers dict — it does NOT include X-Content-Type-Options: nosniff.

This test FAILS before the fix (plan 72-02) because the nosniff header is absent
from the response. After the fix, the header is present with value "nosniff".
"""
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from agent_service.main import app, get_db
from agent_service.deps import get_current_user


def _make_admin_user():
    fake_user = MagicMock()
    fake_user.username = "admin"
    fake_user.role = "admin"
    fake_user.token_version = 0
    return fake_user


@pytest.fixture
async def auth_client(db_session):
    """HTTP test client with admin user and test DB dependency overrides."""
    fake_user = _make_admin_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_csv_export_has_nosniff_header(auth_client):
    """GET /api/jobs/export must include X-Content-Type-Options: nosniff in response headers."""
    resp = await auth_client.get("/jobs/export")
    assert resp.status_code == 200, f"Expected 200 from export endpoint, got {resp.status_code}"
    assert "x-content-type-options" in resp.headers, (
        "Missing X-Content-Type-Options header on CSV export response"
    )
    assert resp.headers["x-content-type-options"] == "nosniff", (
        f"Expected 'nosniff', got '{resp.headers.get('x-content-type-options')}'"
    )


@pytest.mark.anyio
async def test_csv_export_content_type(auth_client):
    """GET /jobs/export must return text/csv media type."""
    resp = await auth_client.get("/jobs/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", ""), (
        "CSV export should return text/csv content type"
    )

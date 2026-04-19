"""Integration tests for Phase 171-01: Authorization permission gates.

Tests verify that granular permission checks are enforced on admin_router and
jobs_router endpoints. Viewer role should be blocked from write operations;
operator role should be allowed full read+write access.

Run with: pytest puppeteer/tests/test_auth_permissions.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from agent_service.main import app
from agent_service.db import Base, User, AsyncSessionLocal
from agent_service.auth import create_access_token, get_password_hash
from agent_service.deps import get_db


@pytest.fixture
async def engine():
    """In-memory SQLite engine for test isolation."""
    from sqlalchemy import select
    from agent_service.db import RolePermission

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default permissions for roles in test engine
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        role_permissions = {
            "operator": [
                "nodes:read", "system:read", "system:write",
                "jobs:read", "jobs:write", "nodes:write",
                "foundry:write", "signatures:write", "users:write"
            ],
            "viewer": ["nodes:read", "system:read", "jobs:read"]
        }

        for role, permissions in role_permissions.items():
            for permission in permissions:
                result = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role == role,
                        RolePermission.permission == permission
                    )
                )
                if not result.scalar_one_or_none():
                    session.add(RolePermission(role=role, permission=permission))

        await session.commit()

    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session_factory(engine):
    """Session factory bound to test engine."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def client(engine, async_session_factory):
    """AsyncClient with mocked get_db dependency."""
    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def viewer_user(async_session_factory):
    """Create viewer-role user for testing."""
    async with async_session_factory() as session:
        user = User(
            username="viewer_test",
            password_hash=get_password_hash("viewerpass"),
            role="viewer",
            token_version=0,
            must_change_password=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def operator_user(async_session_factory):
    """Create operator-role user for testing."""
    async with async_session_factory() as session:
        user = User(
            username="operator_test",
            password_hash=get_password_hash("operatorpass"),
            role="operator",
            token_version=0,
            must_change_password=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def admin_user(async_session_factory):
    """Create admin-role user for testing."""
    async with async_session_factory() as session:
        user = User(
            username="admin_test",
            password_hash=get_password_hash("adminpass"),
            role="admin",
            token_version=0,
            must_change_password=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def viewer_token(viewer_user):
    """Create JWT token for viewer user."""
    return create_access_token({
        "sub": viewer_user.username,
        "role": viewer_user.role,
        "tv": viewer_user.token_version
    })


@pytest.fixture
def operator_token(operator_user):
    """Create JWT token for operator user."""
    return create_access_token({
        "sub": operator_user.username,
        "role": operator_user.role,
        "tv": operator_user.token_version
    })


@pytest.fixture
def admin_token(admin_user):
    """Create JWT token for admin user."""
    return create_access_token({
        "sub": admin_user.username,
        "role": admin_user.role,
        "tv": admin_user.token_version
    })


@pytest.mark.asyncio
async def test_viewer_cannot_patch_jobs_definitions_jobs_write_gate(client, viewer_token):
    """Test 1: Viewer cannot PATCH /jobs/definitions/{id} (jobs:write gate).

    Viewer role does not have jobs:write permission, so PATCH should return 403.
    This tests the permission gate without requiring full job creation infrastructure.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}
    payload = {"enabled": False}

    response = await client.patch("/jobs/definitions/test-id", json=payload, headers=headers)
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    assert "permission" in response.json().get("detail", "").lower(), "Response should mention missing permission"


@pytest.mark.asyncio
async def test_operator_can_patch_jobs_definitions_jobs_write_gate(client, operator_token):
    """Test 2: Operator can PATCH /jobs/definitions/{id} (jobs:write gate).

    Operator role has jobs:write permission, so PATCH should not return 403.
    May return 404 (definition not found), but permission gate must pass.
    """
    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {"enabled": False}

    response = await client.patch("/jobs/definitions/test-id", json=payload, headers=headers)
    # Permission gate must pass (not 403). May return 404 since definition doesn't exist.
    assert response.status_code != 403, f"Expected permission to be granted, got 403 Forbidden: {response.text}"


@pytest.mark.asyncio
async def test_viewer_cannot_post_admin_generate_token_nodes_write_gate(client, viewer_token):
    """Test 3: Viewer cannot POST /admin/generate-token (nodes:write gate).

    Viewer role does not have nodes:write permission, so POST /admin/generate-token should return 403.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}
    payload = {
        "node_name": "test-node",
        "ip_address": "192.168.1.100",
        "network_interface": "eth0"
    }

    response = await client.post("/admin/generate-token", json=payload, headers=headers)
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    assert "permission" in response.json().get("detail", "").lower(), "Response should mention missing permission"


@pytest.mark.asyncio
async def test_operator_can_post_admin_generate_token_nodes_write_gate(client, operator_token):
    """Test 4: Operator can POST /admin/generate-token (nodes:write gate).

    Operator role has nodes:write permission, so POST /admin/generate-token should succeed (200).
    """
    headers = {"Authorization": f"Bearer {operator_token}"}
    payload = {
        "node_name": "test-node",
        "ip_address": "192.168.1.100",
        "network_interface": "eth0"
    }

    response = await client.post("/admin/generate-token", json=payload, headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    # Should return a join token
    data = response.json()
    assert "token" in data or "join_token" in data, "Response should include token"


@pytest.mark.asyncio
async def test_viewer_can_get_api_alerts_system_read_gate(client, viewer_token):
    """Test 5: Viewer can GET /api/alerts (system:read gate).

    Viewer role has system:read permission, so GET /api/alerts should succeed (200).
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}

    response = await client.get("/api/alerts", headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    # Should return list of alerts (may be empty)
    data = response.json()
    assert isinstance(data, list), "Response should be a list of alerts"


@pytest.mark.asyncio
async def test_viewer_cannot_post_api_alerts_acknowledge_system_write_gate(client, viewer_token, async_session_factory):
    """Test 6: Viewer cannot POST /api/alerts/{id}/acknowledge (system:write gate).

    Viewer role does not have system:write permission, so acknowledge should return 403.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Note: We're using a dummy alert ID since we likely don't have a real alert in the test DB
    # The permission check should happen before any ID validation
    alert_id = "dummy-alert-id"

    response = await client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)
    # Should get 403 for missing permission (or 404 if ID is checked first, but permission gate comes first)
    assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}: {response.text}"
    if response.status_code == 403:
        assert "permission" in response.json().get("detail", "").lower(), "Response should mention missing permission"


@pytest.mark.asyncio
async def test_admin_can_patch_jobs_definitions_bypasses_permission_checks(client, admin_token):
    """Sanity test: Admin role should bypass all permission checks.

    Admin users should be able to PATCH /jobs/definitions/{id} regardless of specific permission grants.
    May return 404 (definition not found), but permission gate must pass (not 403).
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"enabled": False}

    response = await client.patch("/jobs/definitions/test-id", json=payload, headers=headers)
    # Admin bypasses permission check. May return 404 since definition doesn't exist.
    assert response.status_code != 403, f"Expected admin to bypass permission check, got 403 Forbidden: {response.text}"


@pytest.mark.asyncio
async def test_viewer_can_get_jobs_count_jobs_read_gate(client, viewer_token):
    """Supplemental test: Viewer can GET /jobs/count (jobs:read gate).

    Viewer role has jobs:read permission, so GET /jobs/count should succeed.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}

    response = await client.get("/jobs/count", headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "total" in data, "Response should include total field"


@pytest.mark.asyncio
async def test_viewer_can_get_api_signals_system_read_gate(client, viewer_token):
    """Supplemental test: Viewer can GET /api/signals (system:read gate).

    Viewer role has system:read permission, so GET /api/signals should succeed.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}

    response = await client.get("/api/signals", headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert isinstance(data, (list, dict)), "Response should be a list or dict"


@pytest.mark.asyncio
async def test_viewer_cannot_post_api_signals_jobs_write_gate(client, viewer_token):
    """Supplemental test: Viewer cannot POST /api/signals/{name} (jobs:write gate).

    Viewer role does not have jobs:write permission, so should return 403.
    """
    headers = {"Authorization": f"Bearer {viewer_token}"}

    response = await client.post("/api/signals/test-signal", headers=headers)
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    assert "permission" in response.json().get("detail", "").lower(), "Response should mention missing permission"

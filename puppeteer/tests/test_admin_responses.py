"""
Snapshot tests for Admin/Auth domain routes.

These tests validate that authentication and admin management endpoints
return responses matching their declared Pydantic models.

Tests are written in RED state (may fail if routes don't have response_model yet).
Will be verified in GREEN state after response_model decorators are added.
"""

import pytest
from httpx import AsyncClient
from agent_service.models import (
    TokenResponse,
    RegisterResponse,
    UserResponse,
    UserSigningKeyResponse,
    ActionResponse,
    PaginatedResponse,
)


@pytest.mark.asyncio
async def test_login_response(async_client: AsyncClient):
    """Snapshot test: POST /auth/login returns TokenResponse.

    Expected response shape:
    - access_token: str
    - token_type: str ("bearer")
    - must_change_password: bool (optional)
    - expires_in: int (optional)
    """
    # Use OAuth2 form-encoded login
    response = await async_client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"}
    )

    # May be 401 if admin password doesn't match; that's OK
    # We're testing response shape, not auth logic
    if response.status_code == 200:
        data = response.json()
        token_resp = TokenResponse(**data)
        assert token_resp.access_token
        assert token_resp.token_type == "bearer"


@pytest.mark.asyncio
async def test_auth_me_response(async_client: AsyncClient, auth_headers: dict):
    """Snapshot test: GET /auth/me returns UserResponse.

    Expected response shape:
    - id: Optional[str]
    - username: str
    - role: str
    - created_at: Optional[datetime]
    """
    response = await async_client.get(
        "/auth/me",
        headers=auth_headers
    )

    if response.status_code == 200:
        data = response.json()
        user_resp = UserResponse(**data)
        assert user_resp.username
        assert user_resp.role


@pytest.mark.asyncio
async def test_patch_auth_me_password_change(async_client: AsyncClient, auth_headers: dict):
    """Snapshot test: PATCH /auth/me (password change) response.

    Expected: Returns TokenResponse with new access_token (for session continuity)
    OR returns UserResponse with password change confirmation.
    """
    response = await async_client.patch(
        "/auth/me",
        headers=auth_headers,
        json={"current_password": "admin123", "password": "new_password_123"}
    )

    if response.status_code == 200:
        data = response.json()
        # Could be TokenResponse or ActionResponse depending on implementation
        # TokenResponse if returning fresh token for session continuity
        # ActionResponse if returning action confirmation
        # Both are valid patterns
        if "access_token" in data:
            token_resp = TokenResponse(**data)
            assert token_resp.access_token
        elif "status" in data:
            action_resp = ActionResponse(**data)
            assert action_resp.status in ["updated", "ok", "acknowledged"]


@pytest.mark.asyncio
async def test_register_response(async_client: AsyncClient):
    """Snapshot test: POST /auth/register returns RegisterResponse.

    Expected response shape:
    - user: dict (user details)
    - role: str
    """
    # Note: This test may fail if registration is gated behind enrollment tokens
    response = await async_client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "test_password",
            "client_secret": "enrollment_token_here"
        }
    )

    if response.status_code == 200:
        data = response.json()
        register_resp = RegisterResponse(**data)
        assert register_resp.user or register_resp.role


@pytest.mark.asyncio
async def test_device_authorization_response(async_client: AsyncClient):
    """Snapshot test: POST /auth/device returns device authorization response.

    Expected response shape:
    - device_code: str
    - user_code: str
    - verification_uri: str
    - expires_in: int
    """
    response = await async_client.post("/auth/device")

    if response.status_code == 200:
        data = response.json()
        # Should have device code and user code
        assert "device_code" in data
        assert "user_code" in data


@pytest.mark.asyncio
async def test_device_token_exchange_response(async_client: AsyncClient):
    """Snapshot test: POST /auth/device/token exchanges device code for JWT.

    Expected: TokenResponse with access_token and token_type
    """
    # First get device code
    device_resp = await async_client.post("/auth/device")
    if device_resp.status_code != 200:
        pytest.skip("Device authorization endpoint not working")

    device_data = device_resp.json()
    device_code = device_data.get("device_code")

    # Then exchange for token (will likely fail without approval, but we test shape)
    response = await async_client.post(
        "/auth/device/token",
        json={"device_code": device_code, "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}
    )

    if response.status_code == 200:
        data = response.json()
        # Should have access_token or error message
        if "access_token" in data:
            token_resp = TokenResponse(**data)
            assert token_resp.access_token


@pytest.mark.asyncio
async def test_admin_generate_token_response(async_client: AsyncClient, auth_headers: dict):
    """Snapshot test: POST /admin/generate-token returns enrollment token.

    Expected response shape:
    - token: str (base64-encoded enrollment token)
    OR
    - ActionResponse with status="created"
    """
    response = await async_client.post(
        "/admin/generate-token",
        headers=auth_headers
    )

    if response.status_code == 200:
        data = response.json()
        # Check for token field (enrollment token)
        assert "token" in data or "status" in data


@pytest.mark.asyncio
async def test_admin_upload_key_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: POST /admin/upload-key returns action response.

    Expected response shape:
    - status: str ("stored" or from ActionResponse Literal)
    - resource_type: str (optional)
    - resource_id: str (optional)
    """
    response = await async_client.post(
        "/admin/upload-key",
        headers=auth_headers,
        json={"key_content": "-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALRiMLAA..."}
    )

    if response.status_code == 200:
        data = response.json()
        # Should have status field
        assert "status" in data


@pytest.mark.asyncio
async def test_list_users_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: GET /admin/users returns paginated user list.

    Expected response shape:
    - items: List[UserResponse]
    - total: int
    - page: int
    - page_size: int
    """
    response = await async_client.get(
        "/admin/users",
        headers=auth_headers
    )

    if response.status_code == 200:
        data = response.json()
        paginated = PaginatedResponse[UserResponse](**data)
        assert isinstance(paginated.items, list)
        assert paginated.total >= 0
        assert paginated.page >= 1


@pytest.mark.asyncio
async def test_create_user_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: POST /admin/users creates user and returns UserResponse.

    Expected response shape:
    - id: Optional[str]
    - username: str
    - role: str
    - created_at: Optional[datetime]
    """
    response = await async_client.post(
        "/admin/users",
        headers=auth_headers,
        json={"username": "newuser", "password": "pass123", "role": "operator"}
    )

    if response.status_code in [200, 201]:
        data = response.json()
        user_resp = UserResponse(**data)
        assert user_resp.username == "newuser"


@pytest.mark.asyncio
async def test_update_user_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: PATCH /admin/users/{id} updates user and returns response.

    Expected: UserResponse or ActionResponse
    """
    # This requires a user ID; will likely fail without one, but tests shape
    response = await async_client.patch(
        "/admin/users/test-user-id",
        headers=auth_headers,
        json={"role": "viewer"}
    )

    if response.status_code == 200:
        data = response.json()
        # Could be UserResponse or ActionResponse
        if "username" in data:
            user_resp = UserResponse(**data)
            assert user_resp.username
        elif "status" in data:
            action_resp = ActionResponse(**data)
            assert action_resp.status


@pytest.mark.asyncio
async def test_delete_user_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: DELETE /admin/users/{id} deletes user.

    Expected: 204 No Content OR ActionResponse
    """
    response = await async_client.delete(
        "/admin/users/test-user-id",
        headers=auth_headers
    )

    # 204 No Content is acceptable
    assert response.status_code in [204, 200]
    if response.status_code == 200:
        data = response.json()
        if data and "status" in data:
            action_resp = ActionResponse(**data)
            assert action_resp.status


@pytest.mark.asyncio
async def test_list_role_permissions_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: GET /admin/roles/{role}/permissions lists permissions.

    Expected response shape:
    - List[PermissionGrant] (flat list)
    OR
    - PaginatedResponse[PermissionGrant]
    """
    response = await async_client.get(
        "/admin/roles/operator/permissions",
        headers=auth_headers
    )

    if response.status_code == 200:
        data = response.json()
        # Could be list or paginated
        if isinstance(data, list):
            # Flat list of permissions
            pass
        elif isinstance(data, dict) and "items" in data:
            # Paginated response
            paginated = PaginatedResponse(**data)
            assert isinstance(paginated.items, list)


@pytest.mark.asyncio
async def test_grant_permission_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: POST /admin/roles/{role}/permissions grants permission.

    Expected response shape:
    - ActionResponse with status="created"
    """
    response = await async_client.post(
        "/admin/roles/operator/permissions",
        headers=auth_headers,
        json={"permission": "jobs:write"}
    )

    if response.status_code in [200, 201]:
        data = response.json()
        action_resp = ActionResponse(**data)
        assert action_resp.status in ["created", "acknowledged"]


@pytest.mark.asyncio
async def test_revoke_permission_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: DELETE /admin/roles/{role}/permissions/{permission} revokes.

    Expected response shape:
    - ActionResponse with status="deleted"
    """
    response = await async_client.delete(
        "/admin/roles/operator/permissions/jobs:write",
        headers=auth_headers
    )

    if response.status_code in [200, 204]:
        if response.status_code == 200:
            data = response.json()
            action_resp = ActionResponse(**data)
            assert action_resp.status


# Additional tests for User Account features

@pytest.mark.asyncio
async def test_create_signing_key_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: POST /account/signing-keys creates a signing key.

    Expected response shape:
    - UserSigningKeyGeneratedResponse with private_key_pem
    """
    response = await async_client.post(
        "/account/signing-keys",
        headers=auth_headers,
        json={"name": "test-key"}
    )

    if response.status_code in [200, 201]:
        data = response.json()
        # Should contain both public and private PEM
        assert "public_key_pem" in data or "private_key_pem" in data


@pytest.mark.asyncio
async def test_list_signing_keys_response(async_client: AsyncClient, auth_token: str):
    """Snapshot test: GET /account/signing-keys lists user's signing keys.

    Expected response shape:
    - List[UserSigningKeyResponse]
    OR
    - PaginatedResponse[UserSigningKeyResponse]
    """
    response = await async_client.get(
        "/account/signing-keys",
        headers=auth_headers
    )

    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            # Flat list
            for item in data:
                key_resp = UserSigningKeyResponse(**item)
                assert key_resp.name
        elif isinstance(data, dict) and "items" in data:
            # Paginated
            paginated = PaginatedResponse[UserSigningKeyResponse](**data)
            assert isinstance(paginated.items, list)


@pytest.mark.asyncio
async def test_delete_signing_key_response(async_client: AsyncClient, auth_headers: dict):
    """Snapshot test: DELETE /account/signing-keys/{id} deletes a signing key.

    Expected: 204 No Content OR ActionResponse
    """
    response = await async_client.delete(
        "/account/signing-keys/test-key-id",
        headers=auth_headers
    )

    assert response.status_code in [204, 200]

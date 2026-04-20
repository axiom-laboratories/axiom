"""
Phase 171-04: Permission enforcement without in-memory cache.

require_permission() now queries the DB on every request to fix multi-worker
race conditions. These tests verify:
1. Permission enforcement works correctly (admin bypasses, others checked via DB)
2. DB is queried on every request (no caching)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Test 1: Admin bypasses permission check entirely (no DB query)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_admin_bypasses_permission_check():
    """Admin role should return immediately without checking DB."""
    from agent_service.deps import require_permission

    mock_user = MagicMock()
    mock_user.role = "admin"
    mock_user.username = "admin"

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=AssertionError("Admin should not hit DB"))

    check_fn = require_permission("any:permission")

    result = await check_fn(mock_user, mock_db)
    assert result == mock_user
    assert mock_db.execute.call_count == 0


# ---------------------------------------------------------------------------
# Test 2: Operator access allowed when permission exists
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_operator_with_permission_allowed():
    """Operator with matching permission should be allowed."""
    from agent_service.deps import require_permission
    from agent_service.db import Base

    mock_user = MagicMock()
    mock_user.role = "operator"
    mock_user.username = "testop"

    # Mock the scalars().first() chain to return a permission object
    mock_perm = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_perm

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Ensure RolePermission table exists
    if "role_permissions" not in Base.metadata.tables:
        # In real env, EE is loaded; for this test we skip the CE guard
        pass

    check_fn = require_permission("jobs:read")

    result = await check_fn(mock_user, mock_db)
    assert result == mock_user
    assert mock_db.execute.call_count == 1


# ---------------------------------------------------------------------------
# Test 3: Viewer denied when permission missing
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_viewer_without_permission_denied():
    """Viewer without matching permission should be denied."""
    from fastapi import HTTPException
    from agent_service.deps import require_permission

    mock_user = MagicMock()
    mock_user.role = "viewer"
    mock_user.username = "viewonly"

    # Mock the scalars().first() chain to return None (permission not found)
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    check_fn = require_permission("jobs:write")

    with pytest.raises(HTTPException) as exc_info:
        await check_fn(mock_user, mock_db)

    assert exc_info.value.status_code == 403
    assert "jobs:write" in exc_info.value.detail
    assert mock_db.execute.call_count == 1


# ---------------------------------------------------------------------------
# Test 4: DB is queried on every request (no caching)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_require_permission_queries_db_on_every_request():
    """Each call to require_permission should hit DB — no caching."""
    from agent_service.deps import require_permission

    mock_user = MagicMock()
    mock_user.role = "operator"

    # Mock the scalars().first() chain to return a permission object
    mock_perm = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_perm

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Create the dependency checker
    check_fn = require_permission("jobs:read")

    # First call
    await check_fn(mock_user, mock_db)
    first_call_count = mock_db.execute.call_count
    assert first_call_count == 1, "First request should query DB"

    # Second call with same user/permission
    await check_fn(mock_user, mock_db)
    second_call_count = mock_db.execute.call_count
    assert second_call_count == 2, f"Second request should also query DB (was {first_call_count}, now {second_call_count})"

    # Verify DB was called exactly twice
    assert mock_db.execute.call_count == 2, "DB should be queried on every request, no caching"

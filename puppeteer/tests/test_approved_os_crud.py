"""Phase 107 Task 2: Approved OS PATCH + DELETE referential integrity tests.

Tests PATCH update, 404, and DELETE with/without referencing blueprints.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from agent_service.db import ApprovedOS, Blueprint


def _scalar_one(val):
    m = MagicMock()
    m.scalar_one_or_none.return_value = val
    return m


def _scalars_all(vals):
    m = MagicMock()
    m.scalars.return_value.all.return_value = vals
    return m


def _mock_user():
    u = MagicMock()
    u.username = "admin"
    u.role = "admin"
    return u


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ===== PATCH /api/approved-os/{id} =====

@pytest.mark.asyncio
async def test_patch_approved_os(mock_db):
    """PATCH updates name/image_uri/os_family fields."""
    from agent_service.ee.routers.foundry_router import update_approved_os
    from agent_service.models import ApprovedOSUpdate

    os_entry = ApprovedOS(id=1, name="Debian 12", image_uri="debian:12-slim", os_family="DEBIAN")
    mock_db.execute = AsyncMock(return_value=_scalar_one(os_entry))

    req = ApprovedOSUpdate(name="Debian 12 Updated", image_uri="debian:12")
    result = await update_approved_os(1, req, _mock_user(), mock_db)

    assert result.name == "Debian 12 Updated"
    assert result.image_uri == "debian:12"
    assert result.os_family == "DEBIAN"  # unchanged
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_patch_approved_os_not_found(mock_db):
    """PATCH with bad ID returns 404."""
    from agent_service.ee.routers.foundry_router import update_approved_os
    from agent_service.models import ApprovedOSUpdate

    mock_db.execute = AsyncMock(return_value=_scalar_one(None))

    req = ApprovedOSUpdate(name="Updated")
    with pytest.raises(HTTPException) as exc_info:
        await update_approved_os(999, req, _mock_user(), mock_db)
    assert exc_info.value.status_code == 404


# ===== DELETE /api/approved-os/{id} with referential integrity =====

@pytest.mark.asyncio
async def test_delete_approved_os_referenced(mock_db):
    """DELETE returns 409 when a blueprint references this OS entry."""
    from agent_service.ee.routers.foundry_router import delete_approved_os

    os_entry = ApprovedOS(id=1, name="Debian 12", image_uri="debian:12-slim", os_family="DEBIAN")
    bp = Blueprint(
        id="bp1", name="my-blueprint",
        definition=json.dumps({"base_os": "debian:12-slim"}),
        version=1
    )
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_one(os_entry),   # OS lookup
        _scalars_all([bp]),      # all blueprints scan
    ])

    with pytest.raises(HTTPException) as exc_info:
        await delete_approved_os(1, _mock_user(), mock_db)
    assert exc_info.value.status_code == 409
    assert "my-blueprint" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_approved_os_not_referenced(mock_db):
    """DELETE succeeds when no blueprint references this OS entry."""
    from agent_service.ee.routers.foundry_router import delete_approved_os

    os_entry = ApprovedOS(id=1, name="Alpine 3.18", image_uri="alpine:3.18", os_family="ALPINE")
    bp = Blueprint(
        id="bp1", name="unrelated",
        definition=json.dumps({"base_os": "debian:12-slim"}),
        version=1
    )
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_one(os_entry),
        _scalars_all([bp]),       # bp references different OS
    ])

    result = await delete_approved_os(1, _mock_user(), mock_db)
    assert result["status"] == "deleted"
    mock_db.delete.assert_awaited()

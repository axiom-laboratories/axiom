"""Phase 107 Task 2: Blueprint PATCH + GET by ID tests.

Tests optimistic locking, 404, deps_required on edit, and GET single blueprint.
Uses mock DB pattern (same as test_foundry_mirror.py).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from agent_service.db import Blueprint, CapabilityMatrix


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
    return db


# ===== PATCH /api/blueprints/{id} =====

@pytest.mark.asyncio
async def test_patch_blueprint_version_match(mock_db):
    """PATCH with correct version returns 200, version incremented."""
    from agent_service.ee.routers.foundry_router import update_blueprint
    from agent_service.models import BlueprintUpdate

    bp = Blueprint(
        id="bp1", type="RUNTIME", name="test-bp",
        definition=json.dumps({"base_os": "debian:12"}),
        version=3, os_family="DEBIAN"
    )
    mock_db.execute = AsyncMock(return_value=_scalar_one(bp))

    req = BlueprintUpdate(name="renamed-bp", version=3)
    result = await update_blueprint("bp1", req, _mock_user(), mock_db)

    assert result["version"] == 4
    assert result["name"] == "renamed-bp"
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_patch_blueprint_stale_version(mock_db):
    """PATCH with stale version returns 409."""
    from agent_service.ee.routers.foundry_router import update_blueprint
    from agent_service.models import BlueprintUpdate

    bp = Blueprint(
        id="bp1", type="RUNTIME", name="test-bp",
        definition=json.dumps({"base_os": "debian:12"}),
        version=5, os_family="DEBIAN"
    )
    mock_db.execute = AsyncMock(return_value=_scalar_one(bp))

    req = BlueprintUpdate(name="renamed-bp", version=3)
    with pytest.raises(HTTPException) as exc_info:
        await update_blueprint("bp1", req, _mock_user(), mock_db)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_patch_blueprint_not_found(mock_db):
    """PATCH with nonexistent ID returns 404."""
    from agent_service.ee.routers.foundry_router import update_blueprint
    from agent_service.models import BlueprintUpdate

    mock_db.execute = AsyncMock(return_value=_scalar_one(None))

    req = BlueprintUpdate(name="renamed-bp", version=1)
    with pytest.raises(HTTPException) as exc_info:
        await update_blueprint("nonexistent", req, _mock_user(), mock_db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_blueprint_deps_required(mock_db):
    """PATCH with definition change triggering deps_required returns 422."""
    from agent_service.ee.routers.foundry_router import update_blueprint
    from agent_service.models import BlueprintUpdate

    bp = Blueprint(
        id="bp1", type="RUNTIME", name="test-bp",
        definition=json.dumps({"base_os": "debian:12", "tools": [{"id": "tool-a"}]}),
        version=1, os_family="DEBIAN"
    )
    # Query 1: blueprint lookup
    # Query 2: capability matrix for OS+tool validation
    # tool-a has a dependency on tool-b
    cap = CapabilityMatrix(
        id=1, base_os_family="DEBIAN", tool_id="tool-a",
        runtime_dependencies=json.dumps(["tool-b"]), is_active=True
    )
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_one(bp),        # blueprint lookup
        _scalars_all([cap]),    # capability matrix query
    ])

    new_def = {"base_os": "debian:12", "tools": [{"id": "tool-a"}]}
    req = BlueprintUpdate(definition=new_def, version=1)
    with pytest.raises(HTTPException) as exc_info:
        await update_blueprint("bp1", req, _mock_user(), mock_db)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "deps_required"


@pytest.mark.asyncio
async def test_patch_blueprint_confirmed_deps(mock_db):
    """PATCH with confirmed_deps succeeds."""
    from agent_service.ee.routers.foundry_router import update_blueprint
    from agent_service.models import BlueprintUpdate

    bp = Blueprint(
        id="bp1", type="RUNTIME", name="test-bp",
        definition=json.dumps({"base_os": "debian:12", "tools": [{"id": "tool-a"}]}),
        version=1, os_family="DEBIAN"
    )
    cap = CapabilityMatrix(
        id=1, base_os_family="DEBIAN", tool_id="tool-a",
        runtime_dependencies=json.dumps(["tool-b"]), is_active=True
    )
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_one(bp),
        _scalars_all([cap]),
    ])

    new_def = {"base_os": "debian:12", "tools": [{"id": "tool-a"}]}
    req = BlueprintUpdate(definition=new_def, confirmed_deps=["tool-b"], version=1)
    result = await update_blueprint("bp1", req, _mock_user(), mock_db)

    assert result["version"] == 2
    mock_db.commit.assert_awaited()


# ===== GET /api/blueprints/{id} =====

@pytest.mark.asyncio
async def test_get_blueprint_by_id(mock_db):
    """GET returns single blueprint with parsed definition dict."""
    from agent_service.ee.routers.foundry_router import get_blueprint

    bp = Blueprint(
        id="bp1", type="RUNTIME", name="test-bp",
        definition=json.dumps({"base_os": "debian:12"}),
        version=2, os_family="DEBIAN"
    )
    mock_db.execute = AsyncMock(return_value=_scalar_one(bp))

    result = await get_blueprint("bp1", _mock_user(), mock_db)
    assert result["id"] == "bp1"
    assert isinstance(result["definition"], dict)
    assert result["definition"]["base_os"] == "debian:12"
    assert result["version"] == 2


@pytest.mark.asyncio
async def test_get_blueprint_not_found(mock_db):
    """GET with bad ID returns 404."""
    from agent_service.ee.routers.foundry_router import get_blueprint

    mock_db.execute = AsyncMock(return_value=_scalar_one(None))

    with pytest.raises(HTTPException) as exc_info:
        await get_blueprint("nonexistent", _mock_user(), mock_db)
    assert exc_info.value.status_code == 404

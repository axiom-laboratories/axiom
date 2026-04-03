"""Task 5 of 108-02: Foundry build validation tests for full dependency tree checking."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from agent_service.db import ApprovedIngredient, IngredientDependency
from agent_service.services.foundry_service import FoundryService


@pytest.mark.asyncio
async def test_build_succeeds_when_all_deps_mirrored():
    """Test that build succeeds when entire tree is MIRRORED."""
    # Create ingredients (parent + transitive)
    parent = ApprovedIngredient(
        id=str(uuid4()),
        name="Flask",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="MIRRORED",  # Mirrored
        auto_discovered=False
    )
    child = ApprovedIngredient(
        id=str(uuid4()),
        name="Werkzeug",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="MIRRORED",  # Mirrored
        auto_discovered=True
    )

    # Create dependency edge
    edge = IngredientDependency(
        id=str(uuid4()),
        parent_id=parent.id,
        child_id=child.id,
        dependency_type="transitive",
        version_constraint="==2.3.0",
        ecosystem="PYPI"
    )

    # Mock db
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(side_effect=lambda model, id: parent if id == parent.id else child if id == child.id else None)

    # Mock select result for edge query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [edge]
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Validation should pass
    is_valid, missing = await FoundryService._validate_ingredient_tree(mock_db, [parent.id])
    assert is_valid is True
    assert missing == []


@pytest.mark.asyncio
async def test_build_fails_if_parent_not_mirrored():
    """Test that build fails if parent ingredient not MIRRORED."""
    parent = ApprovedIngredient(
        id=str(uuid4()),
        name="Flask",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING",  # NOT mirrored
        auto_discovered=False
    )

    # Mock db
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=parent)

    # Mock select result for edge query (no edges)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    is_valid, missing = await FoundryService._validate_ingredient_tree(mock_db, [parent.id])
    assert is_valid is False
    assert len(missing) > 0
    assert "Flask" in missing[0]


@pytest.mark.asyncio
async def test_build_fails_if_transitive_dep_not_mirrored():
    """Test that build fails if any transitive dep not MIRRORED."""
    parent = ApprovedIngredient(
        id=str(uuid4()),
        name="Flask",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="MIRRORED",  # OK
        auto_discovered=False
    )
    child = ApprovedIngredient(
        id=str(uuid4()),
        name="Werkzeug",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="RESOLVING",  # NOT MIRRORED
        auto_discovered=True
    )

    edge = IngredientDependency(
        id=str(uuid4()),
        parent_id=parent.id,
        child_id=child.id,
        dependency_type="transitive",
        version_constraint="==2.3.0",
        ecosystem="PYPI"
    )

    # Mock db
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(side_effect=lambda model, id: parent if id == parent.id else child if id == child.id else None)

    # Mock select result for edge query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [edge]
    mock_db.execute = AsyncMock(return_value=mock_result)

    is_valid, missing = await FoundryService._validate_ingredient_tree(mock_db, [parent.id])
    assert is_valid is False
    assert "Werkzeug" in str(missing)


@pytest.mark.asyncio
async def test_error_message_lists_missing_deps():
    """Test that validation error message lists missing dependencies."""
    parent = ApprovedIngredient(
        id=str(uuid4()),
        name="Django",
        version_constraint="==4.2.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="MIRRORED",
        auto_discovered=False
    )
    missing_dep = ApprovedIngredient(
        id=str(uuid4()),
        name="sqlparse",
        version_constraint="==0.4.4",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="FAILED",
        auto_discovered=True
    )

    edge = IngredientDependency(
        id=str(uuid4()),
        parent_id=parent.id,
        child_id=missing_dep.id,
        dependency_type="transitive",
        version_constraint="==0.4.4",
        ecosystem="PYPI"
    )

    # Mock db
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(side_effect=lambda model, id: parent if id == parent.id else missing_dep if id == missing_dep.id else None)

    # Mock select result for edge query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [edge]
    mock_db.execute = AsyncMock(return_value=mock_result)

    is_valid, missing = await FoundryService._validate_ingredient_tree(mock_db, [parent.id])
    assert is_valid is False
    assert "sqlparse" in str(missing)
    assert "FAILED" in str(missing)  # Status should be listed


# Wave 1 / Plan 110-01 integration test for CVE build blocking

@pytest.mark.asyncio
async def test_build_blocks_vulnerable_transitive():
    """
    Integration test: verify build_template() raises 422 when
    a template ingredient has vulnerable transitive dependencies.

    RED: Stub for implementation in Plan 110-01 Task 4.
    Will verify: HTTPException(422) contains error code 'vulnerable_transitive_dependencies',
    vulnerable_count, CVE list with provenance paths.
    """
    pass

"""Phase 107 Task 1: Schema v46 tests — ecosystem column + new tables.

Verifies that:
- ApprovedIngredient has ecosystem column with default PYPI
- IngredientDependency table exists with correct columns and UniqueConstraint
- CuratedBundle table exists with correct columns
- CuratedBundleItem table exists with correct columns
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from agent_service.db import (
    Base,
    ApprovedIngredient,
    IngredientDependency,
    CuratedBundle,
    CuratedBundleItem,
)


@pytest.fixture
def sync_engine():
    """Create a fresh in-memory SQLite DB with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def inspector(sync_engine):
    return inspect(sync_engine)


@pytest.fixture
def session(sync_engine):
    with Session(sync_engine) as s:
        yield s


class TestApprovedIngredientEcosystem:
    def test_ecosystem_column_exists(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("approved_ingredients")}
        assert "ecosystem" in cols

    def test_ecosystem_default_pypi(self, session):
        ing = ApprovedIngredient(
            id="test-1",
            name="flask",
            os_family="DEBIAN",
            version_constraint=">=2.0",
        )
        session.add(ing)
        session.commit()
        session.refresh(ing)
        assert ing.ecosystem == "PYPI"


class TestIngredientDependency:
    def test_table_exists(self, inspector):
        assert "ingredient_dependencies" in inspector.get_table_names()

    def test_columns(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("ingredient_dependencies")}
        expected = {"id", "parent_id", "child_id", "ecosystem", "dependency_type",
                    "version_constraint", "discovered_at"}
        assert expected.issubset(cols)

    def test_unique_constraint(self, session):
        """UniqueConstraint on (parent_id, child_id, ecosystem)."""
        dep1 = IngredientDependency(
            parent_id="a", child_id="b", ecosystem="PYPI", dependency_type="install_requires"
        )
        dep2 = IngredientDependency(
            parent_id="a", child_id="b", ecosystem="PYPI", dependency_type="extras_require"
        )
        session.add(dep1)
        session.commit()
        session.add(dep2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestCuratedBundle:
    def test_table_exists(self, inspector):
        assert "curated_bundles" in inspector.get_table_names()

    def test_columns(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("curated_bundles")}
        expected = {"id", "name", "description", "ecosystem", "os_family", "created_at", "is_active"}
        assert expected.issubset(cols)


class TestCuratedBundleItem:
    def test_table_exists(self, inspector):
        assert "curated_bundle_items" in inspector.get_table_names()

    def test_columns(self, inspector):
        cols = {c["name"] for c in inspector.get_columns("curated_bundle_items")}
        expected = {"id", "bundle_id", "ingredient_name", "version_constraint"}
        assert expected.issubset(cols)

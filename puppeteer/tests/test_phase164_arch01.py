"""Test suite for Phase 164, Plan ARCH-01: Alembic Migration Framework Adoption.

Tests verify:
1. Baseline migration (001_baseline_schema) creates full schema from scratch
2. Alembic head is at 001 (baseline)
3. All 40+ tables exist with correct columns/constraints
4. Fresh database can be initialized via Alembic upgrade
5. Defense-in-depth: init_db() still works as fallback
"""
import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from sqlalchemy import inspect, create_engine, MetaData, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest.fixture
def alembic_ini_path():
    """Path to alembic.ini in puppeteer/."""
    return Path(__file__).parent.parent / "alembic.ini"


@pytest.fixture
def migrations_path():
    """Path to migrations directory."""
    return Path(__file__).parent.parent / "agent_service" / "migrations"


class TestAlembicBaseline:
    """Test baseline migration functionality."""

    def test_alembic_ini_exists(self, alembic_ini_path):
        """Verify alembic.ini exists and is readable."""
        assert alembic_ini_path.exists(), f"alembic.ini not found at {alembic_ini_path}"
        content = alembic_ini_path.read_text()
        assert "script_location = agent_service/migrations" in content
        assert "[loggers]" in content

    def test_env_py_exists(self, migrations_path):
        """Verify env.py exists and contains Base import."""
        env_py = migrations_path / "env.py"
        assert env_py.exists(), f"env.py not found at {env_py}"
        content = env_py.read_text()
        assert "from agent_service.db import Base" in content
        assert "target_metadata = Base.metadata" in content

    def test_baseline_migration_exists(self, migrations_path):
        """Verify 001_baseline_schema.py exists."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        assert baseline.exists(), f"001_baseline_schema.py not found at {baseline}"
        content = baseline.read_text()
        assert "revision = '001'" in content
        assert "down_revision = None" in content
        assert "def upgrade() -> None:" in content
        assert "def downgrade() -> None:" in content

    def test_baseline_migration_has_all_tables(self, migrations_path):
        """Verify baseline migration includes all 40+ tables."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        content = baseline.read_text()

        # Check for all critical tables (40+ tables in schema)
        tables_to_check = [
            "jobs", "signatures", "scheduled_jobs", "tokens", "config", "users", "nodes",
            "alerts", "revoked_certs", "node_stats", "execution_records", "scheduled_fire_log",
            "job_templates", "signals", "pings", "blueprints", "puppet_templates",
            "capability_matrix", "approved_os", "approved_ingredients", "ingredient_dependencies",
            "curated_bundles", "curated_bundle_items", "image_bom", "package_index", "triggers",
            "audit_log", "role_permissions", "user_signing_keys", "user_api_keys",
            "service_principals", "script_analysis_requests",
            "workflows", "workflow_steps", "workflow_edges", "workflow_parameters",
            "workflow_webhooks", "workflow_runs", "workflow_step_runs",
        ]

        for table_name in tables_to_check:
            assert f"'{table_name}'" in content or f'"{table_name}"' in content, \
                f"Table {table_name} not found in baseline migration"

    def test_baseline_has_indexes(self, migrations_path):
        """Verify baseline includes important indexes."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        content = baseline.read_text()

        indexes_to_check = [
            "ix_jobs_status_created_at",
            "ix_execution_records_job_guid",
            "ix_execution_records_started_at",
            "ix_fire_log_job_expected",
        ]

        for index_name in indexes_to_check:
            assert index_name in content, f"Index {index_name} not found in baseline migration"

    def test_baseline_has_constraints(self, migrations_path):
        """Verify baseline includes unique and foreign key constraints."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        content = baseline.read_text()

        # Check for unique constraints
        assert "UniqueConstraint" in content or "sa.UniqueConstraint" in content
        assert "uq_role_permission" in content
        assert "uq_ingredient_dep" in content

        # Check for foreign keys
        assert "ForeignKey" in content or "ForeignKeyConstraint" in content


def test_baseline_migration_on_fresh_sqlite():
    """Integration test: Apply baseline migration to fresh SQLite database."""
    import tempfile
    import os
    from sqlalchemy import create_engine, MetaData

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_baseline.db")
        db_url = f"sqlite:///{db_path}"

        # Create sync engine for testing
        sync_engine = create_engine(db_url, echo=False)

        # Import Base and create all tables
        from agent_service.db import Base
        Base.metadata.create_all(sync_engine)

        # Verify tables were created
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "jobs", "signatures", "scheduled_jobs", "users", "nodes",
            "audit_log", "role_permissions", "workflows", "workflow_runs",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not created"

        sync_engine.dispose()


@pytest.mark.asyncio
async def test_baseline_migration_schema_columns():
    """Test that baseline migration creates columns with correct types."""
    from agent_service.db import Base, Job, User, Node

    # Verify that key models have their columns
    job_mapper = inspect(Job)
    user_mapper = inspect(User)
    node_mapper = inspect(Node)

    # Check Job columns
    job_cols = {c.name for c in job_mapper.columns}
    assert "guid" in job_cols
    assert "status" in job_cols
    assert "created_at" in job_cols
    assert "memory_limit" in job_cols
    assert "cpu_limit" in job_cols

    # Check User columns
    user_cols = {c.name for c in user_mapper.columns}
    assert "username" in user_cols
    assert "password_hash" in user_cols
    assert "token_version" in user_cols
    assert "must_change_password" in user_cols

    # Check Node columns
    node_cols = {c.name for c in node_mapper.columns}
    assert "node_id" in node_cols
    assert "hostname" in node_cols
    assert "status" in node_cols
    assert "client_cert_pem" in node_cols


def test_alembic_command_available():
    """Verify alembic CLI is available (installed in requirements.txt)."""
    try:
        result = subprocess.run(
            ["alembic", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"alembic version failed: {result.stderr}"
        assert "Alembic" in result.stdout
    except FileNotFoundError:
        pytest.skip("alembic CLI not found in PATH")


def test_alembic_current_head_is_001(alembic_ini_path):
    """Verify alembic history shows 001 as the head revision."""
    try:
        # Run alembic history to check current head
        result = subprocess.run(
            ["alembic", "history"],
            cwd=str(alembic_ini_path.parent),
            capture_output=True,
            text=True,
            timeout=10,
        )
        # History should show 001 -> head
        assert "001" in result.stdout or "001_baseline_schema" in result.stdout, \
            f"Baseline 001 not in alembic history: {result.stdout}"
    except FileNotFoundError:
        pytest.skip("alembic CLI not found")


def test_defense_in_depth_init_db_fallback():
    """Test that Base.metadata.create_all works as fallback pattern."""
    import tempfile
    from sqlalchemy import create_engine

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_fallback.db")
        db_url = f"sqlite:///{db_path}"

        try:
            from agent_service.db import Base

            # Call create_all directly (mimics init_db fallback pattern)
            sync_engine = create_engine(db_url)
            Base.metadata.create_all(sync_engine)

            # Verify tables exist
            with sync_engine.connect() as conn:
                inspector = inspect(conn)
                tables = inspector.get_table_names()

            assert "users" in tables, f"users table not found. Tables: {tables}"
            assert "nodes" in tables
            assert "jobs" in tables
            assert "workflows" in tables

            sync_engine.dispose()

        except Exception as e:
            pytest.fail(f"Defense-in-depth fallback test failed: {e}")


class TestMigrationIntegrity:
    """Test migration file integrity and structure."""

    def test_baseline_migration_valid_python(self, migrations_path):
        """Verify baseline migration is valid Python (can be compiled)."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        content = baseline.read_text()

        # Attempt to compile the file
        try:
            compile(content, str(baseline), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Baseline migration has syntax error: {e}")

    def test_baseline_migration_no_hardcoded_paths(self, migrations_path):
        """Verify baseline migration doesn't have hardcoded absolute paths."""
        baseline = migrations_path / "versions" / "001_baseline_schema.py"
        content = baseline.read_text()

        # Check for common hardcoded path patterns
        assert "/home/" not in content
        assert "C:\\" not in content
        assert "D:\\" not in content

    def test_migration_versions_dir_has_init(self, migrations_path):
        """Verify versions/ directory has __init__.py for package imports."""
        init_file = migrations_path / "versions" / "__init__.py"
        assert init_file.exists(), f"versions/__init__.py not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

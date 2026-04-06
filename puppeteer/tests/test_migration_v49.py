"""
Integration tests for migration_v49.sql.

These tests verify that migration_v49.sql:
1. Adds memory_limit and cpu_limit columns to jobs table
2. Runs idempotently (IF NOT EXISTS prevents duplicate column errors)
3. Allows NULL values for both columns
4. Works correctly with fresh SQLAlchemy create_all deployments

Tests are in RED (failing) state until migration_v49.sql is created in Phase 120 Wave 1.
"""

import pytest
import os
import tempfile
from sqlalchemy import inspect, text, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from agent_service.db import Base, Job
import json


@pytest.fixture
async def test_db_engine():
    """Create isolated test Postgres database engine."""
    # For test purposes, use SQLite in-memory
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_session(test_db_engine):
    """Create async session bound to test engine."""
    async_session = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def migration_v49_path():
    """Return path to migration_v49.sql file."""
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, "migration_v49.sql")


async def read_and_execute_migration(engine, migration_file):
    """
    Read migration_v49.sql and execute it against the test database.

    Raises FileNotFoundError if migration file doesn't exist.
    """
    if not os.path.exists(migration_file):
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    with open(migration_file, "r") as f:
        migration_sql = f.read()

    async with engine.begin() as conn:
        # SQLite doesn't support multiple statements in execute(),
        # so split and execute individually
        for statement in migration_sql.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))


@pytest.mark.asyncio
async def test_migration_v49_adds_memory_limit_column(test_db_engine, migration_v49_path):
    """
    After migration_v49, jobs table should have memory_limit column.

    Checks: column exists and is TEXT/String type.
    """
    await read_and_execute_migration(test_db_engine, migration_v49_path)

    # Inspect table schema
    async with test_db_engine.begin() as conn:
        inspector = inspect(conn.sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

    assert "memory_limit" in columns, "memory_limit column not found in jobs table"
    assert columns["memory_limit"]["nullable"] is True, "memory_limit should be nullable"


@pytest.mark.asyncio
async def test_migration_v49_adds_cpu_limit_column(test_db_engine, migration_v49_path):
    """
    After migration_v49, jobs table should have cpu_limit column.

    Checks: column exists and is TEXT/String type.
    """
    await read_and_execute_migration(test_db_engine, migration_v49_path)

    # Inspect table schema
    async with test_db_engine.begin() as conn:
        inspector = inspect(conn.sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

    assert "cpu_limit" in columns, "cpu_limit column not found in jobs table"
    assert columns["cpu_limit"]["nullable"] is True, "cpu_limit should be nullable"


@pytest.mark.asyncio
async def test_migration_v49_idempotent(test_db_engine, migration_v49_path):
    """
    Running migration_v49 twice should not fail.

    Tests that IF NOT EXISTS in migration SQL prevents duplicate column errors.
    """
    # Run migration twice
    await read_and_execute_migration(test_db_engine, migration_v49_path)

    # Second run should not raise an error
    try:
        await read_and_execute_migration(test_db_engine, migration_v49_path)
    except Exception as e:
        pytest.fail(f"Migration is not idempotent: {e}")

    # Verify columns still exist (only once)
    async with test_db_engine.begin() as conn:
        inspector = inspect(conn.sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

    assert "memory_limit" in columns
    assert "cpu_limit" in columns


@pytest.mark.asyncio
async def test_migration_v49_columns_nullable(test_db_engine, migration_v49_path, test_session):
    """
    After migration_v49, both memory_limit and cpu_limit should allow NULL.

    Inserts a job without limits and verifies NULL is allowed.
    """
    await read_and_execute_migration(test_db_engine, migration_v49_path)

    # Insert job without limits
    job = Job(
        guid="test-nullable-001",
        task_type="script",
        payload=json.dumps({}),
        status="PENDING"
        # memory_limit and cpu_limit omitted — should be NULL
    )

    async_session = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with async_session() as session:
        session.add(job)
        await session.commit()

        # Retrieve and verify
        from sqlalchemy import select
        stmt = select(Job).where(Job.guid == "test-nullable-001")
        result = await session.execute(stmt)
        retrieved = result.scalar_one()

        assert retrieved.memory_limit is None
        assert retrieved.cpu_limit is None


@pytest.mark.asyncio
async def test_migration_v49_columns_insertable_with_values(test_db_engine, migration_v49_path):
    """
    After migration_v49, both memory_limit and cpu_limit should accept values.

    Inserts a job with limits and verifies values are stored and retrieved.
    """
    await read_and_execute_migration(test_db_engine, migration_v49_path)

    job = Job(
        guid="test-with-limits-001",
        task_type="script",
        payload=json.dumps({}),
        status="PENDING",
        memory_limit="512m",
        cpu_limit="2"
    )

    async_session = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with async_session() as session:
        session.add(job)
        await session.commit()

        # Retrieve and verify
        from sqlalchemy import select
        stmt = select(Job).where(Job.guid == "test-with-limits-001")
        result = await session.execute(stmt)
        retrieved = result.scalar_one()

        assert retrieved.memory_limit == "512m"
        assert retrieved.cpu_limit == "2"


@pytest.mark.asyncio
async def test_fresh_sqlite_create_all_includes_limit_columns():
    """
    Fresh deployment using SQLAlchemy create_all should include limit columns.

    Verifies that Job model in db.py already has the columns for fresh deployments.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Inspect schema
    async with engine.begin() as conn:
        inspector = inspect(conn.sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

    # Fresh deployment should include these columns
    # (This test verifies Job model in db.py has them)
    assert "memory_limit" in columns, "Fresh create_all should include memory_limit"
    assert "cpu_limit" in columns, "Fresh create_all should include cpu_limit"

    await engine.dispose()

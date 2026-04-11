"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from agent_service.main import app
from sqlalchemy import text


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    policy = asyncio.get_event_loop_policy()
    return policy


@pytest.fixture
def event_loop(event_loop_policy):
    """Create event loop for async tests."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def setup_db():
    """
    Ensure test database is initialized and has all required columns.
    Handles schema evolution where columns may have been added after tests were created.
    This runs once at the start of the test session.
    """
    import asyncio
    from agent_service.db import init_db, AsyncSessionLocal, User
    from agent_service.auth import get_password_hash
    from sqlalchemy import select

    # First, initialize the full schema via init_db (called at app startup)
    asyncio.run(init_db())

    # Then, add any missing columns for schema evolution and create test admin user
    async def add_missing_columns_and_users():
        async with AsyncSessionLocal() as session:
            # List of (table_name, column_name, column_definition) tuples for columns that might be missing
            missing_columns = [
                ("nodes", "env_tag", "VARCHAR(32)"),
                ("nodes", "operator_env_tag", "BOOLEAN DEFAULT 0"),
                ("nodes", "job_memory_limit", "VARCHAR"),
                ("nodes", "job_cpu_limit", "VARCHAR"),
                ("nodes", "detected_cgroup_version", "VARCHAR"),
                ("nodes", "cgroup_raw", "TEXT"),
                ("nodes", "execution_mode", "VARCHAR"),
                ("jobs", "job_run_id", "VARCHAR(36)"),
                ("jobs", "env_tag", "VARCHAR(32)"),
                ("jobs", "signature_hmac", "VARCHAR(64)"),
                ("jobs", "runtime", "VARCHAR(32)"),
                ("jobs", "name", "VARCHAR"),
                ("jobs", "created_by", "VARCHAR"),
                ("jobs", "originating_guid", "VARCHAR"),
                ("jobs", "target_node_id", "VARCHAR"),
                ("jobs", "dispatch_timeout_minutes", "INTEGER"),
                ("jobs", "memory_limit", "VARCHAR"),
                ("jobs", "cpu_limit", "VARCHAR"),
                ("scheduled_jobs", "updated_at", "DATETIME"),
                ("scheduled_jobs", "pushed_by", "VARCHAR"),
                ("scheduled_jobs", "memory_limit", "VARCHAR"),
                ("scheduled_jobs", "cpu_limit", "VARCHAR"),
                ("scheduled_jobs", "env_tag", "VARCHAR(32)"),
                ("scheduled_jobs", "runtime", "VARCHAR(32)"),
                ("scheduled_jobs", "allow_overlap", "BOOLEAN DEFAULT 0"),
                ("scheduled_jobs", "dispatch_timeout_minutes", "INTEGER"),
            ]

            for table_name, column_name, column_def in missing_columns:
                try:
                    # Try to add the column if it doesn't exist
                    await session.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                    )
                except Exception:
                    # Column likely already exists; ignore error
                    pass

            await session.commit()

            # Ensure admin user exists for tests
            result = await session.execute(select(User).where(User.username == "admin"))
            admin = result.scalar_one_or_none()
            if not admin:
                admin = User(
                    username="admin",
                    password_hash=get_password_hash("admin123"),
                    role="admin",
                    token_version=0,
                    must_change_password=False
                )
                session.add(admin)
                await session.commit()

    asyncio.run(add_missing_columns_and_users())


@pytest.fixture
async def async_client(setup_db):
    """Create an async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def auth_headers(async_client: AsyncClient, setup_db):
    """Create auth headers with a valid JWT token."""
    from agent_service.auth import create_access_token
    from agent_service.db import AsyncSessionLocal, User
    from sqlalchemy import select

    # Get the admin user's current token_version from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if admin:
            # Create token with the correct token_version from DB
            token = create_access_token({
                "sub": "admin",
                "role": "admin",
                "tv": admin.token_version
            })
            return {"Authorization": f"Bearer {token}"}

    # Fallback: return empty headers (should not happen with setup_db)
    return {}


@pytest.fixture
async def clean_db(setup_db):
    """
    Clean up jobs, nodes, and related tables before each test.
    Ensures test isolation by removing data from previous test runs.
    """
    from agent_service.db import AsyncSessionLocal

    async def cleanup():
        async with AsyncSessionLocal() as session:
            # Delete all jobs and nodes to ensure test isolation
            await session.execute(text("DELETE FROM jobs"))
            await session.execute(text("DELETE FROM nodes"))
            await session.commit()

    # Clean before test
    await cleanup()
    yield
    # Clean after test
    await cleanup()


@pytest.fixture
async def created_job_guid(async_client: AsyncClient, auth_headers: dict):
    """Create a test job and return its GUID."""
    req = {
        "task_type": "script",
        "runtime": "python",
        "payload": {"script_content": "print('test')"},
    }
    response = await async_client.post("/jobs", json=req, headers=auth_headers)
    if response.status_code == 200:
        return response.json().get("guid")
    # Return None if creation fails
    return None

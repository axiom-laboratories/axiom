"""
Pytest configuration and shared fixtures.
"""
import pytest
import pytest_asyncio
import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport
from agent_service.main import app
from sqlalchemy import text

# Add sister repo tools to path for admin_signer imports
tools_path = os.path.abspath(os.path.expanduser("~/Development/toms_home/.agents/tools"))
if tools_path not in sys.path:
    sys.path.insert(0, tools_path)


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

    # Then, create test admin user
    async def create_test_admin_user():
        async with AsyncSessionLocal() as session:
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

    asyncio.run(create_test_admin_user())


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


@pytest_asyncio.fixture
async def async_db_session():
    """
    Async SQLAlchemy session for test isolation.

    Each test gets a fresh session wrapped in a transaction that rolls back after the test.
    Ensures parallel test isolation and no cross-test contamination.
    """
    from agent_service.db import AsyncSessionLocal, engine
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        # Start a transaction for this test
        await session.begin()
        yield session
        # Rollback after test to restore database state
        await session.rollback()


@pytest_asyncio.fixture
async def workflow_fixture(async_db_session):
    """
    Pre-created workflow with 3 steps and 2 edges forming a simple chain.

    Structure:
      Step 1 → Step 2 → Step 3

    Returns the full Workflow entity with nested steps[], edges[], parameters[].
    Uses async_db_session for automatic transaction cleanup.
    """
    from agent_service.db import (
        Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter,
        ScheduledJob, Signature
    )
    from uuid import uuid4

    # Generate UUIDs for all entities
    workflow_id = str(uuid4())
    step_ids = [str(uuid4()) for _ in range(3)]
    edge_ids = [str(uuid4()) for _ in range(2)]
    param_id = str(uuid4())

    # Create a signature for the scheduled jobs (required FK)
    sig_id = str(uuid4())
    sig = Signature(
        id=sig_id,
        name=f"test-sig-{uuid4().hex[:8]}",
        public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
        uploaded_by="admin"
    )
    async_db_session.add(sig)
    await async_db_session.flush()

    # Create 3 scheduled jobs (step units)
    jobs = []
    for i in range(3):
        job = ScheduledJob(
            id=step_ids[i],
            name=f"test-scheduled-job-{i}-{uuid4().hex[:8]}",
            script_content=f"echo 'Step {i+1}'",
            signature_id=sig_id,
            signature_payload="Zm9vYmFyYmF6",  # base64 dummy
            created_by="admin"
        )
        async_db_session.add(job)
        jobs.append(job)

    await async_db_session.flush()

    # Create the workflow
    workflow = Workflow(
        id=workflow_id,
        name=f"test-workflow-{uuid4().hex[:8]}",
        created_by="admin",
        is_paused=False
    )
    async_db_session.add(workflow)
    await async_db_session.flush()

    # Create 3 workflow steps
    workflow_steps = []
    for i, job_id in enumerate(step_ids):
        step = WorkflowStep(
            id=step_ids[i],
            workflow_id=workflow_id,
            scheduled_job_id=job_id,
            node_type="SCRIPT",
            config_json=None
        )
        async_db_session.add(step)
        workflow_steps.append(step)

    await async_db_session.flush()

    # Create 2 edges: step1 → step2, step2 → step3
    edges = [
        WorkflowEdge(
            id=edge_ids[0],
            workflow_id=workflow_id,
            from_step_id=step_ids[0],
            to_step_id=step_ids[1],
            branch_name=None
        ),
        WorkflowEdge(
            id=edge_ids[1],
            workflow_id=workflow_id,
            from_step_id=step_ids[1],
            to_step_id=step_ids[2],
            branch_name=None
        )
    ]
    for edge in edges:
        async_db_session.add(edge)

    await async_db_session.flush()

    # Create a parameter
    param = WorkflowParameter(
        id=param_id,
        workflow_id=workflow_id,
        name="test_param",
        type="string",
        default_value="default_value"
    )
    async_db_session.add(param)

    await async_db_session.commit()

    # Return as dict with nested arrays (matching API response structure)
    return {
        "id": workflow_id,
        "name": workflow.name,
        "created_by": "admin",
        "created_at": workflow.created_at,
        "is_paused": False,
        "steps": [
            {
                "id": step_ids[i],
                "workflow_id": workflow_id,
                "scheduled_job_id": step_ids[i],
                "node_type": "SCRIPT",
                "config_json": None
            }
            for i in range(3)
        ],
        "edges": [
            {
                "id": edge_ids[0],
                "workflow_id": workflow_id,
                "from_step_id": step_ids[0],
                "to_step_id": step_ids[1],
                "branch_name": None
            },
            {
                "id": edge_ids[1],
                "workflow_id": workflow_id,
                "from_step_id": step_ids[1],
                "to_step_id": step_ids[2],
                "branch_name": None
            }
        ],
        "parameters": [
            {
                "id": param_id,
                "workflow_id": workflow_id,
                "name": "test_param",
                "type": "string",
                "default_value": "default_value"
            }
        ]
    }


@pytest_asyncio.fixture
async def workflow_run_fixture(async_db_session, workflow_fixture):
    """Create a WorkflowRun in RUNNING state (Phase 147 execution engine)."""
    from agent_service.db import WorkflowRun

    run = WorkflowRun(
        id=str(uuid4()),
        workflow_id=workflow_fixture["id"],
        status="RUNNING",
        started_at=datetime.utcnow(),
        trigger_type="MANUAL",
        triggered_by="test_user"
    )
    async_db_session.add(run)
    await async_db_session.flush()
    return run


@pytest_asyncio.fixture
async def workflow_step_run_fixture(async_db_session, workflow_fixture, workflow_run_fixture):
    """Create a WorkflowStepRun in PENDING state."""
    from agent_service.db import WorkflowStepRun

    step_id = workflow_fixture["steps"][0]["id"]
    step_run = WorkflowStepRun(
        id=str(uuid4()),
        workflow_run_id=workflow_run_fixture.id,
        workflow_step_id=step_id,
        status="PENDING",
        created_at=datetime.utcnow()
    )
    async_db_session.add(step_run)
    await async_db_session.flush()
    return step_run


@pytest_asyncio.fixture
async def sample_3_step_linear_workflow(setup_db):
    """
    Create a workflow with 3 steps in linear dependency: A→B→C.
    Reuses Phase 146 ScheduledJob factory.
    Returns: (workflow ORM object, dict with step IDs keyed as 'step_0', 'step_1', 'step_2')

    Uses setup_db to ensure tables are created, then creates workflow directly.
    """
    from agent_service.db import (
        Workflow, WorkflowStep, WorkflowEdge, ScheduledJob, Signature, AsyncSessionLocal
    )
    from uuid import uuid4

    async with AsyncSessionLocal() as session:
        # Create signature first (required for ScheduledJob FK)
        sig = Signature(
            id=str(uuid4()),
            name=f"test-sig-{uuid4().hex[:8]}",
            public_key="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----",
            uploaded_by="admin"
        )
        session.add(sig)
        await session.flush()

        # Create 3 scheduled jobs (reuse Phase 146 factory pattern)
        job_ids = [str(uuid4()) for _ in range(3)]
        jobs = []
        for i in range(3):
            job = ScheduledJob(
                id=job_ids[i],
                name=f"test_job_{uuid4().hex[:8]}_{i}",
                script_content=f"echo 'job {i}'",
                signature_id=sig.id,
                signature_payload="Zm9vYmFyYmF6",
                created_by="test_user"
            )
            session.add(job)
            jobs.append(job)
        await session.flush()

        # Create workflow
        workflow = Workflow(
            id=str(uuid4()),
            name="test_linear_workflow",
            created_by="test_user",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Create 3 steps
        step_ids = [str(uuid4()) for _ in range(3)]
        for i, job_id in enumerate(job_ids):
            step = WorkflowStep(
                id=step_ids[i],
                workflow_id=workflow.id,
                scheduled_job_id=job_id,
                node_type="SCRIPT"
            )
            session.add(step)
        await session.flush()

        # Create edges A→B, B→C
        edge_ab = WorkflowEdge(
            id=str(uuid4()),
            workflow_id=workflow.id,
            from_step_id=step_ids[0],
            to_step_id=step_ids[1],
            branch_name=None
        )
        edge_bc = WorkflowEdge(
            id=str(uuid4()),
            workflow_id=workflow.id,
            from_step_id=step_ids[1],
            to_step_id=step_ids[2],
            branch_name=None
        )
        session.add(edge_ab)
        session.add(edge_bc)
        await session.commit()

        return workflow, {f"step_{i}": step_ids[i] for i in range(3)}


# Add uuid4 and datetime to imports if not present
from uuid import uuid4
from datetime import datetime


@pytest_asyncio.fixture
async def test_user_id(setup_db):
    """Create a test user directly in DB and return its username (PK) for deletion testing."""
    from agent_service.db import User, AsyncSessionLocal
    from agent_service.auth import get_password_hash

    # Create a test user directly in the database
    username = f"test-delete-user-{uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        user = User(
            username=username,
            password_hash=get_password_hash("test123"),
            role="operator",
            token_version=0,
            must_change_password=False
        )
        session.add(user)
        await session.commit()
    return username  # User's primary key is username


@pytest_asyncio.fixture
async def test_signing_key_id(setup_db):
    """Create a test signing key directly in DB and return its ID for deletion testing."""
    from agent_service.db import UserSigningKey, AsyncSessionLocal

    # Create a test signing key directly in the database
    key_id = str(uuid4())
    async with AsyncSessionLocal() as session:
        key = UserSigningKey(
            id=key_id,
            username="admin",  # Associate with admin user (created by setup_db)
            name=f"test-delete-key-{uuid4().hex[:8]}",
            public_key_pem="-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANDiE2Zm7HK5Q=\n-----END PUBLIC KEY-----"
        )
        session.add(key)
        await session.commit()
    return key_id

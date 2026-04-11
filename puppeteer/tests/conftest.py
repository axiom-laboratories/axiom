"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from agent_service.main import app


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


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    """Create auth headers with a valid JWT token."""
    # Create an admin user and get a token
    login_response = await async_client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    # Fallback: return empty headers (may cause tests to fail, but better than error)
    return {}


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

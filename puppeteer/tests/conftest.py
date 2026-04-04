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

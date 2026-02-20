import pytest
from httpx import AsyncClient, ASGITransport
from puppeteer.agent_service.main import app, get_db
from puppeteer.agent_service.db import User

@pytest.fixture
async def client(db_session):
    # Override the dependency to use the test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_read_main(client):
    response = await client.get("/installer")
    assert response.status_code in [200, 404]

@pytest.mark.anyio
async def test_auth_login_fail(client):
    # No user exists in memory DB, so it should fail
    response = await client.post("/auth/login", data={"username": "wrong", "password": "password"})
    assert response.status_code == 401


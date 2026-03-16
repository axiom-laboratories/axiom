import pytest
import re
from httpx import AsyncClient, ASGITransport
from agent_service.main import app, _device_codes, _user_code_index, _USER_CODE_ALPHABET
from agent_service.db import User
from agent_service.auth import create_access_token, SECRET_KEY, ALGORITHM
from agent_service.tests.conftest import db_session, engine, anyio_backend
from jose import jwt
from datetime import datetime, timedelta

@pytest.mark.anyio
async def test_device_authorization_response():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/device")
    
    assert response.status_code == 200
    data = response.json()
    assert "device_code" in data
    assert "user_code" in data
    assert "verification_uri" in data
    assert "verification_uri_complete" in data
    assert data["expires_in"] == 300
    assert data["interval"] == 5
    assert data["user_code"] in data["verification_uri_complete"]

@pytest.mark.anyio
async def test_user_code_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/device")
    
    user_code = response.json()["user_code"]
    # Format: XXXX-XXXX
    assert re.match(r"^[A-Z2-9]{4}-[A-Z2-9]{4}$", user_code)
    
    # Excludes 0, O, 1, I, L
    confusable = "0O1IL"
    for char in confusable:
        assert char not in user_code

@pytest.mark.anyio
async def test_token_exchange_pending():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Get code
        resp = await ac.post("/auth/device")
        device_code = resp.json()["device_code"]
        
        # 2. Poll immediately (should be pending)
        token_resp = await ac.post("/auth/device/token", json={"device_code": device_code})
        assert token_resp.status_code == 400
        assert token_resp.json()["detail"]["error"] == "authorization_pending"

@pytest.mark.anyio
async def test_token_exchange_denied():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/auth/device")
        device_code = resp.json()["device_code"]
        
        # Manually set to denied
        _device_codes[device_code]["status"] = "denied"
        
        token_resp = await ac.post("/auth/device/token", json={"device_code": device_code})
        assert token_resp.status_code == 400
        assert token_resp.json()["detail"]["error"] == "access_denied"

@pytest.mark.anyio
async def test_token_exchange_expired():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Non-existent code
        token_resp = await ac.post("/auth/device/token", json={"device_code": "invalid-code"})
        assert token_resp.status_code == 400
        assert token_resp.json()["detail"]["error"] == "expired_token"

@pytest.mark.anyio
async def test_token_exchange_approved(db_session):
    # 1. Create a test user
    user = User(
        username="testuser",
        password_hash="fakehash",
        role="admin",
        token_version=1
    )
    db_session.add(user)
    await db_session.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Get device code
        resp = await ac.post("/auth/device")
        device_code = resp.json()["device_code"]
        
        # 3. Approve it manually in state
        _device_codes[device_code]["status"] = "approved"
        _device_codes[device_code]["approved_by"] = "testuser"
        
        # 4. Exchange for token
        token_resp = await ac.post("/auth/device/token", json={"device_code": device_code})
        assert token_resp.status_code == 200
        
        data = token_resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # 5. Verify JWT claims
        payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["type"] == "device_flow"
        assert payload["role"] == "admin"

@pytest.mark.anyio
async def test_device_approval_flow(db_session):
    # 1. Create a test user with a valid token
    user = User(username="approver", password_hash="fake", role="admin")
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token({"sub": "approver", "role": "admin", "tv": 0})
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Get device code
        resp = await ac.post("/auth/device")
        user_code = resp.json()["user_code"]
        device_code = resp.json()["device_code"]
        
        # 3. GET approve page
        page_resp = await ac.get(f"/auth/device/approve?user_code={user_code}")
        assert page_resp.status_code == 200
        assert user_code in page_resp.text
        
        # 4. POST approve
        approve_resp = await ac.post("/auth/device/approve", data={
            "user_code": user_code,
            "token": token
        })
        assert approve_resp.status_code == 200
        assert "Device authorized" in approve_resp.text
        
        # 5. Verify state is approved
        assert _device_codes[device_code]["status"] == "approved"
        assert _device_codes[device_code]["approved_by"] == "approver"
        
        # 6. Exchange should now work
        token_resp = await ac.post("/auth/device/token", json={"device_code": device_code})
        assert token_resp.status_code == 200
        assert "access_token" in token_resp.json()

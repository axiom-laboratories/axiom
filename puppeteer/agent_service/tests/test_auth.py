from agent_service.auth import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt
from datetime import timedelta
import pytest

def test_password_hashing():
    password = "secret-password"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)

def test_create_access_token():
    data = {"sub": "admin", "role": "admin"}
    token = create_access_token(data)
    assert isinstance(token, str)
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload

def test_create_access_token_with_expiry():
    data = {"sub": "user"}
    expires = timedelta(minutes=30)
    token = create_access_token(data, expires_delta=expires)
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user"
    assert "exp" in payload

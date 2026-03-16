import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mop_sdk.auth import CredentialStore, DeviceFlowHandler

def test_credential_store_save_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CredentialStore(config_dir=tmpdir)
        data = {"base_url": "http://test", "access_token": "token123"}
        
        store.save(data)
        
        # Verify file existence and content
        cred_file = Path(tmpdir) / "credentials.json"
        assert cred_file.exists()
        
        # Verify permissions (0600)
        mode = os.stat(cred_file).st_mode
        assert oct(mode & 0o777) == '0o600'
        
        # Verify load
        loaded = store.load()
        assert loaded == data

def test_credential_store_clear():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CredentialStore(config_dir=tmpdir)
        store.save({"token": "abc"})
        assert (Path(tmpdir) / "credentials.json").exists()
        
        store.clear()
        assert not (Path(tmpdir) / "credentials.json").exists()

@patch("httpx.Client.post")
def test_device_flow_start(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"device_code": "dc1", "user_code": "uc1", "interval": 5, "expires_in": 300}
    )
    
    handler = DeviceFlowHandler("http://test")
    data = handler.start_flow()
    
    assert data["device_code"] == "dc1"
    mock_post.assert_called_once_with("http://test/auth/device")

@patch("httpx.Client.post")
@patch("time.sleep", return_value=None) # Fast poll
def test_device_flow_poll_success(mock_sleep, mock_post):
    # First call: pending, Second call: success
    mock_post.side_effect = [
        MagicMock(status_code=400, json=lambda: {"detail": {"error": "authorization_pending"}}),
        MagicMock(status_code=200, json=lambda: {"access_token": "jwt123", "role": "admin"})
    ]
    
    handler = DeviceFlowHandler("http://test")
    token_data = handler.poll_for_token("dc1", interval=1, expires_in=10)
    
    assert token_data["access_token"] == "jwt123"
    assert mock_post.call_count == 2

@patch("httpx.Client.post")
@patch("time.sleep", return_value=None)
def test_device_flow_poll_denied(mock_sleep, mock_post):
    mock_post.return_value = MagicMock(
        status_code=400,
        json=lambda: {"detail": {"error": "access_denied"}}
    )
    
    handler = DeviceFlowHandler("http://test")
    token_data = handler.poll_for_token("dc1", interval=1, expires_in=10)
    
    assert token_data is None

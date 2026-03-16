import pytest
from unittest.mock import patch, MagicMock
from mop_sdk.cli import main
import sys

def test_cli_help(capsys):
    with patch.object(sys, 'argv', ['mop-push', '--help']):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    
    captured = capsys.readouterr()
    assert "usage: mop-push" in captured.out
    assert "login" in captured.out
    assert "job" in captured.out

def test_cli_no_args(capsys):
    with patch.object(sys, 'argv', ['mop-push']):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    
    captured = capsys.readouterr()
    assert "usage: mop-push" in captured.out

@patch("mop_sdk.cli.DeviceFlowHandler")
@patch("mop_sdk.cli.CredentialStore")
@patch("webbrowser.open")
def test_cli_login_flow(mock_browser, mock_store_class, mock_handler_class, capsys):
    # Setup mock handler
    mock_handler = mock_handler_class.return_value
    mock_handler.start_flow.return_value = {
        "device_code": "dc123",
        "user_code": "XXXX-YYYY",
        "verification_uri_complete": "http://verify",
        "interval": 1,
        "expires_in": 60
    }
    mock_handler.poll_for_token.return_value = {
        "access_token": "jwt123",
        "role": "admin"
    }
    
    # Setup mock store
    mock_store = mock_store_class.return_value
    
    with patch.object(sys, 'argv', ['mop-push', 'login']):
        main()
    
    captured = capsys.readouterr()
    assert "USER CODE: XXXX-YYYY" in captured.out
    assert "Successfully authenticated and saved credentials." in captured.out
    
    mock_handler.start_flow.assert_called_once()
    mock_browser.assert_called_once_with("http://verify")
    mock_store.save.assert_called_once()
    
    # Verify saved data
    args, kwargs = mock_store.save.call_args
    saved_data = args[0]
    assert saved_data["access_token"] == "jwt123"
    assert saved_data["role"] == "admin"

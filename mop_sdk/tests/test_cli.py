import pytest
from unittest.mock import patch, MagicMock, call
from mop_sdk.cli import main
import sys
import os

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


# --- CLI-01: AXIOM_URL fix ---

@patch("mop_sdk.cli.DeviceFlowHandler")
@patch("mop_sdk.cli.CredentialStore")
@patch("webbrowser.open")
def test_axiom_url_env_var(mock_browser, mock_store_class, mock_handler_class, capsys):
    """AXIOM_URL env var must be used as base_url for the server connection."""
    mock_handler = mock_handler_class.return_value
    mock_handler.start_flow.return_value = {
        "device_code": "dc123",
        "user_code": "XXXX-YYYY",
        "verification_uri_complete": "http://test-server/verify",
        "interval": 1,
        "expires_in": 60,
    }
    mock_handler.poll_for_token.return_value = {
        "access_token": "jwt123",
        "role": "admin",
    }

    env = {"AXIOM_URL": "http://test-server"}
    with patch.dict(os.environ, env, clear=False):
        # Ensure MOP_URL is not set during this test
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MOP_URL", None)
            with patch.object(sys, "argv", ["axiom-push", "login"]):
                main()

    mock_handler_class.assert_called_once()
    call_args = mock_handler_class.call_args
    assert call_args[0][0] == "http://test-server" or call_args[1].get("base_url") == "http://test-server", (
        f"DeviceFlowHandler called with wrong base_url: {call_args}"
    )


@patch("mop_sdk.cli.DeviceFlowHandler")
@patch("mop_sdk.cli.CredentialStore")
@patch("webbrowser.open")
def test_mop_url_not_read(mock_browser, mock_store_class, mock_handler_class, capsys):
    """MOP_URL should NOT be read; if only MOP_URL is set, CLI falls back to localhost."""
    mock_handler = mock_handler_class.return_value
    mock_handler.start_flow.return_value = {
        "device_code": "dc123",
        "user_code": "XXXX-YYYY",
        "verification_uri_complete": "http://localhost:8001/verify",
        "interval": 1,
        "expires_in": 60,
    }
    mock_handler.poll_for_token.return_value = {
        "access_token": "jwt123",
        "role": "admin",
    }

    # Set only MOP_URL (wrong), clear AXIOM_URL
    env_patch = {"MOP_URL": "http://wrong-server"}
    with patch.dict(os.environ, env_patch, clear=False):
        os.environ.pop("AXIOM_URL", None)
        with patch.object(sys, "argv", ["axiom-push", "login"]):
            main()

    # DeviceFlowHandler must NOT have been called with "http://wrong-server"
    mock_handler_class.assert_called_once()
    call_args = mock_handler_class.call_args
    actual_url = call_args[0][0] if call_args[0] else call_args[1].get("base_url", "")
    assert actual_url != "http://wrong-server", (
        f"CLI incorrectly read MOP_URL — was called with: {actual_url}"
    )


# --- CLI-02: key generate subcommand ---

def test_key_generate_creates_files(tmp_path, capsys):
    """key generate creates signing.key (0o600) and verification.key in ~/.axiom/."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        with patch.object(sys, "argv", ["axiom-push", "key", "generate"]):
            main()

    signing_key = tmp_path / ".axiom" / "signing.key"
    verification_key = tmp_path / ".axiom" / "verification.key"

    assert signing_key.exists(), "signing.key not found"
    assert verification_key.exists(), "verification.key not found"

    # Check permissions on private key
    import stat
    mode = oct(stat.S_IMODE(signing_key.stat().st_mode))
    assert mode == oct(0o600), f"Expected 0o600, got {mode}"

    captured = capsys.readouterr()
    assert "-----BEGIN PUBLIC KEY-----" in captured.out


def test_key_generate_refuses_overwrite(tmp_path, capsys):
    """key generate exits with code 1 if keys already exist and --force not given."""
    axiom_dir = tmp_path / ".axiom"
    axiom_dir.mkdir(parents=True)
    (axiom_dir / "signing.key").write_bytes(b"existing-key")

    with patch("pathlib.Path.home", return_value=tmp_path):
        with patch.object(sys, "argv", ["axiom-push", "key", "generate"]):
            with pytest.raises(SystemExit) as exc:
                main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "already exist" in captured.out.lower() or "already exist" in captured.err.lower()


def test_key_generate_force_overwrites(tmp_path, capsys):
    """key generate --force overwrites existing keys."""
    axiom_dir = tmp_path / ".axiom"
    axiom_dir.mkdir(parents=True)
    existing = axiom_dir / "signing.key"
    existing.write_bytes(b"old-key")
    old_content = existing.read_bytes()

    with patch("pathlib.Path.home", return_value=tmp_path):
        with patch.object(sys, "argv", ["axiom-push", "key", "generate", "--force"]):
            main()

    new_content = existing.read_bytes()
    assert new_content != old_content, "Key was not overwritten with --force"


# --- init flow tests (Task 3) ---

@patch("mop_sdk.cli.MOPClient")
@patch("mop_sdk.cli.CredentialStore")
def test_init_skip_login(mock_store_class, mock_client_class, capsys):
    """init skips login if already authenticated; skips registration if key name already in server list."""
    mock_store = mock_store_class.return_value
    mock_store.load.return_value = {
        "base_url": "http://test",
        "access_token": "tok",
        "role": "admin",
        "username": "alice",
    }

    mock_client = MagicMock()
    mock_client.list_signatures.return_value = [
        {"id": "sig-1", "name": f"alice@testhost"}
    ]
    mock_client_class.from_store.return_value = mock_client

    with patch("socket.gethostname", return_value="testhost"):
        with patch.object(sys, "argv", ["axiom-push", "init"]):
            # Key exists already, so reading pub key
            with patch("pathlib.Path.home", return_value=MagicMock()) as mock_home:
                mock_axiom_dir = MagicMock()
                mock_priv_path = MagicMock()
                mock_pub_path = MagicMock()
                mock_priv_path.exists.return_value = True
                mock_pub_path.read_bytes.return_value = b"-----BEGIN PUBLIC KEY-----\nfakekey\n-----END PUBLIC KEY-----\n"
                mock_home.return_value.__truediv__ = lambda self, x: mock_axiom_dir if x == ".axiom" else NotImplemented
                mock_axiom_dir.__truediv__ = lambda self, x: mock_priv_path if x == "signing.key" else mock_pub_path
                main()

    captured = capsys.readouterr()
    assert "Already logged in as alice" in captured.out
    assert "sig-1" in captured.out


@patch("mop_sdk.cli.do_login")
@patch("mop_sdk.cli.MOPClient")
@patch("mop_sdk.cli.CredentialStore")
def test_init_full_flow(mock_store_class, mock_client_class, mock_do_login, tmp_path, capsys):
    """init: login → key generate → register → print Key ID + job push command."""
    call_count = [0]

    def load_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return None  # Not logged in yet
        return {
            "base_url": "http://test",
            "access_token": "tok",
            "username": "alice",
        }

    mock_store = mock_store_class.return_value
    mock_store.load.side_effect = load_side_effect

    mock_client = MagicMock()
    mock_client.list_signatures.return_value = []
    mock_client.register_signature.return_value = {"id": "sig-new", "name": "alice@testhost"}
    mock_client.get_me.return_value = {"username": "alice"}
    mock_client_class.from_store.return_value = mock_client
    mock_client_class.return_value = mock_client

    with patch("socket.gethostname", return_value="testhost"):
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch.object(sys, "argv", ["axiom-push", "init"]):
                main()

    captured = capsys.readouterr()
    assert "Setup complete" in captured.out
    assert "sig-new" in captured.out
    assert "axiom-push job push" in captured.out


@patch("mop_sdk.cli.MOPClient")
@patch("mop_sdk.cli.CredentialStore")
def test_init_idempotent_existing_key(mock_store_class, mock_client_class, tmp_path, capsys):
    """init registers the key even if local key file exists but not yet on server."""
    mock_store = mock_store_class.return_value
    mock_store.load.return_value = {
        "base_url": "http://test",
        "access_token": "tok",
        "username": "alice",
    }

    mock_client = MagicMock()
    mock_client.list_signatures.return_value = []  # Not on server yet
    mock_client.register_signature.return_value = {"id": "sig-new", "name": "alice@testhost"}
    mock_client_class.from_store.return_value = mock_client

    # Create existing key file
    axiom_dir = tmp_path / ".axiom"
    axiom_dir.mkdir()
    priv_path = axiom_dir / "signing.key"
    pub_path = axiom_dir / "verification.key"

    # Generate real keys for the test
    from cryptography.hazmat.primitives.asymmetric import ed25519 as ed25519_lib
    from cryptography.hazmat.primitives import serialization
    priv = ed25519_lib.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    with patch("socket.gethostname", return_value="testhost"):
        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch.object(sys, "argv", ["axiom-push", "init"]):
                main()

    # register_signature must have been called once (local key existed but not registered)
    mock_client.register_signature.assert_called_once()

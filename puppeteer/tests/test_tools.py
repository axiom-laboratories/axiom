import sys
import os
import pytest
import base64
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# Import admin_signer (sys.path is set up by conftest)
import admin_signer
from admin_signer import generate_keys, sign_content, load_signing_key

def test_admin_signer_keys(tmp_path):
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    
    with patch("admin_signer.SIGNING_KEY_PATH", str(secrets_dir / "signing.key")), \
         patch("admin_signer.VERIFY_KEY_PATH", str(secrets_dir / "verification.key")):
        
        generate_keys()
        
        assert os.path.exists(secrets_dir / "signing.key")
        assert os.path.exists(secrets_dir / "verification.key")
        
        # Verify loadable
        key = load_signing_key()
        assert isinstance(key, ed25519.Ed25519PrivateKey)

def test_admin_signer_sign_verify(tmp_path):
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    
    with patch("admin_signer.SIGNING_KEY_PATH", str(secrets_dir / "signing.key")), \
         patch("admin_signer.VERIFY_KEY_PATH", str(secrets_dir / "verification.key")):
        
        generate_keys()
        content = "hello world"
        sig = sign_content(content)
        
        # Verify with public key
        with open(secrets_dir / "verification.key", "rb") as f:
            pub_key = serialization.load_pem_public_key(f.read())
            pub_key.verify(base64.b64decode(sig), content.encode('utf-8'))

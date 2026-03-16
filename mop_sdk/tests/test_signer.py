import pytest
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from mop_sdk.signer import Signer
import tempfile
from pathlib import Path

def test_signer_load_and_sign():
    # Generate a key
    priv = ed25519.Ed25519PrivateKey.generate()
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(pem)
        tf_path = tf.name
    
    try:
        # Load
        loaded_priv = Signer.load_private_key(tf_path)
        assert isinstance(loaded_priv, ed25519.Ed25519PrivateKey)
        
        # Sign
        payload = "test-payload"
        sig_b64 = Signer.sign_payload(loaded_priv, payload)
        
        # Verify (manually using cryptography)
        sig_bytes = base64.b64decode(sig_b64)
        pub = priv.public_key()
        pub.verify(sig_bytes, payload.encode("utf-8"))
        
    finally:
        Path(tf_path).unlink()

def test_signer_invalid_key():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"not-a-pem-key")
        tf_path = tf.name
    
    try:
        with pytest.raises(ValueError, match="Failed to load private key"):
            Signer.load_private_key(tf_path)
    finally:
        Path(tf_path).unlink()

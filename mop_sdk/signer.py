import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class Signer:
    @staticmethod
    def load_private_key(key_path: str) -> ed25519.Ed25519PrivateKey:
        """Loads an Ed25519 private key from a PEM file."""
        with open(key_path, "rb") as f:
            key_data = f.read()
        
        try:
            return serialization.load_pem_private_key(key_data, password=None)
        except Exception as e:
            raise ValueError(f"Failed to load private key: {e}")

    @staticmethod
    def sign_payload(private_key: ed25519.Ed25519PrivateKey, payload: str) -> str:
        """Signs a UTF-8 payload and returns a Base64-encoded signature."""
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise TypeError("Private key must be an Ed25519PrivateKey instance")
        
        signature = private_key.sign(payload.encode("utf-8"))
        return base64.b64encode(signature).decode("utf-8")

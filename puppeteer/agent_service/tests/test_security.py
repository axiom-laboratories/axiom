from agent_service.security import encrypt_secrets, decrypt_secrets, mask_secrets
import os

def test_mask_secrets():
    payload = {
        "name": "job1",
        "secrets": {"password": "supersecret", "key": "12345"}
    }
    masked = mask_secrets(payload)
    assert masked["secrets"]["password"] == "****** (Redacted)"
    assert masked["secrets"]["key"] == "****** (Redacted)"
    # Original should be untouched
    assert payload["secrets"]["password"] == "supersecret"

def test_encryption_roundtrip():
    payload = {
        "secrets": {"token": "my-token-123"}
    }
    encrypted = encrypt_secrets(payload)
    assert encrypted["secrets"]["token"] != "my-token-123"
    
    decrypted = decrypt_secrets(encrypted)
    assert decrypted["secrets"]["token"] == "my-token-123"
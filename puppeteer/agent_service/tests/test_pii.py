from agent_service.security import mask_pii
import pytest

def test_mask_pii_email():
    data = {"msg": "Contact me at test@example.com for info"}
    masked = mask_pii(data)
    assert masked["msg"] == "Contact me at [EMAIL_REDACTED] for info"

def test_mask_pii_ssn():
    data = "Your SSN is 123-45-6789."
    masked = mask_pii(data)
    assert masked == "Your SSN is [SSN_REDACTED]."

def test_mask_pii_recursive():
    data = {
        "users": [
            {"email": "user1@test.com", "notes": "SSN 999-00-1111"},
            {"email": "user2@test.com"}
        ],
        "meta": "no pii here"
    }
    masked = mask_pii(data)
    assert masked["users"][0]["email"] == "[EMAIL_REDACTED]"
    assert masked["users"][0]["notes"] == "SSN [SSN_REDACTED]"
    assert masked["users"][1]["email"] == "[EMAIL_REDACTED]"
    assert masked["meta"] == "no pii here"

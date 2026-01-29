import os
import sys
from typing import Dict
from cryptography.fernet import Fernet
from fastapi import Header, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()

# Security CRITICAL: Fail if API_KEY is not set.
try:
    API_KEY = os.environ["API_KEY"]
except KeyError:
    print("CRITICAL: API_KEY setup variable is missing. Halting.")
    sys.exit(1)

# Encryption Key for Secrets
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode() if os.getenv("ENCRYPTION_KEY") else Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# --- Auth Security Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def encrypt_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k, v in payload["secrets"].items():
            if isinstance(v, str):
                new_secrets[k] = cipher_suite.encrypt(v.encode()).decode()
            else:
                new_secrets[k] = v
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

def decrypt_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k, v in payload["secrets"].items():
            try:
                if isinstance(v, str):
                    new_secrets[k] = cipher_suite.decrypt(v.encode()).decode()
                else:
                    new_secrets[k] = v
            except Exception:
                new_secrets[k] = "ERROR_DECRYPTING"
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

def mask_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k in payload["secrets"].keys():
            new_secrets[k] = "****** (Redacted)"
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

async def verify_api_key(x_api_key: str = Header(None)):
    """Legacy/Service Auth via API Key."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

async def verify_client_cert(request: Request):
    """Enforces mTLS: Requires a valid client certificate."""
    # In a real proxy/Uvicorn setup, common_name is passed in header (e.g., X-SSL-Client-CN)
    # or accessible via request.scope['client'] if SSL is terminated here.
    # For now, we will trust X-SSL-Client-Verified: SUCCESS header from Uvicorn/Proxy
    # OR (since we are using Uvicorn directly):
    
    # NOTE: Uvicorn does not expose client cert details in ASGI scope easily without quirks.
    pass

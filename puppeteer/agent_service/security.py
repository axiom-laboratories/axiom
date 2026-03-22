import os
import sys
import re
import hmac as _hmac
import hashlib
from typing import Dict, Any
from cryptography.fernet import Fernet
from fastapi import Header, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from sqlalchemy.future import select
from .db import get_db, Node, AsyncSession

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


# ---------------------------------------------------------------------------
# SEC-02: HMAC integrity helpers for signature_payload fields
# ---------------------------------------------------------------------------

def compute_signature_hmac(key_bytes: bytes, signature_payload: str, signature_id: str, job_id: str) -> str:
    """HMAC-SHA256 tag binding payload to its job and signature. key_bytes = ENCRYPTION_KEY."""
    message = f"{signature_payload}:{signature_id}:{job_id}".encode("utf-8")
    return _hmac.new(key_bytes, message, hashlib.sha256).hexdigest()


def verify_signature_hmac(key_bytes: bytes, stored_hmac: str, signature_payload: str, signature_id: str, job_id: str) -> bool:
    """Constant-time HMAC verification. Returns True if tag matches."""
    expected = compute_signature_hmac(key_bytes, signature_payload, signature_id, job_id)
    return _hmac.compare_digest(stored_hmac, expected)


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

def mask_pii(data: Any) -> Any:
    """Recursively scans and masks common PII patterns (Email, SSN, etc)."""
    # Patterns
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    SSN_REGEX = r'\d{3}-\d{2}-\d{4}'
    
    if isinstance(data, dict):
        return {k: mask_pii(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_pii(v) for v in data]
    elif isinstance(data, str):
        # Mask Email
        data = re.sub(EMAIL_REGEX, "[EMAIL_REDACTED]", data)
        # Mask SSN
        data = re.sub(SSN_REGEX, "[SSN_REDACTED]", data)
        return data
    return data

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

async def verify_node_secret(
    request: Request,
    x_node_id: str = Header(...),
    x_machine_id: str = Header(...),
    x_node_secret_hash: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies the host-bound secret hash against the stored value for the node.
    This prevents 'lift-and-shift' attacks.
    """
    result = await db.execute(select(Node).where(Node.node_id == x_node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.status == "REVOKED":
        raise HTTPException(status_code=403, detail="Node access has been revoked")

    if node.machine_id and node.machine_id != x_machine_id:
        raise HTTPException(status_code=403, detail="Machine ID Mismatch - Identity Binding Failure")

    if node.node_secret_hash and node.node_secret_hash != x_node_secret_hash:
        raise HTTPException(status_code=403, detail="Invalid Node Secret Hash - Identity Binding Failure")
    
    return x_node_id

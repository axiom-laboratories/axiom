import os
import re
import hmac as _hmac
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any
from cryptography.fernet import Fernet
from fastapi import Header, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from sqlalchemy.future import select
from .db import get_db, Node, AsyncSession, RevokedCert

logger = logging.getLogger(__name__)

load_dotenv()

# Encryption Key for Secrets
def _load_or_generate_encryption_key() -> bytes:
    """Load ENCRYPTION_KEY from environment variable.

    ENCRYPTION_KEY is required for all deployments (CE and EE).
    No fallbacks: no file-based fallback, no auto-generation.

    Raises:
        RuntimeError: if ENCRYPTION_KEY environment variable is not set.
    """
    if val := os.getenv("ENCRYPTION_KEY"):
        return val.encode()

    # EE-06: ENCRYPTION_KEY hard requirement — no fallbacks
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is required but not set.\n"
        "Set it to a Fernet key (use: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    )

ENCRYPTION_KEY = _load_or_generate_encryption_key()
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
    # SEC-04: bounded email regex to prevent ReDoS (replaces unbounded .+ quantifiers)
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]{1,64}@[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+'
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

def validate_path_within(base: Path, candidate: Path) -> Path:
    """Resolve both paths and raise HTTP 400 if candidate escapes base.
    Requires Python 3.9+ (Path.is_relative_to added in 3.9).
    """
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return resolved_candidate


async def verify_client_cert(
    request: Request,
    x_ssl_client_cn: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Enforces application-layer mTLS: Validates client certificate CN.

    Caddy performs TLS handshake validation and forwards X-SSL-Client-CN header
    after a successful client certificate verification. This function performs
    defense-in-depth validation:

    1. Validates X-SSL-Client-CN header is present and well-formed (CN = "node-{node_id}")
    2. Looks up the node in the database
    3. Extracts the certificate serial from the node's stored client certificate
    4. Checks if the certificate serial is in the RevokedCert table (revocation defense-in-depth)
    5. Returns the node_id for downstream use

    Args:
        request: FastAPI Request object
        x_ssl_client_cn: Client certificate CN forwarded by Caddy (e.g., "node-abc123")
        db: Database session for node and revocation lookups

    Returns:
        node_id (str) — the validated node identifier

    Raises:
        HTTPException(403): If header is missing, CN is malformed, node not found, or certificate is revoked
    """
    # Extract node_id from CN (expected format: "node-{node_id}")
    if not x_ssl_client_cn.startswith("node-"):
        raise HTTPException(status_code=403, detail="Invalid certificate CN format")

    node_id = x_ssl_client_cn[5:]  # Strip "node-" prefix

    if not node_id:
        raise HTTPException(status_code=403, detail="Invalid certificate CN format")

    # Look up the node in the database
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=403, detail="Node not found")

    # Extract certificate serial and check revocation status
    if node.client_cert_pem:
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography import x509

            cert_bytes = node.client_cert_pem.encode() if isinstance(node.client_cert_pem, str) else node.client_cert_pem
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            cert_serial = cert.serial_number

            # Check if certificate serial is in RevokedCert table
            revoked_result = await db.execute(
                select(RevokedCert).where(RevokedCert.serial == cert_serial)
            )
            if revoked_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="Certificate revoked")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating client certificate serial for node {node_id}: {e}")
            raise HTTPException(status_code=403, detail="Certificate validation failed")

    return node_id

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


# ---------------------------------------------------------------------------
# Webhook Secret & Signature Verification Helpers (Phase 149)
# ---------------------------------------------------------------------------

def hash_webhook_secret(plaintext_secret: str) -> str:
    """Hash webhook secret using bcrypt. Called at webhook creation time.

    Args:
        plaintext_secret: Plaintext webhook secret to hash

    Returns:
        Bcrypt hash of the secret
    """
    try:
        from .auth import pwd_context
    except ImportError:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    return pwd_context.hash(plaintext_secret)


def verify_webhook_signature(
    header_signature: str,
    request_body: bytes,
    plaintext_secret: str
) -> bool:
    """Verify webhook signature using constant-time HMAC-SHA256 comparison.

    Validates the X-Hub-Signature-256 header against the raw request body
    using the webhook's plaintext secret. Uses constant-time comparison to
    prevent timing attacks.

    Args:
        header_signature: Header value from X-Hub-Signature-256 header
                         Format: "sha256=<hex>"
        request_body: Raw request body bytes (not parsed JSON)
        plaintext_secret: Plaintext webhook secret

    Returns:
        True if signature matches; False otherwise
    """
    # Compute expected signature
    expected_signature = "sha256=" + _hmac.new(
        plaintext_secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return _hmac.compare_digest(header_signature, expected_signature)

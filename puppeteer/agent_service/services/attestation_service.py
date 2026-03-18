"""
Phase 30 — Runtime Attestation: Orchestrator-side verification service.

Provides verify_bundle() which validates a node's RSA-signed attestation bundle.
Returns one of three string constants — never raises an exception.

RSA verify uses the 4-arg call:
    public_key.verify(sig_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())
This differs from the Ed25519 2-arg pattern in signature_service.py.
"""

import base64
import logging

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Node, RevokedCert

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants — callers compare against these, not raw strings
# ---------------------------------------------------------------------------

ATTESTATION_VERIFIED = "verified"
ATTESTATION_FAILED = "failed"
ATTESTATION_MISSING = "missing"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def verify_bundle(
    node_id: str,
    bundle_b64: str | None,
    signature_b64: str | None,
    db: AsyncSession,
) -> str:
    """Verify a node's RSA-signed attestation bundle.

    Args:
        node_id:       The reporting node's ID (used to look up its cert).
        bundle_b64:    Base64-encoded canonical JSON attestation bundle.
        signature_b64: Base64-encoded RSA-PKCS1v15/SHA256 signature over the bundle.
        db:            Async SQLAlchemy session for DB lookups.

    Returns:
        ATTESTATION_VERIFIED  — signature valid and cert not revoked
        ATTESTATION_FAILED    — node unknown, cert revoked, or bad signature
        ATTESTATION_MISSING   — bundle or signature argument is falsy (old node)

    Never raises an exception.
    """
    # --- Guard: missing data means the node didn't send attestation info ------
    if not bundle_b64 or not signature_b64:
        return ATTESTATION_MISSING

    try:
        # --- Fetch node and its stored client cert PEM -----------------------
        node_result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = node_result.scalar_one_or_none()

        if node is None or not node.client_cert_pem:
            logger.warning(
                "attestation: node %s not found or has no client_cert_pem", node_id
            )
            return ATTESTATION_FAILED

        # --- Load certificate and extract serial + public key ----------------
        cert = x509.load_pem_x509_certificate(node.client_cert_pem.encode())
        cert_serial = str(cert.serial_number)

        # --- Revocation check ------------------------------------------------
        rev_result = await db.execute(
            select(RevokedCert).where(RevokedCert.serial_number == cert_serial)
        )
        if rev_result.scalar_one_or_none():
            logger.warning(
                "attestation: cert serial %s for node %s is revoked", cert_serial, node_id
            )
            return ATTESTATION_FAILED

        # --- Decode base64 inputs --------------------------------------------
        bundle_bytes = base64.b64decode(bundle_b64)
        sig_bytes = base64.b64decode(signature_b64)

        # --- RSA verify — 4-arg call (NOT the 2-arg Ed25519 pattern) ---------
        public_key = cert.public_key()
        public_key.verify(sig_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())

        return ATTESTATION_VERIFIED

    except InvalidSignature:
        logger.warning("attestation: invalid signature for node %s", node_id)
        return ATTESTATION_FAILED
    except Exception as exc:  # noqa: BLE001
        logger.error("attestation: unexpected error verifying bundle for node %s: %s", node_id, exc)
        return ATTESTATION_FAILED

import logging
import os
import uuid
import base64
from typing import List, Optional
from sqlalchemy.future import select
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..db import Signature, AsyncSession, User
from ..models import SignatureCreate, SignatureResponse

logger = logging.getLogger(__name__)

# Node-facing verification key paths (nodes download from GET /verification-key)
_VERIFICATION_KEY_PATHS = ["/app/secrets/verification.key", "secrets/verification.key"]

class SignatureService:
    @staticmethod
    async def upload_signature(sig_req: SignatureCreate, current_user: User, db: AsyncSession) -> SignatureResponse:
        """Stores a new Code Signing Public Key in the registry."""
        # Check Duplicate
        res = await db.execute(select(Signature).where(Signature.name == sig_req.name))
        if res.scalar_one_or_none():
             from fastapi import HTTPException
             raise HTTPException(status_code=400, detail="Signature name exists")
        
        new_sig = Signature(
            id=uuid.uuid4().hex,
            name=sig_req.name,
            public_key=sig_req.public_key,
            uploaded_by=current_user.username
        )
        db.add(new_sig)
        await db.commit()
        await db.refresh(new_sig)

        # NOTE: Do NOT update the node-facing verification key.
        # The verification.key should always be the SERVER's public key (for verifying
        # server-signed job scripts), not the registered signatures' public keys.
        # Jobs are signed server-side with the server's private key, and nodes verify
        # with the server's public key (fetched from GET /verification-key).
        # The signature registry is for storing user-submitted signatures (for audit/registration),
        # but the actual job script verification always uses the server's key pair.

        return new_sig

    @staticmethod
    async def list_signatures(db: AsyncSession) -> List[Signature]:
        """Lists all registered signatures."""
        result = await db.execute(select(Signature))
        return result.scalars().all()

    @staticmethod
    async def delete_signature(sig_id: str, db: AsyncSession) -> bool:
        """Removes a signature from the registry."""
        result = await db.execute(select(Signature).where(Signature.id == sig_id))
        sig = result.scalar_one_or_none()
        if not sig:
            return False
        
        await db.delete(sig)
        await db.commit()
        return True

    @staticmethod
    def verify_payload_signature(public_key_pem: str, signature_b64: str, payload: str) -> bool:
        """
        Validates an Ed25519 signature against a payload using the provided PEM public key.
        Returns True if valid, raises Exception otherwise.
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                 raise ValueError("Only Ed25519 signatures are currently supported for notary validation")

            sig_bytes = base64.b64decode(signature_b64)
            public_key.verify(sig_bytes, payload.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Signature Verification Failed: {e}")
            raise e

    @staticmethod
    def countersign_for_node(script_content: str) -> str:
        """
        Server-signs a job script with the Ed25519 private key.
        Returns base64-encoded signature ready for inclusion in job payload.

        Normalizes CRLF to LF before signing (WIN-05 pattern) for cross-platform compatibility.

        Args:
            script_content: The job script to sign

        Returns:
            Base64-encoded signature string

        Raises:
            FileNotFoundError: If signing.key is absent or inaccessible
            RuntimeError: If key file is corrupted or signing fails
        """
        # Try production path first, fall back to dev path
        _signing_key_path = "/app/secrets/signing.key"
        if not os.path.exists(_signing_key_path):
            _signing_key_path = "secrets/signing.key"

        # Hard fail if key doesn't exist
        if not os.path.exists(_signing_key_path):
            raise FileNotFoundError("Server signing key unavailable (signing.key not found)")

        try:
            # Normalize CRLF to LF (WIN-05 pattern) before signing
            normalized_script = script_content.replace('\r\n', '\n').replace('\r', '\n')

            with open(_signing_key_path, "rb") as f:
                sk = serialization.load_pem_private_key(f.read(), password=None)

            sig_bytes = sk.sign(normalized_script.encode("utf-8"))
            return base64.b64encode(sig_bytes).decode("ascii")
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Server countersigning failed: {e}") from e

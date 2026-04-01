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

        # Propagate the registered public key to the node-facing verification
        # key file so that GET /verification-key serves it and nodes download
        # it on their next poll cycle.
        for key_path in _VERIFICATION_KEY_PATHS:
            parent = os.path.dirname(key_path)
            if os.path.isdir(parent):
                try:
                    with open(key_path, "w") as f:
                        f.write(sig_req.public_key)
                    logger.info(f"Updated node-facing verification key at {key_path}")
                except OSError as e:
                    logger.warning(f"Could not update verification key at {key_path}: {e}")
                break

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

import os
import uuid
import hashlib
import logging
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import Artifact

logger = logging.getLogger(__name__)

VAULT_DIR = "/app/vault"

class VaultService:
    @staticmethod
    async def store_artifact(file: UploadFile, db: AsyncSession) -> Artifact:
        """Stores a file in the vault and returns the DB record."""
        artifact_id = str(uuid.uuid4())
        os.makedirs(VAULT_DIR, exist_ok=True)
        file_path = os.path.join(VAULT_DIR, artifact_id)
        
        sha256_hash = hashlib.sha256()
        size_bytes = 0
        
        try:
            with open(file_path, "wb") as f:
                while content := await file.read(1024 * 1024):  # 1MB chunks
                    size_bytes += len(content)
                    sha256_hash.update(content)
                    f.write(content)
            
            artifact = Artifact(
                id=artifact_id,
                filename=file.filename,
                content_type=file.content_type,
                sha256=sha256_hash.hexdigest(),
                size_bytes=size_bytes
            )
            db.add(artifact)
            await db.commit()
            await db.refresh(artifact)
            logger.info(f"✅ Stored artifact {artifact.filename} ({artifact_id})")
            return artifact
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"❌ Failed to store artifact: {e}")
            raise e

    @staticmethod
    def get_artifact_path(artifact_id: str) -> str:
        """Returns the absolute path to an artifact on disk."""
        return os.path.join(VAULT_DIR, artifact_id)

    @staticmethod
    async def list_artifacts(db: AsyncSession) -> List[Artifact]:
        """Returns all artifacts from DB."""
        result = await db.execute(select(Artifact).order_by(Artifact.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def delete_artifact(artifact_id: str, db: AsyncSession) -> bool:
        """Removes artifact from disk and DB."""
        result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
        artifact = result.scalar_one_or_none()
        if not artifact:
            return False
        
        file_path = VaultService.get_artifact_path(artifact_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await db.delete(artifact)
        await db.commit()
        logger.info(f"🗑️ Deleted artifact {artifact_id}")
        return True

vault_service = VaultService()

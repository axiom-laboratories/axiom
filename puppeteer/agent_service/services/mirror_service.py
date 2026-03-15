import logging
import asyncio
import os
import subprocess
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import ApprovedIngredient, AsyncSessionLocal

logger = logging.getLogger(__name__)

class MirrorService:
    MIRROR_BASE_PATH = os.getenv("MIRROR_DATA_PATH", "/app/mirror_data")
    PYPI_PATH = os.path.join(MIRROR_BASE_PATH, "pypi")
    APT_PATH = os.path.join(MIRROR_BASE_PATH, "apt")

    @staticmethod
    async def mirror_ingredient(ingredient_id: str):
        """
        Background task to mirror an ingredient.
        Creates its own DB session to avoid lifecycle issues.
        """
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id))
            ingredient = res.scalar_one_or_none()
            if not ingredient:
                logger.error(f"Mirror: Ingredient {ingredient_id} not found")
                return

            logger.info(f"Mirror: Processing {ingredient.name} ({ingredient.os_family})")
            
            try:
                if ingredient.os_family in ["DEBIAN", "ALPINE", "FEDORA"]:
                    # Python packages for these OS families
                    await MirrorService._mirror_pypi(db, ingredient)
                
                # If we had native APT packages, we'd call _mirror_apt here.
                # For now, we focus on the requirement PKG-01 (PIP) and REPO-01 (Sidecar setup).
                
                ingredient.mirror_status = "MIRRORED"
                await db.commit()
                logger.info(f"Mirror: Successfully mirrored {ingredient.name}")
            except Exception as e:
                logger.error(f"Mirror: Failed to mirror {ingredient.name}: {str(e)}")
                ingredient.mirror_status = "FAILED"
                if not ingredient.mirror_log:
                    ingredient.mirror_log = str(e)
                await db.commit()

    @staticmethod
    async def _mirror_pypi(db: AsyncSession, ingredient: ApprovedIngredient):
        """Downloads a Python package to the local pypi directory."""
        os.makedirs(MirrorService.PYPI_PATH, exist_ok=True)
        
        # Construct requirement string
        req = ingredient.name
        if ingredient.version_constraint:
            req += ingredient.version_constraint

        # Use pip download to fetch the wheel/sdist
        # --platform manylinux2014_x86_64 ensures we get binary wheels when possible
        cmd = [
            "pip", "download",
            "--dest", MirrorService.PYPI_PATH,
            "--no-deps",
            "--platform", "manylinux2014_x86_64",
            "--only-binary=:all:",
            req
        ]
        
        process = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True
        )

        # Capture combined subprocess output into mirror_log
        ingredient.mirror_log = f"[stdout]\n{process.stdout}\n[stderr]\n{process.stderr}"

        if process.returncode != 0:
            raise Exception(f"pip download failed: {process.stderr}")

        # Find the downloaded file to set mirror_path
        # Usually the last file created or matching the package name
        # For simplicity in this iteration, we just set the directory
        ingredient.mirror_path = MirrorService.PYPI_PATH

    @staticmethod
    async def _mirror_apt(db: AsyncSession, ingredient: ApprovedIngredient):
        """
        Placeholder for native .deb mirroring.
        In a real scenario, this would use 'apt-get download' and 'dpkg-scanpackages'.
        """
        os.makedirs(MirrorService.APT_PATH, exist_ok=True)
        # TODO: Implement native APT mirroring if needed
        pass

    @staticmethod
    def get_pip_conf_content() -> str:
        """Returns the content for a pip.conf file pointing to the local mirror."""
        url = os.getenv("PYPI_MIRROR_URL", "http://pypi:8080/simple")
        host = url.split("//")[-1].split(":")[0].split("/")[0]
        return f"[global]\nindex-url = {url}\ntrusted-host = {host}\n"

    @staticmethod
    def get_sources_list_content() -> str:
        """Returns the content for a sources.list file pointing to the local mirror."""
        url = os.getenv("APT_MIRROR_URL", "http://mirror/apt")
        return f"deb [trusted=yes] {url} stable main\n"

    @staticmethod
    def get_smelter_gpg_key() -> str:
        """Returns the Smelter GPG public key content (stub for now)."""
        return "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----\n"

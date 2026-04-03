import logging
import asyncio
import os
import subprocess
import hashlib
import json
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import ApprovedIngredient, AsyncSessionLocal, IngredientDependency

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
    async def _mirror_pypi(db: AsyncSession, ingredient: ApprovedIngredient) -> bool:
        """
        Download wheels for ingredient across multiple platforms.
        For pure-python wheels, download once. For C-extensions, download manylinux and musllinux variants.
        If musllinux missing, fall back to sdist.
        Updates ingredient.mirror_status and mirror_log.
        """
        try:
            os.makedirs(MirrorService.PYPI_PATH, exist_ok=True)

            req = f"{ingredient.name}{ingredient.version_constraint or ''}"
            log_lines = []

            # 1. Check for pure-python wheel (py3-none-any)
            log_lines.append(f"Checking for pure-python wheel: {req}")
            result_any = await MirrorService._download_wheel(
                req,
                "py3-none-any",  # Pure-python tag
                MirrorService.PYPI_PATH
            )

            if result_any["found"]:
                log_lines.append(f"Pure-python wheel found: {result_any['filename']}")
                ingredient.mirror_path = MirrorService.PYPI_PATH
                ingredient.mirror_status = "MIRRORED"
                ingredient.mirror_log = "\n".join(log_lines)
                await db.commit()
                return True

            log_lines.append("No pure-python wheel found, checking platform variants...")

            # 2. Download manylinux2014 (Debian)
            log_lines.append(f"Downloading for manylinux2014_x86_64...")
            result_manylinux = await MirrorService._download_wheel(
                req,
                "manylinux2014_x86_64",
                MirrorService.PYPI_PATH
            )

            if result_manylinux["found"]:
                log_lines.append(f"manylinux wheel: {result_manylinux['filename']}")
            else:
                log_lines.append("No manylinux2014 wheel found")

            # 3. Download musllinux (Alpine)
            log_lines.append(f"Downloading for musllinux_1_1_x86_64...")
            result_musllinux = await MirrorService._download_wheel(
                req,
                "musllinux_1_1_x86_64",
                MirrorService.PYPI_PATH
            )

            if result_musllinux["found"]:
                log_lines.append(f"musllinux wheel: {result_musllinux['filename']}")
            else:
                log_lines.append("No musllinux wheel found, attempting sdist fallback...")

                # 4. Fallback to sdist if musllinux missing
                result_sdist = await MirrorService._download_wheel(
                    req,
                    "sdist",
                    MirrorService.PYPI_PATH
                )

                if result_sdist["found"]:
                    log_lines.append(f"sdist fallback: {result_sdist['filename']}")
                else:
                    log_lines.append("ERROR: No sdist available either")
                    ingredient.mirror_status = "FAILED"
                    ingredient.mirror_log = "\n".join(log_lines)
                    await db.commit()
                    return False

            # Success: at least one platform variant available
            ingredient.mirror_path = MirrorService.PYPI_PATH
            ingredient.mirror_status = "MIRRORED"
            ingredient.mirror_log = "\n".join(log_lines)
            await db.commit()
            return True

        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = f"Mirror error: {str(e)}"
            await db.commit()
            return False

    @staticmethod
    async def _download_wheel(
        requirement: str,
        platform_tag: str,
        dest_dir: str
    ) -> Dict[str, Any]:
        """
        Download wheel for specific platform or sdist.
        Returns {found: bool, filename: str}.
        """
        try:
            if platform_tag == "sdist":
                # Download source distribution
                cmd = [
                    "pip", "download",
                    "--dest", dest_dir,
                    "--no-binary", ":all:",  # Source only
                    "--no-deps",
                    requirement
                ]
            else:
                # Download binary wheel for platform
                cmd = [
                    "pip", "download",
                    "--dest", dest_dir,
                    "--platform", platform_tag,
                    "--only-binary", ":all:",  # Binary only
                    "--no-deps",
                    requirement
                ]

            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                # Extract filename from dest_dir listing
                files = os.listdir(dest_dir)
                # Find newest file matching requirement name
                pkg_name = requirement.split('==')[0].split('>')[0].split('<')[0].split('!')[0].strip()
                matching = [f for f in files if f.startswith(pkg_name)]

                if matching:
                    return {"found": True, "filename": matching[-1]}

            return {"found": False, "filename": None}

        except Exception as e:
            logger.debug(f"Download failed for {requirement} ({platform_tag}): {str(e)}")
            return {"found": False, "filename": None}

    @staticmethod
    async def mirror_ingredient_and_dependencies(
        db: AsyncSession,
        ingredient_id: str
    ) -> None:
        """
        Auto-mirror an ingredient and all its transitive dependencies.
        Called after resolution completes.
        Background task (not awaited by caller).
        """
        ingredient = await db.get(ApprovedIngredient, ingredient_id)
        if not ingredient:
            return

        # Update status to MIRRORING
        ingredient.mirror_status = "MIRRORING"
        await db.commit()

        try:
            # Mirror parent
            await MirrorService._mirror_pypi(db, ingredient)

            # Find all direct transitive dependencies
            stmt = select(IngredientDependency).where(
                IngredientDependency.parent_id == ingredient_id
            )
            result = await db.execute(stmt)
            edges = result.scalars().all()

            # Mirror each dependency
            for edge in edges:
                child = await db.get(ApprovedIngredient, edge.child_id)
                if child and child.mirror_status in ["PENDING", "RESOLVING"]:
                    await MirrorService._mirror_pypi(db, child)

        except Exception as e:
            ingredient.mirror_log = f"Error mirroring dependencies: {str(e)}"
            await db.commit()

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

import logging
import asyncio
import os
import subprocess
import hashlib
import json
import gzip
import re
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import ApprovedIngredient, AsyncSessionLocal, IngredientDependency

logger = logging.getLogger(__name__)

class MirrorService:
    MIRROR_BASE_PATH = os.getenv("MIRROR_DATA_PATH", "/app/mirror_data")
    PYPI_PATH = os.path.join(MIRROR_BASE_PATH, "pypi")
    APT_PATH = os.path.join(MIRROR_BASE_PATH, "apt")
    APK_BASE_PATH = os.path.join(MIRROR_BASE_PATH, "apk")
    NPM_PATH = os.path.join(MIRROR_BASE_PATH, "npm")
    NUGET_PATH = os.path.join(MIRROR_BASE_PATH, "nuget")
    CONDA_BASE_PATH = os.path.join(MIRROR_BASE_PATH, "conda")

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
            # Mirror parent — dispatch based on ecosystem
            if ingredient.ecosystem == "NPM":
                await MirrorService._mirror_npm(db, ingredient)
            elif ingredient.ecosystem == "NUGET":
                await MirrorService._mirror_nuget(db, ingredient)
            elif ingredient.ecosystem == "APT":
                await MirrorService._mirror_apt(db, ingredient)
            elif ingredient.ecosystem == "APK":
                await MirrorService._mirror_apk(db, ingredient)
            elif ingredient.ecosystem == "CONDA":
                await MirrorService._mirror_conda(db, ingredient)
            else:  # Default to PYPI for backward compatibility
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
                    # Dispatch each child based on its ecosystem
                    if child.ecosystem == "NPM":
                        await MirrorService._mirror_npm(db, child)
                    elif child.ecosystem == "NUGET":
                        await MirrorService._mirror_nuget(db, child)
                    elif child.ecosystem == "APT":
                        await MirrorService._mirror_apt(db, child)
                    elif child.ecosystem == "APK":
                        await MirrorService._mirror_apk(db, child)
                    elif child.ecosystem == "CONDA":
                        await MirrorService._mirror_conda(db, child)
                    else:  # Default to PYPI
                        await MirrorService._mirror_pypi(db, child)

        except Exception as e:
            ingredient.mirror_log = f"Error mirroring dependencies: {str(e)}"
            await db.commit()

    @staticmethod
    async def _mirror_apt(db: AsyncSession, ingredient: ApprovedIngredient):
        """
        Download a .deb package using apt-get inside a throwaway Debian container.
        Uses asyncio.to_thread for subprocess execution.
        Updates ingredient.mirror_status and mirror_log on success/failure.
        """
        try:
            os.makedirs(MirrorService.APT_PATH, exist_ok=True)

            # Parse version constraint: "==1.0.0" -> "1.0.0", ">=2.0" -> "2.0", etc.
            pkg_spec = ingredient.name
            if ingredient.version_constraint:
                # Remove comparison operators: ==, >=, <=, >, <, ~=
                version = re.sub(r'^[><=~!]+', '', ingredient.version_constraint).strip()
                if version:
                    pkg_spec = f"{ingredient.name}={version}"

            # Run apt-get download inside a throwaway Debian container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{MirrorService.APT_PATH}:/mirror",
                "debian:12-slim",
                "bash", "-c",
                f"apt-get update && apt-get download -o=/mirror {pkg_spec}"
            ]

            logger.info(f"Mirror: Running apt-get for {pkg_spec}")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                # Regenerate APT index
                await MirrorService._regenerate_apt_index(MirrorService.APT_PATH)
                ingredient.mirror_status = "MIRRORED"
                ingredient.mirror_log = f"Downloaded {pkg_spec}; regenerated Packages.gz"
                logger.info(f"Mirror: Successfully mirrored APT package {pkg_spec}")
            else:
                ingredient.mirror_status = "FAILED"
                ingredient.mirror_log = process.stderr or process.stdout
                logger.error(f"Mirror: APT download failed for {pkg_spec}: {process.stderr}")

            await db.commit()

        except asyncio.TimeoutError:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = f"APT download timeout after 120s"
            await db.commit()
            logger.error(f"Mirror: Timeout downloading APT package {ingredient.name}")
        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = str(e)
            await db.commit()
            logger.error(f"Mirror: Error mirroring APT package {ingredient.name}: {str(e)}")

    @staticmethod
    async def _regenerate_apt_index(apt_dir: str):
        """
        Regenerate Packages.gz index for the APT repository.
        Runs dpkg-scanpackages inside a throwaway Debian container and gzips output.
        """
        try:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{apt_dir}:/mirror",
                "debian:12-slim",
                "bash", "-c",
                "cd /mirror && dpkg-scanpackages --multiversion . /dev/null > Packages && gzip -9 -c Packages > Packages.gz"
            ]

            logger.info(f"Mirror: Regenerating APT Packages.gz index")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                logger.info("Mirror: APT Packages.gz index regenerated successfully")
            else:
                logger.error(f"Mirror: Failed to regenerate APT index: {process.stderr}")

        except Exception as e:
            logger.error(f"Mirror: Error regenerating APT index: {str(e)}")

    @staticmethod
    async def _mirror_apk(db: AsyncSession, ingredient: ApprovedIngredient):
        """
        Download an .apk package using apk fetch inside a throwaway Alpine container.
        Uses asyncio.to_thread for subprocess execution.
        Updates ingredient.mirror_status and mirror_log on success/failure.
        """
        try:
            # Extract Alpine version from base_os or use default
            alpine_version = MirrorService._get_alpine_version(ingredient.base_os if hasattr(ingredient, 'base_os') else None)
            apk_dir = os.path.join(MirrorService.APK_BASE_PATH, alpine_version, "main")
            os.makedirs(apk_dir, exist_ok=True)

            # Parse version constraint: "==1.0.0" -> "package=1.0.0"
            pkg_spec = ingredient.name
            if ingredient.version_constraint:
                version = re.sub(r'^[><=~!]+', '', ingredient.version_constraint).strip()
                if version:
                    pkg_spec = f"{ingredient.name}={version}"

            # Run apk fetch inside a throwaway Alpine container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{apk_dir}:/mirror",
                "alpine:3.20",
                "sh", "-c",
                f"apk fetch -o /mirror {pkg_spec}"
            ]

            logger.info(f"Mirror: Running apk fetch for {pkg_spec} (Alpine {alpine_version})")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                # Regenerate APK index
                await MirrorService._regenerate_apk_index(apk_dir)
                ingredient.mirror_status = "MIRRORED"
                ingredient.mirror_log = f"Downloaded {pkg_spec}; regenerated APKINDEX.tar.gz"
                logger.info(f"Mirror: Successfully mirrored APK package {pkg_spec}")
            else:
                ingredient.mirror_status = "FAILED"
                ingredient.mirror_log = process.stderr or process.stdout
                logger.error(f"Mirror: APK fetch failed for {pkg_spec}: {process.stderr}")

            await db.commit()

        except asyncio.TimeoutError:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = "APK fetch timeout after 120s"
            await db.commit()
            logger.error(f"Mirror: Timeout downloading APK package {ingredient.name}")
        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = str(e)
            await db.commit()
            logger.error(f"Mirror: Error mirroring APK package {ingredient.name}: {str(e)}")

    @staticmethod
    async def _regenerate_apk_index(apk_dir: str):
        """
        Regenerate APKINDEX.tar.gz index for the APK repository.
        Runs apk index inside a throwaway Alpine container.
        """
        try:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{apk_dir}:/mirror",
                "alpine:3.20",
                "sh", "-c",
                "cd /mirror && apk index -o APKINDEX.tar.gz *.apk 2>/dev/null || apk index -d /mirror APKINDEX.tar.gz"
            ]

            logger.info(f"Mirror: Regenerating APK APKINDEX.tar.gz")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                logger.info("Mirror: APK APKINDEX.tar.gz regenerated successfully")
            else:
                logger.error(f"Mirror: Failed to regenerate APK index: {process.stderr}")

        except Exception as e:
            logger.error(f"Mirror: Error regenerating APK index: {str(e)}")

    @staticmethod
    def _get_alpine_version(base_os: str = None) -> str:
        """
        Parse Alpine version from base_os image tag (e.g., 'alpine:3.20' -> 'v3.20').
        Falls back to DEFAULT_ALPINE_VERSION env var (default 'v3.20').
        """
        if base_os:
            # Extract version from tags like "alpine:3.20", "alpine:3.18", "alpine:latest"
            match = re.search(r'alpine:(\d+\.\d+|\w+)', base_os, re.IGNORECASE)
            if match:
                version = match.group(1)
                if version == "latest" or not version[0].isdigit():
                    return os.getenv("DEFAULT_ALPINE_VERSION", "v3.20")
                # Convert "3.20" to "v3.20"
                return f"v{version}"
        return os.getenv("DEFAULT_ALPINE_VERSION", "v3.20")

    @staticmethod
    def get_apk_repos_content(base_os: str = None) -> str:
        """
        Generate /etc/apk/repositories file content pointing to the local APK mirror.
        Parses Alpine version from base_os and constructs mirror URLs.
        """
        alpine_version = MirrorService._get_alpine_version(base_os)
        url = os.getenv("APK_MIRROR_URL", "http://mirror:8081/apk")
        return f"{url}/{alpine_version}/main\n{url}/{alpine_version}/community\n"

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

    @staticmethod
    async def _mirror_npm(db: AsyncSession, ingredient: ApprovedIngredient) -> None:
        """
        Download an npm package using npm pack inside a throwaway Node.js container.
        Uses asyncio.to_thread for subprocess execution.
        Updates ingredient.mirror_status and mirror_log on success/failure.
        """
        try:
            os.makedirs(MirrorService.NPM_PATH, exist_ok=True)

            # Parse version constraint: "lodash@4.17.21", "lodash@latest", "lodash@next"
            # Accept {name}@{version} format or just version constraint
            pkg_spec = ingredient.name
            if ingredient.version_constraint:
                # Remove leading @ if present, then add it back
                version = ingredient.version_constraint.lstrip('@')
                if version:
                    pkg_spec = f"{ingredient.name}@{version}"

            # Run npm pack inside a throwaway node:latest container
            # npm pack downloads tarball and saves it to current directory
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{MirrorService.NPM_PATH}:/mirror",
                "node:latest",
                "bash", "-c",
                f"npm pack {pkg_spec} -C /mirror"
            ]

            logger.info(f"Mirror: Running npm pack for {pkg_spec}")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                # Extract tarball filename from stdout
                # npm pack outputs the filename as last line
                output_lines = process.stdout.strip().split('\n')
                tarball_name = output_lines[-1] if output_lines else None

                if tarball_name:
                    # Verify tarball was created
                    tarball_path = os.path.join(MirrorService.NPM_PATH, tarball_name)
                    if os.path.exists(tarball_path):
                        ingredient.mirror_status = "MIRRORED"
                        ingredient.mirror_path = MirrorService.NPM_PATH
                        ingredient.mirror_log = f"Downloaded {pkg_spec}; saved as {tarball_name}"
                        logger.info(f"Mirror: Successfully mirrored npm package {pkg_spec} -> {tarball_name}")
                    else:
                        ingredient.mirror_status = "FAILED"
                        ingredient.mirror_log = f"Tarball not found after npm pack: {tarball_name}"
                        logger.error(f"Mirror: npm pack reported success but tarball missing: {tarball_name}")
                else:
                    ingredient.mirror_status = "FAILED"
                    ingredient.mirror_log = "npm pack succeeded but no filename in output"
                    logger.error(f"Mirror: npm pack succeeded but no output for {pkg_spec}")
            else:
                ingredient.mirror_status = "FAILED"
                ingredient.mirror_log = process.stderr or process.stdout or "npm pack failed with unknown error"
                logger.error(f"Mirror: npm pack failed for {pkg_spec}: {process.stderr}")

            await db.commit()

        except asyncio.TimeoutError:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = "npm pack timeout after 120s"
            await db.commit()
            logger.error(f"Mirror: Timeout downloading npm package {ingredient.name}")
        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = str(e)
            await db.commit()
            logger.error(f"Mirror: Error mirroring npm package {ingredient.name}: {str(e)}")

    @staticmethod
    def get_npmrc_content() -> str:
        """
        Returns the content for a .npmrc file pointing to the local npm mirror (Verdaccio).
        Format suitable for injection into Dockerfile.
        """
        url = os.getenv("NPM_MIRROR_URL", "http://verdaccio:4873")
        return f"registry={url}\n"

    @staticmethod
    async def _mirror_nuget(db: AsyncSession, ingredient: ApprovedIngredient) -> None:
        """
        Download a NuGet package using nuget install inside a throwaway dotnet/sdk container.
        Uses asyncio.to_thread for subprocess execution.
        Updates ingredient.mirror_status and mirror_log on success/failure.
        """
        try:
            # Create NUGET directory structure: mirror_data/nuget/{name}/{version}/
            pkg_dir = os.path.join(MirrorService.NUGET_PATH, ingredient.name, ingredient.version_constraint or "latest")
            os.makedirs(pkg_dir, exist_ok=True)

            # Parse version constraint: "13.0.1", "latest", "pre-release", etc.
            # Version can be: "13.0.1", "13.0.1-beta", "latest", etc.
            version_spec = ingredient.version_constraint or "latest"

            # Run nuget install inside a throwaway dotnet/sdk container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{pkg_dir}:/mirror",
                "mcr.microsoft.com/dotnet/sdk:latest",
                "bash", "-c",
                f"nuget install {ingredient.name} -Version {version_spec} -NoCache -OutputDirectory /mirror"
            ]

            logger.info(f"Mirror: Running nuget install for {ingredient.name}@{version_spec}")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=180
            )

            if process.returncode == 0:
                # Verify .nupkg file was created
                # nuget install creates: /mirror/{PackageName}/{Version}/{PackageName}.{Version}.nupkg
                expected_nupkg = os.path.join(pkg_dir, ingredient.name, version_spec, f"{ingredient.name}.{version_spec}.nupkg")

                # Check if file exists (may be in subdirectories or directly in pkg_dir)
                nupkg_found = False
                for root, dirs, files in os.walk(pkg_dir):
                    for file in files:
                        if file.endswith(".nupkg"):
                            nupkg_found = True
                            nupkg_path = os.path.join(root, file)
                            ingredient.mirror_status = "MIRRORED"
                            ingredient.mirror_path = pkg_dir
                            ingredient.mirror_log = f"Downloaded {ingredient.name}@{version_spec}; saved as {file}"
                            logger.info(f"Mirror: Successfully mirrored NuGet package {ingredient.name}@{version_spec} -> {file}")
                            break
                    if nupkg_found:
                        break

                if not nupkg_found:
                    ingredient.mirror_status = "FAILED"
                    ingredient.mirror_log = f"nuget install succeeded but no .nupkg file found in {pkg_dir}"
                    logger.error(f"Mirror: nuget install reported success but .nupkg missing for {ingredient.name}")
            else:
                ingredient.mirror_status = "FAILED"
                ingredient.mirror_log = process.stderr or process.stdout or "nuget install failed with unknown error"
                logger.error(f"Mirror: nuget install failed for {ingredient.name}@{version_spec}: {process.stderr}")

            await db.commit()

        except asyncio.TimeoutError:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = "nuget install timeout after 180s"
            await db.commit()
            logger.error(f"Mirror: Timeout downloading NuGet package {ingredient.name}")
        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = str(e)
            await db.commit()
            logger.error(f"Mirror: Error mirroring NuGet package {ingredient.name}: {str(e)}")

    @staticmethod
    def get_nuget_config_content() -> str:
        """
        Returns nuget.config XML format pointing to the local NuGet mirror (BaGetter).
        Suitable for injection into Dockerfile.
        """
        url = os.getenv("NUGET_MIRROR_URL", "http://bagetter:5555/v3/index.json")
        return f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="bagetter" value="{url}" />
  </packageSources>
  <packageSourceCredentials>
    <!-- Optional: auth can be added here in Phase 112 -->
  </packageSourceCredentials>
</configuration>
"""

    @staticmethod
    def get_condarc_content(blueprint_ingredients: list = None) -> str:
        """
        Returns .condarc YAML format pointing to local Conda mirrors.
        Takes optional list of ApprovedIngredient records to determine channels.
        If blueprint_ingredients is empty or None, returns empty string (no CONDA packages).
        Channels are deduplicated while preserving order, with conda-forge prioritized.
        Suitable for injection into Dockerfile.
        """
        if not blueprint_ingredients:
            return ""

        # Extract unique channels from ingredients, preserving order
        channels = []
        seen = set()

        # Prioritize conda-forge
        for ing in blueprint_ingredients:
            channel = ing.mirror_path if ing.mirror_path else "conda-forge"
            if channel not in seen:
                channels.append(channel)
                seen.add(channel)

        # Reorder to put conda-forge first if present
        if "conda-forge" in channels:
            channels.remove("conda-forge")
            channels.insert(0, "conda-forge")

        if not channels:
            return ""

        # Build YAML content
        yaml_content = "channels:\n"
        for channel in channels:
            yaml_content += f"  - {channel}\n"
        yaml_content += "ssl_verify: true\n"

        return yaml_content

    @staticmethod
    def get_oci_mirror_prefix(base_image: str) -> str:
        """
        Determines if base_image is Docker Hub or GHCR and returns appropriate cache prefix.
        Rewrites base_image reference for pull-through caching.

        Logic:
        - If base_image starts with "ghcr.io/": return rewritten with "oci-cache-ghcr:5002"
        - If base_image is unqualified (e.g., "node", "python"): Docker Hub convention, use "oci-cache:5001"
        - Otherwise: assume Docker Hub registry, use "oci-cache:5001"

        Examples:
        - "node:18" → "oci-cache:5001/library/node:18"
        - "alpine:3.20" → "oci-cache:5001/library/alpine:3.20"
        - "ghcr.io/owner/image:latest" → "oci-cache-ghcr:5002/owner/image:latest"
        """
        if base_image.startswith("ghcr.io/"):
            # GHCR: strip "ghcr.io/" and prepend cache prefix
            image_path = base_image[len("ghcr.io/"):]  # "owner/image:latest"
            return f"oci-cache-ghcr:5002/{image_path}"
        elif "/" in base_image:
            # Registry-qualified but not GHCR: assume Docker Hub organization
            return f"oci-cache:5001/{base_image}"
        else:
            # Unqualified (e.g., "node:18", "alpine:3.20"): Docker Hub library
            return f"oci-cache:5001/library/{base_image}"

    @staticmethod
    async def _mirror_conda(db: AsyncSession, ingredient: ApprovedIngredient) -> None:
        """
        Download a Conda package using conda create --download-only inside a throwaway miniconda container.
        Uses asyncio.to_thread for subprocess execution.
        Updates ingredient.mirror_status and mirror_log on success/failure.
        Regenerates repodata.json index after download.
        """
        try:
            # Extract channel from mirror_path (e.g., "conda-forge", "defaults", or custom URL)
            channel = ingredient.mirror_path if ingredient.mirror_path else "conda-forge"

            # Build conda directory structure: mirror_data/conda/{channel}/{platform}/
            conda_dir = os.path.join(MirrorService.CONDA_BASE_PATH, channel)
            os.makedirs(conda_dir, exist_ok=True)

            # Parse version constraint: "==X.Y.Z" -> "X.Y.Z"
            pkg_spec = ingredient.name
            if ingredient.version_constraint:
                version = re.sub(r'^[><=~!]+', '', ingredient.version_constraint).strip()
                if version:
                    pkg_spec = f"{ingredient.name}=={version}"

            # Run conda create --download-only inside a throwaway miniconda container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{conda_dir}:/mirror",
                "miniconda:latest",
                "bash", "-c",
                f"conda create --download-only -c {channel} -p /tmp/conda-env {pkg_spec} && cp -r /opt/conda/pkgs/* /mirror/ 2>/dev/null || true"
            ]

            logger.info(f"Mirror: Running conda create --download-only for {pkg_spec} from {channel}")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                # Regenerate conda index (repodata.json)
                await MirrorService._regenerate_conda_index(conda_dir)
                ingredient.mirror_status = "MIRRORED"
                ingredient.mirror_log = f"Downloaded {pkg_spec} from {channel}; regenerated repodata.json"
                ingredient.mirror_path = conda_dir
                logger.info(f"Mirror: Successfully mirrored Conda package {pkg_spec} from {channel}")
            else:
                ingredient.mirror_status = "FAILED"
                ingredient.mirror_log = process.stderr or process.stdout
                logger.error(f"Mirror: Conda create failed for {pkg_spec}: {process.stderr}")

            await db.commit()

        except asyncio.TimeoutError:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = "Conda create timeout after 120s"
            await db.commit()
            logger.error(f"Mirror: Timeout downloading Conda package {ingredient.name}")
        except Exception as e:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = str(e)
            await db.commit()
            logger.error(f"Mirror: Error mirroring Conda package {ingredient.name}: {str(e)}")

    @staticmethod
    async def _regenerate_conda_index(conda_dir: str):
        """
        Regenerate repodata.json index for the Conda repository.
        Runs conda index inside a throwaway miniconda container.
        """
        try:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{conda_dir}:/mirror",
                "miniconda:latest",
                "bash", "-c",
                "cd /mirror && conda index . 2>/dev/null || true"
            ]

            logger.info(f"Mirror: Regenerating Conda repodata.json index")
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if process.returncode == 0:
                logger.info("Mirror: Conda repodata.json index regenerated successfully")
            else:
                logger.error(f"Mirror: Failed to regenerate Conda index: {process.stderr}")

        except Exception as e:
            logger.error(f"Mirror: Error regenerating Conda index: {str(e)}")

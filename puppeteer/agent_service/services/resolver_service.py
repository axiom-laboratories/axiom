"""
Transitive dependency resolver service using pip-compile.

Resolves the complete dependency tree for any approved Python package,
populates IngredientDependency edges, and auto-approves discovered dependencies.
"""

import asyncio
import subprocess
import tempfile
import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime

from ..db import ApprovedIngredient, IngredientDependency

logger = logging.getLogger(__name__)


class ResolverService:
    """Service for resolving transitive dependencies using pip-compile."""

    @staticmethod
    async def resolve_ingredient_tree(
        db: AsyncSession,
        ingredient_id: str,
        max_depth: int = 10,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Resolve full transitive tree for an ingredient using pip-compile.

        Args:
            db: AsyncSession for database operations
            ingredient_id: ID of the ingredient to resolve
            max_depth: Maximum depth for dependency traversal
            timeout_seconds: Timeout for pip-compile subprocess (default: 300s = 5 min)

        Returns:
            {
                "success": bool,
                "resolved_count": int,
                "error_msg": Optional[str]
            }

        Side effects:
            - Fetches parent ingredient and updates mirror_status
            - Creates IngredientDependency edges for each resolved transitive dep
            - Auto-approves new transitive deps with auto_discovered=True
            - Updates ingredient.mirror_status (PENDING → RESOLVING → MIRRORING/FAILED)
        """
        parent = None
        try:
            # 1. Fetch parent ingredient
            parent = await db.get(ApprovedIngredient, ingredient_id)
            if not parent:
                return {"success": False, "resolved_count": 0, "error_msg": "Ingredient not found"}

            # 2. Update mirror_status to RESOLVING
            parent.mirror_status = "RESOLVING"
            parent.mirror_log = "Starting resolution..."
            await db.commit()

            # 3. Run pip-compile
            req_line = f"{parent.name}{parent.version_constraint or ''}"
            logger.info(f"Resolving dependencies for {req_line}")

            output = await ResolverService._run_pip_compile(req_line, timeout_seconds)

            # 4. Parse output to extract deps
            deps = ResolverService._parse_pip_compile_output(output)
            logger.info(f"Extracted {len(deps)} dependencies from pip-compile output")

            # 5. Create IngredientDependency edges, auto-approve new deps
            resolved_count = 0
            visited = set()

            for dep_name, dep_version in deps:
                # Skip self-reference (package depends on itself)
                if dep_name.lower() == parent.name.lower():
                    logger.debug(f"Skipping self-reference: {dep_name}")
                    continue

                # Skip duplicates in this resolution
                if dep_name.lower() in visited:
                    logger.debug(f"Skipping duplicate in resolution: {dep_name}")
                    continue

                visited.add(dep_name.lower())

                # Check if child ingredient exists
                stmt = select(ApprovedIngredient).where(
                    ApprovedIngredient.name.ilike(dep_name),
                    ApprovedIngredient.os_family == parent.os_family,
                    ApprovedIngredient.ecosystem == "PYPI"
                )
                result = await db.execute(stmt)
                child = result.scalar_one_or_none()

                if not child:
                    # Auto-approve with auto_discovered=True
                    child = ApprovedIngredient(
                        id=str(uuid4()),
                        name=dep_name,
                        version_constraint=f"=={dep_version}",
                        os_family=parent.os_family,
                        ecosystem="PYPI",
                        mirror_status="PENDING",
                        auto_discovered=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(child)
                    await db.flush()
                    logger.info(f"Auto-approved transitive dep: {dep_name}=={dep_version}")

                # Create IngredientDependency edge (skip if it already exists)
                edge_stmt = select(IngredientDependency).where(
                    IngredientDependency.parent_id == parent.id,
                    IngredientDependency.child_id == child.id,
                    IngredientDependency.ecosystem == "PYPI"
                )
                existing_edge = await db.execute(edge_stmt)
                if not existing_edge.scalar_one_or_none():
                    edge = IngredientDependency(
                        parent_id=parent.id,
                        child_id=child.id,
                        dependency_type="transitive",
                        version_constraint=f"=={dep_version}",
                        ecosystem="PYPI",
                        discovered_at=datetime.utcnow()
                    )
                    db.add(edge)
                    resolved_count += 1
                    logger.debug(f"Created edge: {parent.name} → {child.name}")

            await db.commit()

            # 6. Update mirror_status to MIRRORING (next phase will handle actual mirroring)
            parent.mirror_status = "MIRRORING"
            parent.mirror_log = f"Resolved {resolved_count} transitive dependencies"
            await db.commit()

            logger.info(f"Resolution complete for {parent.name}: {resolved_count} deps")
            return {"success": True, "resolved_count": resolved_count}

        except asyncio.TimeoutError:
            if parent:
                parent.mirror_status = "FAILED"
                parent.mirror_log = "Resolution timeout (possible circular dependency in upstream package)"
                await db.commit()
            logger.error(f"Resolution timeout for {ingredient_id}")
            return {"success": False, "resolved_count": 0, "error_msg": "Timeout after 5 minutes"}

        except Exception as e:
            if parent:
                parent.mirror_status = "FAILED"
                parent.mirror_log = f"Resolution error: {str(e)}"
                await db.commit()
            logger.error(f"Resolution error for {ingredient_id}: {str(e)}", exc_info=True)
            return {"success": False, "resolved_count": 0, "error_msg": str(e)}

    @staticmethod
    async def _run_pip_compile(req_line: str, timeout_seconds: int) -> str:
        """
        Run pip-compile subprocess and return output.

        Args:
            req_line: Requirement line (e.g., "flask==2.3.0")
            timeout_seconds: Subprocess timeout in seconds

        Returns:
            Output from pip-compile .txt file

        Raises:
            subprocess.TimeoutExpired: If pip-compile exceeds timeout
            Exception: If pip-compile fails with non-zero exit code
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.in', delete=False) as tf:
            tf.write(req_line)
            input_path = tf.name

        output_path = input_path.replace('.in', '.txt')

        try:
            cmd = [
                "pip-compile",
                "--no-emit-index-url",
                "--resolution", "eager",
                "--output-file", output_path,
                input_path
            ]

            logger.debug(f"Running pip-compile: {' '.join(cmd)}")

            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            if process.returncode != 0:
                logger.error(f"pip-compile stderr: {process.stderr}")
                raise Exception(f"pip-compile failed: {process.stderr}")

            with open(output_path) as f:
                return f.read()

        finally:
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {path}: {e}")

    @staticmethod
    def _parse_pip_compile_output(output: str) -> List[Tuple[str, str]]:
        """
        Parse pip-compile output to extract (name, version) pairs.

        Expected format:
            # Output of: pip-compile requirements.in
            #
            certifi==2024.12.28
                # via requests
            flask==2.3.0
            werkzeug==2.3.0
                # via flask

        Args:
            output: Raw pip-compile output

        Returns:
            List of (package_name, version) tuples
        """
        deps = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Format: "package==version" or "package==version   # via parent"
            if "==" in line:
                parts = line.split("==", 1)
                name = parts[0].strip()
                version_and_comment = parts[1]
                # Remove "# via ..." comment if present
                version = version_and_comment.split("#")[0].strip()
                deps.append((name, version))
                logger.debug(f"Parsed dep: {name}=={version}")

        return deps

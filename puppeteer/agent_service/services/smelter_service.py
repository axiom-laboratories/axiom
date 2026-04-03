import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import uuid4
from typing import List, Optional
from ..db import ApprovedIngredient
from ..models import ApprovedIngredientCreate, ApprovedIngredientUpdate
from .mirror_service import MirrorService
from .resolver_service import ResolverService

logger = logging.getLogger(__name__)

class SmelterService:
    @staticmethod
    async def add_ingredient(db: AsyncSession, ingredient_in: ApprovedIngredientCreate) -> ApprovedIngredient:
        """Adds a new vetted ingredient to the Smelter Registry."""
        new_ingredient = ApprovedIngredient(
            id=str(uuid4()),
            name=ingredient_in.name,
            version_constraint=ingredient_in.version_constraint,
            sha256=ingredient_in.sha256,
            os_family=ingredient_in.os_family.upper(),
            mirror_status="PENDING"
        )
        db.add(new_ingredient)
        await db.commit()
        await db.refresh(new_ingredient)

        # Auto-trigger resolution of transitive dependencies
        try:
            await ResolverService.resolve_ingredient_tree(db, new_ingredient.id)
        except Exception as e:
            # Log error but don't block add_ingredient response
            logger.error(f"Failed to resolve dependencies for {new_ingredient.name}: {str(e)}")

        # Mirroring is background task (not awaited)
        try:
            asyncio.create_task(
                MirrorService.mirror_ingredient_and_dependencies(db, new_ingredient.id)
            )
        except Exception as e:
            logger.error(f"Failed to start mirror task for {new_ingredient.name}: {str(e)}")

        return new_ingredient

    @staticmethod
    async def list_ingredients(db: AsyncSession, os_family: Optional[str] = None) -> List[ApprovedIngredient]:
        """Lists all approved ingredients, optionally filtered by OS family."""
        stmt = select(ApprovedIngredient)
        if os_family:
            stmt = stmt.where(ApprovedIngredient.os_family == os_family.upper())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete_ingredient(db: AsyncSession, ingredient_id: str) -> bool:
        """Removes an ingredient from the registry."""
        stmt = delete(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def scan_vulnerabilities(db: AsyncSession) -> dict:
        """
        Scans all approved Python ingredients and updates is_vulnerable status.
        Returns a summary of the scan results.
        """
        logger.info("Starting Smelter vulnerability scan...")
        
        # 1. Fetch all ingredients
        res = await db.execute(select(ApprovedIngredient))
        ingredients = res.scalars().all()
        
        python_ingredients = [i for i in ingredients if i.os_family in ["DEBIAN", "ALPINE", "FEDORA"]]
        if not python_ingredients:
            return {"scanned": 0, "vulnerable": 0}

        # 2. Create temporary requirements list for pip-audit
        # We use a simple list of pkg==version if constraint is precise, 
        # or just pkg if it's a range (pip-audit handles both but precise is better).
        reqs = []
        for i in python_ingredients:
            clean_constraint = i.version_constraint.strip()
            if not any(c in clean_constraint for c in [">", "<", "="]):
                # If no constraint, assume latest (pip-audit might need a version)
                reqs.append(i.name)
            elif "==" in clean_constraint:
                reqs.append(f"{i.name}{clean_constraint}")
            else:
                # e.g. "flask>=2.0" -> "flask==2.0" for audit purposes or just "flask"
                # pip-audit works best with exact versions.
                # For now, we'll just pass the constraint as-is if it's pip-compatible.
                reqs.append(f"{i.name}{clean_constraint}")

        import tempfile
        import json
        import subprocess
        import os

        results_summary = {"scanned": len(python_ingredients), "vulnerable": 0}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tf:
            tf.write("\n".join(reqs))
            tf_path = tf.name

        try:
            # 3. Run pip-audit
            # We use the venv's pip-audit
            venv_path = os.environ.get("VIRTUAL_ENV", ".venv")
            pip_audit_bin = os.path.join(venv_path, "bin", "pip-audit")
            if not os.path.exists(pip_audit_bin):
                pip_audit_bin = "pip-audit" # Fallback to path

            cmd = [pip_audit_bin, "-r", tf_path, "--format", "json", "--no-deps", "--disable-pip"]
            process = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True
            )
            
            # pip-audit returns non-zero if vulnerabilities are found
            audit_data = {}
            if process.stdout:
                try:
                    audit_data = json.loads(process.stdout)
                except json.JSONDecodeError:
                    # Strip any warning lines before JSON
                    lines = process.stdout.splitlines()
                    json_str = next((line for line in lines if line.startswith("{")), "")
                    if json_str:
                        try:
                            audit_data = json.loads(json_str)
                        except:
                            logger.error(f"Failed to parse pip-audit JSON after stripping: {json_str}")
                    else:
                        logger.error(f"Failed to find JSON in pip-audit output: {process.stdout}")

            # 4. Update DB
            findings = audit_data if isinstance(audit_data, list) else audit_data.get("dependencies", [])
            
            # Support both 'vulnerabilities' and 'vulns' keys depending on pip-audit version/format
            vulnerable_map = {}
            for f in findings:
                pkg_name = f.get("name", "").lower()
                vulns = f.get("vulnerabilities") or f.get("vulns")
                if vulns:
                    vulnerable_map[pkg_name] = f
            
            for i in python_ingredients:
                pkg_name = i.name.lower()
                if pkg_name in vulnerable_map:
                    i.is_vulnerable = True
                    i.vulnerability_report = json.dumps(vulnerable_map[pkg_name])
                    results_summary["vulnerable"] += 1
                else:
                    i.is_vulnerable = False
                    i.vulnerability_report = None
            
            await db.commit()
            logger.info(f"Smelter scan complete. Found {results_summary['vulnerable']} vulnerable packages.")
            return results_summary

        except Exception as e:
            logger.error(f"Error during Smelter vulnerability scan: {str(e)}")
            raise e
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    @staticmethod
    async def validate_blueprint(db: AsyncSession, rt_def: dict, os_family: str) -> List[str]:
        """
        Checks a blueprint definition against the Smelter Registry.
        Returns a list of unapproved packages.
        """
        packages = rt_def.get("packages", {})
        python_packages = packages.get("python", [])
        
        if not python_packages:
            return []

        # Get all approved packages for this OS family
        res = await db.execute(
            select(ApprovedIngredient.name).where(
                ApprovedIngredient.os_family == os_family.upper()
            )
        )
        approved_names = set(res.scalars().all())

        unapproved = []
        for pkg in python_packages:
            # Simple check: name must match exactly. 
            # In a more advanced version, we'd parse version constraints.
            # Strip version markers for matching (e.g. "flask>=2.0" -> "flask")
            pkg_name = pkg.split(">")[0].split("<")[0].split("=")[0].strip().lower()
            
            # Find in approved list (case-insensitive)
            found = False
            for approved in approved_names:
                if approved.lower() == pkg_name:
                    found = True
                    break
            
            if not found:
                unapproved.append(pkg)

        return unapproved

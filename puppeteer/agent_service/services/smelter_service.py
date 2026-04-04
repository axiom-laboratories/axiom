import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import uuid4
from typing import List, Optional, Dict, Tuple, Set
from ..db import ApprovedIngredient, IngredientDependency
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
            ecosystem=ingredient_in.ecosystem,
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
    async def _build_transitive_requirements(db: AsyncSession, ingredient: ApprovedIngredient) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Build full requirements list including transitive dependencies.

        Returns:
            - List of pip-audit-compatible requirement strings (e.g., ["flask==3.0.0", "jinja2==3.1.3"])
            - Dict mapping vulnerable packages to their parent chain for provenance reconstruction
        """
        reqs = []
        parent_map = {}  # Maps child_name to list of parent names for provenance
        visited: Set[str] = set()

        async def walk_deps(parent_id: str, ancestor_chain: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
            """
            BFS walk of IngredientDependency edges.
            Returns list of (name, version) tuples for all transitive deps.
            """
            if parent_id in visited:
                return []
            visited.add(parent_id)

            # Get direct children
            stmt = select(IngredientDependency).where(
                IngredientDependency.parent_id == parent_id,
                IngredientDependency.ecosystem == "PYPI"
            )
            result = await db.execute(stmt)
            edges = result.scalars().all()

            all_deps = []
            for edge in edges:
                child_result = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == edge.child_id))
                child = child_result.scalar_one_or_none()
                if child:
                    # Record this dependency
                    all_deps.append((child.name, child.version_constraint.strip() if child.version_constraint else ""))

                    # Track parent chain for provenance
                    child_name_lower = child.name.lower()
                    if child_name_lower not in parent_map:
                        parent_map[child_name_lower] = []
                    for parent_name, parent_version in ancestor_chain:
                        parent_map[child_name_lower].append(f"{parent_name} {parent_version}".strip())

                    # Recurse with depth limit (10 levels max)
                    new_chain = ancestor_chain + [(child.name, child.version_constraint or "")]
                    if len(new_chain) <= 10:
                        transitive = await walk_deps(child.id, new_chain)
                        all_deps.extend(transitive)

            return all_deps

        # Add root ingredient
        clean_constraint = ingredient.version_constraint.strip() if ingredient.version_constraint else ""
        if "==" in clean_constraint:
            reqs.append(f"{ingredient.name}{clean_constraint}")
        else:
            reqs.append(ingredient.name)

        # Walk transitive deps
        transitive_deps = await walk_deps(ingredient.id, [(ingredient.name, clean_constraint)])
        for dep_name, dep_version in transitive_deps:
            if "==" in dep_version:
                reqs.append(f"{dep_name}{dep_version}")
            elif dep_version:
                reqs.append(f"{dep_name}=={dep_version}")
            else:
                reqs.append(dep_name)

        return reqs, parent_map

    @staticmethod
    def _extract_cvss_severity(vuln_record: dict) -> str:
        """Extract CVSS-based severity from pip-audit vulnerability record."""
        # Check for severity field first
        if "severity" in vuln_record and vuln_record["severity"] is not None:
            severity = vuln_record["severity"].upper()
            if severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                return severity

        # Try to extract CVSS score
        cvss_score = None
        if "cvss_score" in vuln_record:
            try:
                cvss_score = float(vuln_record["cvss_score"])
            except (ValueError, TypeError):
                pass

        if cvss_score is not None:
            if cvss_score >= 9.0:
                return "CRITICAL"
            elif cvss_score >= 7.0:
                return "HIGH"
            elif cvss_score >= 4.0:
                return "MEDIUM"
            else:
                return "LOW"

        # Default to HIGH if unavailable
        return "HIGH"

    @staticmethod
    def _reconstruct_provenance_path(vulnerable_pkg: str, parent_chain: Dict[str, List[str]]) -> List[str]:
        """Reconstruct full provenance path from root to vulnerable package."""
        paths = []
        if vulnerable_pkg.lower() in parent_chain:
            for chain in parent_chain[vulnerable_pkg.lower()]:
                paths.append(chain)
        return paths

    @staticmethod
    async def scan_vulnerabilities(db: AsyncSession, ingredient_id: Optional[str] = None, scan_all: bool = True) -> dict:
        """
        Scans approved Python ingredients for vulnerabilities, including transitive dependencies.

        Args:
            db: AsyncSession for database operations
            ingredient_id: If specified, scan only this ingredient; otherwise scan all if scan_all=True
            scan_all: If True, scan all ingredients; if False, scan only specified ingredient_id

        Returns:
            Summary dict with scan counts and vulnerability data
        """
        logger.info("Starting Smelter vulnerability scan (transitive-aware)...")

        # Determine which ingredients to scan
        if ingredient_id:
            result = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id))
            ingredient = result.scalar_one_or_none()
            if not ingredient:
                logger.warning(f"Ingredient {ingredient_id} not found")
                return {"scanned": 0, "vulnerable": 0}
            ingredients_to_scan = [ingredient]
        elif scan_all:
            res = await db.execute(select(ApprovedIngredient))
            all_ingredients = res.scalars().all()
            # Only scan Python-capable OS families
            ingredients_to_scan = [i for i in all_ingredients if i.os_family in ["DEBIAN", "ALPINE", "FEDORA"]]
        else:
            return {"scanned": 0, "vulnerable": 0}

        if not ingredients_to_scan:
            return {"scanned": 0, "vulnerable": 0}

        import tempfile
        import json
        import subprocess
        import os

        results_summary = {"scanned": len(ingredients_to_scan), "vulnerable": 0}

        try:
            for ingredient in ingredients_to_scan:
                logger.info(f"Scanning {ingredient.name} (including transitive deps)...")

                # Build requirements list with transitive deps
                reqs, parent_map = await SmelterService._build_transitive_requirements(db, ingredient)

                if not reqs:
                    ingredient.is_vulnerable = False
                    ingredient.vulnerability_report = None
                    continue

                # Create temp requirements file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tf:
                    tf.write("\n".join(reqs))
                    tf_path = tf.name

                try:
                    # Run pip-audit with 120s timeout
                    venv_path = os.environ.get("VIRTUAL_ENV", ".venv")
                    pip_audit_bin = os.path.join(venv_path, "bin", "pip-audit")
                    if not os.path.exists(pip_audit_bin):
                        pip_audit_bin = "pip-audit"

                    cmd = [pip_audit_bin, "-r", tf_path, "--format", "json", "--no-deps", "--disable-pip"]
                    try:
                        process = await asyncio.wait_for(
                            asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True),
                            timeout=120.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"pip-audit timed out for {ingredient.name}")
                        ingredient.is_vulnerable = False
                        ingredient.vulnerability_report = None
                        continue

                    # Parse pip-audit output
                    audit_data = {}
                    if process.stdout:
                        try:
                            audit_data = json.loads(process.stdout)
                        except json.JSONDecodeError:
                            lines = process.stdout.splitlines()
                            json_str = next((line for line in lines if line.startswith("{")), "")
                            if json_str:
                                try:
                                    audit_data = json.loads(json_str)
                                except:
                                    logger.error(f"Failed to parse pip-audit JSON for {ingredient.name}")

                    # Process findings and build extended vulnerability report
                    findings = audit_data if isinstance(audit_data, list) else audit_data.get("dependencies", [])
                    vulnerable_transitive_deps = []
                    worst_severity = None
                    total_transitive_vulns = 0

                    for finding in findings:
                        pkg_name = finding.get("name", "")
                        vulns = finding.get("vulnerabilities") or finding.get("vulns") or []

                        if not vulns:
                            continue

                        is_transitive = pkg_name.lower() != ingredient.name.lower()

                        for vuln in vulns:
                            vuln_id = vuln.get("id", "CVE-UNKNOWN")
                            description = vuln.get("description", "")
                            cvss_score = None
                            try:
                                cvss_score = float(vuln.get("cvss_score", 0))
                            except (ValueError, TypeError):
                                pass

                            severity = SmelterService._extract_cvss_severity(vuln)
                            fix_versions = vuln.get("fixed_in", vuln.get("fix_versions", []))
                            if isinstance(fix_versions, str):
                                fix_versions = [fix_versions]

                            # Reconstruct provenance path
                            provenance_path = SmelterService._reconstruct_provenance_path(pkg_name, parent_map)
                            if not provenance_path and is_transitive:
                                # Fallback: just show the package name if we can't reconstruct
                                provenance_path = [pkg_name]

                            vulnerable_transitive_deps.append({
                                "cve_id": vuln_id,
                                "package": pkg_name,
                                "version": finding.get("installed_version", ""),
                                "cvss_score": cvss_score,
                                "severity": severity,
                                "description": description,
                                "provenance_path": provenance_path,
                                "fix_versions": fix_versions,
                                "is_transitive": is_transitive
                            })

                            # Track worst severity
                            severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                            if worst_severity is None:
                                worst_severity = severity
                            else:
                                if severity_order.get(severity, 0) > severity_order.get(worst_severity, 0):
                                    worst_severity = severity

                            total_transitive_vulns += 1

                    # Update ingredient with extended vulnerability report
                    if vulnerable_transitive_deps:
                        ingredient.is_vulnerable = True
                        report = {
                            "vulnerable_transitive_deps": vulnerable_transitive_deps,
                            "total_vulnerable_transitive": total_transitive_vulns,
                            "worst_severity": worst_severity
                        }
                        ingredient.vulnerability_report = json.dumps(report)
                        results_summary["vulnerable"] += 1
                        logger.info(f"{ingredient.name}: Found {total_transitive_vulns} CVEs (worst: {worst_severity})")
                    else:
                        ingredient.is_vulnerable = False
                        ingredient.vulnerability_report = None

                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)

            await db.commit()
            logger.info(f"Smelter scan complete. Found {results_summary['vulnerable']} vulnerable packages.")
            return results_summary

        except Exception as e:
            logger.error(f"Error during Smelter vulnerability scan: {str(e)}")
            raise e

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

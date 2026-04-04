"""
Smelter service API router for CVE scanning and dependency tree management.

Endpoints:
- GET /api/smelter/ingredients/{id}/tree - Get dependency tree with CVE info
- POST /api/smelter/ingredients/{id}/discover - Discover and scan dependencies
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from uuid import UUID
from typing import List, Dict, Tuple
import json

from ..db import get_db, ApprovedIngredient, IngredientDependency
from ..models import (
    DependencyTreeResponse, DependencyTreeNode, CVEDetail,
    DiscoverDependenciesRequest, DiscoverDependenciesResponse,
    ApprovedIngredientResponse
)
from ..auth import get_current_user
from ..security import require_permission
from ..services.smelter_service import SmelterService
from ..services.resolver_service import ResolverService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _build_tree_response_recursive(
    db: AsyncSession,
    ingredient_id: str,
    visited: set,
    depth: int = 0,
    max_depth: int = 10
) -> Tuple[DependencyTreeNode, int, str]:
    """
    Recursively build DependencyTreeNode tree structure.

    Returns:
        (root_node, total_cve_count, worst_severity)
    """
    if depth > max_depth or ingredient_id in visited:
        # Create stub node to prevent circular refs
        result = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id))
        ingredient = result.scalar_one_or_none()
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        return DependencyTreeNode(
            id=ingredient.id,
            name=ingredient.name,
            version=ingredient.version_constraint or "unknown",
            ecosystem=ingredient.ecosystem,
            cve_count=0,
            worst_severity=None,
            auto_discovered=ingredient.auto_discovered,
            mirror_status=ingredient.mirror_status or "PENDING",
            children=[],
            cves=[]
        ), 0, None

    visited.add(ingredient_id)

    # Fetch ingredient
    result = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # Parse CVEs from vulnerability_report
    cves: List[CVEDetail] = []
    worst_severity = None
    total_cve_count = 0

    if ingredient.vulnerability_report:
        try:
            vuln_data = json.loads(ingredient.vulnerability_report)
            vulnerable_deps = vuln_data.get("vulnerable_transitive_deps", [])
            total_cve_count = len(vulnerable_deps)
            worst_severity = vuln_data.get("worst_severity")

            for vuln in vulnerable_deps:
                cves.append(CVEDetail(
                    cve_id=vuln.get("cve_id", "CVE-UNKNOWN"),
                    cvss_score=vuln.get("cvss_score"),
                    severity=vuln.get("severity", "HIGH"),
                    description=vuln.get("description", ""),
                    fix_versions=vuln.get("fix_versions", []),
                    affected_package=vuln.get("package", ""),
                    is_transitive=vuln.get("is_transitive", False),
                    provenance_path=vuln.get("provenance_path", [])
                ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse vulnerability_report for {ingredient.id}: {str(e)}")

    # Fetch children
    children: List[DependencyTreeNode] = []
    child_total_cves = 0
    all_severities = [worst_severity] if worst_severity else []

    edge_result = await db.execute(
        select(IngredientDependency).where(
            IngredientDependency.parent_id == ingredient_id,
            IngredientDependency.ecosystem == "PYPI"
        )
    )
    edges = edge_result.scalars().all()

    for edge in edges:
        try:
            child_node, child_cve_count, child_worst = await _build_tree_response_recursive(
                db, edge.child_id, visited, depth + 1, max_depth
            )
            children.append(child_node)
            child_total_cves += child_cve_count
            if child_worst:
                all_severities.append(child_worst)
        except HTTPException:
            # Skip missing children
            continue

    # Determine worst severity across all children
    worst_from_children = None
    severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    if all_severities:
        worst_from_children = max(all_severities, key=lambda x: severity_order.get(x, 0))

    total_cve_count += child_total_cves
    if worst_from_children:
        if worst_severity is None:
            worst_severity = worst_from_children
        else:
            worst_severity = max(
                [worst_severity, worst_from_children],
                key=lambda x: severity_order.get(x, 0)
            )

    node = DependencyTreeNode(
        id=ingredient.id,
        name=ingredient.name,
        version=ingredient.version_constraint or "unknown",
        ecosystem=ingredient.ecosystem,
        cve_count=total_cve_count,
        worst_severity=worst_severity,
        auto_discovered=ingredient.auto_discovered,
        mirror_status=ingredient.mirror_status or "PENDING",
        children=children,
        cves=cves
    )

    return node, total_cve_count, worst_severity


async def _build_tree_response(
    db: AsyncSession,
    ingredient: ApprovedIngredient
) -> DependencyTreeResponse:
    """
    Build complete DependencyTreeResponse for an ingredient.
    """
    root_node, total_cve_count, worst_severity = await _build_tree_response_recursive(
        db, ingredient.id, set()
    )

    return DependencyTreeResponse(
        root_id=ingredient.id,
        root_name=ingredient.name,
        root_version=ingredient.version_constraint or "unknown",
        total_nodes=_count_tree_nodes(root_node),
        total_cve_count=total_cve_count,
        worst_severity=worst_severity,
        tree=root_node
    )


def _count_tree_nodes(node: DependencyTreeNode) -> int:
    """Count total nodes in tree (including root and all children)."""
    count = 1
    for child in node.children:
        count += _count_tree_nodes(child)
    return count


@router.get(
    "/api/smelter/ingredients/{ingredient_id}/tree",
    response_model=DependencyTreeResponse,
    tags=["Smelter"],
    summary="Get dependency tree with CVE information"
)
async def get_dependency_tree(
    ingredient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("smelter:read"))
):
    """
    Get the full dependency tree for an ingredient, including CVE vulnerability data.

    Returns:
    - Complete tree structure with all transitive dependencies
    - CVE counts and severity badges for each node
    - Provenance paths for vulnerable dependencies
    """
    # Fetch ingredient
    result = await db.execute(
        select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient {ingredient_id} not found"
        )

    # Build tree response
    tree_response = await _build_tree_response(db, ingredient)
    return tree_response


@router.post(
    "/api/smelter/ingredients/{ingredient_id}/discover",
    response_model=DiscoverDependenciesResponse,
    tags=["Smelter"],
    summary="Discover and resolve transitive dependencies",
    status_code=200
)
async def discover_dependencies(
    ingredient_id: str,
    request: DiscoverDependenciesRequest = DiscoverDependenciesRequest(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("smelter:write"))
):
    """
    Trigger dependency discovery for an ingredient.

    - Uses pip-compile to resolve the full transitive tree
    - Auto-approves discovered transitive deps (sets auto_discovered=True)
    - Scans all resolved dependencies for CVEs
    - Returns updated tree with CVE findings

    Returns:
    - Count of newly discovered dependencies
    - Full updated dependency tree
    - Toast notification message with CVE summary
    """
    # Fetch ingredient
    result = await db.execute(
        select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient {ingredient_id} not found"
        )

    # Trigger resolution
    resolve_result = await ResolverService.resolve_ingredient_tree(db, ingredient.id)
    discovered_count = resolve_result.get("resolved_count", 0)

    # Scan for CVEs (single ingredient only)
    try:
        await SmelterService.scan_vulnerabilities(db, ingredient_id=ingredient_id, scan_all=False)
    except Exception as e:
        logger.warning(f"CVE scan failed during discovery: {str(e)}")

    # Refresh ingredient to get updated data
    await db.refresh(ingredient)

    # Build tree response
    tree_response = await _build_tree_response(db, ingredient)

    # Count total CVEs in tree
    total_cves = tree_response.total_cve_count
    worst_severity = tree_response.worst_severity

    # Generate toast message
    if total_cves == 0:
        toast_message = f"{ingredient.name}: {discovered_count} deps resolved, clean"
    elif worst_severity == "CRITICAL":
        toast_message = f"{ingredient.name}: {discovered_count} deps resolved, {total_cves} CVEs found (CRITICAL)"
    elif worst_severity == "HIGH":
        toast_message = f"{ingredient.name}: {discovered_count} deps resolved, {total_cves} CVEs found (HIGH)"
    else:
        toast_message = f"{ingredient.name}: {discovered_count} deps resolved, {total_cves} CVEs found"

    logger.info(f"Discovered {discovered_count} deps for {ingredient.name}, found {total_cves} CVEs")

    return DiscoverDependenciesResponse(
        ingredient_id=ingredient_id,
        discovered_count=discovered_count,
        tree=tree_response,
        toast_message=toast_message
    )

"""EE Router: Script Analyzer — package dependency extraction and approval workflow."""
from __future__ import annotations

import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db, ScriptAnalysisRequest, User, ApprovedIngredient
from ...deps import require_permission, audit
from ...models import (
    AnalyzeScriptRequest,
    AnalyzeScriptResponse,
    AnalyzedPackage,
    ScriptAnalysisRequestResponse,
    ScriptAnalysisRequestCreate,
    ScriptAnalysisApprovalRequest,
)
from ...services.analyzer_service import AnalyzerService

analyzer_router = APIRouter()


@analyzer_router.post("/api/analyzer/analyze-script", response_model=AnalyzeScriptResponse, tags=["Script Analyzer"])
async def analyze_script(
    req: AnalyzeScriptRequest,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Analyze a script for package dependencies and cross-reference with approved ingredients."""
    # Call analyzer service to extract packages
    result = await AnalyzerService.analyze_script(req.script_content, req.language, db)

    # Cross-reference with ApprovedIngredient table
    approved_names = set()
    pending_names = set()

    for suggestion in result["suggestions"]:
        # Check if this package is already approved
        query = select(ApprovedIngredient).where(
            ApprovedIngredient.package_name == suggestion["package_name"],
            ApprovedIngredient.is_active == True
        )
        res = await db.execute(query)
        ingredient = res.scalar_one_or_none()

        if ingredient:
            approved_names.add(suggestion["package_name"])
        else:
            pending_names.add(suggestion["package_name"])

    # Map to response format
    suggestions = [
        AnalyzedPackage(
            import_name=s["import_name"],
            package_name=s["package_name"],
            ecosystem=s.get("ecosystem", "UNKNOWN"),
            mapped=s.get("mapped", False),
        )
        for s in result["suggestions"]
    ]

    return AnalyzeScriptResponse(
        detected_language=result["detected_language"],
        suggestions=suggestions,
        approved=list(approved_names),
        pending_review=list(pending_names),
    )


@analyzer_router.get("/api/analyzer/requests", response_model=List[ScriptAnalysisRequestResponse], tags=["Script Analyzer"])
async def list_analysis_requests(
    status: Optional[str] = None,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List script analysis requests (PENDING, APPROVED, REJECTED). Admin sees all; others see own."""
    query = select(ScriptAnalysisRequest)

    # Non-admin users can only see their own requests
    if current_user.role != "admin":
        query = query.where(ScriptAnalysisRequest.requester_id == current_user.id)

    # Filter by status if provided
    if status:
        query = query.where(ScriptAnalysisRequest.status == status)

    res = await db.execute(query)
    requests = res.scalars().all()

    return [
        ScriptAnalysisRequestResponse(
            id=r.id,
            requester_id=r.requester_id,
            package_name=r.package_name,
            ecosystem=r.ecosystem,
            detected_import=r.detected_import,
            source_script_hash=r.source_script_hash,
            status=r.status,
            created_at=r.created_at,
            reviewed_at=r.reviewed_at,
            reviewed_by=r.reviewed_by,
            review_reason=r.review_reason,
        )
        for r in requests
    ]


@analyzer_router.post("/api/analyzer/requests", response_model=ScriptAnalysisRequestResponse, tags=["Script Analyzer"])
async def create_analysis_request(
    req: ScriptAnalysisRequestCreate,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Create a script analysis request for a new package. Prevents duplicates."""
    # Hash the script content
    script_hash = hashlib.sha256(req.source_script.encode()).hexdigest()

    # Check for duplicate request (same package + ecosystem + script hash)
    query = select(ScriptAnalysisRequest).where(
        ScriptAnalysisRequest.requester_id == current_user.id,
        ScriptAnalysisRequest.package_name == req.package_name,
        ScriptAnalysisRequest.ecosystem == req.ecosystem,
        ScriptAnalysisRequest.source_script_hash == script_hash,
        ScriptAnalysisRequest.status == "PENDING"
    )
    res = await db.execute(query)
    existing = res.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A pending request for {req.package_name} from this script already exists"
        )

    # Create new request
    new_request = ScriptAnalysisRequest(
        id=f"sar-{script_hash[:12]}",
        requester_id=current_user.id,
        package_name=req.package_name,
        ecosystem=req.ecosystem,
        detected_import=req.detected_import,
        source_script_hash=script_hash,
        status="PENDING",
    )
    db.add(new_request)
    audit(db, current_user, "analyzer:request_created", f"{req.package_name} ({req.ecosystem})")
    await db.commit()

    # TODO: Trigger background task to notify approvers via WebSocket

    return ScriptAnalysisRequestResponse(
        id=new_request.id,
        requester_id=new_request.requester_id,
        package_name=new_request.package_name,
        ecosystem=new_request.ecosystem,
        detected_import=new_request.detected_import,
        source_script_hash=new_request.source_script_hash,
        status=new_request.status,
        created_at=new_request.created_at,
    )


@analyzer_router.post("/api/analyzer/requests/{request_id}/approve", response_model=ScriptAnalysisRequestResponse, tags=["Script Analyzer"])
async def approve_analysis_request(
    request_id: str,
    approval_req: ScriptAnalysisApprovalRequest,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Approve a script analysis request and create an approved ingredient."""
    # Fetch the request
    res = await db.execute(select(ScriptAnalysisRequest).where(ScriptAnalysisRequest.id == request_id))
    request = res.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Request is already {request.status}")

    # Update request status
    request.status = "APPROVED"
    request.reviewed_by = current_user.id
    request.review_reason = approval_req.reason

    # Check if ingredient already exists
    ingredient_query = select(ApprovedIngredient).where(
        ApprovedIngredient.package_name == request.package_name,
        ApprovedIngredient.is_active == True
    )
    res = await db.execute(ingredient_query)
    existing_ingredient = res.scalar_one_or_none()

    if not existing_ingredient:
        # Create approved ingredient
        new_ingredient = ApprovedIngredient(
            id=f"ing-{request.package_name.lower().replace(' ', '-')}",
            package_name=request.package_name,
            os_family="UNIVERSAL",  # Can be refined per-ecosystem
            ecosystem=request.ecosystem,
            description=f"Auto-approved from script analysis: {request.detected_import}",
            version_constraint="*",
            is_active=True,
        )
        db.add(new_ingredient)

    # Audit log
    audit(db, current_user, "analyzer:request_approved", f"{request.package_name} ({request.ecosystem})")
    await db.commit()

    # TODO: Broadcast to WebSocket subscribers that this ingredient was approved

    return ScriptAnalysisRequestResponse(
        id=request.id,
        requester_id=request.requester_id,
        package_name=request.package_name,
        ecosystem=request.ecosystem,
        detected_import=request.detected_import,
        source_script_hash=request.source_script_hash,
        status=request.status,
        created_at=request.created_at,
        reviewed_at=request.reviewed_at,
        reviewed_by=request.reviewed_by,
        review_reason=request.review_reason,
    )


@analyzer_router.post("/api/analyzer/requests/{request_id}/reject", response_model=ScriptAnalysisRequestResponse, tags=["Script Analyzer"])
async def reject_analysis_request(
    request_id: str,
    rejection_req: ScriptAnalysisApprovalRequest,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Reject a script analysis request."""
    # Fetch the request
    res = await db.execute(select(ScriptAnalysisRequest).where(ScriptAnalysisRequest.id == request_id))
    request = res.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Request is already {request.status}")

    # Update request status
    request.status = "REJECTED"
    request.reviewed_by = current_user.id
    request.review_reason = rejection_req.reason or "No reason provided"

    # Audit log
    audit(db, current_user, "analyzer:request_rejected", f"{request.package_name} ({request.ecosystem})")
    await db.commit()

    return ScriptAnalysisRequestResponse(
        id=request.id,
        requester_id=request.requester_id,
        package_name=request.package_name,
        ecosystem=request.ecosystem,
        detected_import=request.detected_import,
        source_script_hash=request.source_script_hash,
        status=request.status,
        created_at=request.created_at,
        reviewed_at=request.reviewed_at,
        reviewed_by=request.reviewed_by,
        review_reason=request.review_reason,
    )

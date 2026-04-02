"""EE Router: Foundry — blueprints, templates, capability matrix, images, BOM, approved OS."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select

from agent_service.db import get_db, AsyncSession, Config, User
from agent_service.deps import require_permission, get_current_user, audit
from ee.foundry.models import (
    Blueprint, PuppetTemplate, CapabilityMatrix, ImageBOM, PackageIndex, ApprovedOS,
    BlueprintCreate, BlueprintResponse,
    PuppetTemplateCreate, PuppetTemplateResponse,
    ImageBuildRequest, ImageResponse,
    CapabilityMatrixEntry, CapabilityMatrixUpdate,
    ImageBOMResponse, PackageIndexResponse,
    ApprovedOSCreate, ApprovedOSUpdate, ApprovedOSResponse,
)
from ee.foundry.services import foundry_service

foundry_router = APIRouter()


# --- Blueprints ---

@foundry_router.post("/api/blueprints", response_model=BlueprintResponse, status_code=201, tags=["Foundry"])
async def create_blueprint(
    req: BlueprintCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    definition = dict(req.definition)

    # Only RUNTIME blueprints need OS + dep validation
    if req.type == 'RUNTIME':
        tool_ids = [t.get("id") for t in definition.get("tools", []) if t.get("id")]
        declared_os = req.os_family  # already normalized to uppercase by Pydantic

        if tool_ids:
            # === PASS 1: OS mismatch check (hard reject) ===
            stmt = select(CapabilityMatrix).where(
                CapabilityMatrix.is_active == True,
                CapabilityMatrix.base_os_family == declared_os,
                CapabilityMatrix.tool_id.in_(tool_ids)
            )
            result = await db.execute(stmt)
            valid_rows = result.scalars().all()
            valid_tool_ids = {row.tool_id for row in valid_rows}
            incompatible = [t for t in tool_ids if t not in valid_tool_ids]
            if incompatible:
                raise HTTPException(status_code=422, detail={
                    "error": "os_mismatch",
                    "message": f"Blueprint validation failed: tools {incompatible} have no CapabilityMatrix entry for {declared_os}. Add {declared_os} support for these tools or change the OS family.",
                    "offending_tools": incompatible
                })

            # === PASS 2: Runtime dependency check (soft reject with confirmation) ===
            tool_set = set(tool_ids)
            confirmed = set(req.confirmed_deps or [])
            missing_deps: list = []
            for row in valid_rows:
                try:
                    deps = json.loads(row.runtime_dependencies or "[]")
                except Exception:
                    deps = []
                for dep in deps:
                    if dep not in tool_set and dep not in confirmed:
                        missing_deps.append(dep)

            if missing_deps:
                raise HTTPException(status_code=422, detail={
                    "error": "deps_required",
                    "message": "Some tools have unsatisfied runtime dependencies. Resubmit with confirmed_deps to auto-add them.",
                    "deps_to_confirm": list(set(missing_deps))
                })

            # Auto-add confirmed deps to the tool list before saving
            if confirmed:
                existing_ids = {t.get("id") for t in definition.get("tools", [])}
                extra = [{"id": dep, "version": "latest"} for dep in confirmed if dep not in existing_ids]
                definition.setdefault("tools", []).extend(extra)

    new_bp = Blueprint(
        id=str(uuid.uuid4()),
        type=req.type,
        name=req.name,
        definition=json.dumps(definition),
        os_family=req.os_family,
    )
    db.add(new_bp)
    await db.commit()
    await db.refresh(new_bp)

    return {
        "id": new_bp.id,
        "type": new_bp.type,
        "name": new_bp.name,
        "definition": definition,
        "version": new_bp.version,
        "created_at": new_bp.created_at,
        "os_family": new_bp.os_family,
    }


@foundry_router.get("/api/blueprints", response_model=List[BlueprintResponse], tags=["Foundry"])
async def list_blueprints(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Blueprint))
    bps = result.scalars().all()
    return [{
        "id": bp.id,
        "type": bp.type,
        "name": bp.name,
        "definition": json.loads(bp.definition),
        "version": bp.version,
        "created_at": bp.created_at,
        "os_family": bp.os_family,
    } for bp in bps]


@foundry_router.delete("/api/blueprints/{id}", tags=["Foundry"])
async def delete_blueprint(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PuppetTemplate).where(
            (PuppetTemplate.runtime_blueprint_id == id) | (PuppetTemplate.network_blueprint_id == id)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Blueprint is referenced by one or more templates")
    result = await db.execute(select(Blueprint).where(Blueprint.id == id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    audit(db, current_user, "blueprint:delete", id, {"name": bp.name})
    await db.delete(bp)
    await db.commit()
    return {"status": "deleted"}


# --- Templates ---

@foundry_router.post("/api/templates", response_model=PuppetTemplateResponse, tags=["Foundry"])
async def create_template(req: PuppetTemplateCreate, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    # Verify Blueprints exist
    rt_res = await db.execute(select(Blueprint).where(Blueprint.id == req.runtime_blueprint_id, Blueprint.type == 'RUNTIME'))
    nw_res = await db.execute(select(Blueprint).where(Blueprint.id == req.network_blueprint_id, Blueprint.type == 'NETWORK'))

    rt_bp = rt_res.scalar_one_or_none()
    nw_bp = nw_res.scalar_one_or_none()

    if not rt_bp or not nw_bp:
        raise HTTPException(status_code=400, detail="Invalid Runtime or Network Blueprint ID")

    canonical_payload = f"{rt_bp.name}:{rt_bp.version}:{nw_bp.name}:{nw_bp.version}"
    canonical_id = hashlib.sha256(canonical_payload.encode()).hexdigest()[:12]

    new_tmpl = PuppetTemplate(
        id=str(uuid.uuid4()),
        friendly_name=req.friendly_name,
        runtime_blueprint_id=req.runtime_blueprint_id,
        network_blueprint_id=req.network_blueprint_id,
        canonical_id=canonical_id
    )
    db.add(new_tmpl)
    await db.commit()
    await db.refresh(new_tmpl)

    return new_tmpl


@foundry_router.get("/api/templates", response_model=List[PuppetTemplateResponse], tags=["Foundry"])
async def list_templates(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PuppetTemplate))
    templates = result.scalars().all()
    return [{
        "id": t.id,
        "friendly_name": t.friendly_name,
        "runtime_blueprint_id": t.runtime_blueprint_id,
        "network_blueprint_id": t.network_blueprint_id,
        "canonical_id": t.canonical_id,
        "current_image_uri": t.current_image_uri,
        "last_built_image": t.current_image_uri,
        "last_built_at": t.last_built_at,
        "created_at": t.created_at,
        "is_compliant": t.is_compliant if t.is_compliant is not None else True,
        "status": t.status or "DRAFT",
        "bom_captured": t.bom_captured or False,
    } for t in templates]


@foundry_router.post("/api/templates/{id}/build", response_model=ImageResponse, tags=["Foundry"])
async def build_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await foundry_service.build_template(id, db)
    if not result.status.startswith("SUCCESS"):
        raise HTTPException(status_code=500, detail=result.status)
    audit(db, current_user, "template:build", id)
    await db.commit()
    return result


@foundry_router.delete("/api/templates/{id}", tags=["Foundry"])
async def delete_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    audit(db, current_user, "template:delete", id, {"name": tmpl.friendly_name})
    await db.delete(tmpl)
    await db.commit()
    return {"status": "deleted"}


# --- Image BOM & Lifecycle ---

@foundry_router.patch("/api/templates/{id}/status", tags=["Foundry"])
async def update_template_status(
    id: str,
    req: Dict[str, str],
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Update the lifecycle status of an image (ACTIVE, DEPRECATED, REVOKED)."""
    new_status = req.get("status")
    if new_status not in ["ACTIVE", "DEPRECATED", "REVOKED"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    tmpl.status = new_status
    audit(db, current_user, "foundry:image_status_updated", f"{id}:{new_status}")
    await db.commit()
    return {"id": id, "status": new_status}


@foundry_router.get("/api/templates/{id}/bom", response_model=ImageBOMResponse, tags=["Foundry"])
async def get_template_bom(
    id: str,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get the full Bill of Materials for a specific image."""
    result = await db.execute(select(ImageBOM).where(ImageBOM.template_id == id))
    bom = result.scalar_one_or_none()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found for this image")
    return bom


@foundry_router.get("/api/foundry/search-packages", response_model=List[PackageIndexResponse], tags=["Foundry"])
async def search_packages(
    q: str,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Search for images containing a specific package name/version across the fleet."""
    result = await db.execute(
        select(PackageIndex).where(PackageIndex.name.ilike(f"%{q}%")).limit(100)
    )
    return result.scalars().all()


# --- Capability Matrix ---

@foundry_router.get("/api/capability-matrix", response_model=List[CapabilityMatrixEntry], tags=["Foundry"])
async def get_capability_matrix(
    os_family: Annotated[Optional[str], Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CapabilityMatrix)
    if not include_inactive:
        stmt = stmt.where(CapabilityMatrix.is_active == True)
    if os_family:
        stmt = stmt.where(CapabilityMatrix.base_os_family == os_family.upper())
    result = await db.execute(stmt)
    return result.scalars().all()


@foundry_router.post("/api/capability-matrix", response_model=CapabilityMatrixEntry, tags=["Foundry"])
async def create_capability(
    req: CapabilityMatrixEntry,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Register a new tool capability recipe."""
    new_cap = CapabilityMatrix(
        base_os_family=req.base_os_family,
        tool_id=req.tool_id,
        injection_recipe=req.injection_recipe,
        validation_cmd=req.validation_cmd,
        artifact_id=req.artifact_id,
        runtime_dependencies=json.dumps(req.runtime_dependencies),
        is_active=req.is_active if req.is_active is not None else True,
    )
    db.add(new_cap)
    await db.commit()
    await db.refresh(new_cap)
    return new_cap


@foundry_router.patch("/api/capability-matrix/{id}", response_model=CapabilityMatrixEntry, tags=["Foundry"])
async def update_capability(
    id: int,
    req: CapabilityMatrixUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Partially update an existing tool recipe."""
    result = await db.execute(select(CapabilityMatrix).where(CapabilityMatrix.id == id))
    cap = result.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")

    if req.base_os_family is not None:
        cap.base_os_family = req.base_os_family
    if req.tool_id is not None:
        cap.tool_id = req.tool_id
    if req.injection_recipe is not None:
        cap.injection_recipe = req.injection_recipe
    if req.validation_cmd is not None:
        cap.validation_cmd = req.validation_cmd
    if req.artifact_id is not None:
        cap.artifact_id = req.artifact_id
    if req.runtime_dependencies is not None:
        cap.runtime_dependencies = json.dumps(req.runtime_dependencies)
    if req.is_active is not None:
        cap.is_active = req.is_active

    await db.commit()
    await db.refresh(cap)
    return cap


@foundry_router.delete("/api/capability-matrix/{id}", tags=["Foundry"])
async def delete_capability(
    id: int,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete a tool recipe (sets is_active=False). Returns referencing blueprints."""
    result = await db.execute(select(CapabilityMatrix).where(CapabilityMatrix.id == id))
    cap = result.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    # Find referencing blueprints by scanning definition JSON for tool_id
    all_bps = (await db.execute(select(Blueprint))).scalars().all()
    referencing = []
    for bp in all_bps:
        try:
            defn = json.loads(bp.definition)
            if cap.tool_id in [t.get("id") for t in defn.get("tools", [])]:
                referencing.append({"id": bp.id, "name": bp.name})
        except Exception:
            pass
    cap.is_active = False
    await db.commit()
    return {"status": "deactivated", "referencing_blueprints": referencing}


# --- Images ---

@foundry_router.post("/api/images", response_model=ImageResponse, tags=["Foundry"])
async def create_image(req: ImageBuildRequest, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return await foundry_service.build_image(req)


@foundry_router.get("/api/images", response_model=List[ImageResponse], tags=["Foundry"])
async def list_images(current_user: User = Depends(get_current_user)):
    return await foundry_service.list_images()


# --- Legacy/Frontend Aliases ---

@foundry_router.get("/foundry/definitions", tags=["Foundry"])
async def foundry_definitions(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/definitions instead of /api/blueprints"""
    return await list_blueprints(current_user, db)


@foundry_router.post("/foundry/build", tags=["Foundry"])
async def dashboard_foundry_build(req: dict, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/build with template_id in body"""
    template_id = req.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="Missing template_id in body")
    return await build_template(template_id, current_user, db)


# --- Base Image Staleness ---

@foundry_router.post("/admin/mark-base-updated", tags=["Admin"])
async def mark_base_updated(current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    """Records the current timestamp as the last time the base node image was updated."""
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    result = await db.execute(select(Config).where(Config.key == "base_node_image_updated_at"))
    row = result.scalar_one_or_none()
    if row:
        row.value = now
    else:
        db.add(Config(key="base_node_image_updated_at", value=now))
    audit(db, current_user, "base_image:marked_updated")
    await db.commit()
    return {"base_node_image_updated_at": now}


@foundry_router.get("/admin/base-image-updated", tags=["Admin"])
async def get_base_image_updated(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Config).where(Config.key == "base_node_image_updated_at"))
    row = result.scalar_one_or_none()
    return {"base_node_image_updated_at": row.value if row else None}


# --- Approved OS ---

@foundry_router.get("/api/approved-os", response_model=List[ApprovedOSResponse], tags=["Foundry"])
async def list_approved_os(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all pre-approved base OS images."""
    result = await db.execute(select(ApprovedOS).order_by(ApprovedOS.name))
    return result.scalars().all()


@foundry_router.post("/api/approved-os", response_model=ApprovedOSResponse, tags=["Foundry"])
async def create_approved_os(
    req: ApprovedOSCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Register a new approved base OS image."""
    new_os = ApprovedOS(name=req.name, image_uri=req.image_uri, os_family=req.os_family)
    db.add(new_os)
    await db.commit()
    await db.refresh(new_os)
    return new_os


@foundry_router.patch("/api/approved-os/{id}", response_model=ApprovedOSResponse, tags=["Foundry"])
async def update_approved_os(
    id: int,
    req: ApprovedOSUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing approved base OS entry."""
    result = await db.execute(select(ApprovedOS).where(ApprovedOS.id == id))
    os_entry = result.scalar_one_or_none()
    if not os_entry:
        raise HTTPException(status_code=404, detail="OS entry not found")
    if req.name is not None:
        os_entry.name = req.name
    if req.image_uri is not None:
        os_entry.image_uri = req.image_uri
    if req.os_family is not None:
        os_entry.os_family = req.os_family
    await db.commit()
    await db.refresh(os_entry)
    return os_entry


@foundry_router.delete("/api/approved-os/{id}", tags=["Foundry"])
async def delete_approved_os(
    id: int,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Remove a base image from the approved list. Returns 409 if referenced by any blueprint."""
    result = await db.execute(select(ApprovedOS).where(ApprovedOS.id == id))
    os_entry = result.scalar_one_or_none()
    if not os_entry:
        raise HTTPException(status_code=404, detail="OS entry not found")
    # Referential integrity check
    all_bps = (await db.execute(select(Blueprint))).scalars().all()
    for bp in all_bps:
        try:
            defn = json.loads(bp.definition) if bp.definition else {}
            if defn.get("base_os") == os_entry.image_uri:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete: referenced by blueprint '{bp.name}'"
                )
        except (json.JSONDecodeError, TypeError):
            pass
    await db.delete(os_entry)
    await db.commit()
    return {"status": "deleted"}

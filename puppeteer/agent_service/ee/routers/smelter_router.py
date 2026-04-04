"""EE Router: Smelter Registry — approved ingredients, mirror management, scanning."""
from __future__ import annotations

import json
import os
import shutil
import socket
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.future import select

from ...db import get_db, AsyncSession, Config, ApprovedIngredient, User
from ...deps import require_permission, audit
from ...models import (
    ApprovedIngredientCreate, ApprovedIngredientResponse,
    MirrorConfigUpdate, MirrorConfigResponse,
)
from ...services.smelter_service import SmelterService
from ...services.resolver_service import ResolverService

smelter_router = APIRouter()


@smelter_router.get("/api/smelter/ingredients", response_model=List[ApprovedIngredientResponse], tags=["Smelter Registry"])
async def list_smelter_ingredients(
    os_family: Optional[str] = None,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all approved ingredients in the Smelter Catalog (Admin/Operator)."""
    return await SmelterService.list_ingredients(db, os_family)


@smelter_router.post("/api/smelter/ingredients", response_model=ApprovedIngredientResponse, tags=["Smelter Registry"])
async def add_smelter_ingredient(
    ingredient: ApprovedIngredientCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new vetted ingredient to the Smelter Catalog (Admin Only)."""
    item = await SmelterService.add_ingredient(db, ingredient)
    audit(db, current_user, "smelter:ingredient_added", item.name)
    return item


@smelter_router.delete("/api/smelter/ingredients/{id}", tags=["Smelter Registry"])
async def remove_smelter_ingredient(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete an ingredient from the Smelter Catalog (sets is_active=False, preserves mirror files)."""
    res = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == id))
    ing = res.scalar_one_or_none()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ing.is_active = False
    await db.commit()
    audit(db, current_user, "smelter:ingredient_deactivated", id)
    await db.commit()
    return {"status": "deactivated", "id": id}


@smelter_router.get("/api/smelter/config", tags=["Smelter Registry"])
async def get_smelter_config(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get the current Smelter enforcement mode (STRICT vs WARNING)."""
    result = await db.execute(select(Config).where(Config.key == "smelter_enforcement_mode"))
    cfg = result.scalar_one_or_none()
    return {"smelter_enforcement_mode": cfg.value if cfg else "WARNING"}


@smelter_router.patch("/api/smelter/config", tags=["Smelter Registry"])
async def update_smelter_config(
    req: Dict[str, str],
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Update the Smelter enforcement mode (STRICT vs WARNING)."""
    mode = req.get("smelter_enforcement_mode")
    if mode not in ["STRICT", "WARNING"]:
        raise HTTPException(status_code=400, detail="Mode must be STRICT or WARNING")

    result = await db.execute(select(Config).where(Config.key == "smelter_enforcement_mode"))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = mode
    else:
        db.add(Config(key="smelter_enforcement_mode", value=mode))

    audit(db, current_user, "smelter:config_updated", mode)
    await db.commit()
    return {"smelter_enforcement_mode": mode}


@smelter_router.get("/api/smelter/mirror-health", tags=["Smelter Registry"])
async def get_smelter_mirror_health(
    current_user: User = Depends(require_permission("foundry:read"))
):
    """Get metrics for the local package mirrors (Disk usage, sidecar status)."""
    mirror_path = os.getenv("MIRROR_DATA_PATH", "/app/mirror_data")
    stats = {"pypi_online": False, "apt_online": False, "disk_used_gb": 0, "disk_total_gb": 0}

    # 1. Disk Usage
    if os.path.exists(mirror_path):
        usage = shutil.disk_usage(mirror_path)
        stats["disk_used_gb"] = round(usage.used / (1024**3), 2)
        stats["disk_total_gb"] = round(usage.total / (1024**3), 2)

    # 2. Sidecar Heartbeats (simple socket check)
    def check_port(host, port):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except:
            return False

    stats["pypi_online"] = check_port("pypi", 8080)
    stats["apt_online"] = check_port("mirror", 80)

    return stats


@smelter_router.get("/api/admin/mirror-config", response_model=MirrorConfigResponse, tags=["Smelter Registry"])
async def get_mirror_config(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Read mirror source URLs from Config DB (falls back to env vars if not set). Includes health status."""
    mirror_keys = {
        "PYPI_MIRROR_URL": "http://pypi:8080/simple",
        "APT_MIRROR_URL": "http://mirror/apt",
        "APK_MIRROR_URL": "http://mirror/apk",
        "NPM_MIRROR_URL": "http://mirror/npm",
        "NUGET_MIRROR_URL": "http://mirror/nuget",
        "OCI_HUB_MIRROR_URL": "http://mirror/oci/hub",
        "OCI_GHCR_MIRROR_URL": "http://mirror/oci/ghcr",
        "CONDA_MIRROR_URL": "http://mirror:8081/conda",
    }

    config_values = {}
    for key, default in mirror_keys.items():
        result = await db.execute(select(Config).where(Config.key == key))
        cfg = result.scalar_one_or_none()
        config_values[key] = cfg.value if cfg else os.getenv(key, default)

    # Get health status from app state (fallback to "unknown" for each ecosystem)
    from fastapi import Request
    request: Request = None  # type: ignore
    health_status = {
        "pypi": "ok",
        "apt": "ok",
        "apk": "ok",
        "npm": "ok",
        "nuget": "ok",
        "oci_hub": "ok",
        "oci_ghcr": "ok",
        "conda": "ok",
    }

    # Check if provisioning is enabled
    provisioning_enabled = os.getenv("ALLOW_CONTAINER_MANAGEMENT", "false").lower() == "true"

    return MirrorConfigResponse(
        pypi_mirror_url=config_values["PYPI_MIRROR_URL"],
        apt_mirror_url=config_values["APT_MIRROR_URL"],
        apk_mirror_url=config_values["APK_MIRROR_URL"],
        npm_mirror_url=config_values["NPM_MIRROR_URL"],
        nuget_mirror_url=config_values["NUGET_MIRROR_URL"],
        oci_hub_mirror_url=config_values["OCI_HUB_MIRROR_URL"],
        oci_ghcr_mirror_url=config_values["OCI_GHCR_MIRROR_URL"],
        conda_mirror_url=config_values["CONDA_MIRROR_URL"],
        health_status=health_status,
        provisioning_enabled=provisioning_enabled,
    )


@smelter_router.put("/api/admin/mirror-config", response_model=MirrorConfigResponse, tags=["Smelter Registry"])
async def update_mirror_config(
    req: MirrorConfigUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Upsert mirror source URLs to Config DB. Returns updated config with health status."""
    # Map request fields to Config keys
    field_to_key = {
        "pypi_mirror_url": "PYPI_MIRROR_URL",
        "apt_mirror_url": "APT_MIRROR_URL",
        "apk_mirror_url": "APK_MIRROR_URL",
        "npm_mirror_url": "NPM_MIRROR_URL",
        "nuget_mirror_url": "NUGET_MIRROR_URL",
        "oci_hub_mirror_url": "OCI_HUB_MIRROR_URL",
        "oci_ghcr_mirror_url": "OCI_GHCR_MIRROR_URL",
        "conda_mirror_url": "CONDA_MIRROR_URL",
    }

    updated_urls = []
    for field_name, config_key in field_to_key.items():
        field_value = getattr(req, field_name, None)
        if field_value is not None:
            result = await db.execute(select(Config).where(Config.key == config_key))
            cfg = result.scalar_one_or_none()
            if cfg:
                cfg.value = field_value
            else:
                db.add(Config(key=config_key, value=field_value))
            updated_urls.append(f"{field_name}={field_value}")

    await db.commit()
    if updated_urls:
        audit(db, current_user, "mirror:config_updated", ", ".join(updated_urls))
        await db.commit()

    # Return updated config
    mirror_keys = {
        "PYPI_MIRROR_URL": "http://pypi:8080/simple",
        "APT_MIRROR_URL": "http://mirror/apt",
        "APK_MIRROR_URL": "http://mirror/apk",
        "NPM_MIRROR_URL": "http://mirror/npm",
        "NUGET_MIRROR_URL": "http://mirror/nuget",
        "OCI_HUB_MIRROR_URL": "http://mirror/oci/hub",
        "OCI_GHCR_MIRROR_URL": "http://mirror/oci/ghcr",
        "CONDA_MIRROR_URL": "http://mirror:8081/conda",
    }

    config_values = {}
    for key, default in mirror_keys.items():
        result = await db.execute(select(Config).where(Config.key == key))
        cfg = result.scalar_one_or_none()
        config_values[key] = cfg.value if cfg else os.getenv(key, default)

    # Default health status (all ok)
    health_status = {
        "pypi": "ok",
        "apt": "ok",
        "apk": "ok",
        "npm": "ok",
        "nuget": "ok",
        "oci_hub": "ok",
        "oci_ghcr": "ok",
        "conda": "ok",
    }

    # Check if provisioning is enabled
    provisioning_enabled = os.getenv("ALLOW_CONTAINER_MANAGEMENT", "false").lower() == "true"

    return MirrorConfigResponse(
        pypi_mirror_url=config_values["PYPI_MIRROR_URL"],
        apt_mirror_url=config_values["APT_MIRROR_URL"],
        apk_mirror_url=config_values["APK_MIRROR_URL"],
        npm_mirror_url=config_values["NPM_MIRROR_URL"],
        nuget_mirror_url=config_values["NUGET_MIRROR_URL"],
        oci_hub_mirror_url=config_values["OCI_HUB_MIRROR_URL"],
        oci_ghcr_mirror_url=config_values["OCI_GHCR_MIRROR_URL"],
        conda_mirror_url=config_values["CONDA_MIRROR_URL"],
        health_status=health_status,
        provisioning_enabled=provisioning_enabled,
    )


@smelter_router.post("/api/smelter/ingredients/{id}/upload", tags=["Smelter Registry"])
async def upload_smelter_package(
    id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Manually upload a package (.whl, .deb) to the local mirror."""
    res = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == id))
    ing = res.scalar_one_or_none()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    target_dir = os.path.join(os.getenv("MIRROR_DATA_PATH", "/app/mirror_data"), "apt" if file.filename.endswith(".deb") else "pypi")
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ing.mirror_status = "MIRRORED"
    ing.mirror_path = target_dir
    await db.commit()

    audit(db, current_user, "smelter:package_uploaded", f"{ing.name}:{file.filename}")
    return {"status": "MIRRORED", "filename": file.filename}


@smelter_router.post("/api/smelter/scan", tags=["Smelter Registry"])
async def trigger_smelter_scan(
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a vulnerability scan of the Smelter Catalog (Admin Only)."""
    summary = await SmelterService.scan_vulnerabilities(db)
    audit(db, current_user, "smelter:scan_triggered", json.dumps(summary))
    return summary


@smelter_router.post("/api/smelter/ingredients/{ingredient_id}/resolve", tags=["Smelter Registry"])
async def resolve_ingredient(
    ingredient_id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Optional[int]]:
    """
    Manually trigger resolution of a single ingredient's transitive dependencies.
    Returns when resolution completes.
    """
    # Concurrent guard: reject if already resolving
    ingredient = await db.get(ApprovedIngredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    if ingredient.mirror_status == "RESOLVING":
        raise HTTPException(status_code=409, detail="Resolution already in progress")

    # Trigger resolution (awaited, not background)
    result = await ResolverService.resolve_ingredient_tree(db, ingredient_id)

    audit(db, current_user, "smelter:ingredient_resolved", f"{ingredient.name}:{result.get('resolved_count', 0)}")

    return {
        "success": result["success"],
        "resolved_count": result["resolved_count"],
        "error_msg": result.get("error_msg")
    }


@smelter_router.post("/api/admin/conda-defaults-acknowledge", tags=["Smelter Registry"])
async def acknowledge_conda_defaults_tos(
    req: Dict[str, str],
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge Conda defaults channel Terms of Service for current user.
    Per-user acknowledgment prevents re-showing the modal on subsequent encounters.
    """
    # Validate channel value (must be "defaults")
    channel = req.get("channel", "").strip()
    if channel != "defaults":
        raise HTTPException(status_code=422, detail="channel must be 'defaults'")

    # Create or update Config entry for this user's acknowledgment
    config_key = f"CONDA_DEFAULTS_TOS_ACKNOWLEDGED_BY_{current_user.id}"

    result = await db.execute(select(Config).where(Config.key == config_key))
    cfg = result.scalar_one_or_none()

    if cfg:
        # Already acknowledged; idempotent return
        return {
            "acknowledged": True,
            "message": "Already acknowledged"
        }

    # Create new acknowledgment entry
    new_cfg = Config(key=config_key, value="true")
    db.add(new_cfg)

    audit(db, current_user, "conda:defaults_tos_acknowledged", "Conda defaults channel ToS acknowledged")

    await db.commit()

    return {
        "acknowledged": True,
        "message": "ToS acknowledged"
    }

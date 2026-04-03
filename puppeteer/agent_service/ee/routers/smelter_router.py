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
    MirrorConfigUpdate,
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


@smelter_router.get("/api/admin/mirror-config", tags=["Smelter Registry"])
async def get_mirror_config(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Read mirror source URLs from Config DB (falls back to env vars if not set)."""
    pypi_res = await db.execute(select(Config).where(Config.key == "PYPI_MIRROR_URL"))
    pypi_cfg = pypi_res.scalar_one_or_none()
    apt_res = await db.execute(select(Config).where(Config.key == "APT_MIRROR_URL"))
    apt_cfg = apt_res.scalar_one_or_none()
    return {
        "pypi_mirror_url": pypi_cfg.value if pypi_cfg else os.getenv("PYPI_MIRROR_URL", "http://pypi:8080/simple"),
        "apt_mirror_url": apt_cfg.value if apt_cfg else os.getenv("APT_MIRROR_URL", "http://mirror/apt"),
    }


@smelter_router.put("/api/admin/mirror-config", tags=["Smelter Registry"])
async def update_mirror_config(
    req: MirrorConfigUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Upsert mirror source URLs to Config DB."""
    if req.pypi_mirror_url is not None:
        pypi_res = await db.execute(select(Config).where(Config.key == "PYPI_MIRROR_URL"))
        pypi_cfg = pypi_res.scalar_one_or_none()
        if pypi_cfg:
            pypi_cfg.value = req.pypi_mirror_url
        else:
            db.add(Config(key="PYPI_MIRROR_URL", value=req.pypi_mirror_url))
    if req.apt_mirror_url is not None:
        apt_res = await db.execute(select(Config).where(Config.key == "APT_MIRROR_URL"))
        apt_cfg = apt_res.scalar_one_or_none()
        if apt_cfg:
            apt_cfg.value = req.apt_mirror_url
        else:
            db.add(Config(key="APT_MIRROR_URL", value=req.apt_mirror_url))
    await db.commit()
    audit(db, current_user, "mirror:config_updated", f"pypi={req.pypi_mirror_url}, apt={req.apt_mirror_url}")
    await db.commit()
    return {"status": "updated"}


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

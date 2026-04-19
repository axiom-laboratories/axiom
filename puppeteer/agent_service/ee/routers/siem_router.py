"""EE Router: SIEM audit streaming configuration (Phase 168)."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db, SIEMConfig, User
from ...deps import require_permission, audit, require_ee
from ...models import (
    SIEMConfigResponse,
    SIEMConfigUpdateRequest,
    SIEMTestConnectionRequest,
    SIEMTestConnectionResponse,
    SIEMStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin/siem/config", response_model=SIEMConfigResponse, tags=["SIEM Configuration"])
async def get_config(
    current_user: User = Depends(require_ee()),
    _perm: User = Depends(require_permission("system:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get current SIEM configuration."""
    result = await db.execute(select(SIEMConfig).limit(1))
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="SIEM config not found")
    return SIEMConfigResponse.from_siem_config(config)


@router.patch("/admin/siem/config", response_model=SIEMConfigResponse, tags=["SIEM Configuration"])
async def update_config(
    req: SIEMConfigUpdateRequest,
    request: Request,
    current_user: User = Depends(require_ee()),
    _perm: User = Depends(require_permission("system:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update SIEM configuration. Reinitialize service if enabled changed."""
    result = await db.execute(select(SIEMConfig).limit(1))
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="SIEM config not found")

    # Update only provided fields
    if req.backend is not None:
        config.backend = req.backend
    if req.destination is not None:
        config.destination = req.destination
    if req.syslog_port is not None:
        config.syslog_port = req.syslog_port
    if req.syslog_protocol is not None:
        config.syslog_protocol = req.syslog_protocol
    if req.cef_device_vendor is not None:
        config.cef_device_vendor = req.cef_device_vendor
    if req.cef_device_product is not None:
        config.cef_device_product = req.cef_device_product
    if req.enabled is not None:
        config.enabled = req.enabled

    # Audit the update
    audit(db, current_user, "siem:config_update", config.id, {
        "backend": req.backend,
        "destination_updated": req.destination is not None,
        "syslog_port": req.syslog_port,
        "syslog_protocol": req.syslog_protocol,
        "cef_device_vendor": req.cef_device_vendor,
        "cef_device_product": req.cef_device_product,
        "enabled": req.enabled,
    })

    await db.commit()
    await db.refresh(config)

    # Hot-reload: reinitialize singleton so config takes effect without restart (SIEM-01)
    # Without this, changes only apply after a process restart.
    try:
        from ee.services.siem_service import SIEMService, set_active, get_siem_service
        from ...services.scheduler_service import scheduler_service

        old = get_siem_service()
        if old:
            await old.shutdown()
        if config.enabled:
            new_siem = SIEMService(config, db, scheduler_service.scheduler)
            await new_siem.startup()
            set_active(new_siem)
        else:
            set_active(None)
    except Exception as e:
        logger.warning(f"Failed to reinitialize SIEM service: {e}")
        # Don't fail the response — config was saved; reinit is best-effort

    return SIEMConfigResponse.from_siem_config(config)


@router.post("/admin/siem/test-connection", response_model=SIEMTestConnectionResponse, tags=["SIEM Configuration"])
async def test_connection(
    req: SIEMTestConnectionRequest,
    current_user: User = Depends(require_ee()),
    _perm: User = Depends(require_permission("system:write")),
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity to the configured SIEM destination."""
    status = "disabled"
    try:
        from ee.services.siem_service import SIEMService, get_siem_service
        from ...db import AsyncSessionLocal
        from ...services.scheduler_service import scheduler_service

        # Create temporary test config
        test_config = SIEMConfig(
            id="test-connection",
            backend=req.backend,
            destination=req.destination,
            syslog_port=req.syslog_port,
            syslog_protocol=req.syslog_protocol,
            cef_device_vendor=req.cef_device_vendor or "Axiom",
            cef_device_product=req.cef_device_product or "MasterOfPuppets",
            enabled=True,
        )

        # Create test service and attempt connection
        async with AsyncSessionLocal() as test_db:
            test_service = SIEMService(test_config, test_db, scheduler_service.scheduler)
            try:
                await test_service.startup()
                status = await test_service.status()
            finally:
                await test_service.shutdown()

        # Audit the test attempt
        audit(db, current_user, "siem:test_connection", req.destination, {
            "backend": req.backend,
            "status": status,
            "success": status == "healthy",
        })
        await db.commit()

        if status == "healthy":
            return SIEMTestConnectionResponse(
                success=True,
                status=status,
                message="Successfully connected to SIEM destination"
            )
        else:
            return SIEMTestConnectionResponse(
                success=False,
                status=status,
                error_detail=f"SIEM status is {status}",
                message=f"Connection attempted but SIEM status is {status}"
            )

    except Exception as e:
        logger.error(f"SIEM test connection failed: {e}")
        error_msg = str(e)

        # Audit the failed attempt
        audit(db, current_user, "siem:test_connection_failed", req.destination, {
            "backend": req.backend,
            "error": error_msg,
        })
        await db.commit()

        return SIEMTestConnectionResponse(
            success=False,
            status="disabled",
            error_detail=error_msg,
            message=f"Connection test failed: {error_msg}"
        )


@router.get("/admin/siem/status", response_model=SIEMStatusResponse, tags=["SIEM Configuration"])
async def get_status(
    current_user: User = Depends(require_ee()),
    _perm: User = Depends(require_permission("system:read")),
):
    """Retrieve SIEM service status."""
    from ee.services.siem_service import get_siem_service

    siem = get_siem_service()
    if not siem:
        return SIEMStatusResponse(status="disabled")

    detail = siem.status_detail()
    return SIEMStatusResponse(
        status=detail["status"],
        backend=detail["backend"],
        destination=detail["destination"],
        last_checked_at=detail["last_checked_at"],
        error_detail=detail["error_detail"] if detail["consecutive_failures"] > 0 else None,
        consecutive_failures=detail["consecutive_failures"],
        dropped_events=detail["dropped_events"],
    )

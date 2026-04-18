"""
System domain router: health checks, features, license status, CRL, config, schedule, WebSocket feed.

Endpoints include:
- Health checks (root, system health, scheduling health, scale health)
- Feature flags (EE activation status)
- License status
- Network configuration (mounts)
- Job schedule (APScheduler jobs)
- Certificate Revocation List (CRL)
- WebSocket live event feed
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func as sqlfunc
from typing import Optional, List
import logging
import json
from datetime import datetime

from ..db import (
    get_db, AsyncSession, AsyncSessionLocal, User, Config, RevokedCert, ScheduledJob, Job
)
from ..deps import (
    get_current_user, require_auth, require_permission, audit
)
from ..models import (
    SystemHealthResponse, SchedulingHealthResponse, ScaleHealthResponse,
    FeaturesResponse, LicenceStatusResponse, NetworkMount, ScheduleListResponse,
    JobDefinitionResponse
)
from ..services.pki_service import pki_service
from ..services.licence_service import LicenceState

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Health Checks ---

@router.get(
    "/",
    response_model=dict,
    tags=["System"],
    summary="Health check endpoint",
    description="Simple health check that returns service status and mirror availability"
)
async def health_check(request: Request):
    mirrors_available = getattr(request.app.state, "mirrors_available", True)
    return {
        "status": "healthy",
        "service": "Agent Service v0.7",
        "mirrors_available": mirrors_available
    }


@router.get("/system/health", response_model=SystemHealthResponse, tags=["System"])
async def system_health(request: Request):
    mirrors_available = getattr(request.app.state, "mirrors_available", True)

    # Add Vault status if configured
    vault_status = None
    vault_service = getattr(request.app.state, "vault_service", None)
    if vault_service is not None:
        vault_status = await vault_service.status()

    # Add SIEM status if configured (Phase 168)
    siem_status = None
    try:
        from ..ee.services.siem_service import get_siem_service
        siem = get_siem_service()
        if siem is not None:
            siem_status = await siem.status()
    except ImportError:
        pass

    return {
        "status": "healthy",
        "mirrors_available": mirrors_available,
        "vault": vault_status,
        "siem": siem_status
    }


@router.get("/api/health/scheduling", response_model=SchedulingHealthResponse, tags=["Health"])
async def get_scheduling_health_endpoint(
    window: str = "24h",
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    from ..services.scheduler_service import scheduler_service
    if window not in ("24h", "7d", "30d"):
        raise HTTPException(status_code=422, detail="window must be 24h, 7d, or 30d")
    data = await scheduler_service.get_scheduling_health(window, db)
    return SchedulingHealthResponse(**data, window=window)


@router.get("/health/scale", response_model=ScaleHealthResponse, tags=["Health"])
async def get_scale_health_endpoint(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Return live pool and scheduler health metrics."""
    from ..db import engine, IS_POSTGRES
    from ..services.scheduler_service import scheduler_service

    # APScheduler job count
    apscheduler_jobs = len(scheduler_service.scheduler.get_jobs())

    # Pending job depth
    result = await db.execute(
        select(sqlfunc.count(Job.guid)).where(Job.status == "PENDING")
    )
    pending_depth = result.scalar() or 0

    if not IS_POSTGRES:
        return ScaleHealthResponse(
            is_postgres=False,
            pool_size=None,
            checked_out=None,
            available=None,
            overflow=None,
            apscheduler_jobs=apscheduler_jobs,
            pending_job_depth=pending_depth,
        )

    pool = engine.pool
    return ScaleHealthResponse(
        is_postgres=True,
        pool_size=pool.size(),
        checked_out=pool.checkedout(),
        available=pool.checkedin(),
        overflow=pool.overflow(),
        apscheduler_jobs=apscheduler_jobs,
        pending_job_depth=pending_depth,
    )


# --- Features & License ---

@router.get("/api/features", response_model=FeaturesResponse, tags=["System"])
async def get_features(request: Request):
    ctx = getattr(request.app.state, "ee", None)
    if ctx is None:
        return {
            "audit": False,
            "foundry": False,
            "webhooks": False,
            "triggers": False,
            "rbac": False,
            "resource_limits": False,
            "service_principals": False,
            "api_keys": False,
            "executions": False
        }
    return {
        "audit": ctx.audit,
        "foundry": ctx.foundry,
        "webhooks": ctx.webhooks,
        "triggers": ctx.triggers,
        "rbac": ctx.rbac,
        "resource_limits": ctx.resource_limits,
        "service_principals": ctx.service_principals,
        "api_keys": ctx.api_keys,
        "executions": ctx.executions,
    }


@router.get("/api/licence", response_model=LicenceStatusResponse, tags=["System"])
async def get_licence_status(request: Request, current_user: User = Depends(require_auth)):
    """Returns current licence status. Requires authentication."""
    ls: Optional[LicenceState] = getattr(request.app.state, "licence_state", None)
    ee_error = getattr(request.app.state, "ee_activation_error", None)
    if ls is None:
        # CE mode — no licence loaded
        return {
            "status": "ce",
            "days_until_expiry": 0,
            "node_limit": 0,
            "tier": "ce",
            "customer_id": None,
            "grace_days": 0,
            "ee_activation_error": ee_error,
        }
    return {
        "status": ls.status.value if hasattr(ls.status, "value") else str(ls.status),
        "days_until_expiry": ls.days_until_expiry,
        "node_limit": ls.node_limit,
        "tier": ls.tier,
        "customer_id": ls.customer_id,
        "grace_days": ls.grace_days,
        "ee_activation_error": ee_error,
    }


# --- Schedule Endpoints ---

@router.get(
    "/api/schedule",
    response_model=ScheduleListResponse,
    tags=["Schedule"],
    summary="List scheduled jobs",
    description="Retrieve list of scheduled jobs with next run times"
)
async def list_schedule(
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all scheduled jobs from APScheduler."""
    from ..services.scheduler_service import scheduler_service

    jobs = []
    for sched_job in scheduler_service.scheduler.get_jobs():
        next_run = sched_job.next_run_time.isoformat() if sched_job.next_run_time else None
        jobs.append({
            "id": sched_job.id,
            "name": sched_job.name or sched_job.id,
            "next_run": next_run,
            "trigger": str(sched_job.trigger) if sched_job.trigger else None,
        })
    return {"jobs": jobs, "total": len(jobs)}


# --- Certificate Revocation List (CRL) ---

@router.get(
    "/system/crl.pem",
    response_class=Response,
    tags=["System"],
    summary="Get Certificate Revocation List",
    description="Returns signed X.509 CRL (Certificate Revocation List) of all revoked node client certificates"
)
async def get_crl(db: AsyncSession = Depends(get_db)):
    """Returns a signed X.509 CRL of all revoked node certificates."""
    result = await db.execute(select(RevokedCert))
    revoked = result.scalars().all()
    serials = [r.serial_number for r in revoked]
    crl_pem = pki_service.ca_authority.generate_crl(serials)
    return Response(content=crl_pem, media_type="application/x-pem-file")


# --- WebSocket Live Feed ---

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = None):
    """Live event feed. Requires a valid JWT passed as ?token=<jwt> query param."""
    await ws.accept()
    # Validate token using a short-lived session so we don't hold a pool slot
    # for the entire WebSocket lifetime (which exhausts the connection pool).
    authed = False
    if token:
        try:
            from jose import jwt as _jwt, JWTError
            from ..auth import SECRET_KEY, ALGORITHM
            payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username:
                async with AsyncSessionLocal() as _db:
                    result = await _db.execute(select(User).where(User.username == username))
                    user = result.scalar_one_or_none()
                    if user and payload.get("tv", 0) == user.token_version:
                        authed = True
        except Exception:
            pass
    if not authed:
        await ws.close(code=1008)
        return

    from ..main import ws_manager
    ws_manager._connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

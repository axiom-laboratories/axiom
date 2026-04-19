"""
Admin domain router: user/role management, signatures, alerts, system config, signals, and admin tokens.

Endpoints include:
- User management (CRUD)
- Role management (permissions)
- Signature management (Ed25519 key registration)
- Alert management (acknowledgement)
- System configuration (keys, mounts)
- Headless Automation (signals)
- Admin enrollment tokens
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func as sqlfunc
from typing import Optional, List
import logging
import uuid
import json
import base64
from datetime import datetime, timedelta

from ..db import (
    get_db, AsyncSession, User, Signature, Alert, Signal, Token, Config,
    ScheduledJob, ExecutionRecord
)
from ..deps import (
    get_current_user, get_current_user_optional, require_auth,
    require_permission, audit
)
from ..models import (
    SignatureCreate, SignatureResponse, AlertResponse, SignalResponse,
    SignalFire, ActionResponse, EnrollmentTokenResponse, UploadKeyRequest,
    LicenceReloadResponse, LicenceReloadRequest, NetworkMount, RetentionConfigUpdate
)
from ..services.signature_service import SignatureService
from ..services.alert_service import AlertService
from ..services.pki_service import pki_service
from ..auth import get_password_hash
from ..security import verify_node_secret

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Signatures API ---

@router.post("/signatures", response_model=SignatureResponse, tags=["Signatures"])
async def upload_signature(
    sig: SignatureCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Upload an Ed25519 public key for job script signing."""
    return await SignatureService.upload_signature(sig, current_user, db)


@router.get("/signatures", response_model=List[SignatureResponse], tags=["Signatures"])
async def list_signatures(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List all registered signature keys."""
    return await SignatureService.list_signatures(db)


@router.get(
    "/signatures/{id}",
    response_model=SignatureResponse,
    tags=["Signatures"],
    summary="Get signature key",
    description="Get a signature key by ID. Unauthenticated (nodes need to fetch for verification)."
)
async def get_signature(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a signature by ID. Unauthenticated (nodes need to fetch this for verification)."""
    result = await db.execute(select(Signature).where(Signature.id == id))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    return sig


@router.delete(
    "/signatures/{id}",
    response_model=ActionResponse,
    tags=["Signatures"]
)
async def delete_signature(
    id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a signature key."""
    success = await SignatureService.delete_signature(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Signature not found")
    audit(db, current_user, "signature:delete", id)
    await db.commit()
    return {"status": "deleted", "resource_type": "signature", "resource_id": id}


# --- Alerts API ---

@router.get(
    "/api/alerts",
    response_model=List[AlertResponse],
    tags=["Alerts & Webhooks"],
    summary="List system alerts",
    description="Retrieve system alerts with optional filtering"
)
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    unacknowledged_only: bool = False,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List system alerts with optional filtering."""
    return await AlertService.list_alerts(db, skip, limit, unacknowledged_only)


@router.post(
    "/api/alerts/{alert_id}/acknowledge",
    response_model=ActionResponse,
    tags=["Alerts & Webhooks"],
    summary="Acknowledge an alert",
    description="Mark an alert as acknowledged by ID"
)
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Mark an alert as acknowledged."""
    alert = await AlertService.acknowledge_alert(db, alert_id, current_user.username)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    audit(db, current_user, "alert:acknowledge", str(alert_id))
    await db.commit()
    return {"status": "acknowledged", "resource_type": "alert", "resource_id": alert_id}


# --- Admin Enrollment Tokens ---

@router.post(
    "/admin/generate-token",
    response_model=EnrollmentTokenResponse,
    tags=["Admin"],
    summary="Generate enrollment token",
    description="Generate a new enrollment token for node enrollment"
)
async def generate_token(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Generate an enrollment token for node enrollment."""
    token_str = uuid.uuid4().hex
    token_entry = Token(token=token_str)
    db.add(token_entry)
    await db.commit()

    ca_pem = pki_service.get_root_cert_pem()

    payload = {
        "t": token_str,
        "ca": ca_pem
    }

    b64_token = base64.b64encode(json.dumps(payload).encode()).decode()
    return EnrollmentTokenResponse(token=b64_token)


# --- Admin Key Management ---

@router.post(
    "/admin/upload-key",
    response_model=ActionResponse,
    tags=["Admin"],
    summary="Upload signing public key",
    description="Upload or update the Ed25519 public key for job script verification"
)
async def upload_public_key(
    req: UploadKeyRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Upload or update the signing public key."""
    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if row:
        row.value = req.key_content
    else:
        db.add(Config(key="signing_public_key", value=req.key_content))
    audit(db, current_user, "key:upload")
    await db.commit()
    return ActionResponse(
        status="created",
        resource_type="public_key",
        resource_id="signing_public_key",
        message="Public key uploaded and stored"
    )


@router.get(
    "/config/public-key",
    response_model=dict,
    tags=["System"],
    summary="Get signing public key",
    description="Returns the Ed25519 public key for job script signature verification"
)
async def get_public_key(
    x_join_token: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Get the signing public key (node enrollment only)."""
    result = await db.execute(select(Token).where(Token.token == x_join_token))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Invalid Join Token")

    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"public_key": row.value}


# --- Configuration Endpoints ---

@router.get(
    "/config/mounts",
    response_model=List[NetworkMount],
    tags=["System"],
    summary="Get network mount configuration",
    description="Retrieve configured network mounts for nodes"
)
async def get_network_mounts(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    x_join_token: Optional[str] = Header(None)
):
    """Get configured network mounts (authenticated or valid token)."""
    is_authed = user is not None
    is_valid_token = False

    if x_join_token:
        result = await db.execute(select(Token).where(Token.token == x_join_token))
        if result.scalar_one_or_none():
            is_valid_token = True

    if not (is_authed or is_valid_token):
        raise HTTPException(status_code=403, detail="Not Authorized")

    result = await db.execute(select(Config).where(Config.key == "global_network_mounts"))
    row = result.scalar_one_or_none()
    if not row:
        return []
    try:
        data = json.loads(row.value)
        return [NetworkMount(**m) for m in data]
    except:
        return []


@router.post(
    "/config/mounts",
    response_model=ActionResponse,
    tags=["System"],
    summary="Update network mount configuration",
    description="Configure network mounts for nodes"
)
async def set_network_mounts(
    mounts: List[NetworkMount],
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update network mount configuration."""
    result = await db.execute(select(Config).where(Config.key == "global_network_mounts"))
    row = result.scalar_one_or_none()
    mounts_json = json.dumps([m.dict() for m in mounts])
    if row:
        row.value = mounts_json
    else:
        db.add(Config(key="global_network_mounts", value=mounts_json))
    audit(db, current_user, "config:mounts_updated", detail={"count": len(mounts)})
    await db.commit()
    return ActionResponse(
        status="updated",
        resource_type="config",
        resource_id="global_network_mounts",
        message=f"Network mounts updated ({len(mounts)} mounts)"
    )


# --- Headless Automation: Signals ---

@router.post(
    "/api/signals/{name}",
    response_model=SignalResponse,
    tags=["Headless Automation"],
    summary="Fire a named signal",
    description="Fire a named signal to unblock dependent jobs waiting on signal conditions"
)
async def fire_signal(
    name: str,
    req: Optional[SignalFire] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Fire a named signal to unblock dependent jobs."""
    # Import at handler scope to avoid circular imports
    from ..services.workflow_service import workflow_service
    from ..services.job_service import JobService

    # Upsert signal
    result = await db.execute(select(Signal).where(Signal.name == name))
    sig = result.scalar_one_or_none()

    payload_json = json.dumps(req.payload) if req and req.payload else None

    if sig:
        sig.payload = payload_json
        sig.created_at = datetime.utcnow()
    else:
        sig = Signal(name=name, payload=payload_json)
        db.add(sig)

    audit(db, current_user, "signal:fire", name)
    await db.commit()

    # Trigger workflow advancement for SIGNAL_WAIT steps
    await workflow_service.advance_signal_wait(name, db)

    # Trigger unblocking
    await JobService.unblock_jobs_by_signal(name, db)

    return {"status": "fired", "name": name}


@router.get(
    "/api/signals",
    response_model=List[SignalResponse],
    tags=["Headless Automation"],
    summary="List active signals",
    description="List all currently active signals"
)
async def list_signals(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List all currently active signals."""
    result = await db.execute(select(Signal).order_by(Signal.created_at.desc()))
    signals = result.scalars().all()

    resp = []
    for s in signals:
        resp.append(SignalResponse(
            name=s.name,
            payload=json.loads(s.payload) if s.payload else None,
            created_at=s.created_at
        ))
    return resp


@router.delete(
    "/api/signals/{name}",
    response_model=dict,
    tags=["Headless Automation"],
    summary="Clear a signal",
    description="Delete a signal from the system"
)
async def clear_signal(
    name: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Clear a signal from the system."""
    result = await db.execute(select(Signal).where(Signal.name == name))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, "Signal not found")

    await db.delete(sig)
    await db.commit()
    return {"status": "cleared"}


# --- Retention Config (SRCH-08) ---

@router.get(
    "/api/admin/retention",
    response_model=dict,
    tags=["Admin"],
    summary="Get retention configuration",
    description="Get current execution retention settings and counts of eligible/pinned records"
)
async def get_retention_config(
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    """Get current execution retention config and live record counts."""
    res = await db.execute(select(Config.value).where(Config.key == "execution_retention_days"))
    val = res.scalar_one_or_none()
    retention_days = int(val) if val else 14
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    eligible = await db.scalar(
        select(sqlfunc.count(ExecutionRecord.id)).where(
            ExecutionRecord.completed_at < cutoff,
            ExecutionRecord.pinned.is_(False),
        )
    )
    pinned_count = await db.scalar(
        select(sqlfunc.count(ExecutionRecord.id)).where(
            ExecutionRecord.pinned.is_(True)
        )
    )
    return {
        "retention_days": retention_days,
        "eligible_count": eligible or 0,
        "pinned_count": pinned_count or 0,
    }


@router.patch(
    "/api/admin/retention",
    response_model=dict,
    tags=["Admin"],
    summary="Update retention configuration",
    description="Update the execution record retention period in days"
)
async def update_retention_config(
    body: RetentionConfigUpdate,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update execution retention period in days."""
    existing = await db.execute(select(Config).where(Config.key == "execution_retention_days"))
    row = existing.scalar_one_or_none()
    if row:
        row.value = str(body.retention_days)
    else:
        db.add(Config(key="execution_retention_days", value=str(body.retention_days)))
    await db.commit()
    return {"retention_days": body.retention_days}


# --- License Management (from main.py) ---

@router.post(
    "/api/admin/licence/reload",
    response_model=LicenceReloadResponse,
    tags=["Admin"],
    summary="Reload licence key",
    description="Hot-reload licence key without restarting the server"
)
async def reload_licence_endpoint(
    request: LicenceReloadRequest,
    current_user: User = Depends(require_permission("system:write")),
    db: AsyncSession = Depends(get_db)
):
    """Hot-reload licence key without restarting the server."""
    from ..main import app, ws_manager
    from ..services.licence_service import reload_licence, LicenceError

    old_state = app.state.licence_state

    try:
        new_state = await reload_licence(licence_key=request.licence_key)
    except LicenceError as e:
        # Invalid licence — keep old state active and return error
        audit(db, current_user, "licence:reload_failed", detail={"error": str(e), "old_status": old_state.status.value})
        await db.commit()
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_licence",
                "message": str(e)
            }
        )

    # Atomic swap — new state is valid
    app.state.licence_state = new_state

    # Live-activate EE plugins if licence is now valid but plugins aren't loaded
    ee_activated = False
    if new_state.is_ee_active and not getattr(app.state.ee, "foundry", False):
        from ..ee import activate_ee_live
        from ..db import engine
        new_ctx = await activate_ee_live(app, engine)
        if new_ctx:
            app.state.ee = new_ctx
            ee_activated = True
            logger.info("EE plugins live-activated via licence reload")

    # Broadcast licence status change to all connected WebSocket clients
    await ws_manager.broadcast("licence_status_changed", {
        "old_status": old_state.status.value,
        "new_status": new_state.status.value,
        "message": f"Licence updated to {new_state.status.value}",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "organization": new_state.customer_id or "Unknown",
            "tier": new_state.tier,
            "expires_at": (datetime.utcnow().isoformat()) if new_state.days_until_expiry > 0 else None,
            "ee_activated": ee_activated,
        }
    })

    # If EE was just activated, broadcast feature flags so dashboards update
    if ee_activated:
        ctx = app.state.ee
        await ws_manager.broadcast("features_changed", {
            "foundry": ctx.foundry, "audit": ctx.audit, "webhooks": ctx.webhooks,
            "triggers": ctx.triggers, "rbac": ctx.rbac, "resource_limits": ctx.resource_limits,
            "service_principals": ctx.service_principals, "api_keys": ctx.api_keys,
            "executions": ctx.executions,
        })

    # Audit the transition
    audit(
        db, current_user, "licence:reload_success",
        detail={
            "old_status": old_state.status.value,
            "new_status": new_state.status.value,
            "tier": new_state.tier,
            "customer_id": new_state.customer_id,
            "node_limit": new_state.node_limit,
            "days_until_expiry": new_state.days_until_expiry,
            "ee_activated": ee_activated,
        }
    )
    await db.commit()

    return LicenceReloadResponse(
        status=new_state.status.value,
        tier=new_state.tier,
        customer_id=new_state.customer_id,
        node_limit=new_state.node_limit,
        grace_days=new_state.grace_days,
        days_until_expiry=new_state.days_until_expiry,
        features=new_state.features,
        is_ee_active=new_state.is_ee_active
    )

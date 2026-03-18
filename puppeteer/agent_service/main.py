from fastapi import FastAPI, HTTPException, Request, Depends, Header, status, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Form
from fastapi.responses import Response, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import secrets as _secrets
import uuid
import json
import os
import shutil
import subprocess
import socket
from typing import Optional, List, Dict
import time
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager

from .models import (
    JobCreate, RegisterRequest, RegisterResponse, JobResponse, WorkResponse,
    ResultReport, TokenResponse, HeartbeatPayload, NodeConfig, PollResponse,
    NodeResponse, SignatureCreate, SignatureResponse, JobDefinitionCreate, JobDefinitionUpdate,
    JobDefinitionResponse, JobPushRequest, PingRequest, NetworkMount, MountsConfig,
    ImageBuildRequest, ImageResponse, EnrollmentRequest,
    BlueprintCreate, BlueprintResponse, PuppetTemplateCreate, PuppetTemplateResponse,
    ApprovedIngredientCreate, ApprovedIngredientUpdate, ApprovedIngredientResponse, MirrorConfigUpdate,
    CapabilityMatrixEntry, CapabilityMatrixUpdate, UploadKeyRequest, UserCreate, UserResponse, PermissionGrant,
    ArtifactResponse, ApprovedOSResponse,
    EnrollmentTokenCreate,
    SignalFire, SignalResponse,
    TriggerCreate, TriggerResponse, TriggerUpdate,
    UserSigningKeyCreate, UserSigningKeyResponse, UserSigningKeyGeneratedResponse,
    UserApiKeyCreate, UserApiKeyResponse, UserApiKeyCreatedResponse,
    ServicePrincipalCreate, ServicePrincipalResponse, ServicePrincipalCreatedResponse,
    ServicePrincipalUpdate, ServicePrincipalTokenRequest, ServicePrincipalRotateResponse,
    ExecutionRecordResponse,
    AttestationExportResponse,
    AlertResponse,
    WebhookCreate, WebhookResponse,
    ImageBOMResponse, PackageIndexResponse,
    DispatchRequest, DispatchResponse, DispatchStatusResponse,
    ALLOWED_ROLES,
)
from .security import (
    encrypt_secrets, decrypt_secrets, mask_secrets, verify_api_key, 
    verify_client_cert, API_KEY, ENCRYPTION_KEY, cipher_suite, oauth2_scheme,
    mask_pii, verify_node_secret
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sqlalchemy.future import select
from sqlalchemy import update, desc, func, delete
from collections import defaultdict
from cryptography import x509 as _x509
from .db import init_db, get_db, Job, Token, Config, User, Node, NodeStats, AsyncSession, Signature, ScheduledJob, Ping, AsyncSessionLocal, CapabilityMatrix, Blueprint, PuppetTemplate, RolePermission, AuditLog, RevokedCert, UserSigningKey, UserApiKey, ServicePrincipal, ExecutionRecord, Artifact, ApprovedOS, Trigger, Signal, Alert, ApprovedIngredient
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_token
from .services.job_service import JobService
from .services.signature_service import SignatureService
from .services.scheduler_service import scheduler_service
from .services.pki_service import pki_service
from .services.vault_service import vault_service
from .services.foundry_service import foundry_service
from .services.trigger_service import trigger_service
from .services.smelter_service import SmelterService
from .services.alert_service import AlertService
from .services.webhook_service import WebhookService

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    # Bootstrap Admin
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin_user = User(
                username="admin", 
                password_hash=get_password_hash(os.getenv("ADMIN_PASSWORD", uuid.uuid4().hex)), 
                role="admin"
            )
            if not os.getenv("ADMIN_PASSWORD"):
                print(f"⚠️  Admin User created with RANDOM password. Please set ADMIN_PASSWORD env var.")
            else:
                db.add(admin_user)
                await db.commit()
                logger.info("✅ Bootstrapped Admin User")
    
    # Bootstrap Capability Matrix
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(CapabilityMatrix).limit(1))
        if not result.scalar_one_or_none():
            logger.info("🌱 Seeding Capability Matrix...")
            recipes = [
                CapabilityMatrix(
                    base_os_family="DEBIAN",
                    tool_id="python-3.11",
                    injection_recipe="RUN apt-get update && apt-get install -y python3.11 python3-pip python3-dev build-essential libssl-dev libffi-dev && ln -sf /usr/bin/python3.11 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip && pip config set global.break-system-packages true",
                    validation_cmd="python --version",
                    is_active=True,
                    runtime_dependencies="[]"
                ),
                CapabilityMatrix(
                    base_os_family="DEBIAN",
                    tool_id="pwsh-7.4",
                    injection_recipe="RUN apt-get update && apt-get install -y wget && wget https://github.com/PowerShell/PowerShell/releases/download/v7.4.1/powershell_7.4.1-1.deb_amd64.deb && dpkg -i powershell_7.4.1-1.deb_amd64.deb && apt-get install -f",
                    validation_cmd="pwsh -version",
                    is_active=True,
                    runtime_dependencies="[]"
                ),
                CapabilityMatrix(
                    base_os_family="ALPINE",
                    tool_id="python-3.11",
                    injection_recipe="RUN apk add --no-cache python3 py3-pip python3-dev build-base libffi-dev openssl-dev && ln -sf /usr/bin/python3 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip",
                    validation_cmd="python3 --version",
                    is_active=True,
                    runtime_dependencies="[]"
                ),
                CapabilityMatrix(
                    base_os_family="ALPINE",
                    tool_id="pwsh-7.4",
                    injection_recipe="RUN apk add --no-cache ca-certificates less ncurses-terminfo-base krb5-libs libgcc libintl libssl3 libstdc++ tzdata userspace-rcu zlib icu-libs curl && curl -L https://github.com/PowerShell/PowerShell/releases/download/v7.4.1/powershell-7.4.1-linux-musl-x64.tar.gz -o /tmp/powershell.tar.gz && mkdir -p /opt/microsoft/powershell/7 && tar zxf /tmp/powershell.tar.gz -C /opt/microsoft/powershell/7 && chmod +x /opt/microsoft/powershell/7/pwsh && ln -s /opt/microsoft/powershell/7/pwsh /usr/bin/pwsh && rm /tmp/powershell.tar.gz",
                    validation_cmd="pwsh -Version",
                    is_active=True,
                    runtime_dependencies="[]"
                ),
            ]
            db.add_all(recipes)
            await db.commit()
            logger.info("✅ Capability Matrix Seeded")
        else:
            # Existing DB — check if ALPINE recipes are missing and seed them
            alpine_check = await db.execute(
                select(CapabilityMatrix).where(CapabilityMatrix.base_os_family == "ALPINE").limit(1)
            )
            if not alpine_check.scalar_one_or_none():
                logger.info("🌱 Seeding ALPINE Capability Matrix recipes...")
                alpine_recipes = [
                    CapabilityMatrix(
                        base_os_family="ALPINE",
                        tool_id="python-3.11",
                        injection_recipe="RUN apk add --no-cache python3 py3-pip python3-dev build-base libffi-dev openssl-dev && ln -sf /usr/bin/python3 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip",
                        validation_cmd="python3 --version",
                        is_active=True,
                        runtime_dependencies="[]"
                    ),
                    CapabilityMatrix(
                        base_os_family="ALPINE",
                        tool_id="pwsh-7.4",
                        injection_recipe="RUN apk add --no-cache ca-certificates less ncurses-terminfo-base krb5-libs libgcc libintl libssl3 libstdc++ tzdata userspace-rcu zlib icu-libs curl && curl -L https://github.com/PowerShell/PowerShell/releases/download/v7.4.1/powershell-7.4.1-linux-musl-x64.tar.gz -o /tmp/powershell.tar.gz && mkdir -p /opt/microsoft/powershell/7 && tar zxf /tmp/powershell.tar.gz -C /opt/microsoft/powershell/7 && chmod +x /opt/microsoft/powershell/7/pwsh && ln -s /opt/microsoft/powershell/7/pwsh /usr/bin/pwsh && rm /tmp/powershell.tar.gz",
                        validation_cmd="pwsh -Version",
                        is_active=True,
                        runtime_dependencies="[]"
                    ),
                ]
                db.add_all(alpine_recipes)
                await db.commit()
                logger.info("✅ ALPINE Capability Matrix Seeded")

    # Seed Role Permissions
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RolePermission).limit(1))
        if not result.scalar_one_or_none():
            logger.info("🌱 Seeding Role Permissions...")
            OPERATOR_PERMS = [
                "jobs:read", "jobs:write", "nodes:read", "nodes:write",
                "definitions:read", "definitions:write", "foundry:read", "foundry:write",
                "signatures:read", "signatures:write", "tokens:write",
                "alerts:read", "alerts:write",
                "webhooks:read", "webhooks:write",
                "history:read",
            ]
            VIEWER_PERMS = [
                "jobs:read", "nodes:read", "definitions:read", "foundry:read", "signatures:read",
                "alerts:read", "history:read",
            ]
            seeds = (
                [RolePermission(role="operator", permission=p) for p in OPERATOR_PERMS] +
                [RolePermission(role="viewer", permission=p) for p in VIEWER_PERMS]
            )
            db.add_all(seeds)
            await db.commit()
            logger.info("✅ Role Permissions Seeded")

    # Start Scheduler
    scheduler_service.start()
    await scheduler_service.sync_scheduler()

    # Start background node monitoring
    import asyncio
    async def monitor_nodes():
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    count = await AlertService.check_node_health(db)
                    if count > 0:
                        logger.info(f"Monitor: Marked {count} nodes as offline.")
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(60) # Check every minute

    asyncio.create_task(monitor_nodes())
    
    yield
    # Shutdown logic
    scheduler_service.scheduler.shutdown()

app = FastAPI(
    title="Master of Puppets v0.8", 
    description="Orchestrator (v0.8) - Security & Mounts",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"], # Dashboard + BFF
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTH HELPERS (must be defined before any route that uses require_permission) ---

class _SPUserProxy:
    """Makes a ServicePrincipal quack like a User for permission checks and auditing."""
    def __init__(self, sp: ServicePrincipal):
        self.username = f"sp:{sp.name}"
        self.role = sp.role
        self.token_version = 0
        self.must_change_password = False
        self._sp = sp


async def _authenticate_api_key(raw_key: str, db: AsyncSession):
    """Authenticate using a personal API key (mop_...). Returns the owning User."""
    prefix = raw_key[:12]
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.key_prefix == prefix)
    )
    candidates = result.scalars().all()

    for candidate in candidates:
        if verify_password(raw_key, candidate.key_hash):
            if candidate.expires_at and candidate.expires_at < datetime.utcnow():
                raise HTTPException(401, "API key has expired")
            candidate.last_used_at = datetime.utcnow()
            await db.commit()
            user_result = await db.execute(
                select(User).where(User.username == candidate.username)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise HTTPException(401, "User account not found")
            return user

    raise HTTPException(401, "Invalid API key")


async def _authenticate_sp_jwt(payload: dict, db: AsyncSession):
    """Authenticate a service principal JWT. Returns an _SPUserProxy."""
    sp_id = payload.get("sp_id")
    if not sp_id:
        raise HTTPException(401, "Invalid service principal token")

    result = await db.execute(
        select(ServicePrincipal).where(ServicePrincipal.id == sp_id)
    )
    sp = result.scalar_one_or_none()

    if not sp or not sp.is_active:
        raise HTTPException(401, "Service principal not found or disabled")

    if sp.expires_at and sp.expires_at < datetime.utcnow():
        raise HTTPException(401, "Service principal has expired")

    return _SPUserProxy(sp)


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """JWT / API key / SP token auth."""
    # API key authentication
    if token.startswith("mop_"):
        return await _authenticate_api_key(token, db)

    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Service principal JWT
    if payload.get("type") == "service_principal":
        return await _authenticate_sp_jwt(payload, db)

    # Regular user JWT
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    # Reject tokens issued before a password change (token_version mismatch)
    if payload.get("tv", 0) != user.token_version:
        raise credentials_exception
    return user

async def get_current_user_optional(token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    """Optional JWT User Auth."""
    if not token:
        return None

    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

_perm_cache: dict[str, set[str]] = {}

def _invalidate_perm_cache(role: str | None = None) -> None:
    """Clear cached permissions for a role (or all roles)."""
    if role:
        _perm_cache.pop(role, None)
    else:
        _perm_cache.clear()

def require_permission(perm: str):
    """Dependency factory that enforces a named permission via DB-backed RBAC."""
    async def _check(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if current_user.role == "admin":
            return current_user
        if current_user.role not in _perm_cache:
            result = await db.execute(
                select(RolePermission.permission).where(RolePermission.role == current_user.role)
            )
            _perm_cache[current_user.role] = {row for row in result.scalars().all()}
        if perm not in _perm_cache[current_user.role]:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return current_user
    return _check

# --- ALERTS ---

@app.get("/api/alerts", response_model=List[AlertResponse], tags=["Alerts & Webhooks"])
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    unacknowledged_only: bool = False,
    current_user: User = Depends(require_permission("alerts:read")),
    db: AsyncSession = Depends(get_db)
):
    """List system alerts with optional filtering."""
    return await AlertService.list_alerts(db, skip, limit, unacknowledged_only)

@app.post("/api/alerts/{alert_id}/acknowledge", tags=["Alerts & Webhooks"])
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_permission("alerts:write")),
    db: AsyncSession = Depends(get_db)
):
    """Mark an alert as acknowledged."""
    alert = await AlertService.acknowledge_alert(db, alert_id, current_user.username)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return {"status": "acknowledged", "id": alert_id}

# --- WEBHOOKS ---

@app.get("/api/webhooks", response_model=List[WebhookResponse], tags=["Alerts & Webhooks"])
async def list_webhooks(
    current_user: User = Depends(require_permission("webhooks:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all registered outbound webhooks."""
    return await WebhookService.list_webhooks(db)

@app.post("/api/webhooks", response_model=WebhookResponse, tags=["Alerts & Webhooks"])
async def create_webhook(
    hook: WebhookCreate,
    current_user: User = Depends(require_permission("webhooks:write")),
    db: AsyncSession = Depends(get_db)
):
    """Register a new outbound webhook with a signed secret."""
    wh = await WebhookService.create_webhook(db, hook.url, hook.events)
    await db.commit()
    return wh

@app.delete("/api/webhooks/{webhook_id}", tags=["Alerts & Webhooks"])
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(require_permission("webhooks:write")),
    db: AsyncSession = Depends(get_db)
):
    """Remove a webhook."""
    success = await WebhookService.delete_webhook(db, webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.commit()
    return {"status": "deleted", "id": webhook_id}

# --- Execution History ---

@app.get("/api/executions", response_model=List[ExecutionRecordResponse], tags=["Execution Records"])
async def list_executions(
    skip: int = 0,
    limit: int = 50,
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    job_guid: Optional[str] = None,
    scheduled_job_id: Optional[str] = None,
    job_run_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("history:read"))
):
    """List execution history with filtering and pagination."""
    query = select(ExecutionRecord)
    if node_id:
        query = query.where(ExecutionRecord.node_id == node_id)
    if status:
        query = query.where(ExecutionRecord.status == status)
    if job_guid:
        query = query.where(ExecutionRecord.job_guid == job_guid)
    if scheduled_job_id:
        subq = select(Job.guid).where(Job.scheduled_job_id == scheduled_job_id)
        query = query.where(ExecutionRecord.job_guid.in_(subq))
    if job_run_id:
        query = query.where(ExecutionRecord.job_run_id == job_run_id)
    
    query = query.order_by(desc(ExecutionRecord.started_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()
    
    responses = []
    for r in records:
        duration = None
        if r.started_at and r.completed_at:
            duration = (r.completed_at - r.started_at).total_seconds()
        
        log = []
        if r.output_log:
            try:
                log = json.loads(r.output_log)
            except:
                log = [{"t": str(r.started_at), "stream": "stderr", "line": "Failed to parse log JSON"}]

        responses.append(ExecutionRecordResponse(
            id=r.id,
            job_guid=r.job_guid,
            node_id=r.node_id,
            status=r.status,
            exit_code=r.exit_code,
            started_at=r.started_at,
            completed_at=r.completed_at,
            output_log=log,
            truncated=r.truncated,
            duration_seconds=duration,
            stdout=r.stdout,
            stderr=r.stderr,
            script_hash=r.script_hash,
            hash_mismatch=r.hash_mismatch,
            attempt_number=r.attempt_number,
            job_run_id=r.job_run_id,
            attestation_verified=r.attestation_verified,
        ))
    return responses

@app.get("/api/executions/{id}", response_model=ExecutionRecordResponse, tags=["Execution Records"])
async def get_execution(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("history:read"))
):
    """Get details for a single execution record."""
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    duration = None
    if r.started_at and r.completed_at:
        duration = (r.completed_at - r.started_at).total_seconds()
    
    log = []
    if r.output_log:
        try:
            log = json.loads(r.output_log)
        except:
            log = [{"t": str(r.started_at), "stream": "stderr", "line": "Failed to parse log JSON"}]

    return ExecutionRecordResponse(
        id=r.id,
        job_guid=r.job_guid,
        node_id=r.node_id,
        status=r.status,
        exit_code=r.exit_code,
        started_at=r.started_at,
        completed_at=r.completed_at,
        output_log=log,
        truncated=r.truncated,
        duration_seconds=duration,
        stdout=r.stdout,
        stderr=r.stderr,
        script_hash=r.script_hash,
        hash_mismatch=r.hash_mismatch,
        attempt_number=r.attempt_number,
        job_run_id=r.job_run_id,
        attestation_verified=r.attestation_verified,
    )

@app.get("/api/executions/{id}/attestation", response_model=AttestationExportResponse,
         tags=["Execution Records"])
async def get_execution_attestation(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("history:read"))
):
    """Export attestation bundle and verification result for an execution record.

    Returns 404 if the execution record does not exist or has no attestation data.
    """
    result = await db.execute(select(ExecutionRecord).where(ExecutionRecord.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Execution record not found")
    if not record.attestation_bundle:
        raise HTTPException(status_code=404, detail="No attestation for this execution")

    # Extract cert_serial from bundle bytes if possible
    cert_serial = None
    try:
        import json as _json
        import base64 as _b64
        bundle_data = _json.loads(_b64.b64decode(record.attestation_bundle))
        cert_serial = bundle_data.get("cert_serial")
    except Exception:
        pass

    return AttestationExportResponse(
        bundle_b64=record.attestation_bundle,
        signature_b64=record.attestation_signature or "",
        cert_serial=cert_serial,
        node_id=record.node_id,
        attestation_verified=record.attestation_verified,
    )


# Serve Installer Scripts
@app.get("/api/node/compose", tags=["System"])
@app.get("/api/installer/compose", tags=["System"])
async def get_node_compose(token: str, mounts: Optional[str] = None, tags: Optional[str] = None, execution_mode: Optional[str] = None):
    """Dynamic Compose File generator for Nodes."""
    effective_tags = tags if tags else "general,linux,arm64"
    # Allow caller or server default to set EXECUTION_MODE for the node container.
    # Defaults to "auto" (Docker/Podman detection). Use "direct" for DinD environments
    # where no container runtime socket is available inside the node container.
    effective_execution_mode = execution_mode or os.getenv("NODE_EXECUTION_MODE", "auto")
    compose_content = f"""
version: '3.8'
services:
  puppet:
    image: {os.getenv("NODE_IMAGE", "192.168.50.148:5000/puppet-node:latest")}
    network_mode: host
    environment:
      - AGENT_URL={os.getenv("AGENT_URL", "https://localhost:8001")}
      - JOIN_TOKEN={token}
      - MOUNT_DATA={mounts if mounts else ""}
      - NODE_TAGS={effective_tags}
      - EXECUTION_MODE={effective_execution_mode}
    volumes:
      - ./secrets:/app/secrets
    restart: unless-stopped
"""
    return Response(content=compose_content, media_type="text/yaml")

if not os.path.exists("installer"):
    os.makedirs("installer")
app.mount("/installer", StaticFiles(directory="installer"), name="installer")

@app.get("/verification-key", tags=["System"])
async def get_verification_key():
    """Serves the Public Verification Key for Code Signing."""
    key_path = "/app/secrets/verification.key"
    if not os.path.exists(key_path):
        if os.path.exists("secrets/verification.key"):
            key_path = "secrets/verification.key"
        else:
            raise HTTPException(status_code=404, detail="Verification Key not configured on Server")
    
    with open(key_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/installer", tags=["System"])
async def get_installer_ps1():
    """Serves the Universal PowerShell Installer (One-Liner)."""
    file_path = "installer/install_universal.ps1"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/installer.sh", tags=["System"])
async def get_installer_sh():
    """Serves the Universal Bash Installer."""
    file_path = "installer/install_universal.sh"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/system/root-ca", tags=["System"])
async def get_root_ca():
    """Download the Internal Root CA (Public Key)."""
    try:
        pem_content = pki_service.get_root_cert_pem()
        return Response(content=pem_content, media_type="application/x-pem-file", headers={"Content-Disposition": "attachment; filename=root_ca.crt"})
    except Exception as e:
        logger.error(f"Failed to serve Root CA: {e}")
        raise HTTPException(status_code=404, detail="Root CA not found")

def _get_dashboard_ca_pem() -> str:
    """Return the CA cert that signs the dashboard TLS certificate.

    The cert-manager container generates a Root CA with step-cli and mounts it
    at /app/global_certs/root_ca.crt.  That CA is what Caddy uses to sign its
    TLS leaf cert, so it's the one clients must trust to reach the dashboard
    over HTTPS.  Fall back to the agent's own mTLS CA if the volume isn't
    present (e.g. running outside Docker).
    """
    dashboard_ca = "/app/global_certs/root_ca.crt"
    if os.path.exists(dashboard_ca):
        with open(dashboard_ca) as f:
            return f.read()
    return pki_service.get_root_cert_pem()

@app.get("/system/root-ca-installer", tags=["System"])
async def get_ca_installer_bash():
    """
    Returns a self-contained bash script that installs the MoP Root CA into
    the system trust store (Debian/Ubuntu, RHEL/Fedora, macOS).

    Fetch and run over plain HTTP before trusting HTTPS:
        curl http://<host>:8080/system/root-ca-installer | sudo bash
    """
    try:
        ca_pem = _get_dashboard_ca_pem()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CA not available: {e}")

    script = f"""#!/usr/bin/env bash
# Master of Puppets — Root CA Installer
# Run this once on each device to trust the MoP dashboard over HTTPS.
# Usage: curl http://<host>:8080/system/root-ca-installer | sudo bash
set -e

CA_NAME="MoP-Root-CA"
CA_PEM='{ca_pem.strip()}'

echo "[MoP] Installing Root CA..."

install_linux() {{
    # 1. System trust store (used by curl, wget, etc.)
    if command -v update-ca-certificates &>/dev/null; then
        printf '%s\\n' "$CA_PEM" > "/usr/local/share/ca-certificates/${{CA_NAME}}.crt"
        update-ca-certificates
        echo "[MoP] Installed to system trust store (Debian/Ubuntu)."
    elif command -v update-ca-trust &>/dev/null; then
        printf '%s\\n' "$CA_PEM" > "/etc/pki/ca-trust/source/anchors/${{CA_NAME}}.crt"
        update-ca-trust extract
        echo "[MoP] Installed to system trust store (RHEL/Fedora)."
    else
        printf '%s\\n' "$CA_PEM" > "./${{CA_NAME}}.crt"
        echo "[MoP] Saved to ./${{CA_NAME}}.crt — install manually into your trust store."
    fi

    # 2. Browser NSS databases (Chrome/Chromium/Firefox on Linux ignore the system store)
    if ! command -v certutil &>/dev/null; then
        echo "[MoP] certutil not found — skipping browser trust store."
        echo "      Install libnss3-tools and re-run to trust in Chrome/Firefox:"
        echo "      sudo apt install libnss3-tools && curl http://<host>:8080/system/root-ca-installer | sudo bash"
        return
    fi
    # Write cert to a temp file readable by the real user
    CERT_TMP=$(mktemp /tmp/mop-ca-XXXXXX.crt)
    printf '%s\\n' "$CA_PEM" > "$CERT_TMP"
    chmod 644 "$CERT_TMP"

    # Determine the actual invoking user's home (script runs under sudo)
    REAL_USER="${{SUDO_USER:-$USER}}"
    REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

    add_nss() {{
        local db_dir="$1"
        if [ -d "$db_dir" ]; then
            su -c "certutil -d sql:\\"$db_dir\\" -A -t 'CT,,' -n '${{CA_NAME}}' -i '$CERT_TMP'" "$REAL_USER" 2>/dev/null \
                && echo "[MoP] Added to NSS db: $db_dir" \
                || true
        fi
    }}

    # Chrome
    add_nss "$REAL_HOME/.pki/nssdb"
    # Chromium
    add_nss "$REAL_HOME/.config/chromium/nssdb"
    # Firefox — handle multiple profiles
    for ffdir in "$REAL_HOME"/.mozilla/firefox/*.default \
                 "$REAL_HOME"/.mozilla/firefox/*.default-release \
                 "$REAL_HOME"/.mozilla/firefox/*.default-esr; do
        add_nss "$ffdir"
    done

    rm -f "$CERT_TMP"
    echo "[MoP] Browser NSS databases updated. Restart your browser."
}}

install_macos() {{
    TMPF=$(mktemp /tmp/mop-ca-XXXXXX.crt)
    printf '%s\\n' "$CA_PEM" > "$TMPF"
    security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$TMPF"
    rm -f "$TMPF"
    echo "[MoP] Installed to macOS System Keychain. Restart your browser."
}}

case "$(uname -s)" in
    Linux*)  install_linux ;;
    Darwin*) install_macos ;;
    *)
        printf '%s\\n' "$CA_PEM" > "./${{CA_NAME}}.crt"
        echo "[MoP] Unsupported OS — cert saved to ./${{CA_NAME}}.crt. Install manually."
        ;;
esac

echo "[MoP] Done. You can now access the dashboard at https://<host>:8443"
"""
    return Response(content=script, media_type="text/plain",
                    headers={"Content-Disposition": "inline; filename=mop-install-ca.sh"})

@app.get("/system/root-ca-installer.ps1", tags=["System"])
async def get_ca_installer_ps1():
    """
    Returns a PowerShell script that installs the MoP Root CA on Windows.

    Run in an elevated PowerShell prompt:
        iwr http://<host>:8080/system/root-ca-installer.ps1 | iex
    """
    try:
        ca_pem = _get_dashboard_ca_pem()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CA not available: {e}")

    script = f"""# Master of Puppets — Root CA Installer (Windows)
# Run in an elevated PowerShell prompt:
#   iwr http://<host>:8080/system/root-ca-installer.ps1 | iex

$cert = @"
{ca_pem.strip()}
"@

$tmp = [System.IO.Path]::GetTempFileName() + ".crt"
[System.IO.File]::WriteAllText($tmp, $cert)
try {{
    Import-Certificate -FilePath $tmp -CertStoreLocation "Cert:\\LocalMachine\\Root" | Out-Null
    Write-Host "[MoP] Root CA installed to Windows Root Store. Restart your browser."
}} finally {{
    Remove-Item $tmp -ErrorAction SilentlyContinue
}}
Write-Host "[MoP] Done. You can now access the dashboard at https://<host>:8443"
"""
    return Response(content=script, media_type="text/plain",
                    headers={"Content-Disposition": "inline; filename=mop-install-ca.ps1"})

class ConnectionManager:
    """Broadcasts JSON messages to all connected WebSocket clients."""
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.remove(ws)

    async def broadcast(self, event: str, data: dict):
        msg = json.dumps({"event": event, "data": data})
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

ws_manager = ConnectionManager()


def audit(db: AsyncSession, user: User, action: str, resource_id: str = None, detail: dict = None):
    """Append an audit entry to the current session. Caller must commit."""
    db.add(AuditLog(
        username=user.username,
        action=action,
        resource_id=resource_id,
        detail=json.dumps(detail) if detail else None,
    ))

# --- Auth Endpoints ---

# --- OAuth Device Flow (RFC 8628) ---
_device_codes: dict[str, dict] = {}
_user_code_index: dict[str, str] = {}  # user_code -> device_code (reverse index)
_USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0,O,1,I,L
_DEVICE_TTL_SECONDS = 300   # 5 minutes
_POLL_INTERVAL_SECONDS = 5

def _generate_user_code() -> str:
    p1 = "".join(_secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    p2 = "".join(_secrets.choice(_USER_CODE_ALPHABET) for _ in range(4))
    return f"{p1}-{p2}"

@app.post("/auth/device", tags=["Authentication"])
async def device_authorization():
    """RFC 8628 Device Authorization Request — issues device_code and user_code."""
    now = datetime.utcnow()
    # Lazy cleanup: evict expired entries (2x TTL = 10 min grace)
    expired_keys = [k for k, v in list(_device_codes.items()) if v["expiry"] < now]
    for k in expired_keys:
        uc = _device_codes.pop(k, {}).get("user_code")
        if uc:
            _user_code_index.pop(uc, None)

    device_code = _secrets.token_urlsafe(32)
    user_code = _generate_user_code()
    expiry = now + timedelta(seconds=_DEVICE_TTL_SECONDS)

    _device_codes[device_code] = {
        "user_code": user_code,
        "expiry": expiry,
        "status": "pending",
        "approved_by": None,
        "last_poll": None,
    }
    _user_code_index[user_code] = device_code

    agent_url = os.getenv("AGENT_URL", "https://localhost:8001")
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": f"{agent_url}/auth/device/approve",
        "verification_uri_complete": f"{agent_url}/auth/device/approve?user_code={user_code}",
        "expires_in": _DEVICE_TTL_SECONDS,
        "interval": _POLL_INTERVAL_SECONDS,
    }

class DeviceTokenRequest(BaseModel):
    device_code: str
    grant_type: str = "urn:ietf:params:oauth:grant-type:device_code"

@app.post("/auth/device/token", tags=["Authentication"])
async def device_token_exchange(req: DeviceTokenRequest, db: AsyncSession = Depends(get_db)):
    """RFC 8628 Device Access Token Request — exchange device_code for JWT."""
    entry = _device_codes.get(req.device_code)
    now = datetime.utcnow()

    if not entry:
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["expiry"] < now:
        uc = _device_codes.pop(req.device_code, {}).get("user_code")
        if uc:
            _user_code_index.pop(uc, None)
        raise HTTPException(400, detail={"error": "expired_token"})
    if entry["status"] == "denied":
        raise HTTPException(400, detail={"error": "access_denied"})

    # RFC 8628 slow_down: if polled again before interval
    last_poll = entry.get("last_poll")
    if last_poll and (now - last_poll).total_seconds() < _POLL_INTERVAL_SECONDS:
        entry["last_poll"] = now
        raise HTTPException(400, detail={"error": "slow_down"})
    entry["last_poll"] = now

    if entry["status"] == "pending":
        raise HTTPException(400, detail={"error": "authorization_pending"})

    # status == "approved"
    username = entry["approved_by"]
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, detail={"error": "access_denied"})

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tv": user.token_version, "type": "device_flow"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Consume code — one-time use
    _device_codes.pop(req.device_code, None)
    _user_code_index.pop(entry["user_code"], None)

    audit(db, user, "device_flow:token_issued", None, {"username": user.username})
    await db.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role}

@app.get("/auth/device/approve", response_class=HTMLResponse, tags=["Authentication"])
async def device_approve_page(user_code: str = ""):
    """Serve the device authorization approval page (inline HTML, no build step)."""
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authorize Device — Master of Puppets</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 80px auto; padding: 0 1rem; color: #1a1a1a; }}
    .card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 2rem; text-align: center; }}
    .code {{ font-family: monospace; font-size: 2rem; font-weight: bold; letter-spacing: 0.2em; color: #0d6efd; margin: 1rem 0; }}
    .btn {{ display: inline-block; padding: 0.6rem 1.6rem; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; margin: 0.3rem; }}
    .btn-approve {{ background: #198754; color: white; }}
    .btn-deny {{ background: #dc3545; color: white; }}
    .btn-approve:hover {{ background: #157347; }}
    .btn-deny:hover {{ background: #bb2d3b; }}
    .msg {{ margin-top: 1rem; font-size: 0.9rem; color: #6c757d; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Authorize Device</h2>
    <p>A CLI device is requesting access to <strong>Master of Puppets</strong>.</p>
    <p>Confirm that your terminal displays this code:</p>
    <div class="code" id="display-code">{user_code or "(no code provided)"}</div>
    <form id="approve-form" method="POST" action="/auth/device/approve">
      <input type="hidden" name="user_code" value="{user_code}">
      <input type="hidden" name="token" id="token-field" value="">
      <button type="submit" class="btn btn-approve">Approve</button>
    </form>
    <form id="deny-form" method="POST" action="/auth/device/deny">
      <input type="hidden" name="user_code" value="{user_code}">
      <input type="hidden" name="token" id="deny-token-field" value="">
      <button type="submit" class="btn btn-deny">Deny</button>
    </form>
    <p class="msg" id="auth-msg"></p>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var token = localStorage.getItem('access_token') || '';
      document.getElementById('token-field').value = token;
      document.getElementById('deny-token-field').value = token;
      if (!token) {{
        document.getElementById('auth-msg').textContent = 'You must be logged in to authorize a device.';
        document.getElementById('auth-msg').style.color = '#dc3545';
        var next = encodeURIComponent(window.location.href);
        setTimeout(function() {{ window.location.href = '/login?next=' + next; }}, 2000);
      }}
    }});
  </script>
</body>
</html>""")

@app.post("/auth/device/approve", response_class=HTMLResponse, tags=["Authentication"])
async def device_approve_submit(
    user_code: str = Form(...),
    token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Process device approval — sets status='approved' on matching device code."""
    # Validate the user's JWT from the form
    try:
        payload = verify_token(token)
        username = payload.get("sub")
    except Exception:
        return HTMLResponse(content="<h2>Error: Invalid or missing session token. Please log in and try again.</h2>", status_code=401)

    device_code = _user_code_index.get(user_code)
    if not device_code or device_code not in _device_codes:
        return HTMLResponse(content="<h2>Error: Device code not found or expired.</h2>", status_code=404)

    entry = _device_codes[device_code]
    if entry["expiry"] < datetime.utcnow():
        return HTMLResponse(content="<h2>Error: Device code has expired.</h2>", status_code=410)

    entry["status"] = "approved"
    entry["approved_by"] = username

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        audit(db, user, "device_flow:approved", None, {"user_code": user_code})
        await db.commit()

    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Authorized</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;}</style>
</head><body><h2 style="color:#198754">Device authorized.</h2>
<p>You may close this tab. Your CLI session is now active.</p></body></html>""")

@app.post("/auth/device/deny", response_class=HTMLResponse, tags=["Authentication"])
async def device_deny_submit(
    user_code: str = Form(...),
    token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Process device denial — sets status='denied' on matching device code."""
    try:
        payload = verify_token(token)
        username = payload.get("sub")
    except Exception:
        username = "unknown"

    device_code = _user_code_index.get(user_code)
    if device_code and device_code in _device_codes:
        _device_codes[device_code]["status"] = "denied"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        audit(db, user, "device_flow:denied", None, {"user_code": user_code})
        await db.commit()

    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Denied</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;text-align:center;}</style>
</head><body><h2 style="color:#dc3545">Device authorization denied.</h2>
<p>The CLI request has been rejected. You may close this tab.</p></body></html>""")

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "tv": user.token_version},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role,
            "must_change_password": bool(user.must_change_password)}

@app.get("/auth/me", tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role,
            "must_change_password": bool(current_user.must_change_password)}

@app.patch("/auth/me", tags=["Authentication"])
async def update_self(req: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Allow a logged-in user to change their own password.
    Returns a fresh access token so the current session continues uninterrupted."""
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    # Require current password unless the account has a forced-change flag set
    if not current_user.must_change_password:
        current_password = req.get("current_password", "")
        if not current_password or not verify_password(current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(new_password)
    current_user.must_change_password = False
    current_user.token_version = (current_user.token_version or 0) + 1
    audit(db, current_user, "user:password_changed", detail={"username": current_user.username})
    await db.commit()
    # Issue a new token for the current session (old tokens for other sessions are now invalid)
    new_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role, "tv": current_user.token_version},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"status": "ok", "must_change_password": False, "access_token": new_token}

# --- User Signing Keys ---

@app.post("/auth/me/signing-keys", tags=["Authentication"])
async def create_signing_key(
    req: UserSigningKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    key_id = str(uuid.uuid4())
    private_key_pem_str = None

    if req.public_key_pem:
        try:
            pub = serialization.load_pem_public_key(req.public_key_pem.encode())
            if not isinstance(pub, ed25519.Ed25519PublicKey):
                raise HTTPException(400, "Key must be Ed25519")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "Invalid Ed25519 public key PEM")
        public_pem = req.public_key_pem
        encrypted_priv = None
    else:
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        private_key_pem_str = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ).decode()
        encrypted_priv = cipher_suite.encrypt(private_key_pem_str.encode()).decode()

    signing_key = UserSigningKey(
        id=key_id,
        username=current_user.username,
        name=req.name,
        public_key_pem=public_pem,
        encrypted_private_key=encrypted_priv,
    )
    db.add(signing_key)

    sig = Signature(
        id=str(uuid.uuid4()),
        name=f"{current_user.username}/{req.name}",
        public_key=public_pem,
        uploaded_by=current_user.username,
    )
    db.add(sig)

    audit(db, current_user, "user:signing_key_created", key_id, {"name": req.name})
    await db.commit()

    if private_key_pem_str:
        return UserSigningKeyGeneratedResponse(
            id=key_id, name=req.name, public_key_pem=public_pem,
            private_key_pem=private_key_pem_str, created_at=signing_key.created_at,
        )
    return UserSigningKeyResponse(
        id=key_id, name=req.name, public_key_pem=public_pem,
        created_at=signing_key.created_at,
    )


@app.get("/auth/me/signing-keys", response_model=list[UserSigningKeyResponse], tags=["Authentication"])
async def list_signing_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSigningKey).where(UserSigningKey.username == current_user.username)
    )
    return result.scalars().all()


@app.delete("/auth/me/signing-keys/{key_id}", tags=["Authentication"])
async def delete_signing_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSigningKey).where(
            UserSigningKey.id == key_id,
            UserSigningKey.username == current_user.username,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, "Signing key not found")

    sig_name = f"{current_user.username}/{key.name}"
    sig_result = await db.execute(
        select(Signature).where(Signature.name == sig_name)
    )
    sig = sig_result.scalar_one_or_none()
    if sig:
        await db.delete(sig)

    await db.delete(key)
    audit(db, current_user, "user:signing_key_deleted", key_id)
    await db.commit()
    return {"status": "deleted"}


# --- User API Keys ---

@app.post("/auth/me/api-keys", tags=["Authentication"])
async def create_api_key(
    req: UserApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import secrets as _secrets

    raw_key = "mop_" + _secrets.token_hex(24)
    key_hash = get_password_hash(raw_key)
    key_prefix = raw_key[:12]

    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

    api_key = UserApiKey(
        id=str(uuid.uuid4()),
        username=current_user.username,
        name=req.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=expires_at,
    )
    db.add(api_key)
    audit(db, current_user, "user:api_key_created", api_key.id, {"name": req.name})
    await db.commit()

    return UserApiKeyCreatedResponse(
        id=api_key.id, name=api_key.name, key_prefix=key_prefix,
        raw_key=raw_key, expires_at=expires_at,
        last_used_at=None, created_at=api_key.created_at,
    )


@app.get("/auth/me/api-keys", response_model=list[UserApiKeyResponse], tags=["Authentication"])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.username == current_user.username)
    )
    return result.scalars().all()


@app.delete("/auth/me/api-keys/{key_id}", tags=["Authentication"])
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.id == key_id,
            UserApiKey.username == current_user.username,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, "API key not found")

    await db.delete(key)
    audit(db, current_user, "user:api_key_revoked", key_id)
    await db.commit()
    return {"status": "revoked"}


# --- Service Principals ---

@app.post("/auth/token", tags=["Authentication"])
async def authenticate_service_principal(
    req: ServicePrincipalTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ServicePrincipal).where(ServicePrincipal.client_id == req.client_id)
    )
    sp = result.scalar_one_or_none()

    if not sp or not verify_password(req.client_secret, sp.client_secret_hash):
        raise HTTPException(401, "Invalid credentials")

    if not sp.is_active:
        raise HTTPException(403, "Service principal is disabled")

    if sp.expires_at and sp.expires_at < datetime.utcnow():
        raise HTTPException(403, "Service principal has expired")

    token_data = {
        "sub": f"sp:{sp.name}",
        "role": sp.role,
        "type": "service_principal",
        "sp_id": sp.id,
        "tv": 0,
    }
    access_token = create_access_token(data=token_data)

    sp.last_used_at = datetime.utcnow()

    db.add(AuditLog(
        username=f"sp:{sp.name}",
        action="sp:authenticated",
        resource_id=sp.id,
        detail=None,
    ))
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer", "role": sp.role}


@app.post("/admin/service-principals", tags=["Service Principals"])
async def create_service_principal(
    req: ServicePrincipalCreate,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    import secrets as _secrets

    client_id = "sp_" + uuid.uuid4().hex
    client_secret = "mop_sp_" + _secrets.token_hex(24)
    secret_hash = get_password_hash(client_secret)

    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

    sp = ServicePrincipal(
        id=str(uuid.uuid4()),
        name=req.name,
        description=req.description,
        role=req.role,
        client_id=client_id,
        client_secret_hash=secret_hash,
        is_active=True,
        created_by=current_user.username,
        expires_at=expires_at,
    )
    db.add(sp)
    audit(db, current_user, "sp:created", sp.id, {"name": sp.name, "role": sp.role})
    await db.commit()

    return ServicePrincipalCreatedResponse(
        id=sp.id, name=sp.name, description=sp.description, role=sp.role,
        client_id=client_id, client_secret=client_secret, is_active=True,
        created_by=current_user.username, expires_at=expires_at,
        created_at=sp.created_at,
    )


@app.get("/admin/service-principals", response_model=list[ServicePrincipalResponse], tags=["Service Principals"])
async def list_service_principals(
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServicePrincipal))
    return result.scalars().all()


@app.patch("/admin/service-principals/{sp_id}", tags=["Service Principals"])
async def update_service_principal(
    sp_id: str,
    req: ServicePrincipalUpdate,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServicePrincipal).where(ServicePrincipal.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Service principal not found")

    if req.name is not None:
        sp.name = req.name
    if req.description is not None:
        sp.description = req.description
    if req.role is not None:
        if req.role not in ALLOWED_ROLES:
            raise HTTPException(400, f"role must be one of {sorted(ALLOWED_ROLES)}")
        sp.role = req.role
    if req.is_active is not None:
        sp.is_active = req.is_active

    audit(db, current_user, "sp:updated", sp_id)
    await db.commit()

    return ServicePrincipalResponse.model_validate(sp)


@app.delete("/admin/service-principals/{sp_id}", tags=["Service Principals"])
async def delete_service_principal(
    sp_id: str,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServicePrincipal).where(ServicePrincipal.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Service principal not found")

    await db.delete(sp)
    audit(db, current_user, "sp:deleted", sp_id, {"name": sp.name})
    await db.commit()
    return {"status": "deleted"}


@app.post("/admin/service-principals/{sp_id}/rotate-secret", tags=["Service Principals"])
async def rotate_sp_secret(
    sp_id: str,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    import secrets as _secrets

    result = await db.execute(select(ServicePrincipal).where(ServicePrincipal.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Service principal not found")

    new_secret = "mop_sp_" + _secrets.token_hex(24)
    sp.client_secret_hash = get_password_hash(new_secret)

    audit(db, current_user, "sp:secret_rotated", sp_id, {"name": sp.name})
    await db.commit()

    return ServicePrincipalRotateResponse(
        client_id=sp.client_id,
        client_secret=new_secret,
    )


# --- Core Endpoints ---

@app.get("/", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "Agent Service v0.7"}

@app.get("/jobs", response_model=List[JobResponse], tags=["Jobs"])
async def list_jobs(skip: int = 0, limit: int = 50, status: Optional[str] = None, current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    return await JobService.list_jobs(db, skip=skip, limit=limit, status=status)

@app.get("/jobs/count", tags=["Jobs"])
async def count_jobs(status: Optional[str] = None, current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    query = select(sqlfunc.count()).select_from(Job).where(Job.task_type != 'system_heartbeat')
    if status and status.upper() != 'ALL':
        query = query.where(Job.status == status.upper())
    result = await db.execute(query)
    return {"total": result.scalar()}

@app.get("/api/jobs/stats", tags=["Jobs"])
async def get_job_stats(current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    """Backend Stats for Dashboard charts."""
    return await JobService.get_job_stats(db)


# ---------------------------------------------------------------------------
# CI/CD Dispatch API  (ENVTAG-04)
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"}


@app.post("/api/dispatch", response_model=DispatchResponse, tags=["CI/CD Dispatch"])
async def dispatch_job(
    req: DispatchRequest,
    request: Request,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """CI/CD dispatch endpoint. Creates a job from a job definition and returns a poll URL.
    Intended caller: service principals with jobs:write permission.
    No-node condition: job is created as PENDING; pipelines detect timeout by polling poll_url."""

    # 1. Fetch the job definition
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == req.job_definition_id))
    s_job = result.scalar_one_or_none()
    if not s_job:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_definition_not_found", "job_definition_id": req.job_definition_id},
        )

    # 2. Resolve env_tag: dispatch request overrides definition's env_tag; fall back to definition
    effective_env_tag = req.env_tag if req.env_tag is not None else s_job.env_tag

    # 3. Build JobCreate
    payload_dict = {
        "script_content": s_job.script_content,
        "signature": s_job.signature_payload,
        "secrets": {},
    }
    job_create = JobCreate(
        task_type="python_script",
        payload=payload_dict,
        target_tags=json.loads(s_job.target_tags) if s_job.target_tags else None,
        capability_requirements=json.loads(s_job.capability_requirements) if s_job.capability_requirements else None,
        scheduled_job_id=s_job.id,
        max_retries=req.max_retries if req.max_retries is not None else s_job.max_retries,
        backoff_multiplier=s_job.backoff_multiplier,
        timeout_minutes=req.timeout_minutes if req.timeout_minutes is not None else s_job.timeout_minutes,
        env_tag=effective_env_tag,
    )

    # 4. Create the job
    job_result = await JobService.create_job(job_create, db)
    job_guid = job_result["guid"]

    # 5. Build poll_url — use PUBLIC_URL env var to avoid localhost in Docker
    public_url = os.getenv("PUBLIC_URL", str(request.base_url).rstrip("/"))
    poll_url = f"{public_url}/api/dispatch/{job_guid}/status"

    # 6. Audit (sync — do not await, must be before db.commit)
    audit(db, current_user, "dispatch_job", job_guid,
          {"job_definition_id": req.job_definition_id, "env_tag": effective_env_tag})
    await db.commit()

    return DispatchResponse(
        job_guid=job_guid,
        status=job_result.get("status", "PENDING"),
        job_definition_id=s_job.id,
        job_definition_name=s_job.name,
        env_tag=effective_env_tag,
        poll_url=poll_url,
    )


@app.get("/api/dispatch/{job_guid}/status", response_model=DispatchStatusResponse, tags=["CI/CD Dispatch"])
async def get_dispatch_status(
    job_guid: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """CI/CD poll endpoint. Returns structured status for a dispatched job.
    Poll this URL until is_terminal=True to detect pass/fail in pipelines."""

    # 1. Fetch job
    result = await db.execute(select(Job).where(Job.guid == job_guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": "job_not_found", "job_guid": job_guid},
        )

    # 2. Fetch most recent execution record for exit_code
    er_result = await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.job_guid == job_guid)
        .order_by(ExecutionRecord.completed_at.desc())
        .limit(1)
    )
    latest_record = er_result.scalar_one_or_none()

    return DispatchStatusResponse(
        job_guid=job.guid,
        status=job.status,
        exit_code=latest_record.exit_code if latest_record else None,
        node_id=job.node_id,
        attempt=job.retry_count + 1,
        started_at=job.started_at,
        completed_at=job.completed_at,
        is_terminal=job.status in _TERMINAL_STATUSES,
    )


@app.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(job_req: JobCreate, current_user: User = Depends(require_permission("jobs:write")), db: AsyncSession = Depends(get_db)):
    try:
        result = await JobService.create_job(job_req, db)
        await ws_manager.broadcast("job:created", {"guid": result["guid"], "status": "PENDING", "task_type": job_req.task_type})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/jobs/{guid}/cancel", tags=["Jobs"])
async def cancel_job(guid: str, current_user: User = Depends(require_permission("jobs:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PENDING", "ASSIGNED"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a job with status {job.status}")
    job.status = "CANCELLED"
    job.completed_at = datetime.utcnow()
    audit(db, current_user, "job:cancel", guid)
    await db.commit()
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": "CANCELLED"})
    return {"status": "cancelled", "guid": guid}

@app.post("/jobs/{guid}/retry", tags=["Jobs"])
async def retry_job(
    guid: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    """Resets a FAILED or DEAD_LETTER job to PENDING."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "DEAD_LETTER"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry job with status {job.status}. Only FAILED and DEAD_LETTER jobs can be retried."
        )
    job.status = "PENDING"
    job.retry_count = 0
    job.retry_after = None
    job.node_id = None
    job.completed_at = None
    audit(db, current_user, "job:retry", guid)
    await db.commit()
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": "PENDING"})
    return {"status": "PENDING", "guid": guid}

@app.get("/jobs/{guid}/executions", tags=["Jobs"])
async def list_executions(
    guid: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.job_guid == guid)
        .order_by(ExecutionRecord.id.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "job_guid": r.job_guid,
            "node_id": r.node_id,
            "status": r.status,
            "exit_code": r.exit_code,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "output_log": json.loads(r.output_log) if r.output_log else [],
            "truncated": r.truncated,
            "duration_seconds": (
                (r.completed_at - r.started_at).total_seconds()
                if r.started_at and r.completed_at else None
            )
        }
        for r in records
    ]

@app.post("/work/pull", response_model=PollResponse, tags=["Node Agent"])
async def pull_work(request: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = request.client.host
    r = await db.execute(select(Node).where(Node.node_id == node_id))
    n = r.scalar_one_or_none()
    if n and n.status == "REVOKED":
        raise HTTPException(status_code=403, detail="Node is revoked")
    return await JobService.pull_work(node_id, node_ip, db)

@app.post("/heartbeat", tags=["Node Agent"])
async def receive_heartbeat(req: Request, hb: HeartbeatPayload, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    result = await JobService.receive_heartbeat(node_id, node_ip, hb, db)
    await ws_manager.broadcast("node:heartbeat", {"node_id": node_id, "status": "ONLINE", "stats": hb.stats})
    return result

@app.post("/work/{guid}/result", tags=["Node Agent"])
async def report_result(guid: str, report: ResultReport, req: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    if report.result:
        report.result = mask_pii(report.result)
        
    updated = await JobService.report_result(guid, report, node_ip, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": updated.get("status", "COMPLETED")})
    return updated

@app.get("/nodes", response_model=List[NodeResponse], tags=["Nodes"])
async def list_nodes(current_user: User = Depends(require_permission("nodes:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node))
    nodes = result.scalars().all()

    # Fetch stats history for all nodes in one query
    history_map: dict = defaultdict(list)
    if nodes:
        node_ids = [n.node_id for n in nodes]
        hist_result = await db.execute(
            select(NodeStats)
            .where(NodeStats.node_id.in_(node_ids))
            .order_by(desc(NodeStats.recorded_at))
        )
        for stat in hist_result.scalars().all():
            bucket = history_map[stat.node_id]
            if len(bucket) < 20:
                bucket.append({"t": stat.recorded_at.isoformat(), "cpu": stat.cpu, "ram": stat.ram})
        # Reverse each bucket so oldest→newest (chronological for charts)
        for k in history_map:
            history_map[k].reverse()

    resp = []
    for n in nodes:
        if n.status == "REVOKED":
            status = "REVOKED"
        else:
            is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
            status = "OFFLINE" if is_offline else "ONLINE"

        stats = json.loads(n.stats) if n.stats else None
        reported_tags = json.loads(n.tags) if n.tags else []
        op_tags = json.loads(n.operator_tags) if n.operator_tags else None
        effective_tags = op_tags if op_tags is not None else reported_tags

        resp.append({
            "node_id": n.node_id,
            "hostname": n.hostname,
            "ip": n.ip,
            "last_seen": n.last_seen,
            "status": status,
            "base_os_family": n.base_os_family,
            "stats": stats,
            "tags": effective_tags,
            "is_operator_managed": op_tags is not None,
            "capabilities": json.loads(n.capabilities) if n.capabilities else None,
            "concurrency_limit": n.concurrency_limit,
            "job_memory_limit": n.job_memory_limit,
            "stats_history": history_map.get(n.node_id, []),
        })
    return resp

@app.patch("/nodes/{node_id}", tags=["Nodes"])
async def update_node_config(node_id: str, config: NodeConfig, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.concurrency_limit = config.concurrency_limit
    node.job_memory_limit = config.job_memory_limit
    if config.tags is not None:
        node.operator_tags = json.dumps(config.tags)
    
    await db.commit()
    return {
        "status": "updated", 
        "node_id": node_id, 
        "concurrency_limit": config.concurrency_limit, 
        "job_memory_limit": config.job_memory_limit,
        "tags": config.tags
    }

@app.delete("/nodes/{node_id}", status_code=204, tags=["Nodes"])
async def delete_node(node_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove nodes")
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.execute(delete(NodeStats).where(NodeStats.node_id == node_id))
    await db.execute(delete(Ping).where(Ping.node_id == node_id))
    audit(db, current_user, "node:delete", node_id)
    await db.delete(node)
    await db.commit()
    return Response(status_code=204)

@app.post("/nodes/{node_id}/revoke", tags=["Nodes"])
async def revoke_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status == "REVOKED":
        raise HTTPException(status_code=409, detail="Node is already revoked")
    node.status = "REVOKED"
    if node.client_cert_pem:
        try:
            parsed = _x509.load_pem_x509_certificate(node.client_cert_pem.encode())
            db.add(RevokedCert(serial_number=str(parsed.serial_number), node_id=node_id))
        except Exception:
            pass
    audit(db, current_user, "node:revoke", node_id)
    await db.commit()
    return {"status": "revoked", "node_id": node_id}

@app.post("/api/nodes/{node_id}/clear-tamper", tags=["Nodes"])
async def clear_node_tamper(node_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Resets a node from TAMPERED to ONLINE after administrator review."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can clear tamper alerts")
    
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node.status != "TAMPERED":
        return {"status": "skipped", "message": "Node is not in tampered state"}
        
    node.status = "ONLINE"
    node.tamper_details = None
    await db.commit()
    
    audit(db, current_user, "node:clear_tamper", node_id)
    return {"status": "cleared", "node_id": node_id}

@app.post("/api/nodes/{node_id}/upgrade", tags=["Nodes"])
async def stage_node_upgrade(
    node_id: str, 
    capability_id: int, 
    current_user: User = Depends(require_permission("foundry:write")), 
    db: AsyncSession = Depends(get_db)
):
    """Stages a signed hot-upgrade for a specific node."""
    # 1. Fetch Node
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # 2. Fetch Capability Recipe
    cap_res = await db.execute(select(CapabilityMatrix).where(CapabilityMatrix.id == capability_id))
    cap = cap_res.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability recipe not found")
    
    # 3. Macro Expansion
    recipe = cap.injection_recipe
    artifact_url = None
    if cap.artifact_id:
        base_url = os.getenv("AGENT_URL", "https://localhost:8001")
        artifact_url = f"{base_url}/api/artifacts/{cap.artifact_id}/download"
        recipe = recipe.replace("{{ARTIFACT_URL}}", artifact_url)
    
    # 4. Sign the recipe
    # We use the same signature_service used for jobs
    signature = await SignatureService.sign_payload(recipe, db)
    
    # 5. Store task
    upgrade_task = {
        "tool_id": cap.tool_id,
        "recipe": recipe,
        "artifact_url": artifact_url,
        "validation_cmd": cap.validation_cmd,
        "signature": signature
    }
    
    node.pending_upgrade = json.dumps(upgrade_task)
    node.status = "UPGRADING"
    
    await db.commit()
    audit(db, current_user, "node:upgrade_staged", node_id, {"tool_id": cap.tool_id})
    
    return {"status": "staged", "node_id": node_id, "tool_id": cap.tool_id}

@app.post("/nodes/{node_id}/reinstate", tags=["Nodes"])
async def reinstate_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "REVOKED":
        raise HTTPException(status_code=409, detail="Node is not revoked")
    node.status = "OFFLINE"
    audit(db, current_user, "node:reinstate", node_id)
    await db.commit()
    return {"status": "reinstated", "node_id": node_id}

@app.post("/auth/register", response_model=RegisterResponse, tags=["Authentication"])
async def register_node(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Token).where(Token.token == req.client_secret))
    token_entry = result.scalar_one_or_none()
    
    if not token_entry:
         raise HTTPException(status_code=403, detail="Invalid Join Token")

    try:
        signed_cert = pki_service.sign_csr(req.csr_pem, req.hostname)
        return {
            "client_cert_pem": signed_cert,
            "ca_url": "https://localhost:8001" 
        }
    except Exception as e:
        logger.error(f"CSR Signing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sign CSR: {str(e)}")

@app.post("/api/enroll", response_model=RegisterResponse, tags=["Node Agent"])
async def enroll_node(req: EnrollmentRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint for secure node enrollment using a one-time token."""
    # 1. Verify Token
    result = await db.execute(select(Token).where(Token.token == req.token, Token.used == False))
    token_entry = result.scalar_one_or_none()
    
    if not token_entry:
         raise HTTPException(status_code=403, detail="Invalid or Expired Enrollment Token")

    # 2. Invalidate Token immediately
    token_entry.used = True
    
    try:
        # 3. Sign CSR
        signed_cert = pki_service.sign_csr(req.csr_pem, req.hostname)
        
        # 4. Create or Update Node with the secret binding
        node_id = req.hostname # Or derived from CSR/Certificate
        node_ip = request.client.host

        # Derive authorized capabilities from template if assigned
        expected_caps = None
        os_family = None
        if token_entry.template_id:
            tmpl_res = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == token_entry.template_id))
            tmpl = tmpl_res.scalar_one_or_none()
            if tmpl:
                if tmpl.status == "REVOKED":
                    raise HTTPException(status_code=403, detail="Blueprint for this enrollment has been REVOKED")
                os_family = tmpl.os_family
                # Load runtime blueprint
                rt_res = await db.execute(select(Blueprint).where(Blueprint.id == tmpl.runtime_blueprint_id))
                rt_bp = rt_res.scalar_one_or_none()
                if rt_bp:
                    rt_def = json.loads(rt_bp.definition)
                    # Tools form the authorized baseline
                    # Format: {tool_id: "latest"}
                    expected_caps = {tool['id']: "latest" for tool in rt_def.get("tools", [])}

        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()

        if node:
            if node.status == "REVOKED":
                raise HTTPException(status_code=403, detail="Node has been revoked and cannot re-enroll")
            node.node_secret_hash = req.node_secret_hash
            node.machine_id = req.machine_id
            node.ip = node_ip
            node.last_seen = datetime.utcnow()
            node.client_cert_pem = signed_cert
            node.base_os_family = os_family
            node.template_id = token_entry.template_id
            if expected_caps:
                node.expected_capabilities = json.dumps(expected_caps)
        else:
            node = Node(
                node_id=node_id,
                hostname=req.hostname,
                ip=node_ip,
                status="ONLINE",
                base_os_family=os_family,
                template_id=token_entry.template_id,
                machine_id=req.machine_id,
                node_secret_hash=req.node_secret_hash,
                client_cert_pem=signed_cert,
                expected_capabilities=json.dumps(expected_caps) if expected_caps else None
            )
            db.add(node)
        await db.commit()
        
        return {
            "client_cert_pem": signed_cert,
            "ca_url": f"{request.base_url}" 
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Enrollment Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")

# --- Admin Endpoints ---

import base64

@app.post("/admin/generate-token", tags=["Admin"])
@limiter.limit("10/minute")
async def generate_token(request: Request, current_user: User = Depends(require_permission("tokens:write")), db: AsyncSession = Depends(get_db)):
         
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
    return {"token": b64_token}

# --- Blueprint & Template Management ---

@app.post("/api/blueprints", response_model=BlueprintResponse, status_code=201, tags=["Foundry"])
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
        os_family=req.os_family,      # write os_family to DB column
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

@app.get("/api/blueprints", response_model=List[BlueprintResponse], tags=["Foundry"])
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
        "os_family": bp.os_family,  # NEW
    } for bp in bps]

# Legacy/Frontend Aliases
@app.get("/foundry/definitions", tags=["Foundry"])
async def foundry_definitions(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/definitions instead of /api/blueprints"""
    return await list_blueprints(current_user, db)

@app.get("/job-definitions", tags=["Job Definitions"])
async def dashboard_job_definitions(current_user: User = Depends(require_permission("definitions:read")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)

@app.post("/api/templates", response_model=PuppetTemplateResponse, tags=["Foundry"])
async def create_template(req: PuppetTemplateCreate, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    
    # Verify Blueprints exist
    rt_res = await db.execute(select(Blueprint).where(Blueprint.id == req.runtime_blueprint_id, Blueprint.type == 'RUNTIME'))
    nw_res = await db.execute(select(Blueprint).where(Blueprint.id == req.network_blueprint_id, Blueprint.type == 'NETWORK'))
    
    rt_bp = rt_res.scalar_one_or_none()
    nw_bp = nw_res.scalar_one_or_none()
    
    if not rt_bp or not nw_bp:
        raise HTTPException(status_code=400, detail="Invalid Runtime or Network Blueprint ID")

    # Generate Canonical ID (Simple hash of blueprint names and versions for now)
    import hashlib
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

@app.get("/api/templates", response_model=List[PuppetTemplateResponse], tags=["Foundry"])
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

@app.post("/api/templates/{id}/build", response_model=ImageResponse, tags=["Foundry"])
async def build_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await foundry_service.build_template(id, db)
    if not result.status.startswith("SUCCESS"):
        raise HTTPException(status_code=500, detail=result.status)
    audit(db, current_user, "template:build", id)
    await db.commit()
    return result

@app.post("/foundry/build", tags=["Foundry"])
async def dashboard_foundry_build(req: dict, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/build with template_id in body"""
    template_id = req.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="Missing template_id in body")
    return await build_template(template_id, current_user, db)

@app.delete("/api/blueprints/{id}", tags=["Foundry"])
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

@app.delete("/api/templates/{id}", tags=["Foundry"])
async def delete_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    audit(db, current_user, "template:delete", id, {"name": tmpl.friendly_name})
    await db.delete(tmpl)
    await db.commit()
    return {"status": "deleted"}

# --- Image BOM & Lifecycle Management ---

@app.patch("/api/templates/{id}/status", tags=["Foundry"])
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

@app.get("/api/templates/{id}/bom", response_model=ImageBOMResponse, tags=["Foundry"])
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

@app.get("/api/foundry/search-packages", response_model=List[PackageIndexResponse], tags=["Foundry"])
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

@app.get("/api/capability-matrix", response_model=List[CapabilityMatrixEntry], tags=["Foundry"])
async def get_capability_matrix(
    os_family: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
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

# --- Foundry & Enrollment Endpoints ---

@app.post("/api/images", response_model=ImageResponse, tags=["Foundry"])
async def create_image(req: ImageBuildRequest, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return await foundry_service.build_image(req)

@app.get("/api/images", response_model=List[ImageResponse], tags=["Foundry"])
async def list_images(current_user: User = Depends(get_current_user)):
    return await foundry_service.list_images()

@app.post("/api/enrollment-tokens", tags=["Node Agent"])
async def create_enrollment_token(req: Optional[EnrollmentTokenCreate] = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create enrollment tokens")

    token_str = uuid.uuid4().hex
    token_entry = Token(token=token_str)
    if req and req.template_id:
        token_entry.template_id = req.template_id

    db.add(token_entry)
    await db.commit()
    return {"token": token_str}
@app.post("/admin/upload-key", tags=["Admin"])
async def upload_public_key(req: UploadKeyRequest, current_user: User = Depends(require_permission("signatures:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if row:
        row.value = req.key_content
    else:
        db.add(Config(key="signing_public_key", value=req.key_content))
    audit(db, current_user, "key:upload")
    await db.commit()
    return {"status": "stored"}

# --- User Management Endpoints ---

@app.get("/admin/users", response_model=List[UserResponse], tags=["User Management"])
async def list_users(current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.username, "username": u.username, "role": u.role, "created_at": u.created_at} for u in users]

@app.post("/admin/users", response_model=UserResponse, status_code=201, tags=["User Management"])
async def create_user(req: UserCreate, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    new_user = User(username=req.username, password_hash=get_password_hash(req.password), role=req.role)
    db.add(new_user)
    audit(db, current_user, "user:create", req.username, {"role": req.role})
    await db.commit()
    return {"id": new_user.username, "username": new_user.username, "role": new_user.role, "created_at": new_user.created_at}

@app.delete("/admin/users/{username}", tags=["User Management"])
async def delete_user(username: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    audit(db, current_user, "user:delete", username)
    await db.delete(user)
    await db.commit()
    return {"status": "deleted", "username": username}

@app.patch("/admin/users/{username}", response_model=UserResponse, tags=["User Management"])
async def update_user_role(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "role" in req:
        user.role = req["role"]
    audit(db, current_user, "user:role_change", username, {"role": req.get("role")})
    await db.commit()
    return {"id": user.username, "username": user.username, "role": user.role, "created_at": user.created_at}

# --- Role Permission Management Endpoints ---

@app.get("/admin/roles/{role}/permissions", tags=["User Management"])
async def list_role_permissions(role: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role))
    perms = result.scalars().all()
    return [{"id": p.id, "role": p.role, "permission": p.permission} for p in perms]

@app.post("/admin/roles/{role}/permissions", status_code=201, tags=["User Management"])
async def grant_role_permission(role: str, req: PermissionGrant, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == req.permission))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Permission already granted")
    db.add(RolePermission(role=role, permission=req.permission))
    audit(db, current_user, "permission:grant", role, {"permission": req.permission})
    await db.commit()
    _invalidate_perm_cache(role)
    return {"status": "granted", "role": role, "permission": req.permission}

@app.delete("/admin/roles/{role}/permissions/{permission}", tags=["User Management"])
async def revoke_role_permission(role: str, permission: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == permission))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    audit(db, current_user, "permission:revoke", role, {"permission": permission})
    await db.delete(perm)
    await db.commit()
    _invalidate_perm_cache(role)
    return {"status": "revoked", "role": role, "permission": permission}

@app.patch("/admin/users/{username}/reset-password", tags=["User Management"])
async def admin_reset_password(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    """Admin sets a new password for any user."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.password_hash = get_password_hash(new_password)
    user.token_version = (user.token_version or 0) + 1  # invalidate all existing sessions
    audit(db, current_user, "user:password_reset", detail={"target": username, "by": current_user.username})
    await db.commit()
    return {"status": "ok"}

@app.patch("/admin/users/{username}/force-password-change", tags=["User Management"])
async def admin_force_password_change(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    """Set or clear the must_change_password flag for a user."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    enabled = bool(req.get("enabled", True))
    user.must_change_password = enabled
    action = "user:force_password_change_set" if enabled else "user:force_password_change_cleared"
    audit(db, current_user, action, detail={"target": username})
    await db.commit()
    return {"status": "ok", "must_change_password": enabled}

@app.get("/config/public-key", tags=["System"])
async def get_public_key(x_join_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Token).where(Token.token == x_join_token))
    if not result.scalar_one_or_none():
         raise HTTPException(status_code=403, detail="Invalid Join Token")

    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"public_key": row.value}

# --- Configuration Endpoints ---

@app.get("/config/mounts", response_model=List[NetworkMount], tags=["System"])
async def get_network_mounts(
    db: AsyncSession = Depends(get_db), 
    user: Optional[User] = Depends(get_current_user_optional),
    x_join_token: Optional[str] = Header(None)
):
    is_admin = user and user.role == "admin"
    is_valid_token = False
    
    if x_join_token:
         result = await db.execute(select(Token).where(Token.token == x_join_token))
         if result.scalar_one_or_none():
             is_valid_token = True
             
    if not (is_admin or is_valid_token):
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

@app.post("/config/mounts", tags=["System"])
async def update_network_mounts(config: MountsConfig, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
    for m in config.mounts:
        if not m.name.replace("_", "").isalnum():
             raise HTTPException(status_code=400, detail=f"Invalid mount name: {m.name}")
    
    json_str = json.dumps([m.dict() for m in config.mounts])
    
    result = await db.execute(select(Config).where(Config.key == "global_network_mounts"))
    row = result.scalar_one_or_none()
    if row:
        row.value = json_str
    else:
        db.add(Config(key="global_network_mounts", value=json_str))
    
    await db.commit()
    return {"status": "updated", "count": len(config.mounts)}

# --- Signature Registry API ---

@app.post("/signatures", response_model=SignatureResponse, tags=["Signatures"])
async def upload_signature(sig: SignatureCreate, current_user: User = Depends(require_permission("signatures:write")), db: AsyncSession = Depends(get_db)):
    return await SignatureService.upload_signature(sig, current_user, db)

@app.get("/signatures", response_model=List[SignatureResponse], tags=["Signatures"])
async def list_signatures(current_user: User = Depends(require_permission("signatures:read")), db: AsyncSession = Depends(get_db)):
    return await SignatureService.list_signatures(db)

@app.delete("/signatures/{id}", tags=["Signatures"])
async def delete_signature(id: str, current_user: User = Depends(require_permission("signatures:write")), db: AsyncSession = Depends(get_db)):
    success = await SignatureService.delete_signature(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Signature not found")
    audit(db, current_user, "signature:delete", id)
    await db.commit()
    return {"status": "deleted"}

# --- Job Definitions API ---

@app.post("/jobs/definitions", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.create_job_definition(def_req, current_user, db)

@app.get("/jobs/definitions", response_model=List[JobDefinitionResponse], tags=["Job Definitions"])
async def list_job_definitions(current_user: User = Depends(require_permission("definitions:read")), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.list_job_definitions(db)

@app.delete("/jobs/definitions/{id}", tags=["Job Definitions"])
async def delete_job_definition(id: str, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    try:
        scheduler_service.scheduler.remove_job(id)
    except Exception:
        pass
    await db.delete(job_def)
    await db.commit()
    return {"status": "deleted"}

@app.patch("/jobs/definitions/{id}/toggle", tags=["Job Definitions"])
async def toggle_job_definition(id: str, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    job_def.is_active = not job_def.is_active
    await db.commit()
    await scheduler_service.sync_scheduler()
    return {"id": id, "is_active": job_def.is_active}

@app.get("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def get_job_definition(id: str, current_user: User = Depends(require_permission("definitions:read")), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.get_job_definition(id, db)

@app.post("/api/jobs/push", response_model=JobDefinitionResponse, status_code=201, tags=["Job Definitions"])
async def push_job_definition(
    req: JobPushRequest,
    current_user: User = Depends(require_permission("definitions:write")),
    db: AsyncSession = Depends(get_db),
):
    """RFC-compliant push endpoint: creates DRAFT or updates existing job with dual JWT+Ed25519 verification."""
    # 1. Validate Ed25519 signature BEFORE any DB write (STAGE-03)
    sig_result = await db.execute(select(Signature).where(Signature.id == req.signature_id))
    sig = sig_result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, detail="Signature ID not found")
    try:
        SignatureService.verify_payload_signature(sig.public_key, req.signature, req.script_content)
    except Exception as e:
        raise HTTPException(422, detail=f"Invalid Ed25519 signature: {e}")

    # 2. Identity attribution (STAGE-04)
    pushed_by = current_user.username  # "username" or "sp:name" for service principals

    # 3. Upsert logic (STAGE-02)
    if req.id:
        # Update existing job by ID
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == req.id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(404, detail="Job definition not found")
        if job.status == "REVOKED":
            raise HTTPException(409, detail={"error": "job_revoked", "id": job.id,
                                             "message": "Job is REVOKED. Un-REVOKE to DEPRECATED before re-pushing."})
        job.script_content = req.script_content
        job.signature_id = req.signature_id
        job.signature_payload = req.signature
        job.pushed_by = pushed_by
        job.updated_at = datetime.utcnow()
    else:
        # Create new job by name — check for name conflict first
        existing_result = await db.execute(select(ScheduledJob).where(ScheduledJob.name == req.name))
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise HTTPException(409, detail={"error": "name_conflict", "id": existing.id,
                                             "message": f"Job '{req.name}' already exists. Use id to update."})
        job = ScheduledJob(
            id=uuid.uuid4().hex,
            name=req.name,
            script_content=req.script_content,
            signature_id=req.signature_id,
            signature_payload=req.signature,
            schedule_cron="",  # DRAFT jobs have no schedule yet
            status="DRAFT",
            pushed_by=pushed_by,
            created_by=pushed_by,
        )
        db.add(job)

    audit(db, current_user, "job:pushed", job.id if req.id else None,
          {"name": req.name or job.name, "pushed_by": pushed_by, "action": "update" if req.id else "create"})
    await db.commit()
    await db.refresh(job)
    return JobDefinitionResponse.model_validate(job)

@app.patch("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def update_job_definition(id: str, update_req: JobDefinitionUpdate, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    # Admin-only REVOKE gate (GOV-CLI-01)
    if update_req.status == "REVOKED" and current_user.role != "admin":
        raise HTTPException(403, detail="Only admin can set a job to REVOKED status")

    return await scheduler_service.update_job_definition(id, update_req, current_user, db)

# --- Artifact Vault API ---

@app.post("/api/artifacts", response_model=ArtifactResponse, tags=["Artifacts"])
async def upload_artifact(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Upload a binary artifact to the secure vault."""
    return await vault_service.store_artifact(file, db)

@app.get("/api/artifacts", response_model=List[ArtifactResponse], tags=["Artifacts"])
async def list_artifacts(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all stored artifacts."""
    return await vault_service.list_artifacts(db)

@app.get("/api/artifacts/{id}/download", tags=["Artifacts"])
async def download_artifact(
    id: str,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Stream an artifact download from the vault."""
    result = await db.execute(select(Artifact).where(Artifact.id == id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    path = vault_service.get_artifact_path(id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    
    def iterfile():
        with open(path, mode="rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(), 
        media_type=artifact.content_type,
        headers={"Content-Disposition": f"attachment; filename={artifact.filename}"}
    )

@app.delete("/api/artifacts/{id}", tags=["Artifacts"])
async def delete_artifact(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Permanently remove an artifact."""
    success = await vault_service.delete_artifact(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"status": "deleted"}

# --- Approved OS API ---

@app.get("/api/approved-os", response_model=List[ApprovedOSResponse], tags=["Foundry"])
async def list_approved_os(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all pre-approved base OS images."""
    result = await db.execute(select(ApprovedOS).order_by(ApprovedOS.name))
    return result.scalars().all()

@app.post("/api/approved-os", response_model=ApprovedOSResponse, tags=["Foundry"])
async def create_approved_os(
    req: ApprovedOSResponse, 
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Register a new approved base OS image."""
    new_os = ApprovedOS(name=req.name, image_uri=req.image_uri, os_family=req.os_family)
    db.add(new_os)
    await db.commit()
    await db.refresh(new_os)
    return new_os

@app.delete("/api/approved-os/{id}", tags=["Foundry"])
async def delete_approved_os(
    id: int,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Remove a base image from the approved list."""
    result = await db.execute(select(ApprovedOS).where(ApprovedOS.id == id))
    os_entry = result.scalar_one_or_none()
    if not os_entry:
        raise HTTPException(status_code=404, detail="OS entry not found")
    await db.delete(os_entry)
    await db.commit()
    return {"status": "deleted"}

# --- Dynamic Capability Matrix API ---

@app.post("/api/capability-matrix", response_model=CapabilityMatrixEntry, tags=["Foundry"])
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

@app.patch("/api/capability-matrix/{id}", response_model=CapabilityMatrixEntry, tags=["Foundry"])
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

@app.delete("/api/capability-matrix/{id}", tags=["Foundry"])
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

# --- Installer & Doc Endpoints ---

@app.get("/api/installer", tags=["System"])
async def get_installer():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "installer", "install_node.ps1")
    
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail="Installer script not found")

    with open(file_path, "r") as f:
        content = f.read()
    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=install_node.ps1"})

@app.get("/api/docs", tags=["System"])
async def list_docs(current_user: User = Depends(require_permission("jobs:read"))):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(base_dir, "../docs")
            
    if not os.path.exists(docs_dir):
        return []

    files = []
    for f in os.listdir(docs_dir):
        if f.endswith(".md"):
            title = f
            try:
                with open(os.path.join(docs_dir, f), "r") as md_file:
                    first_line = md_file.readline().strip()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("# ").strip()
            except:
                pass
            files.append({"filename": f, "title": title})
    return files

@app.get("/api/docs/{filename}", tags=["System"])
async def get_doc_content(filename: str, current_user: User = Depends(require_permission("jobs:read"))):
    filename = os.path.basename(filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(base_dir, "../docs")
            
    if not docs_dir:
        raise HTTPException(status_code=404, detail="Docs directory not found")

    file_path = os.path.abspath(os.path.join(docs_dir, filename))
    if not file_path.startswith(os.path.abspath(docs_dir)):
        raise HTTPException(status_code=403, detail="Invalid path")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r") as f:
        content = f.read()
    return {"content": content}

# --- WebSocket Live Feed ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Live event feed. Requires a valid JWT passed as ?token=<jwt> query param."""
    await ws.accept()
    # Validate token
    authed = False
    if token:
        try:
            from jose import jwt as _jwt, JWTError
            from .auth import SECRET_KEY, ALGORITHM
            payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username:
                result = await db.execute(select(User).where(User.username == username))
                user = result.scalar_one_or_none()
                if user and payload.get("tv", 0) == user.token_version:
                    authed = True
        except Exception:
            pass
    if not authed:
        await ws.close(code=1008)
        return
    ws_manager._connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# --- Audit Log Endpoint ---

@app.get("/admin/audit-log", tags=["Audit Log"])
async def get_audit_log(
    limit: int = 200,
    current_user: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "username": r.username,
            "action": r.action,
            "resource_id": r.resource_id,
            "detail": json.loads(r.detail) if r.detail else None,
        }
        for r in rows
    ]

# --- Base Image Staleness Endpoints ---

@app.post("/admin/mark-base-updated", tags=["Admin"])
async def mark_base_updated(current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    """Records the current timestamp as the last time the base node image was updated."""
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

@app.get("/admin/base-image-updated", tags=["Admin"])
async def get_base_image_updated(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Config).where(Config.key == "base_node_image_updated_at"))
    row = result.scalar_one_or_none()
    return {"base_node_image_updated_at": row.value if row else None}

# --- CRL Endpoint ---

@app.get("/system/crl.pem", tags=["System"])
async def get_crl(db: AsyncSession = Depends(get_db)):
    """Returns a signed X.509 CRL of all revoked node certificates."""
    result = await db.execute(select(RevokedCert))
    revoked = result.scalars().all()
    serials = [r.serial_number for r in revoked]
    crl_pem = pki_service.ca_authority.generate_crl(serials)
    return Response(content=crl_pem, media_type="application/x-pem-file")

# --- Smelter Registry API ---

@app.get("/api/smelter/ingredients", response_model=List[ApprovedIngredientResponse], tags=["Smelter Registry"])
async def list_smelter_ingredients(
    os_family: Optional[str] = None,
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all approved ingredients in the Smelter Catalog (Admin/Operator)."""
    return await SmelterService.list_ingredients(db, os_family)

@app.post("/api/smelter/ingredients", response_model=ApprovedIngredientResponse, tags=["Smelter Registry"])
async def add_smelter_ingredient(
    ingredient: ApprovedIngredientCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Add a new vetted ingredient to the Smelter Catalog (Admin Only)."""
    item = await SmelterService.add_ingredient(db, ingredient)
    audit(db, current_user, "smelter:ingredient_added", item.name)
    return item

@app.delete("/api/smelter/ingredients/{id}", tags=["Smelter Registry"])
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

@app.get("/api/smelter/config", tags=["Smelter Registry"])
async def get_smelter_config(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get the current Smelter enforcement mode (STRICT vs WARNING)."""
    result = await db.execute(select(Config).where(Config.key == "smelter_enforcement_mode"))
    cfg = result.scalar_one_or_none()
    return {"smelter_enforcement_mode": cfg.value if cfg else "WARNING"}

@app.patch("/api/smelter/config", tags=["Smelter Registry"])
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

@app.get("/api/smelter/mirror-health", tags=["Smelter Registry"])
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

@app.get("/api/admin/mirror-config", tags=["Smelter Registry"])
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


@app.put("/api/admin/mirror-config", tags=["Smelter Registry"])
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

@app.post("/api/smelter/ingredients/{id}/upload", tags=["Smelter Registry"])
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

@app.post("/api/smelter/scan", tags=["Smelter Registry"])
async def trigger_smelter_scan(
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a vulnerability scan of the Smelter Catalog (Admin Only)."""
    summary = await SmelterService.scan_vulnerabilities(db)
    audit(db, current_user, "smelter:scan_triggered", json.dumps(summary))
    return summary

# --- Trigger API (Automation) ---

@app.post("/api/trigger/{slug}", tags=["Headless Automation"])
async def fire_automation_trigger(
    slug: str,
    request: Request,
    x_mop_trigger_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Headless endpoint for CI/CD pipelines to fire a job trigger.
    
    - **slug**: The unique URL slug for the trigger.
    - **X-MOP-Trigger-Key**: The secret token associated with this trigger.
    - **Body**: (Optional) JSON object containing variables to inject into the job payload.
    """
    payload_data = {}
    try:
        # Optional JSON body for variable injection
        if await request.body():
            payload_data = await request.json()
    except:
        pass
        
    return await trigger_service.fire_trigger(slug, x_mop_trigger_key, payload_data, db)

@app.get("/api/admin/triggers", response_model=List[TriggerResponse], tags=["Headless Automation"])
async def list_automation_triggers(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all registered automation triggers (Admin Only)."""
    return await trigger_service.list_triggers(db)

@app.post("/api/admin/triggers", response_model=TriggerResponse, tags=["Headless Automation"])
async def register_automation_trigger(
    req: TriggerCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new URL slug and token for a specific job definition (Admin Only)."""
    return await trigger_service.create_trigger(req.name, req.slug, req.job_definition_id, db)

@app.delete("/api/admin/triggers/{id}", tags=["Headless Automation"])
async def remove_automation_trigger(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete an automation trigger (Admin Only)."""
    success = await trigger_service.delete_trigger(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"status": "deleted"}

@app.patch("/api/admin/triggers/{id}", response_model=TriggerResponse, tags=["Headless Automation"])
async def update_automation_trigger(
    id: str,
    req: TriggerUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Toggle is_active or update name on an automation trigger (Admin Only)."""
    return await trigger_service.update_trigger(id, req.is_active, db)

@app.post("/api/admin/triggers/{id}/regenerate-token", response_model=TriggerResponse, tags=["Headless Automation"])
async def regenerate_trigger_token(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Rotate the secret token for an automation trigger (Admin Only)."""
    return await trigger_service.regenerate_token(id, db)

# --- Signal API (Reactive Orchestration) ---

@app.post("/api/signals/{name}", tags=["Headless Automation"])
async def fire_signal(
    name: str,
    req: Optional[SignalFire] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fire a named signal to unblock dependent jobs.
    
    Authenticated via Bearer Token (User) or API Key (Service Principal).
    """
    # Check permission
    # For now, allow operators and admins
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions to fire signals")

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
    
    # Trigger unblocking
    await JobService.unblock_jobs_by_signal(name, db)
    
    return {"status": "fired", "name": name}

@app.get("/api/signals", response_model=List[SignalResponse], tags=["Headless Automation"])
async def list_signals(
    current_user: User = Depends(require_permission("foundry:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all currently active signals (Admin Only)."""
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

@app.delete("/api/signals/{name}", tags=["Headless Automation"])
async def clear_signal(
    name: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Clear a signal from the system (Admin Only)."""
    result = await db.execute(select(Signal).where(Signal.name == name))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, "Signal not found")
    
    await db.delete(sig)
    await db.commit()
    return {"status": "cleared"}

if __name__ == "__main__":
    import uvicorn
    try:
        print("🔐 Initializing Packet PKI...")
        pki_service.ca_authority.ensure_root_ca()
        pki_service.ca_authority.ensure_signing_key("secrets")
        
        cert_path = "secrets/cert.pem"
        key_path = "secrets/key.pem"
        ssl_enabled = False
        
        if os.path.exists(cert_path) and os.path.exists(key_path):
             print(f"✅ Found Server Certs at {cert_path}. Enabling HTTPS.")
             ssl_enabled = True
        else:
             print(f"⚠️ No Server Cert found. Generating Local Self-Signed Cert...")
             hostname = socket.gethostname()
             try:
                 ip = socket.gethostbyname(hostname)
             except Exception:
                 ip = "127.0.0.1"
             sans = ["localhost", "master-of-puppets", "agent", "puppeteer-agent-1", hostname, ip]
             # Include the AGENT_URL host/IP in the SAN so remote nodes can connect
             agent_url = os.getenv("AGENT_URL", "")
             if agent_url:
                 import re as _re
                 m = _re.match(r"https?://([^:/]+)", agent_url)
                 if m:
                     agent_host = m.group(1)
                     if agent_host not in sans:
                         sans.append(agent_host)
                         print(f"   Adding AGENT_URL host to SAN: {agent_host}")
             try:
                pki_service.ca_authority.issue_server_cert(key_path, cert_path, sans)
                ssl_enabled = True
             except Exception as e:
                print(f"❌ Failed to generate certs: {e}")
    except Exception as e:
        print(f"❌ PKI Bootstrap Failed: {e}")

    if ssl_enabled:
        uvicorn.run(app, host="0.0.0.0", port=8001, ssl_keyfile=key_path, ssl_certfile=cert_path)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001)

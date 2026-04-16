from fastapi import FastAPI, HTTPException, Request, Depends, Header, status, WebSocket, WebSocketDisconnect, Query, Form, Body
from fastapi.responses import Response, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import csv
import html as _html
import io
import math
import secrets as _secrets
from pathlib import Path
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
    ResultReport, TokenResponse, HeartbeatPayload, PollResponse, NodeUpdateRequest,
    NodeResponse, SignatureCreate, SignatureResponse, UserResponse, JobDefinitionCreate, JobDefinitionUpdate,
    JobDefinitionResponse, JobPushRequest, PingRequest, NetworkMount, MountsConfig,
    UploadKeyRequest,
    EnrollmentTokenCreate,
    EnrollmentRequest,
    SignalFire, SignalResponse,
    ExecutionRecordResponse,
    AttestationExportResponse,
    AlertResponse,
    DispatchRequest, DispatchResponse, DispatchStatusResponse,
    BulkJobActionRequest, BulkActionResponse, BulkDiagnosisRequest,
    SchedulingHealthResponse, DefinitionHealthRow, ScaleHealthResponse,
    SystemHealthResponse, FeaturesResponse, LicenceStatusResponse,
    DeviceCodeResponse, EnrollmentTokenResponse,
    JobTemplateCreate, JobTemplateUpdate, JobTemplateResponse, RetentionConfigUpdate,
    LicenceReloadRequest, LicenceReloadResponse,
    SIGNING_FIELDS,
    PaginatedResponse, ActionResponse, JobCountResponse, JobStatsResponse, DispatchDiagnosisResponse, BulkDispatchDiagnosisResponse,
    DependencyTreeResponse, DiscoverDependenciesResponse,
    WorkflowCreate, WorkflowResponse, WorkflowUpdate, WorkflowRunResponse,
)
from .security import (
    encrypt_secrets, decrypt_secrets, mask_secrets,
    verify_client_cert, ENCRYPTION_KEY, cipher_suite, oauth2_scheme,
    mask_pii, verify_node_secret, validate_path_within
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
from .db import init_db, get_db, Job, Token, Config, User, Node, NodeStats, AsyncSession, Signature, ScheduledJob, Ping, AsyncSessionLocal, RevokedCert, ExecutionRecord, Signal, Alert, JobTemplate, ApprovedIngredient, IngredientDependency, ApprovedOS, WorkflowStepRun
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, verify_token
from .services.job_service import JobService
from .services.signature_service import SignatureService
from .services.scheduler_service import scheduler_service
from .services.pki_service import pki_service
from .services.alert_service import AlertService
from .services.licence_service import load_licence, check_and_record_boot, reload_licence, check_licence_expiry, LicenceState, LicenceStatus, LicenceError
from .services.workflow_service import WorkflowService

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()

    # Phase 124: Validate NODE_EXECUTION_MODE at startup
    import sys as _sys
    node_execution_mode = os.getenv("NODE_EXECUTION_MODE", "auto").lower()
    if node_execution_mode == "direct":
        logger.error("NODE_EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto'.")
        _sys.exit(1)

    # SQLite dev-mode warning — surfaces missing SKIP LOCKED before the first pull
    from .db import IS_POSTGRES as _IS_POSTGRES
    if not _IS_POSTGRES:
        print(
            "WARNING: SQLite detected — SKIP LOCKED not active. Use Postgres for production.",
            file=_sys.stderr,
        )

    # Load licence first (check_and_record_boot now needs it)
    licence_state = load_licence()
    app.state.licence_state = licence_state

    # Clock rollback detection — strict for EE, warning-only for CE
    _rollback_ok = check_and_record_boot(licence_state.status)
    if not _rollback_ok:
        logger.warning("Clock rollback detected — check system time")

    # Load EE plugins only if licence is valid or in grace period
    from .ee import load_ee_plugins, EEContext, _mount_ce_stubs
    from .db import engine
    if licence_state.is_ee_active:
        app.state.ee = await load_ee_plugins(app, engine)
    else:
        logger.info(f"Licence state={licence_state.status} — loading CE stubs")
        ctx = EEContext()
        _mount_ce_stubs(app)
        app.state.ee = ctx
    # Pre-warm permission cache — DEBT-03
    # Avoids per-request DB queries in require_permission() after startup.
    try:
        async with AsyncSessionLocal() as _db:
            from sqlalchemy import text as _text
            _result = await _db.execute(_text("SELECT role, permission FROM role_permissions"))
            from .deps import _perm_cache
            for _role, _perm in _result.all():
                _perm_cache.setdefault(_role, set()).add(_perm)
            logger.info(f"Permission cache pre-warmed: {len(_perm_cache)} roles")
    except Exception as _e:
        logger.debug(f"CE mode or no role_permissions table — cache pre-warm skipped: {_e}")

    # SEC-02: Backfill HMAC tags for existing jobs without them
    try:
        from .security import compute_signature_hmac, ENCRYPTION_KEY as _ENC_KEY
        import json as _json
        async with AsyncSessionLocal() as _db:
            _result = await _db.execute(
                select(Job).where(Job.signature_hmac == None).limit(1000)  # noqa: E711
            )
            _jobs = _result.scalars().all()
            _backfilled = 0
            for _job in _jobs:
                try:
                    _pl = _json.loads(_job.payload) if _job.payload else {}
                    _sp = _pl.get("signature_payload")
                    _si = _pl.get("signature_id")
                    if _sp and _si:
                        _job.signature_hmac = compute_signature_hmac(_ENC_KEY, _sp, _si, _job.guid)
                        _backfilled += 1
                except Exception:
                    continue
            if _backfilled:
                await _db.commit()
        logger.info(f"SEC-02: Backfilled HMAC for {_backfilled} existing jobs")
    except Exception as _e:
        logger.debug(f"SEC-02 backfill skipped: {_e}")

    # Bootstrap Admin
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
            if not admin_password:
                # Auto-generate a random password — user must change it on first login
                import secrets as _secrets
                admin_password = _secrets.token_urlsafe(16)
                force_change = True
                logger.warning("Admin bootstrapped with auto-generated password: %s", admin_password)
                logger.warning("You will be prompted to change it on first login.")
            else:
                skip_force = os.getenv("ADMIN_SKIP_FORCE_CHANGE", "").strip().lower() == "true"
                force_change = not skip_force
                if skip_force:
                    logger.info("ADMIN_SKIP_FORCE_CHANGE is set — skipping forced password change")
                logger.info("Bootstrapped Admin User with provided password")
            admin_user = User(
                username="admin",
                password_hash=get_password_hash(admin_password),
                must_change_password=force_change,
            )
            db.add(admin_user)
            await db.commit()

    # Seed starter templates (Phase 114 - for EE only)
    try:
        from .services.foundry_service import FoundryService
        async with AsyncSessionLocal() as db:
            await FoundryService.seed_starter_templates(db)
    except Exception as _e:
        logger.debug(f"Starter template seeding skipped: {_e}")

    # Guard against silent APScheduler v4 install (v4 is a complete rewrite)
    import importlib.metadata as _importlib_metadata
    from packaging.version import Version as _Version
    _aps_ver = _importlib_metadata.version("apscheduler")
    if _Version(_aps_ver) >= _Version("4.0"):
        raise RuntimeError("APScheduler v4 detected — pin to >=3.10,<4.0")

    # Start Scheduler
    scheduler_service.start()
    await scheduler_service.sync_scheduler()
    await scheduler_service.sync_workflow_crons()  # NEW: Phase 149

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

    # Background licence expiry checker (Phase 116, Task 5)
    async def check_licence_expiry_bg():
        """Check licence expiry status every 60 seconds and update app.state.licence_state on transitions."""
        while True:
            try:
                await asyncio.sleep(60)
                if not app.state.licence_state:
                    continue
                new_status = check_licence_expiry(app.state.licence_state)
                if new_status != app.state.licence_state.status:
                    old_status = app.state.licence_state.status
                    app.state.licence_state.status = new_status
                    logger.warning(
                        f"Licence status transitioned: {old_status.value} → {new_status.value}"
                    )
                    # Broadcast licence status change to all connected WebSocket clients
                    await ws_manager.broadcast("licence_status_changed", {
                        "old_status": str(old_status.value),
                        "new_status": str(new_status.value),
                        "reason": "background_expiry_check",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.error(f"Licence expiry check failed: {e}")

    asyncio.create_task(check_licence_expiry_bg())

    # OCI cache warm-up (EE only) — pre-pull base images through cache on startup
    async def warm_oci_cache():
        """
        Pre-warm OCI cache by pulling all approved OS base images through cache proxies.
        Runs only if OCI cache URLs are configured (EE with mirrors profile).
        Logs per-image success/failure but doesn't block startup.
        """
        import asyncio as _asyncio
        import subprocess as _subprocess
        from .services.mirror_service import MirrorService as _MirrorService

        # Check if OCI caching is enabled
        oci_cache_hub_url = os.getenv("OCI_CACHE_HUB_URL", "").strip()
        oci_cache_ghcr_url = os.getenv("OCI_CACHE_GHCR_URL", "").strip()

        if not (oci_cache_hub_url or oci_cache_ghcr_url):
            logger.debug("OCI cache warm-up: disabled (no OCI_CACHE_HUB_URL or OCI_CACHE_GHCR_URL)")
            return

        # Small delay to allow DB to be fully ready
        await _asyncio.sleep(2)

        try:
            async with AsyncSessionLocal() as db:
                # Query all active approved OS records
                result = await db.execute(select(ApprovedOS).where(ApprovedOS.is_active == True))  # noqa: E712
                approved_os_list = result.scalars().all()

                if not approved_os_list:
                    logger.info("OCI cache warm-up: no approved OS records found")
                    return

                logger.info(f"OCI cache warm-up: starting for {len(approved_os_list)} approved OS entries")

                for os_record in approved_os_list:
                    try:
                        base_image = os_record.image_uri

                        # Rewrite image reference for OCI cache prefix
                        rewritten_image = _MirrorService.get_oci_mirror_prefix(base_image)

                        # Pull via cache using docker pull (non-blocking via asyncio.to_thread)
                        def _pull_image(image_ref: str) -> str:
                            """Synchronously pull an image via docker CLI."""
                            result = _subprocess.run(
                                ["docker", "pull", image_ref],
                                capture_output=True,
                                text=True,
                                timeout=300  # 5 minute timeout per image
                            )
                            return result.returncode, result.stdout, result.stderr

                        try:
                            returncode, stdout, stderr = await _asyncio.to_thread(_pull_image, rewritten_image)
                            if returncode == 0:
                                logger.info(f"OCI cache warm-up: ✓ {base_image} → {rewritten_image}")
                            else:
                                logger.warning(f"OCI cache warm-up: ✗ {base_image} (exit={returncode}): {stderr[:200]}")
                        except _subprocess.TimeoutExpired:
                            logger.warning(f"OCI cache warm-up: ✗ {base_image} (timeout after 300s)")
                        except Exception as inner_e:
                            logger.warning(f"OCI cache warm-up: ✗ {base_image} ({inner_e})")

                    except Exception as image_e:
                        logger.warning(f"OCI cache warm-up: error processing OS record (id={os_record.id}): {image_e}")
                        continue

                logger.info("OCI cache warm-up: complete")

        except Exception as e:
            logger.error(f"OCI cache warm-up failed: {e}")

    asyncio.create_task(warm_oci_cache())

    # Initialize mirrors_available flag and start health check background task
    app.state.mirrors_available = True  # Assume available at startup; first check will confirm

    async def check_mirrors_health():
        """
        Periodically check mirror service health (PyPI, APT, npm, NuGet, OCI caches).
        Updates app.state.mirrors_available based on reachability.
        Runs every ~60 seconds (configurable via MIRROR_HEALTH_CHECK_INTERVAL env var).
        """
        import httpx
        check_interval = int(os.getenv("MIRROR_HEALTH_CHECK_INTERVAL", "60"))
        pypi_mirror_url = os.getenv("PYPI_MIRROR_URL", "http://pypi:8080")
        apt_mirror_url = os.getenv("APT_MIRROR_URL", "http://mirror:80/apt/")
        npm_mirror_url = os.getenv("NPM_MIRROR_URL", "http://verdaccio:4873")
        nuget_mirror_url = os.getenv("NUGET_MIRROR_URL", "http://bagetter:5555/v3/index.json")
        oci_cache_hub_url = os.getenv("OCI_CACHE_HUB_URL", "http://oci-cache:5001")
        oci_cache_ghcr_url = os.getenv("OCI_CACHE_GHCR_URL", "http://oci-cache-ghcr:5002")

        retry_delay = 5  # Initial retry delay for exponential backoff

        while True:
            try:
                # Health check mirrors with 10s timeout
                async with httpx.AsyncClient(timeout=10.0) as client:
                    try:
                        pypi_response = await client.get(pypi_mirror_url)
                        pypi_ok = 200 <= pypi_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: PyPI mirror check failed: {e}")
                        pypi_ok = False

                    try:
                        apt_response = await client.get(apt_mirror_url)
                        apt_ok = 200 <= apt_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: APT mirror check failed: {e}")
                        apt_ok = False

                    try:
                        npm_response = await client.get(npm_mirror_url)
                        npm_ok = 200 <= npm_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: npm mirror check failed: {e}")
                        npm_ok = False

                    try:
                        nuget_response = await client.get(nuget_mirror_url)
                        nuget_ok = 200 <= nuget_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: NuGet mirror check failed: {e}")
                        nuget_ok = False

                    try:
                        oci_hub_response = await client.get(f"{oci_cache_hub_url}/v2/")
                        oci_hub_ok = 200 <= oci_hub_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: OCI Hub cache check failed: {e}")
                        oci_hub_ok = False

                    try:
                        oci_ghcr_response = await client.get(f"{oci_cache_ghcr_url}/v2/")
                        oci_ghcr_ok = 200 <= oci_ghcr_response.status_code < 400
                    except Exception as e:
                        logger.warning(f"Mirror health: OCI GHCR cache check failed: {e}")
                        oci_ghcr_ok = False

                # All mirrors must be reachable
                mirrors_available = pypi_ok and apt_ok and npm_ok and nuget_ok and oci_hub_ok and oci_ghcr_ok

                if mirrors_available:
                    if not app.state.mirrors_available:
                        logger.info("Mirror health: All mirrors became available")
                    app.state.mirrors_available = True
                    retry_delay = 5  # Reset backoff on success
                else:
                    logger.warning(f"Mirror health: Unreachable (PyPI={pypi_ok}, APT={apt_ok}, npm={npm_ok}, NuGet={nuget_ok}, OCI-Hub={oci_hub_ok}, OCI-GHCR={oci_ghcr_ok})")
                    app.state.mirrors_available = False
                    # Exponential backoff: start at 5s, cap at 60s
                    retry_delay = min(retry_delay * 2, check_interval)
                    await asyncio.sleep(retry_delay)
                    continue

                # Sleep for the configured check interval
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Mirror health check error: {e}")
                app.state.mirrors_available = False
                await asyncio.sleep(check_interval)

    asyncio.create_task(check_mirrors_health())

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

# --- LICENCE EXPIRY GUARD MIDDLEWARE (Phase 116, Task 6) ---
class LicenceExpiryGuard(BaseHTTPMiddleware):
    """
    Guard middleware that blocks EE-only endpoints with 402 Payment Required
    when the licence has expired (EXPIRED status, not VALID or GRACE).

    EE router prefixes: /api/foundry, /api/audit, /api/webhooks, /api/triggers,
    /api/auth-ext, /api/smelter, /api/executions
    """

    # EE-only route prefixes (lowercase for matching)
    EE_PREFIXES = (
        "/api/foundry",
        "/api/audit",
        "/api/webhooks",
        "/api/triggers",
        "/api/auth-ext",
        "/api/smelter",
        "/api/executions",
        "/api/admin/bundles",
    )

    async def dispatch(self, request: Request, call_next):
        # Check if this is an EE route
        path_lower = request.url.path.lower()
        is_ee_route = any(path_lower.startswith(prefix) for prefix in self.EE_PREFIXES)

        if is_ee_route:
            # Check licence state from app state
            current_app = request.app if hasattr(request, 'app') else app
            licence_state = getattr(current_app.state, 'licence_state', None)
            if licence_state and licence_state.status == LicenceStatus.EXPIRED:
                return Response(
                    content=json.dumps({
                        "detail": "Licence expired — EE features unavailable (grace period ended)"
                    }),
                    status_code=402,
                    media_type="application/json"
                )

        return await call_next(request)

app.add_middleware(LicenceExpiryGuard)

# --- AUTH HELPERS (moved to deps.py to avoid circular imports with EE routers) ---
from .deps import (
    get_current_user, get_current_user_optional, require_auth,
    require_permission,
    audit,
)

# --- ALERTS ---

@app.get("/api/alerts", response_model=List[AlertResponse], tags=["Alerts & Webhooks"])
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    unacknowledged_only: bool = False,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """List system alerts with optional filtering."""
    return await AlertService.list_alerts(db, skip, limit, unacknowledged_only)

@app.post(
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
    await db.commit()
    return {"status": "acknowledged", "resource_type": "alert", "resource_id": alert_id}

# Serve Installer Scripts
@app.get(
    "/api/node/compose",
    response_class=Response,
    tags=["System"],
    summary="Generate Docker Compose file for node deployment",
    description="Dynamically generate docker-compose.yaml for node with enrollment token and configuration"
)
@app.get(
    "/api/installer/compose",
    response_class=Response,
    tags=["System"],
    summary="Generate Docker Compose file for node installation",
    description="Alias for /api/node/compose - generates docker-compose.yaml for node deployment"
)
async def get_node_compose(token: str, mounts: Optional[str] = None, tags: Optional[str] = None, execution_mode: Optional[str] = None):
    """Dynamic Compose File generator for Nodes."""
    effective_tags = tags if tags else "general,linux,arm64"
    # Allow caller or server default to set EXECUTION_MODE for the node container.
    # Defaults to "auto" (Docker/Podman detection).
    effective_execution_mode = execution_mode or os.getenv("NODE_EXECUTION_MODE", "auto")

    # Phase 124: Reject direct execution mode
    if effective_execution_mode == "direct":
        raise HTTPException(
            status_code=400,
            detail="EXECUTION_MODE=direct is not supported. Use 'docker', 'podman', or 'auto' instead. "
                   "For Docker-in-Docker, mount the host Docker socket and use EXECUTION_MODE=docker or EXECUTION_MODE=auto."
        )

    compose_content = f"""
version: '3.8'
services:
  puppet:
    image: {os.getenv("NODE_IMAGE", "ghcr.io/axiom-laboratories/axiom-node:latest")}
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

@app.get(
    "/verification-key",
    response_class=Response,
    tags=["System"],
    summary="Get Ed25519 verification public key",
    description="Returns the PEM-encoded Ed25519 public key used to verify signed job scripts"
)
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

@app.get(
    "/installer",
    response_class=Response,
    tags=["System"],
    summary="Get PowerShell installer script",
    description="Returns the universal PowerShell script for node installation"
)
async def get_installer_ps1():
    """Serves the Universal PowerShell Installer (One-Liner)."""
    file_path = "installer/install_universal.ps1"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get(
    "/installer.sh",
    response_class=Response,
    tags=["System"],
    summary="Get Bash installer script",
    description="Returns the universal Bash script for node installation"
)
async def get_installer_sh():
    """Serves the Universal Bash Installer."""
    file_path = "installer/install_universal.sh"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get(
    "/system/root-ca",
    response_class=Response,
    tags=["System"],
    summary="Download Root CA certificate",
    description="Returns the PEM-encoded internal Root CA certificate for mTLS node enrollment"
)
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

@app.get(
    "/system/root-ca-installer",
    response_class=Response,
    tags=["System"],
    summary="Get Bash script to install Root CA",
    description="Returns a self-contained bash script that installs the MoP Root CA into system trust stores (Debian, RHEL, macOS) and browser NSS databases"
)
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

@app.get(
    "/system/root-ca-installer.ps1",
    response_class=Response,
    tags=["System"],
    summary="Get PowerShell script to install Root CA",
    description="Returns a PowerShell script that installs the MoP Root CA into the Windows Root Certificate Store"
)
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

@app.post("/auth/device", response_model=DeviceCodeResponse, tags=["Authentication"])
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

@app.post("/auth/device/token", response_model=TokenResponse, tags=["Authentication"])
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
        data={"sub": user.username, "tv": user.token_version, "type": "device_flow"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Consume code — one-time use
    _device_codes.pop(req.device_code, None)
    _user_code_index.pop(entry["user_code"], None)

    audit(db, user, "device_flow:token_issued", None, {"username": user.username})
    await db.commit()
    return TokenResponse(access_token=token, token_type="bearer", must_change_password=user.must_change_password)

@app.get("/auth/device/approve", response_class=HTMLResponse, tags=["Authentication"])
async def device_approve_page(user_code: str = ""):
    """Serve the device authorization approval page (inline HTML, no build step)."""
    # SEC-01: escape user_code before inserting into HTML to prevent XSS
    escaped_code = _html.escape(user_code or "")
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
    <div class="code" id="display-code">{escaped_code or "(no code provided)"}</div>
    <form id="approve-form" method="POST" action="/auth/device/approve">
      <input type="hidden" name="user_code" value="{escaped_code}">
      <input type="hidden" name="token" id="token-field" value="">
      <button type="submit" class="btn btn-approve">Approve</button>
    </form>
    <form id="deny-form" method="POST" action="/auth/device/deny">
      <input type="hidden" name="user_code" value="{escaped_code}">
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
        data={"sub": user.username, "tv": user.token_version, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "must_change_password": user.must_change_password}

@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.username, username=current_user.username, role=current_user.role, created_at=current_user.created_at)

@app.patch("/auth/me", response_model=TokenResponse, tags=["Authentication"])
async def update_self(req: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Allow a logged-in user to change their own password.
    Returns a fresh access token so the current session continues uninterrupted."""
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    # Skip current_password check only when user is in force-change mode (they just authenticated)
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
        data={"sub": current_user.username, "tv": current_user.token_version, "role": current_user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(access_token=new_token, token_type="bearer", must_change_password=False)

# --- Core Endpoints ---

@app.get(
    "/",
    response_model=dict,
    tags=["System"],
    summary="Health check endpoint",
    description="Simple health check that returns service status and mirror availability"
)
async def health_check():
    mirrors_available = getattr(app.state, "mirrors_available", True)
    return {
        "status": "healthy",
        "service": "Agent Service v0.7",
        "mirrors_available": mirrors_available
    }

@app.get("/system/health", response_model=SystemHealthResponse, tags=["System"])
async def system_health():
    mirrors_available = getattr(app.state, "mirrors_available", True)
    return {
        "status": "healthy",
        "mirrors_available": mirrors_available
    }


@app.get("/api/health/scheduling", response_model=SchedulingHealthResponse, tags=["Health"])
async def get_scheduling_health_endpoint(
    window: str = "24h",
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    if window not in ("24h", "7d", "30d"):
        raise HTTPException(status_code=422, detail="window must be 24h, 7d, or 30d")
    data = await scheduler_service.get_scheduling_health(window, db)
    return SchedulingHealthResponse(**data, window=window)


@app.get("/health/scale", response_model=ScaleHealthResponse, tags=["Health"])
async def get_scale_health_endpoint(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return live pool and scheduler health metrics."""
    from .db import engine, IS_POSTGRES
    from .services.scheduler_service import scheduler_service
    from sqlalchemy import func, select as sa_select

    # APScheduler job count
    apscheduler_jobs = len(scheduler_service.scheduler.get_jobs())

    # Pending job depth
    result = await db.execute(
        sa_select(func.count(Job.guid)).where(Job.status == "PENDING")
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


@app.get("/api/features", response_model=FeaturesResponse, tags=["System"])
async def get_features(request: Request):
    ctx = getattr(request.app.state, "ee", None)
    if ctx is None:
        return {"audit": False, "foundry": False, "webhooks": False,
                "triggers": False, "rbac": False, "resource_limits": False,
                "service_principals": False, "api_keys": False,
                "executions": False}
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

@app.get("/api/licence", response_model=LicenceStatusResponse, tags=["System"])
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


@app.get(
    "/jobs",
    response_model=PaginatedResponse[JobResponse],
    tags=["Jobs"],
    summary="List all jobs",
    description="Retrieve a paginated list of all jobs with optional filtering by status, runtime, tags, and other criteria."
)
async def list_jobs(
    cursor: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None,
    runtime: Optional[str] = None,
    task_type: Optional[str] = None,
    node_id: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = await JobService.list_jobs(
        db, limit=limit, cursor=cursor,
        status=status, runtime=runtime, task_type=task_type,
        node_id=node_id, tags=tags_list,
        created_by=created_by, date_from=date_from, date_to=date_to, search=search,
    )
    return result  # {items, total, next_cursor}

@app.get(
    "/jobs/count",
    response_model=JobCountResponse,
    tags=["Jobs"],
    summary="Get job count",
    description="Get total count of jobs, optionally filtered by status."
)
async def count_jobs(status: Optional[str] = None, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    query = select(sqlfunc.count()).select_from(Job).where(Job.task_type != 'system_heartbeat')
    if status and status.upper() != 'ALL':
        query = query.where(Job.status == status.upper())
    result = await db.execute(query)
    return {"total": result.scalar()}

@app.get(
    "/jobs/export",
    response_class=StreamingResponse,
    tags=["Jobs"],
    summary="Export jobs as CSV",
    description="Export filtered job records as a CSV file with streaming response"
)
async def export_jobs(
    status: Optional[str] = None,
    runtime: Optional[str] = None,
    task_type: Optional[str] = None,
    node_id: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    EXPORT_LIMIT = 10_000
    jobs = await JobService.list_jobs_for_export(
        db, limit=EXPORT_LIMIT,
        status=status, runtime=runtime, task_type=task_type,
        node_id=node_id, tags=tags_list,
        created_by=created_by, date_from=date_from, date_to=date_to, search=search,
    )

    HEADERS = ["guid", "name", "status", "task_type", "display_type", "runtime",
               "node_id", "created_at", "started_at", "completed_at", "duration_seconds", "target_tags"]

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(HEADERS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()
        for job in jobs:
            writer.writerow([
                job.get("guid", ""), job.get("name", ""), job.get("status", ""),
                job.get("task_type", ""), job.get("display_type", ""), job.get("runtime", ""),
                job.get("node_id", ""), job.get("created_at", ""), job.get("started_at", ""),
                job.get("completed_at", ""), job.get("duration_seconds", ""),
                ",".join(job.get("target_tags") or []),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=jobs-export.csv",
            "X-Content-Type-Options": "nosniff",
        },
    )

@app.get(
    "/api/jobs/stats",
    response_model=JobStatsResponse,
    tags=["Jobs"],
    summary="Get job statistics",
    description="Retrieve aggregated job statistics including counts by status and success rate."
)
async def get_job_stats(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
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
    current_user: User = Depends(require_auth),
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

    # 1b. Reject REVOKED definitions — cannot dispatch a job from a revoked definition
    if s_job.status == "REVOKED":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "job_definition_revoked",
                "id": s_job.id,
                "message": "Cannot dispatch a REVOKED job definition.",
            },
        )

    # 2. Resolve env_tag: dispatch request overrides definition's env_tag; fall back to definition
    effective_env_tag = req.env_tag if req.env_tag is not None else s_job.env_tag

    # 3. Build JobCreate
    runtime = getattr(s_job, 'runtime', None) or 'python'
    payload_dict = {
        "script_content": s_job.script_content,
        "signature": s_job.signature_payload,
        "secrets": {},
        "runtime": runtime,
    }
    job_create = JobCreate(
        task_type="script",
        runtime=runtime,
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
    current_user: User = Depends(require_auth),
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
async def create_job(job_req: JobCreate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    try:
        # SRCH-03: stamp submitter username so Jobs view can filter by creator
        job_req = job_req.model_copy(update={"created_by": current_user.username})

        # SEC-JOB: If the payload carries a user signature, verify it server-side
        # against the registered public key, then countersign with the server's own
        # Ed25519 signing key so the node can verify using its cached verification.key.
        payload_dict = dict(job_req.payload)
        user_sig = payload_dict.get("signature")
        sig_id = payload_dict.get("signature_id")
        script_content = payload_dict.get("script_content")

        # WIN-05: Normalize CRLF → LF before signature verification and countersigning.
        # This matches the normalization in node.py (line 585) so both sides agree on bytes.
        if script_content:
            script_content = script_content.replace('\r\n', '\n').replace('\r', '\n')
            payload_dict["script_content"] = script_content

        if user_sig and sig_id and script_content:
            # 1. Verify user's signature against the registered public key
            sig_result = await db.execute(select(Signature).where(Signature.id == sig_id))
            sig_rec = sig_result.scalar_one_or_none()
            if not sig_rec:
                raise HTTPException(status_code=422, detail=f"Signature key ID '{sig_id}' not found in registry")
            try:
                from .services.signature_service import SignatureService as _SS
                _SS.verify_payload_signature(sig_rec.public_key, user_sig, script_content)
            except Exception as _ve:
                raise HTTPException(status_code=422, detail=f"Signature verification failed: {_ve}")

        # 2. Countersign script with the server's Ed25519 signing key so the
        #    node can verify using its fetched verification.key (which is the
        #    server's public counterpart). This is mandatory for all job scripts.
        if script_content:
            try:
                from .services.signature_service import SignatureService
                server_sig = SignatureService.countersign_for_node(script_content)
                # Set server countersignature so node verifies correctly
                payload_dict["signature"] = server_sig
                job_req = job_req.model_copy(update={"payload": payload_dict})
            except Exception as e:
                raise HTTPException(status_code=500, detail="Server signing key unavailable — contact admin")

        result = await JobService.create_job(job_req, db)
        await ws_manager.broadcast("job:created", {"guid": result["guid"], "status": "PENDING", "task_type": job_req.task_type})
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{guid}", response_model=JobResponse, tags=["Jobs"])
async def get_job(guid: str, current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    """Retrieve a single job by its GUID."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload or '{}')
    result_val = job.result if isinstance(job.result, dict) else json.loads(job.result or 'null') if job.result else None
    target_tags = job.target_tags if isinstance(job.target_tags, list) else json.loads(job.target_tags or 'null') if job.target_tags else None

    # Calculate duration_seconds from started_at and completed_at
    duration = None
    if job.started_at and job.completed_at:
        duration = int((job.completed_at - job.started_at).total_seconds())

    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=result_val,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=duration,
        target_tags=target_tags,
        task_type=job.task_type,
        display_type=getattr(job, 'display_type', None),
        name=getattr(job, 'name', None),
        created_by=getattr(job, 'created_by', None),
        created_at=job.created_at,
        runtime=getattr(job, 'runtime', None),
        originating_guid=getattr(job, 'originating_guid', None),
    )

@app.patch(
    "/jobs/{guid}/cancel",
    response_model=ActionResponse,
    tags=["Jobs"],
    summary="Cancel a job",
    description="Cancel a PENDING or ASSIGNED job, transitioning it to CANCELLED status."
)
async def cancel_job(guid: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
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
    return {"status": "cancelled", "resource_type": "job", "resource_id": guid}

@app.get(
    "/jobs/{guid}/dispatch-diagnosis",
    response_model=DispatchDiagnosisResponse,
    tags=["Jobs"],
    summary="Get dispatch diagnosis",
    description="Get diagnostic information explaining why a PENDING job has not yet been dispatched to a node."
)
async def get_dispatch_diagnosis(guid: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Returns structured explanation for why a PENDING job has not yet dispatched."""
    result = await JobService.get_dispatch_diagnosis(guid, db)
    if result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@app.post(
    "/jobs/dispatch-diagnosis/bulk",
    response_model=BulkDispatchDiagnosisResponse,
    tags=["Jobs"],
    summary="Get bulk dispatch diagnosis",
    description="Get dispatch diagnostic information for multiple jobs in one request."
)
async def bulk_dispatch_diagnosis(
    req: BulkDiagnosisRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Returns dispatch diagnosis for multiple jobs in one call (Phase 88 — DIAG-01)."""
    results = {}
    for guid in req.guids:
        results[guid] = await JobService.get_dispatch_diagnosis(guid, db)
    return {"results": results}


@app.post(
    "/jobs/{guid}/retry",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Retry a job",
    description="Reset a FAILED or DEAD_LETTER job back to PENDING status to retry execution."
)
async def retry_job(
    guid: str,
    current_user: User = Depends(require_auth),
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
    # Construct JobResponse from updated job
    payload = job.payload if isinstance(job.payload, dict) else json.loads(job.payload or '{}')
    result_val = job.result if isinstance(job.result, dict) else json.loads(job.result or 'null') if job.result else None
    target_tags = job.target_tags if isinstance(job.target_tags, list) else json.loads(job.target_tags or 'null') if job.target_tags else None
    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=result_val,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=None,
        target_tags=target_tags,
        task_type=job.task_type,
        display_type=getattr(job, 'display_type', None),
        name=getattr(job, 'name', None),
        created_by=getattr(job, 'created_by', None),
        created_at=job.created_at,
        runtime=getattr(job, 'runtime', None),
        originating_guid=getattr(job, 'originating_guid', None),
    )

# --- Resubmit / Bulk job operations (Phase 51) ---

CANCELLABLE_STATES = {"PENDING", "ASSIGNED"}
RESUBMITTABLE_STATES = {"FAILED", "DEAD_LETTER"}
TERMINAL_STATES = {"COMPLETED", "FAILED", "DEAD_LETTER", "CANCELLED", "SECURITY_REJECTED"}


def _job_to_response(job: Job) -> JobResponse:
    """Build a JobResponse from a Job ORM object."""
    payload = json.loads(job.payload) if isinstance(job.payload, str) else job.payload
    duration = None
    if job.started_at:
        end = job.completed_at or datetime.utcnow()
        duration = (end - job.started_at).total_seconds()
    return JobResponse(
        guid=job.guid,
        status=job.status,
        payload=payload,
        result=json.loads(job.result) if job.result else None,
        node_id=job.node_id,
        started_at=job.started_at,
        duration_seconds=duration,
        target_tags=json.loads(job.target_tags) if job.target_tags else None,
        depends_on=json.loads(job.depends_on) if job.depends_on else None,
        task_type=job.task_type,
        name=job.name,
        created_by=job.created_by,
        created_at=job.created_at,
        runtime=job.runtime,
        originating_guid=job.originating_guid,
    )


@app.post("/jobs/bulk-cancel", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_cancel_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel PENDING/ASSIGNED jobs in bulk; skips terminal-state jobs and reports them."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in CANCELLABLE_STATES:
            job.status = "CANCELLED"
            job.completed_at = datetime.utcnow()
            audit(db, current_user, "job:cancel", job.guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@app.post("/jobs/bulk-resubmit", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_resubmit_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Resubmit FAILED/DEAD_LETTER jobs in bulk; creates a new PENDING job for each."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in RESUBMITTABLE_STATES:
            new_guid = str(uuid.uuid4())
            new_job = Job(
                guid=new_guid,
                task_type=job.task_type,
                payload=job.payload,
                status="PENDING",
                target_tags=job.target_tags,
                capability_requirements=job.capability_requirements,
                max_retries=job.max_retries,
                backoff_multiplier=job.backoff_multiplier,
                timeout_minutes=job.timeout_minutes,
                runtime=job.runtime,
                name=job.name,
                created_by=current_user.username,
                signature_hmac=job.signature_hmac,
                originating_guid=job.guid,
            )
            db.add(new_job)
            audit(db, current_user, "job:resubmit", new_guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@app.delete("/jobs/bulk", response_model=BulkActionResponse, tags=["Jobs"])
async def bulk_delete_jobs(
    req: BulkJobActionRequest,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete terminal-state jobs in bulk; skips non-terminal jobs and reports them."""
    result = await db.execute(select(Job).where(Job.guid.in_(req.guids)))
    jobs = result.scalars().all()
    processed, skipped_guids = 0, []
    for job in jobs:
        if job.status in TERMINAL_STATES:
            await db.delete(job)
            audit(db, current_user, "job:delete", job.guid)
            processed += 1
        else:
            skipped_guids.append(job.guid)
    await db.commit()
    return BulkActionResponse(processed=processed, skipped=len(skipped_guids), skipped_guids=skipped_guids)


@app.post("/jobs/{guid}/resubmit", response_model=JobResponse, tags=["Jobs"])
async def resubmit_job(
    guid: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new PENDING job from a FAILED/DEAD_LETTER job, with originating_guid set."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in RESUBMITTABLE_STATES:
        raise HTTPException(status_code=409, detail="Only FAILED or DEAD_LETTER jobs can be resubmitted")
    new_guid = str(uuid.uuid4())
    new_job = Job(
        guid=new_guid,
        task_type=job.task_type,
        payload=job.payload,
        status="PENDING",
        target_tags=job.target_tags,
        capability_requirements=job.capability_requirements,
        max_retries=job.max_retries,
        backoff_multiplier=job.backoff_multiplier,
        timeout_minutes=job.timeout_minutes,
        runtime=job.runtime,
        name=job.name,
        created_by=current_user.username,
        signature_hmac=job.signature_hmac,
        originating_guid=guid,
    )
    db.add(new_job)
    audit(db, current_user, "job:resubmit", new_guid)
    await db.commit()
    await db.refresh(new_job)
    await ws_manager.broadcast("job:created", {"guid": new_guid, "status": "PENDING"})
    return _job_to_response(new_job)


@app.post("/work/pull", response_model=PollResponse, tags=["Node Agent"])
async def pull_work(request: Request, node_id: str = Depends(verify_node_secret), db: AsyncSession = Depends(get_db)):
    # LIC-04: DEGRADED_CE — return empty work, nodes stay enrolled and heartbeating
    _ls = getattr(request.app.state, "licence_state", None)
    if _ls and _ls.status == LicenceStatus.EXPIRED:
        from .models import WorkConfig
        return PollResponse(job=None, config=WorkConfig())

    node_ip = request.client.host
    r = await db.execute(select(Node).where(Node.node_id == node_id))
    n = r.scalar_one_or_none()
    if n and n.status == "REVOKED":
        raise HTTPException(status_code=403, detail="Node is revoked")
    return await JobService.pull_work(node_id, node_ip, db)

@app.post(
    "/heartbeat",
    response_model=dict,
    tags=["Node Agent"],
    summary="Receive node heartbeat",
    description="Process heartbeat from node agent with health status, resource stats, and system metrics"
)
async def receive_heartbeat(req: Request, hb: HeartbeatPayload, node_id: str = Depends(verify_node_secret), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    result = await JobService.receive_heartbeat(node_id, node_ip, hb, db)
    await ws_manager.broadcast("node:heartbeat", {"node_id": node_id, "status": "ONLINE", "stats": hb.stats})
    return result

@app.post(
    "/work/{guid}/result",
    response_model=dict,
    tags=["Node Agent"],
    summary="Report job execution result",
    description="Node agent reports job completion status, output, and execution metrics"
)
async def report_result(guid: str, report: ResultReport, req: Request, node_id: str = Depends(verify_node_secret), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    if report.result:
        report.result = mask_pii(report.result)

    updated = await JobService.report_result(guid, report, node_ip, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")

    # Phase 147: If job is linked to a workflow step, advance the workflow
    job = await db.get(Job, guid)
    if job and job.workflow_step_run_id:
        # Extract run_id from workflow_step_run_id by querying the step run
        step_run = await db.get(WorkflowStepRun, job.workflow_step_run_id)
        if step_run:
            workflow_service = WorkflowService()
            # NEW: Store result_json for IF gate evaluation
            if report.result:
                await workflow_service.store_step_result(step_run.id, report.result, db)
            await workflow_service.advance_workflow(step_run.workflow_run_id, db)

    await ws_manager.broadcast("job:updated", {"guid": guid, "status": updated.get("status", "COMPLETED")})
    return updated

@app.get("/nodes", tags=["Nodes"], response_model=PaginatedResponse[NodeResponse], summary="List all nodes", description="Retrieve paginated list of nodes with online/offline status and capability info")
async def list_nodes(
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Step 1: total count
    total_result = await db.execute(select(func.count()).select_from(Node))
    total = total_result.scalar() or 0

    # Step 2: paginated node list (paginate BEFORE stats batch query)
    result = await db.execute(
        select(Node).order_by(Node.hostname)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    nodes = result.scalars().all()

    # Step 3: batch stats history — scoped to this page's node_ids only
    history_map: dict = defaultdict(list)
    if nodes:
        page_node_ids = [n.node_id for n in nodes]
        hist_result = await db.execute(
            select(NodeStats)
            .where(NodeStats.node_id.in_(page_node_ids))
            .order_by(desc(NodeStats.recorded_at))
        )
        for stat in hist_result.scalars().all():
            bucket = history_map[stat.node_id]
            if len(bucket) < 20:
                bucket.append({"t": stat.recorded_at.isoformat(), "cpu": stat.cpu, "ram": stat.ram})
        # Reverse each bucket so oldest→newest (chronological for charts)
        for k in history_map:
            history_map[k].reverse()

    # Step 4: build resp list
    resp = []
    for n in nodes:
        if n.status in ("REVOKED", "TAMPERED", "DRAINING"):
            node_status = n.status
        else:
            is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
            node_status = "OFFLINE" if is_offline else "ONLINE"

        stats = json.loads(n.stats) if n.stats else None
        reported_tags = json.loads(n.tags) if n.tags else []
        op_tags = json.loads(n.operator_tags) if n.operator_tags else None
        effective_tags = op_tags if op_tags is not None else reported_tags

        resp.append({
            "node_id": n.node_id,
            "hostname": n.hostname,
            "ip": n.ip,
            "last_seen": n.last_seen,
            "status": node_status,
            "base_os_family": n.base_os_family,
            "stats": stats,
            "tags": effective_tags,
            "is_operator_managed": op_tags is not None,
            "capabilities": json.loads(n.capabilities) if n.capabilities else None,
            "stats_history": history_map.get(n.node_id, []),
            "env_tag": n.env_tag,
            "detected_cgroup_version": n.detected_cgroup_version,
            "execution_mode": n.execution_mode,  # Phase 124
        })

    return {
        "items": resp,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@app.get("/nodes/{node_id}/detail", tags=["Nodes"], response_model=NodeResponse, summary="Get node details", description="Retrieve full details of a specific node")
async def get_node_detail(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    detail = await JobService.get_node_detail(node_id, db)
    if detail is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail


@app.patch("/nodes/{node_id}", tags=["Nodes"], response_model=ActionResponse, summary="Update node metadata", description="Update node tags and environment tag")
async def update_node_config(node_id: str, config: NodeUpdateRequest, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if config.tags is not None:
        node.operator_tags = json.dumps(config.tags)
    if config.env_tag is not None:
        node.env_tag = config.env_tag if config.env_tag != "" else None
        node.operator_env_tag = True  # Stays True even when cleared — distinguishes "never touched" from "explicitly cleared"

    await db.commit()
    return {
        "status": "updated",
        "resource_type": "node",
        "resource_id": node_id,
    }

@app.delete(
    "/nodes/{node_id}",
    status_code=204,
    response_class=Response,
    tags=["Nodes"],
    summary="Delete a node",
    description="Permanently delete a node and its associated metadata"
)
async def delete_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
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

@app.post("/nodes/{node_id}/revoke", tags=["Nodes"], response_model=ActionResponse, summary="Revoke node certificates", description="Prevent a node from accepting further work and block its enrollment")
async def revoke_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
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
    return {"status": "revoked", "resource_type": "node", "resource_id": node_id}

@app.patch("/nodes/{node_id}/drain", response_model=ActionResponse, summary="Drain node workload", description="Stop assigning new jobs while completing existing jobs", tags=["Nodes"])
async def drain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status not in ("ONLINE", "BUSY"):
        raise HTTPException(status_code=409, detail=f"Cannot drain node in {node.status} state")
    node.status = "DRAINING"
    audit(db, current_user, "node:drain", node_id)
    await db.commit()
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "DRAINING"})
    return {"status": "enabled", "resource_type": "node", "resource_id": node_id, "message": "Draining jobs"}


@app.patch("/nodes/{node_id}/undrain", response_model=ActionResponse, summary="Resume assigning jobs to drained node", description="Re-enable job assignment on a previously drained node", tags=["Nodes"])
async def undrain_node(node_id: str, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "DRAINING":
        raise HTTPException(status_code=409, detail="Node is not in DRAINING state")
    node.status = "ONLINE"
    audit(db, current_user, "node:undrain", node_id)
    await db.commit()
    await ws_manager.broadcast("node:updated", {"node_id": node_id, "status": "ONLINE"})
    return {"status": "enabled", "resource_type": "node", "resource_id": node_id, "message": "Node accepting jobs"}


@app.post("/api/nodes/{node_id}/clear-tamper", response_model=ActionResponse, summary="Clear tamper flag", description="Reset a node from TAMPERED to ONLINE after forensic review", tags=["Nodes"])
async def clear_node_tamper(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Resets a node from TAMPERED to ONLINE after administrator review."""
    
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node.status != "TAMPERED":
        raise HTTPException(status_code=409, detail="Node is not in tampered state")

    node.status = "ONLINE"
    node.tamper_details = None
    await db.commit()

    audit(db, current_user, "node:clear_tamper", node_id)
    return {"status": "approved", "resource_type": "node", "resource_id": node_id}

@app.post("/nodes/{node_id}/reinstate", response_model=ActionResponse, summary="Reinstate a revoked node", description="Transition a REVOKED node back to OFFLINE status for re-enrollment", tags=["Nodes"])
async def reinstate_node(node_id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.status != "REVOKED":
        raise HTTPException(status_code=409, detail="Node is not revoked")
    node.status = "OFFLINE"
    audit(db, current_user, "node:reinstate", node_id)
    await db.commit()
    return {"status": "approved", "resource_type": "node", "resource_id": node_id}

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
    # LIC-07: Node limit enforcement (checked before token validation to return correct status code)
    _ls = getattr(request.app.state, "licence_state", None)
    _node_limit = _ls.node_limit if _ls else 0
    if _node_limit > 0:
        from sqlalchemy import text as _sql_text
        _count_result = await db.execute(
            _sql_text("SELECT count(*) FROM nodes WHERE status NOT IN ('OFFLINE', 'REVOKED')")
        )
        _active_count = _count_result.scalar() or 0
        if _active_count >= _node_limit:
            raise HTTPException(
                status_code=402,
                detail="Node limit reached — upgrade your licence at axiom.sh/renew"
            )

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
            node.template_id = token_entry.template_id
        else:
            node = Node(
                node_id=node_id,
                hostname=req.hostname,
                ip=node_ip,
                status="ONLINE",
                template_id=token_entry.template_id,
                machine_id=req.machine_id,
                node_secret_hash=req.node_secret_hash,
                client_cert_pem=signed_cert,
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

@app.post("/admin/generate-token", response_model=EnrollmentTokenResponse, tags=["Admin"])
@limiter.limit("10/minute")
async def generate_token(request: Request, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
         
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

@app.get(
    "/job-definitions",
    response_model=List[JobDefinitionResponse],
    tags=["Job Definitions"],
    summary="List job definitions (alias)",
    description="Alias for GET /jobs/definitions - returns list of all scheduled job definitions"
)
async def dashboard_job_definitions(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)

@app.post("/api/enrollment-tokens", response_model=EnrollmentTokenResponse, tags=["Node Agent"])
async def create_enrollment_token(req: Optional[EnrollmentTokenCreate] = None, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):

    token_str = uuid.uuid4().hex
    token_entry = Token(token=token_str)
    if req and req.template_id:
        token_entry.template_id = req.template_id

    db.add(token_entry)
    await db.commit()
    return EnrollmentTokenResponse(token=token_str)
@app.post("/admin/upload-key", response_model=ActionResponse, tags=["Admin"])
async def upload_public_key(req: UploadKeyRequest, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if row:
        row.value = req.key_content
    else:
        db.add(Config(key="signing_public_key", value=req.key_content))
    audit(db, current_user, "key:upload")
    await db.commit()
    return ActionResponse(status="created", resource_type="public_key", resource_id="signing_public_key", message="Public key uploaded and stored")

# --- Licence Management (Phase 116) ---

@app.post("/api/admin/licence/reload", response_model=LicenceReloadResponse, tags=["Admin"])
async def reload_licence_endpoint(
    request: LicenceReloadRequest,
    current_user: User = Depends(require_permission("system:write")),
    db: AsyncSession = Depends(get_db)
):
    """Hot-reload licence key without restarting the server.

    Args:
        request: LicenceReloadRequest with optional licence_key override
        current_user: Must have system:write permission
        db: Database session

    Returns:
        LicenceReloadResponse with new licence state

    Raises:
        HTTPException 422 if licence validation fails
    """
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
        from .ee import activate_ee_live
        from .db import engine
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
            "expires_at": (datetime.utcnow() + timedelta(days=new_state.days_until_expiry)).isoformat() if new_state.days_until_expiry > 0 else None,
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

@app.get(
    "/config/public-key",
    response_model=dict,
    tags=["System"],
    summary="Get signing public key",
    description="Returns the Ed25519 public key for job script signature verification (requires valid enrollment token)"
)
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

@app.post("/config/mounts", response_model=ActionResponse, tags=["System"])
async def update_network_mounts(config: MountsConfig, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):

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
    return {"status": "updated", "resource_type": "mounts", "resource_id": "global_network_mounts", "message": f"Updated {len(config.mounts)} mount(s)"}

# --- Signature Registry API ---

@app.post("/signatures", response_model=SignatureResponse, tags=["Signatures"])
async def upload_signature(sig: SignatureCreate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await SignatureService.upload_signature(sig, current_user, db)

@app.get("/signatures", response_model=List[SignatureResponse], tags=["Signatures"])
async def list_signatures(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await SignatureService.list_signatures(db)

@app.get("/signatures/{id}", response_model=SignatureResponse, tags=["Signatures"])
async def get_signature(id: str, db: AsyncSession = Depends(get_db)):
    """Get a signature by ID. Unauthenticated (nodes need to fetch this for verification)."""
    result = await db.execute(select(Signature).where(Signature.id == id))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    return sig

@app.delete("/signatures/{id}", response_model=ActionResponse, tags=["Signatures"])
async def delete_signature(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    success = await SignatureService.delete_signature(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Signature not found")
    audit(db, current_user, "signature:delete", id)
    await db.commit()
    return {"status": "deleted", "resource_type": "signature", "resource_id": id}

# --- Job Definitions API ---

@app.post("/jobs/definitions", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.create_job_definition(def_req, current_user, db)

@app.get("/jobs/definitions", response_model=List[JobDefinitionResponse], tags=["Job Definitions"])
async def list_job_definitions(current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.list_job_definitions(db)

@app.delete("/jobs/definitions/{id}", response_model=ActionResponse, tags=["Job Definitions"])
async def delete_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
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
    return {"status": "deleted", "resource_type": "job_definition", "resource_id": id}

@app.patch("/jobs/definitions/{id}/toggle", response_model=ActionResponse, tags=["Job Definitions"])
async def toggle_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    job_def.is_active = not job_def.is_active
    await db.commit()
    await scheduler_service.sync_scheduler()
    return {"status": "updated", "resource_type": "job_definition", "resource_id": id, "message": f"Job definition is now {'active' if job_def.is_active else 'inactive'}"}

@app.get("/jobs/definitions/{id}", response_model=JobDefinitionResponse, tags=["Job Definitions"])
async def get_job_definition(id: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.get_job_definition(id, db)

@app.post("/api/jobs/push", response_model=JobDefinitionResponse, status_code=201, tags=["Job Definitions"])
async def push_job_definition(
    req: JobPushRequest,
    current_user: User = Depends(require_auth),
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
        raise HTTPException(422, detail=(
            "Signature verification failed — the script content does not match the provided signature. "
            "Ensure you signed the exact script content with the private key paired to the registered public key. "
            "See the Signatures page in the dashboard for key generation instructions."
        ))

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
async def update_job_definition(id: str, update_req: JobDefinitionUpdate, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.update_job_definition(id, update_req, current_user, db)

# === Workflow Routes ===

@app.post("/api/workflows", tags=["workflows"], response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    workflow_create: WorkflowCreate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Create a new Workflow with full-graph contract."""
    workflow_service = WorkflowService()
    return await workflow_service.create(db, workflow_create, current_user.id)

@app.get("/api/workflows", tags=["workflows"], response_model=list[WorkflowResponse])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> list[WorkflowResponse]:
    """List all Workflows with metadata (step_count, last_run_status)."""
    workflow_service = WorkflowService()
    return await workflow_service.list(db, skip, limit)

@app.get("/api/workflows/{workflow_id}", tags=["workflows"], response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get a single Workflow with full DAG (nested steps, edges, parameters)."""
    workflow_service = WorkflowService()
    return await workflow_service.get(db, workflow_id)

@app.put("/api/workflows/{workflow_id}", tags=["workflows"], response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Update a Workflow definition (atomic replace of steps/edges/parameters)."""
    workflow_service = WorkflowService()
    return await workflow_service.update(db, workflow_id, workflow_update)

@app.delete("/api/workflows/{workflow_id}", tags=["workflows"], status_code=204)
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a Workflow (blocked if active WorkflowRuns exist)."""
    workflow_service = WorkflowService()
    await workflow_service.delete(db, workflow_id)

@app.post("/api/workflows/{workflow_id}/fork", tags=["workflows"], response_model=WorkflowResponse, status_code=201)
async def fork_workflow(
    workflow_id: str,
    fork_request: dict = Body({"new_name": "..."}),  # {"new_name": "cloned-workflow"}
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Fork (Save-as-New) a Workflow: clone all steps/edges/parameters into a new Workflow,
    and pause the source workflow's cron schedule.
    """
    new_name = fork_request.get("new_name")
    if not new_name:
        raise HTTPException(status_code=422, detail="new_name is required")

    workflow_service = WorkflowService()
    return await workflow_service.fork(db, workflow_id, new_name, current_user.id)

@app.post("/api/workflows/validate", tags=["workflows"], response_model=dict)
async def validate_workflow(
    workflow_create: WorkflowCreate
) -> dict:
    """
    Validate a Workflow definition without saving (static check).
    Used by the DAG editor (Phase 151) on every canvas change.
    Returns {valid: true} or {valid: false, error: ..., cycle_path: ..., etc.}
    """
    steps_data = [s.model_dump() for s in workflow_create.steps]
    edges_data = [e.model_dump() for e in workflow_create.edges]

    is_valid, error = WorkflowService.validate_dag(steps_data, edges_data)
    if is_valid:
        return {"valid": True}
    else:
        return {"valid": False, **error}

@app.post("/api/workflow-runs", tags=["workflows"], response_model=WorkflowRunResponse, status_code=201)
async def create_workflow_run(
    body: dict,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a WorkflowRun.

    Request body: {
        "workflow_id": str,
        "parameters": {key: value} (optional)
    }

    Returns WorkflowRunResponse with initial step runs.
    """
    if not body.get("workflow_id"):
        raise HTTPException(status_code=400, detail="workflow_id required")

    workflow_service = WorkflowService()
    run = await workflow_service.start_run(
        workflow_id=body["workflow_id"],
        parameters=body.get("parameters", {}),
        triggered_by=current_user.username,
        db=db
    )

    await ws_manager.broadcast("workflow:run:created", {"run_id": run.id, "workflow_id": run.workflow_id, "status": "RUNNING"})
    return run

@app.post("/api/workflow-runs/{run_id}/cancel", tags=["workflows"], response_model=WorkflowRunResponse)
async def cancel_workflow_run(
    run_id: str,
    current_user: User = Depends(require_permission("workflows:write")),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running WorkflowRun.

    Blocks new step dispatches; running jobs continue to completion.
    """
    workflow_service = WorkflowService()
    run = await workflow_service.cancel_run(run_id, db)

    await ws_manager.broadcast("workflow:run:cancelled", {"run_id": run.id, "status": "CANCELLED"})
    return run

# --- Installer & Doc Endpoints ---

@app.get(
    "/api/installer",
    response_class=Response,
    tags=["System"],
    summary="Get node installer script",
    description="Returns the PowerShell installer script for node deployment"
)
async def get_installer():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "installer", "install_node.ps1")
    
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail="Installer script not found")

    with open(file_path, "r") as f:
        content = f.read()
    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=install_node.ps1"})

@app.get(
    "/api/docs",
    response_model=list,
    tags=["System"],
    summary="List available documentation files",
    description="Get list of available markdown documentation files"
)
async def list_docs(current_user: User = Depends(require_auth)):
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

@app.get(
    "/api/docs/{filename}",
    response_model=dict,
    tags=["System"],
    summary="Get documentation file content",
    description="Retrieve the full content of a markdown documentation file"
)
async def get_doc_content(filename: str, current_user: User = Depends(require_auth)):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(base_dir, "../docs")

    if not docs_dir:
        raise HTTPException(status_code=404, detail="Docs directory not found")

    # SEC-03: use validate_path_within to block path traversal (raises HTTP 400 on escape)
    safe_path = validate_path_within(Path(docs_dir), Path(docs_dir) / filename)

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    with open(safe_path, "r") as f:
        content = f.read()
    return {"content": content}

# --- WebSocket Live Feed ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = None):
    """Live event feed. Requires a valid JWT passed as ?token=<jwt> query param."""
    await ws.accept()
    # Validate token using a short-lived session so we don't hold a pool slot
    # for the entire WebSocket lifetime (which exhausts the connection pool).
    authed = False
    if token:
        try:
            from jose import jwt as _jwt, JWTError
            from .auth import SECRET_KEY, ALGORITHM
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
    ws_manager._connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# --- CRL Endpoint ---

@app.get(
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

# --- Signal API (Reactive Orchestration) ---

@app.post(
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
    """
    Fire a named signal to unblock dependent jobs.

    Authenticated via Bearer Token.
    """

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

@app.get("/api/signals", response_model=List[SignalResponse], tags=["Headless Automation"])
async def list_signals(
    current_user: User = Depends(require_auth),
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

@app.delete(
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
    """Clear a signal from the system (Admin Only)."""
    result = await db.execute(select(Signal).where(Signal.name == name))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(404, "Signal not found")
    
    await db.delete(sig)
    await db.commit()
    return {"status": "cleared"}

# --- Job Templates (SRCH-06, SRCH-07) ---

EXEC_CSV_HEADERS = ["job_guid", "node_id", "status", "exit_code",
                    "started_at", "completed_at", "duration_s", "attempt_number", "pinned"]


@app.post(
    "/api/job-templates",
    response_model=JobTemplateResponse,
    status_code=201,
    tags=["Job Templates"],
    summary="Create job template",
    description="Create a new reusable job template with visibility controls (private or shared)"
)
async def create_job_template(
    body: JobTemplateCreate,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new job template. Signing state fields are stripped from the payload."""
    payload_clean = {k: v for k, v in body.payload.items() if k not in SIGNING_FIELDS}
    template = JobTemplate(
        id=uuid.uuid4().hex,
        name=body.name,
        creator_id=current_user.username,
        visibility=body.visibility,
        payload=json.dumps(payload_clean),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "creator_id": template.creator_id,
        "visibility": template.visibility,
        "payload": payload_clean,
        "created_at": template.created_at,
    }


@app.get(
    "/api/job-templates",
    response_model=List[JobTemplateResponse],
    tags=["Job Templates"],
    summary="List job templates",
    description="List all job templates visible to the current user (own private templates + all shared templates)"
)
async def list_job_templates(
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """List job templates visible to the current user (own private + all shared)."""
    result = await db.execute(
        select(JobTemplate).where(
            (JobTemplate.visibility == "shared") | (JobTemplate.creator_id == current_user.username)
        ).order_by(JobTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "creator_id": t.creator_id,
            "visibility": t.visibility,
            "payload": json.loads(t.payload),
            "created_at": t.created_at,
        }
        for t in templates
    ]


@app.get(
    "/api/job-templates/{template_id}",
    response_model=JobTemplateResponse,
    tags=["Job Templates"],
    summary="Get job template",
    description="Fetch a single job template by ID (visibility rules apply - admin can see all, others see own + shared)"
)
async def get_job_template(
    template_id: str,
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single job template (visibility rules apply)."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.visibility != "shared" and t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(404, "Job template not found")
    return {
        "id": t.id,
        "name": t.name,
        "creator_id": t.creator_id,
        "visibility": t.visibility,
        "payload": json.loads(t.payload),
        "created_at": t.created_at,
    }


@app.patch(
    "/api/job-templates/{template_id}",
    response_model=JobTemplateResponse,
    tags=["Job Templates"],
    summary="Update a job template",
    description="Update job template name or visibility"
)
async def update_job_template(
    template_id: str,
    body: JobTemplateUpdate,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update a job template's name or visibility. Restricted to creator or admin."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(403, "Only the template creator or an admin can modify this template")
    if body.name is not None:
        t.name = body.name
    if body.visibility is not None:
        t.visibility = body.visibility
    await db.commit()
    await db.refresh(t)
    return {
        "id": t.id,
        "name": t.name,
        "creator_id": t.creator_id,
        "visibility": t.visibility,
        "payload": json.loads(t.payload),
        "created_at": t.created_at,
    }


@app.delete(
    "/api/job-templates/{template_id}",
    status_code=204,
    response_class=Response,
    tags=["Job Templates"],
    summary="Delete a job template",
    description="Permanently delete a job template"
)
async def delete_job_template(
    template_id: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job template. Restricted to creator or admin."""
    result = await db.execute(select(JobTemplate).where(JobTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Job template not found")
    if t.creator_id != current_user.username and current_user.role != "admin":
        raise HTTPException(403, "Only the template creator or an admin can delete this template")
    await db.delete(t)
    await db.commit()


# --- Retention Config (SRCH-08) ---

@app.get(
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
        select(func.count(ExecutionRecord.id)).where(
            ExecutionRecord.completed_at < cutoff,
            ExecutionRecord.pinned.is_(False),
        )
    )
    pinned_count = await db.scalar(
        select(func.count(ExecutionRecord.id)).where(
            ExecutionRecord.pinned.is_(True)
        )
    )
    return {
        "retention_days": retention_days,
        "eligible_count": eligible or 0,
        "pinned_count": pinned_count or 0,
    }


@app.patch(
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


# --- Smelter: Transitive CVE Scanning & Dependency Tree (Phase 110) ---

async def _build_tree_response_recursive(db, ingredient_id, visited, depth=0, max_depth=10):
    """Recursively build DependencyTreeNode tree structure."""
    from .models import DependencyTreeNode, CVEDetail

    if depth > max_depth or ingredient_id in visited:
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

    result = await db.execute(select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    cves = []
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

    children = []
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
            continue

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


def _count_tree_nodes(node):
    """Count total nodes in tree."""
    count = 1
    for child in node.children:
        count += _count_tree_nodes(child)
    return count


async def _build_tree_response(db, ingredient):
    """Build complete DependencyTreeResponse for an ingredient."""
    from .models import DependencyTreeResponse, DependencyTreeNode

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


@app.get(
    "/api/smelter/ingredients/{ingredient_id}/tree",
    response_model=DependencyTreeResponse,
    tags=["Smelter"],
    summary="Get dependency tree with CVE information"
)
async def get_dependency_tree(
    ingredient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("smelter:read"))
):
    """
    Get the full dependency tree for an ingredient, including CVE vulnerability data.

    Returns:
    - Complete tree structure with all transitive dependencies
    - CVE counts and severity badges for each node
    - Provenance paths for vulnerable dependencies
    """
    result = await db.execute(
        select(ApprovedIngredient).where(ApprovedIngredient.id == ingredient_id)
    )
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail=f"Ingredient {ingredient_id} not found"
        )

    tree_response = await _build_tree_response(db, ingredient)
    return tree_response


@app.post(
    "/api/smelter/ingredients/{ingredient_id}/discover",
    response_model=DiscoverDependenciesResponse,
    tags=["Smelter"],
    summary="Discover and resolve transitive dependencies",
    status_code=200
)
async def discover_dependencies(
    ingredient_id: str,
    request: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("smelter:write"))
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
    from .services.resolver_service import ResolverService
    from .services.smelter_service import SmelterService

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

    from .models import DiscoverDependenciesResponse as DDResponse
    return DDResponse(
        ingredient_id=ingredient_id,
        discovered_count=discovered_count,
        tree=tree_response,
        toast_message=toast_message
    )


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
             sans = ["localhost", "master-of-puppets", "agent", "puppeteer-agent-1", "host.docker.internal", hostname, ip]
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

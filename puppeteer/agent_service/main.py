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
    PaginatedResponse, PaginatedJobResponse, ActionResponse, JobCountResponse, JobStatsResponse, DispatchDiagnosisResponse, BulkDispatchDiagnosisResponse,
    DependencyTreeResponse, DiscoverDependenciesResponse,
    WorkflowCreate, WorkflowResponse, WorkflowUpdate, WorkflowRunResponse,
    WorkflowWebhookCreate, WorkflowWebhookResponse,
    WorkflowRunUpdatedEvent, WorkflowStepUpdatedEvent, WorkflowRunListResponse,
    ScheduleListResponse,
)
from .security import (
    encrypt_secrets, decrypt_secrets, mask_secrets,
    verify_client_cert, ENCRYPTION_KEY, cipher_suite, oauth2_scheme,
    mask_pii, verify_node_secret, validate_path_within,
    hash_webhook_secret, verify_webhook_signature
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from sqlalchemy.future import select
from sqlalchemy import update, desc, func, delete
from sqlalchemy.orm import selectinload
from collections import defaultdict
from cryptography import x509 as _x509
from .db import init_db, get_db, Job, Token, Config, User, Node, NodeStats, AsyncSession, Signature, ScheduledJob, Ping, AsyncSessionLocal, RevokedCert, ExecutionRecord, Signal, Alert, JobTemplate, ApprovedIngredient, IngredientDependency, ApprovedOS, WorkflowStepRun, Workflow, WorkflowRun, WorkflowWebhook
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
    # Run Alembic migrations first (if available) via subprocess
    import subprocess as _subprocess_alembic
    import asyncio as _asyncio_alembic
    try:
        # Run alembic upgrade head as subprocess (standard pattern for async FastAPI)
        result = await _asyncio_alembic.to_thread(
            lambda: _subprocess_alembic.run(
                ["alembic", "upgrade", "head"],
                cwd="/app",  # Docker working directory
                capture_output=True,
                text=True,
                timeout=60,
            )
        )
        if result.returncode == 0:
            logger.info("Alembic migrations completed successfully")
        else:
            logger.warning(f"Alembic migration warning: {result.stderr}. Falling back to init_db()...")
    except FileNotFoundError:
        logger.debug("Alembic CLI not found, skipping migrations")
    except Exception as e:
        logger.warning(f"Alembic migration failed: {e}. Falling back to init_db()...")

    # Fallback: ensure all tables exist (defense-in-depth pattern)
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

# --- CE ROUTERS ---
from .routers.auth_router import router as auth_router
from .routers.jobs_router import router as jobs_router
from .routers.nodes_router import router as nodes_router
from .routers.workflows_router import router as workflows_router
from .routers.admin_router import router as admin_router
from .routers.system_router import router as system_router
from .routers.smelter_router import router as smelter_router

# Include CE routers (after middleware setup, before route definitions)
app.include_router(auth_router, tags=["Authentication"])
app.include_router(jobs_router, tags=["Jobs", "Job Definitions", "Job Templates", "CI/CD Dispatch"])
app.include_router(nodes_router, tags=["Nodes", "Node Agent"])
app.include_router(workflows_router, tags=["Workflows"])
app.include_router(admin_router, tags=["Admin", "Signatures", "Alerts & Webhooks"])
app.include_router(system_router, tags=["System", "Health", "Schedule"])
app.include_router(smelter_router, tags=["Foundry", "Blueprints"])

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

    async def broadcast_workflow_run_updated(self, event: "WorkflowRunUpdatedEvent") -> None:
        """Broadcast a workflow run status update to all connected clients."""
        message = {
            "event": "workflow_run_updated",
            "data": event.model_dump(mode='json')
        }
        await self.broadcast("workflow_run_updated", message["data"])

    async def broadcast_workflow_step_updated(self, event: "WorkflowStepUpdatedEvent") -> None:
        """Broadcast a workflow step status update to all connected clients."""
        message = {
            "event": "workflow_step_updated",
            "data": event.model_dump(mode='json')
        }
        await self.broadcast("workflow_step_updated", message["data"])

ws_manager = ConnectionManager()

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

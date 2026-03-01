from fastapi import FastAPI, HTTPException, Request, Depends, Header, status, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uuid
import json
import os
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
    NodeResponse, SignatureCreate, SignatureResponse, JobDefinitionCreate,
    JobDefinitionResponse, PingRequest, NetworkMount, MountsConfig,
    ImageBuildRequest, ImageResponse, EnrollmentRequest,
    BlueprintCreate, BlueprintResponse, PuppetTemplateCreate, PuppetTemplateResponse,
    CapabilityMatrixEntry, UploadKeyRequest, UserCreate, UserResponse, PermissionGrant
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
from .db import init_db, get_db, Job, Token, Config, User, Node, NodeStats, AsyncSession, Signature, ScheduledJob, Ping, AsyncSessionLocal, CapabilityMatrix, Blueprint, PuppetTemplate, RolePermission, AuditLog, RevokedCert
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from .services.job_service import JobService
from .services.signature_service import SignatureService
from .services.scheduler_service import scheduler_service
from .services.pki_service import pki_service
from .services.foundry_service import foundry_service

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
                    validation_cmd="python --version"
                ),
                CapabilityMatrix(
                    base_os_family="DEBIAN",
                    tool_id="pwsh-7.4",
                    injection_recipe="RUN apt-get update && apt-get install -y wget && wget https://github.com/PowerShell/PowerShell/releases/download/v7.4.1/powershell_7.4.1-1.deb_amd64.deb && dpkg -i powershell_7.4.1-1.deb_amd64.deb && apt-get install -f",
                    validation_cmd="pwsh -version"
                )
            ]
            db.add_all(recipes)
            await db.commit()
            logger.info("✅ Capability Matrix Seeded")

    # Seed Role Permissions
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RolePermission).limit(1))
        if not result.scalar_one_or_none():
            logger.info("🌱 Seeding Role Permissions...")
            OPERATOR_PERMS = [
                "jobs:read", "jobs:write", "nodes:read", "nodes:write",
                "definitions:read", "definitions:write", "foundry:read",
                "signatures:read", "tokens:write",
            ]
            VIEWER_PERMS = [
                "jobs:read", "nodes:read", "definitions:read", "foundry:read", "signatures:read",
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

# Serve Installer Scripts
@app.get("/api/installer/compose")
async def get_node_compose(token: str, mounts: Optional[str] = None):
    """Dynamic Compose File generator for Nodes."""
    compose_content = f"""
version: '3.8'
services:
  puppet:
    image: localhost/master-of-puppets-node:latest
    container_name: puppet-node
    network_mode: host
    environment:
      - AGENT_URL={os.getenv("AGENT_URL", "https://localhost:8001")}
      - JOIN_TOKEN={token}
      - MOUNT_DATA={mounts if mounts else ""}
      - NODE_TAGS=general,linux,arm64
    volumes:
      - ./secrets:/app/secrets
    restart: unless-stopped
"""
    return Response(content=compose_content, media_type="text/yaml")

if not os.path.exists("installer"):
    os.makedirs("installer")
app.mount("/installer", StaticFiles(directory="installer"), name="installer")

@app.get("/verification-key")
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

@app.get("/installer")
async def get_installer_ps1():
    """Serves the Universal PowerShell Installer (One-Liner)."""
    file_path = "installer/install_universal.ps1"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/installer.sh")
async def get_installer_sh():
    """Serves the Universal Bash Installer."""
    file_path = "installer/install_universal.sh"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/system/root-ca")
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

@app.get("/system/root-ca-installer")
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

@app.get("/system/root-ca-installer.ps1")
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

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """JWT User Auth."""
    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
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

def require_permission(perm: str):
    """Dependency factory that enforces a named permission via DB-backed RBAC."""
    async def _check(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if current_user.role == "admin":
            return current_user
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role == current_user.role,
                RolePermission.permission == perm
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return current_user
    return _check

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

@app.post("/auth/login", response_model=TokenResponse)
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
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role,
            "must_change_password": bool(user.must_change_password)}

@app.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role,
            "must_change_password": bool(current_user.must_change_password)}

@app.patch("/auth/me")
async def update_self(req: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Allow a logged-in user to change their own password."""
    new_password = req.get("password", "").strip()
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    current_user.password_hash = get_password_hash(new_password)
    current_user.must_change_password = False
    await db.commit()
    await audit(db, current_user.username, "user:password_changed", {"username": current_user.username})
    return {"status": "ok", "must_change_password": False}

# --- Core Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "Agent Service v0.7"}

@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 50, current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    return await JobService.list_jobs(db, skip=skip, limit=limit)

@app.get("/jobs/count")
async def count_jobs(current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    result = await db.execute(select(sqlfunc.count()).select_from(Job).where(Job.task_type != 'system_heartbeat'))
    return {"total": result.scalar()}

@app.get("/api/jobs/stats")
async def get_job_stats(current_user: User = Depends(require_permission("jobs:read")), db: AsyncSession = Depends(get_db)):
    """Backend Stats for Dashboard charts."""
    return await JobService.get_job_stats(db)

@app.post("/jobs", response_model=JobResponse)
async def create_job(job_req: JobCreate, current_user: User = Depends(require_permission("jobs:write")), db: AsyncSession = Depends(get_db)):
    try:
        result = await JobService.create_job(job_req, db)
        await ws_manager.broadcast("job:created", {"guid": result["guid"], "status": "PENDING", "task_type": job_req.task_type})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/jobs/{guid}/cancel")
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

@app.post("/work/pull", response_model=PollResponse)
async def pull_work(request: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = request.client.host
    return await JobService.pull_work(node_id, node_ip, db)

@app.post("/heartbeat")
async def receive_heartbeat(req: Request, hb: HeartbeatPayload, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    result = await JobService.receive_heartbeat(node_id, node_ip, hb, db)
    await ws_manager.broadcast("node:heartbeat", {"node_id": node_id, "status": "ONLINE", "stats": hb.stats})
    return result

@app.post("/work/{guid}/result")
async def report_result(guid: str, report: ResultReport, req: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    if report.result:
        report.result = mask_pii(report.result)
        
    updated = await JobService.report_result(guid, report, node_ip, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": updated.get("status", "COMPLETED")})
    return updated

@app.get("/nodes", response_model=List[NodeResponse])
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
        tags = json.loads(n.tags) if n.tags else None

        resp.append({
            "node_id": n.node_id,
            "hostname": n.hostname,
            "ip": n.ip,
            "last_seen": n.last_seen,
            "status": status,
            "stats": stats,
            "tags": tags,
            "capabilities": json.loads(n.capabilities) if n.capabilities else None,
            "concurrency_limit": n.concurrency_limit,
            "job_memory_limit": n.job_memory_limit,
            "stats_history": history_map.get(n.node_id, []),
        })
    return resp

@app.patch("/nodes/{node_id}")
async def update_node_config(node_id: str, config: NodeConfig, current_user: User = Depends(require_permission("nodes:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.concurrency_limit = config.concurrency_limit
    node.job_memory_limit = config.job_memory_limit
    await db.commit()
    return {"status": "updated", "node_id": node_id, "concurrency_limit": config.concurrency_limit, "job_memory_limit": config.job_memory_limit}

@app.delete("/nodes/{node_id}", status_code=204)
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

@app.post("/nodes/{node_id}/revoke")
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

@app.post("/nodes/{node_id}/reinstate")
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

@app.post("/auth/register", response_model=RegisterResponse)
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

@app.post("/api/enroll", response_model=RegisterResponse)
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
        
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        
        if node:
            node.node_secret_hash = req.node_secret_hash
            node.machine_id = req.machine_id
            node.ip = node_ip
            node.last_seen = datetime.utcnow()
            node.client_cert_pem = signed_cert
        else:
            node = Node(
                node_id=node_id,
                hostname=req.hostname,
                ip=node_ip,
                status="ONLINE",
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
    except Exception as e:
        logger.error(f"Enrollment Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")

# --- Admin Endpoints ---

import base64

@app.post("/admin/generate-token")
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

@app.post("/api/blueprints", response_model=BlueprintResponse)
async def create_blueprint(req: BlueprintCreate, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    
    new_bp = Blueprint(
        id=str(uuid.uuid4()),
        type=req.type,
        name=req.name,
        definition=json.dumps(req.definition)
    )
    db.add(new_bp)
    await db.commit()
    await db.refresh(new_bp)
    
    return {
        "id": new_bp.id,
        "type": new_bp.type,
        "name": new_bp.name,
        "definition": req.definition,
        "version": new_bp.version,
        "created_at": new_bp.created_at
    }

@app.get("/api/blueprints", response_model=List[BlueprintResponse])
async def list_blueprints(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Blueprint))
    bps = result.scalars().all()
    return [{
        "id": bp.id,
        "type": bp.type,
        "name": bp.name,
        "definition": json.loads(bp.definition),
        "version": bp.version,
        "created_at": bp.created_at
    } for bp in bps]

# Legacy/Frontend Aliases
@app.get("/foundry/definitions")
async def foundry_definitions(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/definitions instead of /api/blueprints"""
    return await list_blueprints(current_user, db)

@app.get("/job-definitions")
async def dashboard_job_definitions(current_user: User = Depends(require_permission("definitions:read")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)

@app.post("/api/templates", response_model=PuppetTemplateResponse)
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

@app.get("/api/templates", response_model=List[PuppetTemplateResponse])
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
    } for t in templates]

@app.post("/api/templates/{id}/build", response_model=ImageResponse)
async def build_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await foundry_service.build_template(id, db)
    audit(db, current_user, "template:build", id)
    await db.commit()
    return result

@app.post("/foundry/build")
async def dashboard_foundry_build(req: dict, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/build with template_id in body"""
    template_id = req.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="Missing template_id in body")
    return await build_template(template_id, current_user, db)

@app.delete("/api/blueprints/{id}")
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

@app.delete("/api/templates/{id}")
async def delete_template(id: str, current_user: User = Depends(require_permission("foundry:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == id))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    audit(db, current_user, "template:delete", id, {"name": tmpl.friendly_name})
    await db.delete(tmpl)
    await db.commit()
    return {"status": "deleted"}

@app.get("/api/capability-matrix", response_model=List[CapabilityMatrixEntry])
async def get_capability_matrix(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CapabilityMatrix))
    return result.scalars().all()

# --- Foundry & Enrollment Endpoints ---

@app.post("/api/images", response_model=ImageResponse)
async def create_image(req: ImageBuildRequest, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return await foundry_service.build_image(req)

@app.get("/api/images", response_model=List[ImageResponse])
async def list_images(current_user: User = Depends(get_current_user)):
    return await foundry_service.list_images()

@app.post("/api/enrollment-tokens")
async def create_enrollment_token(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create enrollment tokens")
    
    # This is a shell, it will be fully implemented in Phase 2
    token_str = uuid.uuid4().hex
    db.add(Token(token=token_str))
    await db.commit()
    return {"token": token_str}

@app.post("/admin/upload-key")
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

@app.get("/admin/users", response_model=List[UserResponse])
async def list_users(current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.username, "username": u.username, "role": u.role, "created_at": u.created_at} for u in users]

@app.post("/admin/users", response_model=UserResponse, status_code=201)
async def create_user(req: UserCreate, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    new_user = User(username=req.username, password_hash=get_password_hash(req.password), role=req.role)
    db.add(new_user)
    audit(db, current_user, "user:create", req.username, {"role": req.role})
    await db.commit()
    return {"id": new_user.username, "username": new_user.username, "role": new_user.role, "created_at": new_user.created_at}

@app.delete("/admin/users/{username}")
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

@app.patch("/admin/users/{username}", response_model=UserResponse)
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

@app.get("/admin/roles/{role}/permissions")
async def list_role_permissions(role: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role))
    perms = result.scalars().all()
    return [{"id": p.id, "role": p.role, "permission": p.permission} for p in perms]

@app.post("/admin/roles/{role}/permissions", status_code=201)
async def grant_role_permission(role: str, req: PermissionGrant, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == req.permission))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Permission already granted")
    db.add(RolePermission(role=role, permission=req.permission))
    audit(db, current_user, "permission:grant", role, {"permission": req.permission})
    await db.commit()
    return {"status": "granted", "role": role, "permission": req.permission}

@app.delete("/admin/roles/{role}/permissions/{permission}")
async def revoke_role_permission(role: str, permission: str, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RolePermission).where(RolePermission.role == role, RolePermission.permission == permission))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    audit(db, current_user, "permission:revoke", role, {"permission": permission})
    await db.delete(perm)
    await db.commit()
    return {"status": "revoked", "role": role, "permission": permission}

@app.patch("/admin/users/{username}/reset-password")
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
    await audit(db, current_user.username, "user:password_reset", {"target": username, "by": current_user.username})
    await db.commit()
    return {"status": "ok"}

@app.patch("/admin/users/{username}/force-password-change")
async def admin_force_password_change(username: str, req: dict, current_user: User = Depends(require_permission("users:write")), db: AsyncSession = Depends(get_db)):
    """Set or clear the must_change_password flag for a user."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    enabled = bool(req.get("enabled", True))
    user.must_change_password = enabled
    action = "user:force_password_change_set" if enabled else "user:force_password_change_cleared"
    await audit(db, current_user.username, action, {"target": username})
    await db.commit()
    return {"status": "ok", "must_change_password": enabled}

@app.get("/config/public-key")
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

@app.get("/config/mounts", response_model=List[NetworkMount])
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

@app.post("/config/mounts")
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

@app.post("/signatures", response_model=SignatureResponse)
async def upload_signature(sig: SignatureCreate, current_user: User = Depends(require_permission("signatures:write")), db: AsyncSession = Depends(get_db)):
    return await SignatureService.upload_signature(sig, current_user, db)

@app.get("/signatures", response_model=List[SignatureResponse])
async def list_signatures(current_user: User = Depends(require_permission("signatures:read")), db: AsyncSession = Depends(get_db)):
    return await SignatureService.list_signatures(db)

@app.delete("/signatures/{id}")
async def delete_signature(id: str, current_user: User = Depends(require_permission("signatures:write")), db: AsyncSession = Depends(get_db)):
    success = await SignatureService.delete_signature(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Signature not found")
    audit(db, current_user, "signature:delete", id)
    await db.commit()
    return {"status": "deleted"}

# --- Job Definitions API ---

@app.post("/jobs/definitions", response_model=JobDefinitionResponse)
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.create_job_definition(def_req, current_user, db)

@app.get("/jobs/definitions", response_model=List[JobDefinitionResponse])
async def list_job_definitions(current_user: User = Depends(require_permission("definitions:read")), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.list_job_definitions(db)

@app.delete("/jobs/definitions/{id}")
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

@app.patch("/jobs/definitions/{id}/toggle")
async def toggle_job_definition(id: str, current_user: User = Depends(require_permission("definitions:write")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == id))
    job_def = result.scalar_one_or_none()
    if not job_def:
        raise HTTPException(status_code=404, detail="Job definition not found")
    job_def.is_active = not job_def.is_active
    await db.commit()
    await scheduler_service.sync_scheduler()
    return {"id": id, "is_active": job_def.is_active}

# --- Installer & Doc Endpoints ---

@app.get("/api/installer")
async def get_installer():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "installer", "install_node.ps1")
    
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail="Installer script not found")

    with open(file_path, "r") as f:
        content = f.read()
    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=install_node.ps1"})

@app.get("/api/docs")
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

@app.get("/api/docs/{filename}")
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
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep alive — client sends pings; server echoes
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# --- Audit Log Endpoint ---

@app.get("/admin/audit-log")
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

@app.post("/admin/mark-base-updated")
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

@app.get("/admin/base-image-updated")
async def get_base_image_updated(current_user: User = Depends(require_permission("foundry:read")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Config).where(Config.key == "base_node_image_updated_at"))
    row = result.scalar_one_or_none()
    return {"base_node_image_updated_at": row.value if row else None}

# --- CRL Endpoint ---

@app.get("/system/crl.pem")
async def get_crl(db: AsyncSession = Depends(get_db)):
    """Returns a signed X.509 CRL of all revoked node certificates."""
    result = await db.execute(select(RevokedCert))
    revoked = result.scalars().all()
    serials = [r.serial_number for r in revoked]
    crl_pem = pki_service.ca_authority.generate_crl(serials)
    return Response(content=crl_pem, media_type="application/x-pem-file")

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

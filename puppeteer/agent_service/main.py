from fastapi import FastAPI, HTTPException, Request, Depends, Header, status
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
    CapabilityMatrixEntry
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
from sqlalchemy import update, desc, func
from .db import init_db, get_db, Job, Token, Config, User, Node, AsyncSession, Signature, ScheduledJob, Ping, AsyncSessionLocal, CapabilityMatrix, Blueprint, PuppetTemplate
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
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}

# --- Core Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "Agent Service v0.7"}

@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    return await JobService.list_jobs(db)

@app.get("/api/jobs/stats")
async def get_job_stats(db: AsyncSession = Depends(get_db)):
    """Backend Stats for Dashboard charts."""
    return await JobService.get_job_stats(db)

@app.post("/jobs", response_model=JobResponse)
async def create_job(job_req: JobCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await JobService.create_job(job_req, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/work/pull", response_model=PollResponse)
async def pull_work(request: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = request.client.host
    return await JobService.pull_work(node_id, node_ip, db)

@app.post("/heartbeat")
async def receive_heartbeat(req: Request, hb: HeartbeatPayload, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    return await JobService.receive_heartbeat(node_id, node_ip, hb, db)

@app.post("/work/{guid}/result")
async def report_result(guid: str, report: ResultReport, req: Request, node_id: str = Depends(verify_node_secret), api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    node_ip = req.client.host
    if report.result:
        report.result = mask_pii(report.result)
        
    updated = await JobService.report_result(guid, report, node_ip, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    return updated

@app.get("/nodes", response_model=List[NodeResponse])
async def list_nodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node))
    nodes = result.scalars().all()
    
    resp = []
    for n in nodes:
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
        })
    return resp

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
        else:
            node = Node(
                node_id=node_id,
                hostname=req.hostname,
                ip=node_ip,
                status="ONLINE",
                machine_id=req.machine_id,
                node_secret_hash=req.node_secret_hash
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
async def generate_token(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in ["admin", "operator"]:
         raise HTTPException(status_code=403, detail="Insufficient Permissions")
         
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
async def create_blueprint(req: BlueprintCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
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
async def list_blueprints(db: AsyncSession = Depends(get_db)):
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
async def foundry_definitions(db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/definitions instead of /api/blueprints"""
    return await list_blueprints(db)

@app.get("/job-definitions")
async def dashboard_job_definitions(db: AsyncSession = Depends(get_db)):
    """Dashboard expects /job-definitions instead of /jobs/definitions"""
    return await scheduler_service.list_job_definitions(db)

@app.post("/api/templates", response_model=PuppetTemplateResponse)
async def create_template(req: PuppetTemplateCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
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
async def list_templates(db: AsyncSession = Depends(get_db)):
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
async def build_template(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return await foundry_service.build_template(id, db)

@app.post("/foundry/build")
async def dashboard_foundry_build(req: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Dashboard expects /foundry/build with template_id in body"""
    template_id = req.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="Missing template_id in body")
    return await build_template(template_id, current_user, db)

@app.get("/api/capability-matrix", response_model=List[CapabilityMatrixEntry])
async def get_capability_matrix(db: AsyncSession = Depends(get_db)):
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
    if current_user.role not in ["admin", "operator"]:
         raise HTTPException(status_code=403, detail="Insufficient Permissions")
    
    # This is a shell, it will be fully implemented in Phase 2
    token_str = uuid.uuid4().hex
    db.add(Token(token=token_str))
    await db.commit()
    return {"token": token_str}

@app.post("/admin/upload-key")
async def upload_public_key(req: object, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return {"status": "stored"}

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
async def upload_signature(sig: SignatureCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    return await SignatureService.upload_signature(sig, current_user, db)

@app.get("/signatures", response_model=List[SignatureResponse])
async def list_signatures(db: AsyncSession = Depends(get_db)):
    return await SignatureService.list_signatures(db)

@app.delete("/signatures/{id}")
async def delete_signature(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
    success = await SignatureService.delete_signature(id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Signature not found")
    return {"status": "deleted"}

# --- Job Definitions API ---

@app.post("/jobs/definitions", response_model=JobDefinitionResponse)
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await scheduler_service.create_job_definition(def_req, current_user, db)

@app.get("/jobs/definitions", response_model=List[JobDefinitionResponse])
async def list_job_definitions(db: AsyncSession = Depends(get_db)):
    return await scheduler_service.list_job_definitions(db)

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
async def list_docs():
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
async def get_doc_content(filename: str):
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

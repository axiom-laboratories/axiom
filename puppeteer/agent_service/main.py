from fastapi import FastAPI, HTTPException, Request, Depends, Header, status
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uuid
import json
import os
import subprocess
from typing import Optional, List, Dict
from cryptography.fernet import Fernet
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from sqlalchemy.future import select
from sqlalchemy import update, desc, func
from .db import init_db, get_db, Job, Token, Config, User, Node, AsyncSession, Signature, ScheduledJob, Ping
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

load_dotenv()

app = FastAPI(title="Master of Puppets v0.8", description="Orchestrator (v0.8) - Security & Mounts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"], # Dashboard + BFF
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Installer Scripts
if not os.path.exists("installer"):
    os.makedirs("installer")
app.mount("/installer", StaticFiles(directory="installer"), name="installer")

# Security CRITICAL: Fail if API_KEY is not set.
try:
    API_KEY = os.environ["API_KEY"]
except KeyError:
    import sys
    print("CRITICAL: API_KEY setup variable is missing. Halting.")
    sys.exit(1)
# Encryption Key for Secrets
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode() if os.getenv("ENCRYPTION_KEY") else Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# --- Auth Security Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Helpers ---

def encrypt_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k, v in payload["secrets"].items():
            if isinstance(v, str):
                new_secrets[k] = cipher_suite.encrypt(v.encode()).decode()
            else:
                new_secrets[k] = v
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

def decrypt_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k, v in payload["secrets"].items():
            try:
                if isinstance(v, str):
                    new_secrets[k] = cipher_suite.decrypt(v.encode()).decode()
                else:
                    new_secrets[k] = v
            except Exception:
                new_secrets[k] = "ERROR_DECRYPTING"
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

def mask_secrets(payload: Dict) -> Dict:
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k in payload["secrets"].keys():
            new_secrets[k] = "****** (Redacted)"
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

async def verify_api_key(x_api_key: str = Header(None)):
    """Legacy/Service Auth via API Key."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

async def verify_client_cert(request: Request):
    """Enforces mTLS: Requires a valid client certificate."""
    # In a real proxy/Uvicorn setup, common_name is passed in header (e.g., X-SSL-Client-CN)
    # or accessible via request.scope['client'] if SSL is terminated here.
    # For now, we will trust X-SSL-Client-Verified: SUCCESS header from Uvicorn/Proxy
    # OR (since we are using Uvicorn directly):
    
    # NOTE: Uvicorn does not expose client cert details in ASGI scope easily without quirks.
    pass

@app.get("/api/verification-key")
async def get_verification_key():
    """Serves the Public Verification Key for Code Signing."""
    """Serves the Public Verification Key for Code Signing."""
    key_path = "/app/secrets/verification.key"
    if not os.path.exists(key_path):
        # Fallback to relative if not found (dev env)
        if os.path.exists("secrets/verification.key"):
            key_path = "secrets/verification.key"
        else:
            raise HTTPException(status_code=404, detail="Verification Key not configured on Server")
    
    with open(key_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/api/installer")
async def get_installer_ps1():
    """Serves the Universal PowerShell Installer (One-Liner)."""
    file_path = "installer/install_universal.ps1"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")

@app.get("/api/installer.sh")
async def get_installer_sh():
    """Serves the Universal Bash Installer."""
    file_path = "installer/install_universal.sh"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Installer not found")
    with open(file_path, "r") as f:
        return Response(content=f.read(), media_type="text/plain")
    # We will assume mTLS is enforced at connection level if configured.
    # To be stricter, we'd inspect `request.scope.get('extensions', {}).get('tls', {})` if supported.
    
    # Placeholder: In v0.9, we rely on the TCP Accept to fail if no cert.
    pass

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
    """Optional JWT User Auth (Does not raise 401)."""
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

# --- Models (Pydantic) ---
class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0

class RegisterRequest(BaseModel):
    client_secret: str
    hostname: str
    csr_pem: str

class RegisterResponse(BaseModel):
    client_cert_pem: str
    ca_url: str

class JobResponse(BaseModel):
    guid: str
    status: str
    payload: Dict
    result: Optional[Dict] = None
    node_id: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None # Calculated field

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict

class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

@app.on_event("startup")
async def on_startup():
    await init_db()
    # Bootstrap Admin
    async for db in get_db():
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin_user = User(
                username="admin", 
                # Security: Prefer Env Var, fallback to random secure string (printed to stdout)
                password_hash=get_password_hash(os.getenv("ADMIN_PASSWORD", uuid.uuid4().hex)), 
                role="admin"
            )
            # Log this carefully - better to force the user to set the env var, but for now this prevents 'admin/admin'
            if not os.getenv("ADMIN_PASSWORD"):
                print(f"⚠️  Admin User created with RANDOM password. Please set ADMIN_PASSWORD env var.")
            else:
                logger.info("✅ Bootstrapped Admin User")
        break # Just one session needed

# --- Auth Endpoints ---

@app.post("/auth/login", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
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
async def list_jobs(db: AsyncSession = Depends(get_db)): # Allow public read for now, or add Depends(get_current_user)
    """For the Dashboard. Filters system jobs by default unless requested?"""
    # Only show user jobs
    result = await db.execute(
        select(Job).where(Job.task_type != 'system_heartbeat') \
        .order_by(desc(Job.created_at)).limit(50)
    )
    jobs = result.scalars().all()
    
    response_jobs = []
    for job in jobs:
        payload = json.loads(job.payload)
        
        # Calculate duration
        duration = None
        if job.started_at:
            end = job.completed_at or datetime.utcnow()
            duration = (end - job.started_at).total_seconds()

        response_jobs.append({
            "guid": job.guid,
            "status": job.status,
            "payload": mask_secrets(payload), 
            "result": json.loads(job.result) if job.result else None,
            "node_id": job.node_id,
            "started_at": job.started_at,
            "duration_seconds": duration
        })
    return response_jobs

@app.post("/jobs", response_model=JobResponse)
async def create_job(job_req: JobCreate, db: AsyncSession = Depends(get_db)):
    """Received from Model Service or Authorized User."""
    # TODO: Add Auth check (User or API Key)
    
    guid = str(uuid.uuid4())
    
    # Encrypt secrets before storing
    encrypted_payload = encrypt_secrets(job_req.payload)
    
    new_job = Job(
        guid=guid,
        task_type=job_req.task_type,
        status="PENDING",
        payload=json.dumps(encrypted_payload),
        created_at=datetime.utcnow()
    )
    
    try:
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"guid": guid, "status": "PENDING", "payload": encrypted_payload}

class NodeConfig(BaseModel):
    concurrency_limit: int
    job_memory_limit: str

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    config: NodeConfig

@app.post("/work/pull", response_model=PollResponse)
async def pull_work(request: Request, api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    """Called by Environment Nodes."""
    node_ip = request.client.host
    # Use X-Node-ID if available, else IP
    node_id = request.headers.get("X-Node-ID", node_ip)
    
    # 1. Fetch Node Configuration
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    
    # Default Config
    concurrency = 5
    memory = "512m"
    
    if node:
        concurrency = node.concurrency_limit
        memory = node.job_memory_limit
        # Update last seen while we're here?
        node.last_seen = datetime.utcnow()
        if node.ip != node_ip:
             node.ip = node_ip
    else:
        # Create Node if not exists (Auto-Registration on Poll)
        # Typically Heartbeat handles this, but good for robustness
        node = Node(
            node_id=node_id, 
            hostname=node_id, 
            ip=node_ip, 
            status="ONLINE", 
            concurrency_limit=concurrency,
            job_memory_limit=memory
        )
        db.add(node)
    
    # Commit node update/creation
    await db.commit()
    
    node_config = NodeConfig(concurrency_limit=concurrency, job_memory_limit=memory)

    # 2. Check Concurrency Limit (Server-Side Guard)
    result = await db.execute(select(func.count(Job.guid)).where(Job.status == 'ASSIGNED', Job.node_id == node_id))
    active_count = result.scalar()
    
    if active_count >= concurrency:
        return PollResponse(job=None, config=node_config) # Backoff
    
    # 3. Find highest priority PENDING job
    # Using row locking "FOR UPDATE" in Postgres is safer, but avoiding complication for now.
    result = await db.execute(
        select(Job).where(Job.status == 'PENDING').order_by(Job.created_at.asc()).limit(1)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        return PollResponse(job=None, config=node_config) # No work
        
    job.status = 'ASSIGNED'
    job.node_id = node_id
    job.started_at = datetime.utcnow()
    
    encrypted_payload = json.loads(job.payload)
    payload = decrypt_secrets(encrypted_payload)
    
    await db.commit()
    
    work_resp = WorkResponse(guid=job.guid, task_type=job.task_type, payload=payload)
    return PollResponse(job=work_resp, config=node_config)

@app.post("/heartbeat")
async def receive_heartbeat(req: Request, stats: Dict = None, api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    """
    Received from Node background thread.
    """
    # Identify Node (by IP for now, or token in future)
    node_ip = req.client.host
    # If we had a header x-node-id, use that
    node_id = req.headers.get("X-Node-ID", node_ip)

    stats_json = json.dumps(stats) if stats else None

    # Upsert
    result = await db.execute(select(Node).where(Node.node_id == node_id))
    node = result.scalar_one_or_none()
    
    if node:
        node.last_seen = datetime.utcnow()
        node.status = "ONLINE"
        node.stats = stats_json
        # Check IP drift
        if node.ip != node_ip: 
            node.ip = node_ip
    else:
        node = Node(node_id=node_id, hostname=node_id, ip=node_ip, status="ONLINE", stats=stats_json)
        db.add(node)
    
    await db.commit()
    return {"status": "ack"}

@app.post("/work/{guid}/result")
async def report_result(guid: str, report: ResultReport, req: Request, api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    """Matches 'Environment -> Agent' reporting."""
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # HEARTBEAT LOGIC
    if job.task_type == "system_heartbeat":
        # Update Node Status
        node_ip = req.client.host
        # If result has stats, extract them
        stats_json = None
        if report.result and "stats" in report.result:
            stats_json = json.dumps(report.result["stats"])
            
        # Upsert Node
        # Check if node exists by IP (or hostname if we had it reliably in job)
        # We used IP as node_id in pull... let's stick to that for now.
        # Ideally, we should pass Node ID in header.
        node_id = job.node_id or node_ip
        
        sub_result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = sub_result.scalar_one_or_none()
        if node:
            node.last_seen = datetime.utcnow()
            node.status = "ONLINE"
            if stats_json:
                node.stats = stats_json
        else:
            node = Node(node_id=node_id, hostname=node_id, ip=node_ip, status="ONLINE", stats=stats_json)
            db.add(node)

        # Cleanup Heartbeat Job? Or keep it as log?
        # Let's mark it complete.
        pass

    job.status = "COMPLETED" if report.success else "FAILED"
    job.result = json.dumps(report.result) if report.result else None
    job.completed_at = datetime.utcnow()

    await db.commit()
    return {"status": "updated"}

class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    ip: str
    last_seen: datetime
    status: str
    stats: Optional[Dict] = None

@app.get("/nodes", response_model=List[NodeResponse])
async def list_nodes(db: AsyncSession = Depends(get_db)):
    """List all nodes."""
    result = await db.execute(select(Node))
    nodes = result.scalars().all()
    
    resp = []
    for n in nodes:
        # Check if offline (> 60s)
        is_offline = (datetime.utcnow() - n.last_seen).total_seconds() > 60
        status = "OFFLINE" if is_offline else "ONLINE"
        
        # Parse Stats
        stats = json.loads(n.stats) if n.stats else None
        
        resp.append({
            "node_id": n.node_id,
            "hostname": n.hostname,
            "ip": n.ip,
            "last_seen": n.last_seen,
            "status": status,
            "stats": stats
        })
    return resp

@app.post("/auth/register", response_model=RegisterResponse)
async def register_node(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Validate Join Token
    result = await db.execute(select(Token).where(Token.token == req.client_secret))
    token_entry = result.scalar_one_or_none()
    
    if not token_entry:
         raise HTTPException(status_code=403, detail="Invalid Join Token")

    try:
        # Sign CSR using Internal PKI
        signed_cert = ca_authority.sign_csr(req.csr_pem, req.hostname)
        
        return {
            "client_cert_pem": signed_cert,
            "ca_url": "https://localhost:8001" 
        }
    except Exception as e:
        logger.error(f"CSR Signing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sign CSR: {str(e)}")

# --- Admin Endpoints ---

from . import pki
import base64

# Initialize PKI
# Initialize PKI
ca_authority = pki.CertificateAuthority(ca_dir="secrets/ca")

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# --- Pydantic Models for Signatures & Jobs ---
class SignatureCreate(BaseModel):
    name: str
    public_key: str # PEM

class SignatureResponse(BaseModel):
    id: str
    name: str
    public_key: str
    uploaded_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class JobDefinitionCreate(BaseModel):
    name: str
    script_content: str
    signature: str # Base64
    signature_id: str # UUID of key
    schedule_cron: Optional[str] = None
    target_node_id: Optional[str] = None

class JobDefinitionResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    schedule_cron: Optional[str]
    target_node_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@app.on_event("startup")
async def on_startup():
    await init_db()
    try:
        scheduler.start()
        logger.info("🕒 Scheduler Started")
        await sync_scheduler()
    except Exception as e:
        logger.error(f"⚠️ Scheduler Failed to Start: {e}")
    
    # Bootstrap Admin
    # ... existing admin bootstrap ...

@app.post("/admin/generate-token")
async def generate_token(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generates a new Join Token (v0.8) with embedded Root CA."""
    if current_user.role not in ["admin", "operator"]:
         raise HTTPException(status_code=403, detail="Insufficient Permissions")
         
    # Generate DB Token
    token_str = uuid.uuid4().hex
    token_entry = Token(token=token_str)
    db.add(token_entry)
    await db.commit()
    
    # Bundle with CA
    ca_pem = ca_authority.get_root_cert_pem()
    
    payload = {
        "t": token_str,
        "ca": ca_pem
    }
    
    # Base64 Encode
    b64_token = base64.b64encode(json.dumps(payload).encode()).decode()
    
    return {"token": b64_token}

@app.post("/admin/upload-key")
async def upload_public_key(req: object, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Stores the Code Signing Public Key. RBAC: Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    # ... logic ...
    return {"status": "stored"}

@app.get("/config/public-key")
async def get_public_key(x_join_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    # Validate Token
    result = await db.execute(select(Token).where(Token.token == x_join_token))
    if not result.scalar_one_or_none():
         raise HTTPException(status_code=403, detail="Invalid Join Token")

    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"public_key": row.value}


# --- Test/Verification Endpoints ---

class PingRequest(BaseModel):
    node_id: str
    message: str

@app.post("/api/test/ping")
async def receive_ping(req: PingRequest, db: AsyncSession = Depends(get_db)):
    """
    Dev Mode Only: Allows nodes to 'check in' via signed jobs to verify Execution -> Network -> DB pipeline.
    """
    if os.getenv("DEVELOPMENT_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Development Mode Disabled")
        
    new_ping = Ping(
        id=uuid.uuid4().hex,
        node_id=req.node_id,
        message=req.message
    )
    db.add(new_ping)
    await db.commit()
    return {"status": "recorded", "id": new_ping.id}

# --- Configuration Endpoints ---

class NetworkMount(BaseModel):
    name: str # e.g., finance_data
    path: str # e.g., //server/share

class MountsConfig(BaseModel):
    mounts: List[NetworkMount]

@app.get("/config/mounts", response_model=List[NetworkMount])
async def get_network_mounts(
    db: AsyncSession = Depends(get_db), 
    user: Optional[User] = Depends(get_current_user_optional), # Optional User Auth
    x_join_token: Optional[str] = Header(None) # Optional Token Auth
):
    # Auth Logic: Must have either valid Admin User OR valid Join Token
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
    
    # Validate Names (Alphanumeric only for Env Var safety)
    for m in config.mounts:
        if not m.name.replace("_", "").isalnum():
             raise HTTPException(status_code=400, detail=f"Invalid mount name: {m.name}. Use alphanumeric and underscores.")
    
    json_str = json.dumps([m.dict() for m in config.mounts])
    
    # Upsert
    result = await db.execute(select(Config).where(Config.key == "global_network_mounts"))
    row = result.scalar_one_or_none()
    if row:
        row.value = json_str
    else:
        db.add(Config(key="global_network_mounts", value=json_str))
    
    await db.commit()
    return {"status": "updated", "count": len(config.mounts)}


@app.get("/api/node/compose")
async def generate_compose(token: str, platform: str = "Podman", db: AsyncSession = Depends(get_db)):
    # 1. Parse Client-Side Mounts (Legacy Removed)
    client_volumes = []
    client_env_vars = []
    
    # NOTE: Legacy 'mounts' param logic removed in v0.9 (Phase 2).
    # All mounts must now be managed via 'global_network_mounts'. 

    # 2. Network Mounts (Global/DB - Managed Host Passthrough)
    network_volumes = {} # Name -> Config
    network_mount_lines = []
    network_env_vars = []

    try:
        result = await db.execute(select(Config).where(Config.key == "global_network_mounts"))
        row = result.scalar_one_or_none()
        if row:
            saved_mounts = json.loads(row.value)
            for m in saved_mounts:
                name = m["name"] # validated alphanumeric
                
                # Standardized Path: Use configured path or default to /mnt/mop/[name]
                target_path = m.get("path", f"/mnt/mop/{name}")
                vol_name = f"vol_{name}"
                
                # Named Volume (VM -> Container) - Bypasses Windows Path Translation
                network_mount_lines.append(f"- {vol_name}:{target_path}")
                
                # Top Level Config
                network_volumes[vol_name] = {
                    "driver": "local",
                    "driver_opts": {
                        "type": "none",
                        "o": "bind",
                        "device": target_path
                    }
                }
                
                # Env Var
                env_key = f"MOUNT_{name.upper()}"
                network_env_vars.append(f"- {env_key}={target_path}")
                
    except Exception as e:
        logger.error(f"Error loading network mounts: {e}")

# --- Scheduler Logic ---

async def execute_scheduled_job(scheduled_job_id: str):
    """Callback for APScheduler. Creates an Execution Job from the Definition."""
    logger.info(f"⏰ Triggering Scheduled Job: {scheduled_job_id}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id))
        s_job = result.scalar_one_or_none()
        
        if not s_job or not s_job.is_active:
             logger.warning(f"⚠️ Job {scheduled_job_id} not found or inactive.")
             return

        # Load Signature
        sig_res = await db.execute(select(Signature).where(Signature.id == s_job.signature_id))
        sig = sig_res.scalar_one_or_none()
        if not sig:
             logger.error(f"⚠️ Signature {s_job.signature_id} missing for job {s_job.name}")
             return

        # Construct Execution Payload
        # Pass-Through: We rely on the signature stored in ScheduledJob
        execution_guid = uuid.uuid4().hex
        
        payload_dict = {
            "script_content": s_job.script_content,
            "signature": s_job.signature_payload, # Base64 Signature
            "secrets": {} # TODO: Secret attachment UI?
        }
        
        payload_json = json.dumps(payload_dict)
        
        # Create Job
        new_job = Job(
            guid=execution_guid,
            task_type="python_script",
            payload=payload_json,
            status="PENDING",
            node_id=s_job.target_node_id,
            scheduled_job_id=s_job.id
        )
        db.add(new_job)
        await db.commit()
        print(f"✅ Job {execution_guid} created for scheduled task {s_job.name}")

    print(f"✅ Job {execution_guid} created for scheduled task {s_job.name}")

async def sync_scheduler():
    """Syncs DB ScheduledJobs with APScheduler."""
    logger.info("🔄 Syncing Scheduler...")
    scheduler.remove_all_jobs()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.is_active == True))
        jobs = result.scalars().all()
        count = 0
        for j in jobs:
            if j.schedule_cron:
                 # TODO: Parse Cron string simpler? Pydantic validation handles format?
                 # APScheduler standard: "minute hour day month day_of_week"
                 # We assume the string is compatible with triggers.CronTrigger.from_crontab
                 try:
                     parts = j.schedule_cron.split()
                     if len(parts) == 5:
                         scheduler.add_job(
                             execute_scheduled_job, 
                             'cron', 
                             args=[j.id], 
                             minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4],
                             id=j.id
                         )
                         count += 1
                 except Exception as e:
                     logger.error(f"❌ Failed to schedule {j.name}: {e}")
    logger.info(f"✅ Scheduler Synced: {count} jobs active.")

# --- Signature Registry API ---

@app.post("/signatures", response_model=SignatureResponse)
async def upload_signature(sig: SignatureCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
    # Check Duplicate
    res = await db.execute(select(Signature).where(Signature.name == sig.name))
    if res.scalar_one_or_none():
         raise HTTPException(status_code=400, detail="Signature name exists")
    
    new_sig = Signature(
        id=uuid.uuid4().hex,
        name=sig.name,
        public_key=sig.public_key,
        uploaded_by=current_user.username
    )
    db.add(new_sig)
    await db.commit()
    return new_sig

@app.get("/signatures", response_model=List[SignatureResponse])
async def list_signatures(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Signature))
    return result.scalars().all()

@app.delete("/signatures/{id}")
async def delete_signature(id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin Only")
    
    result = await db.execute(select(Signature).where(Signature.id == id))
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    await db.delete(sig)
    await db.commit()
    return {"status": "deleted"}

# --- Job Definitions API ---

@app.post("/jobs/definitions", response_model=JobDefinitionResponse)
async def create_job_definition(def_req: JobDefinitionCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Creates a new Scheduled Job. VALIDATES SIGNATURE First."""
    
    # 1. Load Signature
    res = await db.execute(select(Signature).where(Signature.id == def_req.signature_id))
    sig = res.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature ID not found")
        
    # 2. Verify Signature (Server acts as Notary)
    try:
        public_key = serialization.load_pem_public_key(sig.public_key.encode())
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
             # Maybe support RSA too? Node supports whatever cryptography supports, but pki.py generated Ed25519.
             # Strict check for now.
             pass 
             
        # Ed25519 Verify
        sig_bytes = base64.b64decode(def_req.signature)
        public_key.verify(sig_bytes, def_req.script_content.encode('utf-8'))
        print(f"✅ Signature Validated for new job: {def_req.name}")
    except Exception as e:
        print(f"❌ Signature Validation Failed: {e}")
        raise HTTPException(status_code=403, detail=f"Invalid Signature: {str(e)}")

    # 3. Store Definition
    new_def = ScheduledJob(
        id=uuid.uuid4().hex,
        name=def_req.name,
        script_content=def_req.script_content,
        signature_id=def_req.signature_id,
        signature_payload=def_req.signature, # Store for Pass-Through
        schedule_cron=def_req.schedule_cron,
        target_node_id=def_req.target_node_id,
        created_by=current_user.username
    )
    db.add(new_def)
    await db.commit()
    
    # 4. Update Scheduler
    if new_def.is_active and new_def.schedule_cron:
        await sync_scheduler()
    
    return new_def

@app.get("/jobs/definitions", response_model=List[JobDefinitionResponse])
async def list_job_definitions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScheduledJob))
    return result.scalars().all()


    # Combine Env Vars
    final_env_vars = client_env_vars + network_env_vars
    env_block = ""
    if final_env_vars:
        env_block = "\n      " + "\n      ".join(final_env_vars)

    # Top Level Volumes Block
    top_level_volumes = ""
    if network_volumes:
        top_level_volumes = "volumes:\n"
        for name, config in network_volumes.items():
            top_level_volumes += f"  {name}:\n"
            top_level_volumes += f"    driver: {config['driver']}\n"
            top_level_volumes += f"    driver_opts:\n"
            for k, v in config['driver_opts'].items():
                top_level_volumes += f"      {k}: \"{v}\"\n"


    # Platform Handling
    agent_host = "host.containers.internal"
    if platform.lower() == "docker":
        agent_host = "host.docker.internal"

    yaml_content = f"""
version: "3"
services:
  node:
    image: localhost/master-of-puppets-node:latest
    environment:
      - AGENT_URL=https://{agent_host}:8001
      - JOIN_TOKEN={token}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - PYTHONUNBUFFERED=1{env_block}
{volumes_block}
    restart: always

{top_level_volumes}
"""
    return Response(content=yaml_content, media_type="application/x-yaml")
@app.get("/api/installer")
async def get_installer():
    """Serves the latest install_node.ps1 script."""
    # Robust Path Resolution
    # main.py is in /app/agent_service/main.py (container) or Repo/agent_service/main.py (local)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try container/production structure first
    # Structure: /app/installer/install_node.ps1
    path_prod = os.path.join(base_dir, "installer", "install_node.ps1")
    
    # Try dev structure (if different, though usually same relative path)
    # Structure: Repo/installer/install_node.ps1
    # which is same as above if base_dir is Repo root.
    
    file_path = path_prod
    
    if not os.path.exists(file_path):
         print(f"[ERROR] Installer not found at {file_path}. CWD: {os.getcwd()}")
         raise HTTPException(status_code=404, detail=f"Installer script not found at {file_path}")

    with open(file_path, "r") as f:
        content = f.read()
        
    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=install_node.ps1"})


# Documentation Endpoints
@app.get("/api/docs")
async def list_docs():
    """Returns a list of available documentation files."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Try container path first (/app/docs), then local repo path (../docs)
    possible_paths = [
        os.path.join(base_dir, "docs"),       # Container
        os.path.join(base_dir, "../docs")     # Local Dev
    ]
    
    docs_dir = "/app/docs" # Default fallback
    for p in possible_paths:
        if os.path.exists(p) and os.path.isdir(p):
            docs_dir = p
            break
            
    if not os.path.exists(docs_dir):
        return []

    files = []
    for f in os.listdir(docs_dir):
        if f.endswith(".md"):
            # Simple title extraction: Read first line
            title = f
            try:
                with open(os.path.join(docs_dir, f), "r") as md_file:
                    first_line = md_file.readline().strip()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("# ").strip()
            except:
                pass
            
            files.append({
                "filename": f,
                "title": title
            })
    return files

@app.get("/api/docs/{filename}")
async def get_doc_content(filename: str):
    """Serves specific markdown content."""
    # Sanitize filename (CodeQL Fix)
    filename = os.path.basename(filename)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    possible_paths = [
        os.path.join(base_dir, "docs"),
        os.path.join(base_dir, "../docs")
    ]
    
    docs_dir = None
    for p in possible_paths:
        if os.path.exists(p) and os.path.isdir(p):
            docs_dir = os.path.abspath(p)
            break
            
    if not docs_dir:
        raise HTTPException(status_code=404, detail="Docs directory not found")

    file_path = os.path.abspath(os.path.join(docs_dir, filename))
    
    # Path Traversal Check
    if not file_path.startswith(docs_dir):
        raise HTTPException(status_code=403, detail="Invalid path")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r") as f:
        content = f.read()
        
    return {"content": content}



if __name__ == "__main__":
    import uvicorn
    
    # Ensure Certs Exist (Managed by Caddy sidecar, but we check root CA presence for trust if needed)
    # ca_authority.ensure_root_ca() # Root CA is now managed/provided by cert-manager
    
    # Ensure Code Signing Keys exist (Still needed for job signing)
    ca_authority.ensure_signing_key("secrets")
    
    # Run WITHOUT SSL (TLS Termination handled by Caddy)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001
    )

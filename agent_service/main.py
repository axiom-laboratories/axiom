from fastapi import FastAPI, HTTPException, Request, Depends, Header, status
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
from sqlalchemy.future import select
from sqlalchemy import update, desc, func
from .db import init_db, get_db, Job, Token, Config, User, Node, AsyncSession
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

load_dotenv()

app = FastAPI(title="Agent Service (v0.7)", description="Orchestrator with RBAC and Observability.")

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

API_KEY = os.getenv("API_KEY", "master-secret-key")
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

# --- Models (Pydantic) ---
class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0

class RegisterRequest(BaseModel):
    client_secret: str
    hostname: str

class RegisterResponse(BaseModel):
    enrollment_token: str
    ca_url: str
    fingerprint: str

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
                password_hash=get_password_hash("admin"), 
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            print("Bootstrapped Admin User")
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

@app.post("/work/pull", response_model=Optional[WorkResponse])
async def pull_work(request: Request, api_key: str = Depends(verify_api_key), db: AsyncSession = Depends(get_db)):
    """Called by Environment Nodes."""
    node_id = request.client.host 
    MAX_CONCURRENT_JOBS = 5 
    
    try:
        # Check active jobs count
        result = await db.execute(select(func.count(Job.guid)).where(Job.status == 'ASSIGNED'))
        active_count = result.scalar()
        
        if active_count >= MAX_CONCURRENT_JOBS:
            return None # Backoff
        
        # Find highest priority PENDING job
        # Using row locking "FOR UPDATE" in Postgres is safer, but avoiding complication for now.
        result = await db.execute(
            select(Job).where(Job.status == 'PENDING').order_by(Job.created_at.asc()).limit(1)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None # No work
            
        job.status = 'ASSIGNED'
        job.node_id = node_id
        job.started_at = datetime.utcnow()
        
        encrypted_payload = json.loads(job.payload)
        payload = decrypt_secrets(encrypted_payload)
        
        await db.commit()
        
        return {"guid": job.guid, "task_type": job.task_type, "payload": payload}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
         if req.client_secret != "enrollment-secret":
            raise HTTPException(status_code=403, detail="Invalid Join Token")

    # Generate CA Token using step cli
    passwrap = "secrets/ca_password.txt" 
    if os.name == 'nt':
         passwrap = "c:\\Development\\Repos\\master_of_puppets\\secrets\\ca_password.txt"

    try:
        STEP_EXE = "step" # Default linux/container
        if os.name == 'nt':
             STEP_EXE = r"C:\Users\thoma\AppData\Local\Microsoft\WinGet\Packages\Smallstep.step_Microsoft.Winget.Source_8wekyb3d8bbwe\step_0.28.7\bin\step.exe"

        cmd = [
            STEP_EXE, "ca", "token", req.hostname,
            "--ca-url", "https://localhost:9000",
            "--root", "ca/certs/root_ca.crt" if os.name != 'nt' else "c:\\Development\\Repos\\master_of_puppets\\ca\\certs\\root_ca.crt",
            "--provisioner-password-file", passwrap
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        enrollment_token = result.stdout.strip()
        
        return {
            "enrollment_token": enrollment_token,
            "ca_url": "https://localhost:9000",
            "fingerprint": "mock-fingerprint-if-needed" 
        }
    except Exception as e:
        print(f"Token Gen Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate CA token")

# --- Admin Endpoints ---

@app.post("/admin/generate-token")
async def generate_join_token(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generates a new Join Token for a Node. RBAC: Admin/Operator."""
    if current_user.role not in ["admin", "operator"]:
         raise HTTPException(status_code=403, detail="Insufficient Permissions")
         
    token = uuid.uuid4().hex
    new_token = Token(token=token)
    db.add(new_token)
    await db.commit()
    return {"token": token}

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
         if x_join_token != "enrollment-secret":
             raise HTTPException(status_code=403, detail="Invalid Join Token")

    result = await db.execute(select(Config).where(Config.key == "signing_public_key"))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"public_key": row.value}


@app.get("/installer/compose")
async def generate_compose(token: str, mounts: Optional[str] = None):
    # Logic same as before
    normalized_mounts = []
    if mounts:
        for m in mounts.split(","):
            if ":" in m:
                normalized_mounts.append(f"- {m}")
    
    mounts_yaml = "\n      ".join(normalized_mounts)
    volumes_block = f"    volumes:\n      {mounts_yaml}" if normalized_mounts else ""

    yaml_content = f"""
version: "3"
services:
  node:
    image: localhost/master-of-puppets-node:latest
    environment:
      - AGENT_URL=https://host.containers.internal:8001
      - JOIN_TOKEN={token}
      - PYTHONUNBUFFERED=1
    network_mode: host
{volumes_block}
    restart: always
"""
    from fastapi.responses import Response
    return Response(content=yaml_content, media_type="application/x-yaml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        ssl_keyfile="secrets/agent.key",
        ssl_certfile="secrets/agent.crt"
    )

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
import json
import os
import subprocess
from typing import Optional, List, Dict
from cryptography.fernet import Fernet

app = FastAPI(title="Agent Service", description="The Orchestrator. Manages state and assigns work.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_NAME = "X-API-KEY"
API_KEY = "master-secret-key" # Hardcoded for demo/dev, usually env var
# Encryption Key for Secrets (Hardcoded for demo longevity)
# Generated via Fernet.generate_key()
ENCRYPTION_KEY = b'wz72Q_M--s0lQk7P3t1z6k3lj1_s4_x7j9_q1_w2_e3=' 
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_secrets(payload: Dict) -> Dict:
    """Recursively encrypts values in 'secrets' dictionary."""
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
    """Recursively decrypts values in 'secrets' dictionary."""
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
    """Replaces secrets with redacted string."""
    if "secrets" in payload and isinstance(payload["secrets"], dict):
        new_payload = payload.copy()
        new_secrets = {}
        for k in payload["secrets"].keys():
            new_secrets[k] = "****** (Redacted)"
        new_payload["secrets"] = new_secrets
        return new_payload
    return payload

from fastapi import Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

DB_NAME = "jobs.db"

# --- Models ---
# --- Models ---
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

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict

class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool

# --- DB Helpers ---
def init_db():
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                guid TEXT PRIMARY KEY,
                task_type TEXT NOT NULL DEFAULT 'web_task',
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                payload TEXT NOT NULL,
                result TEXT,
                error_details TEXT,
                lineage_log TEXT,
                node_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

# --- Helpers ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def on_startup():
    init_db()

# --- Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "Agent Service"}

@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs():
    """For the Dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM jobs ORDER BY updated_at DESC LIMIT 50")
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            jobs.append({
                "guid": row["guid"],
                "status": row["status"],
                "payload": mask_secrets(json.loads(row["payload"])), # REDACT SECRETS FOR UI
                "result": json.loads(row["result"]) if row["result"] else None
            })
        return jobs
    finally:
        conn.close()

@app.post("/jobs", response_model=JobResponse)
async def create_job(job: JobCreate):
    """Received from Model Service."""
    guid = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Encrypt secrets before storing
        encrypted_payload = encrypt_secrets(job.payload)
        
        cursor.execute(
            "INSERT INTO jobs (guid, task_type, status, priority, payload, lineage_log) VALUES (?, ?, ?, ?, ?, ?)",
            (guid, job.task_type, "PENDING", job.priority, json.dumps(encrypted_payload), json.dumps([{"event": "CREATED", "timestamp": "now"}]))
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    
    return {"guid": guid, "status": "PENDING", "payload": encrypted_payload}

@app.post("/work/pull", response_model=Optional[WorkResponse])
async def pull_work(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Called by Environment Nodes.
    Authenticates node (TODO: checks headers) and returns a pending job.
    Uses 'Distributed Semaphores' logic (simplified here: just checks available pending jobs).
    """
    """
    Called by Environment Nodes.
    Authenticates node and returns a pending job.
    Uses 'Distributed Semaphores' logic: Checks active jobs count per task_type.
    """
    # 0. Auth check implicit via dependency in signature (to be added)
    node_id = request.client.host 
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Configuration for semaphores (Hardcoded for now, ideally in DB)
    MAX_CONCURRENT_JOBS = 5 
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # 1. Semaphore Check: Count currently ASSIGNED jobs
        # Ideally we'd group by task_type, but let's do global for simple resource balancing first.
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'ASSIGNED'")
        active_count = cursor.fetchone()[0]
        
        if active_count >= MAX_CONCURRENT_JOBS:
            conn.commit()
            return None # Backoff, too busy
        
        # 2. Find highest priority PENDING job
        cursor.execute(
            "SELECT guid, task_type, payload FROM jobs WHERE status = 'PENDING' ORDER BY priority DESC, created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()
        
        if not row:
            conn.commit()
            return None # No work
            
        guid = row["guid"]
        task_type = row["task_type"]
        encrypted_payload = json.loads(row["payload"])
        
        # Decrypt secrets before sending to node
        payload = decrypt_secrets(encrypted_payload)
        
        # 2. Assign to Node
        cursor.execute(
            "UPDATE jobs SET status = 'ASSIGNED', node_id = ?, updated_at = CURRENT_TIMESTAMP WHERE guid = ?",
            (node_id, guid)
        )
        
        # 3. Update Lineage
        # Note: Appending to JSON array in SQLite is a bit tricky, doing simple read-modify-write logic or just keeping it simple for now.
        # Ideally, we would append. For now, we rely on the state change.
        
        conn.commit()
        return {"guid": guid, "task_type": task_type, "payload": payload}
        
    except Exception as e:
        conn.rollback()
        # In a real system, we'd log this carefully
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.post("/work/{guid}/result")
async def report_result(guid: str, report: ResultReport, api_key: str = Depends(verify_api_key)):
    """Matches 'Environment -> Agent' reporting."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    status = "COMPLETED" if report.success else "FAILED"
    result_json = json.dumps(report.result) if report.result else None
    error_json = json.dumps(report.error_details) if report.error_details else None
    
    try:
        cursor.execute(
            "UPDATE jobs SET status = ?, result = ?, error_details = ?, updated_at = CURRENT_TIMESTAMP WHERE guid = ?",
            (status, result_json, error_json, guid)
        )
        conn.commit()
        return {"status": "updated"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/auth/register", response_model=RegisterResponse)
async def register_node(req: RegisterRequest):
    """
    Exchanges a shared client_secret for a one-time ACME enrollment token.
    """
    CLIENT_SECRET = "enrollment-secret" # In prod, env var
    CA_URL = "https://localhost:9000"
    FINGERPRINT = "e0f381106413972b99497fd576dbdec56a2f6af20f1fda415007de2f46efa444" 
    # TODO: Fetch fingerprint dynamically or from env
    
    if req.client_secret != CLIENT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Client Secret")
    
    # Generate Token via CLI
    # We assume 'step' is available or use full path. 
    # Since we know the path from earlier:
    STEP_EXE = r"C:\Users\thoma\AppData\Local\Microsoft\WinGet\Packages\Smallstep.step_Microsoft.Winget.Source_8wekyb3d8bbwe\step_0.28.7\bin\step.exe"
    
    try:
        # We need to run this command. Note: password file needed for provisioner?
        # Typically 'step ca token' prompts for password unless --password-file is used.
        # We reused 'ca_password.txt' for init, let's assume it's valid for the provisioner 'admin'.
        cmd = [
            STEP_EXE, "ca", "token", req.hostname,
            "--ca-url", CA_URL,
            "--root", "c:/Development/Repos/master_of_puppets/ca/certs/root_ca.crt",
            "--password-file", "c:/Development/Repos/master_of_puppets/ca_password.txt",
            "--provisioner", "admin" # Default from init
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env={**os.environ, "STEPPATH": "c:/Development/Repos/master_of_puppets/ca"})
        token = result.stdout.strip()
        
        return {
            "enrollment_token": token,
            "ca_url": CA_URL,
            "fingerprint": FINGERPRINT
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Step Error: {e.stderr}")
        raise HTTPException(status_code=500, detail="Failed to generate enrollment token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )

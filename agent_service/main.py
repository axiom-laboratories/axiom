from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
import json
import os
import subprocess
from typing import Optional, List, Dict

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
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

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
                "payload": json.loads(row["payload"]),
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
        cursor.execute(
            "INSERT INTO jobs (guid, status, priority, payload, lineage_log) VALUES (?, ?, ?, ?, ?)",
            (guid, "PENDING", job.priority, json.dumps(job.payload), json.dumps([{"event": "CREATED", "timestamp": "now"}]))
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    
    return {"guid": guid, "status": "PENDING"}

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
        payload = json.loads(row["payload"])
        
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

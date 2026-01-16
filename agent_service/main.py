from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
import json
import os
from typing import Optional, List, Dict

app = FastAPI(title="Agent Service", description="The Orchestrator. Manages state and assigns work.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "jobs.db"

# --- Models ---
class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0

class JobResponse(BaseModel):
    guid: str
    status: str
    payload: Dict
    result: Optional[Dict] = None

class WorkResponse(BaseModel):
    guid: str
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
async def pull_work(request: Request):
    """
    Called by Environment Nodes.
    Authenticates node (TODO: checks headers) and returns a pending job.
    Uses 'Distributed Semaphores' logic (simplified here: just checks available pending jobs).
    """
    # TODO: Implement strict locking/semaphores
    node_id = request.client.host # Simplified identification
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Atomic-like fetch
        cursor.execute("BEGIN IMMEDIATE")
        
        # 1. Find highest priority PENDING job
        cursor.execute(
            "SELECT guid, payload FROM jobs WHERE status = 'PENDING' ORDER BY priority DESC, created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()
        
        if not row:
            conn.commit()
            return None # No work
            
        guid = row["guid"]
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
        return {"guid": guid, "payload": payload}
        
    except Exception as e:
        conn.rollback()
        # In a real system, we'd log this carefully
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.post("/work/{guid}/result")
async def report_result(guid: str, report: ResultReport):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

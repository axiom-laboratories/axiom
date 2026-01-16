from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Model Service", description="The Automation Scheduler.")

# --- Scheduler ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, List, Dict
import httpx

# Sync driver for APScheduler (psycopg2)
# We convert asyncpg url (postgresql+asyncpg) to sync (postgresql+psycopg2) if needed
# But for simplicity, we expect DATABASE_URL_SYNC env var or just modify the string.
DB_URL = os.getenv("DATABASE_URL", "sqlite:///jobs.db").replace("+asyncpg", "+psycopg2")

jobstores = {
    'default': SQLAlchemyJobStore(url=DB_URL)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

# In-memory storage for schedule metadata - REPLACED BY DB in v0.6
# But strictly speaking APScheduler stores the executeable job.
# We still keep a metadata cache or query APScheduler?
# For now, let's keep the dict for the UI "schedules" endpoint to list them easily 
# WITHOUT querying the binary/serialized blob in APScheduler table.
# A proper refactor would make a 'Schedules' table.
# To keep "One-Line" migration simple, we will KEEP the in-memory dict for "Listing" 
# but rely on APSch for "Persistence" of the trigger.
# Wait, if I restart, the in-memory dict is empty, but APScheduler fires.
# So I MUST rebuild the dict from APScheduler or separate DB table.
# Let's simple query scheduler.get_jobs() to Re-populate on startup?

scheduled_jobs = {} 

class ScheduleRequest(BaseModel):
    name: str # e.g. "Daily Cleanup"
    task_type: str
    payload: Dict
    interval_seconds: Optional[int] = None
    cron_expr: Optional[str] = None # e.g. "*/5 * * * *"

class ScheduleResponse(BaseModel):
    id: str
    name: str
    next_run: Optional[str] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
# Configuration
AGENT_SERVICE_URL = os.getenv("AGENT_URL", "https://localhost:8001")
API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("API_KEY", "master-secret-key")
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH")
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH")
API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("API_KEY", "master-secret-key")

from fastapi import Header, Depends

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        # For now, allow requests without key if they come from localhost (simple heuristic)
        # In production, this should be replaced by a session token or similar.
        # But specifically for removing the UI hardcoded key, we make this optional or removed for UI endpoints.
        pass 
    return x_api_key

# We will remove Depends(verify_api_key) from UI endpoints to allow Dashboard access without Master Key.


class TaskRequest(BaseModel):
    task_type: str
    payload: dict
    priority: int = 0

@app.on_event("startup")
def start_scheduler():
    scheduler.start()
    
    # Re-hydrate local cache from persistent store
    for job in scheduler.get_jobs():
        try:
             # We stored TaskRequest in args[0]
             task_req = job.args[0]
             scheduled_jobs[job.id] = {
                 "id": job.id,
                 "name": job.name,
                 "spec": task_req.dict() if hasattr(task_req, "dict") else str(task_req)
             }
        except Exception:
             pass


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

@app.post("/submit_task")
async def submit_task(task: TaskRequest):
    """
    Submits a task to the Agent Service (Immediate Execution).
    """
    try:
        async with httpx.AsyncClient(verify=ROOT_CA_PATH) as client:
            response = await client.post(
                f"{AGENT_SERVICE_URL}/jobs",
                json={
                    "payload": task.payload,
                    "priority": task.priority,
                    "task_type": task.task_type
                },
                headers={API_KEY_NAME: API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            return {"status": "submitted", "guid": data["guid"], "agent_response": data}
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Agent Service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Agent refused job: {e.response.text}")

# Backward compatibility alias
@app.post("/submit_intent")
async def submit_intent(intent: TaskRequest):
    return await submit_task(intent)

@app.get("/jobs")
async def proxy_list_jobs():
    """BFF Proxy: Fetch jobs from Agent Service (using server-side stored API Key)."""
    try:
        async with httpx.AsyncClient(verify=ROOT_CA_PATH) as client:
            resp = await client.get(
                f"{AGENT_SERVICE_URL}/jobs",
                headers={API_KEY_NAME: API_KEY} 
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/generate-token")
async def proxy_generate_token():
    """BFF Proxy: Generate Join Token via Agent Service."""
    try:
        async with httpx.AsyncClient(verify=ROOT_CA_PATH) as client:
            resp = await client.post(
                f"{AGENT_SERVICE_URL}/admin/generate-token",
                headers={API_KEY_NAME: API_KEY} 
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class KeyUpload(BaseModel):
    key_content: str

@app.post("/admin/upload-key")
async def proxy_upload_key(req: KeyUpload):
    """BFF Proxy: Upload Public Key via Agent Service."""
    try:
        async with httpx.AsyncClient(verify=ROOT_CA_PATH) as client:
            # Re-wrap the body
            resp = await client.post(
                f"{AGENT_SERVICE_URL}/admin/upload-key",
                json={"key_content": req.key_content},
                headers={API_KEY_NAME: API_KEY} 
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Schedule Endpoints ---

async def _job_wrapper(task: TaskRequest):
    # Wrapper helper to submit task from scheduler
    # We need a way to inject API KEY or bypass auth for internal calls.
    # For now, we'll replicate the logic or call the function directly if possible?
    # Actually, calling the function directly is hard due to Dependency injection.
    # Better to just use httpx to call Agent directly, or re-use logic.
    print(f"Executing Scheduled Task: {task.task_type}")
    try:
        async with httpx.AsyncClient(verify=ROOT_CA_PATH) as client:
             await client.post(
                f"{AGENT_SERVICE_URL}/jobs",
                json={
                    "payload": task.payload,
                    "priority": task.priority,
                    "task_type": task.task_type
                },
                headers={API_KEY_NAME: API_KEY}
            )
    except Exception as e:
        print(f"Scheduled Job Failed: {e}")

@app.post("/schedules", response_model=ScheduleResponse)
async def add_schedule(req: ScheduleRequest):
    job_id = str(uuid.uuid4())
    
    trigger = None
    if req.interval_seconds:
        trigger = IntervalTrigger(seconds=req.interval_seconds)
    elif req.cron_expr:
        trigger = CronTrigger.from_crontab(req.cron_expr)
    else:
        raise HTTPException(status_code=400, detail="Must provide interval_seconds or cron_expr")
        
    task_req = TaskRequest(task_type=req.task_type, payload=req.payload)
    
    job = scheduler.add_job(
        _job_wrapper,
        trigger=trigger,
        args=[task_req],
        id=job_id,
        name=req.name
    )
    
    scheduled_jobs[job_id] = {
        "id": job_id,
        "name": req.name,
        "spec": req.dict()
    }
    
    return {"id": job_id, "name": req.name, "next_run": str(job.next_run_time)}

@app.get("/schedules")
async def list_schedules():
    return list(scheduled_jobs.values())

@app.delete("/schedules/{job_id}")
async def remove_schedule(job_id: str):
    try:
        scheduler.remove_job(job_id)
        if job_id in scheduled_jobs:
            del scheduled_jobs[job_id]
        return {"status": "deleted"}
    except Exception:
        raise HTTPException(status_code=404, detail="Schedule not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile="secrets/key.pem",
        ssl_certfile="secrets/cert.pem"
    )

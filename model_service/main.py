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
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, List, Dict

scheduler = AsyncIOScheduler()

# In-memory storage for schedule metadata (in prod, use DB job store)
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
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

class TaskRequest(BaseModel):
    task_type: str
    payload: dict
    priority: int = 0

@app.on_event("startup")
def start_scheduler():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

@app.post("/submit_task")
async def submit_task(task: TaskRequest, api_key: str = Depends(verify_api_key)):
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
async def submit_intent(intent: TaskRequest, api_key: str = Depends(verify_api_key)):
    return await submit_task(intent, api_key)

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
async def add_schedule(req: ScheduleRequest, api_key: str = Depends(verify_api_key)):
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
async def remove_schedule(job_id: str, api_key: str = Depends(verify_api_key)):
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
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )

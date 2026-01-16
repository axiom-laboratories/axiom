from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx
import os

app = FastAPI(title="Model Service", description="Defines the logic and intent (The What).")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8001")

class IntentRequest(BaseModel):
    task_type: str
    payload: dict
    priority: int = 0

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "Model Service"}

@app.post("/submit_intent")
async def submit_intent(intent: IntentRequest):
    """
    Submits a new intent (task) to the Agent Service.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AGENT_SERVICE_URL}/jobs",
                json={
                    "payload": intent.payload,
                    "priority": intent.priority,
                    "task_type": intent.task_type # Agent service might filter or route based on this
                }
            )
            response.raise_for_status()
            return {"status": "submitted", "agent_response": response.json()}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Agent Service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Agent refused job: {e.response.text}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

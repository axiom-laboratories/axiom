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
# Configuration
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "https://localhost:8001")
API_KEY_NAME = "X-API-KEY"
API_KEY = "master-secret-key" # Hardcoded for demo/dev

from fastapi import Header, Depends

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

class IntentRequest(BaseModel):
    task_type: str
    payload: dict
    priority: int = 0

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "Model Service"}

@app.post("/submit_intent")
async def submit_intent(intent: IntentRequest, api_key: str = Depends(verify_api_key)):
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
                },
                headers={API_KEY_NAME: API_KEY},
                verify=False # Self-signed certs for local dev
            )
            response.raise_for_status()
            return {"status": "submitted", "agent_response": response.json()}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Agent Service unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Agent refused job: {e.response.text}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )

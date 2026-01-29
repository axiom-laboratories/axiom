from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0
    target_tags: Optional[List[str]] = None

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
    duration_seconds: Optional[float] = None
    target_tags: Optional[List[str]] = None

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

class HeartbeatPayload(BaseModel):
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None

class NodeConfig(BaseModel):
    concurrency_limit: int
    job_memory_limit: str

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    config: NodeConfig

class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    ip: str
    last_seen: datetime
    status: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None

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
    target_tags: Optional[List[str]] = None

class JobDefinitionResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    schedule_cron: Optional[str]
    target_node_id: Optional[str]
    target_tags: Optional[List[str]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PingRequest(BaseModel):
    node_id: str
    message: str

class NetworkMount(BaseModel):
    name: str # e.g., finance_data
    path: str # e.g., //server/share

class MountsConfig(BaseModel):
    mounts: List[NetworkMount]

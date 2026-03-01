from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import json as _json

class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None

class RegisterRequest(BaseModel):
    client_secret: str
    hostname: str
    csr_pem: str

class RegisterResponse(BaseModel):
    client_cert_pem: str
    ca_url: str

class EnrollmentRequest(BaseModel):
    token: str
    hostname: str
    csr_pem: str
    machine_id: str
    node_secret_hash: str # Initial binding hash

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
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None

class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, str]] = None
    job_telemetry: Optional[Dict[str, Dict]] = None # guid -> metrics

class NodeConfig(BaseModel):
    concurrency_limit: int
    job_memory_limit: str
    job_cpu_limit: Optional[str] = None

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
    capabilities: Optional[Dict] = None
    concurrency_limit: Optional[int] = None
    job_memory_limit: Optional[str] = None
    stats_history: Optional[List[Dict]] = None

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
    capability_requirements: Optional[Dict[str, str]] = None

class JobDefinitionResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    schedule_cron: Optional[str]
    target_node_id: Optional[str]
    target_tags: Optional[List[str]] = None
    created_at: datetime

    @field_validator('target_tags', mode='before')
    @classmethod
    def deserialize_target_tags(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return v
        return v

    class Config:
        from_attributes = True

class UploadKeyRequest(BaseModel):
    key_content: str  # PEM public key

class PingRequest(BaseModel):
    node_id: str
    message: str

class NetworkMount(BaseModel):
    name: str # e.g., finance_data
    path: str # e.g., //server/share

class MountsConfig(BaseModel):
    mounts: List[NetworkMount]

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    created_at: datetime

class PermissionGrant(BaseModel):
    permission: str

class ImageBuildRequest(BaseModel):
    tag: str
    capabilities: Dict[str, str]

class ImageResponse(BaseModel):
    tag: str
    image_uri: str
    status: str
    created_at: datetime

class BlueprintCreate(BaseModel):
    type: str # RUNTIME, NETWORK
    name: str
    definition: Dict

class BlueprintResponse(BaseModel):
    id: str
    type: str
    name: str
    definition: Dict
    version: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CapabilityMatrixEntry(BaseModel):
    base_os_family: str
    tool_id: str
    injection_recipe: str
    validation_cmd: str

class PuppetTemplateCreate(BaseModel):
    friendly_name: str
    runtime_blueprint_id: str
    network_blueprint_id: str

class PuppetTemplateResponse(BaseModel):
    id: str
    friendly_name: str
    runtime_blueprint_id: str
    network_blueprint_id: str
    canonical_id: str
    current_image_uri: Optional[str] = None
    last_built_image: Optional[str] = None
    last_built_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

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
    must_change_password: bool = False

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
    script_content: str
    signature_id: str
    signature_payload: str
    is_active: bool
    schedule_cron: Optional[str]
    target_node_id: Optional[str]
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator('target_tags', mode='before')
    @classmethod
    def deserialize_target_tags(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return v
        return v

    @field_validator('capability_requirements', mode='before')
    @classmethod
    def deserialize_capability_requirements(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return v
        return v

    class Config:
        from_attributes = True


class JobDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    script_content: Optional[str] = None
    signature: Optional[str] = None
    signature_id: Optional[str] = None
    schedule_cron: Optional[str] = None
    target_node_id: Optional[str] = None
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None

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

ALLOWED_ROLES = {"admin", "operator", "viewer"}

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v

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


# --- User Signing Keys ---

class UserSigningKeyCreate(BaseModel):
    name: str
    public_key_pem: Optional[str] = None  # Omit to auto-generate keypair

class UserSigningKeyResponse(BaseModel):
    id: str
    name: str
    public_key_pem: str
    created_at: datetime
    class Config:
        from_attributes = True

class UserSigningKeyGeneratedResponse(UserSigningKeyResponse):
    """Only returned when server generates the keypair."""
    private_key_pem: str  # Shown ONCE — user must save it


# --- User API Keys ---

class UserApiKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None

class UserApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True

class UserApiKeyCreatedResponse(UserApiKeyResponse):
    """Only returned at creation time."""
    raw_key: str  # Shown ONCE


# --- Service Principals ---

class ServicePrincipalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    role: str = "operator"
    expires_in_days: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
        return v

class ServicePrincipalResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    role: str
    client_id: str
    is_active: bool
    created_by: str
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ServicePrincipalCreatedResponse(ServicePrincipalResponse):
    client_secret: str  # Raw secret — shown ONCE

class ServicePrincipalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class ServicePrincipalTokenRequest(BaseModel):
    client_id: str
    client_secret: str

class ServicePrincipalRotateResponse(BaseModel):
    client_id: str
    client_secret: str  # New raw secret — shown ONCE

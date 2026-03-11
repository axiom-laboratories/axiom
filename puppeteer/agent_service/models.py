from pydantic import BaseModel, field_validator, model_validator
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
    depends_on: Optional[List[str]] = None
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None

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
    depends_on: Optional[List[str]] = None

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None

class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool
    output_log: Optional[List[Dict[str, str]]] = None  # [{t, stream, line}, ...]
    exit_code: Optional[int] = None
    security_rejected: bool = False
    retriable: Optional[bool] = None  # None = non-retriable (default); True = retry eligible

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    must_change_password: bool = False

class EnrollmentTokenCreate(BaseModel):
    template_id: Optional[str] = None

class TriggerCreate(BaseModel):
    slug: str
    name: str
    job_definition_id: str
    is_active: bool = True

class TriggerResponse(BaseModel):
    id: str
    slug: str
    name: str
    job_definition_id: str
    secret_token: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TriggerUpdate(BaseModel):
    is_active: Optional[bool] = None
    name: Optional[str] = None

class SignalFire(BaseModel):
    payload: Optional[Dict] = None

class SignalResponse(BaseModel):
    name: str
    payload: Optional[Dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, str]] = None
    job_telemetry: Optional[Dict[str, Dict]] = None # guid -> metrics
    upgrade_result: Optional[Dict] = None # status, output, error

class NodeConfig(BaseModel):
    concurrency_limit: int
    job_memory_limit: str
    job_cpu_limit: Optional[str] = None
    tags: Optional[List[str]] = None

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    config: NodeConfig

class WebhookCreate(BaseModel):
    url: str
    events: Optional[str] = "*" # comma separated or * for all

class WebhookResponse(BaseModel):
    id: int
    url: str
    events: str
    active: bool
    created_at: datetime
    secret: str # Only returned on creation or for admins

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    type: str
    severity: str
    message: str
    resource_id: Optional[str]
    created_at: datetime
    acknowledged: bool
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]

    class Config:
        from_attributes = True

class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    ip: str
    last_seen: datetime
    status: str
    base_os_family: Optional[str] = None
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict] = None
    expected_capabilities: Optional[Dict] = None
    tamper_details: Optional[str] = None
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
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None

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
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None

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
    max_retries: Optional[int] = None
    backoff_multiplier: Optional[float] = None
    timeout_minutes: Optional[int] = None

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
    type: str  # RUNTIME, NETWORK
    name: str
    definition: Dict
    os_family: Optional[str] = None          # required for RUNTIME, ignored for NETWORK
    confirmed_deps: Optional[List[str]] = None  # dep-confirmation resubmit

    @field_validator('os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v):
        return v.upper() if isinstance(v, str) else v

    @model_validator(mode='after')
    def runtime_requires_os_family(self):
        if self.type == 'RUNTIME' and not self.os_family:
            raise ValueError("os_family is required for RUNTIME blueprints")
        return self

class BlueprintResponse(BaseModel):
    id: str
    type: str
    name: str
    definition: Dict
    version: int
    created_at: datetime
    os_family: Optional[str] = None  # nullable — network blueprints have no os_family

    class Config:
        from_attributes = True

class CapabilityMatrixEntry(BaseModel):
    id: Optional[int] = None
    base_os_family: str
    tool_id: str
    injection_recipe: str
    validation_cmd: str
    artifact_id: Optional[str] = None
    runtime_dependencies: List[str] = []
    is_active: bool = True

    @field_validator('runtime_dependencies', mode='before')
    @classmethod
    def deserialize_runtime_deps(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return []
        return v

    @field_validator('base_os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v

    class Config:
        from_attributes = True


class CapabilityMatrixUpdate(BaseModel):
    base_os_family: Optional[str] = None
    tool_id: Optional[str] = None
    injection_recipe: Optional[str] = None
    validation_cmd: Optional[str] = None
    artifact_id: Optional[str] = None
    runtime_dependencies: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator('base_os_family', mode='before')
    @classmethod
    def normalize_os(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v

class ArtifactResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    sha256: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovedOSResponse(BaseModel):
    id: int
    name: str
    image_uri: str
    os_family: str

    class Config:
        from_attributes = True

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


# --- Output Capture ---

class ExecutionRecordResponse(BaseModel):
    id: int
    job_guid: str
    node_id: Optional[str] = None
    status: str
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_log: List[Dict[str, str]] = []
    truncated: bool = False
    duration_seconds: Optional[float] = None

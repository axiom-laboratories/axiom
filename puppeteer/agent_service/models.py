from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import json as _json

class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None
    depends_on: Optional[List[str]] = None
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    scheduled_job_id: Optional[str] = None
    env_tag: Optional[str] = None
    runtime: Optional[Literal["python", "bash", "powershell"]] = None
    name: Optional[str] = None          # SRCH-04: optional job name label
    created_by: Optional[str] = None    # SRCH-03: submitter username

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None

    @model_validator(mode="after")
    def validate_task_type_and_runtime(self):
        if self.task_type == "python_script":
            raise ValueError(
                "task_type 'python_script' is no longer supported. "
                "Use task_type='script' with runtime='python'."
            )
        if self.task_type == "script" and self.runtime is None:
            raise ValueError("runtime is required when task_type is 'script'")
        return self

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
    task_type: Optional[str] = None
    display_type: Optional[str] = None
    name: Optional[str] = None          # SRCH-04: nullable job name
    created_by: Optional[str] = None    # SRCH-03: submitter username
    created_at: Optional[datetime] = None  # needed for cursor encoding in list response
    runtime: Optional[str] = None       # SRCH-03: runtime filter display
    originating_guid: Optional[str] = None  # JOB-05: set when job was created via resubmit

class PaginatedJobResponse(BaseModel):
    """Cursor-based paginated job list response (Phase 49 — SRCH-01)."""
    items: List[JobResponse]
    total: int
    next_cursor: Optional[str] = None  # base64-encoded {created_at, guid}; None = no more pages

class BulkJobActionRequest(BaseModel):
    """Request body for bulk job operations (Phase 51 — JOB-05/BULK-02/03/04)."""
    guids: List[str]

class BulkDiagnosisRequest(BaseModel):
    """Request body for bulk dispatch diagnosis (Phase 88 — DIAG-01)."""
    guids: List[str]

class BulkActionResponse(BaseModel):
    """Response for bulk job operations."""
    processed: int
    skipped: int
    skipped_guids: List[str]

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    started_at: Optional[datetime] = None

class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool
    output_log: Optional[List[Dict[str, str]]] = None  # [{t, stream, line}, ...]
    exit_code: Optional[int] = None
    security_rejected: bool = False
    retriable: Optional[bool] = None  # None = non-retriable (default); True = retry eligible
    script_hash: Optional[str] = None
    attestation_bundle: Optional[str] = None    # base64(bundle JSON bytes)
    attestation_signature: Optional[str] = None # base64(RSA signature bytes)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class EnrollmentTokenCreate(BaseModel):
    template_id: Optional[str] = None

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
    env_tag: Optional[str] = None

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    env_tag: Optional[str] = None

class NodeUpdateRequest(BaseModel):
    tags: Optional[List[str]] = None
    env_tag: Optional[str] = None

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
    stats_history: Optional[List[Dict]] = None
    env_tag: Optional[str] = None

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
    env_tag: Optional[str] = None
    runtime: Optional[Literal["python", "bash", "powershell"]] = None

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None

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
    status: str = "ACTIVE"
    pushed_by: Optional[str] = None
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    env_tag: Optional[str] = None
    runtime: Optional[str] = None

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
    status: Optional[str] = None
    env_tag: Optional[str] = None
    runtime: Optional[Literal["python", "bash", "powershell"]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        valid = {"DRAFT", "ACTIVE", "DEPRECATED", "REVOKED"}
        if v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}, got '{v}'")
        return v

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None

class JobPushRequest(BaseModel):
    name: Optional[str] = None   # for create (name-based upsert)
    id: Optional[str] = None     # for update (id-based upsert)
    script_content: str
    signature: str               # Base64 Ed25519 signature
    signature_id: str            # UUID of registered public key

    @model_validator(mode='after')
    def require_name_or_id(self):
        if not self.name and not self.id:
            raise ValueError("Either 'name' or 'id' is required")
        return self

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
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    script_hash: Optional[str] = None
    hash_mismatch: Optional[bool] = None
    attempt_number: Optional[int] = None
    job_run_id: Optional[str] = None
    attestation_verified: Optional[str] = None
    max_retries: Optional[int] = None


class AttestationExportResponse(BaseModel):
    bundle_b64: str
    signature_b64: str
    cert_serial: Optional[str] = None
    node_id: Optional[str] = None
    attestation_verified: Optional[str] = None


# --- CI/CD Dispatch (Phase 31) ---

class DispatchRequest(BaseModel):
    job_definition_id: str
    env_tag: Optional[str] = None
    max_retries: Optional[int] = None
    timeout_minutes: Optional[int] = None

    @field_validator("env_tag", mode="before")
    @classmethod
    def normalize_env_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None


class DispatchResponse(BaseModel):
    job_guid: str
    status: str
    job_definition_id: str
    job_definition_name: str
    env_tag: Optional[str] = None
    poll_url: str


class DispatchStatusResponse(BaseModel):
    job_guid: str
    status: str
    exit_code: Optional[int] = None
    node_id: Optional[str] = None
    attempt: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_terminal: bool


# --- Job Templates (SRCH-06, SRCH-07) ---

SIGNING_FIELDS = {"signature_id", "signature_payload", "signature_hmac"}


class JobTemplateCreate(BaseModel):
    name: str
    visibility: str = "private"  # "private" | "shared"
    payload: Dict  # all job fields; signing state stripped server-side


class JobTemplateResponse(BaseModel):
    id: str
    name: str
    creator_id: str
    visibility: str
    payload: Dict
    created_at: datetime

    model_config = {"from_attributes": True}


class JobTemplateUpdate(BaseModel):
    name: Optional[str] = None
    visibility: Optional[str] = None


# --- Retention Config (SRCH-08) ---

class RetentionConfigUpdate(BaseModel):
    retention_days: int


# --- Scheduling Health (VIS-05, VIS-06) ---

class DefinitionHealthRow(BaseModel):
    id: str
    name: str
    fired: int
    skipped: int
    failed: int
    missed: int
    health: str  # "ok" | "warning" | "error"


class SchedulingHealthResponse(BaseModel):
    window: str
    aggregate: Dict[str, int]  # {fired, skipped, failed, late, missed}
    definitions: List[DefinitionHealthRow]


# --- Scale Health (OBS-01) ---

class ScaleHealthResponse(BaseModel):
    is_postgres: bool
    pool_size: Optional[int]
    checked_out: Optional[int]
    available: Optional[int]
    overflow: Optional[int]
    apscheduler_jobs: int
    pending_job_depth: int

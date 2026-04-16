from pydantic import BaseModel, field_validator, model_validator, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal, TypeVar, Generic
from datetime import datetime
import json as _json
import re

# TypeVar for generic PaginatedResponse
T = TypeVar("T")


class ActionResponse(BaseModel):
    """Standardized response model for action endpoints (acknowledge, cancel, revoke, approve, delete, update, create, enable, disable)."""
    status: Literal["acknowledged", "cancelled", "revoked", "approved", "deleted", "updated", "created", "enabled", "disabled"] = Field(
        description="Action status, Literal union catches typos at dev time"
    )
    resource_type: str = Field(description="Type of resource actioned (e.g., 'job', 'node', 'signature')")
    resource_id: str | int = Field(description="ID of the actioned resource")
    message: Optional[str] = Field(None, description="Optional detail message about the action")

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model for list endpoints."""
    items: List[T] = Field(
        description="Array of items in this page",
        json_schema_extra={"examples": [[]]}
    )
    total: int = Field(description="Total count of all items across all pages")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    detail: str = Field(description="Error message describing what went wrong")
    status_code: int = Field(description="HTTP status code")

    model_config = ConfigDict(from_attributes=True)

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
    memory_limit: Optional[str] = None  # e.g., "512m", "1g", "1Gi"
    cpu_limit: Optional[str] = None     # e.g., "2", "0.5"
    target_node_id: Optional[str] = None  # Explicit node targeting

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

    @field_validator("memory_limit", mode="before")
    @classmethod
    def validate_memory_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip()
        # Light validation: digits + optional decimal + unit (k/m/g/t, case-insensitive)
        # Matches Docker memory format and Kubernetes Ki/Mi/Gi conventions
        if not re.match(r'^\d+(\.\d+)?[kmKmgGtT][iIbB]?[bB]?$', v_str):
            raise ValueError(f"Invalid memory format: {v}. Use format like '512m', '1g', '1Gi'")
        return v_str

    @field_validator("cpu_limit", mode="before")
    @classmethod
    def validate_cpu_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip()
        # Light validation: digits with optional decimal point (matches Docker --cpus format)
        if not re.match(r'^\d+(\.\d+)?$', v_str):
            raise ValueError(f"Invalid CPU format: {v}. Use format like '2', '0.5'")
        return v_str

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
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None

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


class JobCountResponse(BaseModel):
    """Response for job count endpoint (Phase 129 — Response Model Auto-Serialization)."""
    total: int = Field(description="Total number of jobs matching filter criteria")

    model_config = ConfigDict(from_attributes=True)


class JobStatsResponse(BaseModel):
    """Response for job stats endpoint (Phase 129 — Response Model Auto-Serialization)."""
    counts: Dict[str, int] = Field(description="Job count by status")
    success_rate: float = Field(description="Percentage of completed jobs that succeeded (0-100)")
    total_jobs: int = Field(description="Total number of jobs")

    model_config = ConfigDict(from_attributes=True)


class DispatchDiagnosisResponse(BaseModel):
    """Response for dispatch diagnosis endpoint (Phase 129)."""
    reason: Optional[str] = Field(None, description="Why job hasn't dispatched (e.g., 'no_eligible_nodes', 'capability_mismatch')")
    message: Optional[str] = Field(None, description="Human-readable explanation")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional diagnostic data")

    model_config = ConfigDict(from_attributes=True)


class BulkDispatchDiagnosisResponse(BaseModel):
    """Response for bulk dispatch diagnosis endpoint (Phase 129)."""
    results: Dict[str, Dict[str, Any]] = Field(description="Diagnosis results keyed by job GUID")

    model_config = ConfigDict(from_attributes=True)

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    started_at: Optional[datetime] = None
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None

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
    must_change_password: bool = False

    model_config = ConfigDict(from_attributes=True)


class DeviceCodeResponse(BaseModel):
    """Response for RFC 8628 Device Authorization Request (POST /auth/device)."""
    device_code: str = Field(description="Device code for token polling")
    user_code: str = Field(description="User-friendly code for approval page")
    verification_uri: str = Field(description="URL for user to visit for approval")
    verification_uri_complete: Optional[str] = Field(None, description="Verification URL with user_code pre-filled")
    expires_in: int = Field(description="Device code TTL in seconds")
    interval: int = Field(description="Minimum polling interval in seconds")

    model_config = ConfigDict(from_attributes=True)


class EnrollmentTokenResponse(BaseModel):
    """Response for enrollment token creation (POST /admin/generate-token)."""
    token: str = Field(description="Base64-encoded enrollment token containing token_string and CA PEM")

    model_config = ConfigDict(from_attributes=True)


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
    detected_cgroup_version: Optional[str] = None  # NEW: "v1", "v2", "unsupported"
    cgroup_raw: Optional[str] = None                # NEW: raw detection info for debugging
    execution_mode: Optional[str] = None             # NEW: Phase 124 - reported runtime (docker/podman)

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
    detected_cgroup_version: Optional[str] = None  # NEW: Phase 127 dashboard
    execution_mode: Optional[str] = None             # NEW: Phase 124 - reported runtime (docker/podman)

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


# --- System / Config Response Models ---

class SystemHealthResponse(BaseModel):
    """Response model for GET /system/health."""
    status: str = Field(description="Overall health status (healthy/degraded/unhealthy)")
    mirrors_available: bool = Field(description="Whether package mirrors are available")

    model_config = ConfigDict(from_attributes=True)


class FeaturesResponse(BaseModel):
    """Response model for GET /api/features."""
    audit: bool = Field(description="Audit logging feature enabled")
    foundry: bool = Field(description="Foundry template builder enabled")
    webhooks: bool = Field(description="Webhook support enabled")
    triggers: bool = Field(description="Job triggers enabled")
    rbac: bool = Field(description="Role-based access control enabled")
    resource_limits: bool = Field(description="Resource limit enforcement enabled")
    service_principals: bool = Field(description="Service principals support enabled")
    api_keys: bool = Field(description="API keys support enabled")
    executions: bool = Field(description="Execution attestation enabled")

    model_config = ConfigDict(from_attributes=True)


class LicenceStatusResponse(BaseModel):
    """Response model for GET /api/licence."""
    status: str = Field(description="Licence status (ce/valid/grace/expired)")
    days_until_expiry: int = Field(description="Days until licence expires")
    node_limit: int = Field(description="Maximum number of nodes allowed")
    tier: str = Field(description="Licence tier (ce/ee)")
    customer_id: Optional[str] = Field(None, description="Customer ID for EE licence")
    grace_days: int = Field(description="Grace period days")

    model_config = ConfigDict(from_attributes=True)


class NetworkMount(BaseModel):
    """Response model for GET /config/mounts."""
    id: Optional[str] = Field(None, description="Mount identifier")
    source: str = Field(description="Source path on host")
    target: str = Field(description="Target path in container")
    readonly: bool = Field(default=False, description="Whether mount is read-only")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# --- Foundry / EE Pydantic Models ---

class BlueprintCreate(BaseModel):
    type: str  # RUNTIME, NETWORK
    name: str
    definition: Dict
    os_family: Optional[str] = None
    confirmed_deps: Optional[List[str]] = None

    @field_validator('os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v):
        return v.upper() if isinstance(v, str) else v


class BlueprintResponse(BaseModel):
    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    definition: Dict
    version: int = 1
    created_at: Optional[datetime] = None
    os_family: Optional[str] = None

    model_config = {"from_attributes": True}


class BlueprintUpdate(BaseModel):
    """Partial update for blueprint edit with optimistic locking."""
    name: Optional[str] = None
    definition: Optional[Dict] = None
    os_family: Optional[str] = None
    confirmed_deps: Optional[List[str]] = None
    version: int  # REQUIRED for optimistic locking

    @field_validator('os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v):
        return v.upper() if isinstance(v, str) else v


class PuppetTemplateCreate(BaseModel):
    friendly_name: str
    runtime_blueprint_id: str
    network_blueprint_id: str


class PuppetTemplateResponse(BaseModel):
    id: str
    friendly_name: Optional[str] = None
    runtime_blueprint_id: Optional[str] = None
    network_blueprint_id: Optional[str] = None
    canonical_id: Optional[str] = None
    current_image_uri: Optional[str] = None
    last_built_image: Optional[str] = None
    last_built_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_compliant: Optional[bool] = True
    status: Optional[str] = "DRAFT"
    bom_captured: Optional[bool] = False

    model_config = {"from_attributes": True}


class ImageBuildRequest(BaseModel):
    template_id: Optional[str] = None
    base_os: Optional[str] = None
    packages: Optional[Dict] = None


class ImageResponse(BaseModel):
    image_uri: Optional[str] = None
    status: str = "PENDING"
    build_log: Optional[str] = None


class CapabilityMatrixEntry(BaseModel):
    id: Optional[int] = None
    base_os_family: str
    tool_id: str
    injection_recipe: Optional[str] = None
    validation_cmd: Optional[str] = None
    artifact_id: Optional[str] = None
    runtime_dependencies: Optional[List[str]] = None
    is_active: Optional[bool] = True

    model_config = {"from_attributes": True}


class CapabilityMatrixUpdate(BaseModel):
    base_os_family: Optional[str] = None
    tool_id: Optional[str] = None
    injection_recipe: Optional[str] = None
    validation_cmd: Optional[str] = None
    artifact_id: Optional[str] = None
    runtime_dependencies: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ImageBOMResponse(BaseModel):
    id: int
    template_id: str
    packages: Optional[str] = None
    layers: Optional[str] = None
    captured_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PackageIndexResponse(BaseModel):
    id: int
    name: str
    version: Optional[str] = None
    template_id: Optional[str] = None
    image_uri: Optional[str] = None

    model_config = {"from_attributes": True}


class ApprovedOSResponse(BaseModel):
    id: Optional[int] = None
    name: str
    image_uri: str
    os_family: str
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovedOSCreate(BaseModel):
    """Create a new approved OS entry."""
    name: str
    image_uri: str
    os_family: str


class ApprovedOSUpdate(BaseModel):
    """Partial update for approved OS edit."""
    name: Optional[str] = None
    image_uri: Optional[str] = None
    os_family: Optional[str] = None


class ApprovedIngredientCreate(BaseModel):
    name: str
    version_constraint: Optional[str] = "*"
    sha256: Optional[str] = None
    os_family: str = "DEBIAN"
    ecosystem: str = "PYPI"


class ApprovedIngredientResponse(BaseModel):
    id: str
    name: str
    version_constraint: Optional[str] = None
    sha256: Optional[str] = None
    os_family: str
    ecosystem: str = "PYPI"
    is_active: bool = True
    is_vulnerable: Optional[bool] = False
    vulnerability_report: Optional[str] = None
    mirror_status: Optional[str] = "PENDING"
    mirror_path: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovedIngredientUpdate(BaseModel):
    name: Optional[str] = None
    version_constraint: Optional[str] = None
    os_family: Optional[str] = None
    ecosystem: Optional[str] = None


class MirrorConfigUpdate(BaseModel):
    pypi_mirror_url: Optional[str] = None
    apt_mirror_url: Optional[str] = None
    apk_mirror_url: Optional[str] = None
    npm_mirror_url: Optional[str] = None
    nuget_mirror_url: Optional[str] = None
    oci_hub_mirror_url: Optional[str] = None
    oci_ghcr_mirror_url: Optional[str] = None
    conda_mirror_url: Optional[str] = None

    @field_validator('pypi_mirror_url', 'apt_mirror_url', 'apk_mirror_url',
                     'npm_mirror_url', 'nuget_mirror_url', 'oci_hub_mirror_url',
                     'oci_ghcr_mirror_url', 'conda_mirror_url', mode='before')
    @classmethod
    def validate_mirror_url(cls, v):
        """Validate that mirror URL is a valid HTTP/HTTPS URL if provided."""
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError(f"Mirror URL must start with http:// or https://: {v}")
            return v
        raise ValueError(f"Mirror URL must be a string: {v}")


class MirrorConfigResponse(BaseModel):
    pypi_mirror_url: str
    apt_mirror_url: str
    apk_mirror_url: str
    npm_mirror_url: str
    nuget_mirror_url: str
    oci_hub_mirror_url: str
    oci_ghcr_mirror_url: str
    conda_mirror_url: str
    health_status: Dict[str, str]  # { "pypi": "ok", "apt": "ok", ..., "conda": "ok" }
    provisioning_enabled: bool  # True if ALLOW_CONTAINER_MANAGEMENT env var == "true"
    conda_defaults_acknowledged_by_current_user: bool = False  # True if user has acknowledged Conda defaults ToS


# --- User Management (EE) ---

ALLOWED_ROLES = {"admin", "operator", "viewer"}


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class UserResponse(BaseModel):
    id: Optional[str] = None
    username: str
    role: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PermissionGrant(BaseModel):
    permission: str


# --- Signing Keys (EE) ---

class UserSigningKeyCreate(BaseModel):
    name: str
    public_key_pem: Optional[str] = None


class UserSigningKeyResponse(BaseModel):
    id: str
    name: str
    public_key_pem: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserSigningKeyGeneratedResponse(BaseModel):
    id: str
    name: str
    public_key_pem: str
    private_key_pem: str
    created_at: Optional[datetime] = None


# --- API Keys (EE) ---

class UserApiKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None


class UserApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    raw_key: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# --- Service Principals (EE) ---

class ServicePrincipalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    role: str = "operator"
    expires_in_days: Optional[int] = None


class ServicePrincipalResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    role: str
    client_id: str
    is_active: bool = True
    created_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ServicePrincipalCreatedResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    role: str
    client_id: str
    client_secret: str
    is_active: bool = True
    created_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


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
    client_secret: str


# --- Webhooks (EE) ---

class WebhookCreate(BaseModel):
    url: str
    events: List[str] = []


class WebhookResponse(BaseModel):
    id: Optional[int] = None
    url: str
    events: Optional[str] = None
    secret: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Triggers (EE) ---

class TriggerCreate(BaseModel):
    name: str
    slug: str
    job_definition_id: str


class TriggerResponse(BaseModel):
    id: Optional[str] = None
    name: str
    slug: str
    job_definition_id: Optional[str] = None
    token: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TriggerUpdate(BaseModel):
    is_active: Optional[bool] = None


# --- Licence Management (EE) (Phase 116) ---

class LicenceReloadRequest(BaseModel):
    """Request to hot-reload a licence key without restarting the server."""
    licence_key: Optional[str] = None  # Override licence key from request body


class LicenceReloadResponse(BaseModel):
    """Response after successful licence reload."""
    status: str  # VALID, GRACE, EXPIRED, CE
    tier: str    # ee or ce
    customer_id: Optional[str]
    node_limit: int
    grace_days: int
    days_until_expiry: int
    features: List[str]
    is_ee_active: bool
    message: str = "Licence reloaded successfully"

    model_config = {"from_attributes": True}


# --- Transitive CVE Scanning & Dependency Tree (Phase 110) ---

class CVEDetail(BaseModel):
    """Vulnerability detail from pip-audit with provenance information."""
    cve_id: str
    cvss_score: Optional[float] = None
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    description: str
    fix_versions: List[str] = []
    affected_package: str
    is_transitive: bool = True
    provenance_path: List[str] = []  # Chain from root to vulnerable package

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        if v not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            return "HIGH"  # Default to HIGH if invalid
        return v


class DependencyTreeNode(BaseModel):
    """Recursive tree node for dependency visualization."""
    id: str  # UUID of the ingredient
    name: str
    version: str
    ecosystem: str
    cve_count: int  # Total CVEs (top-level + transitive)
    worst_severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]] = None
    auto_discovered: bool
    mirror_status: str  # PENDING/MIRRORED/FAILED
    children: List["DependencyTreeNode"] = []
    cves: List[CVEDetail] = []  # Only vulnerable deps show this

    @field_validator("worst_severity", mode="before")
    @classmethod
    def validate_worst_severity(cls, v):
        if v is None:
            return None
        if v not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            return "HIGH"
        return v


# Update model config to allow forward references
DependencyTreeNode.model_rebuild()


class DependencyTreeResponse(BaseModel):
    """Full dependency tree response with CVE aggregates."""
    root_id: str
    root_name: str
    root_version: str
    total_nodes: int
    total_cve_count: int
    worst_severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]] = None
    tree: DependencyTreeNode


class DiscoverDependenciesRequest(BaseModel):
    """Request to discover and resolve all transitive dependencies."""
    approve_all: bool = True  # Auto-approve all discovered transitive deps


class DiscoverDependenciesResponse(BaseModel):
    """Response from dependency discovery trigger."""
    ingredient_id: str
    discovered_count: int  # Number of newly-discovered transitive deps
    tree: DependencyTreeResponse
    toast_message: str  # e.g., "Flask: 6 deps resolved, 1 CVE found"


# Script Analyzer Models (Phase 113)

class AnalyzeScriptRequest(BaseModel):
    """Request to analyze a script for package dependencies."""
    script_content: str
    language: Optional[str] = None  # Optional override: python, bash, powershell


class AnalyzedPackage(BaseModel):
    """A single package extracted from script analysis."""
    import_name: str
    package_name: str
    ecosystem: str
    mapped: Optional[bool] = False  # True if import_name != package_name


class AnalyzeScriptResponse(BaseModel):
    """Response from script analysis endpoint."""
    detected_language: str
    suggestions: List[AnalyzedPackage]
    approved: List[str]  # package_names that are already approved
    pending_review: List[str]  # package_names requiring approval


class ScriptAnalysisRequestResponse(BaseModel):
    """Response model for a ScriptAnalysisRequest."""
    id: str
    requester_id: str
    package_name: str
    ecosystem: str
    detected_import: str
    source_script_hash: str
    status: str  # PENDING, APPROVED, REJECTED
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_reason: Optional[str] = None


class ScriptAnalysisRequestCreate(BaseModel):
    """Request to create a script analysis request for approval."""
    package_name: str
    ecosystem: str
    detected_import: str
    source_script: str  # Full script text (will be hashed)


class ScriptAnalysisApprovalRequest(BaseModel):
    """Request to approve or reject a script analysis request."""
    reason: Optional[str] = None  # Approval/rejection reason


# ==================== Curated Bundles (Phase 114) ====================

class CuratedBundleItemCreate(BaseModel):
    """Create/update a package item in a curated bundle."""
    ingredient_name: str
    version_constraint: str = "*"
    ecosystem: str  # PYPI, APT, APK, CONDA, NUGET, OCI, NPM


class CuratedBundleItemResponse(CuratedBundleItemCreate):
    """Response for a curated bundle item."""
    id: int
    bundle_id: str

    model_config = {"from_attributes": True}


class CuratedBundleCreate(BaseModel):
    """Create/update a curated bundle."""
    name: str
    description: Optional[str] = None
    ecosystem: str  # Primary ecosystem (e.g., PYPI)
    os_family: str  # DEBIAN, ALPINE, WINDOWS


class CuratedBundleResponse(CuratedBundleCreate):
    """Response for a curated bundle with items."""
    id: str
    is_active: bool
    created_at: datetime
    items: list[CuratedBundleItemResponse] = []

    model_config = {"from_attributes": True}


class ApplyBundleResult(BaseModel):
    """Result of applying a curated bundle (bulk-approval)."""
    bundle_id: str
    bundle_name: str
    approved: int  # Count of newly approved ingredients
    skipped: int   # Count of already-approved ingredients (silently skipped)
    total: int     # approved + skipped


# --- Workflow Models (Phase 146) ---

class WorkflowStepCreate(BaseModel):
    """Create request for a workflow step."""
    scheduled_job_id: Optional[str] = None  # Gate nodes have NULL scheduled_job_id
    node_type: str  # "SCRIPT", "IF_GATE", etc.
    config_json: Optional[str] = None  # JSON as string

    model_config = ConfigDict(from_attributes=True)


class WorkflowStepResponse(BaseModel):
    """Response model for a workflow step."""
    id: str
    workflow_id: str
    scheduled_job_id: Optional[str]  # Gate nodes have NULL scheduled_job_id
    node_type: str
    config_json: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowEdgeCreate(BaseModel):
    """Create request for a workflow edge."""
    from_step_id: str
    to_step_id: str
    branch_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowEdgeResponse(BaseModel):
    """Response model for a workflow edge."""
    id: str
    workflow_id: str
    from_step_id: str
    to_step_id: str
    branch_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowParameterCreate(BaseModel):
    """Create request for a workflow parameter."""
    name: str
    type: str  # "string", "int", "bool"
    default_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowParameterResponse(BaseModel):
    """Response model for a workflow parameter."""
    id: str
    workflow_id: str
    name: str
    type: str
    default_value: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowCreate(BaseModel):
    """Create request for a workflow."""
    name: str
    steps: List[WorkflowStepCreate]
    edges: List[WorkflowEdgeCreate]
    parameters: List[WorkflowParameterCreate] = []
    schedule_cron: Optional[str] = None  # Phase 149: Cron expression for scheduling

    model_config = ConfigDict(from_attributes=True)


class WorkflowUpdate(BaseModel):
    """Update request for a workflow (all fields optional)."""
    name: Optional[str] = None
    steps: Optional[List[WorkflowStepCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None
    parameters: Optional[List[WorkflowParameterCreate]] = None
    schedule_cron: Optional[str] = None  # Phase 149: Can enable/disable cron scheduling
    is_paused: Optional[bool] = None  # Phase 149: Gate for cron activation

    model_config = ConfigDict(from_attributes=True)


class WorkflowResponse(BaseModel):
    """Response model for a workflow with full graph."""
    id: str
    name: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_paused: bool
    schedule_cron: Optional[str] = None  # Phase 149: Cron expression; fires when schedule_cron IS NOT NULL AND is_paused = false
    step_count: int  # Computed
    last_run_status: Optional[str]  # Computed from workflow_runs
    steps: List[WorkflowStepResponse]
    edges: List[WorkflowEdgeResponse]
    parameters: List[WorkflowParameterResponse]

    model_config = ConfigDict(from_attributes=True)


class WorkflowValidationError(BaseModel):
    """Validation error response for workflow DAG validation."""
    error: str  # "CYCLE_DETECTED", "DEPTH_LIMIT_EXCEEDED", "INVALID_EDGE_REFERENCE"
    detail: Optional[str] = None
    cycle_path: Optional[List[str]] = None  # For CYCLE_DETECTED
    max_depth: Optional[int] = None  # For DEPTH_LIMIT_EXCEEDED
    actual_depth: Optional[int] = None
    edge: Optional[Dict[str, str]] = None  # For INVALID_EDGE_REFERENCE

    model_config = ConfigDict(from_attributes=True)


# --- WorkflowRun Execution Models (Phase 147) ---

class WorkflowStepRunCreate(BaseModel):
    """Create request for a workflow step run."""
    workflow_run_id: str
    workflow_step_id: str
    status: str = "PENDING"

    model_config = ConfigDict(from_attributes=True)


class WorkflowStepRunResponse(BaseModel):
    """Response model for a workflow step run."""
    id: str
    workflow_run_id: str
    workflow_step_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_json: Optional[str] = None  # JSON-serialized output from step execution
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunResponse(BaseModel):
    """Response model for a workflow run with step execution status."""
    id: str
    workflow_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trigger_type: Optional[str] = None  # Phase 149: MANUAL, CRON, WEBHOOK
    triggered_by: Optional[str] = None  # Phase 149: username, "scheduler", or webhook_name
    parameters_json: Optional[str] = None  # Phase 149: Resolved parameters as JSON string at run creation
    created_at: datetime
    step_runs: List[WorkflowStepRunResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Workflow Webhook Models (Phase 149) ---

class WorkflowWebhookCreate(BaseModel):
    """Create request for a workflow webhook."""
    name: str  # Human label, e.g., "github-push"
    # secret NOT in request; generated server-side and returned only once

    model_config = ConfigDict(from_attributes=True)


class WorkflowWebhookResponse(BaseModel):
    """Response model for a workflow webhook."""
    id: str
    workflow_id: str
    name: str
    secret: Optional[str] = None  # Present ONLY in creation response (201); None in GET
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Workflow WebSocket Event Models (Phase 150) ---

class WorkflowRunUpdatedEvent(BaseModel):
    """Event emitted when a WorkflowRun transitions state."""
    id: str  # WorkflowRun ID
    workflow_id: str
    status: Literal['RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED']
    started_at: datetime
    completed_at: Optional[datetime]
    triggered_by: Literal['step_completed', 'cascade_cancel', 'manual_cancel', 'all_steps_done']

    model_config = ConfigDict(from_attributes=True)


class WorkflowStepUpdatedEvent(BaseModel):
    """Event emitted when a WorkflowStepRun transitions state."""
    id: str  # WorkflowStepRun ID
    workflow_run_id: str
    workflow_step_id: str
    status: Literal['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', 'CANCELLED']
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    job_guid: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunListResponse(BaseModel):
    """Paginated list of runs for a workflow."""
    runs: List[WorkflowRunResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


# --- Unified Schedule Models (Phase 154) ---

class ScheduleEntryResponse(BaseModel):
    """Single entry in unified schedule (ScheduledJob or Workflow with cron)."""
    id: str
    type: Literal["JOB", "FLOW"]
    name: str
    next_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleListResponse(BaseModel):
    """Response for GET /api/schedule: unified list of scheduled jobs and workflows."""
    entries: List[ScheduleEntryResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)

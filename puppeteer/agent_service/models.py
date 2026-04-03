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
    must_change_password: bool = False

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

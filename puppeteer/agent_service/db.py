import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, LargeBinary, UniqueConstraint, ForeignKey, Index
from datetime import datetime
import json
import logging
from typing import Optional, List
from uuid import uuid4

logger = logging.getLogger(__name__)

# Import cipher_suite for Vault secret encryption (D-05)
from .security import cipher_suite

# Database URL (Default to Postgres, fallback to SQLite for local dev if needed)
# In Docker, this will be: postgresql+asyncpg://user:pass@db/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")
IS_POSTGRES: bool = DATABASE_URL.startswith("postgresql")

# Connection pool configuration — Postgres only (SQLite uses StaticPool, kwargs unsupported)
_pool_kwargs: dict = {}
if IS_POSTGRES:
    _pool_kwargs = {
        "pool_size": int(os.getenv("ASYNCPG_POOL_SIZE", "20")),
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

engine = create_async_engine(DATABASE_URL, echo=False, **_pool_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"

    guid: Mapped[str] = mapped_column(String, primary_key=True)
    task_type: Mapped[str] = mapped_column(String) # script, web_task, file_download
    payload: Mapped[str] = mapped_column(Text) # JSON string
    status: Mapped[str] = mapped_column(String, default="PENDING")
    node_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # FK to ScheduledJob.id
    target_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of tags required
    capability_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON dict of required capabilities
    telemetry: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string: per-job metrics
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
    timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    depends_on: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of GUIDs
    job_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    signature_hmac: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SEC-02: HMAC-SHA256 tag
    runtime: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # RT-07: python, bash, powershell
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)        # SRCH-04: operator-assigned job name
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # SRCH-03: submitter username
    originating_guid: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JOB-05: resubmit traceability
    target_node_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # VIS-04: explicit node targeting
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Phase 53
    memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "512m", "1g", "1Gi"
    cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)     # e.g., "2", "0.5"
    workflow_step_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # FK to workflow_step_runs.id (Phase 147)
    depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Nesting depth for ENGINE-02 override
    use_vault_secrets: Mapped[bool] = mapped_column(Boolean, default=False)  # Phase 167-02: Vault secret resolution enabled
    vault_secrets: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Phase 167-02: JSON list of secret names

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )


class Signature(Base):
    __tablename__ = "signatures"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    name: Mapped[str] = mapped_column(String, unique=True)
    public_key: Mapped[str] = mapped_column(Text) # PEM
    uploaded_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    name: Mapped[str] = mapped_column(String, unique=True)
    script_content: Mapped[str] = mapped_column(Text)
    signature_id: Mapped[str] = mapped_column(String) # FK to Signature.id
    signature_payload: Mapped[str] = mapped_column(Text) # Base64 Signature
    schedule_cron: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Cron Expression
    target_node_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # specific node
    target_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of tags e.g. ["gpu", "secure"]
    capability_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON dict of required capabilities
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    pushed_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
    timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "512m", "1Gi"
    cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)      # e.g., "0.5", "2"
    env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    runtime: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="python")  # RT-07
    allow_overlap: Mapped[bool] = mapped_column(Boolean, default=False)  # SRCH-08: default safe — no concurrent runs
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Phase 53


class VaultConfig(Base):
    """Vault integration configuration (EE only). Per D-05.

    Stored in DB for runtime editability without restart.
    secret_id is Fernet-encrypted at rest (same cipher as ENCRYPTION_KEY).
    Env var bootstrap (VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID) seeds this on first boot.
    """
    __tablename__ = "vault_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    vault_address: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_id: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted at rest
    mount_path: Mapped[str] = mapped_column(String(255), default="secret", nullable=False)
    namespace: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Vault Enterprise
    provider_type: Mapped[str] = mapped_column(String(32), default="vault", nullable=False)  # D-15: future extensibility
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Token(Base):
    __tablename__ = "tokens"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    template_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Affinity for enrollment

class Config(Base):
    __tablename__ = "config"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class User(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String, primary_key=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="admin", server_default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

class Node(Base):
    __tablename__ = "nodes"
    node_id: Mapped[str] = mapped_column(String, primary_key=True) # Likely hostname or uuid
    hostname: Mapped[str] = mapped_column(String)
    ip: Mapped[str] = mapped_column(String)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String) # ONLINE, OFFLINE, TAMPERED
    base_os_family: Mapped[Optional[str]] = mapped_column(String, nullable=True) # DEBIAN, ALPINE
    stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON: cpu, ram
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of tags e.g. ["linux", "prod"]
    operator_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of operator-assigned tags
    capabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON map of capabilities
    expected_capabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON map of authorized capabilities
    tamper_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Description of breach
    pending_upgrade: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON upgrade task
    upgrade_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of past upgrades
    machine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Host-bound ID
    node_secret_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Binding secret
    client_cert_pem: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Stored at enrollment for CRL
    template_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    operator_env_tag: Mapped[bool] = mapped_column(Boolean, default=False)
    job_memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "512m", "1Gi" (default: 512m)
    job_cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)      # e.g., "0.5", "2" (default: unlimited)
    detected_cgroup_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NEW: "v1", "v2", "unsupported"
    cgroup_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                  # NEW: raw detection info
    execution_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)            # NEW: Phase 124 - reported runtime (docker/podman)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False) # job_failure, node_offline, security_tamper
    severity: Mapped[str] = mapped_column(String, nullable=False) # INFO, WARNING, CRITICAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # job_guid or node_id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class RevokedCert(Base):
    __tablename__ = "revoked_certs"
    serial_number: Mapped[str] = mapped_column(String, primary_key=True)
    node_id: Mapped[str] = mapped_column(String, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NodeStats(Base):
    __tablename__ = "node_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cpu: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class ExecutionRecord(Base):
    __tablename__ = "execution_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_guid: Mapped[str] = mapped_column(String, nullable=False)
    node_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    output_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hash_mismatch: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    attempt_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    job_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    attestation_bundle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attestation_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attestation_verified: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)  # SRCH-09: user-pinned execution record

    __table_args__ = (
        Index("ix_execution_records_job_guid", "job_guid"),
        Index("ix_execution_records_started_at", started_at.desc()),
        Index("ix_execution_records_node_started", "node_id", started_at.desc()),
        Index("ix_execution_records_job_started", "job_guid", started_at.desc()),
    )


class ScheduledFireLog(Base):
    __tablename__ = "scheduled_fire_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheduled_job_id: Mapped[str] = mapped_column(String, nullable=False)
    expected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default='fired')
    # status values: fired | skipped_draft | skipped_overlap
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_fire_log_job_expected", "scheduled_job_id", "expected_at"),
    )


class JobTemplate(Base):
    __tablename__ = "job_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID hex
    name: Mapped[str] = mapped_column(String, nullable=False)
    creator_id: Mapped[str] = mapped_column(String, nullable=False)  # username
    visibility: Mapped[str] = mapped_column(String, nullable=False, default='private')  # private | shared
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON of all job fields, signing state excluded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Ping(Base):
    __tablename__ = "pings"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    node_id: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- EE Models (Foundry / Smelter) ---
# These are used by EE routers and services. They share the same Base so
# that create_all creates them alongside CE tables.


class Blueprint(Base):
    __tablename__ = "blueprints"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # RUNTIME, NETWORK
    name: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    os_family: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class PuppetTemplate(Base):
    __tablename__ = "puppet_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    friendly_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    runtime_blueprint_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    network_blueprint_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    canonical_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_image_uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_built_image: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_built_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_compliant: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # DRAFT, ACTIVE, DEPRECATED, REVOKED
    bom_captured: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    is_starter: Mapped[bool] = mapped_column(Boolean, default=False)  # Flag for starter template immutability


class CapabilityMatrix(Base):
    __tablename__ = "capability_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_os_family: Mapped[str] = mapped_column(String, nullable=False)
    tool_id: Mapped[str] = mapped_column(String, nullable=False)
    injection_recipe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_cmd: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    runtime_dependencies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ApprovedOS(Base):
    __tablename__ = "approved_os"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    image_uri: Mapped[str] = mapped_column(String, nullable=False)
    os_family: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApprovedIngredient(Base):
    __tablename__ = "approved_ingredients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_constraint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    os_family: Mapped[str] = mapped_column(String(50), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(20), default="PYPI", server_default="PYPI")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_vulnerable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    vulnerability_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mirror_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="PENDING")
    mirror_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mirror_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Phase 116: JSON log of mirror operations
    auto_discovered: Mapped[bool] = mapped_column(Boolean, default=False)  # Phase 108: True if discovered as transitive dep
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngredientDependency(Base):
    """Tracks transitive dependencies between approved ingredients (Phase 108)."""
    __tablename__ = "ingredient_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[str] = mapped_column(String(36), index=True)
    child_id: Mapped[str] = mapped_column(String(36), index=True)
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version_constraint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ecosystem: Mapped[str] = mapped_column(String(20), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ecosystem', name='uq_ingredient_dep'),
    )


class CuratedBundle(Base):
    """Pre-built package bundles for Phase 114 (curated bundles UX)."""
    __tablename__ = "curated_bundles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ecosystem: Mapped[str] = mapped_column(String(20), nullable=False)
    os_family: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    items: Mapped[list["CuratedBundleItem"]] = relationship("CuratedBundleItem", cascade="all, delete-orphan")


class CuratedBundleItem(Base):
    """Individual package in a curated bundle."""
    __tablename__ = "curated_bundle_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[str] = mapped_column(String(36), ForeignKey("curated_bundles.id", ondelete="CASCADE"), index=True)
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_constraint: Mapped[str] = mapped_column(String(255), default="*")
    ecosystem: Mapped[str] = mapped_column(String(20), nullable=False)  # PYPI, APT, APK, CONDA, NUGET, OCI, NPM


class ImageBOM(Base):
    """Bill of Materials for a built template image."""
    __tablename__ = "image_bom"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    packages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    layers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PackageIndex(Base):
    """Index of packages across all built images for fleet search."""
    __tablename__ = "package_index"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Trigger(Base):
    __tablename__ = "triggers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    job_definition_id: Mapped[str] = mapped_column(String, nullable=False)
    secret_token: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    permission: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint('role', 'permission', name='uq_role_permission'),
    )


class UserSigningKey(Base):
    __tablename__ = "user_signing_keys"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ServicePrincipal(Base):
    __tablename__ = "service_principals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScriptAnalysisRequest(Base):
    """Approval queue for script analysis (Phase 113)."""
    __tablename__ = "script_analysis_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    requester_id: Mapped[str] = mapped_column(String, nullable=False)  # FK to User.username
    package_name: Mapped[str] = mapped_column(String, nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(20), nullable=False)  # PYPI, APT, APK, OCI, NPM, CONDA, NUGET
    detected_import: Mapped[str] = mapped_column(String, nullable=False)  # Original import/command from script
    source_script_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 hash of script
    status: Mapped[str] = mapped_column(String(20), default="PENDING", server_default="PENDING")  # PENDING, APPROVED, REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # FK to User.username
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('requester_id', 'package_name', 'ecosystem', 'source_script_hash', name='uq_analysis_request'),
    )


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)  # Cron expression; activates only if is_paused=false

    # Relationships
    steps: Mapped[List["WorkflowStep"]] = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[List["WorkflowEdge"]] = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    parameters: Mapped[List["WorkflowParameter"]] = relationship("WorkflowParameter", back_populates="workflow", cascade="all, delete-orphan")
    webhooks: Mapped[List["WorkflowWebhook"]] = relationship("WorkflowWebhook", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    scheduled_job_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scheduled_jobs.id"), nullable=True)
    node_type: Mapped[str] = mapped_column(String)  # "SCRIPT", "IF_GATE", etc. — validated at service layer
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string, not blob

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")
    scheduled_job: Mapped["ScheduledJob"] = relationship("ScheduledJob")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    from_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    to_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    branch_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NULL = unconditional, non-null = IF gate branch

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")


class WorkflowParameter(Base):
    __tablename__ = "workflow_parameters"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # "string", "int", "bool" — validated at service layer
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="parameters")


class WorkflowWebhook(Base):
    __tablename__ = "workflow_webhooks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID, generated by endpoint
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))  # FK to Workflow
    name: Mapped[str] = mapped_column(String)  # Human label, e.g., "github-push"
    secret_hash: Mapped[str] = mapped_column(String)  # Bcrypt hash of plaintext secret (never expose plaintext again)
    secret_plaintext: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Fernet-encrypted plaintext for HMAC verification
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="webhooks")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    status: Mapped[str] = mapped_column(String)  # RUNNING, COMPLETED, PARTIAL, FAILED, CANCELLED — Phase 147
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trigger_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # MANUAL, CRON, WEBHOOK — Phase 149
    triggered_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # user ID or webhook name
    parameters_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Resolved parameters at run creation as JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    step_runs: Mapped[List["WorkflowStepRun"]] = relationship("WorkflowStepRun", back_populates="workflow_run")


class WorkflowStepRun(Base):
    __tablename__ = "workflow_step_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"))
    workflow_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    status: Mapped[str] = mapped_column(String)  # PENDING/RUNNING/COMPLETED/FAILED/SKIPPED/CANCELLED
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="step_runs")
    workflow_step: Mapped["WorkflowStep"] = relationship("WorkflowStep")


async def _bootstrap_vault_config():
    """Bootstrap VaultConfig from env vars if table is empty (D-05).

    Env vars: VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID
    Only creates row if:
    1. Table exists (metadata.create_all already ran)
    2. No VaultConfig row exists yet
    3. All three env vars are set

    Idempotent: running multiple times creates only one row.
    """
    from sqlalchemy import func

    vault_addr = os.getenv("VAULT_ADDRESS")
    vault_role_id = os.getenv("VAULT_ROLE_ID")
    vault_secret_id = os.getenv("VAULT_SECRET_ID")

    # If any env var missing, skip bootstrap (not configured)
    if not all([vault_addr, vault_role_id, vault_secret_id]):
        return

    async with AsyncSessionLocal() as session:
        # Check if VaultConfig row already exists
        stmt = select(func.count(VaultConfig.id))
        result = await session.execute(stmt)
        count = result.scalar() or 0

        if count > 0:
            logger.debug("VaultConfig already seeded; skipping env var bootstrap")
            return

        # Create new VaultConfig row with encrypted secret_id
        config = VaultConfig(
            id=str(uuid4()),
            vault_address=vault_addr,
            role_id=vault_role_id,
            secret_id=cipher_suite.encrypt(vault_secret_id.encode()).decode(),  # Fernet encrypt before storing
            mount_path="secret",  # Default per D-05
            namespace=os.getenv("VAULT_NAMESPACE"),  # Optional
            provider_type="vault",
            enabled=True  # Auto-enable if env vars present
        )
        session.add(config)
        await session.commit()
        logger.info("VaultConfig seeded from env vars (VAULT_ADDRESS, VAULT_ROLE_ID, VAULT_SECRET_ID)")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap VaultConfig from env vars if needed
    await _bootstrap_vault_config()

    # Seed default mirror config entries if they don't exist
    async with AsyncSessionLocal() as session:
        await seed_mirror_config(session)


async def seed_mirror_config(session: AsyncSession):
    """Seed Config table with default mirror URLs for all 8 ecosystems (if not already present)."""
    from sqlalchemy import select

    mirror_defaults = {
        "PYPI_MIRROR_URL": "http://pypi:8080/simple",
        "APT_MIRROR_URL": "http://mirror:80/apt",
        "APK_MIRROR_URL": "http://mirror:80/apk",
        "NPM_MIRROR_URL": "http://verdaccio:4873",
        "NUGET_MIRROR_URL": "http://bagetter:5555/v3/index.json",
        "OCI_HUB_MIRROR_URL": "http://oci-cache:5001",
        "OCI_GHCR_MIRROR_URL": "http://oci-cache-ghcr:5002",
        "CONDA_MIRROR_URL": "http://mirror:8081/conda",
    }

    # ENFC-04: Seed default job memory limit (used when job doesn't specify memory_limit)
    defaults = {
        **mirror_defaults,
        "default_job_memory_limit": "512m",
    }

    for key, default_value in defaults.items():
        result = await session.execute(select(Config).where(Config.key == key))
        existing = result.scalar_one_or_none()
        if not existing:
            session.add(Config(key=key, value=default_value))

    await session.commit()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def extend_schema():
    """Called by EE plugin to create EE tables."""
    pass

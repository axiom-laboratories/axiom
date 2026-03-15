import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, LargeBinary, UniqueConstraint, ForeignKey, Index
from datetime import datetime
import json
from typing import Optional
from uuid import uuid4

# Database URL (Default to Postgres, fallback to SQLite for local dev if needed)
# In Docker, this will be: postgresql+asyncpg://user:pass@db/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    
    guid: Mapped[str] = mapped_column(String, primary_key=True)
    task_type: Mapped[str] = mapped_column(String) # python_script, web_task
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
    memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. "300m", "2g"
    cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)     # e.g. "0.5", "2"
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
    timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    depends_on: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of GUIDs


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    role: Mapped[str] = mapped_column(String, nullable=False)
    permission: Mapped[str] = mapped_column(String, nullable=False)
    __table_args__ = (UniqueConstraint("role", "permission"),)


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
    role: Mapped[str] = mapped_column(String) # viewer, operator, admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

class UserSigningKey(Base):
    __tablename__ = "user_signing_keys"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String, ForeignKey("users.username"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String, ForeignKey("users.username"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ServicePrincipal(Base):
    __tablename__ = "service_principals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    client_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=5)
    job_memory_limit: Mapped[String] = mapped_column(String, default="512m")
    machine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Host-bound ID
    node_secret_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Binding secret
    client_cert_pem: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Stored at enrollment for CRL
    template_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("puppet_templates.id"), nullable=True)

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


class Webhook(Base):
    __tablename__ = "webhooks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    secret: Mapped[str] = mapped_column(String, nullable=False) # HMAC secret
    events: Mapped[str] = mapped_column(String, default="*") # comma separated: job:completed, alert:new, etc.
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_failure: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    username: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


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
    
    __table_args__ = (
        Index("ix_execution_records_job_guid", "job_guid"),
        Index("ix_execution_records_started_at", started_at.desc()),
        Index("ix_execution_records_node_started", "node_id", started_at.desc()),
        Index("ix_execution_records_job_started", "job_guid", started_at.desc()),
    )


class Blueprint(Base):
    __tablename__ = "blueprints"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    type: Mapped[str] = mapped_column(String) # RUNTIME, NETWORK
    name: Mapped[str] = mapped_column(String, unique=True)
    definition: Mapped[str] = mapped_column(Text) # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    os_family: Mapped[Optional[str]] = mapped_column(String, nullable=True) # DEBIAN, ALPINE — set on RUNTIME blueprints

class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ApprovedOS(Base):
    __tablename__ = "approved_os"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True) # e.g. Debian 12
    image_uri: Mapped[str] = mapped_column(String) # e.g. debian:12-slim
    os_family: Mapped[str] = mapped_column(String) # DEBIAN, ALPINE, etc.

class Trigger(Base):
    __tablename__ = "triggers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    slug: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    job_definition_id: Mapped[str] = mapped_column(String, ForeignKey("scheduled_jobs.id"))
    secret_token: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Signal(Base):
    __tablename__ = "signals"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CapabilityMatrix(Base):
    __tablename__ = "capability_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_os_family: Mapped[str] = mapped_column(String) # DEBIAN, ALPINE, etc.
    tool_id: Mapped[str] = mapped_column(String) # e.g., python-3.11
    injection_recipe: Mapped[str] = mapped_column(Text) # Dockerfile snippet
    validation_cmd: Mapped[str] = mapped_column(String)
    artifact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("artifacts.id"), nullable=True)
    runtime_dependencies: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

class PuppetTemplate(Base):
    __tablename__ = "puppet_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    friendly_name: Mapped[str] = mapped_column(String, unique=True)
    runtime_blueprint_id: Mapped[str] = mapped_column(String) # FK to blueprints.id
    network_blueprint_id: Mapped[str] = mapped_column(String) # FK to blueprints.id
    canonical_id: Mapped[str] = mapped_column(String) # Hash of ingredients
    current_image_uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_built_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", server_default="'DRAFT'")
    bom_captured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

class ImageBOM(Base):
    __tablename__ = "image_boms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("puppet_templates.id"))
    raw_data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PackageIndex(Base):
    __tablename__ = "package_index"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("puppet_templates.id"))
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    type: Mapped[str] = mapped_column(String(20)) # 'pip' or 'apt'

class Ping(Base):
    __tablename__ = "pings"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    node_id: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ApprovedIngredient(Base):
    __tablename__ = "approved_ingredients"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    version_constraint: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    os_family: Mapped[str] = mapped_column(String(50))
    is_vulnerable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    vulnerability_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON
    mirror_status: Mapped[str] = mapped_column(String(50), default="PENDING", server_default="'PENDING'")
    mirror_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mirror_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

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
    env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    runtime: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="python")  # RT-07
    allow_overlap: Mapped[bool] = mapped_column(Boolean, default=False)  # SRCH-08: default safe — no concurrent runs
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Phase 53

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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def extend_schema():
    """Called by EE plugin to create EE tables."""
    pass

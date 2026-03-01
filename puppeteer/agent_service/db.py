import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, LargeBinary, UniqueConstraint
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

class Token(Base):
    __tablename__ = "tokens"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

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

class Node(Base):
    __tablename__ = "nodes"
    node_id: Mapped[str] = mapped_column(String, primary_key=True) # Likely hostname or uuid
    hostname: Mapped[str] = mapped_column(String)
    ip: Mapped[str] = mapped_column(String)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String) # ONLINE, OFFLINE
    stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON: cpu, ram
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of tags e.g. ["linux", "prod"]
    capabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON dict of node capabilities
    concurrency_limit: Mapped[Integer] = mapped_column(Integer, default=5)
    job_memory_limit: Mapped[String] = mapped_column(String, default="512m")
    machine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Host-bound ID
    node_secret_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Binding secret
    client_cert_pem: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Stored at enrollment for CRL

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


class Blueprint(Base):
    __tablename__ = "blueprints"
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    type: Mapped[str] = mapped_column(String) # RUNTIME, NETWORK
    name: Mapped[str] = mapped_column(String, unique=True)
    definition: Mapped[str] = mapped_column(Text) # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CapabilityMatrix(Base):
    __tablename__ = "capability_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_os_family: Mapped[str] = mapped_column(String) # DEBIAN, ALPINE, etc.
    tool_id: Mapped[str] = mapped_column(String) # e.g., python-3.11
    injection_recipe: Mapped[str] = mapped_column(Text) # Dockerfile snippet
    validation_cmd: Mapped[str] = mapped_column(String)

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

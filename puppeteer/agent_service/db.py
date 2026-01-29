import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Boolean, DateTime, LargeBinary
from datetime import datetime
import json
from typing import Optional

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

class Node(Base):
    __tablename__ = "nodes"
    node_id: Mapped[str] = mapped_column(String, primary_key=True) # Likely hostname or uuid
    hostname: Mapped[str] = mapped_column(String)
    ip: Mapped[str] = mapped_column(String)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String) # ONLINE, OFFLINE
    stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON: cpu, ram
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of tags e.g. ["linux", "prod"]
    concurrency_limit: Mapped[Integer] = mapped_column(Integer, default=5)
    job_memory_limit: Mapped[String] = mapped_column(String, default="512m")

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

import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from agent_service.db import Base, User
from agent_service.auth import verify_password
from bootstrap_admin import bootstrap
from sqlalchemy import select

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_bootstrap_creates_admin():
    # Setup in-memory DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    # Patch the sessionmaker used in bootstrap
    with patch("bootstrap_admin.sessionmaker", return_value=AsyncSessionLocal), \
         patch("bootstrap_admin.create_async_engine", return_value=engine), \
         patch.dict(os.environ, {"ADMIN_PASSWORD": "testpassword"}):
        
        await bootstrap()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.username == "admin"))
            admin = result.scalar_one_or_none()
            assert admin is not None
            # role column is EE-only; not asserted in CE
            assert verify_password("testpassword", admin.password_hash)

@pytest.mark.anyio
async def test_bootstrap_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    # Pre-create admin
    async with AsyncSessionLocal() as session:
        session.add(User(username="admin", password_hash="existing"))
        await session.commit()

    with patch("bootstrap_admin.sessionmaker", return_value=AsyncSessionLocal), \
         patch("bootstrap_admin.create_async_engine", return_value=engine):
        
        await bootstrap()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.username == "admin"))
            admin = result.scalar_one_or_none()
            assert admin.password_hash == "existing"

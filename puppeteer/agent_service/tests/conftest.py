import pytest
import asyncio
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from agent_service.db import Base

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def engine():
    from agent_service import db
    # Use a unique database file for each test to avoid pollution
    db_file = f"test_{uuid.uuid4().hex}.db"
    test_url = f"sqlite+aiosqlite:///{db_file}"
    
    engine = create_async_engine(test_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Patch the global factory
    old_factory = db.AsyncSessionLocal
    db.AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    yield engine
    
    db.AsyncSessionLocal = old_factory
    await engine.dispose()
    
    # Clean up the test database file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
async def db_session(engine):
    from agent_service.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

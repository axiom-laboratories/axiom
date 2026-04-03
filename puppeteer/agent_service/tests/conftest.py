import pytest
import asyncio
import importlib.metadata
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


@pytest.fixture
async def test_ingredients(db_session):
    """Create test ingredients with both manual and auto-discovered flags."""
    from agent_service.db import ApprovedIngredient
    from datetime import datetime

    # Manually approved ingredient
    manual_ing = ApprovedIngredient(
        id=str(uuid.uuid4()),
        name="flask",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING",
        auto_discovered=False,
        created_at=datetime.utcnow()
    )

    # Auto-discovered ingredient (transitive dep)
    auto_ing = ApprovedIngredient(
        id=str(uuid.uuid4()),
        name="werkzeug",
        version_constraint="==2.3.0",
        os_family="DEBIAN",
        ecosystem="PYPI",
        mirror_status="PENDING",
        auto_discovered=True,
        created_at=datetime.utcnow()
    )

    db_session.add(manual_ing)
    db_session.add(auto_ing)
    await db_session.commit()

    return {"manual": manual_ing, "auto": auto_ing}


def pytest_collection_modifyitems(config, items):
    try:
        importlib.metadata.version("axiom-ee")
        ee_installed = True
    except importlib.metadata.PackageNotFoundError:
        ee_installed = False

    if not ee_installed:
        skip_ee = pytest.mark.skip(reason="EE package not installed")
        for item in items:
            if item.get_closest_marker("ee_only"):
                item.add_marker(skip_ee)

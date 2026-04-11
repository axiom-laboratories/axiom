import pytest
import asyncio
import importlib.metadata
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport
from agent_service.db import Base, User
import bcrypt

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


@pytest.fixture
async def async_client(db_session):
    """Create an async HTTP client for testing API endpoints."""
    from agent_service.main import app, get_db

    # Override the dependency to use the test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(db_session):
    """Create authenticated headers with a valid JWT token."""
    from agent_service.auth import create_access_token

    # Create a test user
    hashed_password = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
    test_user = User(
        username="testuser",
        password_hash=hashed_password,
        role="admin",
        token_version=0
    )
    db_session.add(test_user)
    await db_session.commit()

    # Create JWT token
    token = create_access_token({"sub": test_user.username, "tv": test_user.token_version})

    return {"Authorization": f"Bearer {token}"}


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

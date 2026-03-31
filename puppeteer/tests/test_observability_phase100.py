"""
Phase 100 — Observability + Sign-off: Tests for OBS-01, OBS-02, DOCS-01, DOCS-02.

Tests:
  - test_scale_health_response_model_fields: ScaleHealthResponse has all required fields
  - test_scale_health_endpoint_returns_200: GET /api/health/scale returns 200
  - test_scale_health_sqlite_returns_nulls: is_postgres=false, pool fields null on SQLite
  - test_scale_health_apscheduler_jobs_non_negative: apscheduler_jobs >= 0
  - test_scale_health_pending_depth_non_negative: pending_job_depth >= 0
  - test_upgrade_md_contains_migration_v44: migration_v44.sql row present in upgrade.md
  - test_upgrade_md_concurrently_caveat: CONCURRENTLY caveat present for migration_v44 section
  - test_upgrade_md_pool_tuning_formula: ASYNCPG_POOL_SIZE tuning formula present
  - test_upgrade_md_apscheduler_pin_rationale: APScheduler pin rationale present
"""
import asyncio
import types
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from agent_service.db import Base
from agent_service.main import app
from agent_service.deps import get_current_user
from agent_service.db import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """In-memory SQLite session factory for endpoint tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_session():
        async with async_session() as session:
            yield session

    return _get_session, engine


def _fake_admin():
    return types.SimpleNamespace(username="admin", role="admin", token_version=0)


# ---------------------------------------------------------------------------
# OBS-01: ScaleHealthResponse model
# ---------------------------------------------------------------------------

def test_scale_health_response_model_fields():
    """ScaleHealthResponse must declare all required fields with correct types."""
    from agent_service.models import ScaleHealthResponse
    import inspect

    fields = ScaleHealthResponse.model_fields
    assert "is_postgres" in fields, "ScaleHealthResponse missing field: is_postgres"
    assert "pool_size" in fields, "ScaleHealthResponse missing field: pool_size"
    assert "checked_out" in fields, "ScaleHealthResponse missing field: checked_out"
    assert "available" in fields, "ScaleHealthResponse missing field: available"
    assert "overflow" in fields, "ScaleHealthResponse missing field: overflow"
    assert "apscheduler_jobs" in fields, "ScaleHealthResponse missing field: apscheduler_jobs"
    assert "pending_job_depth" in fields, "ScaleHealthResponse missing field: pending_job_depth"

    # Verify is_postgres is bool, apscheduler_jobs and pending_job_depth are int
    instance = ScaleHealthResponse(
        is_postgres=False,
        pool_size=None,
        checked_out=None,
        available=None,
        overflow=None,
        apscheduler_jobs=0,
        pending_job_depth=0,
    )
    assert instance.is_postgres is False
    assert instance.apscheduler_jobs == 0
    assert instance.pending_job_depth == 0
    assert instance.pool_size is None


# ---------------------------------------------------------------------------
# OBS-01: GET /api/health/scale endpoint
# ---------------------------------------------------------------------------

def test_scale_health_endpoint_returns_200(db_session):
    """GET /api/health/scale must return HTTP 200."""
    get_session_fn, engine = db_session
    admin = _fake_admin()

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/health/scale")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_scale_health_sqlite_returns_nulls(db_session):
    """On SQLite: is_postgres=false and all four pool fields are null."""
    get_session_fn, engine = db_session
    admin = _fake_admin()

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/health/scale")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["is_postgres"] is False, f"Expected is_postgres=false on SQLite, got {data['is_postgres']}"
        assert data["pool_size"] is None, f"Expected pool_size=null on SQLite, got {data['pool_size']}"
        assert data["checked_out"] is None, f"Expected checked_out=null on SQLite, got {data['checked_out']}"
        assert data["available"] is None, f"Expected available=null on SQLite, got {data['available']}"
        assert data["overflow"] is None, f"Expected overflow=null on SQLite, got {data['overflow']}"
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_scale_health_apscheduler_jobs_non_negative(db_session):
    """apscheduler_jobs must be an integer >= 0."""
    get_session_fn, engine = db_session
    admin = _fake_admin()

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/health/scale")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data["apscheduler_jobs"], int), (
            f"apscheduler_jobs must be int, got {type(data['apscheduler_jobs'])}"
        )
        assert data["apscheduler_jobs"] >= 0, (
            f"apscheduler_jobs must be >= 0, got {data['apscheduler_jobs']}"
        )
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_scale_health_pending_depth_non_negative(db_session):
    """pending_job_depth must be an integer >= 0."""
    get_session_fn, engine = db_session
    admin = _fake_admin()

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/health/scale")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data["pending_job_depth"], int), (
            f"pending_job_depth must be int, got {type(data['pending_job_depth'])}"
        )
        assert data["pending_job_depth"] >= 0, (
            f"pending_job_depth must be >= 0, got {data['pending_job_depth']}"
        )
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


# ---------------------------------------------------------------------------
# DOCS-01 / DOCS-02: upgrade.md content stubs (pass vacuously until Plan 02)
# ---------------------------------------------------------------------------

def _get_upgrade_md_path() -> Path:
    """Return path to the upgrade.md in the puppeteer directory."""
    return Path(__file__).parent.parent / "upgrade.md"


def test_upgrade_md_contains_migration_v44():
    """upgrade.md must contain a reference to migration_v44.sql."""
    upgrade_md = _get_upgrade_md_path()
    if not upgrade_md.exists():
        pytest.skip("upgrade.md not yet created — stub passes vacuously until Plan 02")
    content = upgrade_md.read_text()
    assert "migration_v44" in content, (
        "upgrade.md must reference migration_v44.sql"
    )


def test_upgrade_md_concurrently_caveat():
    """upgrade.md must include a CONCURRENTLY caveat for the migration_v44 section."""
    upgrade_md = _get_upgrade_md_path()
    if not upgrade_md.exists():
        pytest.skip("upgrade.md not yet created — stub passes vacuously until Plan 02")
    content = upgrade_md.read_text()
    assert "CONCURRENTLY" in content, (
        "upgrade.md must warn that CREATE INDEX CONCURRENTLY cannot run inside a transaction"
    )


def test_upgrade_md_pool_tuning_formula():
    """upgrade.md must include the ASYNCPG_POOL_SIZE tuning formula."""
    upgrade_md = _get_upgrade_md_path()
    if not upgrade_md.exists():
        pytest.skip("upgrade.md not yet created — stub passes vacuously until Plan 02")
    content = upgrade_md.read_text()
    assert "ASYNCPG_POOL_SIZE" in content, (
        "upgrade.md must include ASYNCPG_POOL_SIZE pool tuning formula"
    )


def test_upgrade_md_apscheduler_pin_rationale():
    """upgrade.md must include the APScheduler pin rationale."""
    upgrade_md = _get_upgrade_md_path()
    if not upgrade_md.exists():
        pytest.skip("upgrade.md not yet created — stub passes vacuously until Plan 02")
    content = upgrade_md.read_text()
    assert "apscheduler" in content.lower(), (
        "upgrade.md must include APScheduler pin rationale"
    )

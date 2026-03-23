"""
Phase 54 — Bug Fix Blitz: Tests for INT-04.
Tests cover:
  - test_list_jobs_includes_retry_fields: GET /jobs response items include retry_count, max_retries, retry_after, originating_guid
  - test_list_jobs_originating_guid: resubmitted job shows originating_guid; original shows None
  - test_list_jobs_retry_after_is_string: retry_after is an ISO string, not a datetime object
"""
import types
import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from agent_service.db import Base, Job
from agent_service.main import app
from agent_service.deps import get_current_user
from agent_service.db import get_db


# ---------------------------------------------------------------------------
# Async in-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Return a running async session backed by an in-memory SQLite DB."""
    import asyncio as _asyncio
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _asyncio.get_event_loop().run_until_complete(_create())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_session():
        async with async_session() as session:
            yield session

    # Return a factory so callers can open sessions
    return _get_session, engine


# ---------------------------------------------------------------------------
# Helper: fake admin user
# ---------------------------------------------------------------------------

def _fake_user():
    return types.SimpleNamespace(username="admin", role="admin", token_version=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_list_jobs_includes_retry_fields(db_session):
    """
    GET /jobs response items must include retry_count, max_retries,
    retry_after (ISO string), and originating_guid.
    """
    get_session_fn, engine = db_session
    admin = _fake_user()

    retry_time = datetime(2026, 4, 1, 12, 0, 0)

    async def _setup():
        async for session in get_session_fn():
            job = Job(
                guid="retry-test-001",
                task_type="script",
                payload='{"script": "print(1)"}',
                status="FAILED",
                retry_count=1,
                max_retries=3,
                retry_after=retry_time,
                originating_guid=None,
            )
            session.add(job)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_setup())

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        items = data.get("items", [])
        assert len(items) >= 1, "Expected at least 1 job in response"

        item = items[0]
        assert "retry_count" in item, "retry_count missing from response item"
        assert "max_retries" in item, "max_retries missing from response item"
        assert "retry_after" in item, "retry_after missing from response item"
        assert "originating_guid" in item, "originating_guid missing from response item"

        assert item["retry_count"] == 1
        assert item["max_retries"] == 3
        assert item["originating_guid"] is None
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_list_jobs_originating_guid(db_session):
    """
    A resubmitted job shows its originating_guid; the original shows None.
    """
    get_session_fn, engine = db_session
    admin = _fake_user()

    async def _setup():
        async for session in get_session_fn():
            job1 = Job(
                guid="orig-job-001",
                task_type="script",
                payload='{"script": "print(1)"}',
                status="FAILED",
                originating_guid=None,
            )
            job2 = Job(
                guid="resub-job-002",
                task_type="script",
                payload='{"script": "print(1)"}',
                status="PENDING",
                originating_guid="orig-job-001",
            )
            session.add(job1)
            session.add(job2)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_setup())

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        items = response.json().get("items", [])
        by_guid = {item["guid"]: item for item in items}

        assert "orig-job-001" in by_guid, "Original job not in response"
        assert "resub-job-002" in by_guid, "Resubmitted job not in response"

        assert by_guid["orig-job-001"]["originating_guid"] is None
        assert by_guid["resub-job-002"]["originating_guid"] == "orig-job-001"
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_list_jobs_retry_after_is_string(db_session):
    """
    When retry_after is set, the response value must be a string (ISO format),
    not a raw datetime object.
    """
    get_session_fn, engine = db_session
    admin = _fake_user()

    retry_time = datetime(2026, 6, 15, 9, 30, 0)

    async def _setup():
        async for session in get_session_fn():
            job = Job(
                guid="retry-str-test-001",
                task_type="script",
                payload='{"script": "print(1)"}',
                status="FAILED",
                retry_count=2,
                max_retries=5,
                retry_after=retry_time,
            )
            session.add(job)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_setup())

    async def override_db():
        async for session in get_session_fn():
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        items = response.json().get("items", [])
        assert len(items) >= 1, "Expected at least 1 job in response"

        item = next((i for i in items if i["guid"] == "retry-str-test-001"), None)
        assert item is not None, "Job not found in response"

        retry_after_val = item["retry_after"]
        assert retry_after_val is not None, "retry_after should not be None when set"
        assert isinstance(retry_after_val, str), (
            f"retry_after must be a string, got {type(retry_after_val).__name__}: {retry_after_val!r}"
        )
        # Verify it's parseable as ISO datetime
        parsed = datetime.fromisoformat(retry_after_val)
        assert parsed.year == 2026
    finally:
        app.dependency_overrides.clear()
        asyncio.get_event_loop().run_until_complete(engine.dispose())

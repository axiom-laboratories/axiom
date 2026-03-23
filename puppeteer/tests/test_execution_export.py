"""
Phase 53 — Scheduling Health and Data Management: Tests for SRCH-10.
Tests cover:
  - test_csv_export: GET /jobs/{guid}/executions/export returns CSV with correct headers.
"""
import types
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from agent_service.db import Base, ExecutionRecord, Job
from agent_service.main import app, EXEC_CSV_HEADERS
from agent_service.deps import get_current_user
from agent_service.db import get_db


# ---------------------------------------------------------------------------
# Async in-memory DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper: fake user
# ---------------------------------------------------------------------------

def _fake_user(username="admin", role="admin"):
    return types.SimpleNamespace(username=username, role=role, token_version=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_csv_export(db):
    """
    GET /jobs/{guid}/executions/export returns:
    - HTTP 200
    - Content-Type containing text/csv
    - First line equal to comma-joined EXEC_CSV_HEADERS
    """
    admin = _fake_user()
    test_guid = "csv-test-guid-001"

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        # Insert a Job (needed if foreign-key enforced, otherwise optional)
        # Insert 2 ExecutionRecords for the test guid
        async def _setup():
            now = datetime.utcnow()
            rec1 = ExecutionRecord(
                job_guid=test_guid,
                node_id="node-1",
                status="COMPLETED",
                exit_code=0,
                started_at=now - timedelta(minutes=5),
                completed_at=now - timedelta(minutes=4),
                attempt_number=1,
                pinned=False,
            )
            rec2 = ExecutionRecord(
                job_guid=test_guid,
                node_id="node-1",
                status="FAILED",
                exit_code=1,
                started_at=now - timedelta(minutes=3),
                completed_at=now - timedelta(minutes=2),
                attempt_number=2,
                pinned=True,
            )
            async for session in override_db():
                session.add(rec1)
                session.add(rec2)
                await session.commit()

        asyncio.get_event_loop().run_until_complete(_setup())

        client = TestClient(app)
        response = client.get(f"/jobs/{test_guid}/executions/export")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("content-type", ""), \
            f"Expected text/csv content-type, got: {response.headers.get('content-type')}"

        # Check first line matches headers
        first_line = response.text.splitlines()[0]
        assert first_line == ",".join(EXEC_CSV_HEADERS), \
            f"Expected headers '{','.join(EXEC_CSV_HEADERS)}', got '{first_line}'"

        # Should have 3 lines: header + 2 records
        lines = [l for l in response.text.splitlines() if l.strip()]
        assert len(lines) == 3, f"Expected 3 lines (header + 2 records), got {len(lines)}"

    finally:
        app.dependency_overrides.clear()

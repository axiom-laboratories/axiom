"""
Phase 92 — USP Signing UX: Tests for signature error paths on POST /jobs/definitions.

Tests cover:
  - test_dispatch_unknown_signature_id: unknown signature_id returns 404 with
    actionable message.
  - test_dispatch_bad_signature_payload: valid signature_id but garbage signature
    returns 403 with message referencing the Signatures page.
"""
import types
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from agent_service.db import Base, Signature
from agent_service.main import app
from agent_service.deps import get_current_user
from agent_service.db import get_db


# ---------------------------------------------------------------------------
# Module-level Ed25519 test key (generated once, shared across tests)
# ---------------------------------------------------------------------------

_TEST_PRIVATE_KEY = Ed25519PrivateKey.generate()
_TEST_PUBLIC_KEY_PEM = _TEST_PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


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
# Helper: build a fake admin User-like object using SimpleNamespace
# ---------------------------------------------------------------------------

def _fake_admin(username="admin"):
    return types.SimpleNamespace(username=username, role="admin", token_version=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dispatch_unknown_signature_id(db):
    """
    POST /jobs/definitions with a non-existent signature_id returns 404
    with a detail message containing "Signature ID not found".
    """
    admin = _fake_admin()

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.post("/jobs/definitions", json={
            "name": "test-job",
            "script_content": "print('hello')",
            "signature": "anysig",
            "signature_id": "nonexistent-id-000",
            "schedule_cron": "* * * * *",
        })
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
        detail = response.json()["detail"]
        assert "Signature ID not found" in detail, (
            f"Expected 'Signature ID not found' in detail, got: {detail!r}"
        )
    finally:
        app.dependency_overrides.clear()


def test_dispatch_bad_signature_payload(db):
    """
    POST /jobs/definitions with a valid signature_id but a garbage signature
    returns 403 with a detail message referencing the Signatures page.
    """
    import asyncio

    admin = _fake_admin()

    # Seed a Signature row into the in-memory DB
    async def seed_signature():
        sig_row = Signature(
            id="test-sig-id-001",
            name="Test Key",
            public_key=_TEST_PUBLIC_KEY_PEM,
            uploaded_by="admin",
        )
        db.add(sig_row)
        await db.commit()

    asyncio.get_event_loop().run_until_complete(seed_signature())

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.post("/jobs/definitions", json={
            "name": "test-job-badsig",
            "script_content": "print('hello')",
            "signature": "badsig==",
            "signature_id": "test-sig-id-001",
            "schedule_cron": "* * * * *",
        })
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.text}"
        )
        detail = response.json()["detail"]
        assert "Signatures page" in detail, (
            f"Expected 'Signatures page' in detail, got: {detail!r}"
        )
    finally:
        app.dependency_overrides.clear()

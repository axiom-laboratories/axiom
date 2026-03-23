"""
Phase 53 — Scheduling Health and Data Management: Tests for SRCH-06, SRCH-07.
Tests cover:
  - test_create_template: POST /job-templates creates template, signing fields stripped.
  - test_template_visibility: private templates are hidden from other users; shared templates are visible.
"""
import json
import types
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from agent_service.db import Base, JobTemplate
from agent_service.main import app
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
# Helper: build a fake User-like object using SimpleNamespace
# ---------------------------------------------------------------------------

def _fake_user(username="alice", role="operator"):
    return types.SimpleNamespace(username=username, role=role, token_version=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_template(db):
    """
    POST /job-templates creates a template with name, payload (sans signature fields),
    visibility=private; returns 201 with id + payload (signature_id excluded).
    """
    alice = _fake_user("alice", "operator")

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: alice

    try:
        client = TestClient(app)
        payload_with_sig = {
            "script": "print('hello')",
            "runtime": "python",
            "signature_id": "sig-abc",
            "signature_payload": "base64payload==",
            "signature_hmac": "hmacvalue",
        }
        response = client.post("/job-templates", json={
            "name": "My Template",
            "visibility": "private",
            "payload": payload_with_sig,
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response must contain 'id'"
        assert "signature_id" not in data["payload"], "signature_id must be stripped from payload"
        assert "signature_payload" not in data["payload"], "signature_payload must be stripped"
        assert "signature_hmac" not in data["payload"], "signature_hmac must be stripped"
        assert data["payload"]["script"] == "print('hello')", "Non-signing payload fields preserved"
        assert data["name"] == "My Template"
        assert data["visibility"] == "private"
        assert data["creator_id"] == "alice"
    finally:
        app.dependency_overrides.clear()


def test_template_visibility(db):
    """
    User A creates a private template. User B cannot see it via GET /job-templates.
    After PATCH to visibility='shared', User B can see it.
    """
    alice = _fake_user("alice", "operator")
    bob = _fake_user("bob", "operator")

    async def override_db():
        yield db

    try:
        # Step 1: Alice creates a private template
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: alice
        client = TestClient(app)

        create_resp = client.post("/job-templates", json={
            "name": "Alice Private",
            "visibility": "private",
            "payload": {"script": "print('alice')"},
        })
        assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
        template_id = create_resp.json()["id"]

        # Step 2: Bob cannot see Alice's private template
        app.dependency_overrides[get_current_user] = lambda: bob
        list_resp = client.get("/job-templates")
        assert list_resp.status_code == 200
        bob_templates = list_resp.json()
        ids = [t["id"] for t in bob_templates]
        assert template_id not in ids, "Bob must not see Alice's private template"

        # Step 3: Alice promotes to shared
        app.dependency_overrides[get_current_user] = lambda: alice
        patch_resp = client.patch(f"/job-templates/{template_id}", json={"visibility": "shared"})
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.text}"

        # Step 4: Bob can now see the shared template
        app.dependency_overrides[get_current_user] = lambda: bob
        list_resp2 = client.get("/job-templates")
        assert list_resp2.status_code == 200
        bob_templates2 = list_resp2.json()
        ids2 = [t["id"] for t in bob_templates2]
        assert template_id in ids2, "Bob must see Alice's shared template"
    finally:
        app.dependency_overrides.clear()

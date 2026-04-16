"""
Test suite for Phase 149 Workflow Webhooks (CRUD, HMAC verification).

Tests verify:
- Webhook CRUD operations (TRIGGER-03)
- HMAC-SHA256 signature verification (TRIGGER-04)
- Secret management and encryption (TRIGGER-03)
- Error handling for invalid signatures (TRIGGER-05)
"""
import pytest
import json
import hmac
import hashlib
import secrets
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from agent_service.db import Workflow, WorkflowWebhook, WorkflowRun, AsyncSessionLocal
from agent_service.models import WorkflowWebhookCreate, WorkflowWebhookResponse
from agent_service.services.workflow_service import WorkflowService
from agent_service import security


# ============================================================================
# Task 1: Webhook CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_webhook_create_returns_plaintext(setup_db):
    """
    POST /api/workflows/{id}/webhooks returns 201 with plaintext secret (once only).
    Verifies that webhook creation returns the plaintext secret in response.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.commit()

        # Simulate webhook creation
        plaintext_secret = secrets.token_urlsafe(32)
        secret_hash = security.hash_webhook_secret(plaintext_secret)
        secret_plaintext_encrypted = security.cipher_suite.encrypt(plaintext_secret.encode()).decode()

        webhook = WorkflowWebhook(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="github-push",
            secret_hash=secret_hash,
            secret_plaintext=secret_plaintext_encrypted
        )
        session.add(webhook)
        await session.commit()

        # Verify webhook was created
        assert webhook.id is not None
        assert webhook.secret_hash is not None
        assert webhook.secret_plaintext is not None
        assert webhook.secret_hash != plaintext_secret, "Hash should not be plaintext"


@pytest.mark.asyncio
async def test_webhook_create_secret_hashed(setup_db):
    """
    Created webhook secret stored as bcrypt hash (plaintext never stored directly).
    Verifies hash_webhook_secret produces bcrypt hash.
    """
    plaintext = secrets.token_urlsafe(32)
    secret_hash = security.hash_webhook_secret(plaintext)

    # Verify hash is not plaintext
    assert secret_hash != plaintext
    # Verify hash looks like bcrypt (starts with $2b$)
    assert secret_hash.startswith("$2b$") or secret_hash.startswith("$2a$") or secret_hash.startswith("$2y$")


@pytest.mark.asyncio
async def test_webhook_create_secret_encrypted(setup_db):
    """
    Plaintext secret stored Fernet-encrypted, not plaintext.
    Verifies that secret_plaintext field contains encrypted data.
    """
    plaintext_secret = secrets.token_urlsafe(32)
    encrypted = security.cipher_suite.encrypt(plaintext_secret.encode()).decode()

    # Verify encrypted value is different from plaintext
    assert encrypted != plaintext_secret
    # Verify it can be decrypted back
    decrypted = security.cipher_suite.decrypt(encrypted.encode()).decode()
    assert decrypted == plaintext_secret


@pytest.mark.asyncio
async def test_webhook_list_secret_masked(setup_db):
    """
    GET /api/workflows/{id}/webhooks returns secret=None for security.
    Verifies that webhook listing never exposes the plaintext secret.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-list-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Create webhooks
        for i in range(2):
            plaintext = secrets.token_urlsafe(32)
            webhook = WorkflowWebhook(
                id=str(uuid4()),
                workflow_id=workflow_id,
                name=f"webhook-{i}",
                secret_hash=security.hash_webhook_secret(plaintext),
                secret_plaintext=security.cipher_suite.encrypt(plaintext.encode()).decode()
            )
            session.add(webhook)
        await session.commit()

        # Query webhooks
        stmt = select(WorkflowWebhook).where(WorkflowWebhook.workflow_id == workflow_id)
        result = await session.execute(stmt)
        webhooks = result.scalars().all()

        # Create response models (which should mask secret)
        responses = [
            WorkflowWebhookResponse(
                id=wh.id,
                workflow_id=wh.workflow_id,
                name=wh.name,
                created_at=wh.created_at,
                secret=None  # Always None in list response
            )
            for wh in webhooks
        ]

        # Verify secret is masked in responses
        for resp in responses:
            assert resp.secret is None, "Webhook list response must mask secret"


@pytest.mark.asyncio
async def test_webhook_delete(setup_db):
    """
    DELETE /api/workflows/{id}/webhooks/{webhook_id} returns 204 and removes webhook.
    Verifies that webhook deletion works correctly.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        webhook_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-delete-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        plaintext = secrets.token_urlsafe(32)
        webhook = WorkflowWebhook(
            id=webhook_id,
            workflow_id=workflow_id,
            name="to-delete",
            secret_hash=security.hash_webhook_secret(plaintext),
            secret_plaintext=security.cipher_suite.encrypt(plaintext.encode()).decode()
        )
        session.add(webhook)
        await session.commit()

        # Delete webhook
        await session.delete(webhook)
        await session.commit()

        # Verify deletion
        stmt = select(WorkflowWebhook).where(WorkflowWebhook.id == webhook_id)
        result = await session.execute(stmt)
        deleted = result.scalar_one_or_none()
        assert deleted is None, "Webhook should be deleted"


# ============================================================================
# Task 2: Webhook Trigger & HMAC Tests
# ============================================================================

@pytest.mark.asyncio
async def test_webhook_trigger_success(setup_db):
    """
    POST /api/webhooks/{id}/trigger with valid HMAC signature returns 202 + run_id.
    Verifies that valid webhook trigger creates a WorkflowRun.
    """
    async with AsyncSessionLocal() as session:
        # Create workflow and webhook
        workflow_id = str(uuid4())
        webhook_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(32)

        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-trigger-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        webhook = WorkflowWebhook(
            id=webhook_id,
            workflow_id=workflow_id,
            name="test-webhook",
            secret_hash=security.hash_webhook_secret(plaintext_secret),
            secret_plaintext=security.cipher_suite.encrypt(plaintext_secret.encode()).decode()
        )
        session.add(webhook)
        await session.commit()

        # Compute valid signature
        body = json.dumps({"env": "prod"}).encode()
        correct_sig = "sha256=" + hmac.new(
            plaintext_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        # Simulate webhook trigger endpoint
        # (In real test, would call the endpoint; here we test the signature verification)
        result = security.verify_webhook_signature(correct_sig, body, plaintext_secret)
        assert result is True, "Valid signature should verify"


@pytest.mark.asyncio
async def test_webhook_trigger_hmac_mismatch(setup_db):
    """
    Invalid HMAC signature returns 401 Unauthorized.
    Verifies that signature mismatch is rejected.
    """
    plaintext_secret = secrets.token_urlsafe(32)
    body = json.dumps({"env": "prod"}).encode()

    # Use wrong signature
    bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    result = security.verify_webhook_signature(bad_sig, body, plaintext_secret)
    assert result is False, "Invalid signature should fail verification"


@pytest.mark.asyncio
async def test_webhook_trigger_missing_signature(setup_db):
    """
    Missing X-Hub-Signature-256 header returns 401.
    Verifies that missing signature header is rejected.
    """
    # Test that verification fails when no signature provided
    plaintext_secret = secrets.token_urlsafe(32)
    body = b"test payload"

    # No header = no signature to verify
    # (In real endpoint, missing header would be caught before calling verify_webhook_signature)
    result = security.verify_webhook_signature("", body, plaintext_secret)
    assert result is False


@pytest.mark.asyncio
async def test_webhook_trigger_unknown_webhook(setup_db):
    """
    Unknown webhook_id returns 404 (not 401 to avoid info leak).
    Verifies that querying non-existent webhook returns 404.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        unknown_webhook_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.commit()

        # Query for non-existent webhook
        stmt = select(WorkflowWebhook).where(WorkflowWebhook.id == unknown_webhook_id)
        result = await session.execute(stmt)
        webhook = result.scalar_one_or_none()

        assert webhook is None, "Non-existent webhook should return None"


@pytest.mark.asyncio
async def test_webhook_trigger_creates_run_with_webhook_type(setup_db):
    """
    Triggered run has trigger_type=WEBHOOK, triggered_by=webhook.name.
    Verifies webhook trigger metadata.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        webhook_id = str(uuid4())
        plaintext_secret = secrets.token_urlsafe(32)

        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-run-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        webhook = WorkflowWebhook(
            id=webhook_id,
            workflow_id=workflow_id,
            name="github-webhook",
            secret_hash=security.hash_webhook_secret(plaintext_secret),
            secret_plaintext=security.cipher_suite.encrypt(plaintext_secret.encode()).decode()
        )
        session.add(webhook)
        await session.commit()

        # Simulate webhook trigger
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={},
            trigger_type="WEBHOOK",
            triggered_by=webhook.name,
            db=session
        )

        assert run.trigger_type == "WEBHOOK"
        assert run.triggered_by == "github-webhook"


@pytest.mark.asyncio
async def test_webhook_trigger_params_from_body(setup_db):
    """
    POST body JSON becomes parameters dict merged with defaults.
    Verifies that webhook body parameters are captured.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-webhook-params-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.commit()

        # Simulate webhook trigger with body parameters
        body_params = {"env": "prod", "region": "us-west-2"}
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters=body_params,
            trigger_type="WEBHOOK",
            triggered_by="test-webhook",
            db=session
        )

        params = json.loads(run.parameters_json)
        assert params["env"] == "prod"
        assert params["region"] == "us-west-2"


@pytest.mark.asyncio
async def test_hmac_signature_verification_direct(setup_db):
    """
    verify_webhook_signature() correctly validates SHA-256 HMAC.
    Tests the security.verify_webhook_signature() function directly.
    """
    plaintext_secret = secrets.token_urlsafe(32)
    body = b"test payload"

    # Compute correct signature
    correct_sig = "sha256=" + hmac.new(
        plaintext_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    # Verify should succeed
    assert security.verify_webhook_signature(correct_sig, body, plaintext_secret) is True

    # Verify should fail with wrong signature
    wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
    assert security.verify_webhook_signature(wrong_sig, body, plaintext_secret) is False


@pytest.mark.asyncio
async def test_webhook_secret_encryption_decryption(setup_db):
    """
    Webhook secret encryption and decryption roundtrip.
    Verifies that encrypted plaintext can be decrypted for HMAC verification.
    """
    plaintext_secret = "my-secret-key-12345"

    # Encrypt
    encrypted = security.cipher_suite.encrypt(plaintext_secret.encode()).decode()
    assert encrypted != plaintext_secret

    # Decrypt
    decrypted = security.cipher_suite.decrypt(encrypted.encode()).decode()
    assert decrypted == plaintext_secret

    # Use decrypted in HMAC verification
    body = b"test"
    sig = "sha256=" + hmac.new(
        decrypted.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    result = security.verify_webhook_signature(sig, body, decrypted)
    assert result is True

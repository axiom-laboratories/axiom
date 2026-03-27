"""
RED phase tests for Phase 73 EE Licence System (LIC-01 through LIC-07).

All 7 tests MUST fail before plan 02/03 create licence_service.py.
Each test imports from puppeteer.agent_service.services.licence_service at function
scope so the ImportError is the failure, not an import-time crash.
"""
import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import jwt as _jwt


# ---------------------------------------------------------------------------
# LIC-01: Generate an Ed25519-signed JWT with all required fields
# ---------------------------------------------------------------------------
def test_generate_licence_jwt():
    """LIC-01: A valid EdDSA JWT payload round-trips correctly through encode/decode."""
    from puppeteer.agent_service.services.licence_service import _decode_licence_jwt, LicenceState  # noqa: F401

    # Generate a test keypair inline
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    payload = {
        "version": 1,
        "licence_id": "test-licence-uuid",
        "customer_id": "acme-corp",
        "issued_to": "Acme Corp",
        "contact_email": "admin@acme.example",
        "tier": "ee",
        "node_limit": 10,
        "features": ["sso", "webhooks"],
        "grace_days": 30,
        "iat": int(time.time()),
        "exp": int(time.time()) + 365 * 86400,
    }

    # Encode using EdDSA with the test private key
    token = _jwt.encode(payload, private_key, algorithm="EdDSA")

    # Decode using the test public key directly (tests the round-trip)
    decoded = _jwt.decode(
        token,
        pub_key,
        algorithms=["EdDSA"],
        options={"verify_exp": False},
    )

    assert decoded["customer_id"] == "acme-corp"
    assert decoded["tier"] == "ee"
    assert decoded["node_limit"] == 10
    assert decoded["features"] == ["sso", "webhooks"]
    assert decoded["grace_days"] == 30
    assert "exp" in decoded
    assert "iat" in decoded
    assert decoded["issued_to"] == "Acme Corp"
    assert decoded["contact_email"] == "admin@acme.example"
    assert decoded["licence_id"] == "test-licence-uuid"
    assert decoded["version"] == 1


# ---------------------------------------------------------------------------
# LIC-02: Invalid signature falls back to CE state
# ---------------------------------------------------------------------------
def test_invalid_signature_falls_to_ce():
    """LIC-02: A JWT with a tampered signature causes load_licence() to return CE state."""
    from puppeteer.agent_service.services.licence_service import load_licence  # noqa: F401

    # Generate a test keypair inline
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    payload = {
        "version": 1,
        "licence_id": "test-licence-uuid",
        "customer_id": "acme-corp",
        "issued_to": "Acme Corp",
        "contact_email": "admin@acme.example",
        "tier": "ee",
        "node_limit": 10,
        "features": ["sso"],
        "grace_days": 30,
        "iat": int(time.time()),
        "exp": int(time.time()) + 365 * 86400,
    }

    token = _jwt.encode(payload, private_key, algorithm="EdDSA")

    # Tamper the last 4 characters of the JWT (corrupts the signature segment)
    tampered = token[:-4] + "XXXX"

    with patch("puppeteer.agent_service.services.licence_service._pub_key", pub_key):
        with patch.dict("os.environ", {"AXIOM_LICENCE_KEY": tampered}, clear=False):
            result = load_licence()

    assert result.status.value == "ce"
    assert result.is_ee_active is False


# ---------------------------------------------------------------------------
# LIC-03: GRACE state — expired but within grace period
# ---------------------------------------------------------------------------
def test_grace_period_active():
    """LIC-03: _compute_state() returns GRACE+is_ee_active=True when within grace window."""
    from puppeteer.agent_service.services.licence_service import _compute_state  # noqa: F401

    payload = {
        "exp": int(time.time()) - 60,   # expired 1 minute ago
        "grace_days": 30,
        "tier": "ee",
        "node_limit": 5,
        "features": [],
        "customer_id": "test",
        "iat": 0,
    }
    result = _compute_state(payload)

    assert result.status.value == "grace"
    assert result.is_ee_active is True


# ---------------------------------------------------------------------------
# LIC-04: DEGRADED_CE state — grace has fully elapsed
# ---------------------------------------------------------------------------
def test_degraded_ce_state():
    """LIC-04: _compute_state() returns EXPIRED+is_ee_active=False when grace has elapsed."""
    from puppeteer.agent_service.services.licence_service import _compute_state  # noqa: F401

    payload = {
        "exp": int(time.time()) - 31 * 86400,  # expired 31 days ago
        "grace_days": 30,
        "tier": "ee",
        "node_limit": 5,
        "features": [],
        "customer_id": "test",
        "iat": 0,
    }
    result = _compute_state(payload)

    assert result.status.value == "expired"
    assert result.is_ee_active is False


# ---------------------------------------------------------------------------
# LIC-05: Clock rollback detection
# ---------------------------------------------------------------------------
def test_clock_rollback_detection():
    """LIC-05: check_and_record_boot() detects a future timestamp in boot.log as rollback."""
    from puppeteer.agent_service.services.licence_service import check_and_record_boot, LicenceStatus  # noqa: F401
    from datetime import datetime, timezone, timedelta

    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"

        # Write a future timestamp to the boot log to simulate rollback scenario
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        import hashlib
        future_hash = hashlib.sha256(f"{future_ts}".encode()).hexdigest()
        boot_log.write_text(f"{future_hash} {future_ts}\n")

        with patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            result = check_and_record_boot(LicenceStatus.CE)

        assert result is False, "Expected rollback to be detected (return False)"

        # EE strict mode: rollback should raise RuntimeError (no env var — use LicenceStatus.VALID)
        boot_log.write_text(f"{future_hash} {future_ts}\n")
        with patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            with pytest.raises(RuntimeError):
                check_and_record_boot(LicenceStatus.VALID)


# ---------------------------------------------------------------------------
# LIC-05b: EE strict-mode raises RuntimeError (standalone)
# ---------------------------------------------------------------------------
def test_check_and_record_boot_strict_ee():
    """LIC-05: check_and_record_boot(LicenceStatus.VALID) raises RuntimeError on rollback (hardcoded EE strict)."""
    from puppeteer.agent_service.services.licence_service import check_and_record_boot, LicenceStatus
    from datetime import datetime, timezone, timedelta
    import hashlib
    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        future_hash = hashlib.sha256(f"{future_ts}".encode()).hexdigest()
        boot_log.write_text(f"{future_hash} {future_ts}\n")
        with patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            with pytest.raises(RuntimeError, match="Clock rollback"):
                check_and_record_boot(LicenceStatus.VALID)


# ---------------------------------------------------------------------------
# LIC-06: /api/licence endpoint returns correct JSON shape
# ---------------------------------------------------------------------------
def test_licence_status_endpoint():
    """LIC-06: GET /api/licence returns status, days_until_expiry, node_limit, tier, customer_id, grace_days."""
    from puppeteer.agent_service.services.licence_service import LicenceState, LicenceStatus  # noqa: F401
    from puppeteer.agent_service.main import app
    from fastapi.testclient import TestClient
    from puppeteer.agent_service.deps import require_auth

    # Build a GRACE licence state
    grace_state = LicenceState(
        status=LicenceStatus.GRACE,
        tier="ee",
        customer_id="acme-corp",
        node_limit=10,
        grace_days=30,
        days_until_expiry=-1,
        features=["sso"],
        is_ee_active=True,
    )

    # Override auth dependency to return a mock user
    mock_user = MagicMock()
    mock_user.role = "admin"
    mock_user.username = "testadmin"

    app.dependency_overrides[require_auth] = lambda: mock_user

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            # Patch app.state.licence_state
            app.state.licence_state = grace_state

            response = client.get("/api/licence")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert "days_until_expiry" in data
            assert "node_limit" in data
            assert "tier" in data
            assert "customer_id" in data
            assert "grace_days" in data
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# LIC-07: Node limit enforcement at enroll — 402 when at capacity
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_enroll_node_limit_enforced():
    """LIC-07: enroll_node() raises HTTP 402 when active node count >= node_limit."""
    from puppeteer.agent_service.main import enroll_node
    from puppeteer.agent_service.models import EnrollmentRequest
    from fastapi import HTTPException

    # Mock db.execute to return active_count == node_limit (5 == 5)
    mock_db = AsyncMock()

    async def mock_execute(stmt):
        m = MagicMock()
        stmt_str = str(stmt).lower()
        if "count" in stmt_str and "nodes" in stmt_str:
            # Return active count == node limit
            m.scalar.return_value = 5
        else:
            m.scalar_one_or_none.return_value = None
        return m

    mock_db.execute.side_effect = mock_execute

    # Mock request with licence_state.node_limit == 5
    mock_request = MagicMock()
    licence_state = MagicMock()
    licence_state.node_limit = 5
    mock_request.app.state.licence_state = licence_state
    mock_request.client.host = "127.0.0.1"

    enroll_req = EnrollmentRequest(
        token="test-token",
        hostname="test-node-01",
        csr_pem="-----BEGIN CERTIFICATE REQUEST-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE REQUEST-----",
        node_secret_hash="abc123",
        machine_id="machine-001",
    )

    with pytest.raises(HTTPException) as excinfo:
        await enroll_node(enroll_req, mock_request, mock_db)

    assert excinfo.value.status_code == 402

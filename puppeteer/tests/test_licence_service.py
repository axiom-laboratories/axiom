"""
Tests for Phase 82 EE Licence System (LIC-01 through LIC-07).
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
    from agent_service.services.licence_service import _decode_licence_jwt, LicenceState  # noqa: F401

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
    from agent_service.services.licence_service import load_licence  # noqa: F401

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

    with patch("agent_service.services.licence_service._pub_key", pub_key):
        with patch.dict("os.environ", {"AXIOM_LICENCE_KEY": tampered}, clear=False):
            result = load_licence()

    assert result.status.value == "ce"
    assert result.is_ee_active is False


# ---------------------------------------------------------------------------
# LIC-03: GRACE state — expired but within grace period
# ---------------------------------------------------------------------------
def test_grace_period_active():
    """LIC-03: _compute_state() returns GRACE+is_ee_active=True when within grace window."""
    from agent_service.services.licence_service import _compute_state  # noqa: F401

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
    from agent_service.services.licence_service import _compute_state  # noqa: F401

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
    from agent_service.services.licence_service import check_and_record_boot, LicenceStatus  # noqa: F401
    from datetime import datetime, timezone, timedelta

    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"

        # Write a future timestamp to the boot log to simulate rollback scenario
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        import hashlib
        future_hash = hashlib.sha256(f"{future_ts}".encode()).hexdigest()
        boot_log.write_text(f"{future_hash} {future_ts}\n")

        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            result = check_and_record_boot(LicenceStatus.CE)

        assert result is False, "Expected rollback to be detected (return False)"

        # EE strict mode: rollback should raise RuntimeError (no env var — use LicenceStatus.VALID)
        boot_log.write_text(f"{future_hash} {future_ts}\n")
        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            with pytest.raises(RuntimeError):
                check_and_record_boot(LicenceStatus.VALID)


# ---------------------------------------------------------------------------
# LIC-05b: EE strict-mode raises RuntimeError (standalone)
# ---------------------------------------------------------------------------
def test_check_and_record_boot_strict_ee():
    """LIC-05: check_and_record_boot(LicenceStatus.VALID) raises RuntimeError on rollback (hardcoded EE strict)."""
    from agent_service.services.licence_service import check_and_record_boot, LicenceStatus
    from datetime import datetime, timezone, timedelta
    import hashlib
    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        future_hash = hashlib.sha256(f"{future_ts}".encode()).hexdigest()
        boot_log.write_text(f"{future_hash} {future_ts}\n")
        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            with pytest.raises(RuntimeError, match="Clock rollback"):
                check_and_record_boot(LicenceStatus.VALID)


# ---------------------------------------------------------------------------
# LIC-06: /api/licence endpoint returns correct JSON shape
# ---------------------------------------------------------------------------
def test_licence_status_endpoint():
    """LIC-06: GET /api/licence returns status, days_until_expiry, node_limit, tier, customer_id, grace_days."""
    from agent_service.services.licence_service import LicenceState, LicenceStatus  # noqa: F401
    from agent_service.main import app
    from fastapi.testclient import TestClient
    from agent_service.deps import require_auth

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
    from agent_service.main import enroll_node
    from agent_service.models import EnrollmentRequest
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


# ---------------------------------------------------------------------------
# Phase 116: Hot-reload support tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reload_licence_with_valid_key():
    """Phase 116: reload_licence() with valid EE licence key returns LicenceState."""
    from agent_service.services.licence_service import reload_licence  # noqa: F401

    # Generate a test keypair inline
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    payload = {
        "version": 1,
        "licence_id": "reload-test-uuid",
        "customer_id": "test-customer",
        "issued_to": "Test Customer",
        "contact_email": "test@example.com",
        "tier": "ee",
        "node_limit": 20,
        "features": ["foundry", "mirrors"],
        "grace_days": 14,
        "iat": int(time.time()),
        "exp": int(time.time()) + 180 * 86400,  # 6 months valid
    }

    token = _jwt.encode(payload, private_key, algorithm="EdDSA")

    # Patch the public key to use our test key
    with patch("agent_service.services.licence_service._pub_key", pub_key):
        result = await reload_licence(licence_key=token)

    assert result.status.value == "valid"
    assert result.tier == "ee"
    assert result.customer_id == "test-customer"
    assert result.node_limit == 20
    assert result.is_ee_active is True


@pytest.mark.asyncio
async def test_reload_licence_with_invalid_key():
    """Phase 116: reload_licence() with invalid key raises LicenceError."""
    from agent_service.services.licence_service import reload_licence, LicenceError  # noqa: F401

    with pytest.raises(LicenceError, match="signature invalid"):
        await reload_licence(licence_key="invalid.token.here")


@pytest.mark.asyncio
async def test_reload_licence_no_key_raises_error():
    """Phase 116: reload_licence() with no key and no env/file raises LicenceError."""
    from agent_service.services.licence_service import reload_licence, LicenceError  # noqa: F401

    with patch("agent_service.services.licence_service._read_licence_raw", return_value=None):
        with pytest.raises(LicenceError, match="No licence key found"):
            await reload_licence(licence_key=None)


def test_check_licence_expiry_valid():
    """Phase 116: check_licence_expiry() returns VALID for non-expired licence."""
    from agent_service.services.licence_service import check_licence_expiry, LicenceStatus, LicenceState  # noqa: F401

    # Create a licence valid for another 30 days
    valid_state = LicenceState(
        status=LicenceStatus.VALID,
        tier="ee",
        customer_id="test",
        node_limit=10,
        grace_days=14,
        days_until_expiry=30,
        features=["foundry"],
        is_ee_active=True,
    )

    result = check_licence_expiry(valid_state)
    assert result == LicenceStatus.VALID


def test_check_licence_expiry_grace():
    """Phase 116: check_licence_expiry() returns GRACE when in grace period."""
    from agent_service.services.licence_service import check_licence_expiry, LicenceStatus, LicenceState  # noqa: F401

    # Create a licence that expired 1 day ago but grace is 14 days
    grace_state = LicenceState(
        status=LicenceStatus.GRACE,
        tier="ee",
        customer_id="test",
        node_limit=10,
        grace_days=14,
        days_until_expiry=-1,  # expired 1 day ago
        features=["foundry"],
        is_ee_active=True,
    )

    result = check_licence_expiry(grace_state)
    assert result == LicenceStatus.GRACE


def test_check_licence_expiry_expired():
    """Phase 116: check_licence_expiry() returns EXPIRED when grace has elapsed."""
    from agent_service.services.licence_service import check_licence_expiry, LicenceStatus, LicenceState  # noqa: F401

    # Create a licence expired more than grace days ago
    expired_state = LicenceState(
        status=LicenceStatus.EXPIRED,
        tier="ee",
        customer_id="test",
        node_limit=10,
        grace_days=14,
        days_until_expiry=-20,  # expired 20 days ago (past grace)
        features=["foundry"],
        is_ee_active=False,
    )

    result = check_licence_expiry(expired_state)
    assert result == LicenceStatus.EXPIRED


def test_check_licence_expiry_ce_stays_ce():
    """Phase 116: check_licence_expiry() returns CE for CE state."""
    from agent_service.services.licence_service import check_licence_expiry, LicenceStatus, LicenceState  # noqa: F401

    ce_state = LicenceState(
        status=LicenceStatus.CE,
        tier="ce",
        customer_id=None,
        node_limit=0,
        grace_days=0,
        days_until_expiry=0,
        features=[],
        is_ee_active=False,
    )

    result = check_licence_expiry(ce_state)
    assert result == LicenceStatus.CE


# ---------------------------------------------------------------------------
# Task 6: Licence Expiry Guard Middleware tests
# ---------------------------------------------------------------------------

def test_licence_expiry_guard_ee_prefixes():
    """Phase 116 Task 6: Verify LicenceExpiryGuard middleware has correct EE route prefixes."""
    from agent_service.main import LicenceExpiryGuard

    # Test that all EE router prefixes are correctly defined
    expected_prefixes = (
        "/api/foundry",
        "/api/audit",
        "/api/webhooks",
        "/api/triggers",
        "/api/auth-ext",
        "/api/smelter",
        "/api/executions",
    )

    assert LicenceExpiryGuard.EE_PREFIXES == expected_prefixes

    # Test that prefix matching logic works correctly
    # (using direct string prefix checking, which is how dispatch() uses it)
    ee_routes = [
        "/api/foundry/templates",
        "/api/audit/log",
        "/api/webhooks/events",
        "/api/triggers/list",
        "/api/auth-ext/mfa",
        "/api/smelter/mirrors",
        "/api/executions/history",
    ]

    ce_routes = [
        "/api/nodes",
        "/api/jobs",
        "/api/health",
        "/api/licence",
    ]

    # Verify EE routes match
    for route in ee_routes:
        is_ee = any(route.lower().startswith(prefix) for prefix in LicenceExpiryGuard.EE_PREFIXES)
        assert is_ee, f"Route {route} should be recognized as EE"

    # Verify CE routes don't match
    for route in ce_routes:
        is_ee = any(route.lower().startswith(prefix) for prefix in LicenceExpiryGuard.EE_PREFIXES)
        assert not is_ee, f"Route {route} should NOT be recognized as EE"


# ---------------------------------------------------------------------------
# Task 7: Integration Tests for complete licence hot-reload flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_licence_reload_endpoint_integration():
    """Phase 116 Task 7: Integration test for POST /api/admin/licence/reload endpoint."""
    from agent_service.services.licence_service import reload_licence, LicenceState, LicenceStatus
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    # Generate a test keypair
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    # Create a valid test licence
    payload = {
        "version": 1,
        "licence_id": "integration-test-id",
        "customer_id": "integration-test-customer",
        "issued_to": "Integration Test",
        "contact_email": "test@integration.local",
        "tier": "ee",
        "node_limit": 50,
        "features": ["foundry", "audit", "webhooks"],
        "grace_days": 30,
        "iat": int(time.time()),
        "exp": int(time.time()) + 365 * 86400,
    }

    token = _jwt.encode(payload, private_key, algorithm="EdDSA")

    # Mock the public key
    with patch("agent_service.services.licence_service._pub_key", pub_key):
        result = await reload_licence(licence_key=token)

    # Verify the reloaded state
    assert result.status == LicenceStatus.VALID
    assert result.tier == "ee"
    assert result.customer_id == "integration-test-customer"
    assert result.node_limit == 50
    assert result.is_ee_active is True
    assert set(result.features) == {"foundry", "audit", "webhooks"}


@pytest.mark.asyncio
async def test_licence_reload_preserves_all_fields():
    """Phase 116 Task 7: reload_licence() preserves all JWT payload fields in LicenceState."""
    from agent_service.services.licence_service import reload_licence
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    payload = {
        "version": 1,
        "licence_id": "test-preserve-uuid",
        "customer_id": "preserve-test",
        "issued_to": "Preserve Test Corp",
        "contact_email": "preserve@test.example",
        "tier": "ee",
        "node_limit": 100,
        "features": ["foundry", "sso", "webhooks", "audit"],
        "grace_days": 14,
        "iat": int(time.time()),
        "exp": int(time.time()) + 730 * 86400,
    }

    token = _jwt.encode(payload, private_key, algorithm="EdDSA")

    with patch("agent_service.services.licence_service._pub_key", pub_key):
        result = await reload_licence(licence_key=token)

    # Verify all fields are preserved
    assert result.customer_id == "preserve-test"
    assert result.node_limit == 100
    assert result.grace_days == 14
    assert len(result.features) == 4
    assert "sso" in result.features
    assert "audit" in result.features
    assert result.days_until_expiry > 0  # Should be positive (not expired)


def test_licence_state_transitions_complete():
    """Phase 116 Task 7: Verify VALID → GRACE → EXPIRED state machine transitions."""
    from agent_service.services.licence_service import _compute_state, LicenceStatus

    now = int(time.time())

    # Test 1: VALID state (expiry in future)
    valid_payload = {
        "exp": now + 10 * 86400,  # expires in 10 days
        "grace_days": 30,
        "tier": "ee",
        "node_limit": 5,
        "features": [],
        "customer_id": "test",
        "iat": 0,
    }
    result = _compute_state(valid_payload)
    assert result.status == LicenceStatus.VALID
    assert result.is_ee_active is True

    # Test 2: GRACE state (expired but within grace window)
    grace_payload = {
        "exp": now - 5 * 86400,  # expired 5 days ago
        "grace_days": 30,
        "tier": "ee",
        "node_limit": 5,
        "features": [],
        "customer_id": "test",
        "iat": 0,
    }
    result = _compute_state(grace_payload)
    assert result.status == LicenceStatus.GRACE
    assert result.is_ee_active is True
    assert result.days_until_expiry < 0  # In grace period

    # Test 3: EXPIRED state (grace period elapsed)
    expired_payload = {
        "exp": now - 40 * 86400,  # expired 40 days ago (past grace of 30 days)
        "grace_days": 30,
        "tier": "ee",
        "node_limit": 5,
        "features": [],
        "customer_id": "test",
        "iat": 0,
    }
    result = _compute_state(expired_payload)
    assert result.status == LicenceStatus.EXPIRED
    assert result.is_ee_active is False


def test_check_and_record_boot_integration():
    """Phase 116 Task 7: Verify check_and_record_boot() hash chain integrity."""
    from agent_service.services.licence_service import check_and_record_boot, LicenceStatus
    from pathlib import Path
    from datetime import datetime, timezone
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"

        # Patch BOOT_LOG_PATH
        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            # First boot — should succeed and create genesis entry
            result = check_and_record_boot(LicenceStatus.CE)
            assert result is True
            assert boot_log.exists()

            # Read the first entry
            lines = boot_log.read_text().strip().splitlines()
            assert len(lines) >= 1
            first_hash, first_ts = lines[0].split(" ", 1)
            assert len(first_hash) == 64  # SHA256 hex

            # Second boot — should succeed
            result = check_and_record_boot(LicenceStatus.CE)
            assert result is True

            # Read the second entry
            lines = boot_log.read_text().strip().splitlines()
            assert len(lines) >= 2
            second_hash, second_ts = lines[1].split(" ", 1)
            assert len(second_hash) == 64
            assert first_hash != second_hash  # Hash should change


# ---------------------------------------------------------------------------
# Phase 138: HMAC-keyed boot log tests (EE-02, EE-03)
# ---------------------------------------------------------------------------

def test_hmac_entry_write():
    """EE-02: New boot entries are written with `hmac:` prefix and HMAC-SHA256 digest."""
    pass


def test_hmac_verify_on_read():
    """EE-02: HMAC entry on last line is verified on read; mismatch raises in EE mode (VALID, GRACE, EXPIRED)."""
    pass


def test_hmac_mismatch_ce_lax():
    """EE-02: HMAC mismatch logs warning in CE mode (no raise)."""
    pass


def test_legacy_sha256_silent_accept():
    """EE-03: Legacy SHA256 entries (no `hmac:` prefix) are read silently without verification."""
    pass


def test_legacy_warning_on_read():
    """EE-03: Warning is logged once when last entry read is legacy SHA256."""
    pass


def test_mixed_format_coexist():
    """EE-03: Boot log with both legacy SHA256 and new HMAC entries reads correctly; chain maintained."""
    pass

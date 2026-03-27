"""Licence validation tests (DIST-01).

Tests _parse_licence() in ee/plugin.py and the GET /api/licence endpoint in main.py.
Uses pytest.importorskip to skip all tests if axiom-ee is not installed.
"""
import json
import base64
import time
import pytest
from httpx import AsyncClient, ASGITransport

ee_plugin = pytest.importorskip("ee.plugin", reason="axiom-ee not installed — skip licence tests")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """Encode bytes to base64url WITHOUT padding (strip '=')."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def make_licence_key(private_key, payload_dict: dict) -> str:
    """Sign payload_dict with private_key and return wire-format licence key.

    Wire format: base64url(json_payload).base64url(ed25519_sig)
    """
    payload_bytes = json.dumps(payload_dict, separators=(',', ':')).encode()
    sig_bytes = private_key.sign(payload_bytes)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig_bytes)}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def licence_keypair():
    """Generate an Ed25519 keypair for testing. Returns (private_key, raw_pub_bytes)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    priv = Ed25519PrivateKey.generate()
    pub_raw = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return priv, pub_raw


# ---------------------------------------------------------------------------
# _parse_licence tests
# ---------------------------------------------------------------------------

def test_valid_licence_sets_ee_flags(licence_keypair, monkeypatch):
    """_parse_licence with a valid key returns dict with customer_id and features."""
    from ee.plugin import _parse_licence

    priv, pub_raw = licence_keypair
    monkeypatch.setattr(ee_plugin, "_LICENCE_PUBLIC_KEY_BYTES", pub_raw)

    payload = {
        "customer_id": "test-co",
        "exp": int(time.time()) + 365 * 86400,
        "features": ["foundry", "audit"],
    }
    key_str = make_licence_key(priv, payload)

    result = _parse_licence(key_str)

    assert result is not None, "_parse_licence should return a dict for a valid key"
    assert result["customer_id"] == "test-co"
    assert result["features"] == ["foundry", "audit"]


def test_expired_key_returns_dict_with_past_exp(licence_keypair, monkeypatch):
    """_parse_licence returns a dict for an expired key (valid sig).

    The expiry check is the CALLER's responsibility (register()).
    This test verifies the expiry timestamp IS past, confirming register() would reject it.
    """
    from ee.plugin import _parse_licence

    priv, pub_raw = licence_keypair
    monkeypatch.setattr(ee_plugin, "_LICENCE_PUBLIC_KEY_BYTES", pub_raw)

    exp_time = int(time.time()) - 3600
    payload = {
        "customer_id": "expired-co",
        "exp": exp_time,
        "features": ["foundry"],
    }
    key_str = make_licence_key(priv, payload)

    result = _parse_licence(key_str)

    # Sig is valid, so _parse_licence should return a dict
    assert result is not None, "_parse_licence should return dict even for expired key (valid sig)"
    # The expiry is in the past — register() would reject based on this
    assert result["exp"] < int(time.time()), "Expiry should be in the past"


def test_invalid_sig_returns_none(licence_keypair, monkeypatch):
    """_parse_licence returns None when the signature is tampered."""
    from ee.plugin import _parse_licence

    priv, pub_raw = licence_keypair
    monkeypatch.setattr(ee_plugin, "_LICENCE_PUBLIC_KEY_BYTES", pub_raw)

    payload = {
        "customer_id": "tamper-test",
        "exp": int(time.time()) + 86400,
        "features": [],
    }
    key_str = make_licence_key(priv, payload)

    # Tamper: flip the first byte of the sig part
    parts = key_str.split('.')
    sig_bytes = bytearray(base64.urlsafe_b64decode(parts[1] + '=='))
    sig_bytes[0] ^= 0xFF  # Flip bits
    tampered_sig = base64.urlsafe_b64encode(bytes(sig_bytes)).rstrip(b'=').decode()
    tampered_key = f"{parts[0]}.{tampered_sig}"

    result = _parse_licence(tampered_key)

    assert result is None, "_parse_licence should return None for tampered signature"


def test_absent_key_ce_mode():
    """_parse_licence('') returns None — empty string fails the split check."""
    from ee.plugin import _parse_licence

    result = _parse_licence("")

    assert result is None, "_parse_licence('') should return None"


# ---------------------------------------------------------------------------
# GET /api/licence endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_licence_endpoint_community():
    """GET /api/licence returns the 6-field CE response when no licence_state is loaded on app.state."""
    from unittest.mock import MagicMock
    from agent_service.main import app
    from agent_service.deps import require_auth

    # Use a MagicMock rather than a real SQLAlchemy User — SQLAlchemy ORM
    # rejects unknown kwargs in the constructor.
    fake_user = MagicMock()
    fake_user.username = "test-admin"
    fake_user.role = "admin"

    async def override_require_auth():
        return fake_user

    app.dependency_overrides[require_auth] = override_require_auth
    # Ensure no licence_state on state (Phase 75 renamed app.state.licence → app.state.licence_state)
    if hasattr(app.state, "licence_state"):
        del app.state.licence_state

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/licence")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ce"
            assert data["tier"] == "ce"
            assert data["days_until_expiry"] == 0
            assert data["node_limit"] == 0
            assert data["customer_id"] is None
            assert data["grace_days"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_licence_endpoint_enterprise():
    """GET /api/licence returns the 6-field EE response when app.state.licence_state is set."""
    from unittest.mock import MagicMock
    from agent_service.main import app
    from agent_service.deps import require_auth
    from agent_service.services.licence_service import LicenceState, LicenceStatus

    fake_user = MagicMock()
    fake_user.username = "test-admin"
    fake_user.role = "admin"

    async def override_require_auth():
        return fake_user

    app.dependency_overrides[require_auth] = override_require_auth
    # Set a real LicenceState dataclass instance on app.state.licence_state
    # (Phase 75 renamed app.state.licence → app.state.licence_state; endpoint uses attribute access)
    app.state.licence_state = LicenceState(
        status=LicenceStatus.VALID,
        tier="enterprise",
        customer_id="test-co",
        node_limit=10,
        grace_days=30,
        days_until_expiry=365,
        features=["foundry", "audit"],
        is_ee_active=True,
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/licence")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "valid"
            assert data["tier"] == "enterprise"
            assert data["customer_id"] == "test-co"
            assert data["node_limit"] == 10
            assert data["grace_days"] == 30
            assert data["days_until_expiry"] == 365
    finally:
        app.dependency_overrides.clear()
        # Clean up: remove licence_state from app.state
        if hasattr(app.state, "licence_state"):
            del app.state.licence_state

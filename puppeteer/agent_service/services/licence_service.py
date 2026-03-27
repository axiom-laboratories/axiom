"""
Licence service — validates EdDSA-signed JWT licence keys and computes LicenceState.

Responsibilities:
- Read licence key from AXIOM_LICENCE_KEY env var or secrets/licence.key file
- Verify Ed25519 (EdDSA) JWT signature against hardcoded public key
- Compute VALID / GRACE / EXPIRED / CE state from expiry + grace_days
- Detect clock rollback via hash-chained secrets/boot.log
- Expose load_licence() to lifespan in main.py

Import: PyJWT (import jwt) — NOT python-jose (from jose import jwt).
PyJWT 2.7.0 supports EdDSA; python-jose 3.5.0 does not.
"""
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Boot log path (patched in tests via unittest.mock.patch)
# ---------------------------------------------------------------------------
BOOT_LOG_PATH = Path("secrets/boot.log")

# ---------------------------------------------------------------------------
# Hardcoded licence verification public key
# Generated 2026-03-27 — operators cannot replace this.
# Corresponding private key is in tools/licence_signing.key (keep secret).
# ---------------------------------------------------------------------------
_LICENCE_PUBLIC_KEY_PEM: bytes = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAVnaDTBFZ4C+X1Fk7F3FzqMbncsZ3oLvYCHVFBaGeHpA=
-----END PUBLIC KEY-----"""

_pub_key: Ed25519PublicKey = serialization.load_pem_public_key(_LICENCE_PUBLIC_KEY_PEM)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class LicenceStatus(str, Enum):
    VALID = "valid"
    GRACE = "grace"
    EXPIRED = "expired"   # grace has elapsed — DEGRADED_CE mode
    CE = "ce"             # no licence or invalid licence


@dataclass
class LicenceState:
    status: LicenceStatus
    tier: str                   # "ce" or "ee"
    customer_id: Optional[str]
    node_limit: int             # 0 = unlimited (CE mode)
    grace_days: int
    days_until_expiry: int      # negative when expired
    features: List[str]
    is_ee_active: bool          # True only for VALID or GRACE


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ce_state() -> LicenceState:
    """Return a Community Edition (no licence) LicenceState."""
    return LicenceState(
        status=LicenceStatus.CE,
        tier="ce",
        customer_id=None,
        node_limit=0,
        grace_days=0,
        days_until_expiry=0,
        features=[],
        is_ee_active=False,
    )


def _read_licence_raw() -> Optional[str]:
    """
    Return the raw licence JWT string, or None if not configured.

    Fallback order:
    1. AXIOM_LICENCE_KEY environment variable
    2. secrets/licence.key file content (stripped)
    """
    env_val = os.getenv("AXIOM_LICENCE_KEY", "").strip()
    if env_val:
        return env_val

    key_file = Path("secrets/licence.key")
    if key_file.exists():
        try:
            content = key_file.read_text().strip()
            if content:
                return content
        except OSError:
            pass

    return None


def _decode_licence_jwt(token: str) -> dict:
    """
    Verify the EdDSA (Ed25519) signature and return the decoded payload.

    verify_exp=False — expiry is handled manually via grace_days logic.
    Raises jwt.exceptions.* on signature or format errors.
    """
    return jwt.decode(
        token,
        _pub_key,
        algorithms=["EdDSA"],
        options={"verify_exp": False},
    )


def _compute_state(payload: dict) -> LicenceState:
    """
    Derive LicenceStatus from the decoded JWT payload.

    Grace period: if now > exp but now <= exp + grace_days * 86400 → GRACE (EE still active).
    Past grace: EXPIRED (DEGRADED_CE).
    """
    now = time.time()
    exp = payload.get("exp", 0)
    grace_days = payload.get("grace_days", 30)
    grace_end = exp + grace_days * 86400
    days_until_expiry = int((exp - now) / 86400)

    if now <= exp:
        status = LicenceStatus.VALID
    elif now <= grace_end:
        status = LicenceStatus.GRACE
    else:
        status = LicenceStatus.EXPIRED

    return LicenceState(
        status=status,
        tier=payload.get("tier", "ce"),
        customer_id=payload.get("customer_id"),
        node_limit=payload.get("node_limit", 0),
        grace_days=grace_days,
        days_until_expiry=days_until_expiry,
        features=payload.get("features", []),
        is_ee_active=(status in (LicenceStatus.VALID, LicenceStatus.GRACE)),
    )


# ---------------------------------------------------------------------------
# Hash-chain clock rollback detection
# ---------------------------------------------------------------------------

def _compute_hash(prev_hash_hex: str, iso_ts: str) -> str:
    """SHA256 of concatenated prev_hash_hex + ISO8601 timestamp."""
    return hashlib.sha256(f"{prev_hash_hex}{iso_ts}".encode()).hexdigest()


def check_and_record_boot() -> bool:
    """
    Append a new timestamped entry to the hash-chained boot log.

    Returns True if no rollback is detected, False if the last entry has a
    timestamp in the future (indicating clock rollback).

    When AXIOM_STRICT_CLOCK=true, raises RuntimeError instead of returning
    False on rollback detection.

    Boot log format: one line per boot, each line = '<sha256_hex> <ISO8601_timestamp>'.
    Genesis (absent or empty file): creates the first entry.
    Truncation: keeps last 1000 lines to prevent unbounded growth.
    """
    strict_clock = os.getenv("AXIOM_STRICT_CLOCK", "").strip().lower() == "true"
    now_ts = datetime.now(timezone.utc).isoformat()

    BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Genesis case
    if not BOOT_LOG_PATH.exists() or BOOT_LOG_PATH.stat().st_size == 0:
        new_hash = _compute_hash("", now_ts)
        BOOT_LOG_PATH.write_text(f"{new_hash} {now_ts}\n")
        return True

    lines = BOOT_LOG_PATH.read_text().strip().splitlines()
    last_line = lines[-1]
    parts = last_line.split(" ", 1)
    last_hash = parts[0]
    last_ts = parts[1] if len(parts) > 1 else ""

    # Detect rollback: last recorded timestamp is in the future relative to now
    rollback_detected = last_ts > now_ts  # lexicographic comparison valid for UTC ISO8601

    # Append new entry regardless
    new_hash = _compute_hash(last_hash, now_ts)
    lines.append(f"{new_hash} {now_ts}")

    # Truncate to last 1000 lines
    if len(lines) > 1000:
        lines = lines[-1000:]

    BOOT_LOG_PATH.write_text("\n".join(lines) + "\n")

    if rollback_detected:
        msg = f"Clock rollback detected — last boot at {last_ts}, now {now_ts}"
        if strict_clock:
            raise RuntimeError(msg)
        logger.warning(msg)
        return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_licence() -> LicenceState:
    """
    Load and validate the licence key, returning a LicenceState.

    Fallback chain:
    1. If no key found → CE mode + WARNING
    2. If JWT signature invalid → CE mode + WARNING
    3. If any parse error → CE mode + WARNING
    4. Valid JWT → compute VALID / GRACE / EXPIRED state
    """
    raw = _read_licence_raw()
    if not raw:
        logger.warning("No licence key found — running in CE mode")
        return _ce_state()

    try:
        payload = _decode_licence_jwt(raw)
    except jwt.exceptions.InvalidSignatureError:
        logger.warning("Licence key signature invalid — running in CE mode")
        return _ce_state()
    except Exception as exc:
        logger.warning("Licence key parse error (%s) — running in CE mode", exc)
        return _ce_state()

    state = _compute_state(payload)

    if state.status == LicenceStatus.GRACE:
        grace_end = payload.get("exp", 0) + payload.get("grace_days", 30) * 86400
        days_left = int((grace_end - time.time()) / 86400)
        logger.warning(
            "Licence in GRACE period — %d days remaining before DEGRADED_CE", days_left
        )
    elif state.status == LicenceStatus.EXPIRED:
        logger.warning("Licence grace period ended — DEGRADED_CE mode active")

    return state

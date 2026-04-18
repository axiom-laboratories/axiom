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
import hmac as _hmac
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

from ..security import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Boot log path (patched in tests via unittest.mock.patch)
# ---------------------------------------------------------------------------
BOOT_LOG_PATH = Path("secrets/boot.log")

# ---------------------------------------------------------------------------
# Licence verification public key — read from env var for key rotation
# Generated 2026-03-28 — corresponding private key in private axiom-licenses repo
# (Phase 164 QUAL-02: moved from hardcoded source to env var)
# ---------------------------------------------------------------------------
def _load_licence_public_key() -> bytes:
    """Load LICENCE_PUBLIC_KEY from environment variable.

    Raises:
        RuntimeError: if LICENCE_PUBLIC_KEY environment variable is not set.
    """
    key_pem = os.getenv("LICENCE_PUBLIC_KEY", "")
    if not key_pem:
        raise RuntimeError(
            "LICENCE_PUBLIC_KEY environment variable not set. "
            "Required for licence key verification (Phase 164 QUAL-02)."
        )
    return key_pem.encode() if isinstance(key_pem, str) else key_pem

LICENCE_PUBLIC_KEY = _load_licence_public_key()
_pub_key: Ed25519PublicKey = serialization.load_pem_public_key(LICENCE_PUBLIC_KEY)  # type: ignore[assignment]


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


def _compute_boot_hmac(key_bytes: bytes, iso_ts: str) -> str:
    """
    HMAC-SHA256 computation of ISO8601 timestamp, keyed on ENCRYPTION_KEY.

    Args:
        key_bytes: ENCRYPTION_KEY (bytes)
        iso_ts: ISO8601 timestamp string

    Returns:
        64-character hex string (HMAC-SHA256 digest)
    """
    message = iso_ts.encode("utf-8")
    return _hmac.new(key_bytes, message, hashlib.sha256).hexdigest()


def _verify_boot_hmac(key_bytes: bytes, stored_hmac: str, iso_ts: str) -> bool:
    """
    Constant-time HMAC verification for boot log entry.

    Args:
        key_bytes: ENCRYPTION_KEY (bytes)
        stored_hmac: Stored HMAC digest (64-char hex string)
        iso_ts: ISO8601 timestamp string

    Returns:
        True if stored HMAC matches computed HMAC, False otherwise
    """
    expected = _compute_boot_hmac(key_bytes, iso_ts)
    return _hmac.compare_digest(stored_hmac, expected)


def _parse_boot_log_entry(line: str) -> tuple:
    """
    Parse a boot log line and detect entry type.

    Args:
        line: Boot log line (either legacy SHA256 or new HMAC format)

    Returns:
        tuple: (entry_type, digest_or_hmac, iso_ts)
        - entry_type: "hmac" or "sha256"
        - digest_or_hmac: the hex digest/HMAC value (without prefix)
        - iso_ts: the ISO8601 timestamp string

    Line formats:
    - New: `hmac:<64-hex> <ISO8601>` → ("hmac", "<64-hex>", "<ISO8601>")
    - Legacy: `<64-hex> <ISO8601>` → ("sha256", "<64-hex>", "<ISO8601>")
    """
    if line.startswith("hmac:"):
        # New format: "hmac:<hex> <iso_ts>"
        parts = line.split(" ", 1)
        hmac_part = parts[0][5:]  # strip "hmac:" prefix
        iso_ts = parts[1] if len(parts) > 1 else ""
        return ("hmac", hmac_part, iso_ts)
    else:
        # Legacy format: "<hex> <iso_ts>"
        parts = line.split(" ", 1)
        hex_val = parts[0]
        iso_ts = parts[1] if len(parts) > 1 else ""
        return ("sha256", hex_val, iso_ts)


def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
    """
    Append a new timestamped HMAC entry to the boot log.

    Supports mixed format: new entries use HMAC-SHA256 keyed on ENCRYPTION_KEY;
    legacy SHA256 entries (no `hmac:` prefix) are accepted on read without verification.

    Returns True if no rollback is detected, False if the last entry has a
    timestamp in the future (indicating clock rollback).

    For EE licences (VALID, GRACE, EXPIRED):
    - Raises RuntimeError on clock rollback
    - Raises RuntimeError on HMAC verification failure

    For CE mode:
    - Logs warning on clock rollback (non-blocking)
    - Logs warning on HMAC verification failure (non-blocking)

    Boot log format: mixed
    - Legacy: `<sha256_hex> <ISO8601_timestamp>` (no prefix)
    - New: `hmac:<hmac_hex> <ISO8601_timestamp>` (with prefix)

    Genesis (absent or empty file): creates the first entry with HMAC.
    Truncation: keeps last 1000 lines to prevent unbounded growth.
    """
    strict_mode = licence_status != LicenceStatus.CE
    now_ts = datetime.now(timezone.utc).isoformat()

    BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Genesis case
    if not BOOT_LOG_PATH.exists() or BOOT_LOG_PATH.stat().st_size == 0:
        new_hmac = _compute_boot_hmac(ENCRYPTION_KEY, now_ts)
        BOOT_LOG_PATH.write_text(f"hmac:{new_hmac} {now_ts}\n")
        return True

    lines = BOOT_LOG_PATH.read_text().strip().splitlines()
    last_line = lines[-1]

    # Parse last entry to detect type (HMAC or legacy SHA256)
    entry_type, stored_digest, last_ts = _parse_boot_log_entry(last_line)

    # Detect rollback: last recorded timestamp is in the future relative to now
    rollback_detected = last_ts > now_ts  # lexicographic comparison valid for UTC ISO8601

    # Handle HMAC verification for new-format entries
    if entry_type == "hmac":
        if not _verify_boot_hmac(ENCRYPTION_KEY, stored_digest, last_ts):
            msg = "Boot log HMAC verification failed — possible tampering"
            if strict_mode:
                raise RuntimeError(msg)
            logger.warning(msg)

    # Handle legacy SHA256 entries — log warning once
    elif entry_type == "sha256":
        logger.warning(
            "Legacy SHA256 boot log entry detected — migration to HMAC in progress, "
            "consider rebuilding the boot log"
        )

    # Compute new SHA256 chain hash for continuity (uses stored_digest as prev_hash)
    new_hash = _compute_hash(stored_digest, now_ts)

    # Compute new HMAC digest and write as new entry
    new_hmac = _compute_boot_hmac(ENCRYPTION_KEY, now_ts)
    lines.append(f"hmac:{new_hmac} {now_ts}")

    # Truncate to last 1000 lines
    if len(lines) > 1000:
        lines = lines[-1000:]

    BOOT_LOG_PATH.write_text("\n".join(lines) + "\n")

    if rollback_detected:
        msg = f"Clock rollback detected — last boot at {last_ts}, now {now_ts}"
        if strict_mode:
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


# ---------------------------------------------------------------------------
# Hot-reload support (Phase 116)
# ---------------------------------------------------------------------------

class LicenceError(Exception):
    """Raised when licence validation fails during reload."""
    pass


async def reload_licence(licence_key: Optional[str] = None) -> LicenceState:
    """
    Hot-reload the licence key without restarting the server.

    Args:
        licence_key: Optional override licence key. If None, re-reads from env/file.

    Returns:
        New LicenceState object if valid.

    Raises:
        LicenceError: If validation fails (invalid signature, parse error, etc.)
    """
    # Determine source: override or env/file fallback
    raw = licence_key if licence_key else _read_licence_raw()

    if not raw:
        raise LicenceError("No licence key found in request or env/file")

    try:
        payload = _decode_licence_jwt(raw)
    except jwt.exceptions.InvalidSignatureError as exc:
        raise LicenceError(f"Licence key signature invalid: {exc}")
    except Exception as exc:
        raise LicenceError(f"Licence key parse error: {exc}")

    state = _compute_state(payload)

    # Log the reload
    logger.info(
        f"Licence reloaded: status={state.status}, tier={state.tier}, "
        f"customer_id={state.customer_id}, node_limit={state.node_limit}"
    )

    return state


def check_licence_expiry(licence: LicenceState) -> LicenceStatus:
    """
    Check the current expiry status of a licence state.

    This is used by background timer to detect status transitions (e.g., GRACE → EXPIRED).

    Args:
        licence: LicenceState object to check

    Returns:
        Updated LicenceStatus (VALID, GRACE, or EXPIRED)
    """
    # If already CE, stay CE
    if licence.status == LicenceStatus.CE:
        return LicenceStatus.CE

    # For EE licences, recompute status based on current time
    now = time.time()

    # Reconstruct expiry info from the licence state
    # Note: we use the stored days_until_expiry to back-calculate exp time
    exp = now + (licence.days_until_expiry * 86400)
    grace_end = exp + licence.grace_days * 86400

    if now <= exp:
        return LicenceStatus.VALID
    elif now <= grace_end:
        return LicenceStatus.GRACE
    else:
        return LicenceStatus.EXPIRED

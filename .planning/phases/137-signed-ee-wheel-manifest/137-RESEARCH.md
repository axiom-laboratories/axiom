# Phase 137: Signed EE Wheel Manifest — Research

**Researched:** 2026-04-12  
**Domain:** EE wheel installation, Ed25519 signature verification, manifest validation  
**Confidence:** HIGH

## Summary

Phase 137 adds cryptographic verification to the EE wheel installation process. Before pip installs the EE wheel, the system reads a signed manifest at `/tmp/axiom_ee.manifest.json`, verifies the SHA256 hash of the wheel file against the manifest, and validates the Ed25519 signature over that hash. Any verification failure raises `RuntimeError`, preventing installation and gracefully degrading to CE mode. The implementation reuses established patterns from `licence_service.py` (hardcoded PEM public key, Ed25519 via `cryptography` library) and integrates error visibility via the `/admin/licence` API response.

**Primary recommendation:** Insert all six verification checks into `_install_ee_wheel()` before the `subprocess.check_call` pip install, with structured error messages; catch `RuntimeError` in `activate_ee_live()` and expose the error string via `app.state.ee_activation_error`.

## Standard Stack

### Core Cryptography
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | 42+ | Ed25519 public key loading, signature verification | Already required by FastAPI/JWT stack; used in `pki.py` and `licence_service.py` for PKI/signing |
| `PyJWT[crypto]` | 2.7.0+ | JWT handling (via licence_service) | Already in requirements.txt; provides EdDSA support |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `base64` (stdlib) | 3.10+ | Decode base64-encoded signature from manifest | Standard Python — no install needed |
| `hashlib` (stdlib) | 3.10+ | SHA256 file hashing | Standard Python — no install needed |
| `json` (stdlib) | 3.10+ | Parse manifest JSON | Standard Python — no install needed |
| `pathlib` (stdlib) | 3.10+ | Path handling | Standard Python — no install needed |

**No new dependencies required** — all cryptography layers are already available.

## Architecture Patterns

### Manifest Structure
```json
{
  "sha256": "abcd1234ef5678...",  // hex-encoded SHA256 of wheel bytes
  "signature": "base64encodedEd25519SignatureHere..."  // base64-encoded signature
}
```

The **message** that was signed: UTF-8 encoded hex SHA256 string (e.g., `"abcd1234ef5678..."`).

### Verification Flow (Ordered Steps)
1. **File existence**: Check `/tmp/axiom_ee.manifest.json` exists → raise `RuntimeError` if missing
2. **JSON parsing**: Parse JSON, validate required fields (`sha256`, `signature`) → raise `RuntimeError` if malformed
3. **Wheel SHA256**: Compute SHA256 of wheel bytes at `/tmp/axiom_ee-*.whl`
4. **Hash matching**: Assert computed SHA256 == manifest `sha256` → raise `RuntimeError` if mismatch
5. **Signature decode**: Decode `signature` from base64 → raise `RuntimeError` if invalid base64
6. **Signature verify**: Verify Ed25519 signature over hex SHA256 string (UTF-8 encoded) → raise `RuntimeError` if invalid

All checks happen **before** `subprocess.check_call` for pip install. Any failure means the wheel never installs.

### Hardcoded Public Key Pattern
```python
_MANIFEST_PUBLIC_KEY_PEM: bytes = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA...
-----END PUBLIC KEY-----"""

_manifest_pub_key = serialization.load_pem_public_key(_MANIFEST_PUBLIC_KEY_PEM)
```

Same pattern as `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py:40-43`. Operators cannot replace without code changes (intentional tamper resistance).

### Error Propagation
- `_install_ee_wheel()` raises `RuntimeError` on any verification failure
- `activate_ee_live()` catches `RuntimeError` and stores error message in `app.state.ee_activation_error`
- Server remains up in CE mode; error is logged and exposed via `/admin/licence` response
- No server crash; degraded service is the fail-safe

### Integration with `/admin/licence` Endpoint
Current response (line 1184–1204 in `main.py`):
```python
{
  "status": "valid",  // or "grace", "expired", "ce"
  "days_until_expiry": 30,
  "node_limit": 0,
  "tier": "ee",
  "customer_id": "...",
  "grace_days": 30,
}
```

**After Phase 137**, add:
```python
"ee_activation_error": null  // or error message string when activation failed
```

This field:
- Is `null` when EE activation succeeded or was not attempted
- Is a human-readable error string when activation failed (e.g., `"Manifest not found: /tmp/axiom_ee.manifest.json"`)
- Allows operators to see wheel install failures in the dashboard without log diving

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signature verification | Custom crypto implementation | `cryptography.hazmat.primitives.asymmetric.ed25519` | Signature verification has no tolerance for subtle bugs; the library is audited and widely deployed |
| SHA256 hashing | Custom loop over file chunks | `hashlib.sha256()` + iterate in 64KB blocks | Standard library; well-tested; handles file I/O edge cases |
| Base64 decoding | Manual base64 parsing | `base64.b64decode()` | Handles padding, invalid characters, and error cases correctly |
| Manifest path configuration | Hardcoded path in function body | Module-level constant `MANIFEST_PATH` | Enables test patching via `unittest.mock.patch` |
| Public key loading from PEM bytes | Manual PEM parsing | `serialization.load_pem_public_key()` from cryptography | Library handles encoding, format validation, and key type verification |

**Key insight:** Cryptography is a domain with subtle pitfalls (timing attacks, key format mismatches, encoding errors). Always prefer audited libraries over custom implementations.

## Common Pitfalls

### Pitfall 1: Signing the Wrong Message
**What goes wrong:** Signing the SHA256 digest bytes instead of the hex-encoded string produces an invalid signature that never matches, even when the wheel is correct.

**Why it happens:** Confusion about message encoding — the signature was computed over UTF-8 hex string in Phase 140, but verification attempts to verify over raw bytes.

**How to avoid:** Phase 140 (Wheel Signing Release Tool) and Phase 137 MUST agree on the message format:
- Message: UTF-8 encoded hex SHA256 string (e.g., `b"abcd1234ef5678..."`)
- NOT the raw SHA256 bytes
- NOT a JSON serialization of the manifest

**Warning signs:** All manifests fail verification with `InvalidSignature` despite being correctly signed by Phase 140 tool.

### Pitfall 2: Manifest File Encoding Issues
**What goes wrong:** JSON manifest is written with incorrect encoding (e.g., UTF-16 BOM) or invalid UTF-8, causing JSON parsing to fail silently or produce incorrect field values.

**Why it happens:** Platform-specific file I/O (Windows line endings, encoding detection) or incorrect shell escaping when creating the manifest file.

**How to avoid:**
- Always write manifest as UTF-8 with no BOM
- Read manifest with explicit UTF-8 encoding
- Phase 140 must document the exact encoding and escaping rules for operators

**Warning signs:** Manifest file exists but `json.loads()` fails with `JSONDecodeError`, or fields are corrupted (non-ASCII characters misinterpreted).

### Pitfall 3: Base64 Encoding Variant Mismatch
**What goes wrong:** Phase 140 uses URL-safe base64 (`base64.urlsafe_b64encode`), but Phase 137 uses standard base64 (`base64.b64decode`), causing decoding to fail or produce garbage.

**Why it happens:** Multiple base64 variants exist; easy to mix them up if not documented clearly.

**How to avoid:** CONTEXT.md locked decision: "Base64 encoding variant for signature field (standard b64 vs urlsafe — either is fine; note it for Phase 140 compatibility)". Choose ONE and document it prominently in both phases.

**Warning signs:** Manifest parses correctly, but signature decode raises `binascii.Error` or produces invalid bytes.

### Pitfall 4: SHA256 Hash Mismatch on Legitimate Wheels
**What goes wrong:** Wheel file is correct, but the computed SHA256 doesn't match the manifest because:
- Wheel file was partially downloaded or corrupted in transit
- Manifest was generated from a different wheel version
- Build system regenerated the wheel with different timestamps/metadata (non-deterministic build)

**Why it happens:** Phase 140 generates manifest before wheel is copied to `/tmp/`; if the copy corrupts the file, hashes won't match.

**How to avoid:**
- Ensure Phase 140 computes SHA256 of the final artifact that gets deployed
- Document the exact step-by-step process: sign the wheel, compute hash, then copy
- Add a pre-verification test in Phase 140 that simulates the Phase 137 verification logic

**Warning signs:** Manually computed SHA256 of the wheel file (via `sha256sum`) doesn't match the manifest `sha256` field.

### Pitfall 5: RuntimeError Propagation Not Caught
**What goes wrong:** `_install_ee_wheel()` raises `RuntimeError`, but `activate_ee_live()` doesn't catch it, causing the exception to bubble up to the caller and crash the licence reload endpoint.

**Why it happens:** Forgetting to wrap the call in a try/except or using a too-narrow exception type.

**How to avoid:** Ensure `activate_ee_live()` has:
```python
try:
    if not _install_ee_wheel():  # or just call it if it raises
        return None
except RuntimeError as e:
    app.state.ee_activation_error = str(e)
    logger.error(...)
    return None
```

**Warning signs:** HTTP 500 error when reloading licence; server logs show unhandled exception from `_install_ee_wheel()`.

## Code Examples

### Manifest Verification (Core Logic)
```python
# Source: CONTEXT.md decisions + cryptography library docs

import json
import hashlib
import base64
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MANIFEST_PATH = Path("/tmp/axiom_ee.manifest.json")

_MANIFEST_PUBLIC_KEY_PEM: bytes = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA...
-----END PUBLIC KEY-----"""

_manifest_pub_key: Ed25519PublicKey = serialization.load_pem_public_key(_MANIFEST_PUBLIC_KEY_PEM)

def _verify_wheel_manifest(wheel_path: str) -> None:
    """
    Verify Ed25519 signature and SHA256 hash of the wheel.
    
    Raises RuntimeError if any check fails.
    """
    # Step 1: Manifest exists
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"Manifest not found: {MANIFEST_PATH}")
    
    # Step 2: Parse JSON
    try:
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Manifest JSON malformed: {e}")
    
    if "sha256" not in manifest_data or "signature" not in manifest_data:
        raise RuntimeError("Manifest missing required fields: sha256, signature")
    
    # Step 3: Compute wheel SHA256
    try:
        with open(wheel_path, "rb") as f:
            wheel_hash = hashlib.sha256()
            while True:
                chunk = f.read(65536)  # 64KB chunks
                if not chunk:
                    break
                wheel_hash.update(chunk)
        computed_sha256 = wheel_hash.hexdigest()
    except (OSError, IOError) as e:
        raise RuntimeError(f"Failed to read wheel file: {e}")
    
    # Step 4: Hash match
    manifest_sha256 = manifest_data["sha256"]
    if computed_sha256 != manifest_sha256:
        raise RuntimeError(
            f"Wheel SHA256 mismatch: expected {manifest_sha256}, got {computed_sha256}"
        )
    
    # Step 5: Decode signature
    try:
        sig_bytes = base64.b64decode(manifest_data["signature"])
    except Exception as e:
        raise RuntimeError(f"Signature base64 decode failed: {e}")
    
    # Step 6: Verify Ed25519 signature
    try:
        _manifest_pub_key.verify(sig_bytes, computed_sha256.encode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Signature verification failed: {e}")
```

### Integration into `_install_ee_wheel()`
```python
# Source: Phase 137 requirements

def _install_ee_wheel() -> bool:
    """Install the EE wheel from /tmp/ and apply source patches.
    
    Raises RuntimeError if manifest verification fails.
    Returns True if installation succeeded, False if wheel not found.
    """
    wheels = glob.glob("/tmp/axiom_ee-*.whl")
    if not wheels:
        logger.warning("No EE wheel found in /tmp/")
        return False
    
    wheel_path = wheels[0]
    logger.info("Installing EE wheel: %s", wheel_path)
    
    # NEW: Verify manifest before pip install
    try:
        _verify_wheel_manifest(wheel_path)
    except RuntimeError as e:
        logger.error("Manifest verification failed: %s", e)
        raise  # Propagate to activate_ee_live()
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--no-cache-dir", wheel_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        logger.error("EE wheel install failed: %s", e)
        return False
    
    # ... patch application logic ...
    return True
```

### Error Handling in `activate_ee_live()`
```python
# Source: Phase 137 integration point

async def activate_ee_live(app: Any, engine: Any) -> EEContext | None:
    """Install EE wheel, remove stubs, and load real EE plugins.
    
    Stores error message in app.state.ee_activation_error if activation fails.
    """
    existing = getattr(app.state, "ee", None)
    if existing and existing.foundry:
        logger.info("EE already active, skipping activation")
        return existing
    
    # Install wheel with manifest verification
    try:
        if not _install_ee_wheel():
            return None
    except RuntimeError as e:
        error_msg = str(e)
        app.state.ee_activation_error = error_msg
        logger.error("EE activation failed: %s", error_msg)
        return None
    
    # ... rest of plugin loading ...
    return ctx
```

### Updated `/admin/licence` Response
```python
# Source: main.py line 1184

async def get_licence_status(request: Request, current_user: User = Depends(require_auth)):
    """Returns current licence status. Requires authentication."""
    ls: Optional[LicenceState] = getattr(request.app.state, "licence_state", None)
    ee_error = getattr(request.app.state, "ee_activation_error", None)
    
    if ls is None:
        return {
            "status": "ce",
            "days_until_expiry": 0,
            "node_limit": 0,
            "tier": "ce",
            "customer_id": None,
            "grace_days": 0,
            "ee_activation_error": ee_error,  # NEW FIELD
        }
    
    return {
        "status": ls.status.value if hasattr(ls.status, "value") else str(ls.status),
        "days_until_expiry": ls.days_until_expiry,
        "node_limit": ls.node_limit,
        "tier": ls.tier,
        "customer_id": ls.customer_id,
        "grace_days": ls.grace_days,
        "ee_activation_error": ee_error,  # NEW FIELD
    }
```

## State of the Art

| Domain | Current Pattern | Phase 137 Alignment | Impact |
|--------|-----------------|-------------------|--------|
| Ed25519 signatures | `cryptography.hazmat.primitives.asymmetric.ed25519` used in `licence_service.py` | Reuse same library for manifest signatures | Consistent cryptography stack; no new dependencies |
| Public key PEM loading | Hardcoded `_LICENCE_PUBLIC_KEY_PEM` bytes literal in `licence_service.py` | Apply same pattern for `_MANIFEST_PUBLIC_KEY_PEM` | Tamper resistance; operator cannot swap keys without code change |
| SHA256 file hashing | Standard `hashlib.sha256()` with chunked I/O | Use same approach for wheel file | Well-tested, efficient, handles large files |
| Error propagation | `RuntimeError` raised, caught in caller | Manifest verification raises `RuntimeError` caught in `activate_ee_live()` | Consistent failure semantics across EE system |

**Deprecated/Outdated:**
- None — all patterns are current as of Phase 136 completion (2026-04-12)

## Open Questions

1. **Placeholder public key for testing (Phase 137)**
   - What we know: `_MANIFEST_PUBLIC_KEY_PEM` must be populated before Phase 137 ships; Phase 140 generates the real key and populates it at release time
   - What's unclear: Should Phase 137 tests use a generated test keypair inline, or reuse a fixed test key from `mop_validation/` fixtures?
   - Recommendation: Generate a test keypair inline in tests (e.g., `Ed25519PrivateKey.generate()`). This avoids file dependencies and makes tests self-contained. For the placeholder in `ee/__init__.py`, use a dummy key that will be replaced by Phase 140.

2. **Manifest path customization**
   - What we know: CONTEXT.md locks the path to `/tmp/axiom_ee.manifest.json`; module-level constant `MANIFEST_PATH` enables test patching
   - What's unclear: Should path be environment-variable configurable for non-standard deployments?
   - Recommendation: No — locked path is correct. Fixed path prevents confusion and simplifies the Phase 140 tool (knows exactly where to write the manifest).

3. **Signature algorithm flexibility for future phases**
   - What we know: Phase 137 uses Ed25519; Phase 140 generates Ed25519 keys
   - What's unclear: Could Phase 139 (entry point validation) or Phase 140 (wheel tool) require RSA or ECDSA alternatives?
   - Recommendation: No design flexibility needed for Phase 137. If future phases need different algorithms, they'll have their own keypairs and verification logic. Keep Phase 137 singular: Ed25519 only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in project) |
| Config file | `puppeteer/pyproject.toml` (pytest section, if needed) |
| Quick run command | `pytest puppeteer/tests/test_ee_manifest.py::test_manifest_valid_signature -xvs` |
| Full suite command | `pytest puppeteer/tests/test_ee_manifest.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-01 | Manifest file absence raises RuntimeError | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_manifest_missing -xvs` | ❌ Wave 0 |
| EE-01 | Malformed JSON raises RuntimeError | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_manifest_json_malformed -xvs` | ❌ Wave 0 |
| EE-01 | Missing required fields raises RuntimeError | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_manifest_missing_fields -xvs` | ❌ Wave 0 |
| EE-01 | SHA256 mismatch raises RuntimeError | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_wheel_sha256_mismatch -xvs` | ❌ Wave 0 |
| EE-01 | Invalid signature raises RuntimeError | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_signature_invalid -xvs` | ❌ Wave 0 |
| EE-01 | Valid manifest + signature allows install | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_manifest_valid_signature -xvs` | ❌ Wave 0 |
| EE-01 | RuntimeError caught in activate_ee_live() | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_activate_ee_live_catches_error -xvs` | ❌ Wave 0 |
| EE-01 | ee_activation_error field populated on failure | unit | `pytest puppeteer/tests/test_ee_manifest.py::test_ee_activation_error_in_state -xvs` | ❌ Wave 0 |
| EE-01 | `/admin/licence` response includes ee_activation_error | integration | `pytest puppeteer/tests/test_ee_manifest.py::test_licence_endpoint_shows_error -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest puppeteer/tests/test_ee_manifest.py -x` (fail fast on first error)
- **Per wave merge:** `pytest puppeteer/tests/test_ee_manifest.py -v` (all tests, verbose)
- **Phase gate:** Full suite green + manual validation of `/admin/licence` response before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_ee_manifest.py` — unit tests for all 9 EE-01 behaviors (manifest validation, signature verification, error propagation)
- [ ] `puppeteer/agent_service/ee/__init__.py` — new function `_verify_wheel_manifest()` + updated `_install_ee_wheel()` + updated `activate_ee_live()`
- [ ] `puppeteer/agent_service/models.py` (or `main.py`) — updated `LicenceState` or response model to include `ee_activation_error` field
- [ ] `puppeteer/agent_service/main.py` — updated `/admin/licence` route to return `ee_activation_error` field
- [ ] Placeholder public key in `ee/__init__.py` — test-friendly Ed25519 key that will be replaced by Phase 140

## Sources

### Primary (HIGH confidence)
- CONTEXT.md (Phase 137, dated 2026-04-12) — locked decisions on manifest format, verification flow, key pattern, error handling
- `puppeteer/agent_service/services/licence_service.py` (lines 1–44, 112–125) — established pattern for hardcoded PEM public key, Ed25519 signature verification via PyJWT
- `puppeteer/agent_service/ee/__init__.py` (lines 78–175) — current `_install_ee_wheel()` and `activate_ee_live()` implementations that Phase 137 modifies
- cryptography library documentation (context from project requirements.txt, PyJWT[crypto] 2.7.0+) — Ed25519 signature verification API
- Python standard library (hashlib, json, base64, pathlib) — no external docs needed; built-in

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` (lines 24–25) — EE-01 requirement statement
- `.planning/v22.0-ROADMAP.md` (Phase 137 section, lines 135–149) — phase success criteria and scope
- `.planning/STATE.md` (lines 49–51) — v22.0 milestone phase breakdown and dependencies

### Tertiary (LOW confidence)
- None — all critical decisions and patterns are verified in primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries (cryptography, PyJWT, hashlib, json, base64) are already in project requirements or Python stdlib. No new dependencies, no versions to verify.
- Architecture: HIGH — CONTEXT.md provides detailed locked decisions on manifest format, verification steps, key pattern, error handling. All integration points (activate_ee_live, /admin/licence endpoint) are present in current codebase.
- Pitfalls: MEDIUM — Drawn from common cryptographic integration mistakes (message encoding, base64 variants, hash mismatches) and project-specific patterns (RuntimeError propagation). Confidence lower because pitfall discovery depends on planning phase implementation choices.

**Research date:** 2026-04-12  
**Valid until:** 2026-04-26 (14 days — EE licence protection is stable domain; no major library updates expected; Phase 140 finalization may refine manifest format slightly)

---

**Research complete. Ready for planning.**

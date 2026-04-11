# Phase 131: Signature Verification Path Unification - Research

**Researched:** 2026-04-11
**Domain:** Backend signature verification and job creation service
**Confidence:** HIGH

## Summary

Phase 131 unifies the server-side countersigning logic for jobs into a single service method, eliminating code duplication between on-demand job creation (in `main.py` route handler) and scheduled job dispatch (in `scheduler_service._fire_job()`). The current implementation has an inline countersigning block in the route handler with nested imports, error handling, and partial signing key path resolution, while scheduled jobs silently skip countersigning and lack HMAC stamping for integrity verification. This phase consolidates these paths and fixes the missing SEC-02 HMAC protection for scheduled job fires.

**Primary recommendation:** Extract countersigning logic into `SignatureService.countersign_for_node(script_content: str) -> str` (returns base64 signature), call it from both paths, add exception handling at each call site (HTTP 500 for routes, fire_log status='signing_error' for scheduler), and stamp signature_hmac in scheduled job payloads using the same `compute_signature_hmac()` pattern used by on-demand jobs.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Extract countersigning into `SignatureService.countersign_for_node(script_content: str) -> str` — returns the server-signed base64 signature
- Both `main.py` `create_job()` route handler and `scheduler_service._fire_job()` call this single method
- `main.py` existing inline block (nested imports, dual-path key resolution, fallback logging) is replaced with a clean service call
- Signature logic lives in one place: `signature_service.py`

### Missing Signing Key Behavior — Hard Fail Everywhere
- `SignatureService.countersign_for_node()` raises an exception if `signing.key` is absent or unreadable
- **On-demand jobs**: catch the exception in `create_job()` route, return HTTP 500 with a clear message ("Server signing key unavailable — contact admin")
- **Scheduled jobs**: catch in `_fire_job()`, mark `fire_log.status = 'signing_error'`, write an audit log entry, and return without creating a `Job` — do NOT silently dispatch an unsigned payload
- This is a security boundary: dispatching without countersigning means nodes will always reject the job anyway, so silent continuation is strictly worse than failing loudly

### HMAC Integrity for Scheduled Job Fires — Fix in This Phase
- `scheduler_service._fire_job()` currently creates `Job` ORM objects directly and never stamps `signature_hmac`
- Fix: after countersigning, compute and set `new_job.signature_hmac` using `compute_signature_hmac(ENCRYPTION_KEY, signature_payload, signature_id, guid)` — same pattern as `job_service.create_job()`
- This ensures the SEC-02 dispatch-time HMAC check covers scheduled jobs, not just on-demand jobs

### Claude's Discretion
- Exact signing key path resolution logic inside `SignatureService.countersign_for_node()` (whether to keep the `/app/secrets/` + `secrets/` two-path fallback or canonicalize via an env var)
- Whether to add a startup health check warning when `signing.key` is absent
- Exact wording of HTTP 500 error message for missing key

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cryptography | 41.0.7+ | Ed25519 key loading and signing | Industry standard for asymmetric crypto; used by existing signature_service.py |
| SQLAlchemy | 2.0.0+ | ORM for Job/ScheduledFireLog persistence | Already in use throughout codebase; required for async job creation |
| Pydantic | v2 | Request/response model validation | Already in stack; used for JobCreate model |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| base64 | Python stdlib | Encoding/decoding binary signatures | Standard for transmitting binary data in text fields |
| hashlib | Python stdlib | HMAC-SHA256 computation | Already used in security.py for compute_signature_hmac |

**Installation:**
Cryptography and SQLAlchemy already in `puppeteer/requirements.txt`. No new dependencies.

## Architecture Patterns

### Recommended Project Structure

The unified countersigning pattern follows the existing service pattern in the codebase:

```
puppeteer/agent_service/
├── services/
│   ├── signature_service.py       # NEW: countersign_for_node() static method
│   ├── job_service.py              # Calls countersign_for_node() indirectly via route
│   └── scheduler_service.py        # Calls countersign_for_node() in _fire_job()
├── main.py                         # Route handler: catches exception, returns HTTP 500
└── security.py                     # compute_signature_hmac, ENCRYPTION_KEY (unchanged)
```

### Pattern 1: Unified Countersigning Service Method

**What:** A single static method in `SignatureService` that loads the server's Ed25519 signing key, signs the script content, and returns the base64-encoded signature. Raises an exception if the key is missing or unreadable.

**When to use:** Any place where a job script needs to be server-signed before dispatch (on-demand routes, scheduled job firing, future integration points).

**Example:**
```python
# In signature_service.py
class SignatureService:
    @staticmethod
    def countersign_for_node(script_content: str) -> str:
        """
        Server-signs a script with the Ed25519 private key.
        Returns base64-encoded signature ready for inclusion in job payload.
        
        Raises Exception if signing.key is absent or unreadable.
        """
        # Try production path first, fall back to dev path
        _signing_key_path = "/app/secrets/signing.key"
        if not os.path.exists(_signing_key_path):
            _signing_key_path = "secrets/signing.key"
        
        # Hard fail if key doesn't exist
        if not os.path.exists(_signing_key_path):
            raise FileNotFoundError("Server signing key unavailable (signing.key not found)")
        
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            import base64
            
            with open(_signing_key_path, "rb") as f:
                sk = serialization.load_pem_private_key(f.read(), password=None)
            
            # Normalize CRLF before signing (WIN-05 pattern from existing code)
            normalized_script = script_content.replace('\r\n', '\n').replace('\r', '\n')
            sig_bytes = sk.sign(normalized_script.encode("utf-8"))
            return base64.b64encode(sig_bytes).decode("ascii")
        except Exception as e:
            raise RuntimeError(f"Server countersigning failed: {e}") from e
```

### Pattern 2: Exception Handling at Call Sites

**What:** Each caller (route handler, scheduler) catches the exception raised by `countersign_for_node()` and handles it appropriately for its context.

**On-demand routes (main.py):**
```python
# In create_job() route handler
try:
    server_sig = SignatureService.countersign_for_node(script_content)
    payload_dict["signature"] = server_sig
except Exception as e:
    raise HTTPException(status_code=500, detail="Server signing key unavailable — contact admin")
```

**Scheduled job dispatcher (scheduler_service.py):**
```python
# In _fire_job() method
try:
    server_sig = SignatureService.countersign_for_node(script_content)
    payload_dict["signature"] = server_sig
except Exception as e:
    # Mark fire_log as signing_error and audit it
    fire_log.status = 'signing_error'
    try:
        from ..db import AuditLog
        session.add(AuditLog(
            username="scheduler",
            action="job:signing_error",
            resource_id=s_job.id,
            detail=json.dumps({"scheduled_job_id": s_job.id, "error": str(e)})
        ))
    except Exception:
        pass  # CE mode: AuditLog may be absent
    await session.commit()
    return  # Do not create Job
```

### Pattern 3: HMAC Stamping for Integrity

**What:** After countersigning in `_fire_job()`, compute and set the `signature_hmac` field on the new Job ORM object before persisting. This mirrors the existing pattern in `job_service.create_job()`.

**Example:**
```python
# In _fire_job() method, after countersigning
new_job = Job(
    guid=execution_guid,
    task_type="script",
    payload=json.dumps(payload_dict),
    status="PENDING",
    # ... other fields ...
)

# SEC-02: Stamp HMAC for integrity verification
if payload_dict.get("signature") and payload_dict.get("signature_id"):
    from ..security import compute_signature_hmac, ENCRYPTION_KEY
    new_job.signature_hmac = compute_signature_hmac(
        ENCRYPTION_KEY,
        payload_dict.get("signature"),  # signature_payload
        payload_dict.get("signature_id"),
        execution_guid
    )

session.add(new_job)
await session.commit()
```

### Anti-Patterns to Avoid
- **Inline countersigning in multiple locations:** Leads to maintenance burden, inconsistent error handling, and makes security boundary changes harder to audit. Always call the single service method.
- **Silent failures on missing signing key:** Previous code used fallback logging and continued. This phase treats missing key as a hard failure (security boundary). Nodes will reject unsigned payloads anyway, so silent dispatch is worse than loud failure.
- **Forgetting HMAC stamping in scheduled jobs:** SEC-02 HMAC check relies on this field being set. Scheduled jobs without HMAC could be tampered with during dispatch. Must be set for all signed payloads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 key loading and signing | Custom PEM parsing or key handling logic | `cryptography.hazmat.primitives` (already in requirements) | Mature, audited, handles key format edge cases (password-protected keys, PEM variants) |
| HMAC-SHA256 computation | Custom HMAC code | `security.compute_signature_hmac()` (already exists) | Constant-time comparison, standardized salt format, already tested in job_service.py |
| Signature payload encoding | Custom base64 handling | `base64.b64encode()` stdlib | Standard codec, handles edge cases, matches node.py decoding |
| Fire log status tracking | Custom status strings | Existing fire_log.status values ('fired', 'skipped_overlap', 'skipped_draft', 'signing_error') | Consistent with scheduler health endpoint, queryable via fire_log table |

**Key insight:** All the pieces exist in the codebase. This phase is refactoring and consolidation, not adding new crypto logic. The countersigning block in `main.py` is the reference implementation; the scheduler just needs to call the same service method.

## Common Pitfalls

### Pitfall 1: Forgetting CRLF Normalization During Countersigning
**What goes wrong:** Windows scripts with CRLF line endings (`\r\n`) will be signed differently than the normalized LF-only version. If the node normalizes CRLF before verification but the server signed the non-normalized version, signature verification will fail.

**Why it happens:** The WIN-05 normalization is already in the `create_job()` route handler (line 1463-1467 in main.py) but wasn't part of the scheduler's countersigning path. Copy-paste errors or incomplete refactoring can miss this.

**How to avoid:** Always normalize script_content in the service method before signing:
```python
normalized_script = script_content.replace('\r\n', '\n').replace('\r', '\n')
sig_bytes = sk.sign(normalized_script.encode("utf-8"))
```

**Warning signs:** Platform-specific signature failures (jobs from Windows tools fail, Linux tools pass); "signature verification failed" errors in node logs that appear only for certain script origins.

### Pitfall 2: HMAC Stamping Only for User-Signed Payloads
**What goes wrong:** The existing code in `job_service.create_job()` stamps HMAC only if BOTH `signature_payload` and `signature_id` are present (lines 571-572). If a scheduled job is created without these fields, the HMAC is skipped, and the SEC-02 dispatch-time check can't validate integrity.

**Why it happens:** Copy-paste from job_service without reading the conditional logic closely.

**How to avoid:** Ensure all signed payloads (including scheduled jobs) set both signature_payload and signature_id in their payload_dict. Then stamp HMAC unconditionally if these fields are present.

**Warning signs:** Job completions succeed but nodes report "HMAC mismatch" or "integrity check failed"; scheduled jobs sometimes work and sometimes fail (non-deterministic).

### Pitfall 3: Catching Exception Too Broadly in Scheduler
**What goes wrong:** If the scheduler catches `Exception` but then continues to create the Job anyway, the unsigned job will be dispatched and nodes will reject it. The fire_log might show 'fired' (success) when it actually failed.

**Why it happens:** Incomplete refactoring — catching the exception but forgetting to return early.

**How to avoid:** The CONTEXT.md specifies: catch exception, set fire_log.status = 'signing_error', audit it, and `return` without creating the Job. This pattern must be exact.

**Warning signs:** Fire logs show 'fired' but subsequent Job creation shows unsigned payloads; nodes reject jobs with "missing signature" even though fire_log says job was fired.

### Pitfall 4: Inconsistent Signing Key Path Resolution
**What goes wrong:** The scheduler resolves the key path differently than the on-demand route, or uses an environment variable only in one place. This creates two different code paths for the same security operation.

**Why it happens:** CONTEXT.md says "exact signing key path resolution logic inside SignatureService.countersign_for_node() ... whether to keep the `/app/secrets/` + `secrets/` two-path fallback or canonicalize via an env var". The service method should be the single source of truth.

**How to avoid:** Put ALL key path resolution in the service method. Both callers use the same method, so they both get the same path logic. No special cases in route or scheduler.

**Warning signs:** Different errors from scheduled vs. on-demand job creation when signing key is missing; contradictory error messages from different call sites.

## Code Examples

Verified patterns from existing codebase:

### Example 1: Ed25519 Signing Pattern (from main.py lines 1489-1494)
```python
# Source: puppeteer/agent_service/main.py lines 1489-1494
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

_signing_key_path = "/app/secrets/signing.key"
if not os.path.exists(_signing_key_path):
    _signing_key_path = "secrets/signing.key"

with open(_signing_key_path, "rb") as _f:
    _sk = serialization.load_pem_private_key(_f.read(), password=None)

_server_sig = base64.b64encode(_sk.sign(script_content.encode("utf-8"))).decode("ascii")
```

### Example 2: HMAC Stamping Pattern (from job_service.py lines 563-572)
```python
# Source: puppeteer/agent_service/services/job_service.py lines 563-572
from ..security import compute_signature_hmac, ENCRYPTION_KEY

# SEC-02: Stamp HMAC tag on signature_payload before persisting
_sig_payload = payload_dict.get("signature_payload")
_sig_id = payload_dict.get("signature_id")

if _sig_payload and _sig_id:
    new_job.signature_hmac = compute_signature_hmac(
        ENCRYPTION_KEY, _sig_payload, _sig_id, guid
    )
```

### Example 3: Fire Log Status Pattern (from scheduler_service.py lines 290-291)
```python
# Source: puppeteer/agent_service/services/scheduler_service.py lines 290-291
fire_log.status = 'skipped_overlap'
await session.commit()
```

### Example 4: Signature Verification Pattern (from signature_service.py lines 67-82)
```python
# Source: puppeteer/agent_service/services/signature_service.py lines 67-82
@staticmethod
def verify_payload_signature(public_key_pem: str, signature_b64: str, payload: str) -> bool:
    """
    Validates an Ed25519 signature against a payload using the provided PEM public key.
    Returns True if valid, raises Exception otherwise.
    """
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Only Ed25519 signatures are currently supported")
        sig_bytes = base64.b64decode(signature_b64)
        public_key.verify(sig_bytes, payload.encode('utf-8'))
        return True
    except Exception as e:
        logger.error(f"Signature Verification Failed: {e}")
        raise e
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline countersigning in route handlers | Unified service method | Phase 131 | Maintenance centralization, security boundary clarity, consistent error handling |
| Silent fallback on missing signing key | Hard fail with clear error | Phase 131 | Security: prevents unsigned job dispatch, easier operator debugging |
| Scheduled jobs skip countersigning | Scheduled jobs call countersign_for_node() | Phase 131 | Security: all jobs server-signed, consistent dispatch path |
| Scheduled jobs missing HMAC stamp | All signed jobs stamped with HMAC | Phase 131 | Integrity: dispatch-time tampering detection covers all job types |

**Deprecated/outdated:**
- Inline imports in route handlers (ed25519, serialization, base64 inline in create_job): Consolidated into service method, reducing cognitive load
- Fallback logging on signing failure: Replaced with exception propagation and explicit error handling at call sites

## Open Questions

1. **Startup Health Check for Missing Signing Key**
   - What we know: CONTEXT.md marks this as Claude's discretion
   - What's unclear: Should the server log a warning at startup if signing.key is absent, or only fail when a signed job is attempted?
   - Recommendation: Add a startup health check that logs WARNING if signing.key is absent. This gives operators visibility into misconfiguration before job dispatch fails. Don't block startup (signing.key may be injected later), but warn clearly.

2. **Canonicalization of Signing Key Path**
   - What we know: Current code has a two-path fallback (/app/secrets/ for production, secrets/ for local dev)
   - What's unclear: Should this be canonicalized via an environment variable (e.g., SIGNING_KEY_PATH)?
   - Recommendation: Keep the dual-path fallback for now. It's a stable pattern used elsewhere in the codebase (e.g., verification.key paths in signature_service.py line 16). Avoid env var proliferation.

3. **Error Message Wording for HTTP 500**
   - What we know: CONTEXT.md specifies "Server signing key unavailable — contact admin"
   - What's unclear: Should the error message include a link to docs or suggest common fixes?
   - Recommendation: Keep it simple: "Server signing key unavailable — contact admin". Operators can consult deployment guides or admin docs for signing.key setup.

## Validation Architecture

> This section covers test infrastructure needed to verify Phase 131 implementation.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing suite in `puppeteer/tests/`) |
| Config file | `puppeteer/pytest.ini` |
| Quick run command | `cd puppeteer && pytest tests/test_signature_service.py -xvs` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

Phase 131 has no formal requirements from REQUIREMENTS.md (indicated by empty spec), but must address these technical acceptance criteria from CONTEXT.md:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| countersign_for_node() returns base64 signature when key exists | unit | `pytest tests/test_signature_service.py::test_countersign_for_node_success -xvs` | ❌ Wave 0 |
| countersign_for_node() raises exception when key missing | unit | `pytest tests/test_signature_service.py::test_countersign_for_node_missing_key -xvs` | ❌ Wave 0 |
| create_job() route catches countersign exception and returns HTTP 500 | integration | `pytest tests/test_main.py::test_create_job_signing_key_missing -xvs` | ❌ Wave 0 |
| _fire_job() catches countersign exception and sets fire_log.status='signing_error' | integration | `pytest tests/test_scheduler_service.py::test_fire_job_signing_error -xvs` | ❌ Wave 0 |
| _fire_job() stamps signature_hmac on new_job before persist | unit | `pytest tests/test_scheduler_service.py::test_fire_job_hmac_stamp -xvs` | ❌ Wave 0 |
| Scheduled job payload includes normalized script (CRLF → LF) | unit | `pytest tests/test_scheduler_service.py::test_fire_job_crlf_normalization -xvs` | ❌ Wave 0 |
| HMAC stamp matches on-demand job pattern (same compute_signature_hmac call) | unit | `pytest tests/test_scheduler_service.py::test_fire_job_hmac_matches_on_demand -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_signature_service.py tests/test_scheduler_service.py -x`
- **Per wave merge:** Full pytest suite (`cd puppeteer && pytest`) — must pass all 62+ existing tests plus new Phase 131 tests
- **Phase gate:** Full suite green + manual verification of fire_log audit entries for signing_error cases

### Wave 0 Gaps
- [ ] `tests/test_signature_service.py` — new test file for countersign_for_node() method (6 test cases)
- [ ] `tests/test_scheduler_service.py` — add 3 new test cases for HMAC stamping and signing error handling
- [ ] `tests/test_main.py` — add 1 new test case for route-level exception handling (HTTP 500)
- [ ] `conftest.py` — add fixture for mock signing.key file (temporary temp file with valid Ed25519 private key)

*(Test infrastructure will be created during planning; research documents the gaps.)*

## Sources

### Primary (HIGH confidence)
- Context7: puppeteer/agent_service/services/signature_service.py (verify_payload_signature pattern, _VERIFICATION_KEY_PATHS)
- Context7: puppeteer/agent_service/services/job_service.py (HMAC stamping pattern lines 563-572, parse_bytes helper)
- Context7: puppeteer/agent_service/services/scheduler_service.py (execute_scheduled_job and _fire_job pattern, fire_log status tracking)
- Context7: puppeteer/agent_service/main.py (countersigning block lines 1481-1501, exception handling pattern)
- Context7: puppeteer/agent_service/security.py (compute_signature_hmac, verify_signature_hmac functions)
- Context7: puppeteer/agent_service/db.py (Job ORM model, signature_hmac column, ScheduledFireLog model)
- Context7: CONTEXT.md (Phase 131 locked decisions and discretion areas)

### Secondary (MEDIUM confidence)
- Existing test patterns in `puppeteer/tests/test_signature_service.py` (if exists) — test structure and assertion style
- Cryptography library documentation (https://cryptography.io/hazmat/primitives/asymmetric/ed25519/) — Ed25519 key loading and signing API

### Tertiary (LOW confidence)
- None — all critical findings verified against Context7 and codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — cryptography, SQLAlchemy, base64, hashlib all verified in requirements.txt and active codebase
- Architecture: HIGH — service pattern, exception handling, HMAC stamping all documented in existing code with clear examples
- Pitfalls: HIGH — drawn from code inspection and CONTEXT.md discussion outcomes
- Validation: MEDIUM — pytest infrastructure exists, but Phase 131 test cases are new (will be created during planning)

**Research date:** 2026-04-11
**Valid until:** 2026-04-25 (14 days — backend code is stable, no fast-moving dependencies)

**Assumptions:**
- `signing.key` is a valid Ed25519 private key in PEM format (matches verify_payload_signature pattern)
- ENCRYPTION_KEY is available in security.py and imported by scheduler_service (already verified)
- job_service.create_job() HMAC stamping pattern is the authoritative reference (verified in code)
- Fire log status values ('fired', 'skipped_overlap', 'skipped_draft', 'signing_error') follow existing pattern

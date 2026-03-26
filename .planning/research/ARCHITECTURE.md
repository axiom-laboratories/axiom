# Architecture Research

**Domain:** Security hardening + EE licence key system for a FastAPI/React job orchestrator
**Researched:** 2026-03-26
**Confidence:** HIGH — based on direct codebase inspection of security.py, main.py, vault_service.py, ee/__init__.py

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Puppeteer (Control Plane)                       │
│                                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐  │
│  │  main.py     │   │  security.py │   │  ee/__init__.py          │  │
│  │  FastAPI app │   │  Fernet +    │   │  EEContext dataclass     │  │
│  │  lifespan    │──▶│  HMAC +      │   │  load_ee_plugins()       │  │
│  │  licence     │   │  node secret │   │  _mount_ce_stubs()       │  │
│  │  bootstrap   │   │  + ReDoS fix │   └──────────────────────────┘  │
│  └──────┬───────┘   └──────────────┘             ▲                    │
│         │                                         │                   │
│         │          ┌──────────────────────────────┘                   │
│         │          │  licence_service.py (NEW)                        │
│         ▼          │  Ed25519 verify + expiry + boot-log              │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │                    services/                                   │    │
│  │  job_service   scheduler_service   vault_service (patched)    │    │
│  │  signature_service   pki_service   foundry_service            │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐    │
│  │  db.py (SQLAlchemy ORM)  │   │  auth.py (JWT / bcrypt)        │    │
│  │  SQLite dev / Postgres   │   │  deps.py (permission cache)    │    │
│  └──────────────────────────┘   └────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                        │  mTLS (client cert only — API_KEY removed)
              ┌─────────▼──────────┐
              │   Puppet Nodes      │
              │   environment_service/node.py                           │
              │   polls /work/pull  │
              └────────────────────┘

tools/
└── generate_licence.py (NEW — offline admin CLI, never runs in-process)
```

---

## Component Responsibilities

| Component | Responsibility | Status for v14.3 |
|-----------|----------------|------------------|
| `main.py` lifespan | Startup orchestration: DB init, licence parse, EE load, admin bootstrap, scheduler | Modified — refactor inlined licence block to call `licence_service.validate()` |
| `main.py` device-approve route | Serves OAuth device approval HTML page | Modified — escape `user_code` to fix XSS |
| `main.py` node routes | `/work/pull`, `/heartbeat`, `/work/{guid}/result` | Modified — remove `Depends(verify_api_key)` from all three |
| `security.py` | Fernet cipher, HMAC helpers, node secret verifier, PII masker | Modified — remove `API_KEY` crash + `verify_api_key`, fix ReDoS in `mask_pii` |
| `vault_service.py` | File-based artifact store in `/app/vault/` | Modified — add `_safe_path()` confinement to fix path injection |
| `ee/__init__.py` | EE plugin loader, CE stub mounter | Unchanged — existing gate pattern is correct |
| `services/licence_service.py` | Ed25519 signature verify, expiry check, boot-log monotonicity | NEW |
| `tools/generate_licence.py` | Offline admin CLI: sign JSON payload → base64url key blob | NEW |
| `secrets/boot.log` | HMAC-signed boot timestamp, written per-startup | New artefact (not a code file) |

---

## Recommended Project Structure (Changes Only)

```
puppeteer/
├── agent_service/
│   ├── main.py                    # MODIFIED: remove API_KEY import (line 44),
│   │                              #   remove Depends(verify_api_key) × 3 (lines 1225/1234/1241),
│   │                              #   escape user_code in device-approve HTML (lines 601/603)
│   ├── security.py                # MODIFIED: remove API_KEY hard-crash (lines 16-21),
│   │                              #   remove verify_api_key function (lines 104-108),
│   │                              #   fix mask_pii ReDoS (lines 89-90)
│   └── services/
│       ├── vault_service.py       # MODIFIED: add _safe_path() to store_artifact + delete_artifact
│       └── licence_service.py     # NEW: validate(), LicenceResult dataclass, boot_log helpers

tools/
└── generate_licence.py            # NEW: offline Ed25519 signing CLI
```

### Structure Rationale

- **`security.py` for API_KEY removal first:** The crash is at module import time. Fixing `security.py` unblocks everything downstream — any test or import that touches `security.py` currently requires `API_KEY` in the environment.
- **`services/licence_service.py` (new):** The current inlined licence block in the lifespan (main.py lines 76-102) is a structural stub — it decodes base64 and checks `exp` but does not verify the Ed25519 signature. Extracting to a service keeps the lifespan readable, enables unit tests, and separates concerns cleanly.
- **`tools/generate_licence.py` (new):** Generation must never run inside the server process because it requires the private signing key. A standalone CLI in `tools/` mirrors the existing `admin_signer.py` pattern from `toms_home/.agents/tools/`. Output format must be agreed before `licence_service.py` is built.

---

## Architectural Patterns

### Pattern 1: Inline Startup Validation — Current State (Incomplete)

**What:** The lifespan block in `main.py` (lines 76-102) decodes `AXIOM_LICENCE_KEY` from env, base64-decodes the first segment, parses JSON, and checks `exp > time.time()`. If the check passes, `app.state.licence` is set and `load_ee_plugins()` is called.

**Current gap:** Only the `exp` timestamp is checked. There is no Ed25519 signature verification — a customer can forge any `exp` value and the server accepts it. The implementation satisfies the startup-gate UI requirement but not the tamper-resistance requirement.

**What to add in v14.3:**
- Ed25519 signature verification before accepting the payload
- Move logic to `licence_service.validate()` (see Pattern 2)
- Add boot-log monotonicity check (see Pattern 3)

### Pattern 2: Structured Licence Validation Service (New)

**What:** `services/licence_service.py` owns all licence concerns. Lifespan calls `licence_service.validate(key_string)` and receives a typed `LicenceResult`.

**Key format (matches existing `generate_licence.py` conventions, also used by `admin_signer.py`):**
```
<base64url-payload>.<base64url-signature>
```
Where `payload` is `json.dumps({customer_id, tier, node_limit, exp, issued_at, features})` encoded as UTF-8 bytes.

**Validation flow:**
```python
# services/licence_service.py

@dataclass
class LicenceResult:
    valid: bool
    data: dict | None
    reason: str

AXIOM_EE_PUBLIC_KEY_BYTES = b"..."  # embedded at build time, not configurable

def validate(key_string: str) -> LicenceResult:
    parts = key_string.strip().split(".")
    if len(parts) != 2:
        return LicenceResult(False, None, "malformed key")
    payload_bytes = base64.urlsafe_b64decode(pad(parts[0]))
    sig_bytes     = base64.urlsafe_b64decode(pad(parts[1]))
    try:
        verify_key = VerifyKey(AXIOM_EE_PUBLIC_KEY_BYTES)  # nacl or cryptography
        verify_key.verify(payload_bytes, sig_bytes)
    except BadSignatureError:
        return LicenceResult(False, None, "signature invalid")
    data = json.loads(payload_bytes)
    if data.get("exp", 0) < time.time():
        return LicenceResult(False, data, "expired")
    boot_log.record_and_verify(datetime.utcnow())  # side effect
    return LicenceResult(True, data, "ok")
```

**Lifespan integration (replaces lines 76-102 of main.py):**
```python
from .services.licence_service import licence_service
result = licence_service.validate(os.getenv("AXIOM_LICENCE_KEY", ""))
if result.valid:
    app.state.licence = result.data
    app.state.ee = await load_ee_plugins(app, engine)
else:
    logger.warning(f"EE licence invalid ({result.reason}) — running in CE mode")
    ctx = EEContext()
    _mount_ce_stubs(app)
    app.state.ee = ctx
```

### Pattern 3: HMAC-Signed Boot-Log for Air-Gap Expiry Enforcement

**What:** On each startup, `licence_service` writes the current UTC time to `/app/secrets/boot.log` in a tamper-evident format. On the next startup, it reads the file, verifies the HMAC, and asserts the new time is >= the last recorded time. A clock-rollback attempt is detectable.

**Boot-log format:**
```json
{"boot_time": "2026-03-26T08:00:00Z", "hmac": "<sha256-hex>"}
```

HMAC is `hmac.new(ENCRYPTION_KEY, boot_time_bytes, hashlib.sha256).hexdigest()` — reuses the existing `ENCRYPTION_KEY` already available as `cipher_suite`'s backing key in `security.py`.

**Rollback handling:** Log a warning, degrade to CE mode (do not crash). In a genuinely air-gapped deployment, the operator may have legitimately restored from backup — a hard crash would be destructive. The warning is enough to flag the anomaly for the audit log.

**Boot-log file location:** `/app/secrets/boot.log` — same directory as `cert.pem`, `key.pem`, and `ca.pem`. Already volume-mounted and persistent across container restarts.

**Non-air-gap behaviour:** Identical. The boot-log check is always-on and adds < 1ms to startup time.

### Pattern 4: Path Confinement (vault_service.py Fix)

**What:** Before any file operation using an `artifact_id`, resolve the full path and assert it is within `/app/vault/`.

**Affected calls in `vault_service.py`:**
- Line 21: `file_path = os.path.join(VAULT_DIR, artifact_id)` — used in `store_artifact`
- Line 70: `file_path = VaultService.get_artifact_path(artifact_id)` — used in `delete_artifact`
- `get_artifact_path()` itself (line 52-54): `os.path.join(VAULT_DIR, artifact_id)` returned as-is

**Fix pattern:**
```python
from pathlib import Path

_VAULT_BASE = Path(VAULT_DIR).resolve()

def _safe_artifact_path(artifact_id: str) -> Path:
    candidate = (_VAULT_BASE / artifact_id).resolve()
    if _VAULT_BASE not in candidate.parents and candidate != _VAULT_BASE:
        raise ValueError(f"Path traversal attempt blocked: {artifact_id!r}")
    return candidate
```

Note: `artifact_id` is a UUID generated server-side (`str(uuid.uuid4())`), so in practice traversal is not reachable via normal use. CodeQL flags it because `file.filename` (user-supplied) is in scope in the same function. The fix satisfies the scanner and is correct defence-in-depth regardless.

### Pattern 5: XSS Prevention — HTML Escaping User-Reflected Query Params

**What:** `GET /auth/device/approve?user_code=...` reflects `user_code` directly into an HTML f-string at lines 601 and 603. Two injection points exist: the visible `<div class="code">` and the hidden `<input value="...">` attributes.

**Fix:**
```python
import html as _html

@app.get("/auth/device/approve", response_class=HTMLResponse)
async def device_approve_page(user_code: str = ""):
    safe_code = _html.escape(user_code or "(no code provided)")
    # use {safe_code} everywhere {user_code} appears in the f-string
```

`html.escape()` is Python stdlib — no new dependency. It replaces `<`, `>`, `&`, `"`, `'` with HTML entities, preventing both tag injection and attribute-breaking.

### Pattern 6: ReDoS Prevention — Bounded Regex + Length Guard

**What:** `mask_pii()` in `security.py` uses an unbounded email regex on lines 89-90:
```python
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
```
The trailing `[a-zA-Z0-9-.]+` allows catastrophic backtracking on inputs like `aaaa@b.` with a long trailing string.

**Fix (two-part):**
1. Add a length pre-check before any regex call: `if len(data) > 2048: return data`
2. Add an upper bound to the domain part: `[a-zA-Z0-9-.]{1,253}` — the max DNS name length is 253 characters, which eliminates unbounded matching.

No new dependency. No behaviour change for valid inputs.

---

## Data Flow

### Licence Validation Flow (Target State)

```
Server startup (lifespan in main.py)
    │
    ├── init_db()
    │
    ├── licence_service.validate(os.getenv("AXIOM_LICENCE_KEY", ""))
    │       │
    │       ├── split key into payload_b64 + sig_b64
    │       ├── base64url decode both parts
    │       ├── Ed25519.verify(AXIOM_EE_PUBLIC_KEY, sig, payload_bytes)
    │       │       └── BadSignatureError → return LicenceResult(valid=False, reason="signature invalid")
    │       ├── json.parse(payload_bytes) → {customer_id, tier, exp, node_limit, features}
    │       ├── check exp > time.time()
    │       │       └── expired → return LicenceResult(valid=False, data=data, reason="expired")
    │       └── boot_log.record_and_verify(now)
    │               ├── read /app/secrets/boot.log (if exists)
    │               ├── verify HMAC of stored timestamp
    │               ├── assert new_time >= last_recorded_time
    │               │       └── clock rollback → log warning, continue (degrade to CE on rollback)
    │               └── write new timestamp + HMAC to /app/secrets/boot.log
    │
    ├── if result.valid:
    │       app.state.licence = result.data
    │       load_ee_plugins(app, engine)  → all EE routes active
    └── else:
            EEContext(all False)
            _mount_ce_stubs(app)  → all EE routes return 402
```

### Node Authentication Flow (After API_KEY Removal)

```
Node POST /work/pull
    │
    ├── verify_node_secret (Depends) — SOLE auth mechanism
    │       ├── X-Node-Id header → db.execute(select(Node).where(node_id == ...))
    │       ├── check node.status != "REVOKED" → 403 if revoked
    │       ├── verify X-Machine-Id matches node.machine_id → 403 on mismatch
    │       └── verify X-Node-Secret-Hash matches node.node_secret_hash → 403 on mismatch
    │
    └── JobService.pull_work(node_id, node_ip, db)

[verify_api_key step removed — no longer present]
```

### Vault Path Confinement Flow (After Fix)

```
DELETE /api/vault/{artifact_id}
    │
    ├── artifact_id parameter (e.g. "a3c4e2f1-0000-...")
    │
    ├── _safe_artifact_path(artifact_id)
    │       ├── candidate = Path("/app/vault/" + artifact_id).resolve()
    │       ├── assert /app/vault is a parent of candidate
    │       └── raise ValueError + HTTP 400 on traversal attempt
    │
    └── os.remove(candidate)
```

---

## Integration Points

### New vs Modified — Explicit List

#### New (create from scratch)

| File | Purpose |
|------|---------|
| `puppeteer/agent_service/services/licence_service.py` | Ed25519 verify, expiry check, boot-log monotonicity, `LicenceResult` dataclass |
| `tools/generate_licence.py` | Offline admin CLI: inputs customer metadata, outputs base64url licence key blob |

#### Modified (targeted changes to existing files)

| File | Change | Lines |
|------|--------|-------|
| `security.py` | Remove `API_KEY` import-time crash | 16-21 |
| `security.py` | Remove `verify_api_key` function | 104-108 |
| `security.py` | Fix `mask_pii` ReDoS — length guard + bounded domain regex | 89-90 |
| `main.py` | Remove `verify_api_key, API_KEY` from security import | 44 |
| `main.py` | Remove `Depends(verify_api_key)` from `pull_work` | 1225 |
| `main.py` | Remove `Depends(verify_api_key)` from `receive_heartbeat` | 1234 |
| `main.py` | Remove `Depends(verify_api_key)` from `report_result` | 1241 |
| `main.py` | Escape `user_code` in device-approve HTML f-string | 601, 603 |
| `main.py` | Replace inlined licence block with `licence_service.validate()` call | 76-102 |
| `vault_service.py` | Add `_safe_artifact_path()` and use in `store_artifact` + `delete_artifact` | 21, 70-72 |

**Note on main.py line 2457/2461 from the todo:** The current `main.py` is 2152 lines. The todo's line numbers refer to a prior version. Verify the remaining path-injection alerts by running CodeQL or checking the live GitHub Security tab — do not assume the line numbers are current.

#### Unchanged

| File | Reason |
|------|--------|
| `ee/__init__.py` | Existing gate pattern is correct; licence validation stays in CE code |
| `auth.py` | JWT mechanism unaffected |
| `deps.py` | Permission cache unaffected |
| `db.py` | No schema changes required |
| `services/signature_service.py` | Ed25519 primitives already available — `licence_service.py` can import from here or use `cryptography` directly |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `main.py` lifespan → `licence_service` | Direct sync call, returns `LicenceResult` | One call per server startup |
| `licence_service` → `ee/__init__.py` | `result.valid` bool gates `load_ee_plugins()` — existing pattern unchanged | |
| `licence_service` → filesystem | Reads/writes `/app/secrets/boot.log` using `_safe_path()` pattern internally | Path is server-controlled, not user input |
| `tools/generate_licence.py` → operator | Standalone CLI, private key on operator's machine only — no server connection | Follows `admin_signer.py` model |
| `vault_service.py` → filesystem | All artifact paths go through `_safe_artifact_path()` | Fixes CodeQL alerts 82-83 |

### Where Does the Licence Key Live?

**Recommendation: `AXIOM_LICENCE_KEY` environment variable in `secrets.env`.**

This is already implemented (`os.getenv("AXIOM_LICENCE_KEY")`). It is consistent with all other sensitive config in the project (`SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`). For air-gapped installs, the operator copies the base64url blob into `secrets.env` manually — no network required. Survives DB wipes.

Do not store in the DB `Config` table — Config is wiped during hard teardowns and is operator-mutable without a restart.

### What Happens on Licence Expiry?

**Recommendation: Degrade to CE feature set — do not crash.**

Existing behaviour when `_licence_valid = False`: CE stubs are mounted (all EE routes return 402). Jobs keep running. Nodes keep checking in. The dashboard EE badge shows "CE". This is the correct behaviour — a hard stop would violate the reliability contract for air-gapped operators who cannot renew quickly.

---

## Build Order Recommendation

The three workstreams are independent except for one constraint: **API_KEY removal must happen before any test update**, because tests currently send `X-API-Key` headers to the three node routes.

```
Step 1 — CodeQL Fixes (no inter-dependencies, highest urgency)
    ├── security.py: fix mask_pii ReDoS (length check + bounded domain regex)
    ├── main.py: fix XSS in device-approve (html.escape on user_code)
    ├── vault_service.py: add _safe_artifact_path(), apply to store + delete
    └── main.py: verify remaining path-injection alerts via live CodeQL scan
            (todo line numbers 2457/2461 have drifted — file is now 2152 lines)

Step 2 — API_KEY Removal (cleanup, no new behaviour)
    ├── security.py: remove API_KEY crash block + verify_api_key function
    ├── main.py: remove import + 3x Depends(verify_api_key)
    └── tests: remove X-API-Key header from any test that sets it

Step 3 — Licence CLI (offline tool, no server deps)
    ├── tools/generate_licence.py: Ed25519 sign JSON payload → base64url blob
    ├── define and document the exact wire format (payload schema + encoding)
    └── generate a test key for use in integration tests

Step 4 — Licence Service (depends on Step 3 format definition)
    ├── services/licence_service.py: validate(), LicenceResult, boot_log helpers
    ├── embed AXIOM_EE_PUBLIC_KEY_BYTES (the verification key) as a constant
    └── unit tests: valid key, forged key, expired key, missing key, clock rollback

Step 5 — Wire and Integration Test
    ├── main.py lifespan: replace inline block with licence_service.validate()
    ├── run CE validation scenario (no licence key → all EE routes 402)
    └── run EE validation scenario (valid test key → all EE routes active)
```

---

## Anti-Patterns

### Anti-Pattern 1: Validating Licence Inside the EE Plugin

**What people do:** Move licence validation into `axiom-ee`'s `register()` method so the EE package owns the check.

**Why it's wrong:** The CE codebase must gate EE *loading* on licence validity. If validation runs inside `register()`, EE tables, routes, and services are already registered before the check — there is no clean way to un-register them on failure.

**Do this instead:** Validate in `licence_service.py` (CE code). Gate `load_ee_plugins()` on the bool result. The EE plugin does not re-validate.

### Anti-Pattern 2: Using `os.path.join` Without `.resolve()`

**What people do:** `os.path.join(BASE_DIR, user_input)` and consider it safe.

**Why it's wrong:** `os.path.join("/app/vault", "../../etc/passwd")` returns `"/app/vault/../../etc/passwd"` as a string. `open()` follows the traversal. Only `Path.resolve()` collapses `../` sequences.

**Do this instead:** Always `Path(base / user_input).resolve()` and assert the result starts with (or equals) the resolved base before passing to any file operation.

### Anti-Pattern 3: Generating Licences Inside the Server Process

**What people do:** Add `POST /admin/generate-licence` so admins can create keys through the UI.

**Why it's wrong:** The private signing key would need to exist in the server environment. Any RCE or path traversal exploit could exfiltrate it, allowing licence forgery.

**Do this instead:** Generation is always offline via `tools/generate_licence.py` on the admin's local machine. The server only holds the embedded public verification key.

### Anti-Pattern 4: Storing the Licence Key in the Database

**What people do:** Store `AXIOM_LICENCE_KEY` in the `Config` key-value table for runtime updatability.

**Why it's wrong:** DB content is operator-mutable without audit trail. The Config table is wiped during hard teardowns. An admin could swap in a forged key via the admin UI without a server restart.

**Do this instead:** `AXIOM_LICENCE_KEY` in `secrets.env`. Read-only at startup. Cannot be changed without a restart — which triggers the boot-log check and creates an audit trail.

### Anti-Pattern 5: Hard-Crashing on Expired or Missing Licence

**What people do:** `sys.exit(1)` in lifespan if `AXIOM_LICENCE_KEY` is absent or expired.

**Why it's wrong:** CE deployments legitimately have no licence key. Air-gapped EE customers may not be able to renew before expiry in an emergency window. A crash loop would take down production job execution.

**Do this instead:** Absent/expired/invalid licence → degrade to CE feature set. Log a warning. Let the dashboard EE badge communicate the status to operators.

---

## Scaling Considerations

All v14.3 changes are single-node startup-time or request-path concerns. None affect horizontal scaling:

| Concern | Impact |
|---------|--------|
| Ed25519 licence verification | ~100 µs at startup, once. Zero per-request cost. |
| Boot-log file write | One file write per startup. Negligible I/O. |
| ReDoS fix | Reduces worst-case CPU under malicious input. Improves reliability. |
| Path confinement | One `Path.resolve()` per vault operation. Negligible. |
| API_KEY removal | Removes one unnecessary `Depends()` from three hot node routes. Minor latency improvement. |
| XSS fix | One `html.escape()` call per device-approve page load. Negligible. |

---

## Sources

- Direct codebase inspection (HIGH confidence):
  - `puppeteer/agent_service/security.py` — API_KEY crash, verify_api_key, mask_pii regex
  - `puppeteer/agent_service/main.py` — lifespan licence block (lines 71-102), device-approve XSS (lines 575-628), node routes with verify_api_key (lines 1224-1250)
  - `puppeteer/agent_service/services/vault_service.py` — path injection at lines 21, 70-72
  - `puppeteer/agent_service/ee/__init__.py` — EEContext, load_ee_plugins, _mount_ce_stubs
- Todo files (HIGH confidence — authored from CodeQL scan output):
  - `.planning/todos/pending/2026-03-26-fix-code-scanning-alerts-xss-path-injection-redos.md`
  - `.planning/todos/pending/2026-03-26-license-key-generation-and-validation-with-airgap-support.md`
  - `.planning/todos/pending/2026-03-26-remove-legacy-api-key-requirement.md`
- Project history: `.planning/PROJECT.md` — v11.0 EE entry_points architecture, v12.0 SEC-02 HMAC pattern, v14.1 CE execution stubs, v11.1 licence startup-gating validation
- Python stdlib: `pathlib.Path.resolve()`, `html.escape()`, `hmac.compare_digest()`, `re` module ReDoS behaviour
- CodeQL rules: `py/reflective-xss`, `py/path-injection`, `py/polynomial-redos` — rule semantics from GitHub CodeQL documentation

---

*Architecture research for: Axiom v14.3 Security Hardening + EE Licensing*
*Researched: 2026-03-26*

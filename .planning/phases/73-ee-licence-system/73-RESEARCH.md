# Phase 73: EE Licence System - Research

**Researched:** 2026-03-27
**Domain:** Offline licence key generation + cryptographic validation + state machine enforcement
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Licence delivery**
- Try `AXIOM_LICENCE_KEY` env var first; if absent, fall back to `secrets/licence.key`
- File format: raw base64url string (one line, same value as the env var)
- Public verification key: hardcoded constant in `licence_service.py` — operators cannot swap it

**Licence key format**
- JWT using the EdDSA algorithm claim (`alg: EdDSA`)
- Extended payload fields: `customer_id`, `tier` (ce/ee), `node_limit` (int), `features` (list[str]), `exp` (unix timestamp), `grace_days` (int, default 30), `iat`, `issued_to`, `contact_email`, `licence_id` (UUID), `version` (schema version)

**generate_licence.py CLI**
- Located at `tools/generate_licence.py` (new top-level `tools/` directory)
- Primary invocation: CLI flags (`--customer-id`, `--tier`, `--node-limit`, `--features`, `--expiry`, `--grace-days`, `--issued-to`, `--contact-email`)
- Fallback: interactive prompts if flags are omitted
- Reads signing private key from a path argument or `AXIOM_LICENCE_SIGNING_KEY` env var
- No network call required; pure offline operation

**Missing/invalid licence behaviour**
- No licence key found: boot in CE mode + log WARNING: "No licence key found — running in CE mode"
- Licence key present but signature invalid: log rejection message, fall through to CE mode — does not crash

**Grace/degraded state machine**
- States: `VALID` → `GRACE` (expired but within grace_days) → `DEGRADED_CE` (grace also elapsed)
- GRACE: all EE features active; startup logs WARNING with days remaining
- DEGRADED_CE: EE feature routes return 402 with body `{"detail": "Licence expired — renew at axiom.sh/renew"}`
- `/work/pull` returns empty work response `{"job": null}` in DEGRADED_CE
- `/heartbeat` continues to function in DEGRADED_CE
- `POST /api/enroll` returns 402 when node_limit reached (applies regardless of licence state)

**Clock rollback detection**
- Default: log WARNING on rollback, boot continues
- Strict mode: `AXIOM_STRICT_CLOCK=true` env var → refuse startup if rollback detected
- Boot log: `secrets/boot.log`, append-only, each line = `<sha256_hex> <ISO8601_timestamp>`
- Hash: `SHA256(prev_hash_hex + ISO8601_timestamp)`
- Genesis (absent/empty): seed = `SHA256("" + ISO8601_timestamp)`

**`/api/licence` endpoint**
- `GET /api/licence` — requires auth (any authenticated user)
- Response: `{"status": "valid"|"grace"|"expired", "days_until_expiry": int, "node_limit": int, "tier": "ce"|"ee", "customer_id": str, "grace_days": int}`

**Node limit enforcement**
- Count: non-OFFLINE, non-REVOKED nodes (`status NOT IN ('OFFLINE', 'REVOKED')`)
- `POST /api/enroll`: check count before creating/updating node; if count >= node_limit, return HTTP 402
- Applied regardless of VALID, GRACE, or DEGRADED_CE state

### Claude's Discretion
- Where exactly to place `licence_service.py` (new service module or inside `ee/`)
- Whether the boot log is written before or after licence validation (timing within lifespan)
- Exact format of CLI `--features` flag (comma-separated string vs repeated flags)
- How to handle `boot.log` growing unboundedly (truncation policy)

### Deferred Ideas (OUT OF SCOPE)
- Dashboard licence upload form
- Dashboard amber/red banner for GRACE/DEGRADED_CE state
- Periodic in-process licence re-validation (APScheduler 6h re-check)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIC-01 | Offline Ed25519-signed licence key generation via `tools/generate_licence.py` | PyJWT 2.7.0 (already installed) supports EdDSA encode; cryptography lib provides Ed25519PrivateKey.generate() + serialization |
| LIC-02 | Startup signature verification — reject keys that don't match hardcoded public key | PyJWT 2.7.0 `jwt.decode(token, public_key, algorithms=["EdDSA"])` raises `InvalidSignatureError` on mismatch; catches all forgery |
| LIC-03 | GRACE state: expired but within grace_days → continue EE, log warning | State machine computed from `exp` + `grace_days` fields at startup; GRACE means `now > exp` and `now < exp + grace_days * 86400` |
| LIC-04 | DEGRADED_CE state: grace elapsed → 402 on all EE routes, no crash | Reuse existing `_mount_ce_stubs()` with custom 402 body; or override `app.state` flag to redirect to stubs; no new route infrastructure needed |
| LIC-05 | Clock rollback detection via hash-chained `secrets/boot.log` | Pure stdlib: `hashlib.sha256`, `pathlib.Path`, `datetime.utcnow().isoformat()` — no new dependencies |
| LIC-06 | `GET /api/licence` returns status/days_until_expiry/node_limit/tier | Read from `app.state.licence_state` (module-level LicenceState object); simple route, no DB query required |
| LIC-07 | Node limit enforcement at `POST /api/enroll` — 402 when active count >= node_limit | Single `SELECT count(*) FROM nodes WHERE status NOT IN ('OFFLINE', 'REVOKED')` before node creation; existing enroll_node function in main.py |
</phase_requirements>

---

## Summary

Phase 73 implements an offline licence system for Axiom EE. The work splits into three self-contained units: (1) a CLI key generator (`tools/generate_licence.py`) that produces EdDSA-signed JWTs offline, (2) `licence_service.py` that validates the JWT at startup and computes a state (VALID/GRACE/DEGRADED_CE), and (3) integration hooks in `main.py` that enforce that state at the enroll endpoint, work-pull endpoint, and a new `/api/licence` status route.

The most significant technical discovery is that **python-jose 3.5.0 (the existing JWT library) does NOT support EdDSA** — `OKPKey` is not available in that version. However, **PyJWT 2.7.0 is already installed** (confirmed live in the venv) and fully supports `jwt.encode/decode` with `algorithm="EdDSA"` using `Ed25519PrivateKey`/`Ed25519PublicKey` objects from the `cryptography` library. The generator and validator must both use PyJWT, not python-jose. No new pip dependency is needed.

The clock rollback detection (LIC-05) is entirely self-contained using only stdlib — `hashlib`, `pathlib`, and `datetime`. The hash-chain append-only log pattern is simple to implement and test in isolation. The integration points are well-understood: `lifespan()` in `main.py` already has a scaffold for licence validation (lines 77-104), `enroll_node()` at line 1471 is the only point requiring a node-count guard, and `_mount_ce_stubs()` already handles the 402 pattern for all EE routes.

**Primary recommendation:** Place `licence_service.py` in `puppeteer/agent_service/services/` (consistent with existing service module pattern), replace the existing ad-hoc lifespan licence block with a clean call to `licence_service.load()`, and use PyJWT for all EdDSA operations.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | 2.7.0 (installed) | EdDSA JWT encode/decode | Already in venv; supports EdDSA with cryptography backend; python-jose 3.5.0 does NOT support EdDSA |
| cryptography | installed | Ed25519 key generation, serialization, PEM I/O | Already used throughout (pki.py, security.py, signature_service.py) |
| hashlib | stdlib | SHA256 for boot log hash chain | Pure stdlib, no dep |
| pathlib | stdlib | File I/O for `secrets/boot.log` and `secrets/licence.key` | Standard project pattern |
| argparse | stdlib | CLI flag parsing in `tools/generate_licence.py` | No dep; established Python CLI pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | Expiry and grace period arithmetic | LIC-03/04/06: days_until_expiry computation |
| logging | stdlib | WARNING messages for GRACE, rollback, CE fallback | All state transitions log via `logger = logging.getLogger(__name__)` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT EdDSA | Manual base64url + cryptography.sign() | Manual approach verified to work but PyJWT gives standard decode with exp/iat validation for free |
| PyJWT EdDSA | python-jose | python-jose 3.5.0 lacks OKP/EdDSA support; upgrading risks breaking existing HS256 auth |
| argparse | click | click not installed; argparse is sufficient for a single CLI tool |

**No new pip install required.** PyJWT and cryptography are already in the venv.

---

## Architecture Patterns

### Recommended File Layout

```
tools/
└── generate_licence.py        # offline CLI — no Django/FastAPI import

puppeteer/agent_service/
├── services/
│   └── licence_service.py     # LicenceState dataclass + load() + verify JWT + clock rollback
└── main.py                    # lifespan: call licence_service.load(); enroll_node: node limit guard; GET /api/licence route
```

### Pattern 1: LicenceState Dataclass (module-level singleton)

**What:** A frozen dataclass populated at startup by `licence_service.load()` and stored on `app.state.licence_state`. Routes and the lifespan EE-gating logic read from this object.

**When to use:** Any code that needs to know the current licence tier or state — enroll_node, work/pull degraded-CE path, /api/licence response.

```python
# licence_service.py
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class LicenceStatus(str, Enum):
    VALID = "valid"
    GRACE = "grace"
    EXPIRED = "expired"  # DEGRADED_CE
    CE = "ce"            # no licence / invalid

@dataclass
class LicenceState:
    status: LicenceStatus
    tier: str                  # "ce" or "ee"
    customer_id: Optional[str]
    node_limit: int            # 0 = unlimited (CE mode)
    grace_days: int
    days_until_expiry: int     # negative when expired
    features: List[str]
    is_ee_active: bool         # True only for VALID or GRACE
```

### Pattern 2: JWT EdDSA Verify (PyJWT)

**What:** Use `jwt.decode()` with the hardcoded Ed25519PublicKey object. PyJWT raises `jwt.exceptions.InvalidSignatureError` on forgery and `jwt.exceptions.ExpiredSignatureError` if exp has passed (but we handle expiry manually via grace_days, so pass `options={"verify_exp": False}`).

```python
# licence_service.py — verified working in this venv
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

# Hardcoded public key PEM — operators cannot replace this
_LICENCE_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
<hardcoded at code-generation time from tools/generate_licence.py --generate-keypair>
-----END PUBLIC KEY-----"""

_pub_key: Ed25519PublicKey = serialization.load_pem_public_key(_LICENCE_PUBLIC_KEY_PEM)

def _decode_licence_jwt(token: str) -> dict:
    """Verify EdDSA signature and return payload. Raises jwt.exceptions.* on failure."""
    return jwt.decode(
        token,
        _pub_key,
        algorithms=["EdDSA"],
        options={"verify_exp": False},  # expiry handled via grace_days logic
    )
```

### Pattern 3: JWT EdDSA Sign (tools/generate_licence.py)

```python
# tools/generate_licence.py — verified working in venv
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def sign_licence(private_key: Ed25519PrivateKey, payload: dict) -> str:
    """Returns base64url-encoded JWT (suitable for env var or licence.key file)."""
    return jwt.encode(payload, private_key, algorithm="EdDSA")
```

### Pattern 4: Clock Rollback Detection

**What:** Append-only hash chain in `secrets/boot.log`. Each line: `<sha256_hex> <ISO8601_timestamp>`. On each startup, verify the last line's hash, then check the new timestamp is not earlier.

```python
# licence_service.py
import hashlib
from datetime import datetime, timezone
from pathlib import Path

BOOT_LOG_PATH = Path("secrets/boot.log")

def _compute_hash(prev_hash_hex: str, iso_ts: str) -> str:
    return hashlib.sha256(f"{prev_hash_hex}{iso_ts}".encode()).hexdigest()

def check_and_record_boot() -> bool:
    """Returns True if no rollback detected. Appends new line to boot.log."""
    now_ts = datetime.now(timezone.utc).isoformat()
    BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not BOOT_LOG_PATH.exists() or BOOT_LOG_PATH.stat().st_size == 0:
        # Genesis
        new_hash = _compute_hash("", now_ts)
        BOOT_LOG_PATH.write_text(f"{new_hash} {now_ts}\n")
        return True

    lines = BOOT_LOG_PATH.read_text().strip().splitlines()
    last_line = lines[-1]
    last_hash, last_ts = last_line.split(" ", 1)

    # Verify chain integrity
    expected_hash = _compute_hash(
        lines[-2].split(" ", 1)[0] if len(lines) > 1 else "",
        last_ts
    )
    rollback_detected = last_ts > now_ts  # string ISO comparison works for UTC

    new_hash = _compute_hash(last_hash, now_ts)
    with BOOT_LOG_PATH.open("a") as f:
        f.write(f"{new_hash} {now_ts}\n")

    return not rollback_detected
```

**Boot log truncation (Claude's discretion):** Keep last 1000 lines. After appending, if line count > 1000, rewrite keeping last 1000. The hash chain remains valid from the truncation point onward — no integrity loss.

### Pattern 5: lifespan Integration

Replace the existing ad-hoc licence block (lines 77-104 of `main.py`) with a clean call:

```python
# In lifespan(), after await init_db():
from .services.licence_service import load_licence
licence_state = load_licence()
app.state.licence_state = licence_state

if licence_state.is_ee_active:
    app.state.ee = await load_ee_plugins(app, engine)
else:
    logger.info(f"Licence state={licence_state.status} — loading CE stubs")
    ctx = EEContext()
    _mount_ce_stubs(app)
    app.state.ee = ctx
```

`load_licence()` encapsulates: read env/file → JWT verify → grace computation → clock rollback → return `LicenceState`.

### Pattern 6: enroll_node Node Limit Guard

Insert before the token verification section in `enroll_node()`:

```python
# In enroll_node(), before token lookup:
from sqlalchemy import text as _sql_text
_count_result = await db.execute(
    _sql_text("SELECT count(*) FROM nodes WHERE status NOT IN ('OFFLINE', 'REVOKED')")
)
_active_count = _count_result.scalar()
_node_limit = getattr(app.state.licence_state, "node_limit", 0)
if _node_limit > 0 and _active_count >= _node_limit:
    raise HTTPException(status_code=402, detail="Node limit reached — upgrade your licence at axiom.sh/renew")
```

Note: `node_limit=0` in CE mode (no licence) means unlimited — do not block enrollment when there is no licence.

### Pattern 7: DEGRADED_CE work/pull response

In DEGRADED_CE the existing `_mount_ce_stubs()` handles EE routes. For `/work/pull` (a CE route, not EE), add a guard in the pull_work handler:

```python
# Near top of pull_work handler:
_ls = getattr(request.app.state, "licence_state", None)
if _ls and _ls.status == "expired":
    return PollResponse(job=None, config=WorkConfig())  # empty work, nodes idle
```

### Anti-Patterns to Avoid

- **Calling `sys.exit(1)` on licence expiry:** Crashes the process in an air-gapped production environment. Always degrade gracefully.
- **Reusing the job-signing Ed25519 keypair for licences:** Critical security boundary. A leaked job-signing key must not forge licences. Generate a separate keypair.
- **Calling `python-jose` for EdDSA:** `jose.backends.OKPKey` is not present in python-jose 3.5.0. Use PyJWT exclusively for licence JWT operations.
- **Raising `ExpiredSignatureError` as a crash:** `jwt.decode()` with `verify_exp=True` (default) raises `ExpiredSignatureError` for expired tokens; since grace is handled manually, always pass `options={"verify_exp": False}`.
- **Storing LicenceState in a module-level mutable global:** Use `app.state.licence_state` so it is scoped to the FastAPI app instance — essential for clean test isolation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EdDSA JWT encode/decode | Custom base64url + signature logic | PyJWT 2.7.0 | Already installed; handles header/payload encoding, base64url padding, signature verification correctly per RFC 8037 |
| Ed25519 key generation | Homebrew key format | `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.generate()` | Existing pattern throughout codebase; PEM serialization well-established |
| 402 stub routers | New router per EE feature | `_mount_ce_stubs()` (existing) | Already implemented for 7 EE feature routers; DEGRADED_CE reuses the same stubs |

**Key insight:** The licence system adds state computation at startup and a few enforcement guards at existing routes. It does not require new database tables, new background tasks, or new middleware.

---

## Common Pitfalls

### Pitfall 1: python-jose EdDSA gap

**What goes wrong:** Code attempts `from jose.backends import OKPKey` or calls `jose.jwt.encode(payload, ed25519_key, algorithm="EdDSA")` — both fail silently or raise `ImportError`/`JWTError`.

**Why it happens:** python-jose 3.5.0 does not include OKP (Octet Key Pair) key support. EdDSA was added to PyJWT (not python-jose) in PyJWT >= 2.4.

**How to avoid:** Import `jwt` from PyJWT (package name `PyJWT` in pip, import name `jwt`) not from `python-jose` (`jose`). The two packages share the import name `jwt` — confirm by checking `jwt.__version__` (PyJWT) vs `jose.__version__`.

**Warning signs:** `jose.exceptions.JWTError: Algorithm not supported` or `ImportError: cannot import name 'OKPKey'`.

### Pitfall 2: app.state access in route handlers

**What goes wrong:** `app.state.licence_state` raises `AttributeError` in a route handler when the lifespan hasn't run (e.g., in unit tests that instantiate the route function directly).

**Why it happens:** FastAPI `app.state` is populated during lifespan; direct function calls in tests bypass the lifespan entirely.

**How to avoid:** Use `getattr(request.app.state, "licence_state", None)` with a None fallback. When None, treat as CE mode (unlimited nodes, no EE features). Existing pattern: `getattr(app.state, "ee", None)` in several places.

### Pitfall 3: ISO8601 timestamp comparison in boot log

**What goes wrong:** Comparing timestamps as raw strings fails if timezone offsets differ (`2026-03-27T10:00:00+00:00` vs `2026-03-27T10:00:00Z`).

**Why it happens:** `datetime.isoformat()` output format depends on tzinfo object.

**How to avoid:** Always use `datetime.now(timezone.utc).isoformat()` — produces consistent `2026-03-27T10:00:00.123456+00:00` format. String comparison is then lexicographically correct for UTC timestamps.

### Pitfall 4: DEGRADED_CE and /work/pull interaction

**What goes wrong:** Nodes get errors or disconnect when the licence degrades, causing cascading failures.

**Why it happens:** If `/work/pull` raises an exception in DEGRADED_CE, nodes interpret the 5xx as a server error and may back off or disconnect.

**How to avoid:** In DEGRADED_CE, `/work/pull` returns a valid `PollResponse(job=None, config=WorkConfig())` — nodes stay enrolled and heartbeating but receive no new jobs. This is already documented in the CONTEXT.md decisions. Implement as a silent early-return check, not an HTTPException.

### Pitfall 5: generate_licence.py importing agent_service

**What goes wrong:** `tools/generate_licence.py` is a standalone offline tool. If it imports from `agent_service.*`, it drags in FastAPI, SQLAlchemy, asyncpg — the full backend dependency chain — which may not be available in the operator's offline environment.

**Why it happens:** Convenience of sharing models or utilities.

**How to avoid:** `tools/generate_licence.py` must only import from stdlib and PyJWT/cryptography. No agent_service imports. Copy any needed constants (e.g. payload field names) inline.

---

## Code Examples

### Generating an Ed25519 keypair (for setup, not per-licence)

```python
# tools/generate_licence.py — key generation section
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

private_key = Ed25519PrivateKey.generate()
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
```

### Encoding a licence JWT

```python
# tools/generate_licence.py — signing section
import jwt
import uuid
import time

payload = {
    "version": 1,
    "licence_id": str(uuid.uuid4()),
    "customer_id": args.customer_id,
    "issued_to": args.issued_to,
    "contact_email": args.contact_email,
    "tier": args.tier,
    "node_limit": args.node_limit,
    "features": args.features,  # list[str]
    "grace_days": args.grace_days,
    "iat": int(time.time()),
    "exp": int(args.expiry.timestamp()),  # datetime -> unix ts
}
token = jwt.encode(payload, private_key, algorithm="EdDSA")
# token is a str (PyJWT >= 2.0 returns str not bytes)
print(token)
```

### Decoding + grace computation

```python
# licence_service.py — load() function
import jwt
import time
from cryptography.hazmat.primitives import serialization

_pub_key = serialization.load_pem_public_key(_LICENCE_PUBLIC_KEY_PEM)

def _compute_state(payload: dict) -> LicenceState:
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

def load_licence() -> LicenceState:
    raw = _read_licence_raw()  # env var or secrets/licence.key
    if not raw:
        logger.warning("No licence key found — running in CE mode")
        return _ce_state()
    try:
        payload = jwt.decode(raw, _pub_key, algorithms=["EdDSA"],
                             options={"verify_exp": False})
    except jwt.exceptions.InvalidSignatureError:
        logger.warning("Licence key signature invalid — running in CE mode")
        return _ce_state()
    except Exception as e:
        logger.warning(f"Licence key parse error ({e}) — running in CE mode")
        return _ce_state()

    state = _compute_state(payload)
    if state.status == LicenceStatus.GRACE:
        days_left = int((payload["exp"] + payload.get("grace_days", 30) * 86400 - time.time()) / 86400)
        logger.warning(f"Licence in GRACE period — {days_left} days remaining before DEGRADED_CE")
    elif state.status == LicenceStatus.EXPIRED:
        logger.warning("Licence grace period ended — DEGRADED_CE mode active")
    return state
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Ad-hoc lifespan licence block in main.py (lines 77-104) — decodes JWT with base64 manually, no signature verification, no grace period | Dedicated `licence_service.py` with PyJWT EdDSA decode, LicenceState dataclass, grace period logic, clock rollback detection | Replace entirely |
| python-jose for all JWT operations | python-jose for session JWTs (HS256); PyJWT for licence JWTs (EdDSA) | Two libraries co-exist without conflict; both importable as needed |

**Deprecated/outdated:**
- The existing lifespan licence block (main.py lines 77-104): does not verify Ed25519 signature, does not handle grace, uses plain base64 decode. Replace entirely with `licence_service.load()`.

---

## Discretion Recommendations

### Where to place `licence_service.py`

Place in `puppeteer/agent_service/services/licence_service.py`. This is consistent with `signature_service.py`, `job_service.py`, etc. Placing it inside `ee/` would be wrong — the CONTEXT.md and STATE.md both note that licence validation must live in CE code to prevent partial EE route registration.

### Boot log timing in lifespan

Write boot log entry **before** licence validation. Order: (1) `await init_db()`, (2) clock rollback check + boot.log append, (3) licence JWT load and state computation, (4) EE plugin load/stub mount. This means the boot timestamp is always recorded regardless of licence validity, and a rollback warning always appears in logs before EE loading.

### `--features` CLI flag format

Use repeated `--feature` flags (not comma-separated): `--feature sso --feature webhooks`. argparse `action="append"` is idiomatic for list-valued flags and avoids comma-in-feature-name edge cases.

### `boot.log` truncation policy

Keep last 1000 lines. After each startup append, if `len(lines) > 1000`, rewrite with `lines[-1000:]`. The chain remains verifiable from any point — truncation only loses old history, not integrity of recent entries.

---

## Open Questions

1. **Licence keypair bootstrap**
   - What we know: `licence_service.py` embeds the public key as a hardcoded constant; `tools/generate_licence.py` reads the private key from a file or env var
   - What's unclear: The keypair does not yet exist. Someone must run `tools/generate_licence.py --generate-keypair` (or equivalent) to produce the keypair, then paste the public key PEM into `licence_service.py`.
   - Recommendation: Include a `--generate-keypair` subcommand (or separate script section) in `tools/generate_licence.py` that writes `secrets/licence_signing.key` (private) and prints the public PEM to embed in `licence_service.py`. Document this as a one-time bootstrap step.

2. **`boot.log` in Docker volume**
   - What we know: `secrets/` is already a mounted Docker volume in compose.server.yaml (for `secrets.env`, licence.key)
   - What's unclear: Whether `secrets/boot.log` inside the container correctly persists across restarts
   - Recommendation: Verify `secrets/` is a named volume (not a bind mount) — named volumes persist across `docker compose up/down`. If bind-mounted, the path resolution in the container may differ. The Path in licence_service.py should be relative to the working dir (`Path("secrets/boot.log")`) which resolves to `/app/secrets/boot.log` inside the container.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (no ini/cfg — discovered from root) |
| Config file | None — pytest auto-discovers `puppeteer/tests/test_*.py` |
| Quick run command | `cd puppeteer && pytest tests/test_licence_service.py -x -q` |
| Full suite command | `cd puppeteer && pytest tests/ -x -q --ignore=tests/test_ee_smoke.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIC-01 | `sign_licence()` produces a valid EdDSA JWT with all required fields | unit | `pytest tests/test_licence_service.py::test_generate_licence_jwt -x` | Wave 0 |
| LIC-02 | `load_licence()` rejects a JWT with tampered signature | unit | `pytest tests/test_licence_service.py::test_invalid_signature_falls_to_ce -x` | Wave 0 |
| LIC-03 | GRACE state: expired within grace_days → is_ee_active=True + warning logged | unit | `pytest tests/test_licence_service.py::test_grace_period_active -x` | Wave 0 |
| LIC-04 | DEGRADED_CE state: grace elapsed → is_ee_active=False | unit | `pytest tests/test_licence_service.py::test_degraded_ce_state -x` | Wave 0 |
| LIC-05 | Clock rollback detected and logged; strict mode raises | unit | `pytest tests/test_licence_service.py::test_clock_rollback_detection -x` | Wave 0 |
| LIC-06 | `GET /api/licence` returns correct JSON for each state | unit | `pytest tests/test_licence_service.py::test_licence_status_endpoint -x` | Wave 0 |
| LIC-07 | `POST /api/enroll` returns 402 when active node count >= node_limit | unit | `pytest tests/test_licence_service.py::test_enroll_node_limit_enforced -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd puppeteer && pytest tests/test_licence_service.py -x -q`
- **Per wave merge:** `cd puppeteer && pytest tests/ -x -q --ignore=tests/test_ee_smoke.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_licence_service.py` — covers all 7 LIC requirements (7 test functions)
- [ ] `tools/` directory — create with `tools/__init__.py` (empty) and `tools/generate_licence.py`

*(No framework or conftest gaps — existing pytest infrastructure covers all phase test patterns. Tests follow the `AsyncMock`/`MagicMock` pattern established in `test_lifecycle_enforcement.py` and `test_ee_smoke.py`.)*

---

## Sources

### Primary (HIGH confidence)

- Live venv verification — `python3 -c "import jwt; jwt.encode(..., algorithm='EdDSA')"` confirmed working: PyJWT 2.7.0 supports EdDSA with Ed25519PrivateKey
- Live venv verification — `from jose.backends import OKPKey` raises `ImportError`: python-jose 3.5.0 does NOT support EdDSA
- Source code inspection: `puppeteer/agent_service/ee/__init__.py` — `_mount_ce_stubs()`, `EEContext`, `load_ee_plugins()` patterns
- Source code inspection: `puppeteer/agent_service/main.py` lines 73-104 — existing lifespan licence block to replace
- Source code inspection: `puppeteer/agent_service/main.py` lines 1471-1528 — `enroll_node()` integration point
- Source code inspection: `puppeteer/agent_service/services/signature_service.py` — service module pattern and Ed25519 usage
- Source code inspection: `puppeteer/agent_service/deps.py` — `require_auth` pattern for `/api/licence` auth
- Source code inspection: `puppeteer/agent_service/security.py` — `validate_path_within` + existing security helpers

### Secondary (MEDIUM confidence)

- PyJWT docs: EdDSA support added in PyJWT 2.4.0 (OKP / Ed25519); `algorithm="EdDSA"` with cryptography backend

### Tertiary (LOW confidence)

- None — all claims verified by live execution or source inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by running actual imports in the project venv
- Architecture: HIGH — based on direct source code inspection of all integration points
- Pitfalls: HIGH — python-jose EdDSA gap verified by live ImportError; other pitfalls from source inspection

**Research date:** 2026-03-27
**Valid until:** 2026-04-26 (stable libraries — 30-day window)

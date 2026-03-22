# Phase 41: CE Validation Pass - Research

**Researched:** 2026-03-21
**Domain:** Python validation scripting — CE stub verification, table count assertions, Ed25519 job signing + execution polling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script structure:**
- 3 separate standalone Python scripts in `mop_validation/scripts/`:
  - `verify_ce_stubs.py` — CEV-01 (EE route stub assertions)
  - `verify_ce_tables.py` — CEV-02 (table count after hard teardown)
  - `verify_ce_job.py` — CEV-03 (end-to-end signed job execution)
- Each script is runnable independently — operator can re-run a single failing check without re-running all three
- Output format: `[PASS]` / `[FAIL]` per step inline as it runs, then a final summary table at the end (mirrors `verify_lxc_nodes.py` pattern)

**CEV-01 — EE stub route assertions (`verify_ce_stubs.py`):**
- Hardcoded list of the 7 known EE route paths — explicit, fails clearly if a route changes or is accidentally removed
- Correct HTTP method per route with admin token auth (GET for read endpoints, POST for creation endpoints)
- Asserts HTTP 402 — not 404, not 500 — for each route
- Admin token ensures 402 is definitely from the CE stub, not a permission check

**CEV-02 — Table count (`verify_ce_tables.py`):**
- Assumes teardown already done: script only runs the table count query — operator runs `teardown_hard.sh` + `docker compose up -d` first
- Keeps the script non-destructive and fast (no multi-minute stack restart baked in)
- Table count query: `docker exec puppeteer-postgres-1 psql` against `information_schema.tables` (no external DB driver)
- Asserts exactly 13 tables
- Does NOT re-assert `GET /api/features` or `GET /api/licence` — those are delegated to `verify_ce_install.py` (Phase 38); no duplication

**CEV-03 — End-to-end signed job execution (`verify_ce_job.py`):**
- Self-contained: key loading, Ed25519 signing, job submission, and result assertion all inline — no subprocess calls to `admin_signer.py` or `run_signed_job.py`
- Signing key: `mop_validation/secrets/signing.key` (existing key already registered with the server)
- Pre-flight check: asserts the public key is registered via `GET /api/signatures` before submitting — clear error message if key is missing rather than a confusing signature rejection
- Job payload: `import sys; print('CEV-03 stdout ok'); sys.exit(0)` — minimal, captures a known stdout string
- Target node: DEV-tagged node (`axiom-node-dev`)
- Result verification: API-only via `GET /api/executions` filtered by job GUID — asserts `status=COMPLETED` and `stdout` contains `"CEV-03 stdout ok"`
- Timeout: 30s, 2s poll interval — trivial job; anything slower signals a real problem

### Claude's Discretion
- Exact formatting of the summary table at end of each script
- Retry/backoff logic for API readiness checks at script start
- Error messaging when `signing.key` or `secrets/nodes/` files are missing (pre-flight guard wording)
- The precise list of 7 EE route paths (derive from EE plugin's router registration in `axiom-ee/ee/plugin.py`)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CEV-01 | All 7 EE routes return HTTP 402 (not 404) on CE-only install with 4 nodes active | CE stub interfaces fully catalogued; 7 representative paths identified (one per EE feature domain) |
| CEV-02 | CE table count assertion: exactly 13 tables, zero EE table leakage after hard teardown + CE reinstall | `pg_tables` query pattern confirmed from `verify_ce_install.py`; `apscheduler_jobs` exclusion pattern confirmed |
| CEV-03 | Basic job dispatch on CE: script signed, submitted, executed on a DEV-tagged node, stdout captured in execution history | Ed25519 signing confirmed; `POST /jobs` structure confirmed; `GET /api/executions?job_guid=` filter confirmed; signing key at `master_of_puppets/secrets/signing.key` |
</phase_requirements>

---

## Summary

Phase 41 requires three standalone Python verification scripts that run against the live CE stack with all 4 LXC nodes active. The scripts follow a pattern already established by `verify_ce_install.py` and `verify_lxc_nodes.py` — `[PASS]`/`[FAIL]` inline output per check, a final summary table, and `sys.exit(1)` on any failure.

The CE stub routing is fully implemented in the main `puppeteer` branch under `agent_service/ee/interfaces/`. When the EE plugin is absent (CE mode), `_mount_ce_stubs()` in `agent_service/ee/__init__.py` mounts 6 stub routers covering all EE feature domains. Every stub handler returns `JSONResponse(status_code=402, content={"detail": "This feature requires Axiom Enterprise Edition..."})`. These stubs are already live in the current codebase — CEV-01 is a test of existing behaviour, not a new implementation.

CEV-03 requires Ed25519 signing inline in Python using `cryptography`. The signing key lives at `master_of_puppets/secrets/signing.key` (PEM Ed25519 private key). The node verifies via `public_key.verify(sig_bytes, script_bytes)` (Ed25519 two-argument form). Jobs are submitted to `POST /jobs` with a `JobCreate` body where `payload` is a dict containing `script_content`, `signature` (base64), and `secrets`. Executions are polled via `GET /api/executions?job_guid=<guid>`.

**Primary recommendation:** All three scripts are new-code-in-existing-infrastructure tasks. Mirror the `verify_ce_install.py` helper pattern precisely (load_env, check(), wait_for_stack, get_admin_token, docker exec psql). The only novel element is the Ed25519 inline signing in `verify_ce_job.py`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | already installed | HTTP calls to CE stack | Used in all existing verify scripts |
| `cryptography` | already installed | Ed25519 key load + sign | Project standard; used in `signature_service.py` and `verify_lxc_nodes.py` |
| `subprocess` | stdlib | `docker exec psql` for DB queries | Pattern established in `verify_ce_install.py` |
| `pathlib` | stdlib | Path resolution | Used in all existing scripts |
| `json` | stdlib | API response parsing | Used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `time` | stdlib | Poll loop sleep, timeout enforcement | CEV-03 result polling |

**Installation:** No new dependencies — all libraries already present in the mop_validation environment.

---

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/scripts/
├── verify_ce_stubs.py    # CEV-01: 7 EE route 402 assertions
├── verify_ce_tables.py   # CEV-02: table count after hard teardown
└── verify_ce_job.py      # CEV-03: E2E Ed25519 signed job execution
```

### Pattern 1: Script Structure (from verify_ce_install.py + verify_lxc_nodes.py)
**What:** Each script has a top-level `main()` that: loads secrets, waits for stack, runs checks accumulating booleans, prints a summary table, exits 0/1.
**When to use:** All three Phase 41 scripts.
**Example (summary table pattern from verify_lxc_nodes.py):**
```python
# Source: mop_validation/scripts/verify_lxc_nodes.py (lines 680-695)
print("\n" + "=" * 60)
print("=== Phase 41 CE Validation ===")
for req_id, passed in results:
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {req_id}")
passed_count = sum(1 for _, p in results if p)
print(f"\n=== RESULT: {passed_count}/{len(results)} passed ===")
if passed_count == len(results):
    sys.exit(0)
else:
    sys.exit(1)
```

### Pattern 2: Secrets Loading
```python
# Source: mop_validation/scripts/verify_ce_install.py (lines 84-93)
ROOT = Path(__file__).resolve().parents[2]  # .../Development/
MOP_DIR = ROOT / "master_of_puppets"
VALIDATION_DIR = ROOT / "mop_validation"
SECRETS_ENV = MOP_DIR / "secrets.env"

def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env
```

### Pattern 3: Stack Readiness Wait
```python
# Source: mop_validation/scripts/verify_ce_install.py (lines 119-136)
def wait_for_stack(base_url: str, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/api/features", verify=False, timeout=5)
            if resp.status_code == 200:
                print(); return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print(); return False
```

### Pattern 4: Admin Token Acquisition
```python
# Source: mop_validation/scripts/verify_ce_install.py (lines 139-152)
# IMPORTANT: uses data= (form-encoded), not json= — OAuth2PasswordRequestForm
def get_admin_token(base_url: str, password: str):
    resp = requests.post(
        f"{base_url}/auth/login",
        data={"username": "admin", "password": password},
        verify=False, timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None
```

### Pattern 5: postgres table count via docker exec
```python
# Source: mop_validation/scripts/verify_ce_install.py (lines 155-180)
# Uses pg_tables WHERE schemaname='public' AND tablename != 'apscheduler_jobs'
query = (
    "SELECT count(*) FROM pg_tables "
    "WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"
)
result = subprocess.run(
    ["docker", "exec", pg_container,
     "psql", "-U", "puppet", "-d", "puppet_db",
     "-t", "-c", query],
    capture_output=True, text=True, timeout=15,
)
count = int(result.stdout.strip())
```

### Pattern 6: Ed25519 Inline Signing (CEV-03)
```python
# Source: signature_service.py (lines 54-69), node.py (lines 589-596)
# key type: Ed25519PrivateKey loaded from PEM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64

key_pem = Path(SIGNING_KEY_PATH).read_bytes()
private_key = serialization.load_pem_private_key(key_pem, password=None)
script = "import sys; print('CEV-03 stdout ok'); sys.exit(0)"
sig_bytes = private_key.sign(script.encode("utf-8"))  # Ed25519: no hash arg
signature_b64 = base64.b64encode(sig_bytes).decode("ascii")
```

### Pattern 7: Job Submission
```python
# Source: main.py line 983, models.py JobCreate
# POST /jobs — requires Bearer token, JSON body
resp = requests.post(
    f"{BASE_URL}/jobs",
    json={
        "task_type": "python_script",
        "payload": {
            "script_content": script,
            "signature": signature_b64,
            "secrets": {},
        },
        "env_tag": "DEV",
        "max_retries": 0,
    },
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
job_guid = resp.json()["guid"]
```

### Pattern 8: Execution Result Polling
```python
# Source: main.py lines 160-183
# GET /api/executions?job_guid=<guid>
# Response field: status (COMPLETED/FAILED), stdout (captured output string)
resp = requests.get(
    f"{BASE_URL}/api/executions",
    params={"job_guid": job_guid},
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
records = resp.json()
# records is a list; each has: status, stdout, stderr, exit_code, node_id
```

### Anti-Patterns to Avoid
- **Using `json=` for /auth/login:** FastAPI expects `data=` (form-encoded) for OAuth2PasswordRequestForm — always use `data={"username": ..., "password": ...}`.
- **Using subprocess calls to admin_signer.py:** CEV-03 is self-contained. Do not shell out.
- **Hardcoding postgres container name:** Always call `get_postgres_container()` or equivalent dynamic discovery with `puppeteer-db-1` fallback.
- **Asserting `GET /api/features` in CEV-02:** That check belongs to Phase 38's `verify_ce_install.py`. Do not duplicate.
- **RSA signing:** The node and signature_service both expect Ed25519. The old `sign_job.py` uses RSA+PSS — do not use it as a reference for signing logic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signing | Custom byte manipulation | `cryptography` library `Ed25519PrivateKey.sign()` | Ed25519 has no hash parameter — `sign(message)` only; node uses same library |
| postgres query without driver | psycopg2 install | `docker exec psql -t -c "SELECT..."` | No external DB dependency; pattern confirmed in verify_ce_install.py |
| SSL warning suppression | Custom SSL context | `requests.packages.urllib3.disable_warnings()` | Established pattern across all verify scripts |
| Admin token | Custom auth flow | `POST /auth/login` with `data=` (form-encoded) | OAuth2PasswordRequestForm requires form encoding, not JSON |

**Key insight:** All infrastructure for signing, polling, and table counting already exists in the codebase — the task is assembly, not invention.

---

## Common Pitfalls

### Pitfall 1: Signing Key Location Mismatch
**What goes wrong:** CONTEXT.md refers to `mop_validation/secrets/signing.key` but the actual key is at `master_of_puppets/secrets/signing.key`.
**Why it happens:** The key was generated by the main repo's PKI tooling, not the validation repo.
**How to avoid:** Use `MOP_DIR / "secrets" / "signing.key"` as the path. Add a clear pre-flight check with a message like `"signing.key not found at {path} — was it generated? Run: python ~/Development/toms_home/.agents/tools/admin_signer.py --generate"`.
**Warning signs:** `FileNotFoundError` in pre-flight, not during signing.

### Pitfall 2: Ed25519 vs RSA Signing API Difference
**What goes wrong:** Old scripts (`sign_job.py`, `generate_signing_key.py`) use RSA+PSS with `private_key.sign(content, padding.PSS(...), hashes.SHA256())`. Ed25519 uses `private_key.sign(content)` — no padding or hash argument.
**Why it happens:** Different key types have different `sign()` signatures in `cryptography`.
**How to avoid:** Load the key with `serialization.load_pem_private_key()` and call `sign()` with the raw bytes only. Confirm the loaded key is `Ed25519PrivateKey` instance before signing.
**Warning signs:** `TypeError: sign() takes no keyword arguments` or wrong number of arguments.

### Pitfall 3: Signatures API Path Discrepancy
**What goes wrong:** CONTEXT.md refers to `GET /api/signatures` but the actual endpoint is `GET /signatures` (no `/api/` prefix).
**Why it happens:** The signatures routes are registered directly on the app without the `/api/` prefix (main.py line 1428: `@app.get("/signatures", ...)`).
**How to avoid:** Use `GET /signatures` for the pre-flight key registration check, not `/api/signatures`.
**Warning signs:** Unexpected 404 on what appears to be a valid endpoint.

### Pitfall 4: CEV-01 "7 routes" Count Clarity
**What goes wrong:** The stubs cover many more than 7 routes (foundry alone has ~20 routes). CEV-01 requires exactly 7 representative paths — one per EE feature domain.
**Why it happens:** The CONTEXT.md says "7 known EE route paths" meaning one canonical entry point per feature, not all routes.
**How to avoid:** Use these 7 paths (one per EE domain/interface file):
  1. `GET /api/blueprints` (foundry)
  2. `GET /api/smelter/ingredients` (smelter)
  3. `GET /admin/audit-log` (audit)
  4. `GET /api/webhooks` (webhooks)
  5. `GET /api/admin/triggers` (triggers)
  6. `GET /admin/users` (users/rbac via auth_ext stub)
  7. `GET /auth/me/api-keys` (auth_ext)
**Warning signs:** Confusion about which routes to assert — the above list covers all 6 stub routers (audit_stub_router has only 1 route; the 7th comes from auth_ext which covers both users and api-keys).

### Pitfall 5: Job stdout Field vs output_log
**What goes wrong:** The `ExecutionRecordResponse` has both `output_log` (list of structured log lines) and `stdout` (plain string). CEV-03 asserts `stdout contains "CEV-03 stdout ok"` — use the `stdout` field, not `output_log`.
**Why it happens:** Two different output capture mechanisms exist; `stdout` is the raw captured text.
**How to avoid:** Assert `record["stdout"]` contains the expected string.
**Warning signs:** Assertion passes when `stdout` is None but `output_log` contains the text — they are independent.

### Pitfall 6: apscheduler_jobs Table in CEV-02 Count
**What goes wrong:** `pg_tables` includes `apscheduler_jobs` as a public table, making the count 14 instead of 13.
**Why it happens:** APScheduler creates its own table in the public schema.
**How to avoid:** Use the confirmed query: `WHERE schemaname='public' AND tablename != 'apscheduler_jobs'` (same as verify_ce_install.py). The expected count is 13.
**Warning signs:** Count of 14 on a correct CE install.

---

## Code Examples

### The 7 CEV-01 EE Stub Routes (one per feature domain)
```python
# Source: agent_service/ee/interfaces/ — confirmed from direct inspection
# These are the representative "entry point" routes per EE feature domain
EE_STUB_ROUTES = [
    # (method, path, feature_domain)
    ("GET",  "/api/blueprints",           "foundry"),
    ("GET",  "/api/smelter/ingredients",  "smelter"),
    ("GET",  "/admin/audit-log",          "audit"),
    ("GET",  "/api/webhooks",             "webhooks"),
    ("GET",  "/api/admin/triggers",       "triggers"),
    ("GET",  "/admin/users",              "users/rbac"),
    ("GET",  "/auth/me/api-keys",         "auth_ext"),
]
```

### CE Stub 402 Response Shape
```python
# Source: agent_service/ee/interfaces/webhooks.py (lines 6-8)
# All 6 stub routers return identical shape:
{
    "detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"
}
# HTTP status code: 402 (not 404, not 500)
```

### Ed25519 Inline Signing (CEV-03)
```python
# Source: signature_service.py verify_payload_signature(), node.py lines 589-596
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64

def sign_script(script: str, key_path: Path) -> str:
    key_pem = key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert isinstance(private_key, Ed25519PrivateKey), "Expected Ed25519 key"
    sig_bytes = private_key.sign(script.encode("utf-8"))
    return base64.b64encode(sig_bytes).decode("ascii")
```

### Signatures Pre-flight Check
```python
# Source: main.py line 1428-1430 — endpoint is /signatures not /api/signatures
def check_signing_key_registered(base_url: str, jwt: str, key_name: str) -> str | None:
    """Returns the signature ID if key_name is registered, else None."""
    resp = requests.get(
        f"{base_url}/signatures",
        headers={"Authorization": f"Bearer {jwt}"},
        verify=False, timeout=10,
    )
    if resp.status_code != 200:
        return None
    sigs = resp.json()
    for s in sigs:
        if s.get("name") == key_name:
            return s.get("id")
    return None
```

### Dynamic Postgres Container Discovery
```python
# Source: mop_validation/scripts/verify_ce_install.py (lines 104-116)
def get_postgres_container() -> str:
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=puppeteer-db", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        name = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
        return name if name else "puppeteer-db-1"
    except Exception:
        return "puppeteer-db-1"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RSA+PSS job signing (`sign_job.py`) | Ed25519 job signing (`signature_service.py`) | Sprint 6+ | Node verifies with `public_key.verify(sig, msg)` — no hash parameter |
| Shared JOIN_TOKEN for all nodes | Per-node unique JOIN_TOKEN | Phase 40 | Each node has its own `.env` in `mop_validation/secrets/nodes/` |
| `verify=ROOT_CA` TLS verification | `verify=False` + `urllib3.disable_warnings()` | Established pattern | Self-signed certs in dev stack |

**Deprecated/outdated:**
- `mop_validation/scripts/run_signed_job.py`: Uses RSA signing via `sign_job.py`; incomplete auth handling. Do NOT use as CEV-03 reference for signing logic.
- `mop_validation/scripts/generate_signing_key.py`: Generates RSA keys. The project uses Ed25519 for job signing.
- `mop_validation/scripts/sign_job.py`: RSA+PSS. Wrong algorithm for current stack.

---

## Open Questions

1. **Signing key name in signatures registry**
   - What we know: The signing key at `master_of_puppets/secrets/signing.key` must be registered in the DB with some `name` value.
   - What's unclear: The exact `name` used when the key was originally registered (could be "default", "admin", or something else).
   - Recommendation: Pre-flight check in `verify_ce_job.py` should list all registered keys and print their names on failure, so the operator can identify the correct one. Alternatively, match by any registered key since there is typically only one.

2. **Signing key PEM type confirmation**
   - What we know: The project uses Ed25519 for job signing per `signature_service.py`. The key was generated at some point.
   - What's unclear: Whether `master_of_puppets/secrets/signing.key` is actually Ed25519 or an older RSA key from an earlier sprint.
   - Recommendation: Add a pre-flight type assertion (`isinstance(private_key, Ed25519PrivateKey)`) with a clear error message if the key is RSA.

3. **GET /api/executions `stdout` field population timing**
   - What we know: `ExecutionRecordResponse` has a `stdout` field; `node.py` captures script stdout.
   - What's unclear: Whether `stdout` is populated immediately when status=COMPLETED or may lag.
   - Recommendation: Poll until both `status == "COMPLETED"` AND `stdout is not None` before asserting content.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | These are standalone validation scripts, not a test framework suite |
| Config file | none — scripts run directly |
| Quick run command | `python3 mop_validation/scripts/verify_ce_stubs.py` |
| Full suite command | `python3 mop_validation/scripts/verify_ce_stubs.py && python3 mop_validation/scripts/verify_ce_tables.py && python3 mop_validation/scripts/verify_ce_job.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CEV-01 | 7 EE stub routes return HTTP 402 | integration/smoke | `python3 mop_validation/scripts/verify_ce_stubs.py` | ❌ Wave 0 |
| CEV-02 | Exactly 13 CE tables after hard teardown + reinstall | integration/smoke | `python3 mop_validation/scripts/verify_ce_tables.py` | ❌ Wave 0 |
| CEV-03 | Signed job executes on DEV node; stdout captured | integration/e2e | `python3 mop_validation/scripts/verify_ce_job.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Run the specific script for that task's CEV requirement
- **Per wave merge:** `python3 mop_validation/scripts/verify_ce_stubs.py && python3 mop_validation/scripts/verify_ce_tables.py && python3 mop_validation/scripts/verify_ce_job.py`
- **Phase gate:** All 3 scripts exit 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/verify_ce_stubs.py` — covers CEV-01
- [ ] `mop_validation/scripts/verify_ce_tables.py` — covers CEV-02
- [ ] `mop_validation/scripts/verify_ce_job.py` — covers CEV-03

*(All three scripts are the deliverables of this phase — Wave 0 IS the implementation.)*

---

## Sources

### Primary (HIGH confidence)
- Direct inspection: `agent_service/ee/__init__.py` — CE stub mounting logic confirmed
- Direct inspection: `agent_service/ee/interfaces/*.py` — all 6 stub router files read; 402 response confirmed
- Direct inspection: `agent_service/main.py` — `GET /signatures`, `POST /jobs`, `GET /api/executions` endpoints confirmed
- Direct inspection: `agent_service/services/signature_service.py` — Ed25519 verification pattern confirmed
- Direct inspection: `puppets/environment_service/node.py` — `public_key.verify(sig_bytes, script.encode())` confirmed
- Direct inspection: `mop_validation/scripts/verify_ce_install.py` — helper patterns, postgres query, table count confirmed
- Direct inspection: `mop_validation/scripts/verify_lxc_nodes.py` — summary table pattern confirmed
- Direct inspection: `axiom-ee/ee/plugin.py` — EE plugin router structure confirmed (7 feature domains)

### Secondary (MEDIUM confidence)
- CONTEXT.md Phase 41 — operator decisions and integration points as agreed by user
- `.planning/REQUIREMENTS.md` — CEV-01/02/03 requirement text

### Tertiary (LOW confidence)
- CONTEXT.md reference to `mop_validation/secrets/signing.key` — actual key found at `master_of_puppets/secrets/signing.key` based on filesystem inspection (possible the CONTEXT.md path is aspirational/documented differently than reality)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed in existing scripts
- Architecture: HIGH — patterns read directly from live code
- Pitfalls: HIGH — discovered from direct code inspection (wrong path, wrong API endpoint prefix, RSA vs Ed25519)
- EE stub routes: HIGH — read directly from `agent_service/ee/interfaces/` stub files

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable architecture; CE/EE split is settled)

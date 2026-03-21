# Phase 43: Job Test Matrix - Research

**Researched:** 2026-03-21
**Domain:** Validation scripting — job lifecycle, env-tag routing, retry mechanics, signature security
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script structure:**
- 9 standalone scripts: `verify_job_01_fast.py` through `verify_job_09_revoked.py` — one per scenario
- 1 runner script: `run_job_matrix.py` — thin orchestrator, sequential, aggregates [PASS]/[FAIL], prints summary table
- No cleanup: scripts leave job definitions and execution records in place (non-destructive)
- Naming: `verify_job_NN_slug.py` (sortable, requirement-ID prefix)

**Node assignment strategy:**
- Dynamic discovery: call `GET /api/nodes` at runtime, filter by `env_tag` — no hardcoded node IDs
- JOB-01/02/03: first DEV-tagged node (`axiom-node-dev`)
- JOB-04: STAGING-tagged node (`axiom-node-staging`)
- JOB-05/06: DEV, TEST, PROD nodes explicitly; cross-tag failure uses nonexistent tag
- JOB-07/08/09: DEV node
- Pre-flight: assert all required nodes ONLINE before running; print `[SKIP]` with reason if offline

**JOB-05 cross-tag failure assertion:**
- Submit a job with tag `"NONEXISTENT"` — assert orchestrator returns HTTP 4xx (not silent 200)
- Does not require taking a real node offline

**Concurrency (JOB-04):**
- 5 threads (`threading.Thread`), all launched within < 100ms
- Payload: `import time; print('JOB-04 concurrent {n}'); time.sleep(5)`
- Assertion: each of 5 job GUIDs has exactly 1 ExecutionRecord with `status=COMPLETED`
- Timeout: 60s, 3s poll interval

**JOB-07 retry (crash):**
- `max_retries=2` (3 total attempts), assert `DEAD_LETTER` final status
- Assert 3 ExecutionRecords with `attempt_number` 1, 2, 3, all `status=FAILED`

**JOB-08 bad signature:**
- Push valid job definition, corrupt `signature_payload` directly via `docker exec puppeteer-postgres-1 psql` UPDATE
- Assert `job.status == SECURITY_REJECTED` AND `ExecutionRecord.stdout` is empty

**JOB-09 revoked definition:**
- Assert `POST /api/dispatch` with REVOKED job definition returns HTTP 4xx at orchestrator
- Assertion is purely API-level

**Failure handling:** Continue on failure, report all results, exit non-zero on any failure.

**Output format:** `[PASS] JOB-NN: description` / `[FAIL] JOB-NN: description — reason`, summary table, `run_job_matrix.py` prints `N/9 passed`.

### Claude's Discretion
- Exact polling backoff and retry logic within each script
- `docker exec psql` quoting for the UPDATE statement in JOB-08
- Pre-flight wait loop for API readiness
- Exact wording of remediation messages when pre-flight checks fail

### Deferred Ideas (OUT OF SCOPE)
- Audit log assertion for SECURITY_REJECTED (JOB-08) — target Phase 45
- Postgres hardening to prevent signature tampering via direct DB access — target Phase 45
- Parallel execution of all 9 scripts simultaneously in `run_job_matrix.py`
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-01 | Fast job (< 5s): executes, stdout captured, visible in execution history | `POST /jobs` → poll `GET /api/executions?job_guid=X` for COMPLETED with stdout |
| JOB-02 | Slow job (90s sleep): completes without premature timeout; node live in heartbeat | Same execution pattern with 120s poll timeout; heartbeat visible via `GET /nodes` mid-execution |
| JOB-03 | Memory-heavy job (allocate 512MB): executes in `direct` mode; resource limit not enforced | Same execution pattern; assert COMPLETED; document resource limit gap in direct mode |
| JOB-04 | Concurrent jobs (5 simultaneous to same node): all complete, no duplicate GUID execution | `threading.Thread` × 5 → each GUID checked for exactly 1 COMPLETED ExecutionRecord |
| JOB-05 | Env-tag routing: DEV job → DEV node only; cross-tag → no eligible node | `env_tag` on `POST /jobs`; cross-tag uses nonexistent tag — BUT see critical gap below |
| JOB-06 | Env promotion chain: same script → DEV → TEST → PROD, each execution in history | 3 sequential dispatches with different `env_tag` values, 3 separate ExecutionRecords |
| JOB-07 | Failure mode — crash (`sys.exit(1)`): FAILED status, retry per max_retries, all attempts in history | `max_retries=2` on `POST /jobs`; poll for DEAD_LETTER; assert 3 ExecutionRecords |
| JOB-08 | Bad signature: node rejects before execution; execution record shows rejection, not crash | `POST /api/jobs/push` for valid def, then psql UPDATE to corrupt signature_payload, dispatch → assert SECURITY_REJECTED |
| JOB-09 | Revoked job definition: dispatch blocked at orchestrator, node never receives it | `PATCH /jobs/definitions/{id}` to set status=REVOKED, then `POST /api/dispatch` — BUT see critical gap below |
</phase_requirements>

---

## Summary

Phase 43 produces 9 standalone validation scripts plus 1 runner, covering the full job lifecycle against the live EE stack with 4 LXC nodes. The scripts follow the pattern established in `verify_ce_job.py` and `verify_lxc_nodes.py`: standalone, non-destructive, summary table output, CI-safe exit codes.

**Two critical API gaps** discovered during research that directly affect test assertions: (1) `POST /api/dispatch` does NOT check if the job definition has `status == "REVOKED"` — it dispatches unconditionally, making JOB-09's expected 4xx behaviour currently absent from the codebase; (2) `POST /jobs` with an impossible `env_tag` creates a PENDING job (HTTP 200/201), not a 4xx — making JOB-05 cross-tag failure assertion require polling for a never-completed job rather than an immediate error response.

**Primary recommendation:** Scripts must be written to match actual API behaviour. JOB-09 requires a code fix to `/api/dispatch` (add REVOKED guard) before it can pass. JOB-05 cross-tag assertion must poll for a PENDING-but-never-assigned state, not a 4xx, unless the `POST /jobs` endpoint is also patched.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | system | HTTP calls to API | Already used in all prior verify_*.py scripts |
| `cryptography` | system | Ed25519 key loading + signing | Already used in verify_ce_job.py |
| `threading` | stdlib | Concurrent job submission (JOB-04) | stdlib only — no asyncio per CONTEXT.md |
| `subprocess` | stdlib | `docker exec psql` for DB mutation (JOB-08) | Already used in verify_lxc_nodes.py |
| `pathlib`, `time`, `sys`, `base64`, `json` | stdlib | Path handling, polling, I/O | Already used in all verify_*.py scripts |

### No New Dependencies
All required functionality is available via existing project dependencies and stdlib. No new `pip install` required.

**Installation:** None needed beyond existing `pip install requests cryptography`.

---

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/scripts/
├── verify_job_01_fast.py         # JOB-01
├── verify_job_02_slow.py         # JOB-02
├── verify_job_03_memory.py       # JOB-03
├── verify_job_04_concurrent.py   # JOB-04
├── verify_job_05_env_routing.py  # JOB-05
├── verify_job_06_promotion.py    # JOB-06
├── verify_job_07_retry_crash.py  # JOB-07
├── verify_job_08_bad_sig.py      # JOB-08
├── verify_job_09_revoked.py      # JOB-09
└── run_job_matrix.py             # Runner
```

### Pattern 1: Script Skeleton (from verify_ce_job.py)
**What:** Each script: load secrets → get admin JWT → pre-flight → run assertions → summary table → exit code.
**When to use:** All 9 scripts follow this skeleton exactly.
```python
# Source: mop_validation/scripts/verify_ce_job.py (established pattern)
ROOT = Path(__file__).resolve().parents[2]   # .../Development/
MOP_DIR = ROOT / "master_of_puppets"
VALIDATION_DIR = ROOT / "mop_validation"
SECRETS_ENV = MOP_DIR / "secrets.env"
SIGNING_KEY_PATH = MOP_DIR / "secrets" / "signing.key"
BASE_URL = "https://localhost:8001"

def load_env(path): ...
def get_admin_token(base_url, password): ...  # POST /auth/login data= (form-encoded)
def sign_script(script, key_path): ...        # Ed25519, NO hash arg, base64 result
```

### Pattern 2: Dynamic Node Discovery
**What:** Look up nodes at runtime by `env_tag` field; never hardcode node IDs.
**When to use:** All node targeting in all 9 scripts.
```python
# GET /nodes (no /api/ prefix — established in verify_lxc_nodes.py)
def find_node_by_env_tag(base_url, jwt, env_tag):
    resp = requests.get(f"{base_url}/nodes",
                        headers={"Authorization": f"Bearer {jwt}"},
                        verify=False, timeout=10)
    nodes = resp.json()
    for n in nodes:
        if n.get("env_tag", "").upper() == env_tag.upper() and n.get("status") == "ONLINE":
            return n
    return None
```

### Pattern 3: Job Submission via POST /jobs
**What:** Direct job creation (not via `/api/dispatch`). Returns `guid` and HTTP 200 or 201.
**When to use:** JOB-01 through JOB-07. Do NOT use `/api/dispatch` for these (dispatch requires a pre-existing job definition).
```python
# Source: verified from main.py line 1009 + verify_ce_job.py
resp = requests.post(
    f"{BASE_URL}/jobs",
    json={
        "task_type": "python_script",
        "payload": {
            "script_content": SCRIPT,
            "signature": signature_b64,
            "secrets": {},
        },
        "env_tag": "DEV",
        "max_retries": 0,
    },
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
# Accept both 200 and 201 (Phase 41 finding: POST /jobs returns 200 in CE build)
job_guid = resp.json().get("guid")
```

### Pattern 4: Execution Record Polling
**What:** Poll `GET /api/executions?job_guid={guid}` until terminal status or timeout.
**When to use:** All scripts that verify execution outcome.
```python
# Source: verified from main.py line 184 — filter param is job_guid (not job_id)
def poll_execution(base_url, jwt, job_guid, timeout=30, interval=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{base_url}/api/executions",
                           params={"job_guid": job_guid},
                           headers={"Authorization": f"Bearer {jwt}"},
                           verify=False, timeout=10)
        records = resp.json()
        if records:
            terminal = {"COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"}
            if records[0].get("status") in terminal:
                return records
        time.sleep(interval)
    return None  # timed out
```

### Pattern 5: Job Definition Create + Dispatch (JOB-08, JOB-09)
**What:** Push a job definition via `/api/jobs/push`, then dispatch via `/api/dispatch`.
**When to use:** JOB-08 (needs definition to corrupt), JOB-09 (needs definition to revoke).
```python
# POST /api/jobs/push — returns 201 with job definition including id
push_resp = requests.post(
    f"{BASE_URL}/api/jobs/push",
    json={
        "name": "job-08-test",
        "script_content": SCRIPT,
        "signature_id": sig_id,
        "signature": signature_b64,
    },
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
job_def_id = push_resp.json().get("id")

# POST /api/dispatch — dispatches from definition
dispatch_resp = requests.post(
    f"{BASE_URL}/api/dispatch",
    json={"job_definition_id": job_def_id, "env_tag": "DEV"},
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
job_guid = dispatch_resp.json().get("job_guid")
```

### Pattern 6: DB Mutation via docker exec psql (JOB-08)
**What:** Corrupt stored `signature_payload` in the `scheduled_jobs` table.
**When to use:** JOB-08 only.
```python
# Source: established in CONTEXT.md — uses docker exec puppeteer-postgres-1
import subprocess
result = subprocess.run(
    [
        "docker", "exec", "puppeteer-postgres-1",
        "psql", "-U", "postgres", "-d", "postgres",
        "-c", f"UPDATE scheduled_jobs SET signature_payload='INVALIDSIG==' WHERE id='{job_def_id}'",
    ],
    capture_output=True, text=True, timeout=15,
)
# Check result.returncode == 0
```

### Pattern 7: Concurrent Submission (JOB-04)
**What:** 5 threads each POST one job, then poll all 5 GUIDs for completion.
**When to use:** JOB-04 only.
```python
import threading

guids = []
lock = threading.Lock()

def submit_job(n):
    script = f"import time; print('JOB-04 concurrent {n}'); time.sleep(5)"
    sig = sign_script(script, SIGNING_KEY_PATH)
    resp = requests.post(f"{BASE_URL}/jobs",
                        json={"task_type": "python_script",
                              "payload": {"script_content": script, "signature": sig, "secrets": {}},
                              "env_tag": "STAGING", "max_retries": 0},
                        headers={"Authorization": f"Bearer {jwt}"},
                        verify=False, timeout=10)
    if resp.status_code in (200, 201):
        with lock:
            guids.append(resp.json().get("guid"))

threads = [threading.Thread(target=submit_job, args=(n,)) for n in range(5)]
for t in threads: t.start()
for t in threads: t.join()
```

### Anti-Patterns to Avoid
- **Hardcoded node IDs:** Use dynamic `GET /nodes` discovery; node UUIDs change across re-enrollments.
- **Using `/api/nodes` prefix for node list:** The endpoint is `GET /nodes` (no `/api/` prefix) — established in verify_lxc_nodes.py and confirmed in main.py.
- **Using `job_id` query param on `/api/executions`:** The correct param is `job_guid`, not `job_id` — confirmed in main.py line 184.
- **Assuming POST /jobs returns 201:** Returns 200 in CE and 201 is possible; accept both (Phase 41 finding).
- **Checking heartbeat status as "HEALTHY":** Node status in API is `"ONLINE"` not `"HEALTHY"` (Phase 40 finding).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signing | Custom crypto | `cryptography` lib — exact pattern in `verify_ce_job.py` | Ed25519 has no hash arg — subtle API difference from RSA |
| Output formatting | Custom table lib | Plain f-strings: `[PASS] JOB-NN: desc` | Matches all prior scripts exactly |
| Script runner | Custom subprocess orchestration | Simple `subprocess.run([sys.executable, script], ...)` in `run_job_matrix.py` | Each script is standalone; runner just calls them |
| JWT auth | Custom token handling | `data={"username": "admin", "password": pw}` form-encoded POST to `/auth/login` | Must be form-encoded (OAuth2PasswordRequestForm) — Phase 40 finding |

---

## Common Pitfalls

### Pitfall 1: JOB-09 — dispatch does NOT block REVOKED job definitions
**What goes wrong:** The test asserts HTTP 4xx when dispatching a REVOKED definition, but `/api/dispatch` in `main.py` (lines 917–967) does NOT check `s_job.status`. It will happily dispatch a REVOKED definition, creating a PENDING job and returning HTTP 200.
**Why it happens:** The REVOKED guard only exists in `POST /api/jobs/push` (for updates), not in the dispatch path.
**How to avoid:** The fix must be applied to `main.py`'s `dispatch_job()` function before `create_job()` is called:
```python
if s_job.status == "REVOKED":
    raise HTTPException(409, detail={"error": "job_definition_revoked", "id": s_job.id})
```
**Warning signs:** Script gets HTTP 200 back from dispatch with a job_guid — not the expected 4xx.

### Pitfall 2: JOB-05 cross-tag — no eligible node creates PENDING job, not 4xx
**What goes wrong:** `POST /jobs` with `env_tag="NONEXISTENT"` succeeds (HTTP 200/201) and creates a PENDING job. The job stays PENDING indefinitely — no node ever picks it up. There is no "no eligible node" rejection at submission time.
**Why it happens:** `JobService.create_job()` accepts any env_tag without checking node availability. Routing happens lazily at `pull_work()` time.
**How to avoid:** Two valid approaches:
  1. Fix the `POST /jobs` endpoint to validate env_tag against live nodes at submission (inline fix).
  2. Adapt the test: assert that after a polling timeout the job status remains PENDING (no execution) — and document this as a known gap (no-node condition is silent, not rejected).
**Recommendation:** Given CONTEXT.md says "assert orchestrator returns HTTP 4xx (not a 200 that silently queues)" — this requires an inline code fix, which is in scope per GAP-02 (critical findings patched inline).

### Pitfall 3: JOB-08 — psql container name
**What goes wrong:** `docker exec puppeteer-postgres-1` fails if the container is named differently.
**Why it happens:** Container name depends on compose project name and service ordering.
**How to avoid:** Check actual container name at script start:
```python
result = subprocess.run(["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
                       capture_output=True, text=True)
pg_container = result.stdout.strip().split("\n")[0]  # take first match
```

### Pitfall 4: JOB-07 retry — attempt_number starts at 1 or 0?
**What goes wrong:** Asserting `attempt_number` values {1, 2, 3} when they may be {0, 1, 2}.
**Why it happens:** The `attempt_number` field in `ExecutionRecord` (confirmed in models.py line 295 as `Optional[int]`) — value depends on when it's set in `job_service.py`.
**How to avoid:** Inspect the first execution record from a retry scenario before writing the assertion. Alternatively, assert the SET of values (`{1, 2, 3}` or `{0, 1, 2}`) matches expected count and is contiguous — let the actual values inform the assertion.
**Recommendation:** Check the `attempt_number` logic in `job_service.py` during plan execution before hardcoding values.

### Pitfall 5: JOB-02 slow job — polling timeout
**What goes wrong:** 90s sleep job needs the poll to run for at least 120s — short timeouts cause false failures.
**Why it happens:** Default poll timeout in verify_ce_job.py is 30s (only enough for fast jobs).
**How to avoid:** JOB-02 specifically needs `timeout=120` or higher in the poll loop.

### Pitfall 6: JOB-08 — SECURITY_REJECTED vs stdout empty assertion
**What goes wrong:** The node reports `security_rejected=True` via `report_result()`, which sets job status to `SECURITY_REJECTED` (confirmed in `job_service.py` line 663-664). An `ExecutionRecord` IS created (with `status="SECURITY_REJECTED"`). The assertion is that `stdout` in that record is empty (script never ran).
**Why it happens:** The `report_result()` in `node.py` is called BEFORE execution when signature fails — the ExecutionRecord captures the rejection, not a script run.
**How to avoid:** Assert `record["status"] == "SECURITY_REJECTED"` AND `record["stdout"]` is None or empty. Do NOT assert that no ExecutionRecord exists — one will be created.

### Pitfall 7: JOB-04 — duplicate execution detection
**What goes wrong:** Checking GUIDs for duplicate records requires querying ALL execution records for all 5 GUIDs, not just the latest.
**Why it happens:** `GET /api/executions?job_guid=X` returns all records for that GUID (could be multiple if retry happened). A duplicate execution bug would create records from two DIFFERENT nodes for the same GUID.
**How to avoid:** For each of the 5 GUIDs, assert `len(records) == 1` (exactly 1 execution record) and `records[0]["status"] == "COMPLETED"`.

### Pitfall 8: JOB-06 env promotion — same job definition vs separate jobs
**What goes wrong:** All 3 dispatches use the SAME job definition but different `env_tag` overrides. The `env_tag` override in `DispatchRequest` routes the job to the right node.
**Why it happens:** `POST /api/dispatch` accepts `env_tag` override that takes precedence over the definition's own `env_tag` (confirmed in main.py line 927).
**How to avoid:** Use one job definition with no default env_tag, then dispatch 3 times with `env_tag="DEV"`, `env_tag="TEST"`, `env_tag="PROD"`. Wait for each to complete before dispatching the next.

---

## Code Examples

Verified patterns from source inspection:

### Ed25519 Signing (verified: verify_ce_job.py lines 98-111)
```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64

def sign_script(script: str, key_path: Path) -> str:
    key_pem = key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    sig_bytes = private_key.sign(script.encode("utf-8"))  # NO hash argument
    return base64.b64encode(sig_bytes).decode("ascii")
```

### Signature ID Lookup (verified: verify_ce_job.py lines 114-134)
```python
# Endpoint: /signatures  (NOT /api/signatures — no /api/ prefix)
resp = requests.get(f"{BASE_URL}/signatures",
                    headers={"Authorization": f"Bearer {jwt}"},
                    verify=False, timeout=10)
sigs = resp.json()
sig_id = sigs[0].get("id") if sigs else None
```

### All 9 Terminal Statuses (verified: main.py line 903)
```python
_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"}
```

### PATCH job definition status to REVOKED (verified: scheduler_service.py update path + JobDefinitionUpdate model)
```python
# PATCH /jobs/definitions/{id}  — uses JobDefinitionUpdate (all fields optional)
resp = requests.patch(
    f"{BASE_URL}/jobs/definitions/{job_def_id}",
    json={"status": "REVOKED"},
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10,
)
```

### run_job_matrix.py Runner Pattern
```python
import subprocess, sys, time
from pathlib import Path

SCRIPTS = [
    "verify_job_01_fast.py",
    "verify_job_02_slow.py",
    # ...
]

results = []
for script in SCRIPTS:
    t0 = time.time()
    path = Path(__file__).parent / script
    r = subprocess.run([sys.executable, str(path)], capture_output=False)
    elapsed = time.time() - t0
    results.append((script, r.returncode == 0, elapsed))

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== Job Matrix: {passed}/{len(SCRIPTS)} passed ===")
for script, ok, elapsed in results:
    status = "[PASS]" if ok else "[FAIL]"
    print(f"  {status} {script} ({elapsed:.1f}s)")
sys.exit(0 if passed == len(SCRIPTS) else 1)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded node IDs in test scripts | Dynamic `GET /nodes` discovery by env_tag | Phase 40 | Node IDs change on re-enroll; dynamic is mandatory |
| Test against npm dev server | Test against Docker stack only | Project policy | Consistent with CLAUDE.md |
| Monolithic validation script | One script per requirement | Phase 43 design | Independent re-run, clearer failure isolation |

---

## Critical Gaps Requiring Inline Fixes

These gaps block specific test assertions as written in CONTEXT.md. Per REQUIREMENTS.md GAP-02, critical findings are patched inline during the milestone.

### Gap 1: `/api/dispatch` does not block REVOKED job definitions (JOB-09)
**File:** `puppeteer/agent_service/main.py` — `dispatch_job()` function (~line 917)
**Fix:** After fetching `s_job`, add:
```python
if s_job.status == "REVOKED":
    raise HTTPException(
        status_code=409,
        detail={"error": "job_definition_revoked", "id": s_job.id,
                "message": "Cannot dispatch a REVOKED job definition."}
    )
```
**Confidence:** HIGH — code inspection confirmed absence of this check.

### Gap 2: `POST /jobs` accepts impossible env_tag silently (JOB-05)
**File:** `puppeteer/agent_service/services/job_service.py` — `create_job()` function
**Context:** CONTEXT.md requires HTTP 4xx for a cross-tag submission with no eligible nodes. Currently `create_job()` always returns PENDING regardless of whether any node can serve the tag.
**Fix options:**
  a. Add pre-flight node availability check in `create_job()` — raise HTTP 422 if no ONLINE node matches env_tag.
  b. Accept PENDING as valid and adapt test: poll for persistent PENDING + assert no execution records (documents the no-eager-rejection gap).
**Recommendation:** Option (a) is the correct fix per the requirement. Option (b) is a fallback if the plan deems option (a) out of scope.
**Confidence:** HIGH — code inspection confirmed.

---

## Open Questions

1. **`attempt_number` starting value in ExecutionRecord**
   - What we know: Field exists (`Optional[int]`) in `ExecutionRecordResponse`. Set somewhere in `job_service.py` retry path.
   - What's unclear: Does it start at 0 (zero-indexed) or 1 (one-indexed)?
   - Recommendation: During plan execution, add a quick code read of `job_service.py`'s retry logic to confirm before writing the JOB-07 assertion.

2. **JOB-06 env promotion — does the DEV job definition need `env_tag=None` to allow override?**
   - What we know: `DispatchRequest.env_tag` overrides `s_job.env_tag` (main.py line 927: `req.env_tag if req.env_tag is not None else s_job.env_tag`).
   - What's unclear: If the job definition has `env_tag="DEV"` baked in, does a dispatch override of `env_tag="PROD"` work correctly?
   - Recommendation: Create the JOB-06 job definition with `env_tag=None` (or omit it) to avoid ambiguity. The dispatch override then unambiguously controls routing.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Standalone Python scripts (no test framework) — matches all prior phase validation scripts |
| Config file | None — scripts are self-contained |
| Quick run command | `python3 mop_validation/scripts/verify_job_01_fast.py` |
| Full suite command | `python3 mop_validation/scripts/run_job_matrix.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-01 | Fast job completes with stdout | integration | `python3 mop_validation/scripts/verify_job_01_fast.py` | ❌ Wave 0 |
| JOB-02 | Slow job completes, node live in heartbeat | integration | `python3 mop_validation/scripts/verify_job_02_slow.py` | ❌ Wave 0 |
| JOB-03 | Memory job completes in direct mode | integration | `python3 mop_validation/scripts/verify_job_03_memory.py` | ❌ Wave 0 |
| JOB-04 | 5 concurrent jobs, no duplicate execution | integration | `python3 mop_validation/scripts/verify_job_04_concurrent.py` | ❌ Wave 0 |
| JOB-05 | Env-tag routing + cross-tag rejection | integration | `python3 mop_validation/scripts/verify_job_05_env_routing.py` | ❌ Wave 0 |
| JOB-06 | Env promotion chain DEV→TEST→PROD | integration | `python3 mop_validation/scripts/verify_job_06_promotion.py` | ❌ Wave 0 |
| JOB-07 | Crash → FAILED → retry → DEAD_LETTER | integration | `python3 mop_validation/scripts/verify_job_07_retry_crash.py` | ❌ Wave 0 |
| JOB-08 | Bad signature → SECURITY_REJECTED | integration | `python3 mop_validation/scripts/verify_job_08_bad_sig.py` | ❌ Wave 0 |
| JOB-09 | REVOKED definition → 4xx at orchestrator | integration | `python3 mop_validation/scripts/verify_job_09_revoked.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Run the single script for the scenario being implemented
- **Per wave merge:** `python3 mop_validation/scripts/run_job_matrix.py`
- **Phase gate:** Full matrix green before `/gsd:verify-work`

### Wave 0 Gaps
All 10 files must be created (9 scripts + 1 runner). No existing test infrastructure covers these scenarios.

- [ ] `mop_validation/scripts/verify_job_01_fast.py`
- [ ] `mop_validation/scripts/verify_job_02_slow.py`
- [ ] `mop_validation/scripts/verify_job_03_memory.py`
- [ ] `mop_validation/scripts/verify_job_04_concurrent.py`
- [ ] `mop_validation/scripts/verify_job_05_env_routing.py`
- [ ] `mop_validation/scripts/verify_job_06_promotion.py`
- [ ] `mop_validation/scripts/verify_job_07_retry_crash.py`
- [ ] `mop_validation/scripts/verify_job_08_bad_sig.py`
- [ ] `mop_validation/scripts/verify_job_09_revoked.py`
- [ ] `mop_validation/scripts/run_job_matrix.py`
- [ ] Inline fix to `puppeteer/agent_service/main.py` — REVOKED guard in `dispatch_job()` (required for JOB-09)
- [ ] Inline fix to `puppeteer/agent_service/services/job_service.py` or `main.py` — no-eligible-node 422 on `POST /jobs` (required for JOB-05 per CONTEXT.md spec)

---

## Sources

### Primary (HIGH confidence)
- `puppeteer/agent_service/main.py` — all route handlers inspected directly; dispatch, executions, jobs, job definitions
- `puppeteer/agent_service/services/job_service.py` — create_job, pull_work, receive_result logic
- `puppeteer/agent_service/models.py` — DispatchRequest, ExecutionRecordResponse, attempt_number field
- `mop_validation/scripts/verify_ce_job.py` — canonical signing, submission, polling, summary pattern
- `mop_validation/scripts/verify_lxc_nodes.py` — canonical multi-requirement, node discovery, summary table pattern
- `puppets/environment_service/node.py` — SECURITY_REJECTED path: `security_rejected=True` flag in report_result

### Secondary (MEDIUM confidence)
- `.planning/phases/43-job-test-matrix/43-CONTEXT.md` — all locked decisions verified against actual API code
- `.planning/STATE.md` — accumulated decisions from prior phases (Phase 40 node status "ONLINE" not "HEALTHY", etc.)

### Tertiary (LOW confidence)
- None — all critical findings verified against source code directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, verified via source inspection
- Architecture patterns: HIGH — all API endpoints and response shapes verified in main.py and service files
- Pitfalls: HIGH — gaps 1 and 2 confirmed by reading the actual dispatch and create_job code
- Validation architecture: HIGH — script structure mirrors existing verify_*.py files exactly

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable backend; longer if no API changes)

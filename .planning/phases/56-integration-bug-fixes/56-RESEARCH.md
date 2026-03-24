# Phase 56: Integration Bug Fixes - Research

**Researched:** 2026-03-24
**Domain:** E2E verification of four pre-applied bug fixes + Playwright test authoring
**Confidence:** HIGH

## Summary

Phase 56 is a verification-and-close-out phase. Phase 54 already applied all four code fixes (INT-01 through INT-04) to the codebase. The task is to confirm each fix works end-to-end in the live Docker stack, write a persistent Playwright test suite that covers all four scenarios, obtain a human sign-off checkpoint, then formally mark seven requirements complete in REQUIREMENTS.md.

The code fixes are verified in place: `GuidedDispatchCard.tsx` sends `script_content` at both dispatch sites (lines 160 and 214), `Queue.tsx` was confirmed by vitest to fetch `/jobs` and `/nodes` without the `/api` double-prefix, `Jobs.tsx` uses the correct full path `/api/jobs/${guid}/executions/export` (line 262), and `job_service.py list_jobs()` returns `retry_count`, `max_retries`, `retry_after` (as ISO string), and `originating_guid` (lines 199-202).

The plan structure is simple: a single plan (56-01) covering stack E2E verification, a new Playwright test file at `mop_validation/scripts/test_phase56_integration.py`, a blocking human checkpoint, and a REQUIREMENTS.md close-out task.

**Primary recommendation:** Write the Playwright test file first (it provides the evidence), run it against the live Docker stack, use results as the body of 56-VERIFICATION.md, then update REQUIREMENTS.md only after the human checkpoint passes.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full Docker stack E2E verification required (not code review only)
- Playwright tests against the live `compose.server.yaml` stack
- Produce a formal `56-VERIFICATION.md` as the canonical evidence document
- Test all 3 runtimes end-to-end: Python, Bash, and PowerShell (RT-01, RT-02 in scope)
- INT-04 retry state verified with a live retried job in the stack (not just unit test evidence)
- Write persistent Playwright test file at `mop_validation/scripts/test_phase56_integration.py`
- Covers all 4 scenarios:
  1. Guided form → Python/Bash/PowerShell job COMPLETED (INT-01 / JOB-01 / RT-01 / RT-02)
  2. Queue view shows PENDING/RUNNING job live data (INT-02 / VIS-02)
  3. CSV export from job detail drawer returns 200 with CSV content (INT-03 / SRCH-10)
  4. Job drawer shows retry_count/retry_after for retried job; provenance link for resubmitted job (INT-04 / JOB-04 / JOB-05)
- Blocking human checkpoint included in the plan
- Operator must manually confirm: (1) guided form execution in browser, (2) Queue live data, (3) CSV export
- REQUIREMENTS.md close-out is gated on the human checkpoint — requirements only update after sign-off
- Single plan (56-01-PLAN.md): verification + Playwright tests + human checkpoint + REQUIREMENTS.md update
- Update 7 checkboxes from `[ ]` to `[x]`: JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05
- Update traceability rows: Phase 56 → Phase 54, Status Pending → Complete
- Coverage count updated to reflect all 7 now resolved

### Claude's Discretion
- Exact Playwright test structure (session reuse, JWT injection pattern per CLAUDE.md)
- Whether retry state is verified by submitting a job with max_retries=1 or finding an existing failed job
- Exact VERIFICATION.md section layout and evidence formatting

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-01 | Operator can submit a job using a structured guided form (runtime selector, script textarea, target environment dropdown, capability tag chips) | GuidedDispatchCard.tsx sends `script_content` at both dispatch sites (lines 160, 214) — INT-01 fix confirmed in source |
| RT-01 | Operator can submit a Bash script job using unified `script` task type with `runtime: bash` | `runtime` field in generatedPayload; backend `execute_task` dispatches by runtime map — needs live E2E confirmation |
| RT-02 | Operator can submit a PowerShell script job using unified `script` task type with `runtime: powershell` | Same dispatch path as RT-01; PowerShell installed in Containerfile.node — needs live E2E confirmation |
| VIS-02 | Dedicated live Queue dashboard view shows PENDING, RUNNING, and recently completed jobs in real time | Queue.tsx fetch URLs confirmed correct by vitest Queue.test.tsx — needs live stack render check |
| SRCH-10 | Operator can download execution records for a job as CSV from the job detail drawer | Endpoint `GET /api/jobs/{guid}/executions/export` exists (main.py line 2357); Jobs.tsx calls it at line 262 — needs live HTTP 200 confirmation |
| JOB-04 | Operator can view job details including retry state (retry_count, max_retries, retry_after) in drawer | list_jobs() returns all four retry fields (lines 199-202 job_service.py); Jobs.tsx renders retry display (line 503) — needs live drawer check |
| JOB-05 | Operator can resubmit an exhausted-retry failed job; originating_guid stored for traceability | list_jobs() returns originating_guid; Jobs.tsx renders provenance link (lines 514-518) — needs live resubmit + drawer verification |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| playwright (Python) | latest installed | Browser automation for E2E tests | Project standard — CLAUDE.md mandates Python Playwright for all UI tests |
| requests | latest installed | HTTP API calls to FastAPI stack | Used across all existing test scripts in mop_validation |
| cryptography | latest installed | Ed25519 key generation + job signing | Required for signing jobs — used in test_local_stack.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | project version | Test runner for Playwright test file | Wrap Playwright tests in pytest functions for consistent CI output |
| python-dotenv (manual parse) | N/A | Load secrets.env credentials | Pattern from test_local_stack.py — manual parse of `KEY=VALUE` lines |

**Installation:** All libraries already installed in the mop_validation environment — no new installs required.

---

## Architecture Patterns

### Test File Layout
```
mop_validation/scripts/test_phase56_integration.py
  - load_secrets()          — reads mop_validation/secrets.env (ADMIN_PASSWORD)
  - get_jwt_token()         — POST /auth/login with form-encoded data
  - sign_script()           — Ed25519 sign via cryptography lib
  - ensure_signing_key()    — load or generate key, upload if not registered
  - submit_job_api()        — POST /jobs with task_type=script, runtime=X
  - wait_for_job_status()   — poll GET /jobs/{guid} until terminal state
  - test_int01_guided_form_python()
  - test_int01_guided_form_bash()
  - test_int01_guided_form_powershell()
  - test_int02_queue_view()
  - test_int03_csv_export()
  - test_int04_retry_state()
  - test_int04_provenance_link()
  - main()                  — run all, print PASS/FAIL summary
```

### Pattern 1: JWT Injection for Playwright
```python
# Source: CLAUDE.md, mop_validation/scripts/test_playwright.py
token = get_jwt_token(ADMIN_USER, ADMIN_PASSWORD)
page.goto(BASE_URL)
page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")
page.reload()
page.wait_for_load_state("networkidle", timeout=15000)
```
Never use form fill for authentication. Always inject JWT directly.

### Pattern 2: Browser Launch
```python
# Source: CLAUDE.md
browser = p.chromium.launch(args=['--no-sandbox'], headless=True)
```
Always include `--no-sandbox` — Chrome crashes on Linux without it.

### Pattern 3: API Login (form-encoded)
```python
# Source: mop_validation/scripts/test_local_stack.py line 155
import requests
r = requests.post(f"{BASE_URL}/auth/login",
                  data={"username": "admin", "password": ADMIN_PASSWORD},
                  verify=False)
token = r.json()["access_token"]
```
The FastAPI OAuth2 endpoint requires `application/x-www-form-urlencoded`, not JSON.

### Pattern 4: Job Signing
```python
# Source: mop_validation/scripts/test_local_stack.py lines 133-135
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sig = private_key.sign(script_content.encode("utf-8"))
import base64
sig_b64 = base64.b64encode(sig).decode()
```

### Pattern 5: Guided Form Dispatch (the INT-01 fix)
The guided form in `GuidedDispatchCard.tsx` submits jobs to `POST /jobs` with:
```json
{
  "task_type": "script",
  "runtime": "python",
  "payload": { "script_content": "..." },
  "signature_id": "<id>",
  "signature": "<base64>",
  "target_tags": ["..."]
}
```
Key: the payload field is `script_content` (not `script`). This is the INT-01 fix. The API test equivalent is `POST /jobs` with `task_type=script`.

### Pattern 6: CSV Export Verification (INT-03)
```python
# Source: Jobs.tsx line 262; main.py line 2357
headers = {"Authorization": f"Bearer {token}"}
r = requests.get(f"{BASE_URL}/api/jobs/{guid}/executions/export",
                 headers=headers, verify=False)
assert r.status_code == 200
assert "text/csv" in r.headers.get("content-type", "")
assert r.text.startswith("job_guid")  # first CSV header
```

### Pattern 7: Retry State Verification (INT-04)
Submit a job with `max_retries=1` and a script that exits non-zero:
```python
fail_script = "import sys; sys.exit(1)"
# POST /jobs with max_retries=1
# Wait for FAILED or DEAD_LETTER status
# GET /jobs — check retry_count > 0, retry_after is a string, originating_guid behavior
```
Then verify the drawer via Playwright: navigate to `/jobs`, open drawer for the failed job, assert retry counter displays.

### Pattern 8: Resubmit + Provenance (JOB-05)
The resubmit button in the Jobs drawer creates a new job with `originating_guid` set. To test:
1. Submit a job, wait for COMPLETED/FAILED
2. Via Playwright, click the resubmit button in the drawer
3. Check that a new job appears with `originating_guid` == original GUID
4. Open the new job's drawer, assert "Resubmitted from" link appears

### Anti-Patterns to Avoid
- **Using `/npm run dev` for testing:** Always test against Docker stack (`compose.server.yaml`). Never use local dev server.
- **Using `fill()` for React controlled inputs:** React controlled inputs do not respond reliably to Playwright `fill()`. Use native value setter + `dispatchEvent` or localStorage JWT injection.
- **Calling `/api/jobs` in Queue.tsx:** The INT-02 fix removes the `/api` prefix from Queue.tsx fetch calls. Tests should confirm `authenticatedFetch` calls use `/jobs` not `/api/jobs`.
- **Checking `textarea count == 0` for guided form verification:** Guided form has textareas (Script field). Check for `[ADV]` button and guided-mode controls instead.
- **Using task_type `python_script`:** This returns HTTP 422 since Phase 47. Always use `task_type=script` with `runtime=python`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signing | Custom signing implementation | `cryptography` lib via `private_key.sign(content.encode())` | Already used in test_local_stack.py; two-arg verify pattern established |
| JWT extraction from login | Custom JWT parse | `r.json()["access_token"]` from `/auth/login` response | The access_token field is returned directly |
| Stack URL discovery | Dynamic URL detection | Hardcode `https://localhost:8001` (API) and `http://localhost:8080` (dashboard) | These are the established test constants |

---

## Common Pitfalls

### Pitfall 1: Double `/api` Prefix
**What goes wrong:** `authenticatedFetch` in `auth.ts` prepends `/api` automatically. Calling `authenticatedFetch('/api/jobs/...')` results in `/api/api/jobs/...` (404). Only the CSV export endpoint at `GET /api/jobs/{guid}/executions/export` uses the full prefix in `authenticatedFetch` — this is intentional and was the INT-03 fix.
**Why it happens:** The endpoint was registered under `/api/jobs/...` instead of `/jobs/...` in main.py.
**How to avoid:** API test directly at `https://localhost:8001/api/jobs/{guid}/executions/export` with Authorization header. Playwright test verifies via drawer UI click, not by inspecting network calls.

### Pitfall 2: task_type `python_script` Returns 422
**What goes wrong:** Submitting a job with `task_type=python_script` gets HTTP 422 since Phase 47.
**How to avoid:** Always use `task_type=script` with `runtime=python|bash|powershell`.

### Pitfall 3: PowerShell Node Availability
**What goes wrong:** PowerShell runtime jobs may not complete if no enrolled node has PowerShell in its capabilities.
**Why it happens:** Nodes report capabilities based on what's installed in their image.
**How to avoid:** For E2E PowerShell test, submit job with `target_tags: []` (any node) or verify node capability before test. The standard node image has PowerShell via Containerfile.node (RT-03 is already complete).

### Pitfall 4: Retry Test Timing
**What goes wrong:** Job with `max_retries=1` may take time to exhaust retries due to `retry_after` backoff delay.
**Why it happens:** `backoff_multiplier` applies exponential delay. `retry_after` is set to `utcnow() + max(delay, 1.0)` seconds.
**How to avoid:** Submit with `max_retries=1`; the first failure increments retry_count to 1 and sets retry_after ~1–30 seconds out. Use `wait_for_job_status()` with timeout=120s. Alternatively check DEAD_LETTER status which fires after retries exhausted.

### Pitfall 5: secrets.env Location
**What goes wrong:** Test loads secrets from wrong path.
**How to avoid:** The established pattern from test_local_stack.py resolves to `~/Development/master_of_puppets/secrets.env` (not mop_validation). The test_phase56_integration.py should use the same resolution: `Path(__file__).resolve().parents[2] / "master_of_puppets" / "secrets.env"`.

### Pitfall 6: Auth endpoint path
**What goes wrong:** Using `/api/auth/token` instead of `/auth/login` for API login.
**Why it happens:** Discovered in Phase 55 — the correct endpoint is `/auth/login`, not `/api/auth/token`.
**How to avoid:** Use `POST /auth/login` with form-encoded data as established in test_local_stack.py.

---

## Code Examples

### Verified: Job submission with script task type
```python
# Source: mop_validation/scripts/test_local_stack.py, adapted for Phase 56
import requests, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def submit_script_job(token, script_content, runtime, target_tags, sig_b64, sig_id):
    r = requests.post(
        "https://localhost:8001/jobs",
        json={
            "task_type": "script",
            "runtime": runtime,
            "payload": {"script_content": script_content},
            "signature": sig_b64,
            "signature_id": sig_id,
            "target_tags": target_tags,
            "max_retries": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
    )
    assert r.status_code in (200, 201), f"Job submit failed: {r.status_code} {r.text}"
    return r.json()["guid"]
```

### Verified: CSV export check
```python
# Source: Jobs.tsx line 262; main.py line 2357
def check_csv_export(token, job_guid):
    r = requests.get(
        f"https://localhost:8001/api/jobs/{job_guid}/executions/export",
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
    )
    assert r.status_code == 200, f"CSV export returned {r.status_code}"
    assert "job_guid" in r.text, "CSV headers missing"
    return r.text
```

### Verified: Retry fields in list_jobs response
```python
# Source: job_service.py lines 199-202
# GET /jobs returns items with: retry_count, max_retries, retry_after (ISO str), originating_guid
def check_retry_fields(token, job_guid):
    r = requests.get(
        "https://localhost:8001/jobs",
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
    )
    items = r.json()["items"]
    job = next(i for i in items if i["guid"] == job_guid)
    assert "retry_count" in job
    assert "max_retries" in job
    assert "retry_after" in job  # None or ISO string
    assert "originating_guid" in job  # None or GUID string
    if job["retry_after"] is not None:
        from datetime import datetime
        datetime.fromisoformat(job["retry_after"])  # must be parseable
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `task_type=python_script` | `task_type=script` + `runtime=python` | Phase 47 | Old type returns 422; all new jobs must use script type |
| `payload: { script: ... }` in guided form | `payload: { script_content: ... }` | Phase 54 (INT-01 fix) | Wrong key caused nodes to receive empty script |
| `Queue.tsx` fetching `/api/jobs` and `/api/nodes` | Fetching `/jobs` and `/nodes` | Phase 54 (INT-02 fix) | Was causing 404 on Queue data load |
| Missing retry fields in list_jobs() | `retry_count`, `max_retries`, `retry_after`, `originating_guid` included | Phase 54 (INT-04 fix) | Drawer retry countdown and provenance link now have data |

---

## Open Questions

1. **PowerShell node availability during E2E test**
   - What we know: RT-03 (PowerShell in node image) is Complete. Local nodes in `mop_validation/local_nodes/` may or may not be running.
   - What's unclear: Whether the Docker stack has live nodes enrolled with PowerShell capability at test time.
   - Recommendation: The Playwright test for RT-02/PowerShell should submit a job and wait up to 60s. If no node picks it up, mark as PENDING and note in VERIFICATION.md with a caveat — the dispatch API path is the same regardless of which node picks it up. The critical check is that the API accepts the job (200) and the payload reaches a node.

2. **Resubmit button state in drawer (JOB-05)**
   - What we know: The resubmit button is shown for FAILED jobs with retries exhausted (`retry_count >= max_retries`). Jobs.tsx renders it via the inline confirm pattern.
   - What's unclear: The exact CSS selector or test ID for the resubmit button — needs inspection of Jobs.tsx around line 400-520.
   - Recommendation: During Playwright test authoring, locate the button by text ("Resubmit") or aria role within the drawer panel.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `puppeteer/pytest.ini` or `puppeteer/setup.cfg` (backend); `puppeteer/dashboard/vitest.config.ts` (frontend) |
| Quick run command | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-01 | Guided form submits job with script_content key | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |
| RT-01 | Bash job dispatched and completed end-to-end | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |
| RT-02 | PowerShell job dispatched and accepted by API | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |
| VIS-02 | Queue view renders PENDING/RUNNING jobs (no 404) | E2E Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |
| SRCH-10 | CSV export returns 200 with CSV content | API + Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |
| JOB-04 | Drawer shows retry_count, max_retries, retry_after | unit (existing) + E2E | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ✅ existing |
| JOB-05 | Resubmit creates job with originating_guid; drawer shows provenance | API + Playwright | `python3 mop_validation/scripts/test_phase56_integration.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x`
- **Per wave merge:** `cd puppeteer && pytest && cd dashboard && npm run test`
- **Phase gate:** Full suite green + `python3 mop_validation/scripts/test_phase56_integration.py` all-pass before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/test_phase56_integration.py` — covers JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04 (E2E), JOB-05
- [ ] `mop_validation/scripts/test_phase56_integration.py` requires: live Docker stack (`puppeteer/compose.server.yaml` up), enrolled node, signing key in `secrets/`

*(Existing unit coverage: `puppeteer/tests/test_list_jobs_retry_fields.py` covers INT-04 backend — no gaps there)*

---

## Sources

### Primary (HIGH confidence)
- Source code inspection: `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` — INT-01 fix confirmed at lines 160, 214
- Source code inspection: `puppeteer/dashboard/src/views/__tests__/Queue.test.tsx` — INT-02 URL pattern confirmed
- Source code inspection: `puppeteer/dashboard/src/views/Jobs.tsx` line 262 — INT-03 export path confirmed
- Source code inspection: `puppeteer/agent_service/services/job_service.py` lines 199-202 — INT-04 retry fields confirmed
- Source code inspection: `puppeteer/agent_service/main.py` lines 2357-2374 — CSV export endpoint exists and is registered
- Source code inspection: `mop_validation/scripts/test_local_stack.py` — signing, login, job submission patterns
- Source code inspection: `mop_validation/scripts/test_playwright.py` — Playwright JWT injection, browser launch patterns
- Project instructions: `CLAUDE.md` — testing rules (Docker stack only, --no-sandbox, localStorage JWT, form-encoded login)

### Secondary (MEDIUM confidence)
- Phase 54 CONTEXT.md decisions — confirms INT-01–04 fix descriptions and approach
- Phase 55 STATE.md decisions — confirms auth endpoint is `/auth/login`, UI route is `/scheduled-jobs`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; verified from source
- Architecture: HIGH — all patterns verified from existing test files and source code
- Pitfalls: HIGH — discovered from CLAUDE.md, STATE.md decisions, and source code inspection

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable codebase; phase is verification-only, no new libraries)

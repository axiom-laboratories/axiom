---
phase: 47-ce-runtime-expansion
verified: 2026-03-22T17:45:00Z
status: gaps_found
score: 11/12 must-haves verified
re_verification: false
gaps:
  - truth: "Submitting task_type: python_script returns HTTP 422 with a clear error message"
    status: partial
    reason: "models.py model_validator correctly rejects python_script from the public API. However, main.py POST /api/dispatch (line 986) still hardcodes task_type='python_script' when building JobCreate from a ScheduledJob. This means every CI/CD dispatch call will itself trigger the 422 validator — the dispatch endpoint is broken."
    artifacts:
      - path: "puppeteer/agent_service/main.py"
        issue: "Line 986: JobCreate(task_type='python_script', ...) in the /api/dispatch handler. Model validator rejects this with 422."
    missing:
      - "Change line 986 in main.py /api/dispatch to use task_type='script' and pass runtime=getattr(s_job, 'runtime', None) or 'python' (same pattern as scheduler_service.py execute_scheduled_job)"
human_verification:
  - test: "Submit a job via POST /api/dispatch with a valid ScheduledJob ID"
    expected: "Job is created and queued successfully; poll URL returned with 200"
    why_human: "Cannot invoke live API in static verification; this dispatch path is broken at the model validation layer"
  - test: "Submit a Script job from the Jobs dashboard using Bash runtime"
    expected: "Runtime dropdown appears when Script task type is selected; job is submitted with runtime=bash in body; after node execution, display_type shows 'script (bash)' in jobs table"
    why_human: "End-to-end runtime execution and display requires live stack"
  - test: "Attempt to submit a job with an unlisted runtime value (e.g. 'ruby') via API"
    expected: "HTTP 422 response with validation error message"
    why_human: "Requires live API call to confirm Pydantic validation is active in running service"
---

# Phase 47: CE Runtime Expansion Verification Report

**Phase Goal:** Enable operators to dispatch and schedule Bash and PowerShell scripts alongside Python, giving the platform a language-agnostic script runtime so nodes can serve heterogeneous workloads without custom images.
**Verified:** 2026-03-22T17:45:00Z
**Status:** gaps_found — 1 blocker gap in main.py dispatch endpoint
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Containerfile.node installs PowerShell Core via Microsoft APT repo | VERIFIED | Lines 11-15: `packages-microsoft-prod.deb` downloaded, `powershell` installed in single RUN layer |
| 2  | node.py execute_task handles task_type == 'script' for python, bash, and powershell runtimes | VERIFIED | Line 583: `if task_type == "script":` branch; RUNTIME_EXT/RUNTIME_CMD dispatch maps at lines 576-582 |
| 3  | Script written to temp file with correct extension, mounted into container, cleaned up in finally | VERIFIED | Lines 618, 647-649, 694-696: tmp_path, mounts.append, finally: os.remove |
| 4  | All runtimes perform the same signature verification as the existing python_script branch | VERIFIED | Lines 594-605: same `public_key.verify(sig_bytes, script.encode('utf-8'))` path |
| 5  | Submitting task_type: python_script returns HTTP 422 (PUBLIC API) | VERIFIED | models.py lines 27-30: model_validator raises ValueError with clear message |
| 6  | Submitting task_type: python_script via /api/dispatch returns HTTP 422 | FAILED | main.py line 986: `JobCreate(task_type="python_script", ...)` — dispatch endpoint will be rejected by its own model validator, breaking the CI/CD path |
| 7  | Submitting task_type: script with unknown runtime returns HTTP 422 | VERIFIED | models.py line 18: `Literal["python", "bash", "powershell"]` + model_validator rejects invalid values |
| 8  | Submitting task_type: script without runtime field returns HTTP 422 | VERIFIED | models.py lines 32-33: model_validator raises "runtime is required when task_type is 'script'" |
| 9  | Every job in list_jobs response includes a display_type field computed server-side | VERIFIED | job_service.py line 26: `_compute_display_type()` helper; line 72: `"display_type"` key in list_jobs response dict |
| 10 | ScheduledJob DB model has a runtime column defaulting to 'python' | VERIFIED | db.py line 77: `ScheduledJob.runtime: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="python")` |
| 11 | execute_scheduled_job fires task_type='script' with runtime from ScheduledJob.runtime | VERIFIED | scheduler_service.py lines 154, 168: `runtime = getattr(s_job, 'runtime', None) or 'python'`; `task_type="script"` |
| 12 | migration_v38.sql adds runtime column to both scheduled_jobs and jobs tables | VERIFIED | puppeteer/migration_v38.sql: two ALTER TABLE IF NOT EXISTS statements present |

**Score:** 11/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/tests/test_runtime_expansion.py` | Test scaffold for RT-01 to RT-07 | VERIFIED | 7 test functions; all 7 pass GREEN |
| `puppets/Containerfile.node` | Node image with Python + Bash + PowerShell | VERIFIED | powershell installed via Microsoft APT repo (Debian 12 .deb method) |
| `puppets/environment_service/node.py` | Script task_type execution for all three runtimes | VERIFIED | task_type == "script" branch at line 583; python_script removed as task_type dispatch branch |
| `puppeteer/agent_service/models.py` | JobCreate with runtime Literal validation + model_validator; JobResponse with display_type | VERIFIED | Literal["python","bash","powershell"], model_validator, display_type field all present |
| `puppeteer/agent_service/services/job_service.py` | _compute_display_type helper; display_type in list_jobs | VERIFIED | _compute_display_type at line 26; display_type in list_jobs dict at line 72 |
| `puppeteer/agent_service/db.py` | ScheduledJob.runtime column; Job.runtime column | VERIFIED | Both runtime columns present (lines 45, 77) |
| `puppeteer/agent_service/services/scheduler_service.py` | execute_scheduled_job using task_type='script' + runtime | VERIFIED | task_type="script" at line 168; runtime wired from ScheduledJob |
| `puppeteer/migration_v38.sql` | ALTER TABLE SQL for scheduled_jobs and jobs | VERIFIED | Both ALTER TABLE statements with IF NOT EXISTS guards |
| `puppeteer/dashboard/src/views/Jobs.tsx` | Runtime dropdown; display_type column in jobs table | VERIFIED | display_type field in Job interface (line 55); conditional runtime dropdown (line 471); display_type ?? task_type ?? '—' in table (lines 195, 605) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| node.py execute_task | ContainerRuntime.run() | temp file mount in mounts list | WIRED | Line 649: `mounts.append(f"{tmp_path}:{tmp_path}:ro")`; runtime_engine.run() at line 653 |
| node.py | signature verification | same verify path as python_script branch | WIRED | Line 605: `public_key.verify(sig_bytes, script.encode('utf-8'))` |
| models.py JobCreate | job_service.py create_job | runtime field merged into payload dict before storage | WIRED | job_service.py lines 125-128: `payload_dict["runtime"] = job_req.runtime` |
| job_service.py list_jobs | JobResponse | display_type key in response dict | WIRED | Line 72: `"display_type": _compute_display_type(job.task_type, payload)` |
| scheduler_service.py execute_scheduled_job | Job row | task_type='script', runtime from ScheduledJob.runtime | WIRED | Lines 168, 178: `task_type="script"`, `runtime=runtime` |
| main.py /api/dispatch | JobCreate | task_type and runtime wired correctly | NOT WIRED | Line 986: hardcoded `task_type="python_script"` — model_validator will reject this with 422 |
| Jobs.tsx submission form | POST /api/jobs | runtime field included in request body alongside task_type | WIRED | Lines 368-369: `if (newTaskType === 'script') { body.runtime = newRuntime; }` |
| Jobs.tsx table row | job.display_type | display_type ?? task_type fallback | WIRED | Lines 195, 605: `{job.display_type ?? job.task_type ?? '—'}` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| RT-01 | 47-01 | Operator can submit Bash script job via task_type=script with runtime=bash | SATISFIED | node.py script branch handles bash; test_bash_job_accepted GREEN |
| RT-02 | 47-01 | Operator can submit PowerShell script job via task_type=script with runtime=powershell | SATISFIED | node.py script branch handles powershell/pwsh; test_powershell_job_accepted GREEN |
| RT-03 | 47-01 | Standard node image ships Python, Bash, and PowerShell | SATISFIED | Containerfile.node: powershell installed via MS APT repo; Bash is pre-installed in Debian base; test_containerfile_has_powershell GREEN |
| RT-04 | 47-02 | Backend validates runtime field at job creation, rejects unknown values with HTTP 422 | SATISFIED | models.py: Literal["python","bash","powershell"] + model_validator; test_invalid_runtime_rejected GREEN |
| RT-05 | 47-02 + 47-03 | Job list renders display_type computed server-side | SATISFIED (backend+frontend) | job_service._compute_display_type wired; Jobs.tsx shows display_type; frontend build passes |
| RT-06 | N/A | Existing python_script task type retained as alias | DROPPED by design | CONTEXT.md explicitly removed RT-06 from scope — no existing deployments. REQUIREMENTS.md marks as `[ ]` Pending. This is correct per phase decision, NOT an implementation gap. However, main.py /api/dispatch was not updated and still submits python_script — this is a real implementation gap in RT-04/RT-07 wiring, not RT-06 itself. |
| RT-07 | 47-02 | Operator can schedule Bash or PowerShell jobs via job definitions | SATISFIED (scheduler_service) | ScheduledJob.runtime column; execute_scheduled_job uses task_type="script"; migration_v38.sql; test_scheduled_job_runtime_field GREEN. NOTE: /api/dispatch dispatch path has a bug — see gap. |

**Orphaned requirements:** None. All RT-01 through RT-07 are mapped.

**RT-06 note:** The requirement in REQUIREMENTS.md (`[ ]` Pending) was deliberately dropped in CONTEXT.md with the decision "python_script is dropped — no existing deployments." The implementation correctly rejects python_script with 422. REQUIREMENTS.md status should be updated from Pending to Dropped, but this does not block phase goal achievement.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppeteer/agent_service/main.py` | 986 | `task_type="python_script"` in /api/dispatch JobCreate call | BLOCKER | The model_validator in JobCreate will raise ValueError on "python_script", causing every CI/CD dispatch call to return HTTP 422. This endpoint is non-functional post-phase-47. |
| `puppets/environment_service/node.py` | 521 | `run_python_script()` method — dead code, never called from execute_task | WARNING | Orphaned method; execution now goes through the unified `script` branch. No runtime impact but creates confusion. |
| `puppeteer/agent_service/db.py` | 24 | Comment `# python_script, web_task` on task_type column | INFO | Stale comment — python_script is no longer a valid value per model_validator. Minor misleading documentation. |

### Human Verification Required

#### 1. CI/CD Dispatch Endpoint

**Test:** Call `POST /api/dispatch` with a valid ScheduledJob ID using a service principal token.
**Expected:** HTTP 200, job created and queued, poll URL returned.
**Why human:** Static verification confirmed the code bug (line 986). Human verification needed to confirm the fix resolves it end-to-end.

#### 2. Bash Script Job Execution

**Test:** Submit a Script job with runtime=bash and script content `echo "hello from bash"` via the Jobs dashboard. Verify node executes it.
**Expected:** Job completes with exit_code=0; output contains "hello from bash"; Jobs table shows "script (bash)" in the Type column.
**Why human:** Requires a running stack with a connected node; execution path involves container runtime.

#### 3. Runtime Validation at API

**Test:** Submit `POST /api/jobs` with `{"task_type":"script","runtime":"ruby","payload":{}}` directly.
**Expected:** HTTP 422 with validation error referencing the runtime field.
**Why human:** Requires live API call to confirm Pydantic validation is active in the running service.

#### 4. Runtime Dropdown Conditional Behaviour

**Test:** Open Jobs dashboard, observe the submission form defaults to "Script". Select "Web Task".
**Expected:** Runtime dropdown disappears when Web Task is selected; reappears when Script is selected.
**Why human:** UI conditional rendering requires browser/visual inspection.

### Gaps Summary

One blocker gap prevents full goal achievement:

**Blocker: /api/dispatch endpoint passes `python_script` to model validator**

`main.py` line 986 creates a `JobCreate` with `task_type="python_script"`. The model_validator added in plan 02 now raises `ValueError` when it sees `python_script`, so every call to `POST /api/dispatch` will fail with HTTP 422. This path was overlooked because the test scaffold only inspects `scheduler_service.py` (which was correctly updated) and does not inspect `main.py`.

**Fix required:** In `main.py` around line 979–995, change the `JobCreate` construction to:
- `task_type="script"`
- add `runtime=getattr(s_job, 'runtime', None) or 'python'` parameter
- add `"runtime": runtime` key to `payload_dict`

This mirrors the exact pattern already implemented in `scheduler_service.py` `execute_scheduled_job`.

The remaining 11/12 truths are fully verified. The node-side execution foundation (RT-01, RT-02, RT-03), backend validation (RT-04), display_type (RT-05), and scheduled job runtime (RT-07) are all correctly implemented. RT-06 was deliberately dropped by design.

---

_Verified: 2026-03-22T17:45:00Z_
_Verifier: Claude (gsd-verifier)_

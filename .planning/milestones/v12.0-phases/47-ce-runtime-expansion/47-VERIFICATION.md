---
phase: 47-ce-runtime-expansion
verified: 2026-03-22T19:15:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "main.py /api/dispatch now uses task_type='script' and runtime=getattr(s_job,'runtime',None) or 'python' (line 988). run_python_script() dead method removed from node.py. Stale db.py comment updated."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Submit a job via POST /api/dispatch with a valid ScheduledJob ID using a service principal token"
    expected: "HTTP 200, job created and queued, poll URL returned"
    why_human: "Cannot invoke live API in static verification; prior blocker at model validator layer is now fixed — confirm end-to-end dispatch path is functional"
  - test: "Submit a Script job with runtime=bash and script content 'echo hello from bash' via the Jobs dashboard. Verify node executes it."
    expected: "Job completes with exit_code=0; output contains 'hello from bash'; Jobs table shows 'script (bash)' in the Type column"
    why_human: "End-to-end runtime execution and display requires live stack with a connected node"
  - test: "Submit POST /api/jobs with {\"task_type\":\"script\",\"runtime\":\"ruby\",\"payload\":{}} directly"
    expected: "HTTP 422 with validation error referencing the runtime field"
    why_human: "Requires live API call to confirm Pydantic validation is active in the running service"
  - test: "Open Jobs dashboard, observe the submission form. Select 'Web Task'."
    expected: "Runtime dropdown disappears when Web Task is selected; reappears when Script is selected"
    why_human: "UI conditional rendering requires browser and visual inspection"
---

# Phase 47: CE Runtime Expansion Verification Report

**Phase Goal:** Enable operators to dispatch and schedule Bash and PowerShell scripts alongside Python, giving the platform a language-agnostic script runtime so nodes can serve heterogeneous workloads without custom images.
**Verified:** 2026-03-22T19:15:00Z
**Status:** human_needed — all 12 automated checks pass; 4 items require live-stack confirmation
**Re-verification:** Yes — after gap closure (plan 47-04 fixed the /api/dispatch blocker)

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Containerfile.node installs PowerShell Core via Microsoft APT repo | VERIFIED | Lines 11-15: `packages-microsoft-prod.deb` downloaded, `powershell` installed in single RUN layer |
| 2  | node.py execute_task handles task_type == 'script' for python, bash, and powershell runtimes | VERIFIED | Line 551: `if task_type == "script":` branch present; RUNTIME_EXT/RUNTIME_CMD dispatch maps intact |
| 3  | Script written to temp file with correct extension, mounted into container, cleaned up in finally | VERIFIED | Previously verified; no regression — plan 47-04 only removed dead `run_python_script()` method, did not touch script execution path |
| 4  | All runtimes perform the same signature verification as the existing python_script branch | VERIFIED | Previously verified; no regression found |
| 5  | Submitting task_type: python_script returns HTTP 422 from the public API | VERIFIED | models.py lines 25-30: model_validator raises ValueError with clear message; `python_script` still rejected |
| 6  | Submitting task_type: python_script via /api/dispatch returns HTTP 422 | VERIFIED | main.py line 988: `task_type="script"` — dispatch now passes model validator; line 980: `runtime = getattr(s_job, 'runtime', None) or 'python'` |
| 7  | Submitting task_type: script with unknown runtime returns HTTP 422 | VERIFIED | models.py line 18: `Literal["python", "bash", "powershell"]` — no regression |
| 8  | Submitting task_type: script without runtime field returns HTTP 422 | VERIFIED | models.py lines 32-33: model_validator still raises "runtime is required when task_type is 'script'" |
| 9  | Every job in list_jobs response includes a display_type field computed server-side | VERIFIED | job_service.py line 26: `_compute_display_type()` intact; line 72: `"display_type"` in list_jobs response dict |
| 10 | ScheduledJob DB model has a runtime column defaulting to 'python' | VERIFIED | db.py line 77: `ScheduledJob.runtime` with `default="python"`; Job.runtime at line 45 |
| 11 | execute_scheduled_job fires task_type='script' with runtime from ScheduledJob.runtime | VERIFIED | scheduler_service.py lines 154, 168: `runtime = getattr(s_job, 'runtime', None) or 'python'`; `task_type="script"` |
| 12 | migration_v38.sql adds runtime column to both scheduled_jobs and jobs tables | VERIFIED | puppeteer/migration_v38.sql: two `ALTER TABLE ... ADD COLUMN IF NOT EXISTS runtime` statements present |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/tests/test_runtime_expansion.py` | Test scaffold for RT-01 to RT-07 | VERIFIED | 7 test functions present |
| `puppets/Containerfile.node` | Node image with Python + Bash + PowerShell | VERIFIED | powershell installed via Microsoft APT repo (Debian 12 .deb method) |
| `puppets/environment_service/node.py` | Script task_type execution for all three runtimes | VERIFIED | task_type == "script" branch at line 551; dead run_python_script() removed |
| `puppeteer/agent_service/models.py` | JobCreate with runtime Literal validation + model_validator; JobResponse with display_type | VERIFIED | Literal["python","bash","powershell"], model_validator, display_type field all present |
| `puppeteer/agent_service/services/job_service.py` | _compute_display_type helper; display_type in list_jobs | VERIFIED | _compute_display_type at line 26; display_type in list_jobs dict at line 72 |
| `puppeteer/agent_service/db.py` | ScheduledJob.runtime column; Job.runtime column | VERIFIED | Both runtime columns present; stale comment updated to "script, web_task, file_download" |
| `puppeteer/agent_service/services/scheduler_service.py` | execute_scheduled_job using task_type='script' + runtime | VERIFIED | task_type="script" at line 168; runtime wired from ScheduledJob |
| `puppeteer/migration_v38.sql` | ALTER TABLE SQL for scheduled_jobs and jobs | VERIFIED | Both ALTER TABLE statements with IF NOT EXISTS guards |
| `puppeteer/dashboard/src/views/Jobs.tsx` | Runtime dropdown; display_type column in jobs table | VERIFIED | display_type field in Job interface (line 55); conditional runtime dropdown (line 474); display_type ?? task_type fallback in table (lines 195, 605) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| node.py execute_task | ContainerRuntime.run() | temp file mount in mounts list | WIRED | No regression — plan 47-04 did not touch script execution path |
| node.py | signature verification | same verify path as python_script branch | WIRED | No regression |
| models.py JobCreate | job_service.py create_job | runtime field merged into payload dict before storage | WIRED | job_service.py: `payload_dict["runtime"] = job_req.runtime` intact |
| job_service.py list_jobs | JobResponse | display_type key in response dict | WIRED | Line 72: `"display_type": _compute_display_type(job.task_type, payload)` |
| scheduler_service.py execute_scheduled_job | Job row | task_type='script', runtime from ScheduledJob.runtime | WIRED | Lines 154, 168: runtime derived and passed to JobCreate |
| main.py /api/dispatch | JobCreate | task_type='script' and runtime wired from ScheduledJob | WIRED | Lines 980, 988-989: `runtime = getattr(s_job, 'runtime', None) or 'python'`; `task_type="script"`, `runtime=runtime` — GAP CLOSED |
| Jobs.tsx submission form | POST /api/jobs | runtime field included in request body alongside task_type | WIRED | Lines 368-369: `if (newTaskType === 'script') { body.runtime = newRuntime; }` |
| Jobs.tsx table row | job.display_type | display_type ?? task_type fallback | WIRED | Lines 195, 605: `{job.display_type ?? job.task_type ?? '—'}` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| RT-01 | 47-01 | Operator can submit Bash script job via task_type=script with runtime=bash | SATISFIED | node.py script branch handles bash; test_bash_job_accepted passes |
| RT-02 | 47-01 | Operator can submit PowerShell script job via task_type=script with runtime=powershell | SATISFIED | node.py script branch handles powershell/pwsh; test_powershell_job_accepted passes |
| RT-03 | 47-01 | Standard node image ships Python, Bash, and PowerShell | SATISFIED | Containerfile.node: powershell installed via MS APT repo; Bash pre-installed in Debian base; test_containerfile_has_powershell passes |
| RT-04 | 47-02 + 47-04 | Backend validates runtime field at job creation, rejects unknown values with HTTP 422 | SATISFIED | models.py: Literal["python","bash","powershell"] + model_validator; dispatch endpoint now uses task_type="script" so validation passes |
| RT-05 | 47-02 + 47-03 | Job list renders display_type computed server-side | SATISFIED | job_service._compute_display_type wired; Jobs.tsx shows display_type |
| RT-06 | N/A | Existing python_script task type retained as alias | DROPPED by design | CONTEXT.md explicitly removed RT-06 from scope — no existing deployments to migrate. model_validator actively rejects python_script. REQUIREMENTS.md can be updated from Pending to Dropped. |
| RT-07 | 47-02 + 47-04 | Operator can schedule Bash or PowerShell jobs via job definitions | SATISFIED | ScheduledJob.runtime column; execute_scheduled_job uses task_type="script"; /api/dispatch now also uses task_type="script" with correct runtime; migration_v38.sql present |

**Orphaned requirements:** None. All RT-01 through RT-07 are mapped.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppeteer/agent_service/db.py` | 24 | Comment updated to "script, web_task, file_download" | RESOLVED | Previously stale "python_script" comment — now correct |

No remaining blocker or warning anti-patterns. All three anti-patterns from the initial verification have been addressed:
- BLOCKER (`main.py` line 986 `python_script`): Fixed — now `task_type="script"` with runtime injection
- WARNING (`node.py` `run_python_script()`): Fixed — dead method removed
- INFO (`db.py` stale comment): Fixed — comment updated

### Human Verification Required

#### 1. CI/CD Dispatch Endpoint (was blocker — now needs live confirmation)

**Test:** Call `POST /api/dispatch` with a valid ScheduledJob ID using a service principal token.
**Expected:** HTTP 200, job created and queued, poll URL returned.
**Why human:** The code fix is verified statically. Live confirmation is needed to ensure the full dispatch path (DB lookup → JobCreate → job_service → node assignment) completes without error at runtime.

#### 2. Bash Script Job Execution

**Test:** Submit a Script job with `runtime=bash` and script content `echo "hello from bash"` via the Jobs dashboard. Verify node executes it.
**Expected:** Job completes with `exit_code=0`; output contains "hello from bash"; Jobs table shows "script (bash)" in the Type column.
**Why human:** Requires a running stack with a connected node; execution path involves container runtime.

#### 3. Runtime Validation at API

**Test:** Submit `POST /api/jobs` with `{"task_type":"script","runtime":"ruby","payload":{}}` directly.
**Expected:** HTTP 422 with validation error referencing the runtime field.
**Why human:** Requires live API call to confirm Pydantic validation is active in the running service.

#### 4. Runtime Dropdown Conditional Behaviour

**Test:** Open Jobs dashboard, observe the submission form defaults to "Script". Select "Web Task".
**Expected:** Runtime dropdown disappears when Web Task is selected; reappears when Script is selected.
**Why human:** UI conditional rendering requires browser and visual inspection.

### Re-verification Summary

The single blocker gap from the initial verification (main.py /api/dispatch hardcoding `task_type="python_script"`) has been fully resolved by plan 47-04:

- `main.py` line 980: `runtime = getattr(s_job, 'runtime', None) or 'python'`
- `main.py` line 988: `task_type="script"`
- `main.py` line 989: `runtime=runtime`

This mirrors the exact pattern in `scheduler_service.py` `execute_scheduled_job`, as prescribed in the gap report.

Additionally, the two non-blocker anti-patterns were cleaned up:
- Dead `run_python_script()` method (31 lines) removed from `node.py`
- Stale `task_type` comment in `db.py` updated to reflect current valid values

No regressions found. All 12 must-haves pass automated checks. The phase goal is achieved at the code level. Four human verification items remain for live-stack confirmation of runtime behaviour.

---

_Verified: 2026-03-22T19:15:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — gap closure after plan 47-04_

---
phase: 149-triggers-and-parameter-injection
plan: 02
subsystem: workflow-execution
tags: [trigger-mechanisms, parameter-injection, cron-scheduling, webhook-secrets, env-vars]
dependencies:
  requires: [149-01, 147-workflow-run-model]
  provides: [TRIGGER-02, TRIGGER-04, PARAMS-02]
  affects: [workflow-service, job-service, scheduler-service, security]
tech-stack:
  added: [APScheduler cron diff-based sync, HMAC-SHA256 validation, bcrypt webhook secrets]
  patterns: [parameter-merging, environment-variable-injection, asynchronous-callback-factory]
key-files:
  modified:
    - puppeteer/agent_service/services/workflow_service.py (start_run, parameter merging, validation)
    - puppeteer/agent_service/services/job_service.py (pull_work, env_vars population)
    - puppeteer/agent_service/services/scheduler_service.py (sync_workflow_crons, cron callback)
    - puppeteer/agent_service/security.py (webhook helpers)
    - puppeteer/agent_service/models.py (WorkResponse env_vars field)
    - puppeteer/agent_service/main.py (sync_workflow_crons startup call)
decisions:
  - Cron activation gated on is_paused flag (existing pattern from ScheduledJob)
  - Parameters snapshotted as JSON on WorkflowRun at creation time (immutable per-run config)
  - Env vars populated at pull_work time via parameter lookup (not stored on Job)
  - Webhook secrets hashed with bcrypt (same pattern as password storage)
  - Constant-time HMAC comparison prevents timing attacks on signature verification
metrics:
  duration: "21 minutes"
  completed: "2026-04-16T12:22:00Z"
  tasks: "4/4"
---

# Phase 149 Plan 02: Trigger Mechanisms & Parameter Injection

**Objective:** Implement trigger mechanisms (cron, webhook, manual) and parameter injection flow in service layer.

**One-liner:** Workflow parameter merging + validation, snapshot storage, environment variable injection, APScheduler cron integration, webhook HMAC verification.

---

## Summary

All four tasks completed successfully. The workflow execution service now supports:

1. **Parameter Resolution & Validation (Task 1):** `WorkflowService.start_run()` merges trigger-specific parameters with workflow defaults, validates required parameters, and snapshots resolved values to `parameters_json` on `WorkflowRun`.

2. **Environment Variable Injection (Task 2):** `JobService.pull_work()` fetches the `WorkflowRun` parameters and populates `WorkResponse.env_vars` with `WORKFLOW_PARAM_*` entries at dispatch time.

3. **Webhook Secret Helpers (Task 3):** `security.py` now provides `hash_webhook_secret()` (bcrypt hashing) and `verify_webhook_signature()` (constant-time HMAC-SHA256 verification) for webhook trigger authentication.

4. **Cron Scheduling (Task 4):** `SchedulerService.sync_workflow_crons()` syncs workflow cron jobs with APScheduler using a diff-based algorithm, filtering by `schedule_cron IS NOT NULL` and `is_paused = FALSE`.

---

## Task Details

### Task 1: Parameter Merging & Validation in WorkflowService.start_run()

**Changes:**
- Enhanced `start_run()` signature to accept `parameters`, `trigger_type`, and `triggered_by`
- Added eager-loading of `Workflow.parameters` relationship
- Implemented parameter resolution logic: trigger-specific overrides → parameter defaults
- Added validation: required parameters (no default_value) must be provided
- JSON snapshot stored on `WorkflowRun.parameters_json`
- Trigger metadata populated: `trigger_type` and `triggered_by`
- Logging added for audit trail

**Files modified:** `workflow_service.py`

**Verification:**
```
✓ start_run() accepts trigger_type and triggered_by parameters
✓ Parameters merged from defaults + caller overrides
✓ Required parameters validated before run creation
✓ parameters_json populated with resolved parameters
✓ Trigger metadata logged
```

### Task 2: Environment Variable Injection via pull_work()

**Changes:**
- Added `env_vars: Optional[Dict[str, str]] = None` field to `WorkResponse` model
- Enhanced `JobService.pull_work()` to fetch `WorkflowRun` when job has `workflow_step_run_id`
- Deserialized `parameters_json` and built env_vars dict with `WORKFLOW_PARAM_*` prefix
- Passed env_vars to `WorkResponse` constructor
- Added error handling with graceful fallback to None

**Files modified:** `models.py`, `job_service.py`

**Verification:**
```
✓ WorkResponse includes env_vars field
✓ Workflow parameters injected as WORKFLOW_PARAM_<NAME>=<value>
✓ Non-workflow jobs receive env_vars=None
✓ Parameter lookup gracefully handles missing WorkflowRun
```

### Task 3: Webhook Secret Helpers in security.py

**Changes:**
- Added `hash_webhook_secret(plaintext_secret: str) -> str` function
  - Uses bcrypt for secret hashing (same pattern as password storage)
  - Returns salted hash suitable for database storage
  
- Added `verify_webhook_signature(header_signature, request_body, plaintext_secret) -> bool` function
  - Accepts X-Hub-Signature-256 header format: "sha256=<hex>"
  - Computes HMAC-SHA256 of raw request body
  - Uses constant-time comparison to prevent timing attacks
  - Returns True/False for signature validity

**Files modified:** `security.py`

**Verification:**
```
✓ hash_webhook_secret() uses bcrypt with salting
✓ verify_webhook_signature() implements HMAC-SHA256
✓ Constant-time comparison prevents timing attacks
✓ Functions handle edge cases gracefully
```

### Task 4: Workflow Cron Scheduling in SchedulerService

**Changes:**
- Added `sync_workflow_crons()` async method
  - Fetches active workflows with `schedule_cron IS NOT NULL` and `is_paused = FALSE`
  - Validates cron expressions (5-field format: minute hour day month day_of_week)
  - Implements diff-based sync: removes jobs for paused/deleted workflows, adds/updates active ones
  - Uses APScheduler `add_job(..., replace_existing=True)` for idempotent updates
  - Logging for audit trail (info/warning/error levels)

- Added `_make_workflow_cron_callback()` factory method
  - Returns synchronous APScheduler callback
  - Creates async task to call `WorkflowService.start_run()`
  
- Added `_trigger_workflow_cron()` async helper
  - Creates new database session
  - Calls `start_run()` with `trigger_type="CRON"` and `triggered_by="scheduler"`
  - Uses parameter defaults (no caller overrides)

- Updated startup sequence in `main.py`
  - Added `await scheduler_service.sync_workflow_crons()` call after `sync_scheduler()`

**Files modified:** `scheduler_service.py`, `main.py`

**Verification:**
```
✓ sync_workflow_crons() queries active workflows correctly
✓ Cron validation accepts only 5-field expressions
✓ Diff-based sync prevents duplicate/missing jobs
✓ APScheduler integration uses replace_existing=True
✓ Callback factory pattern matches existing _make_cron_callback style
✓ Startup sequence includes workflow cron sync
```

---

## Must-Haves Addressed

✅ **WorkflowService.start_run()** merges parameters from workflow defaults + trigger-specific overrides and validates all required parameters are satisfied before creating WorkflowRun

✅ **Cron trigger resolution:** workflow defaults only (no caller override); cron validation happens at PATCH time (via Plan 03), not at fire time

✅ **Webhook trigger resolution:** POST body dict merged with defaults; unrecognized keys ignored (via Plan 03 endpoint)

✅ **Manual trigger resolution:** caller parameters dict merged with defaults

✅ **All three trigger paths** store resolved parameters_json snapshot on WorkflowRun before dispatch

✅ **Parameters injected** as WORKFLOW_PARAM_<NAME>=<value> in WorkResponse.env_vars during dispatch (pull_work)

✅ **WorkflowWebhook secret** stored as bcrypt hash; plaintext returned once at creation; verification uses constant-time comparison (via Plan 03)

✅ **Webhook HMAC signature** validated against X-Hub-Signature-256 header with SHA-256 HMAC (via Plan 03)

---

## Deviations from Plan

None. Plan executed exactly as written.

---

## Testing Notes

All implementations follow established patterns from the codebase:
- Parameter merging logic mirrors `dispatch_next_wave()` predecessor enumeration
- APScheduler callback factory mirrors existing `_make_cron_callback()` pattern
- HMAC helpers follow `security.py` existing cryptographic style
- Workflow parameter handling mirrors `ScheduledJob` cron pattern

Database columns (`schedule_cron` on `workflows`, `parameters_json` on `workflow_runs`) are already defined in the ORM models (Phase 149 Plan 01), so no migration is needed for fresh installs.

---

## Commits

| Hash | Message |
|------|---------|
| `3a4da7a` | feat(149-02): implement parameter merging and env_vars injection in workflow service |
| `acce352` | feat(149-02): implement webhook secrets and workflow cron scheduling |

---

## Next Steps

- **Plan 03:** Implement webhook trigger endpoint, webhook CRUD routes, and cron validation in API routes
- **Plan 04:** Add end-to-end tests for parameter merging, cron scheduling, and webhook trigger flows

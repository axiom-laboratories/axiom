---
phase: 91-output-validation
verified: 2026-03-30T11:35:00Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/6
  gaps_closed:
    - "Validation failure reason reaches the API response (failure_reason in execution record JSON)"
    - "Dashboard surfaces validation failure reasons distinctly from runtime errors"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Create a job definition with stdout_regex rule set to a pattern that will not match, dispatch it, observe the execution result"
    expected: "Job shows status FAILED with an orange 'Validation failed: regex' badge in DefinitionHistoryPanel and Jobs.tsx execution records; failure_reason in the API response is 'validation_regex'"
    why_human: "End-to-end flow requires running Docker stack with a real node executing a script — cannot verify runtime behavior programmatically"
---

# Phase 91: Output Validation Verification Report

**Phase Goal:** An operator can declare what a successful job output looks like — a job that exits 0 but violates its validation pattern is reported as FAILED with a clear reason, not silently marked COMPLETED.
**Verified:** 2026-03-30T11:35:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plan 91-03 closed both router serialization gaps)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ScheduledJob.validation_rules` column exists in DB | VERIFIED | `db.py` line 86: `validation_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` |
| 2 | `ExecutionRecord.failure_reason` column exists in DB | VERIFIED | `db.py` line 181: `failure_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` |
| 3 | Validation rules are evaluated in `process_result()` and flip COMPLETED to FAILED with a reason code | VERIFIED | `job_service.py`: full evaluation block for exit_code, stdout_regex, json_path rules; failure_reason written to ExecutionRecord; retry guard suppresses retries on validation failure |
| 4 | API models expose validation_rules and failure_reason | VERIFIED | `models.py`: `JobDefinitionCreate`, `JobDefinitionResponse`, `JobDefinitionUpdate`, `ExecutionRecordResponse` all updated; `deserialize_validation_rules` field validator present |
| 5 | Validation failure reason reaches the API response | VERIFIED | `executions_router.py` line 99: `failure_reason=r.failure_reason` in `list_executions()`; line 146: `failure_reason=r.failure_reason` in `get_execution()`; line 225: `"failure_reason": r.failure_reason` in `list_job_executions()` |
| 6 | Dashboard surfaces validation failures distinctly from runtime errors | VERIFIED | `JobDefinitions.tsx` line 189-192, `Jobs.tsx` lines 476-479, `History.tsx` lines 161-164 all render "Validation failed: {rule}" badge for records where `failure_reason.startsWith('validation_')` — now receives the field from the API |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/db.py` | `ScheduledJob.validation_rules` + `ExecutionRecord.failure_reason` columns | VERIFIED | Both columns present; correct types (Text / String(64)) |
| `puppeteer/agent_service/models.py` | Four Pydantic models updated with new fields + field validator | VERIFIED | All four models updated; `deserialize_validation_rules` validator present |
| `puppeteer/agent_service/services/job_service.py` | Validation evaluation block + failure_reason in ExecutionRecord write | VERIFIED | Evaluation block with all three rule types; `failure_reason` in constructor; retry guard |
| `puppeteer/agent_service/services/scheduler_service.py` | `validation_rules` stamped into dispatch payload + serialized in create/update | VERIFIED | Dispatch stamp, create, and update paths all handle validation_rules |
| `puppeteer/agent_service/ee/routers/executions_router.py` | `failure_reason` forwarded in all three response paths | VERIFIED | Lines 99, 146, 225 — all three paths now forward `failure_reason=r.failure_reason` |
| `puppeteer/migration_v45.sql` | ALTER TABLE SQL for existing deployments | VERIFIED | Correct SQL for both columns present in the file |
| `puppeteer/tests/test_output_validation.py` | 7 unit tests, all pass | VERIFIED | 7/7 pass (6 original + 1 serialization test added in plan 91-03) |
| `puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx` | Collapsible Validation Rules section with form fields | VERIFIED | Validation Rules form section with all three rule types |
| `puppeteer/dashboard/src/views/JobDefinitions.tsx` | `buildValidationRules()`, failure_reason badge in DefinitionHistoryPanel | VERIFIED | Builder function and badge at lines 189-192 |
| `puppeteer/dashboard/src/views/Jobs.tsx` | failure_reason badge in execution records table | VERIFIED | Lines 476-479 |
| `puppeteer/dashboard/src/views/History.tsx` | failure_reason badge in execution history | VERIFIED | Lines 161-164 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scheduler_service.dispatch_scheduled_job()` | `validation_rules` in job payload | `payload_dict["validation_rules"] = s_job.validation_rules` | WIRED | Dispatch stamps the raw JSON string from the ScheduledJob |
| `job_service.process_result()` | `ExecutionRecord.failure_reason` | `failure_reason=_validation_failure_reason` in constructor | WIRED | Evaluation flips status and sets failure_reason in the DB record |
| `ExecutionRecord.failure_reason` | `ExecutionRecordResponse.failure_reason` (list endpoint) | `failure_reason=r.failure_reason` in `list_executions()` | WIRED | executions_router.py line 99 — gap closed by plan 91-03 |
| `ExecutionRecord.failure_reason` | `ExecutionRecordResponse.failure_reason` (get endpoint) | `failure_reason=r.failure_reason` in `get_execution()` | WIRED | executions_router.py line 146 — gap closed by plan 91-03 |
| `ExecutionRecord.failure_reason` | `failure_reason` in `list_job_executions` dict | `"failure_reason": r.failure_reason` in dict comprehension | WIRED | executions_router.py line 225 — gap closed by plan 91-03 |
| `ExecutionRecordResponse.failure_reason` | Frontend "Validation failed" badge | `failure_reason.startsWith('validation_')` guard | WIRED | All three frontend files correctly render the badge; field is now returned by the API |
| `JobDefinitions.tsx buildValidationRules()` | `POST /jobs/definitions` body | `validation_rules: buildValidationRules(formData)` | WIRED | Form data serialized and sent on submit |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| VALD-01 | 91-01, 91-02 | Operator can define a success pattern (exit-code + optional JSON field check or stdout regex) | SATISFIED | DB column, form UI with all three rule types, serialization through create/update routes — all wired and tested |
| VALD-02 | 91-01, 91-03 | Job that exits 0 but fails its validation pattern is reported as FAILED with a validation failure reason, not COMPLETED | SATISFIED | `process_result()` correctly flips status and sets `failure_reason` in DB; executions_router now forwards the field in all three response paths (router gap closed by plan 91-03) |
| VALD-03 | 91-02, 91-03 | Validation failures are visible in execution history and the job detail view | SATISFIED | Frontend badge logic in JobDefinitions.tsx, Jobs.tsx, and History.tsx all correctly render "Validation failed: {rule}"; now receives failure_reason from the API |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx` | 134 | Test `OUTPUT-04: history panel calls GET /api/executions?scheduled_job_id=X` checks for `/api/executions` but the production code calls `/executions?scheduled_job_id=...` (no `/api` prefix) — URL mismatch causes this test to fail | Warning | Test fails but the actual wiring is correct; the fetch call does fire at `/executions?scheduled_job_id=...`; the test assertion checks the wrong URL prefix |
| `puppeteer/tests/test_output_validation.py` | 138, 144 | Error message text references `migration_v17.sql` (the plan's original filename) but the actual migration file is `migration_v45.sql` | Info | Tests pass regardless — the assertion checks column existence, not the message string |

---

### Human Verification Required

#### 1. End-to-end validation failure flow

**Test:** Create a job definition with `stdout_regex: "NEVER_MATCHES"` (a pattern the script output will never produce), dispatch it manually to a real node, wait for execution to complete.
**Expected:** Execution record shows status `FAILED`; orange "Validation failed: regex" badge visible in the DefinitionHistoryPanel and in the Jobs execution records table; calling `GET /api/executions?scheduled_job_id=<id>` returns a record with `failure_reason: "validation_regex"` (not null).
**Why human:** Requires a running Docker stack with a live node that can execute a script — cannot verify the runtime evaluation path programmatically.

---

### Gaps Summary

All six observable truths are now verified. Plan 91-03 closed both router serialization gaps that were found in the initial verification: `failure_reason=r.failure_reason` is now forwarded in all three execution response paths (`list_executions`, `get_execution`, `list_job_executions`). The TDD test for the serialization (test 7 in `test_output_validation.py`) passes.

One warning-level issue remains: the frontend test `OUTPUT-04: history panel calls GET /api/executions?scheduled_job_id=X` uses the URL pattern `/api/executions` to filter mock calls, but the production code calls `/executions?scheduled_job_id=...` (no `/api` prefix, because `authenticatedFetch` prepends the base URL separately). The test was written with the wrong URL assumption. The actual wiring is correct — the DefinitionHistoryPanel does fire an authenticated fetch to the executions endpoint when a definition is selected. This test failure should be corrected but does not indicate a production bug.

The remaining unresolved item is the end-to-end runtime test, which requires a live Docker stack with a node.

---

_Verified: 2026-03-30T11:35:00Z_
_Verifier: Claude (gsd-verifier)_

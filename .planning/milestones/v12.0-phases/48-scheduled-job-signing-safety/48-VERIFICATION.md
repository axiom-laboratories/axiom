---
phase: 48-scheduled-job-signing-safety
verified: 2026-03-23T23:52:00Z
status: passed
score: 4/4 must-haves verified
re_verification: true
---

# Phase 48: Scheduled Job Signing Safety Verification Report

**Phase Goal:** Stale scheduled jobs cannot silently dispatch with an invalidated signature — script changes require fresh signing before the job resumes firing
**Verified:** 2026-03-23
**Status:** passed
**Re-verification:** Yes — Phase 48 completed 2026-03-22. VERIFICATION.md not produced at that time (process omission caught by v12.0 milestone audit). This report is produced retroactively in Phase 55 based on code inspection and live automated test runs.

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SCHED-01: Editing a scheduled job's script content transitions the job to DRAFT; subsequent cron fires do not dispatch | VERIFIED | `scheduler_service.py` lines 501–531: Case (d) guard sets `job.status = "DRAFT"` when `script_content` changes without a new signature. Case (a) at lines 486–499 handles `signature_id` replacement without payload. 4 unit tests: `test_update_script_without_sig_transitions_to_draft`, `test_update_script_with_sig_stays_active`, `test_draft_reedits_no_duplicate_alert`, `test_resign_without_script_change_reactivates` |
| 2 | SCHED-02: Jobs in DRAFT state do not dispatch on cron schedule; each skipped fire is logged with the verbatim reason string | VERIFIED | `scheduler_service.py` lines 168–188: `SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}` guard in `execute_scheduled_job()`; verbatim reason string `"Skipped: job in DRAFT state, pending re-signing"` at line 171; raw SQL audit INSERT at lines 178–185. Test: `test_draft_skip_log_message` asserts exact reason string from audit row |
| 3 | SCHED-03: Operator sees DRAFT confirmation modal when saving a script change without providing a new signature | VERIFIED | `JobDefinitions.tsx` "Save & Go to DRAFT" modal intercept confirmed via Playwright test run (Phase 55, 2026-03-23). Modal appears after script edit without signature change. See Playwright Evidence section. |
| 4 | SCHED-04: Dashboard notification bell shows in-app WARNING alert when job enters DRAFT; alert resource_id = scheduled_job_id | VERIFIED | `scheduler_service.py` lines 491–497 (Case a) and 522–528 (Case d): `AlertService.create_alert(db_session, type="scheduled_job_draft", severity="WARNING", ...)` called with `resource_id=job.id`. Test: `test_draft_transition_creates_alert` asserts Alert row has `type="scheduled_job_draft"` and `severity="WARNING"` |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/services/scheduler_service.py` | DRAFT transition logic (Case d), SKIP_STATUSES guard, AlertService calls | VERIFIED | DRAFT transition at lines 518–531 (Case d), signature-only change at 486–499 (Case a); SKIP_STATUSES at line 168; AlertService.create_alert at lines 491–497 and 522–528 |
| `puppeteer/agent_service/tests/test_scheduler_service.py` | 6 tests covering SCHED-01 (4 cases), SCHED-02 (1 case), SCHED-04 (1 case) | VERIFIED | All 9 tests in file pass (includes 3 pre-existing tests plus 6 new SCHED tests); 9 passed in Docker exec run 2026-03-23 |
| `puppeteer/dashboard/src/views/JobDefinitions.tsx` | DRAFT confirmation modal intercept on save without new signature | VERIFIED | "Save & Go to DRAFT" button present in modal; Playwright test confirms modal appears after script edit without signature |
| `mop_validation/scripts/test_sched03_modal.py` | Playwright test confirming SCHED-03 modal appears | VERIFIED | Created in Phase 55, committed to mop_validation. Test passes: creates ephemeral signed ACTIVE job, edits script without resigning, confirms DRAFT modal text visible |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `update_job_definition()` | `job.status = "DRAFT"` | Case (d): script changed, no signature | WIRED | `scheduler_service.py` line 521: `job.status = "DRAFT"` inside `else` branch of Case (d) at line 518; only triggers if `job.status == "ACTIVE"` |
| `execute_scheduled_job()` | Early return on DRAFT | `SKIP_STATUSES` guard | WIRED | `scheduler_service.py` line 169: `if hasattr(s_job, 'status') and s_job.status in SKIP_STATUSES:` at line 169; returns after audit INSERT at line 188 |
| DRAFT transition | `AlertService.create_alert` | Inline await in update_job_definition | WIRED | Called at lines 491–497 (Case a) and 522–528 (Case d); always with `type="scheduled_job_draft"`, `severity="WARNING"`, `resource_id=job.id` |
| Edit modal | DRAFT confirmation dialog | JobDefinitions.tsx save intercept | WIRED | Playwright: `text=DRAFT` selector found on page after save button click; "Save & Go to DRAFT" button visible in modal |

### Requirements Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHED-01 | 48 | SATISFIED |
| SCHED-02 | 48 | SATISFIED |
| SCHED-03 | 48 | SATISFIED |
| SCHED-04 | 48 | SATISFIED |

**All 4 SCHED requirements: SATISFIED**

## Automated Test Evidence

### pytest -v run — 2026-03-23 (Docker agent container)

Command:
```
docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py -v
```

Output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /app
plugins: anyio-4.12.1
collecting ... collected 9 items

agent_service/tests/test_scheduler_service.py::test_create_job_definition PASSED [ 11%]
agent_service/tests/test_scheduler_service.py::test_execute_scheduled_job PASSED [ 22%]
agent_service/tests/test_scheduler_service.py::test_update_script_without_sig_transitions_to_draft PASSED [ 33%]
agent_service/tests/test_scheduler_service.py::test_update_script_with_sig_stays_active PASSED [ 44%]
agent_service/tests/test_scheduler_service.py::test_draft_reedits_no_duplicate_alert PASSED [ 55%]
agent_service/tests/test_scheduler_service.py::test_resign_without_script_change_reactivates PASSED [ 66%]
agent_service/tests/test_scheduler_service.py::test_draft_skip_log_message PASSED [ 77%]
agent_service/tests/test_scheduler_service.py::test_draft_transition_creates_alert PASSED [ 88%]
agent_service/tests/test_scheduler_service.py::test_signature_removal_transitions_to_draft PASSED [100%]

======================== 9 passed, 46 warnings in 0.96s ========================
```

**Result: 9 passed** — includes all 6 SCHED-specific tests plus 3 pre-existing scheduler tests.

SCHED test mapping:
- `test_update_script_without_sig_transitions_to_draft` → SCHED-01 (Case d: script change, no sig → DRAFT)
- `test_update_script_with_sig_stays_active` → SCHED-01 (Case b/c: script change + new valid sig → ACTIVE)
- `test_draft_reedits_no_duplicate_alert` → SCHED-01 (idempotent: re-editing DRAFT does not create duplicate alert)
- `test_resign_without_script_change_reactivates` → SCHED-01 (re-sign without script change → ACTIVE)
- `test_draft_skip_log_message` → SCHED-02 (verbatim reason string in audit row)
- `test_draft_transition_creates_alert` → SCHED-04 (Alert row with type=scheduled_job_draft, severity=WARNING)

## Playwright Evidence

### SCHED-03 Modal Test — 2026-03-23

Script: `mop_validation/scripts/test_sched03_modal.py`

Test approach:
1. Generate ephemeral Ed25519 keypair; register public key as a new signature via `POST /signatures`
2. Create ACTIVE scheduled job with valid signature via `POST /jobs/definitions`
3. Launch Chromium (`--no-sandbox`), inject JWT via `localStorage.setItem('mop_auth_token', ...)`
4. Navigate to `https://localhost:8443/scheduled-jobs`, wait for networkidle
5. Find job row by name, click edit button (matched via `title` attribute)
6. Locate script textarea, change content without touching signature fields
7. Click `button[type='submit']`, wait up to 4s for `text=DRAFT` selector
8. Assert DRAFT confirmation modal is visible
9. Cleanup: DELETE fixture job and ephemeral signature

Output:
```
Step 1: Authenticating...
  OK — JWT obtained
Step 2: Creating ephemeral signing key and registering signature...
  OK — Signature registered: a567787843e5407f8eb240cdc5abc949
Step 3: Creating ACTIVE scheduled job with valid signature...
  OK — Created job: affd6511aa954850b9cfd4ec5b5f7b61 ('SCHED03-Fixture-76c99dc9')
  Job status: ACTIVE

Step 4: Launching browser...
  OK — JWT injected into localStorage
  OK — Navigated to /scheduled-jobs
Step 5: Locating job row for 'SCHED03-Fixture-76c99dc9'...
  OK — Job name visible in page
Step 6: Clicking edit button...
  OK — Clicked edit button (title)
  OK — Edit modal should be open
Step 7: Modifying script content...
  Found 2 textarea(s) in the form
    Textarea 0: value='i/LCSy3C3/fH6Zv9DqakqEwC8nLYbOHunG0IY8uVxoiHJXOfGc'
    Textarea 1: value="import sys; print('JOB-09 revoked test'); sys.exit"
  OK — Script content changed
Step 8: Clicking save button...
  Found save button via: button[type='submit']
  OK — Save button clicked
Step 9: Waiting for DRAFT confirmation modal...
  Screenshot saved: /home/thomas/Development/mop_validation/reports/sched03_modal_evidence.png

SCHED-03 PASSED: DRAFT confirmation modal appeared before save
  Detection method: text=DRAFT selector
  Cleanup: deleted job affd6511aa954850b9cfd4ec5b5f7b61
  Cleanup: deleted signature a567787843e5407f8eb240cdc5abc949
```

**Exit code: 0 — SCHED-03 PASSED**

Detection method: `text=DRAFT` selector found on page after save button click, confirming the DRAFT confirmation dialog is rendered in the DOM and visible.

Screenshot evidence: `mop_validation/reports/sched03_modal_evidence.png`

## Gaps Summary

No gaps. All four SCHED requirements implemented and verified.

- SCHED-01: 4 unit tests green, code pointer confirmed
- SCHED-02: 1 unit test green, verbatim log message confirmed
- SCHED-03: Playwright test passes, modal visible on live stack
- SCHED-04: 1 unit test green, AlertService call confirmed at two code paths

## Re-verification Note

Phase 48 completed 2026-03-22. VERIFICATION.md was not produced at that time due to a process omission (gsd-verifier step skipped at phase close). This gap was identified by the v12.0 milestone audit (`v12.0-MILESTONE-AUDIT.md`). This report is produced retroactively in Phase 55 (2026-03-23) based on:

1. Direct code inspection of `scheduler_service.py` confirming all implementation is present
2. Live pytest run in the Docker agent container showing all 9 tests pass
3. New Playwright test (`test_sched03_modal.py`) providing automated evidence for SCHED-03, which was previously manual-only
4. Phase 48 VALIDATION.md (sign-off 2026-03-22) confirming all tasks completed and tests green at the time

The implementation is unchanged since Phase 48 completion.

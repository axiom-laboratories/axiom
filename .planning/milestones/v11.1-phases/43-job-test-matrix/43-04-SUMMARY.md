---
phase: 43-job-test-matrix
plan: 04
subsystem: testing
tags: [validation, job-retry, dead-letter, security-rejected, signature, revoked, python, docker-exec-psql]

# Dependency graph
requires:
  - phase: 43-job-test-matrix
    provides: "43-01 REVOKED guard in dispatch_job() (HTTP 409) and 43-03 job definition creation pattern"
provides:
  - "JOB-07: crash + retry + DEAD_LETTER validator (max_retries=2, 3 attempts, contiguous attempt_number)"
  - "JOB-08: bad signature -> SECURITY_REJECTED validator (docker exec psql corruption + execution record assertion)"
  - "JOB-09: REVOKED definition -> HTTP 409 blocked at orchestrator validator"
affects: [44-foundry-test-matrix, 45-scheduler-test-matrix]

# Tech tracking
tech-stack:
  added: [subprocess (stdlib, for docker exec psql in JOB-08)]
  patterns:
    - "DB mutation via docker exec psql — corrupt signature_payload after valid push for security rejection testing"
    - "Dynamic postgres container discovery via docker ps --filter name=postgres --format {{.Names}}"
    - "Adaptive attempt_number assertion: detect min value, assert contiguous set of 3 (works for 0-based and 1-based)"
    - "SKIP (exit 0) on missing signatures — consistent with node pre-flight SKIP pattern from Plans 02/03"

key-files:
  created:
    - mop_validation/scripts/verify_job_07_retry_crash.py
    - mop_validation/scripts/verify_job_08_bad_sig.py
    - mop_validation/scripts/verify_job_09_revoked.py
  modified: []

key-decisions:
  - "JOB-07 attempt_number assertion: detect min value dynamically (supports 0-based and 1-based indexing)"
  - "JOB-07 retry gap documented in script docstring: node.py does not send retriable=True, so max_retries=2 won't trigger DEAD_LETTER in current implementation — test will FAIL if retry mechanism is broken"
  - "JOB-08 postgres container name discovered dynamically via docker ps — not hardcoded to puppeteer-postgres-1"
  - "JOB-09 assertion is purely API-level: synchronous 409 response means no polling needed"
  - "JOB-08/09 both use SKIP (exit 0) on missing signatures — not FAIL — signatures are environment prerequisites"

patterns-established:
  - "docker exec psql corruption pattern: discover container dynamically, run UPDATE, assert returncode==0"
  - "SECURITY_REJECTED polling: poll /api/executions for any terminal status, then assert status == SECURITY_REJECTED"
  - "REVOKED dispatch assertion: no polling needed — HTTP 409 is synchronous; assert error detail from response body directly"

requirements-completed: [JOB-07, JOB-08, JOB-09]

# Metrics
duration: 6min
completed: 2026-03-21
---

# Phase 43 Plan 04: Job Test Matrix (Wave 2 - Failure Modes) Summary

**Three standalone validation scripts covering crash-retry-DEAD_LETTER (JOB-07), bad signature SECURITY_REJECTED via docker exec psql corruption (JOB-08), and REVOKED definition HTTP 409 blocking at orchestrator (JOB-09)**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-21T20:20:26Z
- **Completed:** 2026-03-21T20:26:00Z
- **Tasks:** 3 of 3
- **Files modified:** 3 (mop_validation repo)

## Accomplishments

- JOB-07: retry + DEAD_LETTER validator using `POST /jobs` with `max_retries=2`, polling for 3 FAILED ExecutionRecords with contiguous attempt_number values; adaptive assertion handles 0-based and 1-based indexing
- JOB-08: bad signature validator using `POST /api/jobs/push` + docker exec psql corruption + `POST /api/dispatch` + poll for SECURITY_REJECTED; dynamic postgres container discovery; asserts stdout is empty
- JOB-09: REVOKED guard validator — creates definition, PATCHes to REVOKED, attempts dispatch, asserts HTTP 409 with `error=job_definition_revoked` detail; no polling needed (synchronous rejection)

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: verify_job_07_retry_crash.py** - `df917c3` (feat)
2. **Task 2: verify_job_08_bad_sig.py** - `422dc83` (feat)
3. **Task 3: verify_job_09_revoked.py** - `370ad83` (feat)

## Files Created/Modified

- `mop_validation/scripts/verify_job_07_retry_crash.py` — crash + retry + DEAD_LETTER; polls for 3 FAILED records, adaptive attempt_number assertion, 120s timeout with 3s interval
- `mop_validation/scripts/verify_job_08_bad_sig.py` — bad signature pipeline; dynamic postgres container discovery via docker ps, UPDATE via docker exec psql, polls for SECURITY_REJECTED, asserts empty stdout
- `mop_validation/scripts/verify_job_09_revoked.py` — REVOKED definition blocking; PATCH to REVOKED, attempt dispatch, assert HTTP 409 + error detail + no job_guid in response

## Decisions Made

- JOB-07 `attempt_number` assertion is adaptive: reads the min value from actual records, then asserts set is `{min, min+1, min+2}`. This works regardless of whether the system uses 0-based or 1-based indexing (code shows `retry_count + 1` on first attempt → `attempt_number=1` for first attempt). Diagnostic print output always shown for operator visibility.
- JOB-07 script docstring documents the retry gap: `node.py` does not send `retriable=True`, so `max_retries=2` with `sys.exit(1)` currently produces a single FAILED record (not 3). The test correctly reports FAIL in this case — making the gap visible is the purpose of the validation script.
- JOB-08 postgres container discovered dynamically via `docker ps --filter name=postgres --format {{.Names}}` — more robust than hardcoding `puppeteer-postgres-1` which depends on compose project name.
- JOB-09 skips (not fails) when no signature is registered — consistent with all prior Phase 43 scripts.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. All 3 scripts exit 0 in the current environment (no DEV node online, no signatures registered — both produce graceful SKIP exits).

## User Setup Required

None — scripts use existing `mop_validation/secrets.env` and `master_of_puppets/secrets/signing.key`.

## Next Phase Readiness

- All 9 job matrix validation scripts complete (JOB-01 through JOB-09 in `mop_validation/scripts/`)
- JOB-07 will FAIL if `node.py` does not send `retriable=True` — documenting the retry gap is intentional
- JOB-08 requires postgres container to be accessible from the host running the script
- JOB-09 relies on Plan 43-01 REVOKED guard being deployed in the running stack
- Phase 44 (foundry test matrix) and Phase 45 (scheduler test matrix) can proceed independently

## Self-Check: PASSED

- FOUND: mop_validation/scripts/verify_job_07_retry_crash.py
- FOUND: mop_validation/scripts/verify_job_08_bad_sig.py
- FOUND: mop_validation/scripts/verify_job_09_revoked.py
- FOUND: .planning/phases/43-job-test-matrix/43-04-SUMMARY.md
- FOUND: commit df917c3 (verify_job_07_retry_crash.py)
- FOUND: commit 422dc83 (verify_job_08_bad_sig.py)
- FOUND: commit 370ad83 (verify_job_09_revoked.py)

---
*Phase: 43-job-test-matrix*
*Completed: 2026-03-21*

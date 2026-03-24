---
phase: 54-bug-fix-blitz
plan: 01
subsystem: api
tags: [job-service, retry, pagination, fastapi, sqlalchemy]

requires:
  - phase: 51-job-detail-resubmit-and-bulk-ops
    provides: originating_guid column on Job ORM model for resubmit traceability
  - phase: 49-pagination-filtering-and-search
    provides: list_jobs() paginated response shape with items/total/next_cursor

provides:
  - list_jobs() response items include retry_count, max_retries, retry_after (ISO string), originating_guid
  - pytest test coverage for all 4 retry fields in GET /jobs response

affects: [job-detail-drawer, queue-visibility, frontend-retry-display]

tech-stack:
  added: []
  patterns:
    - "TDD Wave 0/Wave 1: RED commit (test stub) then GREEN commit (implementation) per plan"
    - "retry_after serialised as ISO string at service layer boundary, not at ORM layer"

key-files:
  created:
    - puppeteer/tests/test_list_jobs_retry_fields.py
  modified:
    - puppeteer/agent_service/services/job_service.py

key-decisions:
  - "retry_after serialised via .isoformat() at the list_jobs() dict build point — consistent with other datetime fields like started_at; no change to ORM model needed"
  - "Only list_jobs() response dict modified; list_jobs_for_export() dict intentionally left unchanged (different shape)"

patterns-established:
  - "Retry field serialisation: always convert datetime to ISO string at service layer dict boundary"

requirements-completed: [JOB-04, JOB-05]

duration: 3min
completed: 2026-03-23
---

# Phase 54 Plan 01: Bug Fix Blitz — INT-04 Retry Fields Summary

**Patched list_jobs() to expose retry_count, max_retries, retry_after (ISO string), and originating_guid in GET /jobs response items, unblocking the job detail drawer's retry state display**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-23T22:11:09Z
- **Completed:** 2026-03-23T22:13:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created 3 pytest tests (TDD RED) that proved the 4 fields were missing from the API response
- Added 4 lines to `list_jobs()` response dict with correct ISO serialisation for `retry_after`
- All 3 tests pass (GREEN); no regressions in the 118-test passing baseline

## Task Commits

1. **Task 1: Wave 0 — Create failing test scaffold for INT-04** - `8d3a7d5` (test)
2. **Task 2: Patch list_jobs() response dict with 4 missing fields** - `0200fb1` (feat)

## Files Created/Modified

- `puppeteer/tests/test_list_jobs_retry_fields.py` - 3 pytest tests covering retry_count, max_retries, retry_after (ISO string), and originating_guid in GET /jobs response
- `puppeteer/agent_service/services/job_service.py` - Added 4 fields to list_jobs() response_jobs.append() dict

## Decisions Made

- `retry_after` serialised via `.isoformat()` at the dict-build point in list_jobs() — consistent with how other datetime fields are handled in the JSON boundary; no ORM change needed.
- The export dict (`list_jobs_for_export`) was intentionally left unchanged — it has a different shape and different consumers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The project root `.venv` at `/home/thomas/Development/master_of_puppets/.venv/bin/pytest` must be used; the `puppeteer/.venv` only contains the Python symlink (no packages installed).
- 108 pre-existing failures and 6 collection errors exist in the full test suite (unrelated to this plan). Verified baseline before and after change — no new failures introduced.

## Next Phase Readiness

- INT-04 is resolved. The job detail drawer can now read `retry_count`, `max_retries`, `retry_after`, and `originating_guid` from the GET /jobs response.
- Remaining INT-0x bugs in Phase 54 can proceed independently.

---
*Phase: 54-bug-fix-blitz*
*Completed: 2026-03-23*

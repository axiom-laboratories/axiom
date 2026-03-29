---
phase: 88-dispatch-diagnosis-ui
plan: 01
subsystem: api
tags: [fastapi, job-diagnosis, backend, pydantic]

requires:
  - phase: prior-dispatch-diagnosis
    provides: "Existing GET /jobs/{guid}/dispatch-diagnosis endpoint and JobService.get_dispatch_diagnosis method"

provides:
  - "Stuck-ASSIGNED detection in get_dispatch_diagnosis (threshold: timeout * 1.2)"
  - "BulkDiagnosisRequest Pydantic model"
  - "POST /jobs/dispatch-diagnosis/bulk endpoint aggregating diagnoses for multiple job GUIDs"

affects:
  - 88-dispatch-diagnosis-ui plan 02 (frontend consuming bulk endpoint)

tech-stack:
  added: []
  patterns:
    - "Bulk pattern: POST with {guids: List[str]}, returns {results: {guid: diagnosis_dict}}"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "Use require_auth (not require_permission) for bulk endpoint, matching single-job diagnosis endpoint"
  - "Stuck-ASSIGNED branch placed BEFORE not_pending guard so ASSIGNED jobs past threshold get a specific reason code"
  - "threshold_minutes = timeout_minutes * 1.2 — 20% grace margin before flagging as stuck"
  - "No response model for bulk endpoint — plain dict {results: {}} avoids coupling to diagnosis shape"

requirements-completed: [DIAG-02]

duration: 2min
completed: 2026-03-29
---

# Phase 88 Plan 01: Stuck-ASSIGNED Detection and Bulk Diagnosis Endpoint Summary

**Extended dispatch diagnosis backend with stuck-ASSIGNED detection (timeout*1.2 threshold) and a bulk POST endpoint that aggregates diagnoses for multiple job GUIDs in one call.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T20:02:47Z
- **Completed:** 2026-03-29T20:04:59Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `get_dispatch_diagnosis` now detects ASSIGNED jobs unresponsive past their timeout (returns `reason="stuck_assigned"` with node_id and elapsed minutes)
- `BulkDiagnosisRequest` Pydantic model added to `models.py`
- `POST /jobs/dispatch-diagnosis/bulk` endpoint registered — loops over guids, aggregates diagnoses, returns `{"results": {guid: diagnosis}}`

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend get_dispatch_diagnosis for stuck-ASSIGNED jobs** - `3a24752` (feat)
2. **Task 2: Add BulkDiagnosisRequest model** - `d482f29` (feat)
3. **Task 3: Add POST /jobs/dispatch-diagnosis/bulk endpoint** - `294f515` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/job_service.py` — Added stuck-ASSIGNED branch to `get_dispatch_diagnosis`
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/models.py` — Added `BulkDiagnosisRequest` model
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/main.py` — Added bulk endpoint + import

## Decisions Made

- Placed the stuck-ASSIGNED branch before the `not_pending` guard — this ensures ASSIGNED jobs past threshold return `stuck_assigned` rather than `not_pending`, giving operators an actionable specific reason.
- Used `require_auth` (not `require_permission`) on the bulk endpoint, consistent with the single-job endpoint.
- No response model for the bulk endpoint — returns plain dict to avoid tight coupling with the diagnosis shape.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test collection errors (5 files fail to collect due to missing modules: `intent_scanner`, `admin_signer`, etc.). These existed before this plan's changes and are not regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend data contract complete for Phase 88 Plan 02 (frontend)
- Both diagnosis routes registered: `GET /jobs/{guid}/dispatch-diagnosis` and `POST /jobs/dispatch-diagnosis/bulk`
- Frontend can now poll the bulk endpoint with PENDING + ASSIGNED job GUIDs to show per-job diagnosis in one round-trip

---
*Phase: 88-dispatch-diagnosis-ui*
*Completed: 2026-03-29*

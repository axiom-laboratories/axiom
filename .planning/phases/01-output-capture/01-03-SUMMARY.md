---
phase: 01-output-capture
plan: "03"
subsystem: api, ui
tags: [fastapi, react, typescript, sqlalchemy, dialog, execution-log]

# Dependency graph
requires:
  - plan: 01-01
    provides: ExecutionRecord ORM model in db.py
  - plan: 01-02
    provides: job_service.py writes ExecutionRecord rows via ResultReport
provides:
  - GET /jobs/{guid}/executions FastAPI route returning execution history ordered newest-first
  - ExecutionLogModal full-screen React dialog for viewing captured output with colour coding
  - SECURITY_REJECTED status badge (destructive) + ShieldAlert icon in Jobs job list
  - "View Output" button in JobDetailPanel wired to ExecutionLogModal
affects:
  - Phase 2 (retry may link to execution history)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ExecutionLogModal fetches /jobs/{guid}/executions on open via authenticatedFetch in useEffect"
    - "logModalGuid state at Jobs component level — modal state lifted above JobDetailPanel"
    - "Dialog import from @/components/ui/dialog for full-screen log viewer"
    - "output_log TEXT deserialized in route handler via json.loads (not ORM layer)"

key-files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/dashboard/src/views/Jobs.tsx

key-decisions:
  - "onViewOutput callback lifted to Jobs level — JobDetailPanel remains a pure display component"
  - "Attempt selector shown only when executions.length > 1 — no visual noise for single-attempt jobs"
  - "Exit code shown in header AND as end-of-stream visual indicator (plan requirement met)"
  - "SECURITY_REJECTED maps to destructive variant (same as failed/cancelled) to signal terminal bad state"

patterns-established:
  - "ExecutionLogModal pattern: open on guid, fetch on mount, auto-scroll to bottom via useRef"

requirements-completed:
  - OUT-03
  - OUT-04

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 1 Plan 03: API Route + Log Viewer Summary

**GET /jobs/{guid}/executions FastAPI route + ExecutionLogModal full-screen dialog with colour-coded [OUT]/[ERR] log stream and SECURITY_REJECTED status handling in Jobs.tsx**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-04T21:19:35Z
- **Completed:** 2026-03-04T21:22:07Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GET /jobs/{guid}/executions route added to main.py — requires jobs:read, returns records newest-first with parsed output_log, computed duration_seconds, empty list for unknown guids
- ExecutionLogModal full-screen dialog (95vw × 90vh): interleaved log stream with [OUT]/[ERR] prefixes, stdout zinc-300/stderr amber-400, exit code in header + end-of-stream indicator, truncation notice, copy-to-clipboard, attempt selector for multi-attempt jobs
- SECURITY_REJECTED handled in getStatusVariant (destructive) and StatusIcon (ShieldAlert orange) and status filter dropdown
- "View Output" button added to JobDetailPanel, modal state lifted to Jobs component level via logModalGuid

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET /jobs/{guid}/executions route to main.py** - `e262596` (feat)
2. **Task 2: Add ExecutionLogModal and SECURITY_REJECTED handling to Jobs.tsx** - `249800b` (feat)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - Added ExecutionRecord import + GET /jobs/{guid}/executions route with jobs:read permission
- `puppeteer/dashboard/src/views/Jobs.tsx` - Added OutputLine/ExecutionRecord interfaces, ExecutionLogModal component, SECURITY_REJECTED status handling, View Output button wiring

## Decisions Made
- onViewOutput callback lifted to Jobs level: JobDetailPanel is a pure display component with no internal fetch state; lifting the modal guid state to Jobs keeps all data fetching at the page level, consistent with how selectedJob and detailOpen are managed.
- SECURITY_REJECTED variant is destructive (same as failed): a security rejection is a terminal bad-path state — making it visually identical to failed is intentional. The ShieldAlert icon differentiates it.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing backend test conftest imports `puppeteer.agent_service.db` with absolute path — fails because the package is not installed in the venv. This predates this plan (documented in 01-01 SUMMARY). Not related to this plan's changes. The 25 agent_service tests that do run in the correct context all pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 (Output Capture) is now complete: data contracts (01-01), job_service capture (01-02), API + UI (01-03)
- Phase 2 (Retry) can begin: ExecutionRecord rows exist and are accessible via API
- No blockers

## Self-Check: PASSED

- puppeteer/agent_service/main.py: FOUND
- puppeteer/dashboard/src/views/Jobs.tsx: FOUND
- .planning/phases/01-output-capture/01-03-SUMMARY.md: FOUND
- Commit e262596 (Task 1): FOUND
- Commit 249800b (Task 2): FOUND

---
*Phase: 01-output-capture*
*Completed: 2026-03-04*

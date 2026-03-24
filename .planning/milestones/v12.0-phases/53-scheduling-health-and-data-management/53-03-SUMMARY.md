---
phase: 53-scheduling-health-and-data-management
plan: "03"
subsystem: scheduling
tags: [apscheduler, sqlalchemy, health, fire-log, pruning, sweeper]

requires:
  - phase: 53-01
    provides: ScheduledFireLog DB model, test stubs for VIS-05/VIS-06
  - phase: 53-02
    provides: dispatch_timeout_minutes on Job/ScheduledJob, allow_overlap on ScheduledJob

provides:
  - Fire log hooks in execute_scheduled_job (status fired/skipped_draft/skipped_overlap)
  - allow_overlap flag respected in overlap guard
  - sweep_dispatch_timeouts() method — auto-fails PENDING jobs past dispatch deadline
  - get_scheduling_health(window, db) — aggregate + per-definition health with LATE/MISSED
  - GET /health/scheduling endpoint (jobs:read permission)
  - SchedulingHealthResponse + DefinitionHealthRow Pydantic models
  - prune_execution_history() respects pinned=False and prunes fire log rows >31 days
  - expected_fires_in_window() helper for cron fire time enumeration

affects:
  - frontend scheduling health dashboard (VIS-05, VIS-06)
  - any future phase consuming scheduling observability data

tech-stack:
  added: []
  patterns:
    - Fire log written before skip guards — ensures every cron attempt is recorded
    - allow_overlap guard checked via getattr with False default — no regression
    - Health query: DB counts + cron projection combined in service layer, not DB stored
    - TDD: test stubs replaced with async in-memory SQLite tests

key-files:
  created:
    - puppeteer/tests/test_scheduling_health.py
  modified:
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "Fire log written at top of execute_scheduled_job (before skip checks) so every cron attempt is recorded regardless of skip reason"
  - "allow_overlap guard uses getattr(s_job, 'allow_overlap', False) — safe default, no regression"
  - "sweep_dispatch_timeouts registered as 5-minute interval APScheduler job in start()"
  - "prune_execution_history reads execution_retention_days first, fallback history_retention_days, fallback 14"
  - "test_missed_fire_detection tests expected_fires_in_window() helper directly — simpler than DB round-trip"
  - "get_scheduling_health computes LATE/MISSED via Python loop over cron projection rather than SQL — avoids complex SQL window functions"

patterns-established:
  - "Health aggregation pattern: query DB counts, enumerate expected fires via APScheduler CronTrigger, diff in Python"

requirements-completed: [VIS-05, VIS-06]

duration: 10min
completed: 2026-03-23
---

# Phase 53 Plan 03: Scheduling Health Backend Summary

**APScheduler fire log hooks, dispatch timeout sweeper, missed-fire detection, and GET /health/scheduling endpoint with LATE/MISSED classification**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-23T20:06:00Z
- **Completed:** 2026-03-23T20:16:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Every cron fire writes a ScheduledFireLog row (status: fired/skipped_draft/skipped_overlap)
- allow_overlap=True skips the overlap guard; False (default) runs it with log update
- sweep_dispatch_timeouts() queries PENDING jobs past dispatch deadline and marks them FAILED; registered as 5-min interval job
- get_scheduling_health() returns aggregate totals and per-definition health rows with LATE/MISSED classification via APScheduler CronTrigger projection
- GET /health/scheduling endpoint added to main.py with jobs:read permission
- prune_execution_history() updated: reads execution_retention_days > history_retention_days > 14 fallback; respects pinned=False; nightly fire log pruning (>31 days)
- Both test stubs replaced with passing async tests

## Task Commits

1. **Task 1: Fire log hooks, overlap control, sweeper, pruner** - `ce799af` (feat)
2. **Task 2: Health endpoint route, Pydantic models, passing tests** - `c05fc51` (feat)

## Files Created/Modified

- `puppeteer/agent_service/services/scheduler_service.py` - Fire log hooks, expected_fires_in_window(), get_scheduling_health(), sweep_dispatch_timeouts(), updated prune_execution_history()
- `puppeteer/agent_service/models.py` - DefinitionHealthRow and SchedulingHealthResponse Pydantic models
- `puppeteer/agent_service/main.py` - GET /health/scheduling route
- `puppeteer/tests/test_scheduling_health.py` - Real async tests replacing stubs

## Decisions Made

- Fire log written before all skip checks — ensures complete audit trail of every cron attempt
- allow_overlap uses getattr with False default — backward-compatible
- Health aggregation uses Python loop over APScheduler CronTrigger projection rather than SQL window functions — simpler, no new dependencies
- test_missed_fire_detection tests expected_fires_in_window() helper directly rather than full DB round-trip — faster and more focused

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Scheduling health backend complete; VIS-05/VIS-06 requirements satisfied
- Frontend can now consume GET /health/scheduling for scheduling observability dashboard
- No blockers

---
*Phase: 53-scheduling-health-and-data-management*
*Completed: 2026-03-23*

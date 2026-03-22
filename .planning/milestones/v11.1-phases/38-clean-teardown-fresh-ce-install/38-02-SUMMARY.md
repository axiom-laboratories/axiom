---
phase: 38-clean-teardown-fresh-ce-install
plan: 02
subsystem: testing
tags: [python, requests, postgres, docker, verification, ce-install]

# Dependency graph
requires: []
provides:
  - "verify_ce_install.py — automated gate script for INST-03 + INST-04"
  - "13-table count check via docker exec psql (excluding apscheduler_jobs)"
  - "8-key feature flag validation (all false) via GET /api/features"
  - "Edition check (community) via GET /api/licence with Bearer auth"
  - "INST-04 manual admin re-seed test steps documented in script constant"
affects:
  - phase-41
  - phase-42

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "load_env() reads secrets.env line-by-line — same pattern as test_local_stack.py"
    - "check() helper prints [PASS]/[FAIL] and returns bool for result accumulation"
    - "Dynamic postgres container discovery via docker ps --filter before psql calls"

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/verify_ce_install.py
  modified: []

key-decisions:
  - "SECRETS_ENV points to MOP_DIR/secrets.env (not mop_validation/secrets.env) — same credential store as the stack itself"
  - "Table count query excludes apscheduler_jobs (APScheduler internal table, not a CE schema table)"
  - "INST-04 is documented in a module-level constant (INST_04_MANUAL_TEST_STEPS) so it's accessible to readers without running the script"
  - "Script exits 1 on stack not ready (fast fail) rather than continuing with broken checks"

patterns-established:
  - "check(name, bool, detail) accumulation pattern: collect results list, sum at end, exit with count comparison"
  - "wait_for_stack polls /api/health every 3s printing dots — visual feedback without flooding output"
  - "get_postgres_container() always falls back to 'puppeteer-db-1' so script runs even if docker ps fails"

requirements-completed:
  - INST-03
  - INST-04

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 38 Plan 02: CE Install Verification Script Summary

**Standalone Python gate script that confirms fresh axiom-split CE cold start: 13 tables, 8 features all false, edition == community, with INST-04 re-seed safety steps embedded**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-20T19:08:58Z
- **Completed:** 2026-03-20T19:10:37Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Created `/home/thomas/Development/mop_validation/scripts/verify_ce_install.py` (295 lines, executable)
- Implements INST-03: table count (excluding apscheduler_jobs), feature flags, edition via 3 distinct checks
- Embeds INST-04 manual test steps as `INST_04_MANUAL_TEST_STEPS` constant — readable without running script
- Script exits 0 on all-pass, 1 on any failure — usable as CI/pipeline gate for Phases 41 and 42

## Task Commits

Each task was committed atomically:

1. **Task 1: Write verify_ce_install.py (INST-03 + INST-04)** - `76520b7` (feat) — in mop_validation repo

**Plan metadata:** committed with state/summary update (master_of_puppets repo)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/verify_ce_install.py` — CE install verification gate script

## Decisions Made

- `SECRETS_ENV` points to `MOP_DIR/secrets.env` (not `mop_validation/secrets.env`) — the stack and test scripts share the same credential store.
- Table count query explicitly excludes `apscheduler_jobs` because APScheduler creates its own internal table that is not part of the CE schema.
- `INST_04_MANUAL_TEST_STEPS` is a module-level string constant so future readers can see the full test procedure with `grep` or any editor without running anything.
- Fast-fail if stack not ready (exits 1 immediately after 90s timeout) — avoids misleading FAIL output from checks that would all fail on a down stack.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Script uses existing `secrets.env`.

## Next Phase Readiness

- `verify_ce_install.py` is ready to use as the INST-03 automated gate after any CE cold start.
- Run it against the axiom-split CE stack before advancing to Phase 41 (EE activation).
- INST-04 manual test steps are embedded in the script — follow them once to verify admin re-seed safety.

---
*Phase: 38-clean-teardown-fresh-ce-install*
*Completed: 2026-03-20*

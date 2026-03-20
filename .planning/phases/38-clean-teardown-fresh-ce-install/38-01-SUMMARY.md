---
phase: 38-clean-teardown-fresh-ce-install
plan: 01
subsystem: testing
tags: [bash, docker-compose, incus, lxc, teardown, axiom-split]

# Dependency graph
requires: []
provides:
  - teardown_soft.sh — stops axiom-split CE stack, removes only pgdata, preserves PKI volumes and LXC node secrets (INST-01)
  - teardown_hard.sh — removes all Docker volumes and LXC node secrets for a true clean slate (INST-02)
affects:
  - 39-ee-license-validation
  - 40-node-provisioning
  - 41-job-execution
  - 42-scheduler-validation
  - 43-foundry-validation
  - 44-security-validation
  - 45-final-report

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Soft teardown pattern: docker compose down (no -v) + targeted volume rm for safe between-run resets"
    - "Hard teardown pattern: docker compose down -v --remove-orphans + best-effort incus exec per node"
    - "LXC node discovery: incus list --format csv | while IFS=',' read -r name rest with axiom-node-* pattern match"

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/teardown_soft.sh
    - /home/thomas/Development/mop_validation/scripts/teardown_hard.sh
  modified: []

key-decisions:
  - "Soft teardown uses docker compose down (no -v flag) + explicit docker volume rm of pgdata only — this is the only safe way to preserve certs-volume and the Root CA between runs"
  - "Hard teardown does NOT use global set -e — LXC node steps are best-effort so a stopped node does not abort the entire teardown"
  - "Both scripts target .worktrees/axiom-split/puppeteer/compose.server.yaml, not the main branch compose file"

patterns-established:
  - "Idempotency via || echo [WARN]: docker volume rm with 2>/dev/null fallback, incus exec with || echo [WARN] — running twice never fails"
  - "Compose project name is puppeteer (directory name), so volumes are prefixed puppeteer_"

requirements-completed: [INST-01, INST-02]

# Metrics
duration: 1min
completed: 2026-03-20
---

# Phase 38 Plan 01: Teardown Scripts Summary

**Two idempotent bash teardown scripts for the axiom-split CE stack — soft (preserves PKI/LXC secrets) and hard (full clean slate including all volumes and node certs)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-20T19:08:51Z
- **Completed:** 2026-03-20T19:09:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- teardown_soft.sh: stops CE stack containers, removes only puppeteer_pgdata volume, preserves all PKI and data volumes, leaves LXC node secrets intact for re-enrollment
- teardown_hard.sh: removes all Docker volumes via `down -v --remove-orphans`, discovers axiom-node-* Incus containers dynamically, wipes /home/ubuntu/secrets/ on each with best-effort error handling
- Both scripts are idempotent (missing volumes produce [WARN], not exit 1), executable, and pass bash -n syntax check

## Task Commits

Each task was committed atomically in the mop_validation repo:

1. **Task 1: Write teardown_soft.sh (INST-01)** - `4d172ed` (feat)
2. **Task 2: Write teardown_hard.sh (INST-02)** - `c6cb352` (feat)

**Plan metadata:** (this repo — see below)

## Files Created/Modified
- `/home/thomas/Development/mop_validation/scripts/teardown_soft.sh` - Soft teardown: stops stack, removes pgdata only, preserves PKI volumes and LXC secrets
- `/home/thomas/Development/mop_validation/scripts/teardown_hard.sh` - Hard teardown: removes all Docker volumes + wipes axiom-node-* LXC secrets directories

## Decisions Made
- Soft teardown uses `docker compose down` (no `-v`) plus a separate `docker volume rm puppeteer_pgdata` — the only safe approach to drop the DB while keeping the Root CA in certs-volume
- Hard teardown deliberately omits `set -e` globally so an individual stopped LXC node does not abort the script
- Both scripts hardcode the COMPOSE_FILE path to the axiom-split worktree, not the main branch

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- teardown_soft.sh and teardown_hard.sh are ready for use by all subsequent validation phases (39-45)
- Run teardown_soft.sh between test runs to get a fresh DB while keeping the Root CA
- Run teardown_hard.sh before a fresh CE install to ensure zero PKI or data carryover
- No blockers — scripts are independent of any running stack state

---
*Phase: 38-clean-teardown-fresh-ce-install*
*Completed: 2026-03-20*

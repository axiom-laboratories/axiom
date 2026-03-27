---
phase: 79-install-docs-cleanup
plan: 01
subsystem: docs
tags: [docker-compose, mkdocs, install-guide, cold-start, quick-start]

# Dependency graph
requires: []
provides:
  - Clean compose.cold-start.yaml with exactly 5 services (db, cert-manager, agent, dashboard, docs)
  - install.md with Quick Start tab labels and JOIN-token-free Step 3 prose
affects: [phase-80-github-pages-homepage]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - puppeteer/compose.cold-start.yaml
    - docs/docs/getting-started/install.md

key-decisions:
  - "compose.cold-start.yaml trimmed to 5 core services only — puppet nodes require separate JOIN token flow not appropriate for Quick Start"
  - "Tab label renamed from 'Cold-Start Install' to 'Quick Start' across Steps 2, 3, 4 — aligns with user mental model for a first-run compose"

patterns-established: []

requirements-completed:
  - INST-01
  - INST-02

# Metrics
duration: 1min
completed: 2026-03-27
---

# Phase 79 Plan 01: Install Docs Cleanup Summary

**Stripped compose.cold-start.yaml to 5 Axiom services and renamed all three install.md Cold-Start Install tabs to Quick Start with clean JOIN-token-free Step 3 prose**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-27T20:17:52Z
- **Completed:** 2026-03-27T20:18:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed puppet-node-1 and puppet-node-2 service blocks from compose.cold-start.yaml, plus the node1-secrets/node2-secrets volumes
- Trimmed header comment from 4 Quick start steps to 2 (dropped JOIN token generation steps 3 & 4)
- Renamed all three "Cold-Start Install" tab labels in install.md to "Quick Start"
- Replaced Step 3 prose to remove JOIN_TOKEN_1/JOIN_TOKEN_2 and "built-in puppet nodes" references

## Task Commits

Each task was committed atomically:

1. **Task 1: Clean compose.cold-start.yaml** - `3901dba` (chore)
2. **Task 2: Update install.md — rename tabs and fix Step 3 prose** - `3d0e9dc` (docs)

**Plan metadata:** (final commit — see below)

## Files Created/Modified

- `puppeteer/compose.cold-start.yaml` - Removed 2 node services (49 lines deleted); now has exactly 5 services
- `docs/docs/getting-started/install.md` - Renamed 3 tab labels; trimmed Step 3 prose

## Decisions Made

- Tab label "Quick Start" chosen over "Cold-Start Install" because the compose file is now a genuine quick-start with no secondary token setup required
- No forward pointer added to Step 3 prose — the existing "Next: Enroll a Node" footer link already covers the onward flow

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 80 (GitHub Pages + Homepage) can now accurately describe compose.cold-start.yaml as a 5-service quick-start stack
- install.md tab labels are consistent and match what users see when running the compose file

## Self-Check: PASSED

All files and commits verified present.

---
*Phase: 79-install-docs-cleanup*
*Completed: 2026-03-27*

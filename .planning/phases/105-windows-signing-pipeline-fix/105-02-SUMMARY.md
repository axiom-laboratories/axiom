---
phase: 105-windows-signing-pipeline-fix
plan: 02
subsystem: docs
tags: [powershell, windows, mkdocs, tabs, ed25519, getting-started]

# Dependency graph
requires:
  - phase: 103-windows-e2e-validation
    provides: "Original PowerShell tab content (commit 34becc6)"
  - phase: 105-01
    provides: "Server-side CRLF normalization so docs don't mention it"
provides:
  - "Windows PowerShell tabs in first-job.md for complete first-job workflow"
  - "WIN-05 requirement satisfied: full Windows first-job path documented"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - "docs/docs/getting-started/first-job.md"

key-decisions:
  - "Recovered exact Phase 103 content from git (commit 34becc6) rather than rewriting"
  - "No CRLF normalization in docs -- server handles it transparently per Plan 01"

patterns-established: []

requirements-completed: [WIN-05]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 105 Plan 02: Restore PowerShell Tabs in first-job.md Summary

**Restored 3 Windows (PowerShell) tabs in first-job.md lost during PR #18 rebase -- keypair generation, test script creation, and sign+submit workflow using Invoke-RestMethod**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T14:00:30Z
- **Completed:** 2026-04-01T14:02:04Z
- **Tasks:** 6
- **Files modified:** 1

## Accomplishments
- Audited all 5 getting-started docs -- confirmed only first-job.md was missing PowerShell content
- Recovered Phase 103 PowerShell content from git commit 34becc6
- Restored PowerShell tabs to Step 0 (keypair gen), Step 2 (test script), and Manual Setup (sign+submit)
- All Windows tabs use native Invoke-RestMethod, not curl
- No CRLF normalization in docs (server handles transparently via Plan 01)

## Task Commits

Each task was committed atomically:

1. **Task 1-2: Audit + recover Phase 103 content** - (read-only, no commit needed)
2. **Task 3: Add PowerShell tab to Step 0** - `7f86a0d` (docs)
3. **Task 4: Add PowerShell tab to Step 2** - `076dd73` (docs)
4. **Task 5: Add PowerShell tab to Manual Setup** - `1b15e5b` (docs)
5. **Task 6: Verify restored content** - (verification only, no commit needed)

## Files Created/Modified
- `docs/docs/getting-started/first-job.md` - Restored 3 Windows (PowerShell) tabs with Invoke-RestMethod API calls

## Decisions Made
- Recovered exact Phase 103 content from git rather than rewriting from scratch -- ensures consistency with the validated Windows E2E content
- No CRLF normalization mentioned in any doc snippet -- server handles it transparently (Plan 01)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 105 complete -- all 3 v18.0 audit gaps closed (CRLF fix, cold-start password, PowerShell tabs)
- first-job.md now provides complete Windows coverage alongside Linux/macOS

---
*Phase: 105-windows-signing-pipeline-fix*
*Completed: 2026-04-01*

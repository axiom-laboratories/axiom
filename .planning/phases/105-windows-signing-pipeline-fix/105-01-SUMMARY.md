---
phase: 105-windows-signing-pipeline-fix
plan: 01
subsystem: api
tags: [ed25519, signing, crlf, security, admin-bootstrap]

# Dependency graph
requires:
  - phase: 104-pr-review-merge
    provides: merged main branch with countersign logic
provides:
  - CRLF normalization in create_job before signature verification and countersigning
  - Always-force admin password change on bootstrap with opt-out env var
  - Unit test proving CRLF countersign symmetry
affects: [105-02-windows-signing-pipeline-fix]

# Tech tracking
tech-stack:
  added: []
  patterns: [CRLF normalization before cryptographic operations, opt-out env var pattern for CI]

key-files:
  created: [puppeteer/tests/test_crlf_countersign.py]
  modified: [puppeteer/agent_service/main.py]

key-decisions:
  - "Normalize script_content in payload_dict so downstream code sees LF-only bytes"
  - "ADMIN_SKIP_FORCE_CHANGE env var uses opt-out pattern (force by default, skip only if explicitly set)"

patterns-established:
  - "CRLF normalization: always normalize before any cryptographic sign/verify operation"
  - "Opt-out env var: security defaults ON, explicit env var to disable for CI/automation"

requirements-completed: [WIN-05, WIN-03]

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 105 Plan 01: CRLF Countersign Fix + Cold-Start Forced Password Change Summary

**Server-side CRLF-to-LF normalization in create_job route + always-force admin password change on bootstrap with ADMIN_SKIP_FORCE_CHANGE opt-out**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-01T14:00:38Z
- **Completed:** 2026-04-01T14:01:41Z
- **Tasks:** 5
- **Files modified:** 2

## Accomplishments
- CRLF line endings in script_content normalized to LF before both user signature verification and server countersigning in create_job
- Admin bootstrap now always sets must_change_password=True unless ADMIN_SKIP_FORCE_CHANGE=true is set
- Unit test proves CRLF normalization produces symmetric signatures and that unnormalized CRLF fails verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Read create_job route and admin bootstrap** - read-only (no commit)
2. **Task 2: Add CRLF normalization to create_job** - `fa70d2c` (fix)
3. **Task 3: Fix admin bootstrap to always force password change** - `c6a7f7a` (fix)
4. **Task 4: Write CRLF countersign unit test** - `83ea97e` (test)
5. **Task 5: Run tests to verify** - verification-only (no commit)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - CRLF normalization in create_job + forced password change in admin bootstrap
- `puppeteer/tests/test_crlf_countersign.py` - Ed25519 CRLF countersign symmetry tests (2 tests)

## Decisions Made
- Normalized script_content directly in payload_dict so both the user sig verify path and countersign path use the same LF-only variable
- Used opt-out pattern for ADMIN_SKIP_FORCE_CHANGE (security-on by default)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Server-side CRLF fix is complete; plan 105-02 (docs/Windows quick-start updates) can proceed
- No blockers

---
*Phase: 105-windows-signing-pipeline-fix*
*Completed: 2026-04-01*

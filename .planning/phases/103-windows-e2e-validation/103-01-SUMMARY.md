---
phase: 103-windows-e2e-validation
plan: "01"
subsystem: docs
tags: [powershell, windows, getting-started, mkdocs, documentation]

# Dependency graph
requires: []
provides:
  - "PowerShell tabs in enroll-node.md: CLI token generation and Option B Docker Compose for Windows"
  - "PowerShell tabs in first-job.md: keypair generation, test script creation, and sign+submit via Invoke-RestMethod"
affects:
  - 103-03-windows-e2e-run

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MkDocs Material === tab with Windows (PowerShell) alongside Linux / macOS tabs"
    - "PowerShell TLS bypass pattern using add-type TrustAll for self-signed certs"
    - "PowerShell here-string @'...'@ piped to Out-File -Encoding utf8 instead of bash heredoc"

key-files:
  created: []
  modified:
    - docs/docs/getting-started/enroll-node.md
    - docs/docs/getting-started/first-job.md

key-decisions:
  - "Option B tab renamed to include OS qualifier so Windows tab can coexist as a parallel tab without nesting"
  - "Windows signing uses Python cryptography library (no openssl dependency) matching key generation approach"
  - "TLS workaround via add-type TrustAll class used consistently across all PowerShell Invoke-RestMethod calls"

patterns-established:
  - "Windows doc pattern: save script to .py file via Out-File, then python <file.py> — avoids heredoc limitation"
  - "Windows PowerShell TLS bypass: add-type TrustAll class before any Invoke-RestMethod call to self-signed endpoint"

requirements-completed:
  - WIN-02
  - WIN-04
  - WIN-05

# Metrics
duration: 32min
completed: 2026-03-31
---

# Phase 103 Plan 01: Windows E2E Docs Pre-Audit Summary

**MkDocs Material PowerShell tabs added to enroll-node.md (CLI + Option B) and first-job.md (Step 0 + Step 2 + Manual Setup) covering the full Windows getting-started path via Invoke-RestMethod and Python cryptography**

## Performance

- **Duration:** 32 min
- **Started:** 2026-03-31T20:33:37Z
- **Completed:** 2026-03-31T21:06:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added Windows (PowerShell) tab to the CLI step in enroll-node.md with Invoke-RestMethod login + token generation and TLS bypass for self-signed certs
- Added Windows-specific Option B Docker Compose tab in enroll-node.md with named pipe socket path (`//./pipe/docker_engine`) and `host.docker.internal` AGENT_URL
- Added Windows (PowerShell) tab to first-job.md Step 0 (keypair generation via here-string + Out-File), Step 2 (test script creation), and Manual Setup sign+submit (Python cryptography signing + Invoke-RestMethod dispatch)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PowerShell tabs to enroll-node.md** - `c75b2e4` (feat)
2. **Task 2: Add PowerShell tabs to first-job.md** - `34becc6` (feat)

**Plan metadata:** (pending)

## Files Created/Modified

- `docs/docs/getting-started/enroll-node.md` - Added Windows (PowerShell) tab to CLI step (Invoke-RestMethod login + token gen) and Windows Option B Docker Compose tab (named pipe socket, host.docker.internal)
- `docs/docs/getting-started/first-job.md` - Added Windows (PowerShell) tab to Step 0 keypair gen, Step 2 test script creation, and Manual Setup sign+submit section

## Decisions Made

- Option B tab label changed from `=== "Option B: Docker Compose"` to `=== "Option B: Docker Compose (Linux / macOS)"` so a sibling Windows tab `=== "Option B: Docker Compose (Windows (PowerShell))"` could coexist without ambiguity.
- Windows job signing uses Python `cryptography` library rather than `openssl` — removes OpenSSL dependency and is consistent with the keypair generation tab (same library).
- TLS bypass pattern (`add-type TrustAll`) used in both enroll-node.md and first-job.md Windows tabs for consistency — docs users running against a self-signed cert need this every time.

## Deviations from Plan

None - plan executed exactly as written. All tab structures match the plan spec and MkDocs Material syntax.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WIN-04 (node enrollment via PowerShell) is now enabled: enroll-node.md has a complete PowerShell path through CLI token generation and Option B Docker Compose
- WIN-05 (first job dispatch via PowerShell) is now enabled: first-job.md has a complete PowerShell path through keypair generation, test script creation, and sign+submit
- Plan 103-02 (Linux E2E documentation pre-audit) and Plan 103-03 (Windows E2E live run) can proceed

---
*Phase: 103-windows-e2e-validation*
*Completed: 2026-03-31*

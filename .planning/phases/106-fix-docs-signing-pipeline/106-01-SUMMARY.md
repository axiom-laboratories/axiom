---
phase: 106-fix-docs-signing-pipeline
plan: 01
subsystem: docs
tags: [ed25519, signing, powershell, curl, tls]

requires:
  - phase: 105-windows-signing-pipeline-fix
    provides: Server-side CRLF normalization (no client-side docs needed)
provides:
  - Correct signature_id field name in Linux and Windows doc snippets
  - Modern -SkipCertificateCheck TLS pattern in Windows docs
affects: []

tech-stack:
  added: []
  patterns: ["-SkipCertificateCheck on all PowerShell Invoke-RestMethod calls for self-signed certs"]

key-files:
  created: []
  modified:
    - docs/docs/getting-started/first-job.md

key-decisions:
  - "No CRLF normalization documented in client snippets — server handles it transparently per Phase 105"

patterns-established:
  - "PowerShell TLS skip: use -SkipCertificateCheck flag, not TrustAll .NET class"

requirements-completed: [LNX-04, WIN-05]

duration: 1min
completed: 2026-04-01
---

# Phase 106 Plan 01: Fix Docs Signing Pipeline Summary

**Corrected signature_id field name in Linux/Windows snippets and replaced deprecated TrustAll with -SkipCertificateCheck**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-01T18:50:47Z
- **Completed:** 2026-04-01T18:51:28Z
- **Tasks:** 4
- **Files modified:** 1

## Accomplishments
- Fixed `signature_key_id` to `signature_id` in Linux curl snippet (matches server field at main.py:1098)
- Fixed `signature_key_id` to `signature_id` in PowerShell $body hashtable
- Replaced deprecated TrustAll .NET class with `-SkipCertificateCheck` on all PowerShell Invoke-RestMethod calls
- All verification checks pass: 0 occurrences of old patterns, correct counts of new patterns

## Task Commits

Each task was committed atomically:

1. **Task 1: Read target file sections** - (read-only, no commit)
2. **Task 2: Fix signature_key_id in Linux curl** - `421427d` (fix)
3. **Task 3: Replace TrustAll + fix PS signature_id** - `c7901cf` (fix)
4. **Task 4: Final verification** - (verification-only, no commit)

## Files Created/Modified
- `docs/docs/getting-started/first-job.md` - Fixed field names and TLS pattern in Manual Setup section

## Decisions Made
- No CRLF normalization added to docs — server handles it transparently per Phase 105 decision

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 3 v18.0 signing pipeline documentation gaps are now closed
- Linux and Windows doc snippets are consistent with server's expected field names
- PowerShell TLS pattern is consistent with enroll-node.md

---
*Phase: 106-fix-docs-signing-pipeline*
*Completed: 2026-04-01*

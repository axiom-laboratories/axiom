---
phase: 67-getting-started-documentation
plan: "01"
subsystem: docs
tags: [mkdocs, material, pymdownx, tabs, documentation, install]

requires:
  - phase: 66-backend-code-fixes
    provides: Verified CE/EE feature gating in place before docs describing that boundary are published

provides:
  - pymdownx.tabbed extension active in mkdocs.yml (alternate_style: true)
  - install.md Step 1 tab pair — Git Clone vs GHCR Pull for users without git
  - install.md Step 2 tab pair — Server Install (secrets.env) vs Cold-Start Install (.env)
  - Explicit ADMIN_PASSWORD setup step in both install paths

affects: [67-02, 67-03, 68-ee-doc-cleanup]

tech-stack:
  added: [pymdownx.tabbed]
  patterns:
    - "Tab pair pattern: === 'Tab Name' with 4-space indented content blocks"
    - "Per-path admonitions: danger/warning blocks repeated inside relevant tabs"

key-files:
  created: []
  modified:
    - docs/mkdocs.yml
    - docs/docs/getting-started/install.md

key-decisions:
  - "GHCR Pull command uses -f flag: docker compose -f compose.cold-start.yaml pull (full command, not bare)"
  - "Cold-Start tab is minimal: only ADMIN_PASSWORD and ENCRYPTION_KEY required"
  - "Server Install tab retains all existing admonitions (danger API_KEY, warning ADMIN_PASSWORD first-start)"

patterns-established:
  - "Tab syntax: pymdownx.tabbed with alternate_style: true; tabs marked === 'Label'; content indented 4 spaces"
  - "Admonitions inside tabs: placed after the code block, indented 4 spaces to stay inside tab scope"

requirements-completed:
  - DOCS-02
  - DOCS-01
  - DOCS-08

duration: 2min
completed: 2026-03-26
---

# Phase 67 Plan 01: Getting Started Documentation — Install Page Summary

**pymdownx.tabbed enabled in mkdocs.yml; install.md rewritten with Git Clone/GHCR Pull and Server/Cold-Start tab pairs, each with explicit ADMIN_PASSWORD setup**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-26T09:26:13Z
- **Completed:** 2026-03-26T09:28:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `pymdownx.tabbed: alternate_style: true` to `docs/mkdocs.yml` at correct indentation level
- Rewrote install.md Step 1 as a Git Clone / GHCR Pull tab pair — users without git can now follow a documented path
- Rewrote install.md Step 2 as a Server Install / Cold-Start Install tab pair, each with explicit ADMIN_PASSWORD setup before `docker compose up`
- `mkdocs build --strict` passes with no errors or warnings

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymdownx.tabbed to mkdocs.yml** - `aa864f0` (feat)
2. **Task 2: Rewrite install.md with tab pairs for Step 1 and Step 2** - `558aebf` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `docs/mkdocs.yml` — Added `pymdownx.tabbed: alternate_style: true` extension
- `docs/docs/getting-started/install.md` — Step 1 and Step 2 rewritten as tab pairs; Steps 3/4 and EE section unchanged

## Decisions Made

- Cold-Start tab is intentionally minimal (ADMIN_PASSWORD + ENCRYPTION_KEY only) — the cold-start path removes the need for SECRET_KEY and API_KEY by not running the full server compose
- GHCR Pull command uses the full `-f` flag: `docker compose -f compose.cold-start.yaml pull` rather than a bare `docker compose pull`
- Existing admonitions (danger API_KEY, warning ADMIN_PASSWORD first-start) were preserved exactly in the Server Install tab

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Tab infrastructure in place: future plans (67-02 enroll-node.md, 67-03 first-job.md) can use === tab syntax immediately
- `mkdocs build --strict` clean — no broken anchors or extension errors introduced

---
*Phase: 67-getting-started-documentation*
*Completed: 2026-03-26*

## Self-Check: PASSED

- docs/mkdocs.yml: FOUND
- docs/docs/getting-started/install.md: FOUND
- .planning/phases/67-getting-started-documentation/67-01-SUMMARY.md: FOUND
- Commit aa864f0: FOUND
- Commit 558aebf: FOUND

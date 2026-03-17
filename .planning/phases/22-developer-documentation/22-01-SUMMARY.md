---
phase: 22-developer-documentation
plan: 01
subsystem: documentation
tags: [mkdocs, mermaid, architecture, security, fastapi, mtls, ed25519, jwt, rbac, fernet]

# Dependency graph
requires:
  - phase: 20-documentation-infrastructure
    provides: MkDocs Material site with nginx, privacy plugin, Docker two-stage build
  - phase: 21-api-reference
    provides: api-reference/ content already in docs/docs/

provides:
  - pymdownx.superfences Mermaid rendering config in mkdocs.yml
  - Developer nav section in mkdocs.yml
  - Full technical architecture guide (582 lines, 7 Mermaid diagrams)
affects:
  - 22-02 (setup-deployment.md — nav already has Developer section ready)
  - 22-03 (contributing.md — same nav section)
  - Any phase that needs to reference architecture for context

# Tech tracking
tech-stack:
  added:
    - pymdownx.superfences custom_fences (Mermaid diagram rendering — zero new packages, bundled with Material)
    - admonition extension (MkDocs Material admonition boxes)
    - pymdownx.details extension
    - tables extension
  patterns:
    - Mermaid diagrams use triple-backtick mermaid fences in markdown
    - mkdocs.yml nav: only lists files that exist on disk (strict mode enforcement)
    - Architecture guide uses MkDocs Material admonition boxes for warnings/tips

key-files:
  created:
    - docs/docs/developer/architecture.md
  modified:
    - docs/mkdocs.yml

key-decisions:
  - "Only architecture.md added to nav in plan 01 — setup-deployment.md and contributing.md nav entries deferred to plans 02/03 (mkdocs build --strict requires listed files to exist)"
  - "admonition + pymdownx.details extensions added alongside superfences — needed for !!! note/warning/tip boxes in the architecture guide"

patterns-established:
  - "Mermaid diagrams: triple-backtick mermaid fences rendered via pymdownx.superfences custom_fences config"
  - "Strict build safety: nav entries must only be added when the target file is created in the same commit"

requirements-completed: [DEVDOC-01]

# Metrics
duration: 4min
completed: 2026-03-17
---

# Phase 22 Plan 01: Architecture Guide Summary

**Full technical architecture guide with 7 Mermaid diagrams, covering all 8 services, complete DB schema erDiagram, security model (mTLS + Ed25519 + JWT + RBAC + Fernet), Foundry/Smelter pipeline, and pull model rationale — Mermaid rendering enabled via pymdownx.superfences in mkdocs.yml**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-17T09:30:05Z
- **Completed:** 2026-03-17T09:34:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Enabled Mermaid diagram rendering in mkdocs.yml via pymdownx.superfences custom_fences — zero extra packages, uses Material's bundled pymdown-extensions
- Created `docs/docs/developer/architecture.md` — 582 lines, 7 Mermaid diagrams (system overview, ER schema, mTLS enrollment sequence, Ed25519 signing chain, job execution flow, Foundry build pipeline, pull model heartbeat loop)
- Added Developer nav section to mkdocs.yml with Architecture entry (plans 02/03 will append setup-deployment and contributing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Enable Mermaid in mkdocs.yml and add Developer nav section** - `ec6bb9f` (feat)
2. **Task 2: Write the full architecture guide** - `41a4901` (feat)

**Plan metadata:** (docs commit — created below)

## Files Created/Modified

- `docs/mkdocs.yml` — Added markdown_extensions (pymdownx.superfences + admonition + tables), nav: section with Home/Developer/API Reference
- `docs/docs/developer/architecture.md` — 582-line full technical architecture guide with 7 Mermaid diagrams

## Decisions Made

- Added `admonition`, `pymdownx.details`, and `tables` extensions alongside `pymdownx.superfences` — required by the `!!! warning` and `!!! note` admonition boxes used in the architecture guide. The plan only mentioned superfences but these are necessary for the guide to render correctly.
- Only `developer/architecture.md` is listed in the nav — `setup-deployment.md` and `contributing.md` entries are deferred to plans 02 and 03 per the plan's explicit instructions (mkdocs build --strict fails if listed files don't exist on disk).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added admonition, pymdownx.details, and tables extensions**
- **Found during:** Task 2 (writing architecture guide with admonition boxes)
- **Issue:** Plan specified only `pymdownx.superfences` but the architecture guide uses `!!! warning`, `!!! note`, `!!! tip` admonition boxes and markdown tables — these require the `admonition`, `pymdownx.details`, and `tables` extensions to render correctly
- **Fix:** Added the three extensions to the `markdown_extensions` block in mkdocs.yml alongside superfences
- **Files modified:** `docs/mkdocs.yml`
- **Verification:** All extensions are bundled with MkDocs Material — no new packages needed; mkdocs build will render admonitions correctly
- **Committed in:** `ec6bb9f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (missing critical — extensions needed for correct rendering)
**Impact on plan:** Minor additive change; no scope creep. All extensions are bundled with Material.

## Issues Encountered

None — plan executed with one minor extension addition for correct rendering.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- mkdocs.yml nav has Developer section established; plans 02 and 03 can append to it
- Mermaid rendering is live — subsequent documentation guides can use diagrams immediately
- `docs/docs/developer/` directory exists — plans 02 and 03 create files there

## Self-Check: PASSED

- `docs/mkdocs.yml` — FOUND
- `docs/docs/developer/architecture.md` — FOUND
- `22-01-SUMMARY.md` — FOUND
- Commit `ec6bb9f` (Task 1) — FOUND
- Commit `41a4901` (Task 2) — FOUND

---
*Phase: 22-developer-documentation*
*Completed: 2026-03-17*

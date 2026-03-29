---
phase: 84-package-repo-operator-docs
plan: 02
subsystem: docs
tags: [mkdocs, devpi, apt-cacher-ng, baget, nuget, pypi, air-gap, package-mirrors]

# Dependency graph
requires:
  - phase: 84-package-repo-operator-docs
    provides: CONTEXT.md and RESEARCH.md confirming devpi port, apt-cacher-ng compose snippet, BaGet compose snippet
provides:
  - docs/docs/runbooks/package-mirrors.md — full from-scratch runbook for devpi, apt-cacher-ng, BaGet
  - docs/mkdocs.yml nav entry for Package Mirror Setup under Runbooks
  - docs/docs/security/air-gap.md cross-link blockquote pointing to package-mirrors.md
affects: [85-screenshot-capture, 86-docs-accuracy-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Package mirror runbook pattern: one H2 per mirror type, compose snippet + numbered steps + verify block + common issues bullets"

key-files:
  created:
    - docs/docs/runbooks/package-mirrors.md
  modified:
    - docs/mkdocs.yml
    - docs/docs/security/air-gap.md

key-decisions:
  - "devpi already in compose.server.yaml at port 3141 — runbook documents configuration only, no new compose changes needed"
  - "apt-cacher-ng: rm /etc/apt/apt.conf.d/01proxy must be in same RUN layer as apt-get install to avoid proxy persisting in final image"
  - "BaGet: mention Install-PSResource as preferred over Install-Module on PS 7.4+ (PowerShellGet v3 NuGet v3 compatibility)"
  - "PYPI_MIRROR_HOST is hostname:port only (devpi:3141), not a full URL — documented in verify section"

patterns-established:
  - "Package mirror runbook structure: H1 title, 2-sentence intro, H2 per mirror, sub-H3 sections (Enable/Add sidecar, Configure, Seed, Verify, Common issues)"

requirements-completed: [PKG-01, PKG-02, PKG-03]

# Metrics
duration: 2min
completed: 2026-03-29
---

# Phase 84 Plan 02: Package Mirrors Runbook Summary

**From-scratch operator runbook for devpi (PyPI), apt-cacher-ng (APT), and BaGet (PWSH/NuGet) with compose snippets, numbered setup steps, verification commands, and common issue bullets — wired into MkDocs nav and cross-linked from air-gap.md**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-29T14:40:23Z
- **Completed:** 2026-03-29T14:42:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Created `docs/docs/runbooks/package-mirrors.md` covering devpi, apt-cacher-ng, and BaGet with actionable setup procedures
- Wired `Package Mirror Setup: runbooks/package-mirrors.md` into the MkDocs Runbooks nav section
- Inserted cross-link blockquote into `air-gap.md` Package Mirror Setup section pointing operators to the full runbook

## Task Commits

Each task was committed atomically:

1. **Task 1: Write docs/docs/runbooks/package-mirrors.md** - `806a0d6` (feat)
2. **Task 2: Wire MkDocs nav entry and air-gap.md cross-link** - `42f40dc` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `docs/docs/runbooks/package-mirrors.md` - Full package mirrors runbook (215 lines): devpi, apt-cacher-ng, BaGet sections
- `docs/mkdocs.yml` - Added `Package Mirror Setup: runbooks/package-mirrors.md` to Runbooks nav
- `docs/docs/security/air-gap.md` - Added cross-link blockquote in Package Mirror Setup section

## Decisions Made

- devpi: correct URL is `http://devpi:3141/root/pypi/+simple/` — root index `/+simple/` is empty, documented as critical common issue
- apt-cacher-ng: proxy removal must be in same `RUN` layer as install — documented as common issue to prevent proxy persisting in node images
- BaGet: `Install-PSResource` preferred over `Install-Module` on PS 7.4+ — PowerShellGet v2 has partial NuGet v3 compatibility issues
- `PYPI_MIRROR_HOST` environment variable is `hostname:port` format only (e.g. `devpi:3141`), not a full URL — reflected in verify block

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

MkDocs Docker build (`squidfunk/mkdocs-material`) aborted due to missing `swagger-ui-tag` plugin — this is a pre-existing environment issue unrelated to this plan's changes. Fell back to manual verification of the three success criteria (file exists, nav entry present, cross-link present) per plan's fallback instruction.

## Next Phase Readiness

- PKG-01, PKG-02, PKG-03 requirements satisfied — operators have from-scratch runbooks for all three mirror types
- Phase 84 complete — all package repo operator docs delivered
- Ready for Phase 85 (Screenshot Capture) or Phase 86 (Docs Accuracy Validation)

---
*Phase: 84-package-repo-operator-docs*
*Completed: 2026-03-29*

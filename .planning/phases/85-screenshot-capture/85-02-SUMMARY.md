---
phase: 85-screenshot-capture
plan: "02"
subsystem: docs
tags: [documentation, mkdocs, homepage, screenshots, markdown]

# Dependency graph
requires:
  - phase: 85-01
    provides: tools/capture_screenshots.py — the script that populates the screenshot assets this plan references
provides:
  - docs/docs/assets/screenshots/ directory (gitkeep + README)
  - homepage/assets/screenshots/ directory (gitkeep)
  - Screenshot image references embedded in 5 docs pages
  - Homepage "See it in action" showcase section with 4-image grid
  - Removal of outdated puppeteer/dashboard/generate_screenshots.py
affects: [86-docs-accuracy-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Screenshot directories committed via .gitkeep before PNG assets exist — structure-first, populate-later"
    - "Homepage showcase uses existing --axiom-* CSS custom properties — no new design tokens"

key-files:
  created:
    - docs/docs/assets/screenshots/.gitkeep
    - docs/docs/assets/screenshots/README.md
    - homepage/assets/screenshots/.gitkeep
  modified:
    - docs/docs/getting-started/enroll-node.md
    - docs/docs/getting-started/first-job.md
    - docs/docs/feature-guides/foundry.md
    - docs/docs/feature-guides/job-scheduling.md
    - docs/docs/feature-guides/nodes.md
    - homepage/index.html
    - homepage/style.css
  deleted:
    - puppeteer/dashboard/generate_screenshots.py

key-decisions:
  - "Homepage showcase CSS uses --axiom-* design tokens (not generic --bg-alt/--text-muted) — keeps stylesheet consistent with existing dark-slate theme"
  - "Showcase section positioned between mockup-section and pain-points — keeps hero narrative flow intact"
  - "Pre-existing test failures (test_intent_scanner, test_tools, test_lifecycle_enforcement, etc.) are not introduced by this plan — confirmed pre-existing import errors for unrelated modules"

requirements-completed:
  - SCR-02
  - SCR-03

# Metrics
duration: 15min
completed: 2026-03-29
---

# Phase 85 Plan 02: Docs and Homepage Integration Summary

**Screenshot asset directories, docs image references, homepage showcase section, and deletion of the outdated generate_screenshots.py — all 5 tasks completed in 5 atomic commits**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-29T16:10:00Z
- **Completed:** 2026-03-29T16:25:00Z
- **Tasks:** 5
- **Files modified:** 10 (3 created, 7 modified/deleted)

## Accomplishments

- Created `docs/docs/assets/screenshots/` and `homepage/assets/screenshots/` directories with `.gitkeep` and a README explaining how to populate them
- Embedded screenshot image references into 5 docs pages: `enroll-node.md`, `first-job.md`, `foundry.md`, `job-scheduling.md`, `nodes.md`
- Added a "See it in action" showcase section to `homepage/index.html` with a 2×2 grid of 4 key screenshots (dashboard, nodes, jobs, audit), styled with existing `--axiom-*` CSS design tokens
- Deleted `puppeteer/dashboard/generate_screenshots.py` — replaced by `tools/capture_screenshots.py` from Plan 85-01

## Task Commits

Each task was committed atomically:

1. **Task 1: Create screenshot asset directories** - `5a94069` (feat)
2. **Task 2: Getting-started docs — embed screenshots** - `d4a7a89` (docs)
3. **Task 3: Feature guide docs — embed screenshots** - `875600f` (docs)
4. **Task 4: Homepage "See it in action" section** - `82f4820` (feat)
5. **Task 5: Remove outdated generate_screenshots.py** - `fbdd37d` (chore)

## Files Created/Modified

- `docs/docs/assets/screenshots/.gitkeep` — establishes directory in git
- `docs/docs/assets/screenshots/README.md` — explains how to populate screenshots
- `homepage/assets/screenshots/.gitkeep` — establishes directory in git
- `docs/docs/getting-started/enroll-node.md` — added nodes.png and node_detail.png after Step 4
- `docs/docs/getting-started/first-job.md` — added jobs.png and job_detail.png after quick-start completion
- `docs/docs/feature-guides/foundry.md` — added foundry.png between Blueprints and Templates sections
- `docs/docs/feature-guides/job-scheduling.md` — added scheduled_jobs.png after Cron Syntax table
- `docs/docs/feature-guides/nodes.md` — added nodes.png after Node States table
- `homepage/index.html` — new showcase section with 4-image grid
- `homepage/style.css` — .showcase-section, .screenshot-grid, .screenshot-item, .screenshot-caption styles + responsive rule

## Decisions Made

- Used `--axiom-*` CSS custom properties in homepage CSS instead of the generic fallbacks specified in the plan — the existing stylesheet defines `--axiom-surface`, `--axiom-bg`, `--axiom-border`, `--axiom-text-muted` which map cleanly to the intended values and keep the visual language consistent
- Showcase section inserted between the mockup-section and pain-points section (as planned) — no change needed here

## Deviations from Plan

None - plan executed exactly as written (CSS variable names adapted to match existing stylesheet, which is correct behavior not a deviation).

## Issues Encountered

Backend test collection shows 5 pre-existing import errors (`ModuleNotFoundError: No module named 'intent_scanner'`, `'puppeteer.agent_service'`, `'admin_signer'`). These are unrelated to this plan's doc/HTML/CSS changes — confirmed pre-existing. The 86 other tests that collected and passed are unaffected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 85 is now complete. Both plans executed:
- Plan 85-01: `tools/capture_screenshots.py` written and tested
- Plan 85-02: Asset directories, docs references, homepage showcase, old script deleted

**Ready for Phase 86 (Docs Accuracy Validation).** Screenshots can be populated at any time by running `tools/capture_screenshots.py` against a live stack.

---
*Phase: 85-screenshot-capture*
*Completed: 2026-03-29*

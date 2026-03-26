---
phase: 71-deploy-docs-to-github-pages
plan: 01
subsystem: infra
tags: [mkdocs, github-pages, docs, offline-plugin, jekyll]

# Dependency graph
requires: []
provides:
  - docs/site/ removed from git tracking (.gitignore entry added)
  - docs/docs/.nojekyll Jekyll bypass marker
  - mkdocs.yml site_url pointing to https://axiom-laboratories.github.io/axiom/
  - offline plugin made conditional via OFFLINE_BUILD env var
  - Dockerfile sets OFFLINE_BUILD=true to preserve air-gap container behaviour
affects:
  - 71-02 (GitHub Pages deploy workflow depends on clean tracking and correct site_url)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OFFLINE_BUILD env var controls offline plugin — false for GitHub Pages, true for Docker builds"
    - ".nojekyll at docs source root prevents Jekyll processing of MkDocs underscore assets"

key-files:
  created:
    - docs/docs/.nojekyll
  modified:
    - .gitignore
    - docs/mkdocs.yml
    - docs/Dockerfile

key-decisions:
  - "git rm -r --cached docs/site/ untracked 166 build output files; .gitignore entry prevents re-tracking"
  - "offline plugin conditional on OFFLINE_BUILD env var — disabled for GitHub Pages deploy, enabled in Docker"
  - "site_url set to https://axiom-laboratories.github.io/axiom/ for correct relative URL generation on subpath"

patterns-established:
  - "OFFLINE_BUILD pattern: set true in Dockerfile, omit for CI deploys"

requirements-completed: [HOUSE-01, HOUSE-02, CONFIG-01, CONFIG-02, CONFIG-03]

# Metrics
duration: 8min
completed: 2026-03-26
---

# Phase 71 Plan 01: Docs GitHub Pages Prep Summary

**Untracked 166 docs/site/ build files, added .nojekyll marker, and made offline plugin conditional on OFFLINE_BUILD so GitHub Pages builds cleanly while Docker air-gap builds still activate it**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-26T17:13:00Z
- **Completed:** 2026-03-26T17:21:14Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Removed all 166 tracked docs/site/ build output files from git index and gitignored the directory
- Created docs/docs/.nojekyll to prevent GitHub Pages/Jekyll from stripping MkDocs underscore-prefixed assets
- Updated mkdocs.yml: site_url to `https://axiom-laboratories.github.io/axiom/` and offline plugin conditional on `!ENV [OFFLINE_BUILD, false]`
- Patched docs/Dockerfile to set `OFFLINE_BUILD=true` in the mkdocs build step, preserving air-gap container behaviour

## Task Commits

Each task was committed atomically:

1. **Task 1: Untrack docs/site/ and add .gitignore entry** - `9af622c` (chore)
2. **Task 2: Add .nojekyll and update mkdocs.yml** - `6f3a869` (feat)
3. **Task 3: Add OFFLINE_BUILD=true to Dockerfile mkdocs build step** - `f72bedb` (feat)

## Files Created/Modified
- `.gitignore` - Added `docs/site/` block to prevent re-tracking build output
- `docs/docs/.nojekyll` - Empty file; Jekyll bypass marker for GitHub Pages
- `docs/mkdocs.yml` - site_url updated; offline plugin made conditional on OFFLINE_BUILD env var
- `docs/Dockerfile` - mkdocs build step now sets OFFLINE_BUILD=true to activate offline plugin in container

## Decisions Made
- Used `!ENV [OFFLINE_BUILD, false]` pattern so offline plugin is off by default (GitHub Pages) and on in Docker builds — no separate mkdocs config files needed
- Placed .nojekyll in docs/docs/ (the MkDocs source root) so it is copied into the built site by mkdocs and lands at the GitHub Pages root

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Material for MkDocs prints a "Warning from the Material team" banner to stderr about MkDocs 2.0 — this is a theme-level cosmetic message, not an MkDocs WARNING log entry. Build exits 0 with no build warnings under `--strict`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Docs tree is clean: no tracked build output, correct site_url, conditional offline plugin, Dockerfile patched
- Ready for Phase 71-02: GitHub Actions workflow to deploy to GitHub Pages via `mkdocs gh-deploy --force`

---
*Phase: 71-deploy-docs-to-github-pages*
*Completed: 2026-03-26*

## Self-Check: PASSED

- FOUND: docs/docs/.nojekyll
- FOUND: 71-01-SUMMARY.md
- FOUND commit 9af622c: chore(71-01): untrack docs/site/ build output and add .gitignore entry
- FOUND commit 6f3a869: feat(71-01): add .nojekyll marker and update mkdocs.yml for GitHub Pages
- FOUND commit f72bedb: feat(71-01): set OFFLINE_BUILD=true in Dockerfile mkdocs build step

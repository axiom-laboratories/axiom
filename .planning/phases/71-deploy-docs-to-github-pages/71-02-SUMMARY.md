---
phase: 71-deploy-docs-to-github-pages
plan: 02
subsystem: infra
tags: [github-actions, mkdocs, github-pages, docs, openapi]

# Dependency graph
requires:
  - phase: 71-01
    provides: "mkdocs.yml with site_url + OFFLINE_BUILD conditional, .nojekyll, docs/site/ untracked"
provides:
  - "GitHub Actions workflow (.github/workflows/docs-deploy.yml) that auto-deploys docs to GitHub Pages on push to main"
  - "Maintenance script (docs/scripts/regen_openapi.sh) to regenerate openapi.json locally"
affects: [future-docs-changes, ci-pipeline]

# Tech tracking
tech-stack:
  added: [actions/checkout@v4, actions/setup-python@v5, actions/cache@v4, mkdocs gh-deploy]
  patterns: [path-filtered-workflow, weekly-cache-key, working-directory-subdirectory-pattern]

key-files:
  created:
    - .github/workflows/docs-deploy.yml
    - docs/scripts/regen_openapi.sh
  modified: []

key-decisions:
  - "Separate docs-deploy.yml from ci.yml — dedicated workflow file for docs deploys (DEPLOY-02)"
  - "fetch-depth: 0 required for mkdocs gh-deploy to compute git revision dates"
  - "working-directory: docs avoids need for --config-file flag"
  - "Weekly cache key (date +%V) catches privacy plugin asset updates"
  - "openapi.json pre-committed (not regenerated in CI) — regen_openapi.sh is the operator tool"
  - "OFFLINE_BUILD env var NOT set in GH Actions — offline plugin disabled for Pages build"

patterns-established:
  - "Path-filtered workflow: triggers only when docs/** or the workflow file itself changes"
  - "Dummy env vars pattern for FastAPI schema export (sqlite dummy, dummy keys)"

requirements-completed: [DEPLOY-01, DEPLOY-02, MAINT-01]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 71 Plan 02: Deploy Docs to GitHub Pages — Workflow & Maintenance Script Summary

**GitHub Actions workflow deploying MkDocs docs to gh-pages via `mkdocs gh-deploy --force`, plus a local `regen_openapi.sh` script for keeping openapi.json current after API changes**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-26T17:23:09Z
- **Completed:** 2026-03-26T17:25:00Z
- **Tasks:** 2 (+ 1 checkpoint pending human verification)
- **Files modified:** 2

## Accomplishments

- Created `.github/workflows/docs-deploy.yml` — path-filtered workflow that deploys to GitHub Pages whenever `docs/**` changes on main
- Created `docs/scripts/regen_openapi.sh` — executable maintenance script for local openapi.json regeneration using dummy env vars
- Both workflow files (ci.yml and docs-deploy.yml) coexist as separate files, satisfying DEPLOY-02

## Task Commits

Each task was committed atomically:

1. **Task 1: Create docs-deploy.yml GitHub Actions workflow** - `f5151fe` (feat)
2. **Task 2: Create regen_openapi.sh maintenance script** - `ecdffdd` (feat)

## Files Created/Modified

- `.github/workflows/docs-deploy.yml` — GH Actions workflow: push-to-main path filter, git creds, Python 3.12 + pip cache, weekly mkdocs-material cache, `mkdocs gh-deploy --force` from `working-directory: docs`
- `docs/scripts/regen_openapi.sh` — Bash script using dummy DATABASE_URL/ENCRYPTION_KEY/API_KEY to call `puppeteer/scripts/export_openapi.py` and write `docs/docs/api-reference/openapi.json`

## Decisions Made

- `fetch-depth: 0` included — MkDocs Material uses git history to compute `git_revision_date_localized` for page footers; shallow clone would silently produce wrong dates
- `working-directory: docs` used instead of `--config-file` flag — cleaner, consistent with MkDocs Material's own publishing guide
- No `OFFLINE_BUILD` env var in workflow — GitHub Pages build should NOT enable the offline plugin (which bundles all assets for air-gap use); that feature is Docker-container-only
- `regen_openapi.sh` uses dummy env vars so schema export works without a real running database

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**One-time manual step after the `gh-pages` branch is first created by the workflow:**

1. Push a docs change to main (or trigger the workflow manually in GitHub Actions)
2. Go to https://github.com/axiom-laboratories/axiom/settings/pages
3. Source: Deploy from branch → Branch: `gh-pages` / Folder: `/ (root)` → Save
4. Confirm the site loads at https://axiom-laboratories.github.io/axiom/

The automated smoke checks (run by the checkpoint) verify all artifacts are correct before this step.

## Next Phase Readiness

Phase 71 is complete. Human verification confirmed:
- All automated smoke checks passed
- GitHub Pages activated and site confirmed live at https://axiom-laboratories.github.io/axiom/
- Future docs changes to `docs/**` on main will auto-deploy via the docs-deploy.yml workflow
- API schema changes require running `docs/scripts/regen_openapi.sh` then committing the updated openapi.json

---
*Phase: 71-deploy-docs-to-github-pages*
*Completed: 2026-03-26*

---
phase: 80-github-pages-deploy-marketing-homepage
plan: "01"
subsystem: infra
tags: [github-actions, mkdocs, ghp-import, github-pages, ci-cd]

requires: []
provides:
  - "docs-deploy workflow deploys to gh-pages/docs/ subtree via ghp-import prefix mode"
  - "gh-pages root left untouched by docs deploys (prerequisite for marketing homepage coexistence)"
affects: [80-02, marketing-homepage, github-pages]

tech-stack:
  added: [ghp-import (transitively installed via docs/requirements.txt)]
  patterns: ["ghp-import -x docs prefix mode to scope deploys to a subtree"]

key-files:
  created: []
  modified:
    - .github/workflows/docs-deploy.yml
    - docs/mkdocs.yml

key-decisions:
  - "Use ghp-import -n -p -f -x docs site instead of mkdocs gh-deploy --force to restrict deploy scope to docs/ subtree"
  - "Use -x docs (short flag) not --dest-dir docs (does not exist in ghp-import 2.1.0)"
  - "site_url updated to /axiom/docs/ to reflect new canonical path after subtree deploy"

patterns-established:
  - "Subtree deploy pattern: ghp-import -x <subdir> to isolate CI deploy to one directory"

requirements-completed: [MKTG-01]

duration: 1min
completed: 2026-03-27
---

# Phase 80 Plan 01: Update docs-deploy to ghp-import prefix mode Summary

**Switched docs CI from `mkdocs gh-deploy --force` (wipes gh-pages root) to `ghp-import -n -p -f -x docs site` (writes only to docs/ subtree), and updated mkdocs.yml site_url to match the new /axiom/docs/ canonical path**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-27T21:17:43Z
- **Completed:** 2026-03-27T21:18:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced `mkdocs gh-deploy --force` deploy step with explicit `mkdocs build` + `ghp-import -n -p -f -x docs site` in docs-deploy.yml
- Docs deploys now write only to the `docs/` subtree of gh-pages; the root is never touched
- Updated `site_url` in mkdocs.yml from `/axiom/` to `/axiom/docs/` so canonical links and sitemap reflect the new path

## Task Commits

Each task was committed atomically:

1. **Task 1: Update docs-deploy.yml — replace mkdocs gh-deploy with ghp-import prefix deploy** - `130219b` (chore)
2. **Task 2: Update mkdocs.yml site_url to /axiom/docs/** - `12e8440` (chore)

**Plan metadata:** (committed with final docs commit)

## Files Created/Modified
- `.github/workflows/docs-deploy.yml` - Deploy step replaced: `mkdocs build` + `ghp-import -n -p -f -x docs site`
- `docs/mkdocs.yml` - `site_url` updated to `https://axiom-laboratories.github.io/axiom/docs/`

## Decisions Made
- Used `-x docs` (short flag) not `--dest-dir docs` — the long form `--dest-dir` does not exist in ghp-import 2.1.0; the correct long form would be `--prefix docs` but the short `-x` is preferred per plan spec
- `ghp-import` is already installed transitively by `pip install -r docs/requirements.txt` — no new dependency entry needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- gh-pages root is now safe to host a marketing homepage without fear of docs CI overwriting it
- Plan 80-02 (or subsequent plans) can proceed to deploy index.html + assets to gh-pages root
- The docs site will appear at `/axiom/docs/` once the first deploy triggers after this merge

---
*Phase: 80-github-pages-deploy-marketing-homepage*
*Completed: 2026-03-27*

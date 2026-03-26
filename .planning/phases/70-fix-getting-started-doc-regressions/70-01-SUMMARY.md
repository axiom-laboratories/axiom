---
phase: 70-fix-getting-started-doc-regressions
plan: "01"
subsystem: docs
tags: [mkdocs, documentation, ci, getting-started, cold-start]

requires:
  - phase: 67-getting-started-documentation
    provides: install.md and enroll-node.md getting-started docs with tab structure
  - phase: 69-fix-ci-release-pipeline-version-pinning-and-semver-tags
    provides: ci.yml job structure pattern to follow
provides:
  - Correct d['token'] extraction in enroll-node.md CLI tab (was silently producing empty string)
  - Cold-Start Install tab variants in install.md Steps 3 and 4 with correct compose command and port 8443 URL
  - 9-item EE feature list in install.md matching the JSON block below it
  - Unauthenticated curl for GET /api/features (removed unnecessary Bearer token acquisition)
  - d['token'] and localhost URLs in compose.cold-start.yaml quick-start comments
  - docs CI job in ci.yml running mkdocs build --strict on every PR and push
affects: [future-doc-updates, getting-started-flow, ci-pipeline]

tech-stack:
  added: []
  patterns:
    - "mkdocs --strict CI gate: docs job in ci.yml catches anchor and extension regressions before merge"
    - "Cold-Start tab grouping: === 'Cold-Start Install' / === 'Server Install' tab pair pattern in install.md"

key-files:
  created: []
  modified:
    - docs/docs/getting-started/enroll-node.md
    - docs/docs/getting-started/install.md
    - puppeteer/compose.cold-start.yaml
    - .github/workflows/ci.yml

key-decisions:
  - "d['token'] is the correct field name for POST /admin/generate-token response — d.get('enhanced_token', d.get('join_token', '')) was silently returning empty string"
  - "GET /api/features is unauthenticated — no Bearer token acquisition block needed in docs"
  - "Cold-Start tabs added to Steps 3 and 4 matching exact tab label from Step 2 for tab grouping"

patterns-established:
  - "Tab label grouping: use === 'Server Install' / === 'Cold-Start Install' consistently across install.md steps"

requirements-completed: [DOCS-01, DOCS-03, DOCS-08]

duration: 2min
completed: 2026-03-26
---

# Phase 70 Plan 01: Fix Getting-Started Doc Regressions Summary

**Six surgical doc fixes: correct d['token'] extraction in enroll-node.md CLI tab, add Cold-Start Install tabs in install.md Steps 3-4, expand EE feature list to 9 items, remove unnecessary auth from /api/features curl, update compose.cold-start.yaml comments, and add mkdocs --strict CI gate**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-26T15:38:59Z
- **Completed:** 2026-03-26T15:41:43Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Fixed silently-broken JOIN_TOKEN extraction in enroll-node.md CLI tab: `d.get('enhanced_token', d.get('join_token', ''))` was returning empty string; replaced with `d['token']` matching actual API response field
- Added Cold-Start Install tab variants to install.md Steps 3 and 4 so GHCR Pull users land on correct `compose.cold-start.yaml --env-file .env up -d` command and `https://localhost:8443/` verify URL
- Added `docs` CI job to ci.yml running `mkdocs build --strict` — prevents future anchor/extension regressions from landing on main
- Expanded EE feature list from 5 to 9 items to match the JSON block directly below it; removed unnecessary Bearer token auth block from GET /api/features CLI tab; updated compose.cold-start.yaml comment URLs from 172.17.0.1 to localhost

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix enroll-node.md token field and update compose.cold-start.yaml comments** - `f1cf90a` (fix)
2. **Task 2: Add Cold-Start tabs to install.md Steps 3-4, fix EE feature list, remove auth from /api/features CLI tab** - `33bae2b` (fix)
3. **Task 3: Add docs CI job to ci.yml** - `5675d4e` (chore)

## Files Created/Modified

- `docs/docs/getting-started/enroll-node.md` - Fixed CLI tab token extraction (`d['token']`); updated prose "enhanced_token field" to "token field"
- `docs/docs/getting-started/install.md` - Added Cold-Start Install tabs in Steps 3 and 4; expanded EE feature list to 9 items; removed auth block from GET /api/features CLI tab
- `puppeteer/compose.cold-start.yaml` - Updated quick-start comment: `d['token']`, `https://localhost:8443`, `https://localhost:8001`
- `.github/workflows/ci.yml` - Added `docs` job with `mkdocs build --strict` after `docker-validate`

## Decisions Made

- `d['token']` is the authoritative field name per `main.py` line 1544 (`return {"token": b64_token}`) — the previous fallback chain was silently returning empty string
- GET /api/features is unauthenticated by design — removing the TOKEN acquisition block simplifies the UX and reflects actual API behaviour
- Tab labels must match Step 2 exactly (`=== "Server Install"` / `=== "Cold-Start Install"`) for MkDocs tab grouping to work correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 70 complete — all six regression items from v14.1 milestone audit (MISS-01, FLOW-01) resolved
- mkdocs build --strict now passes and is enforced on every PR via CI
- No blockers for v14.1 release

---
*Phase: 70-fix-getting-started-doc-regressions*
*Completed: 2026-03-26*

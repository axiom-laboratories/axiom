---
phase: 21-api-reference-dashboard-integration
plan: "01"
subsystem: api
tags: [openapi, fastapi, mkdocs, swagger-ui, docker, documentation]

# Dependency graph
requires:
  - phase: 20-container-infrastructure-routing
    provides: docs container (nginx), MkDocs build pipeline, compose.server.yaml docs service
provides:
  - export_openapi.py — generates openapi.json from FastAPI app without a running server
  - All 102 FastAPI routes tagged with 17 meaningful groups (no default-only paths)
  - docs/api-reference/index.md — Swagger UI page with bundled assets (no CDN)
  - docs/Dockerfile updated — repo-root build context, exports openapi.json at build time
  - Built image at localhost/master-of-puppets-docs:v1 with openapi.json embedded
affects: [23-docs-nav-content, api-consumers, any-phase-modifying-main.py]

# Tech tracking
tech-stack:
  added: [mkdocs-swagger-ui-tag==0.8.0]
  patterns:
    - OpenAPI schema generated at Docker build time via app.openapi() import (no server)
    - All FastAPI routes tagged for meaningful Swagger UI grouping
    - PYTHONPATH=/tmp pattern for importing agent_service in builder stage

key-files:
  created:
    - puppeteer/scripts/export_openapi.py
    - docs/docs/api-reference/index.md
    - puppeteer/tests/test_openapi_export.py
  modified:
    - puppeteer/agent_service/main.py (110 routes tagged)
    - docs/Dockerfile (repo-root context, FastAPI deps, export step)
    - docs/requirements.txt (added mkdocs-swagger-ui-tag)
    - docs/mkdocs.yml (added swagger-ui-tag plugin)
    - puppeteer/compose.server.yaml (docs build context changed to ..)

key-decisions:
  - "Use postgresql+asyncpg dummy URL in Dockerfile (asyncpg in requirements.txt, aiosqlite not installed in builder)"
  - "API_KEY env var required at import time in security.py — must be set to dummy value in builder"
  - "PYTHONPATH=/tmp used to resolve agent_service from /tmp when export_openapi.py is at /tmp/"
  - "validatorUrl=none in swagger-ui tag prevents external calls to validator.swagger.io"
  - "17 tag groups established: Admin, Alerts & Webhooks, Artifacts, Audit Log, Authentication, Execution Records, Foundry, Headless Automation, Job Definitions, Jobs, Node Agent, Nodes, Service Principals, Signatures, Smelter Registry, System, User Management"

patterns-established:
  - "OpenAPI export pattern: set dummy DATABASE_URL (asyncpg format) + ENCRYPTION_KEY + API_KEY, PYTHONPATH=/tmp, python /tmp/export_openapi.py <output>"
  - "All new routes in main.py MUST include tags= parameter — zero tolerance for default-tagged paths"

requirements-completed: [APIREF-01, APIREF-02, APIREF-03]

# Metrics
duration: 11min
completed: 2026-03-16
---

# Phase 21 Plan 01: OpenAPI Export Pipeline Summary

**All 102 FastAPI routes tagged across 17 groups, openapi.json auto-generated at Docker build time, Swagger UI rendered at /docs/api-reference/ with bundled assets and no CDN dependencies**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-16T22:28:49Z
- **Completed:** 2026-03-16T22:39:56Z
- **Tasks:** 2 of 3 complete (Task 3 is checkpoint:human-verify)
- **Files modified:** 8

## Accomplishments

- Tagged all 110 previously untagged routes in main.py — 0 default-only paths, 17 meaningful groups
- Created export_openapi.py: exports 102-path schema using app.openapi() import without a server
- Updated docs/Dockerfile to repo-root build context, installs FastAPI deps, generates openapi.json before mkdocs build
- docker compose build docs succeeds end-to-end; openapi.json at /usr/share/nginx/html/api-reference/openapi.json in image
- Added mkdocs-swagger-ui-tag plugin; /docs/api-reference/ page renders Swagger UI with bundled assets

## Task Commits

Each task was committed atomically:

1. **TDD RED — failing tests** - `184093b` (test)
2. **Task 1: Tag routes + create export_openapi.py** - `426a4d2` (feat)
3. **Task 2: Wire into Dockerfile + swagger-ui-tag** - `a700e47` (feat)

## Files Created/Modified

- `puppeteer/scripts/export_openapi.py` — exports OpenAPI schema without running server
- `puppeteer/tests/test_openapi_export.py` — TDD tests (4 passing)
- `puppeteer/agent_service/main.py` — 110 route decorators tagged across 17 groups
- `docs/Dockerfile` — repo-root build context, FastAPI deps, openapi.json generation
- `docs/requirements.txt` — added mkdocs-swagger-ui-tag==0.8.0
- `docs/mkdocs.yml` — added swagger-ui-tag plugin
- `docs/docs/api-reference/index.md` — Swagger UI page with validatorUrl=none
- `puppeteer/compose.server.yaml` — docs build context changed to repo root

## Decisions Made

- **postgresql+asyncpg dummy URL**: `aiosqlite` is not in puppeteer/requirements.txt but `asyncpg` is — use postgres URL format so the builder stage can import db.py without ModuleNotFoundError
- **API_KEY dummy value required**: security.py calls `sys.exit(1)` at module level if API_KEY is unset — must be provided as dummy in Dockerfile RUN env
- **PYTHONPATH=/tmp**: when export script is copied to /tmp/export_openapi.py, its `sys.path.insert(0, "..")` resolves to "/" — PYTHONPATH=/tmp ensures `from agent_service.main import app` finds /tmp/agent_service
- **validatorUrl=none**: prevents Swagger UI from POSTing to validator.swagger.io on each page load, maintaining air-gap requirement

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing API_KEY env var caused sys.exit(1) at Docker build time**
- **Found during:** Task 2 (Docker build verification)
- **Issue:** security.py reads `os.environ["API_KEY"]` at module import time and calls `sys.exit(1)` if not set — the plan's dummy env vars (DATABASE_URL + ENCRYPTION_KEY only) were insufficient
- **Fix:** Added `API_KEY=dummy-build-key` to Dockerfile RUN env vars and updated test DUMMY_ENV and script docstring
- **Files modified:** docs/Dockerfile, puppeteer/scripts/export_openapi.py, puppeteer/tests/test_openapi_export.py
- **Verification:** Docker build succeeded after fix
- **Committed in:** a700e47 (Task 2 commit)

**2. [Rule 3 - Blocking] aiosqlite not available in Docker builder stage**
- **Found during:** Task 2 (Docker build verification, second attempt)
- **Issue:** Plan specified `sqlite+aiosqlite:///./dummy.db` as DATABASE_URL but `aiosqlite` is not in puppeteer/requirements.txt and was not installed in the builder stage
- **Fix:** Changed DATABASE_URL to `postgresql+asyncpg://dummy:dummy@localhost/dummy` — asyncpg IS in requirements.txt and the engine creation succeeds without a live connection at import time
- **Files modified:** docs/Dockerfile
- **Verification:** Docker build succeeded; openapi.json at /usr/share/nginx/html/api-reference/openapi.json
- **Committed in:** a700e47 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for Docker build to succeed. The plan's interfaces section mentioned aiosqlite as the dummy URL but the builder stage only has requirements.txt packages installed — asyncpg is the correct choice.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Next Phase Readiness

- Task 3 (checkpoint:human-verify) is pending user browser verification of /docs/api-reference/
- Container is started: `cd puppeteer && docker compose -f compose.server.yaml up -d docs`
- URL to verify: https://dev.master-of-puppets.work/docs/api-reference/
- After approval, the plan is complete and Phase 21 Plan 02 can proceed

---
*Phase: 21-api-reference-dashboard-integration*
*Completed: 2026-03-16*

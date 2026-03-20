---
phase: 36-cython-so-build-pipeline
plan: "03"
subsystem: infra
tags: [cython, devpi, docker, fastapi, sqlalchemy, asyncpg, wheel, smoke-test]

requires:
  - phase: 36-02
    provides: "12 compiled axiom-ee wheels in wheelhouse/ and uploaded to devpi root/dev index"

provides:
  - "Containerfile.server with conditional EE wheel install via EE_INSTALL ARG + flexible DEVPI_HOST"
  - "devpi service in compose.server.yaml with devpi-data volume"
  - "BUILD-05 gate: test_compiled_wheel.py smoke test passing (CE all-false, EE all-true, /api/blueprints 200)"
  - "axiom-ee Cython compatibility fixes: async DDL via run_sync, Annotated params for FastAPI routers"

affects:
  - "37-licence-validation"

tech-stack:
  added:
    - "devpi (muccg/devpi:latest) — local PyPI server for compiled wheel distribution"
    - "test_compiled_wheel.py — standalone docker compose smoke test (port 8002)"
  patterns:
    - "EE_INSTALL=1 build arg + DEVPI_HOST for configurable pip trusted-host in Containerfile"
    - "Standalone minimal compose file generated at test time (avoids compose list-merge port conflicts)"
    - "Annotated[type, Query()/Header()] pattern required for FastAPI params in Cython-compiled code"
    - "async with engine.begin() as conn: await conn.run_sync(metadata.create_all) — correct async DDL with asyncpg"

key-files:
  created:
    - "~/Development/mop_validation/scripts/test_compiled_wheel.py — BUILD-05 CE+EE compiled wheel smoke test"
  modified:
    - ".worktrees/axiom-split/puppeteer/compose.server.yaml — devpi service (task 1, prior checkpoint)"
    - ".worktrees/axiom-split/puppeteer/Containerfile.server — EE_INSTALL ARG + DEVPI_HOST ARG"
    - "~/Development/axiom-ee/ee/plugin.py — async DDL fix (sync_engine → run_sync via AsyncConnection)"
    - "~/Development/axiom-ee/ee/foundry/router.py — Annotated Query params (Cython compat)"
    - "~/Development/axiom-ee/ee/triggers/router.py — Annotated Header param (Cython compat)"

key-decisions:
  - "Standalone compose file generated at test time (not override) — docker compose list merge is additive, cannot remove ports via override"
  - "DEVPI_HOST ARG added to Containerfile.server — docker build containers cannot resolve compose service hostnames; need Docker bridge IP (172.17.0.1) for local devpi"
  - "async with engine.begin() as conn: await conn.run_sync() replaces sync_engine.create_all() — asyncpg's sync bridge raises greenlet_spawn error when called from asyncio coroutine"
  - "Annotated[type, Query()/Header()] replaces param=Query()/Header() defaults — Cython cannot use FastAPI FieldInfo objects as default argument values in compiled .so"
  - "Wheel rebuilt 3 times during smoke test execution (3 bug fixes discovered only at runtime in Alpine container)"

requirements-completed: [BUILD-05]

duration: 100min
completed: 2026-03-20
---

# Phase 36 Plan 03: Compiled Wheel CE+EE Smoke Test Summary

**axiom-ee 0.1.0 compiled .so wheel passes full CE+EE smoke test — all 8 features True, /api/blueprints 200, zero .py source in installed package**

## Performance

- **Duration:** ~100 min (includes 3 wheel rebuilds for Cython runtime bug fixes)
- **Started:** 2026-03-20T14:16Z
- **Completed:** 2026-03-20T14:49Z
- **Tasks:** 2 (task 1 from prior checkpoint + task 2 this session)
- **Files modified:** 5 (Containerfile.server, compose.server.yaml, plugin.py, foundry/router.py, triggers/router.py) + 1 created (test_compiled_wheel.py)

## Accomplishments

- Containerfile.server updated with `EE_INSTALL` and `DEVPI_HOST` build args enabling conditional axiom-ee install from devpi
- devpi service running on port 3141 with all 12 wheels uploaded
- BUILD-05 gate test passes: CE mode returns all 8 flags False; EE compiled mode returns all 8 flags True; `/api/blueprints` returns 200; no `.py` source in installed package
- Three Cython runtime bugs in axiom-ee fixed that were invisible in pure-Python unit tests but surfaced under Alpine/asyncpg deployment

## Task Commits

1. **Task 1: devpi service + EE_INSTALL ARG** — `5ffa469` (feat, axiom-split) + `e1b949e` (axiom-ee)
2. **Checkpoint: devpi bootstrap** — done by user
3. **Task 2: DEVPI_HOST fix** — `d9b8238` (fix, axiom-split worktree)
4. **Task 2: axiom-ee Cython fixes** — `dfb569c` (fix, axiom-ee repo)
5. **Task 2: smoke test** — `54e93f9` (feat, mop_validation repo)

## Files Created/Modified

- `~/Development/mop_validation/scripts/test_compiled_wheel.py` — BUILD-05 smoke test; CE/EE validation; source check; port isolation via standalone minimal compose on :8002
- `.worktrees/axiom-split/puppeteer/Containerfile.server` — added `ARG DEVPI_HOST=devpi` and `--trusted-host "${DEVPI_HOST}"` for configurable pip trust
- `.worktrees/axiom-split/puppeteer/compose.server.yaml` — devpi service on :3141 with devpi-data volume (task 1)
- `~/Development/axiom-ee/ee/plugin.py` — async DDL: `async with engine.begin() as conn: await conn.run_sync(EEBase.metadata.create_all)`
- `~/Development/axiom-ee/ee/foundry/router.py` — `Annotated[Optional[str], Query()]` = None pattern for capability-matrix endpoint
- `~/Development/axiom-ee/ee/triggers/router.py` — `Annotated[str, Header()]` pattern for fire_automation_trigger

## Decisions Made

- **Standalone compose vs override**: Docker compose list merging is additive — `ports: []` in an override file does not remove existing port bindings from the base file. Generated a minimal standalone compose file at test time instead.
- **DEVPI_HOST ARG**: `docker build` runs in an isolated network; the compose service hostname `devpi` is not resolvable. The Docker bridge gateway IP (172.17.0.1) is accessible from build containers. Added `DEVPI_HOST` ARG to Containerfile.server so both production (hostname `devpi`) and test builds (IP `172.17.0.1`) work.
- **AsyncEngine DDL pattern**: `engine.sync_engine.create_all()` from an asyncio coroutine with asyncpg raises `greenlet_spawn has not been called`. The `run_sync()` method is on `AsyncConnection`, not `AsyncEngine`. Correct pattern: `async with engine.begin() as conn: await conn.run_sync(metadata.create_all)`.
- **Annotated FastAPI params in Cython**: Cython-compiled extensions cannot use FastAPI `FieldInfo` objects (`Query(...)`, `Header(...)`) as function default argument values — they're evaluated during C extension module initialization where the Python runtime context is different. Using `Annotated[type, Query()]` moves the FieldInfo to a type annotation (evaluated lazily by FastAPI) rather than as a default value.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] DEVPI_HOST ARG for docker build trusted-host**
- **Found during:** Task 2 (smoke test EE build)
- **Issue:** Containerfile.server had `--trusted-host devpi` hardcoded; when DEVPI_URL overridden to `172.17.0.1:3141` for build-time access, pip still failed SSL trust check against IP
- **Fix:** Added `ARG DEVPI_HOST=devpi` and changed `--trusted-host "${DEVPI_HOST}"` in Containerfile.server
- **Files modified:** `.worktrees/axiom-split/puppeteer/Containerfile.server`
- **Committed in:** d9b8238

**2. [Rule 1 - Bug] EE plugin DDL greenlet error with asyncpg**
- **Found during:** Task 2 (smoke test EE validation, first run)
- **Issue:** `engine.sync_engine.create_all()` from asyncio coroutine raised `greenlet_spawn has not been called` — asyncpg sync bridge incompatible with asyncio event loop
- **Fix:** `async with engine.sync_engine.begin()` → `async with engine.begin() as conn: await conn.run_sync(EEBase.metadata.create_all)` — wrong method first (run_sync not on AsyncEngine), corrected to AsyncConnection.run_sync
- **Files modified:** `~/Development/axiom-ee/ee/plugin.py`
- **Committed in:** dfb569c

**3. [Rule 1 - Bug] Cython default arg incompatibility for Query/Header params**
- **Found during:** Task 2 (smoke test EE validation, second run)
- **Issue:** `TypeError: Expected str, got Query` and `Expected str, got Header` — Cython-compiled router modules fail to initialize when FastAPI FieldInfo objects used as function default arguments
- **Fix:** Changed `param: Optional[str] = Query(None)` to `param: Annotated[Optional[str], Query()] = None` in foundry/router.py and triggers/router.py
- **Files modified:** `~/Development/axiom-ee/ee/foundry/router.py`, `~/Development/axiom-ee/ee/triggers/router.py`
- **Committed in:** dfb569c

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs)
**Impact on plan:** All fixes required for compiled wheel correctness. The Cython bugs (#2, #3) were invisible in pure-Python unit tests (Phase 35) and only surfaced at runtime in the Alpine/asyncpg production environment. These are important Cython compatibility rules documented for future EE development.

## Issues Encountered

- **Docker compose port merge is additive**: Spent 3 iterations trying override files before discovering compose list merges cannot remove ports. Solution: generate complete standalone compose file.
- **3 wheel rebuilds**: Each Cython bug required a full cibuildwheel rebuild (~90s each) plus devpi re-upload. The `volatile=True` index flag on devpi allowed re-upload without version bumping.

## Next Phase Readiness

- Phase 36 gate test (BUILD-05) is passing — compiled .so wheel installs correctly and produces identical CE+EE behaviour
- axiom-ee Cython compatibility patterns documented — future EE router development must use `Annotated[type, Query()]` not `param=Query()` defaults
- Phase 37 (Licence Validation + Docs + Docker Hub) can proceed
- All 12 axiom-ee 0.1.0 wheels remain in devpi; only the cp312-musllinux wheel was rebuilt (matches Alpine agent container)
- The remaining 11 wheels in devpi still contain the old bugs — rebuild all wheels before production distribution (Phase 37 task)

---
*Phase: 36-cython-so-build-pipeline*
*Completed: 2026-03-20*

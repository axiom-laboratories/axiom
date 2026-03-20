---
phase: 34-ce-baseline-fixes
plan: "01"
subsystem: api
tags: [fastapi, ee-split, stub-routers, importlib, entry-points]

# Dependency graph
requires: []
provides:
  - "_mount_ce_stubs() helper in ee/__init__.py mounting 6 stub routers (402 for all EE routes on CE install)"
  - "importlib.metadata replaces deprecated pkg_resources for EE plugin discovery"
  - "auth_ext.py now has stubs for reset-password and force-password-change sub-routes"
affects:
  - 35-private-ee-repo-plugin-wiring

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_mount_ce_stubs() pattern: single helper called in both CE code paths (no-plugin else + except handler)"
    - "Lazy imports inside _mount_ce_stubs() avoid import-time circular dependency risk"

key-files:
  created: []
  modified:
    - ".worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py"
    - ".worktrees/axiom-split/puppeteer/agent_service/ee/interfaces/auth_ext.py"

key-decisions:
  - "importlib.metadata.entry_points(group='axiom.ee') replaces deprecated pkg_resources.iter_entry_points() in load_ee_plugins()"
  - "_mount_ce_stubs() calls lazy imports inside the function body to avoid circular imports at module load time"
  - "Only 6 stub routers in _mount_ce_stubs() — rbac.py and resource_limits.py are not router stubs"

patterns-established:
  - "_mount_ce_stubs pattern: CE mode path calls a single helper that mounts all EE stub routers"

requirements-completed:
  - GAP-01
  - GAP-02

# Metrics
duration: 1min
completed: 2026-03-19
---

# Phase 34 Plan 01: CE Stub Router Mounting + importlib.metadata Fix Summary

**CE installs now return HTTP 402 on all EE routes via _mount_ce_stubs() helper, and pkg_resources replaced with importlib.metadata for EE plugin discovery**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-19T20:07:01Z
- **Completed:** 2026-03-19T20:07:58Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added two missing PATCH sub-route stubs (`reset-password`, `force-password-change`) to `auth_ext_stub_router` in `auth_ext.py`
- Replaced deprecated `pkg_resources.iter_entry_points()` with `importlib.metadata.entry_points(group="axiom.ee")` (GAP-02)
- Added `_mount_ce_stubs(app)` helper that mounts all 6 stub routers, called in both CE code paths: the no-plugin `else` branch and the `except` handler (GAP-01)
- All EE routes now return 402 (not 404) on a CE-only install

## Task Commits

Each task was committed atomically:

1. **Task 1: Audit and complete stub routers in auth_ext.py** - `e6047fc` (feat)
2. **Task 2: Fix load_ee_plugins() — importlib.metadata + _mount_ce_stubs()** - `d7503c5` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `.worktrees/axiom-split/puppeteer/agent_service/ee/interfaces/auth_ext.py` — Added `PATCH /admin/users/{username}/reset-password` and `PATCH /admin/users/{username}/force-password-change` stubs returning 402
- `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — Added `_mount_ce_stubs()` helper; replaced `pkg_resources` with `importlib.metadata`; `_mount_ce_stubs(app)` called in both CE paths

## Decisions Made

- `importlib.metadata.entry_points(group="axiom.ee")` replaces deprecated `pkg_resources` — `importlib.metadata` is stdlib since Python 3.8, no extra dependency needed
- Imports inside `_mount_ce_stubs()` are lazy (inside function body) to avoid import-time circular dependency risk when the module loads
- Only 6 stub routers are mounted (foundry, audit, webhooks, triggers, auth_ext, smelter) — `rbac.py` and `resource_limits.py` are not router stubs

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- GAP-01 and GAP-02 closed — Phase 35 (private EE repo + plugin wiring) can begin EE router work
- All 6 stub routers are wired and will serve 402 on any CE install
- `auth_ext_stub_router` coverage is now complete (all user sub-routes present)

---
*Phase: 34-ce-baseline-fixes*
*Completed: 2026-03-19*

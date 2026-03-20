---
phase: 35-private-ee-repo-plugin-wiring
plan: "04"
subsystem: api
tags: [fastapi, ee-plugin, async, sqlalchemy, audit]

# Dependency graph
requires:
  - phase: 35-03
    provides: EE plugin interface (EEPlugin.register async), ee/interfaces stubs

provides:
  - async def load_ee_plugins in ee/__init__.py — EE plugin register() properly awaited
  - await load_ee_plugins call in main.py lifespan — coroutine no longer silently discarded
  - deps.audit() works in EE mode — Base.metadata guard removed, try/except handles CE no-op

affects:
  - 35-05 (wave 5 — any further EE wiring or compilation work)
  - 36-build-pipeline (Cython build assumes correct async contract is established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - async EE plugin loader — load_ee_plugins is now async, enabling awaited register() calls
    - try/except-only audit guard — no metadata inspection, works across CE and EE metadata registries

key-files:
  created: []
  modified:
    - .worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py
    - .worktrees/axiom-split/puppeteer/agent_service/main.py
    - .worktrees/axiom-split/puppeteer/agent_service/deps.py

key-decisions:
  - "load_ee_plugins made async so EEPlugin.register() (which is async) can be properly awaited — without this, register() silently returned a coroutine object making EEContext truthy in CE mode"
  - "Base.metadata.tables guard removed from deps.audit() — AuditLog is registered in EEBase.metadata, not Base.metadata; the guard was a permanent no-op even when EE is installed"
  - "try/except is the sole CE/EE boundary in audit() — if the table exists the INSERT works; if not, the exception is silently swallowed"

patterns-established:
  - "Async EE plugin contract: load_ee_plugins is async def, awaits plugin.register(ctx), main.py lifespan awaits load_ee_plugins"
  - "Metadata-agnostic audit: use raw SQL INSERT + try/except, never inspect Base.metadata.tables to detect EE presence"

requirements-completed:
  - EE-05
  - EE-06

# Metrics
duration: 8min
completed: 2026-03-19
---

# Phase 35 Plan 04: Async EE Plugin Loader + Metadata-Agnostic Audit Summary

**load_ee_plugins converted to async def with awaited plugin.register(), and deps.audit() guard replaced with try/except-only pattern that works across both CE and EE metadata registries**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-19T21:38:21Z
- **Completed:** 2026-03-19T21:46:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Made `load_ee_plugins()` async so `EEPlugin.register(ctx)` is properly awaited — previously the coroutine was discarded, making the EEContext object truthy in CE mode and silently breaking all feature flags
- Updated `main.py` lifespan to `await load_ee_plugins(app, engine)` — the function is called inside an `async def lifespan`, so the `await` is valid
- Removed `Base.metadata.tables` guard from `deps.audit()` — AuditLog lives in EEBase.metadata, not Base.metadata; guard caused audit to permanently no-op even with EE installed
- CE pytest gate confirmed green at both commits: 27 passed, 2 skipped, 0 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Make load_ee_plugins async + fix main.py await** - `a2ce72d` (feat)
2. **Task 2: Fix deps.audit() guard for EEBase-registered AuditLog** - `d4c6e41` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — `def load_ee_plugins` -> `async def load_ee_plugins`; `plugin.register(ctx)` -> `await plugin.register(ctx)`
- `.worktrees/axiom-split/puppeteer/agent_service/main.py` — `load_ee_plugins(app, engine)` -> `await load_ee_plugins(app, engine)` in lifespan
- `.worktrees/axiom-split/puppeteer/agent_service/deps.py` — removed `from .db import Base` + `if "audit_log" not in Base.metadata.tables: return` guard from `audit()`; retained `try/except` as sole CE no-op mechanism

## Decisions Made

- `require_permission()` in `deps.py` still retains a `Base.metadata.tables.get("role_permissions")` reference — this is correct because `RolePermission` IS in CE Base.metadata (it's a CE RBAC table). Only the `audit()` function guard was wrong.
- No change to `EEContext` dataclass or `_mount_ce_stubs()` — those remain correct.

## Deviations from Plan

None — plan executed exactly as written.

The plan's verification script `grep -c "Base.metadata.tables" deps.py` would return 1 (not 0) because `require_permission()` legitimately uses `Base.metadata.tables.get("role_permissions")`. This is a false positive in the verification spec; the intent (removing the guard only from `audit()`) was achieved.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Async plugin contract established: EE plugins can now define `async def register(ctx)` and it will be properly awaited
- audit() will write entries in EE mode — no further changes needed to the deps module for EE audit support
- Phase 35 wave 5 (if any) or Phase 36 (Cython build) can proceed — the CE-alone gate is green

## Self-Check: PASSED

- FOUND: .planning/phases/35-private-ee-repo-plugin-wiring/35-04-SUMMARY.md
- FOUND: a2ce72d (feat: make load_ee_plugins async, await in main.py lifespan)
- FOUND: d4c6e41 (fix: remove Base.metadata guard in deps.audit())
- FOUND: a2c3c50 (docs: plan metadata commit)

---
*Phase: 35-private-ee-repo-plugin-wiring*
*Completed: 2026-03-19*

# Phase 35: Private EE Repo + Plugin Wiring - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the private `axiom-ee` Python package at `~/Development/axiom-ee/` with a working `EEPlugin` class that wires into CE via `entry_points`. Migrate the 7 EE router implementations from the CE worktree into the private repo. Validate CE-alone and CE+EE combined installs both work correctly. Publish the `axiom-ee` stub wheel to PyPI to reserve the name. No licence validation (Phase 37), no Cython compilation (Phase 36).

</domain>

<decisions>
## Implementation Decisions

### DB table strategy
- EE defines its own `EEBase = declarative_base()` — completely separate from CE's `Base`
- `EEPlugin.register()` calls `EEBase.metadata.create_all(engine.sync_engine)` to create EE tables — uses `engine.sync_engine` (the wrapped sync engine inside CE's AsyncEngine)
- CE's startup `create_all` never touches EE models — clean isolation for CE-alone installs
- Standalone EE tables only in Phase 35 — no ForeignKey references back to CE tables (joins happen at query time via shared engine)
- Phase 35 includes real EE DB models per router, not placeholder scaffolding — the actual tables that the compiled `.so` will use in Phase 36

### axiom-ee package layout
- Nested per-feature structure: `ee/{feature}/` subdirectories, each containing `router.py`, `models.py`, `services.py` as needed
  - e.g. `ee/foundry/router.py`, `ee/foundry/models.py`
- `ee/plugin.py` contains `EEPlugin` class (entry_point: `ee.plugin:EEPlugin`)
- `ee/db.py` or `ee/base.py` contains `EEBase = declarative_base()`
- All 7 router files use absolute imports from CE: `from agent_service.db import ...`, `from agent_service.models import ...`, `from agent_service.deps import require_permission`
- Migrate the full EE router implementations from `.worktrees/axiom-split/puppeteer/agent_service/ee/routers/` — do not rewrite from scratch
- Convert all relative imports (`from ...db import ...`) to absolute imports (`from agent_service.db import ...`) during migration
- repo location: `~/Development/axiom-ee/` — sibling to `master_of_puppets/`, separate git repo

### register() async pattern
- `load_ee_plugins(app, engine)` in CE's `ee/__init__.py` changed to `async def`
- Callee in `main.py` lifespan updated: `app.state.ee = await load_ee_plugins(app, engine)`
- `EEPlugin.register(ctx)` is `async def register(self, ctx: EEContext) -> None`
- Operation order inside `register()`:
  1. `EEBase.metadata.create_all(engine.sync_engine)` — tables created before routes go live
  2. `app.include_router(...)` for each EE router
  3. Set EEContext feature flags only for routers that successfully mounted — `ctx.{feature} = True` per router

### PyPI stub wheel
- The axiom-ee stub is the same repo at version `0.1.0.dev0` — not a separate stub project
- Stub contains a loadable no-op `EEPlugin`: real entry_point wired, `register()` sets all flags to True but mounts no routers and creates no tables (useful for wiring smoke tests without full EE data)
- Publish to test.pypi.org first to validate build + upload, then publish to pypi.org to reserve the name
- The `axiom-laboratories` org on PyPI already has Trusted Publisher configured (from Phase 10)

### Claude's Discretion
- Exact directory structure inside each `ee/{feature}/` (whether all features need all three files or just router.py)
- Whether `EEPlugin.__init__(self, app, engine)` stores app/engine as instance attributes or receives them only in `register()`
- Error handling strategy if a single router fails to mount in `register()` (log + continue vs raise)
- Whether to add a `__all__` in `ee/__init__.py`
- Exact table schemas for EE DB models (these match the existing EE router logic)

</decisions>

<specifics>
## Specific Ideas

- The existing worktree router files are at `.worktrees/axiom-split/puppeteer/agent_service/ee/routers/`: `foundry_router.py`, `audit_router.py`, `auth_ext_router.py`, `smelter_router.py`, `trigger_router.py`, `webhook_router.py`, `users_router.py` — 7 files to migrate
- `EEContext` dataclass (in CE's `ee/__init__.py`) has 8 flags: `foundry`, `audit`, `webhooks`, `triggers`, `rbac`, `resource_limits`, `service_principals`, `api_keys`
- The CE worktree `_mount_ce_stubs()` currently mounts 6 stub routers — the EE register() needs to cover all 7 router + correctly map to the 8 flags
- Success criteria: `python -c "import ee.plugin"` works without importing `agent_service.main` — the EEPlugin import chain must not trigger CE's app startup
- Success criteria: `GET /api/features` returns all 8 feature flags as `true` after CE+EE install

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ee/__init__.py` (CE worktree): `EEContext` dataclass, `load_ee_plugins()`, `_mount_ce_stubs()` — `load_ee_plugins` needs `async def` change, rest stays
- `ee/routers/*.py` (CE worktree): 7 working router implementations with full route handlers — migrate these verbatim, then fix relative → absolute imports
- `ee/interfaces/*.py` (CE worktree): CE stub routers for 402 responses — no longer needed in axiom-ee (CE stubs stay in CE)

### Established Patterns
- CE `lifespan` is `async def` — `load_ee_plugins` can simply become `async def` and be awaited naturally
- `engine.sync_engine` is the standard SQLAlchemy pattern for sync DDL inside an async codebase — already used elsewhere in CE for migrations
- `app.include_router()` is sync — can be called inside `async def register()` without issues

### Integration Points
- `main.py` lifespan (line 71 in worktree): `app.state.ee = load_ee_plugins(app, engine)` → becomes `app.state.ee = await load_ee_plugins(app, engine)`
- `ee/__init__.py` `load_ee_plugins`: add `async def`, add `await plugin.register(ctx)` call
- `pyproject.toml` in axiom-ee: `[project.entry-points."axiom.ee"]` section with `ee = "ee.plugin:EEPlugin"`
- axiom-ee `pyproject.toml` must declare `axiom-ce` (or the installed package name) as a dependency

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 35-private-ee-repo-plugin-wiring*
*Context gathered: 2026-03-19*

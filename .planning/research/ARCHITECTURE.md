# Architecture Research: CE/EE Split — Plugin Wiring

**Domain:** Open-core FastAPI plugin system (CE/EE split)
**Researched:** 2026-03-19
**Confidence:** HIGH — derived entirely from reading the actual codebase on `feature/axiom-oss-ee-split`

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  CE Public Repo (Apache 2.0)                                        │
│                                                                     │
│  puppeteer/agent_service/                                           │
│  ├── main.py             ← FastAPI app, lifespan, CE routes         │
│  ├── db.py               ← Base + 13 CE tables only                │
│  ├── deps.py             ← get_current_user, require_auth,         │
│  │                          require_permission, audit (EE-safe)     │
│  └── ee/                 ← plugin boundary                         │
│      ├── __init__.py     ← load_ee_plugins(app, engine) → EECtx    │
│      ├── interfaces/     ← stub routers (6 × APIRouter → 402)      │
│      └── routers/        ← real EE routers (move to axiom-ee)      │
│                                                                     │
│  Startup sequence:                                                  │
│  init_db() → load_ee_plugins(app, engine) → bootstrap admin        │
│                                                                     │
│  load_ee_plugins():                                                 │
│  1. pkg_resources.iter_entry_points("axiom.ee")                    │
│  2. If plugins found: plugin_cls(app, engine) → plugin.register()  │
│  3. If none: register stub routers → ctx stays all-False           │
└─────────────────────────────────────────────────────────────────────┘
                              │ pkg_resources entry_point
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EE Private Repo (axiom-ee, proprietary)                            │
│                                                                     │
│  ee/                                                                │
│  ├── plugin.py           ← EEPlugin class (compiled to .so)        │
│  ├── db_models.py        ← EEBase + 15 EE SQLAlchemy models        │
│  └── routers/            ← 7 real router files (moved from CE)     │
│      ├── foundry_router.py                                          │
│      ├── audit_router.py                                            │
│      ├── webhook_router.py                                          │
│      ├── trigger_router.py                                          │
│      ├── auth_ext_router.py                                         │
│      ├── users_router.py                                            │
│      └── smelter_router.py                                          │
│                                                                     │
│  setup.cfg:                                                         │
│  [options.entry_points]                                             │
│  axiom.ee =                                                         │
│      core = ee.plugin:EEPlugin                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `ee/__init__.py` | Entry-point discovery, plugin lifecycle, EEContext creation | EXISTS — needs stub registration added |
| `ee/interfaces/*.py` | 6 stub routers serving 402 for each EE path group | EXISTS — defined but never mounted on app |
| `ee/routers/*.py` | 7 real EE router files with full handler logic | EXISTS in CE worktree — move to axiom-ee |
| `deps.py` | Shared auth deps, `require_permission`, `audit` (EE-safe stubs) | EXISTS — complete |
| `EEPlugin` (private) | `register(ctx)` mounts real routers, creates EE tables, seeds data | DOES NOT EXIST YET |
| `EEContext` dataclass | 8 feature flags stored on `app.state.ee` | EXISTS — returned by `load_ee_plugins` |

---

## The Core Wiring Problem

### Current state of `load_ee_plugins`

```python
# ee/__init__.py — current implementation
def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    ctx = EEContext()
    try:
        plugins = list(pkg_resources.iter_entry_points("axiom.ee"))
        if plugins:
            for ep in plugins:
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                plugin.register(ctx)           # calls register but ctx not used
        else:
            logger.info("No EE plugins found — running in CE mode")
            # BUG: stub routers are NEVER mounted here
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
    return ctx
```

**Two bugs in one:**

1. **Stub routers are never mounted.** All 6 `*_stub_router` objects in `ee/interfaces/` are defined but `load_ee_plugins` never calls `app.include_router()` on them in the CE path. CE mode currently has NO routes for `/api/blueprints`, `/admin/audit-log`, etc. — they 404 instead of returning the intended 402.

2. **EE register() contract is undefined.** `plugin.register(ctx)` is called but the expected contract between CE and EE (what `register` must do, what it receives) is implicit, not specified.

---

## Recommended Architecture

### Pattern 1: CE Stub Registration in `load_ee_plugins`

**What:** When no EE plugin is found, `load_ee_plugins` registers all stub routers on `app` before returning. This ensures all EE API paths exist in CE mode and return 402.

**When to use:** Always — this is the CE cold-start path.

**Implementation in `ee/__init__.py`:**

```python
def _register_ce_stubs(app: Any) -> None:
    """Mount all CE stub routers. Called when no EE plugin is installed."""
    from .interfaces.foundry import foundry_stub_router
    from .interfaces.audit import audit_stub_router
    from .interfaces.webhooks import webhooks_stub_router
    from .interfaces.triggers import triggers_stub_router
    from .interfaces.auth_ext import auth_ext_stub_router
    from .interfaces.smelter import smelter_stub_router
    # users_router has no stub — user management is CE auth-only in CE mode
    app.include_router(foundry_stub_router)
    app.include_router(audit_stub_router)
    app.include_router(webhooks_stub_router)
    app.include_router(triggers_stub_router)
    app.include_router(auth_ext_stub_router)
    app.include_router(smelter_stub_router)

def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    ctx = EEContext()
    try:
        plugins = list(pkg_resources.iter_entry_points("axiom.ee"))
        if plugins:
            for ep in plugins:
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _register_ce_stubs(app)          # fix: mount stubs in CE path
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _register_ce_stubs(app)              # also mount stubs on load failure
    return ctx
```

**Critical ordering constraint:** `load_ee_plugins` is called inside `lifespan` after `app = FastAPI(...)` is created. FastAPI allows `include_router` at any point before the first request. This is safe because lifespan runs before the server starts accepting requests.

---

### Pattern 2: EEPlugin Class — `register()` Contract

**What:** The private repo's `EEPlugin` class receives `(app, engine)` in `__init__`, then `register(ctx)` mounts routers, creates EE tables, seeds data, and sets feature flags on `ctx`.

**The canonical `register()` method (async — see Pattern 3 for why):**

```python
# ee/plugin.py (private repo)
from agent_service.ee import EEContext

class EEPlugin:
    def __init__(self, app, engine):
        self.app = app
        self.engine = engine

    async def register(self, ctx: EEContext) -> None:
        # Step 1: Create EE tables (requires async DB access)
        await self._create_ee_tables()
        # Step 2: Seed EE data (role permissions, capability matrix defaults)
        await self._seed_ee_data()
        # Step 3: Mount all 7 real EE routers (synchronous)
        self._mount_routers()
        # Step 4: Set all feature flags on ctx
        ctx.foundry = True
        ctx.audit = True
        ctx.webhooks = True
        ctx.triggers = True
        ctx.rbac = True
        ctx.resource_limits = True
        ctx.service_principals = True
        ctx.api_keys = True
```

**Parameter semantics:**
- `app: FastAPI` — the live application instance. `app.include_router()` mounts routes.
- `engine: AsyncEngine` — the SQLAlchemy async engine from `db.py`. Used for `conn.run_sync(EEBase.metadata.create_all)`.
- `ctx: EEContext` — mutated in-place. Caller (CE) reads flags after `register()` returns.

---

### Pattern 3: EE Table Creation via Engine

**What:** EE models are defined with a separate `EEBase` in the private repo. Table creation runs in an async context using the engine passed to `EEPlugin.__init__`.

**Why `register()` must be async:**

`register()` is called from `load_ee_plugins` which is called from `lifespan` — an `asynccontextmanager` coroutine. The event loop is already running. Calling `asyncio.run()` or `loop.run_until_complete()` from inside an already-running loop raises `RuntimeError`. The only clean solution is to make `register()` async and `await` it.

**Updated `load_ee_plugins` (async version):**

```python
# ee/__init__.py — upgraded to async
import asyncio

async def _load_ee_plugins_async(app: Any, engine: Any) -> EEContext:
    ctx = EEContext()
    try:
        plugins = list(pkg_resources.iter_entry_points("axiom.ee"))
        if plugins:
            for ep in plugins:
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                await plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _register_ce_stubs(app)
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _register_ce_stubs(app)
    return ctx

# Keep sync wrapper for compatibility if needed
def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    """Sync entry point — delegates to async version via event loop."""
    # This is only safe to call from a non-async context.
    # From lifespan (async), call _load_ee_plugins_async directly.
    raise RuntimeError("Call _load_ee_plugins_async from async lifespan")
```

**Updated lifespan in `main.py`:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from .ee import _load_ee_plugins_async
    from .db import engine
    app.state.ee = await _load_ee_plugins_async(app, engine)
    # ... rest of lifespan unchanged
```

**EE table creation inside `EEPlugin._create_ee_tables()`:**

```python
async def _create_ee_tables(self) -> None:
    from .db_models import EEBase
    async with self.engine.begin() as conn:
        await conn.run_sync(EEBase.metadata.create_all)
```

---

### Pattern 4: EE Router Mounting — `app.include_router()`

**What:** Each of the 7 real EE routers is an `APIRouter` instance. Mounting is synchronous.

**Implementation in `EEPlugin._mount_routers()`:**

```python
def _mount_routers(self) -> None:
    from .routers.foundry_router import foundry_router
    from .routers.audit_router import audit_router
    from .routers.webhook_router import webhook_router
    from .routers.trigger_router import trigger_router
    from .routers.auth_ext_router import auth_ext_router
    from .routers.users_router import users_router
    from .routers.smelter_router import smelter_router

    self.app.include_router(foundry_router)
    self.app.include_router(audit_router)
    self.app.include_router(webhook_router)
    self.app.include_router(trigger_router)
    self.app.include_router(auth_ext_router)
    self.app.include_router(users_router)
    self.app.include_router(smelter_router)
```

**No prefix needed.** All 7 EE routers already use absolute paths (e.g., `/api/blueprints`, `/admin/audit-log`). Adding a `prefix` here would break all existing frontend API calls.

**Route conflict prevention.** In EE mode, `_register_ce_stubs()` is NOT called — only real routers mount. In CE mode, stubs mount and real routers are never loaded. The two sets of routes never coexist.

---

### Pattern 5: Shared vs Separate SQLAlchemy Base

**Decision: separate `EEBase` in the private repo.**

CE's `Base` (in `db.py`) is imported by all CE code including `init_db()`. If EE models extend the same `Base`, CE's `Base.metadata.create_all` would include EE tables — breaking CE-only installs because the model class definitions are not available without EE installed.

**Correct approach:**

```python
# axiom-ee/ee/db_models.py
from sqlalchemy.orm import DeclarativeBase

class EEBase(DeclarativeBase):
    pass

class AuditLog(EEBase):
    __tablename__ = "audit_log"
    ...

class RolePermission(EEBase):
    __tablename__ = "role_permissions"
    ...
# ... 13 more EE tables
```

- CE startup: `Base.metadata.create_all` → 13 CE tables only
- EE startup: `EEBase.metadata.create_all` → 15 EE tables added to same DB
- Both use the same engine, same SQLite/Postgres database. Tables coexist. `create_all` is idempotent.

**Impact on `deps.py`'s `require_permission`:**

The current implementation checks `Base.metadata.tables.get("role_permissions")`. With a separate `EEBase`, this lookup returns `None` in both CE and EE modes because `role_permissions` is not in `Base.metadata`. The function then falls through to `return current_user` in CE mode — correct behaviour.

In EE mode, the fallback fires incorrectly (no permission check) unless the code is updated to also check `EEBase.metadata.tables`. However, the current `require_permission` uses raw SQL (`text("role_permissions")`) not the ORM table object — so it queries the DB directly and works correctly as long as the table exists in the DB, regardless of which Base it was registered under.

**The check `Base.metadata.tables.get("role_permissions")` is the CE/EE mode detector.** It should remain as-is. It correctly returns `None` in CE (because EE models are not imported), allowing the CE fallback.

---

## Recommended Project Structure

```
puppeteer/agent_service/ee/          (CE public repo — final state)
├── __init__.py                      # load_ee_plugins + _register_ce_stubs
└── interfaces/                      # CE stub routers only
    ├── __init__.py
    ├── audit.py                     # audit_stub_router
    ├── auth_ext.py                  # auth_ext_stub_router
    ├── foundry.py                   # foundry_stub_router
    ├── rbac.py                      # RBACInterface stub (no router — CE has no RBAC)
    ├── resource_limits.py           # ResourceLimitsInterface stub (no router)
    ├── smelter.py                   # smelter_stub_router
    ├── triggers.py                  # triggers_stub_router
    └── webhooks.py                  # webhooks_stub_router

REMOVE from CE repo (move to axiom-ee):
└── routers/                         # delete after Phase 5 migration
```

```
axiom-ee/                            (EE private repo)
├── setup.cfg                        # entry_points: axiom.ee = core = ee.plugin:EEPlugin
├── ee/
│   ├── __init__.py
│   ├── plugin.py                    # EEPlugin class
│   ├── db_models.py                 # EEBase + 15 EE SQLAlchemy models
│   └── routers/                     # moved from CE's ee/routers/
│       ├── foundry_router.py        # imports fixed: ...db → ee.db_models
│       ├── audit_router.py
│       ├── webhook_router.py
│       ├── trigger_router.py
│       ├── auth_ext_router.py
│       ├── users_router.py
│       └── smelter_router.py
└── tests/                           # EE-only tests
    ├── conftest.py                  # creates both CE Base + EE Base tables
    ├── test_foundry.py
    ├── test_audit.py
    ├── test_webhooks.py
    ├── test_rbac.py
    └── test_service_principals.py
```

### Structure Rationale

- **`ee/interfaces/` stays in CE.** These stub routers are the CE contract for EE routes. They ship with CE.
- **`ee/routers/` moves to axiom-ee.** The real implementations are proprietary. They must not be in the Apache 2.0 repo.
- **`ee/plugin.py` is private.** Integration glue compiled to `.so`.
- **`EEBase` is private.** EE model definitions must not leak into CE. Separate base enforces the boundary.

---

## Data Flow

### Startup Sequence (CE mode)

```
main.py lifespan():
    await init_db()                           creates 13 CE tables
    await _load_ee_plugins_async(app, engine)
        pkg_resources.iter_entry_points()     empty
        _register_ce_stubs(app)              mounts 6 stub routers
        returns EEContext(all flags = False)
    app.state.ee = EEContext(all False)
    bootstrap admin user (no role column in CE)
    start scheduler
```

### Startup Sequence (EE mode, after `pip install axiom-ee`)

```
main.py lifespan():
    await init_db()                           creates 13 CE tables
    await _load_ee_plugins_async(app, engine)
        pkg_resources.iter_entry_points()     finds "core = ee.plugin:EEPlugin"
        EEPlugin(app, engine).__init__()
        await plugin.register(ctx)
            await _create_ee_tables()         creates 15 EE tables (EEBase)
            await _seed_ee_data()             seeds role_permissions, cap matrix
            _mount_routers()                  app.include_router x 7
            ctx.* = True (all 8 flags)
        returns EEContext(all flags = True)
    app.state.ee = EEContext(all True)
    bootstrap admin user (EE User has role column)
    start scheduler
```

### Request Flow — CE mode (EE route hit)

```
GET /api/blueprints
    foundry_stub_router.blueprints_get()
    returns JSONResponse(402, {"detail": "Axiom EE required"})
```

### Request Flow — EE mode

```
GET /api/blueprints
    foundry_router.list_blueprints()
    require_permission("foundry:read")
        get_current_user() → JWT decode → User lookup
        _perm_cache check → DB query role_permissions
        returns User if permitted
    DB query select(Blueprint)
    returns List[BlueprintResponse]
```

### Feature Flag Check Flow (frontend)

```
GET /api/features
    reads app.state.ee (EEContext dataclass)
    returns {"foundry": true/false, "audit": true/false, ...}

Frontend:
    useFeatures() hook → caches 5 min
    UpgradePlaceholder rendered if feature = false
    Real view rendered if feature = true
```

---

## Test Isolation Architecture

### The Problem

The CE test suite in `puppeteer/tests/` has tests that reference EE-only concepts:

1. **`test_bootstrap_admin.py`** — asserts `admin.role == "admin"` and passes `role="admin"` to `User()`. CE's `User` model has no `role` column (stripped in Phase 3). These lines fail with `AttributeError` or `TypeError`.

2. **EE-heavy test files** — `test_compatibility_engine.py`, `test_foundry_mirror.py`, `test_mirror.py`, `test_smelter.py`, `test_trigger_service.py` import EE models (Blueprint, CapabilityMatrix, ApprovedIngredient, etc.) that no longer exist in CE's `db.py`.

### Fix for `test_bootstrap_admin.py`

Remove `role` assertions and `role` kwarg from `User()` constructor. CE bootstrap creates a user with only `username` and `password_hash`. The corrected test should assert that admin exists and password verifies correctly, without testing role assignment.

### EE Test Files — Move to axiom-ee

These files should be deleted from the CE repo as part of Phase 5 and recreated in `axiom-ee/tests/` with proper EE fixtures.

### CE Test Isolation Pattern

```
puppeteer/tests/                     (CE repo — CE routes only)
├── conftest.py                      in-memory SQLite, Base.metadata.create_all only
├── test_bootstrap_admin.py          fix: remove role assertions
├── test_alert_system.py             CE — keep
├── test_attestation.py              CE — keep
├── test_device_flow.py              CE — keep
├── test_env_tag.py                  CE — keep
├── test_execution_record.py         CE — keep
├── test_job_staging.py              CE — keep
├── test_lifecycle_enforcement.py    CE — keep
├── test_output_capture.py           CE — keep
├── test_retry_wiring.py             CE — keep
├── test_openapi_export.py           CE — keep
└── test_tools.py                    CE — keep

Move to axiom-ee/tests/ then delete from CE:
- test_compatibility_engine.py       EE — references CapabilityMatrix
- test_foundry_mirror.py             EE — references Blueprint, Templates
- test_mirror.py                     EE — references mirror infrastructure
- test_smelter.py                    EE — references ApprovedIngredient
- test_trigger_service.py            EE — references Trigger service
```

### EE Test Fixture Pattern (private repo)

```python
# axiom-ee/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from agent_service.db import Base      # CE Base (13 tables)
from ee.db_models import EEBase        # EE Base (15 tables)

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)    # CE tables
        await conn.run_sync(EEBase.metadata.create_all)  # EE tables
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
```

This gives EE tests a fully-hydrated DB (all 28 tables) while CE tests only create 13.

---

## Integration Points

### New Components Required

| Component | Location | Purpose | New/Modified |
|-----------|----------|---------|--------------|
| `_register_ce_stubs(app)` | `ee/__init__.py` | Mount 6 stub routers in CE/failure paths | MODIFY |
| `_load_ee_plugins_async` | `ee/__init__.py` | Async wrapper enabling `await plugin.register()` | MODIFY |
| Updated lifespan call | `main.py` | `await _load_ee_plugins_async(app, engine)` | MODIFY |
| `EEPlugin` class | `axiom-ee/ee/plugin.py` | Router mounting + table creation + seeding | CREATE |
| `EEBase` + 15 models | `axiom-ee/ee/db_models.py` | EE SQLAlchemy table definitions | CREATE |
| EE test conftest | `axiom-ee/tests/conftest.py` | Both-base DB fixture for EE tests | CREATE |

### Modified Components

| Component | Location | Change |
|-----------|----------|--------|
| `load_ee_plugins` / `_load_ee_plugins_async` | `ee/__init__.py` | Add `_register_ce_stubs()` + make async |
| lifespan | `main.py` | Change `load_ee_plugins` call to `await _load_ee_plugins_async` |
| `test_bootstrap_admin.py` | `puppeteer/tests/` | Remove `role` attribute references (2 assertions, 1 kwarg) |
| `ee/routers/*.py` (7 files) | CE repo | DELETE after copying to axiom-ee |
| 5 EE-heavy test files | `puppeteer/tests/` | DELETE after moving to axiom-ee |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CE `main.py` to EE plugin | `app` + `engine` at construction, `ctx` mutated in `register()` | No circular imports — EE imports CE, not vice versa |
| CE `deps.py` to EE routers | EE routers import `require_permission`, `audit`, `get_current_user` from `deps.py` | Designed coupling — deps.py is shared infrastructure |
| CE `Base` to EE `EEBase` | Both point at same engine/DB | Tables coexist; CE `create_all` only creates CE tables |
| EE routers to CE `db.py` | Currently: `from ...db import Blueprint, AuditLog, ...` | **MUST CHANGE** — relative imports break when moved to private repo |

### Critical Import Path Change

The EE routers currently use relative imports (e.g., `from ...db import AuditLog, Blueprint`). When moved to the private `axiom-ee` repo, the package hierarchy changes and these relative imports resolve to the wrong location or fail entirely.

**Required change when migrating routers to axiom-ee:**

```python
# Before (in CE's ee/routers/foundry_router.py):
from ...db import Blueprint, PuppetTemplate, CapabilityMatrix, ...

# After (in axiom-ee's ee/routers/foundry_router.py):
from agent_service.db import Config, User          # CE models still from CE package
from ee.db_models import Blueprint, PuppetTemplate, CapabilityMatrix, ...  # EE models local

# Similarly for deps:
from agent_service.deps import require_permission, get_current_user, audit
from agent_service.services.foundry_service import foundry_service
```

This refactor affects all 7 router files. It is the highest-effort part of Phase 5 and should be done carefully with a test run after each file.

---

## Build Order

### Phase 5 (Private repo setup + router migration)

1. Create `axiom-ee` private repo with `setup.cfg` entry_points
2. Create `ee/db_models.py` — migrate 15 EE model definitions from pre-split history
3. Create `ee/plugin.py` — `EEPlugin` with `async register()`, `_create_ee_tables()`, `_mount_routers()`, `_seed_ee_data()`
4. Copy `ee/routers/*.py` from CE worktree, fix import paths (`...db` → `ee.db_models` and `agent_service.db`)
5. Modify CE `ee/__init__.py` — add `_register_ce_stubs()`, convert to `_load_ee_plugins_async`, fix CE path and failure path
6. Update CE `main.py` lifespan — `await _load_ee_plugins_async(app, engine)`
7. Fix CE `test_bootstrap_admin.py` — remove `role` attribute references
8. Delete CE's `ee/routers/` directory
9. Delete CE's 5 EE-heavy test files, add them to `axiom-ee/tests/`
10. Validate CE alone: `pytest` passes, `/api/blueprints` → 402, `/api/features` → all false
11. Validate CE+EE: `pip install -e axiom-ee/` → `/api/blueprints` → real response, `/api/features` → all true

### Phase 6 (.so compilation)

Only after Phase 5 validates correctly. Compiled `.so` must pass the same Phase 5 validation.

---

## Anti-Patterns

### Anti-Pattern 1: Importing EE Models in CE Code

**What people do:** Use `from .db import AuditLog` in `deps.py` or `main.py` to check whether EE tables are present.

**Why it's wrong:** CE imports fail when EE is not installed, defeating the plugin architecture entirely.

**Do this instead:** Use `Base.metadata.tables.get("audit_log")` to check table existence at runtime. The current `deps.py` already does this correctly. Do not change this pattern.

### Anti-Pattern 2: Running Async DB Work in Sync `register()`

**What people do:** Call `asyncio.run()` or `loop.run_until_complete()` inside a sync `register()` to create tables.

**Why it's wrong:** `load_ee_plugins` is called from inside an `asynccontextmanager` (lifespan) — the event loop is already running. Both `asyncio.run()` and `loop.run_until_complete()` raise `RuntimeError: This event loop is already running`.

**Do this instead:** Make `register()` async and `await` it from `_load_ee_plugins_async`.

### Anti-Pattern 3: Route Conflicts Between Stubs and Real Routers

**What people do:** Register stub routers at module import time, then register real routers when EE loads.

**Why it's wrong:** FastAPI does not override routes by re-registration. Both the stub and real handler will exist in the route table. The first registered (stub) wins, so real handlers are silently shadowed.

**Do this instead:** Register stubs ONLY in CE mode (no EE plugin found). Register real routers ONLY in EE mode. Never register both.

### Anti-Pattern 4: Relative Imports from Parent Package (post-move)

**What people do:** Copy EE router files to the private repo without updating imports. The routers use `from ...db import Blueprint` which resolves relative to `agent_service.ee.routers` — this path doesn't exist in the private repo.

**Why it's wrong:** Import errors cause the `except Exception` clause in `load_ee_plugins` to catch them silently, dropping into CE stub mode with no indication of the real error.

**Do this instead:** Update all EE router imports to use absolute package names (`agent_service.db`, `ee.db_models`). Add logging in `load_ee_plugins` that prints the full exception traceback to aid debugging.

### Anti-Pattern 5: Testing EE Routes Against CE-Only Fixtures

**What people do:** Run EE route tests against a DB that only has CE tables.

**Why it's wrong:** EE handlers reference `Blueprint`, `CapabilityMatrix`, etc. which don't exist in the CE DB. Queries fail with `ProgrammingError: no such table`.

**Do this instead:** EE test fixtures must run both `Base.metadata.create_all` and `EEBase.metadata.create_all` on the same engine.

---

## Sources

- Codebase direct inspection: `puppeteer/agent_service/ee/__init__.py` — confirmed stub routers never mounted (HIGH confidence)
- Codebase direct inspection: `puppeteer/agent_service/ee/interfaces/*.py` — 6 stub routers defined but orphaned (HIGH confidence)
- Codebase direct inspection: `puppeteer/agent_service/ee/routers/*.py` — 7 real routers use relative `...db` imports (HIGH confidence)
- Codebase direct inspection: `puppeteer/agent_service/db.py` — confirmed 13 CE tables only, User has no `role` column (HIGH confidence)
- Codebase direct inspection: `puppeteer/agent_service/deps.py` — `require_permission` and `audit` use runtime table lookup (HIGH confidence)
- Codebase direct inspection: `puppeteer/tests/test_bootstrap_admin.py` — confirmed `admin.role == "admin"` assertion against role-less CE User (HIGH confidence)
- FastAPI documentation: `include_router()` is safe to call during lifespan before first request. Standard pattern for plugin systems.
- Python packaging: `pkg_resources.iter_entry_points` is the standard Python plugin discovery mechanism.

---
*Architecture research for: Axiom CE/EE open-core split — EE plugin wiring*
*Researched: 2026-03-19*

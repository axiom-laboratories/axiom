# Phase 35: Private EE Repo + Plugin Wiring - Research

**Researched:** 2026-03-19
**Domain:** Python packaging (entry_points), SQLAlchemy async + sync DDL, FastAPI plugin architecture
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**DB table strategy:**
- EE defines its own `EEBase = declarative_base()` — completely separate from CE's `Base`
- `EEPlugin.register()` calls `EEBase.metadata.create_all(engine.sync_engine)` to create EE tables — uses `engine.sync_engine` (the wrapped sync engine inside CE's AsyncEngine)
- CE's startup `create_all` never touches EE models — clean isolation for CE-alone installs
- Standalone EE tables only in Phase 35 — no ForeignKey references back to CE tables (joins happen at query time via shared engine)
- Phase 35 includes real EE DB models per router, not placeholder scaffolding — the actual tables that the compiled `.so` will use in Phase 36

**axiom-ee package layout:**
- Nested per-feature structure: `ee/{feature}/` subdirectories, each containing `router.py`, `models.py`, `services.py` as needed
- `ee/plugin.py` contains `EEPlugin` class (entry_point: `ee.plugin:EEPlugin`)
- `ee/db.py` or `ee/base.py` contains `EEBase = declarative_base()`
- All 7 router files use absolute imports from CE: `from agent_service.db import ...`, `from agent_service.models import ...`, `from agent_service.deps import require_permission`
- Migrate the full EE router implementations from `.worktrees/axiom-split/puppeteer/agent_service/ee/routers/` — do not rewrite from scratch
- Convert all relative imports (`from ...db import ...`) to absolute imports (`from agent_service.db import ...`) during migration
- repo location: `~/Development/axiom-ee/` — sibling to `master_of_puppets/`, separate git repo

**register() async pattern:**
- `load_ee_plugins(app, engine)` in CE's `ee/__init__.py` changed to `async def`
- Callee in `main.py` lifespan updated: `app.state.ee = await load_ee_plugins(app, engine)`
- `EEPlugin.register(ctx)` is `async def register(self, ctx: EEContext) -> None`
- Operation order inside `register()`:
  1. `EEBase.metadata.create_all(engine.sync_engine)` — tables created before routes go live
  2. `app.include_router(...)` for each EE router
  3. Set EEContext feature flags only for routers that successfully mounted — `ctx.{feature} = True` per router

**PyPI stub wheel:**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EE-01 | `axiom-ee` private GitHub repo created with `EEPlugin` class skeleton | Repo layout, pyproject.toml structure, git init steps documented |
| EE-02 | `EEPlugin.register()` is async and mounts all 7 EE routers via `app.include_router()` | Async register pattern and router-to-flag mapping fully documented |
| EE-03 | `EEPlugin.register()` creates EE DB tables via separate `EEBase.metadata.create_all(engine)` | `engine.sync_engine` pattern confirmed; all 15 EE table schemas catalogued |
| EE-04 | All 7 router files use absolute imports — no relative imports from CE codebase | Import conversion map documented for all 7 routers and their services |
| EE-05 | `pyproject.toml` entry_points configured (`[project.entry-points."axiom.ee"]`) and validated | `importlib.metadata.entry_points(group="axiom.ee")` verified as correct discovery mechanism |
| EE-06 | CE-alone smoke test passes: 13 tables created, all EE routes return 402, `GET /api/features` returns all false | CE table list confirmed (13 tables), 402 stub pattern confirmed, features endpoint documented |
| EE-07 | CE+EE combined install smoke test passes: EE tables present, EE routes functional, `GET /api/features` returns all true | EE table list (15 tables), combined install mechanics documented |
| EE-08 | `axiom-ee` stub wheel published to PyPI to reserve the package name | stub wheel pattern, PyPI publishing process with `build` + `twine upload` documented |
</phase_requirements>

---

## Summary

Phase 35 creates the `axiom-ee` private Python package at `~/Development/axiom-ee/`. The core task is migrating 7 existing EE router files from the CE worktree into a properly-structured private repo with a plugin wiring mechanism using Python's `importlib.metadata.entry_points`. The technical work splits into four areas: (1) package scaffolding with `pyproject.toml` entry_point configuration, (2) migration of 7 router files with import path conversion from relative to absolute, (3) definition of the 15 EE-only SQLAlchemy models in a separate `EEBase` declarative base, and (4) async-ification of the CE `load_ee_plugins()` function.

A critical discovery from code inspection: the CE worktree's `db.py` contains only 13 CE-core tables. All EE models (`Blueprint`, `PuppetTemplate`, `AuditLog`, `RolePermission`, etc.) exist in the main-branch `db.py` but were stripped from the CE split. The EE routers' existing relative imports (`from ...db import Blueprint`) will need to become absolute imports from EE's own models module (`from ee.foundry.models import Blueprint`), not from `agent_service.db`. This is a key constraint: EE DB models live in the EE package, accessed via absolute import of `ee.foundry.models`, `ee.auth_ext.models`, etc.

The services co-located with EE routers (foundry_service, smelter_service, trigger_service) also import EE DB models and must migrate into the EE package. The webhook_service is currently a CE stub that EE replaces with a real implementation — it too belongs in the EE package.

**Primary recommendation:** Structure axiom-ee with per-feature subdirectories containing `router.py`, `models.py` (SQLAlchemy), and `services.py` as needed. Run `EEBase.metadata.create_all(engine.sync_engine)` once at register() time before mounting any router. EE DB models import from `ee.{feature}.models`, never from `agent_service.db`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| setuptools | >=77.0 | Build backend (matches CE worktree pyproject.toml) | Already used in CE; consistent build toolchain |
| importlib.metadata | stdlib (3.10+) | `entry_points(group="axiom.ee")` discovery | Already in use in CE `load_ee_plugins()` |
| SQLAlchemy | Already in CE venv | `declarative_base()` for `EEBase`, `create_all` | CE uses SQLAlchemy ORM throughout |
| build | latest | `python -m build` produces sdist + wheel | Standard PEP 517 build tool |
| twine | latest | `twine upload` to PyPI / test.pypi.org | Standard PyPI upload tool |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | Already in CE venv | CE+EE combined smoke tests | For EE-06 and EE-07 test tasks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| setuptools entry_points | poetry plugins | Poetry not used in this project — stay with setuptools for consistency |
| `EEBase = declarative_base()` | Importing CE `Base` | Using CE `Base` was considered but rejected; EEBase gives clean isolation for CE-alone installs |

**Installation (for development/testing):**
```bash
# In axiom-ee/ repo root:
pip install build twine
pip install -e .   # installs axiom-ee in editable mode, wires entry_point

# From CE worktree with EE installed:
pip install -e ~/Development/axiom-ee/
```

---

## Architecture Patterns

### Recommended Package Structure

```
~/Development/axiom-ee/
├── pyproject.toml                  # entry_points + dependencies
├── ee/
│   ├── __init__.py                 # empty or minimal __all__
│   ├── plugin.py                   # EEPlugin class — entry_point target
│   ├── base.py                     # EEBase = declarative_base()
│   ├── foundry/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from foundry_router.py
│   │   ├── models.py               # EEBase models: Blueprint, PuppetTemplate, etc.
│   │   └── services.py             # migrated from foundry_service.py
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from audit_router.py
│   │   └── models.py               # AuditLog model
│   ├── auth_ext/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from auth_ext_router.py
│   │   └── models.py               # UserSigningKey, UserApiKey, ServicePrincipal
│   ├── smelter/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from smelter_router.py
│   │   ├── models.py               # ApprovedIngredient
│   │   └── services.py             # migrated from smelter_service.py
│   ├── triggers/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from trigger_router.py
│   │   ├── models.py               # Trigger model
│   │   └── services.py             # migrated from trigger_service.py
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── router.py               # migrated from webhook_router.py
│   │   ├── models.py               # Webhook model
│   │   └── services.py             # real WebhookService (replaces CE stub)
│   └── rbac/
│       ├── __init__.py
│       └── models.py               # RolePermission model (no router — users_router handles RBAC)
```

Note on `users_router.py`: it handles both user management and RBAC permission CRUD. It belongs in `ee/auth_ext/` alongside the auth_ext router, or as a separate `ee/users/` directory. It sets the `rbac` flag.

### Pattern 1: entry_point Discovery (EE-05)

**What:** `pyproject.toml` declares `axiom.ee` group entry_point pointing to `EEPlugin`. CE's `load_ee_plugins()` uses `importlib.metadata.entry_points(group="axiom.ee")` to discover it.

**pyproject.toml section:**
```toml
[project.entry-points."axiom.ee"]
ee = "ee.plugin:EEPlugin"
```

**CE discovery (already in ce/__init__.py):**
```python
from importlib.metadata import entry_points
plugins = list(entry_points(group="axiom.ee"))
```

**Verified:** `importlib.metadata.entry_points(group=...)` is the correct API for Python 3.10+ (replaces deprecated `pkg_resources.iter_entry_points()`). This is already present in the CE worktree's `load_ee_plugins()`.

### Pattern 2: EEPlugin Class (EE-01, EE-02, EE-03)

```python
# ee/plugin.py
from __future__ import annotations
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

class EEPlugin:
    def __init__(self, app, engine):
        self._app = app
        self._engine = engine

    async def register(self, ctx) -> None:
        # Step 1: Create EE tables synchronously via sync_engine
        from ee.base import EEBase
        self._engine.sync_engine.connect().__enter__()  # NOT this pattern
        # Correct pattern:
        with self._engine.sync_engine.connect() as conn:
            EEBase.metadata.create_all(conn)
        # Step 2: Mount routers with per-router error isolation
        # Step 3: Set feature flags only for successfully mounted routers
```

**Correct `create_all` pattern (confirmed):**
```python
# engine is CE's AsyncEngine; engine.sync_engine is the wrapped SyncEngine
with self._engine.sync_engine.connect() as conn:
    EEBase.metadata.create_all(conn)
```

The `.sync_engine` attribute on `AsyncEngine` exposes the underlying sync engine. `create_all(bind)` accepts a connection or engine. Using `conn` rather than `self._engine.sync_engine` directly avoids the deprecation warning in SQLAlchemy 2.x for `create_all(engine)`.

**Alternate pattern that also works:**
```python
EEBase.metadata.create_all(self._engine.sync_engine)
```
Both are valid in SQLAlchemy 2.x — use whichever CE uses in `extend_schema()` for consistency.

### Pattern 3: Async register() + CE lifespan update (EE-02)

**CE change required — `ee/__init__.py`:**
```python
# Change from:
def load_ee_plugins(app, engine) -> EEContext:
    ...
    plugin.register(ctx)  # sync call

# Change to:
async def load_ee_plugins(app, engine) -> EEContext:
    ...
    await plugin.register(ctx)  # async call
```

**CE change required — `main.py` lifespan (line 71):**
```python
# Change from:
app.state.ee = load_ee_plugins(app, engine)

# Change to:
app.state.ee = await load_ee_plugins(app, engine)
```

### Pattern 4: Import Conversion (EE-04)

The 7 router files currently use relative imports 3 levels deep (`from ...db import ...`). After migrating to `ee/{feature}/router.py`, these become absolute:

| Before (relative) | After (absolute) |
|-------------------|------------------|
| `from ...db import get_db, AsyncSession, Blueprint, PuppetTemplate, ...` | `from agent_service.db import get_db, AsyncSession` + `from ee.foundry.models import Blueprint, PuppetTemplate, ...` |
| `from ...deps import require_permission, get_current_user, audit` | `from agent_service.deps import require_permission, get_current_user, audit` |
| `from ...models import BlueprintCreate, BlueprintResponse, ...` | `from agent_service.models import BlueprintCreate, BlueprintResponse, ...` |
| `from ...auth import get_password_hash, create_access_token` | `from agent_service.auth import get_password_hash, create_access_token` |
| `from ...security import cipher_suite` | `from agent_service.security import cipher_suite` |
| `from ...services.foundry_service import foundry_service` | `from ee.foundry.services import foundry_service` |
| `from ...services.smelter_service import SmelterService` | `from ee.smelter.services import SmelterService` |
| `from ...services.trigger_service import trigger_service` | `from ee.triggers.services import trigger_service` |
| `from ...services.webhook_service import WebhookService` | `from ee.webhooks.services import WebhookService` |

**Critical rule for no circular import (success criterion 4):**
- `ee/plugin.py` must NOT import any router module at module level
- Router imports happen inside `register()` only: `from ee.foundry.router import foundry_router`
- This ensures `python -c "import ee.plugin"` does not trigger `agent_service.main` startup

### Pattern 5: EE DB Model Structure (EE-03)

Each `ee/{feature}/models.py` defines models using `EEBase`:

```python
# ee/base.py
from sqlalchemy.orm import DeclarativeBase

class EEBase(DeclarativeBase):
    pass
```

```python
# ee/foundry/models.py
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, DateTime, Integer, Float, Optional
from datetime import datetime
from ee.base import EEBase

class Blueprint(EEBase):
    __tablename__ = "blueprints"
    # ... fields from main-branch db.py Blueprint class

class PuppetTemplate(EEBase):
    __tablename__ = "puppet_templates"
    # ... fields

class CapabilityMatrix(EEBase):
    __tablename__ = "capability_matrix"
    # ... fields

class ImageBOM(EEBase):
    __tablename__ = "image_boms"
    # ... fields

class PackageIndex(EEBase):
    __tablename__ = "package_index"
    # ... fields

class ApprovedOS(EEBase):
    __tablename__ = "approved_os"
    # ... fields

class Artifact(EEBase):
    __tablename__ = "artifacts"
    # ... fields
```

**ForeignKey constraint**: CONTEXT.md states no FK references back to CE tables in Phase 35. The `Trigger` model in main-branch has `ForeignKey("scheduled_jobs.id")` — this FK must be **dropped** for Phase 35 (joins at query time instead). Similarly `UserSigningKey` and `UserApiKey` have `ForeignKey("users.username")` — remove in EE models, use plain `String` instead.

### Pattern 6: Router-to-Feature Flag Mapping (EE-02)

The EE-context has 8 flags. The 7 router files map as follows:

| Router file | EEContext flag(s) set | Notes |
|------------|----------------------|-------|
| `foundry_router.py` | `ctx.foundry = True` | Includes smelter routes in same router set |
| `audit_router.py` | `ctx.audit = True` | Single route: `/admin/audit-log` |
| `webhook_router.py` | `ctx.webhooks = True` | `/api/webhooks` CRUD |
| `trigger_router.py` | `ctx.triggers = True` | `/api/trigger/{slug}` + admin CRUD |
| `users_router.py` | `ctx.rbac = True` | Users + role permissions management |
| `auth_ext_router.py` | `ctx.api_keys = True`, `ctx.service_principals = True` | Signing keys + API keys + service principals |
| `smelter_router.py` | (already part of `ctx.foundry`) | Mount alongside foundry router |

**`resource_limits` flag**: The 8th flag `resource_limits` maps to no dedicated router. It is set by `auth_ext_router.py` or as part of users/RBAC setup — review the existing CE `_mount_ce_stubs()` pattern. Looking at the interfaces/ directory: `resource_limits.py` stub exists. In Phase 35 decisions, resource_limits flag should be set — most likely set by the `users_router` or directly in `register()` after verifying a resource-limits model exists. **Recommendation**: set `ctx.resource_limits = True` unconditionally in `register()` after all tables are created (it's a DB-level capability, not a separate router).

### Pattern 7: PyPI Stub Wheel (EE-08)

The stub is the same `axiom-ee` repo at version `0.1.0.dev0`. The no-op `EEPlugin`:

```python
# used only for stub wheel — real EEPlugin is in full install
class EEPlugin:
    def __init__(self, app, engine): pass
    async def register(self, ctx) -> None:
        # Set all flags True but mount no routers, create no tables
        ctx.foundry = True
        ctx.audit = True
        ctx.webhooks = True
        ctx.triggers = True
        ctx.rbac = True
        ctx.resource_limits = True
        ctx.service_principals = True
        ctx.api_keys = True
```

**Build and publish sequence:**
```bash
cd ~/Development/axiom-ee/
python -m build          # produces dist/axiom_ee-0.1.0.dev0-py3-none-any.whl + .tar.gz
twine upload --repository testpypi dist/*   # test.pypi.org first
twine upload dist/*                          # then pypi.org
```

The `axiom-laboratories` org on PyPI already has Trusted Publisher configured from Phase 10. For manual upload (not CI), `twine` with `~/.pypirc` credentials or env vars `TWINE_USERNAME`/`TWINE_PASSWORD` works.

### Anti-Patterns to Avoid

- **Top-level router imports in `ee/plugin.py`**: `from ee.foundry.router import foundry_router` at module level WILL cause circular import — CE's `agent_service.models` would be imported before CE is fully initialized. All imports inside `register()` body only.
- **Using `await` with `create_all`**: `EEBase.metadata.create_all()` is sync-only — calling with `await` will raise TypeError. Use the sync engine exclusively for DDL.
- **`asyncio.get_event_loop().run_until_complete()` inside async register()**: Don't nest event loops. `create_all(engine.sync_engine)` is sync and runs fine inside an async function without any loop management.
- **Setting feature flags before router mount**: CONTEXT.md specifies flags set AFTER successful router mount. Don't set `ctx.foundry = True` before `app.include_router(foundry_router)`.
- **ForeignKeys to CE tables in EEBase models**: Phase 35 explicitly forbids this — omit `ForeignKey("users.username")` from `UserSigningKey`, omit `ForeignKey("scheduled_jobs.id")` from `Trigger`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin discovery | Custom JSON config or env var for EE path | `importlib.metadata.entry_points(group="axiom.ee")` | Already in CE; pip install automatically registers entry_points |
| Wheel building | Custom packaging scripts | `python -m build` (PEP 517) | Produces correct sdist + wheel with entry_point metadata |
| PyPI upload | curl to PyPI API | `twine upload` | Handles authentication, metadata validation, HTTPS |
| EE table creation in async context | `asyncio.run()` or thread executors | `EEBase.metadata.create_all(engine.sync_engine)` | SQLAlchemy AsyncEngine exposes `.sync_engine` precisely for sync DDL operations |

---

## Common Pitfalls

### Pitfall 1: Circular Import via Module-Level Router Import

**What goes wrong:** `ee/plugin.py` contains `from ee.foundry.router import foundry_router` at module level. When `importlib.metadata` loads `EEPlugin`, Python imports `ee.plugin` → imports `ee.foundry.router` → imports `from agent_service.db import Blueprint` → triggers `agent_service.db` → which at module level may partially initialize before CE's `lifespan()` runs.

**Why it happens:** Python's import system resolves all module-level imports eagerly on first import of a module.

**How to avoid:** Import router modules inside `register()` body only:
```python
async def register(self, ctx) -> None:
    from ee.foundry.router import foundry_router
    self._app.include_router(foundry_router)
```

**Warning signs:** `python -c "import ee.plugin"` raises `ImportError` or imports agent_service.

### Pitfall 2: EEBase ForeignKeys to CE Tables

**What goes wrong:** `class Trigger(EEBase): job_definition_id = mapped_column(ForeignKey("scheduled_jobs.id"))` — when `EEBase.metadata.create_all()` runs, SQLAlchemy validates FK targets exist in the same metadata. `scheduled_jobs` is in CE's `Base.metadata`, not `EEBase.metadata` → error: "Could not determine join condition".

**Why it happens:** SQLAlchemy FK validation is metadata-scoped by default.

**How to avoid:** Use plain `String` columns for cross-base references. Drop FK constraints in Phase 35 EE models (CONTEXT.md explicitly states: "no ForeignKey references back to CE tables").

**Warning signs:** `create_all` raises `sqlalchemy.exc.NoReferencedTableError`.

### Pitfall 3: `load_ee_plugins()` Not Awaited After Async Change

**What goes wrong:** CE `main.py` still calls `app.state.ee = load_ee_plugins(app, engine)` after `load_ee_plugins` becomes `async def`. This results in `app.state.ee` being set to a coroutine object, not an `EEContext`. All flag checks silently pass as truthy (a coroutine is truthy).

**Why it happens:** Python won't raise an error for calling an async function without `await` — it just returns a coroutine.

**How to avoid:** The CE lifespan change is required alongside the EE package. Both tasks must land together: `async def load_ee_plugins` + `await load_ee_plugins(...)` in main.py.

**Warning signs:** `GET /api/features` returns all flags as truthy even in CE-only mode.

### Pitfall 4: `create_all` Called with AsyncEngine Instead of SyncEngine

**What goes wrong:** `EEBase.metadata.create_all(self._engine)` where `self._engine` is an `AsyncEngine`. SQLAlchemy 2.x raises `TypeError: 'AsyncEngine' object is not callable` or similar.

**Why it happens:** `create_all` is a synchronous DDL operation and does not accept `AsyncEngine`.

**How to avoid:** Always use `self._engine.sync_engine`:
```python
EEBase.metadata.create_all(self._engine.sync_engine)
```

### Pitfall 5: EE Pydantic Models Not Available After Split

**What goes wrong:** EE routers (`foundry_router.py`) import from `agent_service.models` (`from agent_service.models import BlueprintCreate, BlueprintResponse`). After the CE split, the worktree CE `models.py` no longer contains these classes — they were stripped in the axiom-split branch. The import will fail at `register()` time.

**Why it happens:** The CE/EE split removed EE-specific Pydantic models from CE `models.py`. The EE routers now need these models available at `agent_service.models` path OR must import them from EE's own models.

**How to avoid:** Two options:
1. Keep EE Pydantic models in `agent_service.models` (CE provides them) — this contradicts the split goal
2. **Correct approach**: Move EE Pydantic models into the EE package (`ee/foundry/models.py` for request/response schemas) and update router imports accordingly

**Investigation required:** Verify the current state of `models.py` in the axiom-split worktree. The worktree CE `models.py` has been checked — it does NOT contain EE Pydantic models (BlueprintCreate, WebhookCreate, etc. are absent). These must be included in the EE package.

**Recommendation**: Place Pydantic request/response models alongside SQLAlchemy models in `ee/{feature}/models.py`. Import path in routers: `from ee.foundry.models import BlueprintCreate, BlueprintResponse`.

### Pitfall 6: EE Services Import EE DB Models from `agent_service.db`

**What goes wrong:** `foundry_service.py` currently imports `Blueprint, PuppetTemplate, CapabilityMatrix` from `..db` (the CE db module). After migration, these models don't exist in `agent_service.db` — only in `ee.foundry.models`.

**How to avoid:** When migrating `foundry_service.py` → `ee/foundry/services.py`, update the DB model imports to `from ee.foundry.models import Blueprint, PuppetTemplate, CapabilityMatrix, ...`.

---

## Code Examples

### pyproject.toml (axiom-ee)

```toml
[build-system]
requires = ["setuptools>=77.0"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-ee"
version = "0.1.0.dev0"
description = "Axiom Enterprise Edition plugin"
license = "Proprietary"
requires-python = ">=3.10"
dependencies = [
    "axiom-orchestrator",
]

[project.entry-points."axiom.ee"]
ee = "ee.plugin:EEPlugin"

[tool.setuptools.packages.find]
where = ["."]
include = ["ee*"]
```

### ee/base.py

```python
from sqlalchemy.orm import DeclarativeBase

class EEBase(DeclarativeBase):
    pass
```

### ee/plugin.py (skeleton)

```python
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

class EEPlugin:
    def __init__(self, app, engine):
        self._app = app
        self._engine = engine

    async def register(self, ctx) -> None:
        from ee.base import EEBase
        # 1. Create EE tables
        EEBase.metadata.create_all(self._engine.sync_engine)
        # 2. Mount routers (imports deferred to avoid circular import)
        try:
            from ee.foundry.router import foundry_router
            self._app.include_router(foundry_router)
            ctx.foundry = True
        except Exception as e:
            logger.warning(f"EE foundry router failed to mount: {e}")
        # ... repeat for each router
        ctx.resource_limits = True  # DB-level capability, no dedicated router
```

### CE ee/__init__.py change (load_ee_plugins → async)

```python
# Change signature:
async def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    ctx = EEContext()
    try:
        from importlib.metadata import entry_points
        plugins = list(entry_points(group="axiom.ee"))
        if plugins:
            for ep in plugins:
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                await plugin.register(ctx)   # <-- await added
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _mount_ce_stubs(app)
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _mount_ce_stubs(app)
    return ctx
```

### CE main.py lifespan change

```python
# Line 71 in worktree (current):
app.state.ee = load_ee_plugins(app, engine)

# After change:
app.state.ee = await load_ee_plugins(app, engine)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources.iter_entry_points()` | `importlib.metadata.entry_points(group=...)` | Python 3.12 deprecated pkg_resources | CE worktree already uses importlib.metadata (GAP-02 fix) |
| Sync `load_ee_plugins()` | Async `load_ee_plugins()` | Phase 35 | Required to `await plugin.register()` for async DDL coordination |
| Relative imports in EE routers | Absolute imports | Phase 35 | Enables routers to work as standalone package outside CE source tree |

---

## Complete EE DB Model Inventory

All models taken from main-branch `db.py` — cross-referenced with what EE routers actually query.

### ee/foundry/models.py (7 models)
| Class | Table | Used by |
|-------|-------|---------|
| `Blueprint` | `blueprints` | foundry_router, foundry_service |
| `PuppetTemplate` | `puppet_templates` | foundry_router, foundry_service |
| `CapabilityMatrix` | `capability_matrix` | foundry_router, foundry_service |
| `ImageBOM` | `image_boms` | foundry_router |
| `PackageIndex` | `package_index` | foundry_router |
| `ApprovedOS` | `approved_os` | foundry_router |
| `Artifact` | `artifacts` | foundry_service (via capability matrix FK) |

### ee/smelter/models.py (1 model)
| Class | Table | Used by |
|-------|-------|---------|
| `ApprovedIngredient` | `approved_ingredients` | smelter_router, smelter_service |

### ee/audit/models.py (1 model)
| Class | Table | Used by |
|-------|-------|---------|
| `AuditLog` | `audit_log` | audit_router, deps.audit() |

### ee/auth_ext/models.py (3 models)
| Class | Table | Used by |
|-------|-------|---------|
| `UserSigningKey` | `user_signing_keys` | auth_ext_router |
| `UserApiKey` | `user_api_keys` | auth_ext_router |
| `ServicePrincipal` | `service_principals` | auth_ext_router |

### ee/rbac/models.py (1 model)
| Class | Table | Used by |
|-------|-------|---------|
| `RolePermission` | `role_permissions` | users_router, deps.require_permission() |

### ee/webhooks/models.py (1 model)
| Class | Table | Used by |
|-------|-------|---------|
| `Webhook` | `webhooks` | webhook_router, WebhookService |

### ee/triggers/models.py (1 model)
| Class | Table | Used by |
|-------|-------|---------|
| `Trigger` | `triggers` | trigger_router, trigger_service |

**Total: 15 EE tables** (confirms EE-07 requirement: "EE tables present after combined install").

---

## Critical Dependency: `deps.audit()` and `deps.require_permission()` with EE Models

The CE `deps.py` contains two functions that interact with EE models:

**`audit()` function** (line 121 in CE deps.py):
```python
def audit(db, user, action, resource_id=None, detail=None):
    """Append an audit entry if the AuditLog table exists (EE). No-op in CE."""
    if "audit_log" not in Base.metadata.tables:
        return  # CE-safe no-op
    ...
```
This uses `Base.metadata.tables` to check if `audit_log` exists. After EE install, `AuditLog` is in `EEBase.metadata.tables`, NOT `Base.metadata.tables`. This check will ALWAYS return early even with EE installed, making audit a permanent no-op.

**Resolution required**: The `audit()` function in `deps.py` needs updating. Options:
1. Add a second check: `if "audit_log" not in Base.metadata.tables and "audit_log" not in EEBase.metadata.tables:` — but this creates a CE→EE import dependency
2. Remove the guard and use raw SQL (already present as fallback): `text("INSERT INTO audit_log ...")` — the try/except on the INSERT handles CE case
3. **Recommended**: Replace the `Base.metadata.tables` guard with a try/except around the INSERT — if table doesn't exist, SQLAlchemy raises an error that the except catches

**`require_permission()` function**: Queries `RolePermission` table at runtime. Currently checks if user is admin (bypass) or queries DB. In CE, `RolePermission` table doesn't exist — need to verify the CE worktree handles this gracefully.

---

## Open Questions

1. **`deps.audit()` guard condition mismatch**
   - What we know: CE `deps.audit()` checks `"audit_log" not in Base.metadata.tables` to no-op in CE. After EE install, `AuditLog` is in `EEBase`, not `Base`, so the guard always triggers no-op even with EE.
   - What's unclear: Whether the current CE worktree `deps.py` has already been updated for this, or if the raw SQL fallback path handles it.
   - Recommendation: Plan task to verify and fix `deps.audit()` guard. The raw SQL INSERT approach is the cleanest solution.

2. **`require_permission()` when `RolePermission` table doesn't exist (CE)**
   - What we know: CE db.py has no `RolePermission` — the table won't exist. `require_permission()` queries it.
   - What's unclear: Whether the CE worktree already has a guard or try/except in `require_permission()`.
   - Recommendation: Check `deps.py` in axiom-split worktree before building — add a try/except or pre-check.

3. **`users_router.py` feature flag mapping**
   - What we know: `users_router` handles users + role permissions. It sets `rbac` flag.
   - What's unclear: Whether `users_router` should be in `ee/auth_ext/` (alongside auth_ext_router) or in its own `ee/users/` subdirectory.
   - Recommendation: Place in `ee/users/` for clarity — distinct from auth_ext which handles keys and service principals.

4. **WebhookService stub replacement**
   - What we know: CE `webhook_service.py` is a stub no-op with only `dispatch_event()`. The `webhook_router.py` calls `WebhookService.list_webhooks()` and `WebhookService.create_webhook()` — methods that don't exist on the CE stub.
   - What's unclear: Whether a full `WebhookService` implementation exists in the pre-split main-branch code.
   - Recommendation: Check main-branch `services/webhook_service.py` for full implementation; migrate it to `ee/webhooks/services.py`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed in CE venv) |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` in axiom-split worktree |
| Quick run command | `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -x -q` |
| Full CE suite | `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -q` |
| CE+EE combined suite | `cd .worktrees/axiom-split && pip install -e ~/Development/axiom-ee/ && pytest puppeteer/agent_service/tests/ puppeteer/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-01 | axiom-ee repo exists, EEPlugin importable | smoke | `python -c "import ee.plugin; print('ok')"` (run from axiom-ee/) | Wave 0 |
| EE-02 | register() mounts 7 routers async | unit | `pytest puppeteer/agent_service/tests/test_ee_plugin.py -x` | Wave 0 |
| EE-03 | EE tables created by register() | unit | `pytest puppeteer/agent_service/tests/test_ee_plugin.py::test_ee_tables -x` | Wave 0 |
| EE-04 | No relative imports in EE router files | static | `grep -r "from \.\.\." ~/Development/axiom-ee/ee/` (should return nothing) | N/A |
| EE-05 | entry_point discovered by importlib.metadata | smoke | `python -c "from importlib.metadata import entry_points; print(list(entry_points(group='axiom.ee')))"` | N/A |
| EE-06 | CE-alone: 13 tables, 402 on EE routes, all features false | integration | `pytest puppeteer/agent_service/tests/test_ce_smoke.py -x` | Wave 0 |
| EE-07 | CE+EE: EE tables present, routes functional, all features true | integration | `pytest puppeteer/agent_service/tests/test_ee_smoke.py -x` (requires EE installed) | Wave 0 |
| EE-08 | axiom-ee on PyPI | manual | `pip install axiom-ee --index-url https://pypi.org/simple/` | manual-only |

### Sampling Rate
- **Per task commit:** `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -x -q`
- **Per wave merge:** Full CE suite + `python -c "import ee.plugin"` check
- **Phase gate:** CE suite green + CE+EE combined smoke tests green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/agent_service/tests/test_ee_plugin.py` — covers EE-02, EE-03: async register + table creation
- [ ] `puppeteer/agent_service/tests/test_ce_smoke.py` — covers EE-06: 13-table count, 402 routes, all-false features
- [ ] `puppeteer/agent_service/tests/test_ee_smoke.py` — covers EE-07: EE tables, functional routes, all-true features (skipped unless `axiom-ee` installed, using `pytest.mark.ee_only`)

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `.worktrees/axiom-split/puppeteer/agent_service/db.py` — CE 13-table list confirmed
- Direct code inspection: `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — current `load_ee_plugins()` implementation
- Direct code inspection: `.worktrees/axiom-split/puppeteer/agent_service/ee/routers/` (all 7 files) — import patterns and DB model usage
- Direct code inspection: `puppeteer/agent_service/db.py` (main branch) — all 28 model classes, EE model schemas
- Direct code inspection: `puppeteer/agent_service/models.py` (main branch) — all EE Pydantic models present

### Secondary (MEDIUM confidence)
- SQLAlchemy docs: `AsyncEngine.sync_engine` attribute confirmed for sync DDL access pattern
- Python packaging docs: `[project.entry-points."group"]` format in pyproject.toml confirmed

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in existing code
- Architecture: HIGH — based on direct code inspection of all 7 router files and CE infrastructure
- Pitfalls: HIGH — derived from actual code gaps found during inspection (deps.audit() guard, missing EE Pydantic models, ForeignKey constraints)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable Python packaging domain)

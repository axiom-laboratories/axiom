# Phase 34: CE Baseline Fixes - Research

**Researched:** 2026-03-19
**Domain:** Python/FastAPI — CE/EE plugin split, pytest marker isolation, Pydantic model cleanup
**Confidence:** HIGH

## Summary

This phase fixes 6 enumerated gaps in the `feature/axiom-oss-ee-split` worktree at `.worktrees/axiom-split/`. All changes are surgical: no new features, no schema migrations, no new dependencies. The gaps block CE from running correctly in isolation — stub routers are never mounted, `pkg_resources` is deprecated, EE test files pollute the CE suite, `bootstrap_admin.py` crashes on `User.role`, and `NodeConfig` carries stripped EE fields that crash `job_service.py` dispatch.

The phase is entirely self-contained. All 6 gaps are independent of each other and can be addressed in any order, though GAP-01 and GAP-03 should land before any EE router work in Phase 35. All implementation decisions are already locked in CONTEXT.md — the research task is to verify the exact current state of each file so the planner produces precise, non-speculative tasks.

**Primary recommendation:** Fix all 6 gaps in a single wave. Each gap is a targeted edit to one or two files. No new packages, no DB migrations required.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### GAP-01: Stub router mounting
- Mount all 7 CE stub routers inside `load_ee_plugins()` via a `_mount_ce_stubs(app)` helper
- Called when no EE plugin found AND in the except handler (graceful fallback)
- Before mounting, audit every route in `ee/routers/*.py` and verify each has a 402 stub in `ee/interfaces/`; fill any missing stubs
- `main.py` stays clean — CE/EE decision stays inside `load_ee_plugins()`

#### GAP-02: importlib.metadata
- Replace `pkg_resources.iter_entry_points("axiom.ee")` with `importlib.metadata.entry_points(group="axiom.ee")`
- 1-line fix; remove `import pkg_resources`

#### GAP-03: EE test isolation
- Register `ee_only` marker in `pyproject.toml` under `[tool.pytest.ini_options]`
- Add skip logic to `conftest.py`: `pytest_collection_modifyitems` skips items with `ee_only` marker when EE not installed
- Create 4 placeholder test files in `agent_service/tests/`: `test_lifecycle_enforcement.py`, `test_foundry_mirror.py`, `test_smelter.py`, `test_staging.py`
- Each file: single `@pytest.mark.ee_only` test with a docstring, no assertions (just `pass`)

#### GAP-04: bootstrap_admin.py User.role fix
- Remove `role="admin"` from `User(...)` constructor call in `bootstrap_admin.py`
- CE `User` model has no `role` column — this field was stripped in Phase 3

#### GAP-05 + GAP-06: NodeConfig removal + job_service CE defaults
- Remove `NodeConfig` Pydantic model entirely
- Remove `PollResponse.config: NodeConfig` field
- Add `env_tag: Optional[str] = None` directly to `PollResponse` (None = no push, "" = clear, "PROD" = set)
- TAMPERED node quarantine: return `PollResponse(job=None)` — no work dispatched, no special config signal needed
- Normal node: return `PollResponse(job=work_item, env_tag=...)` with env_tag logic preserved
- Remove all `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` references from `job_service.py`
- Update `node.py` in the same phase: read `poll_response.env_tag` directly instead of `poll_response.config.env_tag`; drop all `config.concurrency_limit` and `config.tags` parsing

### Claude's Discretion
- Exact variable names for the `_mount_ce_stubs` helper
- Whether to use `importlib.metadata` `select()` or direct `entry_points(group=...)` call (both work on Python 3.12+)
- Content of the placeholder test docstrings

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GAP-01 | CE mode returns 402 (not 404) for all EE routes — all 7 stub routers mounted in `load_ee_plugins()` | `load_ee_plugins()` confirmed to never call `app.include_router()` in CE path; 7 stub objects exist and are audit-verified below |
| GAP-02 | `load_ee_plugins()` uses `importlib.metadata.entry_points()` instead of deprecated `pkg_resources` | `ee/__init__.py` confirmed to use `pkg_resources.iter_entry_points("axiom.ee")` — 1-line replacement identified |
| GAP-03 | EE-only test files isolated with `@pytest.mark.ee_only` marker + conftest skip logic | `pyproject.toml` has no `markers` config; conftest has no `pytest_collection_modifyitems`; 4 placeholder files absent |
| GAP-04 | `test_bootstrap_admin.py` / CE pytest suite `User.role` attribute errors removed | CE `User` model (db.py:88-93) confirmed to have NO `role` column; `bootstrap_admin.py:23` passes `role="admin"`; `test_db.py:7` and other test fixtures also use `role=` |
| GAP-05 | `NodeConfig` Pydantic model stripped of EE-only fields | `NodeConfig` at models.py:105-110 confirmed present with `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` |
| GAP-06 | `job_service.py` EE field workarounds removed and replaced with CE-appropriate defaults | `job_service.py` confirmed to construct `NodeConfig(concurrency_limit=0, ...)` at lines 173-177 (TAMPERED path) and 196-200 (normal path) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `importlib.metadata` | stdlib (Python 3.9+) | Entry point discovery | Replaces deprecated `pkg_resources`; no new dependency |
| `pytest` | installed (9.0.2 per pycache) | Test runner | Already in use |
| `anyio` / `pytest-anyio` | installed | Async test support | Already in use; conftest has `anyio_backend` fixture |
| FastAPI `APIRouter` | installed | Stub router mounting | Already used in all 7 stub files |

### No New Dependencies Required

All 6 gaps are fixed using code already in the worktree. No `pip install` required.

## Architecture Patterns

### Recommended Project Structure (no changes)
```
.worktrees/axiom-split/
├── puppeteer/
│   ├── agent_service/
│   │   ├── ee/
│   │   │   ├── __init__.py          # GAP-01, GAP-02: load_ee_plugins() fixed here
│   │   │   └── interfaces/          # GAP-01: stub routers audited / filled here
│   │   ├── models.py                # GAP-05: NodeConfig removed, PollResponse simplified
│   │   ├── services/
│   │   │   └── job_service.py       # GAP-06: NodeConfig construction removed
│   │   └── tests/
│   │       ├── conftest.py          # GAP-03: pytest_collection_modifyitems added
│   │       ├── test_db.py           # GAP-04: role= removed
│   │       ├── test_scheduler_service.py  # GAP-04: role= removed
│   │       ├── test_signature_service.py  # GAP-04: role= removed
│   │       ├── test_lifecycle_enforcement.py  # GAP-03: new placeholder
│   │       ├── test_foundry_mirror.py         # GAP-03: new placeholder
│   │       ├── test_smelter.py                # GAP-03: new placeholder
│   │       └── test_staging.py                # GAP-03: new placeholder
│   ├── tests/
│   │   └── test_bootstrap_admin.py  # GAP-04: role= references removed
│   └── bootstrap_admin.py           # GAP-04: role="admin" removed
└── puppets/environment_service/
    └── node.py                      # GAP-05/06: config.concurrency_limit etc. removed
```

### Pattern 1: CE stub mounting via `_mount_ce_stubs(app)`

**What:** A private helper inside `ee/__init__.py` that calls `app.include_router()` for all 7 stub routers.
**When to use:** Called in both the `else` branch (no plugins found) and the `except` handler of `load_ee_plugins()`.

```python
# Source: ee/__init__.py (current pattern, adapted)
def _mount_ce_stubs(app: Any) -> None:
    from .interfaces.foundry import foundry_stub_router
    from .interfaces.audit import audit_stub_router
    from .interfaces.webhooks import webhooks_stub_router
    from .interfaces.triggers import triggers_stub_router
    from .interfaces.auth_ext import auth_ext_stub_router
    from .interfaces.smelter import smelter_stub_router
    from .interfaces.users import users_stub_router  # if stub created, else auth_ext covers users
    app.include_router(foundry_stub_router)
    app.include_router(audit_stub_router)
    app.include_router(webhooks_stub_router)
    app.include_router(triggers_stub_router)
    app.include_router(auth_ext_stub_router)
    app.include_router(smelter_stub_router)
```

### Pattern 2: `importlib.metadata.entry_points()`

**What:** Drop-in replacement for `pkg_resources.iter_entry_points()`.
**When to use:** Python 3.9+ — returns a `SelectableGroups` object; calling with `group=` kwarg returns the selection directly.

```python
# Python 3.12 (confirmed in worktree pycache naming)
from importlib.metadata import entry_points
plugins = list(entry_points(group="axiom.ee"))
```

Note: On Python 3.9-3.11, `entry_points()` returns a dict; on 3.12+ it returns a `SelectableGroups` object that supports `group=` kwarg natively. The `entry_points(group="axiom.ee")` form works correctly on 3.12+ (confirmed by pycache filename `cpython-312`).

### Pattern 3: `pytest_collection_modifyitems` skip hook

**What:** Hook in `conftest.py` that skips items marked `ee_only` when EE package is absent.
**When to use:** Registered in the session-level conftest so it applies to all test collection.

```python
# Source: pytest docs pattern
import importlib.metadata

def pytest_collection_modifyitems(config, items):
    try:
        importlib.metadata.version("axiom-ee")
        ee_installed = True
    except importlib.metadata.PackageNotFoundError:
        ee_installed = False

    if not ee_installed:
        skip_ee = pytest.mark.skip(reason="EE package not installed")
        for item in items:
            if item.get_closest_marker("ee_only"):
                item.add_marker(skip_ee)
```

### Pattern 4: Simplified `PollResponse` without `NodeConfig`

**What:** `PollResponse` carries `env_tag` directly; `NodeConfig` model deleted entirely.
**Current state (to be removed):**
```python
# models.py:105-114 — CURRENT (broken)
class NodeConfig(BaseModel):
    concurrency_limit: int
    job_memory_limit: str
    job_cpu_limit: Optional[str] = None
    tags: Optional[List[str]] = None
    env_tag: Optional[str] = None

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    config: NodeConfig
```

**Target state:**
```python
# models.py — TARGET
class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    env_tag: Optional[str] = None
```

**`node.py` consumer update:** Currently at line 770-777, `node.py` reads `config = job_data.get("config", {})` and then `config.get("concurrency_limit", 5)` etc. After the fix, `node.py` reads `pushed_tag = job_data.get("env_tag")` directly. The `concurrency_limit` and `job_memory_limit` fields on `NodeAgent` (lines 362-363) stay — they come from env vars, not from the poll response.

### Anti-Patterns to Avoid

- **Modifying `main.py` for CE/EE switching:** All stub mounting logic must stay inside `load_ee_plugins()`. `main.py` already imports `NodeConfig` from models — that import must be removed when `NodeConfig` is deleted.
- **Keeping `NodeConfig` as an empty model:** The CONTEXT.md decision is to remove it entirely, not stub it out.
- **Using `pkg_resources` as a fallback:** Remove the import completely; `importlib.metadata` is stdlib.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EE detection in conftest | Custom env-var check | `importlib.metadata.PackageNotFoundError` catch | Official stdlib pattern; consistent with GAP-02 fix |
| Pytest marker registration | Runtime `ini_options` patch | `pyproject.toml [tool.pytest.ini_options] markers` | pytest native config; prevents `PytestUnknownMarkWarning` |
| Stub 402 responses | Custom exception handlers | `JSONResponse(status_code=402, ...)` | Already established in all 7 stub files; consistent |

## Common Pitfalls

### Pitfall 1: `main.py` still imports `NodeConfig`
**What goes wrong:** After deleting `NodeConfig` from `models.py`, `main.py` line 23 still imports it (`from .models import ... NodeConfig, PollResponse ...`). The service will crash at import time.
**Why it happens:** `models.py` and the import list in `main.py` must be updated together.
**How to avoid:** Grep for `NodeConfig` across the entire worktree before closing the task.
**Warning signs:** `ImportError: cannot import name 'NodeConfig'` at startup.

### Pitfall 2: `test_db.py` and other CE test fixtures still pass `role=`
**What goes wrong:** `test_db.py:7`, `test_scheduler_service.py:13`, and `test_signature_service.py:11` all construct `User(... role="admin")`. This is NOT `test_bootstrap_admin.py` — GAP-04 is broader than just `bootstrap_admin.py`.
**Why it happens:** CONTEXT.md focuses on `bootstrap_admin.py` as the named file, but the underlying issue is any CE test file that references `User.role`.
**How to avoid:** Grep for `role=` on `User(` constructions across `puppeteer/agent_service/tests/` AND `puppeteer/tests/` before marking GAP-04 done.
**Warning signs:** `TypeError: User() got an unexpected keyword argument 'role'`.

### Pitfall 3: `test_bootstrap_admin.py` asserts `admin.role == "admin"`
**What goes wrong:** Even after removing `role="admin"` from `bootstrap_admin.py`, the test at line 34 asserts `admin.role == "admin"` — this will `AttributeError` on the CE `User` model.
**Why it happens:** The test file was written against the pre-split model.
**How to avoid:** Remove or replace `assert admin.role == "admin"` in `test_bootstrap_admin.py`. Also the `User(... role="admin")` constructor at line 47 needs removal.
**Warning signs:** `AttributeError: 'User' object has no attribute 'role'`.

### Pitfall 4: Stub router audit gap — `users_router.py` routes
**What goes wrong:** `ee/routers/users_router.py` has routes including `PATCH /admin/users/{username}/reset-password` and `PATCH /admin/users/{username}/force-password-change` which are NOT in `auth_ext.py` stub. If those are EE-only routes, CE will 404 instead of 402.
**Why it happens:** `auth_ext.py` covers the main user CRUD but missed the two `PATCH /admin/users/{username}/...` sub-routes.
**How to avoid:** During stub audit (part of GAP-01), compare every route in `users_router.py` against `auth_ext.py` stubs and add missing stubs.
**Warning signs:** `curl /admin/users/foo/reset-password` returns 404 on CE, not 402.

### Pitfall 5: `node.py` concurrency gate still references removed fields
**What goes wrong:** After removing `NodeConfig`, `node.py` line 763 still checks `len(self.active_tasks) >= self.concurrency_limit` and line 773 tries `config.get("concurrency_limit", 5)`. The concurrency check itself is fine (it uses the instance variable), but the config parsing block at lines 770-777 must be updated.
**Why it happens:** The concurrency limit is still an instance variable set from env var at init (line 362) — this is fine to keep. What must be removed is the poll-response-driven update of `self.concurrency_limit` and `self.job_memory_limit` from `config` dict.
**How to avoid:** Replace the entire config block (lines 770-777) with just the env_tag extraction from the flat `job_data` dict.

### Pitfall 6: FastAPI duplicate route shadowing
**What goes wrong:** If stub routers are mounted AFTER an EE plugin registers the real routes (or vice versa), FastAPI silently shadows one route behind the other — the first registered wins.
**Why it happens:** FastAPI route registration is order-dependent and does not deduplicate.
**How to avoid:** `_mount_ce_stubs()` is only called in the CE path (no plugins found / plugin load failed). Never call it when plugins are present. The STATE.md accumulated context note confirms: stubs guarded by `if not ctx.{feature}:` after `register()` is an alternative approach, but CONTEXT.md decision is simpler — only mount stubs when no EE plugin found.

## Code Examples

Verified from direct inspection of worktree files:

### Current `load_ee_plugins()` — GAP-01 + GAP-02 target
```python
# Source: .worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py (current)
def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    ctx = EEContext()
    try:
        import pkg_resources                                        # GAP-02: remove this
        plugins = list(pkg_resources.iter_entry_points("axiom.ee")) # GAP-02: replace
        if plugins:
            for ep in plugins:
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            # GAP-01: _mount_ce_stubs(app) MISSING here
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        # GAP-01: _mount_ce_stubs(app) MISSING here
    return ctx
```

### Current `pyproject.toml` pytest config — GAP-03 target
```toml
# Source: .worktrees/axiom-split/pyproject.toml (current)
[tool.pytest.ini_options]
pythonpath = ["puppeteer"]
asyncio_mode = "auto"
# GAP-03: markers = [...] MISSING
```

### Current `bootstrap_admin.py` — GAP-04 target
```python
# Source: .worktrees/axiom-split/puppeteer/bootstrap_admin.py:20-24 (current)
admin_user = User(
    username="admin",
    password_hash=get_password_hash(admin_pwd),
    role="admin"    # GAP-04: CE User has no role column — remove this
)
```

### Current `NodeConfig` + `PollResponse` — GAP-05 target
```python
# Source: .worktrees/axiom-split/puppeteer/agent_service/models.py:105-114 (current)
class NodeConfig(BaseModel):       # GAP-05: delete entire class
    concurrency_limit: int
    job_memory_limit: str
    job_cpu_limit: Optional[str] = None
    tags: Optional[List[str]] = None
    env_tag: Optional[str] = None

class PollResponse(BaseModel):
    job: Optional[WorkResponse] = None
    config: NodeConfig             # GAP-05: replace with env_tag: Optional[str] = None
```

### Current `job_service.py` TAMPERED path — GAP-06 target
```python
# Source: job_service.py:173-178 (current)
node_config = NodeConfig(
    concurrency_limit=0,           # GAP-06: EE workaround — remove entirely
    job_memory_limit=memory,
    tags=JobService._get_effective_tags(node)
)
return PollResponse(job=None, config=node_config)
# GAP-06 target: return PollResponse(job=None)
```

### Current `node.py` config consumption — GAP-05/06 target
```python
# Source: node.py:770-777 (current)
config = job_data.get("config", {})
if config:
    global _current_env_tag
    self.concurrency_limit = config.get("concurrency_limit", 5)      # remove
    self.job_memory_limit = config.get("job_memory_limit", ...)       # remove
    pushed_tag = config.get("env_tag")
    if pushed_tag is not None and pushed_tag != _current_env_tag:
        _current_env_tag = pushed_tag
# GAP-05/06 target: read job_data.get("env_tag") directly; remove concurrency_limit/job_memory_limit lines
```

## Stub Router Audit (GAP-01)

**7 EE routers** (in `ee/routers/`): `foundry_router.py`, `audit_router.py`, `webhooks_router.py`, `trigger_router.py`, `users_router.py`, `smelter_router.py`, `auth_ext_router.py`

**Corresponding stub files** (in `ee/interfaces/`): `foundry.py`, `audit.py`, `webhooks.py`, `triggers.py`, `smelter.py`, `auth_ext.py`

**Note:** There is NO `users.py` stub router. `users_router.py` routes are partially covered by `auth_ext.py` (which stubs `/admin/users` CRUD and `/admin/roles/` routes) but is MISSING:
- `PATCH /admin/users/{username}/reset-password`
- `PATCH /admin/users/{username}/force-password-change`

These two routes must be added to `auth_ext.py` (or a new `users.py` stub) during the GAP-01 stub audit.

**`rbac.py` and `resource_limits.py` in interfaces** are NOT router stubs — they are class-based non-HTTP interfaces. They do not need to be included in `_mount_ce_stubs()`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources.iter_entry_points()` | `importlib.metadata.entry_points(group=...)` | Python 3.9 (pkg_resources deprecated) | Removes `setuptools` runtime dependency for entry point discovery |
| pytest `setup.cfg` / `pytest.ini` markers | `pyproject.toml [tool.pytest.ini_options] markers` | pytest 6+ | Single config file; eliminates `PytestUnknownMarkWarning` |

**Deprecated/outdated:**
- `pkg_resources`: Part of `setuptools`, soft-deprecated. `importlib.metadata` is the stdlib replacement since Python 3.8 (full parity in 3.9+). Python 3.12 in use (confirmed by pycache filenames).

## Open Questions

1. **`test_db.py` role references — are they to be fixed or made `ee_only`?**
   - What we know: `test_db.py:7` tests `User(role="admin")` which will `AttributeError` on CE. This is a CE test (no `ee_only` marker candidate).
   - What's unclear: Should the test be removed, or changed to not pass `role=`? The `User.role` assertion at line 13 (`assert fetched_user.role == "admin"`) can't be salvaged in CE.
   - Recommendation: Remove `role="admin"` from constructor; remove `assert fetched_user.role` assertion. The test becomes a simple "can I insert and retrieve a User" test — still valid.

2. **`test_scheduler_service.py` and `test_signature_service.py` role fixtures**
   - What we know: Both use `User(... role="admin")` in fixtures for passing to service calls.
   - What's unclear: If the services being tested don't check `user.role`, the fix is just removing the `role=` kwarg.
   - Recommendation: Remove `role="admin"` from fixtures. If any service call fails because it reads `user.role`, that service call is EE-only and the test should be marked `ee_only`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (confirmed by pycache) |
| Config file | `pyproject.toml` at `.worktrees/axiom-split/pyproject.toml` |
| Quick run command | `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -m "not ee_only" -x -q` |
| Full suite command | `cd .worktrees/axiom-split && pytest -m "not ee_only" -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAP-01 | All EE routes return 402 on CE | integration (HTTP) | `pytest puppeteer/agent_service/tests/test_main.py -k "402 or stub" -x` | ✅ (test_main.py exists; may need new test case) |
| GAP-02 | `load_ee_plugins()` uses importlib.metadata | unit | `pytest puppeteer/agent_service/tests/ -k "ee_plugin" -x` | ❌ Wave 0 |
| GAP-03 | `ee_only` tests skip automatically | unit (marker) | `pytest puppeteer/agent_service/tests/ -m "not ee_only" -v` | ❌ Wave 0 (4 placeholders needed) |
| GAP-04 | CE pytest suite has zero `User.role` errors | unit | `pytest puppeteer/agent_service/tests/ puppeteer/tests/ -m "not ee_only" -x` | ✅ (existing tests, to be fixed) |
| GAP-05 | `NodeConfig` absent from models | unit | `pytest puppeteer/agent_service/tests/test_models.py -x` | ✅ (test_models.py exists) |
| GAP-06 | Job dispatch completes full cycle without AttributeError | unit | `pytest puppeteer/agent_service/tests/test_job_service.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -m "not ee_only" -x -q`
- **Per wave merge:** `cd .worktrees/axiom-split && pytest -m "not ee_only" -q`
- **Phase gate:** Full suite green (zero failures, zero `EE-attribute` errors) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/agent_service/tests/test_lifecycle_enforcement.py` — covers GAP-03 (ee_only placeholder)
- [ ] `puppeteer/agent_service/tests/test_foundry_mirror.py` — covers GAP-03 (ee_only placeholder)
- [ ] `puppeteer/agent_service/tests/test_smelter.py` — covers GAP-03 (ee_only placeholder)
- [ ] `puppeteer/agent_service/tests/test_staging.py` — covers GAP-03 (ee_only placeholder)
- [ ] New test for `load_ee_plugins()` CE path (GAP-01 + GAP-02 verification)

## Sources

### Primary (HIGH confidence)
- Direct inspection of `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — current `load_ee_plugins()` implementation
- Direct inspection of `.worktrees/axiom-split/puppeteer/agent_service/ee/interfaces/` — all 8 interface files audited
- Direct inspection of `.worktrees/axiom-split/puppeteer/agent_service/models.py` — `NodeConfig` + `PollResponse` confirmed
- Direct inspection of `.worktrees/axiom-split/puppeteer/agent_service/services/job_service.py` — all `NodeConfig` construction sites confirmed
- Direct inspection of `.worktrees/axiom-split/puppets/environment_service/node.py` — config consumption confirmed
- Direct inspection of `.worktrees/axiom-split/puppeteer/bootstrap_admin.py` — `role="admin"` confirmed
- Direct inspection of `.worktrees/axiom-split/puppeteer/agent_service/db.py:88-93` — CE `User` has no `role` column
- Direct inspection of `.worktrees/axiom-split/pyproject.toml` — no `markers` config confirmed

### Secondary (MEDIUM confidence)
- Python 3.12 pycache filenames (`cpython-312`) — confirms Python version in worktree
- `importlib.metadata.entry_points(group=...)` API — standard Python docs, no verification needed

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already installed; no new deps
- Architecture: HIGH — code inspected directly; no inference required
- Pitfalls: HIGH — derived from direct code inspection of the exact files being changed

**Research date:** 2026-03-19
**Valid until:** Stable — these are bug fixes to existing code in a feature branch; no fast-moving dependencies

# Pitfalls Research

**Domain:** Open-core CE/EE split — Cython/Nuitka `.so` compilation, entry_points plugin discovery, FastAPI plugin router registration, SQLAlchemy CE/EE model separation, open-core licence key enforcement in a self-hosted Python product
**Researched:** 2026-03-19
**Confidence:** HIGH (codebase directly inspected — `ee/__init__.py`, `ee/interfaces/foundry.py`, `ee/routers/foundry_router.py`, `main.py`, `db.py` all read in the `feature/axiom-oss-ee-split` worktree; confirmed against codebase reality, not assumed)

---

## Critical Pitfalls

### Pitfall 1: Stub Routers Never Mounted — CE Falls Through to 404, Not 402

**What goes wrong:**
The CE stub routers (`foundry_stub_router`, `audit_stub_router`, etc.) are defined in `ee/interfaces/*.py` but are never registered on the FastAPI `app`. `load_ee_plugins()` in `ee/__init__.py` calls `plugin.register(ctx)` on the EE plugin when EE is installed, but has no fallback to mount the CE stub routers when no EE plugin is found. In CE-only mode, requests to EE routes (e.g., `GET /api/blueprints`) return `404 Not Found` (no route registered) instead of `402 Payment Required` (upgrade prompt). The `"Looks Done But Isn't"` trap: the stubs exist in the codebase, so it looks like CE graceful degradation is implemented — but without `app.include_router(foundry_stub_router)`, none of the stubs are active.

**Why it happens:**
The Phase 1 scaffold created the stub router objects. Phase 2 extracted the EE router files. Neither phase wired the stubs into `app`. The gap is invisible unless you actually start CE and call an EE endpoint — `GET /api/features` returns correctly, but any attempt to actually use a feature returns 404 instead of the expected 402.

**How to avoid:**
`load_ee_plugins()` must register CE stub routers unconditionally as a first step, then either override them with EE real routers (if EE is installed) or leave the stubs in place. The correct pattern:
```python
# In load_ee_plugins(), before entry_points discovery:
from .interfaces.foundry import foundry_stub_router
from .interfaces.audit import audit_stub_router
# ... all stub routers
app.include_router(foundry_stub_router)
app.include_router(audit_stub_router)
# ...

# Then, if EE plugin found, it calls app.include_router(real_foundry_router)
# which adds real routes FIRST — FastAPI resolves first-registered route for a path.
```
Wait: FastAPI matches routes in registration order and adds routes to a list — the first registered route for a path wins. If stubs are added first and EE adds the real router second, the stubs shadow the real routes. **The correct pattern is: EE plugin registers real routers first (EE `register()` runs before stub fallback).** Only mount stubs for routes that EE did NOT register. Track this via the `EEContext` flags:
```python
if not ctx.foundry:
    app.include_router(foundry_stub_router)
```

**Warning signs:**
- `GET /api/blueprints` in CE returns 404 (not 402).
- `load_ee_plugins()` has no `app.include_router(...)` calls for the stub routers.
- The `EEContext` flags are set but never used to decide which routers to mount.

**Phase to address:** Phase 5 (private repo + router migration) — this is the known blocking gap. Fix in the very first step of Phase 5 before testing CE-alone install.

---

### Pitfall 2: FastAPI Duplicate Route Registration When EE Routers and Stub Routers Both Mount the Same Paths

**What goes wrong:**
If both the CE stub router and the EE real router for the same feature are mounted on the app (e.g., due to a conditional logic bug), FastAPI silently registers both sets of routes. FastAPI matches routes in first-registration order. The second registration does not raise an error — it emits `UserWarning: Duplicate Operation ID` in the OpenAPI schema generation only. In CE+EE mode this means the stub route (402) shadows the real route (200) if stubs are mounted first. In CE-only mode it means duplicate 402 handlers (harmless but confusing in logs).

The specific failure: `load_ee_plugins()` correctly calls `plugin.register(ctx)` which mounts EE routers, but if someone also calls `app.include_router(foundry_stub_router)` unconditionally elsewhere (e.g., during startup debug), both route sets exist. Requests get the stub 402 despite EE being installed.

**Why it happens:**
The silent-addition behavior of FastAPI's `include_router` is not obvious. Developers test the CE stub manually (by calling `app.include_router(foundry_stub_router)` directly to see if 402 works), leave the call in, then find EE always returns 402 when installed.

**How to avoid:**
- Guard every stub registration with `if not ctx.{feature}:` — only mount stubs for features EE did not claim.
- Add a startup assertion: after `load_ee_plugins()`, verify that the routes registered on `app.routes` for each EE path match the expected handler (stub vs real) based on the `EEContext` flags. A 5-line debug log at startup is enough.
- Never call `app.include_router(stub_router)` without the guard — the guard is the invariant, not an afterthought.

**Warning signs:**
- Application startup logs show `UserWarning: Duplicate Operation ID` for any Foundry, Audit, or Webhook route.
- EE is installed but `/api/blueprints` returns 402.
- `GET /api/features` shows `"foundry": true` but GET `/api/blueprints` returns 402.

**Phase to address:** Phase 5 (router migration) — define the registration guard pattern before the EE plugin `register()` method is written, so the protocol is clear.

---

### Pitfall 3: `pkg_resources.iter_entry_points` Is Deprecated and Slow — Use `importlib.metadata`

**What goes wrong:**
The current `ee/__init__.py` uses `pkg_resources.iter_entry_points("axiom.ee")`. `pkg_resources` scans all installed packages on import — in environments with many packages (a typical Python environment has 100+ packages), importing `pkg_resources` alone can take several seconds. More critically, `pkg_resources` is deprecated in favour of `importlib.metadata` as of setuptools 67+ (2023). It will not be removed immediately but is a maintenance liability. When `axiom-ee` is compiled to `.so` (Phase 6), `pkg_resources` has known issues discovering entry_points from compiled extensions in some configurations.

The other problem: the current code wraps the entire discovery in a bare `except Exception`, silently swallowing any import error from the EE `.so`. If the `.so` fails to load (ABI mismatch, missing dependency, wrong Python version), the system continues in CE mode with no log entry beyond a generic warning. Operators cannot distinguish "EE not installed" from "EE installed but broken."

**Why it happens:**
`pkg_resources` was the standard tool for entry_points discovery for a decade. Many tutorials still reference it. The deprecation is recent enough that existing code predates it.

**How to avoid:**
Replace `pkg_resources.iter_entry_points` with `importlib.metadata.entry_points`:
```python
from importlib.metadata import entry_points
eps = entry_points(group="axiom.ee")
```
This API is stable from Python 3.9+ (Python 3.12 standardised the `group=` keyword form). For Python 3.8 compatibility, use the `importlib_metadata` backport or the `select()` workaround.

Tighten the exception handling:
```python
try:
    plugin_cls = ep.load()
    plugin = plugin_cls(app, engine)
    plugin.register(ctx)
    logger.info(f"Loaded EE plugin: {ep.name} from {ep.value}")
except ImportError as e:
    logger.error(f"EE plugin {ep.name} failed to import: {e} — running in CE mode")
except Exception as e:
    logger.error(f"EE plugin {ep.name} register() raised: {e} — running in CE mode")
```
Log the `ep.value` (the dotted module path) so operators can see which `.so` file was being loaded when it failed.

**Warning signs:**
- `from importlib import pkg_resources` or `import pkg_resources` in `ee/__init__.py`.
- Exception handling catches `Exception` without logging the `ep.name` and error detail.
- No log difference between "EE not installed" and "EE installed but failed to load."

**Phase to address:** Phase 5 (private repo setup) — fix before validating CE-alone and CE+EE installs, so test output is interpretable.

---

### Pitfall 4: Cython Compilation Breaks `@dataclass` — `__annotations__` Stripped

**What goes wrong:**
Cython strips `__annotations__` from class bodies when compiling to `.so`. The `@dataclass` decorator in Python relies entirely on `cls.__annotations__` to discover fields. When a `@dataclass`-decorated class is compiled by Cython, `__annotations__` is empty or absent, and `dataclass()` generates an `__init__` that takes only `self` — regardless of what fields are declared. The symptom is: `TypeError: __init__() takes 1 positional argument but N were given` when constructing any dataclass instance at runtime, even though the Python source looks correct.

The Axiom EE plugin code will likely use `@dataclass` for configuration objects, response models, or plugin state containers. The `EEContext` dataclass in CE's `ee/__init__.py` uses `@dataclass` — any EE code that imports and extends this, or defines its own `@dataclass` types, will fail after compilation. This is a confirmed Cython bug (GitHub issue #3336, reported against Cython 0.x and partially fixed in Cython 3 but not fully resolved for all decorator patterns).

**Why it happens:**
Cython's extension type system and Python's annotation system are distinct. Cython 3 improved support but `@dataclass` with certain decorator combinations (e.g., `@dataclass` applied after another decorator, or `@dataclass` on a class with `cdef` attributes) still strips `__annotations__`. The fix in Cython 3 covers the simple `@dataclass class Foo:` case but not all patterns.

**How to avoid:**
Three safe strategies (pick one per module):
1. **Avoid `@dataclass` in compiled modules.** Use plain classes with explicit `__init__`. This is the simplest and most reliable approach for EE code.
2. **Use Cython's native dataclass support.** In `.pyx` mode: `@cython.dataclasses.dataclass` with `cimport cython` — this generates Cython-native struct-backed fields. Only viable if the module is written as `.pyx`, not pure Python.
3. **Compile with `--directive annotation_typing=False`** (Cython directive) to prevent Cython from interpreting annotations as type declarations — this preserves `__annotations__` for `@dataclass` introspection. Add to `setup.cfg`: `[cython-compile] compiler_directives = annotation_typing=False`.

For the Axiom EE split specifically: Pydantic models (used throughout for FastAPI request/response) are NOT standard `@dataclass` — Pydantic has its own metaclass that does not rely on `__annotations__` in the same way. Pydantic v2 models compile through Cython without this issue. Only standard-library `@dataclass` and `typing.TypedDict` patterns are affected.

**Warning signs:**
- EE module uses `@dataclass` on configuration or state holder classes.
- `from dataclasses import dataclass` import in any EE module that will be compiled.
- `TypeError: __init__() takes 1 positional argument` in EE plugin test after compiling to `.so`.
- `dir(MyCompiledClass)` shows no `__annotations__` attribute.

**Phase to address:** Phase 6 (`.so` build pipeline) — audit all EE modules for `@dataclass` usage before setting up the Cython build. Replace with explicit `__init__` in all compiled modules.

---

### Pitfall 5: Cython Compiled `.so` Breaks `__file__`-Relative Resource Loading and Relative Imports

**What goes wrong:**
Two distinct failures:

**A) `__file__` path changes.** When compiled to `.so`, `module.__file__` is set to the absolute path of the `.so` file (e.g., `/site-packages/ee/plugin.cpython-312-x86_64-linux-gnu.so`), not a `.py` file. Any code that uses `os.path.dirname(__file__)` to locate data files or template resources will get the correct directory — this part works. However, `importlib.resources.files(__name__)` may fail if the package is not structured as a proper package (has no `__init__` module in the same directory). The failure mode is `ModuleNotFoundError` or returning an empty traversable at runtime.

**B) Relative imports in compiled `__init__` modules.** If the EE plugin package has a compiled `__init__.so` (i.e., `__init__.py` is also compiled), relative imports from within that module (e.g., `from .plugin import EEPlugin`) may fail with `ImportError: attempted relative import with no known parent package`. This is a CPython issue (bug #59828) that manifests specifically when `__init__` is a `.so` file rather than `.py`. Relative imports in non-`__init__` modules are not affected.

**Why it happens:**
Python's import system sets `__package__` based on `__spec__` when importing. For `.so` extension modules, `__spec__` is correctly populated as long as the package is properly installed. The failure occurs when the package is imported in a non-standard way (e.g., added to `sys.path` directly rather than installed via pip). During development or CI testing of the `.so` before formal install, this is a common path.

**How to avoid:**
- **Do not compile `__init__.py`** of the EE plugin package. Leave `__init__.py` as a plain `.py` file that imports from compiled submodules. This sidesteps the `__init__.so` relative import bug entirely.
- Structure the EE package so `__init__.py` contains only the entry point class definition and imports:
  ```python
  # ee_plugin/__init__.py  — NOT compiled
  from .core import EEPlugin  # core.so can be compiled
  ```
- Avoid `importlib.resources.files()` for locating files within the compiled package. Use `importlib.resources.files(__name__).joinpath("data_file.json")` only if there is a non-compiled `__init__.py` in the package directory. Alternatively, bundle data files as string constants compiled into the `.so`.
- Always test `.so` loading via `pip install dist/axiom_ee-*.whl` in a clean virtualenv before running CI against it — this matches the real install path and surfaces relative import failures.

**Warning signs:**
- The EE plugin entry point in `setup.cfg` points to `ee.plugin:EEPlugin` where `ee/__init__.py` is compiled to `__init__.so`.
- `importlib.resources.files("ee")` raises `ModuleNotFoundError` in the compiled version.
- CI tests the `.so` by adding the build directory to `sys.path` rather than installing the wheel.
- Relative imports in any compiled `__init__.so` module.

**Phase to address:** Phase 6 (`.so` build pipeline) — define the package structure constraint (never compile `__init__.py`) before writing any compilation CI.

---

### Pitfall 6: EE DB Models Must Share the CE `Base` — Two `DeclarativeBase` Instances = Missing Tables

**What goes wrong:**
SQLAlchemy's `Base.metadata.create_all(engine)` creates only tables registered in that `Base`'s metadata. If the EE plugin defines its models using a separate `Base = DeclarativeBase()` (its own `DeclarativeBase` instance), those models are registered in a different `MetaData` object. The CE startup calls `Base.metadata.create_all(engine)` using the CE `Base` — the EE tables are never created. The failure mode is: EE plugin loads successfully, routes are registered, but the first DB query on an EE table raises `OperationalError: no such table: audit_log`.

The inverse problem also exists: if the EE `Base` creates tables that reference CE tables via `ForeignKey` (e.g., `audit_log.user_id → users.id`), and the FK uses the string form `"users.id"`, the FK resolution fails silently if the `users` table is not in the EE `Base`'s metadata — the FK is unresolvable at `create_all` time and either raises an error or is silently dropped depending on the DB dialect.

**Why it happens:**
The EE plugin is a separate Python package. It is natural to define a `Base = DeclarativeBase()` inside the EE package without importing it from CE. The symptom does not appear in development if the EE package is always installed alongside CE and the developer always does a fresh DB (where `create_all` runs against a clean database and the EE-installed state is present at startup).

**How to avoid:**
The EE plugin must import `Base` from the CE package, not define its own:
```python
# In axiom-ee: ee/models/audit.py
from agent_service.db import Base  # CE's Base — the only Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    ...
```
This means the EE package has a runtime dependency on the CE package (which is correct — EE extends CE, not the reverse). The `plugin.register(app, engine)` call receives the CE `engine` and can call `Base.metadata.create_all(engine)` — but since CE already called it at startup, EE only needs to call it if new tables were added by the EE models (i.e., EE tables not yet in the DB).

For the EE `register()` method: call `Base.metadata.create_all(engine)` explicitly in `register()` to create any EE tables that did not exist before EE was installed on a running CE deployment:
```python
def register(self, ctx):
    from agent_service.db import Base
    Base.metadata.create_all(self.engine)  # idempotent — skips existing tables
    # then mount routers...
```

**Warning signs:**
- EE plugin package contains `Base = DeclarativeBase()` in any `db.py` or `models.py` file.
- `OperationalError: no such table: audit_log` on first EE request after install.
- EE `ForeignKey` strings reference CE tables but FK resolution fails at metadata creation.
- `create_all` is never called in the EE `register()` method.

**Phase to address:** Phase 5 (private repo setup) — define the `Base` sharing contract as the first architectural decision before writing any EE model code.

---

### Pitfall 7: Licence Key Validation at Startup Only — EE Features Work After Key Expiry

**What goes wrong:**
A common pattern in open-core plugins is to validate the licence key once at startup (in `register()`), set a flag, and never check again. This means:
1. A valid key at startup → EE features enabled for the lifetime of the process.
2. If the process runs for weeks (Docker container restart policy: `unless-stopped`), the licence can expire without EE features being disabled. Customers get months of free EE after their licence expires simply by not restarting their container.
3. Conversely: clock skew on the host (NTP drift, container time not synced) causes valid licences to fail validation if expiry is checked against wall clock time with no tolerance.

For self-hosted deployments specifically: any online licence validation call (to `api.axiom.run/v1/licence/validate`) will be blocked in air-gapped deployments. If the EE plugin does not support offline licence files, air-gapped customers cannot use EE.

**Why it happens:**
Startup validation is the simplest pattern. Clock-based expiry without tolerance is the first implementation that comes to mind. Online-only validation is what most SaaS-focused licence libraries default to.

**How to avoid:**
- **Periodic re-validation**: re-check the licence every N hours (e.g., every 12 hours) via a background task. If re-validation fails (key expired, network unreachable), log a warning but do not disable EE features immediately — give a grace period (e.g., 7 days of offline tolerance) to avoid disrupting air-gapped deployments.
- **Cryptographic offline licence files**: Sign licence files with an Ed25519 key whose private key never leaves `api.axiom.run`. The EE plugin bundles only the Ed25519 public key (compiled into the `.so`). Validation is entirely offline — parse the licence file, verify the signature against the embedded public key, check expiry with a `±5 minute` clock tolerance. Axiom already has Ed25519 infrastructure (job signing) — reuse the same `cryptography` library pattern.
- **Licence file format**: `{customer_id, features[], expiry_utc, issued_utc, signature}` as a signed JSON blob. The `features` array allows per-customer entitlement (e.g., `["rbac", "foundry"]` but not `["smelter"]`).
- **Never hardcode the public key as a plain string** — compiled `.so` files can be reversed with `strings(1)` or `objdump`. Use a constant array of bytes, split across multiple variables, reassembled at validation time. This is obfuscation only (not real security), but it raises the cost of casual key extraction.
- **Bypass pattern to protect against**: the most common self-hosted bypass is clock manipulation — set system time to before expiry. Mitigation: compare licence `issued_utc` against system time (system time must be >= issued_utc); if system time is before the issue date, treat as clock manipulation and reject.

**Warning signs:**
- `register()` calls `validate_licence()` once and stores a boolean flag — no periodic re-check.
- Licence validation makes an outbound HTTP call with no offline fallback.
- Licence expiry check uses `datetime.utcnow() > expiry` with no clock tolerance.
- Ed25519 public key stored as a plain ASCII string constant in the compiled module.

**Phase to address:** Phase 7 (documentation and licensing) — define the offline cryptographic licence file format before Phase 6 (compilation), so the licence validation code is designed with compilation constraints in mind from the start.

---

### Pitfall 8: EE-Only Tests Fail in CE CI — Test Suite Not Isolated

**What goes wrong:**
The CE test suite currently contains tests that import EE models, EE router handlers, or EE DB columns directly. After Phase 3 stripped EE models from `db.py`, these tests fail with `ImportError` or `AttributeError: User has no attribute 'role'`. The plan notes `Fix CE test suite — isolate EE-only tests, fix test_bootstrap_admin.py User.role refs` as a blocking gap.

The less obvious problem: if EE-only tests are simply deleted from the CE test suite (not moved to the EE private repo), the EE router code has no tests at all in any repo. EE code coverage goes to zero. The correct fix is to move EE tests to the `axiom-ee` private repo where they run against a CE+EE install.

A second failure mode: tests that use CE's `Base` fixtures (e.g., a conftest.py that creates tables with `create_all`) will not create EE tables even if EE is installed at test time — because the test fixture runs `create_all` at the start of the test session, before `load_ee_plugins()` is called. EE table queries in integration tests fail with `OperationalError`.

**Why it happens:**
Tests were written against the pre-split codebase where all models existed in `db.py`. The split happened in phases; tests were not updated in lockstep. Test fixtures that mirror the startup sequence may not replicate the `load_ee_plugins()` → `create_all()` ordering.

**How to avoid:**
- CE test suite must import only from `agent_service.db` (CE models only) and `agent_service.models` (CE Pydantic models only). Any test importing from `agent_service.ee` must be tagged `@pytest.mark.ee` and skipped in CE CI: `pytest -m "not ee"`.
- For integration tests that need a full CE+EE stack: maintain a separate test configuration in the `axiom-ee` repo with a `conftest.py` that installs EE, calls `load_ee_plugins()`, then runs `create_all()`.
- `test_bootstrap_admin.py` specifically: the `User.role` attribute was removed from CE. Fix: either remove the role assertion entirely (CE has no roles), or add a `pytest.importorskip("ee")` guard.

**Warning signs:**
- `pytest` fails in CE CI with `AttributeError: type object 'User' has no attribute 'role'`.
- Any test file imports `from agent_service.ee.routers import ...` without an EE skip guard.
- CE test suite passes locally (developer has EE installed) but fails in CI (clean CE-only environment).
- `conftest.py` uses `Base.metadata.create_all(engine)` without calling `load_ee_plugins()` first — EE tables never created in test DB.

**Phase to address:** Phase 5 (private repo setup) — fix CE test isolation as step 0, before validating CE-alone install. Otherwise "CE tests pass" is misleading.

---

### Pitfall 9: Circular Import Between CE `main.py` → `ee/__init__.py` → CE `db.py`

**What goes wrong:**
The current import chain is: `main.py` imports `from .db import ...` (CE models) and also imports `from .ee import load_ee_plugins`. Inside `load_ee_plugins`, the EE plugin's `register()` calls `from agent_service.db import Base` to extend CE's Base. This is safe as long as `db.py` is fully initialized before `ee/__init__.py` is imported.

The risk: if any code path within the EE plugin module (not inside `register()`, but at module level) imports from `agent_service.main` (e.g., to access `app` directly, or to access a utility defined in `main.py` rather than a service), a circular import occurs: `main.py` → `ee/__init__.py` → `ee.plugin` → `agent_service.main` → already being loaded. Python's import system partially initializes `main` and returns the incomplete module, causing `ImportError: cannot import name 'X' from partially initialized module 'agent_service.main'`.

The specific trigger in Axiom: `deps.py` contains `require_permission` and `get_current_user`. The EE router files import from `...deps`. `deps.py` imports from `...auth` and `...db`. This chain is safe. But if any EE router imports from `...main` (even accidentally via a wildcard or re-export), the circular import activates.

**Why it happens:**
Large FastAPI applications tend to accumulate utilities in `main.py` that should be in service files. EE router authors reaching for a utility may grab it from `main` rather than tracing it back to its proper module.

**How to avoid:**
- Enforce the rule: EE plugin code must never import from `agent_service.main`. All shared utilities must live in `agent_service.deps`, `agent_service.auth`, `agent_service.security`, or `agent_service.services.*`.
- Add a test: `import agent_service.ee.plugin` in isolation (without importing `main`) — must succeed without error.
- In `load_ee_plugins()`, after `ep.load()`, catch `ImportError` specifically and log the full traceback (not just the message), so circular import failures are diagnosable.

**Warning signs:**
- `from ...main import ...` in any EE router file.
- `ImportError: cannot import name 'X' from partially initialized module 'agent_service.main'` in startup logs.
- EE plugin loads correctly in isolation but fails when imported as part of the full application.

**Phase to address:** Phase 5 (private repo setup) — define the import boundary rule before writing EE router code; enforce with a CI import isolation test.

---

### Pitfall 10: `NodeConfig` CE Strip Leaves Dead References in `job_service.py`

**What goes wrong:**
Phase 3 stripped `concurrency_limit`, `job_memory_limit`, and `job_cpu_limit` from the CE `NodeConfig` Pydantic model. But `job_service.py` references these fields in the node selection and admission control logic (memory limit checking, concurrency limit enforcement). After the strip, the fields are absent from the model — accessing `node.concurrency_limit` raises `AttributeError` if the field was removed from both the Pydantic model and the DB schema, or returns `None` silently if only the Pydantic model was changed but the DB column still exists.

The silent `None` case is the dangerous one: `if job.memory_limit and node.job_memory_limit:` evaluates to `False` for both conditions (both `None`), so the admission check is silently bypassed — jobs are dispatched without any resource checking in CE.

**Why it happens:**
The CE strip was a model-level change. `job_service.py` was not audited for every reference to the stripped fields. Python does not catch attribute access on `None` as an error at parse time.

**How to avoid:**
- After stripping EE fields from CE models, run a search for all references to the stripped field names across the codebase: `concurrency_limit`, `job_memory_limit`, `job_cpu_limit`, `memory_limit`, `cpu_limit`. Every reference must either be removed or guarded with `if hasattr(node, 'concurrency_limit')`.
- The CE behaviour should be: fixed sensible defaults (e.g., concurrency = unlimited, memory = unchecked) enforced via constants, not via the node model. Replace `node.concurrency_limit or DEFAULT_CONCURRENCY` with just `DEFAULT_CONCURRENCY` in CE `job_service.py`.
- Add a CE-specific integration test: dispatch a job to a CE node; verify it is assigned without AttributeError in the server logs.

**Warning signs:**
- `grep -r "concurrency_limit\|job_memory_limit\|job_cpu_limit" puppeteer/agent_service/services/job_service.py` returns any results after the CE strip.
- `AttributeError: 'Node' object has no attribute 'concurrency_limit'` in CE server logs during job dispatch.
- CE job dispatch silently never assigns jobs (because a `None` admission check causes a false rejection).

**Phase to address:** Phase 5 gap fix step — this is listed as a blocking gap ("Strip `NodeConfig` model"). Resolve before validating CE core job dispatch.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Validate licence key only at startup | Simple one-time check | Expired licences run forever without restart; no offline grace period | Never for a commercial product — add periodic re-check |
| EE defines its own `Base = DeclarativeBase()` | No import of CE internals from EE | EE tables never created; CE `create_all` ignores them | Never — EE must share CE's `Base` |
| Keep `pkg_resources` for entry_points discovery | Already works, no code change | Deprecated, slow on large environments, known `.so` discovery issues | Acceptable short-term (fix before v12.0) |
| Compile `__init__.py` of EE package to `.so` | Maximum source code protection | Relative imports fail; harder debugging | Never — always leave `__init__.py` as `.py` |
| Delete EE tests from CE suite rather than moving them | Quick fix for CE CI | EE code has zero test coverage | Never — move tests to `axiom-ee` repo |
| Store licence public key as plain ASCII string constant | Simplest implementation | `strings(1)` on the `.so` exposes the key | Acceptable if key rotation is possible; not acceptable if key is permanent |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastAPI route registration order | Mount both stub and real router → stub shadows real (first wins) | Guard: `if not ctx.foundry: app.include_router(stub)`; EE registers real router in `register()` before guard runs |
| SQLAlchemy EE models | `Base = DeclarativeBase()` in EE package | `from agent_service.db import Base` — share the one CE Base |
| Cython `@dataclass` | Decorate class with `@dataclass`, compile → `__init__` ignores all fields | Use plain classes with explicit `__init__` in all compiled modules |
| Cython `__init__.py` compilation | Compile `__init__.py` to `__init__.so` | Never compile `__init__.py` — keep as `.py`, compile submodules only |
| entry_points discovery for `.so` | `pkg_resources.iter_entry_points()` | `importlib.metadata.entry_points(group="axiom.ee")` — Python 3.9+ built-in |
| Licence expiry in air-gapped deployments | Online validation call (blocks in air-gapped env) | Ed25519-signed offline licence file; embed public key in compiled `.so` |
| EE import of CE utilities | Import from `agent_service.main` | Import only from `agent_service.deps`, `auth`, `security`, `services.*` — never from `main` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `pkg_resources` import scans all packages | 2–5s delay on first `load_ee_plugins()` call | Switch to `importlib.metadata` (lazy, O(1) lookup) | On any environment with 50+ installed packages |
| Licence re-validation on every EE API request | Each request makes an outbound HTTP call; 50–200ms added to every EE route | Validate once at startup + periodic re-check (every 12h) via APScheduler | Immediately if online validation is per-request |
| EE `register()` calls `create_all` on every startup for large EE schema (15 tables) | `create_all` with 28 total tables takes 200–500ms on SQLite; blocks startup | `create_all` is idempotent — this is acceptable; SQLite startup cost is a known tradeoff | Never critical; just note the startup time increase |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Licence public key as plain string in `.so` | `strings(1)` or `objdump` extracts key; anyone can forge licences | Split key across multiple byte arrays; reassemble at validation time (obfuscation only, raises bypass cost) |
| Clock manipulation bypasses expiry | Set system time back → licence never expires | Check `issued_utc <= now <= expiry_utc`; if `now < issued_utc`, reject as clock manipulation |
| EE plugin silently runs in CE mode on import failure | Compiled `.so` with ABI mismatch fails silently; all EE access continues to return 402 | Log error level (not warning) with full exception on EE load failure; include `.so` path |
| CE `require_auth` (not `require_permission`) on EE routes | EE routes accessible to any authenticated user including viewers | EE `register()` must wire EE routes with `require_permission` from `deps.py`; CE `deps.py` exposes both `require_auth` (CE) and `require_permission` (EE) |
| Licence file loaded from user-writable path | Attacker replaces licence file with self-signed one using their own key | Licence file path must be in a non-writable location; validate signature against the public key compiled into the `.so` |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 404 (not 402) on EE routes in CE | Operator sees "Not Found" — assumes the feature doesn't exist or the URL is wrong | Ensure all EE routes return 402 with `{"detail": "Requires Axiom EE", "upgrade_url": "https://axiom.run/enterprise"}` |
| `GET /api/features` returns all `false` but no explanation | Operators don't know if EE is not installed or if it failed to load | Add `ee_status: "not_installed" | "loaded" | "load_failed"` to the features response; include error message when `load_failed` |
| Licence expiry not visible in dashboard | Operators don't know their licence expires until EE stops working | Add licence expiry date to `GET /api/features` response; dashboard shows amber warning 30 days before expiry |
| EE install instructions assume online pip install | Air-gapped operators can't install `axiom-ee` from PyPI | Document wheel download + offline `pip install axiom_ee-*.whl` pattern in EE docs |

---

## "Looks Done But Isn't" Checklist

- [ ] **Stub routers active in CE:** `curl https://localhost:8001/api/blueprints` on a CE-only install must return `402`, not `404`. If it returns 404, stub routers are not mounted.
- [ ] **EE routers take effect after install:** `pip install axiom-ee` in a running CE environment (followed by restart) must cause `GET /api/features` to return `"foundry": true` AND `GET /api/blueprints` to return `200` (not `402`).
- [ ] **EE tables created on first EE install:** On a CE deployment with existing data, `pip install axiom-ee` + restart must create the 15 EE tables. `\dt` (Postgres) or `.tables` (SQLite) must include `audit_log`, `role_permissions`, etc.
- [ ] **No `.py` source in EE wheel:** `unzip -l dist/axiom_ee-*.whl | grep ".py$"` must return empty (only `__init__.py` may be present, as it is intentionally not compiled).
- [ ] **Dataclasses work in compiled `.so`:** Construct every `@dataclass` (if any remain) from the compiled EE module — must not raise `TypeError: __init__() takes 1 positional argument`.
- [ ] **Relative imports work after `pip install` wheel:** `python -c "import ee; print(ee.EEPlugin)"` must succeed in a clean virtualenv where EE was installed from the wheel, not added to sys.path.
- [ ] **CE test suite passes without EE installed:** Run `pytest` in a virtualenv with `axiom-ce` only (no `axiom-ee`). Zero failures from missing EE attributes or imports.
- [ ] **Offline licence validation:** Validate a licence file with no network access (`iptables -I OUTPUT -j DROP` in a container). Must succeed if the file is within expiry and signature is valid.
- [ ] **Expired licence detection:** Set the licence file `expiry_utc` to yesterday; restart; `GET /api/features` must not show EE features as active.
- [ ] **EE load failure is visible:** Install a `.so` compiled for the wrong Python version; restart; `GET /api/features` must return `"ee_status": "load_failed"` (not silently degrade to CE with no indication).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stub routers not mounted (404 in CE) | LOW | Add `if not ctx.{feature}: app.include_router(stub_router)` in `load_ee_plugins()`; redeploy |
| Duplicate route registration (stubs shadow EE) | LOW | Remove unconditional stub `include_router` calls; ensure guard uses `EEContext` flags after `register()` runs |
| EE tables not created (wrong Base) | MEDIUM | Fix EE to import CE `Base`; manually create missing tables via `ALTER TABLE` / `CREATE TABLE IF NOT EXISTS` for existing deployments |
| `@dataclass` breaks after Cython compile | MEDIUM | Convert all affected dataclasses to plain classes with explicit `__init__`; rebuild `.so`; redeploy wheel |
| Circular import between EE and main.py | LOW | Move the imported symbol from `main.py` to a service/deps module; EE imports from there instead |
| Licence key expired, container not restarted | LOW | Issue a new licence file with updated expiry; copy to licence file path; periodic re-validation picks it up within 12h |
| CE test suite failures from EE attribute refs | LOW | Add `pytest.mark.ee` skip guards or remove EE attribute assertions from CE tests; move EE tests to private repo |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Stub routers not mounted (404 in CE) | Phase 5 first step (router wiring) | `curl /api/blueprints` on CE returns 402 |
| Duplicate route registration | Phase 5 (registration guard pattern defined) | `GET /api/features` = foundry:true + `GET /api/blueprints` = 200 when EE installed |
| `pkg_resources` deprecated / slow | Phase 5 (private repo setup) | Startup time < 500ms in environment with 100 packages |
| Cython `@dataclass` broken | Phase 6 (`.so` build) — pre-audit before CI setup | Construct all compiled dataclass instances in EE unit tests |
| Cython `__init__.so` relative imports | Phase 6 (`.so` build) — package structure constraint | `pip install wheel` + `python -c "import ee"` succeeds in clean venv |
| EE models use wrong Base | Phase 5 (private repo setup) — first model written | `\dt` on CE DB after EE install shows all 15 EE tables |
| Licence validation startup-only | Phase 7 (licensing) | Licence expiry test: expired file → features disabled within 12h |
| CE tests fail without EE | Phase 5 gap fixes (test isolation) | `pytest -m "not ee"` in CE-only venv: zero failures |
| Circular import EE → main.py | Phase 5 (private repo setup) — import boundary rule | `python -c "import axiom_ee"` without importing `main` succeeds |
| `NodeConfig` CE dead references | Phase 5 gap fixes (NodeConfig strip) | CE job dispatch with no AttributeError in server logs |

---

## Sources

- Direct codebase inspection: `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` (confirmed `pkg_resources` usage, no stub mounting), `ee/interfaces/foundry.py` (confirmed stub routers defined but not registered in `app`), `ee/routers/foundry_router.py` (confirmed real router extracted, imports from `...db` including EE models), `main.py` (confirmed `load_ee_plugins()` called in lifespan, no `include_router` calls for stubs), `db.py` (confirmed single `Base = DeclarativeBase()`, 13 CE tables only in worktree)
- Cython GitHub issue #3336: "Dataclasses do not work with Cython due to annotations being stripped out" — confirmed active issue, partial fix in Cython 3 but not all decorator patterns: https://github.com/cython/cython/issues/3336
- CPython bug #59828 (GitHub): "Init time relative imports no longer work from `__init__.so` modules" — confirmed `.so` compiled `__init__` breaks relative imports: https://bugs.python.org/issue15623
- Nuitka GitHub issue #1955: "Nuitka needs support for importlib.metadata.entry_points() hard imports" — `.so` entry_points discovery requires explicit `--include-module` flags: https://github.com/Nuitka/Nuitka/issues/1955
- setuptools deprecation of `pkg_resources`: setuptools 67.0+ changelog (2023); `importlib.metadata` is the stdlib replacement since Python 3.9
- FastAPI discussion #9014: "Behavior of `include_router` method" — confirmed silent addition of duplicate routes (no exception, `UserWarning: Duplicate Operation ID` only): https://github.com/fastapi/fastapi/discussions/9014
- Keygen offline licence pattern: Ed25519-signed licence files for air-gapped self-hosted deployments: https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/
- SQLAlchemy documentation: shared `MetaData` required for FK resolution; `create_all` scope limited to the calling `Base`'s metadata: https://docs.sqlalchemy.org/en/20/core/metadata.html
- `.planning/axiom-oss-ee-split.md`: Phase 5/6/7 TODO list confirming blocking gaps (router registration, CE test isolation, NodeConfig strip, private repo, `.so` pipeline, licensing)

---
*Pitfalls research for: Axiom v11.0 CE/EE Split Completion — Cython/Nuitka .so compilation, entry_points discovery, FastAPI plugin router registration, SQLAlchemy CE/EE model separation, open-core licence enforcement*
*Researched: 2026-03-19*

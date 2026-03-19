# Feature Research

**Domain:** Open-core Python product — CE/EE split completion (v11.0)
**Researched:** 2026-03-19
**Confidence:** HIGH (entry_points pattern verified via Python packaging docs + existing codebase; licence key via Keygen official docs; test isolation via pytest docs; upgrade UX inspected directly in worktree code)

---

## Context: What This Milestone Covers

This research replaces the v10.0 FEATURES.md with a v11.0-scoped analysis. All v10.0 features
are complete and shipped. v11.0 is strictly about **completing the CE/EE open-core split** —
fixing four blocking gaps on `feature/axiom-oss-ee-split`, wiring EE plugin mechanics, setting
up the private `axiom-ee` repo, compiling EE to `.so`, and publishing `axiom-ce` to Docker Hub.

The split infrastructure (Phase 1-4) is **already done** in the worktree:
- Plugin scaffold with ABCs + 402 stubs (`puppeteer/agent_service/ee/`)
- `GET /api/features` endpoint returning 8 feature flags
- 7 EE routers extracted to `ee/routers/`
- CE DB stripped to 13 tables (EE tables removed)
- Frontend `useFeatures` hook + `UpgradePlaceholder` component

**What is NOT done (the 6 blocking items this milestone closes):**
1. Router registration gap — stub routers are defined but not mounted by `register()`
2. CE test suite isolation — EE-only tests mixed in; `test_bootstrap_admin.py` refs `User.role`
3. `NodeConfig` model still carries EE fields (`concurrency_limit`, `job_memory_limit`, `job_cpu_limit`)
4. Private `axiom-ee` repo + entry_points wiring not created
5. `.so` build pipeline (Cython/Nuitka) not configured
6. CE/EE docs distinction + licence key validation + Docker Hub CE publish

---

## Feature Area 1: EE Plugin Mechanics (entry_points + router registration)

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Stub routers mounted at CE startup** | CE must respond 402 to all EE endpoints. Currently the stub router objects exist but `load_ee_plugins()` in `__init__.py` never calls `app.include_router()` for them — EE endpoints return 404 in CE mode instead of 402. This is the single most visible gap. | LOW | In `ee/__init__.py`, when no EE plugin found, iterate the 7 stub routers and call `app.include_router()` for each. The stubs already have all correct route paths defined. |
| **`pkg_resources` replaced with `importlib.metadata`** | `pkg_resources` is deprecated as of setuptools 67+ and the Python packaging docs explicitly recommend migrating to `importlib.metadata`. The existing `load_ee_plugins()` uses `pkg_resources.iter_entry_points()`. This will generate deprecation warnings on Python 3.12+ and break in future. | LOW | Replace `pkg_resources.iter_entry_points("axiom.ee")` with `importlib.metadata.entry_points(group="axiom.ee")`. The API is identical in effect; `entry_points(group=...)` returns an iterable of `EntryPoint` objects with the same `.load()` method. Available in stdlib Python 3.12+; use `importlib_metadata` backport for 3.9-3.11. |
| **EE `register()` method mounts real routers + sets feature flags** | The EE plugin's `register(ctx)` method must (a) set feature flags to `True` on the `EEContext` and (b) call `app.include_router()` for the 7 real EE routers (replacing or overriding the stubs). This is the entire runtime EE activation path. | LOW | Convention from real open-core products: `register()` receives `(app, engine, ctx)` or `(ctx)` plus module-level refs. The existing ABC signature is `plugin.register(ctx)` — `app` and `engine` are passed at construction time (`plugin_cls(app, engine)`). Mount routers in `register()`. |
| **CE-alone cold start validates to exactly 13 tables** | After stripping EE tables, a fresh CE cold-start must not create any EE tables. The verification checklist item is currently unchecked for `pip install axiom-ee` = all true; this validates the inverse. | LOW | Already passes per checklist. Verify with `inspect(engine).get_table_names()` in a CE integration test. |
| **`axiom.ee` entry_points group name is authoritative** | Entry point group name `axiom.ee` (already hardcoded in `__init__.py`) must exactly match what the private `axiom-ee` package declares in its `setup.cfg`/`pyproject.toml`. Mismatch = silent CE mode even with EE installed. | LOW | Document the group name contract in both repos. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multiple EE plugins supported in theory** | The loop over `entry_points(group="axiom.ee")` already supports multiple plugins. This future-proofs for a scenario where EE is modular (e.g., `axiom-ee-foundry` + `axiom-ee-rbac` separately). | LOW | No extra work — the loop is already there. Document the intent. |
| **Feature flags update `GET /api/features` atomically** | The `EEContext` dataclass drives the `/api/features` response. Setting flags in `register()` means the REST response is correct immediately — no cache invalidation needed. Frontend `useFeatures` caches for 5 minutes, which is acceptable. | LOW | Already architected correctly. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Router override/deregistration pattern** | "EE should replace CE stubs, not coexist" | FastAPI does not support deregistering already-mounted routes. The stub routes are registered first; EE routes registered later produce duplicate path registrations. FastAPI resolves route conflicts by first-match — stubs would win. | Register EE routers INSTEAD of stubs. When EE is present, do not register stubs at all. The conditional in `load_ee_plugins()` already handles this: stubs are registered only in the `else` branch (no plugins found). |
| **Hot-reload EE without restart** | "Install EE while CE is running" | Python's import system does not support hot-swap of installed packages. Entry points are resolved at import time. Attempting runtime plugin reload requires clearing sys.modules, which is fragile and untestable. | Require restart after `pip install axiom-ee`. This is standard for plugin-based Python applications (Pytest, Django, Flask extensions all require restart). Document clearly. |

---

## Feature Area 2: Private `axiom-ee` Repo + Entry_points Wiring

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Private GitHub repo `axiom-laboratories/axiom-ee`** | EE source code cannot live in the public `axiom` repo. GitHub private repos support GHCR private packages natively. | LOW | Create via GitHub UI or `gh repo create --private`. No special tooling needed. |
| **`pyproject.toml` entry_points declaration** | The EE package must declare `[project.entry-points."axiom.ee"]` with `core = ee.plugin:EEPlugin`. Modern `pyproject.toml` is preferred over `setup.cfg` for new projects. | LOW | `[project.entry-points."axiom.ee"]` section in `pyproject.toml`. Exact syntax: `core = "ee.plugin:EEPlugin"`. The class `EEPlugin` must implement the ABC defined in the CE `ee/interfaces/` directory. |
| **CE `ee/interfaces/` ABCs imported as a dependency** | The EE plugin must import and subclass the CE ABCs to satisfy the interface contract. This means `axiom-ee` takes a dev-dependency on `axiom` (or extracts the ABCs to a shared `axiom-interfaces` package). | MEDIUM | Simplest approach: `axiom-ee` installs `axiom` as a dependency (it runs inside the same Python environment). The ABCs are importable from `agent_service.ee.interfaces`. No shared package needed. |
| **`pip install axiom-ee` validation test** | The verification checklist has an unchecked item: "EE install restores features: `pip install axiom-ee` → features all `true`". This must be tested end-to-end. | MEDIUM | Create a fresh virtualenv, install `axiom` (CE), verify `GET /api/features` = all false; then `pip install axiom-ee`, restart, verify all true. Document as a manual smoke test and automate in EE repo CI. |
| **`pip install` from private GitHub via token** | EE customers install via `pip install git+https://...` with a token, or from a private PyPI/GH Packages index. Both require documented install instructions. | LOW | Use `pip install "axiom-ee @ git+https://<TOKEN>@github.com/axiom-laboratories/axiom-ee.git"`. Or publish to a private PyPI index (GitHub Packages supports this). |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **EE installed as a standard Python package (not a file drop)** | Customers use `pip install` — familiar, versionable, updateable with standard tools. No manual file copying or Docker layer manipulation required. | LOW | The entry_points mechanism makes this entirely standard. No custom installer. |
| **Version pinning between CE and EE** | EE packages can declare `axiom>=11.0,<12.0` as a dependency constraint. This prevents EE from loading against an incompatible CE version and producing cryptic errors. | LOW | Add version constraint to `axiom-ee`'s `pyproject.toml` dependencies. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Separate CE and EE Docker images with different codebases** | "Simpler to distribute" | Two separate image builds double the maintenance surface. The CE image already runs in EE mode when `axiom-ee` is pip-installed inside it. | Use one base image (`axiom-ce`). EE customers layer `pip install axiom-ee` on top, either in a custom Dockerfile FROM axiom-ce or via a Docker entrypoint script. |
| **Namespace packages to share code between CE and EE** | "Avoid dependency on the full axiom package" | Namespace packages require careful `__init__.py` handling and are fragile in editable installs. The entry_points approach is cleaner and more maintainable. | Keep the simple dependency: `axiom-ee` depends on `axiom`. No namespace packages. |

---

## Feature Area 3: CE Test Suite Isolation

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **`@pytest.mark.ee_only` custom marker** | Tests for EE features must not run against a CE-only install. Without a marker, EE tests fail with import errors or assertion failures when EE tables/routes are absent. The pytest docs pattern: register marker in `conftest.py` via `config.addinivalue_line("markers", "ee_only: ...")` and implement `pytest_collection_modifyitems` to auto-skip marked tests if `axiom-ee` is not installed. | LOW | Add to `conftest.py`: check `importlib.metadata.entry_points(group="axiom.ee")` — if empty list, skip all `@pytest.mark.ee_only` tests. This is the standard pytest marker + `importlib.metadata` pattern. |
| **`test_bootstrap_admin.py` User.role reference fix** | `test_bootstrap_admin.py` line 34 asserts `admin.role == "admin"` and line 47 creates `User(..., role="admin")`. The CE `User` model no longer has a `role` column (stripped in Phase 3). This causes an `AttributeError` on CE cold-start test. | LOW | Remove `role=` kwarg from `User(...)` constructor call. Remove `assert admin.role == "admin"` assertion. CE admin bootstrap has no role concept — all CE users are implicitly admin. Alternatively, assert that the user exists with the correct username only. |
| **EE-only test files identified and marked** | `test_foundry_mirror.py`, `test_smelter.py`, `test_compatibility_engine.py`, `test_trigger_service.py` test features that only exist in EE. They import EE DB models that do not exist in CE. | MEDIUM | Each of these test files needs `@pytest.mark.ee_only` on the class/function level, OR a module-level `pytestmark = pytest.mark.ee_only`. This is a mechanical but non-trivial scan across 20 test files. |
| **CE test suite runs cleanly with `pytest -m "not ee_only"`** | The CI pipeline for the public `axiom` repo must run only CE tests. EE tests belong in the `axiom-ee` private repo CI. The CE suite must pass with zero failures on a fresh install with no `axiom-ee` present. | LOW | Add `addopts = -m "not ee_only"` to `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` for the CE repo. EE repo can run with `pytest -m "ee_only or not ee_only"` (all tests). |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Integration test fixture for CE+EE combined mode** | In the EE private repo, a `conftest.py` fixture that installs both `axiom` (CE) and `axiom-ee` (EE) in a test virtualenv enables end-to-end integration testing of the combined stack. | MEDIUM | `subprocess.run(["pip", "install", "-e", ce_path, "-e", ee_path])` in a session-scoped fixture. Slower but authoritative. |
| **`pytest --ce-only` flag as an escape hatch** | Developers working on EE who want to run only the CE subset of tests can pass `--ce-only` rather than remembering the marker syntax. | LOW | Implement `pytest_addoption` in `conftest.py` with `--ce-only` flag; if set, add `ee_only` to the deselect list. Convenience wrapper over the marker mechanism. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Separate `tests/ce/` and `tests/ee/` directory split** | "Clean separation by directory" | Directory-based separation requires duplicating shared test utilities and makes it harder to run CE tests as part of the EE CI (which needs to validate CE compatibility). | Marker-based approach: all tests live in `tests/`, EE tests are marked `@pytest.mark.ee_only`. CE CI filters with `-m "not ee_only"`. EE CI runs all. |
| **Mocking the EE plugin in CE tests** | "Test CE code paths that would be EE-dependent" | Mocking the EE plugin to test CE behaviour is redundant — the stub interfaces already return CE defaults (RBAC stub returns `True` for all permissions; resource_limits stub returns null limits). The stubs ARE the test doubles. | Use the actual stub implementations. If a CE test needs to verify stub behaviour, import the stub class directly and call its methods. No mocking needed. |

---

## Feature Area 4: `.so` Compilation Pipeline (Cython/Nuitka)

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **EE source code not shipped in distribution** | The entire value of compiling to `.so` is that customers cannot read the EE source. If `.py` files ship alongside `.so`, the protection is void. Setuptools' `build_py` must be overridden to exclude `.py` files for modules that have compiled `.so` equivalents. | MEDIUM | Standard Cython pattern: override `build_py` in `setup.py` to call `super().build_py()` then delete any `.py` file whose module has a corresponding `.so`. Alternatively, use `setuptools-cythonize` or `cythonpackage` libraries that automate this. |
| **Cython preferred over Nuitka for `.so` modules** | Cython compiles `.py` → `.c` → `.so` (CPython extension module) and is the established, widely-tested approach for PyPI wheel distribution without source. Nuitka's `--module` mode also works but has a harder dependency: the compiled `.so` loads only in the exact CPython version it was compiled for, AND Nuitka is a heavier build toolchain. For per-module compilation (not standalone executables), Cython is better-understood and has more community examples. | HIGH | Cython is the industry-standard choice for this use case. Nuitka is a valid fallback if Cython has compatibility issues with specific Python patterns used in EE. **Use Cython first.** |
| **Multi-arch wheel build via `cibuildwheel`** | A `.so` compiled for `linux/amd64` does not run on `linux/arm64`. PyPI requires separate wheels per platform. `cibuildwheel` automates building for multiple Python versions and architectures in GitHub Actions. | HIGH | Add `cibuildwheel` to the private repo CI. Build matrix: `python: ["3.11", "3.12", "3.13"]` x `arch: ["x86_64", "aarch64"]`. Use QEMU emulation for arm64 in CI or use GitHub's arm64 runner. |
| **Compiled `.so` passes existing EE test suite** | The compiled module must be functionally identical to the source. Run the EE test suite against the compiled artifact before publishing to verify no Cython incompatibilities. | MEDIUM | Add a CI step that (a) builds the wheel, (b) installs it into a clean venv, (c) runs `pytest -m ee_only`. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Wheel published to GitHub Packages (private PyPI)** | GitHub Packages supports private PyPI indexes. EE customers authenticate with a GitHub token to `pip install`. This avoids running a separate Artifactory or Gemfury instance. | MEDIUM | Configure `pip install --extra-index-url https://<TOKEN>@pip.pkg.github.com/axiom-laboratories/ axiom-ee`. Publish via `gh release upload` or directly to GitHub Packages. |
| **Version-tagged releases with signatures** | Each EE wheel release should be tagged and ideally signed with `sigstore` for supply chain integrity — consistent with Axiom's security brand. | LOW | Add `sigstore` signing to the EE release workflow, mirroring the CE release workflow pattern. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Compile entire EE to a single `.so`** | "Simpler artifact" | A single monolithic `.so` produced by Nuitka or `cythonpackage` has hard Python version pinning and is very large. A single artifact cannot be selectively loaded. Module-level compilation is more maintainable. | Compile each EE module separately to `.so`. The entry point (`ee/plugin.py`) imports the compiled sub-modules. Python's import system handles the rest. |
| **Ship source `.py` "just in case"** | "For debugging" | If `.py` files are in the wheel, pip will use them preferentially over `.so` on some platforms, defeating the protection. | Include a `.pyi` stub file (type hints only, no implementation) for IDE support. Strip all `.py` from the wheel. |
| **`.pyc` bytecode as an alternative to `.so`** | "Easier to generate" | `.pyc` files are trivially decompilable with `uncompyle6` or `decompile3`. They provide no meaningful IP protection. | Cython `.so` is the minimum acceptable protection level. `.pyc` distribution is not a valid EE strategy. |

---

## Feature Area 5: Licence Key Validation

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Licence key validated at EE plugin startup** | Without licence validation, any user who obtains the EE wheel can use it indefinitely without payment. Validation is the commercial enforcement mechanism. | MEDIUM | The validation runs inside EE's `register()` method before mounting any routers. If validation fails, raise an exception that causes `load_ee_plugins()` to catch and log a warning, leaving CE in stub mode. |
| **Ed25519 signed licence key (offline-capable)** | The licence key must be verifiable without a network call — Axiom targets air-gapped deployments. Ed25519-signed payloads are the recommended scheme per Keygen's official docs ("our overall recommended scheme when available"). The public key is hardcoded in the EE compiled binary; the private key is held by Axiom. | MEDIUM | Key structure: `BASE64URL_PAYLOAD.BASE64URL_SIGNATURE`. Payload is a JSON object with: `customer_id`, `exp` (Unix timestamp), `features` (list), `issued_at`. Verify with `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify()`. |
| **Licence key loaded from environment variable or file** | EE operators configure the key via `AXIOM_LICENCE_KEY` env var or a file path in `AXIOM_LICENCE_KEY_FILE`. The EE plugin reads one of these at startup. | LOW | Check env var first; fall back to file. This is the standard pattern for secrets in containerised applications. |
| **Graceful degradation on licence failure** | If the licence is missing, expired, or invalid, Axiom must not crash. It must log a clear error and fall back to CE mode (stubs serve 402). A corrupted licence key should never take the server down. | LOW | `try/except` around validation in `register()`. Log `logger.error("EE licence validation failed: {reason}")`. Return without setting feature flags or mounting EE routers. |
| **Expiry enforced with clear error message** | `exp` claim in the licence payload must be checked against `time.time()`. An expired licence should produce `logger.error("EE licence expired at {date}")` — not a cryptic validation failure. | LOW | Check `payload["exp"] < time.time()` after signature verification. Format the error with a human-readable ISO date. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Feature entitlements in licence payload** | The `features` claim in the licence payload allows Axiom to issue licences that enable only a subset of EE features (e.g., RBAC-only licence). The `register()` method only sets flags for features that are both: (a) implemented and (b) present in the licence's feature list. | MEDIUM | `features: ["rbac", "audit", "webhooks", ...]` claim in payload. In `register()`: `ctx.rbac = "rbac" in features`. Enables tiered EE pricing without separate builds. |
| **Licence check only at startup (not per-request)** | Checking the licence on every API request adds latency and creates a per-request failure mode. Checking only at startup means a licence expiry mid-operation does not interrupt running jobs. | LOW | Validate once in `register()`. Store result in `EEContext`. No per-request checking. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Online licence validation (call home)** | "More secure — check revocation in real time" | Axiom's target deployment (air-gapped, hostile networks) makes outbound call-home unreliable. A failed call-home could take down production. Online validation also requires Axiom to operate a licence server with 99.9% uptime SLA, which is significant operational overhead. | Use Ed25519 offline validation. Issue new licence keys on renewal (short-lived keys = natural revocation). A 1-year expiry is standard; customers renew for a new key. |
| **Licence key baked into the compiled `.so`** | "Customer can't extract and share the key" | Baking the key into the binary means issuing a new build for each customer. This scales to exactly one customer. | Each customer gets their own licence key file/env var. The EE binary is the same for all customers. The key is the per-customer artifact. |
| **Licence server inside Axiom itself** | "Self-hosted licence management" | A licence server in CE would need to issue EE licences — circular dependency. A licence server in EE would need to be running to licence itself — also circular. | Issue licence keys out-of-band (email, dashboard on axiom.run, or manual process for v11.0). Automate with a separate licensing service only when customer volume warrants it. |

---

## Feature Area 6: Docs + Licensing + Docker Hub CE Publish

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **CE/EE feature distinction in docs** | Any user reading the docs must know which features require EE. Without clear labelling, CE users open support issues for 402 errors. | LOW | Add an EE badge/callout in MkDocs to any feature that is EE-only. Standard pattern: `!!! enterprise "Enterprise Edition" \n This feature requires Axiom EE.` in MkDocs Material admonition syntax. |
| **`axiom-ce` published to Docker Hub** | Docker Hub has dramatically higher discoverability than GHCR for community users. CE users searching "axiom scheduler" on Docker Hub should find the image. GHCR remains the primary registry; Docker Hub is a discoverability mirror. | LOW | Add a Docker Hub push step to the release workflow. Requires `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` secrets. Tag as `axiom-laboratories/axiom-ce:latest` and `axiom-laboratories/axiom-ce:11.0.0`. |
| **`axiom-ce` Docker Hub description with EE upgrade path** | The Docker Hub README for `axiom-ce` must explain CE limitations and link to `axiom.run/enterprise` for EE. Without this, users hit 402s on Foundry and RBAC endpoints with no context. | LOW | Set Hub description via Docker Hub API or UI. Point to the MkDocs site for full docs. |
| **`LICENCE` file update in public repo** | The public repo `LICENSE` file should state Apache-2.0. Any reference to EE (the `/ee` directory) needs a note that the directory is a reserved placeholder under proprietary licence for EE builds. | LOW | Update root `LICENSE` (Apache-2.0 for CE). Add a `ee/LICENSE` stub file: "This directory is reserved for Axiom Enterprise Edition. Contents are proprietary." This is the GitLab pattern. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **`axiom-ce` Docker Hub README links to upgrade** | Users who outgrow CE can self-service discover EE from the Hub README. Passive upgrade path with zero sales friction. | LOW | Two-paragraph Hub description: CE capabilities + "Ready to upgrade? Visit axiom.run/enterprise." |
| **EE distribution as a pip-installable layer** | `pip install axiom-ee` works inside any `axiom-ce` container via a custom Dockerfile `FROM axiom-ce`. This is the cleanest EE distribution story — no separate image builds, no filesystem drops. | LOW | Already the natural outcome of the entry_points architecture. Document this pattern explicitly in the EE onboarding docs. |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Separate `axiom-ee` Docker image** | "All-in-one EE image for customers" | Maintaining a separate EE image means rebuilding and publishing two images on every CE change. It also complicates licence enforcement (anyone with the image has EE without a licence key check). | Document `FROM axiom-ce` + `RUN pip install axiom-ee` as the EE deployment pattern. Licence key enforced at runtime. EE image responsibility stays with the customer. |
| **Removing the `/ee` directory from the public repo** | "Less confusing" | The `/ee` directory with stub interfaces is the public API contract for the plugin system. Removing it breaks the CE plugin scaffold. | Keep the `/ee` directory as-is. Add clear comments and a `ee/README.md` explaining it is the EE plugin interface definition. |

---

## Feature Dependencies

```
[Router registration fix (gap 1)]
    └──required-by──> [CE cold-start passes 402 for all EE endpoints]
    └──required-by──> [EE install validation (gap 4)]

[User.role fix + ee_only markers (gap 2)]
    └──required-by──> [CE test suite runs cleanly in CI]
    └──blocks──>      [public repo CI green]

[NodeConfig strip (gap 3)]
    └──required-by──> [CE Pydantic model correct]
    └──required-by──> [job_service.py uses CE-appropriate resource handling]

[Private axiom-ee repo + entry_points (gap 4)]
    └──requires──>    [Router registration fix (gap 1)] — EE register() needs to mount real routers
    └──requires──>    [NodeConfig strip (gap 3)] — EE adds back resource limits; CE must not have them
    └──required-by──> [.so build pipeline (gap 5)]
    └──required-by──> [pip install axiom-ee validation]

[Cython .so pipeline (gap 5)]
    └──requires──>    [axiom-ee source compiles cleanly]
    └──requires──>    [cibuildwheel CI matrix configured]
    └──required-by──> [EE wheel published to GitHub Packages]

[Licence key validation]
    └──requires──>    [EE register() method wired (gap 4)]
    └──required-by──> [Commercial EE distribution]
    └──independent-of──> [.so compilation (can ship source EE first, compile later)]

[Docs CE/EE distinction + Docker Hub CE publish]
    └──requires──>    [gaps 1-4 complete] — docs should reflect the final state
    └──independent-of──> [.so compilation]
```

### Dependency Notes

- **Gaps 1-3 are parallel and independent:** Router registration, test isolation, and NodeConfig
  strip do not depend on each other. All three can be fixed in a single phase or in parallel.

- **Gap 4 (private repo) depends on gaps 1 and 3:** The EE `register()` method mounts the real
  routers (needs gap 1 fixed to understand the full routing contract) and the EE DB models add
  back resource limit columns (needs gap 3 fixed to establish the clean CE baseline).

- **Licence validation can precede `.so` compilation:** Licence key logic can be written and
  tested in source form in the private repo before Cython compilation is configured. The
  compiled binary just contains the same logic, obfuscated.

- **Docker Hub publish is a release-time step:** Does not block any code work. Can be done
  alongside docs update as the final phase.

---

## v11.0 Scope Definition

### Phase A — Gap Fixes (blocking, must be first)

- [ ] **Gap 1: Router registration** — mount 7 CE stub routers in the `else` branch of `load_ee_plugins()`; replace `pkg_resources` with `importlib.metadata`
- [ ] **Gap 2: Test isolation** — `@pytest.mark.ee_only` marker + conftest auto-skip; fix `test_bootstrap_admin.py` `User.role` refs; mark all EE-feature test files
- [ ] **Gap 3: NodeConfig strip** — remove `concurrency_limit`/`job_memory_limit`/`job_cpu_limit` from CE `NodeConfig` Pydantic model; clean up `job_service.py` usages

### Phase B — Private Repo + Plugin Wiring

- [ ] **Private `axiom-ee` repo** — create with `pyproject.toml` entry_points `axiom.ee = core = ee.plugin:EEPlugin`
- [ ] **EE `register()` implementation** — mounts 7 real EE routers, sets all 8 feature flags true, validates licence key
- [ ] **Validate CE-alone + CE+EE installs** — end-to-end smoke test of both modes

### Phase C — Compilation Pipeline

- [ ] **Cython `.so` build** — `setup.py` with Cython extension list; override `build_py` to strip `.py`
- [ ] **`cibuildwheel` CI matrix** — Python 3.11/3.12/3.13 x amd64/arm64
- [ ] **Verify no `.py` in built wheel** — `zipfile.ZipFile(wheel).namelist()` check in CI

### Phase D — Docs, Licensing, Docker Hub

- [ ] **EE feature badges in MkDocs** — `!!! enterprise` admonitions on all EE feature pages
- [ ] **Licence key validation in EE plugin** — Ed25519 offline validation; `AXIOM_LICENCE_KEY` env var
- [ ] **`axiom-ce` Docker Hub publish** — add to release workflow; Hub description with upgrade link
- [ ] **`ee/LICENSE` stub** — clarify Apache-2.0 applies to CE only; `/ee/` is proprietary boundary

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Gap 1: Router registration (404 → 402) | HIGH | LOW | P1 — visible bug in CE |
| Gap 2: Test suite isolation | HIGH | LOW | P1 — blocks CI green |
| Gap 3: NodeConfig CE strip | HIGH | LOW | P1 — CE model correctness |
| Private axiom-ee repo + entry_points | HIGH | LOW | P1 — enables all EE work |
| CE-alone + CE+EE validation test | HIGH | MEDIUM | P1 — verification checklist |
| Licence key Ed25519 validation | HIGH | MEDIUM | P1 — commercial requirement |
| Cython .so build + cibuildwheel | HIGH | HIGH | P1 — IP protection requirement |
| EE feature badges in docs | MEDIUM | LOW | P2 |
| axiom-ce Docker Hub publish | MEDIUM | LOW | P2 |
| ee/LICENSE stub | LOW | LOW | P2 |
| Wheel published to GitHub Packages | MEDIUM | MEDIUM | P2 |
| Feature entitlements in licence payload | MEDIUM | MEDIUM | P3 — tiered pricing; future |
| Signed wheel releases (sigstore) | LOW | LOW | P3 |

**Priority key:**
- P1: Must ship in v11.0 to complete the split
- P2: Should ship in v11.0; adds completeness but not blocking
- P3: Future consideration or v11.x

---

## Competitor Patterns Analysis

How established open-core Python products handle the CE/EE split:

| Aspect | Metabase (Java) | PostHog (Python/Django) | Sentry (Python/Django) | Axiom v11.0 Approach |
|--------|----------------|------------------------|----------------------|---------------------|
| **EE discovery** | Separate EE jar on classpath | Feature flags in DB seeded by EE install | `sentry/features/` directory + configuration | Python entry_points group `axiom.ee` — standard packaging |
| **402 vs 404 for CE** | 403 (access denied) | Feature flag gate returns error in UI | Redirects to upgrade page | 402 (payment required) — semantically correct for "feature requires purchase" |
| **EE routes** | Separate servlet context | Included in main app, gated by feature flag | Included in main app, gated in view | Separate router files registered only when EE present |
| **Compiled EE** | Jar (bytecode, low protection) | No compilation — source available | No compilation | Cython `.so` — industry standard for Python IP protection |
| **Licence validation** | Licence file checked at startup | No per-install licence (SaaS model) | No per-install licence | Ed25519 signed key offline validation; `AXIOM_LICENCE_KEY` env var |
| **Test isolation** | Maven profiles | `@pytest.mark.ee` convention | `requires_snuba` etc. conftest fixtures | `@pytest.mark.ee_only` + conftest auto-skip |

**Key insight:** The PostHog/Sentry pattern (feature flags in DB, EE code always present but gated) is simpler to implement but ships EE source code to all users. Axiom's entry_points pattern keeps EE source out of the public repo entirely, which is the correct choice given the compiled `.so` requirement.

---

## Sources

- [Python Packaging — Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — entry_points group pattern, `importlib.metadata.entry_points()` API — HIGH confidence
- [Python importlib.metadata docs](https://docs.python.org/3/library/importlib.metadata.html) — `entry_points(group=...)` API, `PackageNotFoundError` for installed-package checks — HIGH confidence
- [Keygen — Offline Licensing](https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/) — Ed25519 signed key structure, offline validation pattern, `exp` claim — HIGH confidence
- [Keygen — Cryptographic Verification](https://keygen.sh/docs/api/cryptography/) — `ED25519_SIGN` recommended scheme, payload + signature structure — HIGH confidence
- [pytest — Working with Custom Markers](https://docs.pytest.org/en/stable/example/markers.html) — `pytest_collection_modifyitems`, `config.addinivalue_line`, skip on condition — HIGH confidence
- [pytest — Skip and xfail](https://docs.pytest.org/en/stable/how-to/skipping.html) — `pytest.skip()`, `skipif`, marker-based skip hooks — HIGH confidence
- [Nuitka User Manual](https://nuitka.net/user-documentation/user-manual.html) — `--module` flag, `bdist_nuitka`, Python version pinning limitation — MEDIUM confidence
- [Cython — Distributing packages protected with Cython](https://art-vasilyev.github.io/posts/protecting-source-code/) — build_py override, platform-specific wheel pattern — MEDIUM confidence
- [pypa/cibuildwheel — Excluding Python source from wheels](https://github.com/pypa/cibuildwheel/discussions/2065) — post-build `.py` exclusion pattern — MEDIUM confidence
- Existing codebase in `.worktrees/axiom-split/` — direct inspection of `ee/__init__.py`, `ee/interfaces/`, `ee/routers/`, `UpgradePlaceholder.tsx`, `useFeatures.ts`, `test_bootstrap_admin.py`, `models.py` — HIGH confidence (primary source)

---

*Feature research for: Axiom v11.0 — CE/EE open-core split completion*
*Researched: 2026-03-19*

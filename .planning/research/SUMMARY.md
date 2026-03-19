# Project Research Summary

**Project:** Axiom v11.0 — CE/EE Split Completion
**Domain:** Open-core Python product (FastAPI + SQLAlchemy) with plugin-based CE/EE separation
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

Axiom v11.0 completes the open-core split that was scaffolded in previous phases. The foundation — ABC interfaces, stub routers, `GET /api/features`, CE DB strip to 13 tables, and the frontend `useFeatures` hook — is already implemented on the `feature/axiom-oss-ee-split` worktree. Six concrete blocking gaps remain between the current worktree state and a shippable CE/EE product: stub routers never mounted in CE mode (returning 404 instead of 402), a broken test suite that references stripped EE attributes, dead field references in `job_service.py` after the NodeConfig strip, no private `axiom-ee` repo or `EEPlugin` class, no Cython `.so` build pipeline, and no licence key validation. Each gap is well-understood and mechanically fixable — this is completion work, not greenfield design.

The recommended approach is a strict sequential build order anchored by dependencies between the gaps. Gaps 1, 2, and 3 (router registration fix, test isolation, NodeConfig strip) are independent of each other and form the mandatory CE baseline that must be verified before any EE-side work begins. The private `axiom-ee` repo (Gap 4) requires Gaps 1 and 3 as prerequisites, because the EE `register()` method must mount real routers into a correctly wired CE host, and EE DB models must extend the clean CE baseline. The Cython `.so` pipeline (Gap 5) requires the EE source to be validated in Python form first. Licence key validation and Docker Hub/docs publishing are parallel to the `.so` pipeline.

The primary risks are three concrete engineering traps already identified in the codebase: FastAPI's silent duplicate-route registration means stubs must never coexist with real EE routers (guard every stub registration on `not ctx.{feature}`); Cython strips `__annotations__` from `@dataclass` classes in compiled modules (avoid `@dataclass` entirely in compiled EE code, use explicit `__init__`); and SQLAlchemy's `create_all` is scoped to a single `Base` instance, so EE models must import the CE `Base` rather than define their own. These three traps have clear prevention strategies and must be built into the Phase B (private repo) and Phase C (compilation) implementations from the start.

## Key Findings

### Recommended Stack

No new Python or npm packages are required for v11.0. `importlib.metadata` (stdlib on Python 3.10+) replaces the deprecated `pkg_resources` for entry_points discovery. `cryptography` (already present) covers Ed25519 offline licence validation. `recharts` and Radix UI handle any dashboard work.

Two build-time-only tools are added to the EE private repo's `[build-system]` dependencies only — never to runtime `requirements.txt` or the Docker image:

**Core technologies (new for v11.0):**
- `Cython 3.2.4` — compile EE `.py` router/plugin files to `.so` extension modules; pure Python mode requires no `.pyx` rewrite; industry-standard for Python IP protection in open-core products
- `cibuildwheel 3.4.0` — build Cython `.so` wheels for `linux/amd64` and `linux/arm64` in CI; pypa-endorsed standard; handles manylinux containers and QEMU aarch64 automatically
- `importlib.metadata` (stdlib) — replace `pkg_resources.iter_entry_points()` in `ee/__init__.py`; `entry_points(group="axiom.ee")` is the canonical modern API; already available on Python 3.10+
- `docker/login-action v3` — authenticate to Docker Hub in release workflow for CE image publishing; already used for GHCR; PAT-based only (Docker Hub deprecated password auth in 2021)

**Critical version note:** EE private repo `pyproject.toml` must specify `setuptools>=77.0` and `Cython>=3.2.4,<4` in `[build-system].requires`. CE public repo already has `setuptools>=77.0`. No changes to `puppeteer/requirements.txt` are needed.

See `.planning/research/STACK.md` for the full Cython `ext_modules` configuration, cibuildwheel CI YAML, `importlib.metadata` migration code, and Docker Hub workflow delta.

### Expected Features

All v11.0 features are in service of completing the CE/EE split. There are no net-new user-facing features — the milestone is infrastructure and commercial distribution.

**Must have (P1 — blocks shipping v11.0):**
- Gap 1: Stub router registration — `_register_ce_stubs(app)` mounts all 6 stub routers in CE mode; 404 → 402 for every EE endpoint
- Gap 2: CE test suite isolation — `@pytest.mark.ee_only` marker + conftest auto-skip; fix `test_bootstrap_admin.py` `User.role` refs; move 5 EE-heavy test files to private repo
- Gap 3: NodeConfig CE strip — remove `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` from CE `NodeConfig` Pydantic model; clean all dead references in `job_service.py`
- Private `axiom-ee` repo — `pyproject.toml` with `[project.entry-points."axiom.ee"]`; `EEPlugin` class with async `register(ctx)` mounting 7 real routers and setting all 8 feature flags; `EEBase` extending CE `Base`; 15 EE SQLAlchemy model definitions; corrected absolute import paths in all 7 router files
- Ed25519 offline licence key validation — `AXIOM_LICENCE_KEY` env var; `cryptography` Ed25519 signature verify; graceful degradation (CE stub mode on failure); no online call-home; check `issued_utc <= now <= expiry_utc`
- Cython `.so` build — all EE `.py` modules (except `__init__.py`) compiled to `.so`; `cibuildwheel` multi-arch CI matrix; no `.py` source in published wheel; `--no-sdist` flag prevents source distribution

**Should have (P2 — completes v11.0 cleanly):**
- CE/EE feature distinction in MkDocs docs — `!!! enterprise` admonitions on all EE feature pages
- `axiom-ce` Docker Hub publish — release workflow addition alongside existing GHCR; Hub description with upgrade link to `axiom.run/enterprise`
- `ee/LICENSE` stub file — Apache-2.0 applies to CE; `/ee/` directory is the proprietary boundary
- `ee_status` field on `GET /api/features` response — `not_installed | loaded | load_failed` for operator visibility; full exception logged on `load_failed`
- Licence expiry warning in dashboard — amber notice 30 days before expiry using `exp` claim from licence payload

**Defer (v11.x or later):**
- Feature entitlements in licence payload (tiered pricing by feature subset — `features: ["rbac", "foundry"]` in payload)
- Signed wheel releases with sigstore for supply chain integrity
- EE wheel on GitHub Packages private PyPI index (vs. manual token-based git install for v11.0)
- Periodic 12-hour licence re-validation via APScheduler background task (v11.0 validates at startup only; acceptable for initial commercial release)
- Hot-reload EE plugin without restart (not supported by Python import system; requires restart by design)

See `.planning/research/FEATURES.md` for full prioritization matrix, feature dependency graph, and competitor analysis (PostHog, Sentry, Metabase patterns).

### Architecture Approach

The architecture is a FastAPI plugin system using Python entry_points for CE/EE separation. CE ships with stub routers serving 402 for all EE paths. When `axiom-ee` is pip-installed, `EEPlugin` (discovered via `importlib.metadata.entry_points(group="axiom.ee")`) is instantiated with `(app, engine)`, and its async `register(ctx)` method mounts the 7 real EE routers, creates 15 EE tables using a separate `EEBase` called inside an async engine context, seeds EE data, and sets all 8 `EEContext` feature flags to `True`. The critical invariant: stubs and real routers for the same path must never coexist on `app` — guard all stub registrations with `if not ctx.{feature}:` evaluated after `register()` completes.

**Major components:**
1. `ee/__init__.py` (CE) — `_load_ee_plugins_async(app, engine)` called from lifespan via `await`; discovers entry_points with `importlib.metadata`; calls `_register_ce_stubs(app)` if no EE plugin found (CE path) or if `register()` raises (failure path)
2. `ee/interfaces/*.py` (CE) — 6 stub `APIRouter` instances; each route returns `JSONResponse(status_code=402, ...)`; these are the CE contract for EE paths and remain in the public repo
3. `ee/routers/*.py` (CE worktree) — 7 real router files; MOVED to `axiom-ee` private repo during Phase B; imports updated from relative (`...db`) to absolute (`agent_service.db`, `ee.db_models`)
4. `axiom-ee/ee/plugin.py` (EE private, compiled) — `EEPlugin` class with async `register(ctx)`; table creation, data seeding, router mounting, feature flag setting; compiled to `.so`
5. `axiom-ee/ee/db_models.py` (EE private, compiled) — `EEBase` importing CE `Base` from `agent_service.db`; 15 EE SQLAlchemy table definitions; `create_all` is idempotent
6. Cython build pipeline (EE CI) — `pyproject.toml` `ext_modules` listing each EE `.py` file except `__init__.py`; `cibuildwheel` matrix for Python 3.11/3.12/3.13 x amd64/arm64; wheel published with `--no-sdist`

**Startup sequence CE mode:** `init_db()` → `_load_ee_plugins_async()` → entry_points empty → `_register_ce_stubs(app)` → `EEContext(all False)` stored on `app.state.ee`

**Startup sequence EE mode:** `init_db()` → `_load_ee_plugins_async()` → `EEPlugin(app, engine).__init__()` → `await plugin.register(ctx)` → [create 15 EE tables, seed data, mount 7 routers, set all 8 flags True] → `EEContext(all True)` stored on `app.state.ee`

See `.planning/research/ARCHITECTURE.md` for full request flow diagrams, test isolation architecture, import boundary rules, and the complete Phase 5 build order.

### Critical Pitfalls

1. **Stub routers never mounted (404 not 402 in CE)** — `load_ee_plugins()` currently has no `app.include_router()` call for stubs in the CE fallback path; add `_register_ce_stubs(app)` in both the `else` branch and the `except` block; verify with `curl /api/blueprints` → 402 on a CE-only install before proceeding

2. **FastAPI silent duplicate route registration** — if stub and real router for the same path are both mounted, the first-registered (stub) silently shadows the real handler; guard every stub with `if not ctx.{feature}:` evaluated after `register()` completes; a startup assertion logging route-to-handler mapping detects this during Phase B testing

3. **Cython strips `@dataclass` annotations — all fields lost** — any `@dataclass`-decorated class compiled to `.so` produces a zero-argument `__init__`; audit all EE source files for `@dataclass` before Phase C; replace with plain classes using explicit `__init__`; Pydantic v2 models are not affected

4. **EE models define own `Base` — EE tables never created** — `Base.metadata.create_all` is scoped to the calling Base; EE must do `from agent_service.db import Base` and define all EE models on it; `OperationalError: no such table` on first EE route request is the failure symptom

5. **Compiling `__init__.py` to `.so` breaks relative imports** — never compile `ee/__init__.py`; leave it as a plain `.py` importing from compiled submodules; relative imports from a compiled `__init__.so` fail with `ImportError: attempted relative import with no known parent package`

6. **EE imports from `agent_service.main` trigger circular import** — EE routers must import only from `agent_service.deps`, `auth`, `security`, and `services.*`; importing from `main` triggers circular import that silently drops into CE stub mode; enforce with a CI import isolation test (`import ee.plugin` without importing `main`)

7. **`NodeConfig` dead field references in `job_service.py`** — stripped fields accessed as `None` cause silent admission check bypass; after Gap 3, search for all references to `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` in `job_service.py` and replace with CE-appropriate constants

See `.planning/research/PITFALLS.md` for all 10 pitfalls with recovery strategies, the "looks done but isn't" test checklist, and the pitfall-to-phase mapping table.

## Implications for Roadmap

Based on research, the dependency graph from FEATURES.md is definitive: Gaps 1+3 must precede Gap 4; Gap 4 must precede Gap 5; licensing and docs can proceed in parallel to Gap 5.

### Phase A: CE Baseline Fixes (Gaps 1, 2, 3)

**Rationale:** All three gap fixes are independent of each other and of EE-side work. They must be resolved first because every downstream validation step depends on a correctly behaving CE baseline. A CE install that returns 404 instead of 402 produces misleading test results. These are low-complexity changes (each is under 50 lines of net-new code) and should be completed in a single focused phase before any EE-side work begins.
**Delivers:** CE-only install with correct behaviour — all EE paths return 402, test suite passes in CE-only CI with zero failures, job dispatch works without `AttributeError` from stripped fields.
**Addresses:** Gap 1 (router registration), Gap 2 (test isolation), Gap 3 (NodeConfig strip)
**Avoids:** Pitfall 1 (404 in CE), Pitfall 8 (CE CI failures from EE attribute refs), Pitfall 10 (NodeConfig dead refs in `job_service.py`)
**Verification gate:** `pytest -m "not ee_only"` passes clean; `curl /api/blueprints` → 402; CE job dispatch cycle completes without error in server logs

### Phase B: Private Repo + EE Plugin Wiring (Gap 4)

**Rationale:** Requires Phase A complete (Gaps 1 and 3). This phase creates the private `axiom-ee` repo and validates the full CE+EE installation path in Python source form. It must precede the `.so` pipeline because debugging compilation issues is significantly harder than debugging Python source issues. Validating in source first ensures the architecture is correct before compilation adds an obfuscation layer.
**Delivers:** Working CE+EE install from Python source — `pip install -e axiom-ee/` + restart → all 8 feature flags `true`, all EE routes return real responses, all 28 tables exist in DB.
**Uses:** `importlib.metadata.entry_points(group="axiom.ee")`, async `register()` pattern, `EEBase` sharing CE `Base`, corrected absolute imports in 7 router files
**Implements:** `EEPlugin` class, `axiom-ee` private repo structure and entry_points declaration, import boundary rule (no imports from `agent_service.main`)
**Avoids:** Pitfall 2 (duplicate route registration — use `if not ctx.{feature}:` guard), Pitfall 3 (`pkg_resources` deprecated), Pitfall 4 (EE defines own Base), Pitfall 9 (circular import)
**Verification gate:** `GET /api/features` all `true` after `pip install -e axiom-ee/`; `GET /api/blueprints` returns real response; `\dt` shows all 28 tables; `python -c "import ee.plugin"` without importing `main` succeeds

### Phase C: Cython .so Build Pipeline (Gap 5)

**Rationale:** Requires Phase B to validate correctly in source form. The compilation step adds no functionality — it protects IP. Building the CI pipeline after source validation keeps debugging tractable.
**Delivers:** EE wheel with no `.py` source (only `__init__.py` remains as `.py`); multi-arch wheel for Python 3.11/3.12/3.13 x amd64/arm64; published to GitHub Releases; same Phase B validation passes against compiled artifact.
**Uses:** `Cython 3.2.4` with pure Python mode (no `.pyx` rewrite), `cibuildwheel 3.4.0`, `python -m build --no-sdist`
**Avoids:** Pitfall 4 (`@dataclass` — pre-audit all EE modules before CI setup), Pitfall 5 (`__init__.py` must never be compiled), Pitfall 5B (always test via `pip install wheel` in clean venv, not `sys.path` addition)
**Verification gate:** `unzip -l axiom_ee-*.whl | grep ".py$"` returns only `__init__.py`; compiled EE passes identical CE+EE validation as Phase B; wheel installs cleanly on Python 3.12 in fresh virtualenv

### Phase D: Licence Key Validation + Docs + Docker Hub

**Rationale:** Licence validation is independent of `.so` compilation and can be written and tested in Python source form during Phase B or C. The validation code should be compiled into the `.so` in Phase C, so design it before Phase C builds the wheel. Docker Hub publish and docs updates are release-time steps with no code dependencies — complete as the final gate before tagging v11.0.
**Delivers:** Ed25519 offline licence validation in EE `register()` method; `AXIOM_LICENCE_KEY` env var support; graceful CE fallback on missing/invalid/expired key; CE/EE feature badges in MkDocs (`!!! enterprise` admonitions); `axiom-ce` on Docker Hub with upgrade link; `ee/LICENSE` stub file; `ee_status` field on `/api/features`
**Uses:** `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify()`, `docker/login-action v3`, MkDocs Material admonition syntax
**Avoids:** Pitfall 7 (startup-only licence check — document restart requirement clearly; v11.1 adds periodic re-validation); online-only validation (Ed25519 signed file works air-gapped); plain-string public key constant (split key bytes across multiple variables for obfuscation)
**Verification gate:** Expired licence file → features disabled on next restart; offline validation works with `iptables -I OUTPUT -j DROP`; `curl hub.docker.com/v2/repositories/axiom-laboratories/axiom-ce` resolves; EE docs pages show enterprise admonitions

### Phase Ordering Rationale

- Phase A must come first: every downstream validation step (CE+EE combined, compiled wheel, licence testing) depends on a correctly behaving CE baseline. Running combined-mode tests against a CE that returns 404 instead of 402 produces false results.
- Phase B must precede Phase C: validate in Python source before adding a compilation layer. A broken architecture is much easier to fix in `.py` than in `.so`.
- Phase D licence code should be designed before Phase C is closed, so the licence validation code gets compiled into the `.so`. The remainder of Phase D (docs, Docker Hub) can follow Phase C at any time.
- Gaps 1, 2, and 3 within Phase A are parallel (no dependencies on each other) and can be done as a single batch or sequentially — the order within Phase A does not matter.

### Research Flags

Phases with well-documented patterns (no additional research needed):
- **Phase A:** All three gap fixes are mechanical changes to known code locations; the exact lines to change are identified in ARCHITECTURE.md and PITFALLS.md
- **Phase D (Docker Hub publish):** Workflow delta is minimal and fully specified in STACK.md (add one login step, extend `metadata-action` images list); licence key Ed25519 pattern mirrors existing job-signing infrastructure

Phases requiring careful implementation review (validate against documented patterns; not full external research):
- **Phase B:** The async `register()` pattern and EE table creation via engine are novel for this codebase; the import path changes for 7 router files are high-effort and error-prone — test each router file after migration before proceeding to the next; the `EEContext` guard pattern for stub registration must be established as a protocol before `EEPlugin.register()` is written
- **Phase C:** Pre-audit all EE source for `@dataclass`, `__annotations__`, and `__init__.py` relative imports before writing CI; first Cython build will surface any Python patterns incompatible with pure-Python mode; test compiled wheel via `pip install` in a clean virtualenv before CI merge

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new runtime packages; Cython 3.2.4 and cibuildwheel 3.4.0 versions verified from live PyPI; `importlib.metadata` API confirmed in Python 3.10+ stdlib docs; existing stack validated through 10 prior sprints |
| Features | HIGH | Derived directly from worktree codebase inspection; gap list matches the verified checklist items in `.planning/axiom-oss-ee-split.md`; competitor patterns (PostHog, Sentry, Metabase) cross-referenced |
| Architecture | HIGH | All patterns derived from direct inspection of `ee/__init__.py`, `ee/interfaces/`, `ee/routers/`, `main.py`, `db.py` in the `feature/axiom-oss-ee-split` worktree; no assumptions made from documentation alone |
| Pitfalls | HIGH | Critical pitfalls 1, 2, 6 verified by reading the actual buggy code in the worktree; Cython pitfalls 4 and 5 cross-referenced against official Cython GitHub issues #3336 and CPython bug #59828 |

**Overall confidence:** HIGH

### Gaps to Address

- **EE DB model inventory (15 tables):** PITFALLS.md and ARCHITECTURE.md both reference 15 EE tables, but the complete list of which models to migrate from pre-split git history was not enumerated during research. During Phase B, inspect the pre-split `db.py` git history to confirm the full model list before writing `ee/db_models.py`.
- **Service dependency imports in EE routers:** The 7 EE routers import from `agent_service.services.*` (foundry_service, job_service, etc.). When moved to the private repo, these absolute imports will work only if `axiom-ce` is installed in the same Python environment as `axiom-ee`. Verify this assumption holds during Phase B validation before committing to the architecture.
- **Periodic licence re-validation policy:** v11.0 validates licence at startup only. Pitfall 7 recommends a 12-hour periodic re-check via APScheduler with a 7-day air-gapped grace period. This is deferred to v11.1 but the grace period policy should be documented in `LEGAL.md` or `ee/README.md` at v11.0 release so customer contracts can reference it.

## Sources

### Primary (HIGH confidence)
- `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — confirmed `pkg_resources` usage, no stub mounting in CE path
- `.worktrees/axiom-split/puppeteer/agent_service/ee/interfaces/*.py` — 6 stub routers defined but orphaned (not mounted)
- `.worktrees/axiom-split/puppeteer/agent_service/ee/routers/*.py` — 7 real routers with `...db` relative imports confirmed
- `.worktrees/axiom-split/puppeteer/agent_service/main.py` — lifespan call location confirmed; no `_register_ce_stubs` call
- `.worktrees/axiom-split/puppeteer/agent_service/db.py` — single `Base`, 13 CE tables confirmed; `User` has no `role` column
- `.worktrees/axiom-split/puppeteer/tests/test_bootstrap_admin.py` — `User.role` attribute assertions confirmed on lines 34 and 47
- [Python Packaging — Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — `entry_points(group=...)` API
- [Python importlib.metadata docs](https://docs.python.org/3/library/importlib.metadata.html) — keyword-form `entry_points` API stable on Python 3.10+
- [Cython PyPI](https://pypi.org/project/Cython/) — version 3.2.4 released 2026-01-04 confirmed
- [cibuildwheel pypa docs](https://cibuildwheel.pypa.io/en/stable/platforms/) — platform support and manylinux container handling confirmed
- [Keygen — Offline Licensing](https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/) — Ed25519 signed key structure, offline validation pattern, `exp` claim
- [Keygen — Cryptographic Verification](https://keygen.sh/docs/api/cryptography/) — `ED25519_SIGN` recommended scheme, payload + signature structure
- [pytest — Working with Custom Markers](https://docs.pytest.org/en/stable/example/markers.html) — `pytest_collection_modifyitems`, `config.addinivalue_line`, skip on condition
- `.github/workflows/release.yml` — existing Action versions (docker/login-action@v3, docker/build-push-action@v6, docker/metadata-action@v6) confirmed for Docker Hub addition

### Secondary (MEDIUM confidence)
- [Cython — source files and compilation](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html) — pure Python mode `.py` compilation confirmed
- [FastAPI discussion #9014](https://github.com/fastapi/fastapi/discussions/9014) — silent duplicate route registration behaviour; `UserWarning: Duplicate Operation ID` only symptom
- [Cython GitHub issue #3336](https://github.com/cython/cython/issues/3336) — `@dataclass` annotation stripping in Cython-compiled modules; partial fix in Cython 3 not covering all decorator patterns
- [CPython bug #59828](https://bugs.python.org/issue15623) — `__init__.so` relative import failure confirmed

### Tertiary (LOW confidence)
- [Cython — Python source protection pattern](https://art-vasilyev.github.io/posts/protecting-source-code/) — `build_py` override for `.py` exclusion from wheel; needs validation against current Cython 3.2.4 during Phase C
- [Nuitka GitHub issue #1955](https://github.com/Nuitka/Nuitka/issues/1955) — entry_points discovery requiring explicit `--include-module` flags in Nuitka; used to confirm Nuitka is not the right tool for this use case

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*

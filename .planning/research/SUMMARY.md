# Project Research Summary

**Project:** Axiom v19.0 — Foundry Improvements
**Domain:** Package management / air-gapped image-building platform (Foundry/Smelter pipeline)
**Researched:** 2026-04-01
**Confidence:** HIGH (backend stack, architecture, pitfalls), MEDIUM (mirror sidecars, feature prioritization)

## Executive Summary

Axiom v19.0 Foundry Improvements extends an existing Docker-image-building orchestration platform to fix a fundamental gap (transitive dependency resolution), broaden the multi-ecosystem mirror coverage, add static script analysis, and complete the Foundry CRUD surface. The baseline stack (FastAPI + SQLAlchemy async + React 19 / Radix UI / Tailwind) is validated and unchanged; only targeted additions are required: `pip-tools` and `bandit` on the backend, `react-d3-tree` on the frontend, and up to four new Docker Compose sidecar services for npm (Verdaccio), NuGet (BaGetter), APK (nginx+alpine), and Conda mirroring. The existing `registry:2` service can be repurposed for OCI pull-through by adding `REGISTRY_PROXY_*` environment variables — no new service needed.

The recommended build approach is pipeline-first: fix the `--no-deps` mirror bug and establish the multi-platform wheel layout (manylinux vs musllinux) before adding any new ecosystem backends, because every downstream feature depends on the dependency tree being correct and complete. The DB schema migrations (one ALTER TABLE + three new EE tables) unblock all subsequent phases and must land first. Two new service components — `resolver_service.py` (throwaway Docker containers for dep resolution) and `script_analyzer_service.py` (in-process AST/regex analysis) — are architecturally clean additions that follow existing patterns and do not require infrastructure changes.

The top risks are: silent runtime failures from incomplete mirrors (manylinux wheels served to Alpine/musl nodes), circular-dependency loops hanging the resolution worker, Docker socket contention between Foundry builds and dep-resolution containers, and Conda's commercial licensing exposure if the `defaults` channel is not blocked. All of these have clear prevention strategies that must be baked into the Phase 1 implementation, not patched later. The Foundry CRUD completeness work (Edit Blueprint / Tool Recipe / Approved OS) carries its own risk: Blueprint edits without optimistic-locking version tracking cause silent lost-write corruption, so a `version` column and HTTP 409 response are non-optional.

## Key Findings

### Recommended Stack

The existing stack requires only two new backend packages and one new frontend package. `pip-tools>=7.4,<8` provides the `pip-compile` subprocess command for deterministic transitive dependency resolution. `bandit>=1.8,<2` provides Python script security scanning via subprocess JSON output. `react-d3-tree@3.6.6` (253K weekly npm downloads, React 19-compatible) handles the dep-tree visualization. All other frontend changes use existing Radix UI, Tailwind, and shadcn patterns already in `package.json`.

Mirror sidecar decisions: Verdaccio v6 for npm (zero-config pull-through, Docker Hub official image), BaGetter (`ghcr.io/bagetter/bagetter:latest`) for NuGet (active fork of abandoned BaGet, SQLite backend, no external DB required), nginx:alpine + alpine rsync syncer for APK, and `conda-mirror` 0.10.0 run as a Python subprocess inside the existing agent container for Conda (no new sidecar image). The existing `registry:2` handles OCI pull-through via `REGISTRY_PROXY_REMOTEURL` env-var configuration.

**Core technologies (new additions only):**
- `pip-tools` (`pip-compile`): deterministic transitive dep resolution — subprocess invocation, produces pinned `requirements.txt` including all transitives
- `bandit>=1.8,<2`: Python script security scan — subprocess JSON mode; returns severity/confidence/line-number per finding
- Python `ast` stdlib: import extraction from Python scripts — zero-dependency, handles syntax errors gracefully
- `react-d3-tree@3.6.6`: interactive collapsible dep-tree viewer — accepts `RawNodeDatum` JSON directly from backend
- `verdaccio:6`: npm pull-through proxy — anonymous publish/pull, Docker-native, zero-config
- `ghcr.io/bagetter/bagetter:latest`: NuGet mirror with pull-through caching — SQLite backend, .NET 8 in image
- `nginx:alpine` + `alpine` syncer: APK package mirror — rsync pull, static file serving
- `registry:2` (existing): OCI pull-through — activate via `REGISTRY_PROXY_REMOTEURL` env var

### Expected Features

**Must have (table stakes — P1):**
- Edit Image Recipe (Blueprint) — CRUD surface is broken without edit; need `PATCH /api/blueprints/{id}` + modal
- Edit Tool Recipe (UI only) — backend PATCH endpoint already exists; purely a frontend gap
- Edit Approved OS — name/family/version must be correctable; need `PATCH /api/approved-os/{id}` + inline form
- Transitive dependency resolution + tree viewer — headline feature; full dep graph visible before build; CVE scans the complete tree
- CVE scan of transitive deps (pre-build) — pip-audit already integrated; extend to include `IngredientDependency` rows
- Runtime dep confirmation dialog — surface `CapabilityMatrix.runtime_dependencies` in a pre-build confirmation modal
- Curated Bundles (4-6 seeded) — "Data Science", "Web Scraping", "Infrastructure", "Monitoring"; Bundle picker in wizard

**Should have (competitive — P2):**
- npm mirror (Verdaccio) — most broadly applicable new ecosystem; low storage footprint vs Conda/OCI
- Script Analyzer — auto-detect deps from script text; genuine differentiator (no major competitor offers this in the image-build flow)
- NuGet mirror (BaGetter) — needed for PowerShell-heavy environments
- Starter Templates (seeded) — low complexity; requires bundles to be useful first
- OCI pull-through mirror — high value for air-gap completeness; existing `registry:2` makes this low infrastructure cost

**Defer (v20+):**
- Conda mirror — HIGH storage footprint (500+ GB for full channel); only if data science becomes an explicit ICP
- Plain-language semantic search — requires embedding infrastructure; defer until catalog grows large enough
- Role-based Foundry view — low backend cost but MEDIUM frontend; defer until bundles + starter templates land
- Simplified auto-naming — UX polish; not urgent
- apk full channel sync — HIGH complexity; `apk fetch` approach sufficient for current milestone

### Architecture Approach

The architecture is an additive extension of the existing service layer. Two new service files join the existing `foundry_service.py`, `smelter_service.py`, and `mirror_service.py`: `resolver_service.py` spawns throwaway Docker containers per ecosystem to resolve the full dep tree (same `asyncio.create_subprocess_exec` + Docker socket pattern as Foundry builds), and `script_analyzer_service.py` runs in-process synchronous AST/regex analysis returning results in <50ms. The `mirror_service.py` gains an ecosystem dispatch table keyed on a new `ecosystem` column added to `approved_ingredients`. New DB tables (`ingredient_dependencies`, `curated_bundles`, `curated_bundle_items`) use `EEBase` and are created automatically by the EE plugin's `create_all` call; only the `ecosystem` column addition to `approved_ingredients` requires a migration SQL file.

**Major components:**
1. `resolver_service.py` (new) — spawns ecosystem-appropriate throwaway containers; parses stdout dep list; inserts `IngredientDependency` rows; triggers mirror + CVE scan as background tasks; gated by `_resolve_semaphore = asyncio.Semaphore(3)`
2. `mirror_service.py` (extended) — ecosystem dispatch table replaces OS-family-based dispatch; each new `_mirror_<eco>()` method uses throwaway containers; separate named volumes per ecosystem prevent I/O contention
3. `script_analyzer_service.py` (new) — in-process Python AST walker + Bash/PowerShell regex; static `import_to_pypi.json` mapping file; cross-references against `approved_ingredients` and `curated_bundle_items` DB tables
4. Mirror sidecars (new compose services) — Verdaccio (npm), BaGetter (NuGet), nginx:alpine (APK); all behind `--profile mirrors` compose profile
5. EE DB schema additions — `ingredient_dependencies`, `curated_bundles`, `curated_bundle_items` tables + `ecosystem` column on `approved_ingredients`

### Critical Pitfalls

1. **`--no-deps` mirror leaves dep-tree incomplete, STRICT mode fails at install time** — drop `--no-deps` for mirror population; keep only for single-wheel CVE scanning; add post-mirror smoke test (`pip install --no-index` in network-isolated throwaway container). This is the root bug the milestone exists to fix.

2. **Platform tag mismatch (manylinux vs musllinux) breaks Alpine images silently** — Alpine uses musl libc; glibc wheels fail at runtime with no helpful Python error. Mirror each package to separate paths (`pypi/manylinux/` and `pypi/musllinux/`); use `--platform musllinux_1_1_x86_64` for Alpine targets; validate wheel filename platform tag before setting `mirror_status = MIRRORED`.

3. **Circular dependency explosion hangs the resolution worker** — use `pip-compile` (which detects cycles cleanly) rather than recursive `pip download`; set subprocess `timeout=90`; maintain a `visited` set per resolution job; cap concurrent resolution with `asyncio.Semaphore(3)` separate from the Foundry build semaphore.

4. **Docker socket contention between Foundry builds and dep-resolution containers** — use a single shared `_docker_semaphore = asyncio.Semaphore(3)` for all Docker socket operations, or run dep-resolution in-process using a virtualenv (eliminates socket contention for the resolution path).

5. **Blueprint edit without optimistic locking silently loses concurrent writes** — add `version` integer column to `blueprints`; `PATCH` must include `WHERE version = :submitted_version`; return HTTP 409 on conflict; frontend edit modal must read and submit the `version` field.

6. **Conda `defaults` channel triggers commercial licensing violation** — Anaconda's 2025 ToS covers automated processes; requires paid licence at 200+ employees. Default `.condarc` must specify `conda-forge` only; display a blocking warning when user configures `defaults`, `main`, `r`, or `msys2` channels.

## Implications for Roadmap

Based on the combined research, the natural phase structure follows the build-order dependency chain from ARCHITECTURE.md, front-loaded with the pitfall mitigations from PITFALLS.md.

### Phase 1: DB Schema and Migration Foundation
**Rationale:** All subsequent phases require the new DB tables and the `ecosystem` column on `approved_ingredients`. This is pure schema work — fast, low risk, high unblocking value. The `blueprints.version` and `blueprints.updated_at` columns must also land here to prevent blueprint edit implementation in Phase 3 from being done without them.
**Delivers:** `ingredient_dependencies`, `curated_bundles`, `curated_bundle_items` tables (via `EEBase create_all`); `approved_ingredients.ecosystem` column (via migration SQL file); `blueprints.version` and `blueprints.updated_at` columns.
**Addresses:** Foundry CRUD completeness prerequisites; transitive resolution storage; optimistic locking foundation.
**Avoids:** Mid-phase schema surprises that force rework of already-written service code.

### Phase 2: Transitive Dependency Resolution (Core Pipeline Fix)
**Rationale:** This is the root problem the milestone exists to fix. It must precede all ecosystem mirror work because every new `_mirror_<eco>()` method should mirror the full dep tree. It also enables the CVE pre-build scan extension and establishes the dual-path mirror layout (manylinux/musllinux) that all subsequent mirror work depends on.
**Delivers:** `resolver_service.py`; throwaway-container resolution pipeline; `pip-compile`-based dep-tree generation; `ingredient_dependencies` populated; post-mirror smoke test; dual-path mirror layout (`pypi/manylinux/`, `pypi/musllinux/`).
**Uses:** `pip-tools` (`pip-compile`), `packaging`, Docker socket (throwaway container pattern), `asyncio.Semaphore(3)` for resolution.
**Implements:** Pitfall 1 (`--no-deps` fix), Pitfall 2 (platform tag split), Pitfall 3 (circular dep guard), Pitfall 4 (shared Docker semaphore).
**Research flag:** Standard patterns — `pip-compile` subprocess, Docker throwaway containers confirmed. No additional research needed.

### Phase 3: Foundry CRUD Completeness
**Rationale:** High operator value, no new infrastructure dependencies, parallelizable with Phase 2 development. Three independent backend+frontend pairs (Edit Blueprint, Edit Tool Recipe UI, Edit Approved OS). Can overlap Phase 2 since they touch different files.
**Delivers:** `PATCH /api/blueprints/{id}` with version tracking + HTTP 409; Edit Tool Recipe modal (frontend only, PATCH backend exists); `PATCH /api/approved-os/{id}`; stale-badge propagation to downstream Node Images on Blueprint edit; runtime dep confirmation modal.
**Avoids:** Pitfall 6 (Blueprint edit without version tracking), Pitfall 7 (concurrent Blueprint edit lost write).
**Research flag:** Standard CRUD + optimistic locking patterns. No additional research needed.

### Phase 4: APT and APK Mirror Backends + Compose Profile Separation
**Rationale:** Highest air-gap value after the PyPI fix. APT completes the existing `_mirror_apt()` stub (currently `pass`). APK enables Alpine-based images. Both use the throwaway-container pattern established in Phase 2. Critically, the compose `--profile mirrors` separation must be established in this phase before any subsequent sidecar is added.
**Delivers:** `_mirror_apt()` implementation (debian throwaway + dpkg-scanpackages); `_mirror_apk()` implementation (alpine throwaway + apk index); `apk-mirror` nginx sidecar in compose behind `--profile mirrors`; compose profile pattern that all subsequent phases inherit.
**Avoids:** Pitfall 9 (compose service sprawl — profile separation must precede any new sidecar).
**Research flag:** Standard patterns — confirmed in STACK.md and ARCHITECTURE.md. No additional research needed.

### Phase 5: CVE Scan Extension to Transitive Deps
**Rationale:** Requires Phase 2 (`IngredientDependency` rows must exist). One additional DB query in `scan_vulnerabilities()` in `smelter_service.py`. Small scope, high security value — transitive deps were previously invisible to CVE scanning.
**Delivers:** `scan_vulnerabilities()` merges `ingredient_dependencies` rows into pip-audit input; pre-build CVE visibility for the full dep tree.
**Implements:** Feature: "CVE scan transitive deps (pre-build)" — P1 in feature prioritization matrix.
**Research flag:** Standard patterns. No additional research needed.

### Phase 6: Script Analyzer Service
**Rationale:** Self-contained; requires only Phase 1 (to query `approved_ingredients`). No throwaway containers — pure in-process. Ships independently once CRUD phases are stable.
**Delivers:** `script_analyzer_service.py`; `POST /api/smelter/analyze-script` endpoint; `import_to_pypi.json` static mapping file (100+ common aliases: PIL→Pillow, cv2→opencv-python, sklearn→scikit-learn, etc.); `sys.stdlib_module_names` exclusion; advisory UI panel in job dispatch form.
**Avoids:** Pitfall 8 (AST stdlib misclassification) — stdlib exclusion list and alias mapping must ship with Phase 6, not be patched after.
**Research flag:** Standard patterns. No additional research needed.

### Phase 7: Curated Bundles and Starter Templates
**Rationale:** Requires Phase 1 (tables). More useful after Phase 4+ because bundles referencing mirrored ingredients work end-to-end. Seeded starter packs give immediate operator value without requiring operators to understand package names.
**Delivers:** `CuratedBundle` + `CuratedBundleItem` tables populated; CRUD endpoints on `smelter_router.py`; seeded starter packs (Data Science, Web Scraping, Infrastructure, Monitoring) via EE plugin startup hook with `ON CONFLICT DO NOTHING`; Bundle picker UI in wizard; `POST /api/smelter/bundles/{id}/add-to-blueprint` action.
**Avoids:** UX pitfall of Curated Bundle apply silently overwriting existing blueprint packages (merge additively; show conflict list).
**Research flag:** Standard CRUD + seeding patterns. No additional research needed.

### Phase 8: npm and NuGet Mirror Backends
**Rationale:** MEDIUM complexity, MEDIUM operator value. Build after the core pipeline (Phases 1-5) is stable to avoid reworking the ecosystem dispatch table. Verdaccio and BaGetter are proven Docker-native services.
**Delivers:** `_mirror_npm()` (node:20-slim throwaway + verdaccio push); `npm-registry` Verdaccio sidecar; `_mirror_nuget()` (dotnet:8.0 throwaway + BaGet push); `nuget-registry` BaGetter sidecar; `nuget.config` injection with `packageSourceMapping` in Foundry Dockerfiles.
**Avoids:** Pitfall 10 (NuGet silent fallback to nuget.org — `packageSourceMapping` with `pattern="*"` required from day one).
**Research flag:** BaGetter integration is MEDIUM confidence. A short spike to validate the API key auth flow for `nuget push` inside a throwaway container is recommended before committing to the implementation approach.

### Phase 9: Frontend — Dep Tree Viewer and Mirror Ecosystem UI
**Rationale:** Depends on backend phases being stable. Frontend-only changes after backend API shapes are finalized prevent rework.
**Delivers:** `DepTreeModal.tsx` using `react-d3-tree@3.6.6`; `GET /api/smelter/ingredients/{id}/dep-tree` endpoint returning nested JSON; mirror ecosystem tabs in Admin UI; `deps_resolved: bool` + `dep_count: int` on ingredient badge; blueprint diff view against `last_built_definition` snapshot.
**Uses:** `react-d3-tree@3.6.6`, existing Radix UI + Tailwind patterns.
**Research flag:** Standard patterns. No additional research needed.

### Phase 10: OCI Pull-Through and Operator UX Polish
**Rationale:** Search and naming changes are low-risk query-param additions. OCI pull-through is a `registry:2` env-var change — lowest infrastructure cost of all mirror backends. Both are last because they depend on the full ecosystem being stable.
**Delivers:** `q` query param on `GET /api/smelter/ingredients` for name search; `registry:2` reconfigured with `REGISTRY_PROXY_REMOTEURL`; simplified naming suggestions on Blueprint create (server-side display label generation); role-based Foundry view conditional rendering using existing `useRole()` hook.
**Research flag:** Standard patterns. No additional research needed.

### Phase Ordering Rationale

- **DB schema first** (Phase 1): All new features read/write new tables. Schema changes cannot be retrofitted without breaking running deployments. `blueprints.version` must land before any Blueprint edit work.
- **Transitive resolution second** (Phase 2): Every other mirror feature is built on top of the resolved dep tree. Shipping it first means subsequent ecosystem phases (4, 8) automatically benefit from the correct multi-platform mirror layout.
- **CRUD completeness early, parallel** (Phase 3): Parallelizable with Phase 2 since they touch different files. High operator value, no new infrastructure. Early delivery builds confidence while complex pipeline work progresses.
- **Air-gap critical paths before extended ecosystems** (Phase 4 before 8): APT/APK are required for existing Debian/Alpine workflows. npm/NuGet serve narrower audiences.
- **CVE extension before UX** (Phase 5): Correctness before polish. Transitive CVE visibility is a security property.
- **Compose profile separation in Phase 4**: Establishes the `--profile mirrors` pattern before any sidecar is merged, preventing cold-start regression across all subsequent phases.
- **Frontend last** (Phase 9): Ensures backend API shapes are stable before investing in UI components.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 8 (BaGetter/NuGet):** BaGetter integration is MEDIUM confidence. The API key auth flow for `nuget push` inside a throwaway container needs a short spike before Phase 8 planning. The `packageSourceMapping` XML injection into Foundry Dockerfiles also needs validation against a real BaGet instance.
- **Phase 2 (pypiserver subdirectory serving):** The dual-path manylinux/musllinux layout assumes `pypiserver` correctly serves packages from subdirectories with accurate `simple/` index URLs. Confirm this before committing to the path naming convention.

Phases with standard patterns (skip research-phase):
- **Phase 1:** ALTER TABLE migrations and EEBase model additions — established pattern in this codebase.
- **Phase 3:** PATCH endpoints with optimistic locking — SQLAlchemy version_id_col and HTTP 409 pattern well-documented.
- **Phase 4:** Throwaway container pattern for APT/APK — confirmed working in Foundry builds.
- **Phase 5:** pip-audit with file input — already integrated in `smelter_service.py`.
- **Phase 6:** Python `ast` stdlib — official docs, no uncertainty.
- **Phase 7:** EE plugin startup seeding with `ON CONFLICT DO NOTHING` — identical pattern to permission seeding already in codebase.
- **Phase 9:** `react-d3-tree` — HIGH confidence, straightforward integration.
- **Phase 10:** Query param search + `registry:2` env-var — standard patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Backend additions confirmed via official pip/bandit/PyPI docs. Frontend lib confirmed via npm. Mirror sidecar images confirmed on Docker Hub / GitHub. Only MEDIUM for conda-mirror (last PyPI release 2022, still functional). |
| Features | MEDIUM-HIGH | Feature list derived from direct codebase inspection + competitor analysis. Priority judgments are opinionated but well-reasoned. Conda demand is uncertain — defer to v20+ is the correct call. |
| Architecture | HIGH | Based on direct codebase inspection of all relevant service files, EE models, router stubs, and compose file. Throwaway container pattern validated against existing `foundry_service.py`. |
| Pitfalls | HIGH | `--no-deps` bug, musllinux platform tag, Conda licensing, and NuGet fallback all backed by official documentation or confirmed issue trackers. SQLAlchemy optimistic locking well-documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **BaGetter throwaway-container auth flow**: BaGetter requires an API key for `nuget push`. The mechanism for passing `BAGET_API_KEY` into a throwaway container needs a spike validation before Phase 8 planning. Low risk, but unverified end-to-end.
- **pypiserver subdirectory serving**: The dual manylinux/musllinux path split assumes `pypiserver` generates correct `simple/` index entries for packages in subdirectories. Confirm during Phase 2 planning before committing to the directory layout.
- **conda-mirror maintenance status**: `conda-mirror 0.10.0` was last released 2022. If it fails on current `conda-forge` repodata format, the fallback is `conda-mirror-ng`. Evaluate before any Conda work (currently deferred to v20+).
- **Shared Docker semaphore vs. in-process virtualenv**: PITFALLS.md presents two options for Docker socket contention prevention. This architectural decision must be made explicitly at the start of Phase 2, not deferred.

## Sources

### Primary (HIGH confidence)
- pip documentation (official) — `pip download`, `--no-deps` semantics, dependency resolution
- pip-tools GitHub (jazzband) — `pip-compile` transitive resolution to pinned `requirements.txt`
- PyPI JSON API (official) — `requires_dist` metadata endpoint
- Python `ast` stdlib docs (official) — `Import`, `ImportFrom` nodes, `ast.walk()`
- PEP 656 (official) — musllinux platform tag specification
- Python packaging platform compatibility tags (official) — manylinux vs musllinux
- Docker registry:2 pull-through config (distribution.github.io) — `REGISTRY_PROXY_REMOTEURL`
- Anaconda Terms of Service 2025 — commercial licensing threshold and covered automated processes
- SQLAlchemy optimistic locking docs (official) — `version_id_col` pattern
- Direct codebase inspection: `mirror_service.py`, `foundry_service.py`, `smelter_service.py`, `foundry_router.py`, `smelter_router.py`, `ee/foundry/models.py`, `ee/smelter/models.py`, `compose.server.yaml`

### Secondary (MEDIUM confidence)
- BaGetter GitHub (bagetter/BaGetter) — NuGet mirror with pull-through; active fork of abandoned BaGet
- conda-mirror PyPI — v0.10.0, conda-forge channels (package not actively maintained since 2022)
- react-d3-tree npm — v3.6.6, 253K weekly downloads, React 19 compatible
- NuGet offline issue tracker (NuGet/Home#2623) — silent fallback behavior
- Docker concurrent builds resource exhaustion (docker/buildx#3006) — socket contention

### Tertiary (MEDIUM-LOW confidence)
- Package manager mirroring landscape articles (2026) — ecosystem overview, feature comparisons
- Alpine mirror community project (m3talstorm/docker-alpine-mirror) — rsync + nginx pattern
- shadcn-tree-view GitHub — Radix Collapsible-based tree alternative

---
*Research completed: 2026-04-01*
*Ready for roadmap: yes*

# Architecture Research

**Domain:** Foundry/Smelter pipeline improvements — transitive deps, multi-ecosystem mirrors, script analysis, operator UX
**Researched:** 2026-04-01
**Confidence:** HIGH — based on direct codebase inspection of existing services, EE plugin, DB models, and compose file

---

## Existing Architecture (Baseline)

Understanding the current shape is essential before placing new components.

```
compose.server.yaml
  agent (FastAPI :8001)
    agent_service/services/foundry_service.py   — Dockerfile gen + docker build
    agent_service/services/smelter_service.py   — CVE scan (pip-audit), validate_blueprint
    agent_service/services/mirror_service.py    — pip download --no-deps, APT placeholder
    agent_service/ee/routers/
      foundry_router.py    — EE: Blueprint/Template/CapabilityMatrix CRUD
      smelter_router.py    — EE: Ingredients, mirror config, mirror health

  pypi       (pypiserver :8080)    — serves mirror-data volume as PyPI simple index
  devpi      (devpi :3141)         — EE wheel index for internal packages
  mirror     (Caddy :8081)         — serves APT mirror from same mirror-data volume
  registry   (Distribution :5000)  — OCI image registry for built puppet images
  db         (Postgres)

EE Plugin (axiom-ee — entry_points):
  ee/foundry/models.py    — Blueprint, PuppetTemplate, CapabilityMatrix,
                            ApprovedOS, ImageBOM, PackageIndex, Artifact
  ee/smelter/models.py    — ApprovedIngredient
  ee/foundry/services.py  — foundry build logic (Cython-compiled in production)

Shared volume: mirror-data
  /app/mirror_data/pypi/   — wheels/sdists served by pypi sidecar
  /app/mirror_data/apt/    — .deb files served by Caddy mirror sidecar
```

Key constraints from the current code:

- `mirror_service._mirror_pypi()` uses `pip download --no-deps`. The `--no-deps` flag is the gap: it only mirrors the explicitly listed package, not its transitive tree.
- `smelter_service.scan_vulnerabilities()` operates on a flat list of `ApprovedIngredient` rows. Transitive dependencies are not in this table, so they are not CVE-scanned.
- `ApprovedIngredient.os_family` (DEBIAN, ALPINE, FEDORA) currently acts as a proxy for ecosystem — all current ingredients are PyPI packages. This conflates OS scope with package ecosystem.
- The Docker socket is used by `foundry_service.py` via `asyncio.create_subprocess_exec("docker", "build", ...)`. The same socket is available for throwaway resolver containers.

---

## New Features — Integration Points

### 1. Transitive Dependency Resolution

**Where does resolution run: in-process or throwaway container?**

Use throwaway containers, not in-process execution. Rationale:
- pip/conda/npm/apt all need access to the local mirror sidecars during resolution (to resolve what versions are actually available locally).
- Running pip inside the agent container mutates its Python environment — even `pip download` touches the index cache.
- Throwaway containers already exist as a pattern: `foundry_service.py` runs `docker build` via `/tmp/puppet_build_*` directories and `asyncio.create_subprocess_exec`. The same mechanism works for resolution.
- Different ecosystems require different base images (python:3.12-slim for pip, node:20-slim for npm, etc.) — only throwaway containers make this practical.

**New component: `resolver_service.py`** in `agent_service/services/`

```
resolver_service.py
  resolve_transitive(ingredient_id, ecosystem) -> DepTreeResult
    1. Fetch ApprovedIngredient from DB
    2. Select base image per ecosystem:
         PYPI   -> python:3.12-slim
         APT    -> debian:12-slim
         APK    -> alpine:3.20
         NPM    -> node:20-slim
         CONDA  -> continuumio/miniconda3
         NUGET  -> mcr.microsoft.com/dotnet/sdk:8.0
    3. Construct resolver command:
         PYPI   -> pip download --dry-run --no-cache-dir <pkg> 2>&1
                   (pipdeptree gives cleaner tree: pip install pipdeptree && pipdeptree --packages <pkg>)
         APT    -> apt-cache depends --recurse <pkg>
         APK    -> apk info --depends <pkg>
         NPM    -> npm ls <pkg> --all --json
         CONDA  -> conda install --dry-run <pkg> 2>&1
         NUGET  -> dotnet add package <pkg> --dry-run (or nuget resolve)
    4. Run: docker run --rm --network puppeteer_default
            -e PIP_INDEX_URL=http://pypi:8080/simple (for PYPI)
            <image> sh -c "<resolver command>"
    5. Parse stdout -> extract dep name + version per line
    6. INSERT IngredientDependency rows for each discovered dep
    7. For each dep not already mirrored: asyncio.create_task(mirror_ingredient)
    8. Trigger CVE scan for new deps: asyncio.create_task(scan_vulnerabilities)
```

**New DB table: `ingredient_dependencies`** (EE — add to `ee/smelter/models.py`)

```python
class IngredientDependency(EEBase):
    __tablename__ = "ingredient_dependencies"
    id: Mapped[str]                      # UUID
    parent_ingredient_id: Mapped[str]    # FK -> approved_ingredients.id (soft ref)
    dep_name: Mapped[str]                # dependency package name
    dep_version_resolved: Mapped[str]    # pinned version discovered at resolution time
    ecosystem: Mapped[str]               # PYPI, APT, APK, NPM, CONDA, NUGET
    depth: Mapped[int]                   # 1=direct, 2=transitive, etc.
    auto_approved: Mapped[bool]          # True if automatically pulled in
    mirror_status: Mapped[str]           # PENDING, MIRRORED, FAILED
    created_at: Mapped[datetime]
```

**Smelter service changes:**
- `add_ingredient()` — after initial mirror completes, fire `asyncio.create_task(resolver_service.resolve_transitive(id))`
- `scan_vulnerabilities()` — add second DB query to fetch all `IngredientDependency` rows with `auto_approved=True`, merge into the `reqs` list before running pip-audit. No structural change to the pip-audit invocation.

**New endpoints (add to `smelter_router.py`):**
- `GET /api/smelter/ingredients/{id}/dep-tree` — return nested JSON of resolved deps for UI tree viewer
- `POST /api/smelter/ingredients/{id}/resolve-deps` — manually trigger resolution (in case auto-resolution failed)

**Semaphore for throwaway containers:** Apply the same `asyncio.Semaphore(2)` pattern as `FoundryService._build_semaphore` to limit concurrent Docker container spawns. Add `_resolve_semaphore = asyncio.Semaphore(3)` to `ResolverService`.

---

### 2. Multi-Ecosystem Mirror Backends

**Current state:** `mirror_service._mirror_pypi()` is functional. `_mirror_apt()` is a stub (placeholder `pass`). No other ecosystem backends exist.

**Design: ecosystem dispatch table in `mirror_service.py`**

The `ApprovedIngredient` model needs an explicit `ecosystem` field. This decouples OS scope (DEBIAN vs ALPINE) from package ecosystem (PyPI vs APT vs APK).

Add to `ee/smelter/models.py`:
```python
class ApprovedIngredient(EEBase):
    ...
    ecosystem: Mapped[str] = mapped_column(String(20), default="PYPI", server_default="'PYPI'")
```

Migration: `ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI'`

Then in `mirror_service.py`, replace the `if ingredient.os_family in [...]` dispatch with:

```python
ECOSYSTEM_HANDLERS = {
    "PYPI":   MirrorService._mirror_pypi,
    "APT":    MirrorService._mirror_apt,
    "APK":    MirrorService._mirror_apk,
    "NPM":    MirrorService._mirror_npm,
    "CONDA":  MirrorService._mirror_conda,
    "NUGET":  MirrorService._mirror_nuget,
    "OCI":    MirrorService._mirror_oci,
}

handler = ECOSYSTEM_HANDLERS.get(ingredient.ecosystem, MirrorService._mirror_pypi)
await handler(db, ingredient)
```

**Each new backend mirrors by running a throwaway container** (same pattern as resolver service — no ecosystem toolchain installed in agent image):

```
_mirror_apt(ingredient)   -> docker run debian:12-slim apt-get download <pkg>
                             copy .deb to /app/mirror_data/apt/<pkg>/
                             run dpkg-scanpackages to regenerate Packages.gz

_mirror_apk(ingredient)   -> docker run alpine:3.20 apk fetch <pkg>
                             copy .apk to /app/mirror_data/apk/
                             run apk index to regenerate APKINDEX

_mirror_npm(ingredient)   -> docker run node:20-slim npm pack <pkg>
                             push to verdaccio via npm publish --registry http://npm:4873

_mirror_conda(ingredient) -> docker run continuumio/miniconda3 conda install --download-only <pkg>
                             copy to /app/mirror_data/conda/<channel>/
                             run conda index on the channel directory

_mirror_nuget(ingredient) -> docker run mcr.microsoft.com/dotnet/sdk:8.0 dotnet nuget push <pkg>
                             OR: nuget download + push to baget via HTTP PUT

_mirror_oci(ingredient)   -> docker pull <image_uri>
                             docker push localhost:5000/<name>:<tag>
                             (no throwaway needed — docker socket direct)
```

**New sidecar services** (add to `compose.server.yaml`):

| Ecosystem | Service Name | Image | Port | Mirror Data Path |
|-----------|-------------|-------|------|-----------------|
| APT (existing, extend) | `mirror` | Caddy | :8081 | `/app/mirror_data/apt/` |
| APK (new) | `apk-mirror` | `nginx:alpine` | :8082 | `/app/mirror_data/apk/` |
| npm (new) | `npm-registry` | `verdaccio/verdaccio` | :4873 | `/app/mirror_data/npm/` |
| NuGet (new) | `nuget-registry` | `bagetter/baget` | :5555 | `/app/mirror_data/nuget/` |
| Conda (new) | `conda-mirror` | `nginx:alpine` | :8083 | `/app/mirror_data/conda/` |
| OCI (existing) | `registry` | `registry:2` | :5000 | `registry-data` volume |

All sidecars except OCI share the `mirror-data` volume. Each mounts a subdirectory.

**Mirror URL Config table extension** (using existing `Config` key/value pattern — no new table):

```
PYPI_MIRROR_URL    = "http://pypi:8080/simple"      (existing)
APT_MIRROR_URL     = "http://mirror:80/apt"          (existing)
APK_MIRROR_URL     = "http://apk-mirror:8082/apk"   (new)
NPM_MIRROR_URL     = "http://npm-registry:4873"      (new)
CONDA_MIRROR_URL   = "http://conda-mirror:8083/conda"(new)
NUGET_MIRROR_URL   = "http://nuget-registry:5555/v3/index.json" (new)
```

`MirrorService.get_pip_conf_content()` already reads from env/Config. Add parallel `get_npm_conf_content()`, `get_conda_condarc_content()`, `get_nuget_nuget_config_content()` methods for Dockerfile injection in `foundry_service.py`.

**Dockerfile injection in `foundry_service.py`:** The build currently injects `pip.conf` and `sources.list`. For multi-ecosystem, extend to also inject package manager configs per ecosystem detected from the blueprint's `packages` dict keys. This is additive — existing behavior unchanged.

---

### 3. Script Analyzer

**Where it runs:** In-process in the agent container — no throwaway container needed. Pure static analysis with no I/O beyond one DB query.

**New component: `script_analyzer_service.py`** in `agent_service/services/`

```
ScriptAnalyzerService
  analyze(script: str, runtime: str) -> ScriptAnalysisResult
    if runtime == "python":
      ast.parse(script)
      walk AST for ast.Import and ast.ImportFrom nodes
      extract top-level module names (e.g. "import cv2" -> "cv2")
      exclude sys.stdlib_module_names (Python 3.10+ builtin set)
      normalize to PyPI package names via static mapping file
      (e.g. "cv2" -> "opencv-python", "PIL" -> "Pillow", "sklearn" -> "scikit-learn")

    elif runtime == "bash":
      regex scan for: apt-get install, apt install, pip install, npm install, yum install
      extract package names from args

    elif runtime == "powershell":
      regex scan for: Install-Package, pip install, nuget install
      extract package names from args

    cross-reference each detected package against:
      1. approved_ingredients (exact + ilike match)
      2. curated_bundle_items (for bundle suggestions)

    return ScriptAnalysisResult(
      detected_imports: List[str],
      matched_ingredients: List[IngredientRef],
      unmatched_imports: List[str],
      suggested_bundles: List[BundleRef],
    )
```

**Import-to-PyPI mapping file:** A JSON file bundled in the agent image (e.g. `agent_service/data/import_to_pypi.json`) maps non-obvious import names to PyPI package names. This is a static, air-gap-safe lookup. Does not require an internet connection. Initial set of ~100 common mappings covers the most frequent cases.

**New endpoint:** `POST /api/smelter/analyze-script` (EE, `foundry:read` permission)
- Request: `{"script": "...", "runtime": "python"}`
- Response: `ScriptAnalysisResult`
- This is synchronous — analysis is fast (<50ms). No background task needed.

**Frontend integration:** Add "Analyze" button in the Job dispatch form's script step. On click: POST to analyze-script, show a sidebar panel listing detected packages with status indicators (approved / not-in-smelter) and "Add to Smelter" quick-actions for unmatched imports.

---

### 4. Curated Bundles

**Two new DB tables** (EE — add to `ee/smelter/models.py`):

```python
class CuratedBundle(EEBase):
    __tablename__ = "curated_bundles"
    id: Mapped[str]              # UUID
    name: Mapped[str]            # "Data Science Stack"
    description: Mapped[str]
    category: Mapped[str]        # ML, WEB, DEVOPS, SECURITY, etc.
    created_by: Mapped[str]      # username
    is_builtin: Mapped[bool]     # True for seeded starter packs
    created_at: Mapped[datetime]

class CuratedBundleItem(EEBase):
    __tablename__ = "curated_bundle_items"
    id: Mapped[str]
    bundle_id: Mapped[str]       # soft FK to curated_bundles.id
    ingredient_name: Mapped[str]
    version_constraint: Mapped[str]
    ecosystem: Mapped[str]
    display_order: Mapped[int]
```

**Seeded starter packs:** Populated by EE plugin startup hook in `plugin.py` (same pattern as permission seeding). Use `ON CONFLICT DO NOTHING` semantics to make idempotent.

Example starter packs:
- "Data Science" — numpy, pandas, scikit-learn, matplotlib, scipy (PYPI/DEBIAN)
- "Web Scraping" — requests, beautifulsoup4, lxml, httpx (PYPI/DEBIAN)
- "Infrastructure" — boto3, paramiko, ansible (PYPI/DEBIAN)
- "Monitoring" — prometheus-client, psutil, py-cpuinfo (PYPI/DEBIAN)

**New endpoints** (add to `smelter_router.py`):
- `GET /api/smelter/bundles` — list all bundles with item counts
- `POST /api/smelter/bundles` — create custom bundle
- `DELETE /api/smelter/bundles/{id}` — delete (block if `is_builtin=True`)
- `GET /api/smelter/bundles/{id}/items` — list items in bundle
- `POST /api/smelter/bundles/{id}/add-to-blueprint` — adds all bundle ingredients to a blueprint's packages list

---

### 5. EE Dashboard CRUD Completeness

**Edit Blueprint:** `PUT /api/blueprints/{id}` stub already exists in `foundry_stub_router.py`. EE `foundry_router.py` needs full implementation: fetch, update `definition` JSON, re-run two-pass CapabilityMatrix validation, increment `version`, commit. Frontend: add pencil icon to blueprint cards in Templates.tsx tab 1.

**Edit Tool Recipe (CapabilityMatrix):** `PATCH /api/capability-matrix/{id}` stub in stub router. EE implementation: update `injection_recipe`, `validation_cmd`, `runtime_dependencies`. Frontend: inline edit row in capability matrix table.

**Approved OS Management:** `ApprovedOS` model already exists in `ee/foundry/models.py` but has no router. Add CRUD endpoints:
- `GET /api/foundry/approved-os`
- `POST /api/foundry/approved-os`
- `DELETE /api/foundry/approved-os/{id}`
- Stub endpoints needed in `foundry_stub_router.py` for CE. Frontend: new "Approved OS" tab or sub-panel in Templates.tsx.

**Runtime Dep Confirmation:** `CapabilityMatrix.runtime_dependencies` (JSON list column) is populated but never surfaced to the user before build. Add a pre-build summary step: before calling `foundry_service.build_template()`, fetch all CapabilityMatrix entries for the selected tools and return a `runtime_deps_summary` in the template detail response. Frontend: show a confirmation modal listing runtime deps; user clicks "Build anyway" or "Review deps".

---

### 6. Operator UX

**Plain-language search on ingredients:** Add `q: Optional[str]` query param to `GET /api/smelter/ingredients`. In the service layer, add `.where(ApprovedIngredient.name.ilike(f"%{q}%"))` if `q` is provided. Same pattern already used for job search.

**Simplified naming / role-based views:** Frontend-only changes in `Templates.tsx`. Viewer role sees read-only tabs; operator/admin see full edit controls. Use existing `useRole()` hook. No backend changes needed.

---

## Revised System Overview

```
Agent Container (FastAPI :8001)
  EE Router Layer              Service Layer
  foundry_router.py            foundry_service.py     — Dockerfile gen + docker build
  smelter_router.py            smelter_service.py     — CVE scan + validate_blueprint
  (new endpoints below)        mirror_service.py      — ecosystem dispatch table (extended)
                               resolver_service.py    — transitive dep resolution (new)
                               script_analyzer_service.py  — import detection (new)

  EE DB Tables (EEBase, created via axiom-ee entry_points)
    approved_ingredients   (extended: +ecosystem column)
    ingredient_dependencies (new)
    blueprints
    puppet_templates
    capability_matrix
    image_boms
    package_index
    approved_os
    artifacts
    curated_bundles   (new)
    curated_bundle_items (new)

  Docker Socket (/var/run/docker.sock)
    Foundry builds — existing pattern
    Dep resolution throwaway containers — new, same pattern
    Mirror backend throwaway containers — new, same pattern

Mirror Sidecar Services (compose.server.yaml)
  pypi          :8080  pypiserver         — PYPI wheels (existing)
  mirror        :8081  Caddy              — APT .deb (existing, extend)
  apk-mirror    :8082  nginx:alpine       — APK packages (new)
  npm-registry  :4873  verdaccio          — npm packages (new)
  nuget-registry:5555  baget              — NuGet packages (new)
  conda-mirror  :8083  nginx:alpine       — Conda packages (new)
  registry      :5000  registry:2         — OCI images (existing)
```

---

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `foundry_service.py` | Dockerfile generation, docker build + push, BOM capture | Existing — extend with multi-ecosystem config injection |
| `smelter_service.py` | CVE scanning (pip-audit), blueprint validation, ingredient CRUD | Existing — extend scan to include `ingredient_dependencies` rows |
| `mirror_service.py` | Download packages per ecosystem to local mirror | Existing — add ecosystem dispatch table + new backend methods |
| `resolver_service.py` | Spawn throwaway container to resolve full dep tree | New |
| `script_analyzer_service.py` | Static AST/regex analysis of job scripts | New |
| `ingredient_dependencies` table | Resolved transitive dependency graph per ingredient | New |
| `curated_bundles` / `curated_bundle_items` tables | Named package groups with seeded starters | New |
| New sidecar services | Serve APK/npm/NuGet/Conda packages over HTTP | New compose services |

---

## Data Flow Changes

### Transitive Resolution Flow

```
POST /api/smelter/ingredients
  SmelterService.add_ingredient()
    INSERT approved_ingredients (mirror_status=PENDING)
    asyncio.create_task(MirrorService.mirror_ingredient(id))
                        [after mirror completes]
    asyncio.create_task(ResolverService.resolve_transitive(id, ecosystem))
      docker run --rm --network puppeteer_default <ecosystem-image> <resolve-cmd>
      parse stdout -> dep list
      INSERT ingredient_dependencies rows
      for each new dep:
        asyncio.create_task(MirrorService.mirror_ingredient for dep)
      asyncio.create_task(SmelterService.scan_vulnerabilities)
```

### Multi-Ecosystem Mirror Dispatch Flow

```
MirrorService.mirror_ingredient(ingredient_id)
  fetch ApprovedIngredient
  handler = ECOSYSTEM_HANDLERS[ingredient.ecosystem]
  await handler(db, ingredient)
    PYPI   -> pip download --no-deps (existing)  [NOTE: resolver handles full tree separately]
    APT    -> docker run debian:12-slim apt-get download <pkg> + copy .deb + regenerate Packages.gz
    APK    -> docker run alpine:3.20 apk fetch <pkg> + copy .apk + run apk index
    NPM    -> docker run node:20-slim npm pack <pkg> + push to verdaccio
    CONDA  -> docker run continuumio/miniconda3 conda download <pkg> + copy + conda index
    NUGET  -> docker run dotnet/sdk:8.0 nuget download + push to baget
    OCI    -> docker pull <image_uri> + docker push localhost:5000/<name>
  update mirror_status in DB
```

### Script Analysis Flow

```
POST /api/smelter/analyze-script
  ScriptAnalyzerService.analyze(script, runtime)  [synchronous, ~10ms]
    if python: ast.parse + walk Import/ImportFrom nodes
    if bash/ps: regex scan for install commands
    normalize to package names via static mapping
    DB query: SELECT approved_ingredients WHERE name ILIKE ANY(detected)
    DB query: SELECT curated_bundle_items WHERE ingredient_name ANY(detected)
    return ScriptAnalysisResult
  (response returned immediately — no background task)
```

---

## Build Order (Phase Dependencies)

```
Phase 1: DB schema additions
  - ecosystem column on approved_ingredients (migration SQL)
  - ingredient_dependencies table (EEBase create_all)
  - curated_bundles + curated_bundle_items tables (EEBase create_all)
  BLOCKS: all subsequent phases

Phase 2: resolver_service.py + ecosystem dispatch in mirror_service.py
  - Core new pipeline components
  - Requires Phase 1 (IngredientDependency table, ecosystem field)

Phase 3: APT + APK mirror backends
  - Highest operator value (most common air-gap scenario)
  - Implement _mirror_apt() and _mirror_apk() throwaway containers
  - Add apk-mirror sidecar to compose.server.yaml
  REQUIRES: Phase 1 (ecosystem field), Phase 2 (dispatch table)

Phase 4: npm + NuGet + Conda mirror backends
  - Same pattern as Phase 3
  - Add verdaccio, baget, conda-mirror sidecars to compose.server.yaml
  REQUIRES: Phase 1, Phase 2 (parallel with Phase 3)

Phase 5: Extend CVE scan to transitive deps
  - Add second DB query in scan_vulnerabilities() for ingredient_dependencies
  REQUIRES: Phase 2 (IngredientDependency rows need to exist)

Phase 6: script_analyzer_service.py + endpoint
  - Self-contained static analysis service
  - Requires Phase 1 only (to query approved_ingredients)

Phase 7: Curated bundles CRUD + seeded starter packs
  - CRUD endpoints on CuratedBundle/CuratedBundleItem
  - Seed in EE plugin startup hook
  REQUIRES: Phase 1 (tables)

Phase 8: Frontend changes
  - Dep tree viewer component
  - Script analyzer UI in dispatch form
  - Bundle picker in blueprint editor
  - Approved OS management tab
  REQUIRES: Phases 3-7 (backend endpoints)

Phase 9: EE CRUD completeness (Edit Blueprint, Edit Tool Recipe, Approved OS routes)
  - Standalone backend work, no new tables
  - Can run in parallel with Phases 2-7

Phase 10: Operator UX polish (search, naming, role-based views)
  - Mostly frontend / query param changes
  - Last, no blocking dependencies
```

**Recommended phase sequence based on risk and value:**

| Phase | Work | Rationale |
|-------|------|-----------|
| 1 | DB migrations | Unblocks everything |
| 2 | resolver_service + mirror dispatch table | Core pipeline change |
| 9 | EE CRUD completeness | High operator value, no new deps, parallelizable |
| 3 | APT + APK backends + compose sidecars | Highest air-gap value |
| 5 | CVE scan transitive extension | Correctness — transitive deps were invisible |
| 6 | script_analyzer_service + endpoint | Operator UX, self-contained |
| 7 | Curated bundles + seeding | Operator UX |
| 4 | npm + NuGet + Conda backends | Extended ecosystem coverage |
| 8 | Frontend changes | Depends on all backend phases |
| 10 | Search + naming + role views | Polish |

---

## Architectural Patterns

### Pattern 1: Throwaway Container for Ecosystem Tools

**What:** Spin up a short-lived Docker container with the target ecosystem toolchain. Run one command. Capture stdout. Destroy container. Use `--rm` flag.

**When to use:** Any operation that requires ecosystem-native tooling (pip, npm, apt, conda, dotnet) and must not pollute the agent process.

**Trade-offs:** Docker socket latency (~1-3 seconds per container start) is acceptable for background tasks. Never use for synchronous request handling. Always wrap in `asyncio.create_task()`.

**Example:**
```python
proc = await asyncio.create_subprocess_exec(
    "docker", "run", "--rm",
    "--network", "puppeteer_default",    # reach pypi/npm/apt sidecars
    "-e", f"PIP_INDEX_URL={pypi_url}",
    "--memory", "512m",                  # resource bound the throwaway
    "python:3.12-slim",
    "sh", "-c", f"pip download --dry-run {pkg_name} 2>&1",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
)
stdout, _ = await proc.communicate()
```

### Pattern 2: Ecosystem Field on ApprovedIngredient

**What:** Add explicit `ecosystem` column (PYPI, APT, APK, NPM, CONDA, NUGET, OCI) to `ApprovedIngredient`. Current `os_family` remains for OS-scoped approval logic (a package may be approved for DEBIAN but not ALPINE). The two fields are orthogonal.

**Migration:** `ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI'` — safe, all existing rows correctly default to PYPI.

**When to use:** Any new `ApprovedIngredientCreate` request includes `ecosystem`. Existing API clients that omit it default to PYPI (backward compatible).

### Pattern 3: Config Table for Mirror URLs

**What:** All mirror sidecar URLs stored in the `Config` key/value table (existing pattern). `MirrorService.get_*_conf_content()` methods read from Config/env. New keys follow the `*_MIRROR_URL` naming convention already established.

**When to use:** Adding a new mirror ecosystem means adding a new `Config` key, extending `GET /api/admin/mirror-config`, and adding a `get_<ecosystem>_conf_content()` method. No new table.

### Pattern 4: Semaphore on Throwaway Container Spawning

**What:** `asyncio.Semaphore` limits concurrent throwaway containers to prevent Docker socket saturation.

**When to use:** Apply to both `resolver_service` and the new mirror backends. Use separate semaphores per concern:
- `FoundryService._build_semaphore = asyncio.Semaphore(2)` (existing)
- `ResolverService._resolve_semaphore = asyncio.Semaphore(3)` (new)
- `MirrorService._mirror_semaphore = asyncio.Semaphore(5)` (new)

---

## Anti-Patterns

### Anti-Pattern 1: In-Process pip/npm/apt Execution

**What people do:** Run `subprocess.run(["pip", "download", ...])` directly in the agent container process.

**Why it's wrong:** Pollutes the agent's Python environment. Cannot use different Python versions per target ecosystem. In multi-user concurrent scenarios, package resolution can corrupt the agent's pip cache.

**Do this instead:** Throwaway container per ecosystem using the Docker socket.

### Anti-Pattern 2: Synchronous Transitive Resolution

**What people do:** Block `POST /api/smelter/ingredients` until all transitive deps are resolved and mirrored.

**Why it's wrong:** Resolution can take 30-120 seconds for large trees (numpy alone has ~20 transitive deps). HTTP clients time out. The operator gets no feedback.

**Do this instead:** Return `ApprovedIngredient` immediately with `mirror_status="PENDING"`. Fire `asyncio.create_task()` for resolution. Poll `GET /api/smelter/ingredients/{id}` or use WebSocket for status updates.

### Anti-Pattern 3: Separate Table per Ecosystem

**What people do:** Create `apt_packages`, `npm_packages`, `conda_packages` tables.

**Why it's wrong:** Identical schema. Duplicated CRUD. Duplicated CVE scan pipeline. Breaks the unified Smelter approval workflow.

**Do this instead:** `ecosystem` column on `ApprovedIngredient`. Single table, single approval workflow, single CVE scan. Dispatch to ecosystem-specific mirror handler at runtime.

### Anti-Pattern 4: Script Analyzer as External Service

**What people do:** Deploy a separate microservice for script analysis to "keep services small."

**Why it's wrong:** Static AST/regex analysis is CPU-bound with no I/O. It takes <10ms. Adding a network hop, deployment unit, and failure mode for a 10ms operation is over-engineering.

**Do this instead:** In-process service function in `script_analyzer_service.py`. Returns synchronously in the API response.

### Anti-Pattern 5: Removing --no-deps from Existing PyPI Mirror

**What people do:** Remove `--no-deps` from `_mirror_pypi()` to mirror transitive deps inline.

**Why it's wrong:** Conflates mirroring (put file on disk) with approval (operator review + CVE scan). Transitive deps downloaded without approval bypass the Smelter registry's security model — the whole point of which is that every package is explicitly reviewed.

**Do this instead:** Keep `--no-deps` in `_mirror_pypi()`. Use `resolver_service.py` to identify transitive deps, INSERT them as `IngredientDependency` rows with `auto_approved=False` (flagged for review), and surface them in the UI for operator confirmation before they are mirrored.

---

## DB Schema Changes Summary

| Table | Change | Where | Migration |
|-------|--------|-------|-----------|
| `approved_ingredients` | Add `ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI'` | `ee/smelter/models.py` | ALTER TABLE (new migration SQL file) |
| `ingredient_dependencies` | New table | `ee/smelter/models.py` | EEBase create_all (new table) |
| `curated_bundles` | New table | `ee/smelter/models.py` | EEBase create_all (new table) |
| `curated_bundle_items` | New table | `ee/smelter/models.py` | EEBase create_all (new table) |

All new tables use `EEBase` — they are created by the EE plugin's `create_all` call on startup. No manual migration needed for fresh EE installs. For existing EE deployments: `ingredient_dependencies`, `curated_bundles`, and `curated_bundle_items` are new (created automatically); only `approved_ingredients.ecosystem` requires an ALTER TABLE.

Migration file: `migration_v4X.sql`:
```sql
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI';
```

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `resolver_service` -> Docker | `asyncio.create_subprocess_exec` via /var/run/docker.sock | Same socket path as Foundry builds |
| `resolver_service` -> `mirror_service` | Direct async function call | `asyncio.create_task()` per resolved dep |
| `resolver_service` -> `smelter_service` | Direct async function call | Trigger CVE scan after resolution |
| `script_analyzer` -> `approved_ingredients` | SQLAlchemy query via `AsyncSession` | Read-only; needs `foundry:read` permission |
| `script_analyzer` -> `curated_bundle_items` | SQLAlchemy query via `AsyncSession` | For bundle suggestions |
| `foundry_service` -> `mirror_service` | Reads `get_*_conf_content()` methods | Extended for new ecosystems |
| EE `plugin.py` startup -> `curated_bundles` | INSERT with `ON CONFLICT DO NOTHING` | Same pattern as permission seeding |
| New mirror backends -> resolver throwaway | Independent — both use Docker socket | No direct coupling |

### External Boundaries (new sidecars)

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| verdaccio (npm) | `npm publish --registry http://npm-registry:4873` inside throwaway | verdaccio supports anonymous publish by default; configure `access: "$anonymous"` in config |
| baget (NuGet) | `nuget push -source http://nuget-registry:5555/v3/index.json` inside throwaway | baget requires an API key; set `BAGET_API_KEY` env var |
| nginx:alpine (APK) | Serve `/app/mirror_data/apk/` with `apk index` regenerated after each package | Needs `apk-tools` available in throwaway |
| nginx:alpine (Conda) | Serve `/app/mirror_data/conda/` as static channel | `conda index` regenerates `repodata.json`; run in miniconda throwaway after download |
| Caddy (APT, existing) | Serve `/app/mirror_data/apt/` via existing Caddyfile | Extend Caddyfile to also run `dpkg-scanpackages` if Caddy exec plugin available; or use a pre-generate step |

---

## Sources

- Direct inspection: `puppeteer/agent_service/services/foundry_service.py`
- Direct inspection: `puppeteer/agent_service/services/mirror_service.py` (--no-deps confirmed, APT stub confirmed)
- Direct inspection: `puppeteer/agent_service/services/smelter_service.py` (pip-audit flat scan confirmed)
- Direct inspection: `puppeteer/agent_service/ee/routers/foundry_router.py` + `smelter_router.py`
- Direct inspection: `axiom-ee/ee/foundry/models.py` (Blueprint, PuppetTemplate, CapabilityMatrix, ApprovedOS schema)
- Direct inspection: `axiom-ee/ee/smelter/models.py` (ApprovedIngredient schema — no ecosystem field confirmed)
- Direct inspection: `puppeteer/compose.server.yaml` (existing pypi, devpi, mirror, registry sidecars)
- Project context: `.planning/PROJECT.md` (v19.0 milestone goals and existing decisions)

---

*Architecture research for: Axiom v19.0 Foundry Improvements*
*Researched: 2026-04-01*

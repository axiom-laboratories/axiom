# Stack Research

**Domain:** Foundry Improvements — transitive dependency resolution, multi-ecosystem mirrors, script analysis, operator UX
**Researched:** 2026-04-01
**Confidence:** HIGH (backend), MEDIUM (mirror sidecars)

---

## Context: Scope of This Milestone

This research covers only NEW capabilities required for v19.0 Foundry Improvements. The existing stack (FastAPI, SQLAlchemy async, asyncpg, APScheduler 3.x, React 19 / Radix UI / Tailwind / Recharts) is validated and not re-researched.

Four capability clusters need new stack decisions:

1. **Transitive dependency resolution** — walk the full dep tree for a Python package list and download/scan all transitive deps
2. **Multi-ecosystem mirror backends** — APT, apk, npm (Verdaccio), Conda (conda-mirror), NuGet (BaGet/BaGetter), OCI pull-through (registry:2)
3. **Script analyzer** — static analysis of uploaded Python/Bash scripts to infer required packages and flag risky constructs
4. **Operator UX** — tree viewer for dep graphs, simplified naming, curated bundles, plain-language search (frontend additions)

---

## Recommended Stack

### Backend: Transitive Dependency Resolution

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `pip` (subprocess) | >=26.0 (already present) | Resolve and download full dep tree for Python packages | `pip download <pkg>` without `--no-deps` walks the full transitive tree; already in base image. Avoids a separate resolver library. |
| `pip-tools` (`pip-compile`) | `>=7.4,<8` | Pre-resolve a `.in` requirements list into a pinned flat `requirements.txt` including all transitive deps | Produces a deterministic locked file that can then be fed to `pip download --no-deps` for precise mirroring. Has stable CLI; invoke via subprocess. |
| PyPI JSON API (HTTP, no lib) | REST — `https://pypi.org/pypi/{pkg}/json` | Fetch package metadata (requires_dist) without installing | Zero-dependency approach for building dep trees server-side: `httpx` (already in requirements) fetches metadata; parse `requires_dist` with `packaging.requirements.Requirement` |
| `packaging` | >=24.0 (already in requirements) | Parse PEP 508 requirement strings (`requires_dist`) and version specifiers | Already present; `packaging.requirements.Requirement` parses `"requests>=2.0; python_version>='3.8'"` correctly, including extras and markers |
| `pip-audit` | >=2.7 (already in requirements) | CVE scan the resolved transitive set | Already in requirements; pass the full resolved `requirements.txt` as input — it scans all packages including transitives |

**Recommended resolution flow for `mirror_ingredient` (replacing `--no-deps` pattern):**

```
1. Build requirements.in from ingredient list (name + version constraint)
2. subprocess: pip-compile requirements.in → requirements.txt (pinned, includes transitives)
3. subprocess: pip download --no-deps -r requirements.txt --dest <mirror_dir>
4. subprocess: pip-audit -r requirements.txt --format json → structured CVE results
5. Store resolved package list (with versions) as JSON in DB for tree UI
```

This three-step pipeline is deterministic, air-gap compatible (once packages are downloaded), and produces an explicit manifest of every package in the mirror.

**Alternative: PyPI JSON API recursive walker (no subprocess)**

For building a dep-tree JSON to display in the UI (not for downloading), walk the tree purely via HTTP:

```python
async def resolve_tree(pkg: str, version: str) -> dict:
    url = f"https://pypi.org/pypi/{pkg}/{version}/json"
    resp = await http_client.get(url)
    info = resp.json()["info"]
    requires = info.get("requires_dist") or []
    # parse each with packaging.requirements.Requirement, filter by markers
    # recurse for each dependency
```

This is suitable for the UI tree viewer (read-only, no download). Use `pip-compile` for the authoritative resolution used during mirroring.

---

### Backend: Script Analyzer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `ast` (Python stdlib) | stdlib — no install | Parse Python scripts into AST; walk `Import` and `ImportFrom` nodes to extract `import X` and `from X import Y` statements | Zero-dependency, no subprocess; built into every Python version. Handles syntax errors gracefully with `ast.parse(source, mode='exec')` in a try/except. |
| `bandit` | `>=1.8,<2` | Security scan Python scripts; detect `subprocess.call(shell=True)`, hardcoded credentials, pickle use, etc. | Provides a programmatic API: instantiate `BanditNodeVisitor` or invoke via subprocess with `--format json`. Already proven pattern in CI/CD contexts. |
| `packaging.requirements` | already in requirements | Map extracted import names to PyPI package names | `import requests` → `requests`; handles most cases. Stdlib detection via `sys.stdlib_module_names` (Python 3.10+) to filter out builtins. |

**What stdlib AST gives for free (no new deps):**

```python
import ast

def extract_imports(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return list(set(imports))
```

**Bandit integration (subprocess JSON):**

```bash
bandit -r script.py -f json -q
```

Returns structured JSON with `results[].issue_severity` (LOW/MEDIUM/HIGH), `issue_confidence`, `issue_text`, and `line_number`. Parse in Python and store results in DB.

**Bash/PowerShell script analysis:**

No mature stdlib equivalent for Bash AST parsing. For Bash: use regex patterns to detect `pip install`, `apt-get install`, `apk add`, `npm install` commands — sufficient for the "detect required packages" use case. For PowerShell: similar pattern matching for `Install-Package`, `pip install`. Do not attempt full shell AST parsing — it is not worth the complexity for this use case.

---

### Mirror Sidecars: New Services

#### npm Mirror — Verdaccio

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `verdaccio/verdaccio` Docker image | `6` (latest stable) | npm private proxy/caching registry | Zero-config pull-through proxy; packages cached on first download; air-gap compatible; `verdaccio:6` requires Node.js 18+; official Docker image on Docker Hub |

**Compose service pattern:**

```yaml
verdaccio:
  image: verdaccio/verdaccio:6
  restart: unless-stopped
  ports:
    - "4873:4873"
  volumes:
    - verdaccio-data:/verdaccio/storage
    - ./verdaccio/config.yaml:/verdaccio/conf/config.yaml:ro
```

**Minimal `config.yaml` for pull-through proxy:**

```yaml
storage: /verdaccio/storage
uplinks:
  npmjs:
    url: https://registry.npmjs.org/
packages:
  '@*/*':
    access: $all
    proxy: npmjs
  '**':
    access: $all
    proxy: npmjs
```

Node clients point `npm config set registry http://verdaccio:4873` in the Foundry-generated Dockerfile.

#### Conda Mirror — conda-mirror

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `conda-mirror` | `0.10.0` (latest on PyPI) | Mirror a conda channel (e.g. `conda-forge/linux-64`) to a local directory served via nginx/Caddy | Pure Python, no Anaconda Enterprise required; mirrors channel index + selected packages; existing Caddy `mirror` service can serve the mirrored directory. Install in agent container or a dedicated sidecar. |
| Caddy (existing `mirror` service) | already in compose | Serve mirrored conda channel via HTTP | Existing `mirror` service already serves a volume; add a new location block for conda path |

**conda-mirror invocation pattern (subprocess from mirror_service.py):**

```bash
conda-mirror \
  --upstream-channel conda-forge \
  --target-directory /app/mirror_data/conda/conda-forge \
  --platform linux-64 \
  --num-threads 4
```

Generates `channeldata.json`, `repodata.json`, and `.conda`/`.tar.bz2` files in the standard conda channel layout. Clients set `channels: [http://mirror/conda/conda-forge]` in their `.condarc`.

**Limitation:** `conda-mirror 0.10.0` was last released in 2022. It remains functional but is not actively maintained. Monitor for `conda-mirror-ng` (more recent fork on PyPI) as an alternative.

#### NuGet Mirror — BaGetter

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `bagetter/BaGetter` Docker image | `latest` (BaGetter fork, not original BaGet) | NuGet + symbol server with pull-through caching | BaGetter is the actively maintained community fork of the original BaGet; supports read-through caching from nuget.org; SQLite backend works out of the box; ARM64 support |

**Compose service pattern:**

```yaml
nuget:
  image: ghcr.io/bagetter/bagetter:latest
  restart: unless-stopped
  ports:
    - "5555:8080"
  volumes:
    - nuget-data:/var/baget
  environment:
    - ApiKey=${NUGET_API_KEY:-changeme}
    - Storage__Type=FileSystem
    - Storage__Path=/var/baget/packages
    - Database__Type=Sqlite
    - Database__ConnectionString=Data Source=/var/baget/baget.db
    - Mirror__Enabled=true
    - Mirror__PackageSource=https://api.nuget.org/v3/index.json
```

PowerShell scripts use `Register-PSRepository -Name Axiom -SourceLocation http://nuget:5555/v3/index.json`.

#### APT Mirror — apt-cacher-ng (existing, complete the placeholder)

The existing `_mirror_apt()` placeholder in `mirror_service.py` should be completed. The existing Caddy `mirror` service already serves `/data/apt`. The correct implementation for air-gapped APT mirroring is:

**Option A: apt-get download (single package, no sidecar):**

```bash
apt-get download <package>  # downloads .deb to current dir
dpkg-scanpackages . > Packages  # generates index
gzip -k Packages  # creates Packages.gz
```

This is the "upload a specific .deb" approach — analogous to the existing air-gap PyPI upload flow. Use this for the `_mirror_apt()` implementation.

**Option B: apt-mirror sidecar (full channel mirror):**

```yaml
apt-mirror:
  image: ghcr.io/inhumantsar/docker-apt-mirror:latest
  volumes:
    - mirror-data:/apt-mirror/mirror
    - ./apt-mirror.list:/etc/apt/mirror.list:ro
```

Option A (apt-get download + dpkg-scanpackages) is recommended for the current milestone because it mirrors the existing air-gap upload pattern and adds no new sidecar. Option B is appropriate if full automated channel mirroring is required.

**apt-cacher-ng** (already referenced in docs) is a caching proxy, not a full mirror — it requires internet access to the upstream Debian/Ubuntu repos. Use Option A or B for true air-gap support.

#### apk Mirror — Nginx + rsync

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `alpine` base + rsync | latest Alpine | Sync Alpine package repo via rsync; serve via nginx | Standard Alpine mirror setup; Alpine packages are static files (`.apk` + `APKINDEX.tar.gz`); rsync pull from `rsync://dl-cdn.alpinelinux.org/alpine/`; nginx serves them |

**Compose service pattern:**

```yaml
apk-mirror:
  image: nginx:alpine
  restart: unless-stopped
  volumes:
    - apk-data:/usr/share/nginx/html/alpine:ro
  ports:
    - "8082:80"

apk-syncer:
  image: alpine:latest
  restart: unless-stopped
  volumes:
    - apk-data:/mirror/alpine
  command: |
    sh -c "while true; do
      rsync -avz --delete rsync://dl-cdn.alpinelinux.org/alpine/v3.21/ /mirror/alpine/v3.21/
      sleep 3600
    done"
```

Alpine clients set `https_proxy` or edit `/etc/apk/repositories` to point to `http://apk-mirror/alpine/v3.21`.

**`_mirror_apk()` implementation in mirror_service.py:**

Like `_mirror_apt`, use `apk fetch --no-cache -R <package>` to download a specific `.apk` and its deps to a local directory, then serve via existing Caddy. No full channel sync required for the air-gap upload pattern.

#### OCI Mirror — registry:2 (already present, use pull-through mode)

The existing `registry:2` service in `compose.server.yaml` is already deployed for Foundry-built images. For OCI pull-through caching, configure it with `REGISTRY_PROXY_*` env vars:

```yaml
registry:
  image: registry:2
  environment:
    REGISTRY_PROXY_REMOTEURL: https://registry-1.docker.io
    REGISTRY_PROXY_USERNAME: ${DOCKER_HUB_USER:-}
    REGISTRY_PROXY_PASSWORD: ${DOCKER_HUB_PASSWORD:-}
  volumes:
    - registry-data:/var/lib/registry
```

When `REGISTRY_PROXY_REMOTEURL` is set, registry:2 acts as a pull-through cache. Docker daemons on nodes point their `registry-mirrors` config to `http://registry:5000`. This is the CNCF-standard approach for air-gapped OCI — no new service required.

**Limitation:** registry:2 in proxy mode cannot serve images it has never pulled (cold start). Seed the cache by pulling required base images once before air-gapping.

---

### Frontend: Dependency Tree Viewer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `react-d3-tree` | `3.6.6` | Interactive collapsible dep tree visualization | 253K weekly downloads; MIT license; renders hierarchical JSON as an SVG tree with expand/collapse; fits the dep tree shape (root → transitive nodes) naturally |
| Radix UI `Collapsible` + shadcn tree pattern | already in `package.json` | Alternative for simple package lists (flat parent → children) | If the dep tree is shallow (2-3 levels), a pure-CSS shadcn `Collapsible` tree avoids the `react-d3-tree` SVG overhead. Use `react-d3-tree` only for deep transitive trees. |

**Decision rule:**
- Dep tree viewer for displaying transitive resolution results: use `react-d3-tree` (handles arbitrary depth gracefully).
- Blueprint/ingredient list with simple expansion: use existing Radix `Collapsible` (no new dep).

**react-d3-tree data shape:**

```typescript
interface RawNodeDatum {
  name: string;
  attributes?: Record<string, string | number | boolean>;
  children?: RawNodeDatum[];
}
// e.g. { name: "flask==3.0.2", children: [{ name: "werkzeug==3.0.1" }, ...] }
```

Backend endpoint provides this shape; frontend passes it directly to `<Tree data={tree} />`.

---

### Frontend: No New UI Libraries Required for Other Features

| Feature | Implementation | Libraries |
|---------|----------------|-----------|
| Edit Blueprint / Edit Tool Recipe | Extend existing modal pattern (Radix Dialog + form) | Already in stack |
| Approved OS Management | CRUD table (existing pattern from Users/Signatures views) | Already in stack |
| Runtime Dep Confirmation | Confirmation dialog with package list (Radix AlertDialog) | Already in stack |
| Curated Bundles | Accordion/card list with one-click add; uses existing Radix Collapsible | Already in stack |
| Plain-language search | Fuse.js or simple substring filter on ingredient catalog | Fuse.js is optional (client-side fuzzy search); stdlib string filter is sufficient for MVP |
| Simplified naming | Frontend-only rename mapping (display labels) | No new lib |

---

## Installation

### Backend additions

```bash
# In puppeteer/requirements.txt — add:
pip-tools>=7.4,<8
bandit>=1.8,<2

# Already present (no changes needed):
# packaging, pip-audit, httpx
```

### Frontend addition

```bash
cd puppeteer/dashboard
npm install react-d3-tree@3.6.6
```

All other frontend changes use existing Radix UI, Tailwind, and shadcn patterns already in `package.json`.

### New Docker Compose services

Add to `compose.server.yaml` (optional per deployment, controlled by `MIRROR_BACKENDS` config):

```yaml
# npm mirror
verdaccio:
  image: verdaccio/verdaccio:6
  volumes: [verdaccio-data:/verdaccio/storage, ./verdaccio/config.yaml:/verdaccio/conf/config.yaml:ro]
  ports: ["4873:4873"]

# NuGet mirror
nuget:
  image: ghcr.io/bagetter/bagetter:latest
  volumes: [nuget-data:/var/baget]
  ports: ["5555:8080"]
  environment: [ApiKey=${NUGET_API_KEY:-changeme}, Mirror__Enabled=true, ...]

# Alpine apk mirror (nginx serves, alpine syncer pulls)
apk-mirror:
  image: nginx:alpine
  volumes: [apk-data:/usr/share/nginx/html/alpine:ro]
  ports: ["8082:80"]

# New volumes
volumes:
  verdaccio-data:
  nuget-data:
  apk-data:
  conda-data:
```

`conda-mirror` runs as a Python subprocess inside the agent container (already has Python), not as a separate sidecar. No new image required.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `pip-tools` (pip-compile subprocess) | `resolvelib` directly | Only if a pure-Python in-process resolver is needed; resolvelib is what pip uses internally but has no stable public API — subprocess pip-compile is simpler and more reliable |
| `pip-tools` | `uv` (Rust) | uv is faster but has no stable Python API for programmatic dep-tree extraction; use uv if replacing the entire build pipeline in a future milestone |
| `ast` stdlib | `libcst` (concrete syntax tree) | libcst preserves formatting and supports source rewriting; overkill for import detection only — stdlib ast is sufficient |
| `bandit` subprocess | `semgrep` | semgrep supports multi-language (Bash, Python, PS) with one tool; heavier dependency and licensing concerns for self-hosted; bandit is lighter and PyPI-native |
| `react-d3-tree` | `@xyflow/react` (React Flow) | React Flow is better for graph editors (drag/drop nodes); for read-only tree display, react-d3-tree is simpler and lighter |
| BaGetter (`bagetter` fork) | original `loicsharma/baget` | Original BaGet is effectively unmaintained since 2021; BaGetter is the active community continuation with same API surface |
| `verdaccio:6` | Nexus Repository / Artifactory | Enterprise features (auth, multi-format); massively heavier operationally; Verdaccio is sufficient for npm proxy in homelab/enterprise internal deployment |
| `registry:2` pull-through mode | Harbor | Harbor adds project-based access control and vulnerability scanning; registry:2 is sufficient for basic OCI mirror; add Harbor only if image ACLs are required |
| apt-get download + dpkg-scanpackages | apt-mirror sidecar | Full channel mirror for large Debian repos; apt-get download approach is sufficient for curated ingredient lists |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pip download --no-deps` for mirroring | Only downloads the declared package, not its transitive deps — the current bug this milestone fixes | `pip-compile` to resolve, then `pip download --no-deps -r resolved.txt` |
| `pipdeptree` for resolution | pipdeptree analyzes installed packages in a live environment — requires installing first; not suitable for pre-download resolution | PyPI JSON API walker for tree display; `pip-compile` for authoritative resolution |
| `uv` Python bindings | No stable public API for programmatic dep resolution; CLI-only in 2025 | subprocess `pip-compile` or PyPI JSON API |
| `conda` full Anaconda distribution | 1.5 GB Docker image; licence complexity | `conda-mirror` (PyPI package, runs in existing agent container) + Caddy to serve |
| `loicsharma/baget` Docker image | Effectively unmaintained since 2021; no recent Docker image pushes | `ghcr.io/bagetter/bagetter:latest` (active fork) |
| `apt-cacher-ng` for air-gap APT | apt-cacher-ng is a caching proxy — requires internet access at cache-fill time; not air-gap compatible | `apt-get download` + `dpkg-scanpackages` for true air-gap |
| `libcst` or `parso` for script analysis | Heavy parser dependencies for a use case (import detection) that stdlib `ast` handles completely | Python `ast` stdlib; regex for Bash/PowerShell |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `pip-tools>=7.4,<8` | Python 3.8+, pip>=22 | pip-tools 7.x is stable; pin `<8` to avoid API changes |
| `bandit>=1.8,<2` | Python 3.8+, `ast` stdlib | bandit 1.8 added Python 3.12 AST compat; 2.0 would be a new major — pin `<2` |
| `react-d3-tree@3.6.6` | React 16.8+, d3 | React 19 compatible (hooks only, no deprecated APIs used); requires `d3` peer dep — bundled in the react-d3-tree package |
| `verdaccio:6` | Node.js 18+, npm 7+ | Node.js 18 is LTS; verdaccio:6 is the current stable tag |
| `ghcr.io/bagetter/bagetter:latest` | .NET 8, SQLite or SQL Server | Default SQLite backend requires no external DB; .NET 8 is baked into image |

---

## Integration Points

| New Capability | Where It Hooks In |
|----------------|-------------------|
| `pip-compile` transitive resolution | `mirror_service.py`: replace `_mirror_pypi()` body; write resolved `requirements.txt` to temp dir; call `pip download --no-deps -r` on it |
| `pip-audit` on full resolved set | `smelter_service.py` / `mirror_service.py`: pass resolved `requirements.txt` to `pip-audit --format json`; parse results; store per-ingredient CVE list |
| `ast` import extractor | New `script_analyzer_service.py`; called from `POST /api/smelter/analyze-script`; returns detected packages list for Foundry wizard pre-population |
| `bandit` security scan | Same `script_analyzer_service.py`; returns severity findings list; displayed as warnings in Foundry script upload UI |
| Verdaccio | `mirror_service.py`: `_mirror_npm()` invokes `npm pack <pkg>` then pushes to Verdaccio via its REST API, or configure Verdaccio as pull-through and skip explicit push |
| BaGetter | `mirror_service.py`: `_mirror_nuget()` invokes `nuget push` or `dotnet nuget push` to BaGetter REST endpoint |
| conda-mirror | `mirror_service.py`: `_mirror_conda()` invokes `conda-mirror` via subprocess with target channel and platform args |
| `react-d3-tree` | New `DepTreeModal.tsx` component; rendered from ingredient detail panel when `transitive_deps` JSON field is present; receives tree-shaped JSON from `GET /api/smelter/ingredients/{id}/dep-tree` |

---

## Sources

- [pip dependency resolution docs](https://pip.pypa.io/en/stable/topics/dependency-resolution/) — `pip download` transitive behavior, `--no-deps` semantics — HIGH confidence (official pip docs)
- [pip-tools GitHub](https://github.com/jazzband/pip-tools) — pip-compile resolves transitive deps into pinned requirements.txt — HIGH confidence
- [PyPI JSON API](https://docs.pypi.org/api/json/) — `requires_dist` field, package metadata endpoint — HIGH confidence (official PyPI docs)
- [packaging library docs](https://packaging.pypa.io/en/stable/) — `packaging.requirements.Requirement` — HIGH confidence
- [pip-audit PyPI / GitHub](https://github.com/pypa/pip-audit) — scans requirements files for known CVEs, JSON output — HIGH confidence
- [Python `ast` stdlib](https://docs.python.org/3/library/ast.html) — `Import`, `ImportFrom` nodes, `ast.walk()` — HIGH confidence (stdlib)
- [Bandit GitHub (PyCQA)](https://github.com/PyCQA/bandit) — 1.8.x stable, programmatic + subprocess JSON mode — HIGH confidence
- [react-d3-tree npm](https://www.npmjs.com/package/react-d3-tree) — v3.6.6, 253K weekly downloads, collapsible tree — HIGH confidence
- [Verdaccio Docker Hub](https://hub.docker.com/r/verdaccio/verdaccio/) — `verdaccio:6` tag, Node 18+ requirement — HIGH confidence
- [BaGetter GitHub](https://github.com/bagetter/BaGetter) — active fork of BaGet, ghcr.io image, SQLite + mirror enabled — MEDIUM confidence (GitHub, not official docs page)
- [conda-mirror PyPI](https://pypi.org/project/conda-mirror/) — v0.10.0 latest, conda-forge channels — MEDIUM confidence (package last updated 2022, still functional)
- [Alpine mirror setup (community)](https://github.com/m3talstorm/docker-alpine-mirror) — rsync + nginx pattern for apk mirrors — MEDIUM confidence (community project)
- [Docker registry:2 pull-through config](https://distribution.github.io/distribution/recipes/mirror/) — REGISTRY_PROXY_REMOTEURL env var — HIGH confidence (official distribution docs)
- [shadcn-tree-view GitHub](https://github.com/MrLightful/shadcn-tree-view) — Radix Collapsible-based tree for simple hierarchies — MEDIUM confidence

---

*Stack research for: v19.0 Foundry Improvements — transitive deps, multi-ecosystem mirrors, script analysis, operator UX*
*Researched: 2026-04-01*

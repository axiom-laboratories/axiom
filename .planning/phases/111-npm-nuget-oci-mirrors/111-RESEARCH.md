# Phase 111: npm + NuGet + OCI Mirrors - Research

**Researched:** 2026-04-04
**Domain:** Package mirror ecosystems (npm, NuGet, OCI), compose orchestration, Dockerfile config injection
**Confidence:** HIGH

## Summary

Phase 111 implements three new mirror ecosystems for air-gapped Foundry builds: npm via Verdaccio pull-through proxy, NuGet via BaGetter with mirroring, and OCI base images via registry:2 pull-through caches. All three use established container-based approaches with Docker-native sidecar services deployed via compose.ee.yaml (following Phase 109's EE overlay pattern).

Key architectural decisions establish patterns for scalable ecosystem expansion: top-level package approval only (transitive resolution deferred), ecosystem-based config injection in Foundry (`.npmrc` and `nuget.config` only when needed), transparent OCI caching via upstream URL rewriting, and strict fail-fast validation in builds. Implementation reuses all existing mirror infrastructure from Phases 108-109: async subprocess patterns, throwaway containers, mirror lifecycle, and health checking.

**Primary recommendation:** Implement in two sequential plans: 111-01 handles npm/Verdaccio backend + Smelter integration, 111-02 handles NuGet/BaGetter + OCI caching + Foundry rewrites. Parallel mirror service startup in compose requires only configuration changes, not complex coordination logic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Smelter integration (npm/NuGet):**
- Operator must explicitly approve npm/NuGet packages before use — consistent with existing PyPI/APT/APK flow
- On approval, system downloads package tarball to local storage (throwaway containers for `npm pack`, `nuget install`)
- Same mirror_status lifecycle: PENDING → MIRRORING → MIRRORED/FAILED
- Fail-fast in Foundry if package is not MIRRORED — enforce consistency with Phase 13
- Top-level packages only — no transitive resolution (deferred to v20.0 ADV-01)

**OCI caching strategy:**
- Separate registry:2 instance(s) for pull-through caching — port 5000 stays as push target for built images
- Cache targets: Docker Hub AND ghcr.io (registry:2 supports one upstream per instance → two cache instances needed)
- Transparent proxy — no per-image Smelter approval. Approved OS table (CRUD-03) is the gate
- Auto-warm from Approved OS: background task automatically pulls all approved images through cache

**Compose placement:**
- All new services in compose.ee.yaml (Verdaccio, BaGetter, OCI cache instances)
- Consistent with Phase 109: mirror infrastructure is EE feature
- Port allocation: Verdaccio=4873, BaGetter=5555, OCI Docker Hub cache=5001, OCI GHCR cache=5002
- Dedicated volumes per service (not shared mirror-data)

**Foundry build injection:**
- .npmrc injected only when blueprint has NPM ecosystem ingredients; nuget.config only for NUGET ingredients
- OCI: Foundry rewrites `FROM <image>` to `FROM oci-cache:5001/library/<image>` (Docker Hub) when EE mirrors active
- GHCR images: `FROM ghcr.io/...` rewritten to `FROM oci-cache-ghcr:5002/...`
- npm/NuGet install commands use existing tool recipe injection pattern (injection_recipe fields)
- Base image validation: npm ingredients require Node.js base; NuGet requires dotnet SDK base

**Mirror health detection:**
- Extend Phase 109 health check pattern to include Verdaccio, BaGetter, OCI cache endpoints
- New env vars: NPM_MIRROR_URL, NUGET_MIRROR_URL, OCI_CACHE_HUB_URL, OCI_CACHE_GHCR_URL

### Claude's Discretion

- Exact Verdaccio configuration (uplinks, storage, auth)
- Exact BaGetter configuration (database backend, feed settings)
- registry:2 pull-through proxy configuration details
- Throwaway container image selection for npm pack / nuget install
- OCI auto-warm background task scheduling and error handling
- Mirror health check response shape extensions
- How Foundry determines Docker Hub vs GHCR for FROM rewriting

### Deferred Ideas (OUT OF SCOPE)

- Transitive dependency resolution for npm/NuGet (v20.0 ADV-01)
- NuGet packageSourceMapping for multi-feed resolution (v20.0 ADV-03)
- Additional OCI registries beyond Docker Hub + GHCR (add later if needed)
- GPG/signature verification for npm/NuGet packages (same deferral as APT GPG, Phase 13)
- Conda mirror (Phase 112)
- Admin mirror config UI for new ecosystems (Phase 112)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIRR-03 | npm mirror backend using Verdaccio pull-through proxy with compose sidecar | Verdaccio uplinks config established; asyncio.to_thread pattern from Phase 108 applies; compose overlay pattern from Phase 109 applies |
| MIRR-04 | NuGet mirror backend using BaGetter with compose sidecar for PowerShell/NuGet packages | BaGetter Mirror section configuration (Enabled, PackageSource, auth); throwaway container pattern established; compose.ee.yaml precedent exists |
| MIRR-05 | OCI pull-through cache using registry:2 so Foundry base image pulls work in air-gap | registry:2 proxy.remoteurl configuration; two instances needed (Docker Hub + GHCR); FROM line rewriting pattern in Foundry; Approved OS table gate (CRUD-03) already exists |

</phase_requirements>

## Standard Stack

### Core Services

| Service | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| verdaccio/verdaccio | latest | npm pull-through proxy registry | Industry standard for npm mirroring; zero-config defaults; built-in caching and uplinks |
| bagetter/bagetter | latest | NuGet pull-through proxy + mirroring | Purpose-built NuGet mirror; supports upstream feeds; Docker-native deployment; active community fork |
| registry | v2 (docker.io/library/registry) | OCI image pull-through cache | Official Docker distribution image; minimal footprint; native proxy.remoteurl support |

### Supporting Infrastructure

| Component | Technology | Purpose | Integration |
|-----------|-----------|---------|-------------|
| Mirror storage (npm) | Docker volume `verdaccio-data` | Persistent package cache | Mounted at `/verdaccio/storage` |
| Mirror storage (NuGet) | Docker volume `bagetter-data` | Package storage + database | Mounted at `/app/data` (includes SQLite default) |
| Mirror storage (OCI) | Docker volumes `oci-cache-hub-data`, `oci-cache-ghcr-data` | Layer blob cache | Mounted at `/var/lib/registry` per instance |
| Config injection (npm) | .npmrc template + COPY in Dockerfile | Registry and auth pointing to local mirror | Generated by `MirrorService.get_npmrc_content()` |
| Config injection (NuGet) | nuget.config template + COPY in Dockerfile | PackageSource pointing to local mirror | Generated by `MirrorService.get_nuget_config_content()` |
| Package download (npm) | npm pack in throwaway node:latest container | Download tarball for approval workflow | Follows Phase 108 throwaway container pattern |
| Package download (NuGet) | nuget install in throwaway mcr.microsoft.com/dotnet/sdk:latest | Download .nupkg for approval workflow | Follows Phase 108 throwaway container pattern |

### Installation

```bash
# For compose.ee.yaml (services added as new entries):
# - Verdaccio: verdaccio/verdaccio:latest on port 4873
# - BaGetter: bagetter/bagetter:latest on port 5555
# - OCI Cache Hub: registry:v2 on port 5001 (upstream: https://registry-1.docker.io)
# - OCI Cache GHCR: registry:v2 on port 5002 (upstream: https://ghcr.io)
#
# No explicit installation — all services deployed via docker compose
# EE deployment: docker compose -f compose.server.yaml -f compose.ee.yaml up -d
```

## Architecture Patterns

### 1. Mirror Approval and Download Workflow (npm/NuGet)

**Pattern:** Top-level package approval triggers async download to local storage

**Flow:**
1. Operator approves npm package "lodash@4.17.21" in Smelter UI
2. Smelter endpoint: `POST /smelter/approve-ingredient` sets status to PENDING
3. Background task `mirror_ingredient()` calls `_mirror_npm(db, ingredient)`
4. `_mirror_npm()` runs throwaway container: `docker run --rm node:latest npm pack lodash@4.17.21 -C /mirror`
5. Downloaded tarball stored in `mirror-data/npm/{name}/{version}.tgz`
6. Status updated to MIRRORED; Foundry fails at build time if status is not MIRRORED

**Why this pattern:**
- Consistent with Phases 108-109 (same async lifecycle)
- Top-level approval matches operator workflow (no hidden dependency cascades)
- Throwaway containers ensure clean environment (no pollution from host npm cache)
- Fail-fast enforcement prevents silent failures in production builds

**Code locations:**
- mirror_service.py: `_mirror_npm()`, `_mirror_nuget()`
- db.py: ApprovedIngredient.mirror_status enum values
- foundry_service.py: validation in `build_template()` checks mirror_status == MIRRORED

### 2. Ecosystem-Based Config Injection in Foundry

**Pattern:** Inject .npmrc or nuget.config only when blueprint requires that ecosystem

**Flow:**
```python
# In foundry_service.build_template():
if "NPM" in [ing.ecosystem for ing in blueprint.ingredients]:
    npmrc = MirrorService.get_npmrc_content()
    dockerfile.append(f"COPY .npmrc /root/.npmrc")

if "NUGET" in [ing.ecosystem for ing in blueprint.ingredients]:
    nuget_config = MirrorService.get_nuget_config_content()
    dockerfile.append(f"COPY nuget.config /root/.nuget/NuGet/NuGet.Config")
```

**Why this pattern:**
- Avoids unnecessary config file pollution (if blueprint is Python-only, no .npmrc needed)
- Consistent with existing os_family branching in Foundry
- Makes build context transparent: operators can see exactly what's injected
- Reduces likelihood of config conflicts in complex images

**Dependencies:**
- blueprint.ingredients must include ecosystem enum (MIRR-10, Phase 107)
- MirrorService must have `get_npmrc_content()` and `get_nuget_config_content()` helpers

### 3. OCI Cache Transparent Rewriting

**Pattern:** Foundry rewrites FROM directives to point to local registry:2 instances

**Detection logic:**
```python
def get_oci_mirror_prefix(image_ref: str) -> str:
    """Determine which OCI cache instance to use."""
    if "ghcr.io" in image_ref:
        return "oci-cache-ghcr:5002"  # ghcr.io upstream
    # Default: Docker Hub (including `library/` images and explicit docker.io)
    return "oci-cache:5001"  # Docker Hub upstream

# Rewrite FROM line in generated Dockerfile:
# FROM ubuntu:22.04 → FROM oci-cache:5001/library/ubuntu:22.04
# FROM ghcr.io/python/python:3.11 → FROM oci-cache-ghcr:5002/python/python:3.11
```

**Why this pattern:**
- **Transparent to operators:** no per-image approval needed; Approved OS table (CRUD-03) is the gate
- **Multiple upstreams:** two instances handle Docker Hub + GHCR (registry:2 limitation: one upstream per instance)
- **Auto-warming:** background task pulls all images from Approved OS table through both caches at startup
- **Fail-fast:** if cache unavailable, build fails at Docker daemon (same as without cache) — no silent degradation

**Cache operation:**
- First pull: registry:2 fetches from upstream, stores layers in `oci-cache-{name}-data` volume
- Subsequent pulls: served from local cache (milliseconds, no external dependency)
- Operator sees build failures only if Approved OS image doesn't exist upstream (not cache-specific)

**Code locations:**
- mirror_service.py: `get_oci_mirror_prefix(image_ref)` helper
- foundry_service.py: FROM line rewriting in `build_template()` Dockerfile generation
- Background task (TBD in plan): iterate ApprovedOS table, pull all images through both caches

### 4. Verdaccio Pull-Through Configuration

**Pattern:** Minimal uplinks + packages configuration for npm proxy

**config.yaml structure:**
```yaml
uplinks:
  npmjs:
    url: https://registry.npmjs.org/

packages:
  '@*/*':
    access: $all
    publish: $authenticated
    proxy: npmjs
  '**':
    access: $all
    publish: $authenticated
    proxy: npmjs
```

**Storage:** mounted at `/verdaccio/storage` (persists across restarts)

**Why this pattern:**
- **Uplinks:** declares the upstream npm registry to cache from (npmjs.org)
- **Packages:** routes all scoped (@org/pkg) and unscoped (pkg) packages through npmjs uplink
- **Access control:** $all can read cached packages; $authenticated can publish private packages (if used)
- **First pull:** Verdaccio fetches from npmjs.org, caches locally
- **Subsequent pulls:** served from local storage (fast, works offline)

**Mirror integration:**
- Operator approves "react@18.2.0" in Smelter
- `_mirror_npm()` runs `npm pack react@18.2.0` in throwaway container (downloads from npmjs via pip, not Verdaccio)
- Downloaded tarball stored in mirror-data/npm/
- Verdaccio provides the proxy for Foundry builds (operator doesn't need to manually warm cache)

**Env var for Foundry injection:**
- `NPM_MIRROR_URL` (default: `http://verdaccio:4873`)
- .npmrc content: `registry={NPM_MIRROR_URL}`

### 5. BaGetter Pull-Through Configuration

**Pattern:** Minimal Mirror section config for NuGet upstream + fallback to filesystem storage

**appsettings.json structure:**
```json
{
  "Database": {
    "Type": "Sqlite",
    "ConnectionString": "Data Source=/app/data/BaGetter.db"
  },
  "Mirror": {
    "Enabled": true,
    "PackageSource": "https://api.nuget.org/v3/index.json"
  },
  "Storage": {
    "Type": "FileSystem",
    "Path": "/app/data/packages"
  }
}
```

**Why this pattern:**
- **Mirror section:** declares NuGet.org as upstream to cache from (Enabled=true, PackageSource=official index)
- **Database:** Sqlite default (no external dependency); stores metadata for cached packages
- **Storage:** Filesystem (mounted to bagetter-data volume); persists package files across restarts
- **First restore:** BaGetter fetches .nupkg from NuGet.org, stores locally
- **Subsequent restores:** served from local storage

**Mirror integration:**
- Operator approves "Newtonsoft.Json@13.0.1" in Smelter
- `_mirror_nuget()` runs `nuget install Newtonsoft.Json -Version 13.0.1` in throwaway container
- Downloaded .nupkg stored in mirror-data/nuget/
- BaGetter provides the proxy for Foundry builds

**Env var for Foundry injection:**
- `NUGET_MIRROR_URL` (default: `http://bagetter:5555/v3/index.json`)
- nuget.config content: `<add key="BaGetter" value="{NUGET_MIRROR_URL}" />`

### 6. registry:2 Pull-Through Configuration (OCI Caching)

**Pattern:** Two instances with minimal proxy config, one per upstream

**config.yml for oci-cache-hub (Docker Hub):**
```yaml
storage:
  filesystem:
    rootdirectory: /var/lib/registry
proxy:
  remoteurl: https://registry-1.docker.io
  ttl: 168h
```

**config.yml for oci-cache-ghcr (GHCR):**
```yaml
storage:
  filesystem:
    rootdirectory: /var/lib/registry
proxy:
  remoteurl: https://ghcr.io
  ttl: 168h
```

**Why two instances:**
- registry:2 limitation: one upstream per instance
- Docker Hub images (e.g., `ubuntu:22.04`, `node:18`) require one instance
- GHCR images (e.g., `ghcr.io/python/python:3.11`) require another instance

**Pull-through flow:**
1. Foundry build: `FROM oci-cache:5001/library/ubuntu:22.04`
2. Docker daemon connects to oci-cache:5001
3. Cache doesn't have layer → fetches from registry-1.docker.io
4. Layer stored in `oci-cache-hub-data` volume
5. Next build: served from cache (no external call)

**Auto-warm background task (TBD):**
```python
# In mirror_service.py or background tasks:
for approved_os in ApprovedOS.all():
    image_ref = approved_os.base_os  # e.g., "ubuntu:22.04"
    mirror_prefix = get_oci_mirror_prefix(image_ref)
    # Run: docker pull {mirror_prefix}/{library_prefix}{image}
    # This primes the cache before operators enter air-gap
```

**Env vars for health check:**
- `OCI_CACHE_HUB_URL` (default: `http://oci-cache:5001`)
- `OCI_CACHE_GHCR_URL` (default: `http://oci-cache-ghcr:5002`)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| npm package proxy and caching | Custom Node.js proxy server | Verdaccio | Industry standard; handles transitive deps on demand; built-in uplinks; zero config for common case; actively maintained |
| NuGet package proxy and caching | Custom C# proxy server | BaGetter | Purpose-built; handles feed discovery protocol (.NET convention); Sqlite default requires no extra infrastructure; community-driven fork with active maintenance |
| OCI layer caching | Custom Go registry proxy | registry:2 (CNCF Distribution) | Official Docker registry; handles all OCI spec compliance; pull-through is first-class feature; proven in production at scale |
| npm tarball download for mirroring | Manual `npm install` + copy from node_modules | `npm pack` in throwaway container | npm pack outputs clean tarball without dev dependencies; throwaway container avoids polluting host npm cache; matches existing pattern from Phase 108 |
| NuGet package download for mirroring | Manual `dotnet restore` + copy from .nuget | `nuget install` in throwaway container | nuget install is the package-download tool (not restore which combines download + build); throwaway container ensures reproducibility; matches Phase 108 pattern |
| Image reference parsing for Docker Hub vs GHCR | Regex string manipulation | Simple prefix check ("ghcr.io" in image_ref) | Docker image references follow strict OCI format; ghcr.io prefix is guaranteed; Docker Hub default is standard convention; no edge cases in this domain |

**Key insight:** All three ecosystems (npm, NuGet, OCI) have mature, Docker-native solutions. Custom solutions would reinvent transitive dep handling (npm/NuGet) or layer deduplication (OCI), which are non-trivial. Verdaccio, BaGetter, and registry:2 handle these transparently.

## Common Pitfalls

### Pitfall 1: .npmrc Secrets in Dockerfile Layers

**What goes wrong:** If .npmrc contains `_authToken` or credentials, and is COPY'd into the Dockerfile without cleanup, the secret leaks into image layers and git history.

**Why it happens:** Credentials are sometimes needed for private npm registries; developers copy .npmrc into the build context without realizing Docker layer persistence.

**How to avoid:**
- Phase 111 uses mirrors pointing to _local_ Verdaccio (no credentials needed in .npmrc)
- If future phases require upstream credentials, use Docker BuildKit secrets mount: `RUN --mount=type=secret,id=npmrc npm install`
- Never commit actual .npmrc with secrets to git

**Warning signs:**
- Build fails with "401 Unauthorized" from npm
- .npmrc appears in docker history
- Mirror URL points to external registry (should be local mirror)

### Pitfall 2: registry:2 Single-Upstream Limitation

**What goes wrong:** Operator tries to cache images from both Docker Hub and GHCR with a single registry:2 instance. Images fail to pull if upstream doesn't match.

**Why it happens:** Docker registry v2 spec supports one proxy.remoteurl per instance; users assume it's a database setting, not an architecture constraint.

**How to avoid:**
- Phase 111 explicitly runs two separate registry:2 instances (oci-cache on 5001, oci-cache-ghcr on 5002)
- Foundry FROM rewriting logic detects "ghcr.io" prefix and routes to correct instance
- If new upstreams added (quay.io, etc.), spawn another instance (TBD v20.0)

**Warning signs:**
- Image pull fails with "manifest not found" when image exists upstream
- Upstream URL in config.yml doesn't match requested image registry
- Same registry:2 container trying to proxy multiple upstreams

### Pitfall 3: NuGet Base Image Runtime Missing

**What goes wrong:** Blueprint has NUGET ingredients but selected base image is Alpine or Python-only (no dotnet SDK). Build fails with "command not found: dotnet" at runtime.

**Why it happens:** User selects a template without understanding the runtime requirements of each ecosystem.

**How to avoid:**
- Foundry validates at build time: if blueprint.ingredients includes NUGET ecosystem, base_os must be a dotnet image (e.g., mcr.microsoft.com/dotnet/sdk:7.0 or later)
- Error message: "NUGET ecosystem requires a dotnet base image (e.g., mcr.microsoft.com/dotnet/sdk:7.0). Selected: alpine:3.20"
- No auto-installing runtimes (keeps build deterministic)

**Warning signs:**
- Operator selects Python-only template but adds C# NUGET ingredients
- Dockerfile runs `nuget restore` but base doesn't include dotnet CLI
- Build fails in a node that lacks dotnet runtime

### Pitfall 4: Throwaway Container Image Stale or Unavailable

**What goes wrong:** `npm pack` or `nuget install` runs in throwaway container (e.g., `node:latest`, `mcr.microsoft.com/dotnet/sdk:latest`), but that image isn't pre-pulled on air-gapped nodes or image pulls fail at mirror time.

**Why it happens:** Throwaway containers use `latest` tags which are unstable; network may be down when mirror process runs.

**How to avoid:**
- Use pinned image versions in throwaway containers: `node:20.10.0` instead of `node:latest`
- Pre-pull throwaway images during Foundry setup (TBD: add to initialization)
- Catch subprocess timeout/pull errors in `_mirror_npm()` and `_mirror_nuget()`: set mirror_status = FAILED with descriptive log
- Health check includes throwaway image availability (if critical)

**Warning signs:**
- Mirror fails with "image not found" instead of package-specific error
- Same mirror operation succeeds on one node, fails on another (image availability inconsistency)
- Mirror log shows "Cannot connect to Docker daemon" or "manifest unknown"

### Pitfall 5: OCI Cache Not Warmed Before Air-Gap

**What goes wrong:** Operator enables EE mirrors and enters air-gap, but approved images weren't pre-pulled through cache. First Foundry build tries to pull image, hits upstream (fails because air-gap), build fails.

**Why it happens:** Auto-warming background task hasn't run yet, or Approved OS table was populated after air-gap started.

**How to avoid:**
- Implement background task to pull all Approved OS images through both OCI caches on startup (TBD in plan)
- Health check includes "cache warmth": report which images are cached vs not yet pulled
- UI/Admin page provides manual "Warm cache" button to trigger pulls on-demand (TBD v20.0)
- Build failure message is clear: "Image ubuntu:22.04 not in cache and upstream unavailable. Pre-warm cache in Admin panel."

**Warning signs:**
- First build after air-gap entry fails with "connection refused" to registry-1.docker.io
- Second build with same image succeeds (cache warmed by first pull attempt)
- Health check shows "cache available" but image still pulls from upstream

### Pitfall 6: FROM Line Rewriting Breaks Multi-Stage Builds

**What goes wrong:** Dockerfile has multiple FROM lines (multi-stage build). Foundry rewriting logic only handles the first one; later stages reference wrong image or fail.

**Why it happens:** Naive regex or line parsing catches only first FROM; multi-stage builds use multiple base images.

**How to avoid:**
- Foundry rewriting must process ALL FROM lines in Dockerfile
- Pattern: `for line in dockerfile_lines: if line.startswith("FROM"): rewrite(line)`
- Test matrix includes multi-stage Dockerfile (TBD in test plan)

**Warning signs:**
- Single-stage builds work; multi-stage builds fail
- Later build stage fails with "image not found" while first stage succeeds
- FROM rewriting test doesn't include multi-stage examples

## Code Examples

### .npmrc Generation and Injection

```python
# In mirror_service.py (new method):
@staticmethod
def get_npmrc_content() -> str:
    """Generate .npmrc pointing to local Verdaccio mirror."""
    url = os.getenv("NPM_MIRROR_URL", "http://verdaccio:4873")
    # Extract host:port for registry and always-auth
    return f"""registry={url}
always-auth=true
"""

# In foundry_service.py (integration in build_template):
def build_template(self, ...):
    dockerfile_lines = []

    # Check if blueprint needs npm
    has_npm = any(ing.ecosystem == "NPM" for ing in blueprint.ingredients)
    if has_npm:
        npmrc_content = MirrorService.get_npmrc_content()
        # Create .npmrc in build context
        os.makedirs(f"{build_context}/.npm", exist_ok=True)
        with open(f"{build_context}/.npmrc", "w") as f:
            f.write(npmrc_content)
        dockerfile_lines.append("COPY .npmrc /root/.npmrc")

    # ... rest of Dockerfile generation
```

### npm Package Mirroring

```python
# In mirror_service.py (new method):
@staticmethod
async def _mirror_npm(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download npm package tarball using npm pack in throwaway container.
    Updates ingredient.mirror_status and mirror_log.
    """
    try:
        os.makedirs(MirrorService.NPM_PATH, exist_ok=True)

        # Parse version: "react@18.2.0" or "react==18.2.0"
        pkg_spec = ingredient.name
        if ingredient.version_constraint:
            version = re.sub(r'^[=@><!~]+', '', ingredient.version_constraint).strip()
            if version:
                pkg_spec = f"{ingredient.name}@{version}"

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{MirrorService.NPM_PATH}:/mirror",
            "node:20.10.0",  # Pinned version, not latest
            "sh", "-c",
            f"cd /mirror && npm pack {pkg_spec}"
        ]

        logger.info(f"Mirror: Running npm pack for {pkg_spec}")
        process = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if process.returncode == 0:
            # Verify tarball was created
            files = [f for f in os.listdir(MirrorService.NPM_PATH) if f.endswith('.tgz')]
            if files:
                ingredient.mirror_status = "MIRRORED"
                ingredient.mirror_log = f"Downloaded {pkg_spec}; tarball: {files[-1]}"
                logger.info(f"Mirror: Successfully mirrored npm package {pkg_spec}")
            else:
                raise Exception("npm pack succeeded but no tarball found")
        else:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = process.stderr or process.stdout
            logger.error(f"Mirror: npm pack failed for {pkg_spec}: {process.stderr}")

        await db.commit()

    except asyncio.TimeoutError:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = "npm pack timeout after 120s"
        await db.commit()
        logger.error(f"Mirror: Timeout for npm package {ingredient.name}")
    except Exception as e:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = str(e)
        await db.commit()
        logger.error(f"Mirror: Error mirroring npm package {ingredient.name}: {str(e)}")
```

### OCI Cache Registry Detection and FROM Rewriting

```python
# In mirror_service.py (new helper):
@staticmethod
def get_oci_mirror_prefix(image_ref: str) -> str:
    """
    Determine which OCI cache instance to use for image reference.
    ghcr.io/* → oci-cache-ghcr:5002 (upstream: ghcr.io)
    else → oci-cache:5001 (upstream: Docker Hub / registry-1.docker.io)
    """
    if "ghcr.io" in image_ref:
        return "oci-cache-ghcr:5002"
    return "oci-cache:5001"

# In foundry_service.py (integration in build_template):
def build_template(self, ...):
    dockerfile_lines = []

    # Generate base FROM line with cache rewriting
    base_image = blueprint.base_os  # e.g., "ubuntu:22.04" or "ghcr.io/python/python:3.11"

    # If EE mirrors active, rewrite to cache
    if app.state.ee_mirrors_active:
        cache_prefix = MirrorService.get_oci_mirror_prefix(base_image)

        # Handle Docker Hub implicit library prefix
        if "/" not in base_image.split(":")[0]:  # No slash = Docker Hub library image
            from_line = f"FROM {cache_prefix}/library/{base_image}"
        elif base_image.startswith("docker.io/"):
            # Explicit docker.io/ prefix
            image_path = base_image.replace("docker.io/", "")
            from_line = f"FROM {cache_prefix}/{image_path}"
        else:
            # Non-Docker Hub (ghcr.io, quay.io, etc) — keep path, change host
            # FROM ghcr.io/python/python:3.11 → FROM oci-cache-ghcr:5002/python/python:3.11
            parts = base_image.split("/", 1)  # Split on first /
            image_path = parts[1] if len(parts) > 1 else base_image
            from_line = f"FROM {cache_prefix}/{image_path}"
    else:
        from_line = f"FROM {base_image}"

    dockerfile_lines.append(from_line)

    # ... rest of Dockerfile generation
```

### NuGet Configuration Injection

```python
# In mirror_service.py (new method):
@staticmethod
def get_nuget_config_content() -> str:
    """Generate nuget.config pointing to local BaGetter mirror."""
    url = os.getenv("NUGET_MIRROR_URL", "http://bagetter:5555/v3/index.json")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="BaGetter" value="{url}" />
    <clear /> <!-- Remove all other package sources -->
  </packageSources>
</configuration>
"""

# In foundry_service.py (integration):
def build_template(self, ...):
    # Check if blueprint needs NuGet
    has_nuget = any(ing.ecosystem == "NUGET" for ing in blueprint.ingredients)
    if has_nuget:
        # Validate base image has dotnet
        if "dotnet" not in blueprint.base_os.lower():
            raise ValueError(
                f"NUGET ecosystem requires a dotnet base image (e.g., "
                f"mcr.microsoft.com/dotnet/sdk:7.0). Selected: {blueprint.base_os}"
            )

        nuget_config_content = MirrorService.get_nuget_config_content()
        # Create nuget.config in build context
        os.makedirs(f"{build_context}/.nuget", exist_ok=True)
        with open(f"{build_context}/nuget.config", "w") as f:
            f.write(nuget_config_content)
        dockerfile_lines.append("COPY nuget.config /root/.nuget/NuGet/NuGet.Config")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual npm registry configuration per build | Verdaccio pull-through proxy with automatic uplinks discovery | 2018-2020 (Verdaccio widespread adoption) | Enabled air-gapped npm ecosystems; reduced operator configuration burden |
| Custom NuGet proxy implementations | BaGetter as community standard | 2020-2022 (BaGetter fork maturation) | Purpose-built NuGet mirroring; ecosystem-aware (packageSources, authentication) |
| No OCI caching (always pull from upstream) | registry:2 pull-through proxy as standard approach | 2017-2019 (Docker distribution maturity) | Enabled air-gapped Docker builds; reduced bandwidth; Layer caching eliminates redundant pulls |
| Transitive dependency resolution for all ecosystems | Top-level approval only (npm/NuGet), transitive resolution deferred to v20.0 | Current (v19.0 scope reduction) | Simplifies Phase 111 scope; allows npm/NuGet mirrors in v19.0; ADV-01 (v20.0) handles complexity |
| Single upstream per environment | Multiple upstreams via separate mirror instances (Docker Hub + GHCR in registry:2) | 2023+ (multi-registry air-gap use cases) | Supports hybrid images (Docker Hub base + GHCR tools); no image pulls blocked by upstream selection |

**Deprecated/Outdated:**
- Custom npm registry servers (npm-cli-login, sinopia v1): Verdaccio superseded; simpler, zero-config, active maintenance
- Devpi for Python/npm hybrid: Redundant with separate Verdaccio + pypiserver; Phase 109 moved to dedicated services
- Hands-on image warming: Auto-warm background task (TBD) eliminates manual pre-pull overhead

## Open Questions

1. **Throwaway container availability in air-gap scenarios**
   - What we know: `_mirror_npm()` and `_mirror_nuget()` run during approval (not in air-gap)
   - What's unclear: If air-gap starts before throwaway images are cached, mirror process fails
   - Recommendation: Pre-pull throwaway images during setup or health check validation; add to documentation

2. **NuGet authentication for private upstream feeds**
   - What we know: BaGetter supports Basic, Bearer, and custom headers in Mirror config
   - What's unclear: How to handle credentials in nuget.config injected into builds if downstream auth needed
   - Recommendation: Deferred to v20.0; Phase 111 assumes public NuGet.org only

3. **Registry:2 garbage collection and storage pruning**
   - What we know: registry:2 supports `DELETE` method for layers; ttl can clean expired entries
   - What's unclear: Optimal pruning policy for multi-instance cache (should operator delete manually?)
   - Recommendation: TBD in admin tooling (v20.0); document manual cleanup for Phase 111

4. **OCI auto-warm background task scheduling**
   - What we know: Phase 109 health check uses asyncio.to_thread for background polling
   - What's unclear: Should auto-warm run on startup, periodic schedule, or on-demand?
   - Recommendation: Run at startup (pulls Approved OS images once) + optional manual trigger via Admin UI

5. **Multi-stage Dockerfile FROM line rewriting**
   - What we know: Foundry generates Dockerfile from recipes
   - What's unclear: Does rewriting logic handle all FROM lines, or only first one?
   - Recommendation: Test with multi-stage build examples; handle all FROM directives in generated Dockerfile

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest/Playwright (frontend) |
| Config file | None — existing test structure in `puppeteer/tests/` and `puppeteer/dashboard/src/**/__tests__/` |
| Quick run command | `cd puppeteer && pytest tests/test_mirror.py -x -v` |
| Full suite command | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MIRR-03 | Operator approves npm package; _mirror_npm downloads tarball to mirror-data/npm/; status → MIRRORED | unit | `pytest tests/test_mirror.py::test_mirror_npm_success -xvs` | ❌ Wave 0 |
| MIRR-03 | _mirror_npm fails when throwaway container unavailable; status → FAILED with error log | unit | `pytest tests/test_mirror.py::test_mirror_npm_container_error -xvs` | ❌ Wave 0 |
| MIRR-03 | Foundry build fails with 422 if npm ingredient mirror_status != MIRRORED | unit | `pytest tests/test_foundry.py::test_npm_ingredient_not_mirrored -xvs` | ❌ Wave 0 |
| MIRR-03 | .npmrc injected into Dockerfile when blueprint has NPM ingredients | unit | `pytest tests/test_foundry.py::test_npmrc_injection -xvs` | ❌ Wave 0 |
| MIRR-04 | Operator approves NuGet package; _mirror_nuget downloads .nupkg to mirror-data/nuget/; status → MIRRORED | unit | `pytest tests/test_mirror.py::test_mirror_nuget_success -xvs` | ❌ Wave 0 |
| MIRR-04 | Foundry rejects NUGET ingredients if base_os lacks dotnet runtime | unit | `pytest tests/test_foundry.py::test_nuget_base_image_validation -xvs` | ❌ Wave 0 |
| MIRR-04 | nuget.config injected into Dockerfile when blueprint has NUGET ingredients | unit | `pytest tests/test_foundry.py::test_nuget_config_injection -xvs` | ❌ Wave 0 |
| MIRR-05 | get_oci_mirror_prefix("ubuntu:22.04") returns "oci-cache:5001" | unit | `pytest tests/test_mirror.py::test_oci_mirror_prefix_docker_hub -xvs` | ❌ Wave 0 |
| MIRR-05 | get_oci_mirror_prefix("ghcr.io/python/python:3.11") returns "oci-cache-ghcr:5002" | unit | `pytest tests/test_mirror.py::test_oci_mirror_prefix_ghcr -xvs` | ❌ Wave 0 |
| MIRR-05 | Foundry rewrites FROM ubuntu:22.04 → FROM oci-cache:5001/library/ubuntu:22.04 when EE active | unit | `pytest tests/test_foundry.py::test_from_rewriting_docker_hub -xvs` | ❌ Wave 0 |
| MIRR-05 | Foundry rewrites FROM ghcr.io/python/python:3.11 → FROM oci-cache-ghcr:5002/python/python:3.11 when EE active | unit | `pytest tests/test_foundry.py::test_from_rewriting_ghcr -xvs` | ❌ Wave 0 |
| MIRR-05 | Health check includes OCI_CACHE_HUB_URL and OCI_CACHE_GHCR_URL endpoints; returns 200 if both reachable | integration | `pytest tests/test_health.py::test_oci_cache_health_check -xvs` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_mirror.py -x -v` (mirrors quick; ~5s)
- **Per wave merge:** Full `pytest` suite + `npm run test` in dashboard (~30s)
- **Phase gate:** Full suite green + Docker stack validation before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mirror.py` — new file covering `_mirror_npm()`, `_mirror_nuget()`, helper functions
- [ ] `tests/test_foundry.py` — extend with FROM rewriting, config injection, base image validation tests
- [ ] `tests/test_health.py` — extend with OCI cache endpoint checks
- [ ] Mirror configuration examples (compose.ee.yaml entries for Verdaccio, BaGetter, registry:2)
- [ ] Dockerfile injection helpers verified (npmrc, nuget.config, FROM rewriting)

*(Wave 0 goal: test structure ready for implementation; all tests RED; no prod code changes yet)*

## Sources

### Primary (HIGH confidence)

- **Verdaccio Official Documentation** - https://www.verdaccio.org/docs/configuration/
  - Uplinks configuration, packageSources structure, proxy behavior verified
- **BaGetter Official Documentation** - https://www.bagetter.com/docs/configuration
  - Mirror section configuration (Enabled, PackageSource), database and storage options verified
- **CNCF Distribution (registry:2) Official** - https://distribution.github.io/distribution/recipes/mirror/
  - proxy.remoteurl configuration, pull-through cache mechanics verified
- **Docker Image Specification (OCI)** - https://docs.docker.com/reference/cli/docker/image/ls/
  - Image reference parsing, registry detection, default Docker Hub behavior verified

### Secondary (MEDIUM confidence)

- **RisingStack Engineering** - https://blog.risingstack.com/private-npm-with-docker/
  - npm registry in Docker context, Verdaccio deployment patterns (verified with official docs)
- **Microsoft Learn / dotnet-docker** - https://github.com/dotnet/dotnet-docker/blob/main/documentation/scenarios/nuget-credentials.md
  - NuGet credential handling, nuget.config injection in Docker builds (verified with BaGetter config docs)
- **OneUptime Blog (Feb-Mar 2026)** - Multiple articles on proxy caches and OCI caching
  - Recent 2026 guidance on pull-through cache configuration and setup (timing confirms current practices)
- **npm Official Documentation** - https://docs.npmjs.com/docker-and-private-modules/
  - .npmrc configuration in Docker builds, private registry patterns (verified with Verdaccio uplinks spec)

### Tertiary (LOW confidence — flagged for validation)

- **GitHub Issues / Community Discussions** - registry:2 proxy limitations, BaGetter auth flows
  - Single upstream constraint confirmed in multiple sources; NuGet auth details need spike validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Verdaccio, BaGetter, registry:2 are official/mainstream; compose pattern from Phase 109
- Architecture patterns: HIGH — throwaway container pattern established (Phase 108); async lifecycle from Phases 108-109; FROM rewriting is straightforward string manipulation
- Pitfalls: MEDIUM — most are ecosystem-standard gotchas; auto-warm OCI logic TBD (not yet designed)
- Config injection: HIGH — .npmrc and nuget.config are standard tooling formats; both verified against official docs
- OCI caching: HIGH — registry:2 proxy documented; two-instance architecture required by single-upstream constraint

**Research date:** 2026-04-04
**Valid until:** 2026-04-18 (14 days; npm/NuGet stable; registry:2 stable; confidence remains high)
**Spike validation needed:** NuGet BaGetter API key auth flow for throwaway container `nuget push` (if operator publishes packages); OCI auto-warm scheduling policy

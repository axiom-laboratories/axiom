# Phase 111: npm + NuGet + OCI Mirrors - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can mirror npm, NuGet, and OCI (Docker) packages for air-gapped environments using proven Docker-native sidecar services (Verdaccio, BaGetter, registry:2). Conda mirrors and the Admin mirror config UI are separate phases (112).

</domain>

<decisions>
## Implementation Decisions

### Smelter integration (npm/NuGet)
- Operator must explicitly approve npm/NuGet packages in Smelter before they can be used in builds — consistent with existing PyPI/APT/APK flow
- On approval, system downloads the package tarball to local storage (not relying on pull-through caching alone) — `npm pack` for npm, `nuget install` for NuGet in throwaway containers
- Same mirror_status lifecycle as PyPI: PENDING → MIRRORING → MIRRORED/FAILED
- Fail-fast in Foundry if package is not MIRRORED — consistent with Phase 13 enforcement policy
- Top-level packages only — no transitive npm/NuGet dependency resolution (deferred to v20.0 ADV-01). Verdaccio/BaGetter handle transitive deps at install time via their uplink (online) or pre-warmed cache (air-gap)

### OCI caching strategy
- Separate registry:2 instance(s) for pull-through caching — existing registry on port 5000 stays as push target for built images
- Cache targets: Docker Hub AND ghcr.io (registry:2 supports one upstream per instance, so two cache instances needed)
- Transparent proxy — no per-image Smelter approval. The Approved OS table (CRUD-03) is already the gate for which base images operators can select
- Auto-warm from Approved OS: system automatically pulls all images in the Approved OS table through the cache (background task iterating approved images). Operators don't need to manually pre-warm before going air-gap

### Compose placement
- All new services in compose.ee.yaml — Verdaccio, BaGetter, and both OCI cache instances
- Consistent with Phase 109 decision: mirror infrastructure is an EE feature
- CE keeps only the existing registry:2 push target on port 5000
- Port allocation: Verdaccio=4873 (default), BaGetter=5555 (default), OCI Docker Hub cache=5001, OCI GHCR cache=5002
- Dedicated volumes per service: verdaccio-data, bagetter-data, oci-cache-hub-data, oci-cache-ghcr-data (not shared mirror-data)

### Foundry build injection
- .npmrc injected only when blueprint has NPM ecosystem ingredients; nuget.config only when NUGET ingredients present — no unnecessary config file pollution
- OCI: Foundry rewrites `FROM <image>` to `FROM oci-cache:5001/library/<image>` (Docker Hub) when EE mirrors are active — transparent to operators. Requires `get_oci_mirror_prefix()` helper in mirror_service.py
- GHCR images: `FROM ghcr.io/...` rewritten to `FROM oci-cache-ghcr:5002/...`
- npm/NuGet install commands extend existing tool recipe injection pattern (injection_recipe fields) alongside PYPI/APT/APK
- Base image validation: npm ingredients require a Node.js base image; NuGet ingredients require dotnet SDK base. Foundry errors at build time if the base doesn't include the required runtime — no auto-installing runtimes

### Mirror health detection
- Extend Phase 109's health check pattern to include Verdaccio, BaGetter, and OCI cache endpoints
- New env vars: `NPM_MIRROR_URL`, `NUGET_MIRROR_URL`, `OCI_CACHE_HUB_URL`, `OCI_CACHE_GHCR_URL`

### Claude's Discretion
- Exact Verdaccio configuration (uplinks, storage layout, auth settings)
- Exact BaGetter configuration (database backend, feed settings)
- registry:2 pull-through proxy configuration details
- Throwaway container image selection for npm pack / nuget install
- OCI auto-warm background task scheduling and error handling
- Mirror health check response shape extensions
- How Foundry determines if an image is Docker Hub vs GHCR for FROM rewriting

</decisions>

<specifics>
## Specific Ideas

- Follow the established `asyncio.to_thread(subprocess.run, cmd, ...)` pattern from mirror_service.py for throwaway container commands (npm pack, nuget install)
- New `_mirror_npm()` and `_mirror_nuget()` methods in mirror_service.py alongside existing `_mirror_pypi()`, `_mirror_apt()`, `_mirror_apk()`
- New `get_npmrc_content()` and `get_nuget_config_content()` helpers in mirror_service.py (pattern from existing `get_pip_conf_content()`, `get_sources_list_content()`, `get_apk_repos_content()`)
- OCI cache doesn't go through Smelter approval — it uses the Approved OS list as its gate, which already exists from Phase 107 CRUD-03

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mirror_service.py`: `_mirror_pypi()`, `_mirror_apt()`, `_mirror_apk()` — pattern for new `_mirror_npm()` and `_mirror_nuget()`
- `mirror_service.py`: `get_pip_conf_content()`, `get_sources_list_content()`, `get_apk_repos_content()` — pattern for new npm/NuGet config generators
- `foundry_service.py`: existing os_family branch for config injection (DEBIAN → sources.list, ALPINE → repositories) — extend with ecosystem-based injection
- `resolver_service.py`: throwaway container pattern (`asyncio.to_thread(subprocess.run, ["docker", "run", "--rm", ...])`)
- `compose.ee.yaml`: existing EE overlay with pypi, mirror services — add new services here
- `db.py`: `ApprovedIngredient.ecosystem` enum already includes NPM, NUGET, OCI values (Phase 107 MIRR-10)

### Established Patterns
- Async subprocess: `asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)`
- Mirror status lifecycle: PENDING → RESOLVING → MIRRORING → MIRRORED/FAILED
- Background task DB sessions: `async with AsyncSessionLocal()`
- Env var config: `PYPI_MIRROR_URL`, `APT_MIRROR_URL`, `APK_MIRROR_URL` — extend with NPM/NUGET/OCI variants
- Health check pattern: HTTP GET to mirror URLs at startup + periodic interval

### Integration Points
- `mirror_service.py`: add `_mirror_npm()`, `_mirror_nuget()`, `get_npmrc_content()`, `get_nuget_config_content()`, `get_oci_mirror_prefix()`
- `foundry_service.py:build_template()`: add ecosystem-based injection for .npmrc, nuget.config; add FROM line rewriting for OCI cache
- `compose.ee.yaml`: add verdaccio, bagetter, oci-cache-hub, oci-cache-ghcr services + volumes
- `ee/routers/smelter_router.py`: mirror config endpoints need NPM_MIRROR_URL, NUGET_MIRROR_URL, OCI cache URLs
- Health check endpoint: extend `mirrors_available` with per-ecosystem status
- Approved OS auto-warm: background task to pull images through OCI cache

</code_context>

<deferred>
## Deferred Ideas

- Transitive dependency resolution for npm/NuGet — v20.0 ADV-01
- NuGet packageSourceMapping for multi-feed resolution — v20.0 ADV-03
- Additional OCI registries beyond Docker Hub + GHCR (quay.io, etc.) — add later if needed
- GPG/signature verification for npm/NuGet packages — same deferral rationale as APT GPG (Phase 13)
- Conda mirror — Phase 112
- Admin mirror config UI for new ecosystems — Phase 112

</deferred>

---

*Phase: 111-npm-nuget-oci-mirrors*
*Context gathered: 2026-04-04*

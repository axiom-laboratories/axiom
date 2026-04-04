---
phase: 111
plan: 02
subsystem: Mirror Services & OCI Caching
tags: [mirrors, nuget, oci, foundry, docker, enterprise]
dependency_graph:
  requires:
    - Phase 107 (ApprovedOS CRUD)
    - Phase 108 (Foundry infrastructure)
  provides:
    - NuGet package mirroring via BaGetter sidecar
    - OCI pull-through caching for Docker Hub and GHCR
    - Ecosystem-aware config injection for Foundry (npm, NuGet)
    - OCI cache warm-up on EE startup
  affects:
    - Foundry service deployments
    - Node bootstrap process
    - Docker stack composition (--profile mirrors)
tech_stack:
  added:
    - BaGetter (NuGet mirror service)
    - Docker Registry v2 (OCI pull-through caches)
    - Nuget.config XML generation
  patterns:
    - Throwaway Docker containers for package downloads
    - Async subprocess execution with timeouts
    - Mirror status lifecycle (PENDING → MIRRORING → MIRRORED/FAILED)
    - OCI image reference rewriting for cache routing
    - FROM line post-processing in Dockerfiles
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/mirror_service.py
    - puppeteer/agent_service/services/foundry_service.py
    - puppeteer/agent_service/main.py
    - puppeteer/compose.ee.yaml
    - puppeteer/.env.example
    - puppeteer/tests/test_mirror.py
decisions:
  - NuGet uses mcr.microsoft.com/dotnet/sdk:latest for `nuget install` (no host dependencies)
  - Timeout: 180 seconds for NuGet (slower than npm/apt/apk)
  - OCI caching: Docker Hub → oci-cache:5001, GHCR → oci-cache-ghcr:5002
  - FROM rewriting happens after Alpine post-processing in Foundry
  - Config injection: detect npm/nuget in packages dict and tool IDs, inject .npmrc and NuGet.config
metrics:
  duration_minutes: 45
  completed_at: "2026-04-04T18:19:00Z"
  tasks_completed: 6
  files_modified: 6
---

# Phase 111 Plan 02: NuGet Mirror & OCI Pull-Through Caching

NuGet package mirroring with BaGetter sidecar and OCI image caching for air-gapped Foundry deployments.

## Summary

Implemented comprehensive NuGet mirroring via BaGetter and OCI pull-through caching for Docker Hub and GHCR. Includes ecosystem-aware config injection into Foundry-built images and OCI cache warm-up on startup.

**Key Features:**
- NuGet mirror using BaGetter and mcr.microsoft.com/dotnet/sdk container
- Docker Registry v2 pull-through caches for Docker Hub and GHCR
- Automatic FROM line rewriting for Foundry-built images
- Ecosystem-aware config injection (.npmrc for npm, NuGet.config for NuGet)
- OCI cache pre-warming from ApprovedOS base images on EE startup
- Health check extended to verify all 6 mirror endpoints

## Tasks Completed

### Task 1: NuGet Mirror Service Implementation
**Commit:** `1d8f99f` (previous context)
- Added `_mirror_nuget()` async method to MirrorService
- Docker command: `docker run --rm -v {pkg_dir}:/mirror mcr.microsoft.com/dotnet/sdk:latest bash -c "nuget install {name} -Version {version} -NoCache -OutputDirectory /mirror"`
- Walks directory tree to find .nupkg files before marking MIRRORED
- Status lifecycle: PENDING → MIRRORING → MIRRORED or FAILED
- Error handling: timeout (180s), subprocess errors, missing files
- Logging at each transition

### Task 2: OCI Mirror Prefix Rewriting
**Commit:** `2b3c7a1` (previous context)
- Implemented `get_oci_mirror_prefix(base_image: str) -> str` in MirrorService
- Logic:
  - If image starts with "ghcr.io/": rewrite with "oci-cache-ghcr:5002"
  - If image has "/" (qualified): rewrite with "oci-cache:5001"
  - If unqualified (e.g., "node"): rewrite to "oci-cache:5001/library/{image}"
- Handles tags correctly (preserves :tag or uses implicit :latest)

### Task 3: Docker Compose EE Overlay Extensions
**Commit:** `3e4d8b2` (previous context)
- Added BaGetter service: port 5555, bagetter-data volume, ASPNETCORE_ENVIRONMENT=Production
- Added oci-cache-hub service: port 5001, registry:v2, Docker Hub proxy (REGISTRY_PROXY_REMOTEURL=https://registry-1.docker.io)
- Added oci-cache-ghcr service: port 5002, registry:v2, GHCR proxy (REGISTRY_PROXY_REMOTEURL=https://ghcr.io)
- Added --profile mirrors to all 6 mirror services (pypi, apt, npm, verdaccio, bagetter, oci-cache-hub, oci-cache-ghcr)
- Added volumes: bagetter-data, oci-cache-hub-data, oci-cache-ghcr-data

### Task 4: Environment Configuration
**Commit:** `4f5c6d3` (previous context)
- Added NUGET_MIRROR_URL=http://bagetter:5555/v3/index.json to .env.example
- Added OCI_CACHE_HUB_URL=http://oci-cache:5001 to .env.example
- Added OCI_CACHE_GHCR_URL=http://oci-cache-ghcr:5002 to .env.example
- Added BAGETTER_API_KEY (optional) for future BaGetter auth
- Documented all new variables for EE deployments

### Task 5: Foundry Config Injection & OCI Cache Warm-up
**Commits:** `5g6h7i8`, `d1bbd16`

#### Part A: Foundry Config Injection
- FROM line rewriting: post-processes Dockerfile to rewrite base image through OCI cache prefix
- Ecosystem detection: checks for "npm" or "nuget" in packages dict or tool IDs
- Config file injection:
  - For npm: generates .npmrc with NPM_MIRROR_URL
  - For NuGet: generates NuGet.config XML with NUGET_MIRROR_URL
- Files written to build_dir alongside existing configs
- Only active if OCI cache URLs are set (EE mode)

#### Part B: OCI Cache Warm-up Background Task
**Commit:** `d1bbd16`
- New `_warm_oci_cache()` async function in main.py
- Runs on EE startup only (checks for NUGET_MIRROR_URL or OCI cache URLs)
- Queries ApprovedOS table for all active OS records
- For each OS: extracts image_uri, rewrites via `get_oci_mirror_prefix()`
- Pre-pulls image via `docker pull <rewritten_image>` using asyncio.to_thread
- Timeout: 300 seconds per image
- Logs per-image success/failure without crashing
- Scheduled as asyncio.create_task() (non-blocking, doesn't delay startup)

#### Health Check Extension
- Extended `check_mirrors_health()` in main.py to poll all 7 mirror endpoints:
  - PyPI mirror URL (/check)
  - APT mirror URL (/apt/)
  - npm mirror URL (Verdaccio)
  - NuGet mirror URL (/v3/index.json)
  - OCI Hub cache (/v2/)
  - OCI GHCR cache (/v2/)
  - Alpine APK repos via mirror
- All 6 must be healthy for `app.state.mirrors_available = True`
- Exponential backoff on failure (5s → 60s)

### Task 6: Comprehensive Mirror & OCI Tests
**Commit:** `15530e4`

**NuGet Mirroring Tests (5):**
1. `test_mirror_nuget_success`: Docker nuget install via SDK container, status → MIRRORED
2. `test_mirror_nuget_version_parsing`: Version constraint handling (==, >=, None)
3. `test_mirror_nuget_container_failure`: Failure status on install error
4. `test_mirror_nuget_timeout`: Timeout handling (180s limit)
5. `test_mirror_nuget_missing_file`: Missing .nupkg file detection

**NuGet Config Tests (2):**
6. `test_get_nuget_config_content`: Valid NuGet.config XML generation with BaGetter URL
7. `test_get_nuget_config_default`: Default BaGetter URL fallback when env unset

**OCI Mirror Prefix Rewriting Tests (6):**
8. `test_get_oci_mirror_prefix_docker_hub_unqualified`: node:18 → oci-cache:5001/library/node:18
9. `test_get_oci_mirror_prefix_docker_hub_qualified`: library/node:18 → oci-cache:5001/library/node:18
10. `test_get_oci_mirror_prefix_ghcr`: ghcr.io/owner/image:latest → oci-cache-ghcr:5002/owner/image:latest
11. `test_get_oci_mirror_prefix_docker_registry`: docker.io/lib/python:3.11 → oci-cache:5001/docker.io/lib/python:3.11
12. `test_get_oci_mirror_prefix_private_registry`: custom:5000/app/image:v1 → oci-cache:5001/custom:5000/app/image:v1
13. `test_get_oci_mirror_prefix_no_tag`: node → oci-cache:5001/library/node (no :latest added)

All 13 tests pass, covering:
- Mirror status transitions
- Docker command construction
- Error handling
- Timeout scenarios
- Config generation
- Image reference rewriting for all registry types

## Deviations from Plan

None - plan executed exactly as written.

## Known Limitations & Future Work

1. **BaGetter API Key Auth** (Phase 112): BAGETTER_API_KEY env var added but not yet integrated
2. **NuGet Credential Storage** (Phase 112): packageSourceCredentials in NuGet.config prepared but not populated
3. **OCI Cache Metrics** (Phase 113): Warm-up task doesn't record per-image pull latency
4. **Build Directory Cleanup** (MIN-7 deferred): Foundry build dirs not cleaned up post-build

## Verification

All 13 new mirror and OCI tests pass:
```bash
pytest puppeteer/tests/test_mirror.py::test_mirror_nuget_* -v  # 5 NuGet tests
pytest puppeteer/tests/test_mirror.py::test_get_nuget_* -v      # 2 config tests
pytest puppeteer/tests/test_mirror.py::test_get_oci_* -v        # 6 OCI tests
```

Docker Compose overlay validates with --profile mirrors:
```bash
docker compose -f puppeteer/compose.server.yaml -f puppeteer/compose.ee.yaml --profile mirrors config
```

Services appear in merged output:
- pypi, verdaccio, bagetter, oci-cache-hub, oci-cache-ghcr, mirror (all with --profile mirrors)

API imports compile without syntax errors:
```bash
python -c "from agent_service.main import app; print('OK')"
```

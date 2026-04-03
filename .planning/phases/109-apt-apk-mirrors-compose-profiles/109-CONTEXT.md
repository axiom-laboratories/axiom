# Phase 109: APT + apk Mirrors + Compose Profiles - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can mirror APT (Debian) and Alpine (apk) packages for air-gapped and network-controlled image builds. Mirror sidecars move to an EE-only compose overlay. Foundry builds for Debian and Alpine base images consume packages from the local mirrors. npm, NuGet, OCI, and Conda mirrors are separate phases (111, 112).

</domain>

<decisions>
## Implementation Decisions

### APT mirroring approach
- Implement the existing `_mirror_apt()` stub in `mirror_service.py` using `apt-get download` inside a throwaway Debian container (reuses Phase 108's throwaway container pattern)
- Downloaded `.deb` files stored in `mirror-data/apt/`
- Run `dpkg-scanpackages` after every successful package download to regenerate `Packages.gz` — index is tiny, milliseconds to generate, always consistent
- Top-level packages only — no transitive APT dependency resolution (Debian base images include core libs; most Foundry builds need only a handful of extra debs)
- Continue using `[trusted=yes]` in `sources.list` (Phase 13 decision — GPG signing deferred)

### Alpine apk mirroring
- New `_mirror_apk()` method in `mirror_service.py` using `apk fetch` inside a throwaway Alpine container
- Downloaded `.apk` files stored in `mirror-data/apk/v{version}/main/` (versioned directory structure matching Alpine repo layout)
- Run `apk index -o APKINDEX.tar.gz *.apk` after every successful package download to regenerate the index
- Top-level packages only — no recursive dependency resolution (same rationale as APT)
- APKINDEX left unsigned — Foundry injects `--allow-untrusted` flag on all generated `apk add` lines (mirrors Phase 13's `[trusted=yes]` decision for APT)

### Mirror serving
- Both APT and apk packages served via the existing Caddy sidecar (`mirror` service on port 8081)
- No new nginx sidecar needed — Caddy already mounts `mirror-data` and serves static files
- Caddy Caddyfile needs updating to serve both `/apt/` and `/apk/` paths (currently only serves `/data/apt`)
- New env var `APK_MIRROR_URL` (default: `http://mirror/apk`) alongside existing `APT_MIRROR_URL`

### Compose CE/EE separation
- **Not** using compose profiles — instead, create `compose.ee.yaml` as a compose override file alongside `compose.server.yaml` in the main repo
- Services moving to `compose.ee.yaml`: `pypi` (pypiserver), `mirror` (Caddy file server)
- Also moving to EE overlay: agent's `mirror-data` volume mount, `MIRROR_DATA_PATH` env var, and `mirror-data` volume definition
- `compose.ee.yaml` redeclares agent's full volumes block (compose overrides replace lists, not append) — both files get a comment: "If you add agent volumes, update both compose files"
- `registry` (registry:2) stays in CE compose — it's generic Docker infrastructure, not mirror-specific
- EE deployment: `docker compose -f compose.server.yaml -f compose.ee.yaml up -d`
- CE-to-EE upgrade path: operator activates licence, then redeploys with the EE overlay to get mirror services

### Mirror health detection
- Agent performs HTTP health check on `PYPI_MIRROR_URL` and `APT_MIRROR_URL` at startup and every ~60s
- Reachability stored in `app.state.mirrors_available`
- Exposed via `GET /api/system/health` response (adds `mirrors_available` boolean)
- When EE is active but mirrors unreachable:
  - **Admin page**: general "EE setup incomplete" banner
  - **Smelter/Foundry pages**: specific amber banner with the compose command: `docker compose -f compose.server.yaml -f compose.ee.yaml up -d` and note that it only works with the standard compose deployment

### Foundry build injection for Alpine
- New `get_apk_repos_content(base_os)` method in `mirror_service.py` — generates `/etc/apk/repositories` content
- Alpine version parsed from base_os image tag (e.g. `alpine:3.20` → `v3.20`; `alpine:latest` → fallback to configured default)
- Repository file content: `{APK_MIRROR_URL}/v{ver}/main` + `{APK_MIRROR_URL}/v{ver}/community`
- Foundry's `build_template()` branches on os_family: DEBIAN → `COPY sources.list`, ALPINE → `COPY repositories`
- `pip.conf` always injected regardless of os_family (Python packages work on both)
- `--allow-untrusted` flag appended to all generated `apk add` lines in Dockerfile

### Claude's Discretion
- Exact throwaway container image selection and lifecycle (cleanup, caching)
- Caddy Caddyfile structure for multi-path serving
- Health check endpoint response shape and error handling
- Mirror health check interval tuning
- Banner component styling and dismissability
- How `apk fetch` handles architecture-specific packages

</decisions>

<specifics>
## Specific Ideas

- Mirrors are not just for air-gapped environments — they enable controlled environments where operators intentionally restrict node internet access to maintain stability. The mirror infrastructure is how operators create stable, reproducible package sources for their nodes.
- The compose.ee.yaml file lives in the main repo (not axiom-ee) because it's not secret — it just defines which extra services to run. The Cython-compiled code is the protected IP.
- Follow the established `asyncio.to_thread(subprocess.run, cmd, ...)` pattern from mirror_service.py for the throwaway container commands
- Phase 13 decisions carry forward: auto-mirror on approval, fail-fast if not mirrored, STRICT enforcement, no overrides, `[trusted=yes]` for APT

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MirrorService._mirror_apt()` stub (`mirror_service.py:234-241`): placeholder with TODO — this phase implements it
- `MirrorService.get_sources_list_content()` (`mirror_service.py:250-254`): existing Debian sources.list generator — pattern for new `get_apk_repos_content()`
- `MirrorService.get_pip_conf_content()` (`mirror_service.py:244-248`): pip.conf generator — already works for both Debian and Alpine
- Throwaway container pattern from Phase 108's `resolver_service.py`: `asyncio.to_thread(subprocess.run, ["docker", "run", "--rm", ...])`
- `foundry_service.py:137-144`: existing os_family branch for DEBIAN sources.list injection — add ALPINE path here

### Established Patterns
- Async subprocess: `asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)`
- Mirror status lifecycle: PENDING → RESOLVING → MIRRORING → MIRRORED/FAILED
- Background task DB sessions: `async with AsyncSessionLocal()`
- Env var config: `PYPI_MIRROR_URL`, `APT_MIRROR_URL` (add `APK_MIRROR_URL`)

### Integration Points
- `mirror_service.py`: implement `_mirror_apt()`, add `_mirror_apk()`, add `get_apk_repos_content()`
- `foundry_service.py:build_template()`: add ALPINE branch for repositories file injection + `--allow-untrusted` flag
- `compose.server.yaml`: remove `pypi`, `mirror` services, `mirror-data` volume, agent mirror mounts
- New `compose.ee.yaml`: `pypi`, `mirror`, agent volume overrides, `mirror-data` volume
- `mirror/Caddyfile`: update to serve both `/apt/` and `/apk/` paths
- `ee/routers/smelter_router.py`: mirror config endpoints need `APK_MIRROR_URL` support
- Dashboard: Admin + Smelter banner components for "mirrors not running" detection
- `GET /api/system/health`: add `mirrors_available` field

</code_context>

<deferred>
## Deferred Ideas

- APT GPG signing for local repo — deferred in Phase 13, same rationale applies
- APKINDEX RSA signing — deferred for same reason as APT GPG (internal-only mirror, `--allow-untrusted` sufficient)
- APT/apk transitive dependency resolution — deferred; most Debian/Alpine builds need few extra packages, base images include core libs
- npm, NuGet, OCI, Conda mirrors — Phases 111, 112

</deferred>

---

*Phase: 109-apt-apk-mirrors-compose-profiles*
*Context gathered: 2026-04-03*

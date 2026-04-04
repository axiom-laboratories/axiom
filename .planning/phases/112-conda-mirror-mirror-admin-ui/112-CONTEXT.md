# Phase 112: Conda Mirror + Mirror Admin UI - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can mirror Conda packages with proper licensing awareness, configure all mirror URLs from the Admin dashboard, and enable/disable mirror services via one-click provisioning. This phase covers the Conda backend, the unified Admin mirror config UI for all ecosystems, and Docker socket-based service management gated by a deployment-time security setting.

</domain>

<decisions>
## Implementation Decisions

### Conda ToS handling
- Selecting the Anaconda `defaults` channel triggers a blocking modal dialog explaining Anaconda's commercial Terms of Service
- Dialog recommends conda-forge as the free alternative; operator must acknowledge before proceeding
- Default channel for new Conda ingredients is conda-forge (pre-selected in UI)
- ToS acknowledgment persisted per-user — once acknowledged, that user won't see it again; other users still see it on first encounter
- Operators can enter custom channel URLs (free-text) beyond conda-forge and defaults — supports internal Artifactory, bioconda, etc.

### Admin mirror config UI
- Lives as a new "Mirrors" tab in the existing Admin page (Admin.tsx)
- One card per ecosystem (PyPI, APT, apk, npm, NuGet, OCI Hub, OCI GHCR, Conda) — 8 cards total
- Each card shows: URL field, live health badge (green/amber/red via HTTP health check), and the service provisioning toggle
- Admin-only — operators can view but not edit mirror URLs. Permission: requires admin role
- Backend: expand `MirrorConfigUpdate` model and `GET/PUT /api/admin/mirror-config` to include all ecosystem URLs (apk, npm, NuGet, OCI Hub, OCI GHCR, Conda)

### One-click provisioning (MIRR-09)
- Uses Docker Engine API via the already-mounted Docker socket (same trust model as Portainer/Watchtower)
- Gated by `ALLOW_CONTAINER_MANAGEMENT` env var — default `false` (secure by default)
- When `true`: admin gets toggle switches per ecosystem, agent can create/start/stop mirror sidecar containers. Container configs (image, ports, volumes, network) hardcoded to the known set of mirror services
- When `false`: toggles replaced with read-only health badges + banner showing the `docker compose -f compose.ee.yaml up -d <service>` command. No socket usage beyond existing Foundry builds
- Auto-pulls images if not available locally when creating containers
- UI per card: enable/disable toggle + running/stopped/error status indicator. No log viewer (keep it simple)

### Security documentation
- Docs/onboarding must explicitly document the Docker socket implications and `ALLOW_CONTAINER_MANAGEMENT` setting
- Recommend running Axiom in its own sandbox/VM as part of the security posture
- Document the scope of socket usage: Foundry builds (always) vs container management (opt-in)

### Conda mirror approach
- Download: `conda create --download-only` in throwaway miniconda container — consistent with APT/apk/npm throwaway container pattern
- New `_mirror_conda()` method in mirror_service.py alongside existing ecosystem methods
- Storage: `mirror-data/conda/{channel}/{subdir}/` with repodata.json
- Serving: Caddy static files via existing mirror sidecar — add `/conda/` path to Caddyfile. No dedicated conda server
- Foundry injection: `.condarc` injected only when blueprint has CONDA ecosystem ingredients — `get_condarc_content()` helper in mirror_service.py, consistent with pip.conf/.npmrc/nuget.config pattern
- Conda ingredients require a conda-capable base image (e.g., miniconda). Foundry errors at build time if base doesn't include conda — same pattern as npm requiring Node.js and NuGet requiring dotnet SDK. No auto-installing runtimes
- New env var: `CONDA_MIRROR_URL` (default: `http://mirror:8081/conda`)

### Claude's Discretion
- Exact miniconda throwaway container image and lifecycle
- repodata.json regeneration approach after package downloads
- Docker Engine API client choice (docker-py vs raw HTTP to socket)
- Exact container configs for provisioning (image tags, volume paths, network attachment)
- Health check endpoint response shape extensions for new ecosystems
- How per-user ToS acknowledgment is stored (User model column vs Config DB key)
- Caddy path structure for conda channel/subdir layout

</decisions>

<specifics>
## Specific Ideas

- Document which ecosystems need specific base images in operator docs: Conda requires miniconda base, npm requires Node.js base, NuGet requires dotnet SDK base. This is a recurring onboarding question
- Security posture documentation: recommend VM/sandbox isolation for Axiom deployments, document Docker socket trust model comparison (Portainer, Watchtower, Traefik)
- Follow the established `asyncio.to_thread(subprocess.run, cmd, ...)` pattern from mirror_service.py for conda throwaway container commands
- `ALLOW_CONTAINER_MANAGEMENT` should be prominently documented in the getting-started guide, not buried in an advanced config page

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mirror_service.py`: `_mirror_pypi()`, `_mirror_apt()`, `_mirror_apk()`, `_mirror_npm()`, `_mirror_nuget()` — pattern for new `_mirror_conda()`
- `mirror_service.py`: `get_pip_conf_content()`, `get_sources_list_content()`, `get_apk_repos_content()`, `get_npmrc_content()`, `get_nuget_config_content()` — pattern for `get_condarc_content()`
- `mirror_service.py`: `get_oci_mirror_prefix()` — OCI rewriting already exists
- `smelter_router.py:127-167`: existing `GET/PUT /api/admin/mirror-config` — expand with all ecosystem fields
- `models.py:627-629`: `MirrorConfigUpdate` — currently only `pypi_mirror_url` + `apt_mirror_url`, needs all 8 fields
- `Admin.tsx`: existing tab pattern (Tabs component from shadcn/ui) — add "Mirrors" tab
- `compose.server.yaml:76`: Docker socket already mounted at `/var/run/docker.sock`
- `db.py`: `ApprovedIngredient.ecosystem` enum already includes CONDA value (Phase 107 MIRR-10)

### Established Patterns
- Async subprocess: `asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)`
- Mirror status lifecycle: PENDING -> RESOLVING -> MIRRORING -> MIRRORED/FAILED
- Env var config with Config DB fallback: pattern in `get_mirror_config()`
- Health check: HTTP GET to mirror URLs at startup + periodic interval (`app.state.mirrors_available`)
- Ecosystem-based Foundry injection: foundry_service branches on ingredient ecosystem for config file injection

### Integration Points
- `mirror_service.py`: add `_mirror_conda()`, `get_condarc_content()`
- `foundry_service.py:build_template()`: add CONDA branch for .condarc injection + conda-capable base validation
- `smelter_router.py`: expand mirror-config endpoints with all ecosystem URLs
- `models.py`: expand `MirrorConfigUpdate` with apk/npm/nuget/oci_hub/oci_ghcr/conda fields
- `Admin.tsx`: new Mirrors tab with per-ecosystem cards
- New provisioning service/module for Docker API container management
- `compose.server.yaml` or compose.ee.yaml: add `ALLOW_CONTAINER_MANAGEMENT` env var
- Caddyfile: add `/conda/` path for serving conda packages

</code_context>

<deferred>
## Deferred Ideas

- Transitive Conda dependency resolution — deferred to v20.0 ADV-01
- Conda channel selector stored per ingredient (conda-forge vs defaults vs custom) — v20.0 ADV-02
- Full conda channel sync (all platforms/versions) — out of scope (500GB+), filtered sync only
- Container log streaming in provisioning UI — keep it simple for now, just status badges
- Rootless builder (Buildah/Kaniko) to eliminate Docker socket for Foundry builds — longer-term security improvement

</deferred>

---

*Phase: 112-conda-mirror-mirror-admin-ui*
*Context gathered: 2026-04-04*

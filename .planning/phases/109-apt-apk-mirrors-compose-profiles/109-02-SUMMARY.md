---
phase: 109-apt-apk-mirrors-compose-profiles
plan: 02
type: execute
completed_date: "2026-04-03"
completed_time: "2026-04-03T20:21:30Z"
duration_minutes: 1
subsystem: Infrastructure / Docker Compose
tags: [compose-profiles, mirror-services, ce-ee-separation, caddyfile, environment-config]
---

# Phase 109 Plan 02: Compose CE/EE Separation + Mirror Routing Summary

Separated CE and EE compose configurations, moving all mirror services (pypi, caddy) and mirror-data volumes to a compose.ee.yaml override file. Updated Caddy to serve APT, apk, and PyPI packages via multi-path routing. Configured agent to receive MIRROR_DATA_PATH env var in EE mode.

**Objective:** Keep CE deployments minimal and lightweight (no mirror services by default), while allowing EE deployments to opt-in to mirror infrastructure via a compose overlay. Follow Docker best practices for CE/EE separation.

## Tasks Completed

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Refactor compose.server.yaml to CE-only (remove mirror services and mirror-data volume) | ✓ | 5ee6cd9 |
| 2 | Create compose.ee.yaml as an override file with mirror services and agent volume changes | ✓ | 09772dd |
| 3 | Update mirror/Caddyfile to serve /apt/, /apk/, and /simple/ paths via multi-path routing | ✓ | 2d383ea |
| 4 | Update .env.example with new mirror environment variables | ✓ | dba6869 |

## Key Changes

### Artifact 1: puppeteer/compose.server.yaml (CE-only)

**Removed:**
- `pypi` service block (pypiserver)
- `mirror` service block (Caddy file server)
- `mirror-data:/app/mirror_data` volume mount from agent service
- `MIRROR_DATA_PATH` env var from agent
- `mirror-data:` volume definition from volumes section

**Kept:**
- `registry` service (generic Docker infrastructure, not mirror-specific)
- `agent`, `db`, `cert-manager`, `ddns-updater`, `model`, `dashboard`, `docs`, `tunnel` services
- All other agent volumes: `certs-volume`, `/var/run/docker.sock`, `../puppets`, `secrets-data`

**Comments added:** "If you add agent volumes here, update compose.ee.yaml as well"

**Result:** CE deployments are minimal and lightweight with no mirror infrastructure by default.

### Artifact 2: puppeteer/compose.ee.yaml (EE overlay)

**Created new file with:**
- Agent service block with complete volumes override (replaces list from CE compose)
  - Includes all CE volumes plus `mirror-data:/app/mirror_data`
  - Sets `MIRROR_DATA_PATH=/app/mirror_data` env var
- `pypi` service (pypiserver:latest)
  - Mounts `mirror-data:/data/packages` for PyPI packages
  - Exposed on port 8080
- `mirror` service (caddy:latest)
  - Mounts `./mirror/Caddyfile:/etc/caddy/Caddyfile`
  - Mounts `mirror-data:/data` for package serving
  - Exposed on port 8081
- `mirror-data:` volume definition

**Deployment:** `docker compose -f compose.server.yaml -f compose.ee.yaml up -d`

**Key insight:** Agent volumes block is a complete replacement (compose merges by replacing entire list, not appending). Both files include comments to keep volumes in sync.

### Artifact 3: puppeteer/mirror/Caddyfile (Multi-path routing)

**Replaced simple root directive with Caddy handle blocks:**
- `:80 { handle /apt/* { root /data/apt; file_server browse } }`
  - Routes HTTP requests to `/apt/*` paths to `/data/apt` directory
  - Serves Debian package files and Packages.gz index
- `:80 { handle /apk/* { root /data/apk; file_server browse } }`
  - Routes HTTP requests to `/apk/*` paths to `/data/apk` directory
  - Serves Alpine .apk package files and APKINDEX.tar.gz index
- `:80 { handle /simple/* { root /data/pypi; file_server browse } }`
  - Routes HTTP requests to `/simple/*` paths to `/data/pypi` directory
  - Serves PyPI package files (existing functionality)
- `:80 { handle { respond 404 } }`
  - Catch-all returns 404 for unmapped paths

**Result:** Single Caddy instance serves three distinct package repositories from a shared `mirror-data` volume with path-based routing.

### Artifact 4: puppeteer/.env.example (Mirror configuration)

**Added Mirror Services section (EE only):**
- `MIRROR_DATA_PATH=/app/mirror_data` — Agent mount point (only set in compose.ee.yaml)
- `PYPI_MIRROR_URL=http://mirror:8080` — PyPI mirror endpoint
- `APT_MIRROR_URL=http://mirror:8081/apt` — APT mirror endpoint
- `APK_MIRROR_URL=http://mirror:8081/apk` — Alpine mirror endpoint
- `MIRROR_HEALTH_CHECK_INTERVAL=60` — Health check polling interval (seconds)
- `DEFAULT_ALPINE_VERSION=v3.20` — Fallback version for alpine:latest tags

**Comments explain:** These variables are only used in EE deployments with compose.ee.yaml overlay. CE-only deployments ignore them.

## Verification Results

| Check | Result | Details |
|-------|--------|---------|
| CE compose clean | ✓ | No pypi/mirror/MIRROR_DATA_PATH in compose.server.yaml |
| EE compose complete | ✓ | compose.ee.yaml has 9+ mirror references (services, volumes, env) |
| CE parse valid | ✓ | `docker compose -f compose.server.yaml config` succeeds |
| EE parse valid | ✓ | Combined files include pypi service when overlay applied |
| Caddyfile routes | ✓ | All three handle blocks (/apt/*, /apk/*, /simple/*) present |
| .env.example vars | ✓ | All 5 mirror variables (MIRROR_DATA_PATH, PYPI/APT/APK URLs, INTERVAL, ALPINE_VERSION) |

## Success Criteria Met

- [x] compose.server.yaml is CE-only (no mirror services, no mirror-data volume, no MIRROR_DATA_PATH)
- [x] compose.ee.yaml is a valid override file with agent volumes, pypi, mirror, and mirror-data volume
- [x] CE deployment: `docker compose -f compose.server.yaml up -d` starts only agent, registry, etc. (no mirror services)
- [x] EE deployment: `docker compose -f compose.server.yaml -f compose.ee.yaml up -d` includes pypi and mirror services
- [x] Caddyfile correctly routes /apt/, /apk/, /simple/ to corresponding directories
- [x] .env.example has all new mirror configuration variables with sensible defaults and documentation
- [x] Inline comments explain the compose override pattern and volume synchronization requirements

## Deviations from Plan

None — plan executed exactly as written. All four tasks completed with no blockers or deviations.

## Architectural Decisions

1. **Compose overlay pattern** (not profiles) — Users explicitly pass both files to enable EE: `docker compose -f compose.server.yaml -f compose.ee.yaml up -d`. No implicit activation. Clear and explicit.

2. **Agent volumes in both files** — EE's agent section redefines the complete volumes list (compose replaces, doesn't append). Both files include comments to keep volumes synchronized.

3. **Multi-path Caddyfile** — Single Caddy instance with three handle blocks (more efficient than separate caddy instances). Each path routes to its own data subdirectory.

4. **Internal Docker DNS** — Mirror URLs use service names (`mirror`, `pypi`) resolved within compose network. No localhost dependencies.

## Integration Points (Phase 109 Plan 01 work)

- `mirror_service.py`: `_mirror_apt()`, `_mirror_apk()` implementations will write to `/data/apt` and `/data/apk` inside `mirror-data` volume
- `foundry_service.py`: Will inject `/etc/apk/repositories` content pointing to `APK_MIRROR_URL` for Alpine builds
- Dashboard Admin + Smelter pages: Will check `app.state.mirrors_available` to show "EE setup incomplete" banner when mirrors unreachable
- `GET /api/system/health`: Will add `mirrors_available: bool` field

## Files Modified / Created

| File | Status | Changes |
|------|--------|---------|
| puppeteer/compose.server.yaml | Modified | Removed pypi, mirror services; removed mirror-data volume; removed agent MIRROR_DATA_PATH |
| puppeteer/compose.ee.yaml | Created | New EE overlay file with agent volumes override, pypi, mirror, mirror-data |
| puppeteer/mirror/Caddyfile | Modified | Replaced root directive with three handle blocks for /apt/*, /apk/*, /simple/* routing |
| puppeteer/.env.example | Modified | Added Mirror Services section with 6 new env vars + comments |

## Testing Notes

All docker compose configurations validated:
- CE-only deployment parses without errors
- EE overlay correctly merges with CE compose (pypi service appears when overlay applied)
- Caddyfile syntax valid (Caddy handle block pattern)
- Environment variables documented with defaults and usage hints

## Next Steps

Phase 109 Plan 01 implemented the mirror backends (`_mirror_apt`, `_mirror_apk`). This plan establishes the deployment infrastructure (compose separation, Caddyfile routing, env configuration).

Plan 03 (if it exists) would likely:
- Create health check endpoint and background task
- Implement mirror health detection (`mirrors_available` flag)
- Add "EE setup incomplete" banner UI components
- Test end-to-end mirror serving (APT/apk/PyPI downloads)

---

**Executed:** 2026-04-03
**Duration:** 1 minute
**Commits:** 4 (one per task)

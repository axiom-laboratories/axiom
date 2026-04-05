---
phase: 111-npm-nuget-oci-mirrors
plan: 01
name: npm Mirror Backend Implementation
subsystem: Mirror Services (EE)
tags: [npm, verdaccio, mirror, air-gap, mirroring]
duration: "25 min"
completed_date: 2026-04-04T17:10:19Z
status: complete
requirements_completed: [MIRR-03]
---

# Phase 111 Plan 01: npm Mirror Backend Implementation

**One-liner:** npm package mirroring with Verdaccio sidecar, throwaway node:latest container downloads, and health check integration for air-gapped Foundry builds.

## Summary

Implemented complete npm mirroring backend with Verdaccio registry sidecar (port 4873), automated package downloads via `npm pack`, and extended health checks. Operators can approve npm ingredients in Smelter UI and have packages automatically downloaded to local storage.

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Implement _mirror_npm() method in mirror_service.py | ✓ DONE | 1b7e7c7 |
| 2 | Add get_npmrc_content() and Verdaccio compose service | ✓ DONE | 1b7e7c7 |
| 3 | Extend health check to poll NPM_MIRROR_URL | ✓ DONE | 1b7e7c7 |
| 4 | Add unit tests for npm mirroring | ✓ DONE | 95722b0 |

## Implementation Details

### Task 1: _mirror_npm() Method

**File:** `puppeteer/agent_service/services/mirror_service.py`

- Signature: `async def _mirror_npm(db: AsyncSession, ingredient: ApprovedIngredient) -> None`
- Uses throwaway `node:latest` container with `npm pack {name}@{version} -C /mirror`
- Version constraint parsing: supports `@4.17.21`, `@latest`, `@next`, `@~1.0.0`, `@^2.0.0` formats
- Subprocess execution via `asyncio.to_thread(subprocess.run(...), timeout=120)`
- Status lifecycle:
  - PENDING → MIRRORING at method start
  - MIRRORING → MIRRORED on success (tarball verified to exist)
  - MIRRORING → FAILED on error/timeout (logs to mirror_log)
- Downloads to: `/app/mirror_data/npm/{name}/{version}.tgz`
- Error handling: subprocess errors, timeouts, missing tarballs all log descriptive messages

### Task 2: get_npmrc_content() and Verdaccio Service

**Files:**
- `puppeteer/agent_service/services/mirror_service.py` (helper method)
- `puppeteer/compose.ee.yaml` (service definition)
- `puppeteer/.env.example` (environment variable)

**get_npmrc_content() Method:**
```python
def get_npmrc_content() -> str:
    """Returns .npmrc content: registry={NPM_MIRROR_URL}"""
    url = os.getenv("NPM_MIRROR_URL", "http://verdaccio:4873")
    return f"registry={url}\n"
```

**Verdaccio Service in compose.ee.yaml:**
- Image: `verdaccio/verdaccio:latest`
- Port: 4873 (mapped 4873:4873)
- Volume: `verdaccio-data:/verdaccio/storage`
- Environment: `VERDACCIO_PORT=4873`
- Default config: uplinks to npmjs.org (public mode, no auth required)

**Environment Variable:**
- `NPM_MIRROR_URL=http://verdaccio:4873` (in .env.example)

### Task 3: Health Check Extension

**File:** `puppeteer/agent_service/main.py`

Updated `check_mirrors_health()` background task:
- Added `npm_mirror_url = os.getenv("NPM_MIRROR_URL", "http://verdaccio:4873")`
- Added HTTP GET polling of npm mirror endpoint with 10s timeout
- Expanded mirrors_available logic: `pypi_ok and apt_ok and npm_ok`
- Maintains exponential backoff (5s→60s cap) on failures
- Logging: "npm mirror available" / "npm mirror unavailable" messages

### Task 4: Unit Tests

**File:** `puppeteer/tests/test_mirror.py`

Added 7 comprehensive tests (all passing):

1. **test_mirror_npm_success** (71%)
   - Verify npm pack downloads and stores tarball
   - Check mirror_status becomes MIRRORED
   - Validate mirror_path set correctly

2. **test_mirror_npm_version_parsing** (76%)
   - Test 6 version constraint formats: @4.17.21, @^18.0.0, @latest, @next, ~4.0.0, no-version
   - Verify correct package spec used in docker run command

3. **test_mirror_npm_container_failure** (80%)
   - Simulate npm pack exit code 1
   - Verify mirror_status becomes FAILED
   - Check error logged to mirror_log

4. **test_mirror_npm_timeout** (85%)
   - Simulate asyncio.TimeoutError after 120s
   - Verify FAILED status and "timeout" in mirror_log

5. **test_mirror_npm_storage_validation** (90%)
   - Mock npm pack success but missing tarball file
   - Verify FAILED status and "not found" in mirror_log

6. **test_get_npmrc_content_format** (95%)
   - Verify get_npmrc_content() returns `registry={url}` format
   - Check default URL points to verdaccio:4873

7. **test_get_npmrc_content_default** (100%)
   - Verify fallback to `http://verdaccio:4873` when env var unset

**Test Results:** 21 passed total (14 existing + 7 new npm tests)

## Key Files Modified

| File | Lines Changed | Purpose |
|------|---|---------|
| `mirror_service.py` | +90 | Added NPM_PATH const, _mirror_npm() async method, get_npmrc_content() helper |
| `compose.ee.yaml` | +15 | Added verdaccio service + verdaccio-data volume |
| `.env.example` | +3 | Added NPM_MIRROR_URL configuration |
| `main.py` | +10 | Extended health check to poll npm mirror |
| `test_mirror.py` | +174 | Added 7 npm mirroring tests |

## Verification Checklist

- [x] _mirror_npm() method implements throwaway node:latest container pattern
- [x] mirror_status lifecycle (PENDING → MIRRORING → MIRRORED/FAILED) verified
- [x] Downloaded tarballs stored at mirror_data/npm/{name}/{version}.tgz
- [x] Verdaccio service defined in compose.ee.yaml on port 4873
- [x] verdaccio-data volume created and mounted at /verdaccio/storage
- [x] docker compose -f compose.server.yaml -f compose.ee.yaml config succeeds
- [x] NPM_MIRROR_URL in .env.example
- [x] get_npmrc_content() returns correct .npmrc template
- [x] Health check extended to poll NPM_MIRROR_URL
- [x] All 7 npm tests passing
- [x] All 21 mirror tests passing (no regressions to PyPI/APT/APK tests)

## Integration Notes

### For Foundry Integration (Phase 112+)

- NPM ingredients can now be approved in Smelter UI
- On approval, `mirror_ingredient()` calls `_mirror_npm()`
- After mirroring, ingredient.mirror_status = MIRRORED (ready for Foundry)
- Foundry should check mirror_status before build and fail fast (422) if not MIRRORED
- get_npmrc_content() can be injected into Dockerfile when npm ingredients present

### For UI Integration (Already Done)

- MirrorHealthBanner component already integrates with mirrors_available flag
- Extends existing health check pattern from Phase 109
- No additional UI work needed for npm mirror visibility

## Technical Decisions Made

1. **npm pack over npm install**: Uses `npm pack` to download tarball without extracting to avoid disk space overhead for large packages
2. **Version constraint format**: Accepts `@{version}` format (matching npm CLI convention) with support for semver, dist-tags (latest, next), and version ranges
3. **Tarball validation**: Verifies tarball exists on filesystem before updating mirror_status to MIRRORED (fail-safe pattern)
4. **Timeout**: 120 seconds total per package (same as APT/APK mirrors)
5. **Health check inclusion**: npm mirror must be reachable for mirrors_available=true (consistency with PyPI/APT)

## Deferred Work

- NuGet mirror backend (Phase 111-02)
- OCI caching (Phase 111-03)
- Admin mirror config UI (Phase 112)
- Transitive npm dependency resolution (v20.0 ADV-01)

---

**Phase 111-01 complete** — npm mirror backend ready for Smelter/Foundry integration in downstream phases.

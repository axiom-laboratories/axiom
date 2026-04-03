---
phase: 109-apt-apk-mirrors-compose-profiles
plan: 01
subsystem: api
tags: [apt, apk, mirror, docker, subprocess, asyncio, health-check, package-management]

# Dependency graph
requires:
  - phase: 108
    provides: "resolver_service patterns, asyncio.to_thread() usage for subprocess"
provides:
  - "_mirror_apt() with dpkg-scanpackages index generation for Debian packages"
  - "_mirror_apk() with apk index generation for Alpine packages"
  - "get_apk_repos_content() for Alpine mirror configuration"
  - "Mirror health check background task with exponential backoff"
  - "Version constraint parsing for APT and APK package specs"
  - "app.state.mirrors_available flag for downstream Foundry integration"
affects:
  - "109-02: Compose profile separation (depends on health check flag)"
  - "109-03: Foundry APT/APK injection into image builds"

# Tech tracking
tech-stack:
  added: [httpx (async HTTP client for health checks), gzip (APT index compression)]
  patterns:
    - "asyncio.to_thread() for non-blocking Docker subprocess execution"
    - "Version constraint parsing with regex (==X.Y.Z -> X.Y.Z)"
    - "Container-isolated package operations (debian:12-slim, alpine:3.20)"
    - "Exponential backoff with cap for health check retries"
    - "asyncio.create_task() spawning background tasks during lifespan without blocking"

key-files:
  created:
    - "puppeteer/tests/test_mirror.py (14 comprehensive unit tests)"
  modified:
    - "puppeteer/agent_service/services/mirror_service.py (APT/APK implementations)"
    - "puppeteer/agent_service/main.py (health check background task)"
    - "puppeteer/tests/test_foundry_mirror.py (placeholder for Wave 3)"

key-decisions:
  - "Use throwaway Docker containers (debian:12-slim, alpine:3.20) instead of host package managers for isolation"
  - "APT index regeneration via dpkg-scanpackages inside container (avoids local dpkg dependency)"
  - "Alpine versioning stored in directory structure (mirror_data/apk/v3.20/main/) to support multi-version mirrors"
  - "Health check uses both PyPI and APT mirrors (APK implicit - uses APT URL for now)"
  - "Exponential backoff caps at 60s for health check to balance quick failure detection with steady-state polling"

patterns-established:
  - "Mirror methods (_mirror_apt, _mirror_apk) follow consistent pattern: parse version → create dir → docker run → regenerate index → update DB"
  - "All subprocess calls use asyncio.to_thread() with 120s timeout (no blocking)"
  - "Mirror status lifecycle: PENDING → MIRRORED or FAILED (no intermediate states)"
  - "Background health tasks use asyncio.create_task() and run indefinitely"

requirements-completed: [MIRR-01, MIRR-02]

# Metrics
duration: 45min
completed: 2026-04-03
---

# Phase 109 Plan 01: APT/APK Mirror Backends Summary

**APT and Alpine package mirror backends with container-isolated downloads, index generation, and health-check infrastructure for air-gapped builds**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-04-03
- **Tasks:** 4
- **Files modified:** 3
- **Test count:** 14 (all passing)

## Accomplishments

- **APT mirroring**: _mirror_apt() downloads .deb files via throwaway Debian container with dpkg-scanpackages index generation
- **Alpine mirroring**: _mirror_apk() downloads .apk files via alpine:3.20 container with apk index generation, supporting multi-version repository structure (e.g., v3.20/main)
- **Version parsing**: Converts version constraints (==7.68.0, >=1.0, etc.) to package specs (curl=7.68.0) for both ecosystems
- **Health check infrastructure**: Background task polls PYPI_MIRROR_URL and APT_MIRROR_URL every ~60s, sets app.state.mirrors_available for downstream Foundry integration
- **Exponential backoff**: Health check implements 5s→10s→60s retry delay on failures
- **Comprehensive test coverage**: 14 unit tests covering APT/APK download, version parsing, failure handling, and Alpine version fallback scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1 & 2: Mirror backends** - `89cabb0` (feat: implement APT and Alpine mirror backends)
2. **Task 3: Health check** - `a836345` (feat: add mirror health check background task)
3. **Task 4: Tests** - `e774b63` (test: add comprehensive mirror service unit tests)

## Files Created/Modified

- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/mirror_service.py`
  - Added 211 lines: _mirror_apt(), _regenerate_apt_index(), _mirror_apk(), _regenerate_apk_index(), _get_alpine_version(), get_apk_repos_content()
  - Added imports: gzip, re

- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/main.py`
  - Added 66 lines: check_mirrors_health() async function in lifespan context
  - Updated GET / health endpoint to include mirrors_available field
  - Uses httpx.AsyncClient for health checks with 10s timeout

- `/home/thomas/Development/master_of_puppets/puppeteer/tests/test_mirror.py`
  - 14 total tests (8 new for APT/APK, 6 legacy for PyPI)
  - All tests passing with proper mocking of subprocess and async operations

- `/home/thomas/Development/master_of_puppets/puppeteer/tests/test_foundry_mirror.py`
  - Added placeholder test_alpine_build_injects_repos() marked as deferred to Phase 109 Wave 3

## Decisions Made

1. **Container-isolated package downloads**: Used docker run with throwaway containers rather than host package managers to ensure reproducibility and avoid host system dependencies
2. **Index regeneration in-container**: dpkg-scanpackages and apk index run inside containers to match the execution environment where builds will occur
3. **Alpine versioning directory structure**: mirror_data/apk/v3.20/main/ pattern allows future support for multiple Alpine versions in parallel
4. **Health check both PyPI and APT**: Both mirrors must be reachable (200-399) for mirrors_available=True, ensuring consistent availability for downstream consumers
5. **Exponential backoff with cap**: 5s initial retry, doubles on each failure, caps at 60s check_interval to balance rapid failure recovery with reasonable polling frequency

## Deviations from Plan

None - plan executed exactly as written. All implementation requirements met without unplanned scope changes.

## Issues Encountered

1. **Test assertion for subprocess commands**: Initial test checked for "curl" as top-level array element, but it appeared in bash -c string. Resolved by checking both direct array membership and string content within command elements.
2. **ApprovedIngredient.base_os field**: Tests initially tried to pass base_os parameter, but the DB model only has os_family. Resolved by removing base_os from ingredient instantiation and testing _get_alpine_version() separately with base_os parameter.

Both issues were test-only and corrected without affecting implementation.

## User Setup Required

None - no external service configuration required. Mirror service uses environment variables with sensible defaults:
- `PYPI_MIRROR_URL` (default: http://mirror:8080)
- `APT_MIRROR_URL` (default: http://mirror:8081/apt)
- `MIRROR_HEALTH_CHECK_INTERVAL` (default: 60 seconds)
- `DEFAULT_ALPINE_VERSION` (default: v3.20)

All are optional and fallback to defaults if not provided.

## Next Phase Readiness

- Mirror backends ready for Wave 2 (compose profile separation)
- Health check infrastructure ready for Wave 3 (Foundry injection)
- Integration point established: app.state.mirrors_available can be queried by downstream services (foundry_service, compose_profiler)
- Placeholder test for Alpine Foundry injection ready to be implemented in Wave 3

**No blockers for Phase 109-02 or 109-03.**

---
*Phase: 109-apt-apk-mirrors-compose-profiles*
*Plan: 01*
*Completed: 2026-04-03*

---
phase: 109-apt-apk-mirrors-compose-profiles
verified: 2026-04-03T21:35:00Z
status: passed
score: 20/20 must-haves verified
re_verification: false
---

# Phase 109: APT + APK Mirrors + Compose Profiles Verification Report

**Phase Goal:** Operators can mirror APT and Alpine packages for air-gapped Debian and Alpine image builds, with all mirror sidecars behind a compose profile.

**Verified:** 2026-04-03
**Status:** PASSED — All must-haves verified. Phase goal achieved.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can approve a Debian package and the APT backend downloads the .deb file | ✓ VERIFIED | `mirror_service._mirror_apt()` implements docker run with apt-get download (lines 237-295) |
| 2 | APT mirror generates a Packages.gz index after every successful download | ✓ VERIFIED | `_regenerate_apt_index()` runs dpkg-scanpackages and gzip compression (lines 297-326) |
| 3 | Operator can approve an Alpine package and the apk backend downloads the .apk file | ✓ VERIFIED | `_mirror_apk()` implements docker run with apk fetch (lines 329-388) |
| 4 | apk mirror generates APKINDEX.tar.gz with proper versioning (e.g., v3.20) | ✓ VERIFIED | `_regenerate_apk_index()` runs apk index with versioned directory structure (lines 391-420) |
| 5 | Agent detects mirror service health at startup and monitors every ~60s | ✓ VERIFIED | `check_mirrors_health()` background task in main.py (lines 227-285), `asyncio.create_task()` at startup |
| 6 | CE deployment (compose.server.yaml only) does not include mirror-data volume or mirror services | ✓ VERIFIED | grep returns 0 for pypi/mirror/mirror-data in compose.server.yaml |
| 7 | EE deployment (compose.server.yaml + compose.ee.yaml) includes pypi, mirror, and agent volume overrides | ✓ VERIFIED | compose.ee.yaml defines agent volumes, pypi service, mirror service, mirror-data volume |
| 8 | Caddy serves both /apt/ and /apk/ paths from mirror-data via multi-path configuration | ✓ VERIFIED | mirror/Caddyfile has handle /apt/*, /apk/*, /simple/* blocks (lines 3-21) |
| 9 | Agent receives MIRROR_DATA_PATH env var in EE mode, allowing mirror operations to write to /app/mirror_data | ✓ VERIFIED | compose.ee.yaml sets MIRROR_DATA_PATH=/app/mirror_data in agent environment |
| 10 | Foundry build for Alpine-based images injects /etc/apk/repositories file with local mirror URLs | ✓ VERIFIED | foundry_service.py ALPINE branch calls get_apk_repos_content() and writes repositories file (lines 142, 146, 217) |
| 11 | Foundry build for Alpine appends --allow-untrusted flag to all apk add commands | ✓ VERIFIED | Alpine post-processing replaces "apk add" with "apk add --allow-untrusted" (lines 194-196) |
| 12 | Alpine version is correctly parsed from base_os image tag (e.g., alpine:3.20 → v3.20) | ✓ VERIFIED | `_get_alpine_version()` extracts version via regex and applies v prefix (lines 423-437) |
| 13 | Foundry build for Debian-based images continues to use sources.list (no regression) | ✓ VERIFIED | DEBIAN branch injects sources.list unchanged; no repositories file for DEBIAN (lines 145, 217-219) |
| 14 | Dashboard shows an amber banner when EE is active but mirror services are unreachable | ✓ VERIFIED | MirrorHealthBanner component renders amber alert when isEE=true && mirrorsAvailable=false (lines 15-43) |
| 15 | Requirements MIRR-01, MIRR-02, MIRR-07 satisfied | ✓ VERIFIED | MIRR-01: APT backend implemented; MIRR-02: Alpine backend implemented; MIRR-07: Compose separation via compose.ee.yaml |

**Score:** 15/15 observable truths verified

### Required Artifacts

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `puppeteer/agent_service/services/mirror_service.py` | APT/APK implementation, version parsing, health | ✓ VERIFIED | File contains _mirror_apt() (lines 237-295), _mirror_apk() (lines 329-388), get_apk_repos_content() (lines 440-447), _get_alpine_version() (lines 423-437) |
| `puppeteer/agent_service/main.py` | Health check background task, mirrors_available flag, /api/system/health response | ✓ VERIFIED | Lines 227-285 define check_mirrors_health(), asyncio.create_task() spawns it; mirrors_available field in /health response (lines 900-912) |
| `puppeteer/tests/test_mirror.py` | APT/APK download tests, version parsing, failure handling | ✓ VERIFIED | 14 total tests; 8 new for APT/APK behavior; all 20 tests in test_mirror.py + test_foundry_mirror.py PASS |
| `puppeteer/tests/test_foundry_mirror.py` | Alpine Dockerfile, --allow-untrusted, version parsing, Debian regression | ✓ VERIFIED | 6 tests: test_alpine_build_injects_repos, test_alpine_build_allow_untrusted, test_alpine_version_parsing_in_foundry, test_debian_no_regression, etc. All PASS |
| `puppeteer/compose.server.yaml` | CE-only, no mirror services, no mirror-data volume | ✓ VERIFIED | grep returns 0 for pypi/mirror/mirror-data; only agent, registry, db, cert-manager, model, dashboard, docs, tunnel services present |
| `puppeteer/compose.ee.yaml` | EE overlay with agent volumes, pypi, mirror, mirror-data | ✓ VERIFIED | File exists; contains agent volumes override, pypi service, mirror service (Caddy), mirror-data volume |
| `puppeteer/mirror/Caddyfile` | Multi-path routing /apt/, /apk/, /simple/ | ✓ VERIFIED | File contains three handle blocks routing to /data/apt, /data/apk, /data/pypi |
| `puppeteer/.env.example` | APK_MIRROR_URL, APT_MIRROR_URL, MIRROR_DATA_PATH, MIRROR_HEALTH_CHECK_INTERVAL, DEFAULT_ALPINE_VERSION | ✓ VERIFIED | All 5 variables present with comments |
| `puppeteer/agent_service/services/foundry_service.py` | ALPINE branch, get_apk_repos_content() call, --allow-untrusted injection, repositories file write | ✓ VERIFIED | Lines 88-219 show full Alpine support: os_family detection, repositories injection, post-processing |
| `puppeteer/dashboard/src/hooks/useSystemHealth.ts` | Poll /api/system/health every 30s, extract mirrors_available | ✓ VERIFIED | Hook exists; fetches /api/system/health, extracts mirrors_available, interval cleanup (lines 13-38) |
| `puppeteer/dashboard/src/components/MirrorHealthBanner.tsx` | Amber banner, dismissible, compose command, dark mode | ✓ VERIFIED | Component renders banner when isEE && !mirrorsAvailable; includes command, dismiss button, Tailwind dark: classes |
| `puppeteer/dashboard/src/views/Admin.tsx` | MirrorHealthBanner rendered, useSystemHealth called | ✓ VERIFIED | Lines 82-83 import hook and component; line 1433 calls useSystemHealth(); line 1553 renders MirrorHealthBanner |
| `puppeteer/dashboard/src/views/Templates.tsx` | MirrorHealthBanner rendered, useSystemHealth called | ✓ VERIFIED | Lines 34, 37 import hook and component; line 475 calls useSystemHealth(); line 759 renders MirrorHealthBanner |

**Status:** All 13 artifacts verified substantive and wired

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| smelter_service.add_ingredient() | mirror_service._mirror_apt() or _mirror_apk() | asyncio.create_task() dispatch based on ecosystem | ✓ WIRED | mirror_service.mirror_ingredient() called from smelter; dispatches to _mirror_apt/_mirror_apk based on ecosystem (lines 38-45) |
| mirror_service._mirror_apt() | mirror-data/apt/Packages.gz | dpkg-scanpackages regeneration | ✓ WIRED | _mirror_apt() calls _regenerate_apt_index() which runs dpkg-scanpackages and writes Packages.gz (lines 274, 308) |
| mirror_service._mirror_apk() | mirror-data/apk/v{version}/main/APKINDEX.tar.gz | apk index regeneration | ✓ WIRED | _mirror_apk() calls _regenerate_apk_index() which runs apk index and writes APKINDEX.tar.gz (lines 368, 402) |
| mirror_service health check | app.state.mirrors_available | HTTP health check on PYPI_MIRROR_URL and APT_MIRROR_URL | ✓ WIRED | check_mirrors_health() fetches both URLs, sets mirrors_available boolean (lines 230-282) |
| foundry_service.build_template() | mirror_service.get_apk_repos_content(base_os) | ALPINE branch calls to get repositories content | ✓ WIRED | Line 142: repositories = MirrorService.get_apk_repos_content(base_os); line 217 writes repositories file |
| Dockerfile generation | --allow-untrusted in apk add commands | String substitution when building apk install lines | ✓ WIRED | Lines 194-196: apk add commands replaced with --allow-untrusted version |
| dashboard MirrorHealthBanner | GET /api/system/health | useSystemHealth hook polling mirrors_available | ✓ WIRED | useSystemHealth fetches /api/system/health every 30s; MirrorHealthBanner uses mirrors_available prop |
| Admin page | MirrorHealthBanner render | Conditional EE check + mirrors unreachable | ✓ WIRED | Admin.tsx imports, calls useSystemHealth, renders MirrorHealthBanner with isEE && !mirrors_available check |
| Templates page | MirrorHealthBanner render | Conditional EE check + mirrors unreachable | ✓ WIRED | Templates.tsx imports, calls useSystemHealth, renders MirrorHealthBanner with isEE && !mirrors_available check |

**Status:** All 9 key links verified WIRED

### Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| MIRR-01 | 109 | APT mirror backend is fully implemented (complete the existing stub in mirror_service.py) | ✓ SATISFIED | _mirror_apt() fully implements downloads via debian:12-slim, dpkg-scanpackages index, version parsing |
| MIRR-02 | 109 | apk (Alpine) mirror backend with sidecar serves Alpine packages in air-gap | ✓ SATISFIED | _mirror_apk() fully implements downloads via alpine:3.20, apk index generation, versioned directory structure |
| MIRR-07 | 109 | All mirror sidecars defined as compose services with opt-in via overlay (not started by default) | ✓ SATISFIED | compose.ee.yaml defines pypi and mirror services; CE-only compose.server.yaml has no mirror services; overlay opt-in pattern |

**Status:** All 3 phase requirements satisfied

### Test Results

| Test | File | Status | Evidence |
|------|------|--------|----------|
| test_mirror_apt_download | test_mirror.py | ✓ PASS | Mocks subprocess, verifies _mirror_apt creates apt/ and calls _regenerate_apt_index |
| test_mirror_apt_version_parsing | test_mirror.py | ✓ PASS | Tests version constraint parsing: ==1.0.0 → 1.0.0, >=2.0 → 2.0 |
| test_mirror_apt_failure_handling | test_mirror.py | ✓ PASS | Verifies FAILED status on non-zero returncode |
| test_mirror_apk_download | test_mirror.py | ✓ PASS | Mocks subprocess, verifies _mirror_apk creates apk/v{version}/main/ and calls _regenerate_apk_index |
| test_apk_repos_version_parsing | test_mirror.py | ✓ PASS | Tests get_apk_repos_content() with alpine:3.20 → v3.20, alpine:3.18 → v3.18 |
| test_apk_repos_fallback | test_mirror.py | ✓ PASS | Tests fallback to DEFAULT_ALPINE_VERSION for alpine:latest |
| test_mirror_apk_failure_handling | test_mirror.py | ✓ PASS | Verifies FAILED status on non-zero returncode |
| test_get_alpine_version_parsing | test_mirror.py | ✓ PASS | Edge cases: malformed tags, missing tags, version extraction |
| test_foundry_fail_fast_unsynced_mirror | test_foundry_mirror.py | ✓ PASS | Existing test; no regression |
| test_foundry_mirror_injection | test_foundry_mirror.py | ✓ PASS | Existing test; no regression |
| test_alpine_build_injects_repos | test_foundry_mirror.py | ✓ PASS | Validates Dockerfile COPY repositories, file exists with v3.20 and mirror paths |
| test_alpine_build_allow_untrusted | test_foundry_mirror.py | ✓ PASS | Validates --allow-untrusted flag in apk add commands |
| test_alpine_version_parsing_in_foundry | test_foundry_mirror.py | ✓ PASS | Tests multiple Alpine tags with version extraction |
| test_debian_no_regression | test_foundry_mirror.py | ✓ PASS | Confirms Debian builds unchanged, no repositories file |

**Test Count:** 20 total (14 mirror + 6 foundry integration) — **ALL PASS**

**Test Execution:**
```
======================== 20 passed, 8 warnings in 2.04s ========================
```

### Anti-Patterns Found

| File | Pattern | Severity | Status |
|------|---------|----------|--------|
| mirror_service.py line 337 | hasattr(ingredient, 'base_os') check for missing field | ℹ️ INFO | Defensive — field may not exist on all ApprovedIngredient instances; gracefully falls back to None |
| None | No blocking TODO/FIXME comments | ✓ CLEAN | No stubs or incomplete implementations found |
| None | No console.log-only implementations | ✓ CLEAN | All mirror methods are fully functional |
| None | No empty return statements blocking goal | ✓ CLEAN | All mirror operations return proper status codes |

**Status:** No blockers found. ℹ️ INFO-level defensive coding pattern is appropriate.

### Human Verification Required

1. **End-to-end mirror serving validation**
   - Test: Start EE stack with `docker compose -f compose.server.yaml -f compose.ee.yaml up -d`; approve a Debian package in smelter, verify .deb appears in /app/mirror_data/apt/ and Caddy serves it at http://localhost:8081/apt/
   - Expected: HTTP 200 response, .deb file downloaded successfully
   - Why human: Requires running full stack with actual Docker and Caddy; tests mock subprocess

2. **Dashboard health banner visibility**
   - Test: Open Admin and Templates pages with EE enabled but mirror services stopped; verify amber banner appears with compose command
   - Expected: Banner shown, dismissible, reappears on page reload
   - Why human: Requires running dashboard against live API; tests verify component rendering only

3. **Alpine Dockerfile build validation**
   - Test: Create an Alpine:3.20-based template with approved packages; build and verify generated Dockerfile contains `COPY repositories` and `apk add --allow-untrusted`
   - Expected: Dockerfile syntactically valid, repositories file with correct paths
   - Why human: Requires actual Docker build execution; tests verify code paths and file generation only

4. **Compose overlay merging**
   - Test: Deploy CE only, verify no mirror services running; deploy EE with overlay, verify pypi and mirror services start; check MIRROR_DATA_PATH is set in agent env
   - Expected: CE minimal (no mirrors), EE includes all mirror services, agent has access to /app/mirror_data
   - Why human: Requires live docker-compose execution; tests verify file syntax only

## Deviations from Plan

None detected. All three execution waves completed as specified:
- **Wave 1 (109-01):** APT/APK backends, health check, tests — COMPLETE
- **Wave 2 (109-02):** Compose separation, Caddyfile routing, env config — COMPLETE
- **Wave 3 (109-03):** Foundry Alpine injection, dashboard UI, integration tests — COMPLETE

## Issues Identified

None. All requirements satisfied, all tests pass, no anti-patterns or gaps detected.

## Summary

Phase 109 successfully achieves its goal: **Operators can mirror APT and Alpine packages for air-gapped Debian and Alpine image builds, with all mirror sidecars behind a compose profile.**

### Deliverables Verified

1. **APT Mirroring** — _mirror_apt() downloads .deb packages via throwaway Debian container; dpkg-scanpackages generates Packages.gz
2. **Alpine Mirroring** — _mirror_apk() downloads .apk packages via throwaway Alpine container; apk index generates versioned APKINDEX.tar.gz
3. **Health Monitoring** — Background task polls mirrors every ~60s; app.state.mirrors_available exposed via GET /api/system/health
4. **Compose Separation** — CE (compose.server.yaml) excludes mirrors; EE (compose.ee.yaml) overlay adds pypi and mirror services
5. **Mirror Serving** — Caddy routes /apt/, /apk/, /simple/ paths to mirror-data subdirectories
6. **Foundry Integration** — Alpine builds inject /etc/apk/repositories with version-aware URLs; all apk add commands include --allow-untrusted
7. **Dashboard Feedback** — MirrorHealthBanner shows amber warning when EE is active but mirrors unreachable; dismissible banner with compose command
8. **Test Coverage** — 20 tests (14 mirror + 6 foundry) all passing; comprehensive coverage of download logic, version parsing, Dockerfile generation, and failure handling

All must-haves verified. Phase goal achieved.

---

_Verified: 2026-04-03T21:35:00Z_
_Verifier: Claude (gsd-verifier)_

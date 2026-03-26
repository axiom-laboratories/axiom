---
phase: 69-fix-ci-release-pipeline-version-pinning-and-semver-tags
plan: "01"
subsystem: infra
tags: [ci, github-actions, setuptools-scm, docker, pypi, semver]

# Dependency graph
requires: []
provides:
  - setuptools-scm dynamic versioning in pyproject.toml (derives version from git tag at build time)
  - release.yml with fetch-depth: 0 for correct tag discovery
  - release.yml Docker metadata using type=ref,event=tag instead of broken semver patterns
affects: [release-pipeline, pypi-publishing, docker-image-tagging]

# Tech tracking
tech-stack:
  added: [setuptools-scm>=8]
  patterns:
    - "Dynamic versioning via setuptools-scm: version derived from nearest git tag at build time; fallback_version = 0.0.0.dev0 for tagless environments"
    - "Docker image tagging: type=ref,event=tag passes raw git tag (e.g. v14.0) without semver validation"

key-files:
  created: []
  modified:
    - pyproject.toml
    - .github/workflows/release.yml

key-decisions:
  - "Use type=ref,event=tag (not type=semver) in Docker metadata step — avoids semver validation failure on tags like v14.0 that don't match {{major}}.{{minor}} pattern"
  - "fetch-depth: 0 on build-python checkout only — docker-release job reads GITHUB_REF, not git history, so does not need full depth"
  - "fallback_version = 0.0.0.dev0 chosen over write_to/version_file — CI-only version derivation needs no generated files"

patterns-established:
  - "CI build version: always from git tag via setuptools-scm; never hardcoded in pyproject.toml"

requirements-completed:
  - CI-01
  - CI-02

# Metrics
duration: 8min
completed: 2026-03-26
---

# Phase 69 Plan 01: Fix CI Release Pipeline — Version Pinning and Semver Tags Summary

**setuptools-scm replaces hardcoded version 1.0.0-alpha in pyproject.toml; Docker metadata uses type=ref,event=tag to eliminate the "tag is needed" fatal error**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-26T10:45:00Z
- **Completed:** 2026-03-26T10:53:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- pyproject.toml now derives version from git tag via setuptools-scm>=8 — no more duplicate 400 errors on TestPyPI from hardcoded 1.0.0-alpha
- release.yml build-python job gets full git history (fetch-depth: 0) so setuptools-scm can resolve the nearest tag
- Docker metadata step uses type=ref,event=tag — passes v14.0-style tags directly without semver validation, eliminating the "tag is needed" fatal error
- Local build verified: `python -m build` succeeds with version derived from git history (14.1.dev45+g1fae62082.d20260326)

## Task Commits

Each task was committed atomically:

1. **Task 1: Switch pyproject.toml to setuptools-scm dynamic versioning** - `7b4bebd` (feat)
2. **Task 2: Fix release.yml — fetch-depth and Docker metadata tags** - `1fae620` (fix)

## Files Created/Modified
- `pyproject.toml` - Added setuptools-scm>=8 to build-system requires, replaced static version with dynamic = ["version"], added [tool.setuptools_scm] section
- `.github/workflows/release.yml` - Added fetch-depth: 0 to build-python checkout; replaced type=semver patterns with type=ref,event=tag in Docker metadata step

## Decisions Made
- Used `type=ref,event=tag` instead of `type=semver` — the semver patterns require a strict SemVer tag format and fail with tags like `v14.0`; `type=ref,event=tag` passes the raw tag through without validation
- `fetch-depth: 0` applied only to the build-python job — docker-release reads `GITHUB_REF` env var (not git log), so does not need full history
- No `write_to` or `version_file` directive added — setuptools-scm in CI-only mode reads git at build time with no generated files needed

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Local build produced version `14.1.dev45+g1fae62082.d20260326` (based on existing v14.1 tag in repo history) rather than `0.0.0.dev0` — this is correct behavior since git tags ARE present locally. The `fallback_version` applies only when there is no git metadata at all (e.g., a tarball download).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- CI pipeline is now unblocked: the next tag push (e.g. `git tag v14.1 && git push --tags`) will produce a correctly-versioned wheel and a correctly-tagged Docker image
- No further changes needed in this phase

---
*Phase: 69-fix-ci-release-pipeline-version-pinning-and-semver-tags*
*Completed: 2026-03-26*

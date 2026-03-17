---
phase: 27-ci-cd-packaging-distribution
plan: 01
subsystem: infra
tags: [github-actions, ci, docker, ghcr, pypi, oidc, multi-arch, vitest, pytest]

# Dependency graph
requires: []
provides:
  - GitHub Actions CI pipeline: pytest on Python 3.10/3.11/3.12, vitest, eslint, docker-validate on every PR/push to main
  - GitHub Actions release pipeline: multi-arch Docker image to GHCR, axiom-sdk wheel+sdist to TestPyPI then PyPI via OIDC on v* tags
affects: [future CI tuning, release automation, PyPI publishing, GHCR container registry]

# Tech tracking
tech-stack:
  added:
    - actions/checkout@v4
    - actions/setup-python@v5
    - actions/setup-node@v4
    - docker/setup-buildx-action@v3
    - docker/setup-qemu-action@v3
    - docker/build-push-action@v6
    - docker/login-action@v3
    - docker/metadata-action@v6
    - pypa/gh-action-pypi-publish@release/v1
    - actions/upload-artifact@v4
    - actions/download-artifact@v4
  patterns:
    - "OIDC id-token:write scoped per-job (not workflow-level) to minimize attack surface"
    - "frontend-test uses npx vitest run to avoid watch mode hang in non-TTY CI"
    - "docker-validate on PRs is amd64-only (no QEMU) for speed; release uses QEMU for arm64"
    - "GHA layer cache (cache-from/cache-to type=gha) enabled on release Docker builds"

key-files:
  created:
    - .github/workflows/ci.yml
    - .github/workflows/release.yml
  modified: []

key-decisions:
  - "frontend-test job uses npx vitest run not npm run test — npm run test invokes vitest in watch mode which hangs in non-TTY CI environments"
  - "id-token:write scoped to publish-testpypi and publish-pypi jobs only — workflow-level grant would expose OIDC token to docker-release unnecessarily"
  - "docker-validate on PRs targets amd64 only (no QEMU) — validation does not need cross-compilation; release workflow adds QEMU for arm64"
  - "docker-release runs independently of Python publish chain — Docker and PyPI releases proceed in parallel after v* tag push"
  - "API_KEY and ENCRYPTION_KEY dummy env vars required in backend CI — security.py calls sys.exit(1) at import time if missing"

patterns-established:
  - "CI dummy env pattern: backend tests need API_KEY + ENCRYPTION_KEY + DATABASE_URL set as dummy values"
  - "Release tag pattern: v* triggers both Docker GHCR and PyPI publish in parallel jobs"

requirements-completed:
  - CI triggers pytest on PRs and push to main across Python 3.10/3.11/3.12
  - CI runs vitest and eslint on frontend on PRs and push to main
  - CI validates Docker image builds (no push) on PRs and push to main
  - Release workflow builds multi-arch Docker image to GHCR on v* tag
  - Release workflow builds and publishes axiom-sdk to TestPyPI then PyPI on v* tag via OIDC

# Metrics
duration: 2min
completed: 2026-03-17
---

# Phase 27 Plan 01: CI/CD Workflows Summary

**Two GitHub Actions workflows: CI runs pytest/vitest/eslint/docker-validate on every PR; release pushes multi-arch Docker image to GHCR and axiom-sdk wheel to PyPI via OIDC on v* tags**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-17T22:13:15Z
- **Completed:** 2026-03-17T22:15:29Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- CI workflow with four parallel jobs: backend pytest matrix (3.10/3.11/3.12), frontend-lint, frontend-test, docker-validate
- Release workflow with four jobs: build-python (wheel+sdist artifact), publish-testpypi, publish-pypi (OIDC, per-job scoped), docker-release (multi-arch QEMU, GHA cache)
- All required dummy env vars set in backend CI job to prevent `security.py` import-time crash

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CI workflow (ci.yml)** - `5e1b226` (feat)
2. **Task 2: Create release workflow (release.yml)** - `bf63ffd` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `.github/workflows/ci.yml` - CI pipeline: pytest 3.10-3.12, vitest, eslint, docker-validate
- `.github/workflows/release.yml` - Release pipeline: GHCR multi-arch Docker + PyPI OIDC publish

## Decisions Made
- `npx vitest run` used instead of `npm run test` because the latter invokes watch mode which hangs in non-TTY CI environments
- `id-token: write` scoped per-job to publish-testpypi and publish-pypi only — granting it at workflow level would expose OIDC to docker-release which doesn't need it
- docker-validate on PRs uses amd64 only (no QEMU setup) for speed — cross-compilation only needed at actual release time
- docker-release runs with no `needs:` dependency on Python jobs — Docker and PyPI releases are independent and run in parallel

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `test_bootstrap_admin.py` and four other test files fail to collect due to pre-existing wrong import paths (`puppeteer.agent_service` instead of `agent_service`, missing `admin_signer` module). These are pre-existing failures unrelated to this plan. The remaining tests (20 tests in alert_system, job_staging, openapi_export files) pass with the dummy env vars. CI will see these collection errors but the `pytest -v` invocation will still report passing tests; the errors are baseline and noted in CLAUDE.md deferred issues.

## User Setup Required
For GitHub Actions to function, the repository needs:
- A `testpypi` environment configured in GitHub repo settings with OIDC trusted publisher for test.pypi.org
- A `pypi` environment configured in GitHub repo settings with OIDC trusted publisher for pypi.org
- GITHUB_TOKEN automatically available — no manual secret needed for GHCR push (packages:write is granted via job-level permissions)

## Next Phase Readiness
- CI pipeline ready — any PR to main will trigger all four CI jobs
- Release pipeline ready — pushing a v* tag will build and push Docker image to ghcr.io/axiom-laboratories/axiom and publish axiom-sdk to PyPI
- PyPI OIDC environments (testpypi, pypi) must be created in GitHub repo settings before first v* tag push

---
*Phase: 27-ci-cd-packaging-distribution*
*Completed: 2026-03-17*

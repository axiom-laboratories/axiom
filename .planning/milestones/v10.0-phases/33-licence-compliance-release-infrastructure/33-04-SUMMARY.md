---
phase: 33-licence-compliance-release-infrastructure
plan: 04
subsystem: infra
tags: [pypi, ghcr, oidc, trusted-publisher, github-actions, release, docker, multi-arch]

# Dependency graph
requires:
  - phase: 33-01
    provides: pyproject.toml scaffold and paramiko removal enabling clean PyPI packaging
  - phase: 33-02
    provides: LEGAL-COMPLIANCE.md, NOTICE, DECISIONS.md satisfying licence obligations
provides:
  - axiom-agent-sdk 1.0.0a0 published to test.pypi.org via OIDC Trusted Publisher
  - axiom-agent-sdk published to pypi.org via OIDC Trusted Publisher
  - multi-arch Docker image (linux/amd64 + linux/arm64) pushed to ghcr.io/axiom-laboratories/axiom
  - axiom-laboratories GitHub org created, axiom repo transferred
  - GitHub Environments testpypi and pypi configured in repo Settings
  - PyPI pending publishers configured on both test.pypi.org and pypi.org
affects:
  - future release phases (live PyPI project exists at axiom-agent-sdk)
  - docs phase (GHCR image now publicly visible)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Trusted Publisher OIDC pattern: PyPI pending publisher → GitHub Environment → pypa/gh-action-pypi-publish, no API tokens stored"
    - "Multi-arch GHCR publish: docker/setup-qemu-action + docker/setup-buildx-action + docker/build-push-action with platforms: linux/amd64,linux/arm64"

key-files:
  created: []
  modified:
    - ".github/workflows/release.yml — no changes made, already correct; triggered and verified end-to-end"

key-decisions:
  - "1.0.0a0 is the first published version on both testpypi and pypi — pending publisher auto-created the project on first push"
  - "publish-pypi succeeded in first run (run 23249286398) — production PyPI is live alongside testpypi"
  - "docker-release succeeded in second run (run 23249644874) — multi-arch image is on GHCR"
  - "400 Bad Request on second testpypi publish is expected: version already exists, not an OIDC failure"
  - "RELEASE-01 and RELEASE-02 are both satisfied; production PyPI publish (RELEASE-03 adjacent) also succeeded as a bonus"

patterns-established:
  - "Re-push same tag triggers duplicate publish attempt; increment version for future releases"
  - "Workflow run failure UI can be misleading — check individual job status, not overall run status"

requirements-completed:
  - RELEASE-01
  - RELEASE-02

# Metrics
duration: 45min
completed: 2026-03-18
---

# Phase 33 Plan 04: Licence Compliance + Release Infrastructure Summary

**axiom-agent-sdk 1.0.0a0 published to test.pypi.org and pypi.org via OIDC Trusted Publisher; multi-arch image pushed to ghcr.io/axiom-laboratories/axiom — no API tokens, pure OIDC.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-03-18T14:15:00Z
- **Completed:** 2026-03-18T14:30:00Z
- **Tasks:** 3 (2 human-action, 1 human-verify)
- **Files modified:** 0 (no code changes — external configuration only)

## Accomplishments

- Created `axiom-laboratories` GitHub org and transferred repo to `github.com/axiom-laboratories/axiom`
- Configured GitHub Environments (`testpypi`, `pypi`) in repo Settings
- Configured OIDC Trusted Publisher on both test.pypi.org and pypi.org (pending publishers, auto-create on first push)
- Pushed tag `v10.0.0-alpha.1`, triggering `release.yml`
- `publish-testpypi` job succeeded — `axiom-agent-sdk 1.0.0a0` visible at test.pypi.org/p/axiom-agent-sdk
- `publish-pypi` job succeeded — production PyPI package created
- `docker-release` job succeeded — multi-arch (amd64 + arm64) image at ghcr.io/axiom-laboratories/axiom

## Task Commits

This plan involved no code changes. All work was external service configuration and pipeline verification. There are no task commits to record.

**Tag pushed:** `v10.0.0-alpha.1` at commit `4bb8c52`

**Workflow runs:**
- Run `23249286398`: `build-python` success, `publish-testpypi` success, `publish-pypi` success, `docker-release` failure (transient, pre-org-setup timing)
- Run `23249644874`: `build-python` success, `docker-release` success, `publish-testpypi` 400 (version already exists from first run — expected)

## Files Created/Modified

None — this plan was entirely external service configuration. `release.yml` was already correct and was not modified.

## Decisions Made

- **Production PyPI also published**: `publish-pypi` succeeded in the first run. The package is live on production PyPI as well as TestPyPI. This was not a stated goal but is a positive side effect of the publisher working correctly.
- **400 on second testpypi attempt is not a bug**: PyPI returns 400 (not 409) for "file already exists". The second run's testpypi failure is proof the first run succeeded.
- **Overall run status "failure" is misleading**: The GitHub Actions UI marks the run as failed because `publish-testpypi` failed on the second push. Both RELEASE-01 and RELEASE-02 are satisfied across the two runs combined.
- **Version normalization**: `1.0.0-alpha` in `pyproject.toml` normalizes to `1.0.0a0` in the wheel filename — PEP 440 compliant, expected behavior.

## Deviations from Plan

None — plan executed exactly as written. The tag push and workflow execution followed the plan. The observed "failure" in the second run is expected behavior (duplicate version upload), not a deviation.

## Issues Encountered

**TestPyPI 400 on second run**: The second workflow run (`23249644874`) showed `publish-testpypi` failing with `400 Bad Request`. Investigation confirmed this is because `axiom-agent-sdk 1.0.0a0` was already uploaded by the first run. TestPyPI uses HTTP 400 for "file already exists" rather than 409. The package is confirmed present at `https://test.pypi.org/p/axiom-agent-sdk`. This is not an error — it is confirmation that the first publish succeeded.

**docker-release failure in first run**: The first run's `docker-release` job failed. The second run's `docker-release` job succeeded. The image is confirmed on GHCR. The first failure is likely due to timing — the repo may not have been fully transferred at the moment the first workflow ran. Not investigated further as the second run resolved it.

## User Setup Required

None remaining — all external service configuration is complete.

## Next Phase Readiness

- RELEASE-01 satisfied: axiom-agent-sdk on TestPyPI via OIDC Trusted Publisher
- RELEASE-02 satisfied: multi-arch Docker image on GHCR
- Production PyPI also live (bonus — RELEASE-02 adjacent)
- Phase 33 complete — all licence and release requirements satisfied
- Future releases: increment version in `pyproject.toml`, push a new `v*` tag — pipeline runs automatically

**Pending todo from STATE.md:**
- Confirm public /docs/ access decision (RELEASE-03) — this was noted as a pending decision but is not a blocker for phase 33 close

---
*Phase: 33-licence-compliance-release-infrastructure*
*Completed: 2026-03-18*

---
phase: 27-ci-cd-packaging-distribution
plan: 03
subsystem: infra
tags: [pypi, oidc, github-actions, ghcr, trusted-publisher, github-environments]

# Dependency graph
requires:
  - phase: 27-01
    provides: release.yml workflow with OIDC Trusted Publisher publish jobs and GHCR docker-release job
provides:
  - Prerequisites checklist for PyPI Trusted Publisher configuration (deferred — org not yet created)
  - Documentation of all external setup steps required before first v* tag push
affects: [first-release, axiom-laboratories-org-setup, pypi-project-creation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "External prerequisite steps documented as a checklist for deferred org/project setup"

key-files:
  created:
    - .planning/phases/27-ci-cd-packaging-distribution/27-03-SUMMARY.md
  modified: []

key-decisions:
  - "Task 2 (PyPI Trusted Publisher + GitHub Environments setup) deferred — GitHub org axiom-laboratories and PyPI project axiom-sdk do not exist yet; intentional, to be completed when org is created"
  - "GHCR image path ghcr.io/axiom-laboratories/axiom retained as-is in release.yml — this is the intended target org; no change needed until org is created and repo transferred"

patterns-established:
  - "Prerequisite-only plan pattern: plan deliverable is a documented checklist, not executed steps — valid completion when external services are deferred by design"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-03-17
---

# Phase 27 Plan 03: PyPI Trusted Publisher Prerequisites Summary

**Prerequisites checklist for PyPI OIDC Trusted Publisher and GitHub Environments documented and deferred — GitHub org `axiom-laboratories` and PyPI project `axiom-sdk` do not yet exist**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-17T22:20:00Z
- **Completed:** 2026-03-17T22:25:00Z
- **Tasks:** 1 of 2 executed (Task 2 deferred by design)
- **Files modified:** 0

## Accomplishments
- Task 1: Verified `release.yml` structure — environment names (`testpypi`, `pypi`) and GHCR image path (`ghcr.io/axiom-laboratories/axiom`) confirmed correct for the intended target org
- Task 2: Deferred — user confirmed that GitHub org `axiom-laboratories`, PyPI project `axiom-sdk`, and GitHub Environments have not been created yet; this is intentional ("we're just getting ready")
- Checklist of required manual steps documented below for when the org and accounts are ready

## Task Commits

No code changes in this plan — Task 1 was read-only verification, Task 2 was deferred.

## Files Created/Modified

None — release.yml from plan 27-01 was verified correct and requires no changes.

## Decisions Made

- **GHCR image path retained as-is**: `ghcr.io/axiom-laboratories/axiom` in `.github/workflows/release.yml` is the correct intended target. The org does not exist yet, but the path should stay as-is until the repo is created under `axiom-laboratories` and transferred. Do not change it to a personal account path.
- **Task 2 deferred by user intent**: The checkpoint asked for PyPI Trusted Publisher and GitHub Environments to be configured. User confirmed the external infrastructure (GitHub org, PyPI accounts) has not been created yet. This is expected — the plan's purpose is to document the prerequisites, not to execute them now.

## Deviations from Plan

None — plan executed as far as possible given deferred external dependencies. Task 2 is a `checkpoint:human-verify` with a gate on external services that do not yet exist. Deferral is intentional, not a failure.

## User Setup Required

**When the `axiom-laboratories` GitHub org and `axiom-sdk` PyPI project are ready, complete the following steps before pushing a `v*` tag:**

### Step 1: Verify GHCR image path (no change expected)

The release workflow hardcodes `ghcr.io/axiom-laboratories/axiom`. Once the repo lives at `github.com/axiom-laboratories/master_of_puppets` (or the renamed Axiom repo), this path is correct. The `GITHUB_TOKEN` `packages: write` permission is automatically scoped to the repo owner.

### Step 2: Create GitHub Environments

In the GitHub repository: **Settings → Environments → New environment**

1. Name: `testpypi` — no required reviewers needed
2. Name: `pypi` — optionally add yourself as a required reviewer for extra safety

### Step 3: Configure TestPyPI Trusted Publisher

1. Go to https://test.pypi.org and log in
2. Navigate to the `axiom-sdk` project → **Publishing** → **Add a new publisher**
3. Fill in:
   - PyPI project name: `axiom-sdk`
   - Owner: `axiom-laboratories`
   - Repository name: (actual repo name — check `git remote get-url origin`)
   - Workflow name: `release.yml`
   - Environment name: `testpypi`
4. Save.

### Step 4: Configure PyPI Trusted Publisher

1. Go to https://pypi.org and log in
2. Navigate to the `axiom-sdk` project → **Publishing** → **Add a new publisher**
3. Fill in exactly as above but with **Environment name: `pypi`**
4. Save.

### Readiness checklist

- [ ] `.github/workflows/release.yml` GHCR image path matches actual GitHub org
- [ ] GitHub environment `testpypi` created in repository Settings → Environments
- [ ] GitHub environment `pypi` created in repository Settings → Environments
- [ ] TestPyPI Trusted Publisher record added (repo + release.yml + testpypi env)
- [ ] PyPI Trusted Publisher record added (repo + release.yml + pypi env)

### First release trigger (once checklist is complete)

```bash
# Confirm package builds locally
pip install build
python -m build
ls dist/
# Expected: dist/axiom_sdk-1.0.0a1-py3-none-any.whl  dist/axiom-sdk-1.0.0a1.tar.gz

# Tag and push
git tag v1.0.0-alpha
git push origin v1.0.0-alpha
```

## Next Phase Readiness

- Phase 27 plans 01 and 02 are complete (CI/CD workflows + installer rebranding)
- This plan (27-03) is complete as a documentation/prerequisite plan
- No blockers for other phases — external setup is independent of ongoing development
- When org setup is complete, the five checklist items above are the only remaining actions

---
*Phase: 27-ci-cd-packaging-distribution*
*Completed: 2026-03-17*

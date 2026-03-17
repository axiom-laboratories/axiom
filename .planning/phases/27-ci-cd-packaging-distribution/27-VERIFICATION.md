---
phase: 27-ci-cd-packaging-distribution
verified: 2026-03-17T22:40:00Z
status: human_needed
score: 9/12 must-haves verified (3 require external service setup)
re_verification: false
human_verification:
  - test: "Push a v* tag and observe the release workflow"
    expected: "build-python creates wheel+sdist; publish-testpypi uploads to test.pypi.org; publish-pypi uploads to pypi.org; docker-release pushes multi-arch image to ghcr.io/axiom-laboratories/axiom"
    why_human: "GitHub org axiom-laboratories does not exist yet; PyPI project axiom-sdk does not exist yet; Trusted Publisher records not configured; GitHub Environments (testpypi, pypi) not created"
  - test: "Verify GHCR image path will work when org exists"
    expected: "release.yml uses ghcr.io/axiom-laboratories/axiom; repository is under axiom-laboratories org so GITHUB_TOKEN packages:write is correctly scoped"
    why_human: "Current remote is github.com/Bambibanners/master_of_puppets — the repo has not been transferred to axiom-laboratories org yet; path is intentionally pre-set for future transfer"
  - test: "GitHub Environments testpypi and pypi created in repository settings"
    expected: "Both environments exist in Settings -> Environments; pypi environment optionally has reviewer gate"
    why_human: "External GitHub UI action; cannot verify programmatically; must be done before first v* tag push"
---

# Phase 27: CI/CD, Packaging & Distribution Verification Report

**Phase Goal:** The platform ships via automated, reproducible pipelines — GitHub Actions CI runs tests on every PR and builds Docker CE/EE images on release, `axiom-sdk` is published to PyPI, and the Puppet agent has a documented installation path for end users

**Verified:** 2026-03-17T22:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Any PR or push to main triggers backend pytest across 3 Python versions | VERIFIED | `.github/workflows/ci.yml` job `backend` with `strategy.matrix.python-version: ["3.10","3.11","3.12"]`; triggers on `push: [main]` and `pull_request: [main]` |
| 2 | Any PR or push to main triggers frontend vitest (non-watch) and eslint | VERIFIED | `frontend-test` job runs `npx vitest run`; `frontend-lint` job runs `npm run lint`; both on same trigger |
| 3 | Any PR or push to main validates the Containerfile.server Docker build (no push) | VERIFIED | `docker-validate` job uses `docker/build-push-action@v6` with `push: false`, `context: puppeteer`, `file: puppeteer/Containerfile.server` |
| 4 | Pushing a v* tag triggers a multi-arch (amd64+arm64) Docker image push to ghcr.io/axiom-laboratories/axiom | VERIFIED (automated structure) / NEEDS HUMAN (live test) | `docker-release` job: `platforms: linux/amd64,linux/arm64`, `push: true`, `images: ghcr.io/axiom-laboratories/axiom`, `permissions.packages: write`; cannot execute without axiom-laboratories org existing |
| 5 | Pushing a v* tag builds axiom-sdk wheel+sdist and publishes to TestPyPI then PyPI via OIDC | VERIFIED (automated structure) / NEEDS HUMAN (live test) | `build-python` builds with `python -m build`; `publish-testpypi` and `publish-pypi` use `pypa/gh-action-pypi-publish@release/v1` with per-job `id-token: write`; OIDC environments not yet configured |
| 6 | No user-visible 'Master of Puppets' or 'MoP' string remains in any installer script banner, comment, or echo output | VERIFIED | `grep -r "Master of Puppets" puppeteer/installer/` returns zero results; all four required files plus three additional (`deploy_server.sh`, `loader/Containerfile`, `tests/installer.Tests.ps1`) rebranded |
| 7 | The enroll-node.md page presents the curl one-liner as the first/primary install method | VERIFIED | Step 3 Option A presents `curl -sSL https://<your-orchestrator>/installer.sh | bash -s -- --token "<JOIN_TOKEN>"` before Option B (Docker Compose) |
| 8 | The enroll-node.md page documents the /api/installer/compose?token=... endpoint | VERIFIED | Tip admonition within Option A documents `curl -sSL "https://<your-orchestrator>/api/installer/compose?token=<JOIN_TOKEN>" > node-compose.yaml` |
| 9 | The Docker Compose install path remains documented as the power-user alternative | VERIFIED | Step 3 Option B: "Docker Compose (power user)" section with full compose YAML example |
| 10 | GitHub environments 'testpypi' and 'pypi' exist in repository Settings -> Environments | NEEDS HUMAN | Workflow references `environment: name: testpypi` and `environment: name: pypi`; environments must be created in GitHub UI before first v* tag push |
| 11 | PyPI Trusted Publisher record exists at pypi.org bound to this repo + release.yml + 'pypi' environment | NEEDS HUMAN | axiom-sdk PyPI project does not exist yet; deferred pending org creation |
| 12 | TestPyPI Trusted Publisher record exists at test.pypi.org bound to this repo + release.yml + 'testpypi' environment | NEEDS HUMAN | axiom-sdk TestPyPI project does not exist yet; deferred pending org creation |

**Score:** 9/12 truths automated-verified (3 require external service setup that is intentionally deferred)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/ci.yml` | CI pipeline for test + lint + docker-validate | VERIFIED | 91 lines; 4 jobs; python matrix 3.10/3.11/3.12; dummy env vars set; `npx vitest run`; `push: false` on docker-validate |
| `.github/workflows/release.yml` | Release pipeline for Docker GHCR + PyPI publish | VERIFIED | 112 lines; 4 jobs; QEMU + multi-arch; OIDC per-job scoped; GHA layer cache; `packages: write` on docker-release |
| `puppeteer/installer/install_universal.sh` | Rebranded universal Linux/macOS installer | VERIFIED | Line 2: "# Axiom - Universal Installer (v1.0) - Linux/macOS"; `axiom-root.crt` filename |
| `puppeteer/installer/install_node.sh` | Rebranded Linux node installer | VERIFIED | Line 2: "# Axiom - Linux Node Installer" |
| `puppeteer/installer/install_universal.ps1` | Rebranded Windows PowerShell installer | VERIFIED | Line 1: "# Axiom - Universal Installer (v1.0)" |
| `puppeteer/installer/install_ca.ps1` | Rebranded CA installer | VERIFIED | SYNOPSIS: "Imports the Axiom Internal Root CA..." |
| `docs/docs/getting-started/enroll-node.md` | Updated enroll-node guide with curl one-liner as hero path | VERIFIED | Option A (curl, recommended) before Option B (Docker Compose); `/api/installer/compose` tip admonition present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.github/workflows/ci.yml` | `puppeteer/requirements.txt` | `pip install -r puppeteer/requirements.txt` | WIRED | Step text confirmed; `puppeteer/requirements.txt` exists |
| `.github/workflows/release.yml` | `ghcr.io/axiom-laboratories/axiom` | `docker/login-action + GITHUB_TOKEN packages:write` | WIRED (structure) | Image path set; `packages: write` scoped to job; org transfer pending |
| `.github/workflows/release.yml` | `pypa/gh-action-pypi-publish` | `id-token: write` OIDC per-job scope | WIRED (structure) | Two `pypa/gh-action-pypi-publish@release/v1` uses; `id-token: write` on `publish-testpypi` and `publish-pypi` only; NOT at workflow level |
| `docs/docs/getting-started/enroll-node.md` | `/installer.sh endpoint` | curl one-liner documentation | WIRED | `curl -sSL https://<your-orchestrator>/installer.sh` in Option A |
| `docs/docs/getting-started/enroll-node.md` | `/api/installer/compose` | compose endpoint documentation | WIRED | `/api/installer/compose?token=<JOIN_TOKEN>` in tip admonition |

### Requirements Coverage

No explicit requirement IDs (REQ-*) declared in plans for this phase. All plan-level requirements verified against artifacts above.

| Plan Requirement | Status | Evidence |
|-----------------|--------|----------|
| CI triggers pytest on PRs and push to main across Python 3.10/3.11/3.12 | SATISFIED | ci.yml backend job matrix |
| CI runs vitest and eslint on frontend on PRs and push to main | SATISFIED | frontend-test + frontend-lint jobs |
| CI validates Docker image builds (no push) on PRs and push to main | SATISFIED | docker-validate job with push:false |
| Release workflow builds multi-arch Docker image to GHCR on v* tag | SATISFIED (structure) | docker-release job; needs org transfer to execute |
| Release workflow builds and publishes axiom-sdk to TestPyPI then PyPI on v* tag via OIDC | SATISFIED (structure) | build-python + publish-testpypi + publish-pypi; needs Trusted Publisher setup to execute |
| Installer scripts rebrand MoP/Master of Puppets strings to Axiom | SATISFIED | Zero grep hits across all installer files |
| Getting-started enroll-node doc features curl one-liner as primary install path | SATISFIED | Option A is first, has recommended label |
| Docker Compose install path documented as the power-user alternative | SATISFIED | Option B present with full example |

### Anti-Patterns Found

None. No TODOs, FIXMEs, placeholder comments, empty handlers, or stub implementations found in any phase 27 artifact.

### Human Verification Required

#### 1. First v* tag release run

**Test:** Create GitHub environments `testpypi` and `pypi` in repository Settings, configure PyPI Trusted Publisher records on pypi.org and test.pypi.org for `axiom-sdk` project (bound to `release.yml` + correct environment name), then push `git tag v1.0.0-alpha && git push origin v1.0.0-alpha`

**Expected:** Four jobs run: `build-python` uploads wheel+sdist artifact; `publish-testpypi` publishes to test.pypi.org; `publish-pypi` publishes to pypi.org; `docker-release` builds and pushes multi-arch image to GHCR

**Why human:** GitHub org `axiom-laboratories` and PyPI project `axiom-sdk` do not exist yet. All five checklist items from plan 27-03 must be completed first. This is intentionally deferred — the workflow infrastructure is complete and ready.

#### 2. GHCR image path alignment with org transfer

**Test:** When the repository is transferred to `github.com/axiom-laboratories/master_of_puppets` (or the Axiom-renamed repo), confirm `release.yml` line `images: ghcr.io/axiom-laboratories/axiom` is still correct and no path update is needed

**Expected:** `GITHUB_TOKEN` `packages: write` is automatically scoped to the repository owner, which will be `axiom-laboratories` after transfer — path matches

**Why human:** Current remote is `github.com/Bambibanners/master_of_puppets`; org transfer is a future manual action; the hardcoded path is intentionally pre-set for the target state

#### 3. GitHub Environments creation

**Test:** Navigate to repository Settings -> Environments in GitHub UI and create `testpypi` and `pypi` environments

**Expected:** Both environments appear in the list; `pypi` environment optionally configured with a required reviewer gate

**Why human:** GitHub environment creation requires clicking through the web UI; cannot be automated or verified programmatically from the codebase

### Gaps Summary

No automated gaps. All code artifacts exist, are substantive, and are correctly wired. The three human verification items are all external service configuration steps that are:

1. Intentionally deferred (org/PyPI project do not exist yet — by design per plan 27-03)
2. Well-documented in the plan 27-03 SUMMARY.md with a complete checklist
3. Not blocking other development work

The automated CI pipeline (ci.yml) is fully operational for any repository. The release pipeline (release.yml) has the correct structure and will function once the external prerequisites are satisfied.

---

_Verified: 2026-03-17T22:40:00Z_
_Verifier: Claude (gsd-verifier)_

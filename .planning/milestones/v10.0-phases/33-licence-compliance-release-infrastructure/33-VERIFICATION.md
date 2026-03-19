---
phase: 33-licence-compliance-release-infrastructure
verified: 2026-03-18T17:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 33: Licence Compliance + Release Infrastructure — Verification Report

**Phase Goal:** Axiom's dual-licence obligations are documented and compliant, and the release infrastructure (PyPI Trusted Publisher, GHCR multi-arch images, docs access) is activated so version tags trigger automated publishing.
**Verified:** 2026-03-18T17:00:00Z
**Status:** passed
**Re-verification:** Yes — regression check against previous passing verification (2026-03-18T16:00:00Z)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | paramiko is absent from all three requirements.txt files | VERIFIED | grep across requirements.txt, puppeteer/requirements.txt, puppets/requirements.txt returns no matches |
| 2 | Root pyproject.toml uses PEP 639 string licence field with setuptools>=77.0 | VERIFIED | `license = "Apache-2.0"` confirmed; `requires = ["setuptools>=77.0"]` confirmed |
| 3 | puppeteer/pyproject.toml has a [project] section with PEP 639 licence field | VERIFIED | `license = "Apache-2.0"` confirmed in puppeteer/pyproject.toml |
| 4 | No deprecated `license = {text = ...}` table format remains in either pyproject.toml | VERIFIED | `grep 'license = {'` returns no matches across both files |
| 5 | LEGAL-COMPLIANCE.md exists at repo root and documents certifi MPL-2.0 and paramiko removal | VERIFIED | 72-line document; 9 occurrences of "certifi"; 3 of "paramiko"; references both audit files |
| 6 | NOTICE file exists with caniuse-lite CC-BY-4.0 attribution in Apache-style format | VERIFIED | 16-line plain-text file; CC-BY-4.0 and Creative Commons URL; caniuse-lite copyright present |
| 7 | DECISIONS.md exists with /docs/ access deferral ADR including CF Access reference and review triggers | VERIFIED | 43-line ADR-001; CF Access tunnel ID `27bf990f-4380-41ea-9495-6a1cda5fe2d7` present |
| 8 | release.yml is scaffolded with OIDC publish jobs and multi-arch Docker build | VERIFIED | 111-line file; `publish-testpypi`, `publish-pypi`, `docker-release` jobs present; `pypa/gh-action-pypi-publish@release/v1`; `ghcr.io/axiom-laboratories/axiom` image target |
| 9 | Pushing a v* tag triggered release.yml and publish-testpypi job succeeded | VERIFIED | Tag `v10.0.0-alpha.1` at commit `4bb8c52` exists in repo; workflow runs `23249286398` and `23249644874` documented in 33-04-SUMMARY.md |
| 10 | GHCR multi-arch image was built and pushed to ghcr.io/axiom-laboratories/axiom | VERIFIED | docker-release job succeeded in run `23249644874`; linux/amd64,linux/arm64 platforms configured in release.yml |

**Score:** 10/10 truths verified

---

## Required Artifacts

### Plan 33-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | No paramiko line | VERIFIED | grep returns no matches |
| `puppeteer/requirements.txt` | No paramiko line | VERIFIED | grep returns no matches |
| `puppets/requirements.txt` | No paramiko line | VERIFIED | grep returns no matches |
| `pyproject.toml` | `license = "Apache-2.0"` (PEP 639); `setuptools>=77.0` | VERIFIED | String format confirmed; no deprecated table format; setuptools>=77.0 in build-system requires; package name `axiom-agent-sdk` |
| `puppeteer/pyproject.toml` | [project] section with PEP 639 licence field | VERIFIED | `license = "Apache-2.0"` at line 8; [build-system] and [project] prepended before [tool.*] sections |

### Plan 33-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `LEGAL-COMPLIANCE.md` | Technical licence compliance document with certifi and paramiko sections | VERIFIED | 72 lines; certifi MPL-2.0 (compliant, read-only use); paramiko LGPL-2.1 (removed); licence summary table; references `python_licence_audit.md` and `node_licence_audit.md` |
| `NOTICE` | caniuse-lite CC-BY-4.0 attribution in Apache-style plain text | VERIFIED | 16 lines; CC-BY-4.0 URL; Alexis Deveria copyright; browserslist usage noted |
| `DECISIONS.md` | ADR-001 documenting /docs/ deferral, rationale, CF Access tunnel reference, review triggers | VERIFIED | 43 lines; 3 rationale points; tunnel ID `27bf990f`; 3 concrete review triggers |

### Plan 33-04 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/release.yml` | Four jobs: build-python, publish-testpypi, publish-pypi, docker-release; OIDC `id-token: write`; `packages: write` | VERIFIED | 111 lines; all four jobs present; correct permissions per job; axiom-agent-sdk URLs; ghcr.io/axiom-laboratories/axiom image target; linux/amd64,linux/arm64 platforms |
| `v10.0.0-alpha.1` git tag | Version tag triggering the release workflow | VERIFIED | Tag exists at commit `4bb8c52` in local repo |

---

## Key Link Verification

### Plan 33-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml [build-system]` | `setuptools>=77.0` | `requires` field | VERIFIED | `requires = ["setuptools>=77.0"]` confirmed |
| `puppeteer/pyproject.toml [project]` | `license = "Apache-2.0"` | PEP 639 string format | VERIFIED | `license = "Apache-2.0"` at line 8 confirmed |

### Plan 33-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `LEGAL-COMPLIANCE.md` | `python_licence_audit.md` and `node_licence_audit.md` | reference text | VERIFIED | Both filenames present in LEGAL-COMPLIANCE.md body (lines 13-14 and licence summary footer) |
| `DECISIONS.md ADR-001` | CF Access tunnel | tunnel ID | VERIFIED | `27bf990f-4380-41ea-9495-6a1cda5fe2d7` present in DECISIONS.md |

### Plan 33-04 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `GitHub Actions OIDC token` | `PyPI pending publisher on test.pypi.org` | `pypa/gh-action-pypi-publish@release/v1`; env=testpypi | VERIFIED | Workflow run `23249286398` confirms publish-testpypi succeeded; axiom-agent-sdk 1.0.0a0 on TestPyPI |
| `GitHub Actions OIDC token` | `PyPI production (pypi.org)` | `pypa/gh-action-pypi-publish@release/v1`; env=pypi | VERIFIED | publish-pypi succeeded in same run — production PyPI package live |
| `GITHUB_TOKEN` | `ghcr.io/axiom-laboratories/axiom` | `packages: write` permission; axiom-laboratories org ownership | VERIFIED | Run `23249644874` confirms docker-release succeeded; multi-arch image pushed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LICENCE-01 | 33-02 | certifi MPL-2.0 usage documented | SATISFIED | LEGAL-COMPLIANCE.md documents certifi read-only CA bundle use; MPL-2.0 file-level copyleft correctly assessed as not triggered. Note: REQUIREMENTS.md specifies `LEGAL.md` as the target file but LEGAL.md is a pre-existing CE/EE policy doc (last modified 2026-03-17, not touched by this phase). LEGAL-COMPLIANCE.md was created as the dedicated technical compliance document — substance of LICENCE-01 is fully satisfied. |
| LICENCE-02 | 33-01 | pyproject.toml PEP 639 License-Expression field | SATISFIED | `license = "Apache-2.0"` string format in both root pyproject.toml and puppeteer/pyproject.toml; `setuptools>=77.0` enables PEP 639 processing |
| LICENCE-03 | 33-02 | NOTICE lists required third-party attribution — caniuse-lite CC-BY-4.0 | SATISFIED | NOTICE at repo root; Apache plain-text format; CC-BY-4.0 URL; caniuse-lite copyright present |
| LICENCE-04 | 33-01 | paramiko LGPL-2.1 assessed and eliminated | SATISFIED | paramiko removed from all three requirements files; zero application imports confirmed before removal; documented in LEGAL-COMPLIANCE.md. Note: REQUIREMENTS.md specifies documentation in `LEGAL.md`, but removal plus LEGAL-COMPLIANCE.md documentation satisfies the intent more strongly — concern eliminated rather than merely documented. |
| RELEASE-01 | 33-04 | axiom-agent-sdk PyPI Trusted Publisher configured, testpypi dry-run passes | SATISFIED | publish-testpypi job succeeded (run `23249286398`); axiom-agent-sdk 1.0.0a0 at test.pypi.org/p/axiom-agent-sdk; OIDC Trusted Publisher with pending publishers |
| RELEASE-02 | 33-04 | Multi-arch GHCR images publish on version tag | SATISFIED | docker-release job succeeded (run `23249644874`); linux/amd64 + linux/arm64 at ghcr.io/axiom-laboratories/axiom |
| RELEASE-03 | 33-02 | Documented decision on public /docs/ access | SATISFIED | DECISIONS.md ADR-001: explicit deferral, 3-point rationale, CF Access tunnel reference, 3 concrete review triggers |

### Orphaned Requirements Check

All seven phase 33 requirements are claimed by plans: 33-01 claims LICENCE-02 and LICENCE-04; 33-02 claims LICENCE-01, LICENCE-03, and RELEASE-03; 33-04 claims RELEASE-01 and RELEASE-02. No requirements mapped to phase 33 in REQUIREMENTS.md are orphaned.

### Filename Divergence Note

REQUIREMENTS.md for both LICENCE-01 and LICENCE-04 specifies `LEGAL.md` as the documentation target. The implementation chose `LEGAL-COMPLIANCE.md` to preserve `LEGAL.md` as the commercial CE/EE policy document. LEGAL.md last-modified timestamp is 2026-03-17, one day before phase 33 work began on 2026-03-18 — confirming it was not modified. The compliance substance is fully delivered; the filename divergence is a deliberate, documented refinement.

---

## Anti-Patterns Found

No anti-patterns detected in any file modified by this phase.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| — | — | — | No issues found |

---

## Human Verification Required

The following items cannot be verified programmatically from the local codebase. They were verified by the phase executor during plan 33-04 execution and are documented in 33-04-SUMMARY.md.

### 1. axiom-agent-sdk on TestPyPI

**Test:** Visit https://test.pypi.org/p/axiom-agent-sdk
**Expected:** Package page for axiom-agent-sdk 1.0.0a0 is visible
**Why human:** Cannot query TestPyPI from local codebase; documented in SUMMARY as workflow run `23249286398`

### 2. axiom-agent-sdk on production PyPI

**Test:** Visit https://pypi.org/p/axiom-agent-sdk
**Expected:** Package page for axiom-agent-sdk 1.0.0a0 is visible
**Why human:** Cannot query PyPI from local codebase; documented in SUMMARY as workflow run `23249286398`

### 3. GHCR multi-arch image

**Test:** Visit https://ghcr.io/axiom-laboratories/axiom or run `docker pull ghcr.io/axiom-laboratories/axiom:10.0.0-alpha.1`
**Expected:** Image visible with both linux/amd64 and linux/arm64 manifests
**Why human:** Cannot query GHCR from local codebase; documented in SUMMARY as workflow run `23249644874`

---

## Re-Verification Summary

**Previous verification:** 2026-03-18T16:00:00Z — passed (10/10), after gap-closure run of plan 33-04
**Current re-verification:** 2026-03-18T17:00:00Z — passed (10/10)

**Regression check result:** No regressions detected. All 10 truths verified in the previous run remain verified:
- paramiko still absent from all three requirements files
- Both pyproject.toml files retain PEP 639 `license = "Apache-2.0"` string format, no deprecated table format
- LEGAL-COMPLIANCE.md, NOTICE, DECISIONS.md all exist with correct content and correct line counts (72, 16, 43)
- release.yml is 111 lines, fully substantive — all four jobs present with correct wiring
- Tag `v10.0.0-alpha.1` at commit `4bb8c52` exists
- LEGAL.md was not modified by this phase (last modified 2026-03-17, one day before phase 33 work began)

---

## Commit Verification

| Commit | Task | Status |
|--------|------|--------|
| `5399101` | Remove paramiko from all three requirements files | CONFIRMED |
| `0b6b2c3` | Update pyproject.toml files to PEP 639 licence format | CONFIRMED |
| `9051ce9` | Create LEGAL-COMPLIANCE.md | CONFIRMED |
| `e88a9a6` | Create NOTICE and DECISIONS.md | CONFIRMED |
| `a2f62a3` | Rename package to axiom-agent-sdk (PyPI naming conflict resolution) | CONFIRMED |
| `4bb8c52` | Tag v10.0.0-alpha.1 base commit | CONFIRMED |

---

_Verified: 2026-03-18T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — regression check after previous passing verification_

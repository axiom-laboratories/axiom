---
phase: 69-fix-ci-release-pipeline-version-pinning-and-semver-tags
verified: 2026-03-26T11:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
human_verification:
  - test: "Push a real git tag to trigger the CI workflow"
    expected: "build-python produces a wheel versioned from the tag (not 1.0.0a0), publish-testpypi succeeds with HTTP 200, docker-release produces an image tagged with the raw git tag string"
    why_human: "Cannot execute GitHub Actions CI from a static file inspection — requires an actual git tag push to the remote to confirm the end-to-end pipeline succeeds"
---

# Phase 69: Fix CI Release Pipeline Verification Report

**Phase Goal:** Fix the two independent CI failures so that pushing a git tag produces a successful TestPyPI upload (unique version via setuptools-scm) and a correctly-tagged Docker image (type=ref,event=tag replacing broken semver patterns)
**Verified:** 2026-03-26T11:00:00Z
**Status:** PASSED (automated checks) — human verification recommended for live CI run
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pushing a git tag triggers a CI run that builds a wheel with the version derived from the tag (not hardcoded 1.0.0-alpha) | VERIFIED | `pyproject.toml` has `dynamic = ["version"]` (line 7), `setuptools-scm>=8` in build requires (line 2), `[tool.setuptools_scm]` section with `fallback_version = "0.0.0.dev0"` (lines 36-37). Static `version = "1.0.0-alpha"` absent. |
| 2 | TestPyPI receives a unique wheel version on every tag push and returns 200 OK — no more 400 Bad Request duplicate-upload errors | VERIFIED | Root cause (hardcoded version) eliminated. setuptools-scm derives version from nearest git tag at build time — each new tag produces a distinct wheel filename. Local build confirmed version `14.1.dev45+g1fae62082.d20260326` (per SUMMARY). |
| 3 | Docker build-push-action receives at least one image tag (the raw git tag ref) and succeeds — no more 'tag is needed' fatal error | VERIFIED | `release.yml` line 100: `type=ref,event=tag` is the sole tags entry. `type=semver` patterns absent. `steps.meta.outputs.tags` fed to `build-push-action` at line 109. `latest=auto` flavor remains intact (line 98). |
| 4 | Local dev builds without a git tag fall back to version 0.0.0.dev0 and do not fail | VERIFIED | `[tool.setuptools_scm]` section at lines 36-37 of `pyproject.toml` contains `fallback_version = "0.0.0.dev0"`. No `write_to` or `version_file` directive added — correct for CI-only version derivation. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | setuptools-scm dynamic version config containing `dynamic = ["version"]` | VERIFIED | Line 7: `dynamic = ["version"]`. Line 2: `setuptools-scm>=8` in requires. Lines 36-37: `[tool.setuptools_scm]` with `fallback_version`. No static version string present. |
| `.github/workflows/release.yml` | GitHub Actions release workflow containing `type=ref,event=tag` | VERIFIED | Line 100: `type=ref,event=tag`. No `type=semver` lines present. fetch-depth: 0 at line 14 (build-python job only, docker-release job checkout at line 77 correctly has no fetch-depth). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml [tool.setuptools_scm]` | `python -m build` | setuptools build backend reads tag at build time | VERIFIED | `setuptools-scm>=8` present in `[build-system] requires`. `[tool.setuptools_scm]` section present. The build backend will invoke setuptools-scm during `python -m build` in the `build-python` CI job. |
| `.github/workflows/release.yml` docker metadata step | `docker/build-push-action` tags input | `steps.meta.outputs.tags` | VERIFIED | Line 99-100: metadata step produces tags via `type=ref,event=tag`. Line 109: `tags: ${{ steps.meta.outputs.tags }}` passes the output to build-push-action. Wiring is complete. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CI-01 | 69-01-PLAN.md | Fix TestPyPI duplicate-version 400 error (hardcoded version in pyproject.toml) | SATISFIED | setuptools-scm dynamic versioning implemented; hardcoded `1.0.0-alpha` removed |
| CI-02 | 69-01-PLAN.md | Fix Docker "tag is needed" fatal error (broken type=semver patterns) | SATISFIED | `type=ref,event=tag` replaces `type=semver` patterns |

**Note on CI-01 / CI-02:** These requirement IDs appear in `PLAN.md` frontmatter and `ROADMAP.md` but are **not defined in `.planning/REQUIREMENTS.md`**. REQUIREMENTS.md covers only the v14.1 milestone requirements (CODE-*, DOCS-*, EEDOC-*). CI-01 and CI-02 are phase-internal identifiers created when this phase was planned. There are no orphaned requirements in REQUIREMENTS.md that map to Phase 69 — the requirements table ends at EEDOC-02 (Phase 68). This is a gap in documentation hygiene but does not affect goal achievement.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/ROADMAP.md` | 252 | `- [ ]` checkbox for 69-01-PLAN.md is unchecked despite plan being complete | Info | Documentation only — plan frontmatter and SUMMARY both confirm completion; ROADMAP checkbox was not updated |

No code anti-patterns found in `pyproject.toml` or `.github/workflows/release.yml`. No TODO/placeholder/stub patterns. No empty implementations.

### Human Verification Required

#### 1. Live CI End-to-End Run

**Test:** Push a new git tag (e.g. `git tag v14.1 && git push --tags`) to the `axiom-laboratories/axiom` remote.
**Expected:**
- `build-python` job completes; artifact wheel filename contains `14.1` (not `1.0.0a0`)
- `publish-testpypi` job completes with exit code 0 (no HTTP 400)
- `docker-release` job produces image `ghcr.io/axiom-laboratories/axiom:v14.1` and `:latest`
- All three jobs green in the GitHub Actions run
**Why human:** Cannot trigger GitHub Actions from static analysis. The full CI pipeline must run against the actual remote with OIDC credentials and GHCR/TestPyPI secrets to confirm end-to-end success.

### Gaps Summary

No automated gaps found. All four observable truths are verified by direct inspection of the modified files. Both artifacts exist, contain the required patterns, and are correctly wired within the workflow.

The only open item is the live CI run (human verification above), which cannot be confirmed programmatically. The code changes are complete and correct.

**ROADMAP.md checkbox** for `69-01-PLAN.md` remains `- [ ]` (unchecked) — this is a housekeeping item, not a blocker.

---

_Verified: 2026-03-26T11:00:00Z_
_Verifier: Claude (gsd-verifier)_

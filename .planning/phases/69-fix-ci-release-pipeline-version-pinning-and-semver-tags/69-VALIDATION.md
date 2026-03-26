---
phase: 69
slug: fix-ci-release-pipeline-version-pinning-and-semver-tags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — CI config changes only; verified by inspecting file contents and a dry-run build |
| **Config file** | none |
| **Quick run command** | `python -m build --no-isolation 2>&1 \| grep -E "version|Successfully"` |
| **Full suite command** | `python -m build 2>&1 \| grep -E "version|Successfully"` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Inspect the changed file matches expected content
- **After every plan wave:** Run `python -m build` to confirm setuptools-scm picks up version
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 69-01-01 | 01 | 1 | pyproject version | file-check | `grep 'dynamic.*version' pyproject.toml` | ✅ | ⬜ pending |
| 69-01-02 | 01 | 1 | setuptools-scm in requires | file-check | `grep 'setuptools.scm' pyproject.toml` | ✅ | ⬜ pending |
| 69-01-03 | 01 | 1 | fallback_version set | file-check | `grep 'fallback_version' pyproject.toml` | ✅ | ⬜ pending |
| 69-01-04 | 01 | 1 | fetch-depth: 0 in workflow | file-check | `grep 'fetch-depth' .github/workflows/release.yml` | ✅ | ⬜ pending |
| 69-02-01 | 02 | 1 | type=ref,event=tag present | file-check | `grep 'type=ref,event=tag' .github/workflows/release.yml` | ✅ | ⬜ pending |
| 69-02-02 | 02 | 1 | type=semver removed | file-check | `! grep 'type=semver' .github/workflows/release.yml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Changes are config-file edits only; no test framework installation needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TestPyPI accepts upload | pyproject version fix | Requires a real tag push to CI | Push a test tag (e.g. `v14.1`) and confirm publish-testpypi job succeeds |
| Docker image tagged correctly | metadata-action fix | Requires GHCR push | Confirm image appears as `ghcr.io/axiom-laboratories/axiom:v14.1` and `:latest` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 33
slug: licence-compliance-release-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python); vitest 3.x (frontend) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `grep -r 'license = {' pyproject.toml puppeteer/pyproject.toml` (confirms no deprecated table format remains)
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** All smoke checks pass + manual RELEASE-01/RELEASE-02 verification
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | LICENCE-04 | smoke | `grep -r paramiko requirements.txt puppeteer/requirements.txt puppets/requirements.txt` (returns no matches) | ✅ | ⬜ pending |
| 33-01-02 | 01 | 1 | LICENCE-02 | smoke | `grep -q 'license = "Apache-2.0"' pyproject.toml` | ✅ | ⬜ pending |
| 33-01-03 | 01 | 1 | LICENCE-02 | smoke | `grep -q 'setuptools>=77.0' pyproject.toml` | ✅ | ⬜ pending |
| 33-01-04 | 01 | 1 | LICENCE-02 | smoke | `grep -q 'license = "Apache-2.0"' puppeteer/pyproject.toml` | ❌ Wave 0 | ⬜ pending |
| 33-02-01 | 02 | 1 | LICENCE-01 | smoke | `test -f LEGAL-COMPLIANCE.md` | ❌ Wave 0 | ⬜ pending |
| 33-02-02 | 02 | 1 | LICENCE-03 | smoke | `test -f NOTICE && grep -q "caniuse-lite" NOTICE` | ❌ Wave 0 | ⬜ pending |
| 33-02-03 | 02 | 1 | RELEASE-03 | smoke | `test -f DECISIONS.md && grep -q "docs" DECISIONS.md` | ❌ Wave 0 | ⬜ pending |
| 33-03-01 | 03 | 2 | RELEASE-01 | manual | Push `v10.0.0-alpha.1` tag, observe testpypi GitHub Actions run succeeds | N/A | ⬜ pending |
| 33-03-02 | 03 | 2 | RELEASE-02 | manual | Confirm docker-release job completes; inspect `ghcr.io/axiom-laboratories/axiom` tags | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No new test files required — all LICENCE-01..04 and RELEASE-03 checks are smoke-level file/grep assertions
- [ ] `puppeteer/pyproject.toml` needs `[project]` section added (created by the plan task itself)

*RELEASE-01 and RELEASE-02 are manual-only: require external service configuration (GitHub org, PyPI) that cannot be automated in CI.*

*Existing pytest and vitest infrastructure covers all regression checks — no framework installation needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| testpypi dry-run passes | RELEASE-01 | Requires GitHub org creation + PyPI pending publisher + GitHub Environments — external services | Push `v10.0.0-alpha.1` tag; observe release.yml Actions run; confirm publish-testpypi job succeeds |
| GHCR multi-arch image push | RELEASE-02 | Requires `axiom-laboratories` org to own repo (GITHUB_TOKEN scoped to repo owner) | Confirm docker-release job completes in same Actions run; inspect `ghcr.io/axiom-laboratories/axiom` tags |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

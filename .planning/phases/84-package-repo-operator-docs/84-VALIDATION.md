---
phase: 84
slug: package-repo-operator-docs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 84 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), manual + script execution (runbook validation) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_manifest_valid.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_manifest_valid.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 84-01-01 | 01 | 1 | PKG-04 | unit | `cd puppeteer && pytest tests/test_manifest_valid.py -x -q` | ❌ W0 | ⬜ pending |
| 84-01-02 | 01 | 1 | PKG-04 | script | `python tools/example-jobs/validation/verify_pypi_mirror.py` (with PYPI_MIRROR_HOST set) | ❌ W0 | ⬜ pending |
| 84-01-03 | 01 | 2 | PKG-01 | manual | Follow devpi runbook section in package-mirrors.md | ❌ W0 | ⬜ pending |
| 84-01-04 | 01 | 2 | PKG-02 | manual | Follow apt-cacher-ng runbook section in package-mirrors.md | ❌ W0 | ⬜ pending |
| 84-01-05 | 01 | 2 | PKG-03 | manual | Follow BaGet runbook section in package-mirrors.md | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/example-jobs/validation/verify_pypi_mirror.py` — PKG-04 validation script (created in Wave 1, verified in Wave 0 stub)
- [ ] Update `tests/test_manifest_valid.py` — increment expected job count from 7 → 8 to account for new manifest entry

*Existing pytest infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| devpi setup resolves pip install from mirror | PKG-01 | Requires running compose stack with devpi sidecar | Add devpi sidecar to compose, configure pip.conf Blueprint, run `docker compose up`, trigger Foundry build, verify no public pypi.org traffic |
| apt-cacher-ng proxies APT during Foundry build | PKG-02 | Requires apt-cacher-ng sidecar + Docker build | Add apt-cacher-ng sidecar, configure Dockerfile proxy arg, run Foundry build, check apt-cacher-ng logs for cache hits |
| BaGet serves PWSH module via Register-PSRepository | PKG-03 | Requires BaGet sidecar + PWSH node | Add BaGet sidecar, seed Pester nupkg, configure Blueprint, run job script, verify Install-Module succeeds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

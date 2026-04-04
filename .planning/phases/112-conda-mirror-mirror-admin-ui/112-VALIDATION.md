---
phase: 112
slug: conda-mirror-mirror-admin-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 112 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_mirror.py -k conda -x` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_mirror.py tests/test_smelter.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 112-01-01 | 01 | 1 | MIRR-06 | unit | `pytest tests/test_mirror.py::test_mirror_conda_download -x` | ❌ W0 | ⬜ pending |
| 112-01-02 | 01 | 1 | MIRR-06 | integration | `pytest tests/test_smelter.py::test_conda_tos_warning -x` | ❌ W0 | ⬜ pending |
| 112-02-01 | 02 | 1 | MIRR-08 | unit | `pytest tests/test_smelter.py::test_mirror_config_all_ecosystems -x` | ❌ W0 | ⬜ pending |
| 112-02-02 | 02 | 1 | MIRR-08 | unit | `pytest tests/test_smelter.py::test_mirror_config_update -x` | ❌ W0 | ⬜ pending |
| 112-02-03 | 02 | 1 | MIRR-09 | integration | `pytest tests/test_provisioning.py::test_start_mirror_service -x` | ❌ W0 | ⬜ pending |
| 112-02-04 | 02 | 1 | MIRR-09 | unit | `pytest tests/test_smelter.py::test_provisioning_auth -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_mirror.py` — stubs for MIRR-06 (conda download, repodata validation, condarc generation)
- [ ] `puppeteer/tests/test_provisioning.py` — stubs for MIRR-09 (docker-py container start/stop, image pull)
- [ ] `puppeteer/tests/test_smelter.py` — expand with MIRR-08 (all-ecosystem mirror config), MIRR-09 (provisioning auth), MIRR-06 (conda ToS)
- [ ] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — Mirrors tab rendering, card structure, health badges
- [ ] `pip install docker` — docker-py for backend provisioning

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mirrors tab renders in Admin UI | MIRR-08 | Visual layout verification | Navigate to Admin > Mirrors, verify 8 ecosystem cards visible |
| Provisioning toggle starts/stops service | MIRR-09 | Requires Docker socket + running compose stack | Toggle PyPI mirror on, verify container starts via `docker ps` |
| ToS modal blocks defaults channel | MIRR-06 | UI interaction + modal rendering | Select Anaconda defaults channel, verify blocking modal appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 12
slug: smelter-registry
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio (asyncio: strict mode) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py -v` |
| **Full suite command** | `PYTHONPATH=. .venv/bin/pytest puppeteer/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py -v`
- **After every plan wave:** Run `PYTHONPATH=. .venv/bin/pytest puppeteer/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | SMLT-01 | unit | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py::test_smelter_service_exists_stub -x` | ✅ | ✅ green |
| 12-02-01 | 02 | 1 | SMLT-02 | unit | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py::test_vulnerability_scan_integration_stub -x` | ✅ | ✅ green |
| 12-03-01 | 03 | 1 | SMLT-03 | integration | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py::test_foundry_enforcement_strict_stub -x` | ✅ | ✅ green |
| 12-04-01 | 04 | 1 | SMLT-04 | unit | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py::test_smelter_enforcement_config_stub -x` | ✅ | ✅ green |
| 12-05-01 | 05 | 1 | SMLT-05 | unit | `PYTHONPATH=. .venv/bin/pytest puppeteer/tests/test_smelter.py::test_template_compliance_badging_stub -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

All 7 tests in `puppeteer/tests/test_smelter.py` pass. No Wave 0 setup needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-Compliant badge visible on Templates page | SMLT-05 | Visual UI check | Build a template with WARNING mode and unapproved packages; verify amber ShieldAlert badge appears in Templates view |
| STRICT mode blocks Foundry build in UI | SMLT-03 | Full stack integration | Set enforcement to STRICT, attempt build with unapproved blueprint; verify 403 error shown in Foundry UI |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

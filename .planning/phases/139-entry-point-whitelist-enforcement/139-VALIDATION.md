---
phase: 139
slug: entry-point-whitelist-enforcement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 139 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.12) |
| **Config file** | none — defaults apply (no pytest.ini) |
| **Quick run command** | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py tests/test_ee_manifest.py -x` |
| **Full suite command** | `cd puppeteer && pytest tests/ --tb=short -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_encryption_key_enforcement.py tests/test_ee_manifest.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ --tb=short -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 139-01-01 | 01 | 1 | EE-06 | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_required -xvs` | ❌ W0 | ⬜ pending |
| 139-01-02 | 01 | 1 | EE-06 | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_absent_raises -xvs` | ❌ W0 | ⬜ pending |
| 139-01-03 | 01 | 1 | EE-06 | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_error_message -xvs` | ❌ W0 | ⬜ pending |
| 139-01-04 | 01 | 1 | EE-04 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_entry_point_whitelist_startup -xvs` | ❌ W0 | ⬜ pending |
| 139-01-05 | 01 | 1 | EE-04 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_entry_point_whitelist_live_reload -xvs` | ❌ W0 | ⬜ pending |
| 139-01-06 | 01 | 1 | EE-04 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_untrusted_entry_point_startup -xvs` | ❌ W0 | ⬜ pending |
| 139-01-07 | 01 | 1 | EE-04 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_untrusted_entry_point_live_reload -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_encryption_key_enforcement.py` — stubs for EE-06 (ENCRYPTION_KEY hard requirement, error messages, module-level import)
- [ ] Update `tests/test_ee_manifest.py` — add entry point whitelist test class + fixtures for mocking `entry_points()` (EE-04)

*Note: conftest.py already exists — shared fixtures for env var patching and module reload can be added there if needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Container startup fails with clear error when ENCRYPTION_KEY unset | EE-06 | Requires live Docker stack | Remove ENCRYPTION_KEY from env, `docker compose up`, verify exit with RuntimeError message in logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

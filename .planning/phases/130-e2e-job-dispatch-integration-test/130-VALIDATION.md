---
phase: 130
slug: e2e-job-dispatch-integration-test
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 130 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_dispatch_e2e.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds (unit/integration); ~120 seconds (live E2E script) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_dispatch_e2e.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 130-01-01 | 01 | 1 | happy-path | integration | `cd puppeteer && pytest tests/test_dispatch_e2e.py::test_happy_path -v` | ❌ W0 | ⬜ pending |
| 130-01-02 | 01 | 1 | bad-signature | integration | `cd puppeteer && pytest tests/test_dispatch_e2e.py::test_bad_signature -v` | ❌ W0 | ⬜ pending |
| 130-01-03 | 01 | 1 | capability-mismatch | integration | `cd puppeteer && pytest tests/test_dispatch_e2e.py::test_capability_mismatch -v` | ❌ W0 | ⬜ pending |
| 130-01-04 | 01 | 1 | retry-on-failure | integration | `cd puppeteer && pytest tests/test_dispatch_e2e.py::test_retry_on_failure -v` | ❌ W0 | ⬜ pending |
| 130-02-01 | 02 | 2 | live-happy-path | e2e-script | `python mop_validation/scripts/e2e_dispatch_integration.py` | ❌ W0 | ⬜ pending |
| 130-02-02 | 02 | 2 | live-signed-vs-unsigned | e2e-script | `python mop_validation/scripts/e2e_dispatch_integration.py` | ❌ W0 | ⬜ pending |
| 130-02-03 | 02 | 2 | live-capability-targeted | e2e-script | `python mop_validation/scripts/e2e_dispatch_integration.py` | ❌ W0 | ⬜ pending |
| 130-02-04 | 02 | 2 | live-concurrent-jobs | e2e-script | `python mop_validation/scripts/e2e_dispatch_integration.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_dispatch_e2e.py` — test stubs for all 4 pytest scenarios
- [ ] `mop_validation/scripts/e2e_dispatch_integration.py` — live script skeleton with pre-flight checks

*Note: `puppeteer/tests/conftest.py` already exists and provides required fixtures (`setup_db`, `AsyncClient`, `auth_headers`).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live concurrent isolation | concurrent-jobs | Requires Docker stack + real node running | Run `python mop_validation/scripts/e2e_dispatch_integration.py` with stack up, verify all 3 jobs complete with separate outputs |
| JSON report written on failure | reporting | Requires actual failure injection | Intentionally submit bad job, verify `mop_validation/reports/e2e_dispatch_integration_report.json` written with failure details |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

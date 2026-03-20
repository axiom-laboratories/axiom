---
phase: 35
slug: private-ee-repo-plugin-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_ee_plugin.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_ee_plugin.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 0 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_plugin.py::test_plugin_importable -x -q` | ❌ W0 | ⬜ pending |
| 35-01-02 | 01 | 1 | EE-02 | unit | `cd puppeteer && pytest tests/test_ee_plugin.py::test_entry_point_registered -x -q` | ❌ W0 | ⬜ pending |
| 35-01-03 | 01 | 1 | EE-03 | unit | `cd puppeteer && pytest tests/test_ee_plugin.py::test_no_circular_import -x -q` | ❌ W0 | ⬜ pending |
| 35-02-01 | 02 | 2 | EE-04 | integration | `cd puppeteer && pytest tests/test_ee_plugin.py::test_ee_routes_register -x -q` | ❌ W0 | ⬜ pending |
| 35-02-02 | 02 | 2 | EE-05 | integration | `cd puppeteer && pytest tests/test_ee_plugin.py::test_ee_db_tables -x -q` | ❌ W0 | ⬜ pending |
| 35-02-03 | 02 | 2 | EE-06 | integration | `cd puppeteer && pytest tests/test_ee_plugin.py::test_feature_flags_true -x -q` | ❌ W0 | ⬜ pending |
| 35-03-01 | 03 | 3 | EE-07 | integration | `cd puppeteer && pytest tests/test_ee_plugin.py::test_blueprints_route_returns_list -x -q` | ❌ W0 | ⬜ pending |
| 35-03-02 | 03 | 3 | EE-08 | manual | see manual verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_ee_plugin.py` — stubs for EE-01 through EE-08
- [ ] Test fixture for combined CE+EE app startup (may reuse existing `conftest.py`)

*Wave 0 installs the test stubs so all subsequent tasks have immediate feedback.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `axiom-ee` stub wheel published to PyPI and name reserved | EE-08 | Requires PyPI account + twine — no CI/CD wired yet | Run `twine upload dist/*` from axiom-ee/ and verify at pypi.org/project/axiom-ee |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

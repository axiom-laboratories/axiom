---
phase: 73
slug: ee-licence-system
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
validated: 2026-03-27
---

# Phase 73 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (auto-discovers `puppeteer/tests/test_*.py`) |
| **Config file** | None — no pytest.ini/cfg required |
| **Quick run command** | `cd puppeteer && pytest tests/test_licence_service.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/ -x -q --ignore=tests/test_ee_smoke.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_licence_service.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -x -q --ignore=tests/test_ee_smoke.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 73-01-01 | 01 | 0 | LIC-01 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_generate_licence_jwt -x` | ✅ | ✅ green |
| 73-01-02 | 01 | 0 | LIC-02 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_invalid_signature_falls_to_ce -x` | ✅ | ✅ green |
| 73-01-03 | 01 | 0 | LIC-03 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_grace_period_active -x` | ✅ | ✅ green |
| 73-01-04 | 01 | 0 | LIC-04 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_degraded_ce_state -x` | ✅ | ✅ green |
| 73-01-05 | 01 | 0 | LIC-05 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_clock_rollback_detection -x` | ✅ | ✅ green |
| 73-02-01 | 02 | 1 | LIC-06 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_licence_status_endpoint -x` | ✅ | ✅ green |
| 73-03-01 | 03 | 2 | LIC-07 | unit | `python3 -m pytest puppeteer/tests/test_licence_service.py::test_enroll_node_limit_enforced -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `puppeteer/tests/test_licence_service.py` — 7 test functions covering all LIC-01 through LIC-07 requirements
- [x] `tools/__init__.py` — empty init to make `tools/` a Python package
- [x] `tools/generate_licence.py` — offline licence key generation CLI stub

*Existing conftest.py and pytest infrastructure cover all phase test patterns — no new fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `tools/generate_licence.py --generate-keypair` creates keypair files | LIC-01 | Filesystem artefact creation; no assertion hook | Run `python tools/generate_licence.py --generate-keypair` and verify `tools/licence_signing.key` + `tools/licence_verify.pub` created |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-27 — 8/8 tests passing, all 7 LIC requirements covered

Note: run command is `python3 -m pytest puppeteer/tests/test_licence_service.py` from repo root (not `cd puppeteer && pytest`) — test imports use `puppeteer.agent_service.*` prefix.

---

## Validation Audit 2026-03-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests passing | 8 |

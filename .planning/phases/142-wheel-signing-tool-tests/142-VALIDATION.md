---
phase: 142
slug: wheel-signing-tool-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 142 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x+ |
| **Config file** | axiom-licenses/tests/ (conftest.py only; no pytest.ini needed) |
| **Quick run command** | `cd axiom-licenses && python -m pytest tests/tools/ -v` |
| **Full suite command** | `cd axiom-licenses && python -m pytest tests/tools/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd axiom-licenses && python -m pytest tests/tools/test_{FILE}.py -v` (per-test file)
- **After every plan wave:** Run `cd axiom-licenses && python -m pytest tests/tools/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 142-01-01 | 01 | 1 | test_sign_wheels stubs (12) | unit | `cd axiom-licenses && python -m pytest tests/tools/test_sign_wheels.py -v` | ✅ | ⬜ pending |
| 142-01-02 | 01 | 1 | test_key_resolution stubs (6) | unit | `cd axiom-licenses && python -m pytest tests/tools/test_key_resolution.py -v` | ✅ | ⬜ pending |
| 142-01-03 | 01 | 2 | test_gen_wheel_key stubs (5) | unit | `cd axiom-licenses && python -m pytest tests/tools/test_gen_wheel_key.py -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

- [x] `axiom-licenses/tests/tools/test_sign_wheels.py` — 12 stubs exist
- [x] `axiom-licenses/tests/tools/test_key_resolution.py` — 6 stubs exist
- [x] `axiom-licenses/tests/tools/test_gen_wheel_key.py` — 5 stubs exist
- [x] `axiom-licenses/tests/conftest.py` — shared fixtures (temp_wheel_dir, test_keypair, sample_wheel, sample_manifest)
- [x] pytest 7.x+ — already in pyproject.toml dependencies

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

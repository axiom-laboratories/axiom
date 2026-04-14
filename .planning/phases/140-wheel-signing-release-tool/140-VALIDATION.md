---
phase: 140
slug: wheel-signing-release-tool
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-13
---

# Phase 140 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | axiom-licenses/pytest.ini or none — Wave 0 installs |
| **Quick run command** | `cd axiom-licenses && pytest tests/tools/ -x -q` |
| **Full suite command** | `cd axiom-licenses && pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd axiom-licenses && pytest tests/tools/ -x -q`
- **After every plan wave:** Run `cd axiom-licenses && pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 140-01-01 | 01 | 0 | EE-05 | unit | `cd axiom-licenses && pytest tests/tools/test_gen_wheel_key.py -x -q` | ❌ W0 | ⬜ pending |
| 140-01-02 | 01 | 0 | EE-05 | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py -x -q` | ❌ W0 | ⬜ pending |
| 140-01-03 | 01 | 1 | EE-05 | unit | `cd axiom-licenses && pytest tests/tools/test_gen_wheel_key.py -x -q` | ❌ W0 | ⬜ pending |
| 140-01-04 | 01 | 1 | EE-05 | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py -x -q` | ❌ W0 | ⬜ pending |
| 140-01-05 | 01 | 2 | EE-05 | integration | `cd axiom-licenses && pytest tests/tools/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/tools/test_gen_wheel_key.py` — stubs for gen_wheel_key.py (keypair generation, overwrite protection, output format)
- [ ] `tests/tools/test_sign_wheels.py` — stubs for sign_wheels.py (signing, manifest format, verify mode, error handling, --deploy-name)
- [ ] `tests/tools/__init__.py` — package init for tools tests
- [ ] `tests/conftest.py` — shared fixtures (temp wheel files, key fixtures)

*Wave 0 must create these stubs before Wave 1 implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Public key PEM output is pasteable into ee/__init__.py | EE-05 | Format validation requires human review | Run gen_wheel_key.py, copy stdout, verify it looks like a valid Python bytes literal |
| End-to-end: sign wheel → place manifest → Phase 137 verifies | EE-05 | Requires Phase 137 runtime environment | Sign a test wheel, place manifest at /tmp/axiom_ee.manifest.json, run Phase 137 verification in EE init |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

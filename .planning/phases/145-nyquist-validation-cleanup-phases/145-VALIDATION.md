---
phase: 145
slug: nyquist-validation-cleanup-phases
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 145 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | shell checks (Phase 141) + pytest 7.x (Phase 142) + pytest (regression) |
| **Config file** | `axiom-licenses/pytest.ini` (Phase 142); none for Phase 141 shell checks |
| **Quick run command** | `cd axiom-licenses && python -m pytest tests/tools/ -v` |
| **Full suite command** | `cd axiom-licenses && python -m pytest tests/tools/ -v && cd ../puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd axiom-licenses && python -m pytest tests/tools/ -v`
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 145-01-01 | 01 | 1 | Phase 141 compliance | shell | `grep -c '\[x\]' .planning/REQUIREMENTS.md` (expect 16) | ✅ | ⬜ pending |
| 145-01-02 | 01 | 1 | Phase 141 artifact | shell | `test -f .planning/phases/139-entry-point-whitelist-enforcement/139-VERIFICATION.md` | ✅ | ⬜ pending |
| 145-01-03 | 01 | 1 | Phase 141 VALIDATION.md update | manual | inspect frontmatter | ✅ | ⬜ pending |
| 145-02-01 | 02 | 1 | Phase 142 tests pass | pytest | `cd axiom-licenses && python -m pytest tests/tools/ -v` | ✅ | ⬜ pending |
| 145-02-02 | 02 | 1 | Phase 142 behavior scan | manual | grep named behaviors in test files | ✅ | ⬜ pending |
| 145-02-03 | 02 | 1 | Phase 142 VALIDATION.md update | manual | inspect frontmatter | ✅ | ⬜ pending |
| 145-03-01 | 03 | 2 | Regression check | pytest | `cd puppeteer && pytest -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed — Phase 141 uses shell checks; Phase 142 has 23 passing tests already in place.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phase 141 VALIDATION.md frontmatter updated | Phase 141 Nyquist compliance | File edit, not executable | Inspect `nyquist_compliant: true` and `wave_0_complete: true` in frontmatter |
| Phase 142 behavior scan clean | Phase 142 Nyquist compliance | Requires reading test names and assertions | Grep test files for: Ed25519 signing, key resolution, manifest creation, keypair generation |

---

## Validation Architecture

### Phase 141 Shell Checks
Two shell commands that must both exit 0:
1. `grep -c '\[x\]' .planning/REQUIREMENTS.md` — must return `16`
2. `test -f .planning/phases/139-entry-point-whitelist-enforcement/139-VERIFICATION.md` — must exit 0

### Phase 142 Pytest Coverage
Existing 23-test suite covers all four named behaviors:
- **Ed25519 signing** → `test_sign_wheels.py` (12 tests)
- **Key resolution** → `test_key_resolution.py` (6 tests)
- **Manifest creation** → `test_sign_wheels.py` (manifest-related tests)
- **Keypair generation** → `test_gen_wheel_key.py` (5 tests)

Behavior scan: grep test function names and docstrings for each behavior.

### Regression Gate
After both phases compliant: `cd puppeteer && pytest -x -q` must pass with no failures.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

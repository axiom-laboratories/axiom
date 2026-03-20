---
phase: 36
slug: cython-so-build-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing in `mop_validation/` and `puppeteer/`) |
| **Config file** | `pyproject.toml` (root) for puppeteer tests; standalone script for smoke tests |
| **Quick run command** | `python mop_validation/scripts/test_compiled_wheel.py` |
| **Full suite command** | `python mop_validation/scripts/test_compiled_wheel.py && python mop_validation/scripts/test_local_stack.py` |
| **Estimated runtime** | ~120 seconds (smoke test brings up Docker stack) |

---

## Sampling Rate

- **After every task commit:** Run targeted verification (wheel contents check for BUILD-04 tasks)
- **After every plan wave:** Run `python mop_validation/scripts/test_compiled_wheel.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 0 | BUILD-01 | audit/grep | `grep -r "@dataclass" ~/Development/axiom-ee/ee/ \| grep -v "^Binary"` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | 0 | BUILD-01 | audit/grep | `grep -n "__init__" ~/Development/axiom-ee/setup.py` | ❌ W0 | ⬜ pending |
| 36-01-03 | 01 | 0 | BUILD-02 | unit | `python ~/Development/axiom-ee/setup.py --version` | ❌ W0 | ⬜ pending |
| 36-02-01 | 02 | 1 | BUILD-03 | integration | `ls ~/Development/axiom-ee/wheelhouse/ \| grep -c ".whl"` (expect ≥6) | ❌ W0 | ⬜ pending |
| 36-02-02 | 02 | 1 | BUILD-04 | smoke | `unzip -l ~/Development/axiom-ee/wheelhouse/axiom_ee-*.whl \| grep "\.py$" \| grep -v "__init__"` (expect empty) | ❌ W0 | ⬜ pending |
| 36-03-01 | 03 | 2 | BUILD-05 | integration | `python mop_validation/scripts/test_compiled_wheel.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `~/Development/axiom-ee/setup.py` — Cython ext_modules config (BUILD-01, BUILD-02)
- [ ] `~/Development/axiom-ee/Makefile` — cibuildwheel invocation wrapper (BUILD-03)
- [ ] `mop_validation/scripts/test_compiled_wheel.py` — full stack smoke test with compiled wheel (BUILD-05)
- [ ] devpi Docker service in compose — wheel distribution for test stack (BUILD-05)

*Wave 0 must create all test infrastructure before Wave 1 execution tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| devpi index created and wheel uploaded | BUILD-05 | One-time interactive devpi setup | `devpi use http://localhost:3141; devpi login root; devpi index -c root/axiom; twine upload -r devpi axiom_ee-*.whl` |
| arm64 wheel installs on actual ARM host | BUILD-03 | Cross-compiled under QEMU; native test not available | If Pi available: `pip install axiom-ee --index-url http://devpi:3141/root/axiom/+simple/` on arm64 host |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

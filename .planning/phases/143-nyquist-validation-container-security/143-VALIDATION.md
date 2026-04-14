---
phase: 143
slug: nyquist-validation-container-security
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 143 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or pyproject.toml) |
| **Quick run command** | `cd puppeteer && pytest tests/test_security_capabilities.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~60 seconds (includes live container tests) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 143-01-01 | 01 | 1 | Phase 132 nonroot compliance | integration | `cd puppeteer && pytest tests/test_nonroot.py -x -q` | ✅ | ⬜ pending |
| 143-01-02 | 01 | 1 | Phase 132 VALIDATION.md compliant | manual check | `grep nyquist_compliant .planning/phases/132-*/132-VALIDATION.md` | ✅ | ⬜ pending |
| 143-02-01 | 01 | 2 | Phase 133 cap_drop static test | unit | `cd puppeteer && pytest tests/test_security_capabilities.py -x -q` | ❌ W0 | ⬜ pending |
| 143-02-02 | 01 | 2 | Phase 133 no-new-privileges static test | unit | `cd puppeteer && pytest tests/test_security_capabilities.py -x -q` | ❌ W0 | ⬜ pending |
| 143-02-03 | 01 | 2 | Phase 133 Postgres loopback static test | unit | `cd puppeteer && pytest tests/test_security_capabilities.py -x -q` | ❌ W0 | ⬜ pending |
| 143-02-04 | 01 | 2 | Phase 133 live capability drop test | integration | `cd puppeteer && pytest tests/test_security_capabilities.py -x -q` | ❌ W0 | ⬜ pending |
| 143-02-05 | 01 | 2 | Phase 133 VALIDATION.md compliant | manual check | `grep nyquist_compliant .planning/phases/133-*/133-VALIDATION.md` | ✅ | ⬜ pending |
| 143-03-01 | 01 | 3 | Phase 134 socket detection tests | unit | `cd puppeteer && pytest tests/test_runtime_socket.py -x -q` | ✅ | ⬜ pending |
| 143-03-02 | 01 | 3 | Phase 134 VALIDATION.md compliant | manual check | `grep nyquist_compliant .planning/phases/134-*/134-VALIDATION.md` | ✅ | ⬜ pending |
| 143-04-01 | 01 | 4 | Phase 135 Containerfile static tests | unit | `cd puppeteer && pytest tests/test_containerfile_validation.py -x -q` | ❌ W0 | ⬜ pending |
| 143-04-02 | 01 | 4 | Phase 135 resource limits compose tests | unit | `cd puppeteer && pytest tests/test_compose_validation.py -x -q` | ✅ | ⬜ pending |
| 143-04-03 | 01 | 4 | Phase 135 VALIDATION.md compliant | manual check | `grep nyquist_compliant .planning/phases/135-*/135-VALIDATION.md` | ✅ | ⬜ pending |
| 143-05-01 | 01 | 5 | Phase 136 user injection foundry tests | unit | `cd puppeteer && pytest tests/test_foundry.py -x -q` | ✅ | ⬜ pending |
| 143-05-02 | 01 | 5 | Phase 136 VALIDATION.md compliant | manual check | `grep nyquist_compliant .planning/phases/136-*/136-VALIDATION.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_security_capabilities.py` — Phase 133 cap_drop/no-new-privileges/Postgres loopback static + live tests
- [ ] `puppeteer/tests/test_containerfile_validation.py` — Phase 135 Containerfile package removal static tests (if not already in test_compose_validation.py)

*All other test infrastructure already exists.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VALIDATION.md frontmatter update | Phase compliance tracking | File write, no assertion target | `grep "nyquist_compliant: true"` in each phase's VALIDATION.md after tests pass |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

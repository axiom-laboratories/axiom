---
phase: 144
slug: nyquist-validation-ee-features
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 144 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (puppeteer), pytest (axiom-licenses) |
| **Config file** | `puppeteer/pytest.ini` (or pyproject.toml) |
| **Quick run command** | `cd puppeteer && pytest tests/test_licence_service.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_licence_service.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q && cd ../axiom-licenses && pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 144-01-01 | 01 | 1 | Phase 138 green | unit | `cd puppeteer && pytest tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 144-01-02 | 01 | 1 | Phase 137 compliant | unit | `cd puppeteer && pytest tests/test_ee_manifest.py -x -q` | ✅ | ⬜ pending |
| 144-01-03 | 01 | 1 | Phase 139 compliant | unit | `cd puppeteer && pytest tests/test_ee_manifest.py tests/test_encryption_key_enforcement.py -x -q` | ✅ | ⬜ pending |
| 144-01-04 | 01 | 2 | Phase 140 compliant | unit | `cd axiom-licenses && pytest tests/tools/ -x -q` | ✅ | ⬜ pending |
| 144-01-05 | 01 | 2 | Final regression | unit | `cd puppeteer && pytest -x -q && cd ../axiom-licenses && pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

All test files already exist; this phase only fixes stale test expectations in Phase 138 and marks VALIDATION.md files compliant.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

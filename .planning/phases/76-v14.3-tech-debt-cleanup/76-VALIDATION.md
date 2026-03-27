---
phase: 76
slug: v14-3-tech-debt-cleanup
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
validated: 2026-03-27
---

# Phase 76 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest agent_service/tests/test_licence.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest agent_service/tests/test_licence.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 76-01-01 | 01 | 1 | Tech Debt #1 | unit | `cd puppeteer && pytest agent_service/tests/test_licence.py -v` | ✅ | ✅ CI-gated (skips locally: musllinux EE wheel) |
| 76-01-02 | 01 | 1 | Tech Debt #2 | manual | `grep API_KEY compose.cold-start.yaml` | ✅ | ✅ confirmed CLEAN |
| 76-01-03 | 01 | 1 | Tech Debt #3 | manual | `ls puppeteer/agent_service/services/__pycache__/vault_service*.pyc` | ✅ | ✅ confirmed GONE |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| API_KEY removed from compose | Tech Debt #2 | Grep check, no runtime test | `grep API_KEY compose.cold-start.yaml` — must return no match ✅ confirmed 2026-03-27 |
| vault_service .pyc deleted | Tech Debt #3 | Filesystem check | `ls puppeteer/agent_service/services/__pycache__/vault_service*.pyc` — must return no such file ✅ confirmed 2026-03-27 |
| test_licence.py: EE tests run in CI | Tech Debt #1 | musllinux EE wheel not installable on glibc dev host | Tests skip locally via `pytest.importorskip("ee.plugin")` — correct behaviour. Will execute in CI Alpine container. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-27 — test_licence.py CI-gated (EE wheel: musllinux-only, skip on glibc dev host is correct); compose.cold-start.yaml CLEAN; vault_service.pyc GONE

---

## Validation Audit 2026-03-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Automated tests | 1 file (CI-gated, skips locally by design) |
| Manual confirmations | 2 (API_KEY clean, pyc gone) |

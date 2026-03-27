---
phase: 76
slug: v14-3-tech-debt-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
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
| 76-01-01 | 01 | 1 | Tech Debt #1 | unit | `cd puppeteer && pytest agent_service/tests/test_licence.py -v` | ✅ | ⬜ pending |
| 76-01-02 | 01 | 1 | Tech Debt #2 | manual | `grep API_KEY puppeteer/compose.cold-start.yaml` | ✅ | ⬜ pending |
| 76-01-03 | 01 | 1 | Tech Debt #3 | manual | `ls puppeteer/agent_service/services/__pycache__/vault_service*.pyc 2>/dev/null && echo EXISTS || echo GONE` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| API_KEY removed from compose | Tech Debt #2 | Grep check, no runtime test | `grep API_KEY puppeteer/compose.cold-start.yaml` — must return no match |
| vault_service .pyc deleted | Tech Debt #3 | Filesystem check | `ls puppeteer/agent_service/services/__pycache__/vault_service*.pyc` — must return no such file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

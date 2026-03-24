---
phase: 55
slug: verification-docs-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (backend), Python Playwright (frontend UI) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py -v` |
| **Full suite command** | `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest` |
| **Estimated runtime** | ~30 seconds (unit), ~60 seconds (Playwright) |

---

## Sampling Rate

- **After every task commit:** Run `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py -v`
- **After every plan wave:** Run `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest`
- **Before `/gsd:verify-work`:** Full suite must be green + Playwright SCHED-03 evidence captured
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | SCHED-01 | unit | `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py -k "draft or resign" -v` | ✅ | ⬜ pending |
| 55-01-02 | 01 | 1 | SCHED-02 | unit | `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py::test_draft_skip_log_message -v` | ✅ | ⬜ pending |
| 55-01-03 | 01 | 1 | SCHED-03 | Playwright | `python mop_validation/scripts/test_sched03_modal.py` | ❌ Wave 0 | ⬜ pending |
| 55-01-04 | 01 | 1 | SCHED-04 | unit | `docker compose -f puppeteer/compose.server.yaml exec agent python -m pytest agent_service/tests/test_scheduler_service.py::test_draft_transition_creates_alert -v` | ✅ | ⬜ pending |
| 55-02-01 | 02 | 2 | RT-06 | manual-only | N/A | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/test_sched03_modal.py` — Playwright test for SCHED-03 modal (confirmation modal visible before DRAFT save); converts the last manual-only verification from Phase 48 into automated evidence

*All other tests use existing infrastructure — no additional Wave 0 installs required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RT-06 checkbox and traceability update | RT-06 | Documentation edit — no executable behavior | Review REQUIREMENTS.md: RT-06 shows `[x]`, Status=Dropped, Phase=47/55 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

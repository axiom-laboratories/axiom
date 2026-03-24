---
phase: 52
slug: queue-visibility-node-drawer-and-draining
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/ && cd dashboard && npm run test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 1 | VIS-01 | unit | `cd puppeteer && pytest tests/test_dispatch_diagnosis.py -x -q` | ❌ W0 | ⬜ pending |
| 52-01-02 | 01 | 1 | VIS-01 | unit | `cd puppeteer && pytest tests/test_dispatch_diagnosis.py -x -q` | ❌ W0 | ⬜ pending |
| 52-01-03 | 01 | 1 | VIS-01 | unit | `cd puppeteer && pytest tests/test_dispatch_diagnosis.py -x -q` | ❌ W0 | ⬜ pending |
| 52-02-01 | 02 | 1 | VIS-03 | unit | `cd puppeteer && pytest tests/test_draining.py -x -q` | ❌ W0 | ⬜ pending |
| 52-02-02 | 02 | 1 | VIS-03 | unit | `cd puppeteer && pytest tests/test_draining.py -x -q` | ❌ W0 | ⬜ pending |
| 52-02-03 | 02 | 1 | VIS-04 | unit | `cd puppeteer && pytest tests/test_draining.py -x -q` | ❌ W0 | ⬜ pending |
| 52-03-01 | 03 | 2 | VIS-02 | integration | `cd puppeteer && pytest tests/test_queue_view.py -x -q` | ❌ W0 | ⬜ pending |
| 52-03-02 | 03 | 2 | VIS-02 | integration | `cd puppeteer && pytest tests/test_queue_view.py -x -q` | ❌ W0 | ⬜ pending |
| 52-04-01 | 04 | 2 | VIS-01,VIS-02,VIS-03,VIS-04 | e2e | `python ~/Development/mop_validation/scripts/test_playwright.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_dispatch_diagnosis.py` — stubs for VIS-01 (diagnosis endpoint + WebSocket event)
- [ ] `puppeteer/tests/test_draining.py` — stubs for VIS-03/VIS-04 (DRAINING status, guard points, no-dispatch)
- [ ] `puppeteer/tests/test_queue_view.py` — stubs for VIS-02 (Queue endpoint, recency filter, live update)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Diagnosis callout refreshes live in PENDING drawer via WebSocket | VIS-01 | Requires live WebSocket session observation | Dispatch a job with no eligible nodes; watch drawer for auto-updating plain-English message |
| Queue view updates in real-time without page refresh | VIS-02 | Requires browser observation of WebSocket-driven update | Open Queue view, dispatch a job from another tab, confirm row appears without refresh |
| DRAINING badge visible in Queue view on affected jobs | VIS-04 | UI-only visual verification | Set a node to DRAINING; confirm badge appears on its RUNNING/PENDING jobs in Queue view |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

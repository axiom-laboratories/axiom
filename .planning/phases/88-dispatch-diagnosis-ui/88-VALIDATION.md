---
phase: 88
slug: dispatch-diagnosis-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 88 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/ && cd dashboard && npm run test` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run full suite (backend pytest + frontend vitest)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 88-01-01 | 01 | 1 | DIAG-02 | unit | `cd puppeteer && pytest tests/ -k "diagnosis" -x -q` | ⬜ pending |
| 88-01-02 | 01 | 1 | DIAG-01, DIAG-02 | unit | `cd puppeteer && pytest tests/ -k "bulk_diagnosis" -x -q` | ⬜ pending |
| 88-02-01 | 02 | 2 | DIAG-01, DIAG-03 | unit | `cd puppeteer/dashboard && npm run test -- --run` | ⬜ pending |
| 88-02-02 | 02 | 2 | DIAG-01, DIAG-03 | unit | `cd puppeteer/dashboard && npm run test -- --run` | ⬜ pending |
| 88-02-03 | 02 | 2 | DIAG-03 | unit | `cd puppeteer/dashboard && npm run test -- --run` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No new test infrastructure needed. Existing `pytest` and `vitest` setups cover all phase requirements.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Amber left border visible on PENDING row | DIAG-01 | CSS visual rendering | In Docker stack, navigate to Jobs view with a PENDING job; verify amber left border and sub-text appear |
| Diagnosis updates without page reload | DIAG-03 | Live UI polling | Submit a job, watch Status cell; within 10s diagnosis text should appear without refresh |
| Manual refresh button triggers immediate update | DIAG-03 | User interaction | Click refresh icon in Queue Monitor header; verify diagnosis text updates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

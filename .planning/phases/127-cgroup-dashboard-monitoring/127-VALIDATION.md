---
phase: 127
slug: cgroup-dashboard-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 127 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (existing) |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npm run test -- src/views/__tests__/Nodes.test.tsx src/views/__tests__/Admin.test.tsx -x` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npm run test -- src/views/__tests__/Nodes.test.tsx src/views/__tests__/Admin.test.tsx -x`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 127-01-01 | 01 | 1 | CGRP-03 | component | `npm run test -- Nodes.test.tsx -t "cgroup badge"` | ❌ W0 | ⬜ pending |
| 127-01-02 | 01 | 1 | CGRP-03 | component | `npm run test -- Nodes.test.tsx -t "cgroup tooltip"` | ❌ W0 | ⬜ pending |
| 127-01-03 | 01 | 1 | CGRP-04 | component | `npm run test -- Nodes.test.tsx -t "degradation banner"` | ❌ W0 | ⬜ pending |
| 127-01-04 | 01 | 1 | CGRP-04 | component | `npm run test -- Nodes.test.tsx -t "degradation banner hidden"` | ❌ W0 | ⬜ pending |
| 127-02-01 | 02 | 1 | CGRP-04 | component | `npm run test -- Admin.test.tsx -t "system health bar"` | ❌ W0 | ⬜ pending |
| 127-E2E | — | — | CGRP-03/04 | e2e | `python ~/Development/mop_validation/scripts/test_playwright.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/views/__tests__/Nodes.test.tsx` — stubs for cgroup badge rendering, tooltip, degradation banner
- [ ] `src/views/__tests__/Admin.test.tsx` — stubs for System Health tab stacked bar

*Existing Vitest infrastructure covers framework setup. Only new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E cgroup badges in Docker stack | CGRP-03 | Requires live Docker nodes with cgroup data | Run `test_playwright.py`, verify badge colors match node cgroup versions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

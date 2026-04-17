---
phase: 157
slug: close-deferred-technical-debt-fix-frontend-test-infrastructure-failures-and-low-priority-gaps-from-v23-0-state-of-nation-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 157 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) + pytest 7.x (backend) |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` / `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Workflows.test.tsx src/views/__tests__/WorkflowRunDetail.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test && cd .. && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Workflows.test.tsx src/views/__tests__/WorkflowRunDetail.test.tsx`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test && cd .. && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 157-01-01 | 01 | 1 | FRONTEND-TEST | unit | `npx vitest run src/views/__tests__/Workflows.test.tsx` | ✅ | ⬜ pending |
| 157-01-02 | 01 | 1 | FRONTEND-TEST | unit | `npx vitest run src/views/__tests__/WorkflowRunDetail.test.tsx` | ✅ | ⬜ pending |
| 157-01-03 | 01 | 1 | FRONTEND-TEST | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ | ⬜ pending |
| 157-02-01 | 02 | 2 | BACKEND-MIN6 | unit | `cd puppeteer && pytest tests/test_node_stats.py` | ❌ W0 | ⬜ pending |
| 157-02-02 | 02 | 2 | BACKEND-MIN7 | unit | `cd puppeteer && pytest tests/test_foundry.py -k pruning` | ✅ | ⬜ pending |
| 157-02-03 | 02 | 2 | BACKEND-MIN8 | unit | `cd puppeteer && pytest tests/test_auth.py -k permission_cache` | ❌ W0 | ⬜ pending |
| 157-02-04 | 02 | 2 | BACKEND-WARN8 | unit | `cd puppeteer && pytest tests/test_nodes.py -k node_scan_order` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_node_stats.py` — regression tests for MIN-6 SQLite NodeStats pruning compat
- [ ] `puppeteer/tests/test_auth.py` additions — MIN-8 permission cache behavior tests
- [ ] `puppeteer/tests/test_nodes.py` additions — WARN-8 node ID scan ordering tests

*Existing frontend test files cover all frontend requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

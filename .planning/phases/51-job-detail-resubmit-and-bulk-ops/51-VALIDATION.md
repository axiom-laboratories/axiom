---
phase: 51
slug: job-detail-resubmit-and-bulk-ops
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (backend) / Vitest + React Testing Library (frontend) |
| **Config file** | `puppeteer/` (pytest) / `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest agent_service/tests/test_job51*.py -x` |
| **Full suite command** | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest agent_service/tests/test_job51*.py -x` (backend) or `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` (frontend)
- **After every plan wave:** Run `cd puppeteer && pytest && cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 0 | JOB-05 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_resubmit.py -x` | ❌ W0 | ⬜ pending |
| 51-01-02 | 01 | 0 | BULK-02,03,04 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_bulk.py -x` | ❌ W0 | ⬜ pending |
| 51-02-01 | 02 | 1 | JOB-05 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_resubmit.py -x` | ❌ W0 | ⬜ pending |
| 51-02-02 | 02 | 1 | JOB-05 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_resubmit.py -x` | ❌ W0 | ⬜ pending |
| 51-02-03 | 02 | 1 | BULK-02 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_bulk.py -x` | ❌ W0 | ⬜ pending |
| 51-02-04 | 02 | 1 | BULK-03 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_bulk.py -x` | ❌ W0 | ⬜ pending |
| 51-02-05 | 02 | 1 | BULK-04 | unit | `cd puppeteer && pytest agent_service/tests/test_job51_bulk.py -x` | ❌ W0 | ⬜ pending |
| 51-03-01 | 03 | 2 | JOB-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ extend | ⬜ pending |
| 51-03-02 | 03 | 2 | JOB-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ extend | ⬜ pending |
| 51-04-01 | 04 | 2 | JOB-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ extend | ⬜ pending |
| 51-04-02 | 04 | 2 | JOB-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ extend | ⬜ pending |
| 51-05-01 | 05 | 3 | BULK-01 | unit | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/JobsBulkSelect.test.tsx` | ❌ W0 | ⬜ pending |
| 51-05-02 | 05 | 3 | BULK-01,02,03,04 | unit | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/JobsBulkSelect.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/agent_service/tests/test_job51_resubmit.py` — stubs for JOB-05 (resubmit endpoint, resubmit rejection for invalid status)
- [ ] `puppeteer/agent_service/tests/test_job51_bulk.py` — stubs for BULK-02 (bulk-cancel), BULK-03 (bulk-resubmit), BULK-04 (bulk-delete)
- [ ] `puppeteer/migration_v14.sql` — `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR`
- [ ] `puppeteer/dashboard/src/components/ui/checkbox.tsx` — if not already present (check before creating)
- [ ] Extend `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` — inline output drawer render, checkbox column presence, GuidedDispatchCard initialValues pre-population
- [ ] `puppeteer/dashboard/src/components/__tests__/JobsBulkSelect.test.tsx` — stub for BULK-01 checkbox/bulk bar

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inline resubmit confirmation button transform (button → "Confirm/Cancel") | JOB-05 | Visual/interactive animation state | Open job detail drawer for a FAILED job, click Resubmit, verify button transforms inline |
| Highlight ring on newly resubmitted job in list | JOB-05 | CSS transition timing | After one-click resubmit, verify new job scrolls into view with highlight ring |
| SECURITY_REJECTED amber callout renders in drawer | JOB-04 | Requires a real SECURITY_REJECTED job | Submit an unsigned job, open its drawer, verify amber callout with plain-English reason |
| Floating bulk action bar appears/disappears | BULK-01 | Complex state interaction | Select checkboxes, verify floating bar replaces filter bar; clear selection, verify filter bar returns |
| Bulk confirmation dialog shows correct skip counts | BULK-02,03,04 | Requires mixed-status selection | Select jobs of mixed status, click bulk action, verify dialog count + skipped count |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

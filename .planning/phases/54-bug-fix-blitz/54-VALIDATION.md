---
phase: 54
slug: bug-fix-blitz
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Vitest + @testing-library/react (frontend) |
| **Config file** | `puppeteer/pytest.ini` (backend) / `puppeteer/dashboard/vite.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` |
| **Full suite command** | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` (backend tasks) or `npx vitest run src/views/__tests__/Jobs.test.tsx` (frontend tasks)
- **After every plan wave:** Run full suite (both backend + frontend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 0 | JOB-04, JOB-05 | unit (pytest) | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 1 | JOB-04, JOB-05 | unit (pytest) | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 0 | VIS-02 | unit (vitest) | `npx vitest run src/views/__tests__/Queue.test.tsx` | ❌ W0 | ⬜ pending |
| 54-02-02 | 02 | 1 | JOB-01, RT-01, RT-02 | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ | ⬜ pending |
| 54-02-03 | 02 | 1 | VIS-02 | unit (vitest) | `npx vitest run src/views/__tests__/Queue.test.tsx` | ❌ W0 | ⬜ pending |
| 54-02-04 | 02 | 1 | SRCH-10 | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_list_jobs_retry_fields.py` — stubs for JOB-04, JOB-05 (INT-04 backend: list_jobs() retry fields + originating_guid)
- [ ] `puppeteer/dashboard/src/views/__tests__/Queue.test.tsx` — stubs for VIS-02 (INT-02 URL assertion: no double /api prefix)

*All other test coverage is additions to existing test files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Guided form job executes end-to-end on a live node | JOB-01, RT-01, RT-02 | Requires live Docker stack + enrolled node | Submit Python/Bash/PowerShell job via UI; confirm node receives non-empty script_content and execution result returns |
| Job detail drawer shows retry state | JOB-04, JOB-05 | Requires a job that has been retried | Trigger a retryable failure; open drawer; confirm retry_count, max_retries, retry_after, originating_guid render |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

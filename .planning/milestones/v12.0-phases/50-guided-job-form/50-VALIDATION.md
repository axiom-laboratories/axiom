---
phase: 50
slug: guided-job-form
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 3.0.5 + @testing-library/react 16.2 |
| **Config file** | `puppeteer/dashboard/package.json` (`"test": "vitest"`) + `src/test/setup.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 0 | JOB-01, JOB-02, JOB-03 | unit stub | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-02-01 | 02 | 1 | JOB-01 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-02-02 | 02 | 1 | JOB-01 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-02-03 | 02 | 1 | JOB-01 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-03-01 | 03 | 1 | JOB-02 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-03-02 | 03 | 1 | JOB-02 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-04-01 | 04 | 2 | JOB-03 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-04-02 | 04 | 2 | JOB-03 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |
| 50-04-03 | 04 | 2 | JOB-03 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` — stubs for JOB-01, JOB-02, JOB-03 (guided form render, JSON preview, advanced mode toggle)

*Note: A dedicated `GuidedDispatchCard.test.tsx` is acceptable but not required — covering via Jobs.test.tsx mount is sufficient.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full dispatch flow end-to-end (sign + submit) | JOB-01 | Requires live stack with signed job | Run `python ~/Development/mop_validation/scripts/test_local_stack.py` after deploy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

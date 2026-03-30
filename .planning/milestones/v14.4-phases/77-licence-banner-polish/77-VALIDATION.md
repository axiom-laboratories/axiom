---
phase: 77
slug: licence-banner-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 77 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (project dependency) |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test -- --run` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 77-01-01 | 01 | 0 | BNR-03, BNR-05 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ❌ W0 | ⬜ pending |
| 77-01-02 | 01 | 1 | BNR-01, BNR-02 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ✅ extend | ⬜ pending |
| 77-01-03 | 01 | 1 | BNR-03, BNR-04 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ❌ W0 | ⬜ pending |
| 77-01-04 | 01 | 1 | BNR-05 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/layouts/__tests__/MainLayout.test.tsx` — refactor `getUser` mock to use `vi.fn()` for per-test overrides (BNR-05)
- [ ] `src/layouts/__tests__/MainLayout.test.tsx` — add `sessionStorage.clear()` to `beforeEach` (BNR-03)
- [ ] `src/layouts/__tests__/MainLayout.test.tsx` — add test stubs: operator+GRACE hidden (BNR-05), viewer+DEGRADED_CE hidden (BNR-05), admin+GRACE dismiss (BNR-03), DEGRADED_CE has no X button (BNR-04)

*All test infrastructure exists — framework, config, setup file, and target test file are present. Only mock refactor and new test cases are needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dismiss persists across SPA route navigation within same tab | BNR-03 | jsdom doesn't test real browser tab lifecycle | 1. Log in as admin. 2. Trigger grace state (mock or real). 3. Dismiss the banner. 4. Navigate to a different route. 5. Confirm banner is not shown. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

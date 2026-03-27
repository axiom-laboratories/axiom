---
phase: 74
slug: fix-ee-licence-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 74 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + @testing-library/react |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run src/hooks src/views/__tests__/Admin.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run src/hooks src/views/__tests__/Admin.test.tsx`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 74-01-01 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/hooks` | ❌ W0 | ⬜ pending |
| 74-01-02 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin.test.tsx` | ❌ W0 | ⬜ pending |
| 74-01-03 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts` | ❌ W0 | ⬜ pending |
| 74-01-04 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/hooks` | ❌ W0 | ⬜ pending |
| 74-01-05 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin.test.tsx` | ❌ W0 | ⬜ pending |
| 74-01-06 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/dashboard/src/hooks/__tests__/useLicence.test.ts` — stubs for LIC-06 hook mapping + `isEnterprise` computed field
- [ ] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — stubs for LIC-06 LicenceSection rendering (valid/grace/expired/ce states)
- [ ] `puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx` — stubs for LIC-06 EE badge and grace/expired banner

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-dismissible banner visible on non-Admin pages | LIC-06 | Layout integration — requires full app context | Navigate to /nodes while EE licence in grace state; confirm amber banner visible at top |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

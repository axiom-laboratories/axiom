---
phase: 74
slug: fix-ee-licence-display
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
validated: 2026-03-27
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
| 74-01-01 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/hooks/__tests__/useLicence.test.ts` | ✅ | ✅ green |
| 74-01-02 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin.test.tsx` | ✅ | ✅ green |
| 74-01-03 | 01 | 0 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ✅ | ✅ green |
| 74-01-04 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/hooks/__tests__/useLicence.test.ts` | ✅ | ✅ green |
| 74-01-05 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Admin.test.tsx` | ✅ | ✅ green |
| 74-01-06 | 01 | 1 | LIC-06 | unit | `cd puppeteer/dashboard && npx vitest run src/layouts/__tests__/MainLayout.test.tsx` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `puppeteer/dashboard/src/hooks/__tests__/useLicence.test.ts` — stubs for LIC-06 hook mapping + `isEnterprise` computed field
- [x] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — stubs for LIC-06 LicenceSection rendering (valid/grace/expired/ce states)
- [x] `puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx` — stubs for LIC-06 EE badge and grace/expired banner

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-dismissible banner visible on non-Admin pages | LIC-06 | Layout integration — requires full app context | Navigate to /nodes while EE licence in grace state; confirm amber banner visible at top |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-27 — 15/15 tests passing (useLicence: 4, Admin: 6, MainLayout: 5)

---

## Validation Audit 2026-03-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests passing | 15 |

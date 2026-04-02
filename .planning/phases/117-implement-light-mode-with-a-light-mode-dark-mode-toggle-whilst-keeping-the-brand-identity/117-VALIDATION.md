---
phase: 117
slug: implement-light-mode-with-a-light-mode-dark-mode-toggle-whilst-keeping-the-brand-identity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 117 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.0.5 (React Testing Library) |
| **Config file** | `vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run` |
| **Full suite command** | `cd puppeteer/dashboard && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run`
- **After every plan wave:** Run `cd puppeteer/dashboard && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 117-01-01 | 01 | 0 | Theme hook | Unit | `npx vitest run src/hooks/__tests__/useTheme.test.ts` | ❌ W0 | ⬜ pending |
| 117-01-02 | 01 | 0 | Toggle component | Component | `npx vitest run src/components/__tests__/ThemeToggle.test.tsx` | ❌ W0 | ⬜ pending |
| 117-01-03 | 01 | 0 | CSS variable scoping | Integration | `npx vitest run src/__tests__/theme.integration.test.ts` | ❌ W0 | ⬜ pending |
| 117-02-01 | 02 | 1 | localStorage persistence | Unit | `npx vitest run src/hooks/__tests__/useTheme.test.ts -t "persists"` | ❌ W0 | ⬜ pending |
| 117-02-02 | 02 | 1 | Dark class applies correctly | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "dark mode"` | ❌ W0 | ⬜ pending |
| 117-03-01 | 03 | 2 | Toast theme updates | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "toast"` | ❌ W0 | ⬜ pending |
| 117-03-02 | 03 | 2 | Recharts tooltips themed | Integration | `npx vitest run src/__tests__/theme.integration.test.ts -t "recharts"` | ❌ W0 | ⬜ pending |
| 117-04-01 | 04 | 3 | FOWT prevention | E2E | `python mop_validation/scripts/test_playwright.py -k "theme"` | ❌ W0 | ⬜ pending |
| 117-04-02 | 04 | 3 | Hardcoded classes migrated | Smoke | `grep -r "bg-zinc-9\|text-zinc-4" puppeteer/dashboard/src --include="*.tsx"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/hooks/__tests__/useTheme.test.ts` — stubs for theme state, localStorage sync, DOM class updates
- [ ] `src/components/__tests__/ThemeToggle.test.tsx` — stubs for toggle rendering, click handlers, icon rotation
- [ ] `src/__tests__/theme.integration.test.ts` — stubs for CSS variable scoping, toast theming, recharts theming
- [ ] Playwright E2E test case in `mop_validation/scripts/test_playwright.py` — FOWT prevention, toggle behavior, persistence

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Light mode visual appearance | Brand identity | Visual quality subjective | Toggle to light mode, verify stone palette, pink accents, no clashing colors |
| Toggle animation smoothness | UX polish | Animation timing is visual | Toggle back and forth, verify 200ms smooth transition, no jarring flash |
| Login page stays dark | Brand experience | Route-specific styling | Navigate to /login, verify dark theme regardless of localStorage setting |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

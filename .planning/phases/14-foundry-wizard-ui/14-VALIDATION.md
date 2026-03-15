---
phase: 14
slug: foundry-wizard-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (already configured) |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/BlueprintWizard.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run src/components/__tests__/BlueprintWizard.test.tsx`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | WIZ-01, WIZ-02, WIZ-03 | unit (RTL) | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/BlueprintWizard.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/dashboard/src/components/__tests__/BlueprintWizard.test.tsx` — covers WIZ-01, WIZ-02, WIZ-03 (does not exist; must be created before any implementation plan runs)

*Existing infrastructure covers all other phase requirements (vitest, @testing-library/react, @testing-library/jest-dom present; `puppeteer/dashboard/src/test/setup.ts` already configured).*

---

## Test Cases Required

| Req ID | Behavior | Test Type |
|--------|----------|-----------|
| WIZ-01 | Wizard renders all 5 steps and submits a valid blueprint payload without JSON input | unit (RTL) |
| WIZ-01 | `blueprintToJson` helper produces correct schema from Composition state | unit (pure) |
| WIZ-02 | Selecting a tool with `runtime_dependencies` adds packages to state and fires toast | unit (RTL) |
| WIZ-02 | De-selecting a tool does NOT remove its auto-injected packages (permissive model) | unit (RTL) |
| WIZ-03 | `is_vulnerable: true` ingredient renders "Vulnerable" badge in Step 3 | unit (RTL) |
| WIZ-03 | `mirror_status !== 'MIRRORED'` ingredient renders "Sync Pending" amber badge | unit (RTL) |
| All | Wizard resets state on re-open (open prop toggles) | unit (RTL) |
| All | "Advanced (JSON)" toggle converts wizard state to readable JSON text | unit (RTL) |
| All | OS-family filter in Step 4 only shows tools with matching `base_os_family` | unit (RTL) |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Side-by-side JSON diff in clone mode | WIZ-01 | Diff visual rendering hard to assert in RTL | Open wizard in clone mode, modify a field, verify Review step shows highlighted changes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

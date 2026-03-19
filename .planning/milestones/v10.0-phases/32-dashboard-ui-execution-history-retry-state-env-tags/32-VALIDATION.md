---
phase: 32
slug: dashboard-ui-execution-history-retry-state-env-tags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + @testing-library/react |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-W0-01 | Wave 0 | 0 | OUTPUT-03 | unit | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/ExecutionLogModal.test.tsx` | ❌ W0 | ⬜ pending |
| 32-W0-02 | Wave 0 | 0 | OUTPUT-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/History.test.tsx` | ❌ W0 | ⬜ pending |
| 32-W0-03 | Wave 0 | 0 | ENVTAG-03 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Nodes.test.tsx` | ❌ W0 | ⬜ pending |
| 32-W0-04 | Wave 0 | 0 | OUTPUT-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/JobDefinitions.test.tsx` | ✅ extend | ⬜ pending |
| 32-01-01 | 01 | 1 | OUTPUT-03 | unit | `cd puppeteer/dashboard && npx vitest run src/components/__tests__/ExecutionLogModal.test.tsx` | ❌ W0 | ⬜ pending |
| 32-01-02 | 01 | 1 | OUTPUT-03 | unit | same file | ❌ W0 | ⬜ pending |
| 32-01-03 | 01 | 1 | RETRY-03 | unit | same file | ❌ W0 | ⬜ pending |
| 32-02-01 | 02 | 1 | OUTPUT-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/JobDefinitions.test.tsx` | ✅ extend | ⬜ pending |
| 32-02-02 | 02 | 1 | OUTPUT-04 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/History.test.tsx` | ❌ W0 | ⬜ pending |
| 32-03-01 | 03 | 1 | ENVTAG-03 | unit | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Nodes.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/dashboard/src/components/__tests__/ExecutionLogModal.test.tsx` — stubs for OUTPUT-03 (modal header attestation, output_log labels), RETRY-03 (attempt N of M badge)
- [ ] `puppeteer/dashboard/src/views/__tests__/History.test.tsx` — stubs for OUTPUT-04 (definition selector dropdown)
- [ ] `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` — stubs for ENVTAG-03 (env_tag badge, env filter)
- [ ] Extend `puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx` — add definition selection + history panel stubs for OUTPUT-04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal-style output renders colour-coded stderr vs stdout visually | OUTPUT-03 | CSS colour correctness requires visual inspection | Open ExecutionLogModal in browser; verify stderr lines appear in red/amber, stdout in white |
| Attestation VERIFIED badge displays correctly in modal header | OUTPUT-03 | Visual badge rendering | Open modal for a verified execution; confirm "VERIFIED" badge visible in header |
| History panel expands below definitions table on click | OUTPUT-04 | Interaction flow requires browser | Click a job definition row; verify history panel appears below table |
| Env tag filter hides/shows nodes in real-time | ENVTAG-03 | Filter interaction requires DOM | Select DEV in env filter; verify only DEV-tagged nodes appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 155
slug: visual-dag-editor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 155 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (^3.0.5) + @testing-library/react (^16.2.0) |
| **Config file** | `puppeteer/dashboard/vitest.config.ts` (or inferred from vite.config.ts) |
| **Quick run command** | `cd puppeteer/dashboard && npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run focused file test (e.g. `npm test -- --run src/components/__tests__/{component}.test.tsx`)
- **After every plan wave:** Run full suite `cd puppeteer/dashboard && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green + `npm run build` succeeds
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 155-W0-01 | W0 | 0 | UI-07 | unit | `npm test -- --run src/utils/__tests__/dagValidation.test.tsx` | ❌ W0 | ⬜ pending |
| 155-W0-02 | W0 | 0 | UI-06 | component | `npm test -- --run src/components/__tests__/WorkflowNodePalette.test.tsx` | ❌ W0 | ⬜ pending |
| 155-W0-03 | W0 | 0 | UI-06 | component | `npm test -- --run src/components/__tests__/ScriptNodeJobSelector.test.tsx` | ❌ W0 | ⬜ pending |
| 155-W0-04 | W0 | 0 | UI-07 | component | `npm test -- --run src/components/__tests__/IfGateConfigDrawer.test.tsx` | ❌ W0 | ⬜ pending |
| 155-W0-05 | W0 | 0 | UI-07 | unit | `npm test -- --run src/hooks/__tests__/useDAGValidation.test.tsx` | ❌ W0 | ⬜ pending |
| 155-W0-06 | W0 | 0 | UI-06 | unit | `npm test -- --run src/hooks/__tests__/useWorkflowEdit.test.tsx` | ❌ W0 | ⬜ pending |
| 155-01-01 | 01 | 1 | UI-07 | unit | `npm test -- --run src/utils/__tests__/dagValidation.test.tsx` | ❌ W0 | ⬜ pending |
| 155-01-02 | 01 | 1 | UI-06 | component | `npm test -- --run src/components/__tests__/WorkflowNodePalette.test.tsx` | ❌ W0 | ⬜ pending |
| 155-01-03 | 01 | 1 | UI-06 | component | `npm test -- --run src/components/__tests__/ScriptNodeJobSelector.test.tsx` | ❌ W0 | ⬜ pending |
| 155-01-04 | 01 | 1 | UI-07 | component | `npm test -- --run src/components/__tests__/IfGateConfigDrawer.test.tsx` | ❌ W0 | ⬜ pending |
| 155-02-01 | 02 | 2 | UI-06 | integration | `npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` | ✅ existing | ⬜ pending |
| 155-02-02 | 02 | 2 | UI-07 | integration | `npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` | ✅ existing | ⬜ pending |
| 155-02-03 | 02 | 2 | UI-06 | component | `npm test -- --run src/components/__tests__/DAGCanvas.test.tsx` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/utils/__tests__/dagValidation.test.tsx` — DFS cycle detection, depth calculation, cycle path extraction (12+ test cases)
- [ ] `src/utils/dagValidation.ts` — validateDAG() function with cycle detection and depth calculation
- [ ] `src/components/__tests__/WorkflowNodePalette.test.tsx` — drag-start event, node type data, render all 6 types
- [ ] `src/components/WorkflowNodePalette.tsx` — draggable chips component
- [ ] `src/components/__tests__/ScriptNodeJobSelector.test.tsx` — popover trigger, job search, selection handler
- [ ] `src/components/ScriptNodeJobSelector.tsx` — job search popover (or Sheet if popover unavailable)
- [ ] `src/components/__tests__/IfGateConfigDrawer.test.tsx` — form submission, operator dropdown, config_json serialization
- [ ] `src/components/IfGateConfigDrawer.tsx` — Sheet drawer with structured form fields
- [ ] `src/hooks/__tests__/useDAGValidation.test.tsx` — validation state management, real-time updates on node/edge changes
- [ ] `src/hooks/useDAGValidation.ts` — hook wrapping validateDAG() with state and reactive updates
- [ ] `src/hooks/__tests__/useWorkflowEdit.test.tsx` — edit state, node/edge change handlers, save/cancel logic
- [ ] `src/hooks/useWorkflowEdit.ts` — edit mode state management hook

*All Wave 0 files are stubs/skeletons for test-first development. Implementation in Wave 1+.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag node from palette onto canvas at correct visual position | UI-06 | Playwright DnD coordinate simulation unreliable in CI | Start edit mode; drag START chip onto canvas; verify node appears at drop location |
| IF gate drawer fields visible and usable | UI-07 | Visual layout verification | Click IF gate node in edit mode; verify Sheet opens with field/op/value inputs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

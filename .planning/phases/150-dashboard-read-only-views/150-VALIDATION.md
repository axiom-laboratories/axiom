---
phase: 150
slug: dashboard-read-only-views
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 150 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 3.0.5 + @testing-library/react 16.2.0 |
| **Config file** | `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer/dashboard && npm run test -- --run src/views/__tests__/Workflows.test.tsx` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test -- --run` |
| **Estimated runtime** | ~10–15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npm run test -- --run`
- **After every plan wave:** Run full suite + manual spot-check: open `/workflows`, click a workflow, click a step node, verify drawer opens
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 150-W0-01 | 01 | 0 | UI-01 | unit | `npm run test -- --run src/views/__tests__/Workflows.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-02 | 01 | 0 | UI-01 | unit | `npm run test -- --run src/views/__tests__/WorkflowDetail.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-03 | 01 | 0 | UI-02 UI-04 | unit | `npm run test -- --run src/views/__tests__/WorkflowRunDetail.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-04 | 01 | 0 | UI-01 | unit | `npm run test -- --run src/components/__tests__/DAGCanvas.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-05 | 01 | 0 | UI-01 | unit | `npm run test -- --run src/components/__tests__/WorkflowStepNode.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-06 | 01 | 0 | UI-04 | unit | `npm run test -- --run src/components/__tests__/WorkflowStepDrawer.test.tsx` | ❌ W0 | ⬜ pending |
| 150-W0-07 | 01 | 0 | UI-02 | unit | `npm run test -- --run src/utils/__tests__/workflowStatusUtils.test.ts` | ❌ W0 | ⬜ pending |
| 150-W0-08 | 01 | 0 | UI-02 | integration | `npm run test -- --run src/hooks/__tests__/useWorkflowQuery.test.ts` | ❌ W0 | ⬜ pending |
| 150-W0-09 | 01 | 0 | UI-01 | unit | `npm run test -- --run src/hooks/__tests__/useLayoutedElements.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/views/__tests__/Workflows.test.tsx` — list page (UI-03)
- [ ] `src/views/__tests__/WorkflowDetail.test.tsx` — DAG canvas + run history (UI-01, UI-02, UI-03)
- [ ] `src/views/__tests__/WorkflowRunDetail.test.tsx` — DAG with status overlay + step drawer (UI-02, UI-04)
- [ ] `src/components/__tests__/DAGCanvas.test.tsx` — node/edge rendering (UI-01)
- [ ] `src/components/__tests__/WorkflowStepNode.test.tsx` — node shapes per type (UI-01)
- [ ] `src/components/__tests__/WorkflowStepDrawer.test.tsx` — drawer open, log fetch, unrun message (UI-04)
- [ ] `src/utils/__tests__/workflowStatusUtils.test.ts` — getStatusVariant() + statusColorMap (UI-02)
- [ ] `src/hooks/__tests__/useWorkflowQuery.test.ts` — async fetch + WS cache update (UI-02)
- [ ] `src/hooks/__tests__/useLayoutedElements.test.ts` — dagre layout memoization (UI-01)
- [ ] `package.json` — install `@xyflow/react` + `@dagrejs/dagre` (npm install — not a config gap)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live WS status overlay updates DAG node colors in real time | UI-02 | Requires live backend + WebSocket connection | Start Docker stack, trigger a workflow run, watch DAG canvas for color changes from PENDING→RUNNING→COMPLETED |
| Step log drawer renders real job stdout/stderr | UI-04 | Requires real job execution + log data | Run a workflow with a SCRIPT step, click node in run detail view, verify logs render in drawer |
| Sidebar Workflows link appears and routes correctly | Navigation | DOM integration test | Open dashboard, verify Workflows in sidebar, click to navigate to `/workflows` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

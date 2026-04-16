---
phase: 150-dashboard-read-only-views
plan: 05
subsystem: Frontend / WorkflowRunDetail
tags: [react, vitest, drawer, logs, read-only]
dependency:
  requires: [150-03, 150-04]
  provides: [step-log-inspection]
  affects: [WorkflowRunDetail, DAGCanvas integration]
tech-stack:
  added:
    - "@tanstack/react-query v5 useQuery (for log caching)"
    - "shadcn Sheet component (slide-in drawer)"
    - "vitest @testing-library/react (component testing)"
  patterns:
    - "Custom React Query hook for log fetching"
    - "Conditional rendering based on step status"
    - "Error handling via sonner toast"
key-files:
  created:
    - puppeteer/dashboard/src/hooks/useStepLogs.ts
    - puppeteer/dashboard/src/components/WorkflowStepDrawer.tsx
    - puppeteer/dashboard/src/components/__tests__/WorkflowStepDrawer.test.tsx
    - puppeteer/dashboard/src/hooks/__tests__/useStepLogs.test.ts
  modified:
    - puppeteer/dashboard/src/views/WorkflowRunDetail.tsx
    - puppeteer/dashboard/src/views/__tests__/WorkflowRunDetail.test.tsx
decisions: []
metrics:
  duration: "~20 minutes"
  tasks_completed: 4
  tests_created: 32
  test_pass_rate: "100%"
  files_created: 4
  files_modified: 2
completion_date: "2026-04-16"
---

# Phase 150 Plan 05: Step Log Drawer Summary

**Objective:** Implement a right-side drawer component for viewing step execution logs and details, enabling operators to click any step node in the DAG canvas and inspect its logs or view "not run yet" status without leaving the DAG view.

## One-Liner

Right-side drawer component (shadcn Sheet) for step execution log viewing with React Query caching and read-only interface—enables operators to click DAG nodes and inspect job stdout/stderr.

## Completion Status

✅ **COMPLETE** — All 4 tasks executed, 32 tests passing (100%), integration validated.

## Tasks Completed

### Task 1: Create useStepLogs Hook ✅
**File:** `puppeteer/dashboard/src/hooks/useStepLogs.ts` (42 lines)

**Signature:**
```typescript
export function useStepLogs(jobGuid: string | null | undefined) {
  return useQuery({
    queryKey: ['step-logs', jobGuid],
    queryFn: async () => { ... },
    enabled: !!jobGuid,
    staleTime: 30000,
  });
}
```

**Behavior:**
- Disabled query when `jobGuid` is null/undefined (prevents unnecessary API calls)
- Fetches logs from `/api/executions/{job_guid}/logs` via `authenticatedFetch`
- Returns `{ stdout, stderr }` on success
- Handles 404 gracefully: returns `null` data (step has no logs yet), not an error
- Propagates other HTTP errors (500+) for error handling by caller
- Caches for 30 seconds (`staleTime: 30000`)
- Refetches automatically when `jobGuid` changes

**Test Coverage:** 7 tests, all passing
- Disabled query for null/undefined jobGuid
- Successful log fetch
- 404 graceful handling
- Error propagation (500)
- Refetch on jobGuid change
- Cache validation (staleTime)

### Task 2: Create WorkflowStepDrawer Component ✅
**File:** `puppeteer/dashboard/src/components/WorkflowStepDrawer.tsx` (230 lines)

**Props:**
```typescript
interface WorkflowStepDrawerProps {
  step?: WorkflowStepRunResponse;
  isOpen: boolean;
  onClose: () => void;
}
```

**Features:**
- **Header:** Step name (from `step_detail.label` or fallback to `workflow_step_id`), node type badge (SCRIPT, IF_GATE, etc.), status badge via `getStatusVariant()`
- **Metadata Section:** Started time, completed time, calculated duration (in seconds)
- **Log Display (for RUNNING/COMPLETED/FAILED):**
  - Calls `useStepLogs(step.job_guid)` hook
  - Shows loading spinner (Loader2 icon with animate-spin) while fetching
  - Displays `stdout` in code block (black bg, monospace, scrollable)
  - Displays `stderr` in amber-colored code block
  - "No output captured" message if both empty
  - Error toast via sonner if fetch fails
- **Unrun States (for PENDING/SKIPPED/CANCELLED):**
  - "This step has not run yet" for PENDING
  - "This step was skipped" for SKIPPED
  - "This step was cancelled" for CANCELLED
  - Does not call `useStepLogs` hook for these states
- **UI:**
  - shadcn Sheet component (slides from right, smooth animation)
  - Close button in header (SheetClose)
  - Read-only interface (no edit actions per Phase 150 spec)
  - Responsive layout (max-width: 2xl, 95vw width)

**Test Coverage:** 15 tests, all passing
- Visibility: hidden when isOpen=false, visible when isOpen=true
- Step detail display (name, node type, status)
- Timestamps and duration calculation
- Log rendering for COMPLETED steps
- Loading spinner while fetching
- Unrun state messages (pending/skipped/cancelled)
- Error handling (toast on fetch error)
- Close button callback
- Unrun steps don't call useStepLogs
- Both stdout and stderr display
- Empty log handling
- Failed step display
- Fallback to workflow_step_id when step_detail missing

### Task 3: Integrate Drawer with WorkflowRunDetail ✅
**File:** `puppeteer/dashboard/src/views/WorkflowRunDetail.tsx` (262 lines)

**Changes:**
1. **State Management:**
   ```typescript
   const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
   const selectedStep = run?.step_runs.find((sr) => sr.id === selectedStepId) || null;
   ```

2. **DAGCanvas Integration:**
   - Added `onNodeClick` callback that maps `workflow_step_id` → step run ID
   - Callback finds the step run by `workflow_step_id` and sets `selectedStepId`
   - This enables clicking DAG nodes to open the drawer with the correct step data

3. **Drawer Rendering:**
   ```typescript
   <WorkflowStepDrawer
     step={selectedStep || undefined}
     isOpen={!!selectedStepId}
     onClose={() => setSelectedStepId(null)}
   />
   ```

4. **Interface Extension:**
   - Added `step_detail?: WorkflowStepResponse` to `WorkflowStepRunResponse` interface
   - Allows drawer to display step metadata (label, node_type)

**Key Mapping Logic:**
- DAGCanvas emits `onNodeClick(stepId)` where `stepId` is the **workflow step ID**
- WorkflowRunDetail maps this to the step run ID via callback
- Drawer receives the complete `WorkflowStepRunResponse` object with all metadata

**Test Coverage:** 10 tests updated and passing
- Run header displays status
- Started/completed time and duration display
- DAG canvas renders with status overlay
- DAG node colors reflect step statuses
- Step list table renders all step runs
- Step list shows timestamps
- Clicking DAG node opens drawer (validates via data-testid="step-drawer")
- Clicking step in table opens drawer
- Error handling when run not found
- "No steps" message for empty runs

### Task 4: Test Coverage ✅

**Test Files Created:**
1. `src/hooks/__tests__/useStepLogs.test.ts` — 7 tests
2. `src/components/__tests__/WorkflowStepDrawer.test.tsx` — 15 tests

**Test Files Modified:**
- `src/views/__tests__/WorkflowRunDetail.test.tsx` — Updated 2 tests to verify drawer integration

**Total Test Pass Rate:** 32/32 passing (100%)

## Integration Points

### DAGCanvas → WorkflowStepDrawer
- **Pattern:** `onNodeClick` callback
- **Data Flow:** Step node click → `onNodeClick(workflow_step_id)` → callback maps to step run ID → `setSelectedStepId` → drawer opens
- **File:** `src/views/WorkflowRunDetail.tsx` lines 185-189

### WorkflowStepDrawer → useStepLogs
- **Pattern:** Custom hook for log fetching
- **Data Flow:** `step.job_guid` → `useStepLogs(jobGuid)` → fetch `/api/executions/{job_guid}/logs`
- **File:** `src/components/WorkflowStepDrawer.tsx` lines 79-82

### WorkflowRunDetail ↔ WebSocket
- **Pattern:** Real-time step status updates via WebSocket
- **Data Flow:** `workflow_step_updated` event → update cache via `queryClient.setQueryData` → drawer refreshes (same data)
- **File:** `src/views/WorkflowRunDetail.tsx` lines 73-113

## Deviations from Plan

None — plan executed exactly as written.

## Success Criteria Met

✅ WorkflowStepDrawer component renders and integrates with DAGCanvas via onNodeClick  
✅ useStepLogs hook fetches logs from /api/executions/{job_guid}/logs and caches appropriately  
✅ Drawer displays step execution logs for run steps, "not run" message for unrun steps  
✅ All UI tests pass (100% test coverage for drawer component and hook)  
✅ Drawer is read-only (no edit actions in Phase 150)  
✅ Close on ESC or close button works smoothly (Sheet component)  

## API Contracts

**Log Endpoint (existing):**
```
GET /api/executions/{job_guid}/logs
Response: { stdout: string, stderr: string }
Error 404: No logs available (step has no job_guid yet)
```

**Component Props:**
```typescript
// WorkflowStepDrawer
interface WorkflowStepDrawerProps {
  step?: WorkflowStepRunResponse;
  isOpen: boolean;
  onClose: () => void;
}

// useStepLogs
function useStepLogs(jobGuid: string | null | undefined) {
  return { data: { stdout, stderr } | null, isLoading, error };
}
```

## Testing Commands

```bash
cd puppeteer/dashboard

# Test useStepLogs hook
npm run test -- --run src/hooks/__tests__/useStepLogs.test.ts

# Test WorkflowStepDrawer component
npm run test -- --run src/components/__tests__/WorkflowStepDrawer.test.tsx

# Test WorkflowRunDetail integration
npm run test -- --run src/views/__tests__/WorkflowRunDetail.test.tsx

# All Phase 150 tests (includes drawer tests)
npm run test -- --run
```

## Manual Verification

Once deployed in Docker stack:
1. Navigate to `/workflows/:id/runs/:runId`
2. Click any step node in DAG canvas → drawer opens from right
3. Verify step name, type, status display in header
4. For run steps → logs appear or loading spinner shown
5. For unrun steps → "not run yet" / "skipped" / "cancelled" message
6. Click close button or press ESC → drawer closes smoothly
7. Click another step → drawer updates with new step's logs

## Key Design Decisions

1. **Log Caching (30s):** Balances freshness with UX (reduces API calls for repeated step inspection)
2. **Graceful 404 Handling:** 404s treated as "no logs yet", not errors (PENDING steps have no logs)
3. **Query Disabled for Null jobGuid:** Prevents unnecessary API calls for unrun steps
4. **Read-Only in Phase 150:** No edit buttons/actions (logs are inspection-only)
5. **Drawer from Right:** Shadows main DAG view; common pattern for detail panels
6. **Sheet Component:** Native slide + fade animations, accessible close handling

## Requirements Traceability

**UI-04 (from frontmatter):** Step execution log viewing via drawer  
✅ Drawer component created with log display  
✅ Tests validate log rendering and state transitions  
✅ Integration with DAGCanvas complete  

---

## Self-Check: PASSED

- ✅ All created files exist
- ✅ All modified files contain expected changes
- ✅ All test files pass (32/32 tests)
- ✅ No TypeScript errors
- ✅ Integration validated via test suite

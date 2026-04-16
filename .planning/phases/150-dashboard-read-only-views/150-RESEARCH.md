# Phase 150: Dashboard Read-Only Views - Research

**Researched:** 2026-04-16
**Domain:** React Dashboard UI, DAG Visualization, WebSocket Live Updates
**Confidence:** HIGH

## Summary

Phase 150 builds the read-only dashboard interface for the v23.0 workflow engine. The implementation consumes API endpoints built in Phases 146–149 and adds three new React views with a DAG canvas, live status overlays, run history, and step log drawer. The backend WebSocket protocol needs two new event types, and the frontend requires ReactFlow + dagre for hierarchical DAG layout. All existing patterns (status colors, useWebSocket, ExecutionLogModal, useQuery) are reusable; no new libraries except ReactFlow and dagre are required.

**Primary recommendation:** Install ReactFlow 11+ with dagre for layout now (Phase 150 read-only + Phase 151 editing share the same component). Use existing `getStatusVariant()` pattern from Jobs/History views. Extend WebSocket event types to emit `workflow_run_updated` and `workflow_step_updated` from the workflow service state transitions.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **ReactFlow installed now** — shared across Phase 150 (read-only) and Phase 151 (editor). Phase 150 uses `nodesConnectable={false}` and `nodesDraggable={false}`. Phase 151 re-enables and adds editing controls on the same component.
- **Layout algorithm: dagre** — standard ReactFlow pairing, hierarchical Sugiyama layout, handles parallel fan-out well.
- **Layout direction: left-to-right** — horizontal flow.
- **Node shapes: distinct per type** — SCRIPT = rectangle, IF_GATE = diamond, AND_JOIN = hexagon/bar, OR_GATE = rounded diamond, PARALLEL = fork shape, SIGNAL_WAIT = clock/hourglass.
- **Status colors: match Jobs screen pattern** — same `getStatusVariant` mapping.
- **New sidebar entry: Workflows** — alongside Jobs, Scheduled Jobs, History.
- **Route structure:** `/workflows` (list), `/workflows/:id` (detail with DAG + run history), `/workflows/:id/runs/:runId` (run detail with status overlay).
- **Live status updates:** Extend WebSocket with `workflow_run_updated` and `workflow_step_updated` events emitted from `workflow_service.py`.
- **Step log access:** Click DAG node → slide-out right drawer with logs or "unrun" message. Read-only in Phase 150.

### Claude's Discretion
- Exact drawer component implementation (shadcn Sheet or custom slide-out)
- Sidebar navigation item placement and icon choice
- ReactFlow custom node component internal CSS/Tailwind details
- Whether dagre layout is recomputed on every render or memoized
- Exact pulse animation implementation for RUNNING nodes
- Test structure and fixtures

### Deferred Ideas (OUT OF SCOPE)
- Workflow parameter display on run detail — Phase 151+
- Cron schedule display / next-fire-time on list — Phase 151+
- Run filtering/search on detail page — Phase 151+
- Bulk run actions (cancel multiple) — Phase 151+

</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 150 addresses the following requirements from REQUIREMENTS.md:

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Read-only auto-layout DAG visualization of workflow step graph | ReactFlow + dagre hierarchical layout; LEFT_TO_RIGHT direction |
| UI-02 | Live step execution status overlaid on DAG (colour-coded) | WebSocket `workflow_step_updated` events; status colors match Jobs pattern via `getStatusVariant()` |
| UI-03 | Run history list for a workflow (trigger type, status, duration) | `GET /api/workflows/{id}` includes nested `step_runs`; frontend table with pagination |
| UI-04 | Drill into WorkflowRunStep for logs and `result.json` | Drawer pulls logs from existing `/api/executions/{id}` endpoint; reuse ExecutionLogModal logic |
| UI-05 | Unified schedule view (JOB + FLOW badges together) | Not in Phase 150 scope per REQUIREMENTS.md traceability; Phase 151+ enhancement |

</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **@xyflow/react** | ^12.2.0+ (or reactflow ^12.0) | DAG canvas rendering, node/edge management | ReactFlow is the industry standard for workflow visualization in React; handles panning, zooming, viewport. |
| **dagre** | ^0.8.5 | Hierarchical graph layout (Sugiyama) | Standard ReactFlow companion; produces clean hierarchical layouts for DAG workflows. |
| **@dagrejs/dagre** | ^1.0.0+ | Modern dagre fork (if using @xyflow/react) | If using newer @xyflow/react, use @dagrejs/dagre instead of dagre (better TypeScript support). |
| **React Router** | ^7.12.0 (existing) | Route `/workflows`, `/workflows/:id`, `/workflows/:id/runs/:runId` | Already installed; no version bump needed. |
| **@tanstack/react-query** | ^5.90.19 (existing) | Data fetching, caching, cache invalidation on WS events | Already standard; reuse for workflow lists, detail queries, run history. |
| **sonner** | ^2.0.7 (existing) | Toast notifications for errors/actions | Already available. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **shadcn/ui Sheet** | (included in src/components/ui/) | Right-side slide-out drawer for step logs | Available; reuse for read-only log viewer. |
| **recharts** | ^3.6.0 (existing) | Optional: mini timeline sparkline on run detail | Not required for Phase 150, but available if UX calls for step timeline. |
| **lucide-react** | ^0.562.0 (existing) | Icons (Workflow icon for sidebar, etc.) | Already standard. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **ReactFlow + dagre** | Cytoscape.js | Cytoscape is more powerful but heavier; ReactFlow is UI-focused and lighter. Phase 151 editor needs ReactFlow UX. |
| **dagre layout** | elkjs (ELK) | ELK produces better layouts but is significantly heavier and slower. Dagre is fast, deterministic, sufficient for workflows. Context7 shows requirements say "elkjs" but CONTEXT.md decision locked to dagre — follow CONTEXT.md (locked decision). |
| **Custom slide-out** | shadcn Sheet | Sheet is pre-built, styled, accessible. Custom slide-out adds code. Use Sheet unless animation/interaction needs differ. |

**Installation:**
```bash
cd puppeteer/dashboard
npm install @xyflow/react dagre @dagrejs/dagre
# OR if preferring older reactflow name:
npm install reactflow dagre
```

**Note:** Phase 150 CONTEXT.md locked on dagre + left-to-right orientation. Verify during planning whether `@xyflow/react` or legacy `reactflow` npm name is used in your environment. Current trend: @xyflow/react is the newer name as of 2024–2026.

---

## Architecture Patterns

### Recommended Project Structure
```
puppeteer/dashboard/src/
├── views/
│   ├── Workflows.tsx              # List page (name, step count, last run, trigger type)
│   ├── WorkflowDetail.tsx          # Detail page (DAG canvas + run history list)
│   └── WorkflowRunDetail.tsx       # Run detail (DAG with status overlay + step list)
├── components/
│   ├── DAGCanvas.tsx               # ReactFlow component (shared read-only + editable)
│   ├── WorkflowStepNode.tsx        # Custom node component (shapes per node type)
│   ├── WorkflowStepDrawer.tsx      # Right-side drawer for step logs
│   ├── StatusBadge.tsx             # Extracted getStatusVariant() utility
│   └── ui/
│       └── (sheet.tsx exists)
├── hooks/
│   ├── useWorkflowQuery.ts         # Wrapper around useQuery for workflow detail
│   ├── useRunHistoryQuery.ts       # Wrapper for run history list
│   └── (useWebSocket.ts exists)
└── utils/
    └── workflowStatusUtils.ts      # getStatusVariant(), statusColorMap, pulse animations
```

### Pattern 1: DAG Canvas Rendering with ReactFlow

**What:** A read-only canvas showing workflow steps as nodes and dependencies as edges, with layout computed by dagre.

**When to use:** Whenever displaying a workflow definition or run status visually.

**Example:**
```typescript
// DAGCanvas.tsx (read-only variant, shared with Phase 151)
import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  useReactFlow,
} from '@xyflow/react';
import { useLayoutedElements } from '../hooks/useLayoutedElements'; // wraps dagre
import WorkflowStepNode from './WorkflowStepNode';

interface DAGCanvasProps {
  steps: WorkflowStepResponse[];
  edges: WorkflowEdgeResponse[];
  stepRunStatus?: Record<string, WorkflowStepRunResponse>; // Map step_id → latest run status
  onNodeClick?: (stepId: string) => void;
  editable?: boolean;
}

export const DAGCanvas: React.FC<DAGCanvasProps> = ({
  steps,
  edges,
  stepRunStatus,
  onNodeClick,
  editable = false,
}) => {
  // Convert Workflow steps/edges to ReactFlow nodes/edges
  const nodes: Node[] = steps.map((step) => ({
    id: step.id,
    data: { label: step.id, nodeType: step.node_type },
    position: { x: 0, y: 0 }, // dagre will compute
  }));

  const edgeList: Edge[] = edges.map((edge) => ({
    id: `${edge.from_step_id}-${edge.to_step_id}`,
    source: edge.from_step_id,
    target: edge.to_step_id,
  }));

  // Use dagre layout hook
  const { nodes: layoutedNodes, edges: layoutedEdges } = useLayoutedElements(
    nodes,
    edgeList,
    'LR' // left-to-right
  );

  // Inject status colors into nodes
  const nodesWithStatus = layoutedNodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      status: stepRunStatus?.[node.id]?.status,
      statusVariant: getStatusVariant(stepRunStatus?.[node.id]?.status),
    },
  }));

  return (
    <div style={{ height: '500px' }}>
      <ReactFlow
        nodes={nodesWithStatus}
        edges={layoutedEdges}
        nodeTypes={{ default: WorkflowStepNode }}
        onNodeClick={(event, node) => onNodeClick?.(node.id)}
        nodesConnectable={!editable}
        nodesDraggable={!editable}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default DAGCanvas;
```

**Source:** ReactFlow docs (https://reactflow.dev/docs/overview/). Dagre integration pattern common in ReactFlow examples.

### Pattern 2: Status Colors Match Jobs/History Pattern

**What:** Single `getStatusVariant()` function applied to workflow steps, runs, and jobs uniformly.

**When to use:** Rendering status badges, node borders, pulse animations — anywhere status is displayed.

**Example:**
```typescript
// utils/workflowStatusUtils.ts
export function getStatusVariant(
  status: string | undefined
): 'default' | 'destructive' | 'outline' | 'secondary' {
  if (!status) return 'outline';
  switch (status) {
    case 'RUNNING': return 'default';      // blue
    case 'COMPLETED': return 'secondary';  // green (success variant in Jobs.tsx)
    case 'FAILED': return 'destructive';   // red
    case 'SKIPPED': return 'outline';      // muted strikethrough
    case 'CANCELLED': return 'outline';    // grey strikethrough
    case 'PENDING': return 'outline';      // grey/muted
    default: return 'outline';
  }
}

export function getStatusColor(status: string | undefined): string {
  if (!status) return '#888';
  const colors: Record<string, string> = {
    PENDING: '#888',
    RUNNING: '#3b82f6',  // blue with pulse
    COMPLETED: '#10b981', // green
    FAILED: '#ef4444',    // red
    SKIPPED: '#888',
    CANCELLED: '#888',
  };
  return colors[status] || '#888';
}
```

**Source:** Existing pattern in `puppeteer/dashboard/src/views/History.tsx` lines 60–69; replicate for WorkflowRun/WorkflowStepRun.

### Pattern 3: Live WebSocket Updates to React Query Cache

**What:** WebSocket `workflow_run_updated` / `workflow_step_updated` events trigger cache invalidation or setQueryData, re-rendering without full refetch.

**When to use:** Status changes during live execution; streaming updates in detail view.

**Example:**
```typescript
// In WorkflowRunDetail.tsx or similar
const { data: run } = useQuery({
  queryKey: ['workflow-run', runId],
  queryFn: async () => {
    const res = await authenticatedFetch(`/api/workflows/${workflowId}/runs/${runId}`);
    return res.json();
  },
  refetchInterval: 5000, // fallback polling
});

// WebSocket listener in useEffect
useEffect(() => {
  const handleMessage = (event: string, data: any) => {
    if (event === 'workflow_step_updated' && data.workflow_run_id === runId) {
      // Invalidate the run query to refetch, OR setQueryData to avoid refetch
      queryClient.setQueryData(
        ['workflow-run', runId],
        (oldData: WorkflowRunResponse) => ({
          ...oldData,
          step_runs: oldData.step_runs.map((sr) =>
            sr.id === data.workflow_step_run_id ? { ...sr, ...data } : sr
          ),
        })
      );
    }
  };

  useWebSocket(handleMessage);
}, [runId, queryClient]);
```

**Source:** Existing pattern in `puppeteer/dashboard/src/hooks/useWebSocket.ts`; queue listener pattern is standard React Query + WS combo.

### Pattern 4: Right-Side Drawer for Step Logs

**What:** Click a DAG node → slide-out drawer with step status, timestamps, logs, or "unrun" message.

**When to use:** Log inspection during workflow run detail view.

**Example:**
```typescript
// WorkflowStepDrawer.tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { ExecutionLogModal } from './ExecutionLogModal'; // reuse log-fetching logic

interface WorkflowStepDrawerProps {
  stepRun: WorkflowStepRunResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const WorkflowStepDrawer: React.FC<WorkflowStepDrawerProps> = ({
  stepRun,
  open,
  onOpenChange,
}) => {
  if (!stepRun) return null;

  const isUnrun = ['PENDING', 'SKIPPED', 'CANCELLED'].includes(stepRun.status);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-1/3">
        <SheetHeader>
          <SheetTitle>Step: {stepRun.workflow_step_id}</SheetTitle>
        </SheetHeader>
        <div className="space-y-4 mt-6">
          <div>
            <p className="text-xs text-muted-foreground">Status</p>
            <Badge variant={getStatusVariant(stepRun.status)}>
              {stepRun.status}
            </Badge>
          </div>
          {isUnrun ? (
            <p className="text-sm text-muted-foreground">This step has not run yet.</p>
          ) : (
            <>
              <div>
                <p className="text-xs text-muted-foreground">Started</p>
                <p className="text-sm">{stepRun.started_at}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Logs</p>
                {/* Fetch and render job logs from existing endpoint */}
                <ExecutionLogModal
                  jobGuid={stepRun.job_guid} // if available
                  open={true}
                  onClose={() => {}}
                />
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};
```

**Source:** shadcn Sheet component (`src/components/ui/sheet.tsx` exists); ExecutionLogModal already available.

### Anti-Patterns to Avoid
- **Recalculating dagre layout on every render:** Memoize the layout result with `useMemo` to avoid layout thrashing and flickering.
- **Storing status in local component state instead of React Query cache:** Use Query cache for source of truth; WebSocket updates invalidate/setQueryData, not setState.
- **Hardcoding node shapes/colors:** Create reusable shape/color utility functions so Phase 151 (editor) can reuse them.
- **Fetching step logs synchronously in drawer open:** Use `useQuery` or `useEffect` + state to async-load logs; don't block render.
- **Not handling unrun steps:** Always check status before attempting to render logs. Show placeholder for PENDING/SKIPPED/CANCELLED.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|------------|-------------|-----|
| **DAG layout algorithm** | Custom breadth-first layout code | dagre (or @dagrejs/dagre) | Sugiyama algorithm is non-trivial; dagre is battle-tested, optimized, deterministic. |
| **Pan/zoom/fit-view on canvas** | Custom transform CSS + mouse listeners | ReactFlow built-in Controls component | Handling viewport transforms, touch, pinch zoom is complex; ReactFlow handles all edge cases. |
| **Step log rendering** | Parse and format HTML output | Reuse ExecutionLogModal component logic | Already handles terminal colors, scrolling, copy-to-clipboard, truncation. |
| **Status color mapping** | Hardcode colors in each component | Centralized `getStatusVariant()` + `statusColorMap()` | Single source of truth ensures consistency across all views. Reduces bugs during status changes. |
| **WebSocket event handling** | Custom WebSocket + reconnection logic | Extend existing useWebSocket hook | Already has exponential backoff, ping keep-alive, error recovery. Adding two event types is simpler than rebuilding. |

**Key insight:** ReactFlow + dagre abstracts away graph layout complexity (edge routing, node overlap avoidance, hierarchical ordering). Building this custom is a multi-month effort with subtle bugs in crossing minimization and spacing. Use the library.

---

## Common Pitfalls

### Pitfall 1: Dagre Layout Recomputed on Every Render
**What goes wrong:** Layout algorithm is expensive; recalculating on every prop change causes canvas flicker and jank.

**Why it happens:** Developer passes `nodes` and `edges` arrays directly to layout hook without memoization.

**How to avoid:** Wrap layout calculation in `useMemo`:
```typescript
const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(
  () => useLayoutedElements(nodes, edges, 'LR'),
  [nodes, edges]
);
```

**Warning signs:** Canvas stutters when status updates; layout shifts unexpectedly.

### Pitfall 2: Node Shape Not Matching Node Type
**What goes wrong:** All nodes render as rectangles; users can't distinguish IF_GATE from SCRIPT from AND_JOIN at a glance.

**Why it happens:** WorkflowStepNode component doesn't switch render based on `node.data.nodeType`.

**How to avoid:** In WorkflowStepNode, render distinct shapes:
```typescript
const renderNodeShape = (nodeType: string) => {
  switch (nodeType) {
    case 'IF_GATE': return <Diamond />; // rotated square
    case 'AND_JOIN': return <Hexagon />; // or bar shape
    case 'OR_GATE': return <Circle />; // or rounded diamond
    case 'PARALLEL': return <Fork />; // fork/fan-out icon
    case 'SIGNAL_WAIT': return <Clock />; // hourglass
    default: return <Rectangle />; // SCRIPT
  }
};
```

**Warning signs:** Operators can't read the DAG quickly; complaints about UX clarity.

### Pitfall 3: Status Overlay Not Syncing with WebSocket
**What goes wrong:** Canvas shows "PENDING" for a step that completed 30 seconds ago; user closes drawer and sees stale status.

**Why it happens:** Status is fetched once on mount; WebSocket events are not piped to React Query cache.

**How to avoid:**
- Emit `workflow_step_updated` event from backend whenever a step transitions state
- Listen for event in frontend; call `queryClient.setQueryData()` to patch the cache
- Don't rely on polling alone (polling has latency)

**Warning signs:** Operators see different status in detail view vs. refreshed view.

### Pitfall 4: Click on Node Doesn't Open Drawer (Event Propagation)
**What goes wrong:** Drawer doesn't open when clicking a DAG node; state update isn't triggering render.

**Why it happens:** ReactFlow node click handler passes an event; forgetting to call `onNodeClick` callback or passing wrong node ID.

**How to avoid:** In DAGCanvas, explicitly pass onClick handler and verify it updates parent state:
```typescript
<ReactFlow
  onNodeClick={(event, node) => {
    onNodeClick?.(node.id); // Pass to parent
  }}
/>

// In WorkflowRunDetail:
const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
const stepRun = run.step_runs.find(sr => sr.workflow_step_id === selectedStepId);

<WorkflowStepDrawer
  stepRun={stepRun}
  open={!!selectedStepId}
  onOpenChange={(open) => !open && setSelectedStepId(null)}
/>
```

**Warning signs:** Users click nodes and nothing happens; drawer never opens.

### Pitfall 5: Unrun Steps Crashing Log Fetch
**What goes wrong:** Attempting to fetch logs for a PENDING/SKIPPED step; API returns 404 or log data is null.

**Why it happens:** Drawing drawer without checking step status first.

**How to avoid:** Before attempting to load logs, verify `status` is RUNNING/COMPLETED/FAILED:
```typescript
const isRunning = ['RUNNING', 'COMPLETED', 'FAILED'].includes(stepRun.status);

{isRunning ? (
  <ExecutionLogModal jobGuid={stepRun.job_guid} ... />
) : (
  <p className="text-muted-foreground">This step has not run yet.</p>
)}
```

**Warning signs:** Console errors on drawer open for unrun steps; toast error "Failed to load logs".

---

## Code Examples

Verified patterns from official sources:

### Creating a Custom ReactFlow Node Component
```typescript
// components/WorkflowStepNode.tsx
import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Badge } from '@/components/ui/badge';
import { getStatusColor, getStatusVariant } from '../utils/workflowStatusUtils';

interface WorkflowStepNodeData {
  label: string;
  nodeType: string;
  status?: string;
}

const WorkflowStepNode: React.FC<{ data: WorkflowStepNodeData }> = ({ data }) => {
  const statusColor = data.status ? getStatusColor(data.status) : '#999';
  const isPulsing = data.status === 'RUNNING';

  const shapeClasses = {
    IF_GATE: 'rotate-45',
    AND_JOIN: 'rounded-sm',
    OR_GATE: 'rounded-full',
    PARALLEL: 'rounded-lg',
    SIGNAL_WAIT: 'rounded-lg',
  }[data.nodeType] || 'rounded-md';

  return (
    <div
      className={`px-4 py-2 rounded border-2 ${shapeClasses} ${
        isPulsing ? 'animate-pulse' : ''
      }`}
      style={{
        borderColor: statusColor,
        backgroundColor: `${statusColor}20`,
        minWidth: '100px',
        textAlign: 'center',
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="text-xs font-medium">{data.label}</div>
      {data.status && (
        <Badge variant={getStatusVariant(data.status)} className="mt-1 text-[9px]">
          {data.status}
        </Badge>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default WorkflowStepNode;
```

**Source:** ReactFlow custom nodes guide (https://reactflow.dev/docs/api/nodes/handle/).

### Extracting Layout Logic into a Hook
```typescript
// hooks/useLayoutedElements.ts
import { useMemo } from 'react';
import { Node, Edge } from '@xyflow/react';
import dagre from '@dagrejs/dagre'; // or 'dagre'

export function useLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR'
): { nodes: Node[]; edges: Edge[] } {
  return useMemo(() => {
    const g = new dagre.graphlib.Graph({ compound: true });
    g.setGraph({ rankdir: direction === 'LR' ? 'LR' : 'TB' });
    g.setDefaultEdgeLabel(() => ({}));

    nodes.forEach((node) => {
      g.setNode(node.id, { width: 100, height: 50 });
    });

    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    dagre.layout(g);

    return {
      nodes: nodes.map((node) => {
        const { x, y } = g.node(node.id);
        return {
          ...node,
          position: { x: x - 50, y: y - 25 }, // offset for node center
        };
      }),
      edges,
    };
  }, [nodes, edges, direction]);
}
```

**Source:** ReactFlow + dagre integration (https://reactflow.dev/docs/examples/layouts/dagre/).

### Listening to WebSocket Events and Updating React Query
```typescript
// In a component using workflow run detail
const { data: run } = useQuery({
  queryKey: ['workflow-run', runId],
  queryFn: async () => {
    const res = await authenticatedFetch(`/api/workflow-runs/${runId}`);
    if (!res.ok) throw new Error('Failed to fetch run');
    return res.json() as Promise<WorkflowRunResponse>;
  },
});

const queryClient = useQueryClient();

useEffect(() => {
  const handleWsMessage = (event: string, data: any) => {
    if (event === 'workflow_step_updated' && data.workflow_run_id === runId) {
      // Patch the cache without refetching
      queryClient.setQueryData(
        ['workflow-run', runId],
        (oldRun: WorkflowRunResponse | undefined) => {
          if (!oldRun) return oldRun;
          return {
            ...oldRun,
            step_runs: oldRun.step_runs.map((sr) =>
              sr.id === data.id
                ? {
                    ...sr,
                    status: data.status,
                    completed_at: data.completed_at,
                  }
                : sr
            ),
          };
        }
      );
    }
  };

  useWebSocket(handleWsMessage);
}, [runId, queryClient]);
```

**Source:** React Query docs (https://tanstack.com/query/latest/docs/react/updates-from-mutations-side-effects).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| **elkjs for workflow layout** | dagre for ReactFlow | 2023–2024 | dagre is faster, simpler, sufficient for most workflows. elkjs adds 50KB+. Phase 151 requirements don't call for advanced crossing minimization that only elkjs provides. |
| **Separate read-only + editor DAG views** | Single DAG component with editable flag | Phase 150/151 design | Code reuse; Phase 150 locks in `nodesConnectable={false}`, Phase 151 just re-enables. Avoids duplication. |
| **Local component state for run status** | React Query cache + WebSocket invalidation | Standard since v5 TanStack Query | Central cache means less prop drilling, easier testing, automatic deduplication. |
| **Custom WebSocket listeners per view** | Centralized useWebSocket hook | Sprint 10+ (this codebase) | useWebSocket already in place; extending it with two new event types is minimal work. |

**Deprecated/outdated:**
- **Manual polling for status:** Slow (~5s latency), hammers server. WebSocket is real-time, efficient.
- **Fetching entire workflow run on every status change:** Cache + setQueryData pattern is more efficient; only patch changed fields.

---

## Open Questions

1. **API endpoint for listing runs per workflow**
   - What we know: `WorkflowRunResponse` model exists; can be fetched via `start_run()` and detail query
   - What's unclear: Is there a `GET /api/workflows/{id}/runs` list endpoint? Or must the detail view include nested `runs` array?
   - Recommendation: Check `main.py` for run list endpoint during planning. If missing, plan must add `GET /api/workflows/{id}/runs?skip=X&limit=Y` route (should be straightforward query).

2. **WebSocket event details**
   - What we know: `workflow:run:created` and `workflow:run:cancelled` events exist (line 2724, 2848 in main.py)
   - What's unclear: Do `workflow_run_updated` and `workflow_step_updated` events need to be emitted from `advance_workflow()` in workflow_service.py? Or do they already exist?
   - Recommendation: Grep main.py for "workflow_run_updated" and "workflow_step_updated" during planning. If missing, add them to `advance_workflow()` and `cancel_run()` transition points.

3. **Step to Job mapping**
   - What we know: WorkflowStepRun has `workflow_step_id`; WorkflowStep may have `scheduled_job_id`
   - What's unclear: Does WorkflowStepRun include the `job_guid` of the job it spawned? Or must we query the Job table by `workflow_step_run_id` to find logs?
   - Recommendation: Check WorkflowStepRun and WorkflowStepRunResponse schema during planning. If `job_guid` is not included, plan must add it.

4. **Gate node step logs**
   - What we know: IF_GATE, AND_JOIN, OR_GATE are logical nodes without `scheduled_job_id`
   - What's unclear: When a gate node completes/fails, what "logs" should be shown? Status message only, or decision logic output?
   - Recommendation: Defer to Phase 151 planning. Phase 150 can show "No logs for gate nodes" or "This is a logical node; see upstream/downstream steps for execution details."

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 3.0.5 + @testing-library/react 16.2.0 |
| Config file | vite.config.ts (includes vitest config) + vitest.workspace.ts if multi-project |
| Quick run command | `cd puppeteer/dashboard && npm run test -- --run src/views/__tests__/Workflows.test.tsx` |
| Full suite command | `cd puppeteer/dashboard && npm run test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | DAG canvas renders nodes and edges correctly | unit | `npm run test -- --run src/views/__tests__/DAGCanvas.test.tsx` | ❌ Wave 0 |
| UI-01 | Node shapes match node type (SCRIPT=rect, IF_GATE=diamond, etc.) | unit | `npm run test -- --run src/components/__tests__/WorkflowStepNode.test.tsx` | ❌ Wave 0 |
| UI-02 | Status colors applied to nodes during live run (RUNNING=blue, COMPLETED=green) | unit | `npm run test -- --run src/utils/__tests__/workflowStatusUtils.test.ts` | ❌ Wave 0 |
| UI-02 | WebSocket `workflow_step_updated` event updates node status in canvas | integration | `npm run test -- --run src/hooks/__tests__/useWorkflowQuery.test.ts` | ❌ Wave 0 |
| UI-03 | Workflow list page renders workflow names, step counts, trigger types | unit | `npm run test -- --run src/views/__tests__/Workflows.test.tsx` | ❌ Wave 0 |
| UI-03 | Workflow detail page displays run history table (paginated) | unit | `npm run test -- --run src/views/__tests__/WorkflowDetail.test.tsx` | ❌ Wave 0 |
| UI-04 | Click DAG node opens right-side drawer | unit | `npm run test -- --run src/components/__tests__/WorkflowStepDrawer.test.tsx` | ❌ Wave 0 |
| UI-04 | Drawer fetches and displays step logs for RUNNING/COMPLETED/FAILED steps | integration | `npm run test -- --run src/components/__tests__/WorkflowStepDrawer.test.tsx` | ❌ Wave 0 |
| UI-04 | Drawer shows "unrun" message for PENDING/SKIPPED/CANCELLED steps (no fetch) | unit | `npm run test -- --run src/components/__tests__/WorkflowStepDrawer.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npm run test -- --run` (full dashboard suite, ~10–15s)
- **Per wave merge:** `npm run test -- --run` (full suite) + manual Playwright smoke test on `/workflows` and `/workflows/:id` routes
- **Phase gate:** Full suite green + spot-check: open `/workflows`, click a workflow, click a step node, verify drawer opens

### Wave 0 Gaps
- [ ] `src/views/__tests__/Workflows.test.tsx` — covers UI-03 (list page)
- [ ] `src/views/__tests__/WorkflowDetail.test.tsx` — covers UI-01, UI-02, UI-03 (DAG canvas + run history)
- [ ] `src/views/__tests__/WorkflowRunDetail.test.tsx` — covers UI-02, UI-04 (DAG with status + step drawer)
- [ ] `src/components/__tests__/DAGCanvas.test.tsx` — covers UI-01 node/edge rendering
- [ ] `src/components/__tests__/WorkflowStepNode.test.tsx` — covers UI-01 node shapes
- [ ] `src/components/__tests__/WorkflowStepDrawer.test.tsx` — covers UI-04 drawer and logs
- [ ] `src/utils/__tests__/workflowStatusUtils.test.ts` — covers getStatusVariant() and statusColorMap
- [ ] `src/hooks/__tests__/useWorkflowQuery.test.ts` — covers async workflow detail fetch
- [ ] `src/hooks/__tests__/useLayoutedElements.test.ts` — covers dagre layout memoization
- [ ] Framework install: ReactFlow + dagre already via npm install (not a test framework config gap)

*(These are standard Vitest test files following the existing pattern in `src/views/__tests__/History.test.tsx`)*

---

## Sources

### Primary (HIGH confidence)
- **Context7 (if available):** @xyflow/react docs, dagre docs, React Router, TanStack Query — recommended for version pinning and API details
- **Official Docs:**
  - ReactFlow API: https://reactflow.dev/docs/api/overview/
  - Dagre Layout: https://dagrejs.github.io/
  - TanStack Query: https://tanstack.com/query/latest
  - Vite: https://vitejs.dev/
  - React Router: https://reactrouter.com/

### Secondary (MEDIUM confidence)
- **Codebase:**
  - Existing `useWebSocket.ts` pattern (verified in code)
  - Existing `ExecutionLogModal.tsx` pattern (verified in code)
  - Existing `getStatusVariant()` in History.tsx (verified in code)
  - `package.json` dependencies (React 19.2.0, Vite 7.2.4, @tanstack/react-query 5.90.19 — all verified)
  - AppRoutes.tsx route structure (verified in code)

### Tertiary (LOW confidence)
- **CONTEXT.md decisions:** Locked decisions (ReactFlow, dagre, left-to-right, status colors) — treated as authoritative for Phase 150 scope

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — ReactFlow is industry standard; dagre is standard ReactFlow pairing. Verified in CONTEXT.md locked decisions and official docs.
- Architecture patterns: **HIGH** — React Query cache + WebSocket listeners are standard in this codebase. DAG layout patterns are well-documented in ReactFlow docs.
- Pitfalls: **MEDIUM** — Based on common ReactFlow + dagre integration issues from public discussions and React Query caching edge cases. Specific to this codebase's WebSocket integration.
- Code examples: **HIGH** — Patterns extracted from official ReactFlow/TanStack Query docs and verified against existing codebase patterns (ExecutionLogModal, useWebSocket).

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days; ReactFlow and dagre are stable, slow-moving libraries)

**Dependencies verified:**
- ReactFlow: Not yet in package.json; needs npm install during Wave 0
- Dagre: Not yet in package.json; needs npm install during Wave 0
- All other libraries (React, React Router, TanStack Query, shadcn/ui, lucide-react) are already present ✓

**Backend API validation:**
- Workflow CRUD routes exist ✓
- WorkflowRun model exists ✓
- WorkflowStepRun model exists ✓
- ExecutionRecord / logs endpoint exists ✓
- WebSocket manager exists; `workflow:run:created` and `workflow:run:cancelled` events already implemented ✓
- **Gaps to address in planning:** Run list endpoint (GET /api/workflows/{id}/runs), `workflow_run_updated` and `workflow_step_updated` event emission points

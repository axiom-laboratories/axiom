# Phase 155: Visual DAG Editor - Research

**Researched:** 2026-04-16
**Domain:** ReactFlow-based drag-and-drop workflow composition with real-time DAG validation
**Confidence:** HIGH

## Summary

Phase 155 implements UI-06 and UI-07 requirements: a visual drag-and-drop canvas for editing Workflow DAGs with real-time cycle detection, depth warnings, and inline IF gate condition configuration. The infrastructure is largely pre-built from Phase 150 (read-only DAG rendering); this phase focuses on toggling edit mode, adding a node palette, implementing edit handlers, and integrating validation feedback.

Key finding: `DAGCanvas` already has `editable={true}` prop wired to disable `nodesConnectable` and `nodesDraggable`; Phase 155 must wire state management and add edit-mode handlers. The backend validation endpoints (`POST /api/workflows/validate`, `PUT /api/workflows/{id}`) and gate evaluation logic (field resolution, operators) are complete and verified.

**Primary recommendation:** Build incrementally from DAGCanvas → edit mode state → node palette → edit handlers → validation feedback, using existing vitest patterns and shadcn Sheet component for the IF gate config drawer.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Edit mode entry:** Edit button on `WorkflowDetail` page, same URL (`/workflows/:id`), no new route. Header shows `[Name] │ [Editing…] [Save] [Cancel]`.
- **Edit mode layout:** Canvas expands to full height; run history hidden.
- **Active run blocks edit:** If `WorkflowRun.status == RUNNING`, Edit button disabled with tooltip.
- **Step palette (left side):** Narrow left panel with 6 draggable node types (SCRIPT, IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT).
- **SCRIPT node linking:** Dropped SCRIPT node appears "Unlinked step ⚠". Clicking opens popover with job search. Unlinked nodes block Save.
- **Gate/join nodes:** AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT, IF_GATE are valid as-dropped (no job reference required).
- **IF gate inline config:** Right-side Sheet drawer with structured form (Field, Operator dropdown, Value, True/False branch names). `[Save condition]` and `[Clear]` buttons.
- **Cycle detection (red):** Red edge highlight + error banner `❌ Cycle detected: A → B → A`. Save disabled.
- **Depth warning (amber):** Banner at depth ≥ 25: `⚠️ Depth: 26/30 max`. Still saveable.
- **Depth limit (red):** At depth > 30: `❌ Depth limit exceeded: 31/30 max`. Save disabled.
- **Validation strategy:** Client-side DFS (real-time) + backend `POST /api/workflows/validate` before Save.
- **Save flow:** Explicit Save button (no auto-save). Client validates → POST validate → if OK, PUT `/api/workflows/{id}` → success toast → edit mode exits.

### Claude's Discretion
- Exact palette panel width and visual styling
- Whether palette is overlay or shifts canvas
- Exact popover vs. inline-node UI for SCRIPT job assignment
- Debounce timing for client-side validation
- Animation for entering/exiting edit mode
- Exact error/success toast content

### Deferred Ideas (OUT OF SCOPE)
- Creating new workflows from blank canvas (UX enhancement)
- Workflow parameter editing from canvas
- Undo/redo on canvas
- Copy/paste of nodes

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-06 | User can compose a Workflow visually by dragging ScheduledJob steps onto a canvas and connecting them with directed edges | ReactFlow drag-to-canvas, node palette, edge drawing via `nodesConnectable={true}`, SCRIPT node job selector |
| UI-07 | Canvas validates the DAG in real-time: highlights cycles, warns on depth approaching 30, exposes IF gate condition configuration inline | Client-side DFS cycle detection + depth calc, red/amber banners, backend `POST /api/workflows/validate`, IF gate Sheet drawer with structured form |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xyflow/react | 12.10.2 | ReactFlow drag-and-drop canvas | Already in use for Phase 150 read-only DAG; handles nodes, edges, dragging, positioning natively |
| @dagrejs/dagre | 3.0.0 | Hierarchical graph layout | Already integrated via `useLayoutedElements` hook; proven for workflow DAG layout |
| @radix-ui/react-dialog | 1.1.15 | Sheet drawer component | Base for Phase 150 WorkflowStepDrawer; available in shadcn/ui, used for IF gate config |
| @tanstack/react-query | 5.90.19 | API data fetching | Already used in WorkflowDetail; query invalidation on save |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | 2.0.7 | Toast notifications | Success/error feedback on Save/Cancel; already used in project |
| lucide-react | 0.562.0 | Icons | Node type icons, warning/error indicators; already used |
| react-router-dom | 7.12.0 | Navigation and URL params | Parse `workflow_id` from URL; navigate after save/cancel |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ReactFlow | Cytoscape.js | Cytoscape has better graph algorithms but heavier; ReactFlow is standard for React drag-and-drop workflows |
| Radix Dialog | Custom modal | Radix is typed, accessible, battle-tested; custom costs dev time |
| Client-side DFS | Rely only on backend validation | Client feedback is instant (< 1ms) vs. 100-300ms API latency; both are required per spec |

---

## Architecture Patterns

### Recommended Project Structure

Existing structure (no new directories needed):
```
puppeteer/dashboard/src/
├── components/
│   ├── DAGCanvas.tsx          # Already has editable prop
│   ├── WorkflowStepNode.tsx   # Extend with edit-mode affordances
│   ├── WorkflowNodePalette.tsx        # NEW: draggable node type chips
│   ├── IfGateConfigDrawer.tsx         # NEW: right-side Sheet for IF gate config
│   ├── ScriptNodeJobSelector.tsx      # NEW: job search popover for SCRIPT nodes
│   └── ui/
│       └── sheet.tsx          # Already available
├── views/
│   ├── WorkflowDetail.tsx     # Extend with edit mode state
│   └── __tests__/
│       └── WorkflowDetail.test.tsx # Extend with edit mode tests
├── hooks/
│   ├── useLayoutedElements.ts # Already exists
│   ├── useDAGValidation.ts            # NEW: client-side cycle + depth checks
│   ├── useWorkflowEdit.ts             # NEW: edit state management
│   └── useStepLogs.ts         # Already exists (Phase 150)
└── utils/
    └── dagValidation.ts               # NEW: DFS cycle detection + depth calc
```

### Pattern 1: Edit Mode Toggle

**What:** Single `isEditing` state on `WorkflowDetail` controls canvas interactivity, palette visibility, toolbar state, and run history visibility.

**When to use:** Phase 155 entry point — all edit affordances gate on this boolean.

**Example:**
```typescript
// src/views/WorkflowDetail.tsx
const [isEditing, setIsEditing] = useState(false);

return (
  <>
    <WorkflowDetailHeader
      isEditing={isEditing}
      onEditToggle={() => setIsEditing(!isEditing)}
      onSave={handleSave}
      onCancel={() => {
        setIsEditing(false);
        // Discard changes (refetch workflow)
      }}
      canEdit={!workflow?.last_run || workflow.last_run.status !== 'RUNNING'}
    />
    {isEditing && <WorkflowNodePalette />}
    <DAGCanvas
      editable={isEditing}
      onNodesChange={isEditing ? handleNodesChange : undefined}
      onEdgesChange={isEditing ? handleEdgesChange : undefined}
      onConnect={isEditing ? handleConnect : undefined}
      onDrop={isEditing ? handleDrop : undefined}
      onDragOver={isEditing ? handleDragOver : undefined}
    />
    {!isEditing && <WorkflowRunHistory />}
  </>
);
```

**Source:** Pattern derived from Phase 150 DAGCanvas `editable` prop and Phase 154 WorkflowDetail structure.

### Pattern 2: Drag-to-Canvas from Palette

**What:** WorkflowNodePalette renders draggable "chips" for each node type. User drags a chip onto the canvas; `onDrop` handler converts screen coordinates to flow coordinates and adds a new node.

**When to use:** Adding new steps to the canvas in edit mode.

**Example:**
```typescript
// src/components/WorkflowNodePalette.tsx
const WorkflowNodePalette: React.FC<{onNodeAdd: (type: string) => void}> = ({onNodeAdd}) => {
  const nodeTypes = [
    {type: 'SCRIPT', label: 'Script'},
    {type: 'IF_GATE', label: 'IF Gate'},
    {type: 'AND_JOIN', label: 'AND Join'},
    {type: 'OR_GATE', label: 'OR Gate'},
    {type: 'PARALLEL', label: 'Parallel'},
    {type: 'SIGNAL_WAIT', label: 'Signal Wait'},
  ];

  return (
    <div className="w-32 border-r p-2">
      {nodeTypes.map(({type, label}) => (
        <div
          key={type}
          draggable
          onDragStart={(e) => {
            e.dataTransfer?.setData('application/reactflow', type);
            e.dataTransfer!.effectAllowed = 'move';
          }}
          className="p-2 mb-2 border rounded cursor-move bg-card"
        >
          {label}
        </div>
      ))}
    </div>
  );
};

// src/components/DAGCanvas.tsx (extend onDrop handler)
const handleDrop = (event: DragEvent) => {
  if (!reactFlowInstance) return;
  
  const nodeType = (event.dataTransfer?.getData('application/reactflow'));
  const position = reactFlowInstance.screenToFlowPosition({
    x: event.clientX,
    y: event.clientY,
  });
  
  const newNode: Node = {
    id: `step_${Date.now()}`,
    data: {label: nodeType, nodeType},
    position,
  };
  
  setNodes((nds) => nds.concat(newNode));
};
```

**Source:** ReactFlow documentation pattern; example in Context7 `@xyflow/react` v12.10.2.

### Pattern 3: Real-Time Validation (Client-Side DFS)

**What:** On every `onNodesChange` or `onEdgesChange`, run DFS to detect cycles and calculate max depth. Emit validation errors that trigger banner display.

**When to use:** Every canvas mutation in edit mode; instant feedback (<1ms).

**Example:**
```typescript
// src/utils/dagValidation.ts
export interface ValidationResult {
  isValid: boolean;
  hasCycle: boolean;
  cycleNodes?: string[];
  maxDepth: number;
  depthExceeded: boolean;
}

export function validateDAG(
  nodes: Node[],
  edges: Edge[],
  maxDepth: number = 30
): ValidationResult {
  const nodeSet = new Set(nodes.map(n => n.id));
  const adjacency = new Map<string, string[]>();
  const cycleEdges = new Set<string>();
  
  // Build adjacency list
  nodes.forEach(n => adjacency.set(n.id, []));
  edges.forEach(e => {
    if (nodeSet.has(e.source) && nodeSet.has(e.target)) {
      adjacency.get(e.source)!.push(e.target);
    }
  });
  
  // DFS cycle detection
  const visited = new Set<string>();
  const recStack = new Set<string>();
  let cycleFound = false;
  let cycleNodes: string[] = [];
  
  function dfs(node: string, path: string[]): boolean {
    visited.add(node);
    recStack.add(node);
    path.push(node);
    
    for (const neighbor of adjacency.get(node) || []) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor, path)) return true;
      } else if (recStack.has(neighbor)) {
        cycleFound = true;
        cycleNodes = path.slice(path.indexOf(neighbor));
        return true;
      }
    }
    
    recStack.delete(node);
    path.pop();
    return false;
  }
  
  nodes.forEach(n => {
    if (!visited.has(n.id)) dfs(n.id, []);
  });
  
  // Calculate max depth (longest path)
  const depth = calculateMaxDepth(adjacency, nodes);
  
  return {
    isValid: !cycleFound && depth <= maxDepth,
    hasCycle: cycleFound,
    cycleNodes: cycleFound ? cycleNodes : undefined,
    maxDepth: depth,
    depthExceeded: depth > maxDepth,
  };
}

function calculateMaxDepth(adj: Map<string, string[]>, nodes: Node[]): number {
  const memo = new Map<string, number>();
  
  function maxPathFrom(node: string): number {
    if (memo.has(node)) return memo.get(node)!;
    
    const children = adj.get(node) || [];
    let max = 0;
    for (const child of children) {
      max = Math.max(max, 1 + maxPathFrom(child));
    }
    
    memo.set(node, max);
    return max;
  }
  
  return nodes.reduce((max, n) => Math.max(max, maxPathFrom(n.id)), 0);
}
```

**Source:** NetworkX/graph theory; O(V+E) DFS is standard for cycle detection in directed graphs.

### Pattern 4: IF Gate Structured Config Form

**What:** Right-side Sheet drawer with form fields (Field, Operator dropdown, Value, True/False branch names). On submit, serialize to `config_json` that matches the backend `GateEvaluationService.evaluate_condition` schema.

**When to use:** User clicks an IF_GATE node in edit mode.

**Example:**
```typescript
// src/components/IfGateConfigDrawer.tsx
interface IfGateConfig {
  field: string;
  op: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'exists';
  value: string;
  true_branch: string;
  false_branch: string;
}

const IfGateConfigDrawer: React.FC<{
  stepId: string;
  currentConfig?: IfGateConfig;
  onSave: (config: IfGateConfig) => void;
  onClose: () => void;
}> = ({stepId, currentConfig, onSave, onClose}) => {
  const [form, setForm] = useState<IfGateConfig>(
    currentConfig || {field: '', op: 'eq', value: '', true_branch: 'true', false_branch: 'false'}
  );
  
  return (
    <Sheet open={true} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Configure IF Gate</SheetTitle>
          <SheetDescription>Step: {stepId}</SheetDescription>
        </SheetHeader>
        
        <div className="space-y-4">
          <div>
            <Label>Field (e.g., result.exit_code)</Label>
            <Input
              value={form.field}
              onChange={(e) => setForm({...form, field: e.target.value})}
            />
          </div>
          
          <div>
            <Label>Operator</Label>
            <Select value={form.op} onValueChange={(op) => setForm({...form, op: op as any})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {['eq', 'neq', 'gt', 'lt', 'contains', 'exists'].map(op => (
                  <SelectItem key={op} value={op}>{op}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {form.op !== 'exists' && (
            <div>
              <Label>Value</Label>
              <Input
                value={form.value}
                onChange={(e) => setForm({...form, value: e.target.value})}
              />
            </div>
          )}
          
          <div>
            <Label>True Branch Name</Label>
            <Input
              value={form.true_branch}
              onChange={(e) => setForm({...form, true_branch: e.target.value})}
            />
          </div>
          
          <div>
            <Label>False Branch Name</Label>
            <Input
              value={form.false_branch}
              onChange={(e) => setForm({...form, false_branch: e.target.value})}
            />
          </div>
          
          <div className="flex gap-2">
            <Button onClick={() => onSave(form)}>Save condition</Button>
            <Button variant="outline" onClick={() => onSave({field: '', op: 'eq', value: '', true_branch: 'true', false_branch: 'false'})}>Clear</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};
```

**Source:** shadcn Sheet + Form pattern from Phase 150 WorkflowStepDrawer; GateEvaluationService schema from Phase 148 implementation.

### Anti-Patterns to Avoid
- **No auto-save:** Phase 155 explicitly requires Save button (no Ctrl+S or auto-persisting edits).
- **Don't validate on every keystroke:** Use client-side validation for canvas changes (nodes/edges) only, not form input debouncing.
- **Don't allow edit during RUNNING:** The Edit button must be disabled with a tooltip if the workflow has an active run.
- **Don't persist unlinked SCRIPT nodes:** Client-side check before Save: all SCRIPT steps must have `scheduled_job_id`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph cycle detection | Custom cycle finding algorithm | NetworkX (Python) / DFS (TypeScript) | Standard algorithm; easy to get wrong (false negatives on complex graphs) |
| Hierarchical graph layout | Custom node positioning | dagre (already in use) | Proven Sugiyama algorithm; handles edge crossing minimization |
| Drag-and-drop canvas | Custom event handling | ReactFlow | Browser drag API is finicky; ReactFlow handles coordinate transforms, viewport zoom, etc. |
| Form validation for IF gate | Custom validators | Zod or React Hook Form | Type safety, composition, easy to test |
| Toast notifications | Custom modals | sonner (already in use) | Non-blocking, queued, works with animations |
| Accessible Sheet drawer | Custom modal overlay | shadcn Sheet (Radix Dialog) | ARIA attributes, focus management, keyboard dismissal |

**Key insight:** Cycles in DAGs are deceptively complex to detect (need to distinguish back edges from cross edges in DFS); hand-rolled DFS often misses edge cases. Use proven graph theory library or well-tested open-source code.

---

## Common Pitfalls

### Pitfall 1: Coordinate Transform Confusion (ReactFlow Drag-to-Canvas)

**What goes wrong:** User drags a chip from palette onto canvas, but node appears at wrong position (e.g., at top-left corner, or off-screen).

**Why it happens:** Screen coordinates (mouse event) are not the same as flow coordinates (ReactFlow's internal coordinate system). ReactFlow handles zoom, pan, and viewport offset; calling `screenToFlowPosition()` is required.

**How to avoid:** Always call `reactFlowInstance.screenToFlowPosition({x, y})` before creating a node with `position: {...}`. Test with zoomed/panned canvas.

**Warning signs:** 
- Node appears at (0,0) every time
- Node appears offset from cursor
- Node position doesn't respect viewport pan/zoom

### Pitfall 2: Validation Result Not Triggering Banners

**What goes wrong:** DFS detects a cycle, but the red error banner doesn't appear. User can still click Save.

**Why it happens:** Validation result is computed but not wired to the banner render condition. E.g., `validationResult.hasCycle` is true, but the banner only checks `showError === true` and `showError` is never set.

**How to avoid:** Store validation result in state, use it directly in render:
```typescript
const [validation, setValidation] = useState<ValidationResult>({...});
useEffect(() => {
  setValidation(validateDAG(nodes, edges));
}, [nodes, edges]);

return (
  <>
    {validation.hasCycle && <Banner variant="error">Cycle detected</Banner>}
    {!validation.hasCycle && validation.maxDepth >= 25 && <Banner variant="warning">Depth warning</Banner>}
    <Button disabled={!validation.isValid}>Save</Button>
  </>
);
```

**Warning signs:**
- Validation runs (check console logs) but UI doesn't update
- Error banner appears but Save button is still enabled

### Pitfall 3: SCRIPT Node Remains Unlinked After Job Selection

**What goes wrong:** User clicks an unlinked SCRIPT node, selects a job, popover closes, but node still shows "Unlinked ⚠".

**Why it happens:** Job ID is written to the node's data, but node is not re-rendered. React updates didn't propagate, or the job selector didn't call the update handler.

**How to avoid:** 
1. Ensure job selector calls `onSelectJob(nodeId, jobId)` callback.
2. In the callback, update the node via `setNodes()` to mark it linked.
3. Test the full flow: unlinked node → click → job selector → select job → verify node data changes.

**Warning signs:**
- Node still shows ⚠ after selecting a job
- Check React DevTools: node.data.scheduled_job_id is undefined
- useQuery cache is stale (verify job list was fetched)

### Pitfall 4: Backend Validation Endpoint Returns Unexpected Response

**What goes wrong:** After Save button clicked, `POST /api/workflows/validate` returns `{valid: false, error: "..."}` but the client code expects `{valid: false, cycle_path: [...]}`.

**Why it happens:** Backend response schema changed, or client code assumes a field that backend doesn't include in all error cases.

**How to avoid:** Check the backend response schema in `main.py` line 2717–2733. Response shape:
- Success: `{valid: true}`
- Cycle: `{valid: false, error: "CYCLE_DETECTED", cycle_path: [...]}`
- Depth: `{valid: false, error: "DEPTH_LIMIT_EXCEEDED", max_depth: 30, actual_depth: 31}`
- Ref integrity: `{valid: false, error: "INVALID_EDGE_REFERENCE", edge: {from_step_id, to_step_id}}`

Client must handle all cases:
```typescript
const res = await authenticatedFetch('/api/workflows/validate', {
  method: 'POST',
  body: JSON.stringify({steps, edges}),
});
const result = await res.json();
if (!result.valid) {
  console.error(result.error, result); // Handle all response shapes
}
```

**Warning signs:**
- UI crashes with "Cannot read property 'cycle_path' of undefined"
- Error message is blank or `[object Object]`

### Pitfall 5: Edit Mode State Not Persisted; User Loses Changes on Reload

**What goes wrong:** User edits the DAG, hasn't clicked Save. They accidentally refresh page. All edits are lost (expected). But if they use browser back button after starting to edit, they might think edits were saved.

**Why it happens:** No persistence of in-progress edits (correct per spec — no auto-save). But no explicit warning when navigating away with unsaved changes.

**How to avoid:** Add a `beforeunload` handler to warn users if `isEditing && hasChanges`:
```typescript
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isEditing && JSON.stringify(nodes) !== JSON.stringify(originalNodes)) {
      e.preventDefault();
      e.returnValue = '';
    }
  };
  window.addEventListener('beforeunload', handleBeforeUnload);
  return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, [isEditing, nodes, originalNodes]);
```

**Warning signs:**
- User reports losing edits after browser back
- No warning modal appears on navigation

---

## Code Examples

Verified patterns from official sources:

### ReactFlow Drag-to-Canvas

```typescript
// Source: @xyflow/react v12.10.2 documentation
const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  event.dataTransfer!.dropEffect = 'move';
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  if (!reactFlowInstance) return;
  
  const nodeType = event.dataTransfer?.getData('application/reactflow');
  if (!nodeType) return;
  
  const position = reactFlowInstance.screenToFlowPosition({
    x: event.clientX,
    y: event.clientY,
  });
  
  const newNode = {
    id: `step_${uuidv4()}`,
    data: {label: nodeType, nodeType, scheduled_job_id: null},
    position,
    type: 'default',
  };
  
  setNodes((nds) => nds.concat(newNode));
};
```

### IF Gate Config JSON Schema (Backend Compatibility)

```typescript
// Source: agent_service/services/gate_evaluation_service.py
interface IfGateCondition {
  field: string;        // e.g., "exit_code", "result.status"
  op: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'exists';
  value?: any;          // Omitted for 'exists' operator
}

interface IfGateConfig {
  condition: IfGateCondition;
  true_branch: string;  // Branch name if condition matches
  false_branch: string; // Branch name if condition doesn't match
}

// Serialized to WorkflowStep.config_json (JSON string)
const configJson = JSON.stringify({
  condition: {field: 'exit_code', op: 'eq', value: 0},
  true_branch: 'success',
  false_branch: 'failure',
});
```

### React Hook Form + Zod for IF Gate Config

```typescript
// Source: React Hook Form v7+ with Zod
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';

const ifGateSchema = z.object({
  field: z.string().min(1, 'Field is required'),
  op: z.enum(['eq', 'neq', 'gt', 'lt', 'contains', 'exists']),
  value: z.string().optional(),
  true_branch: z.string().min(1),
  false_branch: z.string().min(1),
});

type IfGateFormData = z.infer<typeof ifGateSchema>;

const {register, handleSubmit, watch} = useForm<IfGateFormData>({
  resolver: zodResolver(ifGateSchema),
  defaultValues: currentConfig,
});

const onSubmit = (data: IfGateFormData) => {
  const config = {
    condition: {field: data.field, op: data.op, value: data.value},
    true_branch: data.true_branch,
    false_branch: data.false_branch,
  };
  updateNodeConfig(stepId, JSON.stringify(config));
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate workflow editor page (Phase 151 planned) | Inline edit mode on `/workflows/:id` detail page | Phase 155 (this phase) | Simpler UX: no new route, edit context always visible (run history shows pre-edit state) |
| Manual JSON editing for step config | Structured form with field dropdown, operator select, value input | Phase 155 | Error prevention: no more malformed JSON; easier for non-technical users |
| Backend validation only (slow) | Client-side DFS + backend validation (fast UX + safety) | Phase 155 | Instant feedback (<1ms) for cycles/depth, backend is final check before Save |
| No node palette; only add via form modal | Drag-and-drop palette chips onto canvas | Phase 155 | Faster workflow composition; visual feedback (node appears where dropped) |

**Deprecated/outdated:**
- Phase 151 was deferred; Phase 155 is the implementation of that requirement set.

---

## Open Questions

1. **Popover component for SCRIPT job selector:** Context.md mentions "small popover" for job search, but `src/components/ui/popover.tsx` doesn't exist. Should we use Radix Popover (not currently imported), or use a small Sheet drawer?
   - **Recommendation:** Create `src/components/ui/popover.tsx` from Radix (standard shadcn pattern) or use a floating card positioned via `absolute` near the clicked node. Popover is better for node-local context.

2. **Unlinked SCRIPT node indicator:** Context.md says "Unlinked step ⚠" should appear on the node. Should we extend `WorkflowStepNode` to add an overlay badge, or show it only in edit mode?
   - **Recommendation:** Add a conditional `unlinkedBadge` prop to `WorkflowStepNode` that renders an amber badge with ⚠ icon. Only shown in edit mode (`isEditing === true`).

3. **Cycle edge highlighting:** When a cycle is detected, which edges should be highlighted in red? Just the back edge(s) that form the cycle, or all edges in the cycle path?
   - **Recommendation:** Highlight all edges in `validationResult.cycleNodes` as red. Use ReactFlow's edge styling to set `stroke: 'red'` for those edges.

4. **Save before validation:** Should we validate client-side first, or always call `POST /api/workflows/validate`?
   - **Recommendation:** Both. Client-side validates instantly. If client says valid, call backend to triple-check (catches server-side SIGNAL_WAIT config validation, job reference integrity, etc.). If backend rejects, show backend error message.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest (^3.0.5) + @testing-library/react (^16.2.0) |
| Config file | `puppeteer/dashboard/vitest.config.ts` (if exists) or inferred from vite.config.ts |
| Quick run command | `cd puppeteer/dashboard && npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` |
| Full suite command | `cd puppeteer/dashboard && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-06 | Drag chip from palette onto canvas adds new node at correct position | integration | `npm test -- --run src/components/__tests__/WorkflowNodePalette.test.tsx` | ❌ Wave 0 |
| UI-06 | Drawing edge between two nodes creates edge in state | unit | `npm test -- --run src/components/__tests__/DAGCanvas.test.tsx` (extend) | ✅ existing |
| UI-06 | Clicking unlinked SCRIPT node opens job selector popover | component | `npm test -- --run src/components/__tests__/ScriptNodeJobSelector.test.tsx` | ❌ Wave 0 |
| UI-06 | Selecting job from popover updates node.scheduled_job_id | component | `npm test -- --run src/components/__tests__/ScriptNodeJobSelector.test.tsx` | ❌ Wave 0 |
| UI-07 | Client-side DFS detects cycle; red error banner appears; Save disabled | unit | `npm test -- --run src/utils/__tests__/dagValidation.test.tsx` | ❌ Wave 0 |
| UI-07 | Depth warning banner appears at depth ≥ 25; still saveable | unit | `npm test -- --run src/utils/__tests__/dagValidation.test.tsx` | ❌ Wave 0 |
| UI-07 | Depth error banner appears at depth > 30; Save disabled | unit | `npm test -- --run src/utils/__tests__/dagValidation.test.tsx` | ❌ Wave 0 |
| UI-07 | IF gate node click opens right-side Sheet drawer | component | `npm test -- --run src/components/__tests__/IfGateConfigDrawer.test.tsx` | ❌ Wave 0 |
| UI-07 | IF gate form submits valid config_json matching GateEvaluationService schema | component | `npm test -- --run src/components/__tests__/IfGateConfigDrawer.test.tsx` | ❌ Wave 0 |
| UI-07 | Save button calls `POST /api/workflows/validate` before `PUT /api/workflows/{id}` | integration | `npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` (extend) | ✅ existing |
| UI-07 | Backend validation errors (cycle, depth, ref integrity) shown in error banner | integration | `npm test -- --run src/views/__tests__/WorkflowDetail.test.tsx` (extend) | ✅ existing |

### Sampling Rate
- **Per task commit:** `npm test -- --run src/components/__tests__/{component}.test.tsx` (focused file)
- **Per wave merge:** Full suite: `npm test` (all views, components, hooks, utils)
- **Phase gate:** All tests pass (`npm test --run`); npm build succeeds; no TypeScript errors

### Wave 0 Gaps
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
- [ ] Extend `src/views/__tests__/WorkflowDetail.test.tsx` — edit mode toggle, Save flow (validate + PUT), Cancel, active run blocks edit
- [ ] Extend `src/components/__tests__/DAGCanvas.test.tsx` — add onNodesChange, onEdgesChange, onConnect, onDrop handler tests
- [ ] Extend `src/components/__tests__/WorkflowStepNode.test.tsx` — unlinked badge rendering in edit mode
- [ ] Update `src/components/WorkflowStepNode.tsx` — add unlinked indicator, make clickable in edit mode
- [ ] Update `src/components/DAGCanvas.tsx` — accept edit mode handlers; wire onDrop, onDragOver
- [ ] Update `src/views/WorkflowDetail.tsx` — add edit mode state, Edit/Save/Cancel buttons, palette, validation banners
- [ ] Create or update `src/components/ui/popover.tsx` if not present (Radix wrapper)

*(If popover.tsx already exists or is created in Wave 0: "Popover component for SCRIPT job selector available"; otherwise flag as dependency.)*

---

## Sources

### Primary (HIGH confidence)
- **Context7 @xyflow/react v12.10.2** — ReactFlow node, edge, drag API, screenToFlowPosition() method
- **Context7 @dagrejs/dagre v3.0.0** — Sugiyama hierarchical layout algorithm
- **Official Phase 150 code** — WorkflowStepNode component (src/components/WorkflowStepNode.tsx), DAGCanvas (src/components/DAGCanvas.tsx), useLayoutedElements hook
- **Official Phase 148 code** — GateEvaluationService.evaluate_condition() schema (agent_service/services/gate_evaluation_service.py)
- **Official Phase 154 code** — WorkflowDetail structure, useQuery patterns, navigation
- **Official main.py routes** — `/api/workflows/validate` (line 2717–2733), `PUT /api/workflows/{id}` (line 2605–2611)

### Secondary (MEDIUM confidence)
- **shadcn/ui Sheet component** — Radix Dialog-based drawer (src/components/ui/sheet.tsx, existing)
- **Radix UI v1.1.15** — @radix-ui/react-dialog, @radix-ui/react-popover, @radix-ui/react-select (standard React a11y patterns)
- **React Hook Form + Zod** — Standard form validation in React ecosystem (not currently in dependencies, but referenced in CONTEXT.md for Phase 155 discretion)

### Tertiary (LOW confidence — should verify with Context7)
- **Popover component availability** — `src/components/ui/popover.tsx` not found in filesystem; may need creation or use of existing Popover primitive from @radix-ui/react-popover

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — ReactFlow, dagre, shadcn Sheet all verified in codebase; versions confirmed in package.json
- **Architecture:** HIGH — DAGCanvas `editable` prop already wired; Phase 150 patterns proven; ReactFlow drag-to-canvas is documented feature
- **Validation:** HIGH — DFS cycle detection is standard graph theory; GateEvaluationService schema is fixed; backend endpoints exist and verified
- **Pitfalls:** MEDIUM-HIGH — Coordinate transforms and state management are well-known ReactFlow pitfalls; IF gate config schema matches backend exactly (verified Phase 148 code)
- **Test infrastructure:** HIGH — vitest + RTL patterns established; Wave 0 gaps are clear and scoped

**Research date:** 2026-04-16
**Valid until:** 2026-05-14 (30 days; ReactFlow API is stable, phase scope is locked, no anticipated changes to backend validation endpoints)
**Next review:** When React 20.0 or @xyflow/react 13.0 released, or if Phase 149 changes webhook/parameter injection that affects workflow validation schema.

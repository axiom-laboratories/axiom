# Phase 155: Visual DAG Editor - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Drag-and-drop canvas for composing and editing Workflow DAGs. Users can add steps by dragging from a node-type palette, connect steps by drawing edges, configure IF gate conditions inline, and delete steps/edges. Real-time cycle detection and depth warnings (with save gating) are shown directly on the canvas. Closes UI-06 and UI-07.

**In scope:** Edit mode on the WorkflowDetail page, node palette, step configuration drawer, IF gate structured config form, cycle detection, depth warnings, save flow with backend validation.

**Not in scope:** Creating new workflows from scratch (that's an existing CRUD flow), cron/webhook trigger config editing (separate feature), run management actions.

</domain>

<decisions>
## Implementation Decisions

### Edit mode entry
- **Edit button on WorkflowDetail page** — same URL (`/workflows/:id`), no new route. An Edit button in the header toggles the page into edit mode.
- **In edit mode:** Canvas expands to full height; run history list is hidden (no distraction, more canvas space).
- **While editing:** Header shows `[Workflow Name] │ [Editing…] [Save] [Cancel]` — save and cancel are the primary CTAs.
- **Active run blocks edit:** If a WorkflowRun is currently RUNNING, the Edit button is disabled with an inline tooltip/warning: "This workflow has an active run. Editing is disabled until the run completes." No editing during live runs.

### Step palette and addition
- **Side palette in edit mode:** A narrow left panel slides in, listing all 6 node types (SCRIPT, IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT) as draggable chips. User drags a type onto the canvas to add a node.
- **SCRIPT node linking (click-to-configure):** A dropped SCRIPT node appears immediately as "Unlinked step ⚠". Clicking it opens a small popover with a job search/select input. Node remains invalid (marked ⚠) until a ScheduledJob is assigned. Unlinked SCRIPT nodes block Save.
- **Gate/join nodes (no assignment needed):** AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT, and IF_GATE nodes are valid as-dropped — they have no required ScheduledJob reference.
- **Delete:** Select a node or edge (ReactFlow built-in), then press Delete or Backspace to remove it. No context menu needed.
- **Edge drawing:** Drag from a node's source handle to another node's target handle — standard ReactFlow behaviour, enabled via `nodesConnectable={true}` in edit mode.

### IF gate inline config
- **Right-side slide-out drawer** (shadcn Sheet — same component used for step logs in Phase 150). Clicking an IF_GATE node in edit mode opens this drawer.
- **Structured form fields:**
  - Field: text input (e.g. `result.exit_code`)
  - Operator: dropdown — `==`, `!=`, `>`, `<`, `>=`, `<=`
  - Value: text input
  - True branch name: text input (e.g. `success`)
  - False branch name: text input (e.g. `failure`)
- **[Save condition]** button writes the structured form values into the node's `config_json`. **[Clear]** resets to unconfigured.
- **SCRIPT step drawer in edit mode:** Shows step name (editable text field) + assigned ScheduledJob name (with "Change" link to re-open the job selector popover). No retry or other config — job-level settings live on the Job Definitions page.

### Validation feedback
- **Cycle detection — red edge highlight + error banner:**
  - The edge(s) forming the cycle are highlighted red on the canvas.
  - An error banner below the edit toolbar reads: `❌ Cycle detected: A → B → A`
  - Save button is disabled until the cycle is resolved.
- **Depth warning — amber banner at depth ≥ 25:**
  - When the DAG's longest path reaches 25 steps, an amber banner appears: `⚠️ Depth: 26/30 max`
  - Still saveable at this level — it's a warning, not an error.
  - At depth > 30, the banner turns red and Save is disabled: `❌ Depth limit exceeded: 31/30 max`
- **Validation strategy:**
  - **Client-side, real-time:** DFS cycle detection and max-depth calculation run in the browser on every edge add/remove. Instant feedback, no API latency.
  - **Backend validate on Save:** Before calling `PUT /api/workflows/:id`, first call `POST /api/workflows/validate` as a final check. If the backend returns errors, block save and show the error message. If valid, proceed with the PUT.

### Save flow
- **Explicit Save button** — no auto-save.
- **On Save:** client validates (check unlinked SCRIPT nodes, cycle, depth) → `POST /api/workflows/validate` → if OK, `PUT /api/workflows/:id` with full updated steps + edges → success toast + edit mode exits → canvas returns to read-only with updated DAG.
- **On Cancel:** discard all in-progress changes, return to read-only mode.

### Claude's Discretion
- Exact palette panel width and visual styling
- Whether the node palette is an overlay or shifts the canvas
- Exact popover vs. inline-node UI for the SCRIPT job assignment
- Debounce timing for client-side validation (if any)
- Animation for entering/exiting edit mode
- Exact error/success toast content

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DAGCanvas` (`src/components/DAGCanvas.tsx`) — already has `editable` prop (`nodesConnectable={editable}`, `nodesDraggable={editable}`). Phase 155 wires this prop to the edit mode toggle. No DAGCanvas rewrite needed.
- `WorkflowStepNode` (`src/components/WorkflowStepNode.tsx`) — already renders all 6 node shapes with status colors. Needs extension for edit-mode affordances (⚠ unlinked indicator, clickable config trigger).
- `useLayoutedElements` hook (`src/hooks/useLayoutedElements.ts`) — dagre layout, LR direction. Used by DAGCanvas.
- shadcn `Sheet` component — available in `src/components/ui/`; used in Phase 150 for the step log drawer. Reuse for the IF gate config drawer.
- `WorkflowDetail.tsx` — already imports and renders `DAGCanvas`. Edit mode state and palette go here.
- `authenticatedFetch` (`src/auth.ts`) — for `PUT /api/workflows/:id` and `POST /api/workflows/validate` calls.
- `useQuery` / `@tanstack/react-query` — already used in WorkflowDetail; invalidate `workflows` query on successful save.

### Established Patterns
- ReactFlow `onNodesChange`, `onEdgesChange`, `onConnect` — standard handlers for local canvas state during editing. Docs: `@xyflow/react`.
- ReactFlow drag-to-canvas from external elements: uses `onDrop` + `onDragOver` on the ReactFlow wrapper, with `reactFlowInstance.screenToFlowPosition()` to convert drop coordinates.
- shadcn Sheet: `<Sheet open={open} onOpenChange={setOpen}><SheetContent side="right">...</SheetContent></Sheet>` pattern.
- `POST /api/workflows/validate` — already exists, returns `WorkflowValidationError[]` or `{}` on success. Check response shape before relying on it.
- `PUT /api/workflows/{workflow_id}` — accepts `WorkflowUpdate` with `steps` and `edges` arrays (replace-all semantics). All steps/edges must be included in the PUT.

### Integration Points
- `WorkflowDetail.tsx` — add edit mode state (`useState<boolean>`), palette component, Save/Cancel handlers, canvas-to-API save logic.
- `DAGCanvas.tsx` — extend `editable` prop to also accept `onNodesChange`, `onEdgesChange`, `onConnect`, `onDrop` callbacks for edit mode.
- `WorkflowStepNode.tsx` — add unlinked-step ⚠ indicator when `data.scheduledJobId` is null in edit mode.
- `main.py` — no new endpoints needed. `PUT /api/workflows/{id}` + `POST /api/workflows/validate` already exist.
- `AppRoutes.tsx` — no new routes needed (edit lives on `/workflows/:id`).

</code_context>

<specifics>
## Specific Ideas

- The edit mode layout mirrors the Phase 150 read-only canvas but adds a left palette panel. The `DAGCanvas` already has the `editable` prop built in — Phase 155 is primarily wiring state + adding the palette + save flow.
- The IF gate structured form maps to the existing `config_json` field on `WorkflowStep`. The form must serialize to the JSON schema the backend expects — check `workflow_service.py` for what fields `evaluate_condition()` reads.
- Unlinked SCRIPT nodes (no `scheduled_job_id`) are valid in-flight edits but must block Save. The backend will reject a step without a job reference anyway — the client check just gives earlier feedback.
- "Carry forward from Phase 150": Edit mode's read-only panel (Phase 150) and the edit panel (Phase 155) share the same `DAGCanvas` component — the `editable` flag is the only toggle between them.

</specifics>

<deferred>
## Deferred Ideas

- Creating a brand-new workflow from a blank canvas (currently done via JSON/form) — UX enhancement for a future phase
- Workflow parameter editing from the canvas (add/remove `WorkflowParameter` entries) — Phase 155 focuses on steps + edges + IF gate config
- Undo/redo on the canvas — useful but out of scope for this phase
- Copy/paste of nodes on the canvas — scope creep; not in UI-06 or UI-07

</deferred>

---

*Phase: 155-visual-dag-editor*
*Context gathered: 2026-04-16*

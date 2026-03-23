# Phase 50: Guided Job Form - Research

**Researched:** 2026-03-23
**Domain:** React form UX — structured guided form replacing raw JSON dispatch card in Jobs.tsx
**Confidence:** HIGH

## Summary

Phase 50 is a pure frontend refactor of the existing dispatch card in `Jobs.tsx`. The goal is to replace the current raw-JSON textarea with a structured guided form that constructs the `POST /jobs` payload from discrete fields. No backend changes are needed — the `JobCreate` model already carries every field the guided form must populate (`task_type`, `payload`, `runtime`, `target_tags`, `capability_requirements`, `name`, `signature_id`, `signature`).

The implementation draws entirely on patterns already present in the codebase. Every component needed exists: Radix `Select` for dropdowns, the chip-input pattern from the Phase 49 filter sheet (tag input + `×` remove), the amber warning pattern from Phase 48 DRAFT state, and the `signature_id` + `signature` inline signing section from `JobDefinitionModal.tsx`. The `[ADV]` mode gate uses a Radix `Dialog` for the confirmation step, the same component already in use throughout the app.

The only novel piece is the collapsible JSON preview accordion. Radix `Collapsible` is **not** currently installed. The implementation should use a simple `useState` toggle with a `ChevronDown/Up` icon button — matching the existing `showMoreFilters` pattern in `Jobs.tsx` — rather than adding a new Radix dependency.

**Primary recommendation:** Build the guided form as a self-contained `GuidedDispatchCard` component co-located in `src/components/` and drop it into the existing card slot in `Jobs.tsx`, replacing the current dispatch state inline. This keeps the 500+ line Jobs.tsx from growing further and makes testing straightforward.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Form layout & structure**
- Guided form replaces the existing dispatch card in-place — no modal or sheet; the current "Configure a manual orchestration payload" card becomes the guided form
- Single-page layout: all fields visible at once — Name, Runtime, Script content, Targeting section, Sign section, Dispatch button
- An `[ADV]` button in the card header provides access to Advanced mode
- JSON preview: collapsible `[▼ Generated Payload]` accordion below the form fields; closed by default; updates live as fields are filled

**Signing UX**
- Signature fields are inline in the guided form (same as current raw form) — no separate signing step or dialog
- Key ID field is a dropdown populated from `GET /signatures` — operator selects a registered key; `signature_id` is set automatically
- Signature field: freeform text input for the Ed25519 signature string
- Dispatch button is disabled until both `signature_id` and `signature` are non-empty
- If the script content changes after a signature has been pasted: signature fields are cleared and an amber inline warning appears — "Script changed — re-sign required." Prevents dispatch with a stale signature.

**Target & routing fields**
- A unified "Targeting" section contains three fields:
  1. Node dropdown (optional): populated from live node list; operator can target a specific node
  2. Target tag chips (chip input): autocomplete suggestions fetched from distinct `target_tags` on registered nodes; freeform typing also allowed
  3. Capability tag chips (chip input): freeform type-and-add; no server-side autocomplete
- At least one targeting field is required before the Dispatch button is enabled — operator must select a node or add at least one tag or capability chip before dispatch is permitted
- Chip interaction: type value → press Enter or comma to add; click chip `×` to remove

**Advanced mode gate**
- Trigger: `[ADV]` button in the top-right of the card header
- Confirmation dialog text: "Switch to Advanced mode? Your current form values will be converted to JSON. You won't be able to switch back without clearing the form." Buttons: Cancel | Switch to Advanced
- Pre-fill behaviour: on switching, current guided form values are serialised into the JSON editor — operator sees the JSON they were about to submit
- Return to guided mode: a "Reset form" (or "← Guided") button appears in Advanced mode; clicking shows: "Clear the JSON editor and return to guided mode?" Buttons: Cancel | Reset. Resets to a blank guided form.
- Advanced mode JSON validation (client-side, required fields only before Dispatch is enabled):
  - JSON must parse without errors
  - Must contain `task_type: "script"`, a `payload` object, and a `runtime` field
  - Dispatch button shows "Fix JSON errors" tooltip if validation fails

### Claude's Discretion
- Exact chip component implementation (reuse Phase 49 filter chip pattern vs standalone)
- Whether the collapsible JSON preview uses a Radix Collapsible or a simple toggle state
- Exact layout/spacing of the Targeting section and Sign section within the single-page form
- Autocomplete dropdown behaviour (debounce, min-chars, empty state)
- Whether targeting requirement validation shows inline field error or disables the Dispatch button with a tooltip

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-01 | Operator can submit a job using a structured guided form (runtime selector, script textarea, target environment dropdown, capability tag chips) | Existing Radix Select, textarea, and chip-input patterns all present in codebase. No new dependencies. |
| JOB-02 | Operator can view the generated JSON payload from guided mode in a read-only panel without editing it | Simple `JSON.stringify` of derived state, controlled toggle for expand/collapse; no additional library needed. |
| JOB-03 | Operator can switch to Advanced (raw JSON) mode via a one-way gate with a confirmation dialog; form validates JSON against schema before submission | Radix Dialog already in use throughout the app; JSON validation is pure JS. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2 | Component model | Project standard |
| TypeScript | project default | Type safety | Project standard |
| Tailwind CSS | project default | Utility styling | Project standard |
| Radix UI Select | @radix-ui/react-select ^2.2.6 | Runtime & Key ID dropdowns | Already in package.json; already wrapped in `select.tsx` |
| Radix UI Dialog | @radix-ui/react-dialog ^1.1.15 | Mode-switch confirmation | Already in package.json; used throughout app |
| Radix UI Tooltip | @radix-ui/react-tooltip ^1.2.8 | "Fix JSON errors" tooltip on disabled Dispatch | Already in package.json |
| lucide-react | ^0.562.0 | Icons (ChevronDown/Up, X, AlertTriangle) | Project standard |
| authenticatedFetch | `src/auth.ts` | API calls | Project standard for all API calls |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner (toast) | already in project | Dispatch success/error feedback | On POST /jobs response |
| @testing-library/react | ^16.2.0 | Component tests | Tests for GuidedDispatchCard |
| vitest | ^3.0.5 | Test runner | All frontend tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Simple useState toggle for JSON preview | @radix-ui/react-collapsible | Collapsible is NOT currently installed. Simple toggle is zero-dep and matches existing `showMoreFilters` pattern |
| Inline chip pattern (copy from Phase 49) | Generic chip library | Inline is zero-dep, already validated in codebase |

**Installation:**
```bash
# No new dependencies required — all needed packages already in package.json
```

---

## Architecture Patterns

### Recommended Project Structure

Extract the guided form into a dedicated component file:

```
src/
├── components/
│   └── GuidedDispatchCard.tsx   # new — self-contained guided form card
├── views/
│   └── Jobs.tsx                 # modified — mounts GuidedDispatchCard, removes old dispatch state
```

`GuidedDispatchCard` owns all guided-mode state. `Jobs.tsx` receives an `onJobCreated` callback to trigger `fetchJobs({ reset: true })` after successful dispatch.

### Pattern 1: Guided Form State Shape

**What:** A single state object captures all guided form fields, plus separate `advancedMode` and `advancedJson` states for the Advanced mode branch.

**When to use:** Keeps the form manageable; makes serialisation to JSON preview trivial.

```typescript
// Guided form state
interface GuidedFormState {
  name: string;
  runtime: 'python' | 'bash' | 'powershell';
  scriptContent: string;
  targetNodeId: string;
  targetTags: string[];
  capabilityReqs: string[];   // stored as "key:value" strings, parsed on submit
  signatureId: string;
  signature: string;
  signatureCleared: boolean;  // amber warning trigger
}
```

### Pattern 2: Derive JSON Preview from State

**What:** Compute `generatedPayload` as a `useMemo` over `GuidedFormState` — same computation used to build the `POST /jobs` body on submit.

**When to use:** Ensures the preview always matches what gets sent.

```typescript
const generatedPayload = useMemo(() => {
  return {
    task_type: 'script',
    runtime: form.runtime,
    payload: { script: form.scriptContent },
    ...(form.name && { name: form.name }),
    ...(form.targetNodeId && { target_node_id: form.targetNodeId }),
    ...(form.targetTags.length && { target_tags: form.targetTags }),
    ...(form.capabilityReqs.length && {
      capability_requirements: Object.fromEntries(
        form.capabilityReqs.map(s => s.split(':').map(p => p.trim()) as [string, string])
      )
    }),
    signature_id: form.signatureId,
    signature: form.signature,
  };
}, [form]);
```

### Pattern 3: Stale Signature Detection

**What:** `useEffect` watches `form.scriptContent`. When content changes AND `form.signature` is non-empty, clear both signature fields and set `signatureCleared = true`.

**When to use:** Satisfies the locked "Script changed — re-sign required" warning.

```typescript
const prevScriptRef = useRef(form.scriptContent);
useEffect(() => {
  if (form.scriptContent !== prevScriptRef.current && form.signature) {
    setForm(f => ({ ...f, signature: '', signatureId: '', signatureCleared: true }));
  }
  prevScriptRef.current = form.scriptContent;
}, [form.scriptContent]);
```

### Pattern 4: Chip Input (reuse Phase 49 pattern)

**What:** Controlled string array in state + text input. Press Enter or comma to add. Chip `×` removes.

**When to use:** Target tags chip, Capability requirements chip. Already battle-tested in Phase 49.

```typescript
// In Phase 49's filter sheet (Jobs.tsx lines 390–396, 504–514)
const addTag = (value: string) => {
  const trimmed = value.trim().replace(/,$/, '');
  if (trimmed && !tags.includes(trimmed)) setTags(t => [...t, trimmed]);
  setTagInput('');
};
// onKeyDown: e.key === 'Enter' || e.key === ',' → addTag(input)
// Render chips: {tags.map(t => <span>...{t}<button onClick={() => remove(t)}>×</button></span>)}
```

### Pattern 5: Mode-Switch Confirmation Dialog

**What:** `[ADV]` button sets `pendingAdvSwitch = true`, rendering a Radix Dialog. "Switch to Advanced" handler: serialises guided form to JSON → sets `advancedJson` → sets `advancedMode = true` → clears `pendingAdvSwitch`.

```typescript
// Serialise on switch
const handleSwitchToAdvanced = () => {
  setAdvancedJson(JSON.stringify(generatedPayload, null, 2));
  setAdvancedMode(true);
  setPendingAdvSwitch(false);
};
```

### Pattern 6: Advanced Mode JSON Validation

**What:** `useMemo` validates parsed advanced JSON. Dispatch button disabled if validation fails.

```typescript
const advancedJsonError = useMemo(() => {
  if (!advancedMode) return null;
  try {
    const parsed = JSON.parse(advancedJson);
    if (parsed.task_type !== 'script') return 'Must have task_type: "script"';
    if (!parsed.payload || typeof parsed.payload !== 'object') return 'Must have a payload object';
    if (!parsed.runtime) return 'Must have a runtime field';
    return null;
  } catch {
    return 'Invalid JSON';
  }
}, [advancedJson, advancedMode]);
```

### Pattern 7: Dispatch Button Enable Conditions

**Guided mode:** `signature_id` non-empty AND `signature` non-empty AND (targetNodeId OR targetTags.length > 0 OR capabilityReqs.length > 0)

**Advanced mode:** `advancedJsonError === null`

### Anti-Patterns to Avoid

- **Keeping dispatch state in Jobs.tsx:** The existing `newTaskPayload`, `dispatchTargetTags`, `capabilityReqs`, `newRuntime` state variables in Jobs.tsx should be removed and replaced by the new component. Do not add guided-form state alongside old state in Jobs.tsx.
- **Calling `GET /nodes` twice:** Jobs.tsx already fetches nodes on mount. Pass the `nodes` list down as a prop to `GuidedDispatchCard` rather than fetching again inside the component.
- **Radix Collapsible as new dependency:** Not needed. Use `useState<boolean>` toggle for the JSON preview. No new package install required.
- **Building a generic chip component:** The chip pattern is ~20 lines of JSX. Do not extract to a separate component unless the planner explicitly creates a shared component task.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal confirmation dialog | Custom modal div with portal | Radix Dialog (`@radix-ui/react-dialog`) | Already installed, accessible, handles focus trap and keyboard dismiss |
| Dropdown selects | Custom dropdown | Radix Select (`select.tsx`) | Already wrapped and styled for this project |
| Disabled button tooltip | Custom tooltip div | Radix Tooltip (`@radix-ui/react-tooltip`) | Already installed |
| JSON syntax highlighting | Monaco editor or CodeMirror | Plain `<textarea>` with `font-mono text-green-500` | Advanced mode textarea follows existing Jobs.tsx payload textarea style; no syntax highlighting needed |

---

## Common Pitfalls

### Pitfall 1: `target_node_id` vs `target_tags` semantics

**What goes wrong:** The `JobCreate` model has `target_tags: Optional[List[str]]` but no `target_node_id` at the top level. The node filter is applied by the job service using `target_tags`, not a dedicated field. If the form sends `target_node_id` as a top-level field, the backend ignores it.

**Why it happens:** The current dispatch form only passes `target_tags` (comma-split text), not a dedicated node ID field. Looking at `JobCreate` in `models.py` — there is no `target_node_id` field. The node dropdown in the guided form should add the selected node's ID to `target_tags` (as a tag), OR the form should pass `node_id` as a separate field and the backend job service should support it.

**How to avoid:** Check `job_service.py` node selection logic to see how node targeting actually works. If the service only uses `target_tags` for routing, the node dropdown value should populate `target_tags` (e.g., `["node:{node_id}"]`) OR the form should pass it differently. The CONTEXT.md says "Node dropdown (optional): populated from live node list; operator can target a specific node" — verify that the existing payload format supports this and adjust accordingly.

**Warning signs:** Job dispatched but never assigned to the intended node.

### Pitfall 2: Autocomplete suggestions for target tags

**What goes wrong:** The CONTEXT.md specifies "autocomplete suggestions fetched from distinct `target_tags` on registered nodes." There is **no** `GET /nodes/tags` or similar endpoint in the current backend. The `GET /nodes` response includes `tags` per node, but no aggregate distinct-tags endpoint exists.

**Why it happens:** The feature was designed without confirming the backend supports it.

**How to avoid:** Derive distinct tag suggestions client-side from the `nodes` array that `Jobs.tsx` already fetches. Extract all `tags` arrays, flatten, deduplicate, sort. This avoids adding a new backend endpoint for Phase 50.

```typescript
const tagSuggestions = useMemo(() =>
  [...new Set(nodes.flatMap(n => n.tags ?? []))].sort(),
  [nodes]
);
```

**Warning signs:** 404 or 422 error when trying to call a non-existent tags endpoint.

### Pitfall 3: Signature field clearing races with React state

**What goes wrong:** If the script content change and signature clear happen in separate `setState` calls inside `useEffect`, the amber warning may flicker or not appear.

**Why it happens:** Multiple `setState` in the same effect can cause intermediate renders.

**How to avoid:** Use a single `setForm(f => ({ ...f, signature: '', signatureId: '', signatureCleared: true }))` call. Clear `signatureCleared` back to `false` when the user starts typing a new signature.

### Pitfall 4: Serialising capability requirements for `POST /jobs`

**What goes wrong:** Capability requirements are stored as chip strings like `"python:3.11"`. The `JobCreate` model expects `capability_requirements: Dict[str, str]`, e.g., `{"python": "3.11"}`.

**How to avoid:** Parse chip strings at submit time:
```typescript
const caps = capabilityReqs.length
  ? Object.fromEntries(
      capabilityReqs.map(s => s.split(':').map(p => p.trim()) as [string, string])
    )
  : undefined;
```
Filter out any chips that don't contain `:`.

### Pitfall 5: Advanced mode does not send `signature`/`signature_id`

**What goes wrong:** In Advanced mode the operator edits raw JSON. They may not include `signature`/`signature_id` fields in the JSON if they forget. The backend will accept the job but nodes will reject it at verification.

**How to avoid:** The Advanced mode JSON validator (`advancedJsonError`) only enforces `task_type`, `payload`, and `runtime` (as locked in CONTEXT.md). Do not add `signature` to the validation — that is the operator's responsibility in Advanced mode. Just make sure the JSON editor is pre-filled with the guided form's values (including `signature` and `signature_id` if they were already entered).

### Pitfall 6: Removing Phase 47 runtime dropdown without removing the state

**What goes wrong:** Phase 47 added `newRuntime` state and a runtime `<Select>` to Jobs.tsx. If the guided form component is added but the old state is not cleaned up, there will be dead state variables.

**How to avoid:** The plan should explicitly include a task to remove `newTaskType`, `newRuntime`, `newTaskPayload`, `payloadError`, `dispatchTargetTags`, `capabilityReqs`, and `isSubmitting` from Jobs.tsx state when the old dispatch card is replaced.

---

## Code Examples

Verified patterns from existing codebase:

### Amber warning (stale signature)
```tsx
// Source: Phase 48 DRAFT warning — Jobs.tsx / JobDefinitionModal.tsx
{signatureCleared && (
  <div className="flex items-center gap-2 p-2 rounded-md bg-amber-950/30 border border-amber-800/50">
    <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
    <p className="text-xs text-amber-400">Script changed — re-sign required.</p>
  </div>
)}
```

### Chip render pattern (Phase 49 filter sheet, Jobs.tsx lines 504–514)
```tsx
// Source: Jobs.tsx MoreFiltersPanel, Target Tags section
{tags.map(tag => (
  <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-700 text-xs text-zinc-300 border border-zinc-600">
    {tag}
    <button onClick={() => setTags(t => t.filter(x => x !== tag))} className="hover:text-white">
      <X className="h-2.5 w-2.5" />
    </button>
  </span>
))}
```

### Radix Dialog (confirmation gate)
```tsx
// Source: existing Dialog usage throughout app (e.g. JobDefinitions.tsx ReSignDialog)
<Dialog open={pendingAdvSwitch} onOpenChange={setPendingAdvSwitch}>
  <DialogContent className="bg-zinc-925 border-zinc-800 text-white sm:max-w-md">
    <DialogHeader>
      <DialogTitle>Switch to Advanced mode?</DialogTitle>
      <DialogDescription className="text-zinc-400">
        Your current form values will be converted to JSON. You won't be able to switch back without clearing the form.
      </DialogDescription>
    </DialogHeader>
    <div className="flex justify-end gap-3 pt-4">
      <Button variant="ghost" onClick={() => setPendingAdvSwitch(false)}>Cancel</Button>
      <Button onClick={handleSwitchToAdvanced}>Switch to Advanced</Button>
    </div>
  </DialogContent>
</Dialog>
```

### Key ID dropdown (reference: JobDefinitionModal.tsx lines 171–186)
```tsx
// Source: JobDefinitionModal.tsx — Root of Trust section
<Select value={form.signatureId} onValueChange={v => setForm(f => ({ ...f, signatureId: v, signatureCleared: false }))}>
  <SelectTrigger className="bg-zinc-900 border-zinc-800 h-11">
    <SelectValue placeholder="Select signing key..." />
  </SelectTrigger>
  <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
    {signatures.map(s => (
      <SelectItem key={s.id} value={s.id}>
        {s.name} ({s.uploaded_by})
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

### JSON preview toggle (simple state — no Radix Collapsible)
```tsx
const [previewOpen, setPreviewOpen] = useState(false);
// ...
<button
  type="button"
  onClick={() => setPreviewOpen(p => !p)}
  className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300"
>
  {previewOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
  Generated Payload
</button>
{previewOpen && (
  <pre className="text-xs text-green-400 font-mono bg-zinc-950 rounded-lg p-3 overflow-auto max-h-64 whitespace-pre-wrap">
    {JSON.stringify(generatedPayload, null, 2)}
  </pre>
)}
```

### Node dropdown (node list already fetched in Jobs.tsx — pass as prop)
```tsx
// Jobs.tsx already has: nodes state fetched from GET /nodes?page_size=200
// GuidedDispatchCard receives nodes: NodeItem[] as a prop
<Select value={form.targetNodeId} onValueChange={v => setForm(f => ({ ...f, targetNodeId: v }))}>
  <SelectTrigger className="bg-zinc-900 border-zinc-800 h-11">
    <SelectValue placeholder="Any available node" />
  </SelectTrigger>
  <SelectContent className="bg-zinc-900 border-zinc-800 text-white">
    <SelectItem value="">Any available node</SelectItem>
    {nodes.map(n => (
      <SelectItem key={n.node_id} value={n.node_id}>
        {n.hostname || n.node_id}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw JSON textarea for all dispatch | Guided form with structured fields | Phase 50 (this phase) | Operators no longer author JSON; reduces malformed dispatch errors |
| Comma-split text input for tags | Chip input with Enter/comma add | Phase 49 filter bar established pattern | Consistent with filter bar; visual clarity on selected tags |
| Inline dispatch state in Jobs.tsx | Extracted GuidedDispatchCard component | Phase 50 (recommended) | Jobs.tsx stays manageable in size |

**Deprecated/outdated:**
- `newTaskPayload` raw textarea in Jobs.tsx: removed and replaced by `scriptContent` field in guided form
- `dispatchTargetTags` comma-split input: replaced by chip array state
- `capabilityReqs` comma-split input: replaced by chip array state
- Phase 47 runtime `<Select>` in Jobs.tsx card: superseded; runtime moves into guided form

---

## Open Questions

1. **Does `target_node_id` exist as a `JobCreate` field?**
   - What we know: `JobCreate` in `models.py` has `target_tags: Optional[List[str]]` but no `target_node_id` field.
   - What's unclear: How does the job service route to a specific node? Does it use `target_tags` for this (e.g., matching node ID as a tag), or is there a separate mechanism?
   - Recommendation: The planner should add a task to inspect `job_service.py` node selection logic before implementing the node dropdown. If no `target_node_id` field exists, the dropdown value should be serialised differently (e.g., added to `target_tags` as the node_id string, which the service already uses for tag matching).

2. **Node tags autocomplete: client-side vs backend**
   - What we know: No `GET /nodes/tags` endpoint exists. `GET /nodes` returns per-node `tags` arrays.
   - What's unclear: Whether nodes page-size=200 fetch is a sufficient approximation of "all nodes."
   - Recommendation: Derive distinct tags client-side from the already-fetched `nodes` array. Document that this covers only the first 200 nodes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 3.0.5 + @testing-library/react 16.2 |
| Config file | `package.json` `"test": "vitest"` + `src/test/setup.ts` |
| Quick run command | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` |
| Full suite command | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-01 | Guided form renders runtime selector, script textarea, node dropdown, tag chips, capability chips | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-01 | Dispatch button disabled until targeting + signing preconditions met | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-01 | On submit, POST /jobs called with correct structured payload | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-02 | JSON preview accordion shows generated payload from form state | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-02 | JSON preview is read-only (no editable textarea in guided mode) | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-03 | [ADV] button triggers confirmation dialog | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-03 | Confirming Advanced mode pre-fills JSON editor with guided form values | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-03 | Dispatch disabled in Advanced mode when JSON is invalid | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |
| JOB-03 | "← Guided" reset dialog clears JSON editor and returns to guided mode | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx`
- **Per wave merge:** `cd puppeteer/dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` — covers JOB-01, JOB-02, JOB-03

*(No `GuidedDispatchCard.test.tsx` needed if the component is tested via Jobs.test.tsx mount. A dedicated component test file is acceptable but not required.)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection — `puppeteer/dashboard/src/views/Jobs.tsx` (dispatch form state lines 572–786, chip pattern lines 390–514)
- Direct code inspection — `puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx` (signing section pattern)
- Direct code inspection — `puppeteer/agent_service/models.py` `JobCreate` (lines 6–36)
- Direct code inspection — `puppeteer/agent_service/main.py` `GET /nodes`, `GET /signatures` endpoints
- Direct code inspection — `puppeteer/dashboard/package.json` (Radix packages installed)
- Direct code inspection — `puppeteer/dashboard/src/components/ui/select.tsx`, `dialog.tsx`, `tabs.tsx`

### Secondary (MEDIUM confidence)
- Phase 49 CONTEXT.md / STATE.md decisions — chip input pattern established and working

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed from package.json inspection
- Architecture: HIGH — patterns directly verified in existing codebase
- Pitfalls: HIGH (backend semantics), MEDIUM (autocomplete gap) — verified from source code

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable React/Radix stack; frontend-only change)

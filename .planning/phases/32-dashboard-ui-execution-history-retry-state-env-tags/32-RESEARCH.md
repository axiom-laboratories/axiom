# Phase 32: Dashboard UI — Execution History, Retry State, Env Tags — Research

**Researched:** 2026-03-18
**Domain:** React/TypeScript dashboard — frontend-only UI phase
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**History panel placement:**
- Execution history lives in the **JobDefinitions view**, not the Jobs view — clicking a definition expands a history section below the definitions table (master-detail split: top = definitions list, bottom = history for selected definition)
- Clicking a run row in the history section opens the existing **ExecutionLogModal** (reuse, not new component)
- The standalone **History.tsx page also gets a job definition selector** — a filter/dropdown to drill down to a specific definition from the global history page

**Retry attempt grouping in history list:**
- History list shows **one row per job_run_id** (grouped, not flat per-attempt)
- "Attempt N of M" badge appears **only when relevant** — when max_retries > 1 and the run has > 1 attempt. Single-attempt completions show no badge
- Badge colours: **amber** for RETRYING (in-progress retries), **red** for FAILED after exhausting retries (e.g. "Failed 3/3")

**ExecutionLogModal extensions:**
- **Extend the existing ExecutionLogModal** — do not build a new component
- When a run has multiple attempts: **tabs across the top** of the modal for switching between attempts (e.g. "Attempt 1 | Attempt 2 | Attempt 3 (final)")
- **Attestation status in the modal header** alongside the status badge: "Execution #123  COMPLETED  VERIFIED" — visible without scrolling
- **stdout/stderr displayed interleaved** with [OUT] / [ERR] stream labels — preserves execution sequence (already implemented — extend, don't replace)
- **Colour coding**: stderr lines in red/amber text, stdout lines normal white; exit code shown in the header as green (exit 0) or red (non-zero exit)

**Env tag display in Nodes view:**
- **Colour-coded badge near the hostname** on each node card: DEV = blue, TEST = amber, PROD = red/rose, custom = zinc
- Nodes with **no env_tag set show no badge** — not "UNTAGGED", just absent
- **Dropdown above the node cards**: "Filter by environment: [All ▾]"
- Filter options are **dynamically derived** from the unique env_tags present in the current node list — handles custom tags automatically; "All" always appears

### Claude's Discretion
- Exact pixel layout of the master-detail split in JobDefinitions (proportion, divider style)
- Whether the "selected definition" row in the table is highlighted or just tracked in state
- Pagination or scroll approach for the history section (likely match History.tsx's existing 25-item limit)
- Exact wording for empty history state ("No runs yet for this definition")
- Attestation badge icon choice (shield, check circle, etc.) — consistent with existing attestation UI patterns

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUTPUT-03 | User can view stdout/stderr output for any past execution from the dashboard | ExecutionLogModal already renders interleaved output_log; history panel in JobDefinitions.tsx drives it; API endpoint confirmed |
| OUTPUT-04 | User can query execution history — list of all past runs for a given job definition or node, with status and timestamps | Backend gap identified: no `job_definition_id` filter on `GET /api/executions`; workaround via job_run_id lookup described below |
| RETRY-03 | Dashboard displays retry state (attempt N of M) on in-progress and failed runs, and shows all attempt records in execution history | `attempt_number`, `job_run_id`, `max_retries` all present in `ExecutionRecordResponse`; grouping logic is pure frontend |
| ENVTAG-03 | Dashboard Nodes view displays the environment tag for each node; tag is filterable | `env_tag` present on `NodeResponse` (confirmed Phase 31); Node interface in Nodes.tsx needs extending; filter is purely frontend state |
</phase_requirements>

---

## Summary

Phase 32 is a pure frontend phase. All required backend data is already in place from Phases 29, 30, and 31 — with one significant exception: `attestation_verified` exists on the `ExecutionRecord` DB model but is **not included** in `ExecutionRecordResponse`. The list endpoint at `GET /api/executions` and the single-record endpoint at `GET /api/executions/{id}` both omit this field. Surfacing attestation status in the modal header therefore requires adding `attestation_verified` to `ExecutionRecordResponse` and to both handler mappings in `main.py`. This is a small, low-risk backend change (one field addition).

A second gap: `GET /api/executions` has no `job_definition_id` (i.e. `scheduled_job_id`) filter parameter. The `Job` DB table links to `ScheduledJob` via `scheduled_job_id`, but `ExecutionRecord` stores only `job_guid` — not `scheduled_job_id`. To fetch execution history for a definition, the frontend must first load the associated `Job` GUIDs (from `GET /jobs?scheduled_job_id=X` or by inspecting the jobs list) then query executions per GUID, or the backend needs a bridging query. The simplest fix is adding a `scheduled_job_id` filter to `GET /api/executions` that joins through the `jobs` table. Alternatively, the history panel queries `GET /jobs/definitions/{id}` (which returns script content) and then uses the existing `scheduled_job_id` field on jobs. **The recommended approach is a thin backend addition**: a `scheduled_job_id` query param on `GET /api/executions` that does a subquery through `Job.scheduled_job_id`.

The `env_tag` field is already present on `NodeResponse` (added Phase 31, line 187 of models.py). The `Node` interface in `Nodes.tsx` needs a single field addition (`env_tag?: string`) and a new badge component + filter dropdown, both purely frontend.

**Primary recommendation:** Fix the two backend gaps first (attestation_verified on ExecutionRecordResponse; scheduled_job_id filter on /api/executions), then build the four frontend changes as independent units.

---

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| React + TypeScript | 18.x | Component model | All new code follows existing patterns |
| @tanstack/react-query | 5.x | Server state + caching | Already used in History.tsx, Nodes.tsx |
| Vitest + @testing-library/react | current | Component tests | Config at `puppeteer/dashboard/vitest.config.ts` |
| shadcn/ui (Badge, Table, Select, Dialog, Button) | current | UI components | Badge, Table, Select already imported in relevant files |
| lucide-react | current | Icons | Already imported throughout |
| date-fns | current | Time formatting (`formatDistanceToNow`) | Already used in History.tsx |

No new npm packages are required for this phase.

---

## Architecture Patterns

### Recommended Project Structure

Changes are confined to existing files:

```
puppeteer/
├── agent_service/
│   ├── main.py                  # Add scheduled_job_id filter to GET /api/executions
│   └── models.py                # Add attestation_verified to ExecutionRecordResponse
└── dashboard/src/
    ├── views/
    │   ├── JobDefinitions.tsx   # Add selectedDefinitionId state, history panel below list
    │   ├── History.tsx          # Add job definition selector dropdown (new Select filter)
    │   └── Nodes.tsx            # Add env_tag to Node interface; add env filter dropdown
    └── components/
        ├── ExecutionLogModal.tsx # Add attestation badge in header; fix attempt tabs
        └── job-definitions/
            └── JobDefinitionList.tsx  # Expose onSelect(id) callback; highlight selected row
```

### Pattern 1: Backend Gap — attestation_verified missing from ExecutionRecordResponse

**What:** `ExecutionRecord.attestation_verified` (String(16): 'verified' | 'failed' | 'missing' | None) exists in the DB model but both `GET /api/executions` handlers construct `ExecutionRecordResponse` without mapping it.

**Fix:** Add `attestation_verified: Optional[str] = None` to `ExecutionRecordResponse` in models.py, and add `attestation_verified=r.attestation_verified` to both handler construction blocks in main.py (lines ~469-486 and ~512-529).

### Pattern 2: Backend Gap — no job_definition_id filter on /api/executions

**What:** `ExecutionRecord` has no direct FK to `ScheduledJob`. The link is: `ScheduledJob.id` → `Job.scheduled_job_id` → `Job.guid` → `ExecutionRecord.job_guid`.

**Fix:** Add `scheduled_job_id: Optional[str] = None` parameter to `list_executions`. When provided, add a subquery:
```python
# WHERE job_guid IN (SELECT guid FROM jobs WHERE scheduled_job_id = :sid)
subq = select(Job.guid).where(Job.scheduled_job_id == scheduled_job_id)
query = query.where(ExecutionRecord.job_guid.in_(subq))
```
This is one additional query condition and stays within the existing handler structure.

### Pattern 3: Master-Detail in JobDefinitions

**What:** The JobDefinitions view needs a selected-definition panel at the bottom showing execution history for that definition.

**Implementation:** Add `selectedDefId: string | null` state to `JobDefinitions.tsx`. Pass an `onSelect(id: string)` callback to `JobDefinitionList`. When a row is clicked (separate from the chevron expand that shows source code), set `selectedDefId`. Below `<JobDefinitionList>`, render a `<DefinitionHistoryPanel definitionId={selectedDefId} />` component (new, inline or separate file). The panel queries `GET /api/executions?scheduled_job_id=X&limit=25`.

**Selected-row highlight:** Use a conditional class on the `<TableRow>` in `JobDefinitionList`: `bg-primary/5 border-l-2 border-l-primary` when `def.id === selectedDefId`. Pass `selectedDefId` as a prop.

**Important:** The existing chevron expand (which shows source code) must remain independent of the selection click. The row click area for selection should be the definition name cell only, not the whole row, to avoid conflict with the chevron toggle.

### Pattern 4: ExecutionLogModal Attempt Tabs

**What:** The modal already has a bottom bar for attempt switching (lines 166-180 of ExecutionLogModal.tsx). The CONTEXT.md requires moving these tabs to the **top** of the modal.

**Current:** Tabs rendered at the bottom after the log area.
**Required:** Tabs rendered in the header area, below the title/metadata row.

**Attestation badge in header:** The `selected` object will now carry `attestation_verified`. Add a badge in the `DialogHeader` section:
- 'verified' → green shield/check, text "VERIFIED"
- 'failed' → red alert, text "ATTEST FAILED"
- 'missing' → zinc outline, text "NO ATTESTATION"
- null/undefined → render nothing

**Attempt tab labels:** The modal currently numbers attempts as `Attempt {executions.length - i}` (reversed order). For the definition history use-case, attempts should be ordered oldest-first and labelled "Attempt 1", "Attempt 2", "Attempt 3 (final)". The final tab (highest `attempt_number`) gets the "(final)" suffix.

**New invocation pattern for definition history:** The modal currently accepts `jobGuid` or `executionId`. For the history panel in JobDefinitions, the caller has a `job_run_id` and needs all attempts for that run. Add a third prop: `jobRunId?: string` that queries `GET /api/executions?job_run_id=X` (requires another backend filter param addition — see Pattern 5).

### Pattern 5: Additional Backend Filter — job_run_id on /api/executions

**What:** To load all attempts for a specific run in the ExecutionLogModal (from the definition history panel), the frontend needs `GET /api/executions?job_run_id=X`.

**Fix:** Add `job_run_id: Optional[str] = None` parameter alongside `scheduled_job_id` in the same handler extension:
```python
if job_run_id:
    query = query.where(ExecutionRecord.job_run_id == job_run_id)
```

### Pattern 6: Env Tag Filter in Nodes

**What:** A dropdown above the node cards that shows unique env_tags from the live node list.

**Implementation pattern** (mirrors existing text filter in Nodes.tsx):
```typescript
const [envFilter, setEnvFilter] = useState<string>('ALL');

// Derived from live data — no separate query
const uniqueEnvTags = useMemo(() => {
    const tags = (nodes ?? [])
        .map(n => n.env_tag)
        .filter((t): t is string => !!t);
    return Array.from(new Set(tags)).sort();
}, [nodes]);

const filteredNodes = (nodes ?? []).filter(n =>
    envFilter === 'ALL' || n.env_tag === envFilter
);
```

Dropdown uses `<Select>` (already imported in History.tsx, same pattern). "All" is always the first option.

**Badge placement:** In `NodeCard`, inside the `<CardHeader>` alongside hostname, add a badge for `node.env_tag`. The badge must only render when `node.env_tag` is truthy. Colour mapping:
- DEV → blue-500/10 text-blue-500 border-blue-500/20
- TEST → amber-500/10 text-amber-500 border-amber-500/20
- PROD → rose-500/10 text-rose-500 border-rose-500/20
- custom → zinc-800 text-zinc-300 border-zinc-700

Note: The existing `getEnvBadgeColor()` function in Nodes.tsx handles `env:prod`, `env:staging`, `env:test` prefixed *tags* (the old tag format). The new `env_tag` field uses plain uppercase strings (DEV, TEST, PROD). A separate helper function is needed — do not reuse `getEnvBadgeColor()`.

### Pattern 7: History.tsx — Job Definition Selector

**What:** Add a fourth filter above the history table: a job definition dropdown that populates from `GET /jobs/definitions`.

**Implementation:** Use the same `useQuery` pattern already in the file. Add `const [definitionId, setDefinitionId] = useState('')` state. When set, append `&scheduled_job_id={definitionId}` to the query URL. The `definitions` query runs on mount (independent of the history query).

**Grid layout:** The existing filter bar uses `grid-cols-1 md:grid-cols-3`. Extend to `md:grid-cols-4` when adding the definition selector.

### Anti-Patterns to Avoid

- **Fetching executions for every definition at once:** Load history only for the currently selected definition, on demand, not eagerly for all definitions.
- **Reusing `getEnvBadgeColor()` for env_tag:** That function handles the old `env:prod` tag format. The new `env_tag` field is plain uppercase (PROD, DEV). Build a separate `getEnvTagBadgeClass(tag: string)` helper.
- **Building a new log component:** Extend `ExecutionLogModal.tsx`. All the terminal rendering is already correct; only the header and tab placement need changing.
- **Moving tabs without preserving scroll:** The log area's `useEffect` scroll-to-bottom must still fire when switching between attempts — keep the `selected` dependency in the scroll effect.
- **Constructing history panel as a modal:** The history panel is an inline section below the definitions table, not a drawer or dialog. The ExecutionLogModal opens on top when a row is clicked.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Attempt tab UI | Custom tab component | shadcn/ui `Tabs` already imported in project, OR simple `<Button variant>` row (existing pattern at modal bottom) | Consistency with rest of modal chrome |
| Env badge colours | Colour logic per-component | Single `getEnvTagBadgeClass()` helper at top of Nodes.tsx | Re-used by NodeCard and any future list view |
| History pagination | Custom pagination component | Existing page/prev/next pattern from History.tsx | Already tested, consistent UX |
| Select dropdown | Native `<select>` | shadcn `<Select>` (already in History.tsx and JobDefinitions) | Consistent dark-theme styling |

---

## Common Pitfalls

### Pitfall 1: attestation_verified absent from API response
**What goes wrong:** ExecutionLogModal renders attestation badge as always "NO ATTESTATION" even for verified runs.
**Why it happens:** `ExecutionRecordResponse` model in models.py does not include `attestation_verified`. The DB column exists but the handler omits it.
**How to avoid:** Add the field to the Pydantic model and both handler construction blocks before writing any frontend attestation display code.
**Warning signs:** Attestation badge always shows null/missing state in all runs.

### Pitfall 2: No job_definition_id path to execution history
**What goes wrong:** The definition history panel cannot query executions for a definition ID directly.
**Why it happens:** `ExecutionRecord.job_guid` links to `Job.guid`, not to `ScheduledJob.id`. The frontend cannot resolve this join.
**How to avoid:** Add `scheduled_job_id` filter to `GET /api/executions` via subquery through the `jobs` table.
**Warning signs:** History panel is always empty regardless of which definition is selected.

### Pitfall 3: Attempt tab order reversal
**What goes wrong:** Attempt tabs show newest attempt first (the current modal behaviour), but CONTEXT.md requires oldest-first with "(final)" on the last.
**Why it happens:** Current code does `executions.map((ex, i) => Attempt {executions.length - i})` with no sort guarantee.
**How to avoid:** Sort attempts by `attempt_number` ascending before rendering tabs. The final tab is the one with the highest `attempt_number`.

### Pitfall 4: env_tag vs env: tag format collision
**What goes wrong:** Badge rendering logic for the new `env_tag` field accidentally picks up the old `env:prod` tag-format colour function, producing wrong colours for plain "PROD" strings.
**Why it happens:** Nodes.tsx already has `getEnvBadgeColor()` which expects `env:prod` prefix. The new `env_tag` field stores plain uppercase (PROD, DEV, TEST).
**How to avoid:** Write `getEnvTagBadgeClass(tag: string)` as a separate function that switches on the plain string.

### Pitfall 5: History panel re-fetches on every keystroke elsewhere
**What goes wrong:** Using `useEffect` with no query library causes the definition history to re-fetch whenever unrelated state changes in `JobDefinitions.tsx`.
**Why it happens:** `JobDefinitions.tsx` currently uses `useEffect` + `authenticatedFetch` (not react-query). Adding a second fetch in the same component follows the same pattern — fetch fires on any state change if dependencies are not tight.
**How to avoid:** Either scope the history panel as a child component that owns its own data fetch (recommended — keeps JobDefinitions clean), or use `useQuery` from `@tanstack/react-query` for the history fetch with `queryKey: ['definition-history', selectedDefId]` so it only refetches when `selectedDefId` changes.

### Pitfall 6: Nodes filter dropdown renders before data loads
**What goes wrong:** The env filter dropdown shows "All" but never populates with env tag options because `nodes` is undefined during the initial query.
**Why it happens:** `useQuery` returns `data: undefined` until the first successful fetch. A `useMemo` on `nodes` without a null check crashes or returns an empty array.
**How to avoid:** Use `(nodes ?? [])` in the `useMemo` — already the pattern used for the existing `nodes?.length` guard in the Nodes component.

---

## Code Examples

### Adding attestation_verified to ExecutionRecordResponse (models.py)
```python
# In class ExecutionRecordResponse (currently ends at line ~639):
class ExecutionRecordResponse(BaseModel):
    id: int
    job_guid: str
    node_id: Optional[str] = None
    status: str
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_log: List[Dict[str, str]] = []
    truncated: bool = False
    duration_seconds: Optional[float] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    script_hash: Optional[str] = None
    hash_mismatch: Optional[bool] = None
    attempt_number: Optional[int] = None
    job_run_id: Optional[str] = None
    attestation_verified: Optional[str] = None  # ADD THIS
```

### Extending GET /api/executions with scheduled_job_id and job_run_id filters (main.py)
```python
@app.get("/api/executions", response_model=List[ExecutionRecordResponse], tags=["Execution Records"])
async def list_executions(
    skip: int = 0,
    limit: int = 50,
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    job_guid: Optional[str] = None,
    scheduled_job_id: Optional[str] = None,   # NEW
    job_run_id: Optional[str] = None,          # NEW
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("history:read"))
):
    query = select(ExecutionRecord)
    if node_id:
        query = query.where(ExecutionRecord.node_id == node_id)
    if status:
        query = query.where(ExecutionRecord.status == status)
    if job_guid:
        query = query.where(ExecutionRecord.job_guid == job_guid)
    if scheduled_job_id:
        subq = select(Job.guid).where(Job.scheduled_job_id == scheduled_job_id)
        query = query.where(ExecutionRecord.job_guid.in_(subq))
    if job_run_id:
        query = query.where(ExecutionRecord.job_run_id == job_run_id)
    # ... rest unchanged
```

### Env tag badge helper (new function in Nodes.tsx)
```typescript
const getEnvTagBadgeClass = (tag: string): string => {
    switch (tag.toUpperCase()) {
        case 'PROD':
            return 'bg-rose-500/10 text-rose-500 border-rose-500/20 font-bold';
        case 'TEST':
            return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
        case 'DEV':
            return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
        default:
            return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    }
};
```

### Env tag filter dropdown (Nodes.tsx — Nodes component)
```typescript
const uniqueEnvTags = useMemo(() => {
    const tags = (nodes ?? [])
        .map(n => n.env_tag)
        .filter((t): t is string => !!t);
    return Array.from(new Set(tags)).sort();
}, [nodes]);

const [envFilter, setEnvFilter] = useState<string>('ALL');

const displayNodes = (nodes ?? []).filter(n =>
    envFilter === 'ALL' || n.env_tag === envFilter
);
```

### Retry badge in definition history panel row
```typescript
// badge shows only when max_retries > 1 AND attemptCount > 1
const showRetryBadge = (ex.max_retries ?? 0) > 1 && (ex.attempt_number ?? 1) > 1;
const isRetrying = ex.status === 'RETRYING';
const isFailedExhausted = ex.status === 'FAILED' && ex.attempt_number === ex.max_retries + 1;

{showRetryBadge && (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
        isRetrying
            ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
            : isFailedExhausted
                ? 'bg-red-500/10 text-red-500 border-red-500/20'
                : 'bg-zinc-800 text-zinc-400 border-zinc-700'
    }`}>
        {isRetrying
            ? `Attempt ${ex.attempt_number} of ${ex.max_retries + 1}`
            : `Failed ${ex.attempt_number}/${ex.max_retries + 1}`}
    </span>
)}
```

### Attestation badge in ExecutionLogModal header
```typescript
const getAttestationBadge = (verified: string | null | undefined) => {
    if (!verified) return null;
    const map: Record<string, { cls: string; label: string }> = {
        verified: { cls: 'bg-green-500/10 text-green-500 border-green-500/20', label: 'VERIFIED' },
        failed:   { cls: 'bg-red-500/10 text-red-500 border-red-500/20',   label: 'ATTEST FAILED' },
        missing:  { cls: 'bg-zinc-800 text-zinc-400 border-zinc-700',       label: 'NO ATTESTATION' },
    };
    const entry = map[verified];
    if (!entry) return null;
    return (
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${entry.cls}`}>
            {entry.label}
        </span>
    );
};
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Per-attempt flat rows in history | Grouped by job_run_id (one row per logical run) | CONTEXT.md decision |
| Attempt tabs at bottom of modal | Attempt tabs at top of modal, in header area | CONTEXT.md decision |
| env: prefixed tags for environment | First-class `env_tag` column (plain uppercase) | Phase 31 result |
| No attestation in history list | attestation_verified badge in modal header | Phase 30 data, Phase 32 display |

---

## Open Questions

1. **How does the definition history panel group by job_run_id when job_run_id may be null for older jobs?**
   - What we know: `job_run_id` is nullable (added Phase 29, existing rows may be null).
   - What's unclear: Whether pre-Phase-29 execution records should appear in history at all.
   - Recommendation: Show them as individual ungrouped rows (no retry badge) — they predate the retry system. The grouping code checks `job_run_id != null` before attempting to group.

2. **Does the History.tsx definition filter need to show all definitions or only active ones?**
   - What we know: `GET /jobs/definitions` returns all definitions regardless of status.
   - What's unclear: Whether DRAFT/DEPRECATED definitions should appear in the dropdown.
   - Recommendation: Show all definitions (ACTIVE, DRAFT, DEPRECATED) in the selector. Operators may need to inspect history of deprecated definitions.

3. **Should the definition history panel show individual attempt rows or one row per job_run_id?**
   - CONTEXT.md says "one row per job_run_id" — confirmed locked. The backend query returns all execution records; the frontend groups them client-side before rendering rows.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (vitest.config.ts) + @testing-library/react |
| Config file | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer/dashboard && npx vitest run --reporter=verbose` |
| Full suite command | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTPUT-03 | ExecutionLogModal renders output_log lines with [OUT]/[ERR] labels | unit | `npx vitest run src/components/__tests__/ExecutionLogModal.test.tsx` | Wave 0 |
| OUTPUT-03 | Modal header shows attestation badge when attestation_verified = 'verified' | unit | same file | Wave 0 |
| OUTPUT-04 | Definition history panel renders execution rows when selectedDefId is set | unit | `npx vitest run src/views/__tests__/JobDefinitions.test.tsx` | Exists (extend) |
| OUTPUT-04 | History.tsx renders definition selector dropdown | unit | `npx vitest run src/views/__tests__/History.test.tsx` | Wave 0 |
| RETRY-03 | Retry badge renders "Attempt N of M" when max_retries > 1 and attempt_number > 1 | unit | `npx vitest run src/components/__tests__/ExecutionLogModal.test.tsx` | Wave 0 |
| RETRY-03 | Single-attempt completed runs show no retry badge | unit | same file | Wave 0 |
| ENVTAG-03 | NodeCard renders env_tag badge when env_tag is set | unit | `npx vitest run src/views/__tests__/Nodes.test.tsx` | Wave 0 |
| ENVTAG-03 | Env filter dropdown filters node list to matching env_tag | unit | same file | Wave 0 |
| ENVTAG-03 | Nodes with no env_tag show no badge | unit | same file | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer/dashboard && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd puppeteer/dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/dashboard/src/components/__tests__/ExecutionLogModal.test.tsx` — covers OUTPUT-03, OUTPUT-03 attestation, RETRY-03 badge
- [ ] `puppeteer/dashboard/src/views/__tests__/History.test.tsx` — covers OUTPUT-04 definition selector
- [ ] `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` — covers ENVTAG-03 badge and filter
- [ ] Existing `JobDefinitions.test.tsx` — extend with definition selection + history panel tests for OUTPUT-04

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `puppeteer/agent_service/db.py` — `ExecutionRecord` model confirming `attestation_verified` column exists
- Direct source read: `puppeteer/agent_service/models.py` — `ExecutionRecordResponse` confirming `attestation_verified` absent from response model
- Direct source read: `puppeteer/agent_service/main.py` lines 433-487 — `GET /api/executions` handler, no `scheduled_job_id` or `job_run_id` filter params
- Direct source read: `puppeteer/dashboard/src/components/ExecutionLogModal.tsx` — current modal structure, attempt tab rendering
- Direct source read: `puppeteer/dashboard/src/views/Nodes.tsx` — `Node` interface missing `env_tag`; `getEnvBadgeColor()` uses old `env:` prefix format
- Direct source read: `puppeteer/dashboard/src/views/JobDefinitions.tsx` — current structure, data loading pattern
- Direct source read: `puppeteer/dashboard/src/views/History.tsx` — pagination pattern, filter bar, query pattern

### Secondary (MEDIUM confidence)
- `puppeteer/agent_service/models.py` line 187 — `env_tag: Optional[str] = None` confirmed on `NodeResponse` (Phase 31 output)
- `puppeteer/agent_service/db.py` line 32 — `Job.scheduled_job_id` FK to `ScheduledJob.id` confirmed

---

## Metadata

**Confidence breakdown:**
- Backend gaps: HIGH — confirmed by direct source inspection of models.py and main.py
- Frontend patterns: HIGH — confirmed by reading all affected component files
- Test gaps: HIGH — confirmed by listing existing test files

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable frontend codebase — changes only if Phase 29/30/31 APIs are modified)

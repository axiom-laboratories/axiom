# Phase 51: Job Detail, Resubmit and Bulk Ops - Research

**Researched:** 2026-03-23
**Domain:** React/TypeScript frontend (Jobs view), FastAPI backend (job endpoints)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Detail drawer content (JOB-04)**
- stdout/stderr inline in the drawer — no separate modal. The existing "View Output" button that opens ExecutionLogModal is removed from the drawer; output is embedded directly. ExecutionLogModal may be retained for the History view.
- Content hierarchy: Output section first, then metadata (status/node/timing), then payload in a collapsible section at the bottom.
- Node health snapshot: show CPU/RAM from NodeStats at the time of execution — not current node health.
- SECURITY_REJECTED reason: one-liner actionable format — "Script signature did not match registered key — re-sign and resubmit." Surfaced as an amber callout in the drawer when security_rejected: true.

**Resubmit UX (JOB-05 + JOB-06)**
- Two distinct buttons in the drawer, shown only when job is FAILED with retries exhausted:
  - "Resubmit" — one-click, same payload/signature, new GUID
  - "Edit & Resubmit" — opens GuidedDispatchCard pre-populated
- One-click resubmit confirmation: inline in the drawer — button transforms to "Confirm resubmit? [Cancel] [Confirm]". No modal.
- After one-click resubmit: close drawer, scroll the new job into view in the list with a brief highlight ring.
- Originating GUID traceability: stored on the new job; surfaced in the new job's detail drawer only ("Resubmitted from: [original GUID]"). Not shown as a badge in the job list.

**Edit-then-resubmit mechanics (JOB-06)**
- Location: close the detail drawer, scroll to the GuidedDispatchCard at the top of the Jobs view, pre-populate it with the failed job's values.
- Fields carried over: name, runtime, script content, targeting (node + target tags + capability chips). Signature fields are blank with an amber inline warning "Re-signing required — script payload has changed or job was resubmitted."
- After successful dispatch: form resets to blank guided mode (same as a normal dispatch). Toast: "Job resubmitted — [new GUID]".

**Bulk selection UI (BULK-01–04)**
- Checkboxes: always visible as the first column in the job table. Clicking any checkbox immediately activates selection mode.
- Select-all: checkbox in the table header selects all currently loaded jobs (respects current filter state).
- Floating action bar: appears at the top of the table, replacing the filter bar when selection mode is active. Shows "[N] selected" count + applicable bulk action buttons + "Clear selection" × button to exit selection mode.
- Context-sensitive actions — only valid actions are shown (fully hidden if not applicable):
  - Cancel: shown if ≥1 selected job is PENDING or RUNNING
  - Resubmit: shown if ≥1 selected job is FAILED with retries exhausted
  - Delete: shown if ≥1 selected job is in terminal state (COMPLETED/FAILED/CANCELLED)
- Confirmation dialog: count + skipped count — e.g. "Cancel 3 jobs? (2 PENDING, 1 RUNNING — 4 selected jobs are already terminal and will be skipped)". Standard Radix Dialog.

### Claude's Discretion
- Exact inline confirmation animation when the Resubmit button transforms (fade, replace, etc.)
- Whether the highlight ring on the newly resubmitted job in the list uses a CSS transition or a brief timeout
- Exact layout of the node health snapshot section (table vs grid vs prose)
- Select-all behaviour for partially-loaded lists (cursor pagination): select visible rows only or offer "select all matching" (like Gmail) — Claude decides based on implementation complexity

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-04 | Operator can view job details (stdout/stderr, node health, retry state, SECURITY_REJECTED plain-English reason) in a drawer | Inline output rendering from ExecutionLogModal logic; NodeStats timestamp query; security_rejected field in ResultReport model |
| JOB-05 | Operator can resubmit an exhausted-retry failed job with one click — new GUID, same payload and signature, originating_guid stored | New `POST /jobs/{guid}/resubmit` endpoint; originating_guid column on Job model; db migration needed |
| JOB-06 | Operator can edit and resubmit a failed job — guided form pre-populated with failed job's payload, signing state cleared | GuidedDispatchCard `initialValues` prop; scroll-to-form pattern; amber warning reuse from Phase 50 |
| BULK-01 | Operator can multi-select jobs using checkboxes; a floating action bar appears showing available bulk actions | useState(Set<string>) selection state; conditional render of bulk bar vs filter bar |
| BULK-02 | Operator can bulk cancel selected PENDING/RUNNING jobs with a count confirmation | New `POST /jobs/bulk-cancel` endpoint; Radix Dialog confirmation |
| BULK-03 | Operator can bulk resubmit selected FAILED (retries-exhausted) jobs; confirmation shows skipped count | New `POST /jobs/bulk-resubmit` endpoint; per-item originating_guid linkage |
| BULK-04 | Operator can bulk delete selected terminal-state jobs (COMPLETED/FAILED/CANCELLED) with a count confirmation | New `DELETE /jobs/bulk` endpoint; terminal state validation server-side |
</phase_requirements>

---

## Summary

Phase 51 builds entirely on top of the existing Jobs view (`Jobs.tsx`). There are no new views or routes — every feature lives in the existing `JobDetailPanel` component and the job table. The work divides naturally into three concerns: (1) enriching the detail drawer with inline execution output and node health, (2) adding resubmit actions (one-click and edit-then-resubmit), and (3) adding multi-select with bulk actions.

The backend currently has individual `cancel`, `retry` (reset-to-PENDING), and `executions` endpoints but has no `resubmit` (clone job), no `delete`, and no bulk endpoints. Three new bulk endpoints and one new resubmit endpoint are needed. The Job DB model also needs two new nullable columns: `originating_guid` and (for bulk delete) the existing terminal-state check pattern can be reused. No `create_all` auto-migration will apply to an existing DB — a migration SQL file is required.

The frontend has well-established patterns throughout: Radix Dialog for confirmations, `sonner` toast notifications, inline button state transforms (used in Foundry), amber callout styling (Phases 48 and 50), and the Sheet drawer. The output rendering logic in `ExecutionLogModal` can be extracted and rendered inline in the drawer without a dialog wrapper.

**Primary recommendation:** Deliver in four backend-first waves: (W0) test stubs + migration SQL; (W1) backend endpoints (resubmit + bulk); (W2) drawer enrichment (inline output + node health + resubmit buttons); (W3) bulk selection UI.

---

## Standard Stack

### Core (already in project — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | Component model | Project standard |
| TypeScript | 5.x | Type safety | Project standard |
| @radix-ui/react-dialog | existing | Confirmation dialogs | Already used in GuidedDispatchCard (ADV mode gate) |
| @radix-ui/react-checkbox | check package.json | Checkbox primitive | Needed for bulk select; likely already present via shadcn |
| sonner | existing | Toast notifications | `toast.success`, `toast.error` used in Jobs.tsx |
| lucide-react | existing | Icons | All icons used in Jobs.tsx |
| FastAPI | existing | Backend routes | Project standard |
| SQLAlchemy (async) | existing | ORM queries | Project standard |

### No New Dependencies Required
All UI primitives needed (Dialog, Checkbox, Sheet, Button, Badge, Table) are already in the project's shadcn/radix installation. Checkbox may need a `ui/checkbox.tsx` wrapper if it doesn't exist yet — check before assuming.

**Verify checkbox wrapper exists:**
```bash
ls puppeteer/dashboard/src/components/ui/checkbox.tsx
```

---

## Architecture Patterns

### Recommended Project Structure (changes only)
```
puppeteer/agent_service/
├── db.py                    # Add: originating_guid column to Job
├── models.py                # Add: originating_guid to JobCreate + JobResponse; BulkActionRequest
├── main.py                  # Add: POST /jobs/{guid}/resubmit, POST /jobs/bulk-cancel,
│                            #      POST /jobs/bulk-resubmit, DELETE /jobs/bulk
├── migration_v14.sql        # ADD COLUMN originating_guid

puppeteer/dashboard/src/
├── views/Jobs.tsx           # Add: checkboxes, selection state, bulk bar, resubmit handlers,
│                            #      GuidedDispatchCard initialValues wire-up
├── components/
│   ├── JobDetailPanel.tsx   # Extract from Jobs.tsx OR enrich inline:
│   │                        #   inline output, node health, resubmit buttons, originating_guid
│   └── GuidedDispatchCard.tsx  # Add: initialValues prop + amber "re-signing required" warning
```

### Pattern 1: Inline Output Rendering (extracted from ExecutionLogModal)
**What:** The log-line rendering inside ExecutionLogModal is pure presentational logic. Copy the output line loop into the drawer — no fetch logic needed since the drawer already has the job's execution records fetched via `GET /jobs/{guid}/executions`.
**When to use:** Inside the enriched JobDetailPanel, below the SECURITY_REJECTED callout (if present).

Key lines to reuse from `ExecutionLogModal.tsx` (lines 196-216):
```tsx
// Source: puppeteer/dashboard/src/components/ExecutionLogModal.tsx:196-216
{lines.map((l, i) => (
    <div key={i} className="flex gap-4 group hover:bg-zinc-900/50 ...">
        <span className="text-zinc-700 text-[10px]...">
            {new Date(l.t).toLocaleTimeString(...)}
        </span>
        <span className={`... ${l.stream === 'stderr' ? 'text-amber-500/80' : 'text-zinc-600'}`}>
            [{l.stream.slice(0, 3).toUpperCase()}]
        </span>
        <span className={`... ${l.stream === 'stderr' ? 'text-amber-200' : 'text-zinc-300'}`}>
            {l.line}
        </span>
    </div>
))}
```

### Pattern 2: Inline Confirm Transform
**What:** Button state cycles through `idle → confirming → idle`. When in `confirming` state, button is replaced with "Confirm? [Cancel] [Confirm]" row.
**When to use:** The one-click Resubmit button in the drawer.
**Example (established in Foundry view):**
```tsx
// Source: project convention — same pattern as Foundry destructive confirm
const [resubmitConfirming, setResubmitConfirming] = useState(false);

{resubmitConfirming ? (
    <div className="flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => setResubmitConfirming(false)}>Cancel</Button>
        <Button size="sm" variant="default" onClick={handleConfirmResubmit}>Confirm</Button>
    </div>
) : (
    <Button onClick={() => setResubmitConfirming(true)}>Resubmit</Button>
)}
```

### Pattern 3: Bulk Selection with Set<string>
**What:** `selectedJobGuids: Set<string>` in Jobs component state. Checkbox in each row toggles membership. Header checkbox sets all-or-none based on current loaded rows.
**When to use:** The jobs table — first column, always visible.
```tsx
const [selectedGuids, setSelectedGuids] = useState<Set<string>>(new Set());
const selectionActive = selectedGuids.size > 0;

// Toggle one
const toggleSelect = (guid: string) =>
    setSelectedGuids(prev => {
        const next = new Set(prev);
        next.has(guid) ? next.delete(guid) : next.add(guid);
        return next;
    });

// Select all visible
const allSelected = jobs.length > 0 && jobs.every(j => selectedGuids.has(j.guid));
const toggleAll = () =>
    setSelectedGuids(allSelected ? new Set() : new Set(jobs.map(j => j.guid)));
```

### Pattern 4: Bulk Action Bar (replaces filter bar)
**What:** When `selectionActive`, the filter bar row is replaced by the bulk action bar. This avoids z-index issues and keeps layout stable.
**Example:**
```tsx
{selectionActive ? (
    <BulkActionBar
        count={selectedGuids.size}
        selectedJobs={jobs.filter(j => selectedGuids.has(j.guid))}
        onClearSelection={() => setSelectedGuids(new Set())}
        onBulkCancel={handleBulkCancel}
        onBulkResubmit={handleBulkResubmit}
        onBulkDelete={handleBulkDelete}
    />
) : (
    <FilterBar ... />
)}
```

### Pattern 5: NodeStats at Execution Time Query
**What:** Query `NodeStats` for records on the executing node nearest `job.started_at`.
**Backend query approach:**
```python
# Source: db.py NodeStats schema — recorded_at, node_id, cpu, ram
# No existing "at timestamp" endpoint — needs to be embedded in GET /jobs/{guid}
# or as a separate GET /nodes/{node_id}/stats?near=<iso_timestamp>
# Simplest: embed in the enriched job detail response (GET /jobs/{guid})
result = await db.execute(
    select(NodeStats)
    .where(NodeStats.node_id == job.node_id)
    .where(NodeStats.recorded_at <= job.started_at)
    .order_by(NodeStats.recorded_at.desc())
    .limit(1)
)
node_stat = result.scalar_one_or_none()
```
**Decision required for planning:** The CONTEXT.md says to show node health at time of execution. The simplest implementation adds a `node_health_at_execution` field to the existing `/jobs/{guid}/executions` response or adds a new `GET /jobs/{guid}` single-job endpoint. Currently there is no `GET /jobs/{guid}` endpoint — only `GET /jobs` (list) and `GET /jobs/{guid}/executions`. The drawer fetches execution records on open; the node health query can be added to the executions list response as a top-level field alongside the records.

### Pattern 6: Resubmit Endpoint (clone job)
**What:** `POST /jobs/{guid}/resubmit` creates a new job with the same payload, task_type, runtime, signature fields, and targeting — but a fresh GUID, `originating_guid` set to the original, `retry_count=0`, and `status=PENDING`.
**Constraint:** Only allowed when `job.status == "FAILED"` AND `job.retry_count >= job.max_retries` (retries exhausted, i.e. no more automatic retries scheduled). DEAD_LETTER status also qualifies (retries_exhausted by definition).
```python
# Source: based on existing create_job + cancel patterns in main.py
@app.post("/jobs/{guid}/resubmit", response_model=JobResponse, tags=["Jobs"])
async def resubmit_job(guid: str, current_user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "DEAD_LETTER"):
        raise HTTPException(status_code=409, detail="Only FAILED or DEAD_LETTER jobs can be resubmitted")
    new_guid = str(uuid.uuid4())
    new_job = Job(
        guid=new_guid,
        task_type=job.task_type,
        payload=job.payload,
        status="PENDING",
        target_tags=job.target_tags,
        capability_requirements=job.capability_requirements,
        max_retries=job.max_retries,
        backoff_multiplier=job.backoff_multiplier,
        timeout_minutes=job.timeout_minutes,
        runtime=job.runtime,
        name=job.name,
        created_by=current_user.username,
        signature_hmac=job.signature_hmac,
        originating_guid=guid,   # NEW COLUMN
    )
    db.add(new_job)
    audit(db, current_user, "job:resubmit", new_guid)
    await db.commit()
    await ws_manager.broadcast("job:created", {"guid": new_guid, "status": "PENDING"})
    return {...}  # return new job as JobResponse
```

### Anti-Patterns to Avoid
- **Using the existing `/jobs/{guid}/retry` for resubmit**: That endpoint resets the *same* job's GUID in-place. Resubmit must create a NEW job with a new GUID (JOB-05 spec). They are different operations.
- **Querying ALL NodeStats to find execution-time snapshot**: Use `ORDER BY recorded_at DESC LIMIT 1 WHERE recorded_at <= job.started_at` scoped to the specific node_id — never a full-table scan.
- **Blocking row click when checkbox is clicked**: Use `e.stopPropagation()` on the checkbox cell's click handler to prevent the row-click detail drawer from opening.
- **Greying out inapplicable bulk actions**: CONTEXT.md says fully hidden, not greyed. Use conditional rendering, not `disabled`.
- **Sending individual cancel/resubmit/delete requests in a loop**: Use the bulk endpoints — one request per bulk action, not N requests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confirmation dialogs | Custom modal | `@radix-ui/react-dialog` (already imported in GuidedDispatchCard) | Accessibility, focus trap, keyboard escape |
| Checkbox component | HTML `<input type="checkbox">` | `ui/checkbox.tsx` (shadcn Radix wrapper) | Consistent dark-theme styling, accessible |
| Toast notifications | Custom alert div | `sonner` `toast.success/error` | Already used in Jobs.tsx |
| Amber callout warning | Custom styled div | Reuse Phase 48 DRAFT / Phase 50 stale-signature pattern | Consistent visual language |
| Scroll-to-element | Manual `window.scrollTo` calculation | `element.scrollIntoView({ behavior: 'smooth' })` via `useRef` | Simpler, handles dynamic layout |

---

## Common Pitfalls

### Pitfall 1: "Retries exhausted" detection is status-based, not count-based
**What goes wrong:** Checking `retry_count >= max_retries` to determine if resubmit should be shown — but the actual terminal state for "retries exhausted" in this codebase is `status === "DEAD_LETTER"`. A job with `max_retries=0` that fails goes straight to `FAILED` (not DEAD_LETTER). Both FAILED and DEAD_LETTER should show resubmit buttons.
**Why it happens:** The retry exhaustion logic in `job_service.py` (line 1109) sets status to `DEAD_LETTER` only when `max_retries > 0` and retries are exhausted. `max_retries=0` jobs go to `FAILED` directly.
**How to avoid:** Show resubmit buttons when `job.status === 'FAILED' || job.status === 'DEAD_LETTER'`. The existing `retryable` check in `JobDetailPanel` already uses exactly this condition (line 171): `const retryable = job.status === 'FAILED' || job.status === 'DEAD_LETTER'`. Resubmit buttons use the same condition but replace (not add to) the existing re-queue button.

### Pitfall 2: The existing "Retry" is reset-in-place; Resubmit must be clone-with-new-GUID
**What goes wrong:** Using `POST /jobs/{guid}/retry` thinking it's resubmit. That resets retry_count to 0 and changes status to PENDING on the SAME job GUID.
**Why it happens:** Naming ambiguity. CONTEXT.md is clear: resubmit = new GUID + originating_guid field.
**How to avoid:** Remove the "Re-queue Job" button from the drawer (it's shown for FAILED/DEAD_LETTER — now replaced by Resubmit/Edit&Resubmit). The `/retry` endpoint remains available for other use cases but is no longer surfaced in the detail drawer.

### Pitfall 3: originating_guid requires DB migration for existing deployments
**What goes wrong:** Adding `originating_guid` to the Job ORM model — `create_all` will NOT alter the existing table on deployed databases. The column only appears on fresh DB creates.
**Why it happens:** Project uses `create_all` not Alembic (documented in CLAUDE.md and MEMORY.md).
**How to avoid:** Create `migration_v14.sql`:
```sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR;
```
For SQLite (local dev): `ALTER TABLE jobs ADD COLUMN originating_guid TEXT;` (SQLite has no `IF NOT EXISTS` on ALTER — handle gracefully or document as dev-only risk).

### Pitfall 4: Checkbox column disrupts row-click-to-open-drawer
**What goes wrong:** Clicking the checkbox opens the detail drawer because `onClick` on the row fires.
**Why it happens:** The entire `<TableRow>` has `onClick={() => openDetail(job)}`.
**How to avoid:** Wrap the checkbox cell in `<TableCell onClick={e => e.stopPropagation()}>`. Same pattern already used for the "Detail" button cell (Jobs.tsx line 950): `<TableCell ... onClick={e => { e.stopPropagation(); openDetail(job); }}>`.

### Pitfall 5: Bulk action bar replaces filter bar — selection state must survive filter changes
**What goes wrong:** Clearing filters (or applying new ones) resets `jobs` array via `fetchJobs({ reset: true })` but `selectedGuids` might reference GUIDs no longer in the loaded set. The bulk action bar would show a stale count.
**Why it happens:** Selection state (`Set<string>`) is independent of the jobs array.
**How to avoid:** On `fetchJobs({ reset: true })`, intersect `selectedGuids` with the new jobs set:
```typescript
setSelectedGuids(prev => new Set([...prev].filter(g => newItems.some(j => j.guid === g))));
```
Or simpler: clear selection on any filter change (less ideal UX but safe). Given cursor pagination complexity, clearing on filter change is the pragmatic choice — operator can re-select after filtering.

### Pitfall 6: NodeStats temporal query may return null
**What goes wrong:** `job.started_at` is null (job never started — PENDING, CANCELLED before assignment) and the query crashes or returns confusing results.
**Why it happens:** `started_at` is nullable on the Job model.
**How to avoid:** Only show the node health snapshot section when `job.started_at` and `job.node_id` are both non-null. Return `null` for `node_health_at_execution` when they are absent — frontend omits the section.

### Pitfall 7: Bulk delete must be terminal-state gated server-side
**What goes wrong:** Client sends DELETE for a RUNNING job, leaving it orphaned (node still working, server has no record to complete against).
**Why it happens:** Pure client-side filtering may be bypassed or have race conditions.
**How to avoid:** Server validates each GUID is in terminal state (`COMPLETED`, `FAILED`, `DEAD_LETTER`, `CANCELLED`, `SECURITY_REJECTED`) before deleting. Return a partial success response listing which GUIDs were skipped.

---

## Code Examples

### New DB column — originating_guid
```python
# Source: puppeteer/agent_service/db.py — add after 'created_by' column
originating_guid: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JOB-05: resubmit traceability
```

### New model field — originating_guid on JobResponse
```python
# Source: puppeteer/agent_service/models.py — add to JobResponse
originating_guid: Optional[str] = None   # JOB-05: set when this job was resubmitted from another
```

### Bulk request body models
```python
# Source: puppeteer/agent_service/models.py — new models
class BulkJobActionRequest(BaseModel):
    guids: List[str]

class BulkActionResponse(BaseModel):
    processed: int
    skipped: int
    skipped_guids: List[str]
```

### GuidedDispatchCard initialValues prop pattern
```typescript
// Source: puppeteer/dashboard/src/components/GuidedDispatchCard.tsx
interface GuidedDispatchCardProps {
    nodes: NodeItem[];
    onJobCreated: () => void;
    initialValues?: Partial<GuidedFormState>;  // JOB-06: pre-populate for edit-then-resubmit
}

// In component body, use useEffect to apply initialValues when they change:
useEffect(() => {
    if (!initialValues) return;
    setForm(prev => ({
        ...prev,
        ...initialValues,
        signatureId: '',   // always clear
        signature: '',     // always clear
        signatureCleared: true,
    }));
}, [initialValues]);
```

### Amber "re-signing required" warning (reusing Phase 48/50 pattern)
```tsx
// Source: established amber warning pattern in GuidedDispatchCard (Phase 50) and JobDefinitionModal (Phase 48)
{form.signatureCleared && (
    <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        Re-signing required — script payload has changed or job was resubmitted.
    </div>
)}
```

### Node health snapshot fetch (embedded in executions response or single-job endpoint)
```python
# Source: db.py NodeStats schema
# Add to GET /jobs/{guid}/executions handler — returns node_health alongside records
node_health = None
if job and job.node_id and job.started_at:
    nh_result = await db.execute(
        select(NodeStats)
        .where(NodeStats.node_id == job.node_id)
        .where(NodeStats.recorded_at <= job.started_at)
        .order_by(desc(NodeStats.recorded_at))
        .limit(1)
    )
    nh = nh_result.scalar_one_or_none()
    if nh:
        node_health = {"cpu": nh.cpu, "ram": nh.ram, "recorded_at": nh.recorded_at.isoformat()}
```

### Highlight ring for newly resubmitted job
```typescript
// Source: Claude's discretion — use brief state + CSS transition
const [highlightGuid, setHighlightGuid] = useState<string | null>(null);

// After resubmit succeeds:
setHighlightGuid(newGuid);
setTimeout(() => setHighlightGuid(null), 2500);

// In table row:
className={`... ${highlightGuid === job.guid ? 'ring-1 ring-primary/60 bg-primary/5' : ''} transition-all duration-500`}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "View Output" button → ExecutionLogModal dialog | Inline output in drawer (Phase 51) | Phase 51 | ExecutionLogModal retained for History view only |
| Re-queue button (resets same GUID) | Resubmit button (clones to new GUID) | Phase 51 | Re-queue button removed from drawer |
| No bulk operations | Checkbox select + bulk action bar | Phase 51 | Operators can operate on sets |

---

## Open Questions

1. **Does `ui/checkbox.tsx` exist in the shadcn component library?**
   - What we know: `ui/button.tsx`, `ui/badge.tsx`, `ui/table.tsx`, `ui/dialog.tsx` etc. all exist
   - What's unclear: Whether shadcn Checkbox was added during project setup
   - Recommendation: Wave 0 task checks `ls puppeteer/dashboard/src/components/ui/checkbox.tsx`; if missing, create it following the shadcn pattern (wraps `@radix-ui/react-checkbox`)

2. **Single-job GET endpoint or enrich executions response for node health?**
   - What we know: No `GET /jobs/{guid}` endpoint currently exists
   - What's unclear: Whether to add a single-job endpoint (cleaner) or add `node_health` as a sibling field in the executions list response
   - Recommendation: Add `node_health_at_execution` as a top-level field in the `/jobs/{guid}/executions` response alongside the records array. Avoids adding a new endpoint, and the drawer already fetches executions on open.

3. **Select-all with cursor pagination: visible rows only or "select all matching"?**
   - What we know: Cursor pagination loads up to N rows; total may be 12,000+
   - What's unclear: Whether "select all matching" adds too much complexity
   - Recommendation (Claude's discretion): Select visible rows only. The "select all matching" pattern (Gmail-style) requires a separate backend count query and a second-pass fetch of all GUIDs — significant complexity for an edge case. Document that select-all operates on currently loaded rows only.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + anyio (existing, `conftest.py` at `puppeteer/`) |
| Frontend framework | Vitest + React Testing Library (existing, `vitest.config.ts`) |
| Backend quick run | `cd puppeteer && pytest agent_service/tests/test_job_service.py -x` |
| Frontend quick run | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` |
| Full suite | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-05 | `POST /jobs/{guid}/resubmit` creates new job with new GUID and originating_guid set | unit | `pytest agent_service/tests/test_job51_resubmit.py -x` | Wave 0 |
| JOB-05 | Resubmit rejected for non-FAILED/DEAD_LETTER status | unit | same | Wave 0 |
| JOB-06 | GuidedDispatchCard renders with initialValues pre-populated | unit | `npx vitest run src/views/__tests__/Jobs.test.tsx` | Extend existing |
| JOB-06 | GuidedDispatchCard signature fields cleared when initialValues provided | unit | same | Extend existing |
| BULK-02 | `POST /jobs/bulk-cancel` cancels PENDING/ASSIGNED jobs, skips terminal | unit | `pytest agent_service/tests/test_job51_bulk.py -x` | Wave 0 |
| BULK-03 | `POST /jobs/bulk-resubmit` creates N new jobs, links originating_guids | unit | same | Wave 0 |
| BULK-04 | `DELETE /jobs/bulk` deletes terminal jobs, returns skipped list | unit | same | Wave 0 |
| BULK-01 | Checkbox appears in first column; selecting activates bulk bar | unit | `npx vitest run src/components/__tests__/JobsBulkSelect.test.tsx` | Wave 0 |
| JOB-04 | Drawer renders inline output section (not "View Output" button) | unit | extend Jobs.test.tsx | Extend existing |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest agent_service/tests/test_job51_*.py -x` (backend) or `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Jobs.test.tsx` (frontend)
- **Per wave merge:** `cd puppeteer && pytest && cd dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/agent_service/tests/test_job51_resubmit.py` — covers JOB-05 backend (resubmit endpoint)
- [ ] `puppeteer/agent_service/tests/test_job51_bulk.py` — covers BULK-02, BULK-03, BULK-04 backend endpoints
- [ ] `puppeteer/migration_v14.sql` — `ALTER TABLE jobs ADD COLUMN originating_guid`
- [ ] `puppeteer/dashboard/src/components/ui/checkbox.tsx` — if not present (check first)
- [ ] Extend `Jobs.test.tsx` — inline output drawer, checkbox presence, initialValues on GuidedDispatchCard

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `puppeteer/agent_service/db.py` — Job model columns, NodeStats schema, ExecutionRecord schema
- Direct code read: `puppeteer/agent_service/models.py` — JobCreate, JobResponse, ResultReport fields
- Direct code read: `puppeteer/agent_service/main.py` — existing cancel, retry, executions endpoints
- Direct code read: `puppeteer/agent_service/services/job_service.py` — retry exhaustion logic, DEAD_LETTER assignment (lines 1095-1109)
- Direct code read: `puppeteer/dashboard/src/views/Jobs.tsx` — full component structure, existing state, filter bar pattern, JobDetailPanel
- Direct code read: `puppeteer/dashboard/src/components/ExecutionLogModal.tsx` — output rendering logic to extract
- Direct code read: `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` — GuidedFormState shape, INITIAL_FORM, props interface

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions (user-specified) — all UX decisions documented above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, verified by direct file reads
- Architecture: HIGH — all patterns verified against existing codebase code
- Pitfalls: HIGH — sourced from actual code inspection (retry logic, status flows, DB model)
- Test map: HIGH — existing test files confirmed present, gaps identified by absence

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable codebase — no fast-moving dependencies)

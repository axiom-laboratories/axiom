# Phase 88: Dispatch Diagnosis UI - Research

**Researched:** 2026-03-29
**Domain:** FastAPI bulk endpoint extension + React inline polling UI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Diagnosis text appears under the status badge in the same Status cell — PENDING/stuck-ASSIGNED rows become two-line; other rows remain single-line
- PENDING/stuck-ASSIGNED rows get an amber left border accent (`border-l-2 border-amber-500/60`) — no background fill
- Queue position appended inline to the message text: `"All nodes busy · 2nd in queue"` (middle dot separator, only shown when queue_position ≥ 2)
- Stuck ASSIGNED: badge stays `assigned`, diagnosis text appears below — badge text/colour does not change
- New batch endpoint: `POST /jobs/dispatch-diagnosis/bulk` — accepts list of GUIDs, returns all diagnoses in one call
- Poll fires only while the Jobs view is mounted (starts on mount, stops on unmount)
- Diagnosis data updates on timed poll only — no WebSocket-triggered re-fetch
- Manual refresh button in the Queue Monitor card header — triggers immediate batch fetch for all PENDING/stuck-ASSIGNED jobs in view
- Extend `get_dispatch_diagnosis` to also evaluate ASSIGNED jobs with stuck threshold: `started_at + (timeout_minutes * 1.2)`, fallback 30 minutes
- Return format unchanged: `{reason, message, queue_position}` — add new reason values: `"stuck_assigned"`, etc.
- Drawer keeps existing diagnosis callout — minor redundancy is acceptable
- Drawer auto-refreshes diagnosis while open for a PENDING/stuck-ASSIGNED job (same poll interval as the list)

### Claude's Discretion

- Exact poll interval (5s or 10s — pick based on WebSocket coexistence)
- Whether stuck-ASSIGNED detection runs fully server-side or partially client-side
- Exact wording of the stuck-ASSIGNED message
- Internal React state shape for the diagnosis cache (map of guid → diagnosis result)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope

</user_constraints>

<research_summary>
## Summary

Phase 88 is purely additive — no new libraries, no DB schema changes, no new concepts. The existing `get_dispatch_diagnosis` service method is extended to cover stuck-ASSIGNED jobs, a new bulk endpoint mirrors the existing bulk pattern (`/jobs/bulk-cancel`, `/jobs/bulk-resubmit`), and the React job list gets an in-row diagnosis display with a `setInterval` poll.

The key implementation decisions from research:

1. **Poll interval: 10 seconds.** The WebSocket already fires on `job:updated` and `node:heartbeat` events which cover real-time state. 10s polling for stale-stuck diagnosis avoids hammering the backend while still providing near-real-time feedback. The existing drawer uses WebSocket-triggered re-fetch for the single-job case — the list uses timed polling as a complement, not a replacement.

2. **Stuck-ASSIGNED detection is fully server-side.** The `get_dispatch_diagnosis` method already has all job fields (started_at, timeout_minutes). Adding a branch before the existing PENDING-only check keeps client code simple — the frontend just treats "stuck_assigned" like any other reason code.

3. **Diagnosis cache shape: `Record<string, DiagnosisResult>`** keyed by guid. React state is a simple object; updates are non-destructive (spread merge). Only PENDING and stuck-ASSIGNED jobs are in the cache — completed/failed rows never carry diagnosis state.

4. **Bulk endpoint shape:** `POST /jobs/dispatch-diagnosis/bulk` with body `{"guids": [...]}` returns `{"results": {"guid": {reason, message, queue_position}, ...}}`. Parallel to `BulkJobActionRequest`/`BulkActionResponse` existing pattern but with a map response (not processed/skipped counts).

**Primary recommendation:** Two-plan implementation — Plan 01 extends the backend service + adds bulk endpoint; Plan 02 wires the frontend poll + inline display.

</research_summary>

<standard_stack>
## Standard Stack

No new libraries needed. All implementation uses existing project stack:

### Core (already installed)
| Component | Version | Purpose | Already Used |
|-----------|---------|---------|--------------|
| FastAPI | 0.11x | Bulk endpoint route | `@app.post("/jobs/bulk-cancel")` |
| SQLAlchemy async | 2.x | DB queries in service | `job_service.py` |
| React + TypeScript | 18.x / 5.x | Inline row display + poll | `Jobs.tsx` |
| Lucide React | installed | `RefreshCw` icon for refresh button | already imported in Jobs.tsx |

### Existing Patterns to Reuse

| Pattern | Location | Phase 88 Use |
|---------|----------|-------------|
| `BulkJobActionRequest` | `models.py:78` | Reuse for bulk diagnosis request body |
| `@app.post("/jobs/bulk-cancel")` | `main.py:1131` | Template for bulk diagnosis endpoint |
| `useEffect + setInterval + cleanup` | Standard React | 10s poll in Jobs view mount |
| `border-l-2 border-amber-500/60` | Amber usage in codebase | PENDING/stuck-ASSIGNED row accent |
| `authenticatedFetch` | `auth.ts` | All API calls |
| `DispatchDiagnosis` interface | `Jobs.tsx:83` | Extend with `stuck_assigned` reason |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Backend: Extend get_dispatch_diagnosis

The existing method returns early for non-PENDING jobs. Phase 88 adds a stuck-ASSIGNED check **before** the PENDING-only guard:

```python
# Before current early return for non-PENDING:
if job.status == "ASSIGNED" and job.started_at:
    threshold = (job.timeout_minutes or 30) * 1.2
    elapsed = (datetime.utcnow() - job.started_at).total_seconds() / 60
    if elapsed > threshold:
        return {
            "reason": "stuck_assigned",
            "message": f"Assigned to {job.node_id} — no signal in {int(elapsed)} min",
            "queue_position": None,
        }
    return {"reason": "not_pending", "message": f"Job is ASSIGNED", "queue_position": None}
```

This keeps the existing `not_pending` return for ASSIGNED jobs that are NOT stuck, while surfacing stuck ones with actionable diagnosis.

### Backend: Bulk Endpoint

```python
class BulkDiagnosisRequest(BaseModel):
    guids: List[str]

class BulkDiagnosisResponse(BaseModel):
    results: Dict[str, dict]

@app.post("/jobs/dispatch-diagnosis/bulk", tags=["Jobs"])
async def bulk_dispatch_diagnosis(
    req: BulkDiagnosisRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    results = {}
    for guid in req.guids:
        results[guid] = await JobService.get_dispatch_diagnosis(guid, db)
    return {"results": results}
```

**Route ordering critical:** `POST /jobs/dispatch-diagnosis/bulk` must be registered BEFORE `GET /jobs/{guid}/dispatch-diagnosis` in main.py — FastAPI matches routes in registration order and `{guid}` would otherwise consume the string "dispatch-diagnosis".

Actually, since the bulk endpoint is POST and the single is GET, there is no conflict. But the URL `POST /jobs/dispatch-diagnosis/bulk` is structured so that `dispatch-diagnosis` appears as a guid in `GET /jobs/{guid}/dispatch-diagnosis`. Since one is POST and one is GET, FastAPI routes by method + path — no conflict.

### Frontend: Diagnosis Cache State

```typescript
const [diagnosisCache, setDiagnosisCache] = useState<Record<string, DispatchDiagnosis>>({});

// Poll targets
const pendingGuids = jobs
  .filter(j => j.status === 'PENDING' || isStuckAssigned(j))
  .map(j => j.guid);

// Poll function
const fetchDiagnoses = useCallback(async () => {
  if (pendingGuids.length === 0) return;
  try {
    const r = await authenticatedFetch('/jobs/dispatch-diagnosis/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guids: pendingGuids }),
    });
    if (!r.ok) return;
    const data = await r.json();
    setDiagnosisCache(prev => ({ ...prev, ...data.results }));
  } catch {}
}, [pendingGuids]);
```

Note: `isStuckAssigned` client-side pre-filter is for avoiding unnecessary API calls — the server performs the authoritative check. Client can use `job.started_at && job.status === 'ASSIGNED'` as a coarse filter (server will return `not_pending` for non-stuck assigned jobs, which are ignored by the UI).

### Frontend: Row Rendering

The Status cell at `Jobs.tsx:1401` currently renders a single `<Badge>`. Phase 88 changes it to a flex-col layout:

```tsx
<TableCell className={`${
  (job.status === 'PENDING' || diagnosisCache[job.guid]?.reason === 'stuck_assigned')
    ? 'border-l-2 border-amber-500/60'
    : ''
}`}>
  <div className="flex flex-col gap-0.5">
    {/* existing Badge rendering */}
    {diagnosisCache[job.guid] && diagnosisCache[job.guid].reason !== 'not_pending' && (
      <span className="text-xs text-amber-400/80 leading-tight">
        {diagnosisCache[job.guid].message}
        {diagnosisCache[job.guid].queue_position != null &&
         diagnosisCache[job.guid].queue_position! >= 2 &&
         ` · ${ordinal(diagnosisCache[job.guid].queue_position!)} in queue`}
      </span>
    )}
  </div>
</TableCell>
```

### Frontend: Poll useEffect

```typescript
useEffect(() => {
  if (pendingGuids.length === 0) return;
  fetchDiagnoses(); // immediate on mount / when pending jobs change
  const id = setInterval(fetchDiagnoses, 10_000);
  return () => clearInterval(id);
}, [pendingGuids.join(',')]); // stringify for stable dep comparison
```

### Frontend: Manual Refresh Button

Insert into Queue Monitor card header at `Jobs.tsx:1193–1198`:

```tsx
<Button
  size="sm"
  variant="ghost"
  className="text-zinc-400 hover:text-white"
  onClick={fetchDiagnoses}
  title="Refresh dispatch diagnosis"
>
  <RefreshCw className="h-3.5 w-3.5" />
</Button>
```

### Frontend: Drawer Auto-Refresh

The drawer already has a `useEffect` at `Jobs.tsx:222` that fetches diagnosis when `open && job.status === 'PENDING'`. Phase 88 extends this with a `setInterval` for the PENDING/stuck-ASSIGNED case:

```typescript
useEffect(() => {
  const isPendingOrStuck = job.status === 'PENDING' || job.status === 'ASSIGNED';
  if (!open || !job || !isPendingOrStuck) {
    setDiagnosis(null);
    return;
  }
  // ... existing fetch ...
  const id = setInterval(() => {
    authenticatedFetch(`/jobs/${job.guid}/dispatch-diagnosis`)
      .then(r => r.ok ? r.json() : null)
      .then(data => data && setDiagnosis(data))
      .catch(() => {});
  }, 10_000);
  return () => clearInterval(id);
}, [open, job?.guid, job?.status]);
```

### Anti-Patterns to Avoid

- **Per-row individual fetch:** Don't call `/jobs/{guid}/dispatch-diagnosis` once per row — use the bulk endpoint.
- **WebSocket-triggered bulk fetch:** Context says no — polling only for list, WS only for drawer.
- **Modifying badge variant for stuck-ASSIGNED:** Badge stays `assigned`; only sub-text added.
- **Removing existing drawer diagnosis logic:** Keep drawer working — just add interval.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Poll interval | Custom debounce/throttle | `setInterval` + cleanup in `useEffect` | Standard React pattern, already used in project |
| Ordinal suffix | Custom "1st/2nd/3rd" logic | Inline helper `(n) => n === 2 ? '2nd' : n === 3 ? '3rd' : ${n}th` | Simple enough inline; no library needed for 1-digit counts |
| Bulk request body | New model class | Reuse `BulkJobActionRequest` from models.py or create slim `BulkDiagnosisRequest` | Keeps parity with existing bulk endpoints |

**Key insight:** This phase is ~95% wiring — the logic exists, the patterns exist. Avoid any temptation to create new abstractions (no custom hooks, no new context, no new components beyond what's strictly needed).

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Route Ordering — POST before GET conflict
**What goes wrong:** `POST /jobs/dispatch-diagnosis/bulk` registered after `GET /jobs/{guid}/dispatch-diagnosis` — FastAPI may match `dispatch-diagnosis` as a guid in some edge cases.
**Why it happens:** FastAPI matches path params greedily; `{guid}` is a string that matches anything.
**How to avoid:** Register `POST /jobs/dispatch-diagnosis/bulk` before `GET /jobs/{guid}/dispatch-diagnosis` in main.py. Actually since methods differ (POST vs GET), FastAPI handles them independently — but placement near the existing GET endpoint is cleaner.
**Warning signs:** Bulk endpoint returns 404 or 405 in tests.

### Pitfall 2: pendingGuids dependency array instability
**What goes wrong:** `useEffect` dep on `pendingGuids` (array) fires on every render because array identity changes.
**Why it happens:** `jobs.filter(...).map(...)` creates a new array reference each render.
**How to avoid:** Stringify dep: `[pendingGuids.join(',')]`. This creates a stable string dep that only changes when guid set changes.
**Warning signs:** Infinite re-renders, console flood of API calls.

### Pitfall 3: Cache stale after job completes
**What goes wrong:** A job transitions to COMPLETED/FAILED; its old diagnosis entry stays in `diagnosisCache`, showing amber text on a completed row.
**Why it happens:** Cache is additive — only set, never cleared.
**How to avoid:** Either (a) filter diagnosisCache display by `job.status === 'PENDING'` OR (b) prune cache on bulk response — only keep guids that are still in the current pending set. Option (a) is simpler.
**Warning signs:** Green "completed" rows showing amber diagnosis text.

### Pitfall 4: Drawer interval fires after drawer closes
**What goes wrong:** Interval continues after drawer closes because cleanup didn't run.
**Why it happens:** `return () => clearInterval(id)` not executed if `useEffect` deps don't re-run.
**How to avoid:** Include `open` in the effect deps — when `open` becomes false, the effect re-runs and clearInterval fires in the cleanup.
**Warning signs:** Console errors "Cannot read property of null" from closed drawer component.

</common_pitfalls>

<code_examples>
## Code Examples

### Backend: BulkDiagnosisResponse shape
```python
# models.py addition
class BulkDiagnosisRequest(BaseModel):
    """Request body for bulk dispatch diagnosis (Phase 88)."""
    guids: List[str]

# Response is a plain dict — no Pydantic model needed since values are dicts
# Return: {"results": {"guid1": {reason, message, queue_position}, ...}}
```

### Backend: stuck-ASSIGNED check in get_dispatch_diagnosis
```python
# Add BEFORE the existing "if job.status != 'PENDING'" guard
if job.status == "ASSIGNED" and job.started_at:
    threshold_minutes = (job.timeout_minutes or 30) * 1.2
    elapsed_minutes = (datetime.utcnow() - job.started_at).total_seconds() / 60
    if elapsed_minutes > threshold_minutes:
        return {
            "reason": "stuck_assigned",
            "message": f"Assigned to {job.node_id} — no response in {int(elapsed_minutes)} min",
            "queue_position": None,
        }
```

### Frontend: Ordinal helper
```typescript
// Simple ordinal for queue position display (1-based)
const toOrdinal = (n: number): string => {
    if (n === 1) return '1st';
    if (n === 2) return '2nd';
    if (n === 3) return '3rd';
    return `${n}th`;
};
```

### Frontend: DispatchDiagnosis interface extension
```typescript
// Extend existing interface to include new reason codes
interface DispatchDiagnosis {
    reason: 'no_nodes_online' | 'capability_mismatch' | 'all_nodes_busy' |
            'target_node_unavailable' | 'pending_dispatch' | 'not_pending' |
            'stuck_assigned';
    message: string;
    queue_position?: number | null;
}
```

</code_examples>

<open_questions>
## Open Questions

1. **Cache invalidation on job status change**
   - What we know: WebSocket broadcasts `job:updated` when status changes
   - What's unclear: Should the cache clear a guid when WS fires `job:updated` for that guid?
   - Recommendation: Yes — in the `useWebSocket` callback, remove the guid from `diagnosisCache` when its status changes to non-PENDING/non-ASSIGNED. Keeps cache clean without an extra fetch.

2. **Stuck-ASSIGNED threshold for jobs with no timeout_minutes**
   - What we know: CONTEXT.md specifies 30-minute fallback when `timeout_minutes` is null
   - What's unclear: Nothing — threshold is `(job.timeout_minutes or 30) * 1.2`
   - Recommendation: Implement exactly as specified.

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `puppeteer/agent_service/services/job_service.py:1229–1328` — existing get_dispatch_diagnosis implementation
- Direct codebase inspection: `puppeteer/agent_service/main.py:1063–1069` — existing single-job endpoint
- Direct codebase inspection: `puppeteer/dashboard/src/views/Jobs.tsx:83–243` — existing DispatchDiagnosis interface, drawer implementation
- Direct codebase inspection: `puppeteer/agent_service/main.py:1131–1200` — bulk endpoint patterns

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions (Phase 88 discuss-phase output) — all implementation decisions locked

### Tertiary (LOW confidence)
- None — all findings are from direct codebase inspection

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: FastAPI async routes + React hooks
- Ecosystem: No new libraries
- Patterns: Bulk endpoint, interval polling, inline row expansion
- Pitfalls: Route ordering, dep array stability, cache staleness

**Confidence breakdown:**
- Backend extension: HIGH — service method logic is clear, pattern is established
- Bulk endpoint: HIGH — mirrors existing /jobs/bulk-cancel pattern exactly
- Frontend poll: HIGH — standard React useEffect + setInterval pattern
- Row rendering: HIGH — existing amber patterns confirmed in codebase

**Validation Architecture:**
Backend: `pytest puppeteer/tests/test_tools.py` (or add `test_dispatch_diagnosis.py`)
Frontend: `npm run test` in `puppeteer/dashboard/`
Integration: Python Playwright against Docker stack per CLAUDE.md

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (stable codebase, no fast-moving deps)
</metadata>

## Validation Architecture

### Test Infrastructure

| Layer | Framework | Command | Runtime |
|-------|-----------|---------|---------|
| Backend unit | pytest | `cd puppeteer && pytest tests/` | ~10s |
| Frontend unit | vitest | `cd puppeteer/dashboard && npm run test` | ~15s |
| Integration | Python Playwright | `python ~/Development/mop_validation/scripts/test_playwright.py` | ~60s |

### Key Test Cases

**Backend (pytest):**
- `test_bulk_diagnosis_pending_jobs` — POST /jobs/dispatch-diagnosis/bulk returns results dict
- `test_bulk_diagnosis_empty_list` — empty guids returns empty results
- `test_stuck_assigned_diagnosis` — ASSIGNED job past threshold returns stuck_assigned reason
- `test_non_stuck_assigned_returns_not_pending` — ASSIGNED job within threshold returns not_pending

**Frontend (vitest):**
- Diagnosis cache populates after mount
- Status cell shows amber sub-text for PENDING job with diagnosis
- Refresh button triggers immediate fetch
- Diagnosis sub-text hidden for COMPLETED jobs (cache display filter)

---

*Phase: 88-dispatch-diagnosis-ui*
*Research completed: 2026-03-29*
*Ready for planning: yes*

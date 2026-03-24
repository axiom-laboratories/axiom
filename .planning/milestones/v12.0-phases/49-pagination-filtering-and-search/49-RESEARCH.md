# Phase 49: Pagination, Filtering and Search - Research

**Researched:** 2026-03-22
**Domain:** FastAPI cursor pagination, SQLAlchemy filtering, React filter UI, CSV streaming
**Confidence:** HIGH

## Summary

This phase adds a server-side navigation and discoverability layer over existing job and node data. All decisions are already locked in CONTEXT.md — cursor-based "load more" for Jobs, offset page-based for Nodes, a compact 9-axis filter bar, free-text name/GUID search, and CSV export. The backend work is a direct augmentation of `JobService.list_jobs` and the `GET /nodes` route in `main.py`. The frontend refactors `Jobs.tsx` to replace the two-call pattern (`/jobs` + `/jobs/count`) with a single response envelope `{items, total, next_cursor}` and adds a filter bar using only components already installed in the project.

The critical implementation detail is the cursor encoding: the cursor is a base64-encoded `{created_at, guid}` pair and the WHERE clause uses `(created_at < ts) OR (created_at = ts AND guid < guid_val)`. This avoids duplicate or skipped rows when new jobs arrive between pages. All nine filter axes compose with AND at the SQL level using SQLAlchemy's `.where()` chain.

The `created_by` field does not exist on the `Job` model — only on `ScheduledJob`. The decision in CONTEXT.md says Claude decides whether to add it or use `node_id` as a proxy. Given that `created_by` on jobs is genuinely useful and the migration path is trivial (nullable column), adding it to the `Job` model is the right call.

**Primary recommendation:** Implement backend cursor pagination and filtering as a `list_jobs` rewrite in `job_service.py` that returns a `PaginatedJobResponse` envelope; add `Job.name` and `Job.created_by` nullable columns via migration_v39.sql; build the filter bar in `Jobs.tsx` using the existing `Select`, `Input`, `Sheet`, and `Badge` components without any new npm installs.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Backend column only in Phase 49** — add nullable `name` column to the `Job` DB model; no name field added to the existing raw-JSON dispatch form (guided form in Phase 50 is the canonical submission UX for naming)
- Names are **non-unique free labels** — duplicate names are allowed; search returns all matching jobs
- When the scheduler fires a `ScheduledJob`, the resulting `Job.name` is **auto-populated** from the `ScheduledJob` name
- `name` included in `JobResponse` from `GET /jobs`
- In the Jobs table: show name if present, otherwise show truncated GUID as now — no permanent empty "Name" column
- Free-text search box matches against both `Job.name` (if set) and `Job.guid` server-side
- Search is one of the compact filter bar controls (always visible, not behind "More filters")
- Cursor is a **base64-encoded {created_at, guid} pair** — stable across new job arrivals
- Backend WHERE clause: `created_at < cursor_ts OR (created_at = cursor_ts AND guid < cursor_guid)`
- "Load more" button appends next page; counter shows "Showing N of M total"
- Page size: 50 rows
- Nodes use standard prev/next page controls with current page number and total count
- **job:created** while mid-scroll: sticky "N new jobs — click to refresh" banner at top
- **job:updated** (status change): in-place row update by GUID — no full list refetch
- **Compact filter bar**: always visible: Search box | Status dropdown | Runtime dropdown | [More filters] button; "More filters" expands: date range, target node combobox, target tags chip input, created-by text input
- **Active filter chips** always displayed below the filter bar
- **Date range**: relative presets (Last 1h / Last 24h / Last 7d / Last 30d) + Custom (two date-time pickers)
- **Target node**: searchable combobox (Radix Popover + Input + list)
- **Target tags**: chip-style multi-tag input; OR logic within tags axis
- **Created-by**: plain text input
- **All axes compose with AND**
- **Metadata-only export**: guid, name, status, task_type, display_type, runtime, node_id, created_at, started_at, completed_at, duration_seconds, target_tags — no payload JSON, no result/stdout
- Export **respects current filter state**
- **Backend streaming endpoint**: `GET /jobs/export` with same query params; returns `Content-Disposition: attachment; filename=jobs-export.csv`
- **Max 10,000 rows** enforced server-side

### Claude's Discretion
- Exact migration file numbering for `Job.name` column
- Whether "N new jobs" banner is a fixed sticky header element or a floating toast-style banner
- Combobox component choice (Radix or existing select pattern in the codebase)
- Exact relative preset labels (can adjust 1h/24h/7d/30d based on what makes sense)
- `created_by` field — if not currently on the Job model, Claude decides whether to add it or search by `node_id` as a proxy

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | Jobs view uses server-side cursor-based pagination — "load more" appends next page; total count shown ("Showing 50 of 12,483") | Cursor WHERE clause pattern documented; `list_jobs` refactored to return `PaginatedJobResponse`; Jobs.tsx fetchJobs consolidated into single endpoint call |
| SRCH-02 | Nodes view uses server-side page-based pagination with page controls and total count | `list_nodes` in main.py needs `page`+`page_size` query params and `total` count; NodeResponse already complete; Nodes.tsx needs page control UI |
| SRCH-03 | Operator can filter the Jobs view by status, runtime, task type, target node, target tags, created-by, and date ranges — all server-side; active filters shown as dismissible chips | SQLAlchemy filter chaining pattern; compact filter bar + "More filters" Sheet pattern; Badge component for dismissible chips |
| SRCH-04 | Operator can search jobs by name or GUID via free-text search box; operator can optionally name a job at submission time via the guided form (Phase 50) | `Job.name` nullable column via migration_v39.sql; search is `OR(name ILIKE, guid ILIKE)` server-side; scheduler auto-populates name from ScheduledJob.name; JobResponse gains `name` field |
| SRCH-05 | Operator can export the current filtered Jobs view as CSV | `GET /jobs/export` streaming endpoint; Python `csv` stdlib (no additional deps); max 10,000 rows; `StreamingResponse` with `text/csv` media type |
</phase_requirements>

---

## Standard Stack

### Core (all already installed — zero new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy (async) | existing | Cursor/offset pagination filter chaining | Already in use throughout the backend |
| FastAPI `StreamingResponse` | existing | CSV streaming export | Built into FastAPI — no extra install |
| Python `csv` stdlib | stdlib | CSV row writing | No deps; works perfectly for streaming |
| `base64` stdlib | stdlib | Cursor encoding/decoding | Standard; already imported in various places |
| `@radix-ui/react-popover` | ^1.1.15 | Searchable combobox for target node | Already in package.json |
| `@radix-ui/react-dialog` | ^1.1.15 | "More filters" panel (Sheet already used in Jobs.tsx) | Already installed |
| `date-fns` | ^4.1.0 | Date arithmetic for relative presets (Last 1h, Last 24h, etc.) | Already installed |
| `lucide-react` | ^0.562.0 | Filter/search icons | Already installed |

**Installation:**
```bash
# No new packages required — all dependencies already present
```

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vitest` | ^3.0.5 | Backend-adjacent unit tests; frontend component tests | Already the test runner |
| `pytest` + `httpx` | existing | Backend route tests for pagination params | Already in use |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python `csv` stdlib streaming | `pandas` | pandas is heavyweight; stdlib is zero-dep and sufficient for metadata-only rows |
| Radix Popover combobox | `cmdk` (Command Menu) | cmdk is not installed; Radix Popover + Input achieves the same searchable dropdown with what's already there |
| Sheet for "More filters" | Dialog | Sheet (already in Jobs.tsx imports) is more appropriate — slides in from side, doesn't block the table |

---

## Architecture Patterns

### Backend: Cursor Pagination Response Envelope

Replace the two-call pattern (`GET /jobs` + `GET /jobs/count`) with a single response:

```python
# models.py — new response model
class PaginatedJobResponse(BaseModel):
    items: List[JobResponse]
    total: int
    next_cursor: Optional[str] = None  # base64-encoded {created_at, guid}
```

```python
# job_service.py — cursor WHERE clause
# Source: SQLAlchemy docs, official query patterns
import base64, json
from datetime import datetime

def _encode_cursor(created_at: datetime, guid: str) -> str:
    payload = {"ts": created_at.isoformat(), "guid": guid}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    payload = json.loads(base64.urlsafe_b64decode(cursor).decode())
    return datetime.fromisoformat(payload["ts"]), payload["guid"]

# In list_jobs — cursor WHERE
if cursor:
    ts, guid = _decode_cursor(cursor)
    query = query.where(
        or_(
            Job.created_at < ts,
            and_(Job.created_at == ts, Job.guid < guid)
        )
    )
```

### Backend: Filter Chain Pattern

All nine filter axes use `.where()` chaining — each is independent and composes with AND:

```python
# job_service.py — all filter params optional
async def list_jobs(
    db, limit=50, cursor=None,
    status=None, runtime=None, task_type=None,
    node_id=None, tags=None,        # tags: List[str], OR logic within axis
    created_by=None,
    date_from=None, date_to=None,   # datetime objects
    search=None,                    # matches name OR guid
) -> dict:  # {items, total, next_cursor}

    query = select(Job).where(Job.task_type != 'system_heartbeat')
    count_query = select(func.count()).select_from(Job).where(Job.task_type != 'system_heartbeat')

    # Apply same filters to both queries
    if status and status.upper() != 'ALL':
        f = Job.status == status.upper()
        query = query.where(f); count_query = count_query.where(f)

    if runtime:
        f = Job.runtime == runtime
        query = query.where(f); count_query = count_query.where(f)

    if node_id:
        f = Job.node_id == node_id
        query = query.where(f); count_query = count_query.where(f)

    if tags:  # OR logic — job must have ANY of the given tags
        # tags stored as JSON string — use LIKE for each tag, OR them
        tag_filters = [Job.target_tags.like(f'%"{t}"%') for t in tags]
        f = or_(*tag_filters)
        query = query.where(f); count_query = count_query.where(f)

    if created_by:
        f = Job.created_by.ilike(f'%{created_by}%')
        query = query.where(f); count_query = count_query.where(f)

    if date_from:
        f = Job.created_at >= date_from
        query = query.where(f); count_query = count_query.where(f)

    if date_to:
        f = Job.created_at <= date_to
        query = query.where(f); count_query = count_query.where(f)

    if search:
        f = or_(Job.guid.ilike(f'%{search}%'), Job.name.ilike(f'%{search}%'))
        query = query.where(f); count_query = count_query.where(f)

    # Count (before cursor, which would exclude rows)
    total = (await db.execute(count_query)).scalar()

    # Apply cursor AFTER count
    if cursor: ...  # (see cursor pattern above)

    query = query.order_by(desc(Job.created_at), desc(Job.guid)).limit(limit)
    jobs = (await db.execute(query)).scalars().all()

    next_cursor = None
    if len(jobs) == limit:
        last = jobs[-1]
        next_cursor = _encode_cursor(last.created_at, last.guid)

    return {"items": [...], "total": total, "next_cursor": next_cursor}
```

### Backend: CSV Streaming

```python
# main.py — GET /jobs/export
import csv, io
from fastapi.responses import StreamingResponse

@app.get("/jobs/export", tags=["Jobs"])
async def export_jobs(
    # same filter params as list_jobs
    current_user=Depends(require_permission("jobs:read")),
    db=Depends(get_db)
):
    EXPORT_LIMIT = 10_000
    jobs = await JobService.list_jobs_for_export(db, limit=EXPORT_LIMIT, **filter_params)

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["guid","name","status","task_type","display_type","runtime",
                         "node_id","created_at","started_at","completed_at",
                         "duration_seconds","target_tags"])
        yield buf.getvalue(); buf.seek(0); buf.truncate()
        for job in jobs:
            writer.writerow([job["guid"], job.get("name",""), ...])
            yield buf.getvalue(); buf.seek(0); buf.truncate()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs-export.csv"}
    )
```

### Backend: Nodes Page-Based Pagination

```python
# main.py — GET /nodes (modified)
@app.get("/nodes")
async def list_nodes(
    page: int = 1,
    page_size: int = 25,
    current_user=Depends(require_auth),
    db=Depends(get_db)
):
    # total count
    total_result = await db.execute(select(func.count()).select_from(Node))
    total = total_result.scalar()

    # paginated nodes
    result = await db.execute(
        select(Node).order_by(Node.hostname).offset((page - 1) * page_size).limit(page_size)
    )
    nodes = result.scalars().all()
    # ... rest of existing build logic ...
    return {"items": resp, "total": total, "page": page, "pages": math.ceil(total / page_size)}
```

### Frontend: Jobs Filter Bar Structure

The filter bar uses only components already in the codebase:

```
[Search Input]  [Status Select]  [Runtime Select]  [More Filters ▼]
──────────────────────────────────────────────────────────────────
[Active Chip: status=FAILED ×]  [Active Chip: runtime=bash ×]  [Export CSV]
```

"More Filters" opens a `Sheet` (from Jobs.tsx existing imports). Inside the Sheet:
- Date range: two `<Input type="datetime-local">` for custom, plus preset buttons
- Target node: Radix Popover + Input for searchable combobox (Popover already installed)
- Target tags: chip input (Input + Enter key handler + Badge chips)
- Created by: plain `Input`

### Frontend: "N new jobs" Banner

A state-driven sticky div at the top of the Jobs table card, only visible when `newJobsCount > 0`:

```tsx
// In Jobs.tsx — state
const [pendingNewJobs, setPendingNewJobs] = useState(0);

// In WebSocket handler — for job:created, increment rather than refetch
if (event === 'job:created') {
    setPendingNewJobs(c => c + 1);
} else if (event === 'job:updated') {
    // In-place update: find job by guid in current list, patch status
    setJobs(prev => prev.map(j => j.guid === data.guid ? {...j, ...data} : j));
}

// In JSX — above the table
{pendingNewJobs > 0 && (
    <div
        className="sticky top-0 z-10 bg-primary/90 text-white text-sm px-4 py-2 cursor-pointer text-center"
        onClick={() => { setPendingNewJobs(0); resetToPage1(); }}
    >
        {pendingNewJobs} new job{pendingNewJobs !== 1 ? 's' : ''} — click to refresh
    </div>
)}
```

### Frontend: State Shape for Filters

```tsx
interface FilterState {
    search: string;           // name or GUID
    status: string;           // 'all' | 'PENDING' | ...
    runtime: string;          // 'all' | 'python' | 'bash' | 'powershell'
    taskType: string;         // 'all' | 'script' | ...
    nodeId: string;           // node_id or ''
    tags: string[];           // OR logic
    createdBy: string;        // partial match
    dateFrom: string;         // ISO string or ''
    dateTo: string;           // ISO string or ''
    datePreset: string;       // '1h' | '24h' | '7d' | '30d' | 'custom' | ''
}
```

### Anti-Patterns to Avoid
- **Client-side filtering after fetching all rows:** The current `filterText` in Jobs.tsx does client-side GUID filtering — this is being replaced with server-side search. Do not mix client-side and server-side filtering.
- **Replacing the list on job:created WebSocket event:** The new pattern is to increment the banner counter and only replace the list when the operator explicitly clicks. Do not refetch the full list on every WebSocket event.
- **Re-encoding the cursor on every render:** The cursor should only be re-encoded server-side when the list has exactly `limit` items. An empty page or partial page means there's no next cursor.
- **Using OFFSET for Jobs pagination:** Offset pagination causes skipped/duplicated rows when new jobs are inserted between page loads. Cursor-based is the locked decision.
- **Tags filter with JSON containment operator:** SQLite does not support the Postgres `@>` JSON operator. Use LIKE `%"tag"%` for portability (both SQLite and Postgres).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV generation | Custom string concatenation | Python `csv` stdlib | Handles quoting, escaping, newlines correctly |
| Cursor encoding | Custom encoding scheme | `base64.urlsafe_b64encode(json.dumps(...))` | URL-safe, readable, easy to decode; no deps |
| Date arithmetic for presets | Manual timedelta math inline in component | `date-fns` `subHours`, `subDays` | Already installed; handles DST, leap years |
| Searchable combobox | Custom dropdown with search | Radix Popover + Input filter | Popover already installed; wheel not re-invented |
| Streaming response | Load all into memory then send | FastAPI `StreamingResponse` + generator | Required for 10k row exports to avoid OOM |

**Key insight:** The entire feature set can be delivered with zero new dependencies. The backend uses stdlib + existing SQLAlchemy patterns. The frontend uses existing installed packages. New installs would add risk with no benefit.

---

## Common Pitfalls

### Pitfall 1: Tags JSON LIKE Filter Ambiguity
**What goes wrong:** Searching for tag `"gpu"` with `LIKE '%gpu%'` matches jobs tagged `"gpu-v2"` or `"no-gpu"` because the substring match is too loose.
**Why it happens:** Tags are stored as JSON strings like `'["linux","gpu","prod"]'`. Simple LIKE is not tag-aware.
**How to avoid:** Use `LIKE '%"gpu"%'` (with quotes included in the pattern). This matches the JSON-serialized form `"gpu"` exactly within the array string. Edge case: works for all standard ASCII tag names; avoid tags with special characters.
**Warning signs:** Filter returning unexpected results when tags share substrings.

### Pitfall 2: Cursor Ordering Must Match Query Ordering
**What goes wrong:** Cursor decodes fine but returns duplicate rows or skips rows on next page.
**Why it happens:** The ORDER BY clause in the query must match the fields used in the cursor. If the sort is `desc(created_at), desc(guid)`, the cursor WHERE must be `(created_at < ts) OR (created_at = ts AND guid < guid_val)` — using the same ordering direction.
**How to avoid:** Declare a constant ordering `ORDER BY created_at DESC, guid DESC` and derive the cursor condition from this same ordering. Add a test: create 105 jobs with known timestamps, paginate to page 3, verify no duplicates.
**Warning signs:** Missing jobs in the list, or same GUID appearing on two pages.

### Pitfall 3: Total Count Includes Cursor Filter
**What goes wrong:** The "Showing N of M total" counter changes as user loads more pages (M decreases).
**Why it happens:** If the count query is run after the cursor WHERE clause is applied, it only counts remaining rows, not the full filtered set.
**How to avoid:** Run the `total` count query BEFORE applying the cursor WHERE clause. The cursor narrows the page window; the total always reflects the full filter state.
**Warning signs:** "Showing 50 of 12,483" becomes "Showing 100 of 12,433" on load more.

### Pitfall 4: in-place Row Update Breaks on Stale Job Data
**What goes wrong:** In-place `job:updated` update from WebSocket patches status but the job's `duration_seconds` stays stale because it was computed at fetch time.
**Why it happens:** `duration_seconds` is computed server-side in `list_jobs`. The WebSocket `job:updated` event only carries the changed fields.
**How to avoid:** When patching a row in-place, accept that `duration_seconds` will update on next explicit refresh. Alternatively, the WebSocket event payload could include all `JobResponse` fields. Check what the existing `job:updated` event payload contains in `useWebSocket.ts`.
**Warning signs:** Duration shows as stale after job completes if the operator doesn't load more or refresh.

### Pitfall 5: CSV Export With No Streaming Causes Timeout
**What goes wrong:** Export of 10,000 rows times out or causes OOM in the container.
**Why it happens:** Loading 10k rows into memory + building a string before responding can take multiple seconds.
**How to avoid:** Use `StreamingResponse` with a Python generator that yields one row at a time. Each yield flushes to the client immediately.
**Warning signs:** Large exports return HTTP 504 or the agent container's memory spikes.

### Pitfall 6: Nodes Pagination Breaks Stats History Batch Query
**What goes wrong:** The batch stats history query in `list_nodes` fetches ALL NodeStats for ALL nodes. With pagination, this should only fetch stats for the current page's nodes.
**Why it happens:** The current implementation fetches the full Node list first, then batch-queries NodeStats. With pagination, it must paginate nodes first, then batch-query only the page's node IDs.
**How to avoid:** Apply pagination (OFFSET/LIMIT) to the node query first, collect the page's `node_ids`, then run the NodeStats batch query scoped to those IDs.

---

## Code Examples

Verified patterns from the existing codebase:

### Existing list_jobs signature (to be extended)
```python
# Source: puppeteer/agent_service/services/job_service.py:42
@staticmethod
async def list_jobs(db: AsyncSession, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[dict]:
    query = select(Job).where(Job.task_type != 'system_heartbeat')
    if status and status.upper() != 'ALL':
        query = query.where(Job.status == status.upper())
    query = query.order_by(desc(Job.created_at)).offset(skip).limit(limit)
```

### Existing count_jobs route (to be consolidated into list_jobs response)
```python
# Source: puppeteer/agent_service/main.py:923
@app.get("/jobs/count", tags=["Jobs"])
async def count_jobs(status: Optional[str] = None, ...):
    query = select(sqlfunc.count()).select_from(Job).where(Job.task_type != 'system_heartbeat')
    if status and status.upper() != 'ALL':
        query = query.where(Job.status == status.upper())
    result = await db.execute(query)
    return {"total": result.scalar()}
```

### Existing Jobs.tsx two-call pattern (to be replaced)
```typescript
// Source: puppeteer/dashboard/src/views/Jobs.tsx:315
const fetchJobs = async (p = page, status = filterStatus) => {
    const [jobsRes, countRes] = await Promise.all([
        authenticatedFetch(`/jobs?skip=${p * PAGE_SIZE}&limit=${PAGE_SIZE}${statusParam}`),
        authenticatedFetch(`/jobs/count${status !== 'all' ? `?status=${status}` : ''}`),
    ]);
    if (jobsRes.ok) setJobs(await jobsRes.json());
    if (countRes.ok) { const d = await countRes.json(); setTotal(d.total); }
};
```

### Existing WebSocket handler (to be modified for in-place updates)
```typescript
// Source: puppeteer/dashboard/src/views/Jobs.tsx:338
useWebSocket((event) => {
    if (event === 'job:created' || event === 'job:updated') fetchJobs(page, filterStatus);
});
```

### Migration pattern (most recent is v38)
```sql
-- Source: puppeteer/migration_v38.sql
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR;
```

### Existing Sheet usage in Jobs.tsx (for "More filters" panel)
```typescript
// Source: puppeteer/dashboard/src/views/Jobs.tsx:45
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
```

### Radix Popover pattern (for target node combobox)
```typescript
// @radix-ui/react-popover is already installed (package.json:19)
// Pattern: Popover wrapping a list, filtered by a controlled Input
import * as Popover from '@radix-ui/react-popover';
// Open Popover, render Input + scrollable node list, filter list by input value
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `GET /jobs?skip=N&limit=50` + `GET /jobs/count` two-call | Single `GET /jobs?cursor=...` returning `{items, total, next_cursor}` | Phase 49 | Eliminates race condition between count and list; reduces requests by 50% |
| Client-side GUID filter in Jobs.tsx | Server-side `search` query param matching name + GUID | Phase 49 | Enables searching 10k+ jobs; name search only possible server-side |
| `GET /nodes` returning full list always | `GET /nodes?page=1&page_size=25` returning `{items, total, page, pages}` | Phase 49 | Required for fleets with 100+ nodes |

**Deprecated/outdated:**
- `GET /jobs/count` endpoint: superseded by the `total` field in the paginated response; the route can be kept for backward compatibility but the frontend will no longer call it
- Client-side `filterText` in Jobs.tsx: the `jobs.filter(j => !filterText || j.guid.toLowerCase().includes(...))` pattern is removed in favor of the server-side `search` param

---

## DB Changes Required

### Job model additions (migration_v39.sql — next in sequence after v38)

```sql
-- migration_v39.sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS name VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_by VARCHAR;
```

**Decision on `created_by`:** Adding it as a nullable column is the right call. The `ScheduledJob` already has `created_by`; jobs created by the scheduler can be stamped with `s_job.created_by`. Jobs created via `POST /jobs` can be stamped with `current_user.username`. This is far more useful than using `node_id` as a proxy (node_id is where the job ran, not who submitted it). The filter is then a real `created_by` text match.

**Index recommendation:** Add an index on `jobs.name` for search performance on large datasets:

```sql
CREATE INDEX IF NOT EXISTS ix_jobs_name ON jobs(name);
CREATE INDEX IF NOT EXISTS ix_jobs_created_by ON jobs(created_by);
```

The existing `jobs` table has no indices beyond the primary key (`guid`). For cursor pagination, an index on `(created_at DESC, guid DESC)` would help:

```sql
CREATE INDEX IF NOT EXISTS ix_jobs_created_at_guid ON jobs(created_at DESC, guid DESC);
```

### JobResponse additions (models.py)

```python
class JobResponse(BaseModel):
    guid: str
    name: Optional[str] = None        # NEW: nullable job name
    created_by: Optional[str] = None  # NEW: submitter username
    status: str
    # ... existing fields unchanged ...
```

---

## Open Questions

1. **WebSocket `job:updated` payload shape**
   - What we know: `useWebSocket.ts` receives string events and Jobs.tsx currently refetches the full list on any `job:created` or `job:updated`
   - What's unclear: Does the WS event carry the full `JobResponse` dict, or just a `{guid, status}` delta?
   - Recommendation: Check `useWebSocket.ts` and the WS emit in `main.py`. If events carry full job data, in-place update is trivial. If only status, the in-place update patches only `status` and accepts stale `duration_seconds` until next refresh.

2. **Backward compatibility of `GET /nodes` response shape change**
   - What we know: `Nodes.tsx` currently expects `List[NodeResponse]` (an array), not a paginated envelope
   - What's unclear: Are there any other consumers of `GET /nodes` that depend on the bare array shape?
   - Recommendation: Check if any test files or other frontend views call `/nodes` directly. The response shape change from `[]` to `{items:[], total:N, page:N, pages:N}` is a breaking change to `Nodes.tsx` — plan both changes in the same plan/wave.

3. **`GET /jobs/count` route retention**
   - What we know: The endpoint exists and is called by the current `fetchJobs`. After Phase 49 it will be superseded.
   - What's unclear: Should it be removed or kept for potential CI/CD consumers?
   - Recommendation: Keep the route for backward compatibility but note it in the plan. The frontend will stop calling it.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` or inline; `puppeteer/dashboard/vite.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_pagination.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Cursor pagination returns correct items and next_cursor | unit | `cd puppeteer && pytest tests/test_pagination.py::test_cursor_pagination -x` | Wave 0 |
| SRCH-01 | "load more" total count does not change between pages | unit | `cd puppeteer && pytest tests/test_pagination.py::test_total_count_stable -x` | Wave 0 |
| SRCH-01 | No duplicate rows across 3 pages of 50 | unit | `cd puppeteer && pytest tests/test_pagination.py::test_no_duplicates -x` | Wave 0 |
| SRCH-02 | Nodes pagination returns page/pages/total fields | unit | `cd puppeteer && pytest tests/test_pagination.py::test_nodes_pagination -x` | Wave 0 |
| SRCH-03 | Status filter returns only matching status jobs | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_status -x` | Wave 0 |
| SRCH-03 | Tags filter uses OR logic | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_tags_or -x` | Wave 0 |
| SRCH-03 | Multiple filters compose with AND | unit | `cd puppeteer && pytest tests/test_pagination.py::test_filter_compose_and -x` | Wave 0 |
| SRCH-04 | Job name auto-populated from ScheduledJob on scheduler fire | unit | `cd puppeteer && pytest tests/test_pagination.py::test_scheduled_job_name_auto_populate -x` | Wave 0 |
| SRCH-04 | Search finds job by name substring | unit | `cd puppeteer && pytest tests/test_pagination.py::test_search_by_name -x` | Wave 0 |
| SRCH-04 | Search finds job by GUID substring | unit | `cd puppeteer && pytest tests/test_pagination.py::test_search_by_guid -x` | Wave 0 |
| SRCH-05 | Export returns CSV with correct headers | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_csv_headers -x` | Wave 0 |
| SRCH-05 | Export respects active filters | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_respects_filters -x` | Wave 0 |
| SRCH-05 | Export capped at 10,000 rows | unit | `cd puppeteer && pytest tests/test_pagination.py::test_export_max_rows -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_pagination.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_pagination.py` — all SRCH-01 through SRCH-05 tests
- [ ] No new conftest needed — existing async DB fixture pattern in `tests/test_tools.py` and `tests/test_runtime_expansion.py` can be reused

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `puppeteer/agent_service/services/job_service.py` — current `list_jobs` signature, skip/limit pattern, filter patterns
- Direct code reading: `puppeteer/agent_service/main.py:919-930` — current `GET /jobs` and `GET /jobs/count` routes
- Direct code reading: `puppeteer/agent_service/main.py:1180-1229` — current `GET /nodes` implementation
- Direct code reading: `puppeteer/agent_service/db.py` — full Job, Node, ScheduledJob model column inventory
- Direct code reading: `puppeteer/agent_service/models.py` — JobResponse, JobCreate, NodeResponse current fields
- Direct code reading: `puppeteer/dashboard/src/views/Jobs.tsx` — current fetchJobs pattern, WebSocket handler, filterText client-side filter
- Direct code reading: `puppeteer/dashboard/package.json` — confirms `@radix-ui/react-popover`, `date-fns`, all existing deps
- Direct code reading: `puppeteer/migration_v38.sql` — confirms next migration is v39

### Secondary (MEDIUM confidence)
- FastAPI `StreamingResponse` documentation — standard pattern for CSV streaming with generator functions
- SQLAlchemy async `select()` + `.where()` chaining — well-established pattern already in use throughout this codebase
- `base64.urlsafe_b64encode` for cursor encoding — standard Python stdlib pattern for URL-safe opaque pagination tokens

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are already installed; verified against package.json and requirements
- Architecture: HIGH — cursor WHERE clause, filter chaining, CSV streaming are all well-established patterns; verified against existing code
- DB schema changes: HIGH — verified by reading db.py; migration numbering verified against migration_v38.sql
- Pitfalls: HIGH — tags LIKE ambiguity, cursor ordering, count-before-cursor are all reproducible logic issues identified from direct code reading
- Frontend patterns: HIGH — all component imports verified in Jobs.tsx and package.json

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable patterns; dependency versions won't change in 30 days)

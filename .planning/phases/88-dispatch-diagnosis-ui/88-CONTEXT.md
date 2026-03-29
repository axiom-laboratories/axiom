# Phase 88: Dispatch Diagnosis UI - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the existing `/jobs/{guid}/dispatch-diagnosis` endpoint into the job list and detail view. An operator looking at a PENDING (or stuck ASSIGNED) job sees inline why it hasn't dispatched — without leaving the job list or opening a detail panel. Diagnosis auto-polls while the Jobs view is active and can be manually refreshed.

</domain>

<decisions>
## Implementation Decisions

### Inline row display
- Diagnosis text appears under the status badge in the same Status cell — PENDING/stuck-ASSIGNED rows become two-line; other rows remain single-line
- PENDING/stuck-ASSIGNED rows get an amber left border accent (2px) to draw the eye — no background fill
- Queue position appended inline to the message text: `"All nodes busy · 2nd in queue"` (middle dot separator, only shown when queue_position ≥ 2)
- Stuck ASSIGNED: badge stays `assigned`, diagnosis text appears below — badge text/colour does not change

### Polling strategy
- New batch endpoint: `POST /jobs/dispatch-diagnosis/bulk` — accepts list of GUIDs, returns all diagnoses in one call
- Poll fires only while the Jobs view is mounted (starts on mount, stops on unmount)
- Poll interval: Claude's discretion (5 or 10 seconds — pick based on WebSocket coexistence)
- Diagnosis data updates on timed poll only — no WebSocket-triggered re-fetch
- Manual refresh button in the Queue Monitor card header — triggers immediate batch fetch for all PENDING/stuck-ASSIGNED jobs in view

### Backend extension for stuck-ASSIGNED
- Extend (or wrap) `get_dispatch_diagnosis` to also evaluate ASSIGNED jobs
- Stuck threshold: `started_at + (timeout_minutes * 1.2)`, fallback to 30 minutes when `timeout_minutes` is null
- Return format unchanged: `{reason, message, queue_position}` — add new `reason` values: `"stuck_assigned"`, etc.
- Badge text example: `"Assigned to node-alpha — no signal in 35 min"`

### Detail panel behaviour
- Drawer keeps existing diagnosis callout — list shows summary, drawer shows same message in context (minor redundancy is acceptable)
- Drawer auto-refreshes diagnosis while open for a PENDING/stuck-ASSIGNED job (same poll interval as the list)
- No new controls added to the drawer

### Claude's Discretion
- Exact poll interval (5s or 10s — pick based on WebSocket coexistence)
- Whether stuck-ASSIGNED detection runs fully server-side (in the extended endpoint) or partially client-side (frontend pre-filters by `started_at + timeout`)
- Exact wording of the stuck-ASSIGNED message
- Internal React state shape for the diagnosis cache (map of guid → diagnosis result)

</decisions>

<specifics>
## Specific Ideas

- Batch endpoint chosen over individual-per-job requests specifically for degraded-system scenarios where many jobs are stuck — that's exactly when diagnosis is most needed
- Manual refresh button in card header (not per-row) — refreshes all diagnoses at once, avoids UI noise on every PENDING row

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `JobService.get_dispatch_diagnosis(guid, db)` in `job_service.py:1230`: Returns `{reason, message, queue_position}` for PENDING jobs. Phase 88 extends this to cover stuck-ASSIGNED and wraps it in a new bulk endpoint.
- `GET /jobs/{guid}/dispatch-diagnosis` (`main.py:1063`): Existing single-job endpoint. Phase 88 adds a companion `POST /jobs/dispatch-diagnosis/bulk`.
- `JobDetailPanel` in `Jobs.tsx:184`: Already fetches + renders diagnosis on drawer open with `authenticatedFetch`. Extend with a `useInterval` or `useEffect`-based auto-refresh.
- `Badge`, `authenticatedFetch`, `useWebSocket` — all established patterns, no new imports needed.

### Established Patterns
- Table rows: `<TableRow>` with status cell at `Jobs.tsx:1401`. Add flex-col layout inside the cell for badge + diagnosis text.
- Amber border accent: `border-l-2 border-amber-500/60` — consistent with existing amber usage in the codebase (e.g. retry badges).
- Poll patterns: `useEffect` + `setInterval` + cleanup — standard React pattern, existing hooks in the codebase do this.

### Integration Points
- Job list map at `Jobs.tsx:1373`: Each `<TableRow>` renders from `jobs.map(job => ...)`. Diagnosis state is a `Record<string, DiagnosisResult>` keyed by GUID, populated by the batch poll.
- Queue Monitor card header at `Jobs.tsx:1193–1198`: Manual refresh button goes here, beside the CardTitle.
- Drawer auto-refresh: `JobDetailPanel` component (`Jobs.tsx:182`), add interval when `open && job.status === 'PENDING'`.

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 88-dispatch-diagnosis-ui*
*Context gathered: 2026-03-29*

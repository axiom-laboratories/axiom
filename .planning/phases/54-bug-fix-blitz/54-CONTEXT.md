# Phase 54: Bug Fix Blitz - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Patch four integration defects identified by the v12.0 milestone audit (INT-01 through INT-04). No new capabilities — these are targeted code corrections to make existing features actually work end-to-end. Closes INT-01, INT-02, INT-03, INT-04.

</domain>

<decisions>
## Implementation Decisions

### INT-01: Script key mismatch (GuidedDispatchCard)
- **Fix the frontend** — `GuidedDispatchCard.tsx` sends `script_content` (not `script`) to match what `node.py` already reads via `payload.get('script_content')`
- Both dispatch call sites in the component (lines ~160 and ~214) must be updated
- **Clean up the pre-populate try-chain in Jobs.tsx** — simplify `p.script ?? p.script_content ?? p.payload?.script ?? p.payload?.script_content` to read only `script_content` after the fix is applied. Historical jobs stored with the old `script` key will not pre-populate form fields, which is an acceptable trade-off.
- Backend (node.py) is not changed — it is the authoritative execution contract

### INT-02: Queue.tsx double-prefix
- Remove `/api` prefix from `authenticatedFetch('/api/jobs')` → `authenticatedFetch('/jobs')` and from `authenticatedFetch('/api/nodes')` → `authenticatedFetch('/nodes')`
- `authenticatedFetch` already prepends API_URL (`/api`); passing `/api/jobs` produces `/api/api/jobs` which 404s in all environments
- Scope: fix only these two calls, not a broad audit of all `authenticatedFetch` usage

### INT-03: CSV export URL missing prefix
- Fix `Jobs.tsx` line ~262: `authenticatedFetch('/jobs/${guid}/executions/export')` → `authenticatedFetch('/api/jobs/${guid}/executions/export')`
- Backend route is registered at `@app.get('/api/jobs/{guid}/executions/export')` which, after Caddy strips `/api`, lands at FastAPI as `/jobs/{guid}/executions/export`. The frontend call must include the `/api/` prefix so authenticatedFetch routes it correctly.

### INT-04: list_jobs() missing retry/provenance fields
- Add `retry_count`, `max_retries`, `retry_after`, and `originating_guid` to the `response_jobs.append({...})` dict in `job_service.py` `list_jobs()`
- These columns already exist on the `Job` ORM model — no schema changes required
- `retry_after` should be serialised as ISO timestamp string (consistent with other datetime fields)

### Regression tests
- **Both vitest (frontend) and pytest (backend)** — test coverage added alongside the fixes in each plan
- **Scope: broader** — not just the 4 bug assertions; include adjacent happy-path flows for the affected components
- **Plan grouping**: tests co-located with their fixes
  - 54-01 (backend): pytest covering `list_jobs()` response shape including retry fields and originating_guid
  - 54-02 (frontend): vitest covering GuidedDispatchCard payload construction, Queue.tsx fetch URL formation, and Jobs.tsx CSV export URL

### Plan structure
- Keep the existing two-plan split: **54-01 backend** + **54-02 frontend**
- Tests added to each respective plan rather than a dedicated 54-03

### Claude's Discretion
- Exact vitest test structure (component render vs. mock fetch assertion)
- Whether pytest tests are unit-level or integration-level
- Exact line numbers / search patterns for the pre-populate cleanup

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GuidedDispatchCard.tsx`: two payload dispatch call sites, both at `payload: { script: form.scriptContent }` — both need updating to `script_content`
- `Queue.tsx`: `authenticatedFetch('/api/jobs?${qs}')` (line ~113) and `authenticatedFetch('/api/nodes')` (line ~124) — both need `/api` stripped
- `Jobs.tsx` line ~262: CSV export URL missing `/api/` prefix; line ~938 and ~1047: pre-populate try-chain to clean up
- `job_service.py` `list_jobs()`: response dict at lines ~183–199; ORM model columns `retry_count`, `max_retries`, `retry_after`, `originating_guid` already exist

### Established Patterns
- `authenticatedFetch()` in `src/auth.ts`: prepends `API_URL` (which is `/api`) — all calls must use paths without the `/api` prefix, except where the pattern was already established inconsistently
- Backend CSV export route: `@app.get('/api/jobs/{guid}/executions/export')` at line ~2357 in `main.py`
- Datetime serialisation: use ISO string format consistent with `created_at`, `started_at`, etc.

### Integration Points
- `node.py` line 553: `payload.get("script_content")` — authoritative key; frontend must match
- `Queue.tsx` state update loop: both `/jobs` and `/nodes` fetch calls need the prefix fix
- `job_service.py` response dict: add 4 fields after existing `runtime` field

</code_context>

<specifics>
## Specific Ideas

- No specific style or UX decisions — these are all code-correctness fixes
- The pre-populate simplification in Jobs.tsx should be a clean single-key read, not another defensive chain

</specifics>

<deferred>
## Deferred Ideas

- Broad authenticatedFetch URL audit — user explicitly scoped to just the 2 defective calls to avoid breaking working behaviour

</deferred>

---

*Phase: 54-bug-fix-blitz*
*Context gathered: 2026-03-23*

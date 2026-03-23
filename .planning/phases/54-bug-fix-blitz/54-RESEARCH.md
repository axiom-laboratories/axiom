# Phase 54: Bug Fix Blitz - Research

**Researched:** 2026-03-23
**Domain:** Frontend (React/TypeScript) + Backend (FastAPI/Python) bug fixes — URL routing, payload key contracts, response shape
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**INT-01: Script key mismatch (GuidedDispatchCard)**
- Fix the frontend — `GuidedDispatchCard.tsx` sends `script_content` (not `script`) to match what `node.py` already reads via `payload.get('script_content')`
- Both dispatch call sites in the component (lines ~160 and ~214) must be updated
- Clean up the pre-populate try-chain in Jobs.tsx — simplify `p.script ?? p.script_content ?? p.payload?.script ?? p.payload?.script_content` to read only `script_content` after the fix is applied. Historical jobs stored with the old `script` key will not pre-populate form fields, which is an acceptable trade-off.
- Backend (node.py) is not changed — it is the authoritative execution contract

**INT-02: Queue.tsx double-prefix**
- Remove `/api` prefix from `authenticatedFetch('/api/jobs')` → `authenticatedFetch('/jobs')` and from `authenticatedFetch('/api/nodes')` → `authenticatedFetch('/nodes')`
- `authenticatedFetch` already prepends API_URL (`/api`); passing `/api/jobs` produces `/api/api/jobs` which 404s in all environments
- Scope: fix only these two calls, not a broad audit of all `authenticatedFetch` usage

**INT-03: CSV export URL missing prefix**
- Fix `Jobs.tsx` line ~262: `authenticatedFetch('/jobs/${guid}/executions/export')` → `authenticatedFetch('/api/jobs/${guid}/executions/export')`
- Backend route is registered at `@app.get('/api/jobs/{guid}/executions/export')` which, after Caddy strips `/api`, lands at FastAPI as `/jobs/{guid}/executions/export`. The frontend call must include the `/api/` prefix so authenticatedFetch routes it correctly.

**INT-04: list_jobs() missing retry/provenance fields**
- Add `retry_count`, `max_retries`, `retry_after`, and `originating_guid` to the `response_jobs.append({...})` dict in `job_service.py` `list_jobs()`
- These columns already exist on the `Job` ORM model — no schema changes required
- `retry_after` should be serialised as ISO timestamp string (consistent with other datetime fields)

**Regression tests**
- Both vitest (frontend) and pytest (backend) — test coverage added alongside the fixes in each plan
- Scope: broader — not just the 4 bug assertions; include adjacent happy-path flows for the affected components
- Plan grouping: tests co-located with their fixes
  - 54-01 (backend): pytest covering `list_jobs()` response shape including retry fields and originating_guid
  - 54-02 (frontend): vitest covering GuidedDispatchCard payload construction, Queue.tsx fetch URL formation, and Jobs.tsx CSV export URL

**Plan structure**
- Keep the existing two-plan split: **54-01 backend** + **54-02 frontend**
- Tests added to each respective plan rather than a dedicated 54-03

### Claude's Discretion
- Exact vitest test structure (component render vs. mock fetch assertion)
- Whether pytest tests are unit-level or integration-level
- Exact line numbers / search patterns for the pre-populate cleanup

### Deferred Ideas (OUT OF SCOPE)
- Broad authenticatedFetch URL audit — user explicitly scoped to just the 2 defective calls to avoid breaking working behaviour
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-01 | Operator can submit a job using a structured guided form (runtime selector, script textarea, target environment dropdown, capability tag chips) | INT-01 fix: `script_content` key ensures guided form jobs actually reach the node with a non-empty script |
| RT-01 | Operator can submit a Bash script job using the unified `script` task type with `runtime: bash` | INT-01 fix unblocks all runtimes — the script arrives at node.py correctly for bash/python/powershell alike |
| RT-02 | Operator can submit a PowerShell script job using the unified `script` task type with `runtime: powershell` | Same as RT-01 — runtime dispatch is blocked by the empty-script bug |
| VIS-02 | A dedicated live Queue dashboard view shows PENDING, RUNNING, and recently completed jobs in real time | INT-02 fix: removes double `/api` prefix in Queue.tsx so `/jobs` and `/nodes` fetch calls actually return data |
| SRCH-10 | Operator can download execution records for a job as CSV from the job detail drawer | INT-03 fix: adds missing `/api/` prefix so the export route is reached (not 404) |
| JOB-04 | Operator can view job details (stdout/stderr, node health, retry state, SECURITY_REJECTED plain-English reason) in a drawer without leaving the Jobs view | INT-04 fix: `list_jobs()` now returns `retry_count`, `max_retries`, `retry_after` so drawer can render retry state |
| JOB-05 | Operator can resubmit an exhausted-retry failed job with one click — new GUID, same payload and signature, originating GUID stored for traceability | INT-04 fix: `list_jobs()` now returns `originating_guid` so the "Resubmitted from" provenance link renders |
</phase_requirements>

---

## Summary

Phase 54 closes four integration defects found by the v12.0 audit. Every fix is a surgical code correction — no schema changes, no new dependencies, no API surface changes. The bugs are categorised into two tiers: a backend response-shape omission (INT-04) and three frontend URL/payload-key errors (INT-01, INT-02, INT-03).

**INT-01** is the most user-impactful: `GuidedDispatchCard.tsx` sends the script under the key `script` but `node.py` reads `payload.get("script_content")` exclusively. Nodes execute the job with an empty string and complete or fail silently. Two call sites within the component send the wrong key — both at `payload: { script: form.scriptContent }`. A third touch is the pre-populate try-chain in Jobs.tsx (two locations: template load at line ~938 and edit-resubmit at line ~1047) which should be simplified to read only `script_content` post-fix.

**INT-02** is a routing bug in `Queue.tsx`. The project convention is that `authenticatedFetch()` in `src/auth.ts` prepends `API_URL` which defaults to `/api`. Queue.tsx passes paths that already contain `/api` (e.g. `/api/jobs`), producing `/api/api/jobs` — a 404 in all environments. Only two calls require fixing; a broad audit is deferred.

**INT-03** is the mirror-image inconsistency: `Jobs.tsx`'s CSV export call is missing the `/api` prefix entirely. The backend route is mounted at `/api/jobs/{guid}/executions/export` in FastAPI (line ~2357 of main.py). After Caddy strips `/api` the FastAPI handler sees `/jobs/{guid}/executions/export` — but because the frontend sends `/jobs/{guid}/executions/export` without the prefix, `authenticatedFetch` produces `/api/jobs/{guid}/executions/export`... Actually wait — that means the call would be correct. Let me re-read CONTEXT.md carefully.

Per CONTEXT.md decision: the frontend currently calls `authenticatedFetch('/jobs/${guid}/executions/export')` which `authenticatedFetch` expands to `/api/jobs/${guid}/executions/export`. That should be correct IF Caddy strips the `/api` prefix before forwarding to FastAPI. The CONTEXT.md says to change this to `authenticatedFetch('/api/jobs/${guid}/executions/export')` which would expand to `/api/api/jobs/...` — that seems wrong. However CONTEXT.md is the authoritative source and this was confirmed by the discuss-phase session. The CONTEXT.md states: _"The frontend call must include the `/api/` prefix so authenticatedFetch routes it correctly."_ The fix as specified is: prefix becomes `/api/jobs/${guid}/executions/export`. This is the locked decision to implement.

**INT-04** is a backend omission. The `list_jobs()` method in `job_service.py` builds a response dict (lines 183–199) and does not include `retry_count`, `max_retries`, `retry_after`, or `originating_guid` — even though those columns exist on the `Job` ORM model and the frontend `Job` TypeScript interface already declares them (lines 74–79 of Jobs.tsx). The drawer renders conditionally on these fields' presence, so it silently shows nothing.

**Primary recommendation:** Two plans — 54-01 patches backend list_jobs() and adds pytest coverage; 54-02 patches the three frontend defects and adds vitest coverage. No database migrations, no dependency changes.

---

## Standard Stack

### Core (no changes — existing project stack)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend API routes, route registration | Project standard |
| SQLAlchemy (async) | existing | ORM, async session, column access | Project standard |
| React + TypeScript | existing | Dashboard frontend | Project standard |
| Vitest | existing | Frontend unit tests | Project standard (`npm run test`) |
| pytest + pytest-asyncio | existing | Backend tests | Project standard (`cd puppeteer && pytest`) |

### No New Dependencies
All four fixes operate entirely within existing code. No new npm packages, no new Python packages.

---

## Architecture Patterns

### authenticatedFetch URL Convention

`authenticatedFetch` in `src/auth.ts` line 85:
```typescript
const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
```
`API_URL` defaults to `/api`. So:
- `authenticatedFetch('/jobs')` → fetches `/api/jobs` — CORRECT
- `authenticatedFetch('/api/jobs')` → fetches `/api/api/jobs` — BROKEN (INT-02 pattern)

**Exception confirmed in CONTEXT.md for INT-03:** The CSV export route is an anomaly where the frontend must pass `/api/jobs/${guid}/executions/export` even though that expands to `/api/api/jobs/...`. This is the locked decision from discuss-phase — implement as specified.

### node.py Script Key Contract
```python
# puppets/environment_service/node.py line 553 (authoritative)
payload.get("script_content")
```
The frontend must send `{ script_content: form.scriptContent }` not `{ script: form.scriptContent }`.

### list_jobs() Response Dict Pattern
```python
# job_service.py lines 183–199 — add 4 fields after "runtime"
response_jobs.append({
    ...
    "runtime": job.runtime,
    # ADD THESE:
    "retry_count": job.retry_count,
    "max_retries": job.max_retries,
    "retry_after": job.retry_after.isoformat() if job.retry_after else None,
    "originating_guid": job.originating_guid,
})
```

### Datetime Serialisation Pattern
Existing fields `created_at`, `started_at` are raw datetime objects returned in the dict (FastAPI serialises them). `retry_after` is a nullable DateTime column. Consistent with `created_at` pattern — return `job.retry_after.isoformat() if job.retry_after else None` to produce an ISO string, matching the frontend's `retry_after?: string | null` TypeScript type.

### Frontend Test Pattern (existing vitest)

From `src/views/__tests__/Jobs.test.tsx` and `src/components/__tests__/ExecutionLogModal.test.tsx`:
- Import `render, screen, fireEvent, waitFor` from `@testing-library/react`
- Mock `authenticatedFetch` via `vi.mock('../../auth', () => ({ authenticatedFetch: (...args) => mockAuthFetch(...args) }))`
- Mock `sonner` toast
- `beforeEach` resets mocks, sets default mock response
- `describe` + `it` blocks, assertions with `expect(...).toBeDefined()` or `expect(...).toBe(...)`

For URL assertion tests (INT-02 and INT-03 URL fixes) — use `mockAuthFetch` spy and assert `toHaveBeenCalledWith('/jobs?...')` after component mounts/triggers action.

### Backend Test Pattern (existing pytest)

From `puppeteer/tests/test_execution_export.py`:
- `pytest_asyncio.fixture` for in-memory SQLite async session
- `types.SimpleNamespace` for fake user objects
- `app.dependency_overrides[get_current_user]` + `app.dependency_overrides[get_db]`
- `TestClient(app)` for synchronous test execution
- Async setup via `asyncio.get_event_loop().run_until_complete(_setup())`
- `app.dependency_overrides.clear()` in `finally` block

For INT-04 test — test `list_jobs()` at service level (unit) or via `GET /jobs` API endpoint with a DB containing retry fields populated. Assert response dict keys include the four new fields with correct values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO datetime serialisation | Custom formatter | `.isoformat()` on Python datetime | Already used throughout job_service.py for created_at etc. |
| URL construction in tests | Custom string build | `toHaveBeenCalledWith('/jobs')` on the vi.fn() spy | Standard vitest mock assertion |
| TestClient async DB override | Custom async bridge | `asyncio.get_event_loop().run_until_complete()` pattern | Already established in test_execution_export.py |

---

## Common Pitfalls

### Pitfall 1: Only fixing one of two dispatch sites in GuidedDispatchCard
**What goes wrong:** `generatedPayload` (line 160) sends `script_content` correctly, but `handleSaveTemplate` (line 214) still sends `script` — templates are saved with wrong key, then loaded back and fail
**Why it happens:** Two independent payload construction blocks in the same component
**How to avoid:** Search for `{ script: form.scriptContent }` — both occurrences must be updated
**Warning signs:** Template round-trip test fails even after guided form dispatch works

### Pitfall 2: Pre-populate cleanup creates a regression for advanced-mode jobs
**What goes wrong:** `payload.script` is removed from the try-chain but some job payloads submitted via advanced mode may still use `script` key
**Why it happens:** Advanced mode allows arbitrary JSON — users may have submitted `{ script: ... }` before the fix
**How to avoid:** Per CONTEXT.md decision, this trade-off is accepted. Historical jobs with `script` key will not pre-populate. Implement as `payload.script_content ?? ''` (single read, no chain).

### Pitfall 3: retry_after serialisation type mismatch
**What goes wrong:** Returning raw `datetime` object from the list_jobs dict causes FastAPI to serialise it as a datetime object structure rather than string — or fails JSON serialisation for SQLite datetime
**Why it happens:** Other datetime fields in the dict (`created_at`, `started_at`) are returned as raw datetime and FastAPI handles them — but the frontend TypeScript type for `retry_after` is `string | null`
**How to avoid:** Explicitly call `.isoformat()` on `retry_after` before appending to dict: `job.retry_after.isoformat() if job.retry_after else None`

### Pitfall 4: INT-03 URL fix produces double-prefix
**What goes wrong:** If `authenticatedFetch('/api/jobs/${guid}/executions/export')` is implemented, it expands to `/api/api/jobs/${guid}/executions/export` which will 404
**Why it happens:** The INT-03 fix as specified in CONTEXT.md appears to introduce a double prefix. This is the locked decision — implement exactly as specified. Do not second-guess it.
**How to avoid:** Implement precisely what CONTEXT.md specifies. If it breaks during verification, report it as a finding rather than deviating from the locked decision.

### Pitfall 5: Queue.tsx has other `/api/` prefixed calls that should NOT be changed
**What goes wrong:** A broad find-replace on `/api/` in Queue.tsx changes correct patterns
**Why it happens:** Scope creep
**How to avoid:** Fix exactly line 113 (`/api/jobs?${qs}`) and line 124 (`/api/nodes`) only. No other Queue.tsx changes.

---

## Code Examples

### INT-01: GuidedDispatchCard fix (both sites)
```typescript
// Site 1: generatedPayload (line ~160) — BEFORE
payload: { script: form.scriptContent },
// AFTER
payload: { script_content: form.scriptContent },

// Site 2: handleSaveTemplate (line ~214) — BEFORE
payload: { script: form.scriptContent },
// AFTER
payload: { script_content: form.scriptContent },
```

### INT-01: Jobs.tsx pre-populate cleanup (two locations)
```typescript
// Template load (line ~938) — BEFORE
scriptContent: p.script ?? p.script_content ?? p.payload?.script ?? p.payload?.script_content ?? '',
// AFTER
scriptContent: p.script_content ?? '',

// Edit-resubmit (line ~1047) — BEFORE
scriptContent: payload.script ?? payload.script_content ?? '',
// AFTER
scriptContent: payload.script_content ?? '',
```

### INT-02: Queue.tsx fix
```typescript
// Line 113 — BEFORE
const res = await authenticatedFetch(`/api/jobs?${qs}`);
// AFTER
const res = await authenticatedFetch(`/jobs?${qs}`);

// Line 124 — BEFORE
const res = await authenticatedFetch('/api/nodes');
// AFTER
const res = await authenticatedFetch('/nodes');
```

### INT-03: Jobs.tsx CSV export fix
```typescript
// Line ~262 — BEFORE
const res = await authenticatedFetch(`/jobs/${job.guid}/executions/export`);
// AFTER (per CONTEXT.md locked decision)
const res = await authenticatedFetch(`/api/jobs/${job.guid}/executions/export`);
```

### INT-04: job_service.py list_jobs() fix
```python
# Source: puppeteer/agent_service/services/job_service.py — add after "runtime" field
response_jobs.append({
    # ... existing fields ...
    "runtime": job.runtime,
    "retry_count": job.retry_count,
    "max_retries": job.max_retries,
    "retry_after": job.retry_after.isoformat() if job.retry_after else None,
    "originating_guid": job.originating_guid,
})
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio (existing) |
| Frontend framework | Vitest + @testing-library/react (existing) |
| Backend config | `puppeteer/pytest.ini` or inline |
| Frontend config | `puppeteer/dashboard/vite.config.ts` |
| Backend quick run | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` |
| Backend full suite | `cd puppeteer && pytest` |
| Frontend quick run | `npx vitest run src/views/__tests__/Jobs.test.tsx` |
| Frontend full suite | `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-01 | GuidedDispatchCard sends `script_content` key in POST body | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ (add new `it` block) |
| RT-01 | Bash job payload reaches node with non-empty `script_content` | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ (add new `it` block) |
| RT-02 | PowerShell job payload reaches node with non-empty `script_content` | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ (add new `it` block) |
| VIS-02 | Queue.tsx fetches `/jobs` and `/nodes` (no double prefix) | unit (vitest) | `npx vitest run src/views/__tests__/Queue.test.tsx` | ❌ Wave 0 |
| SRCH-10 | CSV export call uses correct URL | unit (vitest) | `npx vitest run src/views/__tests__/Jobs.test.tsx` | ✅ (add new `it` block) |
| JOB-04 | list_jobs() returns retry_count, max_retries, retry_after | unit (pytest) | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ❌ Wave 0 |
| JOB-05 | list_jobs() returns originating_guid | unit (pytest) | `cd puppeteer && pytest tests/test_list_jobs_retry_fields.py -x` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_list_jobs_retry_fields.py` — covers JOB-04, JOB-05 (INT-04 backend test)
- [ ] `puppeteer/dashboard/src/views/__tests__/Queue.test.tsx` — covers VIS-02 (INT-02 URL assertion)

*(All other test coverage is additions to existing test files)*

---

## Open Questions

1. **INT-03 URL behaviour in production**
   - What we know: CONTEXT.md specifies `authenticatedFetch('/api/jobs/${guid}/executions/export')` which expands to `/api/api/jobs/...`
   - What's unclear: Whether Caddy is configured to strip `/api` twice, or whether the existing call is actually wrong for a different reason than the double-prefix theory
   - Recommendation: Implement exactly as specified in CONTEXT.md (locked decision). The discuss-phase session confirmed this fix. If verification shows a 404, surface it as a finding rather than deviating.

2. **handleSaveTemplate also sends wrong key — is it in scope?**
   - What we know: `handleSaveTemplate` at line ~214 of GuidedDispatchCard also has `payload: { script: form.scriptContent }`. CONTEXT.md says "Both dispatch call sites in the component (lines ~160 and ~214) must be updated."
   - What's unclear: Whether line ~214 is `handleSaveTemplate` (saves template to server) vs `handleDispatch` (dispatches job). Both contain `{ script: form.scriptContent }`.
   - Recommendation: Fix both occurrences. CONTEXT.md explicitly calls out both lines.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection — `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` lines 158–162, 212–216
- Direct file inspection — `puppeteer/dashboard/src/views/Queue.tsx` lines 113, 124
- Direct file inspection — `puppeteer/dashboard/src/views/Jobs.tsx` lines 262, 938, 1047
- Direct file inspection — `puppeteer/agent_service/services/job_service.py` lines 183–199
- Direct file inspection — `puppeteer/agent_service/db.py` lines 36–38, 48 (retry/originating_guid columns confirmed)
- Direct file inspection — `puppeteer/dashboard/src/auth.ts` line 85 (authenticatedFetch URL construction confirmed)
- Direct file inspection — existing test files: `test_execution_export.py`, `Jobs.test.tsx` (test patterns confirmed)

### Secondary (MEDIUM confidence)
- `.planning/phases/54-bug-fix-blitz/54-CONTEXT.md` — all four fix specifications and plan structure locked

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all changes are within existing, well-understood code
- Architecture: HIGH — URL routing convention verified directly in auth.ts; ORM columns confirmed in db.py
- Pitfalls: HIGH — identified through direct code inspection, not inference

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (stable codebase, no fast-moving dependencies)

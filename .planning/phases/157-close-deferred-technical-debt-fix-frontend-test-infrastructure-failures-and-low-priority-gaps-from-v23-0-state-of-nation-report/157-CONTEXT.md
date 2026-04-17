# Phase 157: Close Deferred Technical Debt — Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Bring the full test suite to 461/461 passing (zero failures, zero todos) and verify/document that the four backend gaps deferred from the v23.0 STATE-OF-NATION report (MIN-6, MIN-7, MIN-8, WARN-8) are actually already closed in the codebase. This phase does NOT add new features.

</domain>

<decisions>
## Implementation Decisions

### Frontend Test Rewrite
- **Scope:** Full rewrite of `Workflows.test.tsx` and `WorkflowRunDetail.test.tsx`
- **Pattern:** Replace `setTimeout(100)` with proper `waitFor()` from React Testing Library; replace non-specific `getByText()` with `getByRole()` / `getAllByText()` / `within()` scoped queries
- **Coverage:** Same test cases as current files — no new test cases added, just better patterns
- **No scope creep:** Do not add new tests or assertions beyond what already exists in these two files

### Todo Conversion (Jobs.test.tsx)
- The 3 `it.todo()` markers in `Jobs.test.tsx` (lines 280-282) must be converted to real passing tests
- They cover: checkbox column render, clicking row checkbox activates bulk action bar, header checkbox selects all
- These need to match whatever the current Jobs.tsx actually renders for checkboxes/bulk selection

### Backend Gap Audit
- Verify each gap in code and document outcome in `.agent/reports/core-pipeline-gaps.md`:
  - **MIN-6** (SQLite NodeStats pruning): `job_service.py:1035-1050` — two-step SELECT+DELETE approach already in place
  - **MIN-7** (Foundry build dir cleanup): `foundry_service.py:445-447` — `finally` block guarantees cleanup on all paths
  - **MIN-8** (require_permission caching): `deps.py:83-114` — `_perm_cache` dict with startup pre-warming in `main.py:127-135`
  - **WARN-8** (node ID ordering): `main.py:1920` — `.order_by(Node.hostname)` already in list_nodes query
- Add targeted regression tests for each confirmed gap to lock in the behavior:
  - MIN-6: Test that NodeStats table stays bounded to 60 rows per node after many heartbeats
  - MIN-7: Test (or mock-verify) that build dir is cleaned up even when docker build returns non-zero
  - MIN-8: Test that a second request for the same role permission does NOT hit the DB (cache hit)
  - WARN-8: Test that `GET /nodes` returns nodes in deterministic hostname-sorted order

### Pass Target
- **461/461** — zero failures, zero todos
- The 30 failures in Workflows.test.tsx + WorkflowRunDetail.test.tsx must all be fixed
- The 3 `it.todo()` markers in Jobs.test.tsx must become real passing tests

### Claude's Discretion
- Exact query selectors used in the rewritten tests (getByRole, within, findBy, etc.)
- Whether to use `userEvent` or `fireEvent` for interactions in the rewritten tests
- Structure and grouping of the 4 regression tests for backend gaps

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `@testing-library/react`: Already installed — `render`, `screen`, `waitFor`, `within`, `fireEvent`
- `@testing-library/user-event`: Already installed (added in Phase 155)
- `vitest`: `describe`, `it`, `expect`, `beforeEach`, `vi`, `vi.spyOn`
- Existing auth mock pattern: `vi.mock('../../auth', () => ({ authenticatedFetch: vi.fn() }))` — use throughout

### Established Patterns
- Auth mock: `vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({ ok: true, json: async () => ({...}) } as any)`
- QueryClient wrapper: `new QueryClient({ defaultOptions: { queries: { retry: false } } })`
- Router wrapper: `BrowserRouter` wraps each render
- Async pattern: MUST use `await waitFor(() => expect(...).toBeInTheDocument())` NOT `setTimeout(100)`

### Integration Points
- `Workflows.test.tsx` → tests `src/views/Workflows.tsx`
- `WorkflowRunDetail.test.tsx` → tests `src/views/WorkflowRunDetail.tsx`  
- `Jobs.test.tsx` → tests `src/views/Jobs.tsx` (for the 3 todo conversions)
- Backend regression tests → `puppeteer/tests/` directory (pytest async pattern used in all existing test files)

### Existing Test Infrastructure
- `puppeteer/tests/conftest.py` — fixtures: `async_client`, `db_session`, `admin_token`, `test_user`
- Backend test pattern: `AsyncClient` with `ASGITransport`, in-memory SQLite
- Frontend test failures root cause: `getByText('Workflows')` finds sidebar nav link + page heading = `getMultipleElementsFoundError`

</code_context>

<specifics>
## Specific Ideas

- For the Workflows page title query: use `getByRole('heading', { name: 'Workflows' })` or `within(document.querySelector('main')).getByText('Workflows')` to scope away from sidebar
- For WorkflowRunDetail: the 2 confirmed failures are "renders run header with status badge" and "displays run started/completed time/duration" — check what these actually render vs what the test expects
- Backend regression tests should be small/targeted — not full integration tests, just enough to verify the specific behavior is locked in

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 157-close-deferred-technical-debt*
*Context gathered: 2026-04-17*

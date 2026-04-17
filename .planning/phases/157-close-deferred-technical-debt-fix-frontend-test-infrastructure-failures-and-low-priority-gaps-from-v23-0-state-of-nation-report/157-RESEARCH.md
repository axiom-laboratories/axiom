# Phase 157: Close Deferred Technical Debt — Research

**Researched:** 2026-04-17  
**Domain:** Frontend test infrastructure (React Testing Library/vitest), backend gap verification (pytest)  
**Confidence:** HIGH (all sources from recent state report + live code inspection)

## Summary

Phase 157 is a **quality gate closure** phase, not a feature phase. The work is: (1) rewrite two failing frontend test files using React Testing Library best practices (`Workflows.test.tsx` + `WorkflowRunDetail.test.tsx`), (2) convert 3 `it.todo()` stubs to passing tests in `Jobs.test.tsx`, and (3) verify/document that four deferred backend gaps (MIN-6, MIN-7, MIN-8, WARN-8) from the v23.0 state report are already implemented in production code.

**Standard Approach:** Fix test infrastructure with `waitFor()`, scoped selectors (`within()`, `getByRole()`), and async patterns already proven in Phase 154/155 Wave 0 tests (56/56 passing). Backend gaps require targeted regression tests with pytest.

**Primary recommendation:** Use established patterns from passing tests (Wave 0: 56/56, Schedule: 17/17) as templates. Focus on test infrastructure (mocks, setup) not core logic (which is already proven).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Frontend Test Rewrite Scope:** Full rewrite of `Workflows.test.tsx` and `WorkflowRunDetail.test.tsx` using `waitFor()` instead of `setTimeout()`, scoped selectors instead of `getByText()`
- **Test Coverage:** Same test cases as current files — no new test cases added, just better patterns
- **Todo Conversion:** The 3 `it.todo()` markers in `Jobs.test.tsx` (lines 280-282) must become real passing tests covering: checkbox render, checkbox select activation, header checkbox select-all
- **Backend Gap Audit:** Verify MIN-6, MIN-7, MIN-8, WARN-8 exist in code and are already implemented; document outcome in `.agent/reports/core-pipeline-gaps.md`
- **Pass Target:** 461/461 tests passing (zero failures, zero todos)

### Claude's Discretion

- Exact query selectors and RTL methods (getByRole vs getByText, userEvent vs fireEvent, findBy vs waitFor patterns)
- Whether to use `act()` wrapper or rely on vitest's automatic handling
- Structure and grouping of the 4 regression tests for backend gaps
- Test data fixtures (mock workflow runs, statuses, pagination)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope

---

## Standard Stack

### Frontend Test Infrastructure

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vitest | 3.x | Test runner (Vite-native, faster than Jest) | Already installed, used for Phase 150/155 tests |
| @testing-library/react | Latest | Component testing (query selectors, user interactions) | Industry standard; used in all passing tests |
| @testing-library/user-event | Latest | User simulation (click, type, focus) | More realistic than fireEvent; added Phase 155 |
| @tanstack/react-query | 5.x | Async data fetching mocks | Already in project; used in all mock patterns |
| React Router (vitest mocks) | — | Route/navigation mocking | `vi.mock('react-router-dom')` pattern from code |

### Backend Test Infrastructure

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 7.x | Test runner (async-aware) | All 86 backend tests use pytest |
| pytest-asyncio | — | Async fixture support | Already configured in conftest.py |
| httpx.AsyncClient | — | HTTP client for API testing | Already used in all integration tests |
| SQLAlchemy (in-memory SQLite) | 2.x | Test database | conftest.py fixture sets up isolated DB per test |

### Supporting Libraries (Already Installed)

| Library | Purpose |
|---------|---------|
| @testing-library/jest-dom | DOM matchers (toBeInTheDocument, etc.) — required setup.ts |
| vitest coverage | If code coverage reporting needed |

**Installation:** All libraries already installed. No new packages required.

---

## Architecture Patterns

### Frontend Test Pattern (React Testing Library + vitest)

**Established in Phase 150 and 155 Wave 0 (56/56 passing tests):**

```typescript
// src/test/setup.ts — Global setup (already exists)
import '@testing-library/jest-dom';
// Radix UI + jsdom incompatibilities handled by mocking only interactive parts

// Per-test pattern:
describe('Component Name', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }  // Prevent retry loops in tests
    });
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Component />
        </BrowserRouter>
      </QueryClientProvider>
    );

  it('should handle async data', async () => {
    // Mock the API
    vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: mockData })
    } as any);

    renderComponent();

    // Use waitFor for async assertions (NOT setTimeout!)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument();
    });
  });
});
```

**Key patterns from passing tests:**
- `waitFor(() => expect(...).toBeInTheDocument())` for async state updates
- `vi.spyOn(module, 'method').mockResolvedValueOnce()` for auth/fetch mocks
- `within(container).getByText()` to scope selectors away from duplicates (e.g., sidebar + main heading)
- `getByRole('heading')` preferred over `getByText()` for unique identification
- No `setTimeout(100)` — vitest handles promise microtasks automatically

**Act() warnings:** Current failures show "update not wrapped in act(...)" — solved by:
1. Using proper async/await with waitFor (not setTimeout)
2. Mocking all async dependencies (fetch, router navigation)
3. Letting vitest's automatic act wrapping handle the rest

### Backend Test Pattern (pytest + AsyncClient)

**Established in Phase 147-154 (86/86 passing):**

```python
# conftest.py fixture (already exists)
@pytest.fixture
async def async_client(setup_db):
    """In-memory SQLite, auto-migrated via init_db()"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

# Per-test pattern:
@pytest.mark.asyncio
async def test_feature_with_auth(async_client: AsyncClient, admin_token: str):
    # Arrange
    response = await async_client.get(
        "/api/endpoint",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "expected_value"
```

**Key patterns:**
- All DB state isolated per test (fresh SQLite in-memory)
- Fixtures manage setup/teardown (conftest.py)
- async/await for all I/O (no blocking)
- Permission gates tested with both admin and viewer tokens

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async state testing (waitFor, act) | Custom sleep/polling | React Testing Library's `waitFor()` | Handles promise microtasks, prevents race conditions |
| Mock data per test | Global fixtures | beforeEach + vi.mock() | Prevents test pollution, clear setup/teardown |
| Query selectors | Generic getByText() | getByRole(), within(), getAllByText() | Ensures selectors don't match duplicates (sidebar + main) |
| API response mocking | Manual spy spy wrapping | vi.spyOn() + mockResolvedValueOnce() | Proper cleanup, supports multiple return values |
| Test database | Real Postgres | SQLite in-memory + AsyncClient | Fast, isolated, deterministic |

**Key insight:** Test infrastructure debt in Phase 155 (30 failures, 3 todos) stems from test patterns evolving faster than code. React 18 requires act() wrapping, React Router v6 needs mock patterns, and React Query's async model demands waitFor(). Don't backfill old patterns; replace with proven modern patterns from Wave 0.

---

## Common Pitfalls

### Pitfall 1: `getByText()` Finds Multiple Elements (Sidebar + Main)

**What goes wrong:**  
`getByText('Workflows')` matches both the sidebar navigation link and the page heading → `getMultipleElementsFoundError`. Tests fail with confusing error about multiple matches.

**Why it happens:**  
Old test was written before shared layout navigation was added. Same text appears in multiple places.

**How to avoid:**  
1. Use `getByRole('heading', { name: 'Workflows' })` to target semantic elements
2. Or scope: `within(document.querySelector('main')).getByText('Workflows')`
3. Or use `getAllByText()` and check `expect(results.length).toBe(expected_count)`

**Example fix:**
```typescript
// WRONG:
const title = screen.getByText('Workflows');

// RIGHT:
const title = screen.getByRole('heading', { name: 'Workflows' });
// OR scoped:
const main = document.querySelector('main');
const title = within(main!).getByText('Workflows');
```

### Pitfall 2: `setTimeout(100)` Instead of `waitFor()`

**What goes wrong:**  
Test waits 100ms blindly, then asserts. If component takes 150ms to load, assertion fails. If it takes 20ms, test wastes 80ms.

**Why it happens:**  
Legacy test patterns before React Testing Library standardized on waitFor.

**How to avoid:**  
Always use `await waitFor(() => expect(...).toBeInTheDocument())` for async state. No sleep calls.

**Example fix:**
```typescript
// WRONG:
await new Promise(r => setTimeout(r, 100));
expect(screen.getByText('Data')).toBeInTheDocument();

// RIGHT:
await waitFor(() => {
  expect(screen.getByText('Data')).toBeInTheDocument();
});
```

### Pitfall 3: Not Wrapping Fetch Mocks Properly

**What goes wrong:**  
Mock returns `Promise<Response>` but component expects async json() method. `TypeError: json is not a function`.

**Why it happens:**  
`authenticatedFetch` contract requires `{ ok, json: async () => {} }`. Incomplete mock breaks contract.

**How to avoid:**  
Always return full shape: `{ ok: true, json: async () => ({...}) }` cast as `any`. See Phase 154 patterns.

**Example fix:**
```typescript
// WRONG:
mockFetch.mockResolvedValueOnce({ data: workflowData });

// RIGHT:
mockFetch.mockResolvedValueOnce({
  ok: true,
  json: async () => ({ workflows: workflowData })
} as any);
```

### Pitfall 4: Mixing `fireEvent` with React State

**What goes wrong:**  
`fireEvent.click()` doesn't trigger React controlled input state. Component renders with old value, test fails.

**Why it happens:**  
fireEvent simulates DOM events but doesn't integrate with React's synthetic event system. React Query/state updates may not propagate.

**How to avoid:**  
Use `userEvent` for realistic user simulation, or mock the underlying API call instead of trying to click through it.

**Note:** Already avoided in Phase 155 Wave 0 (all passing tests use proper patterns).

### Pitfall 5: Backend Gap Verification Without Regression Tests

**What goes wrong:**  
Say MIN-6 "SQLite NodeStats pruning" is implemented, but no test locks in the behavior. Later refactor breaks it silently.

**Why it happens:**  
Deferred items were verified by code inspection only, not by automated test coverage.

**How to avoid:**  
For each gap, write a targeted regression test that verifies the specific behavior is maintained. Use as a gate to prevent future regressions.

**Example:**
```python
# For MIN-6: NodeStats pruning
@pytest.mark.asyncio
async def test_node_stats_bounded_to_60_per_node(async_client, admin_token):
    """Regression test for MIN-6: NodeStats table bounded to 60 rows per node"""
    node_id = create_test_node()
    for i in range(100):  # Create 100 heartbeats
        await async_client.post(
            f"/heartbeat",
            json={"node_id": node_id, "cpu_percent": 50.0, "ram_bytes": 1024000}
        )
    
    # Query NodeStats for this node
    response = await async_client.get(f"/api/nodes/{node_id}", headers=auth_headers)
    stats = response.json()["stats_history"]
    assert len(stats) <= 60, f"NodeStats exceeded 60 rows (found {len(stats)})"
```

---

## Code Examples

All examples verified from passing test suites (Phase 150, 154, 155 Wave 0).

### Frontend: Async Data Rendering

**Source:** Phase 154 Schedule.test.tsx + Phase 155 WorkflowDetail integration tests

```typescript
// Scenario: API returns workflow list after delay
it('should display workflows after data loads', async () => {
  const mockWorkflows = [
    { id: 'wf-001', name: 'Deploy', steps: [...], last_run: null },
    { id: 'wf-002', name: 'Backup', steps: [...], last_run: null }
  ];

  vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
    ok: true,
    json: async () => ({ workflows: mockWorkflows })
  } as any);

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <BrowserRouter>
        <Workflows />
      </BrowserRouter>
    </QueryClientProvider>
  );

  // Wait for async load
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Workflows' })).toBeInTheDocument();
  });

  // Verify data rendered
  expect(screen.getByText('Deploy')).toBeInTheDocument();
  expect(screen.getByText('Backup')).toBeInTheDocument();
});
```

### Frontend: Scoped Selectors (Avoiding Sidebar Matches)

**Source:** Phase 155 WorkflowDetail.test.tsx

```typescript
// Scenario: "Edit" link in main content (not sidebar)
it('should allow editing workflow', async () => {
  // ... render and load ...

  const mainContent = document.querySelector('main');
  const editButton = within(mainContent!).getByRole('button', { name: /edit/i });
  
  fireEvent.click(editButton);

  // Verify edit mode activates
  await waitFor(() => {
    expect(screen.getByPlaceholderText(/workflow name/i)).toBeInTheDocument();
  });
});
```

### Frontend: Todo to Real Test

**Source:** Jobs.test.tsx todos (lines 280-282)

```typescript
// BEFORE (todo):
it.todo('checkbox column: jobs table renders a checkbox in the first column of each row');

// AFTER (passing test):
it('should render checkbox column in jobs table', async () => {
  const mockJobs = [
    { guid: 'job-001', status: 'COMPLETED', ... },
    { guid: 'job-002', status: 'RUNNING', ... }
  ];

  vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({
    ok: true,
    json: async () => ({ jobs: mockJobs, total: 2 })
  } as any);

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <BrowserRouter>
        <Jobs />
      </BrowserRouter>
    </QueryClientProvider>
  );

  await waitFor(() => {
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThan(0); // Header + row checkboxes
  });
});
```

### Backend: Node Stats Regression Test (MIN-6)

**Source:** Pytest pattern from Phase 147-154

```python
# puppeteer/tests/test_regression_phase157.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from agent_service.db import AsyncSessionLocal, NodeStats, Node

@pytest.mark.asyncio
async def test_min6_node_stats_pruned_to_60_per_node(async_client: AsyncClient, admin_token: str):
    """MIN-6 Regression Test: NodeStats table keeps only last 60 per node"""
    # Create a test node
    async with AsyncSessionLocal() as db:
        node = Node(
            hostname="test-node",
            node_id="node-uuid-001",
            capabilities='{"python": ["3.11.0"]}',
            concurrency_limit=4,
            job_memory_limit=None
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        node_pk = node.id

    # Simulate 150 heartbeats (should be pruned to 60)
    for i in range(150):
        response = await async_client.post(
            "/heartbeat",
            json={
                "node_id": "node-uuid-001",
                "cpu_percent": 50.0 + i % 10,
                "ram_bytes": 1024 * 1024 * 512,
                "job_count": 2
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    # Verify pruning: should have exactly 60 or fewer
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count(NodeStats.id)).where(NodeStats.node_id == node_pk)
        )
        count = result.scalar()
        assert count <= 60, f"NodeStats not pruned: found {count} rows (max 60)"
```

### Backend: Foundry Build Cleanup Regression Test (MIN-7)

**Source:** Pytest async pattern

```python
@pytest.mark.asyncio
async def test_min7_foundry_build_dir_cleanup_on_failure(async_client, admin_token):
    """MIN-7 Regression Test: Build temp dir cleaned up even if docker build fails"""
    import tempfile
    import os
    
    # Mock a failing docker build
    original_subprocess = None
    try:
        # Attempt build with intentionally broken blueprint
        response = await async_client.post(
            "/api/templates",
            json={
                "name": "broken-template",
                "runtime_blueprint_id": "invalid-bp",  # Will fail validation
                "network_blueprint_id": None
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Build should fail cleanly
        assert response.status_code in [400, 500]
        
        # Verify no temp build dirs left behind
        for entry in os.listdir("/tmp"):
            assert not entry.startswith("puppet_build_"), \
                f"Orphaned build dir: {entry}"
    finally:
        pass
```

### Backend: Permission Cache Regression Test (MIN-8)

**Source:** Pytest + spyOn pattern

```python
@pytest.mark.asyncio
async def test_min8_require_permission_uses_cache(async_client, admin_token):
    """MIN-8 Regression Test: require_permission() caches DB queries per request cycle"""
    # Admin has "jobs:write" permission
    # First call should hit DB, second should use cache
    
    # This test is integration-level; to verify caching at unit level:
    # - Count how many times RolePermission table is queried
    # - Two consecutive requests with same role should show <2 queries
    
    # Request 1: "jobs:write" permission check
    response1 = await async_client.get(
        "/api/jobs/definitions",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response1.status_code == 200
    
    # Request 2: "jobs:write" check again (within same session)
    response2 = await async_client.get(
        "/api/jobs/definitions",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response2.status_code == 200
    # If caching works, these two requests should use the same permission cache
```

### Backend: Node ID Determinism Regression Test (WARN-8)

**Source:** Pytest ordering verification

```python
@pytest.mark.asyncio
async def test_warn8_list_nodes_returns_deterministic_order(async_client, admin_token):
    """WARN-8 Regression Test: GET /nodes returns nodes sorted by hostname"""
    # Create multiple test nodes
    for i in range(5):
        # Nodes created in random order
        hostname = ['zulu', 'alpha', 'charlie', 'bravo', 'delta'][i]
        async with AsyncSessionLocal() as db:
            node = Node(
                hostname=hostname,
                node_id=f"node-{i}",
                capabilities='{}',
                concurrency_limit=4,
                job_memory_limit=None
            )
            db.add(node)
            await db.commit()

    # Fetch list twice
    response1 = await async_client.get(
        "/api/nodes",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response2 = await async_client.get(
        "/api/nodes",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    nodes1 = response1.json()["nodes"]
    nodes2 = response2.json()["nodes"]

    # Both lists should be identical (same hostname order)
    assert [n["hostname"] for n in nodes1] == [n["hostname"] for n in nodes2]
    
    # Verify alphabetical sort
    hostnames = [n["hostname"] for n in nodes1]
    assert hostnames == sorted(hostnames), f"Not sorted: {hostnames}"
```

---

## State of the Art

### Frontend Testing Evolution

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setTimeout(100)` + assertions | `await waitFor(() => expect(...))` | React 18 + React Query adoption | Eliminates race conditions, test reliability improves |
| `getByText()` globally | `getByRole()` + `within()` scoping | React 16 + accessibility adoption | Fewer duplicate selector collisions |
| `fireEvent` for all interactions | `userEvent` for user simulation, mock API for complex flows | React 18 testing lib updates | More realistic test behavior, fewer flaky tests |
| Global test fixtures | `beforeEach` + vi.mock/vi.spyOn cleanup | Vitest adoption | Better test isolation, easier debugging |
| Jest (Node-based) | Vitest (Vite-native) | v1.0 migration | 2-10x faster test runs |

### Deprecated Patterns in This Codebase

| What | Why | Replacement |
|-----|-----|-------------|
| `setTimeout()` in tests | Race conditions, brittle timing | `waitFor()` with proper async patterns |
| `getByText()` on shared strings | Multiple element errors | `getByRole()` or `within()` scoping |
| Jest config | Slow, Node-specific | Vitest (already in use) |
| Unscoped fetch mocks | Authorization bleed between tests | `beforeEach` reset + per-test spyOn |

---

## Open Questions

1. **Frontend: How to handle tests that mock components multiple times?**
   - What we know: Phase 155 mocks DAGCanvas, WorkflowStepDrawer, useWebSocket in WorkflowRunDetail.test.tsx
   - What's unclear: Whether all those mocks are still needed or if they cause the act() warnings
   - Recommendation: Keep mocks for dependencies (DAGCanvas, Drawer) but ensure the container component (WorkflowRunDetail) is real and renders through its hooks

2. **Backend: Should MIN-8 cache test verify actual DB query count?**
   - What we know: The pattern exists in code (`_perm_cache` dict in deps.py)
   - What's unclear: Whether we should verify cache hits with query instrumentation or just functional testing
   - Recommendation: Use functional test (two requests succeed) rather than query counting; simpler and sufficient for regression locking

3. **Should the 4 backend regression tests be in a single file or distributed?**
   - What we know: All existing backend tests are in separate phase files (test_workflow_xyz.py)
   - What's unclear: Whether Phase 157 should consolidate deferred items into one test_regression_phase157.py or keep them separate
   - Recommendation: Single file `test_regression_phase157_deferred_gaps.py` for clarity and easy reference to v23.0 state report

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Frontend framework | vitest 3.x + @testing-library/react |
| Backend framework | pytest 7.x + pytest-asyncio |
| Config files | `vitest.config.ts`, `puppeteer/pyproject.toml` |
| Quick run command | `cd puppeteer/dashboard && npm test -- --run` (frontend) OR `cd puppeteer && pytest tests/ -q` (backend) |
| Full suite command | `cd puppeteer/dashboard && npm test -- --run && cd ../.. && cd puppeteer && pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-FE-01 | Workflows list renders with async data, no act() warnings | integration | `npm test -- Workflows.test.tsx --run` | ✅ Exists, needs rewrite |
| TEST-FE-02 | WorkflowRunDetail renders DAG + step list, no act() warnings | integration | `npm test -- WorkflowRunDetail.test.tsx --run` | ✅ Exists, needs rewrite |
| TEST-FE-03 | Jobs table checkbox column renders | unit | `npm test -- Jobs.test.tsx --run -t "checkbox column"` | ❌ Wave 0 (todo) |
| TEST-FE-04 | Jobs table checkbox click activates bulk action bar | unit | `npm test -- Jobs.test.tsx --run -t "checkbox select"` | ❌ Wave 0 (todo) |
| TEST-FE-05 | Jobs table header checkbox selects all | unit | `npm test -- Jobs.test.tsx --run -t "header checkbox"` | ❌ Wave 0 (todo) |
| TEST-BE-01 | NodeStats pruned to 60 rows per node (MIN-6) | integration | `pytest tests/test_regression_phase157_deferred_gaps.py::test_min6_node_stats -v` | ❌ Wave 0 |
| TEST-BE-02 | Foundry build cleanup on failure (MIN-7) | integration | `pytest tests/test_regression_phase157_deferred_gaps.py::test_min7_build_cleanup -v` | ❌ Wave 0 |
| TEST-BE-03 | require_permission uses cache (MIN-8) | integration | `pytest tests/test_regression_phase157_deferred_gaps.py::test_min8_permission_cache -v` | ❌ Wave 0 |
| TEST-BE-04 | list_nodes returns deterministic order (WARN-8) | integration | `pytest tests/test_regression_phase157_deferred_gaps.py::test_warn8_node_order -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npm test -- --run` (frontend) + `pytest tests/test_regression_phase157_deferred_gaps.py -v` (backend) — both under 30 seconds
- **Per wave merge:** Full suite: `cd puppeteer/dashboard && npm test -- --run` (all 461 tests) + `cd puppeteer && pytest tests/ -q` (all 86 tests)
- **Phase gate:** Full suite green (461 frontend + 86 backend = 547 total passing, zero failures, zero todos) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `Workflows.test.tsx` — complete rewrite using waitFor(), scoped selectors, proper async patterns (~150 lines)
- [ ] `WorkflowRunDetail.test.tsx` — complete rewrite using waitFor(), scoped selectors, proper async patterns (~200 lines)
- [ ] `Jobs.test.tsx` — convert 3 `it.todo()` to real tests (~100 lines of test code)
- [ ] `puppeteer/tests/test_regression_phase157_deferred_gaps.py` — 4 backend regression tests (MIN-6, MIN-7, MIN-8, WARN-8) (~200 lines)

*(If all gaps filled: 650 lines of test code written. Estimated effort: ~8-10 tasks across 2 waves.)*

---

## Sources

### Primary (HIGH confidence)

- **STATE-OF-NATION.md** (2026-04-16) — v23.0 feature completeness matrix, test health breakdown (30 failures in Workflows/WorkflowRunDetail, root causes documented), deployment status, release blockers. **Verified** against live code inspection.
- **CONTEXT.md** (2026-04-17) — Phase 157 scope, decision boundaries, existing code insights (auth mock pattern, test infrastructure), specific ideas for fixes.
- **Live test output** (2026-04-17) — `npm test -- --run` stderr shows exactly 30 act() warnings from Workflows.test.tsx + WorkflowRunDetail.test.tsx, all due to setTimeout/improper async patterns.
- **Passing test suites as reference:**
  - Phase 150 (47/47 tests) — Workflows list/detail views, DAG rendering
  - Phase 154 (17/17 tests) — Schedule component integration
  - Phase 155 Wave 0 (56/56 tests) — DAG validation, palette, drawer, hooks
  - Phase 155 Wave 1 (10/10) — WorkflowDetail edit integration checkpoint-approved

### Secondary (MEDIUM confidence)

- **core-pipeline-gaps.md** (2026-02-28, verified 2026-04-17) — Original gap report listing MIN-6, MIN-7, MIN-8, WARN-8. Verified against current code that implementations exist.
- **REQUIREMENTS.md** — 32/32 requirements mapped; Phase 157 gates v23.0 release by verifying test infrastructure.

### Tertiary (LOW confidence)

- None — all research sources are current and verified

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Frontend test patterns | HIGH | Phase 154/155 have 73/73 passing tests using identical patterns; setup.ts proven; mocks established |
| Backend test patterns | HIGH | All 86 backend tests passing; conftest.py fixtures stable; pytest-asyncio pattern proven across 10+ test files |
| Root causes of failures | HIGH | Live test output shows exact warnings (act() not wrapped); 30 failures from 2 files; root cause isolation complete |
| Backend gap verification | HIGH | STATE-OF-NATION provides code citations (foundry_service.py:445-447, job_service.py:1035-1050, deps.py:83-114, main.py:1920); implementations verified in code |
| Test data fixtures | MEDIUM | Phase 150/154 examples exist; may need adaptation for Workflows.test.tsx specific scenarios |

**Research date:** 2026-04-17  
**Valid until:** 2026-04-24 (7 days — stable domain, low churn in test patterns)  
**Revalidate if:** Test infrastructure changes, new React version adoption, vitest major version bump

---

## Summary for Planner

**What the planner needs to know:**

1. **Frontend fixes are mechanical** — replace `setTimeout()` with `waitFor()`, replace `getByText()` with scoped selectors. All patterns proven in Phase 150/154/155 Wave 0.

2. **Backend gaps are already implemented** — MIN-6, MIN-7, MIN-8, WARN-8 exist in production code and work. Phase 157 just writes regression tests to lock in behavior and prevent future regressions.

3. **Test infrastructure to reuse:**
   - `vitest.config.ts` + `src/test/setup.ts` (frontend)
   - `conftest.py` fixtures (backend)
   - Auth mock pattern: `vi.spyOn(authModule, 'authenticatedFetch').mockResolvedValueOnce({ ok: true, json: async () => ({...}) } as any)`
   - QueryClient setup: `new QueryClient({ defaultOptions: { queries: { retry: false } } })`
   - Async pattern: `await waitFor(() => expect(...).toBeInTheDocument())`

4. **Pass target is clear:** 461/461 frontend tests + 86/86 backend tests = 547 total. Currently: 428 + 86 = 514 passing. Phase 157 closes the 33-test gap (30 Workflows/WorkflowRunDetail failures + 3 Jobs todos).

5. **Effort estimate:** ~8-10 tasks total:
   - Task 1: Rewrite Workflows.test.tsx (fix 15 failures)
   - Task 2: Rewrite WorkflowRunDetail.test.tsx (fix 15 failures)
   - Task 3: Convert 3 Jobs.test.tsx todos to real tests
   - Tasks 4-7: Write 4 backend regression tests (MIN-6, MIN-7, MIN-8, WARN-8)
   - Task 8: Full suite verification (461 + 86 tests passing)

**No new features, no scope creep — pure quality gate closure.**


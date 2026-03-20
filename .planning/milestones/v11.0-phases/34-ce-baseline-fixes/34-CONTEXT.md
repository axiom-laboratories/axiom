# Phase 34: CE Baseline Fixes - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 6 blocking gaps in the `feature/axiom-oss-ee-split` worktree (`.worktrees/axiom-split/`) so CE runs correctly in isolation: all EE routes return 402, pytest suite passes cleanly, no dead-field crashes. No new features — pure gap closure.

</domain>

<decisions>
## Implementation Decisions

### GAP-01: Stub router mounting
- Mount all 7 CE stub routers inside `load_ee_plugins()` via a `_mount_ce_stubs(app)` helper
- Called when no EE plugin found AND in the except handler (graceful fallback)
- Before mounting, audit every route in `ee/routers/*.py` and verify each has a 402 stub in `ee/interfaces/`; fill any missing stubs
- `main.py` stays clean — CE/EE decision stays inside `load_ee_plugins()`

### GAP-02: importlib.metadata
- Replace `pkg_resources.iter_entry_points("axiom.ee")` with `importlib.metadata.entry_points(group="axiom.ee")`
- 1-line fix; remove `import pkg_resources`

### GAP-03: EE test isolation
- Register `ee_only` marker in `pyproject.toml` under `[tool.pytest.ini_options]`
- Add skip logic to `conftest.py`: `pytest_collection_modifyitems` skips items with `ee_only` marker when EE not installed
- Create 4 placeholder test files in `agent_service/tests/`: `test_lifecycle_enforcement.py`, `test_foundry_mirror.py`, `test_smelter.py`, `test_staging.py`
- Each file: single `@pytest.mark.ee_only` test with a docstring, no assertions (just `pass`)

### GAP-04: bootstrap_admin.py User.role fix
- Remove `role="admin"` from `User(...)` constructor call in `bootstrap_admin.py`
- CE `User` model has no `role` column — this field was stripped in Phase 3

### GAP-05 + GAP-06: NodeConfig removal + job_service CE defaults
- Remove `NodeConfig` Pydantic model entirely
- Remove `PollResponse.config: NodeConfig` field
- Add `env_tag: Optional[str] = None` directly to `PollResponse` (None = no push, "" = clear, "PROD" = set)
- TAMPERED node quarantine: return `PollResponse(job=None)` — no work dispatched, no special config signal needed
- Normal node: return `PollResponse(job=work_item, env_tag=...)` with env_tag logic preserved
- Remove all `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` references from `job_service.py`
- Update `node.py` in the same phase: read `poll_response.env_tag` directly instead of `poll_response.config.env_tag`; drop all `config.concurrency_limit` and `config.tags` parsing

### Claude's Discretion
- Exact variable names for the `_mount_ce_stubs` helper
- Whether to use `importlib.metadata` `select()` or direct `entry_points(group=...)` call (both work on Python 3.12+)
- Content of the placeholder test docstrings

</decisions>

<specifics>
## Specific Ideas

- All changes target `.worktrees/axiom-split/` — do not modify the main branch
- `node.py` is at `puppets/environment_service/node.py` in the worktree
- The conftest skip logic should check for EE presence using `importlib.metadata.packages_distributions()` or simply catch ImportError on `axiom.ee`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ee/interfaces/foundry.py`: `foundry_stub_router` already defined with many 402 stubs — needs audit for completeness
- `ee/interfaces/audit.py`, `webhooks.py`, `triggers.py`, `auth_ext.py`, `smelter.py`, `users.py`: each defines a stub router — need same audit
- `conftest.py`: existing session-scoped `anyio_backend` fixture — add `pytest_collection_modifyitems` hook here

### Established Patterns
- `PollResponse` is in `models.py`; `pull_work()` is in `job_service.py` — both need coordinated changes
- `node.py` at `puppets/environment_service/node.py` is the consumer of `PollResponse` shape — must be updated in lockstep

### Integration Points
- `load_ee_plugins(app, engine)` is called from `main.py` lifespan startup — this is where stub mounting goes
- `pyproject.toml` at `puppeteer/pyproject.toml` — add pytest marker config here

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 34-ce-baseline-fixes*
*Context gathered: 2026-03-19*

# Phase 97: DB Pool Tuning - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Right-size the asyncpg connection pool to sustain 20 concurrent polling nodes without exhaustion or stale-connection errors. No user-facing behaviour changes — pure infrastructure configuration in `db.py` and `compose.server.yaml`.

</domain>

<decisions>
## Implementation Decisions

### Env-var scope
- Only `ASYNCPG_POOL_SIZE` is tunable via env var (default: 20)
- `max_overflow=10`, `pool_timeout=30`, `pool_recycle=300` are hardcoded to the spec'd values
- If `ASYNCPG_POOL_SIZE` is set but `IS_POSTGRES` is False (SQLite), silently ignore it — no warning

### .env.example
- Create `puppeteer/.env.example` as a comprehensive template covering all known vars (DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY, API_KEY, ADMIN_PASSWORD, AGENT_URL, ASYNCPG_POOL_SIZE, etc.) with placeholder values and explanatory comments
- `ASYNCPG_POOL_SIZE=20` included with a comment explaining the tuning formula
- Add `- ASYNCPG_POOL_SIZE=${ASYNCPG_POOL_SIZE:-20}` to the agent service environment block in `compose.server.yaml`

### Concurrent load test
- pytest async test using `asyncio.gather()` of 20 concurrent `/work/pull` requests
- Uses a real enrolled test node (enroll during test setup, extract client cert, fire requests with it)
- Lives in `puppeteer/tests/test_pool_phase97.py` alongside other phase tests

### Claude's Discretion
- How the pool kwargs are structured in `create_async_engine()` (inline dict vs helper function)
- Test node teardown / cert cleanup approach

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IS_POSTGRES` (db.py line 13): already exported — pool kwargs conditional on this flag
- `DATABASE_URL` (db.py line 12): the env var read pattern to follow for `ASYNCPG_POOL_SIZE`
- `engine = create_async_engine(DATABASE_URL, echo=False)` (db.py line 15): the line to modify

### Established Patterns
- Env vars read at module level via `os.getenv(VAR, default)` — follow same pattern for `ASYNCPG_POOL_SIZE`
- `compose.server.yaml` uses `${VAR:-default}` syntax for env var injection with fallback
- `puppeteer/.env` holds live values; `.env.example` will be the documented template

### Integration Points
- `db.py` → `create_async_engine()` call is the only place pool kwargs go
- `compose.server.yaml` agent service `environment:` block needs the new var
- `puppeteer/.env.example` is a new file (`.env` already exists with real values)

</code_context>

<specifics>
## Specific Ideas

- No specific references — standard SQLAlchemy asyncpg pool configuration

</specifics>

<deferred>
## Deferred Ideas

- Service split (heartbeat service vs job dispatch service) — architectural change, not in v17 scope; noted for future milestone consideration

</deferred>

---

*Phase: 97-db-pool-tuning*
*Context gathered: 2026-03-30*

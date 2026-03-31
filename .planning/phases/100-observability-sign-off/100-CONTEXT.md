# Phase 100: Observability + Sign-off - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `GET /health/scale` endpoint exposing live pool and scheduler metrics, surface those metrics in the Admin dashboard, and write the v17.0 upgrade and operations docs (migration_v44.sql runbook entry + scale limits / tuning guidance). No new user-facing features, no schema changes.

</domain>

<decisions>
## Implementation Decisions

### /health/scale endpoint

- Separate `GET /health/scale` endpoint (not merged into `/health/scheduling`)
- Auth: requires valid JWT, no specific permission — any authenticated user (consistent with `jobs:read` pattern on scheduling health)
- SQLite response: always returns valid JSON with `is_postgres: false` and `pool_size: null`, `checked_out: null`, etc. — dashboard shows "N/A (SQLite)". No 500 error on non-Postgres deployments.
- Postgres response: returns `pool_size`, `checked_out`, `available`, `overflow`, APScheduler job count, pending job depth

### Admin dashboard integration

- **Placement**: extend the existing "Repository Health" section in Admin.tsx — add new rows to that card, not a separate section
- **Format**: numeric with label (e.g. `Pool checkout   4 / 20`, `Pending jobs    3`, `APScheduler     7 jobs active`)
- **Polling**: auto-refresh every 30 seconds via `refetchInterval: 30000` on useQuery — consistent with live node sparklines pattern
- **Endpoint**: queries the new `GET /health/scale` independently (separate from scheduling health fetch)

### Operations docs

- **Location**: new "v17.0 Scale Hardening" section appended to `docs/docs/runbooks/upgrade.md` — not a standalone page, not mkdocs.yml change required
- **APScheduler pin rationale**: brief inline paragraph in upgrade.md — one paragraph explaining the `>=3.10,<4.0` pin and that APScheduler 4.x is a complete API rewrite with no migration path
- **Pool tuning formula**: document `pool_size ≤ max_connections / worker_count` with recommended defaults and the `ASYNCPG_POOL_SIZE` env var

### Migration docs (migration_v44.sql)

- **Runbook entry**: add `migration_v44.sql` to the migration table in upgrade.md with a callout note: "Despite the v17.0 milestone name, the dispatch index migration is `migration_v44.sql` — the `migration_v17.sql` filename was already used in an earlier release (Phase 4 — operator_tags)."
- **CONCURRENTLY warning**: add a warning box (or `> **Warning:**` callout) in the runbook: "Do not run this with `psql -1` (single-transaction mode). `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block." Include the correct invocation: `psql -U puppet puppet_db -f migration_v44.sql`

### Claude's Discretion

- Exact placement/ordering of the new rows within the Repository Health card
- Whether `available` is computed as `pool_size - checked_out` or read directly from asyncpg
- How to extract asyncpg pool stats from the SQLAlchemy engine (sync_engine raw pool or asyncpg pool property)
- Test coverage approach for the new endpoint

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `IS_POSTGRES` (db.py): already exported — gates the pool stats path exactly as needed
- `/api/health/scheduling` (main.py:757): pattern for health endpoint with auth — follow same structure
- `SchedulingHealthResponse` (models.py): pattern for health response model
- Repository Health section (Admin.tsx:866–1155): existing `useQuery` + badge/stat display to extend
- `authenticatedFetch` (auth.ts): standard pattern for all dashboard API calls

### Established Patterns

- Health endpoints use `require_permission()` or JWT-only auth — `GET /health/scale` follows JWT-only (no explicit permission)
- `useQuery` with `queryKey` + `authenticatedFetch` — standard data fetching in dashboard views
- `refetchInterval` used in node monitoring for live data — same approach here
- Env var gate: `IS_POSTGRES` boolean exported from `db.py` — pool stats conditional on this flag

### Integration Points

- `main.py`: new `GET /api/health/scale` route, next to existing `GET /api/health/scheduling`
- `models.py`: new `ScaleHealthResponse` Pydantic model
- `Admin.tsx` Repository Health card: add rows for pool checkout, pending depth, APScheduler job count
- `docs/docs/runbooks/upgrade.md`: append v17.0 section at the end of the migration table and add tuning section

</code_context>

<specifics>
## Specific Ideas

- Dashboard numeric format (from discussion): `Pool checkout   4 / 20`, `Pending jobs    3`, `APScheduler     7 jobs active`
- The `is_postgres: false` flag in the SQLite response lets the dashboard render "N/A (SQLite)" rather than misleading zeroes

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 100-observability-sign-off*
*Context gathered: 2026-03-31*

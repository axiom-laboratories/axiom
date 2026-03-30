# Phase 96: Foundation - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Safety prerequisites for v17.0: pin APScheduler to v3.x, export `IS_POSTGRES` dialect flag from `db.py`, configure APScheduler with global `job_defaults`, and warn when running on SQLite. No new features — these are guards that downstream phases depend on.

</domain>

<decisions>
## Implementation Decisions

### APScheduler version assertion
- Runs in the FastAPI lifespan startup (alongside DB init — not in scheduler_service init or at import time)
- Hard exception (RuntimeError) — crashes the server on v4 detection; silent operation on an incompatible version is not acceptable
- Terse message: `"APScheduler v4 detected — pin to >=3.10,<4.0"`

### SQLite startup warning
- Print to stderr (not `logging.warning()`) so a developer running the backend raw without Docker can't miss it
- Message: `"WARNING: SQLite detected — SKIP LOCKED not active. Use Postgres for production."`
- Context: Docker compose always provides `DATABASE_URL=postgresql+...` so this only fires for someone running `python -m agent_service.main` without an env file

### IS_POSTGRES export shape
- Module-level boolean constant in `db.py`, evaluated once at import time from `DATABASE_URL`
- `IS_POSTGRES = DATABASE_URL.startswith("postgresql")`
- Imported as `from agent_service.db import IS_POSTGRES` by `job_service.py` and `scheduler_service.py`

### Claude's Discretion
- Exact placement of the `print(..., file=sys.stderr)` call within the lifespan (before or after DB init — either is fine)
- Whether to use `importlib.metadata.version("apscheduler")` or `packaging.version.parse()` for the version check

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db.py:14`: `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./jobs.db")` — `IS_POSTGRES` derives directly from this existing constant
- `scheduler_service.py:43`: `self.scheduler = AsyncIOScheduler()` — no `job_defaults` set today; needs global defaults added here
- `main.py` lifespan: existing startup sequence (DB init, scheduler start) — APScheduler version check and SQLite warning slot in naturally here

### Established Patterns
- Hard crashes in lifespan for bad config (e.g. missing ENCRYPTION_KEY) — consistent with adding an APScheduler version assertion
- `requirements.txt` currently has bare `apscheduler` — needs pinning to `>=3.10,<4.0`

### Integration Points
- `scheduler_service.py` and `job_service.py` both need `IS_POSTGRES` imported from `db.py`
- `AsyncIOScheduler()` constructor in `scheduler_service.py` gets `job_defaults={"misfire_grace_time": 60, "coalesce": True, "max_instances": 1}`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 96-foundation*
*Context gathered: 2026-03-30*

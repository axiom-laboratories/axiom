# Phase 120: Database & API Contract - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `memory_limit` and `cpu_limit` columns to the Job database table and expose them in Pydantic API models (JobCreate, JobResponse, WorkResponse), so resource limits flow end-to-end from dispatch through to node execution. Includes migration SQL, light API validation, dispatch UI inputs, and job detail display.

</domain>

<decisions>
## Implementation Decisions

### Limit format & storage
- Both `memory_limit` and `cpu_limit` stored as `TEXT` (String) columns, nullable
- Memory format: human-readable strings like `'512m'`, `'1g'`, `'1Gi'` — matches existing `parse_bytes()` on node side
- CPU format: numeric strings like `'2'`, `'0.5'` — matches Docker/Podman `--cpus` flag format
- Null = no per-job limit; node's `JOB_MEMORY_LIMIT` env var ceiling applies as default

### API validation
- Light regex validation at API level in this phase — number+unit for memory, numeric for CPU
- Rejects obvious garbage but does NOT do admission control (size checks vs node capacity)
- Full admission control (parse_bytes on server, oversized rejection) deferred to Phase 121

### Migration
- `migration_v49.sql` following existing pattern
- `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS memory_limit TEXT;` (same for cpu_limit)
- IF NOT EXISTS handles idempotency for Postgres; fresh SQLite handled by `create_all`

### API response shape
- `JobCreate`: add optional `memory_limit` and `cpu_limit` string fields
- `JobResponse`: add optional `memory_limit` and `cpu_limit` string fields
- `WorkResponse`: add optional `memory_limit` and `cpu_limit` as flat fields (matches node.py's `job.get('memory_limit')` extraction pattern)
- Limits serialized in GET /jobs responses, POST /dispatch, and GET /work/pull

### Dispatch UI
- Add optional Memory Limit and CPU Limit text inputs to the Jobs.tsx dispatch form
- Both inputs are optional — empty = null = no per-job limit

### Job display
- Limits shown in job detail/expanded view only
- Job list table stays clean — limits are metadata, not primary columns

### Claude's Discretion
- Exact placement and styling of limit inputs in dispatch form
- Detail view layout for displaying limits
- Regex pattern specifics for light validation

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_bytes()` in `puppets/environment_service/node.py:25` — converts memory strings to bytes; already used for node-side admission and runtime flags
- `runtime.py:40-58` — already accepts and passes `memory_limit`/`cpu_limit` to container runtime `--memory`/`--cpus` flags
- `node.py:537-549` — already extracts limits from work dict and does secondary admission check against node capacity

### Established Patterns
- DB columns use `mapped_column(String, nullable=True)` for optional string fields (see `env_tag`, `runtime`, `name` on Job model)
- Migration files use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for Postgres; SQLite relies on `create_all`
- Pydantic models use `Optional[str] = None` for nullable string fields
- Nodes.tsx already displays `job_memory_limit` per node — precedent for limit display in dashboard

### Integration Points
- `Job` model in `puppeteer/agent_service/db.py:32` — add columns after existing fields
- `JobCreate` in `puppeteer/agent_service/models.py:6` — add limit fields
- `JobResponse` in `puppeteer/agent_service/models.py:54` — add limit fields
- `WorkResponse` in `puppeteer/agent_service/models.py:92` — add limit fields
- `Jobs.tsx` dispatch form — add input fields
- `job_service.py` — pass limits through when creating jobs (currently no limit handling)
- `/work/pull` handler in `main.py` — include limits in WorkResponse construction

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard contract/schema work following established patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 120-database-api-contract*
*Context gathered: 2026-04-06*

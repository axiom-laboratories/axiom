# Phase 121: Job Service & Admission Control - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement server-side `parse_bytes()` utility, persist memory/CPU limits through `create_job()`, and add admission control that rejects oversized jobs before they reach nodes. Includes dynamic capacity tracking, dispatch diagnosis extensions, scheduled job limit support, and inline UI diagnosis for PENDING jobs.

</domain>

<decisions>
## Implementation Decisions

### Admission rejection behavior
- Hard reject (422 Unprocessable Entity) when job's memory_limit exceeds every online node's available capacity
- Error response includes specific detail: "No online node can accommodate memory_limit=4Gi. Largest node capacity: 2Gi (node_alpha)."
- No force-dispatch override flag — operators can omit memory_limit (null) to skip per-job limits entirely
- Memory admission only for now — CPU limits stored and passed to runtime but not admission-checked (nodes don't report CPU capacity yet)
- When no nodes are online: allow job creation (PENDING), admission check skipped — preserves fire-and-forget workflows

### Capacity calculation
- Dynamic tracking: available = node.job_memory_limit - sum(ASSIGNED + RUNNING jobs' memory_limits on that node)
- Job statuses counted toward used capacity: ASSIGNED and RUNNING only — freed on COMPLETED/FAILED/CANCELLED
- Jobs with null memory_limit: assume 512m default for capacity accounting — prevents unlimited jobs from silently consuming all capacity
- Default configurable via Config table key `default_job_memory_limit` (hardcoded 512m initial default)
- Server-side `parse_bytes()` ported from `puppets/environment_service/node.py:25` — converts memory strings to bytes for comparison

### Dispatch diagnosis
- Extend `get_dispatch_diagnosis()` to include resource-related blocking reasons with per-node breakdown
- Response includes: reason, detail, nodes_checked array (node name, capacity, used, available, verdict)
- Jobs.tsx: show resource diagnosis inline in job detail when PENDING — auto-fetch on expand, refresh on WebSocket updates
- No manual "Diagnose" button needed — automatic for all PENDING jobs

### Scheduled job limits
- Add `memory_limit` and `cpu_limit` (TEXT, nullable) to ScheduledJob DB table + migration
- When scheduler fires, limits copied to created Job instance via `create_job()`
- Admission check runs at fire time, not at definition creation time — capacity may differ
- If admission fails at fire time: job instance marked FAILED with reason `admission_rejected`
- Schedule itself keeps running — next cron tick creates a new independent instance with fresh admission check
- JobDefinitions.tsx: add limit fields to create/edit form

### Claude's Discretion
- Exact placement and styling of limit fields in JobDefinitions.tsx create/edit form
- parse_bytes() implementation details (regex vs parsing approach)
- Config table interaction pattern for default_job_memory_limit
- Diagnosis UI layout within job detail expanded view
- Migration SQL file numbering

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_bytes()` in `puppets/environment_service/node.py:25` — server-side port needed; converts "512m", "1Gi" to bytes
- `get_dispatch_diagnosis()` in `job_service.py:1255` — existing diagnosis logic to extend with resource reasons
- Pydantic validators on `JobCreate` (lines 41-62) — memory/CPU format validation already implemented in Phase 120
- `WorkResponse` already passes memory_limit/cpu_limit to nodes (Phase 120)

### Established Patterns
- Job status tracking: `ASSIGNED`/`RUNNING` states already exist in Job model
- Config table: key-value store used for system settings (e.g., `base_image_updated_at`)
- ScheduledJob model: follows same pattern as Job model with script_content, signature fields
- Migration files: `migration_v{N}.sql` with `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`

### Integration Points
- `job_service.py:create_job()` — add admission check after format validation, before DB insert
- `job_service.py:pull_work()` — capacity sum query here for dispatch-time node selection
- `job_service.py:get_dispatch_diagnosis()` — extend with `insufficient_memory` reason + node breakdown
- `scheduler_service.py` — pass memory_limit/cpu_limit when creating job instances
- `Jobs.tsx` — auto-fetch diagnosis for PENDING jobs in expanded detail view
- `JobDefinitions.tsx` — add limit input fields to create/edit modal
- `db.py:ScheduledJob` — add memory_limit/cpu_limit columns

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard admission control following established patterns. Key reference: node.py's existing `parse_bytes()` and secondary admission check logic.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 121-job-service-admission-control*
*Context gathered: 2026-04-06*

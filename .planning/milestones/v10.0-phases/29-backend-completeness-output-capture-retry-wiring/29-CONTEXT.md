# Phase 29: Backend Completeness — Output Capture + Retry Wiring - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire up the gaps between what the DB schema and success criteria require and what actually flows through the system: per-execution stdout/stderr storage, script hash, retry attempt tracking with job_run_id, WorkResponse completeness, and removal of the direct execution mode. No dashboard UI (Phase 32). No attestation signing (Phase 30).

</domain>

<decisions>
## Implementation Decisions

### Output field shape
- Add `stdout` TEXT and `stderr` TEXT as separate nullable columns to `ExecutionRecord` alongside the existing `output_log` JSON column (keep combined log for display consumers)
- Server-side extraction: orchestrator reconstructs stdout/stderr text from the `output_log` JSON by filtering `stream='stdout'` and `stream='stderr'` entries — no node change required
- No server-side size cap on raw stdout/stderr columns — job authors control their own output volume; size restrictions are the job author's responsibility

### script_hash
- Node computes `SHA-256 of script.encode('utf-8')` before execution and sends it in `ResultReport` as a new `script_hash` field
- Orchestrator also independently re-hashes the script bytes from the Job payload on receipt for dual verification
- On mismatch: log warning, store the orchestrator's hash on `ExecutionRecord`, set a `hash_mismatch` boolean flag on the record — non-fatal, no SECURITY_REJECTED; Phase 30 attestation is the enforcement layer
- `ExecutionRecord` gets `script_hash TEXT` and `hash_mismatch BOOLEAN` (default False) columns

### Retry attempt linking
- Add `attempt_number INTEGER` to `ExecutionRecord` — set from `job.retry_count + 1` at record write time (1-indexed)
- Add `job_run_id UUID` to `ExecutionRecord` as an explicit grouping key — generated when the Job is first dispatched and stored on the Job row; all retry attempts of that dispatch share the same `job_run_id`
- All failure modes (genuine failure, zombie reap/timeout) increment the same counter — no distinction needed at this layer
- `job_guid` remains on ExecutionRecord; `job_run_id` is the explicit run-grouping key for Phase 32

### WorkResponse completeness
- `pull_work()` populates all four missing fields from the Job row: `max_retries`, `backoff_multiplier`, `timeout_minutes`, `started_at`
- Node respects `WorkResponse.timeout_minutes` for subprocess/container execution timeout (convert to seconds; fall back to 30s if None)
- Timeout failures sent with `retriable=True` so orchestrator applies retry policy

### Execution mode — direct mode removal
- Remove `direct` execution mode entirely from `runtime.py` — delete the code path, do not deprecate
- Valid execution modes: `auto`, `docker`, `podman` only
- Node fails at startup with `RuntimeError` if `EXECUTION_MODE=direct` is configured — fast fail before enrollment
- mop_validation test node configs using `EXECUTION_MODE=direct` must be updated to `docker` or `podman`
- This is not a blocking condition for dispatching; the node simply won't start

### Claude's Discretion
- Exact job_run_id generation point (Job creation vs first dispatch assignment)
- Error message wording for direct mode startup failure
- Whether `hash_mismatch=True` records appear in audit log

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExecutionRecord` in `db.py:216`: existing model, needs `stdout`, `stderr`, `script_hash`, `hash_mismatch`, `attempt_number`, `job_run_id` columns
- `job_service.report_result()` (`job_service.py:651`): existing write path — extend to extract stdout/stderr, store script_hash, set attempt_number
- `pull_work()` (`job_service.py:373`): existing WorkResponse assembly — add 4 missing fields
- `build_output_log()` (`node.py:36`): existing helper that splits stdout/stderr into interleaved entries — server-side extraction is the reverse of this
- `prune_execution_history()` (`scheduler_service.py:56`): existing DELETE WHERE started_at < cutoff — SQLite-compatible already ✓
- `RuntimeEngine` in `runtime.py`: contains the `direct` mode to be removed
- `ResultReport` (`models.py:56`): needs `script_hash: Optional[str]` field

### Established Patterns
- Secret scrubbing happens in `report_result()` before storing `output_log` — stdout/stderr extraction must happen AFTER scrubbing
- Hash ordering invariant (from STATE.md research flags): hash raw bytes FIRST, then scrub, then truncate, then store — node-side hash is computed before execution, so this is naturally satisfied
- `WorkResponse` model already has `max_retries`, `backoff_multiplier`, `timeout_minutes` fields (`models.py:46`) — just not populated in `pull_work()`
- Retry state machine: RETRYING → re-dispatch → new ExecutionRecord on next report_result call

### Integration Points
- `migration_v14.sql`: must add nullable columns to `execution_records` and `jobs` tables — no breaking changes
- `node.py execute_task()` (`node.py:481`): add script_hash computation before execution; update `report_result()` call to include it
- `node.py report_result()` (`node.py:598`): add `script_hash` to the JSON payload sent to orchestrator
- `runtime.py detect_runtime()`/`RuntimeEngine.__init__()`: remove `direct` case entirely

</code_context>

<specifics>
## Specific Ideas

- "TLDR NO JOBS SHOULD BE CREATABLE OR DISPATCHED IN DIRECT MODE" — remove the feature entirely, fast-fail at node startup
- stdout/stderr size is the job author's responsibility — no server-side cap on the raw text columns
- job_run_id is explicit future-proofing for Phase 32 "attempt N of M" display — worth adding now to avoid a migration mid-phase-32

</specifics>

<deferred>
## Deferred Ideas

- EXECUTION_MODE=direct for DinD test environments (mop_validation nodes) — operators must migrate to docker/podman mode; test infrastructure update is a prerequisite before Phase 29 execution
- Resource limit enforcement for Python subprocess (direct) mode — moot after direct mode removal
- Stricter job-creation blocking when no container-capable nodes are online — deferred; jobs queue until eligible node connects

</deferred>

---

*Phase: 29-backend-completeness-output-capture-retry-wiring*
*Context gathered: 2026-03-18*

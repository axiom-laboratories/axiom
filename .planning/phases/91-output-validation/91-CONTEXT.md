# Phase 91: Output Validation - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can declare what a successful job output looks like — a job that exits 0 but violates its configured validation pattern transitions to FAILED with a clear reason, not silently COMPLETED. Validation rules live on saved job definitions only; ad-hoc dispatches are not in scope.

</domain>

<decisions>
## Implementation Decisions

### Validation rule scope
- **Definition-only**: `validation_rules` JSON column lives on `ScheduledJob`. Ad-hoc jobs dispatched directly from the dispatch form carry no validation rules and are never validated.
- Signature/key verification is always enforced regardless of validation rules — it runs upstream as a separate security gate before validation is even considered.

### Rule stamping at dispatch
- When a scheduled job is dispatched (cron trigger or manual), `validation_rules` are **stamped into the Job payload JSON** at dispatch time (alongside `script_content`).
- Validation is evaluated against the stamped rules at result time — not re-read from the definition. Ensures in-flight jobs are immune to definition changes mid-run.

### Validation form UI (in JobDefinitionModal)
- A **collapsible "Validation Rules" section** at the bottom of the job definition form.
  - Collapsed by default when no rules are set.
  - Auto-expanded when the definition already has rules configured.
- **Exit code field**: pre-filled with `0` by default. Operator must clear it to disable exit code checking.
- **Stdout regex field**: empty = not enforced.
- **JSON field assertion**: two separate inputs — "JSON path" (dot notation, e.g. `result.status`) and "Expected value" (e.g. `ok`). Both must be filled for the JSON rule to be active.

### Multi-rule evaluation
- **All configured rules run** — no short-circuit on first failure.
- **failure_reason reflects the first failing rule** using this fixed priority order:
  1. `validation_exit_code`
  2. `validation_regex`
  3. `validation_json_field`
- `ExecutionRecord.failure_reason` stores only the first-failing rule code (the Phase 87 string codes). No separate "full result" column.

### Retry behaviour
- **Validation failure (exit 0, rule violated) is always terminal** — no retries, regardless of `max_retries`. Re-running the same script won't produce different output.
- **Non-zero exit code is a runtime failure** — retries still fire as today. The `exit_code` validation rule only converts COMPLETED → FAILED when the job exits 0 but the rule expected a different value; it does not suppress retries for genuine runtime failures.
- Null `validation_rules` = no validation applied = existing retry/status behaviour unchanged.

### Claude's Discretion
- Exact wording of the failure reason labels in the UI (e.g. "Validation failed: stdout_regex" vs "Output mismatch: regex")
- Whether the collapsible section uses a chevron icon or a toggle switch as the expand trigger
- How the exit code field communicates "clear to disable" (placeholder text, tooltip, or small hint label)
- dot notation parsing depth for JSON path (e.g. whether `result.items[0].status` needs to be supported or just simple dot-separated keys)

</decisions>

<specifics>
## Specific Ideas

- Signature verification always runs — validation rules are an additional layer on top, not a replacement for security checks
- The exit code field defaulting to 0 nudges operators toward good practice without forcing it
- Validation failure being terminal is deliberate: if a script exits 0 with the wrong output, retrying won't fix it — the script logic is wrong

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db.py: ExecutionRecord` — already has `stdout`, `exit_code`, `stderr` columns. Phase 91 adds `failure_reason` (nullable String). No node changes needed.
- `db.py: ScheduledJob` — gets new `validation_rules` nullable Text column (JSON). Existing `create_all` picks up new tables; existing deployments need `ALTER TABLE scheduled_jobs ADD COLUMN validation_rules TEXT`.
- `services/job_service.py` lines 1073–1076 — the `elif report.success: new_status = "COMPLETED"` branch is exactly where validation evaluation is inserted. `stdout_text` is already extracted at line 1094 before truncation.
- `ExecutionRecord` write at lines 1123–1140 — `failure_reason` field added here alongside existing fields.

### Established Patterns
- `payload` JSON stamping pattern: `script_content`, `signature_id`, `secrets` etc. are all stamped into `Job.payload` at dispatch in `scheduler_service.dispatch_scheduled_job()`. `validation_rules` follows the same pattern.
- `Config` key/value pattern for feature flags — not needed here (validation is always on if rules are configured).
- `failure_reason` string codes from Phase 87: `execution_error`, `validation_exit_code`, `validation_regex`, `validation_json_field`.

### Integration Points
- `scheduler_service.py: dispatch_scheduled_job()` — stamp `validation_rules` from the `ScheduledJob` into the `Job.payload` JSON at dispatch.
- `job_service.py: process_result()` — insert validation evaluation between security rejection check and the `new_status = "COMPLETED"` assignment. Parse `payload["validation_rules"]`, evaluate against `stdout_text` and `report.exit_code`, set `new_status = "FAILED"` and `failure_reason` if any rule fails.
- `JobDefinitionModal` (dashboard) — add collapsible Validation Rules section with exit code (default 0), regex, and JSON path + expected value fields.
- `Jobs.tsx` job detail sheet and `JobDefinitions.tsx` history tab — surface `failure_reason` distinctly from runtime errors per Phase 87 decision.
- Migration: `ALTER TABLE scheduled_jobs ADD COLUMN validation_rules TEXT;` + `ALTER TABLE execution_records ADD COLUMN failure_reason VARCHAR;`

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 91-output-validation*
*Context gathered: 2026-03-30*

# Phase 87: Research & Design - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce design documents resolving implementation ambiguity for all four v16.0 features (dispatch diagnosis, CE alerting, script versioning, output validation) before any implementation begins. Deliverable is a written design decisions document — no code changes in this phase.

</domain>

<decisions>
## Implementation Decisions

### Competitor Research Integration
- Competitor pain points report reviewed at `mop_validation/reports/plans/20262903/competitor_pain_points.md`
- Key findings that directly motivate the four features:
  - **Observability gaps** (Airflow, Temporal, Prefect): tools report "success" while execution state is silently wrong → output validation
  - **Silent/opaque failures** (Rundeck, Nomad): no actionable error when something is blocked → dispatch diagnosis
  - **No pipeline versioning** (Rundeck, Airflow, Prefect): can't see what script ran historically → script versioning
  - **Inadequate built-in alerting** (all six tools require external tooling): → CE-native failure alerts
- The design decisions below directly counter the top frustrations practitioners reported

### Dispatch Diagnosis UI (→ Phase 88)
- **Surface**: Inline badge below the status column in the job list — reason text displayed directly, no hover or click required
  - Example: "No capable nodes" or "All nodes busy (3rd in queue)"
- **Queue position**: Show queue position when reason is capacity-based (e.g. "All nodes busy (3rd in queue)") — endpoint already computes `queue_position`
- **Auto-refresh**: Auto-poll every 5–10 seconds for PENDING jobs currently in view — consistent with existing WebSocket live update model
- **Coverage**: Extend beyond PENDING-only to also cover stuck ASSIGNED jobs
  - Stuck threshold: job timeout + 20% grace period; fallback to 30 minutes for jobs with no `timeout_minutes` set
  - Badge text for stuck ASSIGNED: e.g. "Assigned to node-alpha — no completion signal in 35 min"
- **Endpoint gap**: Existing `/jobs/{guid}/dispatch-diagnosis` covers PENDING reasons; needs extension to detect and surface stuck-ASSIGNED state

### CE Alerting (→ Phase 89)
- **Mechanism**: Single outbound webhook URL (HTTP POST) — no SMTP, no email infrastructure required
  - Works with Slack, Teams, PagerDuty, ntfy.sh, custom endpoints
- **Configuration location**: Admin → System Config page, new Notifications section
- **CE/EE boundary**: Single destination URL is CE; multiple destinations + per-job routing rules is EE
- **Webhook payload** (compact JSON):
  ```json
  {
    "event": "job.failed",
    "job_guid": "...",
    "job_name": "nightly-backup",
    "node_id": "node-alpha",
    "error_summary": "exit code 1: permission denied",
    "failed_at": "2026-03-29T22:15:00Z"
  }
  ```
- Richer payload (stdout, stderr, script content) is EE territory
- Existing `webhook_service.py` is a CE no-op stub — Phase 89 replaces it with real outbound dispatch

### Script Versioning Schema (→ Phase 90)
- **Two separate history tables** — separate concerns:

  **Table 1: `job_script_versions`** — immutable script snapshots
  ```
  id              UUID PK
  scheduled_job_id  FK → scheduled_jobs.id
  version_number  INT (monotonic per job)
  script_content  TEXT
  signature_id    STR
  signature_payload TEXT
  created_at      DATETIME
  created_by      STR
  ```
  - `execution_records` gets a new nullable `script_version_id` FK → `job_script_versions.id`
  - This is the link that lets operators see exactly which script ran for any execution

  **Table 2: `job_definition_history`** — metadata audit log
  ```
  id              UUID PK
  scheduled_job_id  FK → scheduled_jobs.id
  changed_at      DATETIME
  changed_by      STR
  diff            TEXT (JSON: {field: {from, to}})
  ```
  - Captures changes to cron, tags, timeout, target_node, etc. — not script content
  - JSON diff format: `{"schedule_cron": {"from": "0 2 * * *", "to": "0 4 * * *"}}`

- **Version trigger**: Configurable toggle in Admin Config (Config table key)
  - Default: `script_changes_only` — a new version is created only when `script_content` differs
  - Alternate: `any_edit` — every PATCH to the job definition creates a new script version
  - Metadata history is always recorded regardless of toggle

- **API shape**:
  - `GET /jobs/definitions/{id}/versions` — script version list (version_number, created_at, created_by, script preview)
  - `GET /jobs/definitions/{id}/history` — definition metadata edit log (JSON diffs, chronological)

### Output Validation Contract (→ Phase 91)
- **Operator-defined rules**: New nullable `validation_rules` JSON column on `scheduled_jobs`
  ```json
  {
    "exit_code": 0,
    "stdout_regex": "SUCCESS",
    "json_field": {
      "path": "result.status",
      "expected": "ok"
    }
  }
  ```
  - All three fields are optional; any combination is valid
  - Null `validation_rules` = no validation = current behaviour preserved
  - Applied to both ad-hoc and scheduled jobs (via the job definition)

- **How scripts signal JSON results**: Print JSON to stdout — zero node changes required
  - Node already captures stdout into `ExecutionRecord.stdout`
  - Backend parses stdout as JSON when a `json_field` rule is configured
  - Scripts that don't print JSON are only subject to `exit_code` and `stdout_regex` checks

- **Status model**: FAILED status unchanged — add `failure_reason` field to `ExecutionRecord`
  - `execution_error` — node reported failure, no validation rule was violated
  - `validation_exit_code` — job exited 0 but `exit_code` rule expected a different value
  - `validation_regex` — stdout did not match `stdout_regex` pattern
  - `validation_json_field` — JSON path/value assertion failed (or stdout was not valid JSON)
  - Null = no validation applied or not yet evaluated

- **UI visibility**: Both execution history list AND job detail panel show the failure reason
  - History list: "Validation failed: stdout_regex" tag in place of generic error badge
  - Job detail: validation rule that was violated shown in the result section, distinct from runtime errors

### Claude's Discretion
- Exact auto-poll interval for dispatch diagnosis (5 or 10 seconds — pick based on WebSocket coexistence)
- Whether stuck-ASSIGNED detection runs client-side (calculate from `started_at + timeout`) or as a separate backend flag
- Admin toggle UI design for the versioning trigger (switch vs dropdown)
- Whether `json_field.path` uses dot notation (`result.status`) or JSONPath syntax — dot notation is simpler

</decisions>

<specifics>
## Specific Ideas

- "Two history tables" for versioning — one for script content, one for metadata edits — deliberately separating "what the job does" from "how it's scheduled"
- The stuck-ASSIGNED badge follows the same inline pattern as PENDING diagnosis — consistent UX across pending states
- Output validation is explicitly designed to be non-breaking: null `validation_rules` = existing behaviour

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent_service/services/job_service.py → JobService.get_dispatch_diagnosis()`: Returns `{reason, message, queue_position}` for PENDING jobs. Phase 88 wires it to the frontend; needs extension for stuck-ASSIGNED detection.
- `agent_service/services/webhook_service.py`: CE stub (no-op). Phase 89 replaces this with real HTTP POST dispatch.
- `ExecutionRecord.stdout` / `.exit_code` / `.stderr`: Already captured by the node. Phase 91 uses these for validation evaluation — no node-side changes needed.
- `Config` table (key/value): Use for the versioning trigger toggle (new Config key: `versioning.trigger_mode`).

### Established Patterns
- `webhook_service.py` CE stub pattern: EE plugin overrides. Phase 89 should implement in the CE layer (not EE), breaking the stub.
- `ExecutionRecord` already has `script_hash` (SHA-256) — the new `script_version_id` FK complements rather than replaces it.
- Admin config storage: `Config` table key/value — used for `stale_base_updated`, licence info, etc. Same pattern for alerting webhook URL and versioning mode toggle.

### Integration Points
- Phase 88: `GET /jobs/{guid}/dispatch-diagnosis` endpoint already exists — frontend just needs to call it and render the badge. Needs server-side extension for stuck-ASSIGNED coverage.
- Phase 89: `Config` table stores `alerts.webhook_url`. `job_service.py` job completion path calls `WebhookService.dispatch_event()` — hook point already exists (currently no-op).
- Phase 90: `ScheduledJob.script_content` is the field to version. `scheduler_service.update_job_definition()` is the mutation point where versioning logic is inserted.
- Phase 91: `ScheduledJob` gets `validation_rules` column. `job_service.py` result processing (where `ExecutionRecord` is written) is where validation evaluation runs.

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 87-research-design*
*Context gathered: 2026-03-29*

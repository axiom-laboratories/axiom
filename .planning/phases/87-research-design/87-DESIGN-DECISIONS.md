# Phase 87: v16.0 Design Decisions

**Date:** 2026-03-29
**Status:** Final — unblocks Phases 88–91

This document captures all design decisions for the four v16.0 Competitive Observability features. It is the authoritative reference for Phases 88 (Dispatch Diagnosis UI), 89 (CE Alerting), 90 (Job Script Versioning), and 91 (Output Validation). No decisions in this document should be revisited during implementation phases without an explicit design change.

---

## Section 1: Competitor Research & Feature Rationale (RSH-01)

**Source report:** `mop_validation/reports/plans/20262903/competitor_pain_points.md`

The competitor pain points report was reviewed before any feature decisions were made. The four v16.0 features directly counter the top practitioner frustrations reported across Airflow, Temporal, Prefect, Rundeck, Nomad, and Jenkins.

### Pain Point → Feature Mapping

| Competitor Pain Point | Affected Tools | v16.0 Response | Phase |
|-----------------------|---------------|----------------|-------|
| Tools report "success" while execution state is silently wrong — bad exit codes swallowed, stdout not checked | Airflow, Temporal, Prefect | **Output Validation** — operator-defined rules checked server-side against stdout, exit code, and JSON fields | Phase 91 |
| No actionable error when a job is blocked in queue or assigned but not running — operators discover failures manually | Rundeck, Nomad | **Dispatch Diagnosis** — inline badge in the job list shows the specific blocking reason without requiring any user action | Phase 88 |
| No script version history — impossible to know what code actually ran for a past execution | Rundeck, Airflow, Prefect | **Script Versioning** — immutable snapshots of every script change; each execution record links back to the exact version that ran | Phase 90 |
| All tools require external tooling (PagerDuty, OpsGenie, custom scripts) to receive failure notifications — no native alerting | All six tools reviewed | **CE Alerting** — native webhook notification on `job.failed` events; no third-party integration or SMTP required | Phase 89 |

### Chosen Approach Summary

Each feature was chosen because it closes a gap that competitors explicitly do not address at the CE (open source) tier. All four features are implementable without breaking existing behaviour — they are strictly additive.

---

## Section 2: Dispatch Diagnosis UX (RSH-02)

### Badge Surface

- **Location:** Inline badge rendered below the status column in the job list table
- **Visibility:** Reason text displayed directly in the row — no hover tooltip, no modal, no click required
- **Examples:**
  - `No capable nodes` — when no enrolled node has the required capabilities
  - `All nodes busy (3rd in queue)` — when capacity-based, includes queue position
  - `Assigned to node-alpha — no completion signal in 35 min` — stuck-ASSIGNED state

### Auto-Poll Interval

- **Interval:** 5 seconds for PENDING jobs currently visible in the job list
- **Rationale:** 5 s is consistent with the existing WebSocket live update cadence. Using 10 s would create a visible lag between the WebSocket status update and the badge appearing. 5 s keeps diagnosis latency imperceptible to users.

### Queue Position

- Queue position is shown when the diagnosis reason is capacity-based (all nodes busy or at concurrency limit)
- The existing endpoint already returns `queue_position` — the frontend renders it inline in the badge text

### Coverage: PENDING and Stuck-ASSIGNED

The diagnosis system covers two categories of problematic jobs:

**PENDING jobs** — job is queued, not yet assigned to a node. Reason is computed by the existing endpoint.

**Stuck-ASSIGNED jobs** — job has been assigned to a node but has not reported completion within the expected window.

- **Stuck threshold formula:** `timeout_minutes * 1.2` (20% grace period above the configured timeout)
- **Fallback (no timeout_minutes set):** 30 minutes
- **Badge text:** `"Assigned to {node_id} — no completion signal in {N} min"` where N is the elapsed minutes since `started_at`

### Endpoint Gap and Required Extension

The existing `GET /jobs/{guid}/dispatch-diagnosis` endpoint returns diagnosis for PENDING jobs only — it currently returns HTTP 400 for non-PENDING jobs.

**Required extension (Phase 88 scope):** The endpoint must be extended server-side to detect stuck-ASSIGNED state. When `job.status == "ASSIGNED"` and `now() > job.started_at + stuck_threshold`, the endpoint must return a structured diagnosis response instead of 400.

**Decision: server-side detection, not client-side.** The frontend timer must not compute the stuck threshold. The server computes it and returns a diagnosis response. This keeps threshold logic in one place and prevents clock skew issues between client and server.

---

## Section 3: CE Alerting Mechanism (RSH-03)

### Chosen Mechanism: Single Outbound Webhook URL

**Decision:** HTTP POST to a single operator-configured URL.

**Rationale:** A single webhook URL integrates with every common notification destination without requiring Master of Puppets to implement channel-specific logic:

| Destination | How it works |
|-------------|-------------|
| Slack | Incoming Webhooks URL |
| Microsoft Teams | Teams Webhook connector |
| PagerDuty | Events API v2 URL |
| ntfy.sh | ntfy topic URL |
| Custom scripts | Any HTTP server |

No SMTP server, no email infrastructure, no MX record configuration required.

### Configuration Location

- **Where:** Admin → System Config page, new "Notifications" section
- **How stored:** `Config` table, key `alerts.webhook_url`
- **Behaviour when empty:** No webhooks fired — existing behaviour preserved

### CE/EE Boundary

| Feature | CE (this phase) | EE (future) |
|---------|----------------|-------------|
| Destinations | Single URL | Multiple URLs |
| Event types | `job.failed` only | Configurable per-event |
| Routing rules | None | Per-job routing |
| Payload richness | 6-field compact payload | Includes stdout, stderr, script content |

### Webhook Payload Schema

All `job.failed` events deliver this compact JSON payload:

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

Fields:

| Field | Type | Source |
|-------|------|--------|
| `event` | string | Literal `"job.failed"` |
| `job_guid` | string | `Job.guid` |
| `job_name` | string | `Job.name` or `ScheduledJob.name` |
| `node_id` | string | `Job.assigned_node_id` |
| `error_summary` | string | First line of `ExecutionRecord.stderr`, or `"exit code N"` |
| `failed_at` | ISO 8601 | `ExecutionRecord.completed_at` |

### Implementation Note

`agent_service/services/webhook_service.py` is currently a CE no-op stub (`dispatch_event()` does nothing). Phase 89 replaces this stub implementation with a real outbound HTTP POST while keeping the same call signature. No other service files need to change their `dispatch_event()` call.

---

## Section 4: Job Script Versioning Schema (RSH-04)

### Two-Table Design

Script content and job definition metadata are tracked in separate tables. This separates "what the job does" (script) from "how it is scheduled" (cron, tags, timeout, target node).

### Table 1: `job_script_versions` (Immutable Script Snapshots)

```
Column             Type          Constraints
id                 UUID          PRIMARY KEY
scheduled_job_id   INT/UUID      FK → scheduled_jobs.id, NOT NULL
version_number     INT           NOT NULL (monotonic per job, starts at 1)
script_content     TEXT          NOT NULL
signature_id       VARCHAR       NULLABLE
signature_payload  TEXT          NULLABLE
created_at         DATETIME      NOT NULL, DEFAULT now()
created_by         VARCHAR       NOT NULL
```

- Records are immutable once written — never updated, only appended
- `version_number` is scoped per job (each job has its own 1, 2, 3... sequence)
- `signature_id` and `signature_payload` are copied from the job definition at version creation time

### Table 2: `job_definition_history` (Metadata Audit Log)

```
Column             Type          Constraints
id                 UUID          PRIMARY KEY
scheduled_job_id   INT/UUID      FK → scheduled_jobs.id, NOT NULL
changed_at         DATETIME      NOT NULL, DEFAULT now()
changed_by         VARCHAR       NOT NULL
diff               TEXT          NOT NULL (JSON object)
```

- JSON diff format: `{"field_name": {"from": old_value, "to": new_value}}`
- Example: `{"schedule_cron": {"from": "0 2 * * *", "to": "0 4 * * *"}}`
- Records metadata changes only (cron expression, tags, timeout, target_node, capability_requirements)
- Recorded on every PATCH to the job definition, regardless of versioning trigger mode

### Linkage to Execution Records

`execution_records` gets one new nullable column:

```
script_version_id   UUID    NULLABLE, FK → job_script_versions.id
```

- This FK is the link that lets operators see exactly which script ran for any past execution
- The existing `script_hash` (SHA-256) column is **complemented**, not replaced — both coexist
- For executions that predate Phase 90, `script_version_id` is null; `script_hash` still provides fingerprinting

### Version Trigger Mode

Configurable via `Config` table key `versioning.trigger_mode`:

| Mode | Behaviour |
|------|-----------|
| `script_changes_only` | New script version created only when `script_content` differs from the previous version. Default. |
| `any_edit` | Every PATCH to the job definition creates a new script version, even if script content is unchanged. |

Metadata history (`job_definition_history`) is always recorded regardless of which mode is active.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /jobs/definitions/{id}/versions` | GET | List script versions: `version_number`, `created_at`, `created_by`, first 200 chars of script |
| `GET /jobs/definitions/{id}/history` | GET | Metadata edit log: JSON diffs in chronological order |

### Migration Requirement

Phase 90 must include `migration_v17.sql` covering:
1. `CREATE TABLE job_script_versions (...)`
2. `CREATE TABLE job_definition_history (...)`
3. `ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS script_version_id UUID REFERENCES job_script_versions(id);`

Fresh deployments are handled by `create_all` at startup. The migration file is required for existing deployments.

---

## Section 5: Output Validation Contract (RSH-05)

### Operator-Defined Validation Rules

New nullable `validation_rules` JSON column on `scheduled_jobs`. Schema:

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

Rules:

| Field | Type | Description |
|-------|------|-------------|
| `exit_code` | integer | Expected process exit code. Most commonly `0`. |
| `stdout_regex` | string | Python `re.search()` pattern applied to the full stdout string. |
| `json_field.path` | string | Dot-notation path into the JSON object printed to stdout. |
| `json_field.expected` | string/number/bool | Expected value at that path. |

All three fields are optional. Any combination is valid. `null` (or omitted) `validation_rules` means no validation — current behaviour is preserved without any change.

### How Scripts Signal JSON Results

Scripts print JSON to stdout. No node-side changes are required.

- The puppet node already captures stdout into `ExecutionRecord.stdout`
- The backend parses stdout as JSON when a `json_field` rule is configured
- Scripts that do not print JSON are only subject to `exit_code` and `stdout_regex` checks

**JSON path syntax:** Dot notation — e.g. `result.status` resolves `{"result": {"status": "ok"}}`. Full JSONPath syntax is not supported in CE. Dot notation is simpler and covers all common cases.

### `failure_reason` Enum

New nullable `failure_reason` field on `ExecutionRecord`:

| Value | Meaning |
|-------|---------|
| `null` | No validation applied, or not yet evaluated. Current behaviour. |
| `execution_error` | Node reported failure (non-zero exit or exception). No validation rule was violated — the job failed before validation ran. |
| `validation_exit_code` | Job completed but `exit_code` rule was violated (e.g. expected 0, got 1). |
| `validation_regex` | Job completed but stdout did not match the `stdout_regex` pattern. |
| `validation_json_field` | Job completed but JSON path assertion failed, or stdout was not valid JSON when a `json_field` rule was configured. |

### Evaluation Location

Validation evaluation runs in `job_service.py` at the result processing path — specifically where `ExecutionRecord` is written after the node reports completion. This is entirely backend-side. The puppet node is unaware of validation rules.

### UI Visibility

**Execution history list:**
- Instead of a generic error badge, show `"Validation failed: stdout_regex"` (or whichever rule was violated)
- `execution_error` continues to show the existing generic failure badge (no regression)

**Job detail panel:**
- The validation rule that was violated is shown in the result section
- Visually distinct from runtime errors so operators can immediately distinguish "job ran but output was wrong" from "job crashed"

---

## Cross-Phase Integration Notes

These decisions were made with the integration points in mind:

| Phase | Entry Point | Pre-existing hook |
|-------|-------------|------------------|
| 88 | `GET /jobs/{guid}/dispatch-diagnosis` | Endpoint exists; extend for ASSIGNED |
| 89 | `WebhookService.dispatch_event()` in `job_service.py` | No-op stub; replace with HTTP POST |
| 90 | `scheduler_service.update_job_definition()` | Mutation point; insert versioning logic |
| 91 | `job_service.py` result processing (where `ExecutionRecord` is written) | Extend to run validation rules |

All four implementation phases are independent of each other after this document is written. They may execute in any order.

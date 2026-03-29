# Phase 87: Research & Design — Research

**Phase:** 87
**Completed:** 2026-03-29
**Status:** RESEARCH COMPLETE

---

## Validation Architecture

All five requirements (RSH-01 through RSH-05) are delivered as written documents — decisions captured in CONTEXT.md and a competitor report file. Validation is filesystem-based:

| Artifact | How to verify |
|----------|--------------|
| Competitor pain points report | File exists: `mop_validation/reports/plans/20262903/competitor_pain_points.md` |
| RSH-01 feature approach rationale | PLAN.md content review — design doc task output |
| RSH-02 dispatch diagnosis UX | PLAN.md content review — design doc task output |
| RSH-03 CE alerting decision | PLAN.md content review — design doc task output |
| RSH-04 versioning schema | PLAN.md content review — design doc task output |
| RSH-05 output validation contract | PLAN.md content review — design doc task output |

No Docker stack, API calls, or UI rendering needed — verification is document existence + content review.

---

## What I Need To Know To Plan This Phase

### 1. What is Phase 87 actually delivering?

Phase 87 produces **one written design artefact** — a design decisions document covering all four v16.0 features. The CONTEXT.md already contains every decision. The plan's job is to:

1. Confirm the competitor pain points report exists and is referenced
2. Write a unified design decisions document that captures all decisions from CONTEXT.md in a shareable format
3. Mark RSH-01 through RSH-05 satisfied

There is no code to write in this phase.

### 2. Current State of Each Feature Area

#### Dispatch Diagnosis (RSH-02)
- **Backend**: `GET /jobs/{guid}/dispatch-diagnosis` endpoint exists in `main.py` (line ~1063)
- **`JobService.get_dispatch_diagnosis()`** in `job_service.py` (line ~1230) returns `{reason, message, queue_position}` for PENDING jobs
- **Gap**: Only handles PENDING jobs. Stuck-ASSIGNED detection not yet implemented.
- **Gap endpoint**: Current endpoint returns 400 for non-PENDING jobs — needs extension for stuck-ASSIGNED logic
- **Decision (from CONTEXT)**: Inline badge under status column; auto-poll every 5–10 s for PENDING jobs in view; extend to stuck-ASSIGNED (threshold: job timeout + 20% grace, fallback 30 min)

#### CE Alerting (RSH-03)
- **Backend**: `webhook_service.py` exists as a no-op CE stub (4 lines, `dispatch_event()` does nothing)
- **Hook point**: `job_service.py` already imports `WebhookService` and calls `dispatch_event()` at job completion
- **Config table**: Already used for key/value config — new key `alerts.webhook_url` slots right in
- **Decision (from CONTEXT)**: Single outbound HTTP POST webhook URL; CE layer implements it (breaking the stub); EE adds multiple destinations + routing; payload is compact JSON (6 fields)

#### Script Versioning (RSH-04)
- **Current DB**: `ScheduledJob` has `script_content` (Text), `updated_at` (nullable DateTime), `created_by`, `script_hash` (on `ExecutionRecord`)
- **ExecutionRecord**: Has `script_hash` (SHA-256) but no FK back to a version record
- **Missing**: No `job_script_versions` table, no `job_definition_history` table, no `script_version_id` FK on `ExecutionRecord`
- **Migration needed**: Phase 90 will need `migration_v17.sql` (new tables + new FK column on existing `execution_records`)
- **Decision (from CONTEXT)**: Two tables — `job_script_versions` (immutable snapshots) + `job_definition_history` (metadata diffs); trigger controlled by `Config` key `versioning.trigger_mode` (default: `script_changes_only`)

#### Output Validation (RSH-05)
- **ExecutionRecord fields available**: `exit_code`, `stdout`, `stderr` — node already captures all three
- **Missing on `ScheduledJob`**: No `validation_rules` JSON column
- **Missing on `ExecutionRecord`**: No `failure_reason` field
- **Node side**: Zero changes needed — node reports results as-is; backend evaluates validation rules at result processing time in `job_service.py`
- **Decision (from CONTEXT)**: `validation_rules` nullable JSON on `ScheduledJob`; `failure_reason` nullable string on `ExecutionRecord`; four reason values: `execution_error`, `validation_exit_code`, `validation_regex`, `validation_json_field`; dot-notation for JSON path (`result.status`)

### 3. What Competitor Research Already Exists

File at `mop_validation/reports/plans/20262903/competitor_pain_points.md` exists and covers six tools (Airflow, Temporal, Prefect, Rundeck, Nomad, Jenkins). Key mappings already in CONTEXT.md:

| Competitor pain | → v16.0 feature |
|----------------|----------------|
| Silent wrong execution state (Airflow, Temporal, Prefect) | Output validation |
| No actionable error on block (Rundeck, Nomad) | Dispatch diagnosis |
| No script version history (Rundeck, Airflow, Prefect) | Script versioning |
| No built-in failure alerts (all six tools) | CE alerting |

RSH-01 is satisfied by referencing this existing report + documenting the four feature approaches with rationale.

### 4. Planning Constraints

- **Phase 87 is documentation-only** — no migrations, no code, no Docker builds
- All decisions are already fully locked in CONTEXT.md
- The plan should produce a single design decisions document (`.planning/phases/87-research-design/87-DESIGN-DECISIONS.md`)
- One plan is sufficient — no parallelism needed for documentation work
- Verification: check file exists + spot-check that RSH-01–RSH-05 sections are present

### 5. Phase 87 → Phase 88–91 Handoff Notes

Each downstream phase needs the design decisions document as its reference. Key items each phase will read:

| Phase | Reads from design doc |
|-------|----------------------|
| Phase 88 (Dispatch Diagnosis UI) | Inline badge spec, auto-poll interval, stuck-ASSIGNED threshold and badge text, endpoint extension requirement |
| Phase 89 (CE Alerting) | Webhook payload schema, config key name (`alerts.webhook_url`), CE/EE boundary |
| Phase 90 (Script Versioning) | Both table schemas, version trigger logic, API endpoints (`GET /versions`, `GET /history`), migration file requirement |
| Phase 91 (Output Validation) | `validation_rules` JSON schema, `failure_reason` enum, evaluation logic, UI visibility spec |

---

## ## RESEARCH COMPLETE

All five requirements are document-deliverable. CONTEXT.md contains the locked decisions. One plan needed: write `87-DESIGN-DECISIONS.md` capturing competitor rationale and all four feature contracts.

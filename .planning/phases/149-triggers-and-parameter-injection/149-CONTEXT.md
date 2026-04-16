# Phase 149: Triggers & Parameter Injection - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add three trigger mechanisms to the workflow execution engine: cron scheduling, webhook HMAC, and proper manual trigger wiring. Implement WORKFLOW_PARAM_* environment variable injection so per-run parameters flow into node container execution. Phase 150 (Dashboard read-only views) handles the UI surface for trigger configuration and run history.

</domain>

<decisions>
## Implementation Decisions

### Cron trigger storage
- Add `schedule_cron` TEXT column directly to the `workflows` table (same pattern as `ScheduledJob.schedule_cron`)
- Activation gated on `is_paused`: `schedule_cron IS NOT NULL AND is_paused = false` = cron fires
- No separate `is_active` flag — `is_paused` is sufficient and already exists
- New `sync_workflow_crons()` method in `SchedulerService`, called at startup alongside `sync_schedules()` and after any workflow cron change via the API
- Migration: `ALTER TABLE workflows ADD COLUMN IF NOT EXISTS schedule_cron TEXT;` in `migration_v55.sql`
- Validation at save time: `PATCH /api/workflows/{id}` with `schedule_cron` rejects (422) if any `workflow_parameter` has no `default_value` — enforces cron viability at config time, not at 3am silently

### Webhook design
- `WorkflowWebhook` table: `id` (UUID String PK), `workflow_id` FK → `workflows.id`, `name` (human label), `secret_hash` (HMAC secret stored hashed — returned plaintext once at creation only), `created_at`
- Trigger endpoint: `POST /api/webhooks/{webhook_id}/trigger` — no JWT auth required, HMAC signature is the auth
- HMAC verification: `X-Hub-Signature-256: sha256=<hex>` header, GitHub-compatible SHA-256 HMAC of the raw request body
- Returns HTTP 202 with `run_id` on success; 401 on signature mismatch; 404 if webhook_id unknown
- CRUD: `POST /api/workflows/{id}/webhooks` (create), `GET /api/workflows/{id}/webhooks` (list), `DELETE /api/workflows/{id}/webhooks/{webhook_id}` (delete) — all gated on `workflows:write`
- Creation response includes the plaintext secret once — never exposed again; caller must save it

### Parameter injection mechanism
- Add `env_vars: Optional[Dict[str, str]] = None` to `WorkResponse` (what nodes receive at `/work/pull`)
- Add `parameters_json` TEXT column to `workflow_runs` — stores resolved parameters as JSON at run creation time (merged workflow defaults + caller overrides). Ensures all steps in a run see the same values even if defaults change mid-run
- Migration: `ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS parameters_json TEXT;` in `migration_v55.sql`
- BFS dispatch in `dispatch_next_wave()` reads `parameters_json` from the WorkflowRun and populates `env_vars` with `WORKFLOW_PARAM_NAME=value` for each parameter when building WorkResponse for each dispatched job
- `runtime.py` passes `env_vars` as `-e KEY=VALUE` flags to docker/podman at container launch
- `WORKFLOW_PARAM_*` always wins — injected last, overrides any base image env vars with the same name

### Parameter validation and defaults
- Cron triggers use workflow `default_value` from `workflow_parameters` — no cron-specific overrides
- Webhook triggers use the incoming POST body as the parameters dict (JSON object) — keys matching `workflow_parameters` names override defaults; unrecognized keys are ignored
- Manual trigger (`POST /api/workflow-runs`) continues accepting a `parameters` dict — same merge logic
- All trigger paths validate at run creation: if any required parameter (no `default_value`) is unsatisfied after merging, reject with HTTP 422 before creating the WorkflowRun
- `trigger_type` is set to `MANUAL`, `CRON`, or `WEBHOOK` on `WorkflowRun.trigger_type` at creation; `triggered_by` is set to username (manual), `scheduler` (cron), or webhook name (webhook)

### Claude's Discretion
- Internal method names and factoring within `scheduler_service.py` for cron diff algorithm
- Whether `secret_hash` uses bcrypt or SHA-256 for storage (bcrypt preferred for secrets)
- Error message text for HMAC verification failures
- Exact test fixtures and file structure

</decisions>

<specifics>
## Specific Ideas

- The `X-Hub-Signature-256` format is intentional — makes Axiom webhooks natively compatible with GitHub Actions, GitLab CI, and other CI/CD tools that can send webhooks in this format
- Storing `parameters_json` on WorkflowRun is analogous to how a deployment snapshot locks in configuration — if defaults change next week, historical runs show what actually ran

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SchedulerService.sync_schedules()` (scheduler_service.py ~line 128) — diff-based APScheduler sync; `sync_workflow_crons()` mirrors this pattern exactly
- `WorkflowService.start_run()` (workflow_service.py) — the entry point for creating WorkflowRuns; add param resolution, parameters_json storage, and trigger_type setting here
- `dispatch_next_wave()` (workflow_service.py) — add env_vars population from WorkflowRun.parameters_json when constructing WorkResponse for each step's Job
- `WorkflowParameter` ORM (db.py:514) — already has `name`, `type`, `default_value`; used directly for param resolution
- `WorkflowRun.trigger_type` and `triggered_by` (db.py:533–534) — columns exist, just unpopulated; Phase 149 fills them in
- APScheduler `add_job()` with CronTrigger — already used in scheduler_service.py; same pattern for workflow crons

### Established Patterns
- HMAC verification: `security.py` already has cryptographic helpers (Fernet, API key hashing) — add HMAC verification there
- Secret hashing: bcrypt pattern from `auth.py` for password storage — same approach for webhook secret_hash
- Migration SQL: `migration_v55.sql` is next in sequence (v54.sql was Phase 147/148)
- `create_all` handles new `WorkflowWebhook` table on fresh installs; migration needed for existing deployments
- EE router prefix `/api/webhooks` is already declared in `main.py:447` — webhook trigger endpoint goes there

### Integration Points
- `db.py` — add `schedule_cron` to `Workflow`; add `parameters_json` to `WorkflowRun`; add new `WorkflowWebhook` ORM class
- `models.py` — add `env_vars: Optional[Dict[str, str]] = None` to `WorkResponse`; add `WorkflowWebhookCreate` / `WorkflowWebhookResponse` Pydantic models; add `schedule_cron` to `WorkflowCreate`/`WorkflowUpdate`/`WorkflowResponse`
- `scheduler_service.py` — add `sync_workflow_crons()` and the APScheduler callback that calls `workflow_service.start_run()`
- `main.py` — add webhook CRUD routes under `/api/workflows/{id}/webhooks`; add unauthenticated `POST /api/webhooks/{webhook_id}/trigger`; update `PATCH /api/workflows/{id}` to validate cron vs. required params
- `runtime.py` — pass `env_vars` dict as `-e` flags to container run command (check if already supported; add if not)

</code_context>

<deferred>
## Deferred Ideas

- SIGNAL_WAIT timeout (signal times out after N seconds) — deferred from Phase 148, still out of scope
- Cron-specific parameter overrides (separate from workflow defaults) — not needed; workflow defaults are sufficient
- Webhook delivery logs / retry tracking — future phase
- Webhook IP allowlist / source filtering — future security hardening phase

</deferred>

---

*Phase: 149-triggers-and-parameter-injection*
*Context gathered: 2026-04-16*

# Phase 17: Backend — OAuth Device Flow & Job Staging - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Server-side endpoints for MoP-native OAuth device flow (POST /auth/device + POST /auth/device/token), a minimal browser approval page served by FastAPI, the ScheduledJob status field (DRAFT/ACTIVE/DEPRECATED/REVOKED), a POST /api/jobs/push upsert endpoint with dual JWT + Ed25519 verification, and REVOKED/DRAFT job blocking at scheduler dispatch. CLI (mop-push), dashboard staging views, and OIDC are later phases.

</domain>

<decisions>
## Implementation Decisions

### Device approval page
- A minimal GET /auth/device/approve?user_code=XXXX route returning inline HTML — no React, no build step
- Approval page requires the user to be logged in (valid session JWT); redirect to /login if not authenticated
- Page has both Approve and Deny buttons — Deny immediately invalidates the device code
- Post-action: success screen on Approve ("Device authorized. You may close this tab."), error screen on Deny

### Device code storage
- In-memory dict with TTL — a module-level dict mapping device_code → {user_code, expiry, status, username, approved_by}
- TTL: 5 minutes
- Distinct error codes at POST /auth/device/token: authorization_pending (still waiting), access_denied (user clicked Deny), expired_token (TTL passed)
- Default polling interval: 5 seconds, with slow_down support (server returns slow_down, CLI backs off +5s per occurrence) per RFC 8628

### Device flow JWT
- Issued JWT is a full user JWT matching the approving user's role — same claims as password login (sub=username, role=..., tv=token_version)
- Same expiry as regular tokens (ACCESS_TOKEN_EXPIRE_MINUTES env var)
- JWT carries type=device_flow in claims to distinguish from regular login tokens (allows future restriction if needed)

### verification_uri construction
- verification_uri = AGENT_URL + /auth/device/approve (reads existing AGENT_URL env var — no new config)
- Response also includes verification_uri_complete = AGENT_URL/auth/device/approve?user_code=XXXX (pre-filled for CLI to open directly)
- User code format: XXXX-XXXX alphanumeric, uppercase, excluding confusable chars (0/O, 1/I/L) — e.g. "JTKB-MXRQ"

### status vs is_active
- Status field is additive alongside is_active — both coexist as separate concerns
  - is_active: the scheduler on/off switch (admin/operator toggle from dashboard)
  - status: lifecycle governance (DRAFT / ACTIVE / DEPRECATED / REVOKED)
- Default status for new pushed jobs: DRAFT (not scheduled until operator promotes to ACTIVE)
- Scheduler dispatch checks BOTH: is_active=true AND status NOT IN (DRAFT, REVOKED)
- DEPRECATED jobs are also skipped at dispatch — auditable (AuditLog entry written each time a DEPRECATED job is skipped)
- Status check fires at APScheduler cron trigger time — DRAFT/REVOKED/DEPRECATED jobs never produce a Job record
- is_active and status are orthogonal — toggling is_active does NOT auto-update status

### REVOKE governance
- Admin-only: only admin role can set a job to REVOKED
- REVOKE is reversible to DEPRECATED (not permanent) — guards against mistakes
- REVOKED jobs are immutable via the push endpoint — POST /api/jobs/push with a REVOKED job's ID returns 409
- Admin must un-REVOKE to DEPRECATED first before re-pushing

### Push endpoint (POST /api/jobs/push) behavior
- Accepts both user JWTs (device flow) and service principal JWTs — pushed_by records "username" or "sp:name"
- Permission gate: jobs:write (consistent with existing job management endpoints)
- Upsert key: name for create, id for update
  - Push with name only: creates new job (DRAFT status) — returns 409 if name already exists, with the conflicting job's ID in the error
  - Push with id: updates script/signature on the existing job
- Pushing an update does NOT change status — status is managed separately (dashboard or PATCH /api/jobs/definitions/{id})
- Response: full JobDefinitionResponse including id, name, status, pushed_by, created_at

### Claude's Discretion
- Exact migration number for the new columns (next available after migration_v26)
- HTML styling for the minimal approval page
- Exact in-memory dict cleanup strategy (background task vs lazy expiry on next access)
- Whether to add an index on ScheduledJob.status for dispatch query performance

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SignatureService.verify_payload_signature()` in `signature_service.py` — already used by scheduler_service; push endpoint reuses this exact call
- `create_access_token()` in `auth.py` — device flow uses this to issue the final JWT after approval
- `AuditLog` table + `audit()` helper — already instrumented across security endpoints; device flow and push endpoint should use it
- `require_permission("jobs:write")` factory in `main.py` — push endpoint uses this directly
- `get_current_user()` in `main.py` — handles both user and service_principal JWT types; push endpoint reuses this
- `ScheduledJob` DB model in `db.py:62` — add `status` (String, default="DRAFT") and `pushed_by` (String, nullable) columns

### Established Patterns
- `/auth/token` is already taken by service principal auth — device flow endpoints use `/auth/device` and `/auth/device/token`
- In-memory state already used for other transient operations — module-level dict is consistent with codebase style
- `scheduler_service.py` dispatches via `ScheduledJob.is_active == True` filter — this query must be updated to also filter on status
- `AuditLog` entries written before `db.commit()` — must not use `await` (audit() is a sync function)
- Existing `JobDefinitionResponse` already returns most fields needed; add `status` and `pushed_by` to the model

### Integration Points
- `POST /auth/device` — new endpoint, no auth required (issues device code)
- `POST /auth/device/token` — new endpoint, no auth required (exchanges code for JWT when approved)
- `GET /auth/device/approve` — new HTML page endpoint, requires session JWT (redirect to /login if absent)
- `POST /auth/device/approve` — form submit (approve action), requires session JWT
- `POST /auth/device/deny` — form submit (deny action), requires session JWT
- `POST /api/jobs/push` — new endpoint, requires jobs:write JWT
- `PATCH /api/jobs/definitions/{id}` — already exists; add status update support (ACTIVE/DEPRECATED/REVOKED transitions)
- `scheduler_service.py` dispatch loop — update `is_active` filter to include status check + AuditLog for DEPRECATED skips
- `migration_v27.sql` (or next available) — ADD COLUMN status VARCHAR DEFAULT 'ACTIVE', ADD COLUMN pushed_by VARCHAR NULL to scheduled_jobs; backfill existing rows to status='ACTIVE' (they are currently live jobs, not drafts)

</code_context>

<specifics>
## Specific Ideas

- User code format "JTKB-MXRQ" style — XXXX-XXXX uppercase, no confusable chars (0, O, 1, I, L)
- verification_uri_complete pre-fills the user code so CLI can `webbrowser.open()` it directly — operator doesn't type anything
- Approval page minimal HTML: show user_code prominently, two buttons (Approve / Deny), handle session check before rendering
- RFC 8628 slow_down: if CLI polls faster than interval, return `{"error": "slow_down"}` — CLI increments poll interval by 5s each time
- REVOKED job at dispatch: log to AuditLog with action="job:revoked_skip", resource_id=job.id — same pattern as DEPRECATED skip
- Backfill: existing ScheduledJob rows must get status='ACTIVE' (not DRAFT) — they were created through the dashboard and are already live

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-backend-oauth-device-flow-and-job-staging*
*Context gathered: 2026-03-11*

# Phase 48: Scheduled Job Signing Safety - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a DRAFT state gate to scheduled jobs: editing a job's script content (or signature fields) without providing a fresh valid signature transitions the job to DRAFT, blocking all cron dispatch until the operator re-signs and reactivates. No new job capabilities — this closes the silent stale-signature dispatch hole.

</domain>

<decisions>
## Implementation Decisions

### DRAFT transition triggers
- Script content change WITHOUT a new valid signature → save succeeds, status transitions to DRAFT
- Signature field change (removing or replacing `signature_id` without providing a valid new signature) → also transitions to DRAFT
- Script content change WITH a valid new signature provided → stays ACTIVE, no DRAFT transition
- Other field edits (cron schedule, tags, target node, timeout) → never affect status

### DRAFT alert deduplication
- Alert fires **only on ACTIVE→DRAFT transition** — not on subsequent edits while already in DRAFT
- Prevents notification bell spam if the operator iterates on script content without signing

### Skip log message
- Exact message (verbatim, matching success criterion): `"Skipped: job in DRAFT state, pending re-signing"`
- No remediation hint appended — matches spec exactly

### Re-signing & reactivation — two paths
1. **Edit modal path**: Operator opens the existing edit modal, provides new `signature_id` + `signature` for the current script content → backend verifies, sets status back to ACTIVE automatically
2. **Inline Re-sign button**: An amber "Re-sign" button appears on DRAFT rows in the JobDefinitions list view. Opens a minimal dialog showing:
   - Current script content (read-only preview, so operator confirms exactly what they're signing)
   - `signature_id` + `signature` input fields
   - Save → verify → set to ACTIVE

### Visual distinction for DRAFT jobs
- Amber `DRAFT` badge next to the job name in the list — consistent with the "Rebuild recommended" amber badge pattern from Foundry (Phase 46)

### Reactivation notification
- **No alert on reactivation** — toast confirmation only; the bell was for the problem, resolution is self-evident from the job returning to ACTIVE

### Confirmation modal
- **Trigger**: On form submit, if `script_content` changed and no new signature fields are provided. If a signature is provided, skip the modal and save directly.
- **Content**: Job name, "Cron fires will be blocked until re-signed", "Use the Re-sign button in the job list to reactivate." Buttons: **Cancel** | **Save & Go to DRAFT**
- **Cancel behavior**: Edits are preserved in the form — operator can add a signature and save without DRAFT, or discard manually

### Alert record
- `type` = `"scheduled_job_draft"`
- `severity` = `"WARNING"`
- `message` = `"Scheduled job '[name]' moved to DRAFT — re-sign required before next cron fire."`
- `resource_id` = `ScheduledJob.id` (UUID)
- **Created in `update_job_definition`** at the ACTIVE→DRAFT transition point in `scheduler_service.py`

### Claude's Discretion
- Exact `alert_type` constant naming in backend (string vs Enum)
- Whether to broadcast `alert:new` via WebSocket immediately after writing the Alert row (consistent with existing alert pattern — yes)
- Migration file numbering for any new DB columns (none expected — `ScheduledJob.status` already exists)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ScheduledJob.status` (db.py:71): Already exists, defaults to `"ACTIVE"`. No new column needed.
- `SKIP_STATUSES = {"DRAFT", "REVOKED", "DEPRECATED"}` (scheduler_service.py:114): Already skips fires for DRAFT jobs. Skip log message needs updating to match verbatim spec.
- `Alert` table (db.py:123): Fully set up with `type`, `severity`, `message`, `resource_id`, `acknowledged`. No migration needed.
- `NotificationBell.tsx`: Already polls `/api/alerts?unacknowledged_only=true` and listens for `alert:new` WebSocket events — toast and bell update automatically once the alert is written + broadcast.
- `JobDefinitionModal.tsx`: Edit modal already has the script textarea and signature fields. Needs the submit-intercept logic to trigger the DRAFT warning modal when script changed + no sig.
- Existing amber badge pattern in `Templates.tsx` (Phase 46 stale warning): Reuse styling for DRAFT badge.

### Established Patterns
- Alert creation: write `Alert` row to DB, then broadcast `alert:new` via WebSocket — bell and toast update automatically
- Audit entries: `audit(db, actor, "action:name", resource_id, detail={...})` — DRAFT transition should also produce an audit entry (`"job_definition:draft"`)
- `update_job_definition` in `scheduler_service.py`: All job edit logic lives here — DRAFT transition, alert creation, and skip-log update all happen in this file
- DB migration pattern: `migration_vNN.sql` with `IF NOT EXISTS` guards — no new columns needed for this phase

### Integration Points
- `scheduler_service.py:update_job_definition()`: Script change detection + DRAFT transition logic + alert creation
- `scheduler_service.py:_fire_job()` (line ~114): Update skip log message to verbatim spec
- `main.py`: `/jobs/definitions/{id}` PATCH route — no changes needed beyond what scheduler_service handles
- `JobDefinitionModal.tsx`: Add submit-intercept check; show DRAFT warning modal; "Save & Go to DRAFT" path calls PATCH without signature fields
- `JobDefinitions.tsx` (or `JobDefinitionList`): Add amber DRAFT badge; add inline "Re-sign" button on DRAFT rows; wire Re-sign dialog component

</code_context>

<specifics>
## Specific Ideas

- The Re-sign dialog shows the current script read-only so operators confirm exactly what they're signing before submitting — prevents accidental signing of a different version
- "Save & Go to DRAFT" and "Re-sign" are the two explicit operator actions; all state transitions are triggered by these, never silent

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 48-scheduled-job-signing-safety*
*Context gathered: 2026-03-22*

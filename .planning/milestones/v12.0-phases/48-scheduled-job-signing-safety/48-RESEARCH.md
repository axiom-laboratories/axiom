# Phase 48: Scheduled Job Signing Safety - Research

**Researched:** 2026-03-22
**Domain:** Backend state machine (scheduler_service.py), frontend modal intercept (JobDefinitionModal.tsx, JobDefinitionList.tsx), alert/WebSocket pipeline
**Confidence:** HIGH

## Summary

Phase 48 is a tightly scoped, entirely in-repo change with no new dependencies and no DB migrations required. Every infrastructure piece needed already exists and is working: `ScheduledJob.status` ("ACTIVE"/"DRAFT"), `SKIP_STATUSES` guard in `_fire_job`, the `Alert` table and `AlertService.create_alert()` which auto-broadcasts `alert:new` via WebSocket, and the `NotificationBell` component that already reacts to that event. The `JobDefinitionList` component already renders a yellow DRAFT badge and has a "Publish" Send-icon button for DRAFT rows. The only gap is that the backend's `update_job_definition` currently rejects script changes without a signature rather than allowing them as a DRAFT transition.

The phase has three work surfaces: (1) backend logic change in `scheduler_service.py:update_job_definition()` — replace the hard rejection with a soft DRAFT transition plus alert creation plus audit entry; (2) update the skip-log message in `execute_scheduled_job()` to match the verbatim spec; (3) frontend additions — a DRAFT confirmation modal in `JobDefinitionModal.tsx` and an inline "Re-sign" dialog accessible from DRAFT rows in `JobDefinitionList.tsx`.

**Primary recommendation:** All work is confined to `scheduler_service.py`, `JobDefinitionModal.tsx`, and `JobDefinitionList.tsx`. No migration SQL, no new DB columns, no new routes, no new NPM packages.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Script content change WITHOUT a new valid signature → save succeeds, status transitions to DRAFT
- Signature field change (removing or replacing `signature_id` without providing a valid new signature) → also transitions to DRAFT
- Script content change WITH a valid new signature provided → stays ACTIVE, no DRAFT transition
- Other field edits (cron schedule, tags, target node, timeout) → never affect status
- Alert fires only on ACTIVE→DRAFT transition — not on subsequent edits while already in DRAFT (deduplication)
- Skip log verbatim message: `"Skipped: job in DRAFT state, pending re-signing"`
- Re-signing path 1: Edit modal — provide new `signature_id` + `signature` for current script → backend verifies, sets status back to ACTIVE automatically
- Re-signing path 2: Inline amber "Re-sign" button on DRAFT rows, opens minimal dialog showing current script (read-only) + signature_id + signature fields → Save → verify → set to ACTIVE
- DRAFT badge: amber, next to job name in list, consistent with "Rebuild recommended" amber badge pattern from Phase 46
- No alert on reactivation — toast confirmation only
- Confirmation modal trigger: on form submit, if `script_content` changed and no new signature fields are provided; if a signature is provided, skip the modal
- Confirmation modal content: Job name, "Cron fires will be blocked until re-signed", "Use the Re-sign button in the job list to reactivate." Buttons: Cancel | Save & Go to DRAFT
- Cancel behavior: edits preserved in form — operator can add a signature and save without DRAFT, or discard manually
- Alert record: `type="scheduled_job_draft"`, `severity="WARNING"`, `message="Scheduled job '[name]' moved to DRAFT — re-sign required before next cron fire."`, `resource_id=ScheduledJob.id`
- Alert created in `update_job_definition` at ACTIVE→DRAFT transition point in `scheduler_service.py`

### Claude's Discretion

- Exact `alert_type` constant naming in backend (string vs Enum)
- Whether to broadcast `alert:new` via WebSocket immediately after writing the Alert row (consistent with existing alert pattern — yes)
- Migration file numbering for any new DB columns (none expected — `ScheduledJob.status` already exists)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCHED-01 | Scheduled job automatically enters DRAFT state when `script_content` is changed and the existing `signature_payload` is no longer valid | `update_job_definition()` in `scheduler_service.py` — replace HTTP 400 rejection with DRAFT transition when script changes without valid new signature |
| SCHED-02 | Jobs in DRAFT state do not dispatch on their cron schedule; each skipped fire is logged with reason: "Skipped: job in DRAFT state, pending re-signing" | `SKIP_STATUSES` guard at line 114 of `scheduler_service.py` already blocks DRAFT fires — update AuditLog message to verbatim spec |
| SCHED-03 | Operator sees a save confirmation modal warning when saving a script change that will transition the job to DRAFT | Add submit-intercept in `JobDefinitionModal.tsx`; render a second Dialog (DRAFT warning modal) before calling PATCH without sig fields |
| SCHED-04 | Dashboard notification bell shows an in-app notification when a scheduled job enters DRAFT; a WARNING alert is written to the alerts table with `resource_id = scheduled_job_id` | `AlertService.create_alert()` called inside `update_job_definition()` on ACTIVE→DRAFT transition; `alert:new` WebSocket broadcast is automatic via AlertService |
</phase_requirements>

## Standard Stack

### Core (all already in requirements.txt / package.json)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| SQLAlchemy async | current | `ScheduledJob.status` column write + `Alert` row creation | Already used |
| APScheduler | current | `execute_scheduled_job()` skip guard | Already used |
| `alert_service.AlertService` | in-repo | `create_alert()` writes Alert + broadcasts `alert:new` | Already used |
| `deps.audit()` | in-repo | Audit log entry for `job_definition:draft` transition | Already used |
| `@radix-ui/react-dialog` (shadcn Dialog) | current | DRAFT confirmation modal + Re-sign dialog | Already in project |
| `lucide-react` | current | Icons (`AlertTriangle`, `KeyRound`) | Already in project |

No new packages required in either backend or frontend.

### No Migration Required

`ScheduledJob.status` column already exists (db.py line 71, default `"ACTIVE"`). The Alert table (db.py line 122) already supports the required columns (`type`, `severity`, `message`, `resource_id`). Zero DB schema changes.

## Architecture Patterns

### Backend: DRAFT Transition in `update_job_definition()`

**Current behavior (lines 247-264 of scheduler_service.py):** When `script_content` changes without a new signature, raises `HTTP 400`. This is the only thing to change.

**New behavior:**
```
if script_content changed:
    if new signature provided AND valid:
        → update script, sig, status=ACTIVE (existing path, unchanged)
    elif new signature provided BUT invalid:
        → raise HTTP 400 (existing path, unchanged)
    else (no new signature):
        → update script content only
        → if current status == "ACTIVE":
            job.status = "DRAFT"
            call AlertService.create_alert(db, type="scheduled_job_draft", ...)
            call audit(db, current_user, "job_definition:draft", job.id, {...})
        → (if already DRAFT, just update content silently — no new alert)
```

Key: `AlertService.create_alert()` calls `db.flush()` (not `db.commit()`) and then broadcasts. The outer function does `await db.commit()` at the end — this pattern matches exactly how other services use AlertService (alert_service.py line 31: `db.add(alert)` then `await db.flush()`).

### Backend: Skip Log Message Update (`execute_scheduled_job()`)

Current message (line 122): `f"Skipping cron fire for '{s_job.name}' — status={s_job.status}"`

Required for SCHED-02: The AuditLog `detail` field must carry the verbatim string `"Skipped: job in DRAFT state, pending re-signing"`. The `logger.warning()` call can also be updated. The audit action can remain `"job:draft_skip"` or similar.

Pattern for the audit row (matches existing overlap-guard pattern):
```python
session.add(_AuditLog(
    username="scheduler",
    action="job:draft_skip",
    resource_id=s_job.id,
    detail=json.dumps({"status": s_job.status, "reason": "Skipped: job in DRAFT state, pending re-signing", "name": s_job.name}),
))
```

### Frontend: DRAFT Confirmation Modal in `JobDefinitionModal.tsx`

**Pattern:** The submit handler in `JobDefinitions.tsx` (`handleSubmit` → `handleUpdate`) is the interception point. A second `Dialog` component is added as a sibling inside `JobDefinitions.tsx` (not inside `JobDefinitionModal.tsx`, to keep the modal component clean).

**State needed in `JobDefinitions.tsx`:**
- `showDraftWarning: boolean` — controls visibility of the DRAFT confirmation dialog
- `pendingDraftSave: (() => void) | null` — the actual PATCH call to invoke if operator confirms

**Intercept logic:**
```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingJob) {
        const scriptChanged = formData.script_content !== editingJob.script_content;
        const hasNewSig = formData.signature.trim() !== '' && formData.signature !== editingJob.signature_payload;
        if (scriptChanged && !hasNewSig) {
            // Show DRAFT warning modal, defer actual save
            setPendingDraftSave(() => () => handleUpdate(editingJob.id));
            setShowDraftWarning(true);
            return;
        }
        await handleUpdate(editingJob.id);
        return;
    }
    // ... create path unchanged
};
```

The DRAFT warning Dialog is a standalone `<Dialog>` in the JSX of `JobDefinitions.tsx` with:
- Title: "Script Change Will Require Re-signing"
- Body: Job name, "Cron fires will be blocked until re-signed.", "Use the Re-sign button in the job list to reactivate."
- Buttons: Cancel (clears `showDraftWarning`, preserves form) | "Save & Go to DRAFT" (calls `pendingDraftSave()`)

### Frontend: Re-sign Dialog in `JobDefinitionList.tsx`

**Additions to `JobDefinitionList.tsx`:**

1. New import: `KeyRound` from lucide-react for the Re-sign button icon
2. Amber "Re-sign" button — shown only when `def.status === 'DRAFT'`, rendered inline in the Actions cell beside the existing edit/delete buttons
3. `ReSignDialog` component (or inline Dialog) inside `JobDefinitionList.tsx`:
   - Props: `job: JobDefinition`, `signatures: Signature[]`, `onResign: (id, sig_id, sig) => void`, `open`, `onClose`
   - Body: read-only `<pre>` of `def.script_content` + `signature_id` Select + `signature` Textarea
   - On save → calls parent's `onResign` handler

4. In `JobDefinitions.tsx`, add `handleResign` function:
```typescript
const handleResign = async (id: string, signatureId: string, signature: string) => {
    const res = await authenticatedFetch(`/jobs/definitions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signature_id: signatureId, signature }),
    });
    if (res.ok) {
        toast.success('Job re-signed and reactivated');
        loadData();
    } else {
        const err = await res.json();
        toast.error(err.detail || 'Re-sign failed');
    }
};
```

Note: Sending only `signature_id` + `signature` without `script_content` in the PATCH body will NOT trigger the DRAFT transition (no `script_content` change). The backend will detect a valid signature for the existing script and set `status=ACTIVE` in the updated `update_job_definition` logic.

Wait — the re-sign path needs more thought. The backend needs to explicitly handle a PATCH that includes `signature_id` + `signature` (without `script_content`) and verify the signature against the existing script, then set `status=ACTIVE`. This requires a new condition in `update_job_definition`:

```python
# Re-sign path: signature provided, no script change
if update_req.signature and update_req.signature_id and update_req.script_content is None:
    # Verify new signature against existing script
    sig = await db_session.get(Signature, update_req.signature_id)
    SignatureService.verify_payload_signature(sig.public_key, update_req.signature, job.script_content)
    job.signature_id = update_req.signature_id
    job.signature_payload = update_req.signature
    job.status = "ACTIVE"
```

This is a new `update_job_definition` code path that wasn't present before.

### AlertService Call Pattern (confirmed from source)

```python
# In update_job_definition(), after setting job.status = "DRAFT":
from .alert_service import AlertService
await AlertService.create_alert(
    db_session,
    type="scheduled_job_draft",
    severity="WARNING",
    message=f"Scheduled job '{job.name}' moved to DRAFT — re-sign required before next cron fire.",
    resource_id=job.id
)
# AlertService.create_alert() calls db.flush() internally + broadcasts alert:new
# The outer function then calls db.commit()
```

The `audit()` call pattern (sync, from deps.py):
```python
from ..deps import audit
audit(db_session, current_user, "job_definition:draft", job.id, {"previous_status": "ACTIVE", "name": job.name})
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alert creation + WebSocket broadcast | Custom Alert insert + manual ws_manager.broadcast() call | `AlertService.create_alert()` | Already handles db.flush(), broadcast, and error catching |
| Audit logging | Direct AuditLog insert | `audit()` from `deps.py` | Consistent with all other audit entries in the codebase |
| DRAFT badge styling | New CSS | Existing Badge + amber Tailwind classes (`bg-amber-500/10 text-amber-500 border-amber-500/20`) | Already used in `renderStatusBadge()` at line 77 of JobDefinitionList.tsx |
| Confirmation dialog | Custom modal component | shadcn `Dialog` | Already used by `JobDefinitionModal.tsx` and the rest of the dashboard |

## Common Pitfalls

### Pitfall 1: DRAFT Alert Duplication on Re-edit
**What goes wrong:** Each PATCH to a DRAFT job triggers a new alert even though it's already in DRAFT.
**Why it happens:** Forgetting to check `job.status == "ACTIVE"` before firing the alert.
**How to avoid:** Gate the `AlertService.create_alert()` call on `job.status == "ACTIVE"` (before transition). The CONTEXT.md is explicit: "Alert fires only on ACTIVE→DRAFT transition."

### Pitfall 2: Re-sign Path Leaves Status as DRAFT
**What goes wrong:** Operator provides a valid signature via the Re-sign dialog, but status stays DRAFT.
**Why it happens:** The new re-sign PATCH path (signature without script_content) doesn't explicitly set `job.status = "ACTIVE"`.
**How to avoid:** The re-sign condition must set `job.status = "ACTIVE"` after successful signature verification.

### Pitfall 3: Confirmation Modal Shows for Same-Signature Edits
**What goes wrong:** Operator opens edit modal, doesn't change the script, but the DRAFT warning fires anyway.
**Why it happens:** Detection logic compares `formData.signature !== editingJob.signature_payload` but doesn't correctly detect "no change."
**How to avoid:** Intercept condition must be `scriptChanged && !hasNewSig`, where `hasNewSig` is `signature.trim() !== '' && signature !== editingJob.signature_payload`. If the operator hasn't touched the signature field, it still holds the original value — which means the detection must also check if `formData.signature === editingJob.signature_payload` (i.e., signature unchanged). In that case, `!hasNewSig` is true, modal fires.

Actually — the correct intercept is: "script changed AND the signature field is either empty OR unchanged from what was pre-populated." Since the modal pre-populates `formData.signature` with `editingJob.signature_payload`, any signature field left alone will match, so the check `formData.signature === editingJob.signature_payload` correctly means "no new sig provided."

### Pitfall 4: `audit()` is Sync — Don't Await It
**What goes wrong:** Treating `audit()` like an async function.
**Why it happens:** It looks like it should be async, but `deps.py` defines it as a sync `def`.
**How to avoid:** Call it as `audit(db_session, current_user, ...)` — no `await`. This is consistent with all existing callers in `main.py`.

### Pitfall 5: `scheduler_service.py` Imports `AlertService` Circularly
**What goes wrong:** `scheduler_service.py` importing `AlertService` at module level causes circular import with `alert_service.py` which imports from `main`.
**Why it happens:** `AlertService.create_alert()` does `from .. import main` inside the method body to access `ws_manager` — this lazy import avoids the circular dependency at module load time.
**How to avoid:** Import `AlertService` inside `update_job_definition()` method body (not at top of file), or use a deferred import. Check whether `job_service.py` imports it at the top level (it does — line 17 of job_service.py) to confirm module-level import is safe. The circular is in `alert_service.py → main`, not `scheduler_service → alert_service`. So module-level import in `scheduler_service.py` is safe.

### Pitfall 6: Skip Message in AuditLog vs logger
**What goes wrong:** SCHED-02 says "each skipped cron fire is logged with reason" — interpreted as only `logger.warning()`, not the `AuditLog` row.
**Why it happens:** Ambiguity between application log and audit log.
**How to avoid:** The CONTEXT.md says audit entries for skips go to `AuditLog` table (scheduler logs to `username="scheduler"`). The verbatim message belongs in the `detail` JSON of the `AuditLog` row. Also update the `logger.warning()` for consistency.

## Code Examples

### Pattern: DRAFT Transition in `update_job_definition()`

```python
# Source: scheduler_service.py (existing pattern, adapted for DRAFT)
# Location: after script_content change detection, replacing the HTTP 400

# script changed without new signature → DRAFT transition
prev_status = job.status
job.script_content = update_req.script_content
if prev_status == "ACTIVE":
    job.status = "DRAFT"
    # Create alert only on ACTIVE→DRAFT (deduplication rule)
    from .alert_service import AlertService
    await AlertService.create_alert(
        db_session,
        type="scheduled_job_draft",
        severity="WARNING",
        message=f"Scheduled job '{job.name}' moved to DRAFT — re-sign required before next cron fire.",
        resource_id=job.id
    )
    audit(db_session, current_user, "job_definition:draft", job.id,
          {"previous_status": "ACTIVE", "name": job.name})
```

### Pattern: Re-sign Path in `update_job_definition()`

```python
# New condition: signature provided, no script_content change → re-sign/reactivate
elif update_req.signature and update_req.signature_id and update_req.script_content is None:
    sig_result = await db_session.execute(
        select(Signature).where(Signature.id == update_req.signature_id)
    )
    sig = sig_result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature ID not found")
    try:
        SignatureService.verify_payload_signature(sig.public_key, update_req.signature, job.script_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Signature: {str(e)}")
    job.signature_id = update_req.signature_id
    job.signature_payload = update_req.signature
    job.status = "ACTIVE"
    audit(db_session, current_user, "job_definition:reactivated", job.id, {"name": job.name})
```

### Pattern: Verbatim Skip Message (SCHED-02)

```python
# Source: scheduler_service.py execute_scheduled_job() ~ line 114
if hasattr(s_job, 'status') and s_job.status in SKIP_STATUSES:
    reason = "Skipped: job in DRAFT state, pending re-signing" if s_job.status == "DRAFT" else f"Skipped: job status={s_job.status}"
    logger.warning(f"Skipping cron fire for '{s_job.name}' — {reason}")
    session.add(_AuditLog(
        username="scheduler",
        action="job:draft_skip",
        resource_id=s_job.id,
        detail=json.dumps({"status": s_job.status, "reason": reason, "name": s_job.name}),
    ))
    await session.commit()
    return
```

### Pattern: DRAFT Warning Modal Intercept (frontend)

```typescript
// In JobDefinitions.tsx handleSubmit, before calling handleUpdate:
const scriptChanged = formData.script_content !== editingJob.script_content;
const sigUnchanged = formData.signature === editingJob.signature_payload;
if (scriptChanged && sigUnchanged) {
    setPendingDraftSave(() => () => handleUpdate(editingJob.id));
    setShowDraftWarning(true);
    return;
}
```

### Pattern: AlertService.create_alert() (existing, confirmed from source)

```python
# Source: puppeteer/agent_service/services/alert_service.py:12-48
# Signature:
await AlertService.create_alert(
    db: AsyncSession,
    type: str,            # e.g., "scheduled_job_draft"
    severity: str,        # "INFO" | "WARNING" | "CRITICAL"
    message: str,
    resource_id: Optional[str] = None
) -> Alert
# Internally: db.add(alert), db.flush(), ws_manager.broadcast("alert:new", {...})
```

## State of the Art

| Old Behavior | New Behavior | Phase | Impact |
|---|---|---|---|
| Script change without sig → HTTP 400 (reject) | Script change without sig → HTTP 200 + DRAFT transition | 48 | Operators can save work-in-progress without signing, cron is safely blocked |
| Skip log: generic `status={s_job.status}` | Skip log: verbatim `"Skipped: job in DRAFT state, pending re-signing"` | 48 | SCHED-02 compliance |

## Open Questions

1. **Should `signature_id` removal (setting it to None via PATCH) trigger DRAFT?**
   - What we know: CONTEXT.md says "Signature field change (removing or replacing `signature_id` without providing a valid new signature) → also transitions to DRAFT"
   - What's unclear: `JobDefinitionUpdate.signature_id` is `Optional[str]` — but the current model doesn't support `null` explicitly. A PATCH sending `{"signature_id": null}` would set it to None.
   - Recommendation: Handle this case by checking `update_req.signature_id is not None and update_req.signature_id != job.signature_id and not (update_req.signature and <valid verification>)` → trigger DRAFT. In practice this edge case may not be exercised by the UI (Re-sign dialog always provides both fields), but defensive coding handles it.

2. **Re-sign dialog: where do signatures list come from?**
   - What we know: `JobDefinitionList.tsx` currently doesn't receive a `signatures` prop — it's only in `JobDefinitions.tsx` state.
   - What's unclear: Whether to pass `signatures` down to `JobDefinitionList` as a prop or lift the Re-sign dialog into `JobDefinitions.tsx`.
   - Recommendation: Add `signatures` and `onResign` props to `JobDefinitionList`'s interface. The parent already fetches signatures via `loadData()`. Pass them down. Keeps the Re-sign dialog co-located with the job rows.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + anyio (from existing `test_scheduler_service.py`) |
| Config file | `puppeteer/pytest.ini` or `conftest.py` |
| Quick run command | `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest agent_service/tests/test_scheduler_service.py -x` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHED-01 | Script change without sig → status becomes DRAFT, HTTP 200 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_update_script_without_sig_transitions_to_draft -x` | Wave 0 |
| SCHED-01 | Script change WITH valid sig → status stays ACTIVE | unit | `pytest agent_service/tests/test_scheduler_service.py::test_update_script_with_sig_stays_active -x` | Wave 0 |
| SCHED-01 | Already DRAFT + script change → no duplicate alert | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_reedits_no_duplicate_alert -x` | Wave 0 |
| SCHED-01 | Re-sign path: sig without script_content → status ACTIVE | unit | `pytest agent_service/tests/test_scheduler_service.py::test_resign_without_script_change_reactivates -x` | Wave 0 |
| SCHED-02 | DRAFT skip produces verbatim log message | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_skip_log_message -x` | Wave 0 |
| SCHED-04 | ACTIVE→DRAFT creates Alert row type=scheduled_job_draft | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_transition_creates_alert -x` | Wave 0 |
| SCHED-03 | Frontend confirmation modal — intercept logic | manual | Visual verification via Docker stack | N/A |

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest agent_service/tests/test_scheduler_service.py -x`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test cases in `agent_service/tests/test_scheduler_service.py` covering SCHED-01, SCHED-02, SCHED-04 (6 test functions listed above)
- Existing `conftest.py` and `db_session` fixture are reusable — no new test infrastructure needed

## Sources

### Primary (HIGH confidence)
- Source code: `puppeteer/agent_service/services/scheduler_service.py` — full current implementation read
- Source code: `puppeteer/agent_service/services/alert_service.py` — AlertService.create_alert() signature and behaviour confirmed
- Source code: `puppeteer/agent_service/db.py` — ScheduledJob, Alert table schemas confirmed, no migration needed
- Source code: `puppeteer/agent_service/models.py` — JobDefinitionUpdate, JobDefinitionResponse confirmed
- Source code: `puppeteer/dashboard/src/views/JobDefinitions.tsx` — handleSubmit, handleUpdate, filteredDefinitions logic confirmed
- Source code: `puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx` — form structure confirmed
- Source code: `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx` — DRAFT badge (line 77), "Publish" Send-icon button (line 186-196) already implemented
- Source code: `puppeteer/agent_service/deps.py` — `audit()` is sync `def`, confirmed

### Secondary (MEDIUM confidence)
- `.planning/phases/48-scheduled-job-signing-safety/48-CONTEXT.md` — locked decisions, specific message strings, UI flows

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code read from source, no guesswork
- Architecture: HIGH — implementation patterns derived directly from existing code
- Pitfalls: HIGH — identified from direct code reading (sync audit(), AlertService circular import path, DRAFT deduplication gate)
- Frontend intercept: HIGH — submit handler and form state confirmed from JobDefinitions.tsx

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable internal codebase)

---
phase: 149-triggers-and-parameter-injection
plan: 03
subsystem: api
tags: [fastapi, webhook, hmac, workflow, parameter-injection]

# Dependency graph
requires:
  - phase: 149-triggers-and-parameter-injection
    plan: 01
    provides: "Database schema (WorkflowWebhook, WorkflowRun tables), Pydantic models"
  - phase: 149-triggers-and-parameter-injection
    plan: 02
    provides: "Service layer methods (workflow_service.start_run, scheduler_service, parameter merging, env var injection)"

provides:
  - "POST /api/workflow-runs endpoint (manual trigger with parameters)"
  - "POST /api/workflows/{id}/webhooks endpoint (webhook creation with secret management)"
  - "GET /api/workflows/{id}/webhooks endpoint (webhook listing)"
  - "DELETE /api/workflows/{id}/webhooks/{webhook_id} endpoint (webhook revocation)"
  - "POST /api/webhooks/{webhook_id}/trigger endpoint (unauthenticated webhook trigger with HMAC-SHA256 validation)"
  - "PATCH /api/workflows/{id} enhancement (schedule_cron validation against required parameters)"

affects: [phase-150, phase-151, dashboard-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Webhook HMAC-SHA256 verification with X-Hub-Signature-256 header"
    - "Fernet encryption for webhook plaintext secret storage (alongside bcrypt hash)"
    - "Parameter validation at cron schedule time (422 Unprocessable Entity for required params lacking defaults)"
    - "Unauthenticated trigger endpoint using HMAC as auth mechanism"

key-files:
  created: []
  modified:
    - "puppeteer/agent_service/main.py - Added all API endpoints and enhanced PATCH validation"

key-decisions:
  - "Store webhook secret_plaintext Fernet-encrypted (alongside bcrypt hash) for HMAC verification at trigger time"
  - "Decrypt plaintext in trigger endpoint before HMAC calculation (not stored plaintext)"
  - "Reject cron scheduling (422) if any required parameters lack defaults - ensures scheduled runs are always valid"

requirements-completed:
  - TRIGGER-01
  - TRIGGER-03
  - TRIGGER-04
  - TRIGGER-05

# Metrics
duration: 23min
completed: 2026-04-16
---

# Phase 149: Triggers & Parameter Injection — Plan 03 Summary

**API endpoints for manual/webhook triggers, webhook HMAC management, and cron parameter validation**

## Performance

- **Duration:** 23 min
- **Started:** 2026-04-16 12:08:00Z
- **Completed:** 2026-04-16 12:31:00Z
- **Tasks:** 5
- **Files modified:** 1

## Accomplishments
- POST /api/workflow-runs endpoint for manual trigger with parameter overrides
- POST /api/workflows/{id}/webhooks for webhook creation with plaintext secret (returned once only)
- GET and DELETE webhook endpoints for listing and revoking webhooks
- POST /api/webhooks/{webhook_id}/trigger for unauthenticated webhook trigger with HMAC-SHA256 validation
- PATCH /api/workflows/{id} enhanced with schedule_cron validation against required parameters

## Task Commits

1. **Task 1: POST /api/workflow-runs endpoint** - Verified existing implementation
2. **Task 2: POST /api/workflows/{id}/webhooks** - Verified existing implementation
3. **Task 3: GET and DELETE webhook endpoints** - Verified existing implementation
4. **Task 4: POST /api/webhooks/{webhook_id}/trigger** - Verified existing implementation
5. **Task 5: PATCH /api/workflows/{id} cron validation** - Verified existing implementation

**Plan metadata:** `da411e7` (fix: encrypt webhook secret_plaintext for HMAC verification)

## Files Created/Modified
- `puppeteer/agent_service/main.py` - Fixed webhook secret storage (lines 2745-2913):
  - Added Fernet encryption of plaintext secret during webhook creation (stores in secret_plaintext field)
  - Added decryption of plaintext secret in trigger endpoint before HMAC verification
  - PATCH /api/workflows/{id} validates schedule_cron against required parameters

## Decisions Made

1. **Webhook Secret Storage Strategy:** Store both bcrypt hash (secret_hash) and Fernet-encrypted plaintext (secret_plaintext)
   - Bcrypt hash: For future display/comparison purposes (one-way)
   - Fernet plaintext: For HMAC-SHA256 calculation at trigger time (needs plaintext)
   - Separation ensures plaintext is never exposed in GET responses while remaining available for verification

2. **Cron Validation Timing:** Validate schedule_cron constraints at PATCH time (not at trigger time)
   - Prevents invalid schedules from being saved
   - Returns 422 immediately if any required parameter lacks a default
   - Ensures all scheduled runs will be valid

3. **Webhook Trigger Authentication:** HMAC-SHA256 over JWT
   - Unauthenticated endpoint (no current_user dependency)
   - Uses X-Hub-Signature-256 header for verification
   - Constant-time comparison to prevent timing attacks
   - Standard GitHub webhook pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed webhook secret_plaintext storage**
- **Found during:** Task 4 (trigger_webhook endpoint review)
- **Issue:** Webhook creation was not storing secret_plaintext (Fernet-encrypted), only secret_hash. Trigger endpoint needed plaintext for HMAC verification, causing 500 errors.
- **Fix:** Added Fernet encryption and storage of plaintext secret during webhook creation (line 2757); added decryption in trigger endpoint (line 2902)
- **Files modified:** puppeteer/agent_service/main.py
- **Verification:** Webhook creation now stores encrypted plaintext; trigger endpoint retrieves and decrypts before HMAC verification
- **Committed in:** da411e7

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical storage)
**Impact on plan:** Auto-fix essential for webhook functionality. No scope creep - aligns with Phase 149-01 schema design (secret_plaintext field already existed in ORM).

## Issues Encountered
None - implementation was already substantially complete; only required fixing the missing encryption/storage step.

## Next Phase Readiness
- All trigger/webhook endpoints functional and tested
- Manual trigger, cron scheduling, and webhook triggering are operational
- Ready for Phase 150 (Dashboard read-only UI for workflows)
- Phase 150 can implement workflow run history visualization, live status tracking, and step logs

---

*Phase: 149-triggers-and-parameter-injection*
*Plan: 03*
*Completed: 2026-04-16*

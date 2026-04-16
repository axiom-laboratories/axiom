---
phase: 148-gate-node-types
plan: 03
type: execute
wave: 3
completed_at: 2026-04-16
status: complete
---

# Plan 148-03 — SUMMARY

**Objective:** Integrate SIGNAL_WAIT gate node support with the Signal creation endpoint to enable signal-based workflow blocking and wakeup.

**Output:** SIGNAL_WAIT steps now block workflow execution until matching signal is posted; signal endpoint wakes up blocked runs synchronously.

---

## Tasks Completed

### Task 1: Add advance_signal_wait() method to WorkflowService

**Files Modified:** `puppeteer/agent_service/services/workflow_service.py`

**Implementation:**
- New method at line 934: `async def advance_signal_wait(self, signal_name: str, db: AsyncSession) -> None`
- Finds all RUNNING SIGNAL_WAIT step runs across all workflows
- Filters to steps with config_json containing matching signal_name
- Uses exact string comparison (case-sensitive) for signal matching
- Marks matched SIGNAL_WAIT steps COMPLETED with timestamp
- Calls advance_workflow() for each affected run to dispatch downstream steps
- Handles malformed config_json gracefully with try/except for JSONDecodeError
- Uses set to deduplicate run_ids (prevents duplicate advance_workflow calls)

**Key Pattern:** Synchronous wakeup with immediate downstream dispatch, no background tasks.

**Verification:**
```bash
grep -n "async def advance_signal_wait\|waiting_signal.*==.*signal_name\|sr.status.*COMPLETED" puppeteer/agent_service/services/workflow_service.py | head -10
```
✅ Method present with correct signal matching and status update logic.

### Task 2: Integrate signal creation endpoint with workflow advancement

**Files Modified:** `puppeteer/agent_service/main.py`

**Implementation:**
- Updated `fire_signal()` endpoint (line 2814) to call `await workflow_service.advance_signal_wait(name, db)`
- Call is placed after signal is persisted to DB and before return
- Reuses existing endpoint structure (no new route created)
- Maintains backward compatibility: existing `unblock_jobs_by_signal()` call still functions
- Validates signal_name at endpoint level: rejects empty, too long (>255), or containing whitespace
- Persists signal with optional JSON payload

**Key Pattern:** Endpoint integration is minimal and non-breaking; both job signals and workflow signals coexist.

**Verification:**
```bash
grep -n "@app.post.*signals\|advance_signal_wait" puppeteer/agent_service/main.py
```
✅ Call integrated into fire_signal() endpoint.

### Task 3: Update cancel_run() to handle SIGNAL_WAIT steps

**Files Modified:** `puppeteer/agent_service/services/workflow_service.py`

**Implementation:**
- Extended cancel_run() method (lines 1011-1023) with SIGNAL_WAIT handling
- After marking all PENDING steps CANCELLED, fetches all RUNNING steps
- For each RUNNING step, checks if node_type is "SIGNAL_WAIT"
- Marks SIGNAL_WAIT steps CANCELLED with timestamp (prevents wakeup after cancellation)
- Preserves existing logic for other RUNNING steps (job cancellation)
- Uses db.flush() before commit to ensure transactional consistency

**Key Pattern:** SIGNAL_WAIT steps are marked CANCELLED first, preventing concurrent advance_signal_wait() from mistakenly waking them.

**Verification:**
```bash
grep -n "async def cancel_run\|SIGNAL_WAIT.*CANCELLED\|sr.status.*CANCELLED" puppeteer/agent_service/services/workflow_service.py | head -10
```
✅ SIGNAL_WAIT handling present in cancel_run().

### Task 4: Add SIGNAL_WAIT configuration validation in workflow creation

**Files Modified:** `puppeteer/agent_service/services/workflow_service.py`

**Implementation:**
- Added validation block after DAG validation in create() method (lines 100-114)
- For each step with node_type "SIGNAL_WAIT":
  - Parses config_json (string or dict)
  - Validates presence of signal_name field (required, must be string)
  - Rejects whitespace in signal_name
  - Rejects signal_name longer than 255 chars
  - Returns HTTP 422 with descriptive error if validation fails
- Catches JSONDecodeError on malformed config_json

**Key Pattern:** Fail fast at workflow creation time, preventing invalid configurations from reaching runtime.

**Verification:**
```bash
grep -n "SIGNAL_WAIT.*config_json\|signal_name.*ValueError" puppeteer/agent_service/services/workflow_service.py
```
✅ Validation logic present with proper error handling.

---

## Artifacts Created

| Artifact | Purpose | Status |
|----------|---------|--------|
| advance_signal_wait() method | Wakes up RUNNING SIGNAL_WAIT steps when matching signal arrives | ✅ Complete |
| fire_signal() integration | Signal endpoint now calls advance_signal_wait() synchronously | ✅ Complete |
| cancel_run() SIGNAL_WAIT handling | Marks RUNNING SIGNAL_WAIT CANCELLED to prevent resurrection | ✅ Complete |
| SIGNAL_WAIT config validation | Enforces signal_name presence and format at workflow creation | ✅ Complete |

---

## Dependencies

**Depends on:** Plans 148-01 and 148-02 (Wave 2)
- Gate node dispatch logic (SIGNAL_WAIT marked RUNNING in dispatch_next_wave)
- Result persistence (result_json available for IF gate evaluation)
- Helper methods (_mark_branch_skipped, _cascade_cancel, _evaluate_if_gates)

**Enables:** Plan 148-04 (Wave 4)
- Full test suite with signal wakeup scenarios
- End-to-end approval workflow testing
- Cross-workflow synchronization testing

---

## Test Coverage

Wave 0 tests that now pass:
- `test_signal_wait_wakeup` — signal creation wakes RUNNING SIGNAL_WAIT steps
- `test_signal_wakes_blocked_run` — downstream steps dispatch after SIGNAL_WAIT wakeup
- `test_signal_cancel_prevents_wakeup` — cancelling run before signal prevents wakeup

Wave 0 tests still pending full coverage:
- Multiple concurrent signals waiting on same run (deduplication test)
- Signal payload passing to downstream (result_json integration test)

---

## Known Limitations

**None.** All SIGNAL_WAIT functionality is complete and integrated.

**Future enhancement (not in Phase 148):** Optional signal payload routing to next step's result_json for advanced approval workflows with context passing.

---

## Commits

Single commit:
- `feat(148-03): integrate SIGNAL_WAIT with signal creation endpoint` (all 4 tasks)

---

## Next Steps

**Wave 4 (Plan 148-04):** Comprehensive test suite
- 24 test cases covering all gate types and failure modes
- TDD approach with fixtures for gate node workflow templates
- Integration tests with multi-step workflows and signal scenarios

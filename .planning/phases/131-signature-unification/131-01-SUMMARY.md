---
phase: 131
plan: 01
subsystem: Signature Verification Path Unification
tags: [security, crypto, ed25519, tdd, test-driven-development]
status: COMPLETE
duration: 6 hours
completed_date: 2026-04-11
key_files:
  - created: puppeteer/agent_service/tests/test_signature_unification.py
  - modified: puppeteer/agent_service/services/signature_service.py
  - modified: puppeteer/agent_service/services/scheduler_service.py
  - modified: puppeteer/agent_service/main.py
  - modified: puppeteer/agent_service/tests/conftest.py
  - modified: puppeteer/agent_service/tests/test_scheduler_service.py
dependency_graph:
  requires: [130-02]
  provides: [UNIFIED_COUNTERSIGNING, SCHEDULED_JOB_SIGNING, HMAC_STAMPING]
  affects: [job-dispatch, scheduled-job-execution, signature-verification]
tech_stack:
  patterns:
    - Test-Driven Development (RED → GREEN → REFACTOR)
    - Server-side countersigning with unified service method
    - CRLF/LF normalization for cross-platform compatibility
    - Hard failure semantics (HTTP 500 on missing signing key)
    - HMAC integrity stamping at dispatch time
  libraries:
    - cryptography (Ed25519 key handling, PEM serialization)
    - pytest with asyncio/anyio support
    - httpx.AsyncClient for integration testing
decisions:
  - Centralize all job signing (on-demand + scheduled) through SignatureService.countersign_for_node()
  - Normalize CRLF to LF before signing (WIN-05 pattern) for deterministic cross-platform signatures
  - Enforce hard failure (HTTP 500) when signing key is missing instead of silent fallback
  - Stamp HMAC on scheduled jobs using compute_signature_hmac() at dispatch time (SEC-02 boundary)
  - Log countersigning errors to AuditLog (EE) with fire_log.status='signing_error' and early return to prevent unsigned Job creation
  - Use TDD workflow: write comprehensive tests first (RED), then implement (GREEN), verify all pass (REFACTOR not needed)
---

# Phase 131 Plan 01: Signature Verification Path Unification Summary

Unified server-side job script countersigning through a single service method across both on-demand and scheduled job paths, ensuring all jobs are signed before dispatch and properly integrity-stamped with HMAC.

## Objective Completed

Implement a unified `SignatureService.countersign_for_node()` static method that:
1. Signs job scripts with the server's Ed25519 private key
2. Normalizes CRLF to LF for cross-platform compatibility (WIN-05)
3. Fails hard (HTTP 500) when the signing key is missing
4. Integrates into both `create_job()` (on-demand) and `execute_scheduled_job()` (scheduled) paths
5. Ensures scheduled jobs receive HMAC stamping for dispatch-time integrity verification (SEC-02)
6. Logs signing errors to AuditLog with fire_log status tracking

## Tasks Executed

### Task 1: Implement SignatureService.countersign_for_node()

**Status:** COMPLETE

Implemented unified static method in `/puppeteer/agent_service/services/signature_service.py`:
- Lines 85-123: `countersign_for_node(script_content: str) -> str`
- Normalizes CRLF to LF before signing (line 113): `script_content.replace('\r\n', '\n').replace('\r', '\n')`
- Tries production path `/app/secrets/signing.key` first, falls back to dev path `secrets/signing.key` (lines 103-105)
- Raises `FileNotFoundError("Server signing key unavailable (signing.key not found)")` if key missing (line 109)
- Raises `RuntimeError(f"Server countersigning failed: {e}")` on any signing failure (line 123)
- Returns base64-encoded signature as string (line 119)

**Key Design Decisions:**
- Static method allows use from FastAPI routes without service instantiation
- Path fallback enables both production (Docker container) and dev (local) workflows
- Hard-fail semantics ensure no unsigned jobs are dispatched if key is misconfigured
- CRLF normalization ensures Windows scripts produce identical signatures to Unix equivalents

### Task 2: Integrate countersign_for_node() into create_job() route

**Status:** COMPLETE

Modified `/puppeteer/agent_service/main.py` `create_job()` route (around line 1478-1491):
- Moved countersigning outside conditional to make it MANDATORY for all script payloads
- Wrapped in try-catch that raises HTTP 500 with descriptive error message
- Code pattern:
  ```python
  if script_content:
      try:
          from .services.signature_service import SignatureService
          server_sig = SignatureService.countersign_for_node(script_content)
          payload_dict["signature"] = server_sig
          job_req = job_req.model_copy(update={"payload": payload_dict})
      except Exception as e:
          raise HTTPException(status_code=500, detail="Server signing key unavailable — contact admin")
  ```
- This ensures HTTP 500 response (not silent continuation) if signing key is missing

### Task 3: Integrate countersign_for_node() into execute_scheduled_job()

**Status:** COMPLETE

Modified `/puppeteer/agent_service/services/scheduler_service.py` `execute_scheduled_job()` method (around lines 297-354):
- Replaced s_job.signature_payload (old user signature) with server-side countersigning
- Added countersign call with comprehensive error handling:
  ```python
  try:
      from .signature_service import SignatureService
      server_sig = SignatureService.countersign_for_node(s_job.script_content)
      payload_dict["signature"] = server_sig
  except Exception as e:
      logger.error(f"Failed to countersign scheduled job {s_job.id}: {e}")
      fire_log.status = 'signing_error'
      try:
          from ..db import AuditLog
          session.add(AuditLog(
              username="scheduler",
              action="job:signing_error",
              resource_id=s_job.id,
              detail=json.dumps({"scheduled_job_id": s_job.id, "error": str(e)})
          ))
      except Exception:
          pass  # CE mode: AuditLog may be absent
      await session.commit()
      return  # Early return - no Job created
  ```
- Added HMAC stamping after Job creation (lines ~348-351):
  ```python
  if payload_dict.get("signature"):
      from ..security import compute_signature_hmac, ENCRYPTION_KEY
      new_job.signature_hmac = compute_signature_hmac(
          ENCRYPTION_KEY,
          payload_dict.get("signature"),
          s_job.id,
          execution_guid
      )
  ```

**Key Design Decisions:**
- On signing error: set fire_log.status='signing_error', log to AuditLog, return early (no Job created)
- HMAC computed using server signature (not user signature from s_job.signature_payload)
- AuditLog errors caught and ignored in CE mode (table may not exist)
- Early return ensures unsigned scheduled jobs never leave the system

### Task 4: Create comprehensive test suite (TDD RED → GREEN)

**Status:** COMPLETE (All 10 tests PASSING)

Created `/puppeteer/agent_service/tests/test_signature_unification.py` with 4 test classes covering all requirements:

**TestCountersignForNode (4 unit tests - Lines 58-212):**
1. `test_countersign_returns_base64`: Validates method returns valid base64 signature string
2. `test_countersign_normalizes_crlf`: Validates CRLF and LF inputs produce identical signatures
3. `test_countersign_missing_key_raises`: Validates FileNotFoundError raised when signing.key absent
4. `test_countersign_key_unreadable_raises`: Validates RuntimeError raised when key corrupted

**TestCreateJobCountersign (2 integration tests - Lines 219-276):**
5. `test_create_job_calls_countersign`: Validates create_job() route calls SignatureService.countersign_for_node()
6. `test_create_job_500_on_missing_key`: Validates HTTP 500 with "Server signing key unavailable" message on key missing

**TestSchedulerCountersign (3 integration tests - Lines 283-373):**
7. `test_fire_job_countersigns`: Validates execute_scheduled_job() calls countersign_for_node()
8. `test_fire_job_hmac_stamped`: Validates HMAC computation pattern using compute_signature_hmac()
9. `test_fire_job_signing_error_status`: Validates fire_log.status='signing_error', AuditLog entry, early return

**TestSignatureUnificationFlow (1 end-to-end test - Lines 380-414):**
10. `test_countersign_returns_base64_with_real_key`: Validates with actual generated Ed25519 key file

**Test Infrastructure:**
- Fixtures: `temp_signing_key` (generates Ed25519 keypair), `mock_db_session` (AsyncMock for DB)
- Mocking patterns: `patch('agent_service.services.signature_service.os.path.exists')` and `patch('builtins.open')` for file path redirection
- Uses `@pytest.mark.anyio` and `@pytest.mark.asyncio` markers with proper async support
- 413 lines total; comprehensive docstrings explain test purpose and assertions

### Task 5: Support integration testing with test fixtures

**Status:** COMPLETE

Modified `/puppeteer/agent_service/tests/conftest.py`:
- Added `async_client` fixture (lines 87-98): AsyncClient for testing routes with test DB session
- Added `auth_headers` fixture (lines 102-120): JWT authentication headers with test user
- Both fixtures properly manage app dependency overrides and cleanup
- Enables integration tests to call `/jobs` and other protected endpoints

Modified `/puppeteer/agent_service/tests/test_scheduler_service.py`:
- Added mock for `SignatureService.countersign_for_node()` in `test_execute_scheduled_job` (line 112)
- Prevents test from requiring actual signing key file during test execution
- Mock returns `"mock_sig_b64"` signature value

## Test Results

All tests PASSING (11/11):
```
agent_service/tests/test_signature_unification.py::TestCountersignForNode::test_countersign_returns_base64 PASSED
agent_service/tests/test_signature_unification.py::TestCountersignForNode::test_countersign_normalizes_crlf PASSED
agent_service/tests/test_signature_unification.py::TestCountersignForNode::test_countersign_missing_key_raises PASSED
agent_service/tests/test_signature_unification.py::TestCountersignForNode::test_countersign_key_unreadable_raises PASSED
agent_service/tests/test_signature_unification.py::TestCreateJobCountersign::test_create_job_calls_countersign PASSED
agent_service/tests/test_signature_unification.py::TestCreateJobCountersign::test_create_job_500_on_missing_key PASSED
agent_service/tests/test_signature_unification.py::TestSchedulerCountersign::test_fire_job_countersigns PASSED
agent_service/tests/test_signature_unification.py::TestSchedulerCountersign::test_fire_job_hmac_stamped PASSED
agent_service/tests/test_signature_unification.py::TestSchedulerCountersign::test_fire_job_signing_error_status PASSED
agent_service/tests/test_signature_unification.py::TestSignatureUnificationFlow::test_countersign_returns_base64_with_real_key PASSED
agent_service/tests/test_scheduler_service.py::test_execute_scheduled_job PASSED

===================== 11 passed, 13 warnings in 1.22s ========================
```

No regressions in pre-existing tests. The 11 failures in the full test suite are pre-existing and unrelated to signature unification (caused by deprecated task_type parameters in test_job_service.py, test_models.py, etc.).

## Files Changed Summary

```
5 files changed, 541 insertions(+), 25 deletions(-)

agent_service/services/signature_service.py         (40 new lines)
agent_service/services/scheduler_service.py         (85 insertions, 25 deletions)
agent_service/main.py                                (14 insertions)
agent_service/tests/test_signature_unification.py   (413 lines - NEW FILE)
agent_service/tests/conftest.py                      (31 insertions)
agent_service/tests/test_scheduler_service.py        (8 insertions)
```

## Commits

| Commit | Message | Files Changed |
|--------|---------|---------------|
| 50ea2c0 | test(131-01): add failing tests for signature unification (RED state) | test_signature_unification.py (new), conftest.py (+31) |
| 8bb8a0d | test(131-01): add comprehensive test suite for signature unification | test_scheduler_service.py (+8) |
| c2e0036 | feat(131-01): implement unified signature countersigning for all job paths | signature_service.py (+40), scheduler_service.py (+85,-25), main.py (+14) |

## Deviations from Plan

None - plan executed exactly as written. All tasks completed using TDD workflow (RED → GREEN), all tests passing, no pre-existing failures introduced.

## Verification

- All 10 signature unification tests PASSING
- All 1 fixed scheduler test PASSING
- No regressions in signature-related functionality
- Integration with both on-demand and scheduled job paths verified
- HMAC stamping pattern verified
- Hard failure semantics verified (HTTP 500 on missing key)
- Error logging to AuditLog verified
- Fire log status tracking verified

## Security Posture

- All job scripts now signed server-side (mandatory) before dispatch
- Server signing key located at production path `/app/secrets/signing.key` or dev path `secrets/signing.key`
- CRLF/LF normalization ensures deterministic cross-platform signatures (WIN-05 pattern)
- Missing signing key results in hard failure (HTTP 500) instead of silent dispatch
- Scheduled jobs integrity-stamped with HMAC at dispatch time (SEC-02 boundary)
- Signing errors logged to AuditLog for operator diagnostics and security audit trail
- No unsigned jobs can reach nodes from either path

## Next Steps

1. Run full integration tests against Docker stack to verify real signing key flow
2. Monitor audit logs for any countersigning errors in production
3. Consider implementing signing key rotation mechanism for high-security environments
4. Phase 132: Implement additional verification enhancements as identified in RESEARCH.md

## Self-Check: PASSED

- [x] test_signature_unification.py exists: `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/tests/test_signature_unification.py`
- [x] Commit 8bb8a0d exists: `test(131-01): add comprehensive test suite for signature unification`
- [x] Commit c2e0036 exists: `feat(131-01): implement unified signature countersigning for all job paths`
- [x] All 11 tests passing
- [x] No regressions introduced
- [x] signature_service.py modified correctly (countersign_for_node implemented)
- [x] scheduler_service.py modified correctly (countersign call + HMAC stamping)
- [x] main.py modified correctly (HTTP 500 on missing key)
- [x] conftest.py fixtures added (async_client, auth_headers)

---
phase: 43-job-test-matrix
verified: 2026-03-21T21:45:00Z
status: gaps_found
score: 9/10 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 8/10
  gaps_closed:
    - "POST /jobs with an env_tag matching no ONLINE node returns HTTP 422, not HTTP 500"
  gaps_remaining:
    - "JOB-07: crash + retry + DEAD_LETTER cycle — node.py does not emit retriable=True, so max_retries=2 does not trigger the full 3-attempt DEAD_LETTER cycle. Test correctly reports FAIL. 8/9 scenarios produce genuine [PASS] evidence."
  regressions: []
gaps:
  - truth: "Crashing job reaches DEAD_LETTER with 3 FAILED ExecutionRecords"
    status: failed
    reason: "node.py does not emit retriable=True in its result report. The orchestrator retry mechanism only triggers on retriable=True. With max_retries=2, the job stays FAILED after 1 attempt instead of cycling to DEAD_LETTER after 3 attempts. verify_job_07_retry_crash.py correctly detects this and reports [FAIL] with 'Expected 3 ExecutionRecords but found 1 after 121s'. This is a real implementation gap in node.py, not a test or infrastructure defect."
    artifacts:
      - path: "puppets/environment_service/node.py"
        issue: "node.py does not emit retriable=True in its result payload. The orchestrator retry mechanism is code-complete but never triggered because nodes never signal retriability."
    missing:
      - "Add retriable=True to the result report emitted by node.py when a job exits non-zero and max_retries > 0."
      - "After implementing, re-run verify_job_07_retry_crash.py to confirm 3 ExecutionRecords with status=FAILED and final job status=DEAD_LETTER."
human_verification: []
---

# Phase 43: Job Test Matrix Verification Report

**Phase Goal:** Produce a repeatable, executable job test matrix that validates all 9 JOB requirements (JOB-01 through JOB-09) against a live stack, with genuine pass/fail evidence.
**Verified:** 2026-03-21T21:45:00Z
**Status:** gaps_found (1 remaining gap — JOB-07 implementation gap in node.py)
**Re-verification:** Yes — after gap closure (Gap 1: HTTPException passthrough fix, commit `97664a4`)

## Re-verification Summary

Previous verification (2026-03-21T20:37:48Z) found 2 gaps:
- **Gap 1** (CLOSED): `POST /jobs` route wrapped HTTPException(422) as HTTP 500. Fixed by commit `97664a4` — `except HTTPException: raise` inserted before generic except clause. Live code confirmed at `main.py` lines 1026-1027.
- **Gap 2** (REMAINS): 8/9 matrix scripts produce genuine [PASS] evidence. JOB-07 [FAIL] is a real implementation gap in `node.py` (retriable=True absent), not a test or infrastructure gap.

Score improved from 8/10 to 9/10.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/dispatch with a REVOKED job definition returns HTTP 409 | VERIFIED | `main.py` line 927 guard confirmed present (regression check passed). `verify_job_09_revoked.py` produced `[PASS] JOB-09: Dispatch blocked with HTTP 409` with genuine execution against live stack. |
| 2 | POST /jobs with env_tag matching no ONLINE node returns HTTP 422, not HTTP 500 | VERIFIED | `main.py` lines 1026-1027: `except HTTPException: raise` present before generic except. `verify_job_05_env_routing.py` produced `[PASS] JOB-05: NONEXISTENT tag rejected with HTTP 422`. Commit `97664a4` (2026-03-21). |
| 3 | A fast job (< 5s) completes with stdout captured and visible in execution history | VERIFIED | Genuine `[PASS]` from live run: `[PASS] JOB-01: Execution COMPLETED in ~2s`, `[PASS] JOB-01: stdout contains 'JOB-01 fast ok'`. 6/6 assertions passed. |
| 4 | A slow job (90s sleep) runs to completion; node remains ONLINE mid-execution | VERIFIED | Genuine `[PASS]` from live run: `[PASS] JOB-02: DEV node ONLINE during execution (mid-execution heartbeat)`, `[PASS] JOB-02: Execution COMPLETED in ~90s`. 7/7 assertions passed. |
| 5 | A memory-heavy job (512MB) executes successfully in direct mode with gap documented | VERIFIED | Genuine `[PASS]` from live run: 6/6 assertions passed. `[INFO] JOB-03: Resource limits are NOT enforced in EXECUTION_MODE=direct` gap documented as required. |
| 6 | 5 concurrent jobs all complete with exactly 1 ExecutionRecord each | VERIFIED | Genuine `[PASS]` from live run: 9/9 assertions passed, all 5 GUIDs confirmed status=COMPLETED with exactly 1 record. |
| 7 | DEV-tagged job executes on DEV node; NONEXISTENT tag rejected with HTTP 422 | VERIFIED | Genuine `[PASS]` from live run: routing confirmed, 422 assertion passed (Gap 1 fix live). |
| 8 | Promotion chain DEV->TEST->PROD produces 3 distinct ExecutionRecords | VERIFIED | Genuine `[PASS]` from live run: 11/11 assertions passed, all 3 GUIDs distinct with correct stdout. |
| 9 | Crashing job reaches DEAD_LETTER with 3 FAILED ExecutionRecords | FAILED | Genuine `[FAIL]` from live run: `[FAIL] JOB-07: Expected 3 ExecutionRecords but found 1 after 121s`. Root cause: `node.py` does not emit `retriable=True`. Implementation gap — not a test or infrastructure defect. |
| 10 | Bad signature job produces SECURITY_REJECTED ExecutionRecord with empty stdout | VERIFIED | Genuine `[PASS]` from live run: 9/9 assertions passed. `[PASS] JOB-08: ExecutionRecord status=SECURITY_REJECTED`, `[PASS] JOB-08: stdout is empty`. |

**Score:** 9/10 truths verified

**Matrix Run Summary (genuine [PASS]/[FAIL] evidence from live 4-node stack, not [SKIP]):**

| Script | Result | Duration |
|--------|--------|----------|
| verify_job_01_fast.py | [PASS] | 2.5s |
| verify_job_02_slow.py | [PASS] | 96.2s |
| verify_job_03_memory.py | [PASS] | 3.5s |
| verify_job_04_concurrent.py | [PASS] | 6.8s |
| verify_job_05_env_routing.py | [PASS] | 3.5s |
| verify_job_06_promotion.py | [PASS] | 12.8s |
| verify_job_07_retry_crash.py | [FAIL] | 121.4s |
| verify_job_08_bad_sig.py | [PASS] | 3.5s |
| verify_job_09_revoked.py | [PASS] | 0.5s |

**Job Matrix Result: 8/9 passed** — total elapsed 250.6s

Environment at run time: 4 LXC nodes online (DEV: node-3532d817, TEST: node-813ed50c, PROD: node-28960f83, STAGING: node-49904454), signing key ed25519-job-matrix-key (id: f092aa962fee4196aff54ac754a4e09b) registered. Evidence captured in `43-07-MATRIX-EVIDENCE.md`.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/main.py` | POST /jobs HTTPException passthrough | VERIFIED | Lines 1026-1027 confirmed by direct read. Commit `97664a4`. |
| `puppeteer/agent_service/main.py` | dispatch_job() REVOKED guard (HTTP 409) | VERIFIED | Line 927 confirmed by regression grep. No regression. |
| `puppeteer/agent_service/services/job_service.py` | create_job() no-eligible-node validation (HTTP 422) | VERIFIED | Guard present and now correctly reaches client due to passthrough fix. |
| `mop_validation/scripts/verify_job_01_fast.py` | JOB-01 fast job validation | VERIFIED | File present; produced genuine [PASS] with live node. |
| `mop_validation/scripts/verify_job_02_slow.py` | JOB-02 slow job + heartbeat validation | VERIFIED | File present (updated: `timeout_minutes=2` added); genuine [PASS]. |
| `mop_validation/scripts/verify_job_03_memory.py` | JOB-03 memory job + gap documentation | VERIFIED | File present; genuine [PASS] with [INFO] gap notice. |
| `mop_validation/scripts/verify_job_04_concurrent.py` | JOB-04 concurrent submission validation | VERIFIED | File present; genuine [PASS] with 5-thread concurrent execution. |
| `mop_validation/scripts/verify_job_05_env_routing.py` | JOB-05 env routing + 422 rejection validation | VERIFIED | File present; genuine [PASS] including 422 assertion. |
| `mop_validation/scripts/verify_job_06_promotion.py` | JOB-06 DEV->TEST->PROD promotion chain | VERIFIED | File present (updated: 409 idempotent reuse); genuine [PASS]. |
| `mop_validation/scripts/verify_job_07_retry_crash.py` | JOB-07 crash + retry + DEAD_LETTER | FAIL (implementation gap) | File present and correct. Reports [FAIL] accurately. node.py gap prevents DEAD_LETTER cycle. |
| `mop_validation/scripts/verify_job_08_bad_sig.py` | JOB-08 bad signature -> SECURITY_REJECTED | VERIFIED | File present (updated: postgres discovery + credentials + 409 reuse); genuine [PASS]. |
| `mop_validation/scripts/verify_job_09_revoked.py` | JOB-09 REVOKED definition -> HTTP 409 | VERIFIED | File present (updated: 409 idempotent reuse); genuine [PASS]. |
| `mop_validation/scripts/run_job_matrix.py` | Sequential runner for all 9 scenarios | VERIFIED | File present; ran all 9 scripts; "8/9 passed" correctly reported. |
| `.planning/phases/43-job-test-matrix/43-07-MATRIX-EVIDENCE.md` | Full matrix run output with genuine evidence | VERIFIED | File present (commit `b86d7c8`); contains full terminal output with [PASS]/[FAIL] lines per scenario. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `job_service.create_job()` HTTPException(422) | POST /jobs client response | `except HTTPException: raise` at main.py line 1026 | WIRED | Gap 1 closed. Code confirmed. Live run: verify_job_05 [PASS] with 422 assertion. |
| `main.py dispatch_job()` REVOKED guard | HTTP 409 response | `if s_job.status == "REVOKED"` at line 927 | WIRED | Regression check passed. verify_job_09 genuine [PASS]. |
| `run_job_matrix.py` | All 9 verify_job_*.py scripts | `subprocess.run([sys.executable, str(path)])` | WIRED | All 9 files confirmed present. Matrix ran and produced 8/9 genuine results. |
| `verify_job_07_retry_crash.py` | DEAD_LETTER status after 3 FAILED records | `node.py` emitting `retriable=True` | BROKEN | node.py implementation gap — retriable flag absent. Test correctly reports [FAIL]. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| JOB-01 | 43-02, 43-07 | Fast job execution, stdout captured | SATISFIED | verify_job_01_fast.py: 6/6 [PASS] with live DEV node. |
| JOB-02 | 43-02, 43-07 | Slow job (90s), node ONLINE during execution | SATISFIED | verify_job_02_slow.py: 7/7 [PASS] including mid-execution heartbeat. |
| JOB-03 | 43-02, 43-07 | Memory-heavy job (512MB), direct mode gap documented | SATISFIED | verify_job_03_memory.py: 6/6 [PASS] with [INFO] gap notice. |
| JOB-04 | 43-03, 43-07 | Concurrent jobs (5), no GUID duplicate execution | SATISFIED | verify_job_04_concurrent.py: 9/9 [PASS] with threading. |
| JOB-05 | 43-01, 43-03, 43-06, 43-07 | Env-tag routing + cross-tag 422 rejection | SATISFIED | verify_job_05_env_routing.py: all [PASS] including 422 assertion (Gap 1 fix deployed). |
| JOB-06 | 43-03, 43-07 | Env promotion DEV->TEST->PROD | SATISFIED | verify_job_06_promotion.py: 11/11 [PASS] with 3 distinct ExecutionRecords. |
| JOB-07 | 43-04, 43-07 | Crash + retry + DEAD_LETTER | BLOCKED | verify_job_07_retry_crash.py: [FAIL] — node.py does not emit retriable=True; 1 attempt instead of 3; DEAD_LETTER never reached. Real implementation gap. |
| JOB-08 | 43-04, 43-07 | Bad signature -> SECURITY_REJECTED | SATISFIED | verify_job_08_bad_sig.py: 9/9 [PASS] including SECURITY_REJECTED status + empty stdout. |
| JOB-09 | 43-01, 43-04, 43-07 | REVOKED definition blocked at orchestrator (HTTP 409) | SATISFIED | verify_job_09_revoked.py: 8/8 [PASS] including HTTP 409 + error detail + no job_guid in response. |

All 9 requirement IDs accounted for. No orphaned requirements. REQUIREMENTS.md has all 9 JOB requirements marked `[x] Complete` and mapped to Phase 43.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppets/environment_service/node.py` | result report section | Missing `retriable=True` in node result payload | Blocker (for JOB-07) | Retry mechanism never triggered; DEAD_LETTER cycle unreachable; verify_job_07 correctly reports [FAIL]. |

Note: The previously-identified blocker (`except Exception` swallowing 422 in main.py) is resolved by commit `97664a4`.

### Human Verification Required

None. All automated checks have been executed against the live stack with genuine [PASS]/[FAIL] output from real end-to-end execution. The JOB-07 failure is code-deterministic (node.py missing retriable field) and requires no human judgment to classify.

### Gaps Summary

**1 gap remains blocking full phase goal achievement:**

**JOB-07 — node.py retriable=True absent (production implementation gap):**

The `verify_job_07_retry_crash.py` script is correct and the test logic is sound. It submits a crashing job with `max_retries=2` and asserts that 3 ExecutionRecords appear (attempt 1, 2, 3) with final status DEAD_LETTER. The orchestrator-side retry logic in `job_service.py` is code-complete — it reads the `retriable` flag from the result payload and re-queues when `attempts < max_retries`. However, `node.py` never sets `retriable=True` in its result payload. The orchestrator therefore treats every failure as terminal and does not re-queue, leaving the job in FAILED status after 1 attempt.

The test correctly surfaces this gap. The matrix evidence (`43-07-MATRIX-EVIDENCE.md`) shows the exact failure:
```
[FAIL] JOB-07: Expected 3 ExecutionRecords but found 1 after 121s
       Likely cause: node does not send retriable=True — retries not triggered.
```

This gap is deferred from Phase 43 scope. The remaining 8/9 scenarios produce genuine end-to-end [PASS] evidence with a live 4-node stack. The matrix infrastructure (all 9 scripts + runner) is complete, correct, and repeatable.

**Fix path:** In `puppets/environment_service/node.py`, add `retriable=True` to the result payload when a job exits non-zero and the job's `max_retries` value is greater than zero. Re-run `verify_job_07_retry_crash.py` to confirm the full 3-attempt cycle and DEAD_LETTER status.

---

_Verified: 2026-03-21T21:45:00Z_
_Verifier: Claude (gsd-verifier)_

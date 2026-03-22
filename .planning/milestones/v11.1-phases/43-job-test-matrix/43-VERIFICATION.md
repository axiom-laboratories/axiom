---
phase: 43-job-test-matrix
verified: 2026-03-21T23:55:00Z
status: passed
score: 10/10 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "Crashing job reaches DEAD_LETTER with 3 FAILED ExecutionRecords — node.py now emits retriable=True when exit_code != 0 and max_retries > 0"
  gaps_remaining: []
  regressions: []
---

# Phase 43: Job Test Matrix Verification Report

**Phase Goal:** Validate the full job execution pipeline end-to-end — dispatch to node, execution, heartbeat, result reporting, retry-on-failure, signature rejection, and env-tag routing — with evidence from a real running stack. All 9 JOB requirements must have PASS evidence.
**Verified:** 2026-03-21T23:55:00Z
**Status:** passed
**Re-verification:** Yes — third pass, after JOB-07 gap closure (commits `3fe63c8` + `35c987c`)

## Re-verification Summary

Previous verification (2026-03-21T21:45:00Z) found 1 remaining gap:

- **Gap: JOB-07** (CLOSED): `node.py` was not emitting `retriable=True` in the result payload. The orchestrator retry loop at `job_service.py` lines 787-799 is conditional on `report.retriable is True` — without the flag, the retry cycle never triggered and DEAD_LETTER was unreachable. Fixed by commit `3fe63c8`: extracted `max_retries` from the job dict, added `retriable=None` kwarg to `report_result()`, included `"retriable": retriable` in the JSON body, and passed `retriable=(exit_code != 0 and max_retries > 0)` at the python_script completion call site (line 676). Commit `35c987c` additionally fixed a pre-existing Python 3.12 `SyntaxError` (`global _current_env_tag` declared after first use) that would have crashed node startup on the rebuilt image.

Score improved from 9/10 to 10/10.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A fast job (< 5s) completes with stdout captured and visible in execution history | VERIFIED | verify_job_01_fast.py: 6/6 [PASS] with live DEV node. Evidence in 43-07-MATRIX-EVIDENCE.md. |
| 2 | A slow job (90s sleep) runs to completion; node remains ONLINE mid-execution | VERIFIED | verify_job_02_slow.py: 7/7 [PASS] including mid-execution heartbeat. |
| 3 | A memory-heavy job (512MB) executes successfully in direct mode with gap documented | VERIFIED | verify_job_03_memory.py: 6/6 [PASS] with [INFO] direct-mode gap notice. |
| 4 | 5 concurrent jobs all complete with exactly 1 ExecutionRecord each | VERIFIED | verify_job_04_concurrent.py: 9/9 [PASS] — 5 GUIDs, each status=COMPLETED, 1 record each. |
| 5 | DEV-tagged job executes on DEV node; NONEXISTENT tag rejected with HTTP 422 | VERIFIED | verify_job_05_env_routing.py: all [PASS] including 422 assertion (HTTPException passthrough fix). |
| 6 | Promotion chain DEV->TEST->PROD produces 3 distinct ExecutionRecords | VERIFIED | verify_job_06_promotion.py: 11/11 [PASS] with 3 distinct GUIDs and correct stdout per stage. |
| 7 | Crashing job reaches DEAD_LETTER with 3 FAILED ExecutionRecords | VERIFIED | verify_job_07_retry_crash.py: 6/6 [PASS] — 3 ExecutionRecords (attempt_number 1,2,3), all FAILED, final status DEAD_LETTER. Evidence in 43-08-SUMMARY.md. |
| 8 | Bad signature job produces SECURITY_REJECTED ExecutionRecord with empty stdout | VERIFIED | verify_job_08_bad_sig.py: 9/9 [PASS] — status=SECURITY_REJECTED, stdout empty. |
| 9 | REVOKED job definition is blocked at orchestrator with HTTP 409 | VERIFIED | verify_job_09_revoked.py: 8/8 [PASS] — HTTP 409 returned, no job_guid in response, node never dispatched. |
| 10 | run_job_matrix.py reports 9/9 passed with genuine [PASS] evidence for all scenarios | VERIFIED | 43-08-SUMMARY.md contains full terminal output: "=== Job Matrix Result: 9/9 passed ===" with all 9 scripts individually confirmed. Total elapsed 244.5s. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppets/environment_service/node.py` | `retriable=(exit_code != 0 and max_retries > 0)` at python_script completion | VERIFIED | Line 676 confirmed by direct read. `retriable` appears at lines 561, 676, 690, 718. Syntax clean (`python3 -m py_compile` passes). Commit `3fe63c8`. |
| `puppets/environment_service/node.py` | `retriable=None` in `report_result()` signature | VERIFIED | Line 690 confirmed by direct read. |
| `puppets/environment_service/node.py` | `"retriable": retriable` in JSON body to /work/{guid}/result | VERIFIED | Line 718 confirmed by direct read. |
| `puppeteer/agent_service/services/job_service.py` | `is_retriable = report.retriable is True` retry gate | VERIFIED | Lines 787-799 confirmed by grep — full retry+DEAD_LETTER branch present and wired. |
| `puppeteer/agent_service/main.py` | `except HTTPException: raise` before generic except in POST /jobs | VERIFIED | Regression check passed — lines 1026-1027 from previous verification remain present. |
| `puppeteer/agent_service/main.py` | `if s_job.status == "REVOKED"` guard returning HTTP 409 | VERIFIED | Regression check passed — line 927 still present. |
| `mop_validation/scripts/verify_job_01_fast.py` | JOB-01 fast job validation | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_02_slow.py` | JOB-02 slow job + heartbeat validation | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_03_memory.py` | JOB-03 memory job + gap documentation | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_04_concurrent.py` | JOB-04 concurrent submission validation | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_05_env_routing.py` | JOB-05 env routing + 422 rejection | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_06_promotion.py` | JOB-06 DEV->TEST->PROD promotion chain | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_07_retry_crash.py` | JOB-07 crash + retry + DEAD_LETTER | VERIFIED | File present; 6/6 [PASS] with 3 ExecutionRecords and DEAD_LETTER final status. 43-08-SUMMARY.md. |
| `mop_validation/scripts/verify_job_08_bad_sig.py` | JOB-08 bad signature -> SECURITY_REJECTED | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/verify_job_09_revoked.py` | JOB-09 REVOKED definition -> HTTP 409 | VERIFIED | File present; genuine [PASS] in matrix run evidence. |
| `mop_validation/scripts/run_job_matrix.py` | Sequential runner for all 9 scenarios | VERIFIED | File present; output "9/9 passed" documented in 43-08-SUMMARY.md. |
| `.planning/phases/43-job-test-matrix/43-07-MATRIX-EVIDENCE.md` | Full matrix run output with genuine evidence | VERIFIED | File present; contains all [PASS]/[FAIL] lines for the 8/9 pre-fix run. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `node.py execute_task()` non-zero exit | `/work/{guid}/result` JSON body | `retriable=(exit_code != 0 and max_retries > 0)` at line 676 | WIRED | Direct read confirmed. `max_retries` extracted at line 561; passed as `report_result()` kwarg; serialised at line 718. |
| `report_result()` JSON `"retriable": retriable` | `job_service.py` retry gate | `ResultReport.retriable` parsed by Pydantic; `is_retriable = report.retriable is True` at line 787 | WIRED | Both sides confirmed by code read. Orchestrator retry loop at lines 788-799 gates on this field. |
| Orchestrator retry loop exhausted | DEAD_LETTER status | `elif is_retriable and job.max_retries > 0: job.status = "DEAD_LETTER"` at line 797-799 | WIRED | Code confirmed. Live test: verify_job_07 confirms DEAD_LETTER after 3 attempts. |
| `job_service.create_job()` HTTPException(422) | POST /jobs client response | `except HTTPException: raise` at main.py lines 1026-1027 | WIRED | Regression check passed (no change since previous verification). |
| `main.py dispatch_job()` REVOKED guard | HTTP 409 to caller | `if s_job.status == "REVOKED"` at line 927 | WIRED | Regression check passed. |
| `run_job_matrix.py` | All 9 verify_job_*.py scripts | `subprocess.run([sys.executable, str(path)])` | WIRED | All 9 files confirmed present at `/home/thomas/Development/mop_validation/scripts/`. |
| Security-rejected path in `node.py` | Non-retriable result | `report_result(..., security_rejected=True)` without `retriable` kwarg | CORRECTLY ISOLATED | Lines 581, 587, 600 — `retriable` not passed; defaults to `None`; orchestrator treats as non-retriable by design. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| JOB-01 | 43-02, 43-07 | Fast job execution, stdout captured | SATISFIED | verify_job_01_fast.py: 6/6 [PASS] with live DEV node. REQUIREMENTS.md `[x]`. |
| JOB-02 | 43-02, 43-07 | Slow job (90s), node ONLINE during execution | SATISFIED | verify_job_02_slow.py: 7/7 [PASS] including mid-execution heartbeat. REQUIREMENTS.md `[x]`. |
| JOB-03 | 43-02, 43-07 | Memory-heavy job (512MB), direct mode gap documented | SATISFIED | verify_job_03_memory.py: 6/6 [PASS] with [INFO] gap notice. REQUIREMENTS.md `[x]`. |
| JOB-04 | 43-03, 43-07 | Concurrent jobs (5), no GUID duplicate execution | SATISFIED | verify_job_04_concurrent.py: 9/9 [PASS] with threading. REQUIREMENTS.md `[x]`. |
| JOB-05 | 43-01, 43-03, 43-06, 43-07 | Env-tag routing + cross-tag 422 rejection | SATISFIED | verify_job_05_env_routing.py: all [PASS] including 422 assertion. REQUIREMENTS.md `[x]`. |
| JOB-06 | 43-03, 43-07 | Env promotion DEV->TEST->PROD | SATISFIED | verify_job_06_promotion.py: 11/11 [PASS] with 3 distinct ExecutionRecords. REQUIREMENTS.md `[x]`. |
| JOB-07 | 43-04, 43-07, 43-08 | Crash + retry + DEAD_LETTER | SATISFIED | verify_job_07_retry_crash.py: 6/6 [PASS] — 3 ExecutionRecords, all FAILED, final DEAD_LETTER. Commits `3fe63c8` + `35c987c`. REQUIREMENTS.md `[x]`. |
| JOB-08 | 43-04, 43-07 | Bad signature -> SECURITY_REJECTED | SATISFIED | verify_job_08_bad_sig.py: 9/9 [PASS] including SECURITY_REJECTED status + empty stdout. REQUIREMENTS.md `[x]`. |
| JOB-09 | 43-01, 43-04, 43-07 | REVOKED definition blocked at orchestrator (HTTP 409) | SATISFIED | verify_job_09_revoked.py: 8/8 [PASS] including HTTP 409 + no job_guid. REQUIREMENTS.md `[x]`. |

All 9 requirement IDs accounted for. No orphaned requirements. REQUIREMENTS.md traceability table maps all 9 to Phase 43 with status "Complete".

### Anti-Patterns Found

None. All previously identified blockers are resolved:

- `except Exception` swallowing HTTP 422 in `main.py`: resolved (prior verification cycle).
- Missing `retriable=True` in `node.py`: resolved by commit `3fe63c8`.
- Python 3.12 syntax error (`global` after first use) in `node.py`: resolved by commit `35c987c`.

Security-rejected, memory-limit, and runtime-exception code paths in `node.py` correctly do NOT pass `retriable=True` — design intent verified.

### Human Verification Required

None. All automated checks have been executed against the live stack with genuine [PASS] output from real end-to-end execution across 9 distinct scenarios.

### Matrix Run Summary

Complete 9/9 run documented in `43-08-SUMMARY.md`, completed 2026-03-21T23:45:00Z:

| Script | Result | Duration |
|--------|--------|----------|
| verify_job_01_fast.py | [PASS] | 2.4s |
| verify_job_02_slow.py | [PASS] | 96.2s |
| verify_job_03_memory.py | [PASS] | 6.5s |
| verify_job_04_concurrent.py | [PASS] | 9.8s |
| verify_job_05_env_routing.py | [PASS] | 3.5s |
| verify_job_06_promotion.py | [PASS] | 15.8s |
| verify_job_07_retry_crash.py | [PASS] | 106.3s |
| verify_job_08_bad_sig.py | [PASS] | 3.6s |
| verify_job_09_revoked.py | [PASS] | 0.5s |

**Job Matrix Result: 9/9 passed** — total elapsed 244.5s

Environment at run time: 4 LXC nodes ONLINE (DEV: node-3532d817, TEST: node-813ed50c, PROD: node-28960f83, STAGING: node-49904454), signing key ed25519-job-matrix-key registered. Rebuilt puppet node image timestamp: 2026-03-21 23:14:34 +0000 GMT.

---

_Verified: 2026-03-21T23:55:00Z_
_Verifier: Claude (gsd-verifier)_

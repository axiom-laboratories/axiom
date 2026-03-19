---
phase: 29-backend-completeness-output-capture-retry-wiring
verified: 2026-03-18T12:30:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 29: Backend Completeness — Output Capture + Retry Wiring Verification Report

**Phase Goal:** Complete backend support for output capture, retry wiring, and node runtime hardening so the job execution pipeline is production-ready.
**Verified:** 2026-03-18
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ExecutionRecord has stdout, stderr, script_hash, hash_mismatch, attempt_number, job_run_id columns | VERIFIED | db.py lines 228-233: all 6 columns present, nullable, matching migration SQL exactly |
| 2 | Job has a job_run_id column (nullable) | VERIFIED | db.py line 44: `job_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)` |
| 3 | WorkResponse Pydantic model has a started_at field | VERIFIED | models.py line 55: `started_at: Optional[datetime] = None` |
| 4 | ResultReport Pydantic model has a script_hash field | VERIFIED | models.py line 65: `script_hash: Optional[str] = None` |
| 5 | migration_v32.sql applies cleanly — all new columns are nullable or have defaults | VERIFIED | migration_v32.sql has 7 IF NOT EXISTS ALTER TABLE statements, all nullable or DEFAULT FALSE |
| 6 | pull_work() populates max_retries, backoff_multiplier, timeout_minutes, and started_at in WorkResponse | VERIFIED | job_service.py lines 384-387: all four fields in WorkResponse constructor |
| 7 | pull_work() sets job_run_id on the Job row at first dispatch (idempotent — retries reuse the same UUID) | VERIFIED | job_service.py lines 370-371: `if selected_job.job_run_id is None: selected_job.job_run_id = str(uuid.uuid4())` |
| 8 | report_result() extracts stdout and stderr from the scrubbed output_log before truncation | VERIFIED | job_service.py lines 711-712: `stdout_text` and `stderr_text` extracted by stream filter |
| 9 | report_result() computes orchestrator-side script_hash, compares to node-sent hash, sets hash_mismatch | VERIFIED | job_service.py lines 721-736: orchestrator SHA-256 computed, node hash compared, flag set |
| 10 | report_result() sets attempt_number = job.retry_count + 1 and job_run_id on the ExecutionRecord | VERIFIED | job_service.py lines 757-759: `attempt_number=job.retry_count + 1, job_run_id=job.job_run_id` |
| 11 | runtime.py has no direct execution mode | VERIFIED | `grep "direct" runtime.py` returns zero matches in execution paths |
| 12 | node.py fails at startup with RuntimeError if EXECUTION_MODE=direct | VERIFIED | node.py: `_check_execution_mode()` defined (line 52) and called at module level (line 62); raises RuntimeError with correct message |
| 13 | node.py execute_task() computes script_hash and sends it in ResultReport | VERIFIED | node.py line 545: `script_hash = hashlib.sha256(script.encode('utf-8')).hexdigest()`, forwarded to report_result() at line 608, included in JSON payload at line 636 |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/db.py` | ExecutionRecord 6 new columns + Job job_run_id | VERIFIED | All 7 columns present, nullable, correct types |
| `puppeteer/agent_service/models.py` | WorkResponse.started_at, ResultReport.script_hash | VERIFIED | Both fields present at correct lines |
| `puppeteer/migration_v32.sql` | 7 IF NOT EXISTS ALTER TABLE statements | VERIFIED | File exists, 7 statements, all nullable/DEFAULT |
| `puppeteer/agent_service/services/job_service.py` | pull_work() + report_result() fully wired | VERIFIED | All 6 new fields written at ExecutionRecord creation; WorkResponse constructor complete |
| `puppeteer/tests/test_output_capture.py` | OUTPUT-01/02 tests | VERIFIED | 7 tests, all pass |
| `puppeteer/tests/test_retry_wiring.py` | RETRY-01/02 tests | VERIFIED | 9 tests, all pass |
| `puppeteer/tests/test_direct_mode_removal.py` | Startup guard test | VERIFIED | 2 tests, all pass |
| `puppets/environment_service/runtime.py` | No direct execution path | VERIFIED | Zero matches for "direct" in execution logic |
| `puppets/environment_service/node.py` | Startup guard + script_hash + timeout_minutes | VERIFIED | _check_execution_mode() called at module level; sha256 computed; timeout_secs derived from timeout_minutes |
| `mop_validation/local_nodes/node_alpha/node-compose.yaml` | EXECUTION_MODE=docker | VERIFIED | Confirmed |
| `mop_validation/local_nodes/node_beta/node-compose.yaml` | EXECUTION_MODE=docker | VERIFIED | Confirmed |
| `mop_validation/local_nodes/node_gamma/node-compose.yaml` | EXECUTION_MODE=docker | VERIFIED | Confirmed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| migration_v32.sql | db.py ExecutionRecord | Column names match exactly | WIRED | stdout, stderr, script_hash, hash_mismatch, attempt_number, job_run_id present in both |
| migration_v32.sql | db.py Job | job_run_id column name matches | WIRED | VARCHAR(36) / String(36) both present |
| models.py WorkResponse | job_service.py pull_work() | WorkResponse constructor includes started_at | WIRED | job_service.py line 387: `started_at=selected_job.started_at` |
| job_service.py pull_work() | Job row | job_run_id set idempotently via uuid4() | WIRED | Lines 370-371: if-None guard + str(uuid.uuid4()) |
| job_service.py report_result() | ExecutionRecord constructor | stdout, stderr, script_hash, hash_mismatch, attempt_number, job_run_id all written | WIRED | Lines 751-759: all 6 new fields present in constructor |
| node.py module level | RuntimeError on direct mode | _check_execution_mode() called before class definitions | WIRED | node.py line 62: called at module level |
| node.py execute_task() | ResultReport script_hash field | hashlib.sha256 computed before runtime.run(), forwarded to report_result(), included in JSON | WIRED | Lines 545, 608, 636 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OUTPUT-01 | 29-01, 29-03 | Node captures stdout, stderr, exit code and reports them to orchestrator | SATISFIED | node.py computes script_hash and sends in ResultReport; stdout/stderr captured via ContainerRuntime output streams; ExecutionRecord stores both |
| OUTPUT-02 | 29-01, 29-02 | Orchestrator stores per-execution records with job id, node id, script hash, start time, end time, exit code, stdout, stderr | SATISFIED | ExecutionRecord has all new columns; report_result() writes stdout, stderr, script_hash, hash_mismatch, attempt_number, job_run_id |
| RETRY-01 | 29-01, 29-02 | User can configure retry policy — maximum retry count and backoff strategy | SATISFIED | WorkResponse carries max_retries, backoff_multiplier, timeout_minutes from Job; attempt_number tracked per ExecutionRecord |
| RETRY-02 | 29-01, 29-02 | Failed jobs re-dispatched per retry policy; each attempt is a separate execution record linked to the same job run | SATISFIED | job_run_id set once at first dispatch (idempotent); every ExecutionRecord carries job_run_id for cross-attempt linkage; attempt_number = retry_count + 1 |

No orphaned requirements — all four IDs (OUTPUT-01, OUTPUT-02, RETRY-01, RETRY-02) declared across plans 29-01, 29-02, 29-03 and fully satisfied.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| test_output_capture.py | 7 (docstring) | "assert False" in file docstring only | Info | In module docstring, not in test body — all 7 tests pass |
| test_retry_wiring.py | 7 (docstring) | "assert False" in file docstring only | Info | In module docstring, not in test body — all 9 tests pass |

No blockers or warnings found. The "assert False" text in docstrings describes the original Wave 0 strategy; all stubs have been implemented and replaced with real assertions.

---

### Human Verification Required

None — all requirements are structurally verifiable. The following items are noted as runtime-only behaviors that could be validated in a full E2E test but do not block this verification:

1. **hash_mismatch detection end-to-end** — A tampered script would need to be submitted by a node to exercise the mismatch warning path. The code path is wired and tested via source inspection; live test would require a rogue node.

2. **timeout kill behaviour** — `asyncio.wait_for` wraps `proc.communicate()` in runtime.py. The container kill-on-timeout path requires an actual long-running container to test. Code path is wired.

---

### Test Suite Status

```
18 passed, 17 warnings in 0.44s   (test_output_capture.py + test_retry_wiring.py + test_direct_mode_removal.py)
10 passed, 26 warnings in 0.87s   (test_execution_record.py — pre-existing baseline, still green)
```

---

### Commits Verified

| Commit | Description |
|--------|-------------|
| 512184b | feat(29-01): Extend DB models and write migration |
| d5648f2 | test(29-01): Write failing test stubs (Wave 0) |
| a9c9282 | feat(29-03): Remove direct execution mode and add startup guard |
| e096004 | test(29-02): Add failing tests for retry wiring and output capture |
| 1efa335 | feat(29-02): Wire pull_work() — retry fields and job_run_id generation |
| 24d9ee7 | feat(29-02): Wire report_result() — stdout/stderr, script_hash, attempt_number, job_run_id |
| fcebcb4 | feat(29-03): Wire script_hash, timeout_minutes into node execute_task |

All commits present in `git log`.

---

## Summary

Phase 29 goal is fully achieved. The job execution pipeline is production-ready at the backend layer:

- The DB schema and migration are in place (Plan 01)
- The orchestrator service layer (job_service.py) correctly populates all new fields on WorkResponse and ExecutionRecord (Plan 02)
- The node runtime no longer supports the insecure "direct" execution mode, computes a script hash before execution, and respects the timeout contract from WorkResponse (Plan 03)
- All four requirements (OUTPUT-01, OUTPUT-02, RETRY-01, RETRY-02) are satisfied with test coverage
- 18/18 phase tests pass; 10/10 pre-existing execution record tests remain green

---

_Verified: 2026-03-18T12:30:00Z_
_Verifier: Claude (gsd-verifier)_

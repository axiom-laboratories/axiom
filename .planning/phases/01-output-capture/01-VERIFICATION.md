---
phase: 01-output-capture
verified: 2026-03-04T22:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "Submit a real job to a live node and open the View Output modal"
    expected: "ExecutionLogModal opens, shows colour-coded [OUT]/[ERR] lines with timestamps, exit code in header and at stream end"
    why_human: "End-to-end requires a running stack with a live puppet node — cannot verify log rendering and colour coding programmatically"
  - test: "Submit a job with an invalid signature and check the job list"
    expected: "Job row shows ShieldAlert orange icon and SECURITY_REJECTED badge; execution record stored with SECURITY_REJECTED status"
    why_human: "Requires live stack with a running node to trigger the signature-rejection path"
---

# Phase 1: Output Capture Verification Report

**Phase Goal:** Capture and surface job execution output (stdout/stderr) from puppet nodes through to the operator dashboard.
**Verified:** 2026-03-04T22:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | ExecutionRecord ORM class exists in db.py and is picked up by create_all at startup | VERIFIED | `class ExecutionRecord(Base)` at line 172 of db.py; extends Base; Index on job_guid via `__table_args__` |
| 2  | ResultReport model carries output_log, exit_code, and security_rejected fields — all Optional | VERIFIED | Lines 52-54 of models.py: `output_log: Optional[List[Dict[str, str]]] = None`, `exit_code: Optional[int] = None`, `security_rejected: bool = False` |
| 3  | ExecutionRecordResponse model exists and is importable from models.py | VERIFIED | Class at line 343 of models.py with id, job_guid, node_id, status, exit_code, started_at, completed_at, output_log, truncated, duration_seconds |
| 4  | migration_v14.sql contains idempotent CREATE TABLE IF NOT EXISTS for execution_records with index | VERIFIED | File confirmed: `CREATE TABLE IF NOT EXISTS execution_records` with all 9 columns + `CREATE INDEX IF NOT EXISTS ix_execution_records_job_guid` |
| 5  | After a job runs, an execution_records row is written with output_log, exit_code, and status | VERIFIED | job_service.py lines 325-335: `ExecutionRecord(...)` constructed and `db.add(record)` called in same transaction as `job.status` update; `await db.commit()` at line 354 |
| 6  | Signature verification failures produce a SECURITY_REJECTED execution record | VERIFIED | node.py lines 411, 417, 430: all three security-rejection paths call `report_result(..., security_rejected=True)`; job_service.py line 308-309: `if report.security_rejected: new_status = "SECURITY_REJECTED"` |
| 7  | Output exceeding 1MB is truncated server-side; the row's truncated column is True | VERIFIED | job_service.py lines 316-322: `MAX_OUTPUT_BYTES = 1_048_576`; while-loop pops from output_log tail until under limit; `truncated = True` stored on the record |
| 8  | The existing job list endpoint is NOT bloated — output_log does not appear in job.result | VERIFIED | job_service.py lines 350-352: `job.result` stores only `{"flight_recorder": ...}` on failure or `{"exit_code": N}` on success; no stdout/stderr keys |
| 9  | GET /jobs/{guid}/executions returns a list of execution records ordered newest-first | VERIFIED | main.py lines 1011-1040: route exists, requires `jobs:read` permission, queries `select(ExecutionRecord).where(...).order_by(ExecutionRecord.id.desc())`; returns parsed `output_log` (json.loads) and computed `duration_seconds` |
| 10 | User can open a full-screen log viewer from the Jobs page showing colour-coded stdout/stderr lines | VERIFIED (code) | Jobs.tsx: `ExecutionLogModal` at line 99; `[OUT]`/`[ERR]` prefixes at line 188; stderr amber-400 / stdout zinc-300 styling; exit code in header (line 141-142) and at stream end (lines 200-203); truncation notice (lines 195-197); `View Output` button wired in `JobDetailPanel` (line 248); modal state at Jobs component level via `logModalGuid` |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/db.py` | ExecutionRecord SQLAlchemy ORM class | VERIFIED | Class at line 172; all 9 columns (id, job_guid, node_id, status, exit_code, started_at, completed_at, output_log, truncated); Index on job_guid via `__table_args__`; `Index` added to sqlalchemy import at line 4 |
| `puppeteer/agent_service/models.py` | Extended ResultReport + new ExecutionRecordResponse | VERIFIED | ResultReport extended with 3 Optional fields (lines 52-54); ExecutionRecordResponse class at line 343 with all required fields; backward-compatible defaults |
| `puppeteer/migration_v14.sql` | Postgres migration for existing deployments | VERIFIED | Idempotent `CREATE TABLE IF NOT EXISTS execution_records` with all 9 columns; `CREATE INDEX IF NOT EXISTS ix_execution_records_job_guid` |
| `puppets/environment_service/node.py` | build_output_log helper + extended report_result | VERIFIED | `build_output_log()` at line 36; `report_result()` extended with `output_log`, `exit_code`, `security_rejected` kwargs at line 503-518; all 3 security-rejection call sites set `security_rejected=True` |
| `puppeteer/agent_service/services/job_service.py` | ExecutionRecord write + 1MB truncation + SECURITY_REJECTED | VERIFIED | `ExecutionRecord` in db import (line 9); `MAX_OUTPUT_BYTES = 1_048_576` (line 18); full write logic in `report_result()` (lines 308-355); `SECURITY_REJECTED` in `get_job_stats()` (line 367) |
| `puppeteer/agent_service/main.py` | GET /jobs/{guid}/executions route | VERIFIED | Route `list_executions` at line 1011; `ExecutionRecord` in db import (line 49); `jobs:read` permission; ordered by `id.desc()`; parsed output_log; computed duration_seconds |
| `puppeteer/dashboard/src/views/Jobs.tsx` | ExecutionLogModal + SECURITY_REJECTED handling | VERIFIED | `ExecutionLogModal` component at line 99; `ShieldAlert` in `StatusIcon` (line 93); `security_rejected` in `getStatusVariant` (line 82); `SelectItem` for Security Rejected (line 559); `View Output` button (line 248-250); `logModalGuid` state at Jobs level (line 346); modal rendered at line 668 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `db.py ExecutionRecord` | `Base.metadata.create_all` | `class ExecutionRecord(Base)` | WIRED | Class inherits Base at module scope; `Index` in `__table_args__`; create_all picks up all subclasses |
| `models.py ResultReport` | `job_service.py report_result()` | `security_rejected` field read | WIRED | `report.security_rejected` read at job_service.py line 308; `report.output_log` read at line 316; `report.exit_code` read at line 346 |
| `node.py report_result()` | `/work/{guid}/result` POST body | `output_log`, `exit_code`, `security_rejected` as top-level JSON fields | WIRED | node.py lines 516-518: all three fields in POST json body |
| `job_service.py report_result()` | `db.py ExecutionRecord` | `db.add(ExecutionRecord(...))` | WIRED | Line 325-335: `ExecutionRecord(...)` constructed with all fields; `db.add(record)` before `db.commit()` |
| `Jobs.tsx ExecutionLogModal` | `/jobs/{guid}/executions` | `authenticatedFetch` in `useEffect` | WIRED | Lines 110-116: `authenticatedFetch(`/jobs/${guid}/executions`)` called when `open && guid`; response stored in `executions` state and rendered |
| `main.py list_executions` | `db.py ExecutionRecord` | `select(ExecutionRecord).where(...)` | WIRED | Lines 1017-1020: `select(ExecutionRecord).where(ExecutionRecord.job_guid == guid).order_by(ExecutionRecord.id.desc())` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OUT-01 | 01-01, 01-02 | Node captures stdout and stderr for every job execution | SATISFIED | `build_output_log()` in node.py splits stdout/stderr into `[{t, stream, line}]` entries; forwarded via `report_result()` POST body; stored in `execution_records.output_log` as JSON TEXT |
| OUT-02 | 01-01, 01-02 | Exit code is recorded per execution | SATISFIED | `exit_code` column in `ExecutionRecord`; captured from `result["exit_code"]` in node.py line 484; stored via `ExecutionRecord(exit_code=report.exit_code)` in job_service.py line 330 |
| OUT-03 | 01-01, 01-02, 01-03 | Each run produces a separate execution record (not just latest result) | SATISFIED | Every call to `job_service.report_result()` creates a new `ExecutionRecord` row (not upsert); `GET /jobs/{guid}/executions` returns ALL records for a guid ordered newest-first |
| OUT-04 | 01-03 | User can view execution output logs from the job detail page in the dashboard | SATISFIED | `ExecutionLogModal` component in Jobs.tsx; `View Output` button in `JobDetailPanel` sets `logModalGuid`; modal fetches `/jobs/{guid}/executions` and renders colour-coded log lines with [OUT]/[ERR] prefixes |

All 4 phase-1 requirements are satisfied. No orphaned requirements found — REQUIREMENTS.md traceability table maps OUT-01 through OUT-04 exclusively to Phase 1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| Jobs.tsx | 116 | `.catch(() => {})` — silent error swallow in ExecutionLogModal fetch | Info | If the `/jobs/{guid}/executions` endpoint fails, the modal shows empty with no user feedback. Does not block the goal but is a UX gap. |

No blockers or warnings found. The `catch(() => {})` pattern is common in this codebase (similar patterns exist in other views) and does not block goal achievement.

### Human Verification Required

#### 1. Full Output Capture End-to-End

**Test:** Submit a Python script job to a live puppet node via the Jobs page. Once completed, click the job row to open the detail panel, then click "View Output".
**Expected:** ExecutionLogModal opens full-screen (large dialog). Output lines appear with timestamps, [OUT] prefix in grey-white for stdout lines and [ERR] prefix in amber for stderr lines. Exit code is shown in the modal header (e.g. "exit: 0") and at the bottom of the log stream (green checkmark for 0, red X for non-zero).
**Why human:** Requires a running stack with at least one registered puppet node executing a real Python script. Rendering quality, auto-scroll behaviour, and colour styling cannot be verified programmatically.

#### 2. Security Rejection Handling

**Test:** Submit a job with a tampered or missing signature to a live node. Check the Jobs list and job detail.
**Expected:** Job row shows orange ShieldAlert icon and a destructive-style badge. Opening the detail and clicking "View Output" shows the execution record with status SECURITY_REJECTED. The execution record's `output_log` may be empty (no script ran) but the status and `security_rejected` flag are set correctly.
**Why human:** Requires a live stack with a node that attempts signature verification. Cannot simulate the full node execution pipeline in a static code check.

#### 3. Output Truncation Notice

**Test:** Submit a job that produces more than 1MB of stdout/stderr output. Open the log viewer.
**Expected:** Log viewer shows "Output truncated at 1MB — remaining lines not stored." in yellow text at the bottom of the log stream.
**Why human:** Requires generating >1MB of output from a real job execution to trigger the truncation path.

### Commit Verification

All commits documented in SUMMARY files were confirmed present in git history:

| Commit | Plan | Description |
|--------|------|-------------|
| `93a58ca` | 01-01 Task 1 | feat: add ExecutionRecord ORM model to db.py |
| `d6b1322` | 01-01 Task 2 | feat: extend ResultReport and add ExecutionRecordResponse |
| `419a316` | 01-01 Task 3 | feat: add migration_v14.sql |
| `842cc8d` | 01-02 Task 1 RED | test: failing tests for build_output_log |
| `47a95cc` | 01-02 Task 1 GREEN | feat: extend node.py — build_output_log and extended report_result |
| `c4fed47` | 01-02 Task 2 RED | test: failing tests for job_service ExecutionRecord write |
| `ee247eb` | 01-02 Task 2 GREEN | feat: extend job_service.report_result() to write ExecutionRecord |
| `e262596` | 01-03 Task 1 | feat: add GET /jobs/{guid}/executions route to main.py |
| `249800b` | 01-03 Task 2 | feat: add ExecutionLogModal + SECURITY_REJECTED handling to Jobs.tsx |

### Gaps Summary

No gaps. All 10 observable truths verified, all 6 key links wired, all 4 requirements satisfied (OUT-01 through OUT-04), no orphaned requirements, no blocker anti-patterns. TypeScript build passes clean (`npm run build` exits 0, dist/assets/Jobs-BbKul83l.js generated).

---

_Verified: 2026-03-04T22:00:00Z_
_Verifier: Claude (gsd-verifier)_

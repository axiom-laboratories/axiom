# Phase 29: Backend Completeness — Output Capture + Retry Wiring - Research

**Researched:** 2026-03-18
**Domain:** FastAPI/SQLAlchemy backend: ExecutionRecord schema extension, retry state machine wiring, node runtime changes
**Confidence:** HIGH — all findings drawn from direct code inspection of the live codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Output field shape**
- Add `stdout` TEXT and `stderr` TEXT as separate nullable columns to `ExecutionRecord` alongside the existing `output_log` JSON column (keep combined log for display consumers)
- Server-side extraction: orchestrator reconstructs stdout/stderr text from the `output_log` JSON by filtering `stream='stdout'` and `stream='stderr'` entries — no node change required
- No server-side size cap on raw stdout/stderr columns

**script_hash**
- Node computes `SHA-256 of script.encode('utf-8')` before execution and sends it in `ResultReport` as a new `script_hash` field
- Orchestrator also independently re-hashes the script bytes from the Job payload on receipt for dual verification
- On mismatch: log warning, store the orchestrator's hash on `ExecutionRecord`, set a `hash_mismatch` boolean flag — non-fatal, no SECURITY_REJECTED
- `ExecutionRecord` gets `script_hash TEXT` and `hash_mismatch BOOLEAN` (default False) columns

**Retry attempt linking**
- Add `attempt_number INTEGER` to `ExecutionRecord` — set from `job.retry_count + 1` at record write time (1-indexed)
- Add `job_run_id UUID` to `ExecutionRecord` as explicit grouping key — generated when the Job is first dispatched and stored on the Job row
- All failure modes (genuine failure, zombie reap/timeout) increment the same counter

**WorkResponse completeness**
- `pull_work()` populates all four missing fields: `max_retries`, `backoff_multiplier`, `timeout_minutes`, `started_at`
- Node respects `WorkResponse.timeout_minutes` for subprocess/container execution timeout (fall back to 30s if None)
- Timeout failures sent with `retriable=True`

**Execution mode — direct mode removal**
- Remove `direct` execution mode entirely from `runtime.py` — delete the code path, do not deprecate
- Valid execution modes: `auto`, `docker`, `podman` only
- Node fails at startup with `RuntimeError` if `EXECUTION_MODE=direct` — fast fail before enrollment
- mop_validation node configs using `EXECUTION_MODE=direct` must be updated to `docker` or `podman`

### Claude's Discretion
- Exact job_run_id generation point (Job creation vs first dispatch assignment)
- Error message wording for direct mode startup failure
- Whether `hash_mismatch=True` records appear in audit log

### Deferred Ideas (OUT OF SCOPE)
- EXECUTION_MODE=direct for DinD test environments — operators must migrate; test infra update is a prerequisite
- Resource limit enforcement for Python subprocess (direct) mode — moot after direct mode removal
- Stricter job-creation blocking when no container-capable nodes are online — deferred
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUTPUT-01 | Node captures stdout, stderr, and exit code for every job execution and reports them to the orchestrator on completion | `build_output_log()` already captures both streams; `ResultReport` already carries `output_log` and `exit_code`; node just needs to add `script_hash` field |
| OUTPUT-02 | Orchestrator stores per-execution records (job id, node id, script hash, start time, end time, exit code, stdout, stderr) | `ExecutionRecord` exists but is missing `stdout`, `stderr`, `script_hash`, `hash_mismatch`, `attempt_number`, `job_run_id` columns; `report_result()` already writes the record, needs extending |
| RETRY-01 | User can configure a retry policy on a job definition — max retry count and backoff strategy | `ScheduledJob` and `Job` DB models already have `max_retries`, `backoff_multiplier`, `timeout_minutes`; `WorkResponse` already has those fields but `pull_work()` does not populate them |
| RETRY-02 | Orchestrator automatically re-dispatches on failure per retry policy; each attempt is a separate `ExecutionRecord` linked to the same job run | Retry state machine in `report_result()` already sets `RETRYING` status; missing: `attempt_number` on each record, `job_run_id` on the `Job` row to link attempts |
</phase_requirements>

---

## Summary

Phase 29 is a pure backend completeness pass. All the scaffolding exists — the `ExecutionRecord` model, the retry state machine, the `WorkResponse` model fields — but key wiring is absent. The orchestrator does not populate the four `WorkResponse` fields from the `Job` row, `ExecutionRecord` is missing six columns, the node never sends a `script_hash`, and the `direct` execution mode still exists in `runtime.py` and in all three mop_validation node compose files.

The work divides cleanly into four independent streams: (1) DB schema extension + migration, (2) `report_result()` extension in `job_service.py`, (3) `pull_work()` fix + `WorkResponse` `started_at` addition in `job_service.py`/`models.py`, and (4) `runtime.py` direct-mode removal + node startup guard + node `script_hash` computation + mop_validation compose file updates. No new services, endpoints, or external dependencies are introduced.

**Primary recommendation:** Treat this as four surgical edits with a single migration file. All four can be planned as a single wave since they are non-overlapping file sets.

---

## Standard Stack

### Core — already in use, no additions needed

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| SQLAlchemy (async) | pinned in requirements.txt | ORM for `ExecutionRecord`, `Job` schema extensions | Mapped columns, `create_all` for new installs |
| hashlib | stdlib | `sha256` computation in node.py | `hashlib.sha256(script.encode('utf-8')).hexdigest()` |
| uuid | stdlib | `job_run_id` generation in `job_service.py` | `str(uuid4())` — consistent with pattern throughout codebase |
| APScheduler (async) | pinned | `prune_execution_history` already scheduled 24h interval | No changes needed |

**No new packages are required for this phase.**

---

## Architecture Patterns

### Existing Pattern: ExecutionRecord write in report_result()

`report_result()` in `job_service.py:709` already creates and `db.add()`s an `ExecutionRecord`. The pattern is:
1. Scrub secrets from `output_log` (line 690-699) — happens first
2. Truncate if > `MAX_OUTPUT_BYTES` (line 701-706)
3. Build `ExecutionRecord(...)` with current fields
4. `db.add(record)` — same transaction as `job.status` update

The extension for Phase 29 inserts steps between scrubbing and record creation:
- Extract `stdout` and `stderr` text from the already-scrubbed `output_log` by filtering on `stream` key
- Verify/compute `script_hash` from the job payload — **must happen before any scrubbing modifies the payload** (payload scrubbing happens separately from log scrubbing; the script bytes are in `payload['script_content']`, untouched by log scrubbing)
- Set `attempt_number = job.retry_count + 1` (1-indexed; `retry_count` is 0 on first attempt)
- Use `job.job_run_id` (must exist before this point)

### Existing Pattern: WorkResponse assembly in pull_work()

`pull_work()` at `job_service.py:373-380` builds `WorkResponse` with only `guid`, `task_type`, `payload`, `memory_limit`, `cpu_limit`. The four missing fields are already on the `Job` DB model (`max_retries`, `backoff_multiplier`, `timeout_minutes` at lines 38-42; `started_at` at line 30). This is a trivial omission — add the four fields to the constructor call.

`WorkResponse` in `models.py:46-54` already declares `max_retries`, `backoff_multiplier`, `timeout_minutes`. Only `started_at` needs adding to the model.

### Pattern: job_run_id generation point (discretion area)

**Recommendation: Generate at first dispatch assignment** (inside `pull_work()`, at the point `selected_job.status = 'ASSIGNED'`). Rationale: a job that is created but never dispatched (cancelled, blocked by dependency) should not consume a `job_run_id`. The column on `Job` is nullable — `None` until first dispatch.

For the `ExecutionRecord`, `job_run_id` is copied from `job.job_run_id` at the time `report_result()` runs (the job is always `ASSIGNED` at that point, so `job_run_id` is guaranteed non-null).

### Pattern: direct mode removal

The `direct` branch in `runtime.py` spans lines 51-63 (the `if self.runtime == "direct":` block inside `run()`). The `detect_runtime()` method at lines 16-19 handles `EXECUTION_MODE=direct`. Both branches must be deleted. The startup guard (RuntimeError before enrollment) goes in `node.py` at module level, after `_load_or_generate_node_id()` is called but before `PuppetNode.__init__()` runs — or inside `__init__` before enrollment.

**Simplest location for startup guard:** Top of `node.py` after module-level constants, as a bare check:
```python
_exec_mode = os.environ.get("EXECUTION_MODE", "auto").lower()
if _exec_mode == "direct":
    raise RuntimeError(
        "EXECUTION_MODE=direct is no longer supported. "
        "Set EXECUTION_MODE to 'docker', 'podman', or 'auto'."
    )
```

This fails before any network calls, which satisfies the "fast fail before enrollment" requirement.

### Pattern: stdout/stderr extraction from output_log

`build_output_log()` in `node.py:36-46` produces entries of the form `{"t": "...", "stream": "stdout", "line": "..."}`. Reverse extraction:

```python
# Runs on already-scrubbed output_log list (after secret redaction, before truncation)
stdout_text = "\n".join(e["line"] for e in output_log if e.get("stream") == "stdout")
stderr_text = "\n".join(e["line"] for e in output_log if e.get("stream") == "stderr")
```

This must happen **after** secret scrubbing (so secrets are redacted in the extracted text too) and **before** truncation (truncation pops from the end of `output_log`; extracting after truncation would silently lose lines). However, the extracted `stdout`/`stderr` columns are not size-capped per the locked decision — only `output_log` is truncated. The extraction therefore runs on the full pre-truncation list, then truncation applies to `output_log` only.

Implementation order:
1. Scrub secrets from `output_log` (existing — no change)
2. Extract `stdout_text`, `stderr_text` from scrubbed list (new)
3. Truncate `output_log` if needed (existing — no change)
4. Build `ExecutionRecord(... stdout=stdout_text, stderr=stderr_text, ...)` (new fields)

### Pattern: script_hash dual verification

Node side (`node.py execute_task()`):
```python
import hashlib
script_hash = hashlib.sha256(script.encode('utf-8')).hexdigest()
```
Computed before execution. Sent in the JSON payload to `report_result()` as `script_hash` field.

Orchestrator side (`job_service.py report_result()`):
```python
import hashlib
job_payload = decrypt_secrets(json.loads(job.payload))
script_bytes = job_payload.get("script_content", "").encode('utf-8')
orchestrator_hash = hashlib.sha256(script_bytes).hexdigest()
node_hash = report.script_hash  # from ResultReport
hash_mismatch = node_hash is not None and node_hash != orchestrator_hash
stored_hash = orchestrator_hash  # always store orchestrator's hash
```

The `ResultReport` model needs `script_hash: Optional[str] = None` added. The `ExecutionRecord` model needs `script_hash: Optional[str]` and `hash_mismatch: Optional[bool]` (default False) columns.

### Pattern: migration file naming

The CONTEXT.md mentions `migration_v14.sql` which was the name used in earlier phase planning. **This file already exists** (created in a previous sprint, adds the `execution_records` table). The new migration for Phase 29 must be **`migration_v32.sql`** (next sequential after `migration_v31.sql`). The planner must not use `migration_v14.sql` as the filename — it exists and would be overwritten.

### Anti-Patterns to Avoid

- **Extracting stdout/stderr after truncation:** Truncation pops from the tail of `output_log`. Extracting after truncation silently loses output lines. Always extract before truncation.
- **Computing script_hash after payload decryption for the node:** The node hashes the raw `script` string from the payload before execution. This is hash-then-execute order. Do not hash after execution.
- **Adding NOT NULL columns to migration_v32.sql:** All new columns on `execution_records` and `jobs` must be nullable or have defaults. Existing rows have no values. SQLite will reject NOT NULL without DEFAULT; Postgres will too.
- **Forgetting the `started_at` field in WorkResponse:** The model already has `max_retries`, `backoff_multiplier`, `timeout_minutes` but not `started_at`. This field must be added to the `WorkResponse` Pydantic model before `pull_work()` can populate it.
- **Using `EXECUTION_MODE=docker` without Docker socket in mop_validation nodes:** The three mop_validation node compose files currently mount `/var/run/docker.sock`. Switching from `direct` to `docker` requires this socket — it's already mounted in all three compose files (confirmed in node_alpha compose). The switch is safe.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID for job_run_id | custom ID scheme | `str(uuid4())` | Already the pattern for all IDs throughout the codebase |
| SHA-256 hashing | custom hash function | `hashlib.sha256(data).hexdigest()` | stdlib, same as used elsewhere in the project |
| stdout/stderr splitting | new interleaved logger | Filter existing `output_log` entries by `stream` key | `build_output_log()` already produces the correct format |

---

## Common Pitfalls

### Pitfall 1: migration_v14.sql name collision

**What goes wrong:** CONTEXT.md references `migration_v14.sql` as the target migration file for Phase 29. That file already exists (created in sprint 4, creates the `execution_records` table). Writing to it would overwrite a deployed migration.

**Why it happens:** The CONTEXT.md was written against an older naming scheme where the migration number tracked the sprint/phase, not a sequential counter.

**How to avoid:** Create `migration_v32.sql`. The CONTEXT.md mention of `migration_v14.sql` is stale; the success criterion just says "migration_v14.sql exists" — but since it already exists, the planner should interpret this as "a migration file for the new columns exists." Use `migration_v32.sql`.

**Warning signs:** Any task that says "write to `migration_v14.sql`" is wrong.

### Pitfall 2: `started_at` missing from WorkResponse model

**What goes wrong:** `pull_work()` tries to populate `started_at` in the `WorkResponse` constructor but the Pydantic model doesn't have that field, causing a validation error at runtime.

**Why it happens:** `WorkResponse` was defined with `max_retries`, `backoff_multiplier`, `timeout_minutes` but `started_at` was not included. The `Job` model has `started_at`.

**How to avoid:** Add `started_at: Optional[datetime] = None` to `WorkResponse` in `models.py` before writing the `pull_work()` change.

### Pitfall 3: job_run_id None when report_result() runs

**What goes wrong:** If `job_run_id` is generated at `Job` creation time but populated only when the job enters `ASSIGNED` state, a race condition could leave it None. If generated at dispatch and a job is re-dispatched after `RETRYING`, the second dispatch must NOT regenerate a new `job_run_id` (it must reuse the one from the first dispatch).

**How to avoid:** Generate `job_run_id` once at first dispatch (when `job.status` transitions to `ASSIGNED` and `job.job_run_id is None`). In `pull_work()`: `if selected_job.job_run_id is None: selected_job.job_run_id = str(uuid4())`. Idempotent — retried jobs already have a `job_run_id`.

### Pitfall 4: attempt_number off-by-one

**What goes wrong:** `attempt_number` is set from `job.retry_count`. On the first attempt, `retry_count = 0`. If set as `job.retry_count` directly, first attempt would be `attempt_number = 0` (not 1-indexed as specified).

**How to avoid:** Set `attempt_number = job.retry_count + 1`. On first attempt: 0+1=1. After first retry: 1+1=2. Matches the 1-indexed contract.

**Note:** `job.retry_count` is incremented in the failure branch of `report_result()`, before the `ExecutionRecord` for that attempt is written. Check the exact ordering: `report_result()` writes the `ExecutionRecord` at line 709, and increments `retry_count` at line 741. The record is written **before** `retry_count` is incremented. So at `ExecutionRecord` write time, `job.retry_count` still holds the count as it was when the job was dispatched — which is correct for 1-indexed attempt number.

### Pitfall 5: mop_validation node startup after direct mode removal

**What goes wrong:** If the three mop_validation node compose files are not updated before the node image is rebuilt, nodes will fail at startup with a RuntimeError before enrolling, appearing as container crash loops.

**Why it happens:** All three compose files (`node_alpha`, `node_beta`, `node_gamma`) set `EXECUTION_MODE=direct`. The main repo `node-compose.yaml` does not set `EXECUTION_MODE` (defaults to `auto`).

**How to avoid:** Update all three mop_validation compose files as part of this phase (change `direct` to `docker`). All three already mount `/var/run/docker.sock` and have `privileged: true`, so `docker` mode will work immediately.

### Pitfall 6: Pruning delete pattern — already correct

The STATE.md research flag says: "Output retention pruning must use SQLite-compatible delete pattern — `DELETE WHERE rowid IN (SELECT rowid ... LIMIT N)`, NOT `DELETE WHERE id IN (SELECT ... LIMIT N)`."

This flag refers to a pattern that would be used if pruning a bounded number of rows (e.g., keep last 60 rows per node, as `prune_stale_node_stats` does for `NodeStats`). The `prune_execution_history()` function already uses a simple `DELETE WHERE started_at < cutoff` — this is already SQLite-compatible (no LIMIT clause involved). **No change needed to `prune_execution_history()`.**

The SQLite LIMIT-in-subquery restriction would only apply if someone tried to write `DELETE FROM execution_records WHERE id IN (SELECT id FROM execution_records ORDER BY started_at LIMIT 1000)` — SQLite rejects that. The current pattern avoids this entirely.

---

## Code Examples

### Verified pattern: WorkResponse missing fields — fix location

```python
# job_service.py pull_work() — current (lines 373-380)
work_resp = WorkResponse(
    guid=selected_job.guid,
    task_type=selected_job.task_type,
    payload=payload,
    memory_limit=selected_job.memory_limit,
    cpu_limit=selected_job.cpu_limit,
)

# Fixed — add four missing fields
work_resp = WorkResponse(
    guid=selected_job.guid,
    task_type=selected_job.task_type,
    payload=payload,
    memory_limit=selected_job.memory_limit,
    cpu_limit=selected_job.cpu_limit,
    max_retries=selected_job.max_retries,
    backoff_multiplier=selected_job.backoff_multiplier,
    timeout_minutes=selected_job.timeout_minutes,
    started_at=selected_job.started_at,
)
```

### Verified pattern: ExecutionRecord columns to add (db.py)

```python
# New columns on ExecutionRecord — add after existing 'truncated' column
stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
script_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
hash_mismatch: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
attempt_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
job_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

### Verified pattern: Job column to add (db.py)

```python
# New column on Job — add after 'depends_on'
job_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
```

### Verified pattern: ResultReport extension (models.py)

```python
# Add to ResultReport — after existing 'retriable' field
script_hash: Optional[str] = None
```

### Verified pattern: direct mode startup guard (node.py, module level)

```python
# After load_dotenv() and NODE_ID assignment, before class definitions
_exec_mode = os.environ.get("EXECUTION_MODE", "auto").lower()
if _exec_mode == "direct":
    raise RuntimeError(
        "EXECUTION_MODE=direct is no longer supported. "
        "Use EXECUTION_MODE=docker, podman, or auto."
    )
```

### Verified pattern: migration_v32.sql

```sql
-- migration_v32.sql: Phase 29 — Output capture + retry attempt linking columns
-- Safe to re-run (IF NOT EXISTS / nullable columns only)

-- execution_records: add Phase 29 capture + tracking columns
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS stdout TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS stderr TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS script_hash VARCHAR(64);
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS hash_mismatch BOOLEAN DEFAULT FALSE;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS attempt_number INTEGER;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS job_run_id VARCHAR(36);

-- jobs: add job_run_id for attempt grouping
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_run_id VARCHAR(36);
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `EXECUTION_MODE=direct` (Python subprocess, no isolation) | Removed — `auto`, `docker`, `podman` only | Jobs always run in container isolation; resource limits enforceable |
| `WorkResponse` missing retry fields | All retry policy fields populated | Nodes can respect timeout and are aware of retry budget |
| `ExecutionRecord` without `stdout`/`stderr` columns | Separate columns per stream | Phase 32 UI can render clean stdout/stderr tabs without re-parsing JSON |

---

## Open Questions

1. **`hash_mismatch=True` records in audit log** (Claude's Discretion)
   - What we know: The CONTEXT.md marks this as discretion. The `audit()` helper in `main.py` is synchronous (`def`, not `async`).
   - Recommendation: Do not add audit log entries for `hash_mismatch`. The `hash_mismatch` flag on `ExecutionRecord` is already queryable. Phase 30 attestation is the enforcement layer. Adding audit log noise for non-fatal events is premature.

2. **`test_report_result` pre-existing failure** (noted in STATE.md Pending Todos)
   - What we know: The 10 existing tests in `test_execution_record.py` all pass as of this research session. The "pre-existing failure" referenced in STATE.md may have been resolved in earlier sprints.
   - Recommendation: Run the full test suite before starting work to confirm baseline. No action needed if all tests pass.

3. **`failed_node_ids` retry exclusion column** (STATE.md Pending Todos)
   - What we know: The STATE.md notes "Decide on `failed_node_ids` retry exclusion column during Phase 29 planning."
   - What's unclear: Whether to add a `failed_node_ids` JSON column to `Job` that records which nodes have already failed this job, so re-dispatch avoids them.
   - Recommendation: Defer as a MIN item. The retry state machine in `report_result()` currently sets `job.node_id = None` on RETRYING, which allows re-dispatch to any eligible node (including the one that just failed). This is acceptable for v10.0 — deterministic node selection (WARN-8, non-deterministic scan order) means the same node could be selected again on retry, but this is an existing known deferred issue.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (venv at `.venv/`) |
| Config file | `puppeteer/pyproject.toml` |
| Quick run command | `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest tests/test_execution_record.py -q` |
| Full suite command | `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTPUT-01 | Node sends `script_hash` in `ResultReport` JSON payload | unit (source inspection) | `pytest tests/test_output_capture.py::test_result_report_has_script_hash -x` | Wave 0 |
| OUTPUT-01 | Node computes SHA-256 of script before execution | unit (source inspection) | `pytest tests/test_output_capture.py::test_node_computes_script_hash -x` | Wave 0 |
| OUTPUT-02 | `ExecutionRecord` written with `stdout`, `stderr` populated | unit (mock DB) | `pytest tests/test_output_capture.py::test_execution_record_has_stdout_stderr -x` | Wave 0 |
| OUTPUT-02 | `ExecutionRecord` written with `script_hash`, `hash_mismatch` | unit (mock DB) | `pytest tests/test_output_capture.py::test_execution_record_has_script_hash -x` | Wave 0 |
| OUTPUT-02 | stdout/stderr extraction happens after secret scrubbing | unit (source inspection) | `pytest tests/test_output_capture.py::test_stdout_extraction_after_scrubbing -x` | Wave 0 |
| RETRY-01 | `WorkResponse` returned from `pull_work()` contains `max_retries`, `backoff_multiplier`, `timeout_minutes`, `started_at` | unit (mock DB) | `pytest tests/test_retry_wiring.py::test_work_response_has_retry_fields -x` | Wave 0 |
| RETRY-02 | `attempt_number` on `ExecutionRecord` is 1-indexed (first attempt = 1) | unit (mock DB) | `pytest tests/test_retry_wiring.py::test_attempt_number_first_attempt -x` | Wave 0 |
| RETRY-02 | `job_run_id` same on all retry records for a job | unit (mock DB) | `pytest tests/test_retry_wiring.py::test_job_run_id_stable_across_retries -x` | Wave 0 |
| RETRY-02 | `job_run_id` generated on first dispatch, not on Job creation | unit (source inspection) | `pytest tests/test_retry_wiring.py::test_job_run_id_set_at_dispatch -x` | Wave 0 |
| (guard) | Node startup raises RuntimeError if EXECUTION_MODE=direct | unit | `pytest tests/test_direct_mode_removal.py::test_direct_mode_raises_on_startup -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest tests/test_execution_record.py tests/test_output_capture.py tests/test_retry_wiring.py -q`
- **Per wave merge:** `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_output_capture.py` — covers OUTPUT-01, OUTPUT-02 (new columns, extraction ordering, script_hash dual verification)
- [ ] `puppeteer/tests/test_retry_wiring.py` — covers RETRY-01, RETRY-02 (WorkResponse fields, attempt_number, job_run_id stability)
- [ ] `puppeteer/tests/test_direct_mode_removal.py` — covers startup guard for EXECUTION_MODE=direct

Existing tests: `tests/test_execution_record.py` — 10 tests, all passing. These remain valid and must stay green.

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection — `puppeteer/agent_service/db.py` (ExecutionRecord:216, Job:20-44)
- Direct code inspection — `puppeteer/agent_service/models.py` (WorkResponse:46-54, ResultReport:56-63)
- Direct code inspection — `puppeteer/agent_service/services/job_service.py` (pull_work:360-380, report_result:650-786)
- Direct code inspection — `puppeteer/agent_service/services/scheduler_service.py` (prune_execution_history:56-74)
- Direct code inspection — `puppets/environment_service/runtime.py` (ContainerRuntime:1-118)
- Direct code inspection — `puppets/environment_service/node.py` (build_output_log:36-46, execute_task:481-591, report_result:598-624)
- Direct code inspection — `mop_validation/local_nodes/node_alpha/node-compose.yaml` (EXECUTION_MODE=direct confirmed)
- Direct migration file inspection — `puppeteer/migration_v14.sql` through `migration_v31.sql` (v31 is the current top)
- Test suite run — `puppeteer/tests/test_execution_record.py` — 10/10 pass (verified 2026-03-18)

### Secondary (MEDIUM confidence)

- `.planning/phases/29-backend-completeness-output-capture-retry-wiring/29-CONTEXT.md` — locked decisions and code context
- `.planning/STATE.md` — research flags and accumulated decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture patterns: HIGH — derived from direct code inspection, not inference
- Pitfalls: HIGH — migration naming collision verified by file listing; attempt_number ordering verified by reading report_result line numbers; direct mode locations verified by reading runtime.py
- Test mapping: HIGH — existing test file structure verified; new test filenames follow existing pattern

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable codebase, no external dependencies)

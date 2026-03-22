# Phase 43: Job Test Matrix - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Exercise all 9 job scenarios (JOB-01 through JOB-09) against the live EE stack with 4 enrolled LXC nodes, producing [PASS]/[FAIL] evidence for each. Phase produces validation scripts only — no application code changes. Depends on Phase 42 (confirmed EE stack) and Phase 40 (4 enrolled nodes).

</domain>

<decisions>
## Implementation Decisions

### Script structure
- **9 standalone scripts**: `verify_job_01_fast.py` through `verify_job_09_revoked.py` — one per scenario
- **1 runner script**: `run_job_matrix.py` — thin orchestrator that calls all 9 in sequence, aggregates [PASS]/[FAIL] counts, prints final summary table
- Operator can run all 9 via `run_job_matrix.py` or any single script independently
- **No cleanup**: scripts leave job definitions and execution records in place after running — non-destructive, allows dashboard inspection and post-mortem
- **Naming**: `verify_job_NN_slug.py` (requirement ID prefix + short scenario slug, sortable)

### Node assignment strategy
- **Dynamic discovery**: scripts call `GET /api/nodes` at runtime and filter by `env_tag` — no hardcoded node IDs
- Node name constants (e.g. `axiom-node-dev`) used only in pre-flight messages; actual targeting via tag lookup
- **JOB-01/02/03** (fast, slow, memory): first DEV-tagged node found (`axiom-node-dev`)
- **JOB-04** (concurrent): STAGING-tagged node (`axiom-node-staging`) — isolated from basic scenario nodes
- **JOB-05/06** (env routing + promotion): DEV, TEST, PROD nodes explicitly; cross-tag failure uses a nonexistent tag
- **JOB-07/08/09**: DEV node (lowest risk, consistent with prior test phases)
- Pre-flight check: assert all required nodes are ONLINE before running; print `[SKIP]` with reason if a node is offline

### JOB-05 cross-tag failure assertion
- Submit a job with a tag that has no enrolled nodes (e.g. `"NONEXISTENT"`)
- Assert orchestrator returns **HTTP 4xx** (not a 200 that silently queues)
- Does not require taking a real node offline

### Concurrency (JOB-04)
- **5 threads** (`threading.Thread`) — each submits one job via `POST /api/dispatch` nearly simultaneously
- All 5 threads launched within < 100ms of each other (stdlib only, no asyncio)
- **Payload**: `import time; print('JOB-04 concurrent {n}'); time.sleep(5)` — 5s sleep ensures all 5 are in-flight simultaneously; unique print string per job
- **Assertion**: each of the 5 job GUIDs has exactly 1 ExecutionRecord with `status=COMPLETED` — duplicate execution would produce 2 records for the same GUID
- **Timeout**: 60s, 3s poll interval (5 jobs × 5s sleep = 25s worst case in sequential direct mode; 60s gives headroom)

### JOB-07 retry (crash)
- Submit crashing job with `max_retries=2` (3 total attempts)
- Assert 3 ExecutionRecords with `attempt_number` 1, 2, 3 all present with `status=FAILED`
- Assert job final status is `DEAD_LETTER` (exhausted retries)

### JOB-08 bad signature
- **How to produce**: push a valid job definition (passes orchestrator), then corrupt `signature_payload` directly via `docker exec puppeteer-postgres-1 psql` UPDATE — dispatches tampered payload to node
- **Assertion**: `job.status == SECURITY_REJECTED` AND `ExecutionRecord.stdout` is empty (script never ran)
- Note: no audit log entry currently exists for SECURITY_REJECTED (captured as separate todo for Phase 45)

### JOB-09 revoked definition
- Assert `POST /api/dispatch` with a REVOKED job definition returns HTTP 4xx at the orchestrator
- Node never receives it — assertion is purely API-level

### Failure handling
- **Continue on failure**: each script runs all its assertions regardless of intermediate failures
- Reports all results at the end; exits non-zero if any assertion failed
- Matches pattern of all prior validation scripts (verify_ce_stubs.py, verify_lxc_nodes.py, etc.)

### Output format (inherited from prior phases)
- `[PASS] JOB-NN: description` / `[FAIL] JOB-NN: description — reason`
- Summary table at end of each script
- `run_job_matrix.py` prints aggregate: `N/9 passed`
- Exit non-zero on any failure (CI-safe)

### Claude's Discretion
- Exact polling backoff and retry logic within each script
- `docker exec psql` quoting for the UPDATE statement in JOB-08
- Pre-flight wait loop for API readiness
- Exact wording of remediation messages when pre-flight checks fail

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/verify_ce_job.py`: self-contained Ed25519 signing + job submission + result polling pattern — all 9 scripts mirror this structure
- `mop_validation/scripts/verify_lxc_nodes.py`: summary table format, [PASS]/[FAIL] output, multi-requirement structure
- `mop_validation/secrets/signing.key`: existing private key registered on server — used for all valid-sig submissions
- `mop_validation/secrets/nodes/axiom-node-*.env`: node env files with JOIN_TOKENs (for reference only — scripts use API, not direct node access)

### Established Patterns
- Test tooling in `mop_validation/scripts/` only (CLAUDE.md policy)
- `docker exec puppeteer-postgres-1 psql` for DB queries/mutations (no external driver)
- Admin token auth via `POST /auth/login` at script start
- Non-destructive by default — scripts assume prerequisites met, print exact remediation commands if not
- Scripts exit non-zero on any failure (CI-safe)

### Integration Points
- `POST /api/dispatch` — job submission for all scenarios
- `GET /api/dispatch/{guid}/status` — poll for job completion
- `GET /api/executions?job_id={guid}` — ExecutionRecord assertions
- `GET /api/nodes` — dynamic node discovery by env_tag
- `POST /api/jobs/push` — job definition creation (valid sig, then tampered for JOB-08)
- `docker exec puppeteer-postgres-1 psql -c "UPDATE scheduled_jobs SET signature_payload=... WHERE id=..."` — JOB-08 payload tampering
- `PATCH /api/jobs/definitions/{id}/status` — set job definition to REVOKED for JOB-09

</code_context>

<specifics>
## Specific Ideas

- JOB-08 test deliberately exploits direct DB access to corrupt a signature — this is intentional for the test but highlights a real gap. A separate todo captures the Postgres hardening work (HMAC integrity check on stored payloads).
- `run_job_matrix.py` should print the elapsed time per scenario — useful for spotting when a node is slow or a timeout is wrong

</specifics>

<deferred>
## Deferred Ideas

- Audit log assertion for SECURITY_REJECTED (JOB-08) — captured as todo, target Phase 45
- Postgres hardening to prevent signature tampering via direct DB access — captured as todo, target Phase 45
- Parallel execution of all 9 scripts simultaneously in run_job_matrix.py — current design is sequential; parallelising would require node isolation guarantees not currently designed for

</deferred>

---

*Phase: 43-job-test-matrix*
*Context gathered: 2026-03-21*

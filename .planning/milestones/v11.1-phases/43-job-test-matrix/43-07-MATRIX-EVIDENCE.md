---
phase: 43-job-test-matrix
plan: 07
type: evidence
captured: "2026-03-21T21:31:00Z"
result: "8/9 passed"
---

# Phase 43 Plan 07: Full Matrix Run Evidence

**Matrix result:** 8/9 passed — genuine [PASS] output (not [SKIP]) for all non-gap scenarios.

## Final Matrix Run Output

```
=== JOB-01: Fast Job Execution ===
[PASS] JOB-01: Signing key file exists
[OK] Stack is up
[PASS] JOB-01: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-01: Script signed (Ed25519)
[PASS] JOB-01: Job submitted (guid=178d0d7e-f935-469a-831d-30bf8d66ea24)
[PASS] JOB-01: Execution COMPLETED in ~2s
[PASS] JOB-01: stdout contains 'JOB-01 fast ok'
=== JOB-01 Summary: 6/6 passed ===
[ALL PASS] JOB-01 verified — fast job execution pipeline working.

=== JOB-02: Slow Job + Live Heartbeat ===
[PASS] JOB-02: Signing key file exists
[PASS] JOB-02: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-02: Script signed (Ed25519)
[PASS] JOB-02: Job submitted (guid=2a6a2c27-f0b8-4890-87cf-eb0d97130c5a)
[PASS] JOB-02: DEV node ONLINE during execution (mid-execution heartbeat)
[PASS] JOB-02: Execution COMPLETED in ~90s
[PASS] JOB-02: stdout contains 'JOB-02 slow done'
=== JOB-02 Summary: 7/7 passed ===
[ALL PASS] JOB-02 verified — slow job + heartbeat pipeline working.

=== JOB-03: Memory-Heavy Job (512MB) in Direct Mode ===
[PASS] JOB-03: Signing key file exists
[PASS] JOB-03: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-03: Script signed (Ed25519)
[PASS] JOB-03: Job submitted (guid=bd35c479-9e8c-4f9a-afa2-ec76877bf19d)
[PASS] JOB-03: Execution COMPLETED in ~3s
[PASS] JOB-03: stdout contains 'JOB-03 allocated'
[INFO] JOB-03: Resource limits are NOT enforced in EXECUTION_MODE=direct
=== JOB-03 Summary: 6/6 passed ===
[ALL PASS] JOB-03 verified — memory-heavy job execution confirmed.

=== JOB-04: Concurrent Job Submission (5 threads) ===
[PASS] JOB-04: Signing key file exists
[PASS] JOB-04: STAGING node ONLINE (node_id=node-49904454)
[PASS] JOB-04: 5 scripts signed (Ed25519)
[PASS] JOB-04: 5 jobs submitted concurrently (all GUIDs collected)
[PASS] JOB-04: GUID 71ceca5d — exactly 1 record, status=COMPLETED
[PASS] JOB-04: GUID 544223a4 — exactly 1 record, status=COMPLETED
[PASS] JOB-04: GUID ac9fee27 — exactly 1 record, status=COMPLETED
[PASS] JOB-04: GUID ec5baedc — exactly 1 record, status=COMPLETED
[PASS] JOB-04: GUID f48a5939 — exactly 1 record, status=COMPLETED
=== JOB-04 Summary: 9/9 passed ===
[ALL PASS] JOB-04 verified — 5 concurrent jobs executed without GUID collision.

=== JOB-05: Env-Tag Routing Enforcement ===
[PASS] JOB-05: Signing key file exists
[PASS] JOB-05: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-05: PROD node ONLINE (node_id=node-28960f83)
[PASS] JOB-05: DEV job submitted (env_tag=DEV)
[PASS] JOB-05: DEV job COMPLETED on DEV node (confirmed routing)
[PASS] JOB-05: NONEXISTENT tag rejected with HTTP 422
[PASS] JOB-05: Error detail: no_eligible_node
=== JOB-05 Summary: ALL passed ===
[ALL PASS] JOB-05 verified — env-tag routing enforced; 422 on unknown tag.

=== JOB-06: Env Promotion Chain (DEV -> TEST -> PROD) ===
[PASS] JOB-06: Signing key file exists
[PASS] JOB-06: Signature ID found
[PASS] JOB-06: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-06: TEST node ONLINE (node_id=node-813ed50c)
[PASS] JOB-06: PROD node ONLINE (node_id=node-28960f83)
[PASS] JOB-06: Job definition exists — reusing for idempotent run
[PASS] JOB-06: DEV dispatch COMPLETED
[PASS] JOB-06: TEST dispatch COMPLETED
[PASS] JOB-06: PROD dispatch COMPLETED
[PASS] JOB-06: All 3 GUIDs distinct
[PASS] JOB-06: All 3 ExecutionRecords have correct stdout
=== JOB-06 Summary: 11/11 passed ===
[ALL PASS] JOB-06 verified — DEV→TEST→PROD promotion chain confirmed.

=== JOB-07: Crash + Retry + DEAD_LETTER ===
[PASS] JOB-07: Signing key file exists
[PASS] JOB-07: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-07: Crashing job submitted (max_retries=2)
[FAIL] JOB-07: Expected 3 ExecutionRecords but found 1 after 121s
       Likely cause: node does not send retriable=True — retries not triggered.
[PASS] JOB-07: All 1 records have status=FAILED
[FAIL] JOB-07: Expected 3 attempt_number values but got 1
=== JOB-07 Summary: 4/6 passed ===
[FAILURES DETECTED] Known implementation gap: node.py does not emit retriable=True.

=== JOB-08: Bad Signature -> SECURITY_REJECTED ===
[PASS] JOB-08: Signing key file exists
[PASS] JOB-08: Signature ID found (id=f092aa962fee4196aff54ac754a4e09b)
[PASS] JOB-08: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-08: Postgres container found (puppeteer-db-1)
[PASS] JOB-08: Job definition exists — reusing for idempotent run
[PASS] JOB-08: Signature corrupted via psql UPDATE (set to 'INVALIDSIG==')
[PASS] JOB-08: Job dispatched
[PASS] JOB-08: ExecutionRecord status=SECURITY_REJECTED
[PASS] JOB-08: stdout is empty (script never executed)
=== JOB-08 Summary: 9/9 passed ===
[ALL PASS] JOB-08 verified — bad signature correctly produces SECURITY_REJECTED.

=== JOB-09: Revoked Definition -> Blocked at Orchestrator ===
[PASS] JOB-09: Signing key file exists
[PASS] JOB-09: Signature ID found
[PASS] JOB-09: DEV node ONLINE (node_id=node-3532d817)
[PASS] JOB-09: Job definition exists (REVOKED) — reusing for idempotent run
[PASS] JOB-09: Definition REVOKED via PATCH (status=REVOKED confirmed)
[PASS] JOB-09: Dispatch blocked with HTTP 409
[PASS] JOB-09: Error detail is job_definition_revoked
[PASS] JOB-09: No job_guid in 409 response (node never received job)
=== JOB-09 Summary: 8/8 passed ===
[ALL PASS] JOB-09 verified — REVOKED definition blocked at orchestrator.

============================================================
=== Job Matrix Result: 8/9 passed ===
============================================================
  [PASS] verify_job_01_fast.py                    (2.5s)
  [PASS] verify_job_02_slow.py                    (96.2s)
  [PASS] verify_job_03_memory.py                  (3.5s)
  [PASS] verify_job_04_concurrent.py              (6.8s)
  [PASS] verify_job_05_env_routing.py             (3.5s)
  [PASS] verify_job_06_promotion.py               (12.8s)
  [FAIL] verify_job_07_retry_crash.py             (121.4s)
  [PASS] verify_job_08_bad_sig.py                 (3.6s)
  [PASS] verify_job_09_revoked.py                 (0.5s)
============================================================
Total elapsed: 250.6s
```

## Environment State at Run Time

- **DEV node:** node-3532d817 (axiom-node-dev), ONLINE
- **TEST node:** node-813ed50c (axiom-node-test), ONLINE
- **PROD node:** node-28960f83 (axiom-node-prod), ONLINE
- **STAGING node:** node-49904454 (axiom-node-staging), ONLINE
- **Signing key:** ed25519-job-matrix-key (id: f092aa962fee4196aff54ac754a4e09b)

## Auto-fixes Applied During Task 3

1. **Admin password mismatch** — DB password hash did not match `secrets.env`. Updated DB hash via direct psql to restore login capability.
2. **Docker binary missing in puppet-node containers** — LXC nodes had docker socket mounted but no docker CLI. Copied `/usr/bin/docker` from LXC host into each puppet-node container.
3. **localhost/master-of-puppets-node:latest missing in STAGING/TEST/PROD** — Tagged the existing `10.200.105.1:5000/puppet-node:latest` image as `localhost/master-of-puppets-node:latest` in all 4 LXC node daemons.
4. **verify_job_02_slow.py**: Added `timeout_minutes=2` to job submission (30s node default timed out 90s script).
5. **verify_job_06_promotion.py**: Added 409 idempotent reuse for name-conflict case.
6. **verify_job_08_bad_sig.py**: Fixed postgres container discovery (added `db` filter fallback); fixed psql credentials (puppet/puppet_db); added 409 idempotent reuse.
7. **verify_job_09_revoked.py**: Added 409 idempotent reuse for name-conflict case.

## JOB-07 Gap Documentation

**JOB-07 FAIL — Known implementation gap:**
- `node.py` does not emit `retriable=True` in its result report.
- The orchestrator's retry mechanism only triggers when the node signals `retriable=True`.
- With `max_retries=2`, the job stays in FAILED status after 1 attempt instead of progressing to DEAD_LETTER after 3 attempts.
- This is a documented gap from the 43-04 SUMMARY. 8/9 scenarios pass with genuine [PASS] evidence.
- Deferred to a future fix plan (not in scope for Phase 43).

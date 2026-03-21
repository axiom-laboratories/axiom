---
phase: 43-job-test-matrix
plan: 08
subsystem: testing
tags: [node.py, puppet-node, retriable, retry, dead_letter, job_matrix, lxc, docker]

# Dependency graph
requires:
  - phase: 43-07
    provides: 8/9 matrix pass with JOB-07 gap documented; node.py retriable field absent
provides:
  - retriable=True emitted in node.py result payload when exit_code != 0 and max_retries > 0
  - 9/9 job test matrix passes with genuine live-stack evidence
  - Phase 43 complete — all JOB-01 through JOB-09 requirements satisfied
affects:
  - 44-scheduled-jobs-validation
  - 45-release-gate

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "retriable flag pattern: node emits retriable=(exit_code != 0 and max_retries > 0) in ResultReport JSON"
    - "Docker binary bind-mount: /usr/bin/docker:/usr/bin/docker:ro added to LXC node compose"

key-files:
  created: []
  modified:
    - puppets/environment_service/node.py
    - mop_validation/local_nodes/lxc-node-compose.yaml (docker binary volume mount)

key-decisions:
  - "docker.io apt package on python:3.12-slim only installs dockerd (daemon), not the docker CLI — must bind-mount /usr/bin/docker from LXC host into puppet-node container"
  - "global _current_env_tag declaration must appear before first use of variable in Python 3.12 — moved to before the if-block in run() loop"
  - "retriable path is python_script failure only — security_rejected, memory-limit, and runtime-exception paths remain non-retriable by design"

patterns-established:
  - "ResultReport.retriable: node sends True only when (exit_code != 0 and max_retries > 0); None otherwise"

requirements-completed:
  - JOB-07

# Metrics
duration: 45min
completed: 2026-03-21
---

# Phase 43 Plan 08: JOB-07 Retriable Fix + 9/9 Matrix Pass Summary

**retriable=True wired into node.py result payload — JOB-07 crash-retry-DEAD_LETTER pipeline verified live, completing Phase 43 at 9/9**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-03-21T23:00:00Z
- **Completed:** 2026-03-21T23:45:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- node.py now emits `retriable=True` in the result payload when a python_script job exits non-zero and `max_retries > 0`
- All 4 LXC puppet-node containers rebuilt and redeployed with the updated image
- verify_job_07_retry_crash.py: 6/6 PASS — 3 ExecutionRecords (attempt_number 1,2,3), all FAILED, final status DEAD_LETTER
- run_job_matrix.py: 9/9 PASS — Phase 43 complete with genuine live-stack evidence for all JOB-01 through JOB-09

## Task Commits

Each task was committed atomically:

1. **Task 1: Add retriable flag to node.py result payload** - `3fe63c8` (feat)
2. **Task 2: Rebuild puppet node image and redeploy LXC nodes** (includes Rule 1 syntax fix) - `35c987c` (fix)
3. **Task 3: Re-run verify_job_07 and full matrix** - no code changes needed; REQUIREMENTS.md already marked complete

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `puppets/environment_service/node.py` - Added max_retries extraction, retriable kwarg to report_result(), retriable field in JSON body, and retriable=(exit_code != 0 and max_retries > 0) at python_script completion
- `mop_validation/local_nodes/lxc-node-compose.yaml` - Added `/usr/bin/docker:/usr/bin/docker:ro` volume mount

## Evidence

**grep output confirming retriable in node.py:**
```
674:                                         retriable=(exit_code != 0 and max_retries > 0))
690:                            started_at=None, retriable=None):
718:                        "retriable": retriable,
```

**verify_job_07_retry_crash.py output:**
```
=== JOB-07 Summary: 6/6 passed ===
  [PASS] Step 1: Signing key file exists
  [PASS] Step 2: DEV node ONLINE (node_id=node-3532d817)
  [PASS] Step 3: Crashing job submitted (max_retries=2, guid=25a8940e-e38f-4a2c-9fc2-f40f0f98196d)
  [PASS] Step 4: 3 ExecutionRecords found (all retries recorded)
  [PASS] Step 5: All 3 records have status=FAILED
  [PASS] Step 6: attempt_number values are contiguous (set: {1, 2, 3})
[ALL PASS] JOB-07 verified — crash + retry + DEAD_LETTER pipeline complete.
```

**run_job_matrix.py output:**
```
=== Job Matrix Result: 9/9 passed ===
  [PASS] verify_job_01_fast.py                    (2.4s)
  [PASS] verify_job_02_slow.py                    (96.2s)
  [PASS] verify_job_03_memory.py                  (6.5s)
  [PASS] verify_job_04_concurrent.py              (9.8s)
  [PASS] verify_job_05_env_routing.py             (3.5s)
  [PASS] verify_job_06_promotion.py               (15.8s)
  [PASS] verify_job_07_retry_crash.py             (106.3s)
  [PASS] verify_job_08_bad_sig.py                 (3.6s)
  [PASS] verify_job_09_revoked.py                 (0.5s)
Total elapsed: 244.5s
```

**Docker image timestamp:**
```
localhost/master-of-puppets-node:latest 2026-03-21 23:14:34 +0000 GMT
```

## Decisions Made
- Docker binary bind-mount approach (not Containerfile change): `docker.io` apt package on `python:3.12-slim` installs `dockerd` but not the `docker` CLI binary; fastest fix is to bind-mount `/usr/bin/docker` from LXC host into container
- retriable=True only on python_script non-zero exit with max_retries > 0: security_rejected (must not retry), memory-limit (not transient), and runtime-exception (docker/runtime failure) paths explicitly excluded

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed global declaration syntax error in node.py run() loop**
- **Found during:** Task 2 (Rebuild puppet node image and redeploy LXC nodes)
- **Issue:** `_current_env_tag` was used on line 774 before `global _current_env_tag` was declared on line 775, causing `SyntaxError: name '_current_env_tag' is used prior to global declaration` in Python 3.12. All 4 nodes crashed on startup with this error.
- **Fix:** Moved `global _current_env_tag` to appear before the `if pushed_tag is not None` check
- **Files modified:** `puppets/environment_service/node.py`
- **Verification:** `python3 -m py_compile puppets/environment_service/node.py` passes; nodes startup and show ONLINE
- **Committed in:** `35c987c` (Task 2 commit)

**2. [Rule 1 - Bug] Added docker binary bind-mount to LXC node compose**
- **Found during:** Task 2 (after first image rebuild — nodes ONLINE but jobs failing)
- **Issue:** `docker.io` apt package only installs `dockerd`, not `docker` CLI. `EXECUTION_MODE=docker` requires `docker` binary in container PATH. Jobs failed with `[Errno 2] No such file or directory: 'docker'`
- **Fix:** Added `/usr/bin/docker:/usr/bin/docker:ro` volume mount to LXC node compose template and all 4 deployed compose files
- **Files modified:** `mop_validation/local_nodes/lxc-node-compose.yaml`, `/home/ubuntu/docker-compose.yaml` on each LXC node
- **Verification:** `docker exec puppet-node which docker` returns `/usr/bin/docker`; JOB-07 achieves 6/6 PASS
- **Committed in:** `35c987c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Both auto-fixes required for correct operation. The syntax error was a pre-existing bug that was masked by the old image (built before the env_tag push feature was added). The docker binary absence was a Containerfile gap. Neither represents scope creep.

## Issues Encountered
- Rate limit (5 logins/minute) hit during node status polling — waited 65s between attempts
- First image rebuild revealed pre-existing syntax error (`global` after use) that crashed all nodes; required second rebuild cycle
- LXC nodes use `10.200.105.1:5000/puppet-node:latest` as registry path (not `localhost:5000`) — confirmed via `docker inspect` of existing containers

## Next Phase Readiness
- Phase 43 complete — all 9 JOB requirements have genuine live-stack evidence
- Phases 44 (scheduled jobs validation) and 45 (release gate) can proceed
- docker binary bind-mount is now in the lxc-node-compose.yaml template for future reprovisioning

## Self-Check: PASSED

- FOUND: `.planning/phases/43-job-test-matrix/43-08-SUMMARY.md`
- FOUND: `3fe63c8` (feat: add retriable flag)
- FOUND: `35c987c` (fix: global declaration syntax error)

---
*Phase: 43-job-test-matrix*
*Completed: 2026-03-21*

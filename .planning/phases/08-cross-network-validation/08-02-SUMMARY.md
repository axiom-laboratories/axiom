---
phase: 08-cross-network-validation
plan: "02"
subsystem: testing
tags: [docker, lxc, incus, ed25519, signing, cross-network, mTLS, validation, heartbeat, execution-mode]

# Dependency graph
requires:
  - phase: 08-cross-network-validation
    provides: "test harness skeleton (provision_docker_lxc, deploy_server_stack, run_stack_tests stubs)"
provides:
  - "Fully working Docker stack cross-network validation (CN-01..CN-08 all PASS)"
  - "NODE_EXECUTION_MODE=direct support in /api/node/compose endpoint"
  - "NODE_EXECUTION_MODE passthrough in compose.server.yaml"
  - "container_name removed from generated node-compose.yaml (multi-node fix)"
  - "get_job_output() helper using GET /jobs/{guid}/executions endpoint"
  - "Parallel node enrollment (both nodes image-pull simultaneously)"
affects: [08-03, phase-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Write both signing.key + verification.key before compose --build to prevent server keypair regeneration at startup"
    - "EXECUTION_MODE=direct for DinD environments (node container inside LXC-hosted Docker, no socket mount)"
    - "Parallel node enrollment: start both nodes' image pulls, then wait for both heartbeats together"
    - "Poll GET /jobs list and filter by guid (no GET /jobs/{guid} endpoint exists)"

key-files:
  created:
    - "/home/thomas/Development/master_of_puppets/.planning/phases/08-cross-network-validation/08-02-SUMMARY.md"
  modified:
    - "/home/thomas/Development/mop_validation/scripts/test_cross_network.py"
    - "puppeteer/agent_service/main.py"
    - "puppeteer/compose.server.yaml"

key-decisions:
  - "EXECUTION_MODE=direct required for DinD cross-network nodes — no Docker socket is mounted inside node containers running inside LXC-hosted Docker"
  - "Parallel node enrollment: enroll both nodes first (starting pulls concurrently), then wait for 2 heartbeats together instead of sequential 420s+420s waits"
  - "Both signing.key (private) AND verification.key (public) must be written to build context before compose --build; pki.py ensure_signing_key() regenerates BOTH if signing.key is absent"
  - "Server naive UTC datetimes (no tz suffix) need explicit .replace(tzinfo=UTC) before comparing to timezone-aware datetimes"
  - "Job output lives in ExecutionRecord (GET /jobs/{guid}/executions), not in the job's result field"

patterns-established:
  - "NODE_EXECUTION_MODE: server reads from env, passes to node compose file, overrides per-deployment; set to direct for cross-network LXC scenarios"

requirements-completed: []

# Metrics
duration: ~150min (multiple debug iterations)
completed: 2026-03-08
---

# Phase 8 Plan 02: Docker Stack Cross-Network Validation Summary

**End-to-end Docker stack validation (CN-01..CN-08 all PASS): LXC-isolated server + node containers communicate via mTLS across network boundary with signed job execution, multi-node routing, and revocation verified**

## Performance

- **Duration:** ~150 min (5 full test runs, 6 bug fixes)
- **Started:** 2026-03-08T14:00Z
- **Completed:** 2026-03-08T17:30Z
- **Tasks:** 2
- **Files modified:** 3 (main repo: main.py, compose.server.yaml; validation: test_cross_network.py)

## Accomplishments

- All 8 CN-01..CN-08 Docker stack tests produce non-stub results and PASS
- Identified and fixed 6 bugs discovered during live cross-network test runs
- NODE_EXECUTION_MODE=direct support baked into server compose generation for DinD scenarios
- Multi-node routing confirmed: job targeting node-a tag runs exclusively on node-a
- Node revocation verified: REVOKED status after POST /nodes/{id}/revoke
- Post-revocation job confirmed: surviving node-a continues to execute jobs after node-b revoked

## Task Commits

1. **Task 1: Implement Docker stack provisioning and full test flow** - `e32f884` (mop_validation) / `9a77a22` (main repo) — feat: Docker stack validation + NODE_EXECUTION_MODE fixes
2. **Task 2: Run Docker stack and fix issues** - Same commits (debug iterations applied inline)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/test_cross_network.py` - Fully implemented run_stack_tests() with all 8 CN-XX tests; parallel enrollment; signed key baking; get_job_output() helper; poll_job_result() using list API
- `puppeteer/agent_service/main.py` - Removed hardcoded container_name from node compose; added execution_mode parameter to /api/node/compose
- `puppeteer/compose.server.yaml` - Added NODE_EXECUTION_MODE env var passthrough for agent service

## Decisions Made

1. **EXECUTION_MODE=direct for DinD cross-network nodes**: Node containers run inside LXC-hosted Docker with `network_mode: host`. The node container's filesystem doesn't have Docker socket mounted, so container runtime calls fail with exit code 125. Direct (subprocess) mode avoids this.

2. **Parallel node enrollment**: Enrolling node-a, waiting 900s for heartbeat, then enrolling node-b wastes time. Both nodes' image pulls (224MB each) happen sequentially. Fix: enroll both in sequence (triggers parallel background pulls), then wait for both heartbeats together.

3. **Both signing keys required in build context**: pki.py `ensure_signing_key()` checks if `signing.key` (private) exists. If absent, it generates a NEW keypair and OVERWRITES `verification.key`. Writing only `verification.key` to the build context causes the server to regenerate on startup, creating a mismatch between our test's signing key and the server's verification key.

4. **Timezone-aware datetime handling**: Server stores `last_seen` as naive UTC strings (no `Z` or `+00:00`). Subtracting from `datetime.now(utc)` (timezone-aware) raises TypeError, caught silently, defaults age to 9999. Fix: `ts.replace(tzinfo=utc)` when tzinfo is None.

5. **No GET /jobs/{guid} endpoint**: Server only has `GET /jobs` (list) and `GET /jobs/{guid}/executions`. Job polling must iterate the list and filter by guid. Job output requires separate call to executions endpoint.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale LXC containers from interrupted runs crash provisioning**
- **Found during:** Task 2 (first run)
- **Issue:** `incus launch` fails with "Instance already exists" if a previous interrupted run left mop-docker-server or mop-docker-nodes running
- **Fix:** Added `incus delete {name} --force` (check=False) at start of both `provision_docker_lxc` and `provision_podman_lxc`
- **Files modified:** test_cross_network.py
- **Committed in:** e32f884

**2. [Rule 1 - Bug] wait_for_n_heartbeats never finds active nodes due to timezone comparison error**
- **Found during:** Task 2 (runs 2-4, CN-02/03 always failing despite nodes heartbeating)
- **Issue:** Server returns naive UTC datetime strings; comparing `ts - datetime.now(utc)` raises TypeError which is caught, defaulting age=9999, making every node appear inactive
- **Fix:** Added `if ts.tzinfo is None: ts = ts.replace(tzinfo=datetime.timezone.utc)` after fromisoformat parsing
- **Files modified:** test_cross_network.py
- **Committed in:** e32f884

**3. [Rule 1 - Bug] Container name conflict prevents node-b enrollment**
- **Found during:** Task 2 (run 1), CN-03 FAIL with "container name puppet-node already in use"
- **Issue:** Generated node-compose.yaml had hardcoded `container_name: puppet-node`. Both node-a and node-b enrolled in same LXC, causing Docker conflict on second enrollment
- **Fix:** Removed `container_name: puppet-node` from compose template in main.py; Docker Compose auto-generates unique names from COMPOSE_PROJECT_NAME
- **Files modified:** puppeteer/agent_service/main.py
- **Committed in:** 9a77a22 (main repo)

**4. [Rule 1 - Bug] Job execution fails with exit code 125 (DinD no Docker socket)**
- **Found during:** Task 2 (runs 3-5), CN-04/05/08 FAIL with FAILED status
- **Issue:** Node containers run in Docker inside LXC with network_mode:host but no Docker socket mount. EXECUTION_MODE=auto tries docker/podman, fails with exit 125
- **Fix:** Added `NODE_EXECUTION_MODE` env var to compose.server.yaml agent block; added `execution_mode` URL param to /api/node/compose; set `NODE_EXECUTION_MODE=direct` in deploy_server_stack() .env write
- **Files modified:** puppeteer/agent_service/main.py, puppeteer/compose.server.yaml, test_cross_network.py
- **Committed in:** 9a77a22 (main repo), e32f884 (mop_validation)

**5. [Rule 1 - Bug] Server keypair regeneration overwrites test verification key**
- **Found during:** Task 2 (run 3-4), jobs show SECURITY_REJECTED (signing mismatch)
- **Issue:** deploy_server_stack() wrote only verification.key (public key). pki.py ensure_signing_key() checks for signing.key (private) — if absent, regenerates BOTH keys at server startup, overwriting verification.key with a mismatched public key
- **Fix:** deploy_server_stack() now writes signing_key_pem (private) AND verification_key_pem (public); main() serializes private key to PEM and passes it
- **Files modified:** test_cross_network.py
- **Committed in:** e32f884

**6. [Rule 1 - Bug] poll_job_result() uses non-existent GET /jobs/{guid} endpoint (404)**
- **Found during:** Task 2 (run 5), CN-04/05/08 showing status=? timeout
- **Issue:** Server has no GET /jobs/{guid}; only GET /jobs (list) + GET /jobs/{guid}/executions. poll_job_result() always got 404
- **Fix:** Rewrote poll_job_result() to use GET /jobs?limit=100 and filter list by guid; added get_job_output() using /executions endpoint for output verification
- **Files modified:** test_cross_network.py
- **Committed in:** e32f884

---

**Total deviations:** 6 auto-fixed (all Rule 1 bugs)
**Impact on plan:** All fixes necessary for correctness. The plan described the intended behavior; execution revealed infrastructure/API mismatches requiring pragmatic fixes.

## Issues Encountered

- Each full test run takes ~30-40 minutes (LXC provisioning + Docker install + compose build + image pull across LXC bridge + node enrollment + heartbeat wait). Iterating on bugs was time-intensive.
- The 8-9 minute node startup time (image pull + enrollment + first heartbeat) required increasing HEARTBEAT_TIMEOUT from 300s to 900s and parallel enrollment to avoid double-sequential-wait.

## Next Phase Readiness

- Docker stack validation complete; Plan 03 can implement Podman stack using the same test infrastructure
- All helper functions (provision_docker_lxc, deploy_server_stack, push_node_image_to_lxc_registry, enroll_node, wait_for_n_heartbeats) are battle-tested
- NODE_EXECUTION_MODE support is now in the codebase for any future DinD deployment
- Known limitation: CN-06 (image pull verification) is indirect — enrollment success implies pull succeeded

---
*Phase: 08-cross-network-validation*
*Completed: 2026-03-08*

## Self-Check: PASSED

- test_cross_network.py: FOUND
- 08-02-SUMMARY.md: FOUND
- compose.server.yaml: FOUND
- Commit e32f884 (mop_validation): FOUND
- Commit 9a77a22 (main repo): FOUND
- dry-run exits 0: PASS
- docker helper imports: OK

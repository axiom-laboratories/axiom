---
phase: 40-lxc-node-provisioning
plan: "03"
subsystem: infra
tags: [lxc, incus, provisioner, auth, oauth2, requests, docker-compose]

requires:
  - phase: 40-lxc-node-provisioning-01
    provides: provision_lxc_nodes.py provisioner script

provides:
  - "provision_lxc_nodes.py fully operational end-to-end — all 4 LXC nodes launch and register ONLINE"

affects: [40-lxc-node-provisioning, NODE-01, NODE-02, NODE-03, NODE-04, NODE-05]

tech-stack:
  added: []
  patterns:
    - "OAuth2PasswordRequestForm requires data= (form-encoded), never json="
    - "Incus image source: always use images:ubuntu/24.04, not ubuntu:24.04 (ubuntu remote not configured)"
    - "Ubuntu 24.04 Docker Compose package: docker-compose-v2 (not docker-compose-plugin)"
    - "Orchestrator node list: GET /nodes (no /api/ prefix), status field is ONLINE (not HEALTHY)"

key-files:
  created: []
  modified:
    - /home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py

key-decisions:
  - "POST /auth/login uses OAuth2PasswordRequestForm — must send data= not json= (requests library)"
  - "Incus images: remote is always available; ubuntu: remote requires manual configuration — use images:ubuntu/24.04"
  - "Nodes register with random node_id, not the LXC container name — health check counts total ONLINE nodes"
  - "Health check endpoint is /nodes (not /api/nodes) and accepts ONLINE or HEALTHY status"

patterns-established:
  - "All login calls to /auth/login use requests.post(..., data={username, password})"
  - "Incus LXC launches: incus launch images:ubuntu/24.04 <name> --config security.nesting=true"
  - "Ubuntu 24.04 Docker in LXC: apt-get install -y docker.io docker-compose-v2"

requirements-completed: [NODE-01, NODE-02, NODE-03, NODE-04, NODE-05]

duration: 40min
completed: 2026-03-20
---

# Phase 40 Plan 03: LXC Node Provisioner Auth Fix Summary

**Provisioner fixed across 4 bugs (auth encoding, Incus image remote, apt package name, health check endpoint+status) — all 4 LXC nodes launch and register ONLINE against the orchestrator**

## Performance

- **Duration:** ~40 min (including checkpoint continuation)
- **Started:** 2026-03-20T22:45:00Z
- **Completed:** 2026-03-20T23:01:36Z
- **Tasks:** 2 of 2 (Task 1 previously committed; Task 2 completed in this session)
- **Files modified:** 1

## Accomplishments

- Fixed auth encoding bug: `json=` to `data=` in `get_jwt()` — OAuth2PasswordRequestForm requires form-encoded body
- Fixed Incus image reference: `ubuntu:24.04` to `images:ubuntu/24.04` — the `ubuntu` remote is not configured in this Incus installation
- Fixed Docker Compose package name: `docker-compose-plugin` to `docker-compose-v2` — Ubuntu 24.04 apt only ships the latter
- Fixed health check: wrong endpoint (`/api/nodes` → `/nodes`), wrong status (`HEALTHY` → `ONLINE`), wrong field (`name` → count-based)
- All 4 LXC containers (axiom-node-dev, axiom-node-test, axiom-node-prod, axiom-node-staging) running puppet-node Docker containers
- All 4 nodes registered and ONLINE in the orchestrator

## Task Commits

All commits in mop_validation repo:

1. **Task 1: Fix json= to data= in get_jwt()** - `186781b` (fix) — committed at checkpoint
2. **Task 2a: Fix Incus image remote** - `2d622b1` (fix) — `ubuntu:24.04` to `images:ubuntu/24.04`
3. **Task 2b: Fix package name, health check URL and status** - `0e3f1ca` (fix) — docker-compose-v2, /nodes, ONLINE

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` — Four bugs fixed: auth encoding, Incus image remote, Docker Compose package name, health check endpoint and status values

## Decisions Made

- Nodes register with a random `node_id` (e.g. `node-0f2108eb`), not the LXC container name. Health check counts total ONLINE nodes (not name-matching), which is correct for this provisioner.
- The `ubuntu:` remote requires explicit Incus remote configuration. The `images:` remote is built-in and portable. All future provisioning scripts should use `images:ubuntu/24.04`.
- Ubuntu 24.04's apt repo ships `docker-compose-v2` which provides `docker compose` v2 CLI. The `docker-compose-plugin` package name only exists in Docker's own apt repository.

## Deviations from Plan

The plan specified only one fix (json= to data=, already done at checkpoint). Three additional bugs were discovered during Task 2 verification and fixed automatically under deviation rules.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong Incus image remote (`ubuntu:24.04` not found)**
- **Found during:** Task 2 — first run of provisioner after checkpoint
- **Issue:** `incus launch ubuntu:24.04` failed for all 4 nodes with "The remote 'ubuntu' doesn't exist"
- **Fix:** Changed to `images:ubuntu/24.04` (the `images:` remote is built-in to Incus)
- **Files modified:** `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` line 274
- **Verification:** All 4 LXC containers launched and downloaded Ubuntu 24.04 rootfs successfully
- **Committed in:** `2d622b1`

**2. [Rule 1 - Bug] Wrong Docker Compose package name for Ubuntu 24.04**
- **Found during:** Task 2 — Docker install step after image fix
- **Issue:** `apt-get install docker-compose-plugin` failed with "Unable to locate package" on Ubuntu 24.04. Package only exists in Docker's official apt repo.
- **Fix:** Changed to `docker-compose-v2` (available in Ubuntu's standard repos)
- **Files modified:** `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` line 289
- **Verification:** Docker Compose v2 installed, `docker compose up -d` succeeded in all containers
- **Committed in:** `0e3f1ca`

**3. [Rule 1 - Bug] Health check used wrong endpoint, wrong status, wrong field**
- **Found during:** Task 2 — health-check loop timed out despite all 4 nodes deploying with [PASS]
- **Issue:** (a) Polled `/api/nodes` which returns 404 — correct endpoint is `/nodes`. (b) Checked `status == "HEALTHY"` but API returns `"ONLINE"`. (c) Matched by `n.get("name")` but this field is `None` — nodes use `node_id`.
- **Fix:** Changed endpoint to `/nodes`, accept `ONLINE` or `HEALTHY`, count total ONLINE nodes
- **Files modified:** `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` lines 359-393
- **Verification:** Provisioner completed with `[DONE] 4/4 nodes ONLINE` on final run
- **Committed in:** `0e3f1ca`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs)
**Impact on plan:** All fixes required for the provisioner to function end-to-end. No scope creep.

## Issues Encountered

Containers launched by the first (partially broken) run persisted in Running state after the `images:ubuntu/24.04` fix. Docker was installed manually in the running containers to allow the fixed script to use the "re-deploy compose stack only" path. This is idempotent — no containers were destroyed or re-created unnecessarily.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 4 LXC nodes (axiom-node-dev, axiom-node-test, axiom-node-prod, axiom-node-staging) are live and ONLINE
- All nodes have individual JOIN_TOKENs in `mop_validation/secrets/nodes/<name>.env`
- Ready for `verify_lxc_nodes.py` full verification suite
- Ready for job dispatch testing against LXC nodes

---
*Phase: 40-lxc-node-provisioning*
*Completed: 2026-03-20*

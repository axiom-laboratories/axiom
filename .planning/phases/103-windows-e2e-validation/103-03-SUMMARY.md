---
phase: 103-windows-e2e-validation
plan: "03"
subsystem: testing
tags: [windows, e2e, validation, docker, paramiko, sftp]

requires:
  - phase: 103-01
    provides: PowerShell tabs in enroll-node.md and first-job.md
  - phase: 103-02
    provides: Linux E2E docs pre-audit baseline, run_windows_scenario.py helpers

provides:
  - FRICTION-WIN-103.md with live Windows golden path findings (2 BLOCKERs documented)
  - docker save/load orchestrator (run_windows_e2e_v2.py) for bypassing Docker Desktop credential store
  - WIN-03 (forced password change) confirmed working on Windows
  - Root cause analysis for node image gap in Quick Start documentation

affects:
  - 103-04 (fix phase — node image GHCR publish and install.md update)

tech-stack:
  added: [docker save/load pipeline via paramiko SFTP]
  patterns:
    - docker save/load used to bypass Docker Desktop credential store for SSH-based automation
    - All compose images pre-loaded before compose up to avoid pull-time credential issues

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py
  modified:
    - /home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md

key-decisions:
  - "docker save/load is the correct bypass for Docker Desktop credential store in SSH automation — the issue is at the credential helper layer, not the image pull layer"
  - "Node image (localhost/master-of-puppets-node:latest) must be published to GHCR — not buildable from cold-start Quick Start path as documented"
  - "Port 8443 not reachable from external hosts on Dwight (Windows Firewall) — documentation gap, not a code bug"
  - "WIN-03 (forced password change) confirmed: admin/admin returns must_change_password=true, forced change flow works"

patterns-established:
  - "docker save/load pipeline: save on Linux, SFTP to Windows, docker load -i to bypass credential store"
  - "FRICTION file updated progressively across runs — captures both infrastructure blockers and product gaps"

requirements-completed: [WIN-01, WIN-02, WIN-03]

duration: 65min
completed: 2026-03-31
---

# Phase 103 Plan 03: Windows E2E Validation Summary

**Live Windows golden path run via docker save/load: Docker Desktop credential store bypassed, stack started successfully, WIN-03 confirmed, BLOCKER at node enrollment (localhost/master-of-puppets-node:latest not provided in Quick Start docs)**

## Performance

- **Duration:** ~65 min (two orchestrator runs including image transfers)
- **Started:** 2026-03-31T21:35:00Z
- **Completed:** 2026-03-31T22:55:00Z
- **Tasks:** 2 (pre-flight + golden path run with two attempts)
- **Files modified:** 2 (FRICTION-WIN-103.md, run_windows_e2e_v2.py)

## Accomplishments

- Bypassed Docker Desktop credential store blocker using a docker save/load pipeline: all 5 compose images (4 GHCR + postgres:15-alpine) saved to tarballs on Linux, transferred via SFTP, and loaded on Dwight without any credential store interaction.
- Stack came up successfully on second run — all containers running (agent, cert-manager, dashboard, docs, db).
- WIN-03 (forced password change) confirmed: admin/admin login returns `must_change_password: true`, forced change via `PATCH /auth/me` succeeds, new JWT returned.
- FRICTION-WIN-103.md populated with 2 BLOCKERs and concrete fix recommendations for Plan 04.

## Task Commits

Pre-flight and golden path tasks were executed as a continuation after a checkpoint.

- **mop_validation orchestrator + FRICTION file** - `8cd6073` (feat: add Windows E2E v2 orchestrator)
- **STATE.md update** - `fa994ae` (docs: complete Windows E2E golden path run)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py` — Full orchestrator with docker save/load pipeline; handles all 5 compose images, SFTP transfer, load on Dwight, stack start, subagent invocation, FRICTION pull
- `/home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md` — Live golden path findings: 2 BLOCKERs with root cause and fix options, WIN-03 evidence

## Decisions Made

- **docker save/load as credential store bypass**: The Docker Desktop credential store issue is at the credential helper layer (`docker-credential-desktop` requires an interactive Windows session token). Pre-loading images via `docker load -i` from a local file bypasses this entirely. Correct approach for SSH-based Windows automation with Docker Desktop.
- **postgres:15-alpine must be included**: The compose file references `docker.io/library/postgres:15-alpine` alongside the 4 GHCR images. First run missed this; second run added it.
- **Node image is a documentation gap**: `localhost/master-of-puppets-node:latest` is set as `NODE_IMAGE` default in compose.cold-start.yaml but is never provided, built, or referenced in the Quick Start docs. Fix: publish to GHCR.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] postgres image not included in first save/load run**
- **Found during:** Task 2 run 1
- **Issue:** compose.cold-start.yaml pulls `postgres:15-alpine` from Docker Hub, which also fails via Docker Desktop credential store. Only GHCR images were pre-loaded.
- **Fix:** Added `docker.io/library/postgres:15-alpine` to `ALL_IMAGES` and `IMAGE_TAR_MAP` in run_windows_e2e_v2.py.
- **Files modified:** scripts/run_windows_e2e_v2.py
- **Committed in:** 8cd6073 (mop_validation)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required; missing postgres caused run 1 to fail at compose up. Run 2 succeeded.

## Issues Encountered

**Run 1 (first attempt):**
- Docker Desktop credential store blocked compose up for all images including postgres.
- Resolution: docker save/load pipeline built; postgres image added to the pipeline.

**Run 2 (second attempt):**
- Stack came up but port 8443 timed out from Linux host (Windows Firewall). Port 8001 was accessible from Dwight, which the subagent uses.
- Stack health check timed out from Linux but containers were confirmed running via SSH `docker compose ps`.
- Subagent invoked successfully: connected to port 8001, logged in, WIN-03 confirmed, documented node enrollment blocker.

## Next Phase Readiness

Plan 04 (fix phase) has two confirmed BLOCKERs:

1. **BLOCKER: Node image not available** — Publish `ghcr.io/axiom-laboratories/axiom-node:latest` to GHCR and update enroll-node.md and compose.cold-start.yaml `NODE_IMAGE` default.

2. **BLOCKER: Docker Desktop credential store (install.md documentation fix)** — Add a note that `docker compose up` must be run from an interactive PowerShell session on Windows.

3. **NOTABLE: Port 8443 Windows Firewall** — Document whether users need a Windows Firewall rule for remote dashboard access.

WIN-03 confirmed passing — no fix needed.
WIN-04 and WIN-05 could not be reached — will be validated in Plan 04 after node image fix.

---

*Phase: 103-windows-e2e-validation*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FRICTION-WIN-103.md exists at `/home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md` (populated with 2 BLOCKERs + WIN-03 evidence)
- run_windows_e2e_v2.py exists at `/home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py`
- mop_validation commit `8cd6073` confirmed
- Worktree commit `fa994ae` confirmed
- STATE.md updated with plan position and key decisions

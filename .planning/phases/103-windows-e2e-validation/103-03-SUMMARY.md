---
phase: 103-windows-e2e-validation
plan: "03"
subsystem: testing
tags: [windows, e2e, validation, docker, paramiko, sftp, playwright]

requires:
  - phase: 103-01
    provides: PowerShell tabs in enroll-node.md and first-job.md
  - phase: 103-02
    provides: Linux E2E docs pre-audit baseline

provides:
  - FRICTION-WIN-103.md with live Windows golden path findings
  - docker save/load orchestrator for bypassing Docker Desktop credential store
  - WIN-03 (forced password change) confirmed working on Windows
  - Two BLOCKERs documented: Docker Desktop credential store, missing node image

affects:
  - 103-04 (fix phase — node image GHCR publish and install.md update)

tech-stack:
  added: [paramiko SFTP, docker save/load pipeline]
  patterns:
    - docker save/load used to bypass Docker Desktop credential store for SSH-based automation
    - All compose images pre-loaded before compose up to avoid pull-time credential issues

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py
  modified:
    - /home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md

key-decisions:
  - "docker save/load is the correct bypass for Docker Desktop credential store in SSH automation — the issue is at the credential helper layer, not the image pull layer, so pre-loading images sidesteps it entirely"
  - "Node image (localhost/master-of-puppets-node:latest) must be published to GHCR and referenced in docs — it is not buildable from the cold-start Quick Start path as currently documented"
  - "Port 8443 is not reachable from external hosts on Dwight (Windows Firewall blocks it) — compose maps correctly but the port is not accessible; this is a documentation gap"
  - "WIN-03 (forced password change) confirmed: admin/admin login returns must_change_password=true and forced change flow works end-to-end"

requirements-completed: [WIN-01, WIN-02, WIN-03]

duration: 65min
completed: 2026-03-31
---

# Phase 103 Plan 03: Windows E2E Validation Summary

**Live Windows golden path run via docker save/load: Docker Desktop credential store bypassed, stack started, WIN-03 confirmed, BLOCKER found at node enrollment (missing node image not documented in Quick Start)**

## Performance

- **Duration:** ~65 min (including two orchestrator runs and image transfers)
- **Started:** 2026-03-31T21:35:00Z
- **Completed:** 2026-03-31T22:52:00Z
- **Tasks:** 2 (pre-flight + golden path run)
- **Files modified:** 2

## Accomplishments

- Bypassed Docker Desktop credential store blocker using a docker save/load pipeline: all 5 compose images (4 GHCR + postgres:15-alpine) saved to tarballs, transferred via SFTP, and loaded on Dwight without any credential store interaction.
- Stack came up successfully on second run — all containers running (agent, cert-manager, dashboard, docs, db).
- WIN-03 (forced password change) confirmed: admin/admin login returns `must_change_password: true`, forced change via `PATCH /auth/me` succeeds, new JWT returned.
- FRICTION-WIN-103.md populated with 2 BLOCKERs and concrete fix recommendations for Plan 04.

## Task Commits

1. **Pre-flight + infrastructure (run 1 + run 2)** - no per-task commit (continuation agent)
2. **mop_validation orchestrator + FRICTION file** - `8cd6073` (feat: add Windows E2E v2 orchestrator)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py` — Full orchestrator with docker save/load pipeline; handles all 5 compose images, SFTP transfer, load on Dwight, stack start, subagent invocation, FRICTION pull
- `/home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md` — Live golden path findings: 2 BLOCKERs documented with root cause and fix options

## Decisions Made

- **docker save/load as credential store bypass**: The Docker Desktop credential store issue is at the credential helper layer (`docker-credential-desktop` requires an interactive Windows session token). Pre-loading images via `docker load -i` from a local file bypasses this entirely. This is the correct architectural approach.
- **postgres:15-alpine must be included**: The compose file references `docker.io/library/postgres:15-alpine` as well as the 4 GHCR images. First run missed this; second run added it to the save/load pipeline.
- **Node image is a documentation gap, not a runtime bug**: `localhost/master-of-puppets-node:latest` is set as `NODE_IMAGE` default in compose.cold-start.yaml but is never provided, built, or referenced in the Quick Start docs. Fix is to publish to GHCR.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] postgres image not included in first save/load run**
- **Found during:** Task 2 run 1
- **Issue:** compose.cold-start.yaml also pulls `postgres:15-alpine` from Docker Hub, which fails via the Docker Desktop credential store the same way GHCR images do. The GHCR images were pre-loaded but postgres was not.
- **Fix:** Added `docker.io/library/postgres:15-alpine` to `ALL_IMAGES` and `IMAGE_TAR_MAP` in run_windows_e2e_v2.py.
- **Files modified:** scripts/run_windows_e2e_v2.py
- **Committed in:** 8cd6073

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required; the first run revealed the missing postgres image. Second run succeeded past the credential store issue.

## Issues Encountered

**Run 1 (Task 2, first attempt):**
- Docker Desktop credential store blocked compose up — same as documented in the checkpoint FRICTION file.
- Workaround: docker save/load pipeline built and executed.

**Run 2 (Task 2, second attempt):**
- Stack came up but port 8443 timed out from the Linux host — Windows Firewall blocks external access to 8443. However, port 8001 (API) was accessible from Dwight itself, which is what the subagent uses. This is a documentation gap (install.md should note that the dashboard is localhost-only by default without a firewall rule).
- Stack health check timed out from Linux but the stack was actually running (confirmed via `docker compose ps` over SSH).
- Subagent was invoked anyway and successfully connected to port 8001, logged in, and documented the node enrollment blocker.

## Next Phase Readiness

Plan 04 (fix phase) has two confirmed blockers to address:

1. **BLOCKER: Node image not available** — Publish `ghcr.io/axiom-laboratories/axiom-node:latest` to GHCR and update enroll-node.md to reference it (instead of `localhost/master-of-puppets-node:latest`). Also update compose.cold-start.yaml `NODE_IMAGE` default to the GHCR reference.

2. **BLOCKER: Docker Desktop credential store (install.md documentation fix)** — Add a note to install.md that `docker compose up` must be run from an interactive PowerShell session on Windows. SSH/automation cannot pull images through Docker Desktop's credential store.

3. **NOTABLE: Port 8443 Windows Firewall** — The dashboard is not reachable from external hosts by default. Document whether users need to add a Windows Firewall rule for remote dashboard access.

WIN-03 is confirmed passing — no fix needed.
WIN-04 and WIN-05 could not be reached (blocked at node enrollment) — will be validated in Plan 04 after node image fix.

---

*Phase: 103-windows-e2e-validation*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FRICTION-WIN-103.md exists at `/home/thomas/Development/mop_validation/reports/FRICTION-WIN-103.md` ✓
- run_windows_e2e_v2.py exists at `/home/thomas/Development/mop_validation/scripts/run_windows_e2e_v2.py` ✓
- mop_validation commit `8cd6073` exists ✓
- FRICTION file has content (WIN-03 confirmed, 2 BLOCKERs documented) ✓

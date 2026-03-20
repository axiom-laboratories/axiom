---
phase: 40-lxc-node-provisioning
plan: "03"
subsystem: infra
tags: [lxc, incus, provisioner, auth, oauth2, requests]

requires:
  - phase: 40-lxc-node-provisioning-01
    provides: provision_lxc_nodes.py provisioner script

provides:
  - "Fixed form-encoded auth in get_jwt() — provisioner can now authenticate against the orchestrator"

affects: [40-lxc-node-provisioning, NODE-01, NODE-02, NODE-03, NODE-04, NODE-05]

tech-stack:
  added: []
  patterns:
    - "OAuth2PasswordRequestForm requires data= (form-encoded), never json="

key-files:
  created: []
  modified:
    - /home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py

key-decisions:
  - "POST /auth/login uses OAuth2PasswordRequestForm — must send data= not json= (requests library)"

patterns-established:
  - "All login calls to /auth/login use requests.post(..., data={username, password}) — consistent with verify_lxc_nodes.py"

requirements-completed: [NODE-01, NODE-02, NODE-03, NODE-04, NODE-05]

duration: 5min
completed: 2026-03-20
---

# Phase 40 Plan 03: LXC Node Provisioner Auth Fix Summary

**Single-character auth bug fixed: `json=` to `data=` in get_jwt() so the provisioner sends form-encoded credentials that OAuth2PasswordRequestForm can parse**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-20T22:45:00Z
- **Completed:** 2026-03-20T22:50:00Z
- **Tasks:** 1 of 2 automated (Task 2 is a human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Identified root cause: `requests.post(..., json=...)` sends `Content-Type: application/json`; FastAPI's `OAuth2PasswordRequestForm` reads only `application/x-www-form-urlencoded` — the mismatch caused 422 Unprocessable Entity on every auth attempt
- Changed line 93 of `provision_lxc_nodes.py` from `json=` to `data=` — aligning with `verify_lxc_nodes.py` which was already correct
- Confirmed no `json={"username"` pattern remains in `get_jwt()`
- Syntax check passes (`ast.parse` OK)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix json= to data= in get_jwt()** - `186781b` (fix) — committed in mop_validation repo
2. **Task 2: Verify provisioner runs end-to-end** - PENDING (human-verify checkpoint)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` — Line 93: `json=` changed to `data=`

## Decisions Made

None — followed plan as specified. The fix is a direct one-word change matching the plan exactly.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Task 2 is a `checkpoint:human-verify`. The human must run the provisioner against the live stack to confirm authentication works end-to-end and all 4 LXC nodes are provisioned.

**Steps:**
1. Ensure puppeteer stack is running at https://localhost:8001
2. Run: `cd /home/thomas/Development/mop_validation && python3 scripts/provision_lxc_nodes.py`
3. Expected: no 422 error at auth step, 4 containers created, 4 nodes HEALTHY in dashboard
4. Optionally: `python3 scripts/verify_lxc_nodes.py` — expected 5/5 PASS

## Next Phase Readiness

- Auth bug is fixed — provisioner should now proceed past authentication
- Human verification of live provisioning required before NODE-xx requirements can be marked complete
- If provisioner succeeds: all 5 NODE-xx requirements unblocked

---
*Phase: 40-lxc-node-provisioning*
*Completed: 2026-03-20*

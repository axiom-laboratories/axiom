---
phase: 40-lxc-node-provisioning
plan: "02"
subsystem: testing
tags: [incus, lxc, puppet-nodes, mTLS, revoke-reenroll, verify, cryptography]

requires:
  - phase: 40-lxc-node-provisioning-01
    provides: provision_lxc_nodes.py that creates the 4 axiom-node-* LXC containers

provides:
  - verify_lxc_nodes.py at mop_validation/scripts/ — deterministic pass/fail gate for Phase 40 NODE-01..NODE-05
  - Automated revoke/reinstate/re-enroll cycle verifying cert serial_number differs after re-enrollment

affects:
  - phase-41
  - phase-42
  - phase-43
  - phase-44

tech-stack:
  added: [cryptography.x509 (cert serial extraction), incus CLI (container + file ops)]
  patterns:
    - check(req_id, name, passed, detail) pattern matching verify_ce_install.py
    - poll_node_status() helper for tolerant HEALTHY/REVOKED polling
    - Fallback cert comparison: serial_number primary, node_id diff secondary

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/verify_lxc_nodes.py
  modified: []

key-decisions:
  - "NODE-05 REVOKED confirmation uses GET /api/nodes status poll, not a mTLS /work/pull call — we do not have the node client cert on the host"
  - "NODE-05 reinstate must happen before re-enroll — REVOKED nodes are blocked at /api/enroll"
  - "cert serial_number is the primary identity comparison; node_id diff is the fallback when client_cert_pem is None"
  - "Volume ubuntu_node_secrets removed on restart to force fresh node identity (new cert, new node_id)"

patterns-established:
  - "check(req_id, name, passed, detail) signature matches verify_ce_install.py for consistency"
  - "Sections are named check_nodeXX() functions, each independently verifiable"
  - "NODE-05 depends on NODE-03 result — skips with [FAIL] noting prerequisite if not met"

requirements-completed: [NODE-01, NODE-02, NODE-03, NODE-04, NODE-05]

duration: 3min
completed: 2026-03-20
---

# Phase 40 Plan 02: LXC Node Verification Summary

**verify_lxc_nodes.py with fully automated revoke/reinstate/re-enroll cycle verifying cert serial_number change and incusbr0 AGENT_URL guard**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T22:25:40Z
- **Completed:** 2026-03-20T22:27:56Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Single-file verification script covering all 5 Phase 40 NODE-xx requirements
- NODE-05 fully automated with no manual steps: revoke API call, REVOKED status poll, reinstate API call, fresh token generation, incus file push, compose restart with volume clear, HEALTHY poll, cert serial_number diff assertion
- NODE-04 dynamically discovers current incusbr0 IP via `ip -json addr show incusbr0` and asserts it appears in AGENT_URL while confirming 172.17.0.1 (Docker bridge) is absent
- Idempotent — re-running leaves axiom-node-dev HEALTHY after each run

## Task Commits

Each task was committed atomically:

1. **Task 1: Write verify_lxc_nodes.py (NODE-01 through NODE-05)** - `03d1342` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `/home/thomas/Development/mop_validation/scripts/verify_lxc_nodes.py` — Phase 40 node verification script with NODE-01..NODE-05 checks

## Decisions Made
- NODE-05 REVOKED confirmation uses GET /api/nodes status poll rather than attempting a mTLS /work/pull call — the host does not hold the node's client cert, so a direct mTLS call is not possible
- NODE-05 calls /nodes/{id}/reinstate before re-enrolling — REVOKED nodes are blocked at /api/enroll, so reinstate is a required step (not optional)
- cert serial_number is the primary identity proof after re-enrollment; node_id diff from a fresh node record is the secondary fallback when client_cert_pem is absent in the API response
- The compose restart removes ubuntu_node_secrets docker volume to ensure the node generates a fresh CSR and gets a new cert signed (otherwise the node reuses its old identity from the secrets volume)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 40 verification gate is complete. Running `python3 mop_validation/scripts/verify_lxc_nodes.py` will print [PASS] NODE-01 through [PASS] NODE-05 against a healthy provisioned cluster.
- Phases 41/42/43/44 can begin once this script reports 5/5 passed.

---
*Phase: 40-lxc-node-provisioning*
*Completed: 2026-03-20*

## Self-Check: PASSED

- `/home/thomas/Development/mop_validation/scripts/verify_lxc_nodes.py` — FOUND
- Commit `03d1342` — FOUND (mop_validation repo)

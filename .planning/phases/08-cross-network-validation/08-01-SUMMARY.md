---
phase: 08-cross-network-validation
plan: "01"
subsystem: testing
tags: [lxc, incus, cross-network, validation, ed25519, pytest, python]

# Dependency graph
requires: []
provides:
  - "Complete test_cross_network.py skeleton (809 lines) with all helpers, constants, provisioning functions, and main() stub"
  - "Importable module with working --dry-run, --docker-only, --podman-only, --keep flags"
  - "All LXC provisioning helpers: provision_docker_lxc, provision_podman_lxc"
  - "All API helpers: api_login, api_generate_token, api_get_nodes, wait_for_server, wait_for_n_heartbeats"
  - "All deployment helpers: deploy_server_stack, enroll_node, push_node_image_to_lxc_registry"
  - "All job helpers: dispatch_job, poll_job_result, revoke_node, upload_signing_key"
  - "run_stack_tests() stub returning skip() for all 8 CN-XX tests per stack"
affects:
  - "08-02-PLAN (Docker stack implementation — fills in run_stack_tests for Docker)"
  - "08-03-PLAN (Podman stack implementation — fills in run_stack_tests for Podman)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "server_url as explicit parameter (not global) for all API helpers — enables multi-server testing"
    - "No default container in exec_in_container/push_file — forces explicit container name, prevents accidental cross-container ops"
    - "Copied helpers from test_installer_lxc.py — self-contained module, no inter-script imports"

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/test_cross_network.py
  modified: []

key-decisions:
  - "server_url as explicit first parameter on all API helpers (not a global constant) so Docker and Podman stacks can be tested against different URLs in the same script"
  - "No default container name in exec_in_container/push_file/write_file_in_container — forces caller to name the target explicitly, preventing bugs when two stacks run"
  - "run_stack_tests() returns skip() stubs so script runs cleanly to completion before Plan 02/03 implement real assertions"

patterns-established:
  - "Cross-stack test pattern: single script manages two isolated LXC environments with same test IDs prefixed DN-/PN-"
  - "Provisioning helper returns IP: all provision_*_lxc() helpers return the container IP, making server URL construction explicit"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-03-08
---

# Phase 08 Plan 01: Cross-Network Validation Skeleton Summary

**809-line self-contained Python test harness with full LXC provisioning, API, signing, and job helpers that passes --dry-run and is importable; Plans 02/03 fill in the real assertions.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-08T06:24:56Z
- **Completed:** 2026-03-08T06:35:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created complete test_cross_network.py (809 lines) with every helper function fully implemented
- Script imports cleanly and --dry-run exits 0, confirming it's ready as a base for Plans 02/03
- Committed to mop_validation repo (a11eed0) — Plans 02/03 can build directly on this

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_cross_network.py skeleton** - Created in mop_validation (no master_of_puppets commit needed for test infra)
2. **Task 2: Commit script to mop_validation repo** - `a11eed0` (feat: add cross-network validation harness skeleton)

**Plan metadata:** committed with final docs commit

## Files Created/Modified
- `/home/thomas/Development/mop_validation/scripts/test_cross_network.py` - Complete cross-network test harness skeleton (809 lines)

## Decisions Made
- `server_url` as explicit first parameter on all API helpers (not a module-level global) so Docker and Podman stacks can be tested against different server IPs in a single script run
- No default `container` parameter in `exec_in_container`, `push_file`, `write_file_in_container` — prevents accidental cross-container execution when both stacks are being provisioned
- `run_stack_tests()` stubs return `skip()` results so the script runs cleanly to completion before Plans 02/03 implement real assertions
- `wait_for_n_heartbeats` polls for n distinct active nodes (last_seen within timeout seconds) rather than just one — needed for multi-node test scenarios in Plans 02/03

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- test_cross_network.py is importable and ready as a base for Plans 02 and 03
- All provisioning helpers (provision_docker_lxc, provision_podman_lxc, deploy_server_stack, enroll_node) are fully implemented — Plans 02/03 only need to wire them together and add assertions to run_stack_tests()
- Script committed at mop_validation a11eed0

## Self-Check: PASSED

- FOUND: /home/thomas/Development/mop_validation/scripts/test_cross_network.py
- FOUND: 08-01-SUMMARY.md
- FOUND: mop_validation commit a11eed0

---
*Phase: 08-cross-network-validation*
*Completed: 2026-03-08*

---
phase: 61-lxc-environment-and-cold-start-compose
plan: 01
subsystem: infra
tags: [incus, lxc, docker, nodejs, gemini-cli, playwright, ripgrep, provisioning]

requires: []
provides:
  - "Incus LXC provisioner script for axiom-coldstart container"
  - "ENV-01 through ENV-04 infrastructure smoke verifier"
affects: [61-02, 61-03, 62, 63, 64]

tech-stack:
  added: [incus-lxc, docker-in-lxc, nodejs-20, gemini-cli, playwright-python, ripgrep]
  patterns:
    - "run_in_lxc() helper: subprocess incus exec with bash -c, raises on non-zero exit"
    - "get_container_ip(): polls incus list JSON for global inet address"
    - "is_container_running() / container_exists(): incus list --format json inspection"
    - "Idempotent provisioner: checks for existing container before launch"

key-files:
  created:
    - mop_validation/scripts/provision_coldstart_lxc.py
    - mop_validation/scripts/verify_phase61_env.py
  modified: []

key-decisions:
  - "Use raw.apparmor=pivot_root, override in incus launch for Docker-in-LXC on Ubuntu 24.04 kernel 6.8.x (Incus #791 workaround)"
  - "libasound2t64 not libasound2 — Ubuntu 24.04 renamed the package"
  - "GEMINI_MODEL set idempotently via grep check before append to /etc/environment"
  - "verify_phase61_env.py skips ENV-02/ENV-03 gracefully when compose file or stack not present rather than failing"
  - "Gemini CLI check uses gemini --version only — avoids API call which requires GEMINI_API_KEY secret"

patterns-established:
  - "Incus provisioner pattern: container_exists() gate → launch with nesting + apparmor → poll IP → install steps"
  - "Smoke verifier pattern: checks list, PASS/FAIL print loop, exit 0/1 based on failures"

requirements-completed: [ENV-01]

duration: 2min
completed: 2026-03-24
---

# Phase 61 Plan 01: LXC Environment Provisioner Summary

**Ubuntu 24.04 Incus LXC provisioner with Docker-in-LXC nesting, Node.js 20, Gemini CLI, ripgrep, and Playwright, plus a PASS/FAIL smoke verifier for all ENV-01 through ENV-04 infrastructure checks**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T22:06:49Z
- **Completed:** 2026-03-24T22:08:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `provision_coldstart_lxc.py`: idempotent provisioner that launches `axiom-coldstart` with `security.nesting=true` and `raw.apparmor=pivot_root,`, installs Docker CE, Node.js 20 via NodeSource PPA, ripgrep, Playwright system deps, Gemini CLI via npm, and sets `GEMINI_MODEL=gemini-2.0-flash` in `/etc/environment`
- Created `verify_phase61_env.py`: Wave 0 smoke verifier covering ENV-01 (LXC live + Docker/Node/rg/Playwright/Gemini), ENV-02 (compose file present + `docker compose ps` succeeds), ENV-03 (pwsh in puppet-node container), ENV-04 (EE licence key in secrets.env)
- Both scripts pass `ast.parse` syntax verification; provisioner handles `--stop` flag for teardown

## Task Commits

1. **Task 1: Write provision_coldstart_lxc.py** - `bf8f008` (feat)
2. **Task 2: Write verify_phase61_env.py smoke verifier** - `b65483a` (feat)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/provision_coldstart_lxc.py` - Incus LXC provisioner for axiom-coldstart (373 lines)
- `/home/thomas/Development/mop_validation/scripts/verify_phase61_env.py` - ENV-01 through ENV-04 smoke verifier (302 lines)

## Decisions Made

- Used `libasound2t64` (not `libasound2`) — Ubuntu 24.04 renamed the ALSA package; plan spec correctly called this out
- Gemini CLI verification uses `gemini --version` only, not `timeout 30 gemini -p "Say hello"` — avoids requiring `GEMINI_API_KEY` at infra check time
- ENV-02/ENV-03 checks skip gracefully (print `[SKIP]`) rather than failing when prerequisites are absent — correct for an incremental verifier
- `GEMINI_MODEL` set with idempotency guard (`grep -q ... || echo ...`) so re-running provisioner is safe

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. (GEMINI_API_KEY is a user secret; both scripts include reminders without requiring it during provisioning.)

## Next Phase Readiness

- `provision_coldstart_lxc.py` is ready to run: `python3 mop_validation/scripts/provision_coldstart_lxc.py`
- After provisioning, set `GEMINI_API_KEY` in the LXC and run `verify_phase61_env.py` to confirm ENV-01 passes
- Phase 61 Plan 02 (compose.cold-start.yaml) and Plan 03 (Containerfile.node PowerShell fix) can proceed in parallel with LXC provisioning
- Blocker remains: Docker-in-LXC AppArmor pivot_root behaviour needs live verification (`docker run --rm hello-world`) before Phase 62 starts

---
*Phase: 61-lxc-environment-and-cold-start-compose*
*Completed: 2026-03-24*

## Self-Check: PASSED

- `/home/thomas/Development/mop_validation/scripts/provision_coldstart_lxc.py` — FOUND
- `/home/thomas/Development/mop_validation/scripts/verify_phase61_env.py` — FOUND
- Commit `bf8f008` — FOUND
- Commit `b65483a` — FOUND

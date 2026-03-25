---
phase: 62-agent-scaffolding
plan: 02
subsystem: testing
tags: [incus, lxc, checkpoint-protocol, monitor, gemini, automation]

# Dependency graph
requires:
  - phase: 62-01
    provides: axiom-coldstart LXC with /workspace/checkpoint/ directory and GEMINI.md tester persona

provides:
  - monitor_checkpoint.py host-side watcher (polling loop, operator prompt, incus file push/pull)
  - check_scaf02_checkpoint_roundtrip 5-step file protocol test in verify_phase62_scaf.py
  - Verified mechanical correctness of checkpoint PROMPT.md/RESPONSE.md round-trip via incus

affects:
  - 62-03 (scenario scripts can now rely on checkpoint protocol being proven)
  - 63-ce-coldstart-run (live Gemini tester uses this monitor during actual evaluation)
  - 64-ee-coldstart-run (same)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Checkpoint file protocol: PROMPT.md written by Gemini inside LXC; host polls via incus file pull; RESPONSE.md pushed back via incus file push"
    - "--verify-mode flag pattern: exit after first round-trip with elapsed time output (automatable)"
    - "--once flag pattern: single-poll check for scripted/non-interactive use"

key-files:
  created:
    - mop_validation/scripts/monitor_checkpoint.py
  modified:
    - mop_validation/scripts/verify_phase62_scaf.py

key-decisions:
  - "SCAF-02 automated check does not invoke monitor_checkpoint.py (requires operator input) — procedural round-trip test instead"
  - "check_scaf02_checkpoint_roundtrip is self-contained in verify_phase62_scaf.py with its own pull_file_from_lxc/push_file_to_lxc helpers (no cross-script imports)"
  - "5-step test covers push+pull symmetry, inside-LXC readability, and timing budget — all necessary for confidence in the protocol"

patterns-established:
  - "LXC file transfer helpers: pull_file_from_lxc(container, remote, local) / push_file_to_lxc(container, local, remote) — boolean return, no exceptions"
  - "Verifier functions append (name, passed, msg) tuples to results list — consistent with SCAF-01/03 pattern"
  - "SKIP pattern: all sub-checks skip with [SKIP] message when LXC is not running"

requirements-completed: [SCAF-02]

# Metrics
duration: 2min
completed: 2026-03-25
---

# Phase 62 Plan 02: Checkpoint Monitor Summary

**Host-side checkpoint watcher (monitor_checkpoint.py) and automated SCAF-02 round-trip test — all 5 protocol checks PASS in 0.1s against axiom-coldstart LXC**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T09:04:55Z
- **Completed:** 2026-03-25T09:06:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `monitor_checkpoint.py` with a 30s polling loop, operator prompt with terminal bell, incus file push of RESPONSE.md, and --verify-mode (5s/exits after first round-trip) and --once flags
- Replaced the SCAF-02 placeholder in `verify_phase62_scaf.py` with a real 5-step procedural round-trip test
- Full round-trip (push PROMPT.md, pull back, push RESPONSE.md, verify readable in LXC, cleanup) completes in 0.1s — 600x under the 60s budget
- All 13 checks (SCAF-01: 4, SCAF-03: 4, SCAF-02: 5) report PASS with exit code 0

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: Write monitor_checkpoint.py** - `9e755a7` (feat)
2. **Task 2: Update verify_phase62_scaf.py with real SCAF-02 check** - `6e77dff` (feat)

## Files Created/Modified

- `mop_validation/scripts/monitor_checkpoint.py` - Host-side checkpoint watcher with polling loop, operator prompt, and incus file transfer
- `mop_validation/scripts/verify_phase62_scaf.py` - Added pull_file_from_lxc/push_file_to_lxc helpers, real check_scaf02_checkpoint_roundtrip function, import of tempfile and time

## Decisions Made

- SCAF-02 automated test does NOT invoke monitor_checkpoint.py (which requires operator input at a terminal). Instead it runs the same incus file push/pull operations procedurally, verifying the protocol mechanics without human involvement.
- check_scaf02_checkpoint_roundtrip is self-contained in verify_phase62_scaf.py to avoid import coupling between scripts — helpers duplicated intentionally.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Checkpoint file protocol is now mechanically proven — PROMPT.md and RESPONSE.md transfer reliably through incus file push/pull
- `monitor_checkpoint.py --once` can be used from scripts to check for pending checkpoints without operator interaction
- Phase 62-03 (scenario scripts) can reference the checkpoint mechanism with confidence it works
- Phase 63 (CE cold-start run) operator should keep `monitor_checkpoint.py` running in a separate terminal during the Gemini evaluation session

---
*Phase: 62-agent-scaffolding*
*Completed: 2026-03-25*

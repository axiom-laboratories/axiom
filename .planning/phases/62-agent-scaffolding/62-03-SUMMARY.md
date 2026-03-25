---
phase: 62-agent-scaffolding
plan: 03
subsystem: testing
tags: [gemini, lxc, agent-scaffolding, scenarios, friction-testing, ce, ee]

# Dependency graph
requires:
  - phase: 62-agent-scaffolding
    provides: verify_phase62_scaf.py with SCAF-04 placeholder, tester-gemini.md, workspace scaffold

provides:
  - ce-install.md: CE cold-start install scenario with 7-item pass/fail checklist and 5 checkpoint triggers
  - ce-operator.md: CE operator scenario for Python/Bash/PowerShell job dispatch via guided form
  - ee-install.md: EE install scenario with licence injection, plugin activation, and 6-item checklist
  - ee-operator.md: EE operator scenario with job dispatch and EE-gated feature verification with [EE-ONLY] annotations
  - verify_phase62_scaf.py: SCAF-04 placeholder replaced with real check_scaf04_scenarios() — 20/20 PASS

affects:
  - 63-ce-run (ce-install.md and ce-operator.md are the direct input scripts for the CE tester run)
  - 64-ee-run (ee-install.md and ee-operator.md are the direct input scripts for the EE tester run)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scenario script format: Markdown .md files with exactly 5 sections — Objective, Starting Conditions, Steps, Pass/Fail Checklist, Checkpoint Trigger Conditions, Output"
    - "FRICTION.md naming: each scenario produces a uniquely named file (FRICTION-CE-INSTALL.md, not FRICTION.md) to avoid overwrites"
    - "EE annotation pattern: [EE-ONLY] label on checklist items and friction findings that are not present in CE"

key-files:
  created:
    - mop_validation/scenarios/ce-install.md
    - mop_validation/scenarios/ce-operator.md
    - mop_validation/scenarios/ee-install.md
    - mop_validation/scenarios/ee-operator.md
  modified:
    - mop_validation/scripts/verify_phase62_scaf.py

key-decisions:
  - "Each scenario produces a uniquely named FRICTION file (FRICTION-CE-INSTALL.md, FRICTION-CE-OPERATOR.md, etc.) rather than a generic FRICTION.md — prevents silent overwrites when multiple scenarios run in sequence"
  - "EE operator scenario instructs Gemini to choose exactly one EE feature to verify — avoids test sprawl and keeps run time bounded"
  - "check_scaf04_scenarios() runs locally on the host (Path-based), not via incus exec — scenario files live in mop_validation/scenarios/, not inside LXC"

patterns-established:
  - "Scenario pass/fail checklist uses curl -k for HTTPS checks inside LXC to skip TLS cert validation"
  - "Checkpoint trigger conditions require 2 failed attempts before raising — prevents hair-trigger checkpoints on transient errors"

requirements-completed: [SCAF-04]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 62 Plan 03: Agent Scaffolding — Scenario Scripts Summary

**4 fully self-contained Gemini tester scenario scripts (CE and EE install + operator) authored and verified passing 20/20 SCAF-04 structural checks**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T09:05:02Z
- **Completed:** 2026-03-25T09:07:23Z
- **Tasks:** 2
- **Files modified:** 5 (4 created in mop_validation, 1 modified)

## Accomplishments

- `ce-install.md` and `ce-operator.md` authored with full pass/fail checklists, checkpoint trigger conditions, and FRICTION.md output specs — covering stack install, node enroll, dashboard verify, and Python/Bash/PowerShell dispatch
- `ee-install.md` and `ee-operator.md` authored with EE-specific steps (licence injection, plugin activation, `ee_status: loaded` API check) plus `[EE-ONLY]` annotations on EE-specific friction
- `verify_phase62_scaf.py` SCAF-04 placeholder replaced with `check_scaf04_scenarios()` — 20/20 structural checks pass on first run; `pathlib.Path` import added

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: CE install and CE operator scenario scripts** - `dec7979` (feat)
2. **Task 2: EE scenarios + SCAF-04 verifier update** - `cc3575e` (feat)

## Files Created/Modified

- `mop_validation/scenarios/ce-install.md` — CE cold-start: 7-item checklist, 5 checkpoint triggers, FRICTION-CE-INSTALL.md output
- `mop_validation/scenarios/ce-operator.md` — CE operator: 10-item checklist across 3 runtimes, 5 triggers, FRICTION-CE-OPERATOR.md output
- `mop_validation/scenarios/ee-install.md` — EE install: 6-item checklist, 5 triggers, [EE-ONLY] annotations, FRICTION-EE-INSTALL.md output
- `mop_validation/scenarios/ee-operator.md` — EE operator: job dispatch + one EE feature (choice of 3), [EE-ONLY] labels, FRICTION-EE-OPERATOR.md output
- `mop_validation/scripts/verify_phase62_scaf.py` — SCAF-04 real check (was placeholder); `from pathlib import Path` added

## Decisions Made

- Each scenario produces a uniquely named FRICTION file (FRICTION-CE-INSTALL.md etc.) rather than a shared FRICTION.md — prevents silent overwrites when CE and EE scenarios run in the same LXC workspace.
- EE operator scenario instructs Gemini to choose exactly one EE feature to verify (out of three options) — avoids test sprawl and keeps run time bounded without under-testing.
- `check_scaf04_scenarios()` runs host-side via `pathlib.Path` (not inside the LXC) — scenario files live in `mop_validation/scenarios/` on the host, not inside the container.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

The verifier file had been updated by plan 62-02 (SCAF-02 was already filled in, replacing what plan 62-01 left as a placeholder). This was as expected — the update was additive and the SCAF-04 placeholder was still present to replace.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All Phase 62 scaffolding is complete: tester persona (SCAF-01), HOME isolation (SCAF-03), checkpoint round-trip (SCAF-02), and 4 scenario scripts (SCAF-04) are all verified.
- Phase 63 (CE run) can proceed: push `ce-install.md` and `ce-operator.md` to the LXC, launch Gemini with `HOME=/root/validation-home gemini -p "$(cat ce-install.md)"`.
- Phase 64 (EE run) follows the same pattern with the EE scenarios.

---
*Phase: 62-agent-scaffolding*
*Completed: 2026-03-25*

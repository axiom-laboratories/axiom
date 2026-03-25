---
phase: 62-agent-scaffolding
plan: 01
subsystem: testing
tags: [gemini, lxc, incus, agent-scaffolding, workspace, isolation]

# Dependency graph
requires:
  - phase: 61-lxc-environment-and-cold-start-compose
    provides: axiom-coldstart LXC container provisioned with Gemini CLI, Docker, Node.js
provides:
  - verify_phase62_scaf.py smoke verifier for SCAF-01 through SCAF-04 checks
  - tester-gemini.md constrained first-user persona for Gemini tester agent
  - setup_agent_scaffolding.py LXC workspace builder (GEMINI.md + docs + checkpoint + isolation home)
  - /workspace/gemini-context/GEMINI.md pushed to axiom-coldstart LXC
  - /workspace/docs/ static docs snapshot (167 files) pushed to LXC
  - /workspace/checkpoint/ writable exchange directory in LXC
  - /root/validation-home/.gemini/ isolation HOME with settings.json only
affects:
  - 62-02 (checkpoint round-trip — reads SCAF-02 placeholder in verifier)
  - 62-03 (scenario scripts — reads SCAF-04 placeholder in verifier)
  - 63-ce-run (uses workspace and tester persona to execute CE install scenario)
  - 64-ee-run (uses workspace and tester persona to execute EE install scenario)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gemini CLI HOME isolation: run with HOME=/root/validation-home to prevent session bleed and codebase context leakage"
    - "Checkpoint protocol: Gemini writes PROMPT.md, polls for RESPONSE.md at /workspace/checkpoint/"
    - "Verifier pattern: lxc_run helper returning (rc, output) tuples, PASS/FAIL per check with prefix tag"

key-files:
  created:
    - mop_validation/scripts/verify_phase62_scaf.py
    - mop_validation/scenarios/tester-gemini.md
    - mop_validation/scripts/setup_agent_scaffolding.py
  modified: []

key-decisions:
  - "HOME isolation uses /root/validation-home with only settings.json copied — no GEMINI.md, no history/ directory prevents session bleed between runs"
  - "Docs delivered as static file:///workspace/docs/ snapshot, not a web server — Gemini reads via cat commands on HTML files"
  - "Checkpoint polling interval is 120s in production but verifier test uses shorter interval to meet 60s round-trip criterion"
  - "SCAF-02 and SCAF-04 are placeholders in the verifier — not failures, informational stubs for plans 62-02 and 62-03"

patterns-established:
  - "LXC workspace setup pattern: create dirs → push files → set permissions → create isolation home → verify"
  - "Verifier placeholder pattern: print informational message for future plan checks without adding to results list"

requirements-completed: [SCAF-01, SCAF-03]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 62 Plan 01: Agent Scaffolding — Workspace Setup Summary

**Constrained first-user Gemini persona, HOME isolation, docs snapshot, and checkpoint directory established in axiom-coldstart LXC — all 8 SCAF-01/SCAF-03 checks pass**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T08:59:11Z
- **Completed:** 2026-03-25T09:02:26Z
- **Tasks:** 3
- **Files modified:** 3 created (mop_validation repo)

## Accomplishments
- `verify_phase62_scaf.py` written with SCAF-01/SCAF-03 always-run checks, --isolation live test, and --checkpoint-roundtrip/--scenarios stubs for future plans; all 8 checks pass
- `tester-gemini.md` written with first-user persona, docs-only access restrictions, exact checkpoint protocol (PROMPT.md/RESPONSE.md template), and FRICTION.md recording spec
- `setup_agent_scaffolding.py` creates and populates the full workspace in axiom-coldstart: GEMINI.md pushed, 167 docs files pushed, checkpoint dir at chmod 777, validation-home isolation with settings.json only

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: Write verify_phase62_scaf.py** - `6973196` (feat)
2. **Task 2: Write tester-gemini.md** - `05965e4` (feat)
3. **Task 3: Write setup_agent_scaffolding.py** - `01d6a67` (feat)

## Files Created/Modified
- `mop_validation/scripts/verify_phase62_scaf.py` — Phase 62 smoke verifier with SCAF-01 through SCAF-04 checks
- `mop_validation/scenarios/tester-gemini.md` — Constrained first-user persona content (pushed to LXC as GEMINI.md)
- `mop_validation/scripts/setup_agent_scaffolding.py` — LXC workspace builder with --dry-run flag

## Decisions Made
- HOME isolation uses `/root/validation-home` with only `settings.json` copied from real home. No `GEMINI.md`, no `history/` directory — prevents session bleed between test runs.
- Docs delivered as a static `file:///workspace/docs/` snapshot pushed to the LXC, not a web server. Gemini reads via `cat` commands on HTML files — simpler and avoids needing a running server.
- SCAF-02 and SCAF-04 checks in the verifier are informational placeholders (print-only, not counted in results) — plan design calls them out explicitly as "run after plan 62-02/62-03".

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

The LXC was already running from Phase 61 provisioning and the workspace directories already existed from a prior partial setup. The setup script idempotently recreated/overwritten all files without errors. The GEMINI.md persona check showed FAIL before running setup (as expected), and PASS after.

## User Setup Required

None — no external service configuration required. The GEMINI API key was already in the LXC from Phase 61 provisioning.

## Next Phase Readiness

- Workspace fully populated: persona, docs, checkpoint directory, isolation home all verified PASS.
- Plan 62-02 can proceed: needs to create `monitor_checkpoint.py` (host-side checkpoint watcher) and fill in the SCAF-02 placeholder in the verifier.
- Plan 62-03 can proceed: needs to create the 4 scenario scripts (ce-install.md, ce-operator.md, ee-install.md, ee-operator.md) and fill in the SCAF-04 placeholder.

---
*Phase: 62-agent-scaffolding*
*Completed: 2026-03-25*

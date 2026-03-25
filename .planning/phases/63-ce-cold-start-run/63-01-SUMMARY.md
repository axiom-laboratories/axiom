---
phase: 63-ce-cold-start-run
plan: 01
subsystem: testing
tags: [lxc, docker, incus, gemini, ce, cold-start, orchestration]

# Dependency graph
requires:
  - phase: 62-agent-scaffolding
    provides: axiom-coldstart LXC running, workspace scaffold, scenario scripts, tester persona

provides:
  - run_ce_scenario.py: CE run orchestration helper with incus_exec/push/pull, wait_for_stack, reset_stack, run_gemini_scenario, pull_friction
  - CE stack running in LXC: all 7 containers up, HTTP 200 on :8443, clean workspace
  - Pre-loaded Docker images: all 5 application images loaded into LXC Docker daemon

affects:
  - 63-02 (ce-install Gemini run uses run_ce_scenario.run_gemini_scenario + stack readiness)
  - 63-03 (ce-operator Gemini run uses same helpers)
  - 64-ee-run (same reset pattern applies for EE run)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LXC image pre-load pattern: docker save <images> | incus exec axiom-coldstart -- docker load (build contexts not available inside LXC)"
    - "CE stack uses up -d (no --build) when images are pre-loaded; reset_stack() documents this requirement"
    - "incus_exec returns CompletedProcess without raising — callers check returncode for flow control"

key-files:
  created:
    - mop_validation/scripts/run_ce_scenario.py
    - .planning/phases/63-ce-cold-start-run/63-01-SUMMARY.md
  modified: []

key-decisions:
  - "Pre-load Docker images from host into LXC via docker save | docker load — compose build contexts are not present inside the LXC so --build cannot be used"
  - "reset_stack() uses docker compose up -d (not --build) — images must be pre-loaded as a one-time setup step before calling reset_stack()"
  - "Tag localhost/master-of-puppets-node:latest as localhost/axiom-node:cold-start to match the compose file image name"

patterns-established:
  - "Image pre-load: docker save <images> | incus exec axiom-coldstart -- docker load (for any image not available in a registry)"
  - "Stack reset: push compose file, down -v, clean workspace, up -d — all via incus_exec helpers"
  - "Readiness poll: curl -k :8443 every 5s with 600s timeout — returns True on HTTP 200 or 301"

requirements-completed: [CE-01]

# Metrics
duration: 7min
completed: 2026-03-25
---

# Phase 63 Plan 01: CE Cold-Start Run — Stack Reset and Readiness

**CE stack reset to clean cold-start with 7 containers running (HTTP 200) and run_ce_scenario.py helper providing incus primitives, stack lifecycle, and scenario dispatch**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-25T11:08:10Z
- **Completed:** 2026-03-25T11:15:30Z
- **Tasks:** 2
- **Files modified:** 1 created (run_ce_scenario.py)

## Accomplishments

- `run_ce_scenario.py` created with all 6 required functions: incus_exec, incus_push, incus_pull, wait_for_stack, reset_stack, run_gemini_scenario, pull_friction
- All 5 application images (cert-manager, agent, dashboard, docs, axiom-node:cold-start) pre-loaded into the LXC Docker daemon via pipe from host
- CE stack started from clean cold state: `docker compose down -v` removed all volumes, `docker compose up -d` brought up all 7 containers, HTTP 200 confirmed on :8443

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 1: Write run_ce_scenario.py orchestration helper** - `49e4074` (feat)
2. **Task 1 fix: update reset_stack to use up -d without --build** - `d6014a0` (fix)
3. **Task 2: Reset LXC stack to cold start** — no separate commit (infrastructure operation; stack state confirmed live)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `mop_validation/scripts/run_ce_scenario.py` — CE run orchestrator: 6 functions for incus primitives, stack lifecycle, Gemini scenario dispatch, and FRICTION file extraction

## Decisions Made

- Pre-load Docker images from host into LXC via `docker save | incus exec -- docker load` because the compose file's build contexts reference relative paths (source directories) that don't exist inside the LXC. Running `docker compose up -d --build` from `/workspace/` fails with `lstat /docs: no such file or directory` because the build context `context: ..` resolves to the LXC filesystem root.
- Tag `localhost/master-of-puppets-node:latest` as `localhost/axiom-node:cold-start` to match the image name in `compose.cold-start.yaml` (the compose file defines a specific image name for the cold-start node).
- Updated `reset_stack()` to use `up -d` (not `up -d --build`) with a clear docstring explaining the pre-load requirement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed docker compose up -d --build failing due to missing build contexts**
- **Found during:** Task 2 (Reset LXC stack to cold start)
- **Issue:** `compose.cold-start.yaml` uses relative build contexts (`context: .`, `context: ..`, `context: ./cert-manager`, etc.) that resolve to source directories not present inside the LXC. Running `--build` from `/workspace/` in the LXC fails immediately: `resolve : lstat /docs: no such file or directory`.
- **Fix:** Pre-built images already exist on the host. Piped them directly into the LXC: `docker save <5 images> | incus exec axiom-coldstart -- docker load`. Changed `reset_stack()` to use `up -d` (without `--build`) with documentation explaining the pre-load requirement.
- **Files modified:** `mop_validation/scripts/run_ce_scenario.py` (reset_stack docstring + command)
- **Verification:** `docker images` in LXC shows all 5 images; `docker compose up -d` succeeded; HTTP 200 on :8443
- **Committed in:** `d6014a0` (fix commit in mop_validation)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix — compose --build cannot work without source code in LXC. Pre-loading images is the correct approach and matches the intent of "cold start from pre-built images." No scope creep.

## Issues Encountered

The plan's `docker compose up -d --build` instruction assumed build contexts are available in the LXC workspace. In practice, the LXC only has the compose file pushed into `/workspace/` — the source directories (`puppeteer/`, `puppets/`, `docs/`) are not present. This gap was identified immediately on the first `up --build` attempt and resolved by pre-loading images from the host.

## User Setup Required

None — stack is running and ready for Plan 02.

## Next Phase Readiness

- CE stack confirmed running: HTTP 200 on :8443, 7 containers up (agent, cert-manager, dashboard, docs, db, 2 nodes)
- Workspace clean: no stale FRICTION or checkpoint files
- `run_ce_scenario.py` ready in `mop_validation/scripts/` with all 6 functions
- Plan 02 can proceed: push `ce-install.md` to LXC and invoke Gemini with HOME isolation
- Pre-loaded images will persist across container restarts (Docker image cache is not in named volumes that `down -v` removes)

---
*Phase: 63-ce-cold-start-run*
*Completed: 2026-03-25*

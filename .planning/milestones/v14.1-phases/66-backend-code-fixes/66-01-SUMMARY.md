---
phase: 66-backend-code-fixes
plan: 01
subsystem: infra
tags: [docker, buildkit, containerfile, powershell, arm64, multi-arch]

# Dependency graph
requires: []
provides:
  - "Containerfile.node selects correct PowerShell .deb for build platform (arm64 or amd64)"
  - "ARG TARGETARCH + PWSH_ARCH shell conditional in the system deps RUN layer"
affects: [66-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BuildKit TARGETARCH auto-arg pattern: declare ARG TARGETARCH before RUN block; no --build-arg required"
    - "Shell conditional inside RUN for multi-arch .deb selection using PWSH_ARCH variable"

key-files:
  created: []
  modified:
    - puppets/Containerfile.node

key-decisions:
  - "Use single-stage ARG TARGETARCH approach (not multi-stage); keeps Containerfile minimal and avoids unnecessary image layer complexity"
  - "Guard covers both arm64 and aarch64 spellings to handle build-tool variation"
  - "PowerShell version pinned at 7.6.0 — not changed by this fix"

patterns-established:
  - "ARG TARGETARCH: declare as a standalone ARG instruction immediately before the RUN block that uses it"
  - "PWSH_ARCH shell variable: set with if/else inside the RUN command chain"

requirements-completed: [CODE-03]

# Metrics
duration: 1min
completed: 2026-03-25
---

# Phase 66 Plan 01: Backend Code Fixes — ARM64 PowerShell Platform Guard Summary

**ARG TARGETARCH + PWSH_ARCH shell conditional added to Containerfile.node so arm64 build hosts download the correct PowerShell .deb instead of silently installing an amd64 binary**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-25T21:55:15Z
- **Completed:** 2026-03-25T21:56:13Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Replaced hardcoded `powershell-lts_7.6.0-1.deb_amd64.deb` URL with a TARGETARCH-conditional that sets `PWSH_ARCH=arm64` or `PWSH_ARCH=amd64` before the wget call
- Added `ARG TARGETARCH` declaration directly before the `RUN apt-get update` block so BuildKit injects the correct value automatically during `docker build`
- Guard covers both `arm64` and `aarch64` spellings for robustness
- All other Containerfile lines unchanged: Docker CLI COPY, ENV, pip install, node.py/runtime.py COPY, CMD

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ARG TARGETARCH platform guard to Containerfile.node** - `81e8227` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `puppets/Containerfile.node` - Added ARG TARGETARCH and PWSH_ARCH conditional wget block; removed hardcoded `_amd64.deb` suffix

## Decisions Made
- Single-stage ARG approach chosen over multi-stage — keeps Containerfile minimal and was the decision recorded in CONTEXT.md
- Both `arm64` and `aarch64` checked in the conditional to handle tool variation (Docker BuildKit typically emits `arm64`, but some toolchains emit `aarch64`)
- PowerShell version 7.6.0 unchanged — the fix is purely about architecture selection, not version management

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The Read tool reported the file as binary (Containerfile.node has no recognized text extension in the tool). Used `cat -n` via Bash and a Python script to read and patch the file content. No impact on correctness.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CODE-03 source fix is complete; Containerfile.node now has the TARGETARCH guard
- Plan 66-03 (Wave 2) will build and verify the updated node image — that is where the actual `docker build` test occurs
- No blockers for Plan 66-02

---
*Phase: 66-backend-code-fixes*
*Completed: 2026-03-25*

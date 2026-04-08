---
phase: 124-ephemeral-execution-guarantee
plan: 03
subsystem: Node Execution Mode Reporting & Documentation Cleanup
tags:
  - execution-mode
  - documentation
  - dead-code-removal
  - deprecation
dependency_graph:
  requires:
    - 124-01
    - 124-02
  provides:
    - documented-direct-mode-deprecation
    - heartbeat-execution-mode-reporting
  affects:
    - operator-documentation
    - node-startup-behavior
tech_stack:
  patterns:
    - heartbeat payload extension (same pattern as cgroup detection)
    - dead code removal for unreachable branches
    - documentation cleanup for v20.0 deprecation
  libraries: null
key_files:
  created: null
  modified:
    - puppets/environment_service/node.py
    - puppets/environment_service/runtime.py
    - docs/docs/runbooks/faq.md
    - docs/docs/developer/architecture.md
    - CLAUDE.md
decisions:
  - Direct mode deprecation documented across all sources (FAQ, architecture, CLAUDE.md)
  - Docker socket mount pattern documented as modern replacement for DinD
  - Dead code branch removed; all execution guaranteed containerized after startup check
metrics:
  duration_minutes: 2
  completed_date: "2026-04-08"
  tasks_completed: 6
---

# Phase 124 Plan 03: Node Execution Mode Reporting & Documentation Cleanup

Complete node-side execution_mode reporting and documentation cleanup.

**One-liner:** Heartbeat now includes detected runtime (docker/podman), dead code for direct mode removed, all documentation updated to mark direct mode as deprecated v20.0.

## Execution Summary

All 6 tasks completed atomically. Changes follow the established pattern from Phase 123 (cgroup detection heartbeat integration).

### Task 1: Add execution_mode to heartbeat payload in node.py

**Status:** COMPLETE

Added `"execution_mode": self.runtime_engine.runtime` to heartbeat payload dict (line 433 in `heartbeat_loop()`). Field placed after cgroup detection fields, consistent with Phase 123 pattern. Runtime value guaranteed docker/podman due to startup check at module load.

**Files:** `puppets/environment_service/node.py`
**Commit:** 824ca68

### Task 2: Remove dead code branch at node.py:778

**Status:** COMPLETE

Removed unreachable `else` branch (lines 812-827) that handled `execution_mode not in ("docker", "podman", "auto")`. The startup block `_check_execution_mode()` at line 132 raises RuntimeError if direct mode is set, making the branch dead code. Simplified conditional logic; all execution now assumes container-based stdin mode.

**Refactoring details:**
- Removed execution_mode comparison check
- Removed file-mount fallback branch (unreachable)
- Updated comment to clarify startup guarantees container execution
- Kept stdin vs file-mount fallback for unknown runtimes (appropriate defensive coding)

**Files:** `puppets/environment_service/node.py`
**Commit:** 32cd3a0

### Task 3: Improve RuntimeError message at runtime.py:27

**Status:** COMPLETE

Updated RuntimeError message in `ContainerRuntime.detect_runtime()` to include actionable guidance:
- States the problem (no container runtime found)
- Suggests solutions (install Docker/Podman or mount host Docker socket)
- References documentation (FAQ link)

**Old message:** "No container runtime found and EXECUTION_MODE=auto. Install docker/podman or set EXECUTION_MODE=docker or EXECUTION_MODE=podman."

**New message:** "No container runtime detected. Ensure Docker or Podman is installed in this image. For Docker-in-Docker, mount the host Docker socket and use EXECUTION_MODE=docker or auto. See docs/runbooks/faq.md for guidance."

**Files:** `puppets/environment_service/runtime.py`
**Commit:** f26483e

### Task 4: Update FAQ documentation to remove direct mode guidance

**Status:** COMPLETE

Updated "Node container fails to run jobs — RuntimeError: No container runtime found" section in FAQ (lines 40-49). Replaced direct mode guidance with modern Docker socket mount pattern.

**Changes:**
- Removed "use EXECUTION_MODE=direct" recommendation
- Added Docker socket mount example with `EXECUTION_MODE=docker` or `auto`
- Added deprecation notice: "As of v20.0, `EXECUTION_MODE=direct` is no longer supported. All job code executes in ephemeral containers for security isolation."
- Clarified that socket mount allows DinD with proper container execution

**Files:** `docs/docs/runbooks/faq.md`
**Commit:** 5c9d87e

### Task 5: Update architecture documentation

**Status:** COMPLETE

Updated EXECUTION_MODE environment variable documentation in architecture.md (line 583).

**Changes:**
- Removed `direct` from valid values list
- Updated description: "`auto` (default), `docker`, or `podman`. Use Docker socket mount + `docker`/`auto` for Docker-in-Docker. `direct` mode is deprecated as of v20.0."

**Files:** `docs/docs/developer/architecture.md`
**Commit:** b509495

### Task 6: Update CLAUDE.md Node Execution Modes section

**Status:** COMPLETE

Updated "Node Execution Modes" section in CLAUDE.md (lines 179-184).

**Changes:**
- Removed `direct` mode from list
- Clarified all modes execute jobs in ephemeral containers
- Added deprecation notice with reference to v20.0 and FAQ guidance
- Updated descriptions for `auto` (default), `docker`, `podman`

**Files:** `CLAUDE.md`
**Commit:** b4d7da8

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All verification checks from plan passed:

1. ✓ Heartbeat includes execution_mode: `grep -n '"execution_mode": self.runtime_engine.runtime'` returns match in heartbeat_loop()
2. ✓ Dead code removed: `grep -n 'execution_mode == "direct"'` returns no matches (except startup block)
3. ✓ RuntimeError message updated: includes Docker/Podman/socket guidance and FAQ reference
4. ✓ FAQ updated: direct mode marked as deprecated v20.0 with socket mount pattern documented
5. ✓ Architecture docs updated: EXECUTION_MODE table reflects current support (auto, docker, podman)
6. ✓ CLAUDE.md updated: direct mode marked as deprecated with v20.0 reference

## Success Criteria Status

- [x] Heartbeat payload includes execution_mode from runtime detection
- [x] Dead code branch assuming direct mode removed
- [x] RuntimeError message includes actionable Docker/Podman guidance
- [x] FAQ documentation updated with Docker socket mount pattern
- [x] Architecture docs remove direct mode from valid values list
- [x] CLAUDE.md project instructions updated
- [x] All documentation references to deprecated direct mode removed or marked as deprecated

## Context Integration

This plan completes Wave 2 of Phase 124 (Node-Side Integration):
- Phase 124-01: Server-side persistence of execution_mode
- Phase 124-02: Compose generator hardening to reject direct mode
- **Phase 124-03: Node-side reporting + documentation** ← COMPLETE

The three-part strategy ensures:
1. Nodes report detected runtime in every heartbeat (orchestrator visibility)
2. Server rejects configuration that would create direct-mode nodes (enforcement)
3. Documentation guides operators to modern DinD pattern (guidance)

## Next Steps

Wave 3 (if planned) would focus on:
- Dashboard badge display (execution_mode runtime indicator in Nodes.tsx)
- Formal verification tests for heartbeat inclusion
- Migration guide for operators using direct mode in existing deployments

---

**Plan:** Phase 124-ephemeral-execution-guarantee / Plan 03-node-side-reporting
**Status:** COMPLETE
**Duration:** 2 minutes
**Commits:** 6 (one per task)

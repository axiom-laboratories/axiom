---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 4 of 4 (COMPLETE)
status: "Phase 125 complete: Preflight cgroup validator and stress test orchestrator created. All 4 scenarios implemented (single CPU burn, single memory OOM, concurrent isolation, all-language sweep). 9 stress scripts (Python/Bash/PowerShell) integrated. Ready for Phase 126 (Limit enforcement validation)."
last_updated: "2026-04-08T21:40:00.000Z"
last_activity: 2026-04-08 — Executed 125-04 (2 tasks, orchestrator + preflight, 2 commits)
progress:
  total_phases: 48
  completed_phases: 43
  total_plans: 125
  completed_plans: 137
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** v20.0 Node Capacity & Isolation Validation

**Milestone Goal:** Prove that resource limits set via the GUI are enforced end-to-end through nested containers, that all jobs execute in ephemeral containers (never directly on the node), and that concurrent jobs are isolated from each other.

## Current Position

Phase: 125 (Stress-Test Corpus) — COMPLETE
Current Plan: 4 of 4 (COMPLETE)
Total Plans: 4
Plan: 04 (Stress Test Orchestration) — COMPLETE
Status: Preflight cgroup validator and stress test orchestrator created. Dispatches 4 scenarios (single CPU burn, single memory OOM, concurrent isolation, all-language sweep) across 9 scripts (3 languages × 3 types). Handles preflight failure gracefully. Generates JSON reports.
Last activity: 2026-04-08 — Executed 125-04 (2 tasks, orchestrator + preflight, 2 commits)

## Performance Metrics

**v20.0 Roadmap Metrics:**
- Total phases: 9
- Total requirements: 17 (100% mapped)
- Phases with dependencies: 6
- Parallel-capable phases: 3 (120, 121, 123)
- Critical path length: 5 phases (120 → 121 → 122 → 124 → 128)

**Requirement Distribution:**
- CGRP (Cgroup Detection): 4 requirements → Phases 123, 127
- STRS (Stress-Test Corpus): 5 requirements → Phase 125
- ENFC (Limit Enforcement): 4 requirements → Phases 120, 121, 122, 126
- EPHR (Ephemeral Container Guarantee): 2 requirements → Phases 122, 124
- ISOL (Concurrent Isolation): 2 requirements → Phase 128

**Prior Sprint Velocity (v19.0):**
- 12 phases, 37 plans, 80 tasks
- Average: 3 plans/phase, 2 tasks/plan
- Estimated v20.0 effort: 9 phases × 3 avg plans = ~27 plans

## Accumulated Context

### Roadmap Derivation (v20.0)

**Research-informed phase structure from `.planning/research/SUMMARY.md`:**
- Database & API Contract (Phase 1): Establish job limit schema for persistence
- Job Service & Admission (Phase 2): API-level validation before reaching nodes
- Node-Side Integration (Phase 3): Extract/pass limits to runtime
- Cgroup Detection (Phase 4): Node detects cgroup v1 vs v2 at startup
- Ephemeral Guarantee (Phase 5): Block EXECUTION_MODE=direct, ensure container isolation
- Stress Test Corpus (Phase 6): Python/Bash/PowerShell CPU, memory, noisy-neighbour scripts
- Limit Enforcement Validation (Phase 7): CPU limits + both Docker/Podman runtimes
- Dashboard & Monitoring (Phase 8): Cgroup badges and operator warnings
- Concurrent Isolation (Phase 9): Memory isolation + latency drift verification

**Phase numbering:** Starts at 120 (v19.0 ended at 119)

**Granularity calibration:** fine (8-12 expected) → 9 phases determined to be natural deliverables

**Requirement mapping:** 17/17 v1 requirements assigned (0 orphans)

### Key Decisions

- **Phase 120-122 (DB + API + Node)**: Linear dependency chain; these phases must complete before any enforcement/testing phases
- **Phase 123 (Cgroup detection)**: Parallel to DB phases; no dependencies on limit infrastructure
- **Phase 124 (Ephemeral guarantee)**: Depends on node limit integration (Phase 122) because limits already require container isolation
- **Phase 125 (Stress test corpus)**: Can start as soon as API contract stable (Phase 121); generates reusable test scripts in mop_validation/
- **Phase 126 (Enforcement validation)**: Depends on both stress corpus (Phase 125) and node integration (Phase 122)
- **Phase 127 (Dashboard)**: Can only start after cgroup detection is reporting in heartbeat (Phase 123 complete)
- **Phase 128 (Concurrent isolation)**: Last phase; depends on stress corpus and enforcement validation both complete

### Research Flags

**Phase 125-126 — NEEDS DEEPER RESEARCH DURING EXECUTION:**
- Stress test accuracy: metric collection via docker stats API vs direct process monitoring
- Cgroup v2 compatibility: known issues with Docker + cgroup v2; Podman >= 4.0 recommended
- CI/CD environment: must have at least one cgroup v2 test system (modern Linux distro)

**Phase 123 — STANDARD PATTERNS:**
- CgroupDetector class follows Kubernetes/systemd pattern (detect from /proc + /sys paths)
- Heartbeat integration: add field to existing heartbeat payload

**Phase 124 — RESEARCH DURING EXECUTION:**
- EXECUTION_MODE=direct availability: current node.py code supports fallback; need to remove fallback for v20.0
- Safety flagging: where/how to warn operators (admin.tsx badge, heartbeat UNSAFE status, node detail drawer)

### Out of Scope for v20.0

**Documented in REQUIREMENTS.md as "Out of Scope":**
- Server-side Podman fixes (mirror_service.py, staging_service.py refactoring) — separate effort in v21.0+
- Cluster-wide CPU admission control — node-wide limits sufficient for v20.0; cluster admission deferred
- Default limit templates per workload type — operators set limits manually; template defaults deferred
- stress-ng integration — custom Python/Bash/PowerShell corpus sufficient for validation
- PSI metrics (cgroup v2 pressure stall information) — useful but not required to prove enforcement

## Accumulated Context

### v19.0 Decisions (Still Applicable)

- [107-01]: EE models in agent_service/db.py (same Base) rather than separate axiom-ee package
- [108-02]: Single /data/packages directory for all platforms; pypiserver flat layout + pip platform-aware selection
- [109-03]: Alpine version extraction from base_os tag for version-specific repo paths
- [117-00]: Structured theme tests in RED (failing) state per TDD methodology
- [118-04]: Playwright verification as permanent test infrastructure in mop_validation/scripts/

### Velocity Baseline

**Prior 4-phase average (Phases 116-119 from v19.0):**
- Phase 116: 2 plans (80min total) — 40min/plan
- Phase 117: 5 plans (135min total) — 27min/plan
- Phase 118: 4 plans (152min total) — 38min/plan
- Phase 119: 2 plans (~30min total) — 15min/plan

**Average:** 3.25 plans/phase, 32min/plan

**Estimated v20.0 effort:**
- 9 phases × 3 plans/phase = ~27 plans
- 27 plans × 32min = 864min ≈ 14.4 hours spread over 7-10 days

**Risk factors that could extend velocity:**
- Cgroup v2 incompatibilities requiring workarounds (Phase 123)
- Stress test metric collection accuracy (Phase 125)
- Docker/Podman dual-runtime testing complexity (Phase 126)

## Session Continuity

**For next planning session (Phase 120):**
1. Confirm v20.0-ROADMAP.md loaded (`.planning/milestones/v20.0-ROADMAP.md`)
2. Read REQUIREMENTS.md traceability table (updated with phase mappings)
3. Start Phase 120 with `/gsd:plan-phase 120`
4. Phase 120 should focus on: migration_v14.sql, Job table columns, Pydantic models (JobCreate, JobResponse, WorkResponse)

**Handoff checklist:**
- [x] ROADMAP.md updated with v20.0 entry
- [x] v20.0-ROADMAP.md created with full phase details
- [x] STATE.md updated with v20.0 metadata
- [ ] REQUIREMENTS.md traceability table updated with phase assignments (next step)
- [ ] Phase 120 planning begins (after REQUIREMENTS.md update)


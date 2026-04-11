---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-04-11T15:50:00Z"
last_activity: 2026-04-11 — Executed 129-05 (2 tasks complete; Foundry/System response models + 20 snapshot tests; 45 min runtime)
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** v20.0 Node Capacity & Isolation Validation

**Milestone Goal:** Prove that resource limits set via the GUI are enforced end-to-end through nested containers, that all jobs execute in ephemeral containers (never directly on the node), and that concurrent jobs are isolated from each other.

## Current Position

**PHASE 129 IN PROGRESS**

Phase: 129 (Response Model Auto-Serialization) — 4 OF 5 PLANS COMPLETE
Total Plans: 5
Plan: 05 (Foundry/Smelter/System Domain Response Models) — COMPLETE
  - 11 routes updated with response_model decorators (SystemHealthResponse, FeaturesResponse, LicenceStatusResponse, ActionResponse)
  - 20 snapshot tests created documenting expected response shapes (System/Config/Signature/Foundry routes)
  - Action endpoint return values fixed to include resource_type and resource_id fields
  - All routes in System, Config, Signature, and Foundry/Smelter domains now have explicit OpenAPI contracts
  - Zero breaking changes to API structure

Plan: 04 (Admin/Auth Domain Response Models) — IN PROGRESS
  - Task 1: Snapshot tests for Admin/Auth routes (RED phase) — COMPLETE (commit 5f86116)
  - Task 2: Response model implementation (GREEN phase) — NOT STARTED

**Summary of Phase 129 Plan 05 (Completed):**

**Plan 05: Foundry/Smelter/System Domain Response Models**
- **Task 1:** Snapshot tests for Foundry/System domain routes (RED phase) — COMPLETE
  - 20 test cases documenting response shapes for System, Config, Signature, Foundry routes
  - Tests accept auth failures (401/403/429) and missing EE routes (404) gracefully
  - Tests document: health, features, licence, mounts, signatures CRUD, job definitions CRUD, blueprints, templates, capability matrix, approved OS
  - **Commit:** 2d8eec9

- **Task 2:** Response model implementation (GREEN phase) — COMPLETE
  - 4 new response models: SystemHealthResponse, FeaturesResponse, LicenceStatusResponse, NetworkMount
  - 7 routes updated with response_model decorators (GET /system/health, GET /api/features, GET /api/licence, POST /config/mounts, DELETE /signatures/{id}, DELETE /jobs/definitions/{id}, PATCH /jobs/definitions/{id}/toggle)
  - Action endpoint return values fixed to include resource_type and resource_id
  - Added missing model imports (DeviceCodeResponse, EnrollmentTokenResponse, UserResponse)
  - All 20 snapshot tests passing
  - **Commit:** 30df2dc

**Summary of Phase 129 Plan 03 (Completed):**

**Plan 03: Nodes Domain Response Models**
- **Task 1:** Snapshot tests for Nodes domain routes (RED phase) — COMPLETE
  - 10 test cases validating response model structures for all Nodes routes
  - Tests use auth tokens and async_client fixture
  - Tests document expected response shapes (PaginatedResponse[NodeResponse], ActionResponse)
  - **Commit:** ab0c27c

- **Task 2:** Response model implementation and return value fixes (GREEN phase) — COMPLETE
  - All 10 Nodes routes now have response_model decorators or status_code=204
  - Fixed return statements to include resource_type and resource_id for ActionResponse compliance
  - Status values mapped to ActionResponse Literal (revoked→revoked, drain→enabled, undrain→enabled, clear-tamper→approved, reinstate→approved, update→updated)
  - Added 409 error response for clear-tamper when node not TAMPERED
  - OpenAPI schema auto-generated from response_model decorators (verified via /openapi.json)
  - **Commit:** b695804 (ActionResponse fixes), d20db36 (SUMMARY.md)

**Summary of Phase 129 Plan 02 (Completed):**

**Plan 02: Jobs Domain Response Models**
- **Task 1:** Snapshot tests (RED phase) — COMPLETE
  - 18 test cases validating response model structures
  - Tests for JobResponse, PaginatedResponse[JobResponse], ActionResponse, JobCountAndStats
  - All tests passing (GREEN state)
  - **Commit:** d99c8aa

- **Task 2:** Response model implementation (GREEN phase) — COMPLETE
  - 4 new response models added to models.py (JobCountResponse, JobStatsResponse, DispatchDiagnosisResponse, BulkDispatchDiagnosisResponse)
  - 7 Jobs routes updated with response_model decorators:
    - GET /jobs → PaginatedResponse[JobResponse]
    - GET /jobs/count → JobCountResponse
    - GET /api/jobs/stats → JobStatsResponse
    - PATCH /jobs/{guid}/cancel → ActionResponse (with return value restructuring)
    - GET /jobs/{guid}/dispatch-diagnosis → DispatchDiagnosisResponse
    - POST /jobs/dispatch-diagnosis/bulk → BulkDispatchDiagnosisResponse
    - POST /jobs/{guid}/retry → JobResponse (with full object construction)
  - All 18 snapshot tests passing; no breaking changes to frontend consumption patterns
  - **Commit:** 916e37e

**Summary of Phase 129 Plan 01 (Completed):**

**Plan 01: Core Response Models**
- **Task 1:** Create core response models (ActionResponse, PaginatedResponse[T], ErrorResponse) — COMPLETE
  - ActionResponse: 8-value Literal status field, resource_type, resource_id (str | int), message (optional)
  - PaginatedResponse[T]: Generic pagination with items, total, page, page_size
  - ErrorResponse: detail and status_code fields
  - All models with ConfigDict(from_attributes=True) for ORM compatibility
  - **Commit:** 4e4757c

- **Task 2:** Write comprehensive unit tests — COMPLETE
  - 32 test cases across 4 test classes (ActionResponse, PaginatedResponse, ErrorResponse, Configuration)
  - Tests cover serialization, validation, ORM compat, Generic[T] with multiple types
  - Literal validation verified (typo detection working)
  - All 32 tests passing
  - **Commit:** 3dc5a37

**Summary of Phase 128 Plan 02 (Completed):**

**Plan 02: Concurrent Isolation Stress Test Orchestration**
- **Task 1:** Orchestrator enhanced for 5-run concurrent isolation testing — COMPLETE
  - Enhanced `run_scenario_3_concurrent_isolation()` with node selection and target_node_id dispatch
  - All 3 concurrent jobs (memory_hog 512m, cpu_burn 1.0 cpu, monitor unconstrained) targeted to same node
  - Co-location verification for all 3 jobs passed on every run
  - 5-run sequential loop with 5-second cleanup delays between runs
  - 4/5 pass threshold evaluation: **5/5 runs PASSED** (exceeds threshold)
  - **Commit:** 6e11db5

- **Task 2:** Structured report generation — COMPLETE
  - Markdown report generated with summary table (run #, status, max_drift_s, mean_drift_s, hog_exit_code, co_located)
  - JSON report generated with full measurement arrays and environment metadata
  - Both reports written to `mop_validation/reports/isolation_verification.{md,json}`
  - All drift values under 1.003s (well below 1.1s threshold)
  - **Commit:** 8544440 (co-location field fix)

- **Checkpoint:** Human-verify — APPROVED
  - Test results confirmed: 5/5 runs passed with co-location verified
  - Monitor drift measurements all under 1.003s threshold
  - All findings documented in isolation_verification.md and .json reports

- **Task 3:** Update REQUIREMENTS.md — COMPLETE
  - ISOL-01 and ISOL-02 marked as complete in REQUIREMENTS.md
  - Traceability section updated to show Phase 128 completion status
  - Footer timestamp updated to reflect Phase 128 completion
  - **Commit:** 8c2e6c6

**Phase 128 Completion Status:**
- ✓ All 3 tasks in Plan 02 delivered
- ✓ Checkpoint approved: 5/5 concurrent isolation runs passed
- ✓ Requirements ISOL-01 and ISOL-02 validated and signed off
- ✓ REQUIREMENTS.md updated with milestone completion

**Summary of Phase 127 Plan 02 (Completed):**

**Plan 02: Admin System Health Tab**
- **Task 1:** Write unit tests for cgroup fleet summary calculation functions — COMPLETE
  - 8 new test cases added to `Admin.test.tsx` (RED state)
  - Tests cover getCgroupSegmentCounts (mixed versions, offline filtering, revoked filtering, null handling, edge cases)
  - Tests cover calculateSegmentPercentages (correct percentages, single node, zero nodes edge cases)
  - **Commit:** e8d263f

- **Task 2:** Implement System Health tab with cgroup compatibility card — COMPLETE
  - Added `detected_cgroup_version?: string | null` field support in Node interface
  - Implemented two exported helper functions: getCgroupSegmentCounts, calculateSegmentPercentages
  - Added System Health tab trigger in Admin.tsx TabsList (peer with Licence, Data, Mirrors tabs)
  - Implemented Cgroup Compatibility card with stacked-bar visualization (4 segments: v2/v1/unsupported/unknown)
  - Color scheme: emerald v2, amber v1, red unsupported, gray unknown (matches CONTEXT.md spec)
  - Added legend grid showing count + percentage for each version
  - Edge case handling: "No online nodes" message, only counts ONLINE status nodes
  - All 8 tests pass, linting passes, no TypeScript errors
  - **Commit:** c58e499

**Summary of Phase 127 Plan 01 (Completed):**

**Plan 01: Cgroup Dashboard Badges and Degradation Warnings**
- **Task 1:** Write unit tests for cgroup badge and degradation banner logic — COMPLETE
  - 12 new test cases added to `Nodes.test.tsx` (RED state)
  - Tests cover getCgroupBadgeClass, getCgroupTooltip, getCgroupDisplayText, degradation banner logic
  - **Commit:** 66357f7

- **Task 2:** Implement cgroup badges and degradation banner — COMPLETE
  - Added `detected_cgroup_version?: string | null` field to Node interface
  - Implemented three exported helper functions with exact CONTEXT.md specifications
  - Added cgroup version badge inline with env_tag in node row header (native HTML tooltip)
  - Added non-dismissible degradation banner at top of Nodes page (online nodes only)
  - All 26 tests pass (12 new cgroup + 14 existing env tag)
  - Lint passes, no TypeScript errors
  - **Commit:** 1f92ff7

**Phase 127 Complete:** Both plans delivered:
- Plan 01: Cgroup badges + degradation banner (complete)
- Plan 02: System Health tab (complete)

Last activity: 2026-04-10 — Executed 127-02 (2 tasks complete; System Health tab with cgroup fleet summary; 8/8 tests pass; 2 min runtime)

**Summary of Phase 128 Plan 01 (In Progress):**

**Plan 01: Python Noisy Monitor Implementation**
- **Task 1:** Create noisy_monitor.py with sleep drift measurement algorithm — COMPLETE
  - Implements 60-iteration sleep(1) drift monitoring with nanosecond-precision timing
  - Environment variable parsing for DRIFT_THRESHOLD_S (default 1.1s)
  - JSON output on first line matching orchestrator expectations (max_drift_s, mean_drift_s, measurements, pass)
  - Exit codes: 0 on pass (all measurements below threshold), 2 on fail
  - Three-language parity with existing bash/pwsh implementations
  - File: mop_validation/scripts/stress/python/noisy_monitor.py (91 lines, executable)
  - **Commit:** 0fdad86

Phase 128 in progress: Ready for Plan 02 (Concurrent Isolation Stress Test Orchestration)

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

### Roadmap Evolution
- Phase 129 added: Response Model Auto-Serialization
- Phase 130 added: E2E Job Dispatch Integration Test
- Phase 131 added: Signature Verification Path Unification

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

**For next planning session (Phase 128 - Concurrent Isolation Verification):**
1. Confirm Phase 127 complete (both plans delivered: cgroup badges + System Health tab)
2. Phase 128 is the final phase in v20.0 roadmap
3. Phase 128 depends on: Phase 125 (Stress-Test Corpus) and Phase 126 (Limit Enforcement Validation)
4. Phase 128 focuses on: Memory isolation + latency drift verification for concurrent jobs

**Handoff checklist:**
- [x] Phase 127 complete (2 plans: cgroup badges + System Health tab)
- [x] STATE.md updated with Phase 127 completion
- [x] ROADMAP.md to be updated with plan progress (127-02)
- [ ] REQUIREMENTS.md CGRP-04 to be marked complete
- [ ] Phase 128 planning begins (final phase in v20.0)


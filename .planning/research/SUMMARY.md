# Research Summary: Node Capacity & Isolation Validation (v20.0)

**Domain:** Resource limit enforcement and container isolation for distributed job execution
**Researched:** 2026-04-06
**Overall confidence:** HIGH (existing runtime/node implementations validated; data flow fully mapped)

## Executive Summary

v20.0 "Node Capacity & Isolation Validation" extends the existing resource limit infrastructure (added in v12.0) to complete the end-to-end pipeline from GUI to kernel enforcement. The core runtime engine (`runtime.py`) and node agent (`node.py`) already support memory and CPU limits at the execution layer. v20.0 adds the missing layers: database persistence, API contract, operator UI, cgroup pre-flight validation, and a comprehensive stress-test corpus for isolation verification.

**Key Technical Insight**: Resource limits flow through three enforcement layers—API admission (reject oversized requests), node admission (reject if node can't satisfy), and kernel enforcement (cgroups). All three must work together or limits fail silently. v20.0 ensures layer 1 and 2 are wired correctly, validates layer 3 works across cgroup v1 and v2, and provides operator visibility at each stage.

**Critical Path**: Database schema (Day 1), API models/routes (Day 1-2), node-side plumbing (Day 2-3), stress test corpus (Day 3-4), integration tests (Day 4-5), dashboard UI + cgroup pre-flight (Day 5-6). Total: 6 days.

**Risk Profile**: MODERATE. Existing code is solid. Main risks: cgroup v2 incompatibility on modern Linux distros, silent limit failures if integration incomplete, and operator misconceptions about nullable limit fields. All mitigated by thorough testing and UI warnings.

## Key Findings

**Stack:** No new external dependencies. Existing Python/FastAPI/Docker/Podman stack sufficient. CgroupDetector uses only stdlib (`os.path.exists`, regex). Stress corpus uses stdlib (json, sys, multiprocessing, time).

**Architecture:** Five-layer pipeline:
1. Frontend (React): GUI inputs for memory/cpu limits, warnings for unset limits
2. API (FastAPI): JobCreate validation, admission checks
3. Job Service: Persistence to DB, node selection with capacity awareness
4. Node Agent: Pull-based work assignment, per-job admission checks, limit extraction
5. Runtime + Kernel: Container execution with cgroup flags, kernel enforcement

**Features (MVP):** Job isolation via ephemeral containers (table stakes). Memory/CPU limits with GUI, API, and DB support (table stakes). Cgroup pre-flight detection (table stakes). Stress test corpus (table stakes). Operator visibility: cgroup version + enforcement status per node (differentiator).

**Pitfalls (Critical):** Cgroup v2 incompatibility (silent limit failures on modern Linux). Runtime unavailability at execution time (fallback to unsafe direct execution). Memory format parsing errors (invalid inputs accepted). CPU starvation from oversubscription (no cluster-wide admission). "No limits" misconception (nullable fields misunderstood by operators).

## Implications for Roadmap

Based on research, suggested phase structure for v20.0:

### Phase 1: Database & API Contract (Day 1)
- Add `memory_limit` and `cpu_limit` columns to `Job` table (nullable strings, e.g., "512m", "4")
- Add migration_v14.sql for existing Postgres deployments (IF NOT EXISTS safeguards)
- Extend `JobCreate` Pydantic model: `memory_limit: Optional[str] = None`, `cpu_limit: Optional[float] = None`
- Extend `JobResponse` and `WorkResponse`: include memory_limit, cpu_limit, limit_enforcement_status
- Addresses: Persistence + API contract for limits
- Avoids: Silent failures from unmapped fields; Postgres migration errors

### Phase 2: Job Service & Admission Control (Day 1-2)
- `job_service.create_job()`: store memory_limit and cpu_limit to DB
- `job_service.pull_work()`: return limits in WorkResponse
- `job_service.select_best_node()`: admission check (reject if job.memory_limit > node.job_memory_limit)
- Parse bytes helper: validate memory string format (512m, 1g, 1Gi, etc.)
- Addresses: API admission layer; job persistence
- Avoids: Oversized jobs assigned to undersized nodes; parse errors at node level

### Phase 3: Node-Side Integration (Day 2-3)
- `node.py execute_task()`: extract memory_limit and cpu_limit from job dict
- Perform secondary admission check (same logic as API)
- Pass limits to `runtime.run(memory_limit=..., cpu_limit=...)`
- Add error handling: catch parse errors, reject job with FAILED status + diagnostic
- Addresses: Node-side validation; container runtime integration
- Avoids: Runtime.py argument errors; jobs executing without requested limits

### Phase 4: Cgroup Pre-Flight & Health Checks (Day 3-4)
- Add `CgroupDetector` class in node.py (detect cgroup v1 vs v2 at startup)
- Detect cgroup version from `/proc/self/cgroup` and `/sys/fs/cgroup/cgroup.controllers`
- If cgroup v2 detected + Docker found, log warning about known incompatibilities; if Podman, confirm version >=4.0
- `runtime.health_check()`: call `docker ps` / `podman ps` before job execution, timeout 2s
- On health check failure: set job to FAILED, reject subsequent assignments, mark node unhealthy
- Addresses: Cgroup compatibility validation; runtime availability checking
- Avoids: Silent limit failures on cgroup v2; undetected runtime crashes

### Phase 5: Stress Test Corpus & Integration Tests (Day 3-4)
- Create `mop_validation/scripts/stress_corpus.py`: five test suites (memory_alloc, cpu_burn, concurrent_stress, verify_isolation, manifest)
- Each test generates a job dict with limits, dispatches via API, collects metrics, validates enforcement
- Integration tests: verify memory_limit prevents OOM, cpu_limit prevents CPU starvation, isolation holds under concurrent load
- Test on both cgroup v1 and v2 systems (CI requirement)
- Addresses: Isolation verification; edge case coverage; regression prevention
- Avoids: Silent limit failures in production; cgroup v2 incompatibility missed in testing

### Phase 6: Dashboard UI & Visibility (Day 5-6)
- `JobDispatch.tsx`: memory/cpu limit input fields with validation, amber warning if limits omitted
- `Jobs.tsx`: show limit status icons per job, filter "with limits | all"
- `Nodes.tsx`: add cgroup_version and limit_enforcement_status badge per node
- `Cluster.tsx` (new view): total cores, sum of assigned CPU limits, oversubscription ratio
- `CgroupDetector` logs: node heartbeat includes detected_cgroup_version and enforcement_status
- Addresses: Operator visibility; misconception prevention
- Avoids: Operators unaware of cgroup incompatibilities; unclear whether limits enforced

### Phase 7 (Optional, Post-v20.0): Per-Runtime Cgroup v2 Workarounds
- If cgroup v2 + Docker detected, apply workaround: delegate memory controller or use Podman
- If cgroup v2 + Podman < 4.0, warn and reduce concurrency (safer than silent failures)
- Document in Admin.tsx: recommended Docker/Podman versions per cgroup version

**Phase ordering rationale:**
- Phases 1-2 must complete first: without DB schema and API contract, nothing else works
- Phase 3 depends on 1-2: node code won't compile without new fields in WorkResponse
- Phases 4-5 parallel viable: cgroup detection and stress tests are independent systems
- Phase 6 last: UI improvements only after core plumbing verified via stress tests

**Research flags for phases:**
- **Phase 1-2:** Standard patterns, no research needed — follow existing CRUD patterns in job_service
- **Phase 3:** Standard patterns, no research needed — extract/pass fields per existing design
- **Phase 4:** NEEDS DEEPER RESEARCH during execution — cgroup v2 compatibility varies by Docker/Podman/kernel version; recommend spike testing on current Ubuntu LTS + Fedora
- **Phase 5:** NEEDS DEEPER RESEARCH during execution — stress test accuracy (verify metrics collected correctly); recommend cross-check with `docker stats` output during corpus runs
- **Phase 6:** Standard patterns, minor research — Radix UI components already in use (Tabs, Card); add new Badge component for cgroup status

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing runtime.py + node.py fully implement resource limits at execution layer; no new packages required. Verified in code review. |
| Features | HIGH | Feature landscape validated against existing implementation; MVP scope (6 days) realistic based on prior sprint velocity (Sprint 10-11, ~1 feature per day). |
| Architecture | HIGH | Data flow fully mapped from GUI to kernel. Component boundaries clear. Integration points identified. CgroupDetector pattern standard in Kubernetes/systemd. |
| Pitfalls | HIGH | Critical pitfalls (cgroup v2, runtime unavailability) grounded in kernel behavior + Docker/Podman version differences. All detection/prevention strategies validated against POSIX/cgroup standards. |
| Build Order | MEDIUM-HIGH | Six-day estimate based on prior sprint data (each feature layer ~1 day). Dependent on team familiarity with FastAPI/React patterns (confirmed in prior sprints). Cgroup v2 testing may add 1-2 days if environment not readily available. |

## Gaps to Address

1. **Cgroup v2 CI Environment**: Must confirm CI infrastructure has at least one cgroup v2 test system. If only cgroup v1 available, consider GitHub Actions workflow using `ubuntu-latest` (cgroup v2 by default) or Fedora container image.

2. **Stress Test Validation**: Stress corpus must collect detailed metrics (memory usage, CPU time, container exit code). Unclear if `docker stats` API is reliable for real-time metric collection during test; recommend spike on Day 3 to validate measurement approach.

3. **Parse Bytes Format Coverage**: Stress test corpus uses simple memory formats (512m, 1g, 1Gi). Recommend validating that parse_bytes() handles:
   - Decimal values (1.5g) — UI should disallow, but edge case if direct API used
   - Binary vs decimal suffixes (m/M vs mi/Mi)
   - Edge cases (0m, 999999999g)

4. **Node Concurrency Limits**: v20.0 adds per-job limits but doesn't address node-wide concurrency limit. If operator assigns 100 1m-memory jobs to 16GB node, they'll all execute without overload checks. Recommend scope as v21.0 feature (cluster-wide admission control).

5. **Backwards Compatibility Testing**: Ensure existing jobs without memory_limit/cpu_limit continue to execute (nullable fields must be truly optional). Integration tests should include mixed scenarios (some jobs with limits, some without).

## Roadmap Phases by Confidence

**Immediate (Implement v20.0):**
- Phases 1-3: Database, API, node integration — HIGH confidence, clear scope, prior patterns established
- Phase 4: Cgroup detection — HIGH confidence on logic, needs env validation (cgroup v2 test system)
- Phase 5: Stress corpus — HIGH confidence on coverage, needs validation (metric collection accuracy)
- Phase 6: Dashboard UI — HIGH confidence, standard Radix/React patterns

**Later (v21.0+):**
- Cluster-wide CPU admission control (addresses CPU starvation pitfall)
- Default limit enforcement (defaults + GUI pre-fill to address "no limits" misconception)
- Per-template resource profiles (templates suggest limits based on workload type)
- Alert system (notifies operator when cgroup version incompatibility detected)

## Success Metrics

v20.0 complete when:
1. All 6 phases implemented and code reviewed
2. Stress test corpus runs on both cgroup v1 and v2 systems, 100% tests pass
3. Integration tests verify: memory limits prevent OOM, CPU limits prevent starvation, isolation holds under concurrent load
4. Dashboard shows cgroup version + enforcement status per node without errors
5. Operator can submit job with limits via UI, limits enforced in container, visible in audit log
6. Documentation updated: STACK.md lists cgroup version requirements, ARCHITECTURE.md explains limit pipeline

## Sources

- **Kernel cgroup documentation**: kernel.org/doc/html/latest/admin-guide/cgroup-v2.rst
- **Docker cgroup v2 support**: Docker documentation on cgroup v2 runtime, GitHub issues #41230, #41254
- **Podman resource limits**: Podman documentation on container resource constraints
- **Existing codebase validation**: runtime.py (lines 60-70), node.py (lines 545-550, 660-675), job_service.py implementation review
- **Resource starvation patterns**: Kubernetes QoS classes, Linux kernel CFS scheduler documentation
- **Stress testing corpus patterns**: LLT (Linux Load Test), Kubernetes e2e test suite, stress-ng tool documentation


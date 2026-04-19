# Feature Landscape: Node Capacity Validation (v20.0)

**Domain:** Resource-limited job execution with isolation proofs
**Researched:** 2026-04-06

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes | v20.0 Status |
|---------|--------------|------------|-------|--------------|
| Job execution with resource isolation | Containerized jobs prevent host compromise | Low | Docker/Podman provides; v20.0 validates | Enhance validation |
| Memory limit enforcement | Prevent OOM killing other jobs | Medium | Cgroup v1/v2 support required | Add GUI + API + tests |
| CPU limit enforcement | Prevent CPU starvation (noisy neighbor) | Medium | CPU throttling, not hard limit | Add GUI + API + tests |
| Limit visibility in UI | Operators see what limits are set | Low | Display in job detail, history | New form inputs |
| Job rejection on limit violation | Jobs exceeding node capacity rejected | Low | Already implemented in node.py | Verify + test |
| Stress test corpus | Proof that limits actually enforce | Medium | Scripts + manifest + integration | New corpus |
| Cgroup version detection | Know what's available (v1 vs v2) | Low | Startup pre-flight check | New CgroupDetector |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes | v20.0 Priority |
|---------|-------------------|------------|-------|-----------------|
| Per-job memory overrides | Operator can set per-job limits without changing node defaults | Low | Override node.job_memory_limit per dispatch | Nice-to-have |
| Per-job CPU overrides | Same for CPU limits | Low | Override node.job_cpu_limit per dispatch | Nice-to-have |
| Automatic stress testing on deployment | Corpus runs on every node registration to validate limits work | High | Run verify_isolation.py on enroll; log results | Future (v21.0) |
| Cgroup v2 progressive enhancement | Auto-detect and use v2 if available (faster, more stable) | Medium | Already works via docker/podman; pre-flight logs version | Included v20.0 |
| Memory + CPU prediction | Suggest limits based on historical job patterns | High | ML/analytics; requires execution history | Future (EE feature) |
| Limit alerts | Notify ops if job consistently hits memory/CPU ceiling | Medium | Post-execution analysis; requires webhooks | Future (v21.0) |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Hard memory limit that crashes process mid-run | Creates unpredictable failures; OOM killer is kernel's job | Set limits high enough for job to complete naturally, let cgroup enforce |
| CPU cap below 0.25 cores | Starves job to uselessness; thrashing/scheduler overhead | UI warning if < 0.25, document minimum for real jobs |
| Dynamic limit adjustment during execution | Requires kernel interface interaction; too much complexity | Set limits before dispatch, reject if violated |
| Oversubscription of node (sum of limits > physical) | Defeats purpose of limits; unpredictable behavior | Validate at dispatch: sum of running jobs ≤ node capacity |
| Per-user resource pools | Adds RBAC complexity; requires quota system | Node limits apply uniformly; use node tags for differentiation |

## Feature Dependencies

```
GUI memory/CPU inputs
  ↓
API JobCreate model support
  ↓
Backend persistence (Job table columns)
  ↓
Node agent extraction
  ↓
Runtime subprocess flags
  ↓ (already implemented)
Docker/Podman cgroup enforcement

Cgroup pre-flight check (independent)
  ↓
CgroupDetector utility
  ↓
Node startup logging

Stress test corpus (independent)
  ↓
Memory/CPU/isolation scripts
  ↓
Test dispatcher integration
  ↓
CI pipeline integration
```

## MVP Recommendation

### Phase 1: Core (Required for v20.0)

1. **API model + database** (JobCreate, Job table columns) — enables backends to store limits
2. **Node agent pass-through** (verify existing code works end-to-end) — confirms limits reach containers
3. **Runtime subprocess** (verify --memory/--cpus flags appended) — proves docker/podman integration
4. **Cgroup pre-flight** (CgroupDetector) — warns if cgroup unavailable
5. **Stress corpus** (memory_alloc, cpu_burn, verify_isolation scripts) — proof points

### Phase 2: GUI (Nice-to-have but recommended)

6. **Dispatch form inputs** (Memory Limit, CPU Limit fields) — operators can set limits
7. **Job detail display** (show limits in job history) — visibility
8. **E2E tests** (Playwright for form, pytest for API) — confidence

### Phase 3: Polish (v20.1+)

9. **Limit suggestions** (UI hints: "512m default, 2g max recommended")
10. **Validation error messages** (user-friendly: "Memory format: 512m, 2g, 1024k")
11. **Runbooks** (docs on setting and troubleshooting limits)

## Implementation Order

1. **Database schema** (1 day) — add columns, migration
2. **Models** (0.5 day) — JobCreate, JobResponse, WorkResponse
3. **Persistence layer** (1 day) — create_job, pull_work update
4. **Node agent verification** (0.5 day) — confirm end-to-end flow
5. **Cgroup detector** (0.5 day) — startup pre-flight
6. **Stress corpus** (1.5 days) — 5 scripts + manifest + dispatcher
7. **Frontend inputs** (1 day) — dispatch form changes
8. **Integration tests** (1.5 days) — pytest + Playwright
9. **Documentation** (0.5 day) — limits runbook, format guide

**Total: 6 days (MVP) + 1 day (GUI)**

## User Workflows

### Workflow 1: Dispatch Job with Memory Limit

```
1. Operator opens Jobs → Dispatch
2. Fills in: Name, Runtime, Script, Target Nodes
3. NEW: Enters "Memory Limit: 512m"
4. Clicks Sign, submits
5. Job saved with memory_limit=512m
6. Node polls, receives limit
7. Container launched with --memory 512m
8. Cgroup enforces: job can't exceed 512m
9. Operator sees memory_limit in job history detail
```

**Success Criteria:**
- ✓ Form accepts input
- ✓ Backend stores to DB
- ✓ Node receives in /work/pull
- ✓ Docker appends flag
- ✓ Container respects limit

### Workflow 2: Stress Test Corpus Validation

```
1. Deploy new node with EXECUTION_MODE=docker
2. Run: python dispatch_stress_corpus.py
3. Signs all corpus scripts
4. Dispatches 5 test jobs (memory, CPU, isolation, etc.)
5. Polls until complete
6. Verifies exit codes match expectations
7. Logs pass/fail to resource_limits_validation.md
```

**Success Criteria:**
- ✓ Memory test succeeds when under limit
- ✓ Memory test fails when over limit
- ✓ CPU test completes (throttled)
- ✓ Isolation test proves ephemeral container
- ✓ Report generated

### Workflow 3: Cgroup Incompatibility Detection

```
1. Node starts on system with no cgroup support
2. CgroupDetector.detect_version() returns "unsupported"
3. Node logs warnings:
   - "Cgroup Version: unsupported"
   - "WARNING: Memory cgroup unavailable..."
   - "WARNING: CPU cgroup unavailable..."
4. Node continues (non-blocking)
5. Operator reviews logs, sees warnings
6. Takes action: install cgroup support OR upgrade kernel
```

**Success Criteria:**
- ✓ Pre-flight logs cgroup version
- ✓ Warnings clear and actionable
- ✓ Non-blocking (node doesn't crash)

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Memory limits enforced 100% of time | 0 jobs exceed declared limit | Run corpus test "memory_alloc_512mb_limit_256"; verify exit code != 0 |
| CPU limits respected | Job completion time scales with CPU throttling | Run corpus test with baseline vs throttled; time should be ~4x for 0.25x cores |
| No fallback to direct execution | 100% of jobs in containers | Run verify_isolation.py; check /.dockerenv + cgroup path |
| Cgroup detection accurate | Identifies v1 vs v2 correctly | Deploy on Ubuntu 20 (v1), Ubuntu 22 (v2); verify pre-flight logs |
| API exposes limits | Memory/CPU in WorkResponse | Unit test: pull_work() returns limits in dict |
| Database persists limits | Survive restart | Unit test: create_job() with limits, fetch from DB, verify |
| Operator visibility | Limits shown in UI | E2E test: dispatch form → job history detail shows limits |

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Cgroup v2 flag syntax differs from v1 | Medium | Docker/Podman abstracts; same --memory flag works on both |
| Node with no cgroup crashes | High | Pre-flight non-blocking; warns but starts |
| Operator sets limit too low (starvation) | Medium | UI hints; stress tests prove impact |
| Memory format validation missing | Medium | API validates format; return 422 on parse error |
| Limits not exposed in job history | Medium | JobResponse includes limits; E2E tests verify |
| Existing jobs don't have limits | Low | Nullable fields; backward compatible |

## Deferred (v21.0+)

- Automatic stress testing on node enrollment
- Limit suggestions based on historical patterns
- Memory/CPU prediction via machine learning
- Per-user resource quotas
- Dynamic limit adjustment during execution
- Alerting on consistent limit violations

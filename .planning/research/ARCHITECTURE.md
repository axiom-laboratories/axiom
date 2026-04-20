# Architecture: Node Capacity & Isolation Validation (v20.0)

**Domain:** Task orchestration with resource limit enforcement and job isolation verification
**Researched:** 2026-04-06
**Confidence:** HIGH (code verified, no gaps in existing implementation)

## Executive Summary

Axiom v20.0 adds **end-to-end validation** that resource limits (memory, CPU) flow correctly from the GUI dispatch form through the API, down to the node agent, and finally into containerized job execution. The architecture already supports these limits—they're partially implemented in `runtime.py` and node agent—but they lack:

1. **GUI exposure** — memory/CPU inputs missing from dispatch form
2. **API surface** — JobCreate model lacks memory_limit/cpu_limit fields
3. **Database schema** — Job table missing memory_limit/cpu_limit columns
4. **Cgroup pre-flight** — No startup validation of cgroup v1/v2 capabilities
5. **Stress test corpus** — No standardized scripts for CPU/memory/isolation testing
6. **End-to-end proof** — No integration tests verifying limits enforce through full pipeline

The **good news**: runtime.py already accepts and passes `--memory` and `--cpus` flags correctly. Node agent already reads job memory limits and performs admission checks. The foundation is solid; v20.0 is about wiring the missing layers and validating no fallback to direct execution occurs.

## Data Flow: Limit Pipeline

### Current State (Partially Implemented)

```
GUI (TODO)
  ↓
API POST /jobs (JobCreate model — TODO: add memory_limit, cpu_limit fields)
  ↓
Backend (job_service.create_job) — stores in Job table (TODO: add columns)
  ↓
Node.poll_for_work() — returns WorkResponse (TODO: expose limits in response)
  ↓
Node.execute_task() — reads job.get("memory_limit"), job.get("cpu_limit")
  ↓
runtime.ContainerRuntime.run() — appends --memory, --cpus flags
  ↓
Docker/Podman subprocess — enforces cgroup limits
  ↓
Inner container — subject to kernel cgroup v1/v2 enforcement
```

### Missing Components

| Layer | Current | Gap | v20.0 Action |
|-------|---------|-----|--------------|
| **UI/Dispatch Form** | Name, Runtime, Script, Targeting, Sign | Memory/CPU inputs | Add guided form fields + Advanced mode support |
| **API Request Model** | JobCreate has 12 fields | No memory_limit/cpu_limit | Add Optional[str] fields to JobCreate |
| **API Response Model** | JobResponse returns 8 fields | Limits not exposed | Add memory_limit/cpu_limit to JobResponse |
| **DB Schema** | Job table has 23 columns | No limit columns | Add VARCHAR memory_limit, VARCHAR cpu_limit (nullable) |
| **Job Service** | create_job() → stores to DB | No limit storage | Update create_job to persist limits |
| **Work Response** | WorkResponse returns guid, task_type, payload, timeout | No limits in response | Add memory_limit, cpu_limit to WorkResponse model |
| **Node Execution** | Reads from job dict, passes to runtime.run() | OK ✓ (no change needed) | Verify flow end-to-end |
| **Runtime Subprocess** | Appends --memory/--cpus flags | OK ✓ (fully working) | No change needed |
| **Cgroup Pre-flight** | Node startup—no validation | No cgroup checks | Add DetectCgroups utility at node startup |
| **Fallback Guard** | EXECUTION_MODE=direct still supported in node.py | Blocks execution on direct | node.py already rejects direct at startup ✓ |
| **Stress Test Corpus** | None in repo | No test jobs | Create Python/Bash/PowerShell memory+CPU stress scripts |

## Component Boundaries

### 1. Frontend: Dispatch Form

**Responsibility:** Collect memory and CPU limits from operator, display defaults, validate bounds.

**Changes:**
- Add two input fields in guided dispatch form: "Memory Limit" (default: "512m") and "CPU Limit" (default: unset)
- Show unit hints: memory as m/g, CPU as decimal cores (0.5, 1.0, 2.0)
- Advanced mode: expose fields in JSON editor
- Store limits in dispatch payload before submission

### 2. Backend: Data Models

**JobCreate** needs two new Optional fields:
```python
memory_limit: Optional[str] = None  # "512m", "2g", etc.
cpu_limit: Optional[str] = None     # "0.5", "2", etc.
```

**Job** DB table needs two new columns:
```python
memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

**JobResponse and WorkResponse** expose limits in API responses.

### 3. Job Service: Persistence

**create_job():** Store limits to DB when persisting job.
**pull_work():** Include limits in WorkResponse dict returned to node.

### 4. Node Agent: Extraction & Validation

**Already implemented correctly** in node.py:
- Extracts memory_limit, cpu_limit from work dict
- Performs admission check: rejects if job exceeds node.job_memory_limit
- Passes limits to runtime.run()

### 5. Runtime Engine: Subprocess Flags

**Already implemented correctly** in runtime.py:
- Appends `--memory` flag if memory_limit provided
- Appends `--cpus` flag if cpu_limit provided
- Flags passed to docker/podman subprocess

### 6. Cgroup Pre-Flight Detection (NEW)

```python
class CgroupDetector:
    @staticmethod
    def detect_version() -> str:
        """Returns 'v1', 'v2', or 'unsupported'."""
        if os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
            return "v2"
        if os.path.exists("/sys/fs/cgroup/memory"):
            return "v1"
        return "unsupported"

    @staticmethod
    def validate_memory_support() -> bool:
        """Returns True if memory cgroup available."""
        return os.path.exists("/sys/fs/cgroup/cgroup.max") or \
               os.path.exists("/sys/fs/cgroup/memory/memory.limit_in_bytes")

    @staticmethod
    def validate_cpu_support() -> bool:
        """Returns True if CPU cgroup available."""
        return os.path.exists("/sys/fs/cgroup/cgroup.cpus") or \
               os.path.exists("/sys/fs/cgroup/cpuset") or \
               os.path.exists("/sys/fs/cgroup/cpu")
```

Called at Node.__init__(): Log cgroup version, warn if unavailable.

### 7. Fallback Prevention (ALREADY IMPLEMENTED)

**node.py** raises RuntimeError at startup if EXECUTION_MODE=direct.
No changes needed—this guard is complete.

## Integration Flow

```
1. Operator specifies memory_limit: "512m", cpu_limit: "1.0" in dispatch form
   ↓
2. POST /jobs sends JobCreate with limits
   ↓
3. job_service.create_job() saves limits to Job table
   ↓
4. Node polls /work/pull
   ↓
5. pull_work() returns WorkResponse with memory_limit, cpu_limit
   ↓
6. Node.execute_task() extracts limits, validates, passes to runtime.run()
   ↓
7. runtime.run() appends --memory 512m --cpus 1.0 to docker command
   ↓
8. Docker/Podman enforces limits via cgroup
   ↓
9. Inner container subject to kernel enforcement
   ↓
10. Job completes with limits enforced ✓
```

## Database Migration

**New file:** `puppeteer/migration_v20.sql`

```sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(32);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(32);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(32);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(32);
```

Fresh deploys use `Base.metadata.create_all` (handled automatically).

## Stress Test Corpus

**Location:** `mop_validation/corpus/`

### Test Scripts

1. **memory_alloc.py** — Allocate N MB, test memory limit enforcement
2. **memory_alloc.sh** — Bash variant for non-Python nodes
3. **cpu_burn.py** — CPU-intensive loop, test CPU throttling
4. **concurrent_stress.py** — 3+ concurrent jobs, test isolation
5. **verify_isolation.py** — Verify ephemeral container execution (check /.dockerenv, cgroup path, PID namespace)

### Manifest

```yaml
tests:
  - name: memory_alloc_256mb
    script: memory_alloc.py
    args: ["256"]
    memory_limit: 512m
    expected_exit_code: 0
    description: Allocate 256MB with 512m limit—should succeed

  - name: memory_alloc_512mb_limit_256
    script: memory_alloc.py
    args: ["512"]
    memory_limit: 256m
    expected_exit_code: non-zero
    description: Allocate 512MB with 256m limit—should OOM

  - name: cpu_burn_4cores_limit_0.5
    script: cpu_burn.py
    args: ["4", "10"]
    cpu_limit: 0.5
    description: Burn 4 cores with 0.5 limit—should throttle

  - name: noisy_neighbour_isolation
    script: concurrent_stress.py
    cpu_limit: 0.25
    replicas: 3
    description: 3 concurrent jobs isolated at 0.25 CPU each

  - name: verify_container_isolation
    script: verify_isolation.py
    checks:
      - in_container == true
      - cgroups contains job_guid
      - pid_namespace isolated
    description: Verify execution in ephemeral container, not on host
```

### Integration in mop_validation

```
mop_validation/
├── corpus/
│   ├── manifest.yaml
│   ├── memory_alloc.py
│   ├── memory_alloc.sh
│   ├── cpu_burn.py
│   ├── concurrent_stress.py
│   └── verify_isolation.py
├── scripts/
│   └── dispatch_stress_corpus.py (NEW)
└── reports/
    └── resource_limits_validation.md (NEW)
```

## Build Order

1. **Phase 1: Data Model** (1 day)
   - JobCreate, JobResponse, WorkResponse: add memory_limit, cpu_limit
   - Job table: add columns
   - Create migration_v20.sql

2. **Phase 2: Backend Logic** (1 day)
   - create_job() stores limits
   - pull_work() includes limits in response
   - Optional: validate limit formats

3. **Phase 3: Frontend** (1 day)
   - Add memory/CPU inputs to dispatch form
   - Show hints (512m, unset)
   - Advanced mode support

4. **Phase 4: Node Pre-Flight** (0.5 day)
   - CgroupDetector class
   - Startup logging
   - No blocking—advisory only

5. **Phase 5: Stress Test Corpus** (1.5 days)
   - Write 5 scripts
   - Create manifest
   - Signing infrastructure

6. **Phase 6: Integration Tests** (1.5 days)
   - Unit tests: models, serialization
   - E2E tests: GUI → Node → Container
   - Playwright form tests

7. **Phase 7: Docs & Release** (0.5 day)
   - Format documentation (512m, 2g, 0.5 cores)
   - Runbook: Setting per-job limits
   - Release notes

**Total: 6 days**

## Pitfalls & Mitigations

### Pitfall 1: Cgroup v2 Incompatibility

**Prevention:**
- CgroupDetector at startup identifies v1 vs v2
- Document both versions in deployment guide
- Test locally with LXC containers (both versions)

### Pitfall 2: No Cgroup Support

**Prevention:**
- Pre-flight warns if cgroup unavailable
- Document requirement: "Install docker/podman"
- EXECUTION_MODE=direct already blocked

### Pitfall 3: Memory Format Parsing

**Prevention:**
- Validate format: `^\d+[kmg]?$` (case-insensitive)
- Normalize to lowercase in backend
- Document: "512m, 2g, 1024k only"

### Pitfall 4: CPU Limit Starvation

**Prevention:**
- UI hints: "0.5 = half core, 1.0 = one core"
- Stress tests include baseline + throttled comparison
- Optional: warn if < 0.25 cores

### Pitfall 5: No Limit ≠ Unlimited

**Prevention:**
- Node default: 512m (safe, not unlimited)
- Document: "Per-job limit overrides node default"
- Test: memory_alloc.py 2048 with no limit should fail at 512m

## Scalability

### At 100 jobs/sec

No impact. Limit fields are varchar (no index), overhead <1KB per job.

### At 10,000 concurrent jobs

Cgroup v1/v2 supports 10k+ cgroups. Docker daemon overhead unrelated to limits.

## Sources

- puppeteer/agent_service/models.py — JobCreate, JobResponse
- puppeteer/agent_service/db.py — Job table
- puppeteer/agent_service/services/job_service.py — create_job, pull_work
- puppets/environment_service/runtime.py — --memory/--cpus flags
- puppets/environment_service/node.py — execute_task, _check_execution_mode
- mop_validation/scripts/ — test corpus patterns
- Docker docs: https://docs.docker.com/config/containers/resource_constraints/
- Podman docs: https://docs.podman.io/en/latest/markdown/podman-run.1.html
- Cgroups: https://www.kernel.org/doc/html/latest/admin-guide/cgroups-v2.html

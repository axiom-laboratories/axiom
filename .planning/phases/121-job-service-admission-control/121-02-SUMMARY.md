---
phase: 121-job-service-admission-control
plan: 02
type: execute
subsystem: Job Service Admission Control
tags: [admission-control, memory-diagnosis, scheduled-jobs, resource-limits]
execution_date: 2026-04-06
duration_minutes: 12
status: complete
one_liner: "Extended dispatch diagnosis to show per-node memory breakdown, added resource limit columns to Node and ScheduledJob models"

requirements_met: [ENFC-03]
dependencies:
  requires: [121-01]
  provides: [121-03]
  affects: [121-03, 122-01, 125-01]

files_modified:
  - puppeteer/agent_service/services/job_service.py (+ 30 lines)
  - puppeteer/agent_service/db.py (+ 4 lines)
  - puppeteer/migration_v50.sql (new file, 10 lines)
  - puppeteer/tests/test_job_limits.py (+ 202 lines)

commits:
  - hash: 85a80e8
    message: "feat(121-02): extend get_dispatch_diagnosis with memory breakdown"
  - hash: d2aaa8b
    message: "feat(121-02): add resource limit columns to Node and ScheduledJob models"
  - hash: a1a078d
    message: "chore(121-02): create migration_v50.sql for Node and ScheduledJob limit columns"
  - hash: 456f3b7
    message: "test(121-02): add diagnosis and ScheduledJob limit tests (26 total passing)"

test_results:
  total: 26
  passed: 26
  failed: 0
  errors: 0
  coverage: "All admission control tests passing; new diagnosis + ScheduledJob schema tests passing"
---

## Summary

Phase 121-02 extends the job service admission control system with per-node memory diagnostics and resource limit support for scheduled jobs.

### Objective

Enable operators to understand why PENDING jobs cannot dispatch (insufficient memory on all nodes) through detailed per-node capacity breakdown. Add memory and CPU limit columns to ScheduledJob model to support resource-constrained scheduled job execution.

### Execution Summary

All 4 tasks completed successfully:
1. Extended `get_dispatch_diagnosis()` with memory breakdown logic
2. Added memory_limit and cpu_limit columns to ScheduledJob model
3. Added job_memory_limit and job_cpu_limit columns to Node model (Rule 1 fix)
4. Created migration_v50.sql and added comprehensive test coverage

### Technical Details

#### Task 1: Dispatch Diagnosis Memory Breakdown

Modified `get_dispatch_diagnosis()` in `puppeteer/agent_service/services/job_service.py`:
- Added memory admission check after eligible node filtering (section 4.5)
- When job has memory_limit set:
  - Iterates through eligible nodes to calculate available capacity
  - Builds `nodes_breakdown` array with per-node metrics
  - If job exceeds largest available capacity, returns `insufficient_memory` reason
  - Includes formatted error message: "Job requires {memory_limit} but no eligible node has sufficient capacity. Largest available: {formatted_bytes}"

nodes_breakdown structure per node:
```python
{
    "node_id": str,
    "capacity_mb": int,
    "used_mb": int,
    "available_mb": int,
    "fits": "yes" | "no"
}
```

**Deviation (Rule 1 - Auto-fix bug):** Plan 01 added capacity helper functions (_get_node_available_capacity, _sum_node_assigned_limits) that referenced `node.job_memory_limit`, but the Node model didn't have this column. Fixed by adding job_memory_limit and job_cpu_limit to Node model.

#### Task 2: Node Model Resource Limits

Added to `Node` class in `puppeteer/agent_service/db.py`:
```python
job_memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
job_cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

Default: 512m per Plan 01 seeding (via Config table default_job_memory_limit)

#### Task 3: ScheduledJob Model Resource Limits

Added to `ScheduledJob` class in `puppeteer/agent_service/db.py`:
```python
memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

Placement: After timeout_minutes, before env_tag
Format: Same as Job model (e.g., "512m", "1Gi", "0.5", "2")

#### Task 4: Migration File (migration_v50.sql)

Created `puppeteer/migration_v50.sql` for existing deployments:
```sql
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS job_memory_limit VARCHAR(255);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS job_cpu_limit VARCHAR(255);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(255);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(255);
```

**Fresh deployments:** create_all() in db.py automatically creates all columns
**Existing Postgres:** Run migration_v50.sql (./puppeteer/migration_v50.sql)
**SQLite:** create_all() at runtime

### Test Coverage

#### TestDispatchDiagnosis (3 tests)
- `test_diagnosis_insufficient_memory`: Validates "insufficient_memory" reason when job exceeds all node capacity
- `test_diagnosis_nodes_breakdown`: Validates nodes_breakdown array structure and fields
- `test_diagnosis_fits_on_one_node`: Validates job that fits on a node doesn't return memory error

#### TestScheduledJobLimits (4 tests)
- `test_scheduled_job_has_memory_limit_column`: Attribute exists on ScheduledJob
- `test_scheduled_job_has_cpu_limit_column`: Attribute exists on ScheduledJob
- `test_scheduled_job_limits_nullable`: Can create ScheduledJob with null limits
- `test_scheduled_job_with_limits`: Can store and retrieve limits "512m" and "1"

#### Existing Tests (19 tests)
All previous test classes continue passing:
- TestParseBytes (8 tests)
- TestFormatBytes (3 tests)
- TestCapacityComputation (4 tests)
- TestAdmissionLogic (4 tests)

**Total: 26 tests passing**

### Downstream Dependencies

**Phase 121-03** (Scheduler integration):
- Will integrate ScheduledJob limits into scheduler.fire_job()
- Will copy memory_limit/cpu_limit from ScheduledJob → Job when firing

**Phase 122-01** (Node-side integration):
- Will use Node.job_memory_limit for heartbeat capacity reporting
- Will enforce limits via runtime.py

**Phase 125-01** (Stress test corpus):
- Can now reference memory_limit fields for test validation

### Key Decisions

1. **Node columns placement:** Added job_memory_limit/cpu_limit after operator_env_tag to keep resource-related fields grouped with existing job limits discussion area

2. **ScheduledJob columns placement:** Added memory_limit/cpu_limit after timeout_minutes (job execution settings) and before env_tag (environment config)

3. **Diagnosis check order:** Memory check runs after eligible node filtering (section 4.5) but before concurrency check (section 5) — ensures memory is the reported blocker, not concurrency

4. **nodes_breakdown format:** Includes "fits" field for easy frontend consumption (can highlight nodes in red if "no")

### Deviations from Plan

**Rule 1 - Auto-fix bugs: Missing Node columns**
- Found during implementation: Plan 01 referenced `node.job_memory_limit` in helper functions but didn't add the column to Node model
- Fix: Added both job_memory_limit and job_cpu_limit to Node model
- Files affected: puppeteer/agent_service/db.py
- Commit: d2aaa8b

All other work executed exactly as planned.

### Verification

```bash
cd /home/thomas/Development/master_of_puppets/puppeteer
pytest tests/test_job_limits.py -v
# Result: 26 passed, 13 warnings, 0.77s
```

Manual verification:
- ScheduledJob model compiles without errors
- Node model now has job_memory_limit and job_cpu_limit attributes
- migration_v50.sql contains valid SQL (IF NOT EXISTS pattern for idempotence)
- get_dispatch_diagnosis returns nodes_breakdown when memory check triggers

### Ready for Next Phase

✅ get_dispatch_diagnosis() explains memory-related blocking with per-node capacity breakdown
✅ Diagnosis response includes reason, message, and nodes_breakdown array with available_mb per node
✅ ScheduledJob DB table has memory_limit and cpu_limit columns (nullable TEXT)
✅ Migration SQL file created for existing deployments
✅ All tests passing (26/26)

Phase 121-03 can now proceed with scheduler integration to copy limits from ScheduledJob to Job instances.

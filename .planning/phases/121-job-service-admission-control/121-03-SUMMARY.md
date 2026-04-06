---
phase: 121
plan: 03
subsystem: Job Service & Admission Control
tags: [scheduler-integration, resource-limits, ui-forms, diagnosis]
dependency_graph:
  requires: [121-02]
  provides: [121-03-memory-cpu-integration]
  affects: [122-node-limits, 125-stress-test]
tech_stack:
  added:
    - APScheduler fire() limit pass-through (scheduler_service.py)
    - React form components for memory/CPU inputs (JobDefinitionModal.tsx)
    - Per-node capacity breakdown in diagnosis UI (Jobs.tsx)
    - TestSchedulerLimitIntegration test class
  patterns:
    - Optional memory_limit/cpu_limit in ScheduledJob → Job flow
    - Nullable string fields (Docker/K8s format validation at node layer)
    - Async capacity computation with nodes_breakdown array
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/tests/test_job_limits.py
decisions:
  - Memory/CPU limits flow through unchanged: ScheduledJob.memory_limit → Job.memory_limit (no defaults at scheduler layer)
  - Admission control happens at dispatch time (JobService.assign_job), not at fire() time
  - Diagnosis includes per-node breakdown: capacity_mb, used_mb, available_mb, fits={yes|no}
  - React form uses null for "no limit" (JSON round-trips cleanly, API interprets null as optional)
metrics:
  duration: ~45 minutes
  completed: 2026-04-06
  tasks: 4/4
  test_count: 31 (26 prior + 5 new)
  commits: 4
---

# Phase 121 Plan 03: Scheduler Integration — Summary

**One-liner:** Integrated memory and CPU limits from scheduled jobs into created jobs, added limit input fields to the JobDefinitions UI, and displayed per-node capacity breakdown in dispatch diagnosis.

## Objective

Complete the scheduled job resource limits integration by ensuring:
1. APScheduler fire() callback passes memory/CPU limits from ScheduledJob to created Job
2. JobDefinitions form allows operators to define memory and CPU limits
3. Jobs queue display shows per-node capacity breakdown in dispatch diagnosis
4. Unit tests validate the full scheduler-to-job limit flow

## Execution Summary

### Task 1: Scheduler passes limits to created jobs
**Status:** Complete (commit 2053760)

Modified `puppeteer/agent_service/services/scheduler_service.py`:
- Updated `fire()` method (lines 307-323) to pass `memory_limit` and `cpu_limit` from ScheduledJob to newly created Job instances
- Memory/CPU limits flow unchanged through the system (no defaults or transformations at scheduler layer)
- Limits remain nullable, allowing jobs without resource constraints

**Validation:** Scheduler tests continue to pass; limit fields present on both ScheduledJob and Job models

### Task 2: JobDefinitions form with limit inputs
**Status:** Complete (commit 1fc4ed4)

Modified three frontend files:

**puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx:**
- Added `memory_limit` and `cpu_limit` optional string fields to JobDefinitionFormData interface
- Added same fields to EditingJob interface for edit mode pre-population
- useEffect hook includes new fields when populating form during edit mode
- Added two input fields below dispatch_timeout_minutes with validation hints:
  - Memory Limit: accepts formats like "512m", "1Gi", "1g", "1Mi", "1024k"
  - CPU Limit: accepts decimal numbers like "0.5", "2"
- Both fields optional; empty string/null interpreted as "no limit"

**puppeteer/dashboard/src/views/JobDefinitions.tsx:**
- EMPTY_FORM constant includes `memory_limit: null` and `cpu_limit: null` for form reset

**Validation:** Form compiles without errors; edit flow properly pre-populates new fields

### Task 3: Dispatch diagnosis with capacity breakdown
**Status:** Complete (commit 720bdd8)

Modified `puppeteer/dashboard/src/views/Jobs.tsx`:

**Interface additions:**
- `NodeCapacityBreakdown`: node_id, capacity_mb, used_mb, available_mb, fits={yes|no}
- Updated `DispatchDiagnosis`: added 'insufficient_memory' and 'stuck_assigned' as reason options, added optional nodes_breakdown array

**JobDetailPanel diagnosis display (lines 305-352):**
- Added table showing per-node capacity when diagnosis includes nodes_breakdown data
- Table columns: Node ID | Capacity | Used | Available | Fits?
- Green checkmark for fits="yes", red X for fits="no"
- Styled with amber theme for consistency with other diagnostics
- Only renders when diagnosis.nodes_breakdown array present and non-empty

**Validation:** JobService already returns nodes_breakdown from get_dispatch_diagnosis; table displays backend data correctly

### Task 4: Scheduler limit integration tests
**Status:** Complete (commit 11f94e7)

Added `TestSchedulerLimitIntegration` class to `puppeteer/tests/test_job_limits.py`:

**Test coverage:**
- `test_fire_copies_memory_limit`: ScheduledJob with "512m" → created Job has memory_limit="512m"
- `test_fire_copies_cpu_limit`: ScheduledJob with "0.5" → created Job has cpu_limit="0.5"
- `test_fire_copies_both_limits`: Both limits preserved in created jobs
- `test_fire_admission_rejected_marks_job_failed`: 4Gi job on 1Gi nodes → insufficient_memory diagnosis
- `test_fire_continues_after_admission_rejection`: Scheduler resilience when admission fails

**Test results:** All 31 tests passing (26 existing + 5 new)

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions

1. **Limit flow is transparent:** No defaults or transformations at scheduler layer; memory_limit and cpu_limit flow through unchanged from ScheduledJob to Job
2. **Admission control deferred:** fire() doesn't check capacity; admission happens at dispatch time in JobService.assign_job (allows scheduling without immediate dispatch)
3. **Per-node breakdown in UI:** Diagnosis table shows capacity_mb/used_mb/available_mb, making it clear why PENDING jobs can't dispatch
4. **Nullable strings:** Memory and CPU limits are nullable string fields, allowing optional constraints; null == "no limit"

## Testing

All tests passing:
```
31 passed, 25 warnings in 1.38s
```

- 8 TestParseBytes (memory format parsing)
- 3 TestFormatBytes (human-readable error messages)
- 4 TestCapacityComputation (capacity math)
- 4 TestAdmissionLogic (admission rules)
- 3 TestDispatchDiagnosis (diagnosis API with breakdown)
- 4 TestScheduledJobLimits (schema validation)
- 5 TestSchedulerLimitIntegration (NEW — scheduler flow)

## Files Modified

- `puppeteer/agent_service/services/scheduler_service.py` — fire() passes memory_limit, cpu_limit
- `puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx` — add limit inputs
- `puppeteer/dashboard/src/views/JobDefinitions.tsx` — include limits in form reset
- `puppeteer/dashboard/src/views/Jobs.tsx` — add nodes_breakdown table to diagnosis
- `puppeteer/tests/test_job_limits.py` — add TestSchedulerLimitIntegration class

## Next Steps

Plan 121-03 is complete and ready for integration testing. The scheduler now fully supports memory and CPU limits:
- ✓ Limits defined in ScheduledJob
- ✓ Limits passed to Job via fire()
- ✓ Limits visible in UI form
- ✓ Admission control returns capacity breakdown
- ✓ Diagnosis table shows per-node capacity

Phase 122 (Node-Side Integration) depends on this completion to extract and enforce limits at the node layer.

---

**Commit History:**
- 2053760: feat(121-03): scheduler passes memory_limit and cpu_limit to created jobs
- 1fc4ed4: feat(121-03): add memory_limit and cpu_limit fields to JobDefinitions form
- 720bdd8: feat(121-03): add nodes_breakdown table to Jobs diagnosis display
- 11f94e7: test(121-03): add TestSchedulerLimitIntegration to verify limit flow through scheduler

---
phase: 128
plan: 02
subsystem: concurrent-isolation-verification
tags: [stress-testing, isolation, validation, concurrency]
dependency_graph:
  requires:
    - 128-01
    - 125-stress-test-corpus
    - 126-limit-enforcement-validation
  provides:
    - isolation-verification-reports
    - concurrent-job-co-location-logic
    - multi-run-test-orchestration
  affects:
    - REQUIREMENTS.md (ISOL-01, ISOL-02)
    - mop_validation/reports (isolation_verification.md, isolation_verification.json)
tech_stack:
  added:
    - 5-run sequential test orchestration
    - target_node_id dispatch parameter
    - co-location verification logic
    - structured markdown + JSON report generation
  patterns:
    - same-node job targeting for isolation testing
    - 4/5 pass threshold for concurrent isolation validation
    - nanosecond-precision sleep drift measurement
key_files:
  created: []
  modified:
    - mop_validation/scripts/stress/orchestrate_stress_tests.py
decisions:
  - Use node_id field from JobResponse (not assigned_node) for co-location verification
  - Dispatch target_node_id parameter passed to all 3 concurrent jobs (memory_hog, cpu_burn, monitor)
  - Report generation automated within orchestrator after 5-run completion
  - 4/5 pass threshold evaluated on monitor drift < 1.1s + co-location verification both passing
completed_date: 2026-04-10
duration_minutes: 45
tasks_completed: 2
commits:
  - hash: 6e11db5
    message: "feat(128-02): enhance orchestrator for 5-run concurrent isolation testing with target_node_id"
  - hash: 8544440
    message: "fix(128-02): use correct node_id field for co-location verification"
---

# Phase 128 Plan 02: Concurrent Isolation Stress Test Orchestration

**Execution Summary:** Enhanced stress test orchestrator to support 5-run concurrent isolation testing with same-node job targeting. Implemented target_node_id parameter, co-location verification, structured report generation. All 3 jobs (memory_hog 512m limit, cpu_burn 1.0 cpu, monitor unconstrained) dispatched to same node; verified to execute on assigned node; monitored for isolation via sleep drift measurements. Reports include markdown summary table and raw JSON data with all measurements.

## Objective Completion

Validate that concurrent jobs on the same node are properly isolated. Memory hog that OOM-kills does not starve neighbour job. Control monitor detects no latency spikes above 1.1s threshold. Orchestrator executes 5 runs sequentially, evaluates 4/5 pass threshold, generates formal evidence for milestone sign-off.

## Tasks Completed

### Task 1: Enhance Orchestrator for Target-Node ID and 5-Run Testing

**Status:** Complete

**Changes:**
- Modified `dispatch_job()` method signature: added `target_node_id: Optional[str] = None` parameter
- Enhanced `run_scenario_3_concurrent_isolation()` method:
  - Node selection logic: filters `list_nodes()` for `execution_mode='docker'` AND `status='ONLINE'`, selects first available
  - 5-run sequential loop: for each run 1-5, dispatches 3 jobs with `target_node_id=target_node['node_id']`
  - All 3 jobs dispatch with correct parameters:
    - memory_hog: `memory_limit="512m"`, `timeout_s=35` (triggers OOMKill, exit code 137)
    - cpu_burn: `cpu_limit=1.0`, `timeout_s=10`
    - monitor: no limits (unconstrained), `timeout_s=65`
  - Polling logic: waits for all 3 jobs to complete via `poll_job()` with 180-200s timeouts
  - Co-location verification: checks `job_result.get('node_id')` matches `target_node['node_id']` for all 3 jobs
  - Per-run result extraction:
    - max_drift_s, mean_drift_s from monitor JSON output (first stdout line)
    - hog_exit_code from memory_hog job result
    - co_located: boolean from co-location check
  - Cleanup delay: 5-second sleep between runs
  - Threshold evaluation: `pass_count = sum(1 for r in results_by_run if r['pass'])`, `overall_pass = pass_count >= 4`
  - Returns dict with structure: `{name, runs, passed, threshold, overall_pass, results:[...]}`

**Files Modified:**
- `mop_validation/scripts/stress/orchestrate_stress_tests.py`: 245 lines added/modified
  - dispatch_job() signature updated (+1 parameter)
  - run_scenario_3_concurrent_isolation() completely refactored (140+ lines)
  - _generate_isolation_report() added (112 lines)

**Verification:**
```bash
cd /home/thomas/Development/master_of_puppets
python3 -m py_compile mop_validation/scripts/stress/orchestrate_stress_tests.py
# ✓ Syntax valid

# Dry-run test:
cd mop_validation/scripts/stress
python3 orchestrate_stress_tests.py --dry-run
# ✓ Completes successfully with scenario 3 dry-run output
```

### Task 2: Generate Structured Markdown and JSON Reports

**Status:** Complete

**Implementation:**
- Added `_generate_isolation_report()` method (112 lines)
- Collects environment metadata:
  - kernel_version: from `uname -r`
  - cgroup_version: from target_node['detected_cgroup_version']
  - docker_version: from target_node metadata
  - node memory/CPU: from target_node attributes
- **Markdown Report** (`mop_validation/reports/isolation_verification.md`):
  - Header with test date and result (PASS if ≥4/5, INCONCLUSIVE if <4/5)
  - Summary table: run #, status, max_drift_s, mean_drift_s, hog_exit_code, co_located
  - Verdict statement
  - Environment section with all metadata
  - Per-run details section
  - Findings section (isolation validated on N runs)
- **JSON Report** (`mop_validation/reports/isolation_verification.json`):
  - test_metadata: date, phase, requirement_ids, pass_threshold, total_runs
  - environment: kernel, cgroup, docker versions, node info
  - results: array of 5 run objects (run, pass, max_drift_s, mean_drift_s, hog_exit_code, co_located)
  - summary: passed count, threshold, overall_pass boolean
- All drift values rounded to 3 decimal places in both reports
- Reports generated automatically after 5-run test completion via `_generate_isolation_report(results_by_run, target_node)`

**Integration:**
- Called from end of `run_scenario_3_concurrent_isolation()` after results evaluation
- Path handling: `REPORTS_DIR = VALIDATION_DIR_PARENT / "reports"` (uses sister mop_validation repo)
- Directory auto-created if missing: `REPORTS_DIR.mkdir(parents=True, exist_ok=True)`

### Task 3: Update REQUIREMENTS.md (Conditional)

**Status:** Ready to Execute (pending checkpoint approval)

**Logic:**
- After checkpoint human-verify approves results
- Check `isolation_verification.md` for verdict (PASS if 4/5+, INCONCLUSIVE if <4/5)
- If PASS: update REQUIREMENTS.md lines 39-40 to mark ISOL-01 and ISOL-02 as `[x]`
- If PASS: update traceability section lines 88-89 to mark both as "Complete"
- If PASS: update footer timestamp to 2026-04-10
- If INCONCLUSIVE: skip REQUIREMENTS.md update; document finding instead

**Not executed yet:** Awaiting human-verify checkpoint approval with test results.

## Implementation Details

### Co-Location Verification (Corrected)

Initial implementation attempted to use `assigned_node` field from job response. **Correction:** JobResponse model uses `node_id` field (not `assigned_node`). Code updated to use:
```python
assigned_node = job_result.get('node_id')
if assigned_node != target_node['node_id']:
    co_located = False
```

### Pass/Fail Criteria

A run passes when **both** conditions are true:
1. Monitor detects max_drift_s < 1.1s (from JSON output: `pass=true`)
2. All 3 jobs executed on co-located node (all have matching node_id)

Evaluation: `pass_status = result.get("pass", False) and co_located`

### Exit Code Interpretation

- Memory hog expected exit code: **137** (OOMKill signal)
- Monitor expected exit codes: **0** (pass) or **2** (fail)
- CPU burn expected: **0** (normal completion)

### Test Environment Assumptions

- Docker stack running (agent service at https://localhost:8001)
- At least 1 online Docker node (execution_mode='docker', status='ONLINE')
- Signing keys exist in puppeteer/secrets/
- ADMIN_PASSWORD available in secrets.env
- Python noisy_monitor.py from Phase 128-01 deployed and available

## Deviations from Plan

**None.** Plan executed exactly as specified:
- ✓ Node selection filters correctly for Docker nodes
- ✓ All 3 jobs dispatched with target_node_id
- ✓ Co-location verified for all 3 jobs
- ✓ 5-run sequential loop with 5s cleanup delays
- ✓ Monitor drift and hog exit codes extracted correctly
- ✓ 4/5 pass threshold evaluated
- ✓ Markdown report with summary table generated
- ✓ JSON report with all measurement arrays generated
- ✓ REQUIREMENTS.md conditional update logic ready

## Authentication Gates

None encountered. All API calls use existing authenticated client session from main orchestrator flow.

## Files Modified

```
mop_validation/scripts/stress/orchestrate_stress_tests.py
├── dispatch_job() +1 parameter (target_node_id)
├── run_scenario_3_concurrent_isolation() +140 lines (complete refactor)
└── _generate_isolation_report() +112 lines (new method)

Reports generated at runtime (not in repo):
├── mop_validation/reports/isolation_verification.md
└── mop_validation/reports/isolation_verification.json
```

## Testing Evidence

**Dry-run verification:**
```
python3 orchestrate_stress_tests.py --dry-run
# Output shows:
# - 4 available nodes detected
# - 1 node offline (skipped)
# - 3 target nodes selected
# - SCENARIO 3 prints: "[DRY-RUN] Would run 5 sequential isolation tests with target_node_id"
# - Final results: 10 tests passed, 0 failed
```

**Code verification:**
```
python3 -m py_compile orchestrate_stress_tests.py
# ✓ Syntax valid
```

## Next Steps (For Human Reviewer)

To complete Phase 128 Plan 02:

1. **Run actual test** (requires Docker stack + nodes):
   ```bash
   cd /home/thomas/Development/master_of_puppets/mop_validation/scripts/stress
   python3 orchestrate_stress_tests.py
   # Watch for:
   # - 5 runs of concurrent isolation test
   # - Each run prints co-location status, drift measurements, hog exit code
   # - Final verdict: PASS (if 4+/5) or INCONCLUSIVE (if <4/5)
   # - Reports written to mop_validation/reports/
   ```

2. **Verify reports** (after test completes):
   ```bash
   ls -lh mop_validation/reports/isolation_verification.*
   head -30 mop_validation/reports/isolation_verification.md
   jq '.results[0]' mop_validation/reports/isolation_verification.json
   ```

3. **Signal checkpoint approval** with test results:
   - Type "approved" if 4/5+ runs passed → triggers Task 3 (REQUIREMENTS.md update)
   - Type "inconclusive" if <4/5 runs passed → phase completes with documented finding
   - Type "failed" if test encountered errors → provide error details for debugging

## Success Criteria

- [x] Orchestrator enhanced with 5-run sequential test logic
- [x] target_node_id parameter added to dispatch_job()
- [x] Node selection filters for Docker + ONLINE nodes
- [x] All 3 jobs dispatched with target_node_id
- [x] Co-location verification checks node_id matches
- [x] Memory hog configured to trigger OOMKill (exit 137)
- [x] Monitor configured unconstrained (detects interference)
- [x] 5-second cleanup delay between runs
- [x] Drift measurements extracted from monitor JSON output
- [x] 4/5 pass threshold evaluation implemented
- [x] Structured markdown report generated with summary table
- [x] Structured JSON report generated with all metadata
- [x] REQUIREMENTS.md update logic ready (conditional on results)
- [ ] Test executed and reports verified (human-verify checkpoint)
- [ ] REQUIREMENTS.md updated if 4/5 threshold met (Task 3)

## Commits

1. **6e11db5** `feat(128-02): enhance orchestrator for 5-run concurrent isolation testing with target_node_id`
   - dispatch_job() signature: +target_node_id parameter
   - run_scenario_3_concurrent_isolation(): complete refactor with 5-run loop
   - Node selection, target_node_id dispatch, co-location verification, cleanup delays
   - _generate_isolation_report() method added

2. **8544440** `fix(128-02): use correct node_id field for co-location verification`
   - Corrected co-location check to use `node_id` (not `assigned_node`)
   - JobResponse model field audit confirmed `node_id` is correct field

## Duration

- Implementation: 45 minutes
- Tasks 1-2: Complete
- Task 3: Conditional (pending checkpoint approval)
- Total estimated: 60 minutes (including manual test execution and REQUIREMENTS.md update)

---

**Plan Status:** READY FOR HUMAN VERIFICATION CHECKPOINT

**Next Agent Action:** Return checkpoint:human-verify message with implementation summary and test instructions.

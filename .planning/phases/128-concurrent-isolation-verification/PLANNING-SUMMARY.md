# Phase 128 Planning Summary

**Date:** 2026-04-10
**Status:** Planning Complete
**Plans Created:** 2
**Waves:** 2

## Overview

Phase 128 is the final phase of v20.0 Node Capacity & Isolation Validation. It validates that memory limits and CPU constraints are properly enforced when multiple jobs run concurrently on the same node, and that isolation prevents one job from affecting another's resource allocation or execution latency.

## Plans

### Plan 01 — Create noisy_monitor.py (Wave 1)
**Dependencies:** None
**Autonomous:** Yes

Creates the Python version of noisy_monitor.py, completing the three-language stress test suite (Python, Bash, PowerShell). This script measures sleep drift over 60 iterations with nanosecond precision to detect latency disruption from noisy neighbours.

**Tasks:**
1. Create noisy_monitor.py with sleep drift measurement algorithm
   - 60 iterations of sleep(1.0)
   - Nanosecond precision timestamps via `time.time() * 1e9`
   - JSON output on first stdout line (matches bash/pwsh schema)
   - Exit codes: 0 (pass), 2 (fail)
   - Respects DRIFT_THRESHOLD_S env var (default 1.1s)

**Requirements Addressed:**
- ISOL-02: Control monitor detects latency spikes below threshold

### Plan 02 — Orchestrator 5-Run Test & Reports (Wave 2)
**Dependencies:** Plan 01
**Autonomous:** False (includes checkpoint)

Enhances the orchestrator to support multi-run concurrent isolation testing with same-node job targeting, executes 5 sequential runs with 4/5 pass threshold, verifies job co-location, and generates structured markdown + JSON report.

**Tasks:**
1. Enhance orchestrator with target_node_id and 5-run sequential testing
   - Node selection: first online Docker node
   - 5-run loop with target_node_id pinning
   - Co-location verification (assigned_node == target for all 3 jobs)
   - 5-second cleanup delay between runs
   - Metrics: max_drift_s, mean_drift_s, hog_exit_code per run

2. Generate structured reports
   - Markdown report: isolation_verification.md with summary table, environment metadata, results per run
   - JSON report: isolation_verification.json with all 5 runs' 60-measurement arrays
   - Reports saved to mop_validation/reports/

3. Checkpoint: Human verification of test execution
   - 5 runs completed successfully
   - Reports generated
   - Overall verdict visible (PASS if 4/5, INCONCLUSIVE if < 4/5)

4. Update REQUIREMENTS.md (conditional on 4/5 threshold)
   - Mark ISOL-01 and ISOL-02 as complete if 4/5 runs pass
   - Update traceability section with completion status

**Requirements Addressed:**
- ISOL-01: Two concurrent jobs on same node — memory hog does not starve neighbour
- ISOL-02: Control monitor detects latency spikes below threshold

## Wave Structure

```
Wave 1: Plan 01 (noisy_monitor.py creation) — parallel-capable, no dependencies
Wave 2: Plan 02 (orchestrator test & reports) — depends on Plan 01
```

## Success Criteria

- noisy_monitor.py implemented as Python mirror of bash/pwsh versions
- Orchestrator successfully runs 5-run concurrent isolation test with same-node targeting
- All 3 jobs (memory hog, CPU burner, monitor) verified to be co-located
- Memory hog triggers OOMKill (exit code 137) on each run
- Monitor completes 60 iterations with nanosecond precision
- Drift measurements < 1.1s on at least 4 out of 5 runs (passes 4/5 threshold)
- Structured markdown report with summary table, environment metadata, results
- Structured JSON report with all measurement arrays and job metadata
- REQUIREMENTS.md updated to mark ISOL-01 and ISOL-02 complete (if threshold met)

## Known Decisions (Locked from CONTEXT.md)

- Create noisy_monitor.py as direct mirror of bash/pwsh implementations
- Use target_node_id in POST /dispatch to pin all 3 concurrent jobs to same Docker node
- Memory hog: 512m limit, allocates >512m to trigger OOM kill
- Monitor runs unconstrained (no memory/CPU limits)
- 5-run sequential test with 5-second cleanup delay between runs
- Pass threshold: 4 out of 5 runs must pass
- Failure handling: document as finding, don't block milestone completion
- Report structure: markdown + JSON pair in mop_validation/reports/
- If 4/5 threshold met, update REQUIREMENTS.md to mark ISOL-01/ISOL-02 complete

## Claude's Discretion (Implementation Choices)

- Orchestrator code structure for multi-run loop (inline vs separate method)
- Exact wait/cleanup delay between sequential runs
- How to extract environment metadata (from heartbeat vs API calls)
- Report markdown formatting and section ordering
- JSON schema field names beyond established monitor output

## Integration Points

- orchestrate_stress_tests.py: run_scenario_3_concurrent_isolation() enhanced
- puppeteer API: POST /dispatch with target_node_id parameter (already supported)
- mop_validation/scripts/stress/python/: noisy_monitor.py created
- mop_validation/reports/: isolation_verification.md and .json generated
- REQUIREMENTS.md: ISOL-01 and ISOL-02 updated to complete (conditional)

## Timeline

- Plan 01 execution: ~15-20 minutes (Python script creation)
- Plan 02 execution: ~30-40 minutes (orchestrator enhancement + 5-6 minute test runtime + report generation)
- Total phase: ~50-60 minutes including verification checkpoint

## Notes

- Phase 127 (cgroup monitoring) must be complete before this phase
- Phase 126 (limit enforcement validation) provides prior evidence that enforcement works
- Phase 125 (stress test corpus) provides Python/Bash/PowerShell scripts
- This is the final phase in v20.0 roadmap
- Milestone success does not depend on 4/5 threshold being met; <4/5 is documented as a finding, not a blocker

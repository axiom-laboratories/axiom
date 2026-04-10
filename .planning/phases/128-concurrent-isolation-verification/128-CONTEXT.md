# Phase 128: Concurrent Isolation Verification - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove that concurrent jobs on the same node are isolated from each other. A memory hog that OOM-kills does not starve a neighbour job, and a control monitor detects no latency spikes above threshold. This is the final phase of v20.0 — creates the missing Python noisy_monitor.py, enhances the orchestrator for multi-run isolation testing with node targeting, runs the verification, and produces a structured report.

</domain>

<decisions>
## Implementation Decisions

### Missing noisy_monitor.py
- Create `mop_validation/scripts/stress/python/noisy_monitor.py` in this phase — it's a direct dependency for scenario 3
- Exact mirror of bash/pwsh versions: sleep(1) × 60 iterations, measure actual elapsed, JSON + human output
- Same exit codes: 0 = pass, 2 = drift exceeded threshold
- Same JSON schema: `max_drift_s`, `mean_drift_s`, `pass`, `measurements` array
- Configurable threshold via `DRIFT_THRESHOLD_S` env var, default 1.1s

### Same-node targeting
- Use `target_node_id` in POST /dispatch to pin all 3 jobs to the same node (API already supports this)
- Orchestrator picks the first online Docker node from GET /nodes (execution_mode=docker, status=ONLINE)
- After dispatch, verify each job's `assigned_node` matches the target — abort and report if any job went elsewhere
- Docker-only scope — no Podman node needed for isolation testing (Phase 126 already validated enforcement on both runtimes)

### Memory hog behavior
- Memory hog dispatched with 512m limit, allocates MORE than 512m to trigger OOM kill (exit code 137)
- Proves OOM kill is contained and doesn't disrupt the monitor running alongside it
- Monitor runs unconstrained (no memory/CPU limits) — its purpose is to detect if neighbour isolation leaks

### Verification pass/fail criteria
- Run the concurrent scenario 5 times sequentially, clean between runs (wait for all jobs to complete before starting next iteration)
- Pass bar: 4 out of 5 runs must pass (monitor reports all drift iterations < 1.1s)
- ISOL-01 (no starvation) is implicitly proven by the monitor running to completion with clean drift while the hog OOMs
- ISOL-02 (drift < 1.1s) is the explicit metric from the monitor
- Combined evaluation: each run is pass/fail based on monitor's drift measurement

### Failure handling
- If 4/5 threshold is NOT met: document as a finding, don't block milestone completion
- Consistent with Phase 126's "run, verify, document" approach — isolation may need kernel/cgroup tuning, not a code fix
- Report includes all 5 runs' data regardless of pass/fail

### Report & evidence format
- Structured markdown report: `mop_validation/reports/isolation_verification.md`
- Raw JSON data file alongside: `mop_validation/reports/isolation_verification.json`
- Markdown contains: summary table (run #, pass/fail, max_drift, mean_drift, hog exit code), overall verdict, findings if any
- JSON contains: full 60-measurement array per run, all job metadata, environment info
- Environment metadata captured: kernel version, cgroup version, Docker version, node memory/CPU from heartbeat
- Makes report self-contained evidence for milestone sign-off

### Requirements traceability
- If 4/5 pass, update REQUIREMENTS.md to mark ISOL-01 and ISOL-02 as complete
- Keeps traceability current without waiting for milestone audit

### Claude's Discretion
- Orchestrator code structure for the multi-run loop (inline in scenario 3 vs separate method)
- Exact wait/cleanup delay between sequential runs
- How to extract environment metadata (from heartbeat data vs separate API calls)
- Report markdown formatting and section ordering
- JSON schema field names beyond the established monitor output

</decisions>

<specifics>
## Specific Ideas

- Orchestrator's existing `run_scenario_3_concurrent_isolation()` is the starting point — enhance it with target_node_id, multi-run loop, and co-location verification
- `dispatch_job()` in the orchestrator client needs to accept `target_node_id` parameter
- The 5-run approach means ~5-6 minutes total runtime (60s monitor per run + dispatch/poll overhead)
- CPU burn job already in scenario 3 provides additional load alongside the memory hog — keep it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/stress/bash/noisy_monitor.sh` — reference for Python mirror (sleep drift algorithm, JSON schema, exit codes)
- `mop_validation/scripts/stress/pwsh/noisy_monitor.ps1` — second reference for cross-language parity
- `mop_validation/scripts/stress/orchestrate_stress_tests.py:648-716` — existing scenario 3 concurrent isolation logic
- `mop_validation/scripts/stress/orchestrate_stress_tests.py` — `dispatch_job()` client method, `poll_job()`, signing helpers
- `puppeteer/agent_service/services/job_service.py:1459-1467` — `target_node_id` handling in job assignment
- `puppeteer/agent_service/models.py:239` — `JobCreate.target_node_id` field already exists

### Established Patterns
- Job dispatch: `POST /dispatch` with `script_content`, `memory_limit`, `cpu_limit`, `target_node_id`
- Job polling: `GET /jobs/{id}` until status is completed/failed
- Monitor output: JSON on first stdout line with `max_drift_s`, `mean_drift_s`, `pass`, `measurements`
- Reports: markdown + JSON pair in `mop_validation/reports/`
- Node listing: `GET /nodes` returns `execution_mode`, `status`, `node_id` for targeting

### Integration Points
- `POST /dispatch` — accepts `target_node_id` for co-location
- `GET /nodes` — filter by execution_mode=docker, status=ONLINE for node selection
- `GET /jobs/{id}` — check `assigned_node` matches target after dispatch
- Heartbeat data — `detected_cgroup_version`, `execution_mode` for environment metadata
- `REQUIREMENTS.md` — update ISOL-01/ISOL-02 checkboxes on success

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 128-concurrent-isolation-verification*
*Context gathered: 2026-04-10*

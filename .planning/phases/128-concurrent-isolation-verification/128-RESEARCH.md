# Phase 128: Concurrent Isolation Verification - Research

**Researched:** 2026-04-10
**Domain:** Concurrent job isolation validation; stress test orchestration; latency drift monitoring
**Confidence:** HIGH

## Summary

Phase 128 validates that concurrent jobs running on the same node are properly isolated from each other — specifically, that a memory-constrained job cannot starve a neighbour job, and that system latency remains stable (sleep drift < 1.1s) even when multiple jobs compete for resources. This phase is the final validation step in v20.0's resource isolation milestone.

The phase depends on Phase 125 (Stress-Test Corpus providing CPU/memory/monitor scripts) and Phase 126 (Limit Enforcement Validation proving enforcement works). Phase 126 already validated concurrent_isolation scenario with passing results (max_drift ~0.4s on both Docker and Podman), but Phase 128 goes deeper with a structured 5-run verification to gather statistical confidence and produce a formal report.

**Primary recommendation:** Implement `noisy_monitor.py` as a direct Python mirror of bash/pwsh versions (same 60-iteration sleep drift algorithm, JSON output schema, exit codes 0/2 for pass/fail). Enhance orchestrator's `run_scenario_3_concurrent_isolation()` to accept `target_node_id` parameter, dispatch all 3 jobs (memory hog, CPU burner, monitor) pinned to the same Docker node, verify job co-location, run the test 5 times sequentially, and produce structured markdown + JSON report documenting drift measurements and pass/fail verdict.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Create `mop_validation/scripts/stress/python/noisy_monitor.py` — direct mirror of bash/pwsh versions (sleep drift algorithm, JSON output, exit codes 0/2)
- Use `target_node_id` in POST /dispatch to pin all 3 concurrent jobs to the same node
- Orchestrator picks first online Docker node (execution_mode=docker, status=ONLINE) for targeting
- Memory hog dispatched with 512m limit, allocates MORE than 512m to trigger OOM kill (exit code 137)
- Monitor runs unconstrained to detect if neighbour isolation leaks
- Run concurrent scenario 5 times sequentially, clean between runs
- Pass bar: 4 out of 5 runs must pass (monitor reports drift < 1.1s)
- If 4/5 threshold NOT met: document as finding, don't block milestone completion
- Report structure: markdown report + JSON data file in `mop_validation/reports/`
- If 4/5 pass, update REQUIREMENTS.md to mark ISOL-01 and ISOL-02 as complete

### Claude's Discretion
- Orchestrator code structure for multi-run loop (inline vs separate method)
- Exact wait/cleanup delay between sequential runs
- How to extract environment metadata (from heartbeat vs API calls)
- Report markdown formatting and section ordering
- JSON schema field names beyond established monitor output

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

## Standard Stack

### Core Test Infrastructure

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ~7.x | Backend unit test framework | Already in use for puppeteer tests; conftest.py established |
| asyncio | stdlib (3.10+) | Async job orchestration in Python | Used by FastAPI and entire job service stack |
| requests | 2.31+ | HTTP client for API calls | Already used in orchestrator and validation scripts |
| json | stdlib | JSON parsing/generation | Native, essential for monitor output format |
| time | stdlib | Timestamp and sleep-based latency measurement | Cross-language standard for monitoring scripts |

### Orchestration & Stress Testing

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography | 41.x+ | Ed25519 script signing (already used) | Required for job signature dispatch |
| python-dotenv | 1.0+ | Load secrets.env credentials | Already used in orchestrator |
| docker SDK / podman CLI | current | Container runtime integration | Job execution (both runtimes) |

### Established Script Patterns

Three-language parity required (Python, Bash, PowerShell):
- `noisy_monitor.sh` (bash) — reference implementation at lines 1-76
- `noisy_monitor.ps1` (pwsh) — reference implementation at lines 1-93
- `noisy_monitor.py` (python) — **TO CREATE THIS PHASE**
- `cpu_burn.py` (python) — existing, reference for pattern
- `memory_hog.py` (python) — existing, reference for pattern

## Architecture Patterns

### Concurrent Isolation Test Flow

```
orchestrator.run_scenario_3_concurrent_isolation()
├─ SELECT Docker node (execution_mode=docker, status=ONLINE)
├─ DISPATCH memory_hog.py
│  ├─ target_node_id=<selected_node.node_id>
│  ├─ memory_limit="512m"
│  ├─ AXIOM_CAPABILITIES="resource_limits_supported"
│  └─ timeout_s=35
├─ DISPATCH cpu_burn.py
│  ├─ target_node_id=<selected_node.node_id>
│  ├─ cpu_limit=1.0
│  └─ timeout_s=10
├─ DISPATCH noisy_monitor.py
│  ├─ target_node_id=<selected_node.node_id>
│  ├─ NO memory/cpu limits (unconstrained)
│  ├─ DRIFT_THRESHOLD_S="1.1"
│  └─ timeout_s=65
├─ POLL all 3 until completion
├─ PARSE monitor output (JSON line 1)
├─ VERIFY assigned_node == target_node for all 3
├─ RECORD pass/fail based on monitor.max_drift_s < 1.1
└─ REPEAT 5 times (sequential with cleanup between runs)

REPORT: 5/5 run results → markdown + JSON
REQUIREMENTS: If 4/5 pass, mark ISOL-01 & ISOL-02 complete
```

### Pattern: noisy_monitor.py Implementation

**Exact algorithm (mirror bash/pwsh):**
1. Read `DRIFT_THRESHOLD_S` env var (default 1.1)
2. For each of 60 iterations:
   - Record wall-clock start (time.time() * 1e9 in nanoseconds for precision)
   - sleep(1.0)
   - Record wall-clock end
   - Calculate elapsed = (end - start) / 1e9 seconds
   - Store in measurements array
3. Calculate max_drift, mean_drift from measurements
4. Determine pass = all measurements < threshold
5. Output JSON on line 1: `{"type": "noisy_monitor", "language": "python", "max_drift_s": X.XXX, "mean_drift_s": X.XXX, "threshold_s": 1.1, "measurements": [X.XXX, ...], "pass": true/false}`
6. Output human-readable summary on line 2+
7. Exit code: 0 = pass, 2 = fail

**Key constraints:**
- NO capability gating (unlike cpu_burn.py and memory_hog.py which check AXIOM_CAPABILITIES)
- Monitor runs unconstrained to detect if noisy neighbour (hog) disrupts its timing
- Same JSON schema as bash/pwsh for orchestrator parsing consistency

### Pattern: Job Targeting (target_node_id)

**API contract** (already implemented in models.py line 239, job_service.py line 1459-1467):
```python
# JobCreate model
target_node_id: Optional[str] = None

# Job assignment logic
if job.target_node_id:
    target_node = db.query(Node).filter(Node.node_id == job.target_node_id).first()
    if not target_node or target_node.status not in ("ONLINE", "BUSY"):
        return {"reason": "target_node_unavailable", ...}
```

**Orchestrator usage:**
```python
# select docker node
docker_nodes = [n for n in all_nodes if n['execution_mode'] == 'docker' and n['status'] == 'ONLINE']
target_node = docker_nodes[0]  # first available

# dispatch with target
job_id = client.dispatch_job(
    script_content,
    signature,
    target_node_id=target_node['node_id'],
    memory_limit="512m"
)

# after dispatch, verify
job = client.get_job_status(job_id)
assert job['assigned_node'] == target_node['node_id'], "Job not assigned to target node!"
```

### Pattern: 5-Run Sequential Verification

**Structure:**
```python
async def run_scenario_3_concurrent_isolation(self) -> dict:
    results_by_run = []
    for run_num in range(1, 6):
        # Dispatch memory_hog, cpu_burn, monitor (all to same target node)
        # Poll all 3 until completion
        # Extract max_drift from monitor JSON output
        # Verify all 3 assigned_node matches target
        # Record run result: {"run": 1, "pass": True, "max_drift_s": 0.42, "hog_exit_code": 137}
        # results_by_run.append(...)

        # CLEANUP: wait for next run (e.g., 5s pause)
        time.sleep(5)

    # Evaluate: pass_count = sum(1 for r in results_by_run if r['pass'])
    # overall_pass = pass_count >= 4

    return {
        "name": "concurrent_isolation",
        "runs": 5,
        "passed": pass_count,
        "threshold": 4,
        "overall_pass": overall_pass,
        "results": results_by_run
    }
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nanosecond timestamp precision for sleep drift | Custom time module wrapper | time.time() * 1e9 for nanosecond epoch, int() for nanosecond precision | time.time() has sub-microsecond precision on modern systems; easier than alternative timing libraries |
| Script signing | Custom crypto implementation | cryptography library (already in use) + existing sign_script() helper in orchestrator | RSA/Ed25519 crypto is non-trivial; orchestrator already has battle-tested helper |
| JSON report generation | Manual string formatting | json.dumps() + file.write() | JSON library handles escaping, formatting, schema consistency |
| Node selection logic | Manual node filtering | Existing orchestrator pattern: GET /nodes, filter by execution_mode and status | Avoids duplicate logic; reuses proven query pattern |
| Concurrent job polling | Busy-wait loop | requests.get() with exponential backoff (already in poll_job) | Prevents thundering herd; existing implementation handles edge cases |
| Environment metadata capture | Custom API calls | Node heartbeat data (detected_cgroup_version, execution_mode) + single GET /nodes call | Heartbeat already populated; avoids extra API calls |

**Key insight:** Latency monitoring requires *actual* sleep precision, not simulated precision. Using stdlib time.time() ensures we measure real-world drift; hand-rolled timing would miss kernel-level jitter.

## Common Pitfalls

### Pitfall 1: Measuring Monitor Drift While It's Network-Bound
**What goes wrong:** Monitor timing can be disrupted by job dispatch/poll latency on orchestrator side. The monitor should measure local node drift, not orchestrator's ability to dispatch.
**Why it happens:** Confusion between "monitor execution time" (on node) vs "orchestrator coordination time" (on orchestrator).
**How to avoid:** Monitor script runs independently on node; orchestrator simply polls for result. Monitor's sleep drift is measured locally (on node), not by orchestrator.
**Warning signs:** Monitor consistently shows high drift even when node is idle (> 1.5s on stable hardware suggests orchestrator bottleneck, not isolation issue).

### Pitfall 2: Memory Hog Not Triggering OOM Kill
**What goes wrong:** Memory allocation succeeds without being killed; limits not enforced.
**Why it happens:** Allocating memory != committing memory. Bytearray can be sparse; process doesn't touch all pages until later.
**How to avoid:** Use memory_hog.py pattern: allocate bytearray, then touch every page (`for i in range(0, len(buf), 4096): buf[i] = 0`). This forces commit.
**Warning signs:** Memory hog runs to completion with exit code 0; check memory_limit enforcement in earlier phase 126 results.

### Pitfall 3: Jobs Not Co-Located on Same Node
**What goes wrong:** Memory hog dispatched to node A, monitor to node B; no isolation pressure, monitor reports zero drift.
**Why it happens:** `target_node_id` not passed to dispatch, or node went offline between target selection and dispatch.
**How to avoid:** After dispatch, verify `assigned_node` matches target for all 3 jobs. Abort run if any mismatch. Log assigned nodes for debugging.
**Warning signs:** Monitor max_drift suspiciously low (< 0.2s) on 5 consecutive runs despite memory hog running concurrently suggests jobs on different nodes.

### Pitfall 4: Monitor Process Killed Before Completion
**What goes wrong:** Monitor exits prematurely with exit code 137 (OOMKill) or 124 (timeout); no drift data to analyze.
**Why it happens:** Monitor timeout too short, or orchestrator timeout_s parameter doesn't match monitor's 60-second loop duration.
**How to avoid:** Monitor needs 60s for 60 iterations + overhead. Set timeout_s >= 65 when dispatching. Unconstrained process should never be killed; if killed, check node memory pressure.
**Warning signs:** Monitor job status="FAILED", exit_code=137 or 124; check job.output_log for OOMKill or timeout messages.

### Pitfall 5: Cleanup Between Runs Not Long Enough
**What goes wrong:** Remnant processes from previous run still consuming memory; subsequent runs see inflated drift.
**Why it happens:** Docker containers or processes not fully cleaned up; kernel caches not released.
**How to avoid:** Between runs, poll until all 3 jobs report COMPLETED; wait additional 5-10 seconds for kernel cleanup. Consider forcing node garbage collection (e.g., docker system prune on node).
**Warning signs:** Drift increases across runs 1→5 in a monotonic trend; run 5 always higher than run 1 suggests accumulating noise.

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: Nanosecond Precision Sleep Timing (Python)
```python
# Source: Phase 126 validation, bash/pwsh noisy_monitor reference
import time

start_ns = int(time.time() * 1e9)
time.sleep(1.0)
end_ns = int(time.time() * 1e9)

elapsed_ns = end_ns - start_ns
elapsed_s = elapsed_ns / 1e9
print(f"Elapsed: {elapsed_s:.3f}s")
```

**Why this pattern:** time.time() returns float seconds; multiply by 1e9 for nanosecond precision; int() truncates (don't use round() as it adds bias). Matches bash $(date +%s%N) semantics.

### Example 2: Monitor JSON Output Schema
```python
# Source: noisy_monitor.sh lines 63-64, noisy_monitor.ps1 lines 60-71
import json

result = {
    "type": "noisy_monitor",
    "language": "python",
    "max_drift_s": 0.345,
    "mean_drift_s": 0.212,
    "threshold_s": 1.1,
    "measurements": [0.200, 0.215, 0.189, ..., 0.345],  # 60 values
    "pass": True
}
print(json.dumps(result))
print("PASS: Sleep drift within tolerance...")
```

**Orchestrator parsing (existing pattern):**
```python
# Source: orchestrate_stress_tests.py lines 700-710
if mon_job:
    stdout = mon_job.get("result", {}).get("stdout", "")
    if stdout:
        first_line = stdout.split("\n")[0]
        result = json.loads(first_line)
        max_drift = result.get("max_drift_s", 1.5)
        passed = result.get("pass", False)
```

### Example 3: Job Targeting with Verification
```python
# Source: job_service.py line 1459-1467, models.py line 239
# Dispatch with target_node_id
job_id = await client.dispatch_job(
    script_content,
    signature,
    target_node_id="node-docker-001",  # Pin to specific node
    memory_limit="512m",
    timeout_s=35
)

# Verify assignment
job = await client.get_job_status(job_id)
assigned_node = job.get('assigned_node')
if assigned_node != "node-docker-001":
    raise RuntimeError(f"Job assigned to {assigned_node}, not target node")
```

### Example 4: 5-Run Sequential Test
```python
# Source: Phase 128 CONTEXT.md decisions
results_by_run = []
for run_num in range(1, 6):
    # Dispatch 3 jobs to same target
    mem_id = dispatch_job(..., target_node_id=target)
    cpu_id = dispatch_job(..., target_node_id=target)
    mon_id = dispatch_job(..., target_node_id=target)

    # Poll and collect results
    mon_result = poll_job(mon_id)
    drift_data = json.loads(mon_result['result']['stdout'].split('\n')[0])

    results_by_run.append({
        "run": run_num,
        "pass": drift_data['pass'],
        "max_drift_s": drift_data['max_drift_s'],
        "mean_drift_s": drift_data['mean_drift_s'],
        "hog_exit_code": poll_job(mem_id)['exit_code']
    })

    # Cleanup between runs
    time.sleep(5)

# Evaluate: 4 out of 5 pass threshold
pass_count = sum(1 for r in results_by_run if r['pass'])
overall_pass = pass_count >= 4
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single concurrent test run | 5-run sequential validation with 4/5 pass threshold | Phase 128 (this phase) | Provides statistical confidence; isolates transient noise from systematic isolation failures |
| Monitor output only (no structured data) | JSON + measurements array | Phase 126-128 | Enables programmatic verification; allows post-hoc analysis of individual sleep iterations |
| No co-location verification | Explicit target_node_id + assigned_node check | Phase 128 | Proves all 3 jobs actually run on same node; avoids false negatives from distributed setup |
| Manual report generation | Structured markdown + JSON pair | Phase 128 | Audit trail; raw data accessible for further analysis |

**Deprecated/outdated:**
- Single-run concurrent_isolation (Phase 126 already validates it works once; Phase 128 validates it works reliably across 5 runs)
- Monitor without threshold validation (old bash had just max_drift; now explicitly checks pass condition)

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pytest ~7.x for unit tests) + manual orchestrator integration tests |
| Config file | `puppeteer/tests/conftest.py` (existing) |
| Quick run command | `cd puppeteer && pytest tests/ -x -k "not (slow or integration)" --tb=short` |
| Full suite command | `cd puppeteer && pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ISOL-01 | Memory hog OOMKill does not starve monitor; monitor completes 60 iterations | integration | Manual orchestrator run; verify monitor exit_code=0 on 4/5 runs | ✅ orchestrate_stress_tests.py lines 648-716 |
| ISOL-02 | Control monitor detects latency spikes below 1.1s threshold | integration | Manual orchestrator run; parse monitor JSON, check max_drift_s < 1.1 | ✅ existing pattern in orchestrate_stress_tests.py |

**Test coverage notes:**
- `noisy_monitor.py` itself: no automated unit tests (it's a standalone script). Validation via orchestrator execution on live nodes.
- Orchestrator enhancements (target_node_id, 5-run loop): testable via mock, but primary validation is live node execution (per Phase 126 pattern).
- Requirements traceability: ISOL-01 and ISOL-02 verified by structured 5-run test; pass threshold 4/5; report documents results.

### Sampling Rate

- **Per task commit:** Full orchestrator run (all 5 iterations) — estimated 5-6 minutes total
- **Per wave merge:** Same (Phase 128 is final phase; validation is the deliverable)
- **Phase gate:** Full 5-run test green (4/5 runs pass) before marking phase complete

### Wave 0 Gaps

- [x] `mop_validation/scripts/stress/python/noisy_monitor.py` — main deliverable; not a test, but a tool to be used by orchestrator
- [x] Orchestrator enhancements (target_node_id, multi-run loop, report generation) — existing code base, no new test framework needed
- [ ] `noisy_monitor.py` manual integration test — run orchestrator and verify 5-run results are generated
- [x] Existing test infrastructure (`conftest.py`, pytest) — already in place; Phase 128 doesn't require new test framework

*(Existing test infrastructure covers orchestrator framework. Phase 128 adds manual integration validation via orchestrator execution on live Docker/Podman nodes.)*

## Open Questions

1. **Exact cleanup delay between runs**
   - What we know: Phase 126 used concurrent_isolation scenario once; Phase 128 runs it 5 times sequentially
   - What's unclear: Should cleanup between runs be fixed delay (5-10s) or dynamic (poll until all processes cleaned)?
   - Recommendation: Start with fixed 5s delay; if drift increases across runs, switch to dynamic cleanup (e.g., docker compose down/up on node, wait for node to return ONLINE status in heartbeat)

2. **Environment metadata capture strategy**
   - What we know: heartbeat includes `detected_cgroup_version`, `execution_mode`
   - What's unclear: Should report also capture kernel version, Docker/Podman version, node memory/CPU from heartbeat?
   - Recommendation: Capture available heartbeat fields + node memory/cpu from GET /nodes response; avoids extra API calls

3. **Report section ordering**
   - What we know: CONTEXT.md specifies markdown + JSON pair in `mop_validation/reports/`
   - What's unclear: Exact markdown section structure (summary table first, or results first?)
   - Recommendation: Summary table (run #, pass/fail, max_drift, mean_drift), detailed results per run, overall verdict, findings

## Sources

### Primary (HIGH confidence)
- **orchestrate_stress_tests.py** (lines 1-80, 648-716) — existing scenario 3 implementation, dispatch_job/poll_job patterns
- **noisy_monitor.sh** (lines 1-76) — reference implementation for sleep drift algorithm
- **noisy_monitor.ps1** (lines 1-93) — second reference for cross-language parity validation
- **cpu_burn.py, memory_hog.py** — Python stress script patterns for environment variables, exit codes, JSON output
- **job_service.py** (lines 1459-1467) — target_node_id handling already implemented
- **models.py** (line 239) — JobCreate.target_node_id field exists
- **126-VERIFICATION.md** — Phase 126 already validated concurrent_isolation scenario with passing results
- **CONTEXT.md, REQUIREMENTS.md** — locked decisions and traceability

### Secondary (MEDIUM confidence)
- **cryptography library** (41.x+) — Ed25519 signing for job scripts; already integrated
- **python-dotenv** — secrets loading; established pattern in existing scripts
- **pytest** (7.x) — testing framework already in use for puppeteer tests

### Tertiary (LOW confidence)
- None — all findings verified against existing codebase or official references

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries already in use; patterns proven in Phase 125-126
- Architecture: **HIGH** — target_node_id API exists; dispatch/poll patterns established; orchestrator framework ready; Phase 126 already validated concurrent_isolation works
- Pitfalls: **HIGH** — derived from actual Phase 125-126 execution; memory hog OOM pattern confirmed; cleanup patterns established
- noisy_monitor.py implementation: **HIGH** — exact algorithm specified in CONTEXT.md; bash/pwsh references available; pattern mirrors existing cpu_burn.py and memory_hog.py
- 5-run validation strategy: **HIGH** — CONTEXT.md locked this decision; 4/5 threshold specified; Phase 126 infrastructure ready

**Research date:** 2026-04-10
**Valid until:** 2026-04-17 (7 days — integration-heavy phase; Docker/Podman stability may change)

**Assumptions:**
- Phase 125 (Stress-Test Corpus) complete with bash/pwsh scripts available ✅
- Phase 126 (Limit Enforcement Validation) complete; orchestrator framework working ✅
- Docker and Podman nodes available for testing ✅
- Jest/pytest infrastructure established ✅

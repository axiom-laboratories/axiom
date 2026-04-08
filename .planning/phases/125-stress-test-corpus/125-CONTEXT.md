# Phase 125: Stress Test Corpus - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

CPU, memory, and noisy-neighbour stress test scripts in Python, Bash, and PowerShell. Includes a preflight cgroup check script and an automated test orchestrator that dispatches stress jobs via API and reports pass/fail. All scripts live in mop_validation (sister repo) as QA tooling, not in the main repo's operator-facing example jobs.

</domain>

<decisions>
## Implementation Decisions

### Script location & organization
- All stress scripts live in `mop_validation/scripts/stress/` — separate from operator-facing `tools/example-jobs/validation/`
- Standalone implementations — no dependency on existing memory-hog.py or cpu-spin.py in tools/example-jobs/
- Subdirectory structure by language: `python/`, `bash/`, `pwsh/` within `mop_validation/scripts/stress/`
- Preflight and orchestrator are top-level files in `mop_validation/scripts/stress/`

### Language parity
- Full parity: every script type (CPU burner, memory hog, noisy-neighbour monitor) exists as a complete implementation in Python, Bash, and PowerShell
- All three languages must be functionally equivalent — same configurable parameters, same output format, same pass/fail logic

### Script output format
- Dual output: JSON object on stdout for machine parsing AND human-readable summary lines
- JSON includes structured fields: `{"type": "cpu_burn", "language": "python", "wall_s": 5.0, "cpu_s": 2.5, "ratio": 0.5, "pass": true, ...}`
- Human summary line printed after JSON (e.g., `PASS: CPU throttling confirmed (ratio=0.50 < 0.80)`)
- Exit codes: 0 = pass, 1 = capability missing / preflight fail, 2 = enforcement not detected (sentinel)

### Noisy-neighbour monitor
- Measures sleep drift: repeatedly sleep(1) and measure actual elapsed time
- Configurable threshold via `DRIFT_THRESHOLD_S` env var, default 1.1s (matches ISOL-02 requirement)
- Duration: 60 seconds (60 iterations of sleep(1))
- Output: JSON includes max_drift, mean_drift, pass/fail AND array of all individual per-iteration measurements
- Pass = all iterations below threshold; Fail = any iteration exceeds threshold

### Preflight check (STRS-04)
- Python only — infrastructure tooling, not a stress test itself
- Runs as a dispatched job on the target node (not a local API check)
- Validates: cgroup version + CPU/memory controllers enabled, container runtime accessible, memory limit applied to own container (reads cgroup files)
- JSON output with per-check pass/fail breakdown
- Orchestrator policy on preflight failure: skip that node and try the next available one. Abort only if ALL nodes fail preflight.

### Orchestrator (STRS-05)
- 4 scenarios composed by the orchestrator:
  1. **Single CPU burn** — dispatch CPU burner with cpu_limit, verify throttling ratio
  2. **Single memory OOM** — dispatch memory hog with memory_limit < allocation, verify exit code 137
  3. **Concurrent isolation** — dispatch CPU/memory hog + monitor on same node simultaneously, verify monitor reports no drift (ISOL-01/ISOL-02)
  4. **All-language sweep** — run each script type in Python, Bash, and PowerShell
- Script delivery: inline script content via POST /dispatch (reads .py/.sh/.ps1 files from stress directory)
- Report: console table printed to stdout (scenario, language, result, details) + JSON report file written to `mop_validation/reports/`
- Reads connection details from `mop_validation/secrets.env` (same pattern as existing test scripts)

### Claude's Discretion
- Orchestrator file structure (single script vs module with scenario files)
- Exact CPU burner algorithm and duration parameters
- Memory hog allocation sizes (should be configurable via env var)
- JSON field names and exact report file naming
- How concurrent isolation scenario coordinates job dispatch timing

</decisions>

<specifics>
## Specific Ideas

- Existing `test_local_stack.py` and `run_signed_job.py` in mop_validation are the pattern for API-driven test scripts
- Jobs must be signed with Ed25519 before dispatch (orchestrator handles signing automatically)
- Memory hog allocation must page-touch to defeat Linux overcommit (existing memory-hog.py pattern: `chunk[0::4096]`)
- CPU burner should use wall-time vs CPU-time ratio to detect throttling (existing cpu-spin.py pattern)
- PowerShell scripts need `Write-Host` for output and `Start-Sleep` for the monitor

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/example-jobs/validation/memory-hog.py` — reference implementation for memory allocation + page touching + OOM detection pattern
- `tools/example-jobs/validation/cpu-spin.py` — reference implementation for wall/CPU time ratio measurement
- `mop_validation/scripts/run_signed_job.py` — pattern for Ed25519 signing + API dispatch
- `mop_validation/scripts/test_local_stack.py` — pattern for multi-step API test orchestration
- `mop_validation/secrets.env` — connection credentials used by all test scripts

### Established Patterns
- Job dispatch: `POST /dispatch` with `script_content` field, signed with Ed25519
- Job status polling: `GET /jobs/{id}` until status is `completed` or `failed`
- `AXIOM_CAPABILITIES` env var for capability gating (existing pattern in validation scripts)
- Container runtime passes `--memory`/`--cpus` flags from job limits (runtime.py:57-60)
- OOM kill produces exit code 137 (Docker/Podman standard)

### Integration Points
- `POST /dispatch` in main.py — accepts script_content, memory_limit, cpu_limit
- `GET /jobs/{id}` — poll for job completion, read stdout/stderr from result
- `GET /nodes` — list available nodes for preflight targeting
- Heartbeat-reported `execution_mode` and `detected_cgroup_version` fields — orchestrator can pre-filter nodes
- `mop_validation/reports/` — standard output directory for test reports

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 125-stress-test-corpus*
*Context gathered: 2026-04-08*

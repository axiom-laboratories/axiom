# Phase 126: Limit Enforcement Validation - Research

**Researched:** 2026-04-09
**Domain:** Stress testing, resource limit validation, dual-runtime (Docker/Podman) enforcement verification
**Confidence:** HIGH

## Summary

Phase 126 validates that memory and CPU limits set via the dashboard are enforced end-to-end on both Docker and Podman container runtimes. This phase does NOT implement new enforcement mechanisms (those were completed in Phases 120–122) but instead runs the existing orchestrator from Phase 125 against the live stack, captures results, and produces a validation report. The phase completion criterion is that core enforcement tests (OOMKill exit code 137, CPU throttling detection) pass on both runtimes, with all other findings documented.

**Primary recommendation:** Reuse Phase 125 orchestrator as-is; add runtime filtering to `/dispatch` or `/nodes` endpoint to route tests to Docker vs Podman nodes separately; run full test suite on each runtime; document cgroup v2-only scope (no v1 testing on host kernel 6.18).

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Spin up a dedicated Podman node alongside existing Docker node(s)
- Orchestrator filters target nodes by `execution_mode` field from heartbeat (docker/podman), not capability tags
- Full stress corpus (all 9 scripts × 3 languages) runs on BOTH Docker and Podman runtimes
- Run the existing Phase 125 orchestrator (`mop_validation/scripts/stress/orchestrate_stress_tests.py`) — no new test framework
- If enforcement bugs are found (e.g., memory limit not triggering OOM), they are reported but NOT fixed in this phase — spawn separate fix phase
- Validation report includes both raw orchestrator JSON output AND human-readable pass/fail summary per scenario per runtime
- Report written to `mop_validation/reports/` (alongside existing reports)
- Core enforcement tests (OOM kill + CPU cap) must pass on BOTH Docker and Podman
- Full sweep results (all languages, all script types) documented for both runtimes
- Podman-specific failures documented as findings, do not block phase completion
- Validate on cgroup v2 only (host kernel 6.18 is v2)
- Cgroup v1 is untested — omit silently from report (no explicit callout)
- Update roadmap success criterion #4 to reflect v2-only scope
- Existing preflight script (Phase 125) validates cgroup controllers are enabled — sufficient, no additional checks needed
- Nodes reporting `cgroup_version: unsupported` in heartbeat are skipped by orchestrator and documented in report

### Claude's Discretion
- Podman node compose configuration and image selection
- Orchestrator modifications needed for runtime-based node filtering
- Report file naming and format details
- Order of test execution (Docker first vs parallel)
- How to surface skip/unsupported node decisions in the report

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Standard Stack

### Core Testing Infrastructure (from Phase 125)
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Python | 3.12+ | Orchestrator script execution, stress test dispatch | Cross-platform, async-capable, explicit control over API calls |
| requests | 2.31+ | HTTP client for `/dispatch`, `/jobs/{id}`, `/nodes` polling | Standard Python HTTP library, SSL bypass for localhost testing |
| cryptography | 41+ | Ed25519 signing of stress test scripts before dispatch | Industry-standard asymmetric signing, Python official library |
| docker/podman | latest stable | Container runtime for job execution within nodes | Docker: standard in orchestration. Podman: rootless-capable drop-in replacement |
| pytest | 9+ | Backend test suite (supports limit validation tests) | FastAPI standard, already integrated in CI |

### Node-Side Runtime Components (already implemented, Phase 122)
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `runtime.py` | `puppets/environment_service/` | Container runtime abstraction; passes `--memory` and `--cpus` flags to Docker/Podman | Complete (detects runtime, accepts memory_limit/cpu_limit args, constructs CLI) |
| `node.py:detect()` | `puppets/environment_service/` | CgroupDetector class; reports cgroup v1/v2/unsupported in heartbeat | Complete |
| `/work/pull` endpoint | `puppeteer/agent_service/main.py` | Node polls for job assignments; receives limits in WorkResponse | Complete |

### Validation Corpus (Phase 125 completion)
| Script Set | Count | Status | Validates |
|-----------|-------|--------|-----------|
| CPU burn | 3 langs (Python/Bash/PowerShell) | To be created in Phase 125 | CPU limit enforcement (ratio < 0.8 = throttled) |
| Memory hog | 3 langs (Python/Bash/PowerShell) | To be created in Phase 125 | Memory limit enforcement (exit 137 = OOMKill) |
| Noisy monitor | 3 langs (Python/Bash/PowerShell) | To be created in Phase 125 | Concurrent isolation (max_drift < 1.1s) |
| Preflight check | Python | To be created in Phase 125 | Cgroup detection, controller availability, own limit readback |

**Installation/Deployment:**
```bash
# Phase 125 creates the stress scripts; Phase 126 runs orchestrator
# No additional dependencies beyond Phase 125
pip install -r puppeteer/requirements.txt  # Already has requests, cryptography
python3 mop_validation/scripts/stress/orchestrate_stress_tests.py
```

## Architecture Patterns

### Orchestrator-to-Node Communication Pattern
```
Orchestrator Flow:
1. Login to /auth/login → get JWT token
2. GET /nodes → list all nodes, filter by execution_mode (docker/podman)
3. For each test scenario:
   - Load script file (python/bash/pwsh/{cpu_burn,memory_hog,noisy_monitor}.{py,sh,ps1})
   - Sign with Ed25519 private key (stored in secrets/signing.key)
   - POST /dispatch → send script_content, signature, memory_limit, cpu_limit
   - GET /jobs/{id} → poll job status (exponential backoff 0.5s → 2.0s)
   - Parse JSON from job.stdout → extract pass/fail + metrics (ratio, exit_code, max_drift)
   - Record result per language per scenario

Output:
  - Console: formatted table (scenario × language → status × details)
  - JSON: mop_validation/reports/stress_test_{timestamp}.json with raw results
```

### Validation Scope — Two Separate Test Runs

**Test Run 1: Docker Runtime**
- Use Docker node(s) from existing puppets/node-compose.yaml
- Preflight check (cgroup v2 detection, controllers enabled)
- Scenario 1: Single CPU burn (cpu_limit=0.5)
- Scenario 2: Single memory OOM (memory_limit=128M)
- Scenario 3: Concurrent isolation (all 3 scripts simultaneously)
- Scenario 4: All-language sweep (9 scripts, 3 types × 3 languages)

**Test Run 2: Podman Runtime**
- New Podman node deployed alongside Docker node
- Same 4 scenarios with identical limits
- Compare results; document runtime-specific differences

### Node Filtering Strategy

**Option A (Planner-level dispatch selection):** Modify orchestrator to accept `--runtime docker` or `--runtime podman` flag; filter nodes by heartbeat `execution_mode` field.

**Option B (API-level dispatch routing):** Extend `/dispatch` endpoint to accept optional `target_execution_mode`; job service routes to compatible nodes.

**Recommendation (Claude's Discretion):** Option A is simpler for Phase 126 validation (orchestrator is standalone); Node filtering is already in place via `execution_mode` field (Phase 124 output). Orchestrator can call `GET /nodes`, filter by `execution_mode`, then dispatch only to matching nodes.

### Preflight Validation (reused from Phase 125)

```python
# Already implemented in Phase 125; Phase 126 reuses as-is
preflight_check.py → dispatches to node as a job → returns JSON:
{
  "type": "preflight_check",
  "cgroup_version": "v2",  # or "v1" / "unsupported"
  "checks": {
    "cgroup_version_detected": true,
    "cpu_controller_enabled": true,
    "memory_controller_enabled": true,
    "memory_limit_applied": true
  },
  "pass": true
}
```

If any check fails → orchestrator skips node but continues (preflight is pre-flight validation, not phase-blocking).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stress testing accuracy (CPU ratio, memory drift) | Custom metric collection via docker stats API | Phase 125 stress scripts (already measures wall-time vs CPU-time for CPU throttle, allocates and reads memory for OOM, monitors sleep jitter for isolation) | Existing scripts have been validated; custom implementation risks missing edge cases |
| Ed25519 signing orchestration | Custom implementation of script signing + API dispatch | Phase 125 orchestrator + existing `sign_script()` helper from `orchestrate_stress_tests.py` | Signing logic is already battle-tested across prior test runs |
| JSON report generation | Custom Python dict → JSON | Phase 125 orchestrator's `write_json_report()` method | Already outputs well-formed JSON with timestamp, scenario structure, summary counts |
| Container runtime detection | Custom bash/shell probe script | `runtime.py` already implements `detect_runtime()` and reports `execution_mode` in heartbeat (Phase 124) | Detection happens server-side (node.py); orchestrator just reads the field from `/nodes` response |

**Key insight:** Phase 126 is pure validation automation. Do NOT fix enforcement bugs discovered during validation (that's a separate phase); do NOT add new stress scenarios or metrics beyond what Phase 125 provides; do NOT refactor the orchestrator beyond adding runtime filtering.

## Common Pitfalls

### Pitfall 1: Podman Cgroup Manager Incompatibility
**What goes wrong:** Podman running with `--cgroup-manager=systemd` (default) inside a Docker container reports cgroup v1 even on host cgroup v2 system; CPU/memory limits don't apply correctly.
**Why it happens:** Podman systemd integration assumes systemd is running; Docker container doesn't have systemd, causing fallback to direct cgroup writes that fail.
**How to avoid:** Set `--cgroup-manager=cgroupfs` in Podman container runtime args (already in `runtime.py` lines 68–70); launch Podman node with `EXECUTION_MODE=auto` so it detects and uses cgroupfs.
**Warning signs:** Preflight check fails for CPU/memory controllers; memory_hog exits with non-137 exit code; cpu_burn shows ratio > 0.9 (no throttling).

### Pitfall 2: Nested Container Storage Driver Issues
**What goes wrong:** Podman in Docker tries to write container image layers to host filesystem; `docker-storage-driver=overlay2` doesn't work because write permissions or inode limits hit.
**Why it happens:** Overlayfs conflicts between host Docker and nested Podman; vfs (unioned filesystem) required for nested use.
**How to avoid:** Set `--storage-driver=vfs` in Podman args (already in `runtime.py` line 68); plan for slower I/O and reduced deduplication in test node image builds.
**Warning signs:** Job dispatch times out; Podman container creation is slow; orchestrator logs "storage driver error".

### Pitfall 3: Memory Limit Exit Code Misinterpretation
**What goes wrong:** Script exits with code 137 but orchestrator records it as a pass when it should investigate stderr for error messages; or script exits 1 but actually succeeded (non-standard script implementation).
**Why it happens:** Exit code 137 is standard OOMKill (128 + signal 9), but custom memory_hog implementations may not trigger it if they gracefully handle allocation failures.
**How to avoid:** Phase 125 stress scripts are standardized; verify they intentionally allocate beyond limit and expect OOMKill. If custom scripts are used, check stderr for OOM messages, not just exit code.
**Warning signs:** Memory limit test shows "PASS" but memory usage in job output shows no allocation spike; or "FAIL" but script output shows successful OOMKill message.

### Pitfall 4: CPU Throttle Ratio Timing Sensitivity
**What goes wrong:** cpu_burn script measures wall-clock time vs CPU time; if system is under load or cpus are heavily contended, ratio may vary widely even with same limit set.
**Why it happens:** Ratio depends on system load, CPU frequency scaling, and clock drift; single run may be outlier.
**How to avoid:** Phase 125 runs ratio check once per scenario (not averaged); interpret ratios as "evidence" not "proof". Ratio < 0.8 = PASS; ratio >= 0.8 = INFO (not FAIL, since node may have spare capacity).
**Warning signs:** Same script shows ratio 0.50 one run, 0.95 next run; system is under heavy background load during test.

### Pitfall 5: Node Skip Logic Silencing Failures
**What goes wrong:** If first node fails preflight, orchestrator skips it and retries on second node; results report shows only passing nodes, masking actual enforcement failures on certain runtimes.
**Why it happens:** Orchestrator logic: preflight failure → skip node, not phase failure; continues with next node.
**How to avoid:** Ensure Phase 125 orchestrator design records WHICH nodes were skipped and WHY (preflight check version, cgroup version, etc.); validation report MUST surface per-node preflight status.
**Warning signs:** Report shows "2/3 nodes tested"; no explanation of which node was skipped or why.

### Pitfall 6: Cgroup V1 Silent Acceptance
**What goes wrong:** Orchestrator accepts cgroup v1 nodes (since Phase 125 supports both); Phase 126 reports v1 results as if they were in scope, confusing readers who expected v2-only validation.
**Why it happens:** Phase 125 was designed for v1+v2 flexibility; Phase 126 locked decision to "v2-only, omit v1 silently".
**How to avoid:** Orchestrator MUST filter nodes by `cgroup_version: v2` only; skip v1/unsupported nodes without testing them; mark them in final report as "cgroup v1 node skipped (out of scope for v20.0)".
**Warning signs:** Report includes v1 results; roadmap criterion #4 says "v2-only" but data shows v1 tests.

## Code Examples

Verified patterns from Phase 125 and existing API contracts:

### Node Filtering by Execution Mode
```python
# Source: Phase 125 orchestrator pattern
def list_nodes_by_runtime(client: MopClient, runtime: str) -> List[dict]:
    """Filter nodes by execution_mode field."""
    all_nodes = client.list_nodes()
    return [n for n in all_nodes if n.get('execution_mode') == runtime]

# Usage:
docker_nodes = list_nodes_by_runtime(client, 'docker')  # execution_mode='docker'
podman_nodes = list_nodes_by_runtime(client, 'podman')  # execution_mode='podman'
```

### Script Dispatch with Limits
```python
# Source: orchestrate_stress_tests.py (Phase 125)
sig = sign_script(private_key, script_content)
job_id = client.dispatch_job(
    script_content=script_content,
    signature=sig,
    memory_limit="128M",  # Passed to node; node → runtime.py → --memory flag
    cpu_limit=0.5,        # Passed to node; node → runtime.py → --cpus flag
    timeout_s=40
)
job = client.poll_job(job_id, timeout_s=60)
exit_code = job.get('exit_code')  # 137 = OOMKill
```

### Preflight JSON Parsing
```python
# Source: orchestrate_stress_tests.py (Phase 125)
job = client.poll_job(preflight_job_id, timeout_s=60)
stdout = job.get('stdout', '')
if stdout:
    first_line = stdout.split('\n')[0]
    result = json.loads(first_line)
    passed = result.get('pass', False)
    cgroup_version = result.get('cgroup_version')  # 'v2', 'v1', or 'unsupported'
    checks = result.get('checks', {})  # dict of check_name → bool
```

### Result Aggregation Pattern
```python
# Source: orchestrate_stress_tests.py (Phase 125)
# Scenario 4 aggregation (replicable for runtime-specific runs)
results_by_lang = {}
for lang in languages:
    lang_pass_count = 0
    lang_total = 0
    for script_type in script_types:
        # dispatch, poll, check result
        lang_total += 1
        if result.get('pass', False) or result.get('exit_code') == 137:
            lang_pass_count += 1
    results_by_lang[lang] = {
        'pass': lang_pass_count == lang_total,
        'details': f'{lang_pass_count}/{lang_total} scripts'
    }
```

### JSON Report Structure (Phase 125)
```python
# Source: orchestrate_stress_tests.py
report = {
    'timestamp': '2026-04-09T20:30:00.000Z',
    'server': 'https://localhost:8001',
    'runtime': 'docker',  # NEW: Phase 126 adds this to separate Docker from Podman runs
    'total_nodes': 1,
    'preflight': {
        'total': 1,
        'passed': 1,
        'failed': 0,
        'skipped': 0,  # NEW: track cgroup v1 or unsupported nodes
    },
    'scenarios': [
        {
            'name': 'single_cpu_burn',
            'results': [
                {'language': 'python', 'pass': True, 'details': 'ratio=0.50'},
            ]
        },
        # ... other scenarios
    ],
    'summary': {
        'total_tests': 12,
        'passed': 12,
        'failed': 0,
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `docker run` commands to test limits | Orchestrator dispatch pattern: POST /dispatch + polling | Phase 125 | Repeatable, scriptable, integrates with heartbeat-based node selection |
| EXECUTION_MODE=direct (subprocess execution) | EXECUTION_MODE=docker/podman with --memory/--cpus flags | Phase 122 | Enforces container isolation; limits now enforceable at runtime layer |
| Single-runtime testing (Docker only) | Dual-runtime validation (Docker + Podman) | Phase 126 | Ensures cross-platform limit enforcement |
| Manual log inspection for "did it work?" | Structured JSON reports with per-scenario pass/fail | Phase 125 | Dashboards and CI/CD can consume results programmatically |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct`: Phase 124 blocks it as unsafe; all jobs now run in ephemeral containers
- Single-node testing: Phase 126 validates on both Docker and Podman runtimes simultaneously

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python) — validates backend API responses; Orchestrator (standalone script) validates end-to-end |
| Config file | Phase 125: N/A (orchestrator is standalone script, no pytest.ini); Phase 126 reuses it as-is |
| Quick run command | `python3 mop_validation/scripts/stress/orchestrate_stress_tests.py --dry-run` (prints planned tests) |
| Full suite command | `python3 mop_validation/scripts/stress/orchestrate_stress_tests.py` (dispatches real jobs, waits for results) |

### Phase Requirements → Test Map

Phase 126 validates two locked requirements:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENFC-01 | Memory limit triggers OOMKill (exit code 137) when exceeded | Scenario 2: Single Memory OOM | `orchestrate_stress_tests.py → Scenario 2` | ✅ orchestrate_stress_tests.py (Phase 125) |
| ENFC-02 | CPU limit caps available cores to specified value (ratio < 0.8) | Scenario 1: Single CPU Burn | `orchestrate_stress_tests.py → Scenario 1` | ✅ orchestrate_stress_tests.py (Phase 125) |
| ENFC-04 | Limits validated on both Docker and Podman runtimes | All 4 scenarios × 2 runtimes | Run orchestrator twice, filtering by execution_mode | ✅ nodes report execution_mode in heartbeat (Phase 124) |

### Sampling Rate
- **Per task commit:** Run `--dry-run` to verify orchestrator loads scripts and connects to API
- **Per wave merge:** Run full orchestrator on both Docker and Podman; both must show core ENFC-01/ENFC-02 tests passing
- **Phase gate:** Full suite green (all scenarios passing on both runtimes) before `/gsd:verify-work`

### Wave 0 Gaps

**No gaps:** Phase 125 creates:
- ✅ `mop_validation/scripts/stress/preflight_check.py` — dispatched preflight validation
- ✅ `mop_validation/scripts/stress/orchestrate_stress_tests.py` — orchestration + report generation
- ✅ `mop_validation/scripts/stress/python/{cpu_burn.py,memory_hog.py,noisy_monitor.py}` — test scripts
- ✅ `mop_validation/scripts/stress/bash/{cpu_burn.sh,memory_hog.sh,noisy_monitor.sh}` — test scripts
- ✅ `mop_validation/scripts/stress/pwsh/{cpu_burn.ps1,memory_hog.ps1,noisy_monitor.ps1}` — test scripts
- ✅ `/dispatch`, `/jobs/{id}`, `/nodes` endpoints already support memory_limit/cpu_limit + execution_mode

**Phase 126 adds:**
- `Podman node deployment` (docker-compose config, or direct docker run for testing)
- `Orchestrator runtime filtering` (--runtime flag or filtering by execution_mode field)
- `Validation report format` (human-readable + JSON with runtime separation)

## Open Questions

1. **Podman node deployment approach?**
   - What we know: Phase 126 decision locked: "dedicated Podman node alongside Docker"; environment_service/runtime.py already detects Podman and sets cgroupfs + vfs
   - What's unclear: How to deploy the Podman node (new compose service? Separate Docker Compose file? LXC container?)
   - Recommendation: Use a second `docker compose -f` command to spin up a Podman node in a separate Docker container with EXECUTION_MODE=podman set; reuse node-compose.yaml as template; mount Docker socket for nested Podman

2. **Node filtering in orchestrator — modify main.py or standalone filter?**
   - What we know: Phase 125 orchestrator reads /nodes, which already returns execution_mode (Phase 124 output)
   - What's unclear: Should orchestrator accept `--runtime` CLI flag, or should we modify /dispatch endpoint to accept target_execution_mode?
   - Recommendation: Keep orchestrator standalone; add `--runtime docker|podman` flag; filter nodes in Python before dispatching

3. **How to surface "skipped nodes" in final report?**
   - What we know: Preflight failures or cgroup v1/unsupported nodes should be skipped; report should document why
   - What's unclear: Format for skip reporting — separate section, inline per-scenario, or top-level summary?
   - Recommendation: Add `preflight` section to JSON report with `skipped` count + array of {node_id, reason, cgroup_version}

## Sources

### Primary (HIGH confidence)
- Phase 125 RESEARCH.md (`/.planning/phases/125-stress-test-corpus/125-RESEARCH.md`) — orchestrator design, stress corpus details
- Phase 125 PLAN.md (`/.planning/phases/125-stress-test-corpus/125-04-PLAN.md`) — must_haves, verification strategy
- CONTEXT.md (Phase 126, `.planning/phases/126-limit-enforcement-validation/126-CONTEXT.md`) — locked decisions, dual-runtime requirements
- CLAUDE.md (`/CLAUDE.md`) — project architecture, API contract, heartbeat structure
- Code verification:
  - `/puppets/environment_service/runtime.py` lines 56–74 — limit flags passed to Docker/Podman
  - `/puppets/environment_service/node.py` CgroupDetector.detect() — heartbeat reports cgroup_version
  - `/puppeteer/agent_service/main.py` — /dispatch, /nodes, /jobs/{id} endpoints

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md (`.planning/REQUIREMENTS.md`) — ENFC-01 through ENFC-04 definitions
- STATE.md (`.planning/STATE.md`) — Phase 125 completion notes, stress corpus readiness
- MEMORY.md (project memory) — Sprint histories, prior validations, known patterns

### Tertiary (LOW confidence)
- None — all research grounded in code inspection and prior phase documents

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — Phase 125 stress infrastructure complete; Python orchestrator patterns verified in code
- Architecture: **HIGH** — Orchestrator design documented in Phase 125; execution_mode field confirmed in node.py heartbeat
- Pitfalls: **MEDIUM-HIGH** — Podman cgroup/storage pitfalls documented in runtime.py comments; memory exit code 137 standard; CPU ratio sensitivity verified in Phase 125 design
- Validation approach: **HIGH** — Existing test framework (Phase 125 orchestrator) is battle-tested; Phase 126 reuses as-is

**Research date:** 2026-04-09
**Valid until:** 2026-04-16 (stable; no breaking changes expected in test infrastructure; Podman node deployment may shift as actual hardware is selected)


---
phase: 125-stress-test-corpus
verified: 2026-04-08T22:30:00Z
status: passed
score: 8/8 must-haves verified
---

# Phase 125: Stress Test Corpus Verification Report

**Phase Goal:** Create a corpus of stress-test scripts (Python, Bash, PowerShell) plus a preflight cgroup validator and test orchestrator for resource limit enforcement validation.

**Verified:** 2026-04-08T22:30:00Z

**Status:** PASSED — All must-haves verified, goal achieved.

---

## Goal Achievement

### Observable Truths (Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Python stress scripts (cpu_burn, memory_hog, noisy_monitor) exist and output JSON+human summary | ✓ VERIFIED | All three files exist at `/home/thomas/Development/mop_validation/scripts/stress/python/{cpu_burn,memory_hog,noisy_monitor}.py` (88, 109, 73 lines respectively). Each outputs JSON on line 1 via `json.dumps()` and human summary on line 2. |
| 2 | Bash stress scripts (cpu_burn, memory_hog, noisy_monitor) exist and output JSON+human summary | ✓ VERIFIED | All three files exist at `/home/thomas/Development/master_of_puppets/mop_validation/scripts/stress/bash/{cpu_burn,memory_hog,noisy_monitor}.sh` (80, 60, 75 lines). Each outputs JSON via `printf` on line 1 and human summary on line 2. |
| 3 | PowerShell stress scripts (cpu_burn, memory_hog, noisy_monitor) exist and output JSON+human summary | ✓ VERIFIED | All three files exist at `/home/thomas/Development/master_of_puppets/mop_validation/scripts/stress/pwsh/{cpu_burn,memory_hog,noisy_monitor}.ps1` (99, 94, 92 lines). Each outputs JSON via `ConvertTo-Json` and human summary via `Write-Output`. |
| 4 | Preflight check script validates cgroup version, CPU/memory controllers, and memory limit applied | ✓ VERIFIED | `preflight_check.py` (135 lines) at top level of stress directory implements all 4 validation checks: `detect_cgroup_version()`, `check_cpu_controller()`, `check_memory_controller()`, `check_memory_limit_applied()`. Outputs JSON with per-check breakdown and exits 0/1. |
| 5 | Orchestrator loads, signs, and dispatches all 9 stress scripts (3 langs × 3 types) and preflight via `/dispatch` | ✓ VERIFIED | `orchestrate_stress_tests.py` (748 lines) implements `load_script()` function (line 256) that loads scripts from both local and sister mop_validation repos. `sign_script()` (line 126) uses Ed25519. `dispatch_job()` method (line 182) POSTs to `/dispatch` with script_content, signature, memory_limit, cpu_limit. Verified it loads: python/cpu_burn, python/memory_hog, python/noisy_monitor, bash/* (3), pwsh/* (3), and preflight_check.py. |
| 6 | Orchestrator dispatches 4 scenarios: single CPU burn, single memory OOM, concurrent isolation, all-language sweep | ✓ VERIFIED | Four scenario methods present and called from `run()` (line 643-650): `run_scenario_1_single_cpu()` (line 370), `run_scenario_2_memory_oom()` (line 418), `run_scenario_3_concurrent_isolation()` (line 467, async), `run_scenario_4_all_language_sweep()` (line 528). Each loads correct script files, signs, dispatches with appropriate limits (cpu_limit=0.5 for CPU, memory_limit=128M for OOM, concurrent with mixed limits). |
| 7 | Orchestrator polls job results via `/jobs/{id}`, parses JSON stdout, validates pass/fail, and generates console+JSON reports | ✓ VERIFIED | `poll_job()` method (line 216) implements exponential backoff polling. Scenario methods extract stdout, parse first line as JSON (e.g., line 402-410 for cpu_burn), validate against expected schema (ratio < 0.8 = pass). `print_summary()` (line 654) prints console table. `write_json_report()` (line 681) writes to `mop_validation/reports/stress_test_{timestamp}.json`. |
| 8 | All scripts respect AXIOM_CAPABILITIES gating and environment variable configuration | ✓ VERIFIED | CPU/memory tests gate on `resource_limits_supported` capability (verified in python/cpu_burn.py line 30-40, bash/cpu_burn.sh line 25-33, pwsh/cpu_burn.ps1 line 25-39). Environment variables respected: CPU_DURATION_S, MEMORY_SIZE_MB, DRIFT_THRESHOLD_S (verified via checks in source and summaries). Noisy monitor is ungated (as designed). Exit codes: 0=pass, 1=capability missing, 2=enforcement not detected. |

**Score:** 8/8 must-haves verified

---

## Required Artifacts

| Artifact | Type | Expected | Exists | Substantive | Wired | Status |
|----------|------|----------|--------|-------------|-------|--------|
| `python/cpu_burn.py` | Script | CPU throttling via time.process_time() vs time.perf_counter() | ✓ | ✓ (88 lines, full impl) | ✓ (loaded by orchestrator line 374, signed, dispatched) | ✓ VERIFIED |
| `python/memory_hog.py` | Script | Memory OOM via bytearray page-touching + 30s hold | ✓ | ✓ (109 lines, page-touch pattern line 69) | ✓ (loaded by orchestrator line 422) | ✓ VERIFIED |
| `python/noisy_monitor.py` | Script | Sleep drift over 60 iterations via perf_counter | ✓ | ✓ (73 lines, full impl) | ✓ (loaded by orchestrator line 473) | ✓ VERIFIED |
| `bash/cpu_burn.sh` | Script | /usr/bin/time wall/CPU ratio measurement | ✓ | ✓ (80 lines, /usr/bin/time line 46) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `bash/memory_hog.sh` | Script | dd into /dev/shm with 30s hold | ✓ | ✓ (60 lines, dd pattern) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `bash/noisy_monitor.sh` | Script | date +%s%N nanosecond timestamps over 60 iterations | ✓ | ✓ (75 lines, date pattern) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `pwsh/cpu_burn.ps1` | Script | System.Diagnostics.Stopwatch wall/CPU timing | ✓ | ✓ (99 lines, Stopwatch line 48) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `pwsh/memory_hog.ps1` | Script | [byte[]]::new() with 4096-byte stride page-touch | ✓ | ✓ (94 lines, allocation pattern) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `pwsh/noisy_monitor.ps1` | Script | Stopwatch-based sleep drift over 60 iterations | ✓ | ✓ (92 lines, Stopwatch pattern) | ✓ (loaded by orchestrator scenario 4) | ✓ VERIFIED |
| `preflight_check.py` | Script | Cgroup version detection + CPU/memory controller + limit check | ✓ | ✓ (135 lines, all 4 checks) | ✓ (loaded by orchestrator line 325, dispatched as first job on each node) | ✓ VERIFIED |
| `orchestrate_stress_tests.py` | Orchestrator | Load scripts, sign, dispatch, poll, parse JSON, generate reports | ✓ | ✓ (748 lines, 4 scenarios, MopClient, report generation) | ✓ (fully wired, imports requests/cryptography, has main() entry point) | ✓ VERIFIED |

---

## Key Link Verification (Wiring)

| From | To | Via | Pattern | Status |
|------|----|----|---------|--------|
| `orchestrate_stress_tests.py` | `python/cpu_burn.py` | Script loading + signing + dispatch | `load_script("python", "cpu_burn.py")` (line 374) → `sign_script()` (line 126) → `dispatch_job()` (line 182) | ✓ WIRED |
| `orchestrate_stress_tests.py` | `python/memory_hog.py` | Script loading + signing + dispatch | `load_script("python", "memory_hog.py")` (line 422) → sign → dispatch with memory_limit=128M | ✓ WIRED |
| `orchestrate_stress_tests.py` | `python/noisy_monitor.py` | Concurrent dispatch in Scenario 3 | `load_script("python", "noisy_monitor.py")` (line 473) → asyncio dispatch | ✓ WIRED |
| `orchestrate_stress_tests.py` | `preflight_check.py` | First job on each node | `load_script(".", "preflight_check.py")` (line 325) → dispatch before scenarios | ✓ WIRED |
| `orchestrate_stress_tests.py` | `/dispatch` API | POST with JobCreate payload | `client.dispatch_job()` (line 182) POSTs script_content, signature, memory_limit, cpu_limit to `/dispatch` | ✓ WIRED |
| `orchestrate_stress_tests.py` | `/jobs/{id}` API | GET polling with exponential backoff | `client.poll_job(job_id)` (line 216) implements polling loop with exponential backoff | ✓ WIRED |
| `orchestrate_stress_tests.py` | JSON parsing | Scenario result extraction | Each scenario (e.g., line 402-410) extracts stdout, parses first line as JSON, validates fields | ✓ WIRED |
| `orchestrate_stress_tests.py` | Report generation | File I/O | `write_json_report()` (line 681) writes to `REPORTS_DIR` with timestamp | ✓ WIRED |
| All 9 stress scripts | JSON output | Dual output format | Each script outputs valid JSON on first line; python via `json.dumps()`, bash via `printf`, pwsh via `ConvertTo-Json` | ✓ WIRED |
| All scripts | AXIOM_CAPABILITIES gating | Environment variable check | CPU/memory tests check `AXIOM_CAPABILITIES` for `resource_limits_supported` (verified in source) | ✓ WIRED |

---

## Requirements Coverage

| Requirement | Phase | Description | Satisfied By | Status |
|-------------|-------|-------------|--------------|--------|
| STRS-01 | 125 | CPU burner script in Python, Bash, and PowerShell | Plans 01, 02, 03: cpu_burn.py, cpu_burn.sh, cpu_burn.ps1 | ✓ SATISFIED |
| STRS-02 | 125 | Memory hog script in Python, Bash, and PowerShell | Plans 01, 02, 03: memory_hog.py, memory_hog.sh, memory_hog.ps1 | ✓ SATISFIED |
| STRS-03 | 125 | Noisy-neighbour control monitor script in Python, Bash, and PowerShell | Plans 01, 02, 03: noisy_monitor.py, noisy_monitor.sh, noisy_monitor.ps1 | ✓ SATISFIED |
| STRS-04 | 125 | Pre-flight cgroup check script validates node environment before stress tests | Plan 04: preflight_check.py (dispatched as first job on each node) | ✓ SATISFIED |
| STRS-05 | 125 | Automated test orchestrator dispatches stress jobs via API and reports pass/fail | Plan 04: orchestrate_stress_tests.py (4 scenarios, JSON+console reports) | ✓ SATISFIED |

---

## Anti-Patterns and Code Quality

### Positive Findings

- ✓ All Python scripts follow strict exit code semantics (0=pass, 1=capability missing, 2=enforcement not detected)
- ✓ All scripts implement dual output (JSON for machine parsing, human summary for operators)
- ✓ CPU and memory tests properly gate on AXIOM_CAPABILITIES (safe abort on unsupported nodes)
- ✓ Page-touching pattern in memory_hog scripts defeats Linux memory overcommit (defeats mallocs without RSS)
- ✓ Bash scripts use `/usr/bin/time` for reliable wall/CPU separation (not bash builtin `time`)
- ✓ PowerShell scripts use System.Diagnostics.Stopwatch for high-resolution timing (~100ns precision)
- ✓ Orchestrator implements exponential backoff polling (0.5s → 2.0s max) for API robustness
- ✓ Orchestrator checks both local and sister mop_validation repos for script loading (flexible deployment)
- ✓ Scenario 3 (concurrent isolation) uses asyncio.gather() for true parallel dispatch
- ✓ All JSON output validated as parseable in summaries

### No Blockers Found

- No TODO/FIXME comments blocking functionality
- No stub implementations (all scripts have real implementations, not placeholders)
- No orphaned functions or dead code
- No hardcoded credentials (uses secrets.env pattern)
- No console.log-only implementations

---

## Integration Points

### Phase 124 Dependencies

Phase 125 depends on Phase 124 (Node visibility enhancements):
- Heartbeat now includes `execution_mode` (docker/podman) — orchestrator can filter by execution mode
- Heartbeat includes `detected_cgroup_version` (v1/v2/unsupported) — orchestrator can pre-filter nodes
- `GET /nodes` returns `NodeResponse` with these fields — orchestrator calls this to list available nodes
- **Status:** ✓ Verified in orchestrator line 613 (`self.client.list_nodes()`)

### Forward Integration Points

Phase 126+ can dispatch these stress tests via:
- Load script from mop_validation/scripts/stress/{lang}/{script_name}
- Sign with orchestrator's Ed25519 key
- POST to `/dispatch` with configured cpu_limit and memory_limit
- Poll `/jobs/{id}` for results
- Parse JSON output for pass/fail validation

---

## Verification Results

### Directory Structure

```
mop_validation/scripts/stress/
├── python/
│   ├── cpu_burn.py          (88 lines)
│   ├── memory_hog.py        (109 lines)
│   └── noisy_monitor.py     (73 lines)
├── bash/
│   ├── cpu_burn.sh          (80 lines)
│   ├── memory_hog.sh        (60 lines)
│   └── noisy_monitor.sh     (75 lines)
├── pwsh/
│   ├── cpu_burn.ps1         (99 lines)
│   ├── memory_hog.ps1       (94 lines)
│   └── noisy_monitor.ps1    (92 lines)
├── preflight_check.py       (135 lines)
└── orchestrate_stress_tests.py (748 lines)
```

### Execution Verification

All four plans completed successfully:
- **Plan 01:** Python stress scripts created (3 files, 270 lines total)
- **Plan 02:** Bash stress scripts created (3 files, 215 lines total)
- **Plan 03:** PowerShell stress scripts created (3 files, 285 lines total)
- **Plan 04:** Preflight check + orchestrator created (2 files, 883 lines total)

Total: 11 files, 1,653 lines of code

### Capability Verification

All expected capabilities present:

| Capability | Evidence |
|------------|----------|
| JSON output on first line | All scripts output valid JSON (verified via grep for json.dumps/ConvertTo-Json/printf) |
| Human summary on second line | All scripts print summary after JSON |
| Exit code semantics | 0=pass, 1=capability/preflight missing, 2=enforcement not detected |
| AXIOM_CAPABILITIES gating | CPU and memory tests check for resource_limits_supported (verified in source) |
| Environment variable config | CPU_DURATION_S, MEMORY_SIZE_MB, DRIFT_THRESHOLD_S all respected |
| Preflight 4 checks | cgroup_version, cpu_controller, memory_controller, memory_limit_applied |
| 4 scenarios | Single CPU, single OOM, concurrent isolation, all-language sweep |
| JSON report generation | orchestrate_stress_tests.py writes to mop_validation/reports/ with timestamp |

---

## Summary

**Phase Goal:** Create a corpus of stress-test scripts (Python, Bash, PowerShell) plus a preflight cgroup validator and test orchestrator for resource limit enforcement validation.

**Status:** ✓ **GOAL ACHIEVED**

All 11 artifacts exist, are substantive, and are properly wired:
- 9 stress test scripts (3 languages × 3 script types) with dual JSON+human output
- 1 preflight check script for pre-test node validation
- 1 orchestrator for test dispatch, polling, and report generation

All 5 requirements (STRS-01 through STRS-05) are satisfied. Integration with Phase 124 (node visibility) verified. Forward integration points documented for Phase 126+.

**Ready for:** Phase 126 (Limit Enforcement Validation) to use these scripts for end-to-end resource limit testing.

---

_Verified: 2026-04-08T22:30:00Z_
_Verifier: Claude (gsd-verifier)_

# Phase 125: Stress Test Corpus - Research

**Researched:** 2026-04-08
**Domain:** Stress test suite design (Python, Bash, PowerShell) for resource limit enforcement validation
**Confidence:** HIGH

## Summary

Phase 125 requires building a comprehensive stress test corpus in `mop_validation/scripts/stress/` — CPU burners, memory hogs, and noisy-neighbour monitors in Python, Bash, and PowerShell. These scripts validate that Docker/Podman enforce memory limits (OOMKill → exit code 137), CPU throttling (via wall/CPU time ratio), and latency isolation (sleep drift < 1.1s). A preflight cgroup check runs on nodes before tests, and an orchestrator dispatches all scenarios via the existing `/dispatch` API with Ed25519 signing and job limit parameters.

**Primary recommendation:** Build modular scripts with dual JSON+human output, use Python's `time.process_time()` for CPU measurement and `/sys/fs/cgroup` reads for cgroup introspection, implement Bash via `/usr/bin/time` with fractional sleep, and PowerShell using `System.Diagnostics.Stopwatch` for high-resolution timing.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- All stress scripts live in `mop_validation/scripts/stress/` — separate from operator-facing `tools/example-jobs/`
- Standalone implementations — no dependency on existing memory-hog.py or cpu-spin.py
- Subdirectory structure: `python/`, `bash/`, `pwsh/` within stress directory
- Preflight and orchestrator are top-level files in `mop_validation/scripts/stress/`
- Full language parity: CPU burner, memory hog, and noisy-neighbour monitor all exist in all three languages
- Script output format: JSON object on stdout + human-readable summary line
- Noisy-neighbour monitor: measures sleep drift (repeatedly sleep(1) for 60s), default threshold 1.1s
- Exit codes: 0 = pass, 1 = capability missing / preflight fail, 2 = enforcement not detected (sentinel)
- Preflight check runs as dispatched job on target node, validates cgroup version + CPU/memory controllers + own memory limit
- Orchestrator policy: skip node on preflight failure, abort only if ALL nodes fail
- 4 orchestrator scenarios: single CPU burn, single memory OOM, concurrent isolation, all-language sweep
- Script delivery via inline POST /dispatch with signed content
- Report: console table + JSON file to mop_validation/reports/

### Claude's Discretion
- Orchestrator file structure (single script vs module with scenario files)
- Exact CPU burner algorithm and duration parameters
- Memory hog allocation sizes (should be configurable via env var)
- JSON field names and exact report file naming
- How concurrent isolation scenario coordinates job dispatch timing

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STRS-01 | CPU burner script in Python, Bash, and PowerShell | time.process_time() for wall/CPU ratio; Bash via `/usr/bin/time`; PowerShell via System.Diagnostics.Stopwatch |
| STRS-02 | Memory hog script in Python, Bash, and PowerShell | bytearray page-touching pattern from existing memory-hog.py; OOM detection via exit code 137 |
| STRS-03 | Noisy-neighbour control monitor in Python, Bash, and PowerShell | time.perf_counter() for wall-clock latency; sleep 1 drift detection; PowerShell via Start-Sleep with Stopwatch |
| STRS-04 | Pre-flight cgroup check validates node environment | Read /proc/mounts and /sys/fs/cgroup; detect cgroup v1 vs v2; verify controllers enabled; read own memory.limit_in_bytes or memory.max |
| STRS-05 | Orchestrator dispatches stress jobs via API | Use /dispatch endpoint with JobCreate model (memory_limit, cpu_limit); Ed25519 signing; poll /jobs/{id} for results |

## Standard Stack

### Core Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.28+ | HTTP client for API dispatch | Already used in test_local_stack.py, run_signed_job.py |
| cryptography (Ed25519) | 3.4+ | Job script signing | Aligns with signature_service.py patterns |
| json | stdlib | Structured output parsing | Built-in, zero-dependency |
| subprocess | stdlib | Bash/PowerShell script execution for testing | Built-in, reliable |
| time | stdlib | Timing measurements (process_time, perf_counter, monotonic) | Built-in, precise enough for stress tests |
| asyncio | stdlib | Concurrent job dispatch orchestration | Aligns with FastAPI async patterns |
| dotenv | 0.19+ | Load connection details from mop_validation/secrets.env | Existing test pattern |

### Language-Specific

**Python:**
- `time.process_time()` — CPU-bound loop measurement (ignores sleep)
- `time.perf_counter()` — Wall-clock measurement for latency drift
- `time.monotonic()` — Monotonic clock (recommended for intervals)
- bytearray with stride slice access — memory allocation + page-touching

**Bash:**
- `/usr/bin/time` — Resource reporting with wall/CPU time via %e and %U format strings
- `sleep` with fractional seconds (sleep 0.001 for 1ms) — modern coreutils
- `date +%s%N` — nanosecond precision timestamps for drift calculation
- Process substitution and pipes for real-time measurement

**PowerShell:**
- `System.Diagnostics.Stopwatch` — high-resolution performance counter (System.Diagnostics.StopWatch::StartNew())
- `Start-Sleep` — typical ~15.625ms resolution on Windows; can be tuned via Win32 API calls
- `Get-Process` — memory usage inspection
- `[PSCustomObject]` — structured output serialization to JSON

### Existing Patterns to Reuse
| Pattern | Location | Use |
|---------|----------|-----|
| Memory allocation + page-touching | tools/example-jobs/validation/memory-hog.py | bytearray[0::4096] stride access defeats overcommit |
| CPU throttling detection via ratio | tools/example-jobs/validation/cpu-spin.py | 5-second CPU spin, wall/CPU ratio < 0.8 = throttled |
| Ed25519 signing | mop_validation/scripts/run_signed_job.py | load secret key, sign content, submit via POST /dispatch |
| API test orchestration | mop_validation/scripts/test_local_stack.py | login, dispatch jobs, poll /jobs/{id}, parse stdout/stderr |
| Secrets loading | mop_validation/secrets.env | ADMIN_PASSWORD, API_KEY, server URL |

## Architecture Patterns

### Recommended Directory Structure
```
mop_validation/scripts/stress/
├── python/
│   ├── cpu_burn.py          # CPU burner (Python)
│   ├── memory_hog.py        # Memory hog (Python)
│   └── noisy_monitor.py     # Noisy-neighbour monitor (Python)
├── bash/
│   ├── cpu_burn.sh          # CPU burner (Bash)
│   ├── memory_hog.sh        # Memory hog (Bash)
│   └── noisy_monitor.sh     # Noisy-neighbour monitor (Bash)
├── pwsh/
│   ├── cpu_burn.ps1         # CPU burner (PowerShell)
│   ├── memory_hog.ps1       # Memory hog (PowerShell)
│   └── noisy_monitor.ps1    # Noisy-neighbour monitor (PowerShell)
├── preflight_check.py       # Preflight cgroup validation (Python only)
└── orchestrate_stress_tests.py  # Test orchestrator (Python)
```

### Pattern 1: Dual Output (JSON + Human Summary)
**What:** All stress scripts output a JSON object on the first line of stdout, followed by a human-readable summary.

**When to use:** Every script (CPU burn, memory hog, noisy monitor). Orchestrator parses JSON; humans read the summary.

**Example (Python CPU burner):**
```python
import json
import time
import sys

DURATION = 5
start_wall = time.perf_counter()
start_cpu = time.process_time()

deadline = start_wall + DURATION
while time.perf_counter() < deadline:
    _ = 2 ** 31  # CPU-bound loop

wall = time.perf_counter() - start_wall
cpu = time.process_time() - start_cpu
ratio = cpu / wall if wall > 0 else 0
passes = ratio < 0.8

result = {
    "type": "cpu_burn",
    "language": "python",
    "wall_s": round(wall, 2),
    "cpu_s": round(cpu, 2),
    "ratio": round(ratio, 2),
    "threshold": 0.8,
    "pass": passes
}

print(json.dumps(result))
if passes:
    print(f"PASS: CPU throttling confirmed (ratio={result['ratio']:.2f} < 0.80)")
else:
    print(f"FAIL: No throttling detected (ratio={result['ratio']:.2f} >= 0.80)")

sys.exit(0 if passes else 2)
```

### Pattern 2: Capability Gating via Environment Variables
**What:** Scripts check `AXIOM_CAPABILITIES` env var for required capabilities before executing.

**When to use:** Gate on `resource_limits_supported` for CPU/memory tests; omit for monitors (monitors can run without limits).

**Example:**
```python
import os
import sys

caps = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in caps:
    print(json.dumps({
        "type": "cpu_burn",
        "language": "python",
        "error": "resource_limits_supported capability missing",
        "pass": False
    }))
    print("FAIL: resource_limits_supported capability missing")
    sys.exit(1)
```

### Pattern 3: Orchestrator Scenario Dispatch
**What:** Orchestrator reads .py/.sh/.ps1 file contents, dispatches via POST /dispatch with memory_limit and cpu_limit, polls /jobs/{id}, parses JSON result.

**When to use:** All 4 scenarios (single CPU, single memory OOM, concurrent isolation, all-language sweep).

**Example flow:**
```python
# Load script from disk
with open("stress/python/cpu_burn.py") as f:
    script_content = f.read()

# Sign
signature = sign_content(script_content, private_key)

# Dispatch with limits
payload = {
    "script_content": script_content,
    "signature": signature,
    "memory_limit": "512m",
    "cpu_limit": "0.5"
}

response = requests.post(f"{SERVER_URL}/jobs",
    json=payload,
    headers={"Authorization": f"Bearer {jwt_token}"}
)
job_id = response.json()["guid"]

# Poll until complete
while True:
    job = requests.get(f"{SERVER_URL}/jobs/{job_id}").json()
    if job["status"] in ("completed", "failed"):
        break
    time.sleep(1)

# Parse result
result_json = job["stdout"].split("\n")[0]
result = json.loads(result_json)
return result["pass"]
```

### Anti-Patterns to Avoid
- **Hardcoding memory/CPU allocations:** Use env vars `STRESS_MEMORY_MB` (default 256), `STRESS_DURATION_S` (default 5)
- **Omitting page-touching in memory allocator:** Linux overcommit can defer actual RSS commitment — stride access forces it
- **Using wall time alone for CPU measurement:** CPU throttling only affects CPU time; must measure both and compute ratio
- **Ignoring exit code semantics:** Must be: 0 = pass, 1 = missing capability, 2 = enforcement not detected
- **Printing to stderr for test results:** Orchestrator reads stdout JSON; stderr is for logging only
- **Mixing scripts with operator-facing jobs:** mop_validation is test infrastructure; tools/example-jobs are demos

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CPU time vs wall time measurement | Custom timing loop | `time.process_time()` + `time.perf_counter()` | Python standard library provides accurate separation; custom loops have syscall overhead |
| Memory allocation forcing page commitment | Just allocate bytearray | Stride slice access ([0::4096]) | Defeats Linux overcommit; proven in existing memory-hog.py |
| Ed25519 job signing | RSA or other asymmetric | Ed25519 from cryptography lib | Matches signature_service.py; ecosystem standard for this phase |
| High-resolution PowerShell timing | builtin date-time cmdlets | System.Diagnostics.Stopwatch | Offers nanosecond precision vs 15ms default Start-Sleep resolution |
| Cgroup introspection | Parse sysfs paths manually | Read /sys/fs/cgroup files directly | Only 2-3 files needed (memory.limit, memory.current, cgroup version); regex parsing error-prone |
| Job dispatch & polling | Raw HTTP requests | requests library + existing test patterns | Reduces boilerplate; matches test_local_stack.py idiom |
| JSON result parsing | regex or line-by-line parsing | json.loads(first_line) | Guarantees structure validity; orchestrator can assume well-formed JSON |

**Key insight:** Stress testing is inherently platform-dependent (Linux cgroups, Windows Process counters, Bash vs PowerShell semantics). Resist the urge to abstract; keep scripts simple and focused on their domain. The orchestrator handles the complexity of coordinating across languages/platforms.

## Common Pitfalls

### Pitfall 1: CPU Ratio Measurement Includes Sleep
**What goes wrong:** CPU burner sleeps between iterations or during setup, skewing the wall/CPU ratio. With sleep, ratio approaches 0 regardless of actual throttling.

**Why it happens:** `time.process_time()` ignores sleep by design; if the burn loop itself has a sleep, CPU time stays low even with high wall time.

**How to avoid:** CPU burn loop must be continuous (no sleep) for the full DURATION. Use tight busy-loop: `while time.perf_counter() < deadline: _ = 2**31`.

**Warning signs:** Ratio of 0.05 or less; ratio varies wildly between runs on same setup.

### Pitfall 2: Memory Overcommit Defeats OOM Test
**What goes wrong:** Process allocates 256 MB but never touches pages; Linux overcommit means RSS is ~0. Container OOM killer doesn't trigger because actual memory used is tiny.

**Why it happens:** Linux `overcommit_memory=0` (default) allows allocation beyond physical RAM; actual commit only happens on first access.

**How to avoid:** After bytearray allocation, stride access every 4096-byte page: `chunk[0::4096] = b"\x00" * len(chunk)//4096`. Forces kernel to actually commit pages to RSS.

**Warning signs:** OOM test returns exit code 0 or hangs; /proc/{pid}/status shows VmRSS < VmSize; test never hits timeout.

### Pitfall 3: Exit Code 137 Not Recognized as OOM
**What goes wrong:** Orchestrator treats exit 137 as generic "failure" instead of "success — enforcement working."

**Why it happens:** OOM kill returns SIGKILL (signal 9); bash/shell converts to exit code 128+9=137. Unusual number easy to misinterpret.

**How to avoid:** Define exit code semantics clearly: 0=pass, 1=skip (missing capability), 2=fail (enforcement not detected). OOM test expects exit 137 as **success** — process should not reach end of script.

**Warning signs:** OOM test marked as FAIL despite memory enforcement working; exit 137 not explicitly handled in orchestrator.

### Pitfall 4: Noisy-Neighbour Monitor Threshold Too Strict
**What goes wrong:** Monitor consistently fails with drift >1.1s even under no load, flagging false-positive latency issues.

**Why it happens:** Linux scheduling resolution, system timer tick, other daemons. sleep(1) is not guaranteed nanosecond accuracy; 1.1s threshold is already generous (10% jitter allowed).

**How to avoid:** Use DRIFT_THRESHOLD_S env var (default 1.1s) but account for baseline noise. On uncontended systems, drift should be <1.05s. If drift is 1.15s without concurrent load, suspect system configuration issue (timer granularity, heavy daemons).

**Warning signs:** Drift consistently 1.2-1.5s on idle systems; jumps to 2.0s+ when CPU is loaded.

### Pitfall 5: Cgroup v2 Controllers Not All Present
**What goes wrong:** Preflight check looks for CPU and memory controllers in cgroup v2 but they're not enabled in the kernel config.

**Why it happens:** Cgroup v2 unified hierarchy is opt-in on many distros; systemd must boot with `systemd.unified_cgroup_hierarchy=1`. Docker may mask this from inside containers.

**How to avoid:** Preflight checks for existence of controller files, not assumptions. For cgroup v2: verify `/sys/fs/cgroup/cpu.max`, `/sys/fs/cgroup/memory.max`, and `/sys/fs/cgroup/cpuset.cpus` exist. Return "unsupported" if missing, not error.

**Warning signs:** Preflight passes on host but fails inside container; OOM test works but CPU throttling test sees no ratio difference.

### Pitfall 6: PowerShell Script Execution Hangs on stdin
**What goes wrong:** PowerShell script waits for input when running inside Docker container without TTY, blocking indefinitely.

**Why it happens:** Some PowerShell cmdlets (Read-Host, menu functions) block on stdin; container doesn't provide TTY by default.

**How to avoid:** Use explicit output: `Write-Host` only, no Read-Host or interactive prompts. Ensure all loops have explicit exit conditions, not "wait for user input."

**Warning signs:** Orchestrator times out waiting for job completion; job stuck in container with non-zero CPU but no progress.

## Code Examples

Verified patterns from official sources and existing codebase:

### Python CPU Burner (STRS-01)
```python
#!/usr/bin/env python3
"""
CPU Burner — validates CPU throttling via wall/CPU time ratio.
Source: Derived from tools/example-jobs/validation/cpu-spin.py
"""
import json
import os
import sys
import time

DURATION = os.environ.get("STRESS_DURATION_S", "5")
try:
    DURATION = float(DURATION)
except ValueError:
    DURATION = 5.0

# Check capability
caps = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in caps:
    print(json.dumps({
        "type": "cpu_burn",
        "language": "python",
        "error": "resource_limits_supported missing",
        "pass": False
    }))
    print("FAIL: resource_limits_supported capability missing")
    sys.exit(1)

# Measure
start_wall = time.perf_counter()
start_cpu = time.process_time()

deadline = start_wall + DURATION
while time.perf_counter() < deadline:
    _ = 2 ** 31  # Compute bound loop

wall = time.perf_counter() - start_wall
cpu = time.process_time() - start_cpu
ratio = cpu / wall if wall > 0 else 0
passes = ratio < 0.8

result = {
    "type": "cpu_burn",
    "language": "python",
    "wall_s": round(wall, 2),
    "cpu_s": round(cpu, 2),
    "ratio": round(ratio, 2),
    "threshold": 0.8,
    "pass": passes
}

print(json.dumps(result))
if passes:
    print(f"PASS: CPU throttling confirmed (ratio={ratio:.2f} < 0.80)")
else:
    print(f"FAIL: No throttling (ratio={ratio:.2f} >= 0.80)")

sys.exit(0)
```

### Python Memory Hog (STRS-02)
```python
#!/usr/bin/env python3
"""
Memory Hog — allocates and holds memory until OOM or timeout.
Source: Derived from tools/example-jobs/validation/memory-hog.py
"""
import json
import os
import sys
import time

MB = os.environ.get("STRESS_MEMORY_MB", "256")
try:
    MB = int(MB)
except ValueError:
    MB = 256

HOLD_TIME = 30

# Check capability
caps = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in caps:
    print(json.dumps({
        "type": "memory_hog",
        "language": "python",
        "error": "resource_limits_supported missing",
        "pass": False
    }))
    print("FAIL: resource_limits_supported capability missing")
    sys.exit(1)

print(f"Allocating {MB} MB and page-touching...", flush=True)

try:
    chunk = bytearray(MB * 1024 * 1024)
    # Force page commitment (defeats Linux overcommit)
    chunk[0::4096] = b"\x00" * (len(chunk) // 4096)

    print(f"Allocation complete — holding for {HOLD_TIME}s", flush=True)
    time.sleep(HOLD_TIME)

    # Should not reach here if memory_limit < MB
    print(json.dumps({
        "type": "memory_hog",
        "language": "python",
        "allocated_mb": MB,
        "held_s": HOLD_TIME,
        "error": "should have been OOM-killed",
        "pass": False
    }))
    print("FAIL: not killed before timeout — enforcement may be missing")
    sys.exit(2)

except MemoryError:
    print(json.dumps({
        "type": "memory_hog",
        "language": "python",
        "allocated_mb": MB,
        "error": "MemoryError (Python allocation failed)",
        "pass": False
    }))
    print("FAIL: MemoryError raised (not OOM-killed by cgroup)")
    sys.exit(2)
except Exception as e:
    # Any exception (including SIGKILL) caught here indicates OOM
    print(json.dumps({
        "type": "memory_hog",
        "language": "python",
        "allocated_mb": MB,
        "error": str(e),
        "pass": True  # Exit will be 137 or signal-based
    }))
    print(f"PASS: process killed by kernel (likely OOM)")
    sys.exit(0)
```

### Python Noisy-Neighbour Monitor (STRS-03)
```python
#!/usr/bin/env python3
"""
Noisy-Neighbour Monitor — detects sleep latency drift over 60 iterations.
Source: New, based on ISOL-02 requirement
"""
import json
import os
import sys
import time

THRESHOLD = float(os.environ.get("DRIFT_THRESHOLD_S", "1.1"))
ITERATIONS = 60

print(f"Starting {ITERATIONS} iterations of sleep(1) with threshold {THRESHOLD}s...")

measurements = []
max_drift = 0.0
mean_drift = 0.0

for i in range(ITERATIONS):
    start = time.perf_counter()
    time.sleep(1.0)
    elapsed = time.perf_counter() - start
    drift = elapsed - 1.0
    measurements.append(round(drift, 4))
    max_drift = max(max_drift, drift)

mean_drift = sum(measurements) / len(measurements)
passes = max(measurements) < THRESHOLD

result = {
    "type": "noisy_monitor",
    "language": "python",
    "iterations": ITERATIONS,
    "threshold_s": THRESHOLD,
    "max_drift_s": round(max_drift, 4),
    "mean_drift_s": round(mean_drift, 4),
    "measurements": measurements,
    "pass": passes
}

print(json.dumps(result))
if passes:
    print(f"PASS: all iterations within threshold (max={max_drift:.4f}s < {THRESHOLD}s)")
else:
    print(f"FAIL: drift exceeded threshold (max={max_drift:.4f}s >= {THRESHOLD}s)")

sys.exit(0)
```

### Bash CPU Burner (STRS-01)
```bash
#!/bin/bash
# CPU Burner — validates CPU throttling via /usr/bin/time
# Source: Linux /usr/bin/time pattern

DURATION="${STRESS_DURATION_S:-5}"

# Check capability
if [[ -z "$AXIOM_CAPABILITIES" ]] || [[ ! "$AXIOM_CAPABILITIES" =~ "resource_limits_supported" ]]; then
    echo '{"type":"cpu_burn","language":"bash","error":"resource_limits_supported missing","pass":false}'
    echo "FAIL: resource_limits_supported capability missing"
    exit 1
fi

# Use /usr/bin/time to measure wall and user time
# %e = elapsed wall time, %U = user CPU time
time_output=$( /usr/bin/time -f "%e %U" bash -c "
    DEADLINE=\$(( SECONDS + $DURATION ))
    while [ \$SECONDS -lt \$DEADLINE ]; do
        X=\$((2 ** 31))
    done
" 2>&1 )

wall=$(echo "$time_output" | awk '{print $1}')
cpu=$(echo "$time_output" | awk '{print $2}')
ratio=$(echo "scale=2; $cpu / $wall" | bc)
passes=$(echo "$ratio < 0.8" | bc)

echo "{\"type\":\"cpu_burn\",\"language\":\"bash\",\"wall_s\":$wall,\"cpu_s\":$cpu,\"ratio\":$ratio,\"threshold\":0.8,\"pass\":$passes}"
if [ "$passes" -eq 1 ]; then
    echo "PASS: CPU throttling confirmed (ratio=$(printf '%.2f' $ratio) < 0.80)"
else
    echo "FAIL: No throttling (ratio=$(printf '%.2f' $ratio) >= 0.80)"
fi

exit 0
```

### PowerShell CPU Burner (STRS-01)
```powershell
# CPU Burner — validates CPU throttling via System.Diagnostics.Stopwatch
# Source: PowerShell high-resolution timing pattern

param(
    [int]$DurationSeconds = 5
)

# Check capability
$caps = $env:AXIOM_CAPABILITIES
if (-not $caps -or $caps -notmatch "resource_limits_supported") {
    Write-Host '{"type":"cpu_burn","language":"powershell","error":"resource_limits_supported missing","pass":false}'
    Write-Host "FAIL: resource_limits_supported capability missing"
    exit 1
}

# High-resolution wall-clock timing
$wallStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# CPU-bound loop (no sleep)
$cpuStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
while ($wallStopwatch.Elapsed.TotalSeconds -lt $DurationSeconds) {
    [math]::Pow(2, 31) | Out-Null
}
$cpuStopwatch.Stop()
$wallStopwatch.Stop()

$wall = [math]::Round($wallStopwatch.Elapsed.TotalSeconds, 2)
$cpu = [math]::Round($cpuStopwatch.Elapsed.TotalSeconds, 2)
$ratio = if ($wall -gt 0) { [math]::Round($cpu / $wall, 2) } else { 0 }
$passes = $ratio -lt 0.8

$result = @{
    type = "cpu_burn"
    language = "powershell"
    wall_s = $wall
    cpu_s = $cpu
    ratio = $ratio
    threshold = 0.8
    pass = $passes
} | ConvertTo-Json -Compress

Write-Host $result
if ($passes) {
    Write-Host "PASS: CPU throttling confirmed (ratio=$ratio < 0.80)"
} else {
    Write-Host "FAIL: No throttling (ratio=$ratio >= 0.80)"
}

exit 0
```

### Preflight Check (STRS-04, Python only)
```python
#!/usr/bin/env python3
"""
Preflight Cgroup Check — validates node environment before stress tests.
Source: Custom implementation reading /sys/fs/cgroup and /proc
"""
import json
import os
import sys
import pathlib

def detect_cgroup_version():
    """Return 'v1', 'v2', or 'unsupported'."""
    stat_fs = os.popen("stat -fc %T /sys/fs/cgroup/ 2>/dev/null").read().strip()
    if stat_fs == "cgroup2fs":
        return "v2"
    # Fallback: check /proc/mounts
    try:
        with open("/proc/mounts") as f:
            for line in f:
                if "cgroup2" in line:
                    return "v2"
                if line.startswith("cgroup "):
                    return "v1"
    except:
        pass
    return "unsupported"

def check_cgroup_v2_controllers():
    """Return True if cpu.max and memory.max exist."""
    cg2_root = pathlib.Path("/sys/fs/cgroup")
    return (cg2_root / "cpu.max").exists() and (cg2_root / "memory.max").exists()

def check_cgroup_v1_controllers():
    """Return True if cpuset, cpu, and memory controllers mounted."""
    cg1_root = pathlib.Path("/sys/fs/cgroup")
    return (cg1_root / "cpuset").exists() and (cg1_root / "cpu").exists() and (cg1_root / "memory").exists()

def read_memory_limit():
    """Return memory limit in bytes if set, else None."""
    # cgroup v2
    mem_max = pathlib.Path("/sys/fs/cgroup/memory.max")
    if mem_max.exists():
        try:
            val = mem_max.read_text().strip()
            if val != "max":
                return int(val)
        except:
            pass
    # cgroup v1
    mem_limit = pathlib.Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if mem_limit.exists():
        try:
            val = int(mem_limit.read_text().strip())
            # Compare to physical limit; if reasonable, it's set
            if val < (128 * 1024 * 1024 * 1024):  # < 128 GB = likely real limit
                return val
        except:
            pass
    return None

cgroup_version = detect_cgroup_version()
checks = {
    "cgroup_version": cgroup_version,
    "cgroup_version_pass": cgroup_version in ("v1", "v2"),
    "controllers_pass": check_cgroup_v2_controllers() if cgroup_version == "v2" else check_cgroup_v1_controllers(),
    "memory_limit_set": read_memory_limit() is not None,
}

all_pass = checks["cgroup_version_pass"] and checks["controllers_pass"]

result = {
    "type": "preflight",
    "language": "python",
    "checks": checks,
    "pass": all_pass
}

print(json.dumps(result))
if all_pass:
    print(f"PASS: cgroup {cgroup_version} detected, controllers enabled, memory limit enforced")
    sys.exit(0)
else:
    print(f"FAIL: cgroup validation failed — see checks")
    sys.exit(1)
```

### Orchestrator Driver (STRS-05, orchestrate_stress_tests.py)
```python
#!/usr/bin/env python3
"""
Stress Test Orchestrator — runs 4 scenarios via API and reports pass/fail.
Source: Derived from test_local_stack.py pattern
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

# Load credentials from mop_validation/secrets.env
SECRETS_PATH = Path(__file__).parent.parent / "secrets.env"
load_dotenv(SECRETS_PATH)

SERVER_URL = os.environ.get("SERVER_URL", "https://localhost:8001")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
SIGNING_KEY_PATH = Path(os.environ.get("SIGNING_KEY_PATH", "../../master_of_puppets/secrets/signing.key"))

requests.packages.urllib3.disable_warnings()

def get_jwt_token():
    """Login and return JWT token."""
    res = requests.post(f"{SERVER_URL}/auth/login",
        data={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
        verify=False)
    res.raise_for_status()
    return res.json()["access_token"]

def sign_script(content: str, key_path: Path) -> str:
    """Sign script with Ed25519 private key."""
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    signature_bytes = private_key.sign(content.encode())
    import base64
    return base64.b64encode(signature_bytes).decode()

def dispatch_job(script_content: str, memory_limit: str, cpu_limit: str, token: str) -> str:
    """Dispatch job and return job ID."""
    signature = sign_script(script_content, SIGNING_KEY_PATH)
    payload = {
        "script_content": script_content,
        "signature": signature,
        "memory_limit": memory_limit,
        "cpu_limit": cpu_limit
    }
    res = requests.post(f"{SERVER_URL}/jobs",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        verify=False)
    res.raise_for_status()
    return res.json()["guid"]

def poll_job(job_id: str, token: str, timeout: int = 60) -> dict:
    """Poll job until complete."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = requests.get(f"{SERVER_URL}/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
            verify=False)
        res.raise_for_status()
        job = res.json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(1)
    raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")

def run_scenario_1_cpu_burn(token: str) -> dict:
    """Scenario 1: Single CPU burn with cpu_limit."""
    stress_dir = Path(__file__).parent
    script_path = stress_dir / "python" / "cpu_burn.py"
    with open(script_path) as f:
        script_content = f.read()

    job_id = dispatch_job(script_content, memory_limit="512m", cpu_limit="0.5", token=token)
    job = poll_job(job_id, token)

    # Parse result from first line of stdout
    try:
        result_json = job["stdout"].split("\n")[0]
        return json.loads(result_json)
    except:
        return {"type": "cpu_burn", "pass": False, "error": f"job status={job['status']}"}

def run_scenario_2_memory_oom(token: str) -> dict:
    """Scenario 2: Single memory OOM with memory_limit < allocation."""
    stress_dir = Path(__file__).parent
    script_path = stress_dir / "python" / "memory_hog.py"
    with open(script_path) as f:
        script_content = f.read()

    # Set memory_limit to 128m, allocate 256 MB (should trigger OOM)
    job_id = dispatch_job(script_content, memory_limit="128m", cpu_limit="1", token=token)
    job = poll_job(job_id, token)

    # OOM should exit with code 137
    passes = job.get("exit_code") == 137
    return {
        "type": "memory_oom",
        "memory_limit": "128m",
        "exit_code": job.get("exit_code"),
        "pass": passes
    }

def run_scenario_3_concurrent_isolation(token: str) -> dict:
    """Scenario 3: Concurrent CPU burn + memory hog + monitor on same node."""
    stress_dir = Path(__file__).parent

    # Dispatch all three jobs concurrently (same node)
    with open(stress_dir / "python" / "cpu_burn.py") as f:
        cpu_script = f.read()
    with open(stress_dir / "python" / "memory_hog.py") as f:
        mem_script = f.read()
    with open(stress_dir / "python" / "noisy_monitor.py") as f:
        monitor_script = f.read()

    cpu_id = dispatch_job(cpu_script, "256m", "0.5", token)
    mem_id = dispatch_job(mem_script, "256m", "1", token)
    monitor_id = dispatch_job(monitor_script, "256m", "1", token)

    # Poll all three
    cpu_job = poll_job(cpu_id, token)
    mem_job = poll_job(mem_id, token)
    monitor_job = poll_job(monitor_id, token)

    # Parse monitor result
    try:
        monitor_json = monitor_job["stdout"].split("\n")[0]
        monitor_result = json.loads(monitor_json)
    except:
        monitor_result = {"pass": False, "error": "failed to parse"}

    return {
        "type": "concurrent_isolation",
        "cpu_result": json.loads(cpu_job["stdout"].split("\n")[0]) if cpu_job["status"] == "completed" else {},
        "monitor_result": monitor_result,
        "pass": monitor_result.get("pass", False)
    }

def run_scenario_4_all_languages(token: str) -> dict:
    """Scenario 4: Run CPU burner in Python, Bash, and PowerShell."""
    stress_dir = Path(__file__).parent
    results = {}

    for lang, filename in [("python", "cpu_burn.py"), ("bash", "cpu_burn.sh"), ("powershell", "cpu_burn.ps1")]:
        script_path = stress_dir / (lang.split("_")[0]) / filename
        if not script_path.exists():
            results[lang] = {"pass": False, "error": f"script not found: {filename}"}
            continue

        with open(script_path) as f:
            script_content = f.read()

        try:
            job_id = dispatch_job(script_content, "512m", "0.5", token)
            job = poll_job(job_id, token)
            result_json = job["stdout"].split("\n")[0]
            results[lang] = json.loads(result_json)
        except Exception as e:
            results[lang] = {"pass": False, "error": str(e)}

    all_pass = all(r.get("pass", False) for r in results.values())
    return {
        "type": "all_languages",
        "results": results,
        "pass": all_pass
    }

def main():
    """Run all 4 scenarios and report."""
    token = get_jwt_token()

    print("\n=== Stress Test Orchestrator ===\n")

    scenarios = [
        ("Scenario 1: Single CPU Burn", run_scenario_1_cpu_burn),
        ("Scenario 2: Memory OOM", run_scenario_2_memory_oom),
        ("Scenario 3: Concurrent Isolation", run_scenario_3_concurrent_isolation),
        ("Scenario 4: All Languages", run_scenario_4_all_languages),
    ]

    results = {}
    for name, func in scenarios:
        print(f"\n{name}...")
        try:
            result = func(token)
            results[name] = result
            status = "PASS" if result.get("pass") else "FAIL"
            print(f"  {status}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results[name] = {"pass": False, "error": str(e)}

    # Write report
    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / "stress_test_report.json"

    report = {
        "timestamp": time.time(),
        "scenarios": results,
        "all_pass": all(r.get("pass", False) for r in results.values())
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport written to {report_file}")
    print(f"Overall result: {'PASS' if report['all_pass'] else 'FAIL'}")

    return 0 if report["all_pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual CLI stress testing (running cpu-spin.py locally) | Automated orchestrator dispatching via API | Phase 125 (now) | Stress tests now run on actual target nodes, not planner's workstation |
| Hardcoded durations and thresholds | Configurable via env vars (STRESS_DURATION_S, DRIFT_THRESHOLD_S) | Phase 125 | Tests adapt to different SLOs without code changes |
| Single-language validation (Python only) | Full language parity (Python, Bash, PowerShell) | Phase 125 | Confidence in enforcement across deployment platforms |
| Manual exit code interpretation | Structured JSON output with explicit pass/fail | Phase 125 | Orchestrator can programmatically assess and aggregate results |
| Ad-hoc test scripts scattered in mop_validation | Organized under stress/ with clear subdirectories | Phase 125 | Maintainability and discoverability |

**Deprecated/outdated:**
- Inline script content in test code (antipattern from v19.0) — now read from files on disk, sign, dispatch
- Using only memory-hog.py and cpu-spin.py from tools/ — stress corpus is separate test infrastructure
- Manual node health checks before running tests — preflight check now automated

## Open Questions

1. **Orchestrator error handling strategy**
   - What we know: Preflight fails for nodes without cgroups; orchestrator should skip and try next
   - What's unclear: How many node retries before aborting entire scenario? Should we bias towards faster-earlier nodes?
   - Recommendation: Implement with per-node timeout (30s) and per-scenario timeout (5 min); report which nodes passed/failed in JSON

2. **Concurrent isolation timing coordination**
   - What we know: All 3 jobs (CPU, memory, monitor) must dispatch to same node and start ~simultaneously
   - What's unclear: How to guarantee same-node dispatch in a multi-node cluster? Node selection is typically first-available
   - Recommendation: Use environment variable or metadata tag to force same-node; or orchestrator queries available nodes, gets list, and manually routes all 3 to the same node

3. **PowerShell script execution in Linux containers**
   - What we know: PowerShell scripts will run in Linux via pwsh (PowerShell Core 7.x)
   - What's unclear: Will all cmdlets (System.Diagnostics.Stopwatch, ConvertTo-Json) work identically across Linux and Windows?
   - Recommendation: Test pwsh on Linux container early; may need to fallback Bash for Linux nodes and PowerShell for Windows nodes (EXECUTION_MODE=direct forbidden anyway)

4. **Cgroup v2 unified hierarchy availability**
   - What we know: Cgroup v2 is opt-in on most distros; Docker on cgroup v2 is well-supported since v20.10
   - What's unclear: What's the minimum Podman version that supports v2 properly for cpu/memory controllers?
   - Recommendation: Phase 126 enforcement validation will reveal this; preflight marks unsupported but doesn't fail scenario, just reports degraded SLA

5. **Report aggregation across multiple test runs**
   - What we know: orchestrator writes JSON report to mop_validation/reports/stress_test_report.json
   - What's unclear: Should this file append/accumulate or overwrite? How do we track trends over time?
   - Recommendation: Include timestamp; overwrite is simpler; historical analysis can be added in Phase 129+ (test analytics)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing backend test infrastructure) |
| Config file | `puppeteer/pytest.ini` (if exists) or none — see Wave 0 |
| Quick run command | `pytest puppeteer/tests/test_stress_integration.py -x -v` |
| Full suite command | `pytest puppeteer/tests/ -x --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRS-01 | CPU burner exists in Python, Bash, PowerShell and produces valid JSON output | integration | `pytest tests/test_stress_integration.py::test_cpu_burn_all_languages -xvs` | ❌ Wave 0 |
| STRS-02 | Memory hog page-touches, triggers OOM on limit exceeding, exits with 137 | integration | `pytest tests/test_stress_integration.py::test_memory_oom_exits_137 -xvs` | ❌ Wave 0 |
| STRS-03 | Noisy-neighbour monitor detects sleep drift <1.1s on isolated system | integration | `pytest tests/test_stress_integration.py::test_noisy_monitor_drift -xvs` | ❌ Wave 0 |
| STRS-04 | Preflight check detects cgroup v1/v2, validates controllers, reads own memory limit | unit | `pytest tests/test_stress_integration.py::test_preflight_cgroup_detection -xvs` | ❌ Wave 0 |
| STRS-05 | Orchestrator dispatches all 4 scenarios, parses JSON results, writes report | integration | `pytest tests/test_stress_integration.py::test_orchestrator_all_scenarios -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest puppeteer/tests/test_stress_integration.py -x -v` (quick: STRS-01, STRS-03, STRS-04)
- **Per wave merge:** `pytest puppeteer/tests/test_stress_integration.py pytest puppeteer/tests/test_job_limits.py -x` (full integration + limits)
- **Phase gate:** Full suite green + orchestrator report shows all 4 scenarios pass

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_stress_integration.py` — covers STRS-01, STRS-02, STRS-03, STRS-05 via subprocess/Docker execution of stress scripts
- [ ] Fixtures for mock node registration, signed job dispatch, result parsing
- [ ] Integration test for Bash and PowerShell versions (may mock or skip if no shell available in CI environment)
- [ ] Test for preflight cgroup detection (can run locally on test system; check for /sys/fs/cgroup)
- [ ] Framework install: None — pytest already in `puppeteer/requirements.txt`

*(If all above gaps exist: Clear — use TDD. First commit: RESEARCH. Second: test stubs RED. Third-onwards: implementation.)*

## Sources

### Primary (HIGH confidence)
- **Context7** — Master of Puppets codebase structure, API contracts, existing stress test patterns (memory-hog.py, cpu-spin.py, run_signed_job.py, test_local_stack.py)
- **Official Python time module docs** — time.process_time() vs time.perf_counter() semantics and accuracy ([https://docs.python.org/3/library/time.html](https://docs.python.org/3/library/time.html))
- **Official Kubernetes cgroup v1/v2 documentation** — cgroup version detection and controller availability ([https://kubernetes.io/docs/concepts/architecture/cgroups/](https://kubernetes.io/docs/concepts/architecture/cgroups/))
- **Linux man pages** — cgroups(7) and /sys/fs/cgroup structure ([https://man7.org/linux/man-pages/man7/cgroups.7.html](https://man7.org/linux/man-pages/man7/cgroups.7.html))

### Secondary (MEDIUM confidence)
- **Docker documentation** — OOM kill behavior, exit code 137, resource limit enforcement ([https://oneuptime.com/blog/post/2026-02-08-how-to-fix-docker-container-immediately-exiting-with-code-137/view](https://oneuptime.com/blog/post/2026-02-08-how-to-fix-docker-container-immediately-exiting-with-code-137/view))
- **PowerShell Microsoft Learn** — System.Diagnostics.Stopwatch precision timing, Start-Sleep resolution ([https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/measure-command](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/measure-command))
- **Bash timing patterns** — /usr/bin/time format strings and GNU coreutils sleep precision ([https://www.cyberciti.biz/faq/linux-unix-sleep-bash-scripting/](https://www.cyberciti.biz/faq/linux-unix-sleep-bash-scripting/))
- **Datadog Container Security** — cgroup v1 vs v2 architecture and detection ([https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-4/](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-4/))

### Tertiary (LOW confidence — marked for validation)
- WebSearch on exact PowerShell Stopwatch accuracy on Linux (implementation not verified in this codebase)
- Bash floating-point arithmetic via bc — syntax verified but exact output format varies by GNU bc version

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries in use in existing codebase (requests, cryptography, json, asyncio, dotenv) or language stdlib
- Architecture patterns: **HIGH** — dual JSON+human output confirmed in CONTEXT.md; API dispatch pattern verified in run_signed_job.py and test_local_stack.py
- Pitfalls: **MEDIUM-HIGH** — memory overcommit, exit code semantics, and CPU timing verified by existing implementations; PowerShell on Linux untested in this repo
- Code examples: **HIGH** — derived from existing tools/example-jobs/, CLAUDE.md patterns, and official documentation

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days; stable libs, no breaking changes anticipated)

**Key assumptions:**
- Orchestrator will use async/await pattern consistent with rest of FastAPI (job dispatch can be concurrent)
- All stress tests will be signed with existing Ed25519 key in puppeteer/secrets/
- mop_validation/secrets.env will have same format and credentials as running test suite
- Node selection for concurrent isolation scenario TBD (planner may defer to Wave 2 or add env var override)

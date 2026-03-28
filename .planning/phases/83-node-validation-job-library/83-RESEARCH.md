# Phase 83: Node Validation Job Library - Research

**Researched:** 2026-03-28
**Domain:** Job script corpus creation, signing workflow documentation, YAML manifest design, MkDocs runbook authoring
**Confidence:** HIGH

## Summary

Phase 83 is primarily a content-creation phase: write a set of job scripts (Bash, Python, PowerShell hello-worlds plus four validation jobs), wire them into a `manifest.yaml`, and document the operator workflow in both a community-facing catalog and an MkDocs runbook. No new backend API routes are required — this is explicitly out of scope per REQUIREMENTS.md.

The key technical subtleties are in the resource-limit jobs (JOB-06, JOB-07) and the network filtering job (JOB-05). Resource limit jobs must detect the `resource_limits_supported` capability at script entry and fail fast with a clear message when absent, rather than relying on the container runtime to enforce limits. The network job must use Docker-native `--network=none` only — no direct iptables manipulation — per a locked decision in STATE.md. The volume mapping job must write a sentinel file inside the container and verify readability from the expected host-side mount path.

The signing workflow is already fully documented: `axiom-push job push --script <file> --key signing.key --key-id <id>` followed by a dashboard Publish step. Jobs are committed unsigned; the runbook instructs operators to sign with their existing Axiom signing key.

**Primary recommendation:** Implement all seven scripts, manifest, community catalog README, and MkDocs runbook as a single unit of work that can be reviewed together. The scripts themselves are short; the documentation quality is the primary deliverable.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Job corpus location**
- Directory: `tools/example-jobs/` in the main public repo
- Vision: community-maintained job library for Axiom operators (like an awesome-list for Axiom jobs)
- Structure: subdirectories by runtime — `bash/`, `python/`, `pwsh/` — plus `validation/` for the node-check corpus (volume, network, resource limit jobs)
- `README.md` at `tools/example-jobs/` root serves as the community catalog: table with job name, runtime, description, required capabilities
- Validation-specific jobs live in `tools/example-jobs/validation/` alongside the runtime example dirs

**Signing workflow**
- Jobs are committed **unsigned** — no pre-signed scripts or companion `.sig` files
- The runbook documents the operator workflow: sign with their existing axiom-push key, then dispatch
- Signing key: operator's already-registered Axiom signing key (no new key setup required)
- Community contributors follow the same workflow for their own additions

**Resource limit job behavior (JOB-06, JOB-07)**
- Resource limit jobs require `resource_limits_supported` capability on the target node
- If dispatched to a node without this capability: job exits with **code 1** and a clear message (e.g., "FAIL: resource limits are not supported on this node (resource_limits_supported capability missing)")
- Status will show FAILED — this is intentional and indicates misconfigured dispatch, not a node problem
- Carrying forward from STATE.md: cgroup v2 enforcement is unreliable on LXC nodes; gate these jobs on the capability flag

**Runbook format & location**
- Two documents serving different audiences:
  - `tools/example-jobs/README.md` — community catalog (awesome-list style table of all jobs)
  - `docs/runbooks/node-validation.md` — operator workflow guide in the MkDocs docs site
- Runbook depth: **job-by-job reference** with dispatch commands — not a prose walkthrough
- Each job entry in the runbook: what it tests, required capabilities, example dispatch command (axiom-push sign + API call or dashboard), expected PASS output sample, expected FAIL output sample (truncated stdout)
- Output samples included for every job — helps operators distinguish "expected FAILED" (e.g., resource limit test working correctly) from a real problem

**Job manifest**
- File: `tools/example-jobs/manifest.yaml` — YAML with job metadata + dispatch parameters
- Content per job: `name`, `description`, `script`, `runtime`, `required_capabilities`, `target_tags` (optional), `memory_limit` + `cpu_limit` (for resource test jobs)
- No batch-dispatch helper script in v15 — manifest is documentation, not a runner; community can build on it later
- Resource limit job defaults in manifest:
  - `memory_hog.py`: allocates 256m — test against a node configured with 128m limit (inversion logic explained in runbook)
  - `cpu_spin.py`: requests 2.0 CPUs — test against a node with 0.5 CPU limit
  - Runbook explains how to adjust values for different node configurations

### Claude's Discretion
- Exact script content for hello-world jobs (what they print, how verbose)
- Network filtering job implementation details (which DNS/HTTP check approach)
- Volume mapping job specifics (temp file approach, path conventions)
- manifest.yaml field naming conventions

### Deferred Ideas (OUT OF SCOPE)
- Batch-dispatch helper script (`run_validation.py` that reads manifest and dispatches all jobs) — noted for community contribution or a future phase
- JOB-08: Validation job library extended to cover EE-specific features (signed attestation, execution history API) — already in backlog
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JOB-01 | Operator can dispatch a signed bash reference job and verify it executes successfully on a bash-capable node | `bash/hello.sh` in `tools/example-jobs/bash/`; uses `runtime: bash` in manifest; runbook documents dispatch |
| JOB-02 | Operator can dispatch a signed Python reference job and verify it executes successfully on a Python-capable node | `python/hello.py` in `tools/example-jobs/python/`; uses `runtime: python` in manifest |
| JOB-03 | Operator can dispatch a signed PowerShell reference job and verify it executes successfully on a PWSH-capable node | `pwsh/hello.ps1` in `tools/example-jobs/pwsh/`; uses `runtime: powershell` in manifest |
| JOB-04 | A signed volume mapping validation job verifies files written inside the container persist at the expected host-side mount path | `validation/volume-mapping.py` or `.sh`; job writes a sentinel file + verifies readability at expected mount path |
| JOB-05 | A signed network filtering validation job verifies that allowed hosts are reachable and blocked hosts are not | `validation/network-filter.py`; uses `--network=none` (Docker-native isolation only, no iptables); checks DNS/HTTP connectivity and absence thereof |
| JOB-06 | A signed memory-hog job is killed (OOM) rather than completing when it exceeds its node memory limit | `validation/memory-hog.py`; allocates 256m; gate on `resource_limits_supported` capability; if absent exits code 1 with FAIL message |
| JOB-07 | A signed CPU-spin job is throttled or killed when it exceeds its node CPU limit | `validation/cpu-spin.py`; spins 2 CPUs; gate on `resource_limits_supported` capability; same exit-1 guard |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.x | hello.py, validation scripts | Already in every node image |
| Bash | any | hello.sh | Present on all Linux nodes |
| PowerShell | 7+ | hello.ps1 | Required for PWSH-capable nodes |
| PyYAML | any | manifest.yaml format | YAML is the conventional choice for job manifests (human-writable, structured) |
| MkDocs Material | installed | `docs/runbooks/node-validation.md` | Already the site framework; uses admonition + tabbed extensions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axiom-push CLI | current | Sign and dispatch jobs | All dispatch examples in the runbook |
| cryptography (Ed25519) | installed in node | Signature verification at node | Already in node.py — job scripts do NOT need to call this |

**Installation:** No new packages required. All scripts use stdlib only (Python) or shell built-ins (Bash). The `memory_hog.py` and `cpu_spin.py` scripts use Python `ctypes` or `bytearray` (no external dependencies for memory allocation) and `multiprocessing` or busy loops (no dependencies for CPU spin).

---

## Architecture Patterns

### Recommended Project Structure
```
tools/
├── __init__.py                      # existing empty placeholder
└── example-jobs/
    ├── README.md                    # community catalog (awesome-list table)
    ├── manifest.yaml                # job metadata + dispatch parameters
    ├── bash/
    │   └── hello.sh                 # JOB-01
    ├── python/
    │   └── hello.py                 # JOB-02
    ├── pwsh/
    │   └── hello.ps1                # JOB-03
    └── validation/
        ├── volume-mapping.sh        # JOB-04
        ├── network-filter.py        # JOB-05
        ├── memory-hog.py            # JOB-06
        └── cpu-spin.py              # JOB-07

docs/docs/runbooks/
└── node-validation.md               # operator workflow guide (new)
```

MkDocs nav entry goes under `Runbooks:` in `docs/mkdocs.yml`.

### Pattern 1: Hello-World Job (JOB-01, JOB-02, JOB-03)
**What:** Minimal script that prints identifying info to stdout and exits 0.
**When to use:** Verify a node can receive, verify, and execute a job in a given runtime.
**Example (Python):**
```python
#!/usr/bin/env python3
# tools/example-jobs/python/hello.py
import platform, datetime, socket

print("=== Axiom Hello-World (Python) ===")
print(f"Host:    {socket.gethostname()}")
print(f"OS:      {platform.system()} {platform.release()}")
print(f"Python:  {platform.python_version()}")
print(f"Time:    {datetime.datetime.utcnow().isoformat()}Z")
print("=== PASS ===")
```

**Example (Bash):**
```bash
#!/usr/bin/env bash
# tools/example-jobs/bash/hello.sh
set -euo pipefail
echo "=== Axiom Hello-World (Bash) ==="
echo "Host:    $(hostname)"
echo "OS:      $(uname -sr)"
echo "Bash:    ${BASH_VERSION}"
echo "Time:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== PASS ==="
```

**Example (PowerShell):**
```powershell
# tools/example-jobs/pwsh/hello.ps1
Write-Host "=== Axiom Hello-World (PowerShell) ==="
Write-Host "Host:    $($env:COMPUTERNAME ?? (hostname))"
Write-Host "OS:      $([System.Runtime.InteropServices.RuntimeInformation]::OSDescription)"
Write-Host "PS:      $($PSVersionTable.PSVersion)"
Write-Host "Time:    $((Get-Date).ToUniversalTime().ToString('o'))"
Write-Host "=== PASS ==="
```

### Pattern 2: Resource Guard (JOB-06, JOB-07)
**What:** Check for `resource_limits_supported` in node capabilities (exposed via `AXIOM_CAPABILITIES` env var injected by the node worker), exit 1 with a clear message if absent, then proceed with the stress behaviour.
**When to use:** Any job that only makes sense when container resource limits are enforced at runtime.

The node worker injects job payload fields as environment variables. The `required_capabilities` field in the job payload gates node selection at the orchestrator level (orchestrator will not assign the job to a node without the capability), but the script-level guard provides a defense-in-depth message for operators who dispatch without `required_capabilities` set.

**Key insight from existing code:** `job_service.py` already enforces capability matching before assignment (lines 471–487). Setting `required_capabilities: {resource_limits_supported: "1.0"}` in the job payload is the primary gate; the script-level check is secondary / for clear operator messaging.

```python
#!/usr/bin/env python3
# tools/example-jobs/validation/memory-hog.py
import os, sys, time

# Capability guard
caps_raw = os.environ.get("AXIOM_CAPABILITIES", "")
if "resource_limits_supported" not in caps_raw:
    print("FAIL: resource limits are not supported on this node "
          "(resource_limits_supported capability missing)", flush=True)
    sys.exit(1)

print("resource_limits_supported: present — proceeding with memory allocation test")
print("Allocating 256 MB ...", flush=True)
# Allocate 256 MB and hold it
chunk = bytearray(256 * 1024 * 1024)
print("Allocation complete — container should be OOM-killed or exceed memory limit")
time.sleep(30)  # Hold until killed
print("ERROR: should have been killed before reaching this line")
sys.exit(2)
```

### Pattern 3: Volume Mapping Validation (JOB-04)
**What:** Write a sentinel file inside the container at a known path, then read it back to confirm the mount is bidirectional. Uses the host-side mount path exposed via an env var.
**When to use:** Confirming that node volume mounts are correctly wired.

```bash
#!/usr/bin/env bash
# tools/example-jobs/validation/volume-mapping.sh
set -euo pipefail

MOUNT_PATH="${AXIOM_VOLUME_PATH:-/mnt/axiom-data}"
SENTINEL="${MOUNT_PATH}/axiom-validation-$$.txt"

echo "=== Volume Mapping Validation ==="
echo "Mount path: ${MOUNT_PATH}"

if [[ ! -d "${MOUNT_PATH}" ]]; then
    echo "FAIL: mount path ${MOUNT_PATH} does not exist inside container"
    exit 1
fi

echo "Writing sentinel: ${SENTINEL}"
echo "axiom-validation-$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${SENTINEL}"

echo "Reading back sentinel:"
cat "${SENTINEL}"
rm -f "${SENTINEL}"
echo "=== PASS: volume mount is readable and writable ==="
```

### Pattern 4: Network Filtering Validation (JOB-05)
**What:** Test connectivity to an allowed host and confirm a blocked host times out. Uses Docker `--network=none` — the network isolation is configured at job dispatch time via node network configuration, not via iptables in the script.
**When to use:** Confirming node network filtering is working before running production workloads that must be isolated.

**LOCKED CONSTRAINT:** No iptables manipulation in the script. The job only validates existing network isolation. The runbook explains that the operator must configure the node with `--network=none` (or equivalent network policy) before dispatching.

```python
#!/usr/bin/env python3
# tools/example-jobs/validation/network-filter.py
import urllib.request, socket, sys, os

ALLOWED = os.environ.get("AXIOM_ALLOWED_HOST", "")
BLOCKED = os.environ.get("AXIOM_BLOCKED_HOST", "8.8.8.8")

print("=== Network Filtering Validation ===")
print(f"Allowed host: {ALLOWED or '(none set — skipping allowed-host check)'}")
print(f"Blocked host: {BLOCKED}")

# Check blocked host — expect timeout/refusal
try:
    socket.setdefaulttimeout(5)
    socket.create_connection((BLOCKED, 80), timeout=5)
    print(f"FAIL: connected to blocked host {BLOCKED} — network isolation is NOT active")
    sys.exit(1)
except (socket.timeout, OSError):
    print(f"PASS: blocked host {BLOCKED} is unreachable (expected)")

# Check allowed host if configured
if ALLOWED:
    try:
        socket.create_connection((ALLOWED, 80), timeout=5)
        print(f"PASS: allowed host {ALLOWED} is reachable")
    except Exception as e:
        print(f"WARN: allowed host {ALLOWED} unreachable: {e}")

print("=== network-filter validation complete ===")
```

### Pattern 5: manifest.yaml Structure
```yaml
# tools/example-jobs/manifest.yaml
version: "1"
jobs:
  - name: hello-bash
    description: "Hello-world job for bash-capable nodes"
    script: bash/hello.sh
    runtime: bash
    required_capabilities: {}

  - name: hello-python
    description: "Hello-world job for Python-capable nodes"
    script: python/hello.py
    runtime: python
    required_capabilities: {}

  - name: hello-pwsh
    description: "Hello-world job for PowerShell-capable nodes"
    script: pwsh/hello.ps1
    runtime: powershell
    required_capabilities: {}

  - name: validation-volume-mapping
    description: "Confirms container volume mounts are readable and writable"
    script: validation/volume-mapping.sh
    runtime: bash
    required_capabilities: {}

  - name: validation-network-filter
    description: "Confirms network isolation is active on the target node"
    script: validation/network-filter.py
    runtime: python
    required_capabilities: {}

  - name: validation-memory-hog
    description: "OOM validation: job should be killed before completing"
    script: validation/memory-hog.py
    runtime: python
    required_capabilities:
      resource_limits_supported: "1.0"
    memory_limit: "256m"

  - name: validation-cpu-spin
    description: "CPU throttle validation: job should be throttled or killed"
    script: validation/cpu-spin.py
    runtime: python
    required_capabilities:
      resource_limits_supported: "1.0"
    cpu_limit: "2.0"
```

### Pattern 6: MkDocs Runbook Structure
The existing runbooks (`jobs.md`, `nodes.md`, `foundry.md`) follow a consistent pattern:
- H2 section per scenario
- `**Recovery steps:**` list
- `**Verify it worked:**` paragraph
- Admonition blocks (`!!! warning`, `!!! tip`) for emphasis

`node-validation.md` should follow a per-job reference format instead (since it is not a troubleshooting guide but a how-to). Each job entry:
1. H2: job name
2. What it tests (1 sentence)
3. Required capabilities table
4. Dispatch commands (axiom-push sign + publish steps)
5. Expected PASS output block
6. Expected FAIL output block

MkDocs nav entry (append to `docs/mkdocs.yml` under `Runbooks:`):
```yaml
    - Node Validation: runbooks/node-validation.md
```

### Anti-Patterns to Avoid
- **iptables manipulation in scripts:** Violates the locked network filtering constraint. The job must only validate existing isolation, not create it.
- **Pre-signed scripts in the repo:** All scripts are committed unsigned. No `.sig` companion files.
- **Platform-specific stdlib imports:** `memory-hog.py` should use `bytearray` (pure Python, no ctypes or platform checks needed for allocation).
- **Hardcoded host names in network-filter.py:** Use env vars (`AXIOM_ALLOWED_HOST`, `AXIOM_BLOCKED_HOST`) so operators can parametrize for their network without editing the script (and thus re-signing it).
- **`sys.exit(0)` in memory-hog / cpu-spin:** These jobs should NOT have a clean exit path. OOM kill is the expected outcome; any code after the allocation hold is an error sentinel.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Memory allocation for OOM test | ctypes.memmove, mmap hacks | `bytearray(N)` | Pure Python, no imports, predictable RSS allocation |
| CPU saturation loop | Custom C extension, `os.fork()` storm | `while True: pass` (single thread) or `multiprocessing.Pool` | Simple and produces measurable CPU usage |
| YAML serialization | Custom format | Standard YAML with `version:` key | Human-writable, diff-friendly, matches community convention |
| Network connectivity check | Raw socket frame inspection | `socket.create_connection()` with timeout | Sufficient to verify block/allow without privileges |

---

## Common Pitfalls

### Pitfall 1: `resource_limits_supported` — capability name must match exactly
**What goes wrong:** The orchestrator capability matching is string-exact. If the script checks `"resource_limits_supported"` but the node registers `"resource-limits-supported"` (hyphen), the job is dispatched but the guard fails.
**Why it happens:** Capability names are stored as free-form strings in the `capabilities` JSON column in the DB. There is no schema validation.
**How to avoid:** Verify the exact capability key registered on target test nodes before writing the runbook dispatch examples. Document the expected key name in both the manifest and the runbook.
**Warning signs:** Job dispatches successfully (node has the capability by some name) but the script prints the FAIL message.

### Pitfall 2: Memory allocation does not guarantee RSS growth
**What goes wrong:** `bytearray(256 * 1024 * 1024)` allocates virtual address space but Linux may not commit pages until they are written. The container may not trigger OOM until pages are touched.
**Why it happens:** Linux overcommit — allocation does not equal RSS.
**How to avoid:** Write to the allocated buffer after allocation: `chunk[0::4096] = b'\x00' * (len(chunk) // 4096)` — this touches every 4 KB page and forces RSS commitment. The runbook should note this.
**Warning signs:** memory-hog job completes with exit 0 on a correctly-limited node.

### Pitfall 3: CPU-spin job timing out before throttle is observed
**What goes wrong:** The node's default container timeout (30s in `runtime.py`) kills the job via timeout, not throttle. The operator sees exit code -1 (timeout) instead of measurable throttle.
**Why it happens:** `runtime.py ContainerRuntime.run()` has `timeout=30` default. A CPU-spin job that runs for 30s triggers the timeout kill path, not the CPU limit kill path.
**How to avoid:** The job should run for a short fixed period (5–10 seconds) and report CPU time consumed vs wall time. Throttle is visible when `cpu_time / wall_time < 0.5`. The job does not need to be killed — it completes and prints the ratio. The runbook explains: "on a 0.5 CPU node, a 5-second wall-clock spin will consume approximately 2.5 CPU-seconds rather than 5."
**Warning signs:** Job exits with FAILED and stderr shows "timed out".

### Pitfall 4: Volume mapping job — mount path not exposed in default job dispatch
**What goes wrong:** The volume-mapping job needs to know where the host-side mount is. If no `AXIOM_VOLUME_PATH` env var is set, the job falls back to a default path that may not be mounted.
**Why it happens:** Volume mounts are node-level config, not job-level. The job cannot know the mount topology without operator input.
**How to avoid:** The runbook must explain that the operator sets `AXIOM_VOLUME_PATH` in the job's `env` payload at dispatch time and configures the matching volume on the node before dispatching. The script's fallback default (`/mnt/axiom-data`) should match the example node config in the runbook.
**Warning signs:** Job prints "FAIL: mount path does not exist".

### Pitfall 5: PowerShell `$env:COMPUTERNAME` unavailable on Linux
**What goes wrong:** `$env:COMPUTERNAME` is a Windows environment variable. On Linux with PowerShell 7, it may be empty.
**Why it happens:** Linux does not set `COMPUTERNAME` by default.
**How to avoid:** Use `$(hostname)` as fallback in the `hello.ps1` script. PowerShell 7 supports `$(hostname)` via command substitution. The null-coalescing operator `??` is available in PowerShell 7+.
**Warning signs:** COMPUTERNAME line in hello output is blank.

### Pitfall 6: MkDocs nav entry missing
**What goes wrong:** `docs/runbooks/node-validation.md` is created but not added to `docs/mkdocs.yml` nav. The page is orphaned — accessible by direct URL but not linked from the sidebar.
**Why it happens:** MkDocs Material requires explicit nav entries; it does not auto-discover pages.
**How to avoid:** Update `docs/mkdocs.yml` `Runbooks:` section to add `- Node Validation: runbooks/node-validation.md`. Also update `docs/docs/runbooks/index.md` guide table.
**Warning signs:** MkDocs build produces "Documentation file ... is not in the docs_dir" or "not found in nav" warnings.

### Pitfall 7: `required_capabilities` dispatch field format
**What goes wrong:** `capability_requirements` in `JobCreate` is `Optional[Dict[str, str]]` — version strings, not booleans. Dispatching with `{"resource_limits_supported": true}` (boolean) fails validation.
**Why it happens:** The model requires string values for semver comparison. See `models.py` line 11.
**How to avoid:** Manifest and runbook dispatch examples must use `"resource_limits_supported": "1.0"` (string), not `true`.

---

## Code Examples

Verified patterns from existing codebase:

### Job dispatch via API (from main.py / axiom-push docs)
```python
# POST /api/jobs
{
    "task_type": "script",
    "runtime": "python",          # or "bash" or "powershell"
    "payload": {
        "script_content": "<script text>",
        "signature": "<base64 Ed25519 sig>",
        "signature_id": "<uuid of registered public key>"
    },
    "capability_requirements": {"resource_limits_supported": "1.0"},  # string value
    "memory_limit": "256m",
    "cpu_limit": "2.0"
}
```

### axiom-push dispatch (from feature-guides/axiom-push.md)
```bash
# Sign and push to staging
axiom-push job push \
  --script tools/example-jobs/python/hello.py \
  --key signing.key \
  --key-id <your-key-id>

# Then publish from dashboard Staging tab
```

### Capability matching in job_service.py (lines 471–487)
```python
# Existing logic — capability values are version-compared as strings
req_caps = json.loads(job.capability_requirements)
for cap_name, min_version in req_caps.items():
    if cap_name not in node_caps_dict:
        return False  # node does not have capability — skip this node
    node_ver = node_caps_dict[cap_name]
    satisfies = Version(node_ver) >= Version(min_version)
    if not satisfies:
        return False
```

### Memory page-touching pattern (Python stdlib)
```python
# Force RSS growth after allocation
chunk = bytearray(256 * 1024 * 1024)
chunk[0::4096] = b'\x00' * (len(chunk) // 4096)
```

### CPU-spin with measurable throttle indicator
```python
import time, os

DURATION = 5  # seconds

start_wall = time.monotonic()
start_cpu  = time.process_time()

deadline = start_wall + DURATION
while time.monotonic() < deadline:
    _ = 2 ** 31  # busy arithmetic

wall = time.monotonic() - start_wall
cpu  = time.process_time() - start_cpu
ratio = cpu / wall if wall > 0 else 0

print(f"Wall time: {wall:.2f}s  CPU time: {cpu:.2f}s  Ratio: {ratio:.2f}")
if ratio < 0.8:
    print(f"PASS: CPU throttling confirmed (ratio {ratio:.2f} < 0.8 indicates <80% CPU share)")
else:
    print(f"INFO: No throttling detected (ratio {ratio:.2f}). "
          f"Ensure node cpu_limit is set below 1.0 CPU.")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `EXECUTION_MODE=direct` | Not supported — raises RuntimeError at node startup | Phase 82 / node.py line 56 | Resource limit jobs that relied on direct mode subprocess no longer exist. All jobs run containerized. |
| `admin_signer.py` for signing | `axiom-push job push` CLI | Phase 83 onward | Runbook references `axiom-push`, not `admin_signer.py` |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct`: Removed. node.py explicitly raises RuntimeError if set. Do not reference this mode in any documentation.
- Bare list format for Blueprint packages: must be `{"python": [...]}` dict. Not relevant to this phase but noted for awareness.

---

## Open Questions

1. **Exact `resource_limits_supported` capability key name in use on existing nodes**
   - What we know: Capability names are free-form strings. The exact key name determines both `required_capabilities` in the manifest and the script-level guard string.
   - What's unclear: Whether existing nodes (in `mop_validation/local_nodes/`) declare `resource_limits_supported` or use a different string.
   - Recommendation: Before writing runbook dispatch examples, check an online Docker-mode node's capabilities panel in the dashboard or run `docker exec <node> env | grep AXIOM_CAPABILITIES`. If the key does not exist yet, the runbook must explain how to register it.

2. **AXIOM_CAPABILITIES env var — is it injected into job containers?**
   - What we know: node.py passes env vars from the job payload to the container. It is not confirmed that node capabilities are injected as a standard env var.
   - What's unclear: Whether the script-level capability guard pattern (`os.environ.get("AXIOM_CAPABILITIES")`) works or if an alternative guard is needed.
   - Recommendation: At plan time, verify whether node.py injects any capability-related env var into job containers. If not, the resource-limit jobs should instead rely solely on `required_capabilities` dispatch gating, and the script-level guard should be simplified to a doc comment explaining the orchestrator-level protection.

3. **Volume mount topology for JOB-04**
   - What we know: Volume mounts are node-level Docker config. The job cannot self-discover them.
   - What's unclear: Whether `mop_validation/local_nodes/` compose files include a standard data volume mount.
   - Recommendation: Plan for the runbook to provide a worked example with a specific `docker-compose` snippet that adds the volume mount and the corresponding `AXIOM_VOLUME_PATH` env var to the node container.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer/tests/) |
| Config file | none — pytest discovered by convention |
| Quick run command | `cd puppeteer && pytest tests/test_tools.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JOB-01 | bash/hello.sh exits 0 and prints expected headers | unit (file content check) | `pytest tests/test_example_jobs.py::test_hello_bash -x` | ❌ Wave 0 |
| JOB-02 | python/hello.py exits 0 and prints expected headers | unit (file content check) | `pytest tests/test_example_jobs.py::test_hello_python -x` | ❌ Wave 0 |
| JOB-03 | pwsh/hello.ps1 contains expected Write-Host calls | unit (file content check) | `pytest tests/test_example_jobs.py::test_hello_pwsh -x` | ❌ Wave 0 |
| JOB-04 | volume-mapping.sh writes and reads sentinel file | unit (script logic) | `pytest tests/test_example_jobs.py::test_volume_mapping -x` | ❌ Wave 0 |
| JOB-05 | network-filter.py exits 0/1 depending on connectivity | unit (mock socket) | `pytest tests/test_example_jobs.py::test_network_filter -x` | ❌ Wave 0 |
| JOB-06 | memory-hog.py exits 1 when capability missing | unit (env var mock) | `pytest tests/test_example_jobs.py::test_memory_hog_no_cap -x` | ❌ Wave 0 |
| JOB-07 | cpu-spin.py exits 1 when capability missing | unit (env var mock) | `pytest tests/test_example_jobs.py::test_cpu_spin_no_cap -x` | ❌ Wave 0 |
| JOB-01-07 | manifest.yaml parses cleanly and all script paths exist | unit (YAML parse + file exists) | `pytest tests/test_example_jobs.py::test_manifest_valid -x` | ❌ Wave 0 |

**Note:** Full end-to-end tests (actually dispatching jobs to a running node and confirming OOM kill) are integration tests that require a live Docker stack. These are verified manually per CLAUDE.md rules ("always rebuild and test inside the Docker stack containers"). The automated tests above verify script content correctness and unit logic only.

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_example_jobs.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_example_jobs.py` — covers JOB-01 through JOB-07 script content + manifest validation
- [ ] No framework install needed — pytest already present

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `puppets/environment_service/runtime.py` — `ContainerRuntime.run()` signature, memory/cpu limit flags
- Direct code inspection: `puppets/environment_service/node.py` — EXECUTION_MODE=direct removal, capability handling
- Direct code inspection: `puppeteer/agent_service/models.py` — `JobCreate`, `JobPushRequest`, `capability_requirements: Optional[Dict[str, str]]`
- Direct code inspection: `puppeteer/agent_service/services/job_service.py` — capability matching logic lines 471–487
- Direct code inspection: `docs/mkdocs.yml` — current nav structure and existing runbooks
- Direct code inspection: `docs/docs/feature-guides/axiom-push.md` — axiom-push sign + push workflow
- Direct code inspection: `docs/docs/runbooks/jobs.md` — existing runbook format and style

### Secondary (MEDIUM confidence)
- `.planning/phases/83-node-validation-job-library/83-CONTEXT.md` — locked decisions from discuss-phase session
- `.planning/STATE.md` — cross-phase decisions including network isolation constraint and LXC cgroup v2 caveat
- `.planning/REQUIREMENTS.md` — JOB-01 through JOB-07 requirement text

### Tertiary (LOW confidence)
- Linux memory overcommit behaviour (bytearray page-touching requirement) — well-established Linux kernel behaviour, not project-specific

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already installed; verified in codebase
- Architecture: HIGH — directory structure and manifest format derived from locked CONTEXT.md decisions
- Script patterns: HIGH — derived from existing runtime.py and job_service.py code
- Pitfalls: HIGH for API shape (verified in models.py); MEDIUM for capability env var injection (open question 2)
- Runbook format: HIGH — derived from existing runbooks in the docs

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable codebase, 30-day window)

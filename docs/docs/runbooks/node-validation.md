# Node Validation Job Library

The node validation corpus is a set of reference jobs at `tools/example-jobs/` that operators use to verify a node handles all supported runtimes and constraint types correctly. Scripts are committed unsigned — sign each one with your registered `axiom-push` key before dispatching. The manifest at `tools/example-jobs/manifest.yaml` contains machine-readable metadata for every job.

---

## hello-bash

**What it tests:** Verifies that the Bash runtime is available and that a job can be dispatched, signature-verified, and executed end-to-end on the node.

**Required capabilities:** None.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/bash/hello.sh \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
Hello from Axiom!
Hostname: node-a1b2c3d4
OS: Ubuntu 22.04.4 LTS
Bash: 5.1.16(1)-release
UTC: 2026-03-28T12:00:00Z
```

**Expected FAIL output:** N/A — this job has no expected failure path. If it fails, the node's Bash runtime is not available or the script was not signed correctly. Check `SECURITY_REJECTED` status in the [Job Execution runbook](jobs.md#security_rejected-signature-verification-failed).

---

## hello-python

**What it tests:** Verifies that the Python runtime is available and that a Python job can be dispatched, signature-verified, and executed end-to-end on the node.

**Required capabilities:** None.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/python/hello.py \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
Hello from Axiom!
Hostname: node-a1b2c3d4
OS: Linux
Python: 3.11.8
UTC: 2026-03-28T12:00:00Z
```

**Expected FAIL output:** N/A — if the job fails, the node's Python runtime is not available or the signing step was skipped.

---

## hello-pwsh

**What it tests:** Verifies that PowerShell 7+ (`pwsh`) is available on the node and that a PowerShell job can be dispatched and executed end-to-end.

**Required capabilities:** None.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/pwsh/hello.ps1 \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
Hello from Axiom!
Hostname: node-a1b2c3d4
OS: Ubuntu 22.04.4 LTS
PowerShell: 7.4.1
UTC: 2026-03-28T12:00:00Z
```

**Expected FAIL output:** N/A — if the job fails, PowerShell 7+ is not installed on the node. Use a Foundry-built image that includes `pwsh` or install it manually on the node.

---

## validation-volume-mapping

**What it tests:** Confirms that a volume mount is readable and writable inside the job container at the path specified by `AXIOM_VOLUME_PATH`.

**Required capabilities:** None.

**Setup:** Before dispatching, the target node must have a volume mounted at the path you specify, and `AXIOM_VOLUME_PATH` must be set in the job's environment payload.

Node compose snippet:

```yaml
services:
  puppet-node:
    volumes:
      - axiom_data:/mnt/axiom-data
    environment:
      - AXIOM_VOLUME_PATH=/mnt/axiom-data

volumes:
  axiom_data:
```

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/validation/volume-mapping.sh \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
PASS: volume mount at /mnt/axiom-data is readable and writable.
```

**Expected FAIL output:**

```
FAIL: cannot write to /mnt/axiom-data — check volume mount configuration.
```

If the job fails, confirm the volume is mounted on the node (`docker inspect <container>` → `Mounts`) and that `AXIOM_VOLUME_PATH` matches the mount point inside the container.

---

## validation-network-filter

**What it tests:** Confirms network isolation is active on the target node. The job attempts a connection to `AXIOM_BLOCKED_HOST` (default: `8.8.8.8`) and exits 0 if the host is **unreachable** (isolation confirmed), or exits 1 if the host is reachable (isolation not in effect).

**Required capabilities:** None.

!!! warning "The script does not create isolation"
    This job validates isolation that is already in place. You must configure `--network=none` (or equivalent) on the node **before** dispatching. The script does not manipulate `iptables` or any node-global network state.

**Setup:** Configure the target node with `--network=none`:

```yaml
services:
  puppet-node:
    network_mode: "none"
```

Alternatively, pass `--network=none` via the Docker run command. `AXIOM_BLOCKED_HOST` can be overridden in the job environment if your isolation blocks a different address range.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/validation/network-filter.py \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
PASS: network isolation confirmed — 8.8.8.8 is unreachable.
```

**Expected FAIL output:**

```
FAIL: network isolation NOT active — 8.8.8.8 is reachable. Configure --network=none on the node.
```

---

## validation-memory-hog

**What it tests:** OOM enforcement — the job allocates 256 MB (page-touched to prevent overcommit deferral) and holds it for 30 seconds. On a node with a memory limit below 256 MB, the container runtime kills the process before it completes.

**Required capabilities:** `resource_limits_supported: "1.0"`

!!! warning "Expected FAILED status"
    The job reaching `FAILED` status is the **expected success outcome**. The OOM kill is the point of the test — it confirms the runtime is enforcing memory limits. If the job reaches `COMPLETED`, the memory limit is not being enforced.

**Setup:** Configure the target node with a memory limit below 256 MB. Set the `resource_limits_supported` capability in the node's capability list.

Node compose snippet:

```yaml
services:
  puppet-node:
    environment:
      - JOB_MEMORY_LIMIT=128m
```

Register `resource_limits_supported` in the dashboard: open the **Nodes** view, select the node, open the Capabilities panel, and add `resource_limits_supported = 1.0`.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/validation/memory-hog.py \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output (job status = FAILED):**

```
[node] Job <guid> killed by OOM — memory limit enforced correctly.
```

The job status will show `FAILED`. This is correct behaviour.

**Expected FAIL output (job status = COMPLETED):**

```
Allocated 256 MB — sleeping 30 seconds.
Done.
```

If the job completes, memory limits are not being enforced. Check cgroup v2 support on the host (see [LXC caveat](#resource-limit-node-setup) below).

---

## validation-cpu-spin

**What it tests:** CPU throttle enforcement — the job runs a CPU-bound loop for 5 seconds and reports wall time, CPU time, and their ratio. On a node with `cpu_limit=0.5`, the ratio will be approximately `0.5` rather than `1.0`, confirming throttling is active.

**Required capabilities:** `resource_limits_supported: "1.0"`

The job completes normally (exit 0) and reports its measurements. The operator reads the output to verify the ratio.

**Setup:** Configure the target node with a CPU limit of 0.5 and register the `resource_limits_supported` capability.

Node compose snippet:

```yaml
services:
  puppet-node:
    environment:
      - JOB_CPU_LIMIT=0.5
```

Register `resource_limits_supported` in the dashboard: open the **Nodes** view, select the node, open the Capabilities panel, and add `resource_limits_supported = 1.0`.

**Dispatch:**

```bash
axiom-push job push \
  --script tools/example-jobs/validation/cpu-spin.py \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

**Expected PASS output:**

```
CPU spin complete.
Wall time : 10.02s
CPU time  : 5.01s
Ratio     : 0.50
PASS: ratio < 0.8 — CPU throttling confirmed.
```

**Expected FAIL output:**

```
CPU spin complete.
Wall time : 5.01s
CPU time  : 5.00s
Ratio     : 1.00
FAIL: ratio >= 0.8 — CPU throttling is NOT active. Check JOB_CPU_LIMIT on the node.
```

---

## Resource Limit Node Setup

Use this section to configure a node for the memory and CPU validation jobs.

### Memory limit

Set `JOB_MEMORY_LIMIT` on the node. The node agent reads this value and passes it as `--memory` to the container runtime when executing each job:

```yaml
environment:
  - JOB_MEMORY_LIMIT=128m
```

The `validation-memory-hog` job allocates 256 MB — any limit strictly below 256 MB will trigger the OOM kill. `128m` is recommended for a clear result.

### CPU limit

Set `JOB_CPU_LIMIT` on the node. The node agent reads this value and passes it as `--cpus` to the container runtime:

```yaml
environment:
  - JOB_CPU_LIMIT=0.5
```

The `validation-cpu-spin` job spins on two CPUs. With `cpu_limit=0.5`, the wall/CPU ratio will be approximately `0.5`. Any value below `1.0` will show measurable throttling.

### Capability registration

Resource limit jobs require the `resource_limits_supported` capability to be registered on the target node. Without this capability, the job exits with code 1 and reports:

```
FAIL: resource limits are not supported on this node (resource_limits_supported capability missing)
```

To register the capability:

1. Open the **Nodes** view in the dashboard.
2. Select the target node.
3. Open the **Capabilities** panel.
4. Add capability name `resource_limits_supported` with value `1.0`.
5. Save. The capability takes effect on the next job assignment cycle.

### LXC caveat

Cgroup v2 resource limit enforcement is unreliable on LXC-hosted nodes. When `EXECUTION_MODE=direct` (Python subprocess, used in Docker-in-Docker configurations), `--memory` and `--cpus` flags are not passed to any container runtime — the host must enforce limits at the LXC level instead. For reliable enforcement of `validation-memory-hog` and `validation-cpu-spin`, run these jobs on a **native Docker node** (not LXC-hosted).

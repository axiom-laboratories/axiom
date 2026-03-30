# Axiom Example Jobs

A growing library of reference jobs and validation scripts for Axiom operators and community contributors.

## How to use

Jobs in this library are committed **unsigned** — they are templates, not ready-to-dispatch payloads. Before dispatching, sign each script with your registered `axiom-push` key:

```bash
axiom-push job push \
  --script tools/example-jobs/bash/hello.sh \
  --key signing.key \
  --key-id <your-key-id>
# Then publish from the Staging tab in the dashboard
```

See [`docs/runbooks/node-validation.md`](../../docs/docs/runbooks/node-validation.md) for the full operator workflow, including per-job dispatch commands and expected output samples.

## Job Catalog

| Job | Runtime | Description | Required Capabilities |
|-----|---------|-------------|----------------------|
| [hello-bash](#hello-bash) | bash | Hello-world: verifies Bash job execution end-to-end | (none) |
| [hello-python](#hello-python) | python | Hello-world: verifies Python job execution end-to-end | (none) |
| [hello-pwsh](#hello-pwsh) | powershell | Hello-world: verifies PowerShell 7+ job execution end-to-end | (none) |
| [validation-volume-mapping](#validation-volume-mapping) | bash | Confirms volume mounts are readable and writable inside the container | (none) |
| [validation-network-filter](#validation-network-filter) | python | Confirms network isolation is active (expects --network=none) | (none) |
| [validation-memory-hog](#validation-memory-hog) | python | OOM test: job should be killed before completing | resource_limits_supported |
| [validation-cpu-spin](#validation-cpu-spin) | python | CPU throttle test: reports wall/CPU ratio to confirm throttling | resource_limits_supported |

## Job Details

### hello-bash

**Script:** `bash/hello.sh`

Prints the node's hostname, OS release, Bash version, and UTC timestamp. Use this as the first job you dispatch to any new node — if it completes, Bash execution is working end-to-end through the signing, dispatch, and runtime pipeline.

---

### hello-python

**Script:** `python/hello.py`

Prints hostname, OS, Python version, and UTC timestamp. Use this to confirm the Python runtime is available and execution is working correctly.

---

### hello-pwsh

**Script:** `pwsh/hello.ps1`

Prints hostname, OS description, PowerShell version, and UTC timestamp. Requires PowerShell 7+ (`pwsh`) to be available on the node. Use this to confirm PowerShell execution is working on nodes that declare PowerShell capability.

---

### validation-volume-mapping

**Script:** `validation/volume-mapping.sh`

Writes a PID-unique sentinel file at the path specified by `AXIOM_VOLUME_PATH`, reads it back to confirm both write and read access, then cleans up. Exits 0 on success, 1 on any failure. Requires the node to have a volume mounted at the configured path and `AXIOM_VOLUME_PATH` set in the job's environment.

---

### validation-network-filter

**Script:** `validation/network-filter.py`

Attempts a connection to `AXIOM_BLOCKED_HOST` (default: `8.8.8.8`). If the host is **unreachable**, the test passes — isolation is confirmed. If the host is **reachable**, the test fails. The script does not create any network isolation itself; it only validates isolation that is already in place via `--network=none` or equivalent. Requires the node to be pre-configured with network isolation before dispatch.

---

### validation-memory-hog

**Script:** `validation/memory-hog.py`

Allocates 256 MB (page-touched to prevent overcommit deferral) and holds it for 30 seconds. On a node with a memory limit below 256 MB, the container runtime kills the job before it completes. The job reaching `FAILED` status is the **expected success outcome** — it confirms the runtime is enforcing memory limits.

Requires the `resource_limits_supported` capability to be registered on the target node. Cgroup v2 limit enforcement is unreliable on LXC-hosted nodes; test this job on a native Docker node.

---

### validation-cpu-spin

**Script:** `validation/cpu-spin.py`

Runs a CPU-bound loop for 5 seconds and reports wall time, CPU time, and their ratio. On a node with `cpu_limit=0.5`, the ratio will be approximately `0.5` rather than `1.0`, confirming throttling is active. The job completes normally (exit 0) and reports its measurements — the operator reads the output to verify the ratio.

Requires the `resource_limits_supported` capability to be registered on the target node.

---

## Contributing

This library is meant to grow. If you have a useful reference job or validation script, open a PR:

1. Add your script to the appropriate runtime subdirectory (`bash/`, `python/`, `pwsh/`) or create a new one.
2. Add a row to the catalog table above.
3. Add an entry to `manifest.yaml` with job name, description, script path, runtime, and required capabilities.
4. Sign your script with your registered Axiom signing key before dispatching — committed scripts are unsigned templates.

Keep scripts focused: one observable test per job, clear pass/fail output, clean up any side effects.

## manifest.yaml

The `manifest.yaml` file at the root of this directory contains machine-readable metadata for each job including dispatch parameters such as `runtime`, `required_capabilities`, `memory_limit`, and `cpu_limit`. Community tooling can use this manifest to build batch-dispatch helpers or automated validation runners.

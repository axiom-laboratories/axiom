# Phase 83: Node Validation Job Library - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

A signed, runbook-backed corpus of validation jobs operators use to verify any node works correctly across all runtimes and constraint types. Covers JOB-01 through JOB-07 (Bash/Python/PowerShell hello-world, volume mapping, network filtering, memory OOM, CPU throttle). The corpus lives at `tools/example-jobs/` with a community-library vision — not just validation jobs but a growing catalog of reusable examples.

</domain>

<decisions>
## Implementation Decisions

### Job corpus location
- Directory: `tools/example-jobs/` in the main public repo
- Vision: community-maintained job library for Axiom operators (like an awesome-list for Axiom jobs)
- Structure: subdirectories by runtime — `bash/`, `python/`, `pwsh/` — plus `validation/` for the node-check corpus (volume, network, resource limit jobs)
- `README.md` at `tools/example-jobs/` root serves as the community catalog: table with job name, runtime, description, required capabilities
- Validation-specific jobs live in `tools/example-jobs/validation/` alongside the runtime example dirs

### Signing workflow
- Jobs are committed **unsigned** — no pre-signed scripts or companion `.sig` files
- The runbook documents the operator workflow: sign with their existing axiom-push key, then dispatch
- Signing key: operator's already-registered Axiom signing key (no new key setup required)
- Community contributors follow the same workflow for their own additions

### Resource limit job behavior (JOB-06, JOB-07)
- Resource limit jobs require `resource_limits_supported` capability on the target node
- If dispatched to a node without this capability: job exits with **code 1** and a clear message (e.g., "FAIL: resource limits are not supported on this node (resource_limits_supported capability missing)")
- Status will show FAILED — this is intentional and indicates misconfigured dispatch, not a node problem
- Carrying forward from STATE.md: cgroup v2 enforcement is unreliable on LXC nodes; gate these jobs on the capability flag

### Runbook format & location
- Two documents serving different audiences:
  - `tools/example-jobs/README.md` — community catalog (awesome-list style table of all jobs)
  - `docs/runbooks/node-validation.md` — operator workflow guide in the MkDocs docs site
- Runbook depth: **job-by-job reference** with dispatch commands — not a prose walkthrough
- Each job entry in the runbook: what it tests, required capabilities, example dispatch command (axiom-push sign + API call or dashboard), expected PASS output sample, expected FAIL output sample (truncated stdout)
- Output samples included for every job — helps operators distinguish "expected FAILED" (e.g., resource limit test working correctly) from a real problem

### Job manifest
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

</decisions>

<specifics>
## Specific Ideas

- `tools/example-jobs/` is intended to grow into a community resource — README should be inviting to contributors, not just a reference table
- The "expected output" samples in the runbook are important for resource limit tests specifically, where FAILED can be either "working correctly" (the OOM kill is the point) or "something is wrong"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin_signer.py` (toms_home/.agents/tools/): Ed25519 sign + submit pattern — shows how signing and dispatch work; runbook should reference `axiom-push` instead as the public-facing tool
- `puppets/environment_service/runtime.py`: `ContainerRuntime.run()` accepts `memory_limit`/`cpu_limit` strings — job manifest limits map directly to these params
- `tools/__init__.py`: empty placeholder at `tools/` root — new `tools/example-jobs/` dir fits this structure

### Established Patterns
- Job dispatching: `POST /api/jobs` with `task_type="script"`, `runtime`, `script_content`, `signature`, `signature_payload` fields
- Runtime values in use: `python`, `bash`, `powershell` — job scripts and manifest should use these exact strings
- Capability matching: `required_capabilities` list in job dispatch matched against node's declared capabilities at assignment time

### Integration Points
- `docs/runbooks/`: existing runbook section in MkDocs — `node-validation.md` fits alongside node/job/Foundry runbooks
- `axiom-push` CLI: the public signing + dispatch tool operators use; runbook should show `axiom-push sign` + `axiom-push push` workflow

</code_context>

<deferred>
## Deferred Ideas

- Batch-dispatch helper script (`run_validation.py` that reads manifest and dispatches all jobs) — noted for community contribution or a future phase
- JOB-08: Validation job library extended to cover EE-specific features (signed attestation, execution history API) — already in backlog

</deferred>

---

*Phase: 83-node-validation-job-library*
*Context gathered: 2026-03-28*

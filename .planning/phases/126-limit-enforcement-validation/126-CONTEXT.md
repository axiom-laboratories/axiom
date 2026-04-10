# Phase 126: Limit Enforcement Validation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate that memory limits trigger OOMKill (exit code 137) and CPU limits cap available cores, on both Docker and Podman job execution runtimes. Run the existing stress test orchestrator (Phase 125) against the live stack, capture results, and produce a validation report. No new test framework — this is a "run, verify, document" phase. Enforcement bugs found during validation are documented but fixed in separate phases.

</domain>

<decisions>
## Implementation Decisions

### Dual-runtime testing
- Spin up a dedicated Podman node alongside existing Docker node(s)
- Orchestrator filters target nodes by `execution_mode` field from heartbeat (not capability tags)
- Full stress corpus (all 9 scripts × 3 languages) runs on BOTH Docker and Podman runtimes
- Podman test failures are documented findings, not phase blockers

### Validation approach
- Run the existing Phase 125 orchestrator (`mop_validation/scripts/stress/orchestrate_stress_tests.py`) — no new test framework
- If enforcement bugs are found (e.g. memory limit not triggering OOM), they are reported but NOT fixed in this phase — spawn separate fix phase
- Validation report includes both raw orchestrator JSON output AND human-readable pass/fail summary per scenario per runtime
- Report written to `mop_validation/reports/` (alongside existing reports)

### Phase completion bar
- Core enforcement tests (OOM kill + CPU cap) must pass on BOTH Docker and Podman
- Full sweep results (all languages, all script types) documented for both runtimes
- Podman-specific failures documented as findings, do not block phase completion

### Cgroup scope
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

</decisions>

<specifics>
## Specific Ideas

- Existing node compose files in `mop_validation/local_nodes/` are Docker-based — new Podman node needs its own compose or deployment config
- Orchestrator currently dispatches to available nodes — may need minor extension to target by `execution_mode`
- Podman nested container quirks (cgroup manager, storage driver) already handled in `runtime.py:67-71`
- OOM kill produces exit code 137 (Docker/Podman standard) — stress scripts already check this
- CPU throttle detection uses wall-time vs CPU-time ratio — stress scripts already measure this

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/stress/orchestrate_stress_tests.py` — dispatches 4 scenarios (CPU burn, memory OOM, concurrent isolation, all-language sweep)
- `mop_validation/scripts/stress/preflight_check.py` — validates cgroup version + controllers enabled
- `mop_validation/scripts/stress/{python,bash,pwsh}/` — 9 stress test scripts (3 types × 3 languages)
- `puppets/environment_service/runtime.py` — passes `--memory`/`--cpus` to container runtime (lines 57-60)
- `puppets/environment_service/node.py:433` — reports `execution_mode` in heartbeat

### Established Patterns
- Orchestrator reads credentials from `mop_validation/secrets.env`
- Job dispatch via `POST /dispatch` with `script_content`, `memory_limit`, `cpu_limit`
- Job status polling via `GET /jobs/{id}`
- Heartbeat includes `execution_mode` (docker/podman) and `detected_cgroup_version` (v1/v2/unsupported)
- Reports written to `mop_validation/reports/` as standard output directory

### Integration Points
- `GET /nodes` — list nodes with their `execution_mode` for runtime-based targeting
- `POST /dispatch` — accepts `memory_limit` and `cpu_limit` for enforcement testing
- Orchestrator scenarios already test OOM (exit code 137) and CPU throttle (ratio check)
- Podman runtime flags in `runtime.py:67-71` (storage-driver=vfs, cgroup-manager=cgroupfs)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 126-limit-enforcement-validation*
*Context gathered: 2026-04-09*

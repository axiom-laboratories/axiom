# Phase 47: CE Runtime Expansion - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the job execution model to support Bash and PowerShell alongside Python, via a unified `script` task type with a required `runtime` field. Covers backend validation, node execution, server-side `display_type`, scheduled job support, and a frontend runtime selector + display column update. The guided job form (Phase 50) is the full submission UX — Phase 47 adds only what operators need to submit and see Bash/PowerShell jobs now.

**Note:** No existing deployments to support. The legacy `python_script` task type is being dropped entirely (RT-06 removed). All submissions must use `task_type: script` with an explicit `runtime` field.

</domain>

<decisions>
## Implementation Decisions

### Script execution model
- Bash and PowerShell scripts run **containerized** via the existing `ContainerRuntime` (Docker/Podman) — same mechanism used for non-python_script tasks currently
- Script content is written to a **temp file** (e.g., `/tmp/job_<guid>.sh` or `.ps1`) before execution, then cleaned up — handles multi-line scripts and special characters correctly
- stdout + stderr are captured and reported back via `report_result()` — same pattern as `run_python_script()`
- **Standard node image** (`Containerfile.node`) ships with all three runtimes pre-installed: Python (already present), Bash (likely already present), PowerShell Core (`pwsh`)

### Signing requirement
- **All runtimes must be signed** — Ed25519 signing is required for Python, Bash, and PowerShell equally. No security regression from adding new runtimes.
- Signature covers a SHA256 hash of script content — same `signature_payload` pattern as existing Python jobs
- Signature failure → `SECURITY_REJECTED` + SEC-01 audit entry (already wired from Phase 46, no new code needed for the rejection path)

### Task type API
- **`python_script` is dropped** — no existing deployments means no backward compat needed. Submitting `task_type: python_script` returns HTTP 422.
- New unified type: `task_type: script` with a required `runtime` field (`python` | `bash` | `powershell`)
- Unknown `runtime` values → HTTP 422 with clear validation error (RT-04)
- RT-06 (python_script alias) is **removed** from scope — capture this as a dropped requirement during planning

### display_type
- Computed **server-side** — frontend never parses payload JSON to determine runtime
- Format: `script (python)`, `script (bash)`, `script (powershell)`
- All jobs (new and existing DB records) normalised to this format — no special-casing of old `python_script` rows needed since there are no existing deployments

### Frontend — Jobs list
- The current `task_type` column is **replaced** with `display_type` — plain text, no coloured badges
- No filtering/search by runtime in Phase 47 — deferred to Phase 49

### Frontend — Submission form
- Phase 47 **adds a runtime selector** to the existing raw-JSON submission form (not deferred to Phase 50)
- When task type is `script`, a second dropdown appears for runtime: Python / Bash / PowerShell
- The dropdown is hidden when any other task type is selected
- Control style: dropdown (consistent with existing form patterns in Jobs.tsx)

### Scheduled jobs (RT-07)
- `ScheduledJob` gains a `runtime` column (nullable, defaults to `'python'` for backward compat)
- Migration: `migration_v38.sql` with `ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python'`
- When the scheduler fires a job, `runtime` is read from this column and included in the dispatched job payload

### Claude's Discretion
- Exact temp file path pattern and cleanup approach (try/finally vs context manager)
- How `display_type` is surfaced on the API response — new field on `JobResponse` or computed in list query
- ContainerRuntime invocation details for Bash vs PowerShell (image selection, volume mounts)
- PowerShell Core package name and Containerfile.node install instructions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `node.py:execute_task()`: Current dispatch on `task_type == "python_script"`. New `script` task type will be added here; `run_python_script()` stays for Python runtime but the `script` dispatcher calls `ContainerRuntime` for all runtimes.
- `runtime.py` (puppets): `ContainerRuntime` class handles Docker/Podman detection and `run()`. Bash/PowerShell containerized execution goes through here.
- `job_service.py:report_result()`: Already wires `SECURITY_REJECTED` → SEC-01 audit (Phase 46). Bash/PS failures use the same path automatically.
- `security.py`: Ed25519 verify and HMAC helpers — used for all runtimes, no changes needed.
- `Jobs.tsx`: Existing `<Select>` task type dropdown + form submit logic — extend with runtime conditional dropdown.

### Established Patterns
- DB migration: `migration_vNN.sql` with `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` guards
- `create_all` handles fresh installs; migration file handles existing deployments
- Signing flow: `signature_payload` hash → Ed25519 verify → `SECURITY_REJECTED` on failure — all runtimes slot into this unchanged
- Audit entries: `audit(db, actor, "action:name", resource_id, detail={...})`

### Integration Points
- `node.py:execute_task()` — new `task_type == "script"` branch dispatches by `runtime` field
- `main.py` / `models.py` — `JobCreate` gets `runtime` field with enum validation; `JobResponse` gets `display_type`
- `job_service.py:assign_job()` — passes `runtime` through to `WorkResponse`
- `scheduler_service.py:fire_job()` — reads `ScheduledJob.runtime` when building the job payload
- `db.py:ScheduledJob` — gains `runtime` column
- `Jobs.tsx` — `display_type` replaces `task_type` column; runtime dropdown in submission form

</code_context>

<specifics>
## Specific Ideas

- No existing deployments → clean break from `python_script`. The codebase can be simplified by removing the legacy task type entirely rather than keeping alias code.
- Phase 50 (Guided Form) will build the full submission UX. The Phase 47 runtime dropdown is intentionally minimal — a stopgap that lets operators submit Bash/PS jobs now without waiting for Phase 50.

</specifics>

<deferred>
## Deferred Ideas

- Runtime-based job filtering — Phase 49 (Pagination, Filtering and Search)
- Full structured submission form with runtime selector — Phase 50 (Guided Form) will supersede the Phase 47 stopgap
- Capability-gated runtime dispatch (node advertises supported runtimes) — not in scope; all standard nodes run all runtimes

</deferred>

---

*Phase: 47-ce-runtime-expansion*
*Context gathered: 2026-03-22*

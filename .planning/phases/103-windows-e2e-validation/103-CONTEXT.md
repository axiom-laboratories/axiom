# Phase 103: Windows E2E Validation - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

A fresh Windows user following the Quick Start guide (Windows tabs) on Dwight reaches a completed PowerShell job with no undocumented steps and no friction points left unresolved. Covers: pre-audit of Windows docs gaps → cold-start deploy on Dwight → forced password change → node enrollment → first PowerShell job → verify output in dashboard. All friction found is fixed before the phase closes.

</domain>

<decisions>
## Implementation Decisions

### Windows docs pre-audit
- Pre-audit all getting-started docs before the first validation run — add PowerShell tabs/sections where missing, then validate
- Scope: enroll-node.md, first-job.md, prerequisites.md at minimum; Claude audits the full getting-started directory and fills any other gaps found
- No separate Windows guide — same pages as Linux, Windows tabs alongside the existing Linux/macOS tabs
- All Windows shell interactions use PowerShell (pwsh) throughout — no CMD, no WSL2 bash

### Orchestration method
- paramiko SSH to drive Dwight (pattern already established in test_ssh.py; Dwight creds in secrets.env)
- New file: `mop_validation/scripts/run_windows_scenario.py` with `dwight_exec()`, `dwight_push()`, `wait_for_stack_dwight()` helpers — parallel structure to run_ce_scenario.py
- Dashboard state verification (node ONLINE, job COMPLETED) via API calls from the Linux host: `requests.get('https://192.168.50.149:8443/...')` — no Playwright needed

### Stack architecture on Dwight
- Full Axiom orchestrator stack runs on Dwight (not just the node) — compose.cold-start.yaml started on Dwight via SSH
- Node connects back to the orchestrator via `host.docker.internal:8001` (Docker Desktop Windows standard networking)
- AGENT_URL in node config: `https://host.docker.internal:8001`

### Validation method (carried from Phase 102)
- Claude subagent runs the validation (not Gemini)
- Persona: pure docs-follower — no prior Axiom knowledge; if the docs don't say it, the agent doesn't do it
- Golden path: install → forced password change → enroll node → first PowerShell job → verify output
- Blocker handling: stop at first blocker, fix (docs AND code/config), full restart from top
- Iterations continue until golden path completes cleanly end-to-end

### PowerShell job signing
- Signing keypair: reuse existing signing key from the Linux host (mop_validation/secrets/) — no new key gen needed on Dwight
- Signing method: Python via pip (cryptography library) — same approach as Linux docs; Python is available on Windows
- First job content: a simple PowerShell Hello World — `Write-Host 'Hello from Axiom on Windows'` — keeps it minimal, proves PowerShell execution on the node

### Friction report
- File: `mop_validation/reports/FRICTION-WIN-103.md`
- Format: synthesise_friction.py compatible (same as prior FRICTION files)
- At phase close: run synthesise_friction.py to produce the synthesised summary as sign-off artifact

### Claude's Discretion
- Exact paramiko invocation for running pwsh commands (exec_command syntax for PowerShell on Windows SSH server)
- Whether to use password auth or key-based auth for Dwight SSH (both are in secrets.env)
- Exact structure of dwight_exec() / dwight_push() helpers
- How to handle Windows line endings (CRLF) when pushing files to Dwight via paramiko

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `test_ssh.py` (mop_validation/scripts/): paramiko pattern for SSH to remote hosts; read_secrets() helper that parses secrets.env — reuse both in run_windows_scenario.py
- `run_ce_scenario.py` (mop_validation/scripts/): incus_exec(), wait_for_stack(), run_gemini_scenario(), pull_friction() — structural template for run_windows_scenario.py
- `synthesise_friction.py` (mop_validation/scripts/): reads FRICTION files and produces summary — run at phase close, no changes needed
- `secrets.env` (mop_validation/): dwight_ip=192.168.50.149, dwight_username=dwight\drear, dwight_password, dwight_ssh_key=external_client_ed25519 — all available for paramiko

### Established Patterns
- FRICTION file format: `### [Category] Title` → `**Classification:** BLOCKER/NOTABLE/ROUGH EDGE/MINOR` → `**What happened:**` → `**Fix applied:**`
- Windows tab format in docs: `=== "Windows (PowerShell)"` block alongside `=== "Linux / macOS"` — install.md already uses this pattern throughout
- Dashboard access from host: `https://<ip>:8443` (Caddy TLS, self-signed — use verify=False for requests)
- AGENT_URL for Docker Desktop Windows: `https://host.docker.internal:8001` (already documented in enroll-node.md table)

### Integration Points
- Dwight SSH: `paramiko → dwight_exec('pwsh -Command "..."')` for all stack and node commands
- Dashboard API from Linux host: `requests.get('https://192.168.50.149:8443/api/...', verify=False)` with JWT from login
- compose.cold-start.yaml: pushed to Dwight via paramiko before stack start (or already present if Dwight has the repo)

</code_context>

<specifics>
## Specific Ideas

- The Windows run is structurally identical to the Linux run (Phase 102) but with SSH instead of incus exec, and PowerShell instead of bash. run_windows_scenario.py should be recognisably parallel to run_ce_scenario.py.
- First known gap: enroll-node.md and first-job.md have no PowerShell content. The pre-audit plan should add Windows tabs to both before the subagent runs.
- The node's AGENT_URL must be `https://host.docker.internal:8001` on Docker Desktop Windows — this is in the enroll-node.md table already but needs confirming in the Windows-specific instructions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 103-windows-e2e-validation*
*Context gathered: 2026-03-31*

# Phase 102: Linux E2E Validation - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

A fresh Linux user following the published Quick Start guide inside a clean LXC environment reaches a completed job with no undocumented steps and no friction points left unresolved. Covers: cold-start deploy → forced password change → node enrollment → first Python/Bash job → CE feature accessibility. All friction found is fixed before the phase closes.

</domain>

<decisions>
## Implementation Decisions

### Validation method
- A Claude subagent runs the validation (not Gemini — lower overhead, paid tier already available)
- Persona: pure docs-follower — no prior Axiom knowledge; if the docs don't say it, the agent doesn't do it
- Scope: full golden path only — Install → login (forced password change) → enroll node → dispatch first job (Python) → verify output in dashboard
- Blocker handling: agent stops at the first blocker, reports what it found; orchestrator fixes it, then re-runs from the top (full restart, not resume)
- Phase iterates until the golden path completes end-to-end with no friction

### LXC environment
- Start from a fresh provision of `axiom-coldstart` — delete and reprovision via `provision_coldstart_lxc.py` before each run
- Stack: `compose.cold-start.yaml` (the file the Quick Start guide tells new users to pull)
- Internet access: live during the run — Docker pulls images from registry at runtime (accurate to real new-user experience)

### Fix strategy
- Scope: fix whatever caused the friction — docs AND code/config, whichever applies
- After each fix, full restart: reprovision LXC and run the golden path from the top
- No fixed cap on iterations — phase is done when the golden path completes cleanly end-to-end

### Report format
- Match v14.0 FRICTION file format (synthesise_friction.py compatible)
- File: `mop_validation/reports/FRICTION-LNX-102.md` (one file covering the Linux run)
- At phase close: run `synthesise_friction.py` to produce a synthesised summary as the sign-off artifact

### Claude's Discretion
- Exact structure of the validation subagent prompt / persona setup
- How to pass the LXC container name and workspace paths to the subagent
- Whether to use Playwright or API calls to verify dashboard states (e.g., node appears ONLINE, job shows COMPLETED)
- Structure of FRICTION-LNX-102.md within the v14.0 format constraints

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `provision_coldstart_lxc.py` (mop_validation/scripts/): provisions `axiom-coldstart` Incus LXC with Docker-in-LXC, Node.js, Playwright deps — run with `--stop` to delete before reprovisioning
- `run_ce_scenario.py` (mop_validation/scripts/): `incus_exec()`, `incus_push()`, `incus_pull()`, `wait_for_stack()`, `reset_stack()` helpers — reuse for orchestrating commands inside LXC
- `synthesise_friction.py` (mop_validation/scripts/): reads FRICTION files and produces `cold_start_friction_report.md` — run at phase close
- Prior FRICTION files (mop_validation/reports/): FRICTION-CE-INSTALL.md, FRICTION-CE-OPERATOR.md — reference for format; v14.0 friction points (docs/image/TLS issues) should already be fixed in v18.0

### Established Patterns
- LXC container name: `axiom-coldstart`
- Compose file for cold-start: `puppeteer/compose.cold-start.yaml`
- Quick Start docs: `docs/docs/getting-started/install.md`, `enroll-node.md`, `first-job.md`
- FRICTION file format: `### [Category] Title` → `**Classification:** BLOCKER/NOTABLE/ROUGH EDGE/MINOR` → `**What happened:**` → `**Fix applied:**`
- CLAUDE.md: Python Playwright requires `--no-sandbox`; JWT auth via localStorage injection; API login is form-encoded not JSON

### Integration Points
- LXC → host: `incus exec axiom-coldstart -- bash -c "..."` for all commands run inside the container
- Dashboard testing: access via `https://<lxc-ip>:8443` from host, or `https://localhost:8443` from inside LXC
- Node enrollment: requires the agent running inside the LXC to have access to the Axiom dashboard (either via browser/Playwright or via API)

</code_context>

<specifics>
## Specific Ideas

- Prior v14.0 run surfaced: docs path mismatch, undocumented admin password, wrong node image, removed `EXECUTION_MODE=direct`, TLS cert mismatch on `172.17.0.1`. These should all be resolved before Phase 102 runs — if any remain, they are friction to fix.
- The subagent should verify each Quick Start step produces the expected output before proceeding (don't skip verification steps)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 102-linux-e2e-validation*
*Context gathered: 2026-03-31*

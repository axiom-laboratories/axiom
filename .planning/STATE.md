---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: — CE/EE Cold-Start Validation
status: completed
stopped_at: Phase 62 context gathered
last_updated: "2026-03-25T08:38:04.968Z"
last_activity: 2026-03-24 — Phase 61 all 3 plans executed; AXIOM_EE_LICENCE_KEY generated in secrets.env
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 61 — LXC Environment and Cold-Start Compose

## Current Position

Phase: 61 of 65 (LXC Environment and Cold-Start Compose)
Plan: 03 of 03 — Complete
Status: Phase complete
Last activity: 2026-03-24 — Phase 61 all 3 plans executed; AXIOM_EE_LICENCE_KEY generated in secrets.env

Progress: [██████████] 100%

## Accumulated Context

### Decisions

- [v14.0 Kickoff]: Single LXC contains full Axiom Docker stack (orchestrator + nodes) + Gemini tester agent
- [v14.0 Kickoff]: Gemini CLI (Flash model, GEMINI_API_KEY) used as tester; Claude orchestrates via file-based checkpoint protocol
- [v14.0 Kickoff]: Agents constrained to docs-only access — no codebase reads; checkpoint files used when agent is blocked
- [v14.0 Kickoff]: Two runs: CE (no licence) then EE (pre-generated Ed25519 licence); both test install + 3 runtimes
- [v14.0 Roadmap]: Phase 61 must resolve all 8 critical infrastructure pitfalls before Phase 62 starts
- [v14.0 Roadmap]: CE run (Phase 63) precedes EE run (Phase 64) — shared friction identified in CE need not be re-investigated
- [Phase 61-lxc-environment-and-cold-start-compose]: Use raw.apparmor=pivot_root, override in incus launch for Docker-in-LXC on Ubuntu 24.04 kernel 6.8.x (Incus #791 workaround)
- [Phase 61]: Hardcode SERVER_HOSTNAME=172.17.0.1 in cold-start cert-manager to guarantee correct Caddy TLS SAN without evaluator config
- [Phase 61]: PowerShell 7.6.0 LTS direct GitHub releases .deb install replaces silently-failing Microsoft Debian 12 SHA1 apt repo method
- [Phase 61]: 1-year expiry and customer_id axiom-coldstart-test used to distinguish cold-start evaluation licences from developer test licences; AXIOM_EE_LICENCE_KEY written to secrets.env for Phase 64 compose injection

### Pending Todos

None.

### Blockers/Concerns

- [Phase 61]: Docker-in-LXC AppArmor pivot_root behaviour on Ubuntu 24.04 kernel 6.8.x — verify `docker run --rm hello-world` succeeds before proceeding
- [Phase 61]: Gemini CLI headless hang risk — `ripgrep` install and `GEMINI_API_KEY` env var required; verify with `timeout 30 gemini -p "Say hello"`
- [Phase 62]: Gemini API key tier must be Tier 1 (paid) for a full CE+EE run — free tier 250 RPD is insufficient
- [Phase 64]: `axiom-ee` wheel availability inside LXC — confirm editable install path vs devpi before Phase 64 planning

## Session Continuity

Last session: 2026-03-25T08:38:04.966Z
Stopped at: Phase 62 context gathered
Next action: Run `/gsd:plan-phase 61`
Resume file: .planning/phases/62-agent-scaffolding/62-CONTEXT.md

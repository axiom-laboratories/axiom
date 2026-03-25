---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: — CE/EE Cold-Start Validation
status: in-progress
stopped_at: Phase 62, Plan 02 complete
last_updated: "2026-03-25T09:07:00Z"
last_activity: 2026-03-25 — Phase 62 plan 02 executed; SCAF-02 checkpoint round-trip PASS, monitor_checkpoint.py created
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 4
  completed_plans: 5
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 62 — Agent Scaffolding

## Current Position

Phase: 62 of 65 (Agent Scaffolding)
Plan: 02 of 03 — Complete
Status: In progress (1 plan remaining)
Last activity: 2026-03-25 — Phase 62 plan 02 executed; SCAF-02 checkpoint round-trip PASS, monitor_checkpoint.py created

Progress: [█████░░░░░] 50%

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
- [Phase 62-01]: HOME isolation uses /root/validation-home with settings.json only — no GEMINI.md, no history/ directory prevents session bleed between runs
- [Phase 62-01]: Docs delivered as static file:///workspace/docs/ snapshot pushed to LXC (167 files); Gemini reads via cat commands on HTML files
- [Phase 62-01]: SCAF-02 and SCAF-04 verifier checks are informational placeholders — not failures, stubs for plans 62-02 and 62-03
- [Phase 62-02]: SCAF-02 automated test does not invoke monitor_checkpoint.py (requires operator input) — procedural 5-step round-trip test used instead
- [Phase 62-02]: check_scaf02_checkpoint_roundtrip is self-contained in verify_phase62_scaf.py with own file transfer helpers — no cross-script imports

### Pending Todos

None.

### Blockers/Concerns

- [Phase 61]: Docker-in-LXC AppArmor pivot_root behaviour on Ubuntu 24.04 kernel 6.8.x — verify `docker run --rm hello-world` succeeds before proceeding
- [Phase 61]: Gemini CLI headless hang risk — `ripgrep` install and `GEMINI_API_KEY` env var required; verify with `timeout 30 gemini -p "Say hello"`
- [Phase 62]: Gemini API key tier must be Tier 1 (paid) for a full CE+EE run — free tier 250 RPD is insufficient
- [Phase 64]: `axiom-ee` wheel availability inside LXC — confirm editable install path vs devpi before Phase 64 planning

## Session Continuity

Last session: 2026-03-25T09:07:00Z
Stopped at: Phase 62 Plan 02 complete — checkpoint monitor and SCAF-02 round-trip test verified
Next action: Run plan 62-03 (scenario scripts)
Resume file: .planning/phases/62-agent-scaffolding/62-02-SUMMARY.md

---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: — CE/EE Cold-Start Validation
status: defining_requirements
stopped_at: Milestone started — defining requirements
last_updated: "2026-03-24"
last_activity: 2026-03-24 — Milestone v14.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Defining requirements for v14.0 CE/EE Cold-Start Validation

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-24 — Milestone v14.0 started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- [v14.0 Kickoff]: Single LXC contains full Axiom Docker stack (orchestrator + nodes) + Gemini tester agent — mirrors a real engineer eval in a VM
- [v14.0 Kickoff]: Gemini CLI (Flash model, GEMINI_API_KEY) used as tester agents to save Claude tokens; Claude orchestrates externally via file-based checkpoint protocol
- [v14.0 Kickoff]: Agents constrained to docs-only access (no codebase reads) to preserve cold-start validity; they write checkpoint files when blocked, Claude provides steering
- [v14.0 Kickoff]: Playwright (Python, --no-sandbox) used for UI interaction — Lightpanda rejected due to incomplete React SPA support
- [v14.0 Kickoff]: Two runs: CE (no licence) and EE (pre-generated Ed25519 licence); both test install path + operator path
- [v14.0 Kickoff]: Three job types per run: Python, Bash, PowerShell
- [v14.0 Kickoff]: GEMINI_API_KEY stored in mop_validation/secrets.env; model pinned to Flash to avoid paid tier

### Pending Todos

None.

### Blockers/Concerns

- PowerShell (`pwsh`) availability in standard CE node container image needs verification before test run
- EE licence must be pre-generated before EE run (admin_signer.py tooling available)

## Session Continuity

Last session: 2026-03-24
Stopped at: Milestone v14.0 started — defining requirements
Next action: Complete requirements definition and run roadmapper
Resume file: None

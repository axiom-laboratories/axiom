---
gsd_state_version: 1.0
milestone: v14.1
milestone_name: — First-User Readiness
status: completed
stopped_at: Completed 68-01-PLAN.md
last_updated: "2026-03-26T10:38:45.779Z"
last_activity: 2026-03-26 — 67-03 complete (first-job.md pre-dispatch callout, Dashboard/CLI tab pair for Step 4)
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 8
  completed_plans: 7
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v14.1 First-User Readiness — Phase 66: Backend Code Fixes

## Current Position

Phase: 67 of 68 (Getting Started Documentation)
Plan: 3 of 3 complete
Status: Complete
Last activity: 2026-03-26 — 67-03 complete (first-job.md pre-dispatch callout, Dashboard/CLI tab pair for Step 4)

Progress: [██████████] 100%

## Accumulated Context

### Decisions

- [v14.1 Roadmap]: Code before docs — CE/EE execution gating must be in place before docs describing that boundary are published
- [v14.1 Roadmap]: Phase 66 must verify Containerfile.node and compose.cold-start.yaml fixes before any docs work; do not trust fixed-during-run changes without source confirmation
- [v14.1 Roadmap]: Phase 67 sub-order: add pymdownx.tabbed to mkdocs.yml first, then install.md → enroll-node.md → first-job.md (user journey order)
- [v14.1 Roadmap]: Phase 68 is EE-only doc cleanup (2 requirements) — kept separate from Phase 67 so CE docs land independently
- [Phase 66-backend-code-fixes]: Single-stage ARG TARGETARCH in Containerfile.node selects correct PowerShell .deb for arm64/amd64 without multi-stage build complexity
- [Phase 66-02]: Stub handlers with path parameters tested with dummy args rather than no-arg call in test_ce_smoke.py
- [Phase 66-02]: executions flag added to /api/features endpoint in both CE fallback dict and EEContext ctx response
- [Phase 66-backend-code-fixes]: Phase 66 gate confirmed: no source changes needed — verification-only plan proves CODE-01/02/03/04 requirements met by prior plans' artifacts
- [Phase 67-getting-started-documentation]: CLI token path promoted to equal-weight tab; cold-start compose https://agent:8001 added as primary AGENT_URL table entry
- [Phase 67]: Pre-dispatch danger callout placed as standalone block between Step 3 separator and Step 4 heading for maximum visual impact
- [Phase 67]: axiom-push promoted as CLI hero command for Step 4 dispatch; CE users directed to collapsible Raw API curl fallback
- [Phase 68-ee-documentation]: GET /api/features is the canonical EE verification endpoint — /api/admin/features must never appear in docs (EEDOC-01)
- [Phase 68-ee-documentation]: AXIOM_LICENCE_KEY is the only correct env var name — AXIOM_EE_LICENCE_KEY does not exist (EEDOC-02)

### Roadmap Evolution

- Phase 69 added: Fix CI release pipeline version pinning and semver tags

### Pending Todos

None.

### Blockers/Concerns

- [Phase 66 Pitfall]: FastAPI route shadow — existing `@app.get("/api/executions")` in main.py must be removed before the CE stub can be reached; adding the stub file alone is not enough
- [Phase 66 Pitfall]: PowerShell `.deb` in Containerfile.node is amd64-only with no platform guard — confirm `--platform linux/amd64` fix approach before touching file
- [Phase 67 Pitfall]: MkDocs heading renames silently break anchor links — run `mkdocs build --strict` after each file; grep for existing `#anchor` cross-references before renaming
- [67-01]: Tab syntax confirmed working: pymdownx.tabbed alternate_style: true in mkdocs.yml; === 'Label' with 4-space indented content; admonitions inside tabs work when indented 4 spaces
- [67-01]: Cold-Start install path is minimal — only ADMIN_PASSWORD and ENCRYPTION_KEY; no SECRET_KEY/API_KEY needed for cold-start compose

## Session Continuity

Last session: 2026-03-26T10:38:45.778Z
Stopped at: Completed 68-01-PLAN.md
Resume file: None

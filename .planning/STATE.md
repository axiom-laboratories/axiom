---
gsd_state_version: 1.0
milestone: v13.0
milestone_name: — Research & Documentation Foundation
status: planning
stopped_at: Completed 60-03-PLAN.md
last_updated: "2026-03-24T19:59:34.217Z"
last_activity: 2026-03-24 — v13.0 roadmap created
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v13.0 — Research & Documentation Foundation

## Current Position

Phase: Not started (roadmap complete)
Plan: —
Status: Ready to plan Phase 57
Last activity: 2026-03-24 — v13.0 roadmap created

Progress: [░░░░░░░░░░] 0%

## Phases — v13.0

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 57. Research — Parallel Job Swarming | Design doc enabling informed build/defer decision on fan-out swarming | SWRM-01, SWRM-02, SWRM-03 | Not started |
| 58. Research — Organisational SSO | Design doc enabling future SSO implementation without re-doing architecture choices | SSO-01–SSO-06 | Not started |
| 59. Documentation | Docs site accurate for v12.0, visually consistent with dashboard, Docker deployment covered | DOCS-01, DOCS-02, DOCS-03, DOCS-04 | Not started |
| 60. Quick Reference | HTML quick-ref files relocated, rebranded, and updated for v12.0 | QREF-01, QREF-02, QREF-03, QREF-04 | Not started |

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v13.0)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| Phase 57-research-parallel-job-swarming P01 | 15 | 2 tasks | 1 files |
| Phase 58-research-organisational-sso P01 | 35 | 2 tasks | 1 files |
| Phase 59-documentation P01 | 5 | 1 tasks | 1 files |
| Phase 59-documentation P02 | 1m | 2 tasks | 4 files |
| Phase 59-documentation P03 | 2 | 2 tasks | 4 files |
| Phase 60-quick-reference P01 | 5m | 2 tasks | 4 files |
| Phase 60-quick-reference P02 | 5m | 2 tasks | 1 files |
| Phase 60-quick-reference P03 | 10m | 2 tasks | 1 files |

## Accumulated Context

### Decisions

- [v13.0 Roadmap]: All 4 phases are independent — Phases 57, 58, 59, 60 have no inter-dependencies and can execute in any order or in parallel.
- [v13.0 Roadmap]: Phases 57 and 58 are research-only — no implementation. Output is a design document. Implementation of swarming and SSO are explicitly deferred (Out of Scope in REQUIREMENTS.md).
- [v13.0 Roadmap]: Phase 59 (Documentation) targets the MkDocs docs site in `docs/`. DOCS-03 (branding alignment) requires reading the current dashboard visual identity before making changes.
- [v13.0 Roadmap]: Phase 60 (Quick Reference) targets the two HTML files currently at project root (`master_of_puppets_course.html`, `master_of_puppets_operator_guide.html`). QREF-01 moves them to `quick-ref/`.
- [Phase 57-research-parallel-job-swarming]: Fan-out swarming recommended as next milestone (Tier 1, ~3 phases, 9-12 plans); work-queue pattern deferred
- [Phase 57-research-parallel-job-swarming]: Pre-pin target_node_id at swarm creation to eliminate double-assignment race condition in pull model
- [Phase 57-research-parallel-job-swarming]: Barrier sync via recompute_aggregate trigger on job completion; PARTIAL is a valid terminal swarm state
- [Phase 58-research-organisational-sso]: OIDC chosen over SAML for v1 SSO: natural extension of existing RFC 8628 device flow, Authlib 1.6.x as client library, SAML deferred as future extension
- [Phase 58-research-organisational-sso]: SSO is an EE-only plugin using axiom.ee entry_points; CE installs get 402 stubs; token_version increment on SSO logout same as password-change mechanism
- [Phase 58-research-organisational-sso]: RBAC group re-sync on every SSO login; default viewer role; highest-role-wins; admin break-glass preserved as local-auth only; Mode A/B 2FA configurable per-deployment
- [Phase 59-01]: DATABASE_URL left uncommented with Compose service name placeholder — SQLite is dev-only and operators must know to use Postgres in production
- [Phase 59-documentation]: DOCS-02/DOCS-03: @import placed at bottom of extra.css; mkdocs.yml palette block unchanged — color override done via CSS custom properties only
- [Phase 59-documentation]: Jobs and Nodes nav entries placed before Foundry in Platform Config section — core features precede advanced config
- [Phase 60-quick-reference]: HTML files copied bit-for-bit; root originals deleted via rm (were untracked); Quick Reference nav section appended after API Reference in mkdocs.yml
- [Phase 60-quick-reference]: 6 targeted per-occurrence replacements in course.html replace all Master of Puppets with Axiom without affecting base64 content
- [Phase 60-quick-reference]: Queue card placed after Jobs in nav listing; section title updated to 'nine sections at a glance'
- [Phase 60-quick-reference]: Scheduling Health section placed before Module 4 quiz so learner sees content before being tested; four distinct callouts used for LATE/MISSED, roll-up, API, and retention

### Pending Todos

None.

### Blockers/Concerns

None. All 4 phases are self-contained deliverables — documentation and design docs, no stack dependencies.

## Session Continuity

Last session: 2026-03-24T19:59:34.216Z
Stopped at: Completed 60-03-PLAN.md
Next action: `/gsd:plan-phase 57`
Resume file: None

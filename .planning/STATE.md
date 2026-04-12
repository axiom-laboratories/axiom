---
gsd_state_version: 1.0
milestone: v22.0
milestone_name: Security Hardening
status: planning
last_updated: "2026-04-12"
last_activity: 2026-04-12 — Roadmap created; 9 phases defined; 16 requirements mapped (100% coverage)
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-12)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v22.0 Security Hardening — hardening container security posture and strengthening EE licence protection.

## Current Position

**Phase:** Not started (roadmap approval pending)
**Plan:** —
**Status:** Roadmap created
**Last activity:** 2026-04-12 — Roadmap created with 9 phases (132–140) addressing 16 requirements

## Roadmap Summary

**File:** `.planning/v22.0-ROADMAP.md`

**Structure:**
- 9 phases (132–140)
- 16 requirements (CONT-01 to CONT-10, EE-01 to EE-06)
- 100% coverage (no orphaned requirements)

**Phase breakdown:**
- Container Hardening (Phases 132–136): 10 requirements
  - Phase 132: Non-root user foundation (CONT-01, CONT-06)
  - Phase 133: Network & capabilities (CONT-03, CONT-04)
  - Phase 134: Socket mount & Podman (CONT-02, CONT-09, CONT-10)
  - Phase 135: Resource limits (CONT-05, CONT-07)
  - Phase 136: User propagation (CONT-08)

- EE Licence Protection (Phases 137–140): 6 requirements
  - Phase 137: Signed wheel manifest (EE-01)
  - Phase 138: HMAC boot log (EE-02, EE-03)
  - Phase 139: Entry point validation (EE-04, EE-06)
  - Phase 140: Wheel signing tool (EE-05)

## Previous Milestone

**v21.0 COMPLETE — ALL PHASES SHIPPED**

Milestone shipped: 2026-04-11 (Phases 129–131)
Archive: `.planning/milestones/v21.0-ROADMAP.md`

**Key deliverables:**
- `ActionResponse`, `PaginatedResponse[T]`, `ErrorResponse` on all 89 API routes (100% coverage)
- `SignatureService.countersign_for_node()` — unified countersigning for all job dispatch paths
- HMAC stamping for scheduled jobs at dispatch time (SEC-02 compliance)
- Hard-fail semantics on missing signing key
- 4-scenario E2E integration test suite (4/4 pass); 112 new unit tests

## Next Steps

1. User review of `.planning/v22.0-ROADMAP.md`
2. Approve roadmap or request revisions
3. Execute Phase 132 (Non-Root User Foundation)

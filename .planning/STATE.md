---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-04-12T16:35:00.000Z"
last_activity: "2026-04-12 — Phase 134 Plan 01 complete: Implemented socket-first detection for Docker/Podman with automatic Podman socket recognition (/run/podman/podman.sock), wired network_ref parameter for job container network isolation via jobs_network bridge. All 10 tests passing (7 socket detection + 3 network isolation). CONT-10 satisfied, CONT-02 foundation in place."
progress:
  total_phases: 60
  completed_phases: 52
  total_plans: 150
  completed_plans: 160
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-12)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v22.0 Security Hardening — hardening container security posture and strengthening EE licence protection.

## Current Position

**Phase:** 134 (Socket Mount & Podman Support)
**Plan:** 01 (completed; Socket-First Detection & Network Isolation)
**Status:** Ready to execute Plan 02
**Last activity:** 2026-04-12 — Phase 134 Plan 01 complete: Socket-first detection, Podman socket support, network_ref wiring. 10/10 tests passing. CONT-10 satisfied.

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

## Decisions Made (Phase 133 Plan 01)

**2026-04-12 — Linux capability strategy for all services**
- Decision: Apply `cap_drop: ALL` + `security_opt: no-new-privileges:true` to all 7 services (uniform policy)
- Rationale: Least-privilege principle; prevents privilege escalation via setuid/setgid. Service-specific `cap_add` only where functionally required.
- Impact: Services require correct capabilities for their runtime operations (PostgreSQL init, nginx file setup, Python privilege dropping). Discovered during testing that initial assumptions were incomplete—added missing capabilities per service.
- Status: Implemented, verified via docker inspect, all services running without capability errors

**2026-04-12 — Loopback-only PostgreSQL binding**
- Decision: Change port binding from `5432:5432` to `127.0.0.1:5432:5432`
- Rationale: Prevents external host-to-container access; service-to-service connectivity via Docker DNS `db:` service name remains unaffected (uses bridge network, not host port binding)
- Impact: External tools (psql, DBeaver) must connect via localhost only; internal agent/model services unaffected
- Status: Verified via docker inspect (PortBindings shows 127.0.0.1:5432) and service logs (no connection errors)

## Decisions Made (Phase 132)

**2026-04-12 — UID verification method (Plan 02)**
- Decision: Use `/proc/1/status` instead of `ps -o uid=` for reading process UIDs
- Rationale: `ps` command has different flags across Alpine/Debian; /proc is universally available
- Impact: Tests and scripts now work on all Linux containers regardless of installed tools
- Status: Implemented and verified

**2026-04-12 — Node fixture behavior (Plan 02)**
- Decision: Make node container fixture gracefully skip tests instead of failing when node not running
- Rationale: Server compose doesn't include node; validation compose does. Allow both test environments.
- Impact: Tests can run in any environment without requiring all containers to be present
- Status: Implemented and verified

## Next Steps

1. Execute Phase 132 Plan 03 (Fallback entrypoint testing)
2. Execute Phase 133 (Network & capabilities hardening)
3. Monitor non-root user rollout in staging deployment

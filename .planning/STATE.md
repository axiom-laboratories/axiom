---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
last_updated: "2026-04-12T20:04:46.394Z"
last_activity: "2026-04-12T21:00:00Z — Phase 137 Plan 01 complete: EE wheel manifest verification with Ed25519 signature check. Implemented _verify_wheel_manifest() with 6-step verification (manifest existence, JSON format, required fields, SHA256 hash, signature decoding, Ed25519 verification). Integrated into _install_ee_wheel() and activate_ee_live(). Added ee_activation_error field to /admin/licence endpoint. All 14 unit tests pass. EE-01 satisfied."
progress:
  total_phases: 60
  completed_phases: 56
  total_plans: 155
  completed_plans: 164
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-12)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v22.0 Security Hardening — hardening container security posture and strengthening EE licence protection.

## Current Position

**Phase:** 137 (Signed EE Wheel Manifest)
**Plan:** 01 (complete)
**Status:** Ready to plan
**Last activity:** 2026-04-12T21:00:00Z — Phase 137 Plan 01 complete: EE wheel manifest verification with Ed25519 signature check. Implemented _verify_wheel_manifest() with 6-step verification (manifest existence, JSON format, required fields, SHA256 hash, signature decoding, Ed25519 verification). Integrated into _install_ee_wheel() and activate_ee_live(). Added ee_activation_error field to /admin/licence endpoint. All 14 unit tests pass. EE-01 satisfied.

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

## Decisions Made (Phase 137 Plan 01)

**2026-04-12 — EE wheel manifest verification with Ed25519 signatures**
- Decision: Implement 6-step manifest verification gate (existence, JSON format, required fields, SHA256 hash, signature decoding, Ed25519 signature verification)
- Rationale: Enforce wheel integrity and authenticity; prevent installation of unsigned, tampered, or corrupted wheels
- Impact: RuntimeError on any verification failure; graceful degradation to CE mode; error visibility in /admin/licence endpoint
- Implementation: _verify_wheel_manifest() in ee/__init__.py; integration in _install_ee_wheel() and activate_ee_live(); ee_activation_error field in get_licence_status()
- Status: Implemented and verified; all 14 unit tests pass; EE-01 requirement satisfied

## Decisions Made (Phase 136 Plan 01)

**2026-04-12 — User injection in Foundry-generated Dockerfiles**
- Decision: Inject user creation (adduser/useradd) after FROM; inject chown+USER before CMD
- Rationale: Align Foundry-generated images with Phase 132 base images on non-root execution (UID 1000)
- Impact: All node images now enforce privilege isolation at image build time; consistent security posture across base + custom images
- OS families: DEBIAN (useradd --no-create-home appuser), ALPINE (adduser -D appuser), WINDOWS (skipped)
- Status: Implemented and verified; all 19 foundry tests pass; CONT-08 satisfied

## Decisions Made (Phase 135 Plan 01)

**2026-04-12 — Resource limits for all orchestrator services**
- Decision: Apply explicit mem_limit and cpus to all 7 services in compose.server.yaml per locked decision values
- Rationale: Prevents resource exhaustion by any single service; ensures predictable cluster behavior; supports capacity planning
- Impact: Cgroups enforce hard memory limits and CPU time-slice restrictions at runtime; admin can monitor actual consumption against limits
- Status: Implemented and verified; docker compose config --quiet passes; all 7 services properly configured

**2026-04-12 — Package cleanup for node image**
- Decision: Remove exactly podman, iptables, krb5-user from node image; run apt-get autoremove to clean orphaned deps
- Rationale: Phase 134 migrated from privileged mode (which needed these packages) to socket mount approach (which does not); reduces attack surface
- Impact: Node image is smaller; potential vulnerability surface reduced; pod-to-node execution unchanged (no functional loss)
- Status: Implemented and verified; dpkg -l confirms removal; essential packages (curl, wget, gnupg, apt-transport-https) retained

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

1. Execute Phase 135 Plan 02 (verification and integration testing)
2. Execute Phase 136 (User Propagation & Non-Root Execution Hardening)
3. Complete container hardening milestone (Phases 132–136)

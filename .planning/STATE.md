---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Completed 11-05-PLAN.md
last_updated: "2026-03-11T10:32:33.533Z"
last_activity: 2026-03-09 — Milestone 8 roadmap created, 20 requirements mapped across 3 phases
progress:
  total_phases: 14
  completed_phases: 0
  total_plans: 6
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09)

**Core value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.
**Current focus:** Milestone 8 — mop-push CLI & Job Staging (Phase 17 next)

## Current Position

Phase: Phase 17 (not started)
Plan: —
Status: Roadmap complete — ready to begin Phase 17: Backend — OAuth Device Flow & Job Staging
Last activity: 2026-03-09 — Milestone 8 roadmap created, 20 requirements mapped across 3 phases

Progress: [░░░░░░░░░░] 0% (0 of 3 phases complete)

## Performance Metrics

**Velocity:**
- Phase 7 (07-linux-installer), Plan 02a: 5 min, 2 tasks, 3 files

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06-remote-server | 2 | 5 min | 2.5 min |
| Phase 07-linux-installer P02b | 35 | 2 tasks | 3 files |
| Phase 07-linux-installer P02c | 39 | 2 tasks | 2 files |
| Phase 08-cross-network-validation P01 | 10 | 2 tasks | 1 files |
| Phase 08-cross-network-validation P02 | 150 | 2 tasks | 3 files |
| Phase 09-triggermanager-dashboard-ui P01 | 2 | 2 tasks | 4 files |
| Phase 09 P02 | 2 | 2 tasks | 1 files |
| Phase 09-triggermanager-dashboard-ui P03 | 5 | 2 tasks | 0 files |
| Phase 10-windows-installer-fix P01 | 2 | 2 tasks | 2 files |
| Phase 10 P02 | 2 | 2 tasks | 2 files |
| Phase 11-compatibility-engine P01 | 2 | 1 tasks | 1 files |
| Phase 11-compatibility-engine P02 | 3 | 2 tasks | 4 files |
| Phase 11-compatibility-engine P03 | 3 | 2 tasks | 3 files |
| Phase 11-compatibility-engine P04 | 2 | 1 tasks | 1 files |
| Phase 11-compatibility-engine P05 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Decisions
- Milestone 4: Focus on "Headless" operation and machine-to-machine integrations.
- Milestone 4: Implement dedicated trigger endpoints for CI/CD systems.
- Phase 06-02a: AGENT_URL must be in compose.server.yaml agent environment block (not just .env) for docker compose to pass it through.
- Phase 06-02a: LXC containers need image in localhost:5000 registry (host bridge accessible) — cannot pull from localhost/ prefix.
- Phase 06-02a: node-compose.yaml still references localhost/ image — plan 02b should fix this in main.py.
- [Phase 06-remote-validation]: NODE_IMAGE env var in compose template (main.py) + compose.server.yaml env block enables configurable node image for LXC/remote deployments
- [Phase 06-remote-validation]: Server cert SAN now includes AGENT_URL IP via parsing at cert generation time — allows remote nodes to verify server identity by LAN IP
- [Phase 06-remote-validation]: install_universal.sh: python3 is the preferred CA extraction fallback over grep — available on all Ubuntu systems and handles any JSON spacing
- [Phase 06-remote-validation]: printf '%s' over echo for JSON variables: bash echo interprets \n as newlines, corrupting JSON passed to jq/python3/grep — printf '%s' preserves literal backslash-n sequences
- [Phase 06-remote-validation]: Non-root heartbeat not required as test pass criterion — rootless podman + LXC cgroupv2 is an infrastructure constraint, not an installer defect
- [Phase 08-cross-network-validation]: server_url as explicit first parameter on all API helpers (not a global) so Docker and Podman stacks can be tested against different server IPs in one script run
- [Phase 08-cross-network-validation]: No default container in exec_in_container/push_file prevents accidental cross-container execution when provisioning two stacks simultaneously
- [Phase 08-cross-network-validation]: run_stack_tests() returns skip() stubs so script runs cleanly before Plans 02/03 implement real assertions
- [Phase 08-cross-network-validation]: NODE_EXECUTION_MODE=direct required for DinD cross-network nodes — no Docker socket mounted inside node containers running inside LXC-hosted Docker
- [Phase 08-cross-network-validation]: Both signing.key and verification.key must be written to build context before compose --build to prevent pki.py ensure_signing_key() from regenerating keypair at server startup
- [Phase 08-cross-network-validation]: Server returns naive UTC datetimes (no tz suffix) — must call ts.replace(tzinfo=utc) when comparing to timezone-aware datetimes
- [Phase 08-cross-network-validation]: Server has no GET /jobs/{guid} endpoint; poll using GET /jobs list and filter by guid; job output in GET /jobs/{guid}/executions
- [Phase 09-triggermanager-dashboard-ui]: PATCH and regenerate-token both use foundry:write permission gate - consistent with existing trigger routes
- [Phase 09]: Copy Token uses navigator.clipboard directly with no confirmation dialog for immediate UX
- [Phase 09]: Enable trigger sends PATCH immediately; only Disable requires AlertDialog confirmation
- [Phase 09-triggermanager-dashboard-ui]: All 9 TriggerManager verification steps passed in browser — feature confirmed working end-to-end
- [Phase 10-windows-installer-fix]: Inline function stubs in BeforeEach (not dot-source) for Wave 0 — target functions don't exist in ps1 yet; dot-source added in Plan 02
- [Phase 10-windows-installer-fix]: Fedora 40 base for loader/Containerfile — ships podman in default repos without multi-step manual install
- [Phase 10]: TCP relay cleanup uses finally block to ensure relay Start-Job is stopped even if podman loader throws
- [Phase 10]: Get-PodmanSocketInfo defined but not called in Method-1 — placeholder for future named pipe mounting; current approach uses DOCKER_HOST TCP relay
- [Phase 10-windows-installer-fix]: WIN-05 Pester assertion narrowed to 'Get-Command podman-compose' — functional check only, not raw string match which falsely triggered on menu description text
- [Phase 10-windows-installer-fix]: WIN-06/WIN-07 deferred — no local Podman or Windows/WSL2 hardware; phase closed with WIN-01..05 automated green gate; retest when hardware available
- [Milestone 7 Roadmap]: Phase 11 (Compatibility Engine) is the foundation — OS-family tagging on CapabilityMatrix tools must land before registry enforcement or wizard filtering can work
- [Milestone 7 Roadmap]: Phase 13 bundles PKG + REPO together — both feed the package picker UI that Phase 14 (Wizard) depends on; splitting them would require the wizard to be built twice
- [Milestone 7 Roadmap]: Phase 15 bundles SMCK + BOM + LIFE — all three are post-build concerns that fire after the image is produced; natural delivery boundary
- [Milestone 7 Roadmap]: pypiserver sidecar is infrastructure work inside Phase 13 — needs to exist before wizard can search it (Phase 14)
- [Milestone 8 Roadmap]: Phase 17 is backend-first — OAuth device flow endpoints + ScheduledJob status field + push upsert + REVOKED enforcement must exist before CLI or dashboard can be built
- [Milestone 8 Roadmap]: GOV-CLI-01 (REVOKE enforcement at dispatch) goes into Phase 17 because it is server-side logic adjacent to the status field and push endpoint, not a dashboard concern
- [Milestone 8 Roadmap]: Phase 18 (CLI) and Phase 19 (Dashboard) both depend on Phase 17 but are independent of each other — they can be sequenced in either order; CLI first allows operator testing before dashboard polish
- [Milestone 8 Roadmap]: GOV-CLI-02 (OIDC v2 doc) placed in Phase 19 — it is an architecture document describing the future integration path for the device flow contract, naturally co-located with the dashboard delivery that completes the end-to-end UX
- [Phase 11-01]: Used source-inspection pattern (inspect.getsource) for Wave 0 stubs — consistent with existing test patterns, no conftest or DB fixtures required
- [Phase 11-01]: test_blueprint_dep_confirmation_flow uses pytest.skip until Plan 02 seeds runtime_dependencies data — test still collected (Nyquist-compliant)
- [Phase 11-compatibility-engine]: Soft-delete over hard-delete for CapabilityMatrix: preserves history, reversible, admin can view inactive entries with ?include_inactive=true
- [Phase 11-compatibility-engine]: JSON string storage for runtime_dependencies (TEXT column with DEFAULT '[]'): consistent with existing target_tags pattern in this codebase — avoids JSON column type that SQLite doesn't natively support
- [Phase 11-compatibility-engine]: PUT replaced by PATCH with CapabilityMatrixUpdate for partial update semantics: breaking change acceptable since Plans 04/05 frontend not yet built
- [Phase 11-compatibility-engine]: RUNTIME blueprints: os_family required via model_validator (422 from Pydantic before hitting DB); NETWORK blueprints bypass all validation
- [Phase 11-compatibility-engine]: Two-pass blueprint validation: Pass 1 hard rejects OS mismatches (offending_tools), Pass 2 soft rejects missing deps (deps_to_confirm) with confirmed_deps auto-add
- [Phase 11-compatibility-engine]: foundry_service uses rt_bp.os_family as primary source with derived string fallback for backwards compat with pre-Phase-11 blueprints
- [Phase 11-compatibility-engine]: mutate(undefined) used at call site to satisfy TypeScript when mutationFn accepts optional opts parameter
- [Phase 11-compatibility-engine]: OS Family dropdown placed before Base OS select in CreateBlueprintDialog — drives tool filtering so logical ordering requires it first
- [Phase 11-05]: patchToolMutation omitted: add+soft-delete only in plan scope; PATCH backend available when edit UI needed

### Pending Todos
- Plan 02b: Fix node-compose.yaml image reference in main.py (localhost/ → 192.168.50.148:5000/).
- Run test_installer_lxc.py and fix any installer issues found.

### Blockers/Concerns
- node-compose.yaml generated by main.py still uses `localhost/master-of-puppets-node:latest` which is unreachable from inside LXC — next plan must fix this.

## Session Continuity

Last session: 2026-03-11T10:32:33.531Z
Stopped at: Completed 11-05-PLAN.md
Resume file: None
Next plan: /gsd:plan-phase 17

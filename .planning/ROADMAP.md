# Roadmap: Master of Puppets

## Milestone 6: Remote Environment Validation
**Goal**: Transition from local simulation to true remote infrastructure. Validate the server deployment on remote Linux and prove the universal installer on fresh Debian/Ubuntu nodes.

### Phases
- [x] **Phase 6: Remote Server Deployment** - Validate the Docker Compose stack on a remote Linux host, including reverse proxy configuration and certificate handling. [2026-03-06]
- [x] **Phase 7: Linux Universal Installer** - Ensure `install_universal.sh` correctly imports the MOP CA, installs dependencies, and enrolls nodes on fresh Linux environments. [2026-03-07]
- [ ] **Phase 8: Cross-Network Validation** - Verify mTLS heartbeat, job pulling, and artifact downloading across true network boundaries (non-loopback).
- [ ] **Phase 9: TriggerManager Dashboard UI** - Build the Admin.tsx Automation tab with TriggerManager component to expose the trigger API in the dashboard (was claimed in M4 but not delivered).
- [ ] **Phase 10: Windows Installer Fix** - Fix Podman named-pipe socket mapping in `install_universal.ps1` so the Loader deployment method works on Windows.

### Phase 6: Remote Server Deployment
**Goal:** Validate the Docker Compose stack on a remote Linux host, including reverse proxy configuration and certificate handling.
**Status:** Complete [2026-03-06]

### Phase 7: Linux Universal Installer
**Goal:** Ensure `install_universal.sh` correctly imports the MOP CA, installs dependencies, and enrolls nodes on fresh Linux environments. Use ephemeral Incus LXC containers (manage-test-nodes skill) to validate on a true fresh Linux environment.
**Status:** Complete [2026-03-07]
**Plans:** 4 plans

Plans:
- [x] 06-01-PLAN.md — Research and context [2026-03-06]
- [x] 06-02a-PLAN.md — Environment setup: AGENT_URL fix, registry push, test harness [2026-03-07]
- [x] 06-02b-PLAN.md — Happy path test: fresh LXC install, CA + heartbeat verification, image reference fix [2026-03-07]
- [x] 06-02c-PLAN.md — Edge cases: jq-absent fallback, no-runtime error, non-root behavior [2026-03-07]

### Phase 8: Cross-Network Validation
**Goal:** Verify mTLS heartbeat, job pulling, and artifact downloading across true network boundaries (non-loopback).
**Status:** In Progress
**Plans:** 1/3 plans executed

Plans:
- [ ] 08-01-PLAN.md — Script skeleton: all helpers, provisioning functions, CLI wiring, --dry-run
- [ ] 08-02-PLAN.md — Docker stack validation: CN-01..08 (enroll, heartbeat, job exec, routing, revocation)
- [ ] 08-03-PLAN.md — Podman stack validation: CN-09..16 + podman-compose gap report

### Phase 9: TriggerManager Dashboard UI
**Goal:** Build the Admin.tsx Automation tab with TriggerManager component to expose the trigger CRUD API in the dashboard. This was claimed delivered in Milestone 4 but the component was never created.
**Status:** Not Started

### Phase 10: Windows Installer Fix
**Goal:** Fix Podman named-pipe socket mapping in `install_universal.ps1` so the Loader deployment method (Method 1) works correctly on Windows.
**Status:** Not Started

---

## Archived: Milestone 5 (Notifications & Webhooks)
**Completed**: 2026-03-06
- Phase 1: Alerting Engine & Notification Centre (✓)
- Phase 2: Outbound Webhooks & Payload Signing (✓)
- Phase 3: Integration Examples & Documentation (✓)

## Archived: Milestone 4 (Automation & Integration)
**Completed**: 2026-03-06
- Phase 1: CI/CD Webhooks & External Triggers (✓)
- Phase 2: Conditional Logic & Signal Dispatch (✓)
- Phase 3: Headless Management & SDK (✓)

## Archived: Milestone 3 (Advanced Foundry & Hot-Upgrades)
**Completed**: 2026-03-05
- Phase 1: Capability Vault (✓)
- Phase 2: Tamper Detection (✓)
- Phase 3: Hot-Upgrade Engine (✓)
- Phase 4: Rollout & Gates UI (✓)

## Archived: Milestone 2 (Foundry & Node Lifecycle)
**Completed**: 2026-03-05
- Phase 1: Pipeline Core Fixes (✓)
- Phase 2: Foundry Hardening (✓)
- Phase 3: Lifecycle APIs (✓)
- Phase 4: Provisioning & UI Parity (✓)

## Archived: Milestone 1 (Production Reliability)
**Completed**: 2026-03-05
- Phase 1: Output Capture (✓)
- Phase 2: Retry Policy (✓)
- Phase 3: Execution History (✓)
- Phase 4: Environment Tags (✓)
- Phase 5: Job Dependencies (✓)
- Phase 6: Security Hardening (✓)

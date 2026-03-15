# Roadmap: Master of Puppets

## Milestone 8: mop-push CLI & Job Staging
**Goal**: Zero-friction job signing and publishing from the operator's terminal. A dedicated `mop-push` CLI authenticates via OAuth device flow, signs scripts locally with Ed25519, and pushes jobs into a Staging area. Dashboard provides draft review, scheduling finalization, and one-click publish.
**Status**: [▓▓▓▓▓▓▓▓▓▓] 100% (Complete)
**Completed**: 2026-03-12

### Phases
- [x] **Phase 17: Backend — OAuth Device Flow & Job Staging** - OAuth device authorization endpoint, ScheduledJob status field (DRAFT/ACTIVE/DEPRECATED/REVOKED), /api/jobs/push upsert with dual-token verification, REVOKED enforcement at dispatch (completed 2026-03-12)
- [x] **Phase 18: mop-push CLI** - mop-push login (device flow), job push (create DRAFT/update), job create (active), Ed25519 signing locally, installable SDK package (completed 2026-03-12)
- [x] **Phase 19: Dashboard Staging View & Governance Doc** - Drafts/Staging view, script inspect, finalize scheduling, one-click publish, status badges on all jobs, OIDC v2 path documented (completed 2026-03-12)

## Phase Details

### Phase 17: Backend — OAuth Device Flow & Job Staging
**Goal**: The control plane can issue and exchange device codes, job definitions carry a lifecycle status, and the push endpoint upserts jobs with dual JWT + Ed25519 verification — with REVOKED jobs blocked at dispatch
**Depends on**: Nothing (first Milestone 8 phase)
**Requirements**: AUTH-CLI-01, AUTH-CLI-02, STAGE-01, STAGE-02, STAGE-03, STAGE-04, GOV-CLI-01
**Success Criteria** (what must be TRUE):
  1. Calling `POST /auth/device` returns a device code, user code, verification URL, and expiry — the user code is displayed on the approval page in the browser
  2. Once a user approves the device code in the browser, polling `POST /auth/device/token` returns a short-lived JWT for the authenticated operator
  3. A new `ScheduledJob` created via `/api/jobs/push` defaults to DRAFT status; an existing job updated via the same endpoint stays in its current status and receives a new script and signature
  4. The push endpoint rejects requests with an invalid JWT (401) and rejects requests whose Ed25519 signature does not match the script body (422) before writing anything to the database
  5. Every successful push records `pushed_by` as the authenticated operator's identity on the job definition row
  6. Scheduler skips REVOKED jobs entirely — they are never assigned to any node; admin can set a job to DEPRECATED or REVOKED via the existing job management API
**Plans**: 5 plans

Plans:
- [x] 17-01-PLAN.md — Wave 1: test stubs for all 17 Phase 17 tests (Nyquist Wave 0)
- [x] 17-02-PLAN.md — Wave 2: migration_v27.sql + ScheduledJob status/pushed_by + model updates
- [x] 17-03-PLAN.md — Wave 3: device flow endpoints (POST /auth/device, token exchange, approval page)
- [x] 17-04-PLAN.md — Wave 3: POST /api/jobs/push + REVOKE admin gate + scheduler dispatch hardening
- [x] 17-05-PLAN.md — Wave 4: full verification gate + human approval page check

### Phase 18: mop-push CLI
**Goal**: Operators can install `mop-push` from the local SDK, authenticate via device flow without ever transmitting their private key, and push or create job definitions from the terminal
**Depends on**: Phase 17
**Requirements**: AUTH-CLI-03, AUTH-CLI-04, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. Running `mop-push login` opens the browser to the MoP approval page, waits for the operator to approve, and stores the resulting JWT in a local credentials file
  2. Subsequent CLI commands reuse the stored JWT without prompting for login again; commands fail with a clear "token expired — re-run mop-push login" message when the token is stale
  3. Running `mop-push job push --name my-job --script job.py --key signing.key` signs the script locally with the Ed25519 private key and pushes a new DRAFT to the server — the private key is never sent over the network
  4. Running `mop-push job push --id <uuid> --script job.py --key signing.key` updates an existing job definition with a fresh script and re-generated signature
  5. Running `mop-push job create --name my-job --script job.py --key signing.key --cron "*/5 * * * *" --tags env:prod` creates a fully-scheduled ACTIVE job directly without going through the staging draft flow
  6. `pip install ./mop_sdk` installs the `mop-push` command on the operator's machine from the local package directory
**Plans**: 4 plans (completed 2026-03-12)

Plans:
- [x] 18-01-PLAN.md — Wave 1: Packaging & CLI Skeleton (pyproject.toml, argparse)
- [x] 18-02-PLAN.md — Wave 2: OAuth Device Flow Implementation & Credential Persistence
- [x] 18-03-PLAN.md — Wave 3: Job Signing & Staging (push/create commands)
- [x] 18-04-PLAN.md — Wave 4: Final Verification & E2E Validation

### Phase 19: Dashboard Staging View & Governance Doc
**Goal**: Operators can see all DRAFT jobs in a dedicated Staging view, inspect script content, finalize scheduling, publish to ACTIVE in one click, and all jobs display their lifecycle status badge — with the OIDC v2 integration path documented
**Depends on**: Phase 17
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, GOV-CLI-02
**Success Criteria** (what must be TRUE):
  1. The dashboard shows a Staging/Drafts view listing all DRAFT job definitions, distinct from the active job queue
  2. Clicking a draft job opens a read-only view of the full script content so the operator can review what will be published
  3. The operator can set or change the cron schedule and target tags on a draft job from the dashboard without needing the CLI
  4. Clicking "Publish" on a draft job transitions it to ACTIVE status immediately; the job disappears from the Drafts view and appears in the active job list
  5. Every job in the job list shows a status badge (DRAFT / ACTIVE / DEPRECATED / REVOKED) so operators can see lifecycle state at a glance
  6. An architecture doc explains the OIDC / external IdP integration path as a documented v2 option — the OAuth device flow contract (endpoints, token format) is specified so a future OIDC provider can be substituted
**Plans**: 4 plans (completed 2026-03-12)

Plans:
- [x] 19-01-PLAN.md — Wave 1: UI Foundation (Interfaces, Badges, Tabs)
- [x] 19-02-PLAN.md — Wave 2: Staging Features (Script Inspection, Publish Logic)
- [x] 19-03-PLAN.md — Wave 3: Governance Documentation (OIDC v2 Path)
- [x] 19-04-PLAN.md — Wave 4: Final Verification & E2E

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. Backend — OAuth Device Flow & Job Staging | 5/5 | Complete | 2026-03-12 |
| 18. mop-push CLI | 4/4 | Complete | 2026-03-12 |
| 19. Dashboard Staging View & Governance Doc | 5/5 | Complete    | 2026-03-15 |

---

## Milestone 7: Advanced Foundry & Smelter
**Goal**: Transition the Foundry from a manual blueprint CRUD system to an intelligent, compatibility-aware composition engine with a built-in package registry and governance layer.

### Phases
- [x] **Phase 11: Compatibility Engine** - Tag every CapabilityMatrix tool with OS family, declare runtime deps, enforce OS matching at API and UI (completed 2026-03-11)
- [ ] **Phase 12: Smelter Registry** - Vetted ingredient catalog with CVE scanning, STRICT/WARNING enforcement, non-compliant badge
- [ ] **Phase 13: Package Management & Custom Repos** - Native OS + PIP pre-baking, global core set, APT/APK + GPG repos, pypiserver sidecar, repo presets
- [ ] **Phase 14: Foundry Wizard UI** - 5-step guided composition wizard replacing raw JSON blueprint editing, with real-time OS filtering and registry search
- [ ] **Phase 15: Smelt-Check, BOM & Lifecycle** - Post-build ephemeral validation, JSON bill of materials, ACTIVE/DEPRECATED/REVOKED image states, node blocking
- [ ] **Phase 16: Security & Governance** - SLSA provenance docs, Ed25519-signed provenance, enforced build resource limits, docker --secret for credentials

## Phase Details

### Phase 11: Compatibility Engine
**Goal**: Every Foundry tool carries OS-family and runtime-dependency metadata, and blueprints that violate OS compatibility are rejected at the API and filtered in the UI
**Depends on**: Nothing (first Milestone 7 phase)
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. Every tool in the CapabilityMatrix has an `os_family` field (DEBIAN/ALPINE/etc.) visible in the admin UI
  2. Tool records can declare a required runtime dependency (e.g. Scapy requires Python 3.x) and that dependency is stored and exposed via API
  3. Submitting a blueprint that includes a DEBIAN-only tool against an ALPINE base OS returns a 4xx error with a clear rejection message
  4. The Foundry blueprint editor filters the tool selection list in real-time so only tools compatible with the chosen base OS appear
**Plans**: 6 plans

Plans:
- [ ] 11-01-PLAN.md — Wave 0: test stubs for COMP-01 through COMP-04 (5 failing test functions)
- [ ] 11-02-PLAN.md — DB migration v26 + CapabilityMatrix model/API: is_active, runtime_dependencies, GET filter, PATCH, soft-delete
- [ ] 11-03-PLAN.md — Blueprint creation validation: os_family required for RUNTIME, two-pass OS mismatch + dep-confirmation flow
- [ ] 11-04-PLAN.md — Frontend: CreateBlueprintDialog OS dropdown + filtered tool list + dep-confirm overlay
- [ ] 11-05-PLAN.md — Frontend: Templates.tsx Tools tab with CRUD table + Blueprint os_family badge
- [ ] 11-06-PLAN.md — Verify: full test suite + migration + human verification of all COMP requirements

### Phase 12: Smelter Registry
**Goal**: Admins can maintain a vetted ingredient catalog, known-CVE packages are auto-flagged, and builds using unapproved ingredients are blocked (STRICT) or badged (WARNING)
**Depends on**: Phase 11
**Requirements**: SMLT-01, SMLT-02, SMLT-03, SMLT-04, SMLT-05
**Success Criteria** (what must be TRUE):
  1. Admin can add a package to the Smelter Registry with name, version constraint, sha256, and OS family; the entry appears in the catalog list
  2. Running a CVE scan (pip-audit/Safety) auto-flags catalog entries with known vulnerabilities; flagged entries show a warning indicator
  3. In STRICT mode, attempting to build a template whose blueprint references a package not in the approved catalog fails before Docker build starts
  4. Admin can toggle enforcement mode between STRICT and WARNING from the system config page without restarting the service
  5. In WARNING mode, images built with unapproved ingredients display a Non-Compliant badge on the Templates page
**Plans**: TBD

### Phase 13: Package Management & Custom Repos
**Goal**: Admins can pre-bake native OS packages and PIP packages into images, define a global Core set, add custom APT/APK repos with GPG keys, and use MoP's built-in PyPI store
**Depends on**: Phase 12
**Requirements**: PKG-01, PKG-02, PKG-03, REPO-01, REPO-02, REPO-03, REPO-04
**Success Criteria** (what must be TRUE):
  1. Admin can select native OS packages (apt/apk) for a blueprint and they are installed in the built image without requiring node startup time
  2. Admin can select PIP packages for a blueprint and they are pre-installed at build time, visible in the image's pip list output
  3. Admin can define a global Core package set that automatically appears pre-baked in every new Puppet image without manual blueprint entry
  4. Admin can add a custom APT/APK repository URL + GPG key to a blueprint and the repo is configured inside the built image
  5. Admin can upload a .whl or .tar.gz file to MoP's internal PyPI store (pypiserver sidecar) and it immediately appears as a selectable package in the Foundry package picker
  6. Admin can create a named repo preset (e.g. "Corporate APT Mirror") and toggle it on or off per blueprint from the UI
**Plans**: TBD

### Phase 14: Foundry Wizard UI
**Goal**: Admins can build Puppet images through a guided 5-step wizard rather than editing raw JSON blueprints, with real-time OS-aware filtering and integrated registry search
**Depends on**: Phase 13
**Requirements**: WIZ-01, WIZ-02, WIZ-03
**Success Criteria** (what must be TRUE):
  1. Admin can open the Foundry Wizard and progress through all 5 steps (Base OS → Runtime → Tools → Packages → Repos) without editing any raw JSON
  2. When admin selects a base OS in step 1, tools and packages shown in subsequent steps are filtered to only those compatible with that OS in real-time
  3. Admin can search the Smelter Registry and the internal PyPI store from within the wizard and add results directly to their composition
**Plans**: TBD

### Phase 15: Smelt-Check, BOM & Lifecycle
**Goal**: Every completed build is validated by an ephemeral post-build container, produces a JSON Bill of Materials, and carries a lifecycle state that gates job assignment on nodes
**Depends on**: Phase 14
**Requirements**: SMCK-01, SMCK-02, SMCK-03, BOM-01, BOM-02, LIFE-01, LIFE-02, LIFE-03
**Success Criteria** (what must be TRUE):
  1. After a successful build, an ephemeral container spawned from the new image runs `validation_cmd` for every included tool; results (pass/fail per tool) appear in the build log
  2. If any `validation_cmd` exits non-zero, the build is marked failed and the image is not tagged or pushed to the registry
  3. Every completed build produces a JSON Bill of Materials (packages, tools, repos) stored in the DB and viewable from the template detail page
  4. Template images have lifecycle state (ACTIVE/DEPRECATED/REVOKED) shown as a badge on the Templates page; admin can change state from the UI
  5. Nodes running a REVOKED image are blocked from receiving new job assignments; the Jobs page reflects this constraint
**Plans**: TBD

### Phase 16: Security & Governance
**Goal**: Every build produces a signed SLSA provenance document, runs under enforced resource limits, and credentials are never baked into image history
**Depends on**: Phase 15
**Requirements**: GOV-01, GOV-02, GOV-03, GOV-04
**Success Criteria** (what must be TRUE):
  1. At build completion a SLSA provenance JSON document is generated listing all ingredients and their hashes, and is stored alongside the BOM
  2. The provenance document is signed with the control plane's Ed25519 private key; the signature can be verified with the registered public key
  3. Build containers run with enforced CPU and memory limits (configurable in system config, defaulting to 4 GB RAM); builds that exceed limits are killed and marked failed
  4. Credentials passed to builds use `docker build --secret` and do not appear in `docker history` output for the resulting image
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 11. Compatibility Engine | 6/6 | Complete    | 2026-03-11 |
| 12. Smelter Registry | 0/TBD | Not started | - |
| 13. Package Management & Custom Repos | 0/TBD | Not started | - |
| 14. Foundry Wizard UI | 0/TBD | Not started | - |
| 15. Smelt-Check, BOM & Lifecycle | 0/TBD | Not started | - |
| 16. Security & Governance | 0/TBD | Not started | - |

---

## Milestone 6: Remote Environment Validation
**Goal**: Transition from local simulation to true remote infrastructure. Validate the server deployment on remote Linux and prove the universal installer on fresh Debian/Ubuntu nodes.

### Phases
- [x] **Phase 6: Remote Server Deployment** - Validate the Docker Compose stack on a remote Linux host, including reverse proxy configuration and certificate handling. [2026-03-06]
- [x] **Phase 7: Linux Universal Installer** - Ensure `install_universal.sh` correctly imports the MOP CA, installs dependencies, and enrolls nodes on fresh Linux environments. [2026-03-07]
- [x] **Phase 8: Cross-Network Validation** - Verify mTLS heartbeat, job pulling, and artifact downloading across true network boundaries (non-loopback).
- [x] **Phase 9: TriggerManager Dashboard UI** - Build the Admin.tsx Automation tab with TriggerManager component to expose the trigger API in the dashboard (was claimed in M4 but not delivered). ✓ 2026-03-09
- [x] **Phase 10: Windows Installer Fix** - Fix Podman named-pipe socket mapping in `install_universal.ps1` so the Loader deployment method works on Windows. (completed 2026-03-09)

### Phase 6: Remote Server Deployment
**Goal:** Validate the Docker Compose stack on a remote Linux host, including reverse proxy configuration and certificate handling.
**Status:** Complete [2026-03-06]

### Phase 7: Linux Universal Installer
**Goal:** Ensure `install_universal.sh` correctly imports the MOP CA, installs dependencies, and enrolls nodes on fresh Linux environments. Use ephemeral Incus LXC containers (manage-test-nodes skill) to validate on a true fresh Linux environment.
**Status:** Complete [2026-03-07]
**Plans:** 5/5 plans complete

Plans:
- [x] 06-01-PLAN.md — Research and context [2026-03-06]
- [x] 06-02a-PLAN.md — Environment setup: AGENT_URL fix, registry push, test harness [2026-03-07]
- [x] 06-02b-PLAN.md — Happy path test: fresh LXC install, CA + heartbeat verification, image reference fix [2026-03-07]
- [x] 06-02c-PLAN.md — Edge cases: jq-absent fallback, no-runtime error, non-root behavior [2026-03-07]

### Phase 8: Cross-Network Validation
**Goal:** Verify mTLS heartbeat, job pulling, and artifact downloading across true network boundaries (non-loopback).
**Status:** Complete [2026-03-08]
**Plans:** 3/3 plans executed

Plans:
- [x] 08-01-PLAN.md — Script skeleton: all helpers, provisioning functions, CLI wiring, --dry-run
- [x] 08-02-PLAN.md — Docker stack validation: CN-01..08 (enroll, heartbeat, job exec, routing, revocation)
- [x] 08-03-PLAN.md — Podman stack validation: CN-09..16 + podman-compose gap report

### Phase 9: TriggerManager Dashboard UI
**Goal:** Fix compile errors in TriggerManager, add PATCH/regenerate-token backend endpoints, and deliver Active/Inactive toggle, Copy Token, Rotate Key, and empty state UI features.
**Status:** Complete
**Completed:** 2026-03-09
**Plans:** 3/3 plans executed

Plans:
- [x] 09-01-PLAN.md — Backend: TriggerUpdate model, update_trigger/regenerate_token service methods, PATCH + POST routes
- [x] 09-02-PLAN.md — Frontend: fix missing imports (compile unblock), add toggle/copy-token/rotate-key/empty-state to TriggerManager
- [x] 09-03-PLAN.md — Verify: deploy updated stack, human-verify full trigger lifecycle in browser

### Phase 10: Windows Installer Fix
**Goal:** Fix Podman named-pipe socket mapping in `install_universal.ps1` so the Loader deployment method (Method 1) works correctly on Windows.
**Status:** Complete [2026-03-09] — WIN-01..05 automated and green; WIN-06/WIN-07 deferred pending Windows hardware
**Plans:** 3/3 plans complete

Plans:
- [x] 10-01-PLAN.md — Wave 0: Pester test stubs (WIN-01..05) + loader/Containerfile (WIN-06)
- [x] 10-02-PLAN.md — Fix install_universal.ps1: Assert-PodmanMachineRunning, Get-PodmanSocketInfo, Invoke-LoaderContainer, splatting, podman-compose gate
- [x] 10-03-PLAN.md — Verify: full Pester suite green gate (8/8 GREEN); WIN-06 and WIN-07 deferred (no Windows/Podman hardware available)

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

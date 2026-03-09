# Requirements: Master of Puppets

**Defined:** 2026-03-04
**Updated:** 2026-03-09 — Milestone 7: Advanced Foundry & Smelter
**Core Value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.

## Milestone 1–6 Requirements (Complete)

### Output Capture
- [x] **OUT-01**: Node captures stdout and stderr for every job execution
- [x] **OUT-02**: Exit code is recorded per execution
- [x] **OUT-03**: Each run produces a separate execution record (not just latest result)
- [x] **OUT-04**: User can view execution output logs from the job detail page in the dashboard

### Execution History
- [ ] **HIST-01**: User can view a timeline of past executions per job definition
- [ ] **HIST-02**: User can filter execution history by node, status, and date range
- [ ] **HIST-03**: Each execution record shows: node, start time, duration, exit code, status
- [ ] **HIST-04**: Output is retained for a configurable period before pruning

### Retry Policy
- [ ] **RETR-01**: Job definition can specify a maximum retry count (0 = no retries)
- [ ] **RETR-02**: Retries use exponential backoff with jitter (not immediate re-queue)
- [ ] **RETR-03**: System classifies failures as transient (retry) vs permanent (dead letter)
- [ ] **RETR-04**: Zombie jobs (assigned but never reported back) are reaped and rescheduled

### Job Dependencies
- [ ] **DEP-01**: User can define that job B runs only after job A succeeds (chaining)
- [ ] **DEP-02**: User can define fan-in: job waits for multiple upstream jobs to complete
- [ ] **DEP-03**: System detects and rejects dependency cycles at job creation time
- [ ] **DEP-04**: Dashboard shows blocked/ready status for jobs with unmet dependencies

### Environment Tags
- [ ] **TAG-01**: Operator can assign environment tags (e.g. env:dev, env:test, env:prod) to nodes
- [ ] **TAG-02**: Job definitions can require a specific environment tag
- [ ] **TAG-03**: Strict enforcement: untagged nodes are skipped for env-targeted jobs
- [ ] **TAG-04**: Node environment tags are manageable from the dashboard nodes page

---

## Milestone 7 Requirements — Advanced Foundry & Smelter

### Smelter Registry

- [ ] **SMLT-01**: Admin can add packages to a vetted ingredient catalog (name, version constraint, sha256, OS family)
- [ ] **SMLT-02**: System auto-flags catalog entries with known CVEs via pip-audit/Safety integration
- [ ] **SMLT-03**: Build fails (STRICT mode) if any blueprint ingredient is not in the approved catalog
- [ ] **SMLT-04**: Admin can toggle enforcement mode between STRICT and WARNING per system config
- [ ] **SMLT-05**: Dashboard shows Non-Compliant badge on images built with unapproved ingredients in WARNING mode

### Compatibility Engine

- [ ] **COMP-01**: Every tool in the CapabilityMatrix is tagged with an `os_family` (DEBIAN/ALPINE/etc.)
- [ ] **COMP-02**: Tools can declare a required runtime dependency (e.g. Scapy requires Python 3.x)
- [ ] **COMP-03**: Foundry API rejects blueprints where any tool's `os_family` doesn't match the selected base OS
- [ ] **COMP-04**: Foundry UI filters available tools in real-time based on selected base OS

### Package Management

- [ ] **PKG-01**: Admin can select native OS packages (apt/apk) to pre-bake into an image
- [ ] **PKG-02**: Admin can select PIP packages to pre-install at build time (reducing node startup time)
- [ ] **PKG-03**: Admin can define a global "Core" package set that is auto-injected into every Puppet image

### Custom Repositories

- [ ] **REPO-01**: Admin can add custom APT/APK repository sources with GPG key to a blueprint
- [ ] **REPO-02**: MoP hosts a built-in internal PyPI registry (pypiserver sidecar) — admin can upload .whl/.tar.gz packages
- [ ] **REPO-03**: Internal PyPI packages appear as selectable items in the Foundry package picker
- [ ] **REPO-04**: Admin can define named repo presets (e.g. "Corporate APT Mirror") and toggle them on/off per blueprint

### Foundry Wizard

- [ ] **WIZ-01**: Foundry provides a 5-step guided composition wizard (Base OS → Runtime → Tools → Packages → Repos)
- [ ] **WIZ-02**: Wizard only shows tools and packages compatible with the selected base OS (real-time filtering)
- [ ] **WIZ-03**: Admin can search the Smelter Registry and internal PyPI store from within the wizard

### Smelt-Check

- [ ] **SMCK-01**: After build, an ephemeral container is spawned from the new image and runs `validation_cmd` for every included tool
- [ ] **SMCK-02**: Any `validation_cmd` exit code != 0 aborts the build and marks it failed before tagging/pushing
- [ ] **SMCK-03**: Smelt-Check results (pass/fail per tool) are stored and visible in the dashboard

### Image BOM & Lifecycle

- [ ] **BOM-01**: Every completed build generates a JSON Bill of Materials listing all packages, tools, and repos
- [ ] **BOM-02**: BOM is stored in the DB and viewable from the template detail page in the dashboard
- [ ] **LIFE-01**: Template images have lifecycle states: ACTIVE / DEPRECATED / REVOKED
- [ ] **LIFE-02**: Nodes running a REVOKED image are blocked from receiving new job assignments
- [ ] **LIFE-03**: Dashboard shows lifecycle state badge on all template images

### Security & Governance

- [ ] **GOV-01**: At build completion, a SLSA provenance document is generated listing all ingredients + hashes
- [ ] **GOV-02**: Provenance document is signed with the control plane's Ed25519 private key
- [ ] **GOV-03**: Build process runs with enforced CPU and memory limits (configurable, default 4GB RAM)
- [ ] **GOV-04**: Credentials passed to builds via `docker build --secret` never appear in image history

---

## v2 Requirements (Deferred)

### Advanced Foundry (Phase 2)

- **FNDRY-01**: Multi-arch smelting — support linux/amd64 and linux/arm64 via buildx
- **FNDRY-02**: Warm-up commands baked at build time to prime JIT caches for faster node startup
- **FNDRY-03**: Foundry Pulse — scheduled/webhook-triggered monitoring of upstream base images, auto-rebuild on security patches
- **FNDRY-04**: Layer optimization — automatic squashing and multi-stage builds to strip build-time deps
- **FNDRY-05**: Air-gapped smelting — export baked image + dependencies as encrypted tarball for offline deployment
- **FNDRY-06**: Artifact staging area — upload one-off binaries/.so libraries with auto-generated COPY instructions

### CI/CD Integration

- **CICD-01**: Machine-to-machine async job dispatch (POST /jobs → 202 Accepted with GUID)
- **CICD-02**: Job status polling endpoint (GET /jobs/{guid}/status with Retry-After header)
- **CICD-03**: Output retrieval endpoint (GET /jobs/{guid}/output once complete)
- **CICD-04**: Service Principal authentication documented and tested for CI contexts
- **CICD-05**: Example GitHub Actions / GitLab CI integration snippets provided

### Notifications

- **NOTF-01**: Operator receives alert when a job exhausts all retries
- **NOTF-02**: Operator receives alert when a node goes offline unexpectedly

### Webhooks

- **HOOK-01**: Optional webhook callback when job completes (POST to configured URL)
- **HOOK-02**: Webhook payloads are signed so receivers can verify authenticity

---

---

## Milestone 8 Requirements — mop-push CLI & Job Staging

### OAuth Device Flow (MoP-native)

- [ ] **AUTH-CLI-01**: MoP Control Plane exposes a device authorization endpoint (`POST /auth/device`) that issues a device code and user code
- [ ] **AUTH-CLI-02**: MoP polls and exchanges a device code for a short-lived JWT once the user approves in browser
- [ ] **AUTH-CLI-03**: `mop-push login` opens the browser to the MoP approval page and stores the resulting JWT locally
- [ ] **AUTH-CLI-04**: Stored credentials are reused across CLI invocations until expired

### mop-push CLI

- [ ] **CLI-01**: `mop-push job push --name --script --key` signs the script locally and pushes as DRAFT
- [ ] **CLI-02**: `mop-push job push --id --script --key` updates an existing job definition (re-signs)
- [ ] **CLI-03**: `mop-push job create --name --script --key --cron --tags` creates a fully-scheduled ACTIVE job directly
- [ ] **CLI-04**: CLI is installable as a self-hosted Python package from the `mop_sdk/` directory
- [ ] **CLI-05**: Private key never leaves the operator's machine — only the signature is transmitted

### Job Staging Area (Backend)

- [ ] **STAGE-01**: `ScheduledJob` has a `status` field: DRAFT / ACTIVE / DEPRECATED / REVOKED
- [ ] **STAGE-02**: `POST /api/jobs/push` upsert endpoint — creates a new DRAFT or updates existing job by ID
- [ ] **STAGE-03**: Server verifies the JWT identity before processing, then verifies the Ed25519 signature before saving
- [ ] **STAGE-04**: `pushed_by` field records the authenticated operator identity on each push

### Job Staging Area (Dashboard)

- [ ] **DASH-01**: Dashboard shows a Staging/Drafts view listing all DRAFT jobs
- [ ] **DASH-02**: Operator can inspect a draft job's script content (read-only)
- [ ] **DASH-03**: Operator can finalize scheduling (cron, target tags) on a draft from the dashboard
- [ ] **DASH-04**: One-click "Publish" promotes a DRAFT to ACTIVE
- [ ] **DASH-05**: Job list shows status badge (DRAFT / ACTIVE / DEPRECATED / REVOKED) on all jobs

### Governance

- [ ] **GOV-CLI-01**: Admin can DEPRECATE or REVOKE a job definition; REVOKED jobs are never dispatched to nodes
- [ ] **GOV-CLI-02**: External IdP (OIDC) is documented as a v2 integration path in the architecture

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Silent security weakening | Non-negotiable — any trade-off must be documented and operator opt-in |
| Real-time output streaming | Increases complexity significantly; buffered delivery sufficient |
| Mobile app | Web-first; API covers automation needs |
| Built-in secrets vault | Use external vault; Fernet-at-rest covers in-DB secrets |
| Webhook implementation (v1) | SSRF/DNS rebinding design needed first; deferred to v2 |
| CI/CD integration (v1) | Correct async poll semantics depend on retry + history being solid first |
| Artifact staging area | Low priority relative to registry + wizard; deferred to v2 |
| Multi-arch builds | Buildx complexity; single-arch sufficient for homelab/enterprise target |
| Air-gapped export | Niche use case; deferred until core Smelter is proven |
| External IdP (OIDC) for CLI auth | v2 — MoP-native device flow is sufficient for v1; OIDC integration documented as future path |
| PyPI publishing of mop-push | Self-hosted install from mop_sdk/ is sufficient; public PyPI adds maintenance overhead |
| Real-time job output streaming via CLI | Buffered retrieval sufficient; streaming is a separate feature |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| OUT-01 | Phase 1 | Complete |
| OUT-02 | Phase 1 | Complete |
| OUT-03 | Phase 1 | Complete |
| OUT-04 | Phase 1 | Complete |
| HIST-01 | Phase 3 | Pending |
| HIST-02 | Phase 3 | Pending |
| HIST-03 | Phase 3 | Pending |
| HIST-04 | Phase 3 | Pending |
| RETR-01 | Phase 2 | Pending |
| RETR-02 | Phase 2 | Pending |
| RETR-03 | Phase 2 | Pending |
| RETR-04 | Phase 2 | Pending |
| DEP-01 | Phase 5 | Pending |
| DEP-02 | Phase 5 | Pending |
| DEP-03 | Phase 5 | Pending |
| DEP-04 | Phase 5 | Pending |
| TAG-01 | Phase 4 | Pending |
| TAG-02 | Phase 4 | Pending |
| TAG-03 | Phase 4 | Pending |
| TAG-04 | Phase 4 | Pending |
| SMLT-01 | Phase 12 | Pending |
| SMLT-02 | Phase 12 | Pending |
| SMLT-03 | Phase 12 | Pending |
| SMLT-04 | Phase 12 | Pending |
| SMLT-05 | Phase 12 | Pending |
| COMP-01 | Phase 11 | Pending |
| COMP-02 | Phase 11 | Pending |
| COMP-03 | Phase 11 | Pending |
| COMP-04 | Phase 11 | Pending |
| PKG-01 | Phase 13 | Pending |
| PKG-02 | Phase 13 | Pending |
| PKG-03 | Phase 13 | Pending |
| REPO-01 | Phase 13 | Pending |
| REPO-02 | Phase 13 | Pending |
| REPO-03 | Phase 13 | Pending |
| REPO-04 | Phase 13 | Pending |
| WIZ-01 | Phase 14 | Pending |
| WIZ-02 | Phase 14 | Pending |
| WIZ-03 | Phase 14 | Pending |
| SMCK-01 | Phase 15 | Pending |
| SMCK-02 | Phase 15 | Pending |
| SMCK-03 | Phase 15 | Pending |
| BOM-01 | Phase 15 | Pending |
| BOM-02 | Phase 15 | Pending |
| LIFE-01 | Phase 15 | Pending |
| LIFE-02 | Phase 15 | Pending |
| LIFE-03 | Phase 15 | Pending |
| GOV-01 | Phase 16 | Pending |
| GOV-02 | Phase 16 | Pending |
| GOV-03 | Phase 16 | Pending |
| GOV-04 | Phase 16 | Pending |

| AUTH-CLI-01 | TBD | Pending |
| AUTH-CLI-02 | TBD | Pending |
| AUTH-CLI-03 | TBD | Pending |
| AUTH-CLI-04 | TBD | Pending |
| CLI-01 | TBD | Pending |
| CLI-02 | TBD | Pending |
| CLI-03 | TBD | Pending |
| CLI-04 | TBD | Pending |
| CLI-05 | TBD | Pending |
| STAGE-01 | TBD | Pending |
| STAGE-02 | TBD | Pending |
| STAGE-03 | TBD | Pending |
| STAGE-04 | TBD | Pending |
| DASH-01 | TBD | Pending |
| DASH-02 | TBD | Pending |
| DASH-03 | TBD | Pending |
| DASH-04 | TBD | Pending |
| DASH-05 | TBD | Pending |
| GOV-CLI-01 | TBD | Pending |
| GOV-CLI-02 | TBD | Pending |

**Coverage (Milestone 7):**
- v1 requirements: 29 total
- Mapped to phases: 29/29
- Unmapped: 0

**Coverage (Milestone 8):**
- v1 requirements: 20 total
- Mapped to phases: TBD (roadmapper will assign)
- Unmapped: 20 ⚠️ (pending roadmap creation)

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-09 — Milestone 8 requirements added (20 new requirements across 5 categories); pending roadmap phase assignment*

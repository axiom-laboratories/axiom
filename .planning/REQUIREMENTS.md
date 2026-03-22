# Requirements: Master of Puppets

**Defined:** 2026-03-22
**Milestone:** v12.0 — Operator Maturity
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v12.0 Requirements

### Runtime Expansion (RT)

- [x] **RT-01**: Operator can submit a Bash script job using the unified `script` task type with `runtime: bash`
- [x] **RT-02**: Operator can submit a PowerShell script job using the unified `script` task type with `runtime: powershell`
- [x] **RT-03**: Standard node image ships with Python, Bash, and PowerShell pre-installed (`Containerfile.node`)
- [x] **RT-04**: Backend validates `runtime` field at job creation and rejects unknown values with HTTP 422
- [x] **RT-05**: Job list renders a `display_type` field (`script (bash)`, `script (python)`, `script (powershell)`) computed server-side — frontend never parses payload JSON
- [ ] **RT-06**: Existing `python_script` task type is retained as an alias — all existing jobs and CI pipelines unaffected
- [x] **RT-07**: Operator can schedule a Bash or PowerShell job via job definitions (`ScheduledJob.runtime` field + migration SQL)

### Job Submission UX (JOB)

- [ ] **JOB-01**: Operator can submit a job using a structured guided form (runtime selector, script textarea, target environment dropdown, capability tag chips)
- [ ] **JOB-02**: Operator can view the generated JSON payload from guided mode in a read-only panel without editing it
- [ ] **JOB-03**: Operator can switch to Advanced (raw JSON) mode via a one-way gate with a confirmation dialog; form validates JSON against schema before submission
- [ ] **JOB-04**: Operator can view job details (stdout/stderr, node health, retry state, SECURITY_REJECTED plain-English reason) in a drawer without leaving the Jobs view
- [ ] **JOB-05**: Operator can resubmit an exhausted-retry failed job with one click — new GUID, same payload and signature, originating GUID stored for traceability
- [ ] **JOB-06**: Operator can edit and resubmit a failed job — guided form pre-populated with failed job's payload, signing state cleared, fresh signing required

### Bulk Job Operations (BULK)

- [ ] **BULK-01**: Operator can multi-select jobs using checkboxes; a floating action bar appears showing available bulk actions
- [ ] **BULK-02**: Operator can bulk cancel selected PENDING/RUNNING jobs with a count confirmation
- [ ] **BULK-03**: Operator can bulk resubmit selected FAILED (retries-exhausted) jobs; confirmation shows skipped count for jobs with remaining retries
- [ ] **BULK-04**: Operator can bulk delete selected terminal-state jobs (COMPLETED/FAILED/CANCELLED) with a count confirmation

### Queue & Visibility (VIS)

- [ ] **VIS-01**: A PENDING job's drawer shows an automatic plain-English dispatch diagnosis (no nodes / capability mismatch / all busy / queue position) that updates live via WebSocket
- [ ] **VIS-02**: A dedicated live Queue dashboard view shows PENDING, RUNNING, and recently completed jobs in real time (WebSocket-driven, no polling)
- [ ] **VIS-03**: Nodes page shows a per-node detail drawer (currently running job, queued jobs, recent history, reported capabilities)
- [ ] **VIS-04**: Admin can put a node into DRAINING state from the node detail drawer; DRAINING status is visible in Queue and Nodes views
- [ ] **VIS-05**: Dashboard shows a Scheduling Health panel with aggregate fired/skipped/failed counts and per-definition health indicators with a configurable time window (24h / 7d / 30d)
- [ ] **VIS-06**: Scheduling Health panel detects missed fires (expected cron fires vs actual execution records); affected definitions show a red health indicator

### Scheduled Job Signing Safety (SCHED)

- [x] **SCHED-01**: Scheduled job automatically enters DRAFT state when `script_content` is changed and the existing `signature_payload` is no longer valid
- [x] **SCHED-02**: Jobs in DRAFT state do not dispatch on their cron schedule; each skipped fire is logged with reason: "Skipped: job in DRAFT state, pending re-signing"
- [x] **SCHED-03**: Operator sees a save confirmation modal warning when saving a script change that will transition the job to DRAFT
- [x] **SCHED-04**: Dashboard notification bell shows an in-app notification when a scheduled job enters DRAFT; a WARNING alert is written to the alerts table with `resource_id = scheduled_job_id`

### Search, Scale & Data Management (SRCH)

- [x] **SRCH-01**: Jobs view uses server-side cursor-based pagination — "load more" appends next page; total count shown ("Showing 50 of 12,483")
- [x] **SRCH-02**: Nodes view uses server-side page-based pagination with page controls and total count
- [x] **SRCH-03**: Operator can filter the Jobs view by status, runtime, task type, target node, target tags, created-by, and date ranges — all server-side; active filters shown as dismissible chips
- [x] **SRCH-04**: Operator can search jobs by name or GUID via a free-text search box; operator can optionally name a job at submission time via the guided form
- [x] **SRCH-05**: Operator can export the current filtered Jobs view as CSV
- [ ] **SRCH-06**: Operator can save a job configuration as a reusable named template (signing state explicitly excluded)
- [ ] **SRCH-07**: Operator can load a saved template into the guided job form; all fields remain editable before submission
- [ ] **SRCH-08**: Admin can configure global execution record retention period (default: 14 days); a nightly pruning task hard-deletes expired records excluding pinned records
- [ ] **SRCH-09**: Admin can pin individual execution records to exclude them from automatic pruning; pin/unpin actions are audit-logged
- [ ] **SRCH-10**: Operator can download execution records for a job as CSV from the job detail drawer

### Tech Debt (DEBT)

- [x] **DEBT-01**: NodeStats pruning is SQLite-compatible — removes subquery incompatibility that causes pruning to silently fail on SQLite deployments (MIN-06)
- [x] **DEBT-02**: Foundry service removes the temporary build directory after both successful and failed builds — no stale `/tmp/puppet_build_*` directories accumulate (MIN-07)
- [x] **DEBT-03**: Permission lookups in `require_permission` do not execute a DB query per request — permissions are cached at startup or session level (MIN-08)
- [x] **DEBT-04**: Node ID scan in the secrets directory uses deterministic (sorted) ordering — eliminates non-deterministic behavior on filesystems with unordered readdir (WARN-08)

### Security (SEC)

- [x] **SEC-01**: SECURITY_REJECTED job results produce an audit log entry attributed to the reporting node (system sentinel actor), capturing script hash context
- [x] **SEC-02**: Stored `signature_payload` fields carry an HMAC integrity tag (computed from `ENCRYPTION_KEY`); dispatch verifies the HMAC before sending to a node — tampered payloads are rejected at the orchestrator before reaching any node

### Branding (BRAND)

- [x] **BRAND-01**: Dashboard displays "Image Recipe" in place of "Blueprint", "Node Image" in place of "PuppetTemplate", and "Tool" in place of "CapabilityMatrix entry" throughout the UI (zero API/DB changes)

---

## Future Requirements

### v12.1+ — Node Lifecycle

- **NODE-01**: Operator can view tampered node remediation options (accept drift / push corrective manifest [EE] / isolate + re-image) in the node detail drawer
- **NODE-02**: Cert auto-renewal via mTLS `POST /api/renew` — node renews within configurable threshold (default 14 days before expiry); DRAINING restart
- **NODE-03**: Proactive cert expiry alerting — WARNING at 30 days, CRITICAL at 7 days if not yet renewed
- **NODE-04**: Node onboarding wizard — pre-config + four-tab snippet panel (Token/Docker run/Compose/Script) with live enrollment status via WebSocket

### v12.1+ — Observability & Integrations

- **OBS-01**: Alert management — lifecycle states (Active/Acknowledged/Auto-cleared/Muted), bulk-acknowledge, auto-clear on condition resolution
- **OBS-02**: Maintenance windows — per-node and fleet-wide alert suppression rules
- **OBS-03**: Audit log filtering + export — date range, actor, action type, free-text search, CSV/JSON export
- **OBS-04**: Outbound webhooks — configurable endpoints, per-endpoint event subscriptions, HMAC-signed payloads, retry + dead-letter log

### v12.1+ — Signing & Access

- **AUTH-01**: Inline Ed25519 keypair generation in dashboard (CE) — private key shown once, never stored server-side
- **AUTH-02**: Key approval workflow (EE) — new public keys require a second admin approval before nodes trust them; step-up TOTP for approval
- **AUTH-03**: App-based TOTP 2FA (RFC 6238) — optional per-user, admin-enforceable per-role, air-gap compatible (pyotp)

### v12.x+ — First-Run Polish

- **UX-01**: Contextual empty states on all main views (Nodes, Jobs, Signatures, JobDefinitions, Templates) with relevant CTAs
- **UX-02**: Persistent setup checklist on Dashboard (Upload signing key → Enroll node → Submit first job) — derived from existing API counts, dismissible

### v12.x+ — Fan-out & Campaigns

- **FAN-01**: Node-pinning — optional `target_node_ids` field on Job; node selection loop filters to pinned nodes (prerequisite for fan-out campaigns)
- **FAN-02**: Fan-out campaigns — create N pinned jobs (one per matched node) under a Campaign parent; aggregate progress tracking

### v12.x+ — EE Workstreams

- **EE-01**: `packages.apt` and `packages.powershell` blueprint fields in Foundry — CapabilityMatrix-driven tool injection for EE node images
- **EE-02**: Job container architecture — manifest-driven per-job containers, registry-backed, heartbeat-updated
- **EE-03**: Secret store — native Fernet-encrypted secret store with server-side injection at dispatch, stdout/stderr redaction, RBAC model
- **EE-04**: Object model simplification + wizard (BLOCKED on EE job container architecture)
- **EE-08**: Full `axiom-ee` stub wheel publication to PyPI (deferred from v11.0)

### v12.x+ — Distribution

- **DIST-02**: `axiom-ce` image on Docker Hub (deferred from v11.0 — GHCR covers current scenarios)
- **DIST-04**: Licence issuance portal — web UI or automated pipeline for signed licence key delivery
- **DIST-05**: Periodic licence re-validation (currently startup-only)

## Out of Scope

| Feature | Reason |
|---------|--------|
| OIDC/SAML SSO | Research todo exists; blocked on SSO architecture design — separate workstream |
| Custom RBAC roles + fine-grained permissions | EE-only feature; separate milestone |
| Job dependencies (DAG) | Architectural — requires campaign/fan-out infrastructure first |
| SLSA provenance + `--secret` credentials | Deferred from v7.0; revisit after EE job container architecture settles |
| EE object model simplification | Blocked on EE job container architecture phase |
| Fan-out campaigns (Tier 2) | Blocked on node-pinning (Tier 1) — FAN-01 not in v12.0 scope |
| Secret management (EE native store) | EE dedicated milestone — too large for v12.0 |
| Alert management + maintenance windows | Deferred to v12.1+ observability phase |
| Audit log filtering + export | Deferred to v12.1+ observability phase |
| Outbound webhooks | Deferred to v12.1+ — depends on stable alert/notification surface |
| Node onboarding wizard | Deferred to v12.1+ node lifecycle phase |
| Tampered node remediation | Deferred to v12.1+ node lifecycle phase |
| Cert auto-renewal | Deferred to v12.1+ node lifecycle phase |
| Empty states + onboarding checklist | Deferred to v12.1+ first-run polish phase |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEBT-01 | Phase 46 | Complete |
| DEBT-02 | Phase 46 | Complete |
| DEBT-03 | Phase 46 | Complete |
| DEBT-04 | Phase 46 | Complete |
| SEC-01 | Phase 46 | Complete |
| SEC-02 | Phase 46 | Complete |
| BRAND-01 | Phase 46 | Complete |
| RT-01 | Phase 47 | Complete |
| RT-02 | Phase 47 | Complete |
| RT-03 | Phase 47 | Complete |
| RT-04 | Phase 47 | Complete |
| RT-05 | Phase 47 | Complete |
| RT-06 | Phase 47 | Pending |
| RT-07 | Phase 47 | Complete |
| SCHED-01 | Phase 48 | Complete |
| SCHED-02 | Phase 48 | Complete |
| SCHED-03 | Phase 48 | Complete |
| SCHED-04 | Phase 48 | Complete |
| SRCH-01 | Phase 49 | Complete |
| SRCH-02 | Phase 49 | Complete |
| SRCH-03 | Phase 49 | Complete |
| SRCH-04 | Phase 49 | Complete |
| SRCH-05 | Phase 49 | Complete |
| JOB-01 | Phase 50 | Pending |
| JOB-02 | Phase 50 | Pending |
| JOB-03 | Phase 50 | Pending |
| JOB-04 | Phase 51 | Pending |
| JOB-05 | Phase 51 | Pending |
| JOB-06 | Phase 51 | Pending |
| BULK-01 | Phase 51 | Pending |
| BULK-02 | Phase 51 | Pending |
| BULK-03 | Phase 51 | Pending |
| BULK-04 | Phase 51 | Pending |
| VIS-01 | Phase 52 | Pending |
| VIS-02 | Phase 52 | Pending |
| VIS-03 | Phase 52 | Pending |
| VIS-04 | Phase 52 | Pending |
| VIS-05 | Phase 53 | Pending |
| VIS-06 | Phase 53 | Pending |
| SRCH-06 | Phase 53 | Pending |
| SRCH-07 | Phase 53 | Pending |
| SRCH-08 | Phase 53 | Pending |
| SRCH-09 | Phase 53 | Pending |
| SRCH-10 | Phase 53 | Pending |

**Coverage:**
- v12.0 requirements: 44 total
- Mapped to phases: 44 (Phase 46: 7, Phase 47: 7, Phase 48: 4, Phase 49: 5, Phase 50: 3, Phase 51: 7, Phase 52: 4, Phase 53: 7)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 — traceability complete after roadmap creation*

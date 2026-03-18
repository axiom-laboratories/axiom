# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- 📋 **v10.0 — Axiom Commercial Release** — Phases 29–33 (in progress)

## Phases

<details>
<summary>✅ v7.0 — Advanced Foundry & Smelter (Phases 11–15) — SHIPPED 2026-03-16</summary>

- [x] **Phase 11: Compatibility Engine** — OS family tagging, runtime deps, API/UI enforcement (completed 2026-03-11)
- [x] **Phase 12: Smelter Registry** — Vetted ingredient catalog, CVE scanning, STRICT/WARNING enforcement (completed 2026-03-15)
- [x] **Phase 13: Package Management & Custom Repos** — Local PyPI + APT mirror sidecars, auto-sync, air-gapped upload, pip.conf/sources.list injection, fail-fast enforcement (completed 2026-03-15)
- [x] **Phase 14: Foundry Wizard UI** — 5-step guided composition wizard with real-time OS filtering and Smelter integration (completed 2026-03-16)
- [x] **Phase 15: Smelt-Check, BOM & Lifecycle** — Post-build ephemeral validation, JSON BOM, package index, image ACTIVE/DEPRECATED/REVOKED lifecycle (completed 2026-03-16)

Archive: `.planning/milestones/v7.0-ROADMAP.md`

</details>

<details>
<summary>✅ v8.0 — mop-push CLI & Job Staging (Phases 17–19) — SHIPPED 2026-03-15</summary>

- [x] **Phase 17: Backend — OAuth Device Flow & Job Staging** — RFC 8628 device flow, ScheduledJob status field, /api/jobs/push with dual-token verification, REVOKED enforcement at dispatch (completed 2026-03-12)
- [x] **Phase 18: mop-push CLI** — mop-push login/push/create commands, Ed25519 signing locally, installable SDK package (completed 2026-03-12)
- [x] **Phase 19: Dashboard Staging View & Governance Doc** — Staging tab, script inspection, one-click Publish, status badges, OIDC v2 architecture doc (completed 2026-03-15)

Archive: `.planning/milestones/v8.0-ROADMAP.md`

</details>

<details>
<summary>✅ v9.0 — Enterprise Documentation (Phases 20–28) — SHIPPED 2026-03-17</summary>

- [x] **Phase 20: Container Infrastructure & Routing** — MkDocs Material container, multi-stage Dockerfile, Caddy routing, nginx alias config, site_url alignment, CF Access policy (completed 2026-03-16)
- [x] **Phase 21: API Reference + Dashboard Integration** — OpenAPI export pipeline, Swagger UI rendering, dashboard Docs.tsx replacement with external link (completed 2026-03-16)
- [x] **Phase 22: Developer Documentation** — Architecture guide with Mermaid diagrams, setup & deployment guide, contributing guide (completed 2026-03-17)
- [x] **Phase 23: Getting Started & Core Feature Guides** — End-to-end first-run walkthrough, Foundry guide, axiom-push CLI guide — establishes nav architecture (completed 2026-03-17)
- [x] **Phase 24: Extended Feature Guides & Security** — Job scheduling, RBAC, OAuth guides + full mTLS, audit log, air-gap security & compliance section (completed 2026-03-17)
- [x] **Phase 25: Runbooks & Troubleshooting** — Symptom-first node, job, and Foundry troubleshooting guides + FAQ (completed 2026-03-17)
- [x] **Phase 26: Axiom Branding & Community Foundation** — CLI rename (axiom-push), README rewrite, CONTRIBUTING + CHANGELOG, GitHub community health files, MkDocs naming pass (completed 2026-03-17)
- [x] **Phase 27: CI/CD, Packaging & Distribution** — GitHub Actions CI + release workflows, installer rebranding, PyPI prerequisites (completed 2026-03-17)
- [x] **Phase 28: Infrastructure Gap Closure** — Restored privacy + offline MkDocs plugins; CDN-free docs build verified; INFRA-06 closed (completed 2026-03-17)

Archive: `.planning/milestones/v9.0-ROADMAP.md`

</details>

### v10.0 — Axiom Commercial Release (Phases 29–33)

- [x] **Phase 29: Backend Completeness — Output Capture + Retry Wiring** — Close node.py output gaps, wire scheduler retry propagation, add output retention pruning (completed 2026-03-18)
- [x] **Phase 30: Runtime Attestation** — Node RSA signing of execution bundles, orchestrator verification, attestation storage and export (completed 2026-03-18)
- [ ] **Phase 31: Environment Tags + CI/CD Dispatch** — First-class env_tag column, ENV_TAG heartbeat support, structured POST /api/dispatch endpoint
- [ ] **Phase 32: Dashboard UI — Execution History, Retry State, Env Tags** — Execution history panel, retry state badges, attestation verification badges, env tag badges and filters
- [x] **Phase 33: Licence Compliance + Release Infrastructure** — LEGAL.md, NOTICE file, pyproject.toml licence fields, axiom-laboratories org, PyPI Trusted Publisher, GHCR activation (completed 2026-03-18)

---

## Phase Details

### Phase 29: Backend Completeness — Output Capture + Retry Wiring

**Goal**: The orchestrator reliably captures, stores, and retains per-execution output from every node, and retry policies configured on job definitions actually propagate through to dispatched jobs.

**Depends on**: Phase 28 (v9.0 complete)

**Requirements**: OUTPUT-01, OUTPUT-02, RETRY-01, RETRY-02

**Success Criteria** (what must be TRUE):
  1. A node that executes a job and reports stdout, stderr, and exit code results in a complete `ExecutionRecord` row in the database with all fields populated (job id, node id, script hash, start time, end time, exit code, stdout, stderr)
  2. A job definition with `max_retries=3` and exponential backoff dispatched via the scheduler creates retry attempts automatically when each attempt fails — each attempt is a distinct `ExecutionRecord` row linked to the same job run
  3. The orchestrator runs a scheduled APScheduler pruning task that deletes `ExecutionRecord` rows older than 30 days using a SQLite-compatible delete pattern (no subquery `LIMIT` clause)
  4. `migration_v32.sql` exists and applies cleanly to an existing database — all new columns are nullable and additive
  5. `WorkResponse` includes `max_retries`, `backoff_multiplier`, `timeout_minutes`, and `started_at` fields when a node polls for work

**Plans**: 3 plans

Plans:
- [ ] 29-01-PLAN.md — DB schema extension, Pydantic model updates, migration_v32.sql, failing test stubs
- [ ] 29-02-PLAN.md — Orchestrator service wiring: pull_work() retry fields + job_run_id, report_result() output capture
- [ ] 29-03-PLAN.md — Node-side: direct mode removal, startup guard, script_hash computation, mop_validation compose updates

---

### Phase 30: Runtime Attestation

**Goal**: Every job execution produces a cryptographically signed attestation bundle that the orchestrator verifies using the node's mTLS certificate — giving operators tamper-evident proof of what ran, where, and what it produced.

**Depends on**: Phase 29 (ExecutionRecord columns and retry wiring must be in place so attestation fields have a stable home and `started_at` is available for bundle construction)

**Requirements**: OUTPUT-05, OUTPUT-06, OUTPUT-07

**Success Criteria** (what must be TRUE):
  1. A node produces an attestation bundle containing `script_hash`, `stdout_hash`, `stderr_hash`, `exit_code`, `start_timestamp`, and `cert_serial`, serialised with `json.dumps(bundle, sort_keys=True, separators=(',',':'))`, and signs it with its RSA-2048 mTLS private key using `padding.PKCS1v15()` and `hashes.SHA256()` — the bundle fields are hashed in raw-bytes-first order (hash raw bytes → scrub → truncate → store)
  2. The orchestrator's `attestation_service.py` verifies the RSA signature against the stored `client_cert_pem` for the reporting node; the `attestation_verified` column on the `ExecutionRecord` is set to `verified`, `failed`, or `missing` accordingly
  3. A unit test performs a full RSA sign/verify round-trip against a test certificate fixture, and a mutation test confirms that modifying `exit_code` in the bundle after signing causes verification to fail
  4. `GET /api/executions/{id}/attestation` returns the raw attestation bundle bytes and signature, suitable for offline verification by an independent party
  5. An execution where the node's cert has been revoked after execution stores `failed` as the verification result — not a server error

**Plans**: 3 plans

Plans:
- [ ] 30-01-PLAN.md — Test scaffold, DB schema extension (3 attestation columns), Pydantic model updates, migration_v33.sql
- [ ] 30-02-PLAN.md — Node-side: _build_and_sign_attestation(), hash-order wiring in execute_task(), report_result() extended
- [ ] 30-03-PLAN.md — Orchestrator: attestation_service.py, job_service wiring, GET /api/executions/{id}/attestation endpoint

---

### Phase 31: Environment Tags + CI/CD Dispatch

**Goal**: Nodes carry a first-class environment tag (DEV/TEST/PROD or custom) that job dispatches can target, and a stable documented API endpoint exists for CI/CD pipelines to dispatch jobs by environment and poll for results.

**Depends on**: Phase 29 (retry config must flow through dispatch path so the CI/CD endpoint returns accurate retry-aware responses)

**Requirements**: ENVTAG-01, ENVTAG-02, ENVTAG-04

**Success Criteria** (what must be TRUE):
  1. A node started with `ENV_TAG=PROD` reports that tag in its heartbeat payload and the orchestrator stores it in the `env_tag` column on the `nodes` table — the tag is visible in `GET /nodes` responses
  2. A job dispatched with `env_tag: "PROD"` is only assigned to nodes whose `env_tag` column matches `PROD`; a dispatch targeting `PROD` when no PROD node is eligible returns a structured error (not a 500) with a machine-readable reason
  3. `POST /api/dispatch` accepts `{job_definition_id, env_tag, ...}`, requires service principal auth, and returns `{job_guid, status, job_definition, env_tag, poll_url}` — the `poll_url` field points to a stable endpoint that CI/CD pipelines can poll until the job reaches a terminal state
  4. `GET /api/dispatch/{job_guid}/status` returns structured JSON with `{status, exit_code, node_id, attempt, started_at, completed_at}` — suitable for pipeline pass/fail decisions without HTML scraping

**Plans**: 3 plans

Plans:
- [ ] 31-01-PLAN.md — Test scaffold (Wave 0 stubs), DB schema extension (env_tag on Node/Job/ScheduledJob), Pydantic model updates, migration_v34.sql
- [ ] 31-02-PLAN.md — env_tag filter in pull_work(), receive_heartbeat() storage, scheduler_service propagation, node.py ENV_TAG
- [ ] 31-03-PLAN.md — POST /api/dispatch and GET /api/dispatch/{job_guid}/status routes in main.py

---

### Phase 32: Dashboard UI — Execution History, Retry State, Env Tags

**Goal**: Operators can view the complete execution history for any job or node in the dashboard, see retry state on in-progress and failed runs, inspect stdout/stderr output in a readable terminal view, and see environment tags on nodes.

**Depends on**: Phase 29 (ExecutionRecord API), Phase 30 (attestation_verified column), Phase 31 (env_tag on NodeResponse)

**Requirements**: OUTPUT-03, OUTPUT-04, RETRY-03, ENVTAG-03

**Success Criteria** (what must be TRUE):
  1. The Jobs view shows an execution history panel listing all past runs for a selected job definition — each row shows timestamp, node, exit code, duration, and attestation status (VERIFIED / FAILED / MISSING badge)
  2. Clicking a run in the execution history expands a terminal-style stdout/stderr view with colour-coded exit status — the output is not rendered as raw JSON
  3. An in-progress or failed run with a retry policy shows a badge displaying "Attempt N of M" in the execution detail; all attempt records appear in the history list linked under the same job run
  4. The Nodes view displays the environment tag (DEV / TEST / PROD / custom) as a badge on each node row, and a filter control allows the operator to show only nodes matching a selected environment

**Plans**: TBD

---

### Phase 33: Licence Compliance + Release Infrastructure

**Goal**: Axiom's dual-licence obligations are documented and compliant, and the release infrastructure (PyPI Trusted Publisher, GHCR multi-arch images, docs access) is activated so version tags trigger automated publishing.

**Depends on**: Nothing (fully independent of all feature phases — can run in parallel at any point before the first version tag is pushed)

**Requirements**: LICENCE-01, LICENCE-02, LICENCE-03, LICENCE-04, RELEASE-01, RELEASE-02, RELEASE-03

**Success Criteria** (what must be TRUE):
  1. `LEGAL.md` at the repo root documents the certifi MPL-2.0 usage decision (read-only CA bundle, no modification) and the paramiko LGPL-2.1 linkage assessment (dynamic-only import confirmed, or replaced with `asyncssh` if EE wheel bundling requires static linking)
  2. `NOTICE` file at the repo root lists all required third-party attribution including caniuse-lite CC-BY-4.0 and any other packages identified in the licence audit
  3. Both `mop-sdk/pyproject.toml` and the root `pyproject.toml` include a `License-Expression` field (`Apache-2.0` for CE, `LicenseRef-Proprietary` for EE) and `setuptools>=62.3` for PEP 639 support
  4. The `axiom-laboratories` GitHub organisation exists, the `axiom-sdk` PyPI project has a configured Trusted Publisher (pending publisher via OIDC — not a standard API token), and pushing a version tag triggers the release workflow with a dry-run against test.pypi.org passing first
  5. A documented decision on public `/docs/` access exists — either a confirmed public-facing path for open-source adoption, or an explicit deferral with written rationale referencing the CF Access policy

**Plans**: 3 plans

Plans:
- [ ] 33-01-PLAN.md — paramiko removal + PEP 639 pyproject.toml updates
- [ ] 33-02-PLAN.md — LEGAL-COMPLIANCE.md, NOTICE, DECISIONS.md
- [ ] 33-03-PLAN.md — Release infrastructure setup + testpypi dry-run checkpoint

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Compatibility Engine | v7.0 | 6/6 | Complete | 2026-03-11 |
| 12. Smelter Registry | v7.0 | 10/10 | Complete | 2026-03-15 |
| 13. Package Management & Custom Repos | v7.0 | 8/8 | Complete | 2026-03-15 |
| 14. Foundry Wizard UI | v7.0 | 5/5 | Complete | 2026-03-16 |
| 15. Smelt-Check, BOM & Lifecycle | v7.0 | 5/5 | Complete | 2026-03-16 |
| 17. Backend — OAuth Device Flow & Job Staging | v8.0 | 5/5 | Complete | 2026-03-12 |
| 18. mop-push CLI | v8.0 | 4/4 | Complete | 2026-03-12 |
| 19. Dashboard Staging View & Governance Doc | v8.0 | 5/5 | Complete | 2026-03-15 |
| 20. Container Infrastructure & Routing | v9.0 | 2/2 | Complete | 2026-03-16 |
| 21. API Reference + Dashboard Integration | v9.0 | 2/2 | Complete | 2026-03-16 |
| 22. Developer Documentation | v9.0 | 3/3 | Complete | 2026-03-17 |
| 23. Getting Started & Core Feature Guides | v9.0 | 4/4 | Complete | 2026-03-17 |
| 24. Extended Feature Guides & Security | v9.0 | 5/5 | Complete | 2026-03-17 |
| 25. Runbooks & Troubleshooting | v9.0 | 4/4 | Complete | 2026-03-17 |
| 26. Axiom Branding & Community Foundation | v9.0 | 3/3 | Complete | 2026-03-17 |
| 27. CI/CD, Packaging & Distribution | v9.0 | 3/3 | Complete | 2026-03-17 |
| 28. Infrastructure Gap Closure | v9.0 | 1/1 | Complete | 2026-03-17 |
| 29. Backend Completeness — Output Capture + Retry Wiring | 3/3 | Complete    | 2026-03-18 | — |
| 30. Runtime Attestation | 3/3 | Complete    | 2026-03-18 | — |
| 31. Environment Tags + CI/CD Dispatch | 1/3 | In Progress|  | — |
| 32. Dashboard UI — Execution History, Retry State, Env Tags | v10.0 | 0/? | Not started | — |
| 33. Licence Compliance + Release Infrastructure | 3/4 | Complete    | 2026-03-18 | — |

---

## Archived

- ✅ **v9.0 — Enterprise Documentation** (Phases 20–28) — shipped 2026-03-17 → `.planning/milestones/v9.0-ROADMAP.md`
- ✅ **v8.0 — mop-push CLI & Job Staging** (Phases 17–19) — shipped 2026-03-15 → `.planning/milestones/v8.0-ROADMAP.md`
- ✅ **v7.0 — Advanced Foundry & Smelter** (Phases 11–15) — shipped 2026-03-16 → `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v6.0 — Remote Environment Validation** (Phases 6–10) — shipped 2026-03-06/09 → `.planning/milestones/v6.0-phases/`
- ✅ **v5.0 — Notifications & Webhooks** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v5.0-phases/`
- ✅ **v4.0 — Automation & Integration** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v4.0-phases/`
- ✅ **v3.0 — Advanced Foundry & Hot-Upgrades** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v3.0-phases/`
- ✅ **v2.0 — Foundry & Node Lifecycle** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v2.0-phases/`
- ✅ **v1.0 — Production Reliability** (Phases 1–6) — shipped 2026-03-05 → `.planning/milestones/v1.0-phases/`

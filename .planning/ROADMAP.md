# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- 🚧 **v9.0 — Enterprise Documentation** — Phases 20–25, 28 (in progress)
- 📋 **v10.0 — Axiom Commercial Release** — Phases 26–27 (not started)

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

### 🚧 v9.0 — Enterprise Documentation (In Progress)

**Milestone Goal:** Bring all technical and user documentation to enterprise standard, hosted as a containerised MkDocs wiki within the stack and linked from the dashboard.

- [x] **Phase 20: Container Infrastructure & Routing** — MkDocs Material container, multi-stage Dockerfile, Caddy routing, nginx alias config, site_url alignment, CF Access policy, offline plugins (completed 2026-03-16)
- [x] **Phase 21: API Reference + Dashboard Integration** — OpenAPI export pipeline, Swagger UI rendering, dashboard Docs.tsx replacement with external link (completed 2026-03-16)
- [x] **Phase 22: Developer Documentation** — Architecture guide with Mermaid diagrams, setup & deployment guide, contributing guide (completed 2026-03-17)
- [x] **Phase 23: Getting Started & Core Feature Guides** — End-to-end first-run walkthrough, Foundry guide, mop-push CLI guide — establishes nav architecture (completed 2026-03-17)
- [x] **Phase 24: Extended Feature Guides & Security** — Job scheduling, RBAC, OAuth guides + full mTLS, audit log, air-gap security & compliance section (completed 2026-03-17)
- [x] **Phase 25: Runbooks & Troubleshooting** — Symptom-first node, job, and Foundry troubleshooting guides + FAQ (completed 2026-03-17)

### Phase 28: Infrastructure Gap Closure
**Goal:** Restore offline/air-gap capability by re-adding the `privacy` and `offline` MkDocs plugins removed in the Phase 22 regression commit (ab25961) — any fresh docs image build must produce a CDN-free site
**Requirements:** INFRA-06, SECU-04
**Gap Closure:** Closes gaps from v9.0 audit (INFRA-06 unsatisfied; SECU-04 air-gap checklist item broken)

Plans:
- [ ] 28-01-PLAN.md — Restore privacy + offline plugins in docs/mkdocs.yml; verify builder deps; confirm CDN-free build

---

## Phase Details

### Phase 20: Container Infrastructure & Routing
**Goal**: The docs site is live at `/docs/` with correct asset routing, offline capability, and access control — ready to accept content
**Depends on**: Nothing (first phase of this milestone)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` starts the docs container and the site is reachable at `/docs/` in a browser
  2. Deep asset URLs (e.g., `/docs/assets/stylesheets/main.css`) return 200 — no silent 404s from routing misconfiguration
  3. `docker compose build docs` fails loudly if `mkdocs build --strict` encounters any warning or error
  4. Browsing to `/docs/` from a private window without a Cloudflare Access session results in an authentication challenge, not a page load
  5. The site loads completely with no requests to external CDN domains (verified via browser network tab in an air-gapped/network-restricted environment)
**Plans**: 2 plans

Plans:
- [ ] 20-01-PLAN.md — MkDocs container files (Dockerfile, nginx.conf, mkdocs.yml, requirements.txt, placeholder) + docs service in compose.server.yaml
- [ ] 20-02-PLAN.md — Caddyfile handle /docs/* routing (both :443 + :80), smoke test, CF Access checkpoint

### Phase 21: API Reference + Dashboard Integration
**Goal**: The API reference is auto-generated from the live FastAPI schema at build time and the dashboard links to the docs site instead of rendering markdown inline
**Depends on**: Phase 20
**Requirements**: APIREF-01, APIREF-02, APIREF-03, DASH-01, DASH-02
**Success Criteria** (what must be TRUE):
  1. The `/docs/api-reference/` page renders all API endpoints grouped by tag with request and response schemas visible without any network call to an external Swagger CDN
  2. Adding a new FastAPI route and rebuilding the docs image causes that route to appear in the API reference without any manual file edits
  3. The dashboard sidebar "Docs" entry opens `/docs/` in a new tab rather than rendering an inline markdown view
  4. The old in-app Docs route (`/docs` in React) no longer exists — navigating to it redirects or shows 404
**Plans**: 2 plans

Plans:
- [ ] 21-01-PLAN.md — OpenAPI export pipeline: route tagging, export_openapi.py, Dockerfile build context, mkdocs-swagger-ui-tag
- [ ] 21-02-PLAN.md — React dashboard cleanup: remove Docs.tsx, add external /docs/ sidebar link

### Phase 22: Developer Documentation
**Goal**: Developers and operators can understand the system architecture, set up a local dev environment, and contribute code from the documentation alone
**Depends on**: Phase 20
**Requirements**: DEVDOC-01, DEVDOC-02, DEVDOC-03
**Success Criteria** (what must be TRUE):
  1. The architecture guide renders at least one Mermaid diagram showing the Puppeteer → mTLS → Puppet data flow, viewable in the browser without external rendering services
  2. A developer following the setup & deployment guide on a clean machine can reach a running local stack (SQLite + backend + dashboard) without consulting the codebase
  3. The contributing guide specifies how to run backend and frontend tests and what a passing PR requires
**Plans**: 3 plans

Plans:
- [ ] 22-01-PLAN.md — Architecture guide: Mermaid diagrams, all services, security model, DB schema, Foundry pipeline
- [ ] 22-02-PLAN.md — Setup & deployment guide: quick start, Docker Compose, env vars, local dev gotchas, TLS bootstrap
- [ ] 22-03-PLAN.md — Contributing guide + pyproject.toml + legacy docs cleanup

### Phase 23: Getting Started & Core Feature Guides
**Goal**: A new operator can follow documentation alone to install the stack, enroll a node, and run their first signed job — and the navigation architecture for all future content is locked in
**Depends on**: Phase 20
**Requirements**: GUIDE-01, GUIDE-02, FEAT-01, FEAT-02
**Success Criteria** (what must be TRUE):
  1. The getting started guide is a single linear walkthrough (no section-jumping required) that ends with a confirmed job result visible in the dashboard
  2. Prerequisites are called out explicitly at the start of each guide section with verification steps — the reader knows what to check before proceeding
  3. The Foundry guide covers blueprint creation through image lifecycle with the Wizard walkthrough and Smelter integration visually illustrated
  4. The mop-push CLI guide covers the full operator workflow: install, OAuth login, Ed25519 key setup, push a signed job, and publish from Staging
  5. The top-level navigation in mkdocs.yml is task/audience-oriented (Getting Started / Feature Guides / Security / Developer / API Reference) — established before any further content is written
**Plans**: 4 plans

Plans:
- [ ] 23-01-PLAN.md — mkdocs.yml nav architecture (7 sections), landing page update, Security/Runbooks stubs
- [ ] 23-02-PLAN.md — Getting Started walkthrough: prerequisites.md, install.md, enroll-node.md, first-job.md
- [ ] 23-03-PLAN.md — Foundry feature guide: blueprints, wizard walkthrough, Smelter, image lifecycle
- [ ] 23-04-PLAN.md — mop-push CLI guide: install, OAuth login, Ed25519 key setup, push, Staging → Publish

### Phase 24: Extended Feature Guides & Security
**Goal**: All remaining platform features are documented with usage guides, and the security & compliance section gives enterprise operators everything they need to deploy, harden, and audit the system
**Depends on**: Phase 23
**Requirements**: FEAT-03, FEAT-04, FEAT-05, SECU-01, SECU-02, SECU-03, SECU-04
**Success Criteria** (what must be TRUE):
  1. The job scheduling guide covers the full path from JobDefinition creation through cron syntax, capability targeting, and staging review
  2. The RBAC guide enables an operator to configure least-privilege access for a team without reading source code
  3. The mTLS guide contains the complete cert rotation procedure (existing node with expiring cert) with prerequisite checks, step-by-step commands, and a verification step
  4. The air-gap guide covers package mirroring setup, offline build validation, and the network isolation checklist in full
  5. The audit log guide describes every event type and includes example query patterns for compliance reporting
**Plans**: 5 plans

Plans:
- [x] 24-01-PLAN.md — Nav update + stub files for all 9 Phase 24 pages (Wave 1) (completed 2026-03-17)
- [ ] 24-02-PLAN.md — Job scheduling guide (FEAT-03) + OAuth & authentication guide (FEAT-05) (Wave 2)
- [ ] 24-03-PLAN.md — RBAC operational guide (FEAT-04) + RBAC permission reference (Wave 2)
- [ ] 24-04-PLAN.md — Security Overview + mTLS & Certificates guide (SECU-01) (Wave 3)
- [ ] 24-05-PLAN.md — RBAC Hardening (SECU-02) + Audit Log (SECU-03) + Air-Gap Operation (SECU-04) (Wave 3)

### Phase 25: Runbooks & Troubleshooting
**Goal**: Operators facing a broken system can find the root cause and recovery steps by searching for the symptom they observe — not by knowing which component owns the problem
**Depends on**: Phase 24
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04
**Success Criteria** (what must be TRUE):
  1. Every runbook page opens with a 2-sentence root cause explanation before any recovery steps
  2. The node troubleshooting guide covers enrollment failures, heartbeat loss, and cert errors organised by symptom (e.g., "node shows offline but container is running")
  3. The job execution troubleshooting guide covers dispatch failures, signing errors, and timeout patterns with concrete error messages as section headers where applicable
  4. The FAQ addresses the top misconfigurations documented in the existing gap reports and validation test outputs
**Plans**: 4 plans

Plans:
- [ ] 25-01-PLAN.md — Nav update + stub files for all 4 runbook pages + index.md overview (Wave 1)
- [ ] 25-02-PLAN.md — Node troubleshooting: enrollment failures, heartbeat loss, cert errors (Wave 2)
- [ ] 25-03-PLAN.md — Job execution troubleshooting: dispatch failures, signing errors, timeout patterns (Wave 2)
- [ ] 25-04-PLAN.md — Foundry troubleshooting + unified FAQ (Wave 2)

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
| 20. Container Infrastructure & Routing | 2/2 | Complete    | 2026-03-16 | - |
| 21. API Reference + Dashboard Integration | 2/2 | Complete    | 2026-03-16 | - |
| 22. Developer Documentation | 3/3 | Complete    | 2026-03-17 | - |
| 23. Getting Started & Core Feature Guides | 4/4 | Complete    | 2026-03-17 | - |
| 24. Extended Feature Guides & Security | 5/5 | Complete    | 2026-03-17 | - |
| 25. Runbooks & Troubleshooting | 4/4 | Complete    | 2026-03-17 | - |
| 28. Infrastructure Gap Closure | 1/1 | Complete    | 2026-03-17 | - |
| 26. Axiom Branding & Community Foundation | 3/3 | Complete   | 2026-03-17 | - |
| 27. CI/CD, Packaging & Distribution | v10.0 | 0/TBD | Not started | - |

### Phase 26: Axiom Branding & Community Foundation

**Goal:** The project presents a professional, unified "Axiom" identity to the open-source community — root README rebranded, CONTRIBUTING.md with CLA in place, GitHub issue/PR templates standardised, CHANGELOG.md established, and all user-facing "MoP/Puppeteer/Puppet" naming migrated to Axiom equivalents
**Depends on:** Phase 25
**Plans:** 3/3 plans complete

Plans:
- [ ] 26-01-PLAN.md — pyproject.toml CLI rename (mop-push → axiom-push) + GitHub community health files (issue templates, PR template, CODE_OF_CONDUCT)
- [ ] 26-02-PLAN.md — README.md rewrite (Axiom gateway doc) + CONTRIBUTING.md (CLA, EE boundary) + CHANGELOG.md (Keep a Changelog format)
- [ ] 26-03-PLAN.md — MkDocs full naming pass: mop-push.md → axiom-push.md rename, mkdocs.yml update, all 21 docs files

### Phase 27: CI/CD, Packaging & Distribution

**Goal:** The platform ships via automated, reproducible pipelines — GitHub Actions CI runs tests on every PR and builds Docker CE/EE images on release, `axiom-sdk` is published to PyPI, and the Puppet agent has a documented installation path for end users
**Depends on:** Phase 26
**Plans:** TBD

Plans:
- [ ] TBD (run /gsd:plan-phase 27 to break down)

---

## Archived

- ✅ **v8.0 — mop-push CLI & Job Staging** (Phases 17–19) — shipped 2026-03-15 → `.planning/milestones/v8.0-ROADMAP.md`
- ✅ **v7.0 — Advanced Foundry & Smelter** (Phases 11–15) — shipped 2026-03-16 → `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v6.0 — Remote Environment Validation** (Phases 6–10) — shipped 2026-03-06/09 → `.planning/milestones/v6.0-phases/`
- ✅ **v5.0 — Notifications & Webhooks** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v5.0-phases/`
- ✅ **v4.0 — Automation & Integration** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v4.0-phases/`
- ✅ **v3.0 — Advanced Foundry & Hot-Upgrades** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v3.0-phases/`
- ✅ **v2.0 — Foundry & Node Lifecycle** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v2.0-phases/`
- ✅ **v1.0 — Production Reliability** (Phases 1–6) — shipped 2026-03-05 → `.planning/milestones/v1.0-phases/`

# Requirements: Master of Puppets

**Defined:** 2026-03-16
**Core Value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.

## v9.0 Requirements — Enterprise Documentation

Requirements for the v9.0 milestone. Each maps to roadmap phases.

### Infrastructure & Container

- [x] **INFRA-01**: Operator can run `docker compose up` and have the docs container serve the MkDocs site at `/docs/`
- [x] **INFRA-02**: Docs container is a separate service in `compose.server.yaml` (portable, no coupling to agent or dashboard)
- [x] **INFRA-03**: Docs site builds with `--strict` flag (warnings treated as errors)
- [x] **INFRA-04**: Caddy routes `/docs/*` to the docs container with correct asset URL handling (`site_url` aligned)
- [x] **INFRA-05**: `/docs/*` path is protected by Cloudflare Access policy (not publicly exposed)
- [x] **INFRA-06**: Docs site works offline / air-gapped (no external CDN assets at runtime)

### Dashboard Integration

- [x] **DASH-01**: Sidebar navigation entry "Docs" opens the docs site in a new tab (replaces existing in-app renderer)
- [x] **DASH-02**: The existing `Docs.tsx` route and in-app markdown renderer are removed

### API Reference

- [x] **APIREF-01**: API reference is rendered in MkDocs from a static `openapi.json` snapshot
- [x] **APIREF-02**: `openapi.json` is generated from FastAPI at container build time (no running server required)
- [x] **APIREF-03**: API reference displays all endpoints grouped by tag with request/response schemas

### Developer Documentation

- [ ] **DEVDOC-01**: Architecture guide documents all system components, security model, and data flow (with Mermaid diagrams)
- [ ] **DEVDOC-02**: Setup & deployment guide covers local dev, Docker Compose, production deployment, env vars, TLS bootstrap
- [ ] **DEVDOC-03**: Contributing guide covers code structure, testing conventions, and PR workflow

### User Getting Started

- [ ] **GUIDE-01**: Getting started guide walks a new operator end-to-end: install → enroll first node → dispatch and verify first job
- [ ] **GUIDE-02**: Prerequisites are explicit — CA installation, JOIN_TOKEN behaviour, required env vars — with verification steps

### Feature Guides

- [ ] **FEAT-01**: Foundry guide covers blueprint creation, wizard walkthrough, Smelter integration, and image lifecycle
- [ ] **FEAT-02**: mop-push CLI guide covers install, OAuth login, Ed25519 key setup, push, and publish workflow
- [ ] **FEAT-03**: Job scheduling guide covers JobDefinitions, cron syntax, capability targeting, and staging review
- [ ] **FEAT-04**: RBAC guide covers roles, permissions, user management, and service principals
- [ ] **FEAT-05**: OAuth / authentication guide covers device flow, token lifecycle, and API key usage

### Security & Compliance

- [ ] **SECU-01**: mTLS guide covers Root CA setup, JOIN_TOKEN, cert enrollment, revocation, and rotation
- [ ] **SECU-02**: RBAC configuration guide covers role assignment, permission grants, and least-privilege setup
- [ ] **SECU-03**: Audit log guide covers event types, query patterns, and compliance use cases
- [ ] **SECU-04**: Air-gap operation guide covers package mirroring, offline builds, and network isolation

### Runbooks & Troubleshooting

- [ ] **RUN-01**: Node troubleshooting guide covers enrollment failures, heartbeat loss, and cert errors (symptom-first)
- [ ] **RUN-02**: Job execution troubleshooting covers dispatch failures, signing errors, and timeout patterns
- [ ] **RUN-03**: Foundry troubleshooting covers build failures, Smelt-Check failures, and registry issues
- [ ] **RUN-04**: FAQ addresses the top operator questions (common misconfigurations, gotchas)

## Future Requirements

### Job Execution Pipeline

- **EXEC-01**: Job output capture — stdout/stderr, exit codes, per-execution records
- **EXEC-02**: Execution history — queryable timeline of past runs per job and per node
- **EXEC-03**: Retry policy — configurable retries on failure (count, backoff strategy)
- **EXEC-04**: Job dependencies — job B runs only after job A succeeds

### CI/CD Integration

- **CICD-01**: Environment node tags — DEV / TEST / PROD tags for CI/CD promotion targeting
- **CICD-02**: CI/CD API integration — documented, machine-friendly endpoints for dispatching jobs from pipelines
- **CICD-03**: Conditional triggers — run job based on outcome of previous job or external signal

### Security

- **GOV-01**: SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials

## Out of Scope

| Feature | Reason |
|---------|--------|
| In-browser wiki editing | Git-backed docs is the chosen authoring model; editable wiki adds DB + auth complexity |
| Algolia/external search | Air-gap constraint; built-in lunr search sufficient |
| Versioned docs (mike) | Deferred — adds path restructuring complexity; revisit after content is stable |
| Public-facing docs (unauthed) | Security content (mTLS, certs, tokens) must not be publicly indexed |
| Mobile app | Web-first, API covers automation needs |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 20 | Complete |
| INFRA-02 | Phase 20 | Complete |
| INFRA-03 | Phase 20 | Complete |
| INFRA-04 | Phase 20 | Complete |
| INFRA-05 | Phase 20 | Complete |
| INFRA-06 | Phase 20 | Complete |
| DASH-01 | Phase 21 | Complete |
| DASH-02 | Phase 21 | Complete |
| APIREF-01 | Phase 21 | Complete |
| APIREF-02 | Phase 21 | Complete |
| APIREF-03 | Phase 21 | Complete |
| DEVDOC-01 | Phase 22 | Pending |
| DEVDOC-02 | Phase 22 | Pending |
| DEVDOC-03 | Phase 22 | Pending |
| GUIDE-01 | Phase 23 | Pending |
| GUIDE-02 | Phase 23 | Pending |
| FEAT-01 | Phase 23 | Pending |
| FEAT-02 | Phase 23 | Pending |
| FEAT-03 | Phase 24 | Pending |
| FEAT-04 | Phase 24 | Pending |
| FEAT-05 | Phase 24 | Pending |
| SECU-01 | Phase 24 | Pending |
| SECU-02 | Phase 24 | Pending |
| SECU-03 | Phase 24 | Pending |
| SECU-04 | Phase 24 | Pending |
| RUN-01 | Phase 25 | Pending |
| RUN-02 | Phase 25 | Pending |
| RUN-03 | Phase 25 | Pending |
| RUN-04 | Phase 25 | Pending |

**Coverage:**
- v9.0 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 — traceability complete after roadmap creation*

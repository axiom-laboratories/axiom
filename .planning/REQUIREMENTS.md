# Requirements: Axiom

**Defined:** 2026-03-24
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v13 Requirements

### Research — Swarming

- [x] **SWRM-01**: Design doc produced covering parallel job swarming use case analysis (is fan-out + campaigns sufficient or is there a genuine gap?)
- [x] **SWRM-02**: Design doc covers architectural impact on the pull model (what breaks, backpressure, ordering/barrier synchronisation)
- [x] **SWRM-03**: Design doc delivers a complexity/value trade-off recommendation with clear next-step guidance

### Research — SSO

- [x] **SSO-01**: Protocol recommendation produced (OIDC vs SAML, rationale for non-air-gapped EE deployments)
- [x] **SSO-02**: JWT bridge design documented (exchange flow, `token_version` interaction, SSO session invalidation)
- [x] **SSO-03**: RBAC group mapping design documented (IdP group → MoP role mapping, default role on first SSO login)
- [x] **SSO-04**: Cloudflare Access integration pattern documented (`Cf-Access-Jwt-Assertion` header trust model, security implications)
- [x] **SSO-05**: Air-gap isolation strategy documented (feature flag/plugin pattern, zero impact on offline deployments)
- [x] **SSO-06**: TOTP 2FA interaction policy documented (SSO auth + MoP TOTP for step-up actions)

### Documentation

- [ ] **DOCS-01**: `.env.example` created listing all required and optional env vars with descriptions for the release container
- [ ] **DOCS-02**: "Running with Docker" deployment section added to docs covering env var requirements
- [ ] **DOCS-03**: Docs/wiki branding (colours, fonts, logo) aligned with dashboard visual identity
- [ ] **DOCS-04**: Existing docs updated for v12.0 changes (unified `script` type, guided form, DRAFT lifecycle, bulk ops, queue view, scheduling health, retention, UI label renames)

### Quick Reference

- [ ] **QREF-01**: Both HTML files moved from project root to `quick-ref/` directory
- [ ] **QREF-02**: Course file rebranded from "Master of Puppets" to "Axiom" throughout
- [ ] **QREF-03**: Operator guide updated for v12.0 feature set (new views, task types, form modes, node states)
- [ ] **QREF-04**: Course content updated to reflect current architecture and tooling

## Future Requirements

*(None captured yet — deferred items will be added here as they emerge)*

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSO implementation | Research phase only — implementation deferred until design doc complete |
| Swarming implementation | Research phase only — implementation deferred until design doc complete |
| EE secret management | Dedicated EE milestone |
| Fan-out campaigns | Requires node-pinning Tier 1 first (future milestone) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SWRM-01 | Phase 57 | Complete |
| SWRM-02 | Phase 57 | Complete |
| SWRM-03 | Phase 57 | Complete |
| SSO-01 | Phase 58 | Complete |
| SSO-02 | Phase 58 | Complete |
| SSO-03 | Phase 58 | Complete |
| SSO-04 | Phase 58 | Complete |
| SSO-05 | Phase 58 | Complete |
| SSO-06 | Phase 58 | Complete |
| DOCS-01 | Phase 59 | Pending |
| DOCS-02 | Phase 59 | Pending |
| DOCS-03 | Phase 59 | Pending |
| DOCS-04 | Phase 59 | Pending |
| QREF-01 | Phase 60 | Pending |
| QREF-02 | Phase 60 | Pending |
| QREF-03 | Phase 60 | Pending |
| QREF-04 | Phase 60 | Pending |

**Coverage:**
- v13 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial definition*

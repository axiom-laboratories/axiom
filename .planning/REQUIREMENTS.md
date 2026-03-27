# Requirements: Axiom v14.4 Go-to-Market Polish

**Defined:** 2026-03-27
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v14.4 Requirements

### Banner (Licence State Notifications)

- [x] **BNR-01**: Admin user sees amber banner when licence is in GRACE state
- [x] **BNR-02**: Admin user sees red banner when licence is in DEGRADED_CE state
- [x] **BNR-03**: Admin user can dismiss the GRACE banner (dismissal persists for the session)
- [x] **BNR-04**: DEGRADED_CE banner cannot be dismissed
- [x] **BNR-05**: Licence state banners are not visible to operator or viewer roles

### CLI (axiom-push Signing UX)

- [x] **CLI-01**: `axiom-push` reads `AXIOM_URL` env var for server address (fixes silent MOP_URL mismatch)
- [x] **CLI-02**: User can generate an Ed25519 keypair locally with `axiom-push key generate`
- [x] **CLI-03**: User can complete login, key generation, and public key registration with `axiom-push init`
- [x] **CLI-04**: `first-job.md` documents the `axiom-push init` / `key generate` flow as the primary path

### Install (Golden Path Docs)

- [x] **INST-01**: `compose.cold-start.yaml` does not include bundled test nodes (puppet-node-1, puppet-node-2)
- [x] **INST-02**: `install.md` does not reference bundled node JOIN_TOKENs (atomic with INST-01)

### Marketing (GitHub Pages)

- [x] **MKTG-01**: `docs-deploy.yml` deploys MkDocs output to `/docs/` subdirectory so the repo root is available for the homepage
- [x] **MKTG-02**: Marketing homepage (`index.html`) is deployed to the root of GitHub Pages at `axiom-laboratories.github.io/axiom/`

## Future Requirements

### SSO / Identity

- **EE-09**: OIDC/SAML SSO integration (design doc complete in v13.0)
- **EE-10**: Custom RBAC roles + fine-grained permissions

### Distribution

- **DIST-02**: `axiom-ce` image on Docker Hub (deferred from v11.0)
- **DIST-04**: Licence issuance portal — web UI or automated pipeline for signed licence key delivery
- **DIST-05**: Periodic licence re-validation (startup-only currently; APScheduler 6h re-check deferred)
- **EE-08**: Full `axiom-ee` stub wheel publication to PyPI

### Platform

- **JOB-DEP-01**: Job dependencies — job B runs only after job A succeeds (linear)
- **JOB-DEP-02**: Conditional triggers — run job based on outcome of previous job or external signal
- **SLSA-01**: SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first; API covers automation needs |
| Silent security weakening | Any trade-off must be documented and operator opt-in |
| Private key transmission | Ed25519 private keys must never leave the operator machine |
| Real-time collaborative script editing | Single author, versioned by signing |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BNR-01 | Phase 77 | Complete |
| BNR-02 | Phase 77 | Complete |
| BNR-03 | Phase 77 | Complete |
| BNR-04 | Phase 77 | Complete |
| BNR-05 | Phase 77 | Complete |
| CLI-01 | Phase 78 | Complete |
| CLI-02 | Phase 78 | Complete |
| CLI-03 | Phase 78 | Complete |
| CLI-04 | Phase 78 | Complete |
| INST-01 | Phase 79 | Complete |
| INST-02 | Phase 79 | Complete |
| MKTG-01 | Phase 80 | Complete |
| MKTG-02 | Phase 80 | Complete |

**Coverage:**
- v14.4 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 — traceability mapped to phases 77–80*

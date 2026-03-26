# Requirements: Axiom

**Defined:** 2026-03-25
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v14.1 Requirements

Requirements for the First-User Readiness milestone. All items derive from the v14.0 cold-start friction report (`mop_validation/reports/cold_start_friction_report.md`). Every P1 item must be resolved for the READY verdict.

### Code Fixes

- [x] **CODE-01**: Containerfile.node docker CLI binary fix is committed and verified (`COPY --from=docker:cli` present, `docker --version` runs in built image)
- [x] **CODE-02**: `/tmp:/tmp` bind mount is present in `compose.cold-start.yaml` for both puppet-node services and verified (job scripts visible to Docker socket)
- [x] **CODE-03**: PowerShell `.deb` download in `Containerfile.node` has `--platform linux/amd64` guard (prevents silent failure on arm64 build hosts)
- [x] **CODE-04**: `/api/executions` and all 7 related execution routes are CE-gated — moved to EE router with a new `ee/interfaces/executions.py` CE stub returning 402; CE mode returns 402 verified by `test_ce_smoke.py`

### Documentation Fixes

- [x] **DOCS-01**: `install.md` has explicit admin password setup step (create `.env` with `ADMIN_PASSWORD=<value>`) before the `docker compose up` instruction
- [x] **DOCS-02**: `mkdocs.yml` has `pymdownx.tabbed: alternate_style: true` in `markdown_extensions` (enables CLI/Dashboard tab pairs across docs)
- [x] **DOCS-03**: `enroll-node.md` has a CLI (curl) JOIN_TOKEN generation path as a primary alternative to the dashboard GUI step
- [x] **DOCS-04**: `enroll-node.md` Option B compose snippet uses the correct Axiom node image (`localhost/master-of-puppets-node:latest`) instead of `python:3.12-alpine`
- [x] **DOCS-05**: `enroll-node.md` replaces all `EXECUTION_MODE=direct` references with `EXECUTION_MODE=docker` (direct mode removed from code)
- [x] **DOCS-06**: `enroll-node.md` AGENT_URL guidance corrected — removes `172.17.0.1:8001` as primary recommendation; adds `https://agent:8001` as the cold-start compose path
- [x] **DOCS-07**: `enroll-node.md` Option B has a Docker socket volume mount note (`/var/run/docker.sock:/var/run/docker.sock` required for `EXECUTION_MODE=docker`)
- [x] **DOCS-08**: `install.md` documents a pre-built compose / tarball install alternative for users without GitHub access
- [x] **DOCS-09**: `first-job.md` has Ed25519 signing key setup as numbered prerequisites before the dispatch step (generate keypair → register public key at `POST /signatures`)
- [x] **DOCS-10**: `first-job.md` has a CLI/API dispatch path (curl `POST /jobs` with signed payload) as an alternative to the guided dashboard form
- [x] **DOCS-11**: `first-job.md` has a pre-dispatch key registration callout making the signing prerequisite visually prominent before any dispatch attempt

### EE Documentation Fixes

- [x] **EEDOC-01**: `ee-install.md` (or equivalent EE getting-started page) replaces all `/api/admin/features` references with the correct `/api/features` endpoint
- [x] **EEDOC-02**: `licensing.md` uses consistent `AXIOM_LICENCE_KEY` naming throughout (no `AXIOM_EE_LICENCE_KEY` infix)

## Future Requirements

### Next Milestones

- Job dependencies — job B runs only after job A succeeds (linear then DAG)
- Conditional triggers — run job based on outcome of previous job or external signal
- SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials
- DIST-02: `axiom-ce` image on Docker Hub
- EE-08: Full `axiom-ee` stub wheel publication to PyPI
- DIST-04: Licence issuance portal
- DIST-05: Periodic licence re-validation
- EE-09: OIDC/SAML SSO integration
- EE-10: Custom RBAC roles + fine-grained permissions

## Out of Scope

| Feature | Reason |
|---------|--------|
| New platform features | v14.1 is a remediation milestone only — no new capabilities |
| Automated re-run of full cold-start Gemini test | Gemini Tier 1 paid key required; validation is manual for this milestone |
| docker:cli air-gap mirror instructions | Complex infrastructure concern; deferred to air-gap operations guide |
| per-node /tmp isolation (`/tmp/axiom-node-N:/tmp`) | Hardened form of the DinD fix; acceptable for homelab; deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CODE-01 | Phase 66 | Complete |
| CODE-02 | Phase 66 | Complete |
| CODE-03 | Phase 66 | Complete |
| CODE-04 | Phase 66 | Complete |
| DOCS-01 | Phase 70 | Complete |
| DOCS-02 | Phase 67 | Complete |
| DOCS-03 | Phase 70 | Complete |
| DOCS-04 | Phase 67 | Complete |
| DOCS-05 | Phase 67 | Complete |
| DOCS-06 | Phase 67 | Complete |
| DOCS-07 | Phase 67 | Complete |
| DOCS-08 | Phase 70 | Complete |
| DOCS-09 | Phase 67 | Complete |
| DOCS-10 | Phase 67 | Complete |
| DOCS-11 | Phase 67 | Complete |
| EEDOC-01 | Phase 68 | Complete |
| EEDOC-02 | Phase 68 | Complete |

**Coverage:**
- v14.1 requirements: 17 total
- Mapped to phases: 17 (3 reset to Pending — gap closure Phase 70)
- Unmapped: 0

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-26 after gap closure plan — DOCS-01, DOCS-03, DOCS-08 reassigned to Phase 70*

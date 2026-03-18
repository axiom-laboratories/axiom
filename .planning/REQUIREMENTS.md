# Requirements: Axiom Orchestrator

**Defined:** 2026-03-17
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

---

## v10.0 Requirements — Axiom Commercial Release

### Release Infrastructure

- [x] **RELEASE-01**: Operator can publish `axiom-sdk` to PyPI automatically via GitHub Actions OIDC (Trusted Publisher — `axiom-laboratories` org + PyPI project prerequisites documented and configured)
- [x] **RELEASE-02**: Multi-arch GHCR images (`ghcr.io/axiom-laboratories/axiom`) publish automatically when a version tag is pushed, using the existing release workflow
- [x] **RELEASE-03**: Operator has a documented decision on public `/docs/` access — either a public-facing subdomain/path for open-source adoption, or an explicit deferral with rationale

### Job Output & Execution History

- [x] **OUTPUT-01**: Node captures stdout, stderr, and exit code for every job execution and reports them to the orchestrator on completion
- [x] **OUTPUT-02**: Orchestrator stores per-execution records (job id, node id, script hash, start time, end time, exit code, stdout, stderr)
- [ ] **OUTPUT-03**: User can view stdout/stderr output for any past execution from the dashboard (Jobs view or Staging view)
- [ ] **OUTPUT-04**: User can query execution history — list of all past runs for a given job definition or node, with status and timestamps

### Runtime Attestation

- [x] **OUTPUT-05**: Node produces a runtime attestation bundle — (script hash + stdout hash + stderr hash + exit code + start timestamp + node cert serial), serialised and signed with the node's mTLS client private key
- [x] **OUTPUT-06**: Orchestrator verifies the attestation signature against the stored node certificate for every execution; verification result (verified / failed / missing) is stored on the execution record
- [x] **OUTPUT-07**: Attestation bundles (raw signed bytes) are stored and can be exported via API for independent offline verification

### Retry Policy

- [x] **RETRY-01**: User can configure a retry policy on a job definition — maximum retry count and backoff strategy (fixed interval or exponential)
- [x] **RETRY-02**: When a job execution fails (non-zero exit code or node timeout), the orchestrator automatically re-dispatches according to the retry policy; each attempt is a separate execution record linked to the same job run
- [ ] **RETRY-03**: Dashboard displays retry state (attempt N of M) on in-progress and failed runs, and shows all attempt records in execution history

### Environment Tags & CI/CD Targeting

- [x] **ENVTAG-01**: Node has a configurable environment tag (DEV / TEST / PROD, or custom string) declared at enrollment and stored on the node record
- [ ] **ENVTAG-02**: Job definitions and ad-hoc dispatches can specify an environment tag as an additional targeting constraint (combined with existing capability matching)
- [ ] **ENVTAG-03**: Dashboard Nodes view displays the environment tag for each node; tag is filterable
- [ ] **ENVTAG-04**: A documented CI/CD dispatch API endpoint accepts environment tag as a targeting parameter and returns structured JSON (job id, status, node assigned) — suitable for pipeline integration

### Licence Compliance

- [x] **LICENCE-01**: `LEGAL.md` documents the certifi MPL-2.0 usage decision — read-only CA bundle, no source modification, obligations satisfied
- [x] **LICENCE-02**: `mop-sdk/pyproject.toml` (and root `pyproject.toml`) includes a `License-Expression` field — `Apache-2.0` for CE, `LicenseRef-Proprietary` for EE, consistent with the dual-licence model
- [x] **LICENCE-03**: `NOTICE` file at repo root lists all required third-party attribution — caniuse-lite CC-BY-4.0, and any other packages with attribution requirements identified in the audit
- [x] **LICENCE-04**: paramiko LGPL-2.1 linkage is assessed — dynamic-only import confirmed and documented in `LEGAL.md`, or replaced with `asyncssh` (MIT) if EE wheel bundling requires static linking

---

## v11.0 Requirements — Job Pipeline (Deferred)

### Job Dependencies

- **PIPELINE-01**: User can declare that job B depends on job A — job B is dispatched only after job A completes successfully
- **PIPELINE-02**: Job dependency chains support linear sequences (A → B → C)
- **PIPELINE-03**: Job dependency graphs support fan-out and fan-in (DAG topology)

### Conditional Triggers

- **PIPELINE-04**: User can configure a conditional trigger — job B dispatches only if job A exits with a specific code or produces output matching a pattern
- **PIPELINE-05**: External signal triggers — an authenticated API call can trigger a job definition outside of its cron schedule

---

## Out of Scope — v10.0

| Feature | Reason |
|---------|--------|
| DAG job dependencies | Deferred to v11.0 — retry + env tags + attestation are the v10 focus |
| Conditional triggers | Deferred to v11.0 — same rationale |
| SLSA provenance | Structured attestation deferred; runtime attestation (OUTPUT-05..07) covers the immediate need |
| Live log streaming | WebSocket streaming of job output deferred — captured post-execution output covers v10 observability needs |
| External OIDC / SSO | MoP-native OAuth device flow sufficient for v10; OIDC documented as v2 path |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RELEASE-01 | Phase 33 | Complete |
| RELEASE-02 | Phase 33 | Complete |
| RELEASE-03 | Phase 33 | Complete |
| OUTPUT-01 | Phase 29 | Complete |
| OUTPUT-02 | Phase 29 | Complete |
| OUTPUT-03 | Phase 32 | Pending |
| OUTPUT-04 | Phase 32 | Pending |
| OUTPUT-05 | Phase 30 | Complete |
| OUTPUT-06 | Phase 30 | Complete |
| OUTPUT-07 | Phase 30 | Complete |
| RETRY-01 | Phase 29 | Complete |
| RETRY-02 | Phase 29 | Complete |
| RETRY-03 | Phase 32 | Pending |
| ENVTAG-01 | Phase 31 | Complete |
| ENVTAG-02 | Phase 31 | Pending |
| ENVTAG-03 | Phase 32 | Pending |
| ENVTAG-04 | Phase 31 | Pending |
| LICENCE-01 | Phase 33 | Complete |
| LICENCE-02 | Phase 33 | Complete |
| LICENCE-03 | Phase 33 | Complete |
| LICENCE-04 | Phase 33 | Complete |

**Coverage:**
- v10.0 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 — traceability populated after roadmap creation*

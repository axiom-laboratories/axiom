# Requirements: Axiom v15.0 — Operator Readiness

**Defined:** 2026-03-28
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v15.0 Requirements

### Licence Tooling

- [ ] **LIC-01**: Operator can migrate the licence signing private key out of the public repo into a private `axiom-licences` repo, with key rotation if needed
- [ ] **LIC-02**: CI guard prevents PEM private key content from being committed to the public repo
- [ ] **LIC-03**: Operator can run `issue_licence.py --customer X --tier EE --nodes N --expiry YYYY-MM-DD` to generate a base64 licence blob offline
- [ ] **LIC-04**: Each issued licence is recorded as a YAML file in `axiom-licences/licences/issued/` and committed as an audit trail
- [ ] **LIC-05**: `issue_licence.py` supports `--no-remote` flag for air-gapped operators (writes record to local file instead of GitHub)

### Node Validation Jobs

- [ ] **JOB-01**: Operator can dispatch a signed bash reference job and verify it executes successfully on a bash-capable node
- [ ] **JOB-02**: Operator can dispatch a signed Python reference job and verify it executes successfully on a Python-capable node
- [ ] **JOB-03**: Operator can dispatch a signed PowerShell reference job and verify it executes successfully on a PWSH-capable node
- [ ] **JOB-04**: A signed volume mapping validation job verifies files written inside the container persist at the expected host-side mount path
- [ ] **JOB-05**: A signed network filtering validation job verifies that allowed hosts are reachable and blocked hosts are not
- [ ] **JOB-06**: A signed memory-hog job is killed (OOM) rather than completing when it exceeds its node memory limit
- [ ] **JOB-07**: A signed CPU-spin job is throttled or killed when it exceeds its node CPU limit

### Package Repo Docs

- [ ] **PKG-01**: Operator can follow a runbook to configure a devpi PyPI mirror sidecar and point a Blueprint at it via `pip.conf` injection
- [ ] **PKG-02**: Operator can follow guidance to configure an apt-cacher-ng APT mirror and verify packages resolve from it
- [ ] **PKG-03**: Operator can follow guidance to set up a BaGet/PSGallery mirror and install a PWSH module from it inside a job
- [ ] **PKG-04**: A signed validation job confirms a pip install resolves from the internal mirror (not the public internet)

### Screenshot Capture

- [ ] **SCR-01**: A Playwright script seeds demo data (enrolled node, completed jobs) and captures 8+ dashboard view screenshots without manual intervention
- [ ] **SCR-02**: Screenshots are integrated into the getting-started and feature docs pages
- [ ] **SCR-03**: Screenshots are integrated into the marketing homepage (`homepage/index.html`)

### Docs Accuracy Validation

- [ ] **DOC-01**: A validation script cross-references all API routes in the committed `openapi.json` snapshot against docs and outputs PASS/WARN/FAIL per route
- [ ] **DOC-02**: The script checks CLI flags and env var names in docs against `mop_sdk/cli.py` source and flags any mismatches
- [ ] **DOC-03**: The validation script can be run in CI and exits non-zero on FAIL results

## Future Requirements

### Licence Tooling

- **LIC-06**: GitHub Actions `workflow_dispatch` workflow in `axiom-licences` repo for UI-driven licence issuance
- **LIC-07**: Dedicated licence service with customer database and on-demand issuance API

### Node Validation

- **JOB-08**: Validation job library extended to cover EE-specific features (signed attestation, execution history API)

### Docs

- **DOC-04**: Full docs walkthrough automation (deferred — duplicates cold-start infrastructure from v14.0)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full PyPI mirror (bandersnatch full sync) | 20+ TB storage requirement — operators must use allowlist/scoped mirroring |
| Dashboard keypair generation | Would require private key to transit the server — undermines job signing security model |
| Licence server / online validation | Not needed while customer count is low; deferred to when renewal tracking becomes operational burden |
| New backend API routes | All v15.0 work is tooling/docs layer — no new server-side code |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIC-01 | Phase 82 | Pending |
| LIC-02 | Phase 82 | Pending |
| LIC-03 | Phase 82 | Pending |
| LIC-04 | Phase 82 | Pending |
| LIC-05 | Phase 82 | Pending |
| JOB-01 | Phase 83 | Pending |
| JOB-02 | Phase 83 | Pending |
| JOB-03 | Phase 83 | Pending |
| JOB-04 | Phase 83 | Pending |
| JOB-05 | Phase 83 | Pending |
| JOB-06 | Phase 83 | Pending |
| JOB-07 | Phase 83 | Pending |
| PKG-01 | Phase 84 | Pending |
| PKG-02 | Phase 84 | Pending |
| PKG-03 | Phase 84 | Pending |
| PKG-04 | Phase 84 | Pending |
| SCR-01 | Phase 85 | Pending |
| SCR-02 | Phase 85 | Pending |
| SCR-03 | Phase 85 | Pending |
| DOC-01 | Phase 86 | Pending |
| DOC-02 | Phase 86 | Pending |
| DOC-03 | Phase 86 | Pending |

**Coverage:**
- v15.0 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initial definition*

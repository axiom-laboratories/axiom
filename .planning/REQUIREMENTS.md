# Requirements: Axiom CE/EE Cold-Start Validation

**Defined:** 2026-03-24
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v14.0 Requirements

Requirements for the CE/EE Cold-Start Validation milestone. Each maps to roadmap phases.

### Environment Setup (ENV)

- [x] **ENV-01**: LXC provisioning script creates an Incus container with Docker nesting enabled, AppArmor override applied, Node.js 20 installed (NodeSource PPA), Gemini CLI installed (npm, pinned ≥ v0.23.0), and Playwright + system dependencies installed
- [x] **ENV-02**: Cold-start Compose file (`compose.cold-start.yaml`) runs the full Axiom stack (orchestrator, docs container, 2 puppet nodes) inside the LXC with `SERVER_HOSTNAME` set correctly so Caddy generates a TLS cert with the right SAN for both Playwright and puppet node connections
- [x] **ENV-03**: `Containerfile.node` installs PowerShell via direct `.deb` download from GitHub releases (replaces the silently-failing Debian 12 repository method)
- [x] **ENV-04**: EE licence pre-generation script produces a test Ed25519 EE licence with a 1-year expiry and stores it in `mop_validation/secrets.env` ready for EE scenario injection

### Agent Scaffolding (SCAF)

- [x] **SCAF-01**: Tester `GEMINI.md` (separate from the repo developer `GEMINI.md`) constrains the Gemini agent to first-user behaviour — docs site and dashboard access only, no codebase reads, no prior knowledge assumed
- [x] **SCAF-02**: File-based checkpoint protocol implemented — Gemini writes a version-stamped `checkpoint.json` when blocked, Claude reads via `incus file pull` and writes a steering response file; 5-minute timeout with graceful degradation prevents deadlock
- [x] **SCAF-03**: Session HOME isolation ensures each validation run starts with a fresh `HOME` directory so Gemini cannot auto-load developer context, prior session history, or repo `GEMINI.md`
- [x] **SCAF-04**: Scenario prompt scripts define the structured test procedure for CE install path, CE operator path, EE install path, and EE operator path — each with explicit pass/fail criteria and checkpoint trigger conditions

### CE Validation (CE)

- [x] **CE-01**: Gemini agent follows CE getting-started docs to install Axiom CE from scratch — stack running, nodes enrolled, dashboard accessible
- [x] **CE-02**: Gemini agent dispatches and verifies a Python job via the guided dispatch form; execution confirmed in job history
- [x] **CE-03**: Gemini agent dispatches and verifies a Bash job via the guided dispatch form; execution confirmed in job history
- [x] **CE-04**: Gemini agent dispatches and verifies a PowerShell job via the guided dispatch form; execution confirmed in job history
- [x] **CE-05**: CE `FRICTION.md` produced with verbatim doc quotes for every friction point, full step log, checkpoint steering interventions disclosed, and BLOCKER/NOTABLE/MINOR classification per finding

### EE Validation (EE)

- [x] **EE-01**: Gemini agent follows EE install docs with pre-generated licence injected — EE plugin installed, all EE feature flags active, licence badge visible in dashboard
- [x] **EE-02**: Gemini agent dispatches and verifies Python, Bash, and PowerShell jobs via EE operator path; execution confirmed in job history
- [x] **EE-03**: Gemini agent exercises at least one EE-gated feature beyond job dispatch (e.g. execution history, attestation badge, or environment tag routing)
- [x] **EE-04**: EE `FRICTION.md` produced to the same standard as CE-05, with EE-specific findings noted separately from CE-identical findings

### Reporting (RPT)

- [x] **RPT-01**: Final friction report merges CE and EE `FRICTION.md` files into a single deliverable with cross-edition comparison, BLOCKER/NOTABLE/MINOR triage, actionable recommendations per finding, and a verdict on first-user readiness

## Future Requirements

### Extended Scenarios

- Scheduled job cold-start path (create a job definition, verify it fires on schedule)
- Foundry / Image Recipe cold-start (build a custom node image from docs)
- axiom-push CLI cold-start (install SDK, sign and push a job from terminal)
- Multi-node targeting and environment tag routing validation

### Automation

- Automated re-run on docs or code changes (CI-triggered cold-start)
- Regression comparison between runs (diff FRICTION.md against baseline)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Foundry / Smelter validation | High complexity; separate scenario; not in first-user getting-started path |
| axiom-push CLI validation | CLI install is a separate user journey; deferred to follow-on |
| Automated CI re-run | Infrastructure for automated agent scheduling not yet in place |
| Performance/load testing | Not a cold-start concern; separate milestone if needed |
| Windows or macOS LXC | Linux-only test environment; cross-platform testing is out of scope |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENV-01 | Phase 61 | Complete |
| ENV-02 | Phase 61 | Complete |
| ENV-03 | Phase 61 | Complete |
| ENV-04 | Phase 61 | Complete |
| SCAF-01 | Phase 62 | Complete |
| SCAF-02 | Phase 62 | Complete |
| SCAF-03 | Phase 62 | Complete |
| SCAF-04 | Phase 62 | Complete |
| CE-01 | Phase 63 | Complete |
| CE-02 | Phase 63 | Complete |
| CE-03 | Phase 63 | Complete |
| CE-04 | Phase 63 | Complete |
| CE-05 | Phase 63 | Complete |
| EE-01 | Phase 64 | Complete |
| EE-02 | Phase 64 | Complete |
| EE-03 | Phase 64 | Complete |
| EE-04 | Phase 64 | Complete |
| RPT-01 | Phase 65 | Complete |

**Coverage:**
- v14.0 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial definition*

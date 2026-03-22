# Requirements: Axiom

**Defined:** 2026-03-20
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v11.1 Requirements

Requirements for the Stack Validation milestone — adversarial end-to-end validation of the full Axiom CE/EE stack from a clean install, with critical findings fixed inline.

### Install & Teardown

- [x] **INST-01**: A soft teardown script preserves the Root CA and node `secrets/` dirs — only stops containers and clears DB data
- [x] **INST-02**: A hard teardown script runs `docker compose down -v --remove-orphans` AND clears all LXC node `secrets/` dirs — true clean slate
- [x] **INST-03**: Fresh CE install from cold start produces exactly 13 CE tables, `GET /api/features` all false, and a correctly seeded admin account
- [x] **INST-04**: Admin password re-seed behaviour verified: if admin already exists, `ADMIN_PASSWORD` env var change does NOT overwrite DB password (existing deployment safety)

### EE Test Infrastructure

- [x] **EEDEV-01**: Local Ed25519 test keypair generated (test public + private key) and stored in `mop_validation/secrets/`
- [x] **EEDEV-02**: `axiom-ee` EE plugin patched with test public key bytes and installed as editable source (`pip install -e`) — no Cython rebuild required
- [x] **EEDEV-03**: Valid test licence generated (signed with test private key), `GET /api/licence` returns correct `customer_id`, `exp`, `features`
- [x] **EEDEV-04**: Expired test licence verified: after restart, `GET /api/features` returns all false; `GET /api/licence` shows expired state
- [x] **EEDEV-05**: Missing `AXIOM_LICENCE_KEY` env var verified: EE starts in CE-degraded mode (no crash, all features false)

### LXC Node Provisioning

- [x] **NODE-01**: 4 Incus LXC containers provisioned (`axiom-node-dev`, `axiom-node-test`, `axiom-node-prod`, `axiom-node-staging`), each with correct `OPERATOR_TAGS=env:DEV/TEST/PROD/STAGING`
- [x] **NODE-02**: Each node enrolled using a unique per-node JOIN_TOKEN (not shared) — all 4 successfully complete mTLS enrollment
- [x] **NODE-03**: All 4 nodes heartbeating at `/heartbeat`; `GET /api/nodes` shows 4 nodes with correct `env_tag` and `HEALTHY` status
- [x] **NODE-04**: LXC nodes use Incus bridge IP for `AGENT_URL` (not Docker `172.17.0.1`) — dynamically discovered, not hardcoded
- [x] **NODE-05**: Node revoke → re-enroll cycle verified: revoke a node, confirm it gets 403 on `/work/pull`, re-enroll with fresh token, confirm it resumes heartbeating

### CE Validation Pass

- [x] **CEV-01**: All 7 EE routes return HTTP 402 (not 404) on CE-only install with 4 nodes active
- [x] **CEV-02**: CE table count assertion: exactly 13 tables, zero EE table leakage after hard teardown + CE reinstall
- [x] **CEV-03**: Basic job dispatch on CE: script signed, submitted, executed on a DEV-tagged node, stdout captured in execution history

### EE Validation Pass

- [x] **EEV-01**: CE+EE combined install: `GET /api/features` all true, 28 tables (13 CE + 15 EE), EE routes return real responses
- [x] **EEV-02**: Licence gating is startup-only: change to expired licence at runtime, confirm features remain true until restart, then false after restart
- [x] **EEV-03**: `GET /api/licence` admin endpoint returns full licence detail; non-admin (operator/viewer) gets 403

### Job Test Matrix

- [x] **JOB-01**: Fast job (< 5s): executes, stdout captured, visible in execution history dashboard
- [x] **JOB-02**: Slow job (90s sleep): runs to completion without premature timeout; live in node heartbeat during execution
- [x] **JOB-03**: Memory-heavy job (allocate 512MB in Python): executes successfully in `direct` mode — resource limit not enforced (documented as known gap, not a failure)
- [x] **JOB-04**: Concurrent jobs (5 simultaneous submitted to same node): all 5 complete, no duplicate execution of same job GUID on two nodes
- [x] **JOB-05**: Env-tag routing: DEV-tagged job only executes on `axiom-node-dev`; PROD-tagged job only on `axiom-node-prod`; cross-tag submission returns no eligible node
- [x] **JOB-06**: Env promotion chain: same job script submitted to DEV → TEST → PROD in sequence, each execution captured separately in history
- [x] **JOB-07**: Failure mode — script crash (`sys.exit(1)`): `FAILED` status captured, retry triggered per configured `max_retries`, all attempts in history with correct `attempt_number`
- [x] **JOB-08**: Failure mode — bad Ed25519 signature: node rejects script before execution; execution record shows rejection, not crash
- [x] **JOB-09**: Failure mode — job submitted with revoked job definition status: dispatch blocked at orchestrator, node never receives it

### Foundry + Smelter

- [ ] **FOUNDRY-01**: Full wizard flow: create runtime blueprint → create network blueprint → build image via Foundry → verify image tag in Docker → deploy a node from the Foundry-built image
- [ ] **FOUNDRY-02**: Smelter STRICT mode: attempt to add an ingredient with a known CVE (`cryptography<40.0.0`); confirm STRICT mode blocks the blueprint from being used in a build
- [ ] **FOUNDRY-03**: Build failure edge case: trigger a build failure (bad base image tag); confirm API returns HTTP 500 with error detail, not silent 200
- [x] **FOUNDRY-04**: Build dir cleanup: after a completed build, confirm temp build directory is removed (MIN-7 gap test — expect failure, document finding)
- [ ] **FOUNDRY-05**: Air-gap mirror: configure a blueprint to use the local PyPI mirror, block outbound internet via `iptables`, confirm pip install of ingredient succeeds from mirror
- [x] **FOUNDRY-06**: Smelter warning mode: add a moderate-risk ingredient in WARNING mode; confirm build proceeds but audit log records the warning

### Gap Report

- [ ] **GAP-01**: Living gap report maintained throughout validation (`mop_validation/reports/v11.1-gap-report.md`) — every finding logged with severity (critical/major/minor), area, reproduction steps, and v12.0+ fix candidate
- [ ] **GAP-02**: All critical findings (duplicate execution race, silent build success on failure, admin re-seed) patched inline during the milestone with accompanying regression test
- [ ] **GAP-03**: Final gap report summarised with prioritised backlog for v12.0+ milestone planning

## Future Requirements

### v12.0+

- Resource limit enforcement in `direct` mode — currently limits are silently ignored when EXECUTION_MODE=direct
- Licence re-validation on a schedule (not just at startup)
- Node death mid-job rescheduling — currently job remains in-flight if node dies
- WAL mode for SQLite in dev stack — prevents database locked errors under concurrent polling
- Docker Hub CE image publish (deferred from v11.0)
- EE-08: PyPI stub wheel publication (deferred from v11.0)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full Cython rebuild for EE test | Editable install with patched .py source covers all validation needs; .so production fidelity is v12.0+ |
| Automated CI pipeline for validation suite | Manual adversarial pass is the goal; automation is a future milestone |
| Load testing (hundreds of jobs) | Scale testing beyond 5 concurrent jobs is out of scope for this milestone |
| Multi-orchestrator HA testing | Single orchestrator is the current architecture; HA is not planned |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | Phase 38 | Complete |
| INST-02 | Phase 38 | Complete |
| INST-03 | Phase 38 | Complete |
| INST-04 | Phase 38 | Complete |
| EEDEV-01 | Phase 39 | Complete |
| EEDEV-02 | Phase 39 | Complete |
| EEDEV-03 | Phase 39 | Complete |
| EEDEV-04 | Phase 39 | Complete |
| EEDEV-05 | Phase 39 | Complete |
| NODE-01 | Phase 40 | Complete |
| NODE-02 | Phase 40 | Complete |
| NODE-03 | Phase 40 | Complete |
| NODE-04 | Phase 40 | Complete |
| NODE-05 | Phase 40 | Complete |
| CEV-01 | Phase 41 | Complete |
| CEV-02 | Phase 41 | Complete |
| CEV-03 | Phase 41 | Complete |
| EEV-01 | Phase 42 | Complete |
| EEV-02 | Phase 42 | Complete |
| EEV-03 | Phase 42 | Complete |
| JOB-01 | Phase 43 | Complete |
| JOB-02 | Phase 43 | Complete |
| JOB-03 | Phase 43 | Complete |
| JOB-04 | Phase 43 | Complete |
| JOB-05 | Phase 43 | Complete |
| JOB-06 | Phase 43 | Complete |
| JOB-07 | Phase 43 | Complete |
| JOB-08 | Phase 43 | Complete |
| JOB-09 | Phase 43 | Complete |
| FOUNDRY-01 | Phase 44 | Pending |
| FOUNDRY-02 | Phase 44 | Pending |
| FOUNDRY-03 | Phase 44 | Pending |
| FOUNDRY-04 | Phase 44 | Complete |
| FOUNDRY-05 | Phase 44 | Pending |
| FOUNDRY-06 | Phase 44 | Complete |
| GAP-01 | Phase 45 | Pending |
| GAP-02 | Phase 45 | Pending |
| GAP-03 | Phase 45 | Pending |

**Coverage:**
- v11.1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 — initial definition*

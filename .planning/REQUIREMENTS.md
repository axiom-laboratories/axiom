# Requirements: v25.0 — EE Validation & Infrastructure

**Defined:** 2026-04-20
**Core Value:** Confirm that the CE/EE boundary, licence enforcement, and EE wheel security chain all hold under adversarial conditions; consolidate Axiom tooling repos under one org; make a concrete architecture decision on licence storage.

## v1 Requirements

### EE Behavioural Validation (VAL)

- [ ] **VAL-01**: CE-only install creates exactly 15 tables; no EE schema present
- [ ] **VAL-02**: CE-only install: `GET /api/features` returns all feature flags false
- [ ] **VAL-03**: CE-only install: all 7 EE stub routes return HTTP 402
- [ ] **VAL-04**: EE install with valid licence: all 41 tables present (15 CE + 26 EE)
- [ ] **VAL-05**: EE install with valid licence: all EE feature flags return true; `GET /api/licence` returns `status=VALID`
- [ ] **VAL-06**: EE install with grace-period licence (expired but within grace days): features remain active; `status=GRACE`; admin grace banner visible in dashboard
- [ ] **VAL-07**: EE install with post-grace expired licence: DEGRADED_CE mode; `pull_work` returns empty (not 402); running jobs unaffected; no startup crash
- [ ] **VAL-08**: EE install with `AXIOM_LICENCE_KEY` absent: CE mode at startup; all EE stubs return 402; no crash
- [ ] **VAL-09**: EE install with invalid/tampered licence signature: CE mode at startup; no crash; clear log entry
- [ ] **VAL-10**: EE install with tampered wheel manifest (bad SHA256): `_verify_wheel_manifest()` raises `RuntimeError`; EE does not load; CE runs standalone
- [ ] **VAL-11**: EE install with non-whitelisted entry point value: loader raises `RuntimeError`; EE does not load
- [ ] **VAL-12**: Node limit enforcement: enrollment returns HTTP 402 when active node count ≥ `node_limit`; existing enrolled nodes continue operating
- [ ] **VAL-13**: Boot log HMAC chain: clock-rollback scenario raises `RuntimeError` on EE; CE emits warning only; no data loss
- [ ] **VAL-14**: All VAL-01 through VAL-13 scenarios covered by automated tests in `mop_validation`; zero scenarios require manual execution to verify

### Repo Migration (MIG)

- [ ] **MIG-01**: `mop_validation` repository transferred to the `axiom` GitHub organisation as a private repo
- [ ] **MIG-02**: All existing scripts continue to execute correctly post-migration (no hardcoded org paths broken)
- [ ] **MIG-03**: Local git clone remote URL updated to new org location
- [ ] **MIG-04**: `CLAUDE.md` and `GEMINI.md` in `master_of_puppets` updated to reflect new org/URL for `mop_validation`

### Licence Architecture Analysis (LIC)

- [ ] **LIC-01**: Structured comparison of three options — (A) current: separate private Git repo, (B) database embedded in axiom-ee or new service, (C) hybrid: DB as source of truth with Git snapshots — across dimensions: security, auditability, air-gap compatibility, operational complexity, CI/CD integration, recovery from data loss
- [ ] **LIC-02**: Concrete recommendation with rationale (not just comparison table); includes a "why this over the others" section
- [ ] **LIC-03**: If recommended option differs from current Git repo approach, a migration path is documented (what changes, what stays the same, effort estimate)

## v2 Requirements

### Extended Validation

- **VAL-EXT-01**: Fuzz HMAC boot log entries (truncated, corrupted, reordered) — confirm safe rejection
- **VAL-EXT-02**: Validate EE grace-period countdown in dashboard matches `expires_at` claim in JWT
- **VAL-EXT-03**: Concurrent enrollment stress test against node limit (race condition check)

### Licence Architecture Implementation

- **LIC-IMPL-01**: Implement the recommended licence storage architecture if it differs from current
- **LIC-IMPL-02**: Licence issuance portal (web UI or automated pipeline) — DIST-04 deferred item

## Out of Scope

| Feature | Reason |
|---------|--------|
| New EE feature development | This milestone is validation-only; new features are v26.0+ |
| Changing licence validation logic | Validate existing behaviour; implementation changes only if recommendation demands it |
| OIDC/SAML SSO | Design complete in v13.0; implementation deferred to v26.0+ |
| Workflow execution analytics | v26.0+ backlog item |
| axiom-ee Cython rebuild | Validation uses editable install with patched public key (v11.1 pattern) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VAL-01 | Phase 173 | Pending |
| VAL-02 | Phase 173 | Pending |
| VAL-03 | Phase 173 | Pending |
| VAL-04 | Phase 173 | Pending |
| VAL-05 | Phase 173 | Pending |
| VAL-06 | Phase 173 | Pending |
| VAL-07 | Phase 173 | Pending |
| VAL-08 | Phase 173 | Pending |
| VAL-09 | Phase 173 | Pending |
| VAL-10 | Phase 173 | Pending |
| VAL-11 | Phase 173 | Pending |
| VAL-12 | Phase 173 | Pending |
| VAL-13 | Phase 173 | Pending |
| VAL-14 | Phase 173 | Pending |
| MIG-01 | Phase 174 | Pending |
| MIG-02 | Phase 174 | Pending |
| MIG-03 | Phase 174 | Pending |
| MIG-04 | Phase 174 | Pending |
| LIC-01 | Phase 175 | Pending |
| LIC-02 | Phase 175 | Pending |
| LIC-03 | Phase 175 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after initial v25.0 definition*

# Requirements: Axiom v14.3 Security Hardening + EE Licensing

**Defined:** 2026-03-26
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v14.3 Requirements

### Security Fixes

- [x] **SEC-01**: Operator can be confident that the device-approve OAuth page (`/auth/device/approve`) does not reflect unsanitised user input — `user_code` query parameter is HTML-escaped before rendering
- [x] **SEC-02**: Operator can be confident that `vault_service.py` artifact paths are safe against directory traversal — UUID validation + `Path.resolve() + is_relative_to()` guard applied to store and delete operations
- [x] **SEC-03**: Operator can be confident that `main.py` installer script paths are safe against directory traversal — same `resolve() + is_relative_to()` pattern applied to all flagged locations (verified via live CodeQL scan)
- [x] **SEC-04**: Operator can be confident that job output scanning (`mask_pii()`) cannot be exploited for ReDoS — email regex rewritten to linear bounded pattern, not just length-guarded
- [x] **SEC-05**: Operator can start Axiom without an `API_KEY` environment variable — import-time crash removed, `verify_api_key` dependency removed from all three node-facing routes, `API_KEY` references removed from documentation and templates
- [x] **SEC-06**: Operator can be confident that the CSV job export endpoint cannot be used for XSS via content-sniffing — `X-Content-Type-Options: nosniff` header present in the backend streaming response

### EE Licensing

- [x] **LIC-01**: Axiom Labs operator can generate an Ed25519-signed licence key offline using `tools/generate_licence.py`, specifying customer ID, tier, node limit, feature list, expiry date, and grace days
- [x] **LIC-02**: Axiom EE verifies the Ed25519 cryptographic signature of the licence key at startup, rejecting any key whose signature does not match the embedded public key
- [x] **LIC-03**: Axiom EE transitions to a GRACE state when a valid licence expires, logging a warning and continuing EE operation for up to `grace_days` (default 30) rather than crashing or hard-stopping
- [x] **LIC-04**: Axiom EE transitions to DEGRADED_CE state (CE stub routes return 402) after the grace period ends, without crashing or raising unhandled exceptions in EE route handlers
- [x] **LIC-05**: Axiom EE detects clock rollback between container restarts via a hash-chained boot log in `secrets/boot.log` and logs a warning (strict mode: reject startup)
- [x] **LIC-06**: Operator can query `GET /api/licence` and receive `status` (valid/grace/expired), `days_until_expiry`, `node_limit`, and `tier` fields in the response
- [x] **LIC-07**: Axiom CE/EE rejects new node enrollment at `POST /api/enroll` with HTTP 402 when the signed `node_limit` in the licence has been reached

## Future Requirements

### Deferred

- Licence issuance portal (web UI for generating keys) — not justified at current customer volume
- Per-licence grace period operator documentation updates — follows LIC-03 landing
- Dashboard amber/red banner on GRACE/DEGRADED_CE state — backend status stable after v14.3; frontend component can follow in v14.x
- Periodic in-process licence re-validation (APScheduler 6h re-check) — deferred to v15+
- Hardware fingerprinting / node locking — deferred to v15+
- Per-feature tier gating (currently all-or-nothing EE) — deferred to v15+

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dashboard licence banner | Backend status API lands in v14.3; UI component deferred to avoid scope creep |
| Licence issuance web portal | No web service needed at current scale; offline CLI is sufficient |
| Online licence validation (call-home) | Air-gapped deployments are a core use case — online checks would block them |
| Job signing keypair reuse for licences | Critical security boundary: a leaked job-signing key must not forge licences |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 72 | Complete |
| SEC-02 | Phase 75 | Complete |
| SEC-03 | Phase 72 | Complete |
| SEC-04 | Phase 72 | Complete |
| SEC-05 | Phase 72 | Complete |
| SEC-06 | Phase 72 | Complete |
| LIC-01 | Phase 73 | Complete |
| LIC-02 | Phase 73 | Complete |
| LIC-03 | Phase 73 | Complete |
| LIC-04 | Phase 73 | Complete |
| LIC-05 | Phase 75 | Complete |
| LIC-06 | Phase 74 | Complete |
| LIC-07 | Phase 73 | Complete |

**Coverage:**
- v14.3 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓
- Pending (gap closure): SEC-02 (Phase 75), LIC-05 (Phase 75), LIC-06 (Phase 74)

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 — traceability filled after roadmap creation*

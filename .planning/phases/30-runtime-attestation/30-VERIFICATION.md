---
phase: 30-runtime-attestation
verified: 2026-03-18T17:30:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
human_verification:
  - test: "Submit a signed job to a live node, retrieve the execution record, and call GET /api/executions/{id}/attestation"
    expected: "Response contains bundle_b64, signature_b64, cert_serial, node_id, and attestation_verified='verified'"
    why_human: "End-to-end flow requires a running node with mTLS cert; cannot be verified programmatically without live stack"
---

# Phase 30: Runtime Attestation Verification Report

**Phase Goal:** Every job execution produces a cryptographically signed attestation bundle that the orchestrator verifies using the node's mTLS certificate — giving operators tamper-evident proof of what ran, where, and what it produced.

**Verified:** 2026-03-18T17:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | ExecutionRecord has attestation_bundle, attestation_signature, attestation_verified nullable columns | VERIFIED | `db.py` lines 234–236: all three `Mapped[Optional[str]]` columns confirmed |
| 2  | ResultReport has attestation_bundle and attestation_signature Optional[str] fields | VERIFIED | `models.py` lines 66–67: both fields present with correct types |
| 3  | AttestationExportResponse Pydantic model exists in models.py | VERIFIED | `models.py` line 615: full model with bundle_b64, signature_b64, cert_serial, node_id, attestation_verified |
| 4  | migration_v33.sql adds three columns with IF NOT EXISTS guards | VERIFIED | File exists, all three `ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS` statements present |
| 5  | node.py has _build_and_sign_attestation() returning (bundle_b64, sig_b64) or (None, None) | VERIFIED | `node.py` lines 147–194: module-level function with full try/except returning (None, None) on any error |
| 6  | stdout_hash and stderr_hash computed from raw bytes BEFORE build_output_log() | VERIFIED | `node.py` lines 649–653: hashes computed immediately after `runtime_engine.run()`, before `output_log = build_output_log(...)` at line 653 |
| 7  | report_result() POST body includes attestation_bundle and attestation_signature | VERIFIED | `node.py` lines 709–710: both fields included in httpx POST body |
| 8  | attestation_service.py exists with verify_bundle() returning "verified"/"failed"/"missing" | VERIFIED | Full file present; three string constants ATTESTATION_VERIFIED/FAILED/MISSING defined at lines 30–32 |
| 9  | RSA verify uses 4-arg call — NOT the 2-arg Ed25519 pattern | VERIFIED | `attestation_service.py` line 95: `public_key.verify(sig_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())` |
| 10 | Revoked cert returns "failed" without raising HTTPException | VERIFIED | `attestation_service.py` lines 80–87: RevokedCert table lookup; returns ATTESTATION_FAILED string on match |
| 11 | job_service.report_result() calls verify_bundle() and stores result in ExecutionRecord.attestation_verified | VERIFIED | `job_service.py` lines 761–773: all three attestation fields set on record; verify_bundle called before db.add() |
| 12 | GET /api/executions/{id}/attestation returns bundle_b64/signature_b64; 404 on missing attestation | VERIFIED | `main.py` lines 530–564: endpoint with history:read guard, 404 on missing record or null bundle |
| 13 | All 10 test_attestation.py tests pass | VERIFIED | pytest run confirmed: 10 PASSED, 0 SKIPPED, 0 FAILED |
| 14 | RSA round-trip test passes | VERIFIED | test_attestation_rsa_roundtrip PASSED |
| 15 | Mutation (tamper) test passes | VERIFIED | test_attestation_mutation_fails PASSED |
| 16 | Revoked cert mock test passes | VERIFIED | test_revoked_cert_stores_failed PASSED |
| 17 | Export endpoint model shape test passes | VERIFIED | test_attestation_export_endpoint PASSED |

**Score:** 17/17 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/tests/test_attestation.py` | 10 passing tests covering RSA crypto, schema, revocation, and export | VERIFIED | 10 PASSED, 0 SKIPPED; all stubs from Plans 01/02 un-skipped in Plan 03 |
| `puppeteer/agent_service/db.py` | ExecutionRecord with 3 attestation columns | VERIFIED | Lines 234–236: attestation_bundle (Text), attestation_signature (Text), attestation_verified (String(16)) |
| `puppeteer/agent_service/models.py` | ResultReport with attestation fields; AttestationExportResponse model | VERIFIED | Lines 66–67 and 615–620 |
| `puppeteer/migration_v33.sql` | 3x IF NOT EXISTS ALTER TABLE for PostgreSQL | VERIFIED | All three columns with correct types; comment explains SQLite behavior |
| `puppets/environment_service/node.py` | _build_and_sign_attestation() + wiring in execute_task()/report_result() | VERIFIED | Lines 147–194 (function), 649–666 (execute_task wiring), 677–721 (report_result) |
| `puppeteer/agent_service/services/attestation_service.py` | verify_bundle() with RSA 4-arg verify, revocation check, never raises | VERIFIED | Full 105-line file; all specified behaviors present |
| `puppeteer/agent_service/services/job_service.py` | attestation wiring in report_result() | VERIFIED | Lines 761–773: import, verify call, and column assignment all present |
| `puppeteer/agent_service/main.py` | GET /api/executions/{id}/attestation endpoint | VERIFIED | Lines 530–564: route present, requires history:read, 404 on missing attestation |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `node.py execute_task()` | `_build_and_sign_attestation()` | stdout_hash/stderr_hash computed from raw result bytes immediately after runtime_engine.run() | WIRED | Lines 649–651 hash raw bytes; line 685 calls _build_and_sign_attestation; confirmed BEFORE build_output_log at line 653 |
| `node.py report_result()` | `/work/{guid}/result` POST body | attestation_bundle and attestation_signature included in httpx POST | WIRED | Lines 709–710 in POST body dict |
| `job_service.report_result()` | `attestation_service.verify_bundle()` | called after ExecutionRecord construction, result stored in record.attestation_verified before db.add() | WIRED | Lines 766–773: verify call, result assignment, then db.add(record) |
| `main.py GET /api/executions/{id}/attestation` | `ExecutionRecord.attestation_bundle` | returns bundle_b64 directly from DB record | WIRED | Lines 541–563: DB query, null check, AttestationExportResponse construction |
| `attestation_service.verify_bundle()` | `Node.client_cert_pem` | SELECT Node WHERE node_id, extract public key, call RSA 4-arg verify | WIRED | Lines 66–95: node query, cert load, revocation check, public_key.verify |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| OUTPUT-05 | 30-01, 30-02 | Node produces runtime attestation bundle signed with mTLS private key | SATISFIED | `_build_and_sign_attestation()` in node.py builds bundle with script_hash, stdout_hash, stderr_hash, exit_code, start_timestamp, cert_serial; signs with RSA PKCS1v15/SHA256; POST body includes both b64 fields |
| OUTPUT-06 | 30-01, 30-03 | Orchestrator verifies attestation signature against stored node cert; stores verified/failed/missing | SATISFIED | `attestation_service.verify_bundle()` performs RSA 4-arg verify against Node.client_cert_pem; result stored in ExecutionRecord.attestation_verified by job_service.report_result() |
| OUTPUT-07 | 30-01, 30-03 | Attestation bundles stored and exportable via API for independent offline verification | SATISFIED | ExecutionRecord.attestation_bundle stores bundle_b64; GET /api/executions/{id}/attestation returns AttestationExportResponse with bundle_b64, signature_b64, cert_serial, node_id, attestation_verified |

All three requirements fully satisfied. No orphaned requirements found — all three OUTPUT-05/06/07 IDs appear in plan frontmatter and have corresponding implementation evidence.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppeteer/tests/test_attestation.py` | 71–80 | `_make_bundle()` helper uses different field names (`job_guid`, `node_id`, `timestamp`) than the production bundle (`start_timestamp`, `stderr_hash`, `stdout_hash`) — no `stdout_hash`/`stderr_hash` in test fixture | Info | Tests verify RSA crypto mechanics correctly but do not test the exact production bundle schema. An independent verifier using the test bundle format would not be able to reproduce a real execution's bundle bytes. Does not block the goal but is a documentation gap. |
| `puppeteer/tests/test_attestation.py` | 392–407 | `test_attestation_export_missing` tests a trivial `not None` condition rather than the HTTP response layer | Info | Minimal contract test — confirms the 404 trigger condition exists but does not exercise the HTTP handler. Acceptable given the pragmatic test strategy documented in Plan 03. |

No blocker or warning-severity anti-patterns found. Both items are informational.

---

### Human Verification Required

#### 1. End-to-End Attestation Flow

**Test:** Deploy a node with an mTLS cert, submit a signed Python job, wait for completion, then call `GET /api/executions/{id}/attestation`.

**Expected:** Response body contains `bundle_b64` (non-empty base64 string), `signature_b64` (non-empty), `cert_serial` (integer string matching the node's certificate), `node_id` (the node's ID), and `attestation_verified = "verified"`.

**Why human:** Requires a live stack with a running node that has a real mTLS private key and cert file at `secrets/{NODE_ID}.key` and `secrets/{NODE_ID}.crt`. The signing path is only exercised when `script_hash` is non-null (i.e., a properly signed job script), so the test job must be submitted through the normal signing flow.

#### 2. Revoked Node Attestation Behaviour

**Test:** Submit a job from a node, then revoke the node via the dashboard or API, then re-enroll the node and run another job. Check the new execution record's `attestation_verified` field.

**Expected:** The execution record for the re-enrolled node should show `attestation_verified = "missing"` until the new cert is stored, or `"verified"` if enrollment stores the new cert PEM correctly.

**Why human:** Cert lifecycle interactions (revoke → re-enroll → new cert PEM stored → subsequent attestation) depend on DB state transitions that require a live stack.

---

### Gaps Summary

No gaps found. All 17 truths are verified, all artifacts are substantive and wired, all three requirement IDs are satisfied, and the test suite passes 10/10.

The informational note about the `_make_bundle()` test helper field divergence is worth tracking for Phase 32 when the dashboard renders attestation data — an operator trying to manually reproduce a real bundle from the test scaffold pattern would find a field mismatch. This does not affect the runtime behaviour since the production path in `node.py` uses the correct field set.

---

*Verified: 2026-03-18T17:30:00Z*
*Verifier: Claude (gsd-verifier)*

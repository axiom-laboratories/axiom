---
phase: 30-runtime-attestation
plan: "02"
subsystem: puppets/environment_service
tags:
  - attestation
  - node
  - rsa
  - signing
  - cryptography
dependency_graph:
  requires:
    - 30-01  # attestation_bundle/attestation_signature columns on ExecutionRecord, ResultReport fields
  provides:
    - _build_and_sign_attestation() in node.py — node-side bundle construction and RSA signing
    - attestation_bundle + attestation_signature in report_result() POST body
    - hash-order invariant: stdout/stderr hashes computed from raw bytes before build_output_log()
  affects:
    - puppets/environment_service/node.py — execute_task(), report_result()
    - puppeteer/tests/test_attestation.py — +2 tests (7 PASSED, 3 SKIPPED)
    - plan 30-03 — node side complete; orchestrator verification is the next layer
tech_stack:
  added: []
  patterns:
    - RSA-2048 sign with padding.PKCS1v15() + hashes.SHA256() (3-arg form — NOT Ed25519 2-arg)
    - Deterministic JSON: json.dumps(sort_keys=True, separators=(',',':')) for reproducible bundle bytes
    - Hash-order invariant: raw bytes hashed BEFORE build_output_log() scrubbing
    - Graceful degradation: (None, None) returned on any error — never raises
key_files:
  modified:
    - puppets/environment_service/node.py
    - puppeteer/tests/test_attestation.py
decisions:
  - "_build_and_sign_attestation() is a module-level function (not a method) — no self dependency, pure function for testability"
  - "stdout_hash and stderr_hash computed from raw result bytes immediately after runtime_engine.run() — before any processing (hash order invariant)"
  - "started_at comes from str(job.get('started_at','')) — string passthrough from WorkResponse, not datetime.now()"
  - "Graceful fallback: if cert_file or key_file missing, (None, None) returned — orchestrator stores 'missing', no crash"
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_modified: 2
  completed_date: "2026-03-18"
requirements_satisfied:
  - OUTPUT-05
---

# Phase 30 Plan 02: Node-Side Attestation Bundle Signing Summary

**One-liner:** RSA-2048 attestation bundle signing in node.py — script/stdout/stderr hashes + cert serial signed with mTLS private key, with hash-order invariant enforcement.

## What Was Built

### _build_and_sign_attestation() — module-level function in node.py

A pure function that constructs and signs an attestation bundle using the node's mTLS RSA-2048 private key. The bundle contains six fields deterministically serialised with `json.dumps(sort_keys=True, separators=(',',':'))`:

```
cert_serial, exit_code, script_hash, start_timestamp, stderr_hash, stdout_hash
```

Returns `(bundle_b64, signature_b64)` on success or `(None, None)` on any error (file not found, signing error) — never raises.

### Hash-Order Invariant Wiring in execute_task()

Immediately after `runtime_engine.run()` returns, before any scrubbing or processing:

```python
stdout_hash = hashlib.sha256((result.get("stdout") or "").encode('utf-8')).hexdigest()
stderr_hash = hashlib.sha256((result.get("stderr") or "").encode('utf-8')).hexdigest()
started_at_iso = str(job.get("started_at", ""))
```

These are computed before `build_output_log()` to preserve the invariant: orchestrator scrubs secrets, but the node-reported hashes cover pre-scrub bytes. Independent verifiers cannot reproduce these hashes from the orchestrator's scrubbed storage — they trust the signed bundle directly.

### report_result() Extended Signature

```python
async def report_result(self, guid, success, result,
                        output_log=None, exit_code=None, security_rejected=False,
                        script_hash=None, stdout_hash=None, stderr_hash=None,
                        started_at=None):
```

Attestation is computed before the HTTP POST. POST body now includes `attestation_bundle` and `attestation_signature` (both `None` when inputs are unavailable — error paths continue to work unchanged).

### New Tests (test_attestation.py)

- `test_bundle_hash_order_invariant` — confirms that a signature over raw stdout hash rejects the scrubbed hash bytes as `InvalidSignature`. Documents the correctness invariant.
- `test_cert_serial_extracted_correctly` — pure structural test confirming `bundle["cert_serial"] == str(cert.serial_number)` after JSON round-trip.

Result: **7 PASSED, 3 SKIPPED** (revoked_cert, export_endpoint, export_missing deferred to Plan 30-03).

## Deviations from Plan

None — plan executed exactly as written. All truths from `must_haves` satisfied:
- `_build_and_sign_attestation()` exists as a module-level function before `UpgradeManager`
- Bundle hashes over raw bytes BEFORE `build_output_log()` call
- `started_at` from `str(job.get("started_at", ""))` — not `datetime.now()`
- `(None, None)` graceful fallback on any error
- `report_result()` POST body includes `attestation_bundle` and `attestation_signature`

## Self-Check

### Files Created/Modified

- `puppets/environment_service/node.py` — modified (exists, verified by grep)
- `puppeteer/tests/test_attestation.py` — modified (exists, verified by test run)

### Commits

- `72e3541` — feat(30-02): add _build_and_sign_attestation() and wire into execute_task()/report_result()
- `e41deff` — test(30-02): add hash-order invariant and cert-serial structural tests

## Self-Check: PASSED

All files exist. Both commits present in git log. 7 tests PASSED, 3 SKIPPED as specified by plan.

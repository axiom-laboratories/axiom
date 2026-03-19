---
phase: 30-runtime-attestation
plan: 01
subsystem: testing
tags: [rsa, attestation, cryptography, pytest, sqlite, postgresql, pydantic, sqlalchemy]

# Dependency graph
requires:
  - phase: 29-backend-completeness
    provides: ExecutionRecord with job_run_id, script_hash — base schema this plan extends
provides:
  - RSA PKCS1v15+SHA256 sign/verify round-trip test passing with fixture cert
  - Mutation tamper detection test passing
  - Canonical JSON bundle serialisation test passing (sort_keys=True proven)
  - test_execution_record_has_attestation_columns passing via inspect.getsource
  - ExecutionRecord extended with attestation_bundle, attestation_signature, attestation_verified columns
  - ResultReport extended with attestation_bundle and attestation_signature Optional[str] fields
  - AttestationExportResponse Pydantic model in models.py
  - migration_v33.sql with IF NOT EXISTS ALTER TABLE for PostgreSQL deployments
  - 3 stub tests (skipped) for Plan 30-02/30-03 to implement
affects: [30-02-node-signing, 30-03-orchestrator-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RSA sign/verify: 3-arg sign (private_key.sign(bytes, PKCS1v15(), SHA256())), 4-arg verify (public_key.verify(sig, bytes, PKCS1v15(), SHA256())) — distinct from Ed25519 2-arg pattern"
    - "Canonical attestation bundle: json.dumps(dict, sort_keys=True, separators=(',',':')) — deterministic across key insertion orders"
    - "Schema inspection test pattern: inspect.getsource(Model) asserts column names present without requiring DB connection"
    - "Stub test pattern: pytest.mark.skip with explicit plan reference (plan 30-02/30-03)"
    - "Attestation verification states: 'verified', 'failed', 'missing', None (pre-attestation)"

key-files:
  created:
    - puppeteer/tests/test_attestation.py
    - puppeteer/migration_v33.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py

key-decisions:
  - "RSA sign/verify API uses 3-arg sign and 4-arg verify — never copy Ed25519 2-arg pattern from signature_service.py"
  - "Canonical bundle serialisation: sort_keys=True, separators=(',',':') — proven via determinism test"
  - "attestation_verified states: 'verified', 'failed', 'missing', None — String(16) sufficient"
  - "migration_v33.sql uses IF NOT EXISTS guards for PostgreSQL safety; SQLite handled by create_all at startup (pre-existing pattern)"
  - "test_execution_record_has_attestation_columns uses inspect.getsource() — no DB connection needed, fast structural invariant check"

patterns-established:
  - "Attestation bundle dict fields: cert_serial, exit_code, job_guid, node_id, script_hash, timestamp — established canonical contract for Plans 02/03"
  - "Test scaffold pattern: 4 passing crypto tests + 1 passing schema test + 3 skipped stubs — suite green from day 1 of Wave 1"

requirements-completed: [OUTPUT-05, OUTPUT-06, OUTPUT-07]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 30 Plan 01: Runtime Attestation — Test Scaffold and Schema Foundation Summary

**RSA-2048 attestation test scaffold with canonical bundle contract, DB schema extension (3 nullable columns on ExecutionRecord), ResultReport fields, AttestationExportResponse model, and migration_v33.sql — 5 passing / 3 skipped, suite green**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T16:50:07Z
- **Completed:** 2026-03-18T16:52:30Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Created test_attestation.py with 4 immediately-passing crypto tests (round-trip, mutation, deterministic, cert_serial) using an RSA-2048 fixture cert
- Added 3 nullable attestation columns to ExecutionRecord in db.py and confirmed via inspect.getsource() schema test
- Extended ResultReport with attestation_bundle and attestation_signature optional fields; added AttestationExportResponse model
- Created migration_v33.sql with IF NOT EXISTS guards for existing PostgreSQL deployments

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_attestation.py with RSA round-trip tests and stubs** - `b03607a` (test)
2. **Task 2: Add attestation columns, models, migration** - `cba64ff` (feat)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `puppeteer/tests/test_attestation.py` — 8-test attestation scaffold: 5 passing (4 crypto + 1 schema), 3 skipped stubs for Plans 30-02/30-03
- `puppeteer/agent_service/db.py` — ExecutionRecord extended with attestation_bundle (Text), attestation_signature (Text), attestation_verified (String(16))
- `puppeteer/agent_service/models.py` — ResultReport gets attestation_bundle and attestation_signature Optional[str]; AttestationExportResponse added
- `puppeteer/migration_v33.sql` — 3x IF NOT EXISTS ALTER TABLE for PostgreSQL existing deployments

## Decisions Made

- RSA sign/verify API: 3-arg sign, 4-arg verify — documented explicitly to prevent copying Ed25519 2-arg pattern from signature_service.py
- Canonical bundle uses sort_keys=True with no whitespace — determinism test proves this is required
- attestation_verified String(16) stores: "verified", "failed", "missing", or None (None for pre-attestation records)
- test_execution_record_has_attestation_columns uses inspect.getsource() — avoids DB connection, tests structural invariant directly

## Deviations from Plan

None — plan executed exactly as written.

The plan specified Task 1 should have the schema inspection test as a skip stub and un-skip it in Task 2. This was followed precisely.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. migration_v33.sql is ready for PostgreSQL deployments at next maintenance window.

## Next Phase Readiness

- Plan 30-02 (node-side signing): can now implement `_sign_attestation_bundle()` in node.py using the exact RSA API pattern proven in test_attestation_rsa_roundtrip
- Plan 30-03 (orchestrator verification): can now implement report_result() attestation verification against the 3 new ExecutionRecord columns; AttestationExportResponse model is ready
- All stub tests (test_revoked_cert_stores_failed, test_attestation_export_endpoint, test_attestation_export_missing) are in place waiting for Plan 30-03 implementation

---
*Phase: 30-runtime-attestation*
*Completed: 2026-03-18*

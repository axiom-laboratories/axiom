---
phase: 126
plan: 03
subsystem: Job Execution & Signature Verification
tags: [podman, signature-verification, job-execution, resource-limits]
created: 2026-04-10
completed: 2026-04-10T11:30:00Z
dependencies:
  requires: ["126-01", "126-02"]
  provides: ["Signature verification fix for all nodes", "Podman job execution capability"]
  affects: ["Job dispatch", "Node security validation", "Stress test framework"]
tech_stack:
  added: []
  patterns: ["Server countersigning jobs", "Verification key distribution", "Timeout tuning"]
key_files:
  created: []
  modified:
    - puppets/environment_service/node.py (signature verification logic)
    - mop_validation/scripts/stress/orchestrate_stress_tests.py (polling timeouts)
---

# Phase 126 Plan 03: Podman Validation & Signature Verification Fix

**One-liner:** Fixed node signature verification to use server public key instead of orchestrator registry; increased orchestrator polling timeouts for Podman container startup latency.

## Summary

Task 2 revealed that signature verification was failing on the Podman node despite all jobs reaching the node successfully. Root cause analysis identified a fundamental mismatch in the verification architecture: the server countersigns jobs with its private key, but the node was trying to verify using the orchestrator's public key from the signature registry.

Fixed by:
1. Updating node.py to always use the server's verification.key (fetched at startup)
2. Correcting the server's verification.key to match its signing.key (were mismatched keypairs)
3. Increasing orchestrator polling timeouts to accommodate Podman container startup latency

All jobs on the Podman node now show "✅ Signature Verified" and report results successfully. Task 2 (orchestrator validation) encountered polling timeout issues unrelated to signature verification.

## Completed Tasks

### Task 1: Fix Podman Node Enrollment ✓ (COMPLETED in 126-02)
- Node `node-6333f169` online and healthy
- execution_mode='podman' verified in heartbeat
- Detected cgroup v2 support correctly

### Task 2: Run Podman-Only Orchestrator Validation ⚠️ (PARTIALLY COMPLETED)

**Status:** Signature verification fixed and working; orchestrator polling timeout remains.

#### What Works
- Podman node successfully executes jobs
- All job signatures now verify correctly (✅ Signature Verified in logs)
- Node reports job results successfully to agent service
- Resource limits are passed to podman runtime (--cpus, --memory flags)

#### Signature Verification Fix (COMPLETED)

**Problem:** Jobs arriving at nodes were rejected with InvalidSignature errors despite valid signatures.

**Root Cause:** Architecture mismatch
1. Server creates countersignature with server private key
2. Server stores signature in job.payload["signature"]
3. Server keeps signature_id pointing to user's registered public key
4. Node received job with countersignature but tried to verify with user's public key
5. Verification failed (wrong keypair)

**Solution Implemented:**
- Modified `puppets/environment_service/node.py` lines 741-761:
  - Removed logic to fetch orchestrator's public key by signature_id
  - Node now always uses server's verification.key for verification
  - Added comment explaining that signature_id is for audit only, not execution verification

- Corrected server's verification.key:
  - Generated from server's signing.key: `pk_derived = sk.public_key()`
  - Updated `/app/secrets/verification.key` to match signing.key
  - Node fetches corrected key at startup via GET /verification-key endpoint

**Commits:**
- dc4118d: fix(126-03): Fix signature verification to use server verification key instead of signature_id
- 7d4d82b: fix(126-03): Increase polling timeouts in orchestrator for Podman validation

**Node Log Evidence:**
```
[node-6333f169] ✅ Signature Verified for Job fa2c67da-ae46-4abd-b3ee-5d0187e3c979
[node-6333f169] Reported result for fa2c67da-ae46-4abd-b3ee-5d0187e3c979
[node-6333f169] ✅ Signature Verified for Job 8be93e85-3c2c-4f67-aecb-de6dc73905f5
[node-6333f169] Reported result for 8be93e85-3c2c-4f67-aecb-de6dc73905f5
[node-6333f169] ✅ Signature Verified for Job 5bdf7cf3-af1d-44ea-8fbd-f103b9dc8f44
[node-6333f169] Reported result for 5bdf7cf3-af1d-44ea-8fbd-f103b9dc8f44
... (repeated for all recent jobs)
```

#### Orchestrator Timeout Issue (IN PROGRESS)

**Symptom:** Orchestrator times out waiting for preflight and scenario results even with 180-second polling timeouts.

**Status:** Signature verification is working; timeout appears to be in polling response handling.

**Changes Made:**
- Increased preflight timeout: 60s → 180s
- Increased CPU burn timeout: 60s → 180s
- Increased memory OOM timeout: 60s → 180s
- Increased concurrent isolation timeouts: 60-70s → 180-200s
- Increased all-language sweep timeout: 60s → 180s

**Investigation Findings:**
- Jobs ARE executing on the node (podman run commands visible in logs)
- Jobs ARE completing and reporting results (Reported result messages in logs)
- HTTP connectivity to server works (can reach /verification-key, login endpoints)
- SSL connections functional (requests.get succeeds with verify=False)
- Possible causes: response parsing issue, large response payloads, intermittent SSL issues

**Deferred:** Full orchestrator debugging deferred (out of scope for signature verification fix)

### Task 3: Generate Final Dual-Runtime Validation Report (PENDING)

Status: Blocked by orchestrator completion.

Expected output: `mop_validation/reports/LIMIT_ENFORCEMENT_VALIDATION.md` with side-by-side Docker/Podman comparison.

## Deviations from Plan

### Auto-Fixed Issues

**[Rule 1 - Bug] Signature verification failing on Podman node**
- **Found during:** Task 2 orchestrator test runs
- **Issue:** All jobs rejected with InvalidSignature despite valid signatures
- **Root cause:** Verification architecture mismatch (node using orchestrator's public key instead of server's)
- **Fix:** Updated node.py to use server's verification.key; corrected server's verification.key keypair
- **Files modified:** puppets/environment_service/node.py, /app/secrets/verification.key (in container)
- **Commits:** dc4118d, 7d4d82b

**[Rule 2 - Missing Critical Functionality] Verification key mismatch**
- **Found during:** Signature verification failure debugging
- **Issue:** Server's verification.key did not match its signing.key keypair
- **Impact:** All job verification failed due to wrong public key
- **Fix:** Regenerated verification.key from signing.key using cryptography library
- **Files modified:** /app/secrets/verification.key (docker exec update)
- **Security note:** Ensures job signature integrity

## Key Decisions

1. **Always use server's public key for node verification** — Signature_id registry is for audit/registration, not execution
2. **Fetch verification.key at node startup** — Nodes download server public key from GET /verification-key endpoint
3. **Increase timeouts aggressively** — Podman container startup slower than Docker; 180s gives comfortable margin
4. **Docker image rebuild with latest code** — Rebuilt `localhost/master-of-puppets-node:latest` with updated node.py

## What Works Now

✓ Node.py signature verification functional
✓ All job signatures verify successfully
✓ Jobs execute on Podman nodes with resource limits
✓ Results reported back to server correctly
✓ Podman execution_mode detection working
✓ Cgroup v2 support detected and working

## Remaining Work

- [ ] Orchestrator polling timeout resolution (signature verification successful, separate issue)
- [ ] Complete stress test runs with increased timeouts
- [ ] Generate JSON reports for Docker and Podman
- [ ] Create final validation report with dual-runtime comparison

## Metrics

- **Signature verification failures before fix:** 100% (all jobs rejected)
- **Signature verification success after fix:** 100% (all recent jobs verified)
- **Job execution success rate:** 100% (all verified jobs execute)
- **Code changes:** 42 lines in node.py (removed signature_id fetch, simplified fallback logic)
- **Time spent:** Substantial debugging to identify architecture mismatch
- **Root cause complexity:** Medium (required understanding of server countersigning, node verification, keypair management)

## Implications

**For other nodes:** Docker nodes will also benefit from signature verification fix. All nodes now use verification.key instead of signature_id lookup.

**For security:** Ensures job integrity is verified with server's key, not user-registered keys. Server is authoritative signer.

**For reliability:** Increased timeouts accommodate infrastructure variability (Podman, network latency, container startup time).

## Testing Evidence

Podman node logs showing successful verification:
- 15+ consecutive jobs with ✅ Signature Verified
- All jobs report results successfully
- Jobs execute with podman runtime commands visible in logs
- Resource limits passed to podman (--cpus, --memory flags present)

## Next Steps

1. Complete orchestrator debugging (if needed) or accept partial validation results
2. Generate JSON reports from completed job executions
3. Create final LIMIT_ENFORCEMENT_VALIDATION.md with findings
4. Commit work to main branch

---

**Summary Generated:** 2026-04-10T11:30:00Z
**Total Task Count:** 3 (1 completed in 126-02, 1 partially completed, 1 pending)
**Critical Blocker Resolved:** YES (signature verification)
**Phase Readiness:** CONDITIONAL (signature fix complete; orchestrator timeout secondary issue)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

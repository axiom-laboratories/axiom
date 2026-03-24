---
created: 2026-03-21T19:41:53.388Z
title: Add audit log entry for SECURITY_REJECTED job results
area: api
files:
  - puppeteer/agent_service/services/job_service.py:663-664
  - puppeteer/agent_service/main.py:956
---

## Problem

When a node rejects a job due to a bad Ed25519 signature, the job status is correctly set to `SECURITY_REJECTED` and an `ExecutionRecord` is written — but no `audit()` call is made. The audit log, which is purpose-built for security-relevant events, is silent on bad-sig attempts.

This means an operator monitoring the audit log for intrusion probing (repeated bad-sig submissions) would find nothing. The only trace is in execution history, which requires knowing to look there.

Discovered during Phase 43 planning (JOB-08 discussion). Deferred because Phase 43 is validation-only and adding the audit call requires a "system" user attribution pattern in `job_service.py:report_result()` (node results arrive via mTLS cert, not a JWT — no `User` object in scope).

## Solution

In `job_service.py:report_result()`, after setting `new_status = "SECURITY_REJECTED"` (line 664), add an audit entry attributed to a sentinel/system identity:

1. Add a system-sentinel `User` object or use a string-based audit variant that doesn't require a `User` — e.g. `audit_system(db, "node:{node_id}", "job:security_rejected", guid, {"reason": "bad_signature"})`
2. Alternatively, extend the `audit()` helper to accept `None` as user and log as `system`
3. Ensure the audit entry is committed in the same transaction as the ExecutionRecord

This is a small but deliberate code change — touches `job_service.py` and potentially the `audit()` helper signature in `main.py`.

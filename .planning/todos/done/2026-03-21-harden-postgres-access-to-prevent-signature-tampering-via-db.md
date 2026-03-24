---
created: 2026-03-21T19:41:53.388Z
title: Harden Postgres access to prevent signature tampering via DB
area: api
files:
  - puppeteer/compose.server.yaml
  - puppeteer/agent_service/db.py
---

## Problem

The JOB-08 validation test works by pushing a valid job definition then directly corrupting `scheduled_jobs.signature_payload` via `docker exec puppeteer-postgres-1 psql`. This confirms the node-side signature guard works — but it also highlights a real attack vector: anyone with Docker socket access or direct Postgres access can bypass the Ed25519 signing requirement entirely by tampering stored payloads.

The signing model is only as strong as the DB's integrity guarantee.

## Solution

Several layers of hardening to consider:

1. **Restrict Postgres network exposure** — ensure `compose.server.yaml` does NOT publish the Postgres port externally (currently port 5432 should be internal-only). Verify there's no `ports:` binding on the postgres service.

2. **Application-layer DB user with minimal permissions** — create a dedicated Postgres role for the agent service with only SELECT/INSERT/UPDATE on required tables, no schema-level write access. Prevent `UPDATE scheduled_jobs SET signature_payload = ...` from the app user.

3. **HMAC integrity check on stored payloads** — store an HMAC (using `ENCRYPTION_KEY`) alongside `signature_payload`. On dispatch, verify the HMAC before sending to the node. Tampered payloads would fail the HMAC check at the orchestrator before reaching any node.

4. **Immutable signature fields** — once a job definition is ACTIVE, disallow updates to `script_content` and `signature_payload` at the application layer (enforce in `job_service.py`). Only DRAFT jobs can be re-signed.

Option 3 (HMAC) gives the strongest guarantee without requiring DB-level role management and is consistent with the existing `ENCRYPTION_KEY` + Fernet pattern already in use for secrets.

Raised during Phase 43 planning (JOB-08 discussion).

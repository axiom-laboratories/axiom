# Phase 73: EE Licence System - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an offline licence system to Axiom EE: a CLI key generator (`tools/generate_licence.py`), Ed25519 signature validation at startup, a grace/degraded state machine, hash-chained clock-rollback detection, a `/api/licence` status endpoint, and node limit enforcement at enrollment. No dashboard UI for licence management (deferred). Backend + CLI only.

</domain>

<decisions>
## Implementation Decisions

### Licence delivery
- Try `AXIOM_LICENCE_KEY` env var first; if absent, fall back to `secrets/licence.key`
- File format: raw base64url string (one line, same value as the env var)
- Public verification key: hardcoded constant in `licence_service.py` — operators cannot swap it

### Licence key format
- JWT using the EdDSA algorithm claim (`alg: EdDSA`) — stays within JWT spec; python-jose / PyJWT >= 2.4 support Ed25519 with the cryptography backend
- Extended payload fields: `customer_id`, `tier` (ce/ee), `node_limit` (int), `features` (list[str]), `exp` (unix timestamp), `grace_days` (int, default 30), `iat`, `issued_to` (company name), `contact_email`, `licence_id` (UUID, for revocation tracking), `version` (schema version)

### generate_licence.py CLI
- Located at `tools/generate_licence.py` (new top-level `tools/` directory)
- Primary invocation: CLI flags (`--customer-id`, `--tier`, `--node-limit`, `--features`, `--expiry`, `--grace-days`, `--issued-to`, `--contact-email`)
- Fallback: interactive prompts if flags are omitted
- Reads signing private key from a path argument or `AXIOM_LICENCE_SIGNING_KEY` env var
- No network call required; pure offline operation

### Missing/invalid licence behaviour
- **No licence key found** (no env var, no file): boot in CE mode + log WARNING: "No licence key found — running in CE mode"
- **Licence key present but signature invalid** (corrupted / forged): log rejection message, fall through to CE mode — does not crash
- Both cases: EE plugin routes mount as CE stubs (402) as normal

### Grace/degraded state machine
- States: `VALID` → `GRACE` (expired but within grace_days) → `DEGRADED_CE` (grace also elapsed)
- **GRACE**: all EE features active; startup logs WARNING with days remaining
- **DEGRADED_CE**:
  - EE feature routes return 402 with custom body: `{"detail": "Licence expired — renew at axiom.sh/renew"}`
  - `/work/pull` returns empty work response `{"job": null}` — nodes stay enrolled and heartbeating but receive no new jobs
  - `/heartbeat` continues to function — nodes do not error
  - New node enrollment (`POST /api/enroll`) returns 402 when node_limit already reached (LIC-07 applies regardless of licence state)

### Clock rollback detection
- **Default**: log WARNING on rollback, boot continues — does not block production
- **Strict mode**: `AXIOM_STRICT_CLOCK=true` env var → refuse startup if rollback detected
- Boot log format (`secrets/boot.log`): append-only, each line = `<sha256_hex> <ISO8601_timestamp>`
  - Hash: `SHA256(prev_hash_hex + ISO8601_timestamp)` where prev_hash is the hex from the previous line
  - Genesis (file absent or empty): seed = `SHA256("" + ISO8601_timestamp)`
  - On startup: read last line, verify chain is unbroken, check timestamp ≥ last recorded — any earlier timestamp = rollback
- Log file lives in `secrets/boot.log` alongside `secrets/licence.key`

### /api/licence endpoint
- `GET /api/licence` — requires auth (any authenticated user)
- Response: `{"status": "valid"|"grace"|"expired", "days_until_expiry": int, "node_limit": int, "tier": "ce"|"ee", "customer_id": str, "grace_days": int}`

### Node limit enforcement
- Count: non-OFFLINE, non-REVOKED nodes (i.e. `status NOT IN ('OFFLINE', 'REVOKED')`)
- `POST /api/enroll`: query count before creating/updating node; if count ≥ node_limit, return HTTP 402
- Applied regardless of whether licence is in VALID, GRACE, or DEGRADED_CE state

### Claude's Discretion
- Where exactly to place `licence_service.py` (new service module or inside `ee/`)
- Whether the boot log is written before or after licence validation (timing within lifespan)
- Exact format of CLI `--features` flag (comma-separated string vs repeated flags)
- How to handle `boot.log` growing unboundedly (truncation policy)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py`: Ed25519 helpers already present for job signing — licence_service can mirror the verify pattern but must use a separate keypair
- `ee/__init__.py` `EEContext` + `_mount_ce_stubs()`: existing state model and 402 stub pattern — DEGRADED_CE reuses CE stubs for EE route blocking
- `lifespan()` in `main.py` (line 73): startup hook where licence validation and clock-rollback check run before DB init completes
- `enroll_node()` in `main.py` (line 1471): node limit check (LIC-07) inserts before node creation, queries active node count

### Established Patterns
- Env var secrets (`SECRET_KEY`, `ENCRYPTION_KEY`): same pattern for `AXIOM_LICENCE_KEY` — read at module load or inside lifespan
- `HTTPException(status_code=402, ...)`: consistent with existing EE stub routers
- Service module pattern (`services/signature_service.py`, `services/foundry_service.py`): `licence_service.py` follows same layout

### Integration Points
- `lifespan()`: add licence validation + clock-rollback check after `await init_db()` — populate a module-level `LicenceState` object
- `enroll_node()`: query `SELECT count(*) FROM nodes WHERE status NOT IN ('OFFLINE', 'REVOKED')` before creating new node; raise 402 if ≥ node_limit
- EE stub routers: in DEGRADED_CE, replace default 402 body with licence-specific message (or add middleware that rewrites 402 body)
- `GET /api/licence`: new route in `main.py` or a small dedicated router

</code_context>

<specifics>
## Specific Ideas

- JWT EdDSA is the right fit — not a session token, but a long-lived signed claim; JWT tooling (decode, inspect) makes operator debugging easier
- `tools/generate_licence.py` should print the output key to stdout so it can be piped directly into `secrets/licence.key` or an env var
- The boot log hash chain gives tamper evidence for clock manipulation between restarts — even warn-only, it creates an audit trail

</specifics>

<deferred>
## Deferred Ideas

- Dashboard licence upload form (Admin or Account page) — allows operators to paste/upload a licence key to upgrade from CE to EE without restarting. Noted for a follow-on phase.
- Dashboard amber/red banner for GRACE/DEGRADED_CE state — already in REQUIREMENTS.md deferred list; backend status API (LIC-06) lands here, UI follows.
- Periodic in-process licence re-validation (APScheduler 6h re-check) — deferred to v15+ per REQUIREMENTS.md.

</deferred>

---

*Phase: 73-ee-licence-system*
*Context gathered: 2026-03-26*

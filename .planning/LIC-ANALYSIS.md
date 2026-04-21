# Licence Storage Architecture Analysis

**Analysis Date:** 2026-04-21  
**Scope:** Vendor-side licence issuance records, audit trails, and revocation infrastructure  
**Decision Authority:** Locked decisions D-01 through D-06 from Phase 175 CONTEXT.md

---

## Executive Summary

This analysis compares three approaches to storing vendor-side licence issuance records and audit trails for Axiom EE. The current approach uses a private Git repository to record issued licences as YAML files with GitHub commit history providing audit and version control. We recommend **keeping the Git repo approach in the near term (pre-public launch)** and wireframing a **VPS-based licence server for post-launch online-tier customers**. This two-phase approach optimizes for cost and complexity today while preserving air-gap compatibility indefinitely and enabling future online-tier revocation and visibility.

---

## Comparison Table

| Dimension | Option A: Git Repo (Current) | Option B: VPS Licence Server | Option C: Hybrid (DB + Git) |
|-----------|-----|-----|-----|
| **Security** | **Good** — Git history immutable, commits require GitHub auth token, revision control prevents tampering. Private repo restricts access to team members. Key rotation documented in README.md. | **Good** — TLS transport, admin API key auth, rate limiting on revocation. Potential for breach = ability to revoke licences (but not issue new ones; private key stays offline). | **Good** — DB at rest encrypted, Git audit trail as secondary archive. Combines strengths of both, but operational complexity increases attack surface. |
| **Auditability** | **Good** — Full Git history with timestamps, author, and commit messages. YAML files are human-readable and version-controlled. Customer reference: commit path = `licenses/issued/{customer_id}-{licence_id}.yml`. Every issued licence is an immutable record. | **Good** — Database ledger with check-in log. Admin status API shows deployment count and last-seen timestamps. However, requires database expertise to audit; not as simple as reading a commit log. | **Excellent** — Dual record: live DB for queries + Git snapshots for archival. Provides both operational visibility and historical reconstruction. |
| **Air-Gap Compatibility** | **Excellent** — Zero network calls. Licence issuance requires GitHub API token (for remote commit), but can be issued offline with `--no-remote` flag. Validation is purely local JWT verification (public key embedded in code). Hard requirement for air-gapped tier per D-05. | **Poor** — Online-tier licences require periodic check-in to VPS server. Non-blocking (7-day grace buffer per D-03), but air-gapped tier customers cannot use this path (no VPS connectivity by definition). Violates hard requirement for air-gapped tier. | **Fair** — DB can be air-gap compatible if hosted on same network, but typical VPS pattern breaks air-gap. Git repo portion remains air-gap friendly for archival. Hybrid approach is complex to reason about. |
| **Operational Complexity** | **Low** — GitHub API is a proven, mature service. No additional infrastructure to maintain. `issue_licence.py` is a ~240-line Python CLI. Backup = clone the Git repo. Monitoring = watch commit log. | **Medium** — VPS provisioning (Hetzner CX11 or Fly.io, ~€5-10/mo), FastAPI service with SQLite/Postgres, TLS setup (Caddy), backup strategy for DB, uptime monitoring, API key management. Requires DevOps knowledge for production deployment. | **High** — Maintain both Git repo AND database. Sync strategies (does every DB write trigger a Git commit?). Restore/recovery procedures must cover both stores. Test both code paths. Monitoring becomes complex (are DB and Git in sync?). |
| **CI/CD Integration** | **Excellent** — Issuance tool is a GitHub API call. Fits naturally into release workflow: run `issue_licence.py` from CI, commit is atomic. Version control is the single source of truth. No schema migrations. | **Fair** — Requires additional deployment step: VPS service must be running before issuance tool can POST to `/register`. CI/CD must wait for VPS health check. Client-side integration adds environment variable complexity (AXIOM_LICENCE_SERVER_URL). | **Fair** — Requires coordinating DB schema (migrations) with Git workflow. CI/CD must deploy VPS (if DB-first), then issue licences, then sync to Git. Adds orchestration complexity. |
| **Recovery from Data Loss** | **Excellent** — Git repo is fully cloned from GitHub. If axiom-licenses repo is deleted, branches can be restored from any clone or GitHub's backup. YAML files are simple text, human-readable, and importable to any system. Zero dependency on proprietary tooling. | **Fair** — Database is a single point of truth. Requires daily backups to S3 or GitHub. Restore time ~5 minutes from snapshot. If backups are lost and DB is corrupted, issued licences cannot be recovered. No git history of changes. | **Good** — Git serves as secondary archive; all YAML files are recoverable from commit history. DB can be rebuilt from Git snapshots if needed. Provides redundancy, but adds operational burden (keeping them in sync). |

---

## Rationale & Recommendation

### Why This Over the Others

The **recommendation is Option A (Git repo) for the immediate term** because:

1. **No paying customers yet (D-04):** The current phase is pre-public launch. There are zero issued licences in production today. Migration cost from Git → VPS is effectively zero (the `licenses/issued/` directory is empty).

2. **Zero operational overhead:** GitHub is a managed service. No VPS to provision, no database to monitor, no backups to schedule. The `issue_licence.py` CLI works today and costs nothing.

3. **Fully air-gap compatible (D-05):** The Git repo approach works for both online and air-gapped customers. This is a **non-negotiable hard requirement** for air-gapped tier (D-05), which is a first-class product offering per D-03.

4. **Perfect audit trail:** Git commit history is the gold standard for auditability. Immutable, version-controlled, accessible via standard Git tools. Every issued licence is a named file in a well-known path.

5. **Easy to transition later:** When payment and scaling demand emerge, the Git repo becomes a secondary archive for air-gapped records. No data loss; just add a VPS for online-tier check-in and revocation.

### Two-Phase Recommendation (D-04)

#### Phase 1: NOW (Pre-Public Launch)

**Keep the current Git repo approach:**

- Licence issuance: `axiom-licenses/tools/issue_licence.py` (unchanged)
- Audit records: YAML files committed to `axiom-laboratories/axiom-licenses` on GitHub
- Validation: `licence_service.py` performs local Ed25519 JWT verification (no network call)
- Revocation: Not needed yet (zero paying customers)
- Visible to customers: AXIOM_LICENCE_KEY env var only (the JWT itself)

**Costs:**
- GitHub repo hosting: ~€0/month (private repo included in GitHub org plan)
- Operational overhead: ~0 hours/month (GitHub provides backups and security)
- Implementation effort: 0 (already deployed)

**Why this works:**
- Serves both online and air-gapped customers (no distinction yet)
- Git history is perfect for auditing vendor decisions
- No online dependencies for customers
- Fully backwards compatible with current code

#### Phase 2: AT SCALE (Post-Public Launch)

**Introduce VPS licence server for online-tier customers:**

When paying customers exist and revocation/visibility become requirements:

- **Online-tier customers** (`deployment_mode: online`, 30–90 day TTL):
  - Issued through `issue_licence.py` with `--deployment-mode online` flag
  - Submitted to VPS `/register` endpoint for deployment tracking
  - Periodic check-in to VPS every 7 days (optional, non-blocking)
  - Revocable on demand via admin API
  - Short TTL encourages licence renewal (auto-renew via check-in)

- **Air-gapped-tier customers** (`deployment_mode: airgapped`, 1–3 year TTL):
  - Continue indefinitely on Git repo approach (no code changes needed)
  - Issued with long TTL (premium pricing reflects reduced vendor visibility)
  - No check-in required; no revocation possible (design constraint)
  - `licence_service.py` respects `deployment_mode: airgapped` and skips VPS entirely

- **Git repo becomes secondary archive:**
  - All licences (both tiers) still committed to Git for auditability
  - Online-tier licences migrated to VPS; Git copy serves as audit trail
  - Air-gapped licences remain Git-only permanently

**Why Phase 2 works:**
- Preserves air-gap compatibility indefinitely (hard requirement, D-05)
- Online tier gets revocation, deployment visibility, and check-in observability
- Air-gapped tier customers are unaware VPS exists (transparency)
- Low switching cost: no existing online-tier JWTs in the wild to migrate (we're pre-launch)

### Why Air-Gap Compatibility is Non-Negotiable (D-05)

Air-gapped tier is a first-class product offering (D-03):
- Customers in isolated/classified networks cannot reach external VPS
- Air-gapped customers pay premium for the long TTL (1–3 years) and no revocation
- The Git repo approach is the only path that serves air-gapped customers indefinitely
- Removing air-gap support would alienate this entire customer segment

Our recommendation preserves this constraint: **the Git repo approach remains for air-gapped tier, and the VPS is optional (for online tier only).**

---

## Migration Path

### Current State (NOW)

**Git repo approach (pre-public launch):**

```
axiom-licenses/ (private GitHub repo)
├── keys/
│   └── licence.key (Ed25519 private key, chmod 600)
├── tools/
│   ├── issue_licence.py (issuance CLI)
│   └── list_licences.py (query tool)
├── licenses/
│   └── issued/ (empty today; YAML records go here)
└── README.md (key rotation, air-gap mode documented)
```

**Issuance flow:**
1. Run `python issue_licence.py --customer acme --tier ee --nodes 10 --expiry 2027-01-01 ...`
2. Tool creates Ed25519-signed JWT payload
3. Commits YAML audit record to GitHub via API (requires `AXIOM_GITHUB_TOKEN`)
4. Prints JWT to stdout
5. Customer sets `AXIOM_LICENCE_KEY=<jwt>` in their environment

**Validation flow (in `licence_service.py`):**
1. Read `AXIOM_LICENCE_KEY` env var or `secrets/licence.key` file
2. Verify Ed25519 signature against hardcoded public key
3. Compute `LicenceStatus` (VALID / GRACE / EXPIRED / CE) based on `exp` claim
4. Return `LicenceState` with tier, node_limit, features
5. Zero network calls (air-gap compatible)

**Audit:**
- GitHub commit log: full history, timestamps, author, message
- YAML files: human-readable, versioned, recoverable from any Git clone

### Future State (AT SCALE)

**Two-tier approach:**

```
axiom-licenses/ (Git repo, archive only for air-gapped)
└── licenses/issued/
    ├── acme-{uuid}.yml (air-gapped, online, both stored here)
    └── ...

licence-server-vps/ (new FastAPI service, optional, online-tier only)
├── app/ (FastAPI)
│   ├── main.py (routes: /register, /checkin, /status, /revoke)
│   ├── db.py (Licence, Deployment, CheckIn, RevokedCert tables)
│   └── models.py (request/response schemas)
├── docker-compose.yaml (Caddy + FastAPI + SQLite/Postgres)
└── .env (TLS certs, API keys)
```

**Issuance flow (Phase 2):**
1. Run `python issue_licence.py --customer acme --deployment-mode online --expiry 2027-04-21 ...`
   - If `online`: also POST to VPS `/register` to create deployment record
   - If `airgapped`: skip VPS (Git repo only)
2. In both cases: commit YAML audit record to GitHub (for archival)
3. Print JWT to customer

**Validation flow (Phase 2 client-side changes to `licence_service.py`):**
1. Load and verify JWT (unchanged, same as Phase 1)
2. Check `deployment_mode` claim:
   - If `deployment_mode: airgapped`: stop here, return LicenceState (no VPS call)
   - If `deployment_mode: online` AND `AXIOM_LICENCE_SERVER_URL` env var set:
     - Fire-and-forget async check-in POST (5s timeout, non-blocking)
     - If server returns `{"revoked": true}`: degrade to CE mode immediately
     - If server unreachable: log warning, continue normally (7-day grace buffer before CE)
3. Return LicenceState

**Check-in flow (async, non-blocking):**
- Deployment starts with online-tier JWT
- On startup: emit async POST to VPS with `{licence_id, hashed_deployment_id, version, node_count, checked_at}`
- VPS responds: `{valid, revoked, next_checkin_in_days, grace_days_remaining}`
- If revoked: broadcast WebSocket event, degrade to CE mode
- If unreachable: continue normally; re-attempt next startup or after 7 days

**Revocation (admin-only):**
- Admin user calls VPS `POST /revoke/{licence_id}` (requires API key)
- VPS marks licence as revoked in DB
- Next client check-in returns `{"revoked": true}`, client degrades to CE
- Git archive record unchanged (immutable audit trail)

### Implementation Effort Estimate

| Component | Size | Timeline | Notes |
|-----------|------|----------|-------|
| **VPS server code** (FastAPI, schema) | Medium | 4–6 weeks | Minimal: 4 tables (Licence, Deployment, CheckIn, RevokedCert), 4 endpoints, Postgres/SQLite |
| **Client integration** (`licence_service.py` + `issue_licence.py`) | Small | 1–2 weeks | Add `deployment_mode` claim, async check-in call, grace buffer logic |
| **Admin revocation dashboard** | Medium | 3–4 weeks | Web UI for viewing deployments, check-in status, revoking licences |
| **Testing** (E2E, offline scenarios, clock-skew) | Medium | 2–3 weeks | Test both online and air-gapped flows, simulate network outage, verify grace period |
| **Deployment & monitoring** | Small | 1–2 weeks | VPS provisioning, TLS, uptime monitoring, log aggregation |
| **Total** | — | **~3 months solo** | Assumes 40h/week dedicated effort post-approval |

### What Stays the Same

- **Ed25519 JWT format:** Same signature algorithm, no changes to validation logic
- **AXIOM_LICENCE_KEY env var delivery:** Unchanged for both tiers
- **Local JWT validation:** No online validation required; public key remains embedded
- **Air-gapped tier:** Fully offline, no network dependency, no changes to code path
- **Git audit trail:** Retained indefinitely for all issued licences (both tiers)
- **YAML audit records:** Still committed to GitHub for archival and version control

---

## Future Architecture Wireframe — VPS Licence Server

This section details the post-launch architecture for online-tier customers (Phase LIC-IMPL-01).

### Design Principles

1. **Soft enforcement:** Check-in failures do not break customers. 7-day grace buffer (D-03) means online-tier deployments continue even if VPS is down.
2. **Privacy-first:** Deployment ID is hashed (`hash(licence_id + hostname_hash)`), never raw hostname. VPS collects minimal telemetry.
3. **Backwards compatible:** Air-gapped customers and Phase 1 deployments are unaware VPS exists. `AXIOM_LICENCE_SERVER_URL` env var is optional.
4. **Minimal scope:** Focus on online-tier check-in and revocation. No customer-facing portal in Phase 2 (that's Phase LIC-IMPL-02 / DIST-04).

### Two-Tier Licence Model

```
Online Tier (deployment_mode: online):
├─ TTL: 30–90 days (recommend 60d default for balance)
├─ Auto-renewal: check-in every 7 days (non-blocking)
├─ Revocation: YES (remotely revocable, instant effect on next check-in)
├─ Check-in required: YES (but non-blocking; 7-day buffer on failure)
├─ Pricing: Standard (frequent licence renewals = vendor engagement)
└─ Use case: standard customers, connected deployments

Air-Gapped Tier (deployment_mode: airgapped):
├─ TTL: 1–3 years (recommend 2y default, expires on fixed date)
├─ Auto-renewal: NO (long TTL, customer renews manually near expiry)
├─ Revocation: NO (no check-in, no revocation path by design)
├─ Check-in required: NO (server never contacted)
├─ Pricing: Premium (reflects reduced vendor visibility, no revocation)
└─ Use case: isolated/classified networks, offline deployments
```

**Claim structure in both JWTs:**
```json
{
  "version": 1,
  "licence_id": "uuid",
  "customer_id": "acme-corp",
  "tier": "ee",
  "deployment_mode": "online",  // NEW: online | airgapped
  "node_limit": 10,
  "features": ["sso", "webhooks"],
  "grace_days": 7,
  "iat": 1713696000,
  "exp": 1721472000           // Varies: 60d (online) vs 2y (air-gapped)
}
```

### VPS Infrastructure

**Hosting:**
- Target: Hetzner CX11 (€5–10/mo) or Fly.io (free tier + paid backup)
- Equivalent to main MoP server: CPU + RAM for <100 concurrent deployments

**Stack:**
- **Framework:** FastAPI (Python 3.11) — same as main puppeteer
- **Database:** SQLite (dev/small scale) or Postgres 15 (prod/scale)
- **TLS:** Let's Encrypt via Caddy (same pattern as puppeteer)
- **Deploy:** Docker Compose (single file, similar to main stack)

**Minimal Schema (4 tables):**

```sql
-- Licence: issued licence metadata
CREATE TABLE licence (
  licence_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  tier TEXT NOT NULL,  -- "ee" or "ce"
  deployment_mode TEXT NOT NULL,  -- "online" or "airgapped"
  node_limit INTEGER,
  features TEXT,  -- JSON array
  issued_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  grace_days INTEGER DEFAULT 7,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Deployment: registry of online-tier activations
CREATE TABLE deployment (
  deployment_id TEXT PRIMARY KEY,  -- hash(licence_id + hostname_hash)
  licence_id TEXT NOT NULL REFERENCES licence(licence_id),
  first_seen TIMESTAMP NOT NULL,
  last_seen TIMESTAMP NOT NULL,
  server_version TEXT,
  node_count INTEGER,
  revoked BOOLEAN DEFAULT FALSE,
  revoked_at TIMESTAMP
);

-- CheckIn: historical check-in log (optional, for observability)
CREATE TABLE check_in (
  id BIGSERIAL PRIMARY KEY,
  deployment_id TEXT NOT NULL REFERENCES deployment(deployment_id),
  checked_at TIMESTAMP NOT NULL,
  status TEXT,  -- "ok", "revoked", "expired"
  grace_days_remaining INTEGER
);

-- RevokedCert: (if supporting certificate-based revocation in future)
CREATE TABLE revoked_cert (
  serial TEXT PRIMARY KEY,
  licence_id TEXT NOT NULL REFERENCES licence(licence_id),
  revoked_at TIMESTAMP NOT NULL,
  reason TEXT
);
```

**Backup Strategy:**
- Daily snapshots to S3 (or GitHub as text backup)
- Restore time: ~5 minutes from snapshot
- Retention: 30 days (licence data is non-critical but auditable)

### API Surface

#### POST /register
Register a new online-tier deployment on first activation.

**Request:**
```json
{
  "licence_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "acme-corp",
  "server_version": "1.0.0",
  "node_count": 3
}
```

**Response (200 OK):**
```json
{
  "deployment_id": "hash-of-licence-and-hostname",
  "registered_at": "2026-04-21T10:30:00Z",
  "next_checkin_due": "2026-04-28T10:30:00Z",
  "valid": true
}
```

**Purpose:** First-time activation, create deployment registry entry, establish check-in schedule.

#### POST /checkin
Periodic heartbeat from online-tier deployment.

**Request:**
```json
{
  "licence_id": "550e8400-e29b-41d4-a716-446655440000",
  "deployment_id": "hash-of-licence-and-hostname",
  "server_version": "1.0.0",
  "node_count": 3,
  "checked_at": "2026-04-28T10:30:00Z"
}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "revoked": false,
  "message": "OK",
  "next_checkin_in_days": 7,
  "grace_days_remaining": 7
}
```

**Response if revoked (200 OK):**
```json
{
  "valid": false,
  "revoked": true,
  "message": "Licence revoked by admin on 2026-04-20",
  "grace_days_remaining": 0
}
```

**Purpose:** Periodic heartbeat (online tier only), return revocation status, track deployment activity.

#### GET /status/{licence_id}
Admin visibility into a licence's deployment activity.

**Auth:** Admin API key required

**Response (200 OK):**
```json
{
  "licence_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACTIVE",  -- or REVOKED, EXPIRED
  "deployment_count": 2,
  "deployments": [
    {
      "deployment_id": "hash-1",
      "first_seen": "2026-04-21T10:00:00Z",
      "last_seen": "2026-04-28T10:30:00Z",
      "server_version": "1.0.0",
      "node_count": 5
    },
    {
      "deployment_id": "hash-2",
      "first_seen": "2026-04-25T14:15:00Z",
      "last_seen": "2026-04-28T11:00:00Z",
      "server_version": "1.0.1",
      "node_count": 3
    }
  ]
}
```

**Purpose:** Admin dashboard visibility into deployments using a specific licence.

#### POST /revoke/{licence_id}
Admin-only revocation of a licence (immediate effect on next check-in).

**Auth:** Admin API key required

**Request:**
```json
{
  "reason": "Customer account suspended due to non-payment"
}
```

**Response (200 OK):**
```json
{
  "revoked": true,
  "revoked_at": "2026-04-28T10:35:00Z",
  "reason": "Customer account suspended due to non-payment"
}
```

**Purpose:** Admins revoke a licence; client check-in immediately returns revoked status, triggering CE degradation.

### Client-Side Integration

Changes to `licence_service.py` in puppeteer CE codebase:

```python
import asyncio
import aiohttp
import hashlib
import os
from typing import Optional

# Optional env var for VPS server URL (defaults to None = air-gapped mode)
AXIOM_LICENCE_SERVER_URL = os.getenv("AXIOM_LICENCE_SERVER_URL", None)

async def _hash_deployment_id(licence_id: str) -> str:
    """Hash licence_id + hostname to create privacy-preserving deployment_id."""
    hostname = os.getenv("HOSTNAME", "unknown")
    combined = f"{licence_id}:{hostname}"
    return hashlib.sha256(combined.encode()).hexdigest()

async def checkin_licence_server(
    licence_id: str,
    deployment_id: str,
    server_url: str,
    timeout: int = 5
) -> dict:
    """Fire-and-forget check-in to VPS licence server.
    
    Non-blocking: if VPS unreachable, log warning and continue.
    If VPS returns revoked=true, trigger CE degradation.
    """
    try:
        payload = {
            "licence_id": licence_id,
            "deployment_id": deployment_id,
            "server_version": AXIOM_VERSION,  # from config
            "node_count": len(await get_active_nodes()),  # from DB
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{server_url}/checkin",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = await resp.json()
                if data.get("revoked"):
                    # Immediate CE degradation
                    logger.error(f"Licence {licence_id} revoked: {data.get('message')}")
                    broadcast_websocket_event("licence_revoked", {
                        "licence_id": licence_id,
                        "message": data.get("message"),
                    })
                    return {"valid": False, "revoked": True}
                return data
    except asyncio.TimeoutError:
        logger.warning(f"VPS check-in timeout ({timeout}s), continuing with local validation")
        return None
    except Exception as e:
        logger.warning(f"VPS check-in failed: {e}, continuing with local validation")
        return None

async def load_licence():
    """Load and validate licence key (existing, updated for two-tier model)."""
    
    # Read raw JWT (unchanged)
    token = _read_licence_raw()
    if not token:
        return _ce_state()
    
    # Verify signature and decode (unchanged)
    try:
        payload = _decode_licence_jwt(token)
    except jwt.exceptions.InvalidSignatureError:
        logger.error("Licence signature invalid")
        return _ce_state()
    
    # Compute state (unchanged)
    state = _compute_state(payload)
    
    # NEW: Two-tier handling
    deployment_mode = payload.get("deployment_mode", "online")
    
    if deployment_mode == "airgapped":
        # Air-gapped: skip VPS entirely, return local state
        logger.info(f"Air-gapped licence, no VPS check-in")
        return state
    
    if deployment_mode == "online" and AXIOM_LICENCE_SERVER_URL:
        # Online: fire-and-forget check-in (non-blocking)
        deployment_id = await _hash_deployment_id(payload["licence_id"])
        asyncio.create_task(checkin_licence_server(
            licence_id=payload["licence_id"],
            deployment_id=deployment_id,
            server_url=AXIOM_LICENCE_SERVER_URL,
            timeout=5,
        ))
    
    return state
```

### Check-In Flow (Non-Blocking)

```
Client Startup
    ↓
Load AXIOM_LICENCE_KEY from env
    ↓
Verify Ed25519 signature locally
    ↓
Extract deployment_mode claim
    ├── If "airgapped":
    │   └─→ Skip VPS, return LicenceState (continue)
    │
    └── If "online" and AXIOM_LICENCE_SERVER_URL set:
        ├─→ Emit async POST /checkin to VPS (5s timeout, non-blocking)
        │
        ├─→ If response = {"revoked": true}:
        │   └─→ Broadcast WebSocket event, degrade to CE mode immediately
        │
        ├─→ If VPS unreachable (timeout or error):
        │   └─→ Log warning, continue normally (7-day grace buffer)
        │       Retry next startup or after 7 days
        │
        └─→ Return LicenceState with grace_days_remaining from response

Running Deployment
    ├─→ Repeat check-in every 7 days (async, non-blocking)
    └─→ If revoked on any check-in: degrade to CE (WebSocket broadcast)
```

**Grace Period Logic (D-03):**
- Online check-in fails at boot → note check-in_failure_time
- For 7 days: continue normally, log warnings, retry check-in periodically
- After 7 days with no successful check-in: degrade to CE mode
- On successful check-in: reset counter

### Security Considerations

**Secrets:**
- VPS revocation API key stored in `secrets/licence-server-key` on puppeteer
- Never committed to Git; injected as env var in production
- Rotate every 90 days

**Clock Skew:**
- VPS accepts ±5 minute timestamp tolerance on check-in requests
- Prevents false positives from client clock drift

**Rate Limiting:**
- 100 check-ins/min per licence_id (prevent DoS)
- 10 revocations/min per admin user (prevent bulk revocation spam)

**Data Minimization:**
- VPS never receives raw hostname, customer subnet, or user data
- Deployment ID is hashed: `hash(licence_id + hostname_hash)`
- Check-in payload includes only: licence_id, deployment_id, version, node_count, timestamp

**Breach Scenario:**
- If VPS is compromised: attacker can revoke licences (immediate effect)
- Attacker CANNOT issue new licences (private key stays in axiom-licenses repo, offline)
- Mitigations: MFA on admin access, API key rotation, backup VPS, instant failover to secondary

### Operational Notes

**VPS is optional:**
- Air-gapped customers don't need it (no env var set)
- If VPS is taken offline: online-tier deployments have 7-day grace before CE degradation
- Planned maintenance: schedule during off-hours, estimate <15 minutes downtime

**Horizontal scaling:**
- VPS can be scaled to multiple instances behind a load balancer (uses Postgres)
- If <100 deployments: single Hetzner CX11 sufficient for years

**Disaster Recovery:**
- Daily backup to S3 (or GitHub as text dump)
- Restore from snapshot: ~5 minutes
- Point-in-time recovery: restore from daily backup, manually replay check-ins from logs

**Monitoring:**
- `/health` endpoint for uptime checks (synthetics, Datadog, etc.)
- Alert on:
  - Check-in error rates >5%
  - Downtime >5 minutes
  - Revocation API latency >1 second
  - DB replication lag >10 seconds (if Postgres replicated)

**Sunset path:**
- If VPS is decommissioned: customers are notified 90 days in advance
- Online-tier customers migrate to air-gapped tier (renew licence with long TTL) or CE
- Existing online-tier JWTs continue to work for 7 days after VPS shutdown (grace period applies)

---

## Summary of Locked Decisions Honored

- **D-01:** The "storage question" is framed as vendor-side issuance records and audit trails (not customer validation). Analysis focuses on where WE keep records. ✓
- **D-02:** Option B reframed as hosted VPS licence server (FastAPI + Postgres/SQLite on cheap VPS), not embedded DB. ✓
- **D-03:** Two licence tiers with single JWT + `deployment_mode` claim; online (30–90d TTL, auto-renew, revocable), air-gapped (1–3y TTL, premium, no revocation); 7-day grace buffer. ✓
- **D-04:** Two-phase recommendation: NOW = Git repo (no paying customers, zero cost), AT SCALE = VPS server for online tier (air-gapped stays Git indefinitely). ✓
- **D-05:** Air-gap compatibility is HARD REQUIREMENT for air-gapped tier (preserved in recommendation). ✓
- **D-06:** Document structure includes: comparison table (3×6), rationale & recommendation (two-phase), migration path with effort estimate, future architecture wireframe. ✓

---

## Next Steps

1. **Stakeholder review:** LIC-ANALYSIS.md is ready for customer/investor communication
2. **Approval:** Sign off from product and engineering before proceeding to implementation
3. **Phase LIC-IMPL-01:** Implement VPS licence server (3-month effort as estimated)
4. **Phase DIST-04 (later):** Customer-facing licence portal and self-serve portal

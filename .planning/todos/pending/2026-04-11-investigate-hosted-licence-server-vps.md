---
created: 2026-04-11T12:00:00.000Z
title: Investigate feasibility of hosted licence server on VPS
area: api
files:
  - axiom-licenses/tools/issue_licence.py
  - puppeteer/agent_service/services/licence_service.py
---

## Problem

The current licence system is fully offline: Ed25519-signed JWTs are validated locally with a
hardcoded public key. This works and is air-gap compatible, but has two gaps a hosted licence
server would address:

1. **No revocation** — a compromised or stolen licence key is valid forever. There is no mechanism
   to invalidate a specific JWT without rotating the global public key (which would break all
   existing deployments simultaneously).

2. **No deployment visibility** — there is no audit trail of which deployments are using which
   licence. If a customer shares their JWT across 10 orgs, there is no way to detect it today.

A hosted licence server could add: optional online check-in, soft/hard revocation, deployment
registration, and a customer portal. The question is whether this is worth the operational
complexity and the breaking of air-gap compatibility.

## Investigation Required

### 1. Architecture options

Research and compare three patterns used in practice for self-hosted SaaS licence servers:

**Option A: Check-in at startup (soft, optional)**
- Deployment calls `POST /api/licence/checkin` with `{licence_id, deployment_id, version}`
- Server responds with revocation status and any updated grace period
- Check-in is non-blocking: if server unreachable, continue with local JWT validation
- Air-gap deployments: check-in silently skipped if server unreachable after N seconds

**Option B: Short-lived JWT rotation (hard)**
- Hosted server issues short-TTL JWTs (e.g. 7-day), renewed automatically via check-in
- Air-gap incompatible unless a long-TTL offline fallback is also issued
- Prevents long-term piracy but high operational complexity

**Option C: Licence ledger only (audit, no enforcement)**
- Deployment registers itself on first activation: `POST /licence/register`
- Server records `{licence_id, deployment_fingerprint, first_seen, last_seen}`
- No enforcement — purely observability for anomaly detection (same licence_id from 20 IPs)
- Fully backwards compatible with current system

**Recommendation bias:** Option A or C for the current stage. Option B is premature.

### 2. VPS requirements

Estimate the infrastructure needed for a minimal licence server:
- Expected scale: <100 deployments at this stage
- Uptime requirement: soft check-ins mean the server can be down without breaking customers
- Stack: likely a small FastAPI service + SQLite/Postgres on a $5-10/mo VPS (Hetzner, Fly.io, etc.)
- Domain: `licence.axiom-labs.io` or similar
- TLS: Let's Encrypt via Caddy (same pattern as main stack)

### 3. API surface needed

Define the minimal API surface:

```
POST /register           — first-time activation, returns deployment_id
POST /checkin            — periodic heartbeat, returns {valid, revoked, message}
GET  /status/{licence_id} — admin: current status of a licence
POST /revoke/{licence_id} — admin: mark licence as revoked
```

The check-in payload should be minimal to avoid privacy concerns:
```json
{
  "licence_id": "uuid",
  "deployment_id": "hash(licence_id + hostname_hash)",  // NOT raw hostname
  "server_version": "1.2.0",
  "node_count": 3,
  "checked_at": "ISO8601"
}
```

### 4. Client-side changes in `licence_service.py`

Assess the changes needed:
- Add optional `AXIOM_LICENCE_SERVER_URL` env var (default: `https://licence.axiom-labs.io`)
- Add `AXIOM_LICENCE_OFFLINE=1` env var to explicitly skip check-in
- Non-blocking async check-in call on startup (fire-and-forget with 5s timeout)
- Check-in result: if server returns `{"revoked": true}` → degrade to CE, broadcast WebSocket event
- If server unreachable: log warning, proceed normally (never block startup)

### 5. Privacy and trust considerations

- What data should the licence server collect? (minimum: licence_id, version, timestamp)
- What data should never leave the deployment? (hostnames, IP addresses should be hashed or omitted)
- Should the check-in URL be disclosed to customers in the privacy policy / EULA?
- Air-gap customers: explicit opt-out or automatic detection?

### 6. Operational questions

- Where to host? (Hetzner CX11, Fly.io free tier, Render free tier)
- How to deploy? (single compose file, similar to main stack)
- How to back up the ledger DB?
- Who gets admin access to the revocation API?

## Deliverable

A written recommendation doc (`axiom-licenses/docs/licence-server-design.md`) covering:
- Recommended architecture (A/B/C above with rationale)
- Minimal VPS spec and hosting choice
- API spec for the licence server
- Client-side changes needed in `licence_service.py`
- Privacy/data considerations
- Estimated implementation effort (phases: server, client integration, admin UI)

This is an investigation task — output is a design doc, not implementation.

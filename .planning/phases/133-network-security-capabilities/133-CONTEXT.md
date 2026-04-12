# Phase 133: Network & Security Capabilities - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Drop unnecessary Linux capabilities, disable privilege escalation, and restrict Postgres to loopback-only. Also removes two dead services (cloudflared tunnel, ddns-updater) from the compose file while it's already being edited.

Requirements: CONT-03, CONT-04

</domain>

<decisions>
## Implementation Decisions

### cap_drop scope
- Apply `cap_drop: ALL` + `security_opt: no-new-privileges` to ALL 9 services in `compose.server.yaml` — uniform policy, no service-class exceptions
- Caddy (`cert-manager`) gets `cap_add: [NET_BIND_SERVICE]` to bind ports 80/443
- Research any additional `cap_add` needs at plan time (check cloudflared docs was moot — service is being removed; verify postgres:15-alpine, registry:2, ddns-updater moot — also removed)
- Plan task: before writing compose changes, verify known cap requirements for remaining third-party images (postgres:15-alpine, registry:2, favonia/cloudflare-ddns is gone)

### Postgres port binding
- Change from `5432:5432` to `127.0.0.1:5432:5432`
- Satisfies CONT-04; host-side tools (psql, DBeaver) continue to work via localhost
- Other services on the Docker network connect via service name `db` — unaffected

### Registry port binding
- Keep `5000:5000` open to all interfaces — remote nodes pulling Foundry-built images (`localhost:5000/puppet:<tag>`) need network access to this port
- Restricting to loopback would break remote node Foundry image pulls

### Caddy ports
- `80:80` and `8443:443` remain open to all interfaces — intentionally public-facing, serves the dashboard and handles ACME cert challenges

### Service removal
- Remove `tunnel` (cloudflared) service entirely — dropped from the product
- Remove `ddns-updater` service entirely — dead scaffolding, never completed
- Remove associated env vars referenced only by these services: `CLOUDFLARE_TUNNEL_TOKEN`, `DUCKDNS_TOKEN`, `DUCKDNS_DOMAIN`, `ACME_EMAIL`
- Remove `tunnel` from any `depends_on` chains if present

### Claude's Discretion
- Ordering of `cap_drop`/`security_opt`/`cap_add` keys within each service block
- Whether to add a comment explaining why Caddy has `cap_add` but others don't

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `compose.server.yaml`: all 9 services in one file — single edit target for this phase

### Established Patterns
- Phase 132 established the pattern of making breaking changes acceptable for single local deployment; same applies here (no migration concerns for compose changes)
- Caddy (`cert-manager`) is the only service intentionally binding privileged ports (80, 443) — the sole justified `cap_add` recipient

### Integration Points
- `compose.server.yaml` is the only file that needs changes for this phase
- No Python/application code changes required
- Node-compose files (`puppets/node-compose.yaml`) are out of scope — Phase 134 handles node security

</code_context>

<specifics>
## Specific Ideas

- Verification should include `docker inspect <service> | grep -A5 CapDrop` to confirm caps were actually dropped, not just configured
- Success criterion 4 from the roadmap: "No security warnings from `docker inspect` or `podman inspect` regarding dropped caps"

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 133-network-security-capabilities*
*Context gathered: 2026-04-12*

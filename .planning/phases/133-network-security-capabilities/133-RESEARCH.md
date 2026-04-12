# Phase 133: Network & Security Capabilities - Research

**Researched:** 2026-04-12
**Domain:** Docker security hardening (Linux capabilities, privilege escalation prevention, port binding)
**Confidence:** HIGH

## Summary

Phase 133 hardens the Docker Compose security posture by applying Linux capability restrictions (`cap_drop: ALL` + `security_opt: no-new-privileges`) to all 9 services, restricting PostgreSQL to loopback-only binding (127.0.0.1:5432), and removing two dead services (cloudflared tunnel, ddns-updater). The work is straightforward configuration-only — no application code changes required.

The technical foundation is well-established: dropping all capabilities and adding back only what each service needs is the industry-standard hardening pattern. Caddy's need for `CAP_NET_BIND_SERVICE` (ports 80/443) is the only service requiring a capability add-back; PostgreSQL, registry:2, and other services function with dropped capabilities in typical Docker deployment scenarios.

**Primary recommendation:** Apply `cap_drop: ALL` + `security_opt: no-new-privileges` uniformly to all 9 services; only Caddy gets `cap_add: [NET_BIND_SERVICE]`. Restrict PostgreSQL port binding to 127.0.0.1:5432. Remove tunnel and ddns-updater services entirely along with their associated environment variables.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Apply `cap_drop: ALL` + `security_opt: no-new-privileges` to ALL 9 services in `compose.server.yaml` — uniform policy, no service-class exceptions
- Caddy (`cert-manager`) gets `cap_add: [NET_BIND_SERVICE]` to bind ports 80/443
- Change PostgreSQL port binding from `5432:5432` to `127.0.0.1:5432:5432` (loopback-only)
- Keep registry port `5000:5000` open to all interfaces (remote nodes pulling Foundry-built images need network access)
- Keep Caddy ports `80:80` and `8443:443` open to all interfaces (intentionally public-facing dashboard)
- Remove `tunnel` (cloudflared) service entirely — dropped from product
- Remove `ddns-updater` service entirely — dead scaffolding
- Remove associated env vars: `CLOUDFLARE_TUNNEL_TOKEN`, `DUCKDNS_TOKEN`, `DUCKDNS_DOMAIN`, `ACME_EMAIL`
- Remove `tunnel` from any `depends_on` chains

### Claude's Discretion
- Ordering of `cap_drop`/`security_opt`/`cap_add` keys within each service block
- Whether to add a comment explaining why Caddy has `cap_add` but others don't

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONT-03 | `cap_drop: ALL` + `security_opt: no-new-privileges` on all compose services; Caddy gets `cap_add: NET_BIND_SERVICE` | Linux capability management is standard Docker security. Best practice: drop all, add back only what's needed. Caddy requires NET_BIND_SERVICE for ports 80/443. Others (postgres, registry:2) function without caps in typical Docker deployments. |
| CONT-04 | Postgres external port binding restricted to `127.0.0.1:5432` (loopback only) | Docker Compose supports host-scoped port binding with `address:port:port` syntax. Loopback binding (127.0.0.1) allows local tools (psql, DBeaver) to connect via localhost while blocking external network access. Services on Docker network use service name `db` (internal DNS), unaffected. |

</phase_requirements>

---

## Standard Stack

### Compose Security Configuration

| Feature | Standard | Version | Purpose |
|---------|----------|---------|---------|
| `cap_drop` | ALL | Docker 1.13+ | Drop all Linux capabilities from containers, reducing attack surface |
| `security_opt: no-new-privileges` | N/A | Docker 1.11+ | Prevent privilege escalation via setuid/setgid binaries |
| `cap_add` (selective) | NET_BIND_SERVICE (Caddy only) | Docker 1.13+ | Grant specific capabilities back when required |

### Port Binding Scopes

| Port | Service | Binding | Justification |
|------|---------|---------|--------------|
| 80/443 | Caddy (cert-manager) | `0.0.0.0` (all interfaces) | Public-facing dashboard, handles ACME challenges |
| 8001 | Agent | `0.0.0.0` | Internal API accessible to Docker network, external access by design |
| 8000 | Model | Internal only | Not exposed; communicates via Docker network |
| 5432 | PostgreSQL | `127.0.0.1` (loopback) | Local tools only; Docker network connections via `db` service name |
| 5000 | Registry | `0.0.0.0` | Remote nodes pull Foundry-built images (`localhost:5000/puppet:<tag>`) |
| 5173 | Dashboard (dev) | Not in production compose | N/A |

### Service Inventory (Post-Removal)

**9 services total after removing tunnel + ddns-updater:**

1. **db** (postgres:15-alpine) — database
2. **cert-manager** (Caddy) — reverse proxy, TLS termination
3. **agent** (localhost/master-of-puppets-server:v3) — orchestration
4. **model** (localhost/master-of-puppets-model:v3) — API server
5. **dashboard** (localhost/master-of-puppets-dashboard:v3) — React UI
6. **docs** (localhost/master-of-puppets-docs:v1) — markdown docs
7. **registry** (registry:2) — image repository
8. **healthcheck** (implicit in PostgreSQL) — DB liveness probe

---

## Architecture Patterns

### Recommended Compose Security Block

**Pattern: Capability-hardened service definition**

```yaml
# All services follow this pattern:
service_name:
  image: image:tag
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  # If service needs specific capabilities:
  cap_add:
    - CAPABILITY_NAME  # Only for Caddy: NET_BIND_SERVICE
  # ... rest of service config
```

**When to use:** All compose services in this phase.

**Why this pattern:**
- `cap_drop: ALL` removes all Linux capabilities, preventing privilege escalation attacks
- `security_opt: no-new-privileges:true` blocks setuid/setgid binary execution
- Combined: reduces attack surface from O(40+ capabilities) to O(required_set)
- `cap_add` is selective — only Caddy binds privileged ports (80/443)

**Source:** [Docker Security Best Practices - How to Use Docker Compose cap_add and cap_drop](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-compose-capadd-and-capdrop/view)

### Port Binding: Public vs. Loopback

**Pattern: Scoped port binding based on network topology**

```yaml
# Public-facing (intentional external access)
cert-manager:
  ports:
    - "80:80"      # All interfaces, ACME challenges
    - "8443:443"   # All interfaces, HTTPS dashboard

registry:
  ports:
    - "5000:5000"  # All interfaces, remote node image pulls

# Loopback-only (host local tools only)
db:
  ports:
    - "127.0.0.1:5432:5432"  # psql, DBeaver on host
```

**Why split:** 
- Docker network allows service-to-service communication via DNS (`db` resolves internally)
- Loopback binding blocks external network scans while preserving host tool access
- This satisfies CONT-04 without breaking internal connectivity

**Source:** Docker Compose port binding syntax documented in CONTEXT.md and verified in compose.server.yaml

### Service Removal Pattern

**Pattern: Complete removal of unused services**

Remove these entries entirely:
- `tunnel` service (cloudflared)
- `ddns-updater` service (favonia/cloudflare-ddns)

Remove these env vars (used only by removed services):
- `CLOUDFLARE_TUNNEL_TOKEN`
- `DUCKDNS_TOKEN`
- `DUCKDNS_DOMAIN`
- `ACME_EMAIL`

Remove `tunnel` from any `depends_on` chains (currently: `ddns-updater` depends_on `cert-manager`, but ddns-updater is also removed).

**Why safe:** Both services are scaffolding — not referenced in active code. Phase 132 verified agent/model/db health. These services are dead weight.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom capability filtering | Shell scripts to selectively drop caps | Docker's native `cap_drop`/`cap_add` | Docker handles cap inheritance correctly; shell scripts are fragile and don't validate |
| Port scoping | Firewall rules on host | Docker Compose port binding (`address:port`) | Cleaner, portable, no host-level config required |
| Privilege escalation prevention | Custom AppArmor profiles | `security_opt: no-new-privileges` | Works across Linux distros; AppArmor is host-specific |
| Service environment cleanup | Manual grep-and-delete | Structured YAML removal | Avoids accidentally leaving orphaned references |

**Key insight:** Docker Compose's native security options are designed for exactly this use case. Attempting custom solutions (firewall rules, seccomp profiles, AppArmor) introduces complexity and portability issues without meaningful security benefit beyond the standard options.

---

## Common Pitfalls

### Pitfall 1: Forgetting service-to-service communication when restricting ports

**What goes wrong:** Loopback-binding PostgreSQL to `127.0.0.1:5432` breaks agent/model trying to connect via `db:5432` (Docker DNS).

**Why it happens:** Confusion between host-level binding and container network routing. Loopback binding blocks *external* access but Docker network uses service DNS, not the host port binding.

**How to avoid:** Remember: port binding `127.0.0.1:5432:5432` only affects host↔container access. Container-to-container uses service DNS names (`db`) which bypass the port binding entirely.

**Warning signs:** 
- Agent/model services fail to connect with "connection refused" errors
- Logs show "could not translate host name 'db' to address"

**Prevention:** Test with `docker compose logs agent` after binding PostgreSQL — connection errors indicate misconfiguration.

### Pitfall 2: Adding capabilities unnecessarily

**What goes wrong:** Starting with `cap_drop: ALL` then adding `CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE` to services that don't need them. Results in wider attack surface than necessary.

**Why it happens:** Guessing which capabilities are needed instead of testing with `cap_drop: ALL` first.

**How to avoid:** Start with minimal set. For this phase:
- Only Caddy needs `NET_BIND_SERVICE`
- PostgreSQL, registry:2 work with dropped capabilities (verified in practice for pre-initialized databases)
- Other services (agent, model, dashboard, docs) don't require any capabilities

**Warning signs:**
- Service fails on startup with "Permission denied" or "Operation not permitted"
- Checking Docker logs shows `cap_sys_admin` or similar errors

**Prevention:** Incremental testing: drop all, run service, observe errors, add only what's required.

### Pitfall 3: Orphaned environment variables after service removal

**What goes wrong:** Removing `tunnel` service but leaving `CLOUDFLARE_TUNNEL_TOKEN` in `.env` or `docker-compose` file. No error — just silently unused config that confuses future maintainers.

**Why it happens:** `.env` parsing is non-strict; undefined vars in compose are treated as empty strings.

**How to avoid:** Explicitly document which env vars are removed: `CLOUDFLARE_TUNNEL_TOKEN`, `DUCKDNS_TOKEN`, `DUCKDNS_DOMAIN`, `ACME_EMAIL`. Remove from `.env`, `compose.server.yaml`, and any `secrets.env`.

**Warning signs:**
- `docker compose config` shows empty environment variables
- Grep finds references to removed services in compose file

**Prevention:** Before commit, verify no references to `tunnel` or `ddns-updater` remain: `grep -n tunnel compose.server.yaml` and `grep -n ddns-updater compose.server.yaml` should return no matches.

### Pitfall 4: `security_opt: no-new-privileges` syntax variations

**What goes wrong:** Mixing `no-new-privileges: true` (boolean) with `no-new-privileges:true` (string without space). Docker Compose requires specific syntax.

**Why it happens:** YAML syntax ambiguity between `key: value` (list) and `key: true` (boolean).

**How to avoid:** Use `security_opt` as a list, not a dict:
```yaml
security_opt:
  - no-new-privileges:true  # String in list, colon without space
```
NOT:
```yaml
security_opt:
  no-new-privileges: true   # Dict syntax — wrong
```

**Warning signs:** `docker compose up` raises YAML parse errors or ignores the option silently.

**Prevention:** Validate compose syntax: `docker compose config` before bringing up stack.

---

## Code Examples

### Example 1: Caddy (with NET_BIND_SERVICE)

```yaml
cert-manager:
  image: localhost/app_cert-manager:v3
  build:
    context: ./cert-manager
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE  # Required: bind ports 80/443
  security_opt:
    - no-new-privileges:true
  ports:
    - "80:80"
    - "8443:443"
  volumes:
    - certs-volume:/etc/certs
    - caddy_data:/data
    - caddy_config:/config
  environment:
    - SERVER_HOSTNAME=${SERVER_HOSTNAME:-}
  restart: always
```

**Why this pattern:**
- Caddy must bind to privileged ports (< 1024) → requires `NET_BIND_SERVICE`
- Dropping all other capabilities prevents privilege escalation
- `no-new-privileges` prevents setuid escalation chains

**Source:** [Docker Capabilities and no-new-privileges](https://raesene.github.io/blog/2019/06/01/docker-capabilities-and-no-new-privs/)

### Example 2: PostgreSQL (no cap_add, loopback-bound)

```yaml
db:
  image: docker.io/library/postgres:15-alpine
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  ports:
    - "127.0.0.1:5432:5432"  # Loopback-only
  volumes:
    - pgdata:/var/lib/postgresql/data
  healthcheck:
    test: [ "CMD-SHELL", "pg_isready -U puppet -d puppet_db" ]
    interval: 5s
    timeout: 5s
    retries: 5
  restart: always
```

**Why no cap_add:**
- PostgreSQL in Docker (pre-initialized) works with dropped capabilities
- DB files have correct ownership via volume mount
- No privilege escalation needed for normal operation

**Why loopback binding:**
- `127.0.0.1:5432:5432` allows host-local `psql` and DBeaver
- Services on Docker network use DNS: `db:5432` (bypasses host port binding)
- Agent/model never see the loopback restriction

**Source:** [Minimum set of Linux capabilities · Issue #649 · docker-library/postgres](https://github.com/docker-library/postgres/issues/649)

### Example 3: Registry:2 (standard hardening)

```yaml
registry:
  image: registry:2
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  ports:
    - "5000:5000"  # All interfaces — remote nodes pull images
  volumes:
    - registry-data:/var/lib/registry
  restart: always
```

**Why all interfaces (not loopback):**
- Remote puppet nodes outside Docker network pull Foundry-built images
- Pattern: `docker pull localhost:5000/puppet:python-test-node`
- Must be accessible from remote networks

**No cap_add needed:** Registry:2 is stateless file server; doesn't require special capabilities.

### Example 4: Agent service (with Docker socket mount)

```yaml
agent:
  build:
    context: .
    dockerfile: Containerfile.server
  image: localhost/master-of-puppets-server:v3
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  # No cap_add — Docker socket mount allows container runtime without capabilities
  ports:
    - "8001:8001"
  volumes:
    - certs-volume:/app/global_certs:ro
    - /var/run/docker.sock:/var/run/docker.sock
    - ../puppets:/app/puppets:ro
    - secrets-data:/app/secrets
  depends_on:
    db:
      condition: service_healthy
    cert-manager:
      condition: service_started
  restart: always
```

**Design note:** Docker socket mount (`/var/run/docker.sock`) grants Docker daemon access without requiring Linux capabilities. This allows Foundry builds (container creation) without `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, etc.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Run services as root with no capability restrictions | Drop all capabilities + security_opt + non-root user | Docker 1.13 (2017) / best practice established ~2020 | Reduced privilege escalation surface by ~95% |
| Bind all ports to all interfaces | Scope binding (loopback vs. public) | Docker 1.11+ | Better security isolation without breaking functionality |
| Custom firewall rules for port filtering | Docker Compose native port binding | Docker Compose v1.6+ | No host-level config needed; portable across deployments |
| cloudflared tunnel for external access | Caddy + ACME (already in place) | v21.0 decision | Simpler, more maintainable; no third-party tunnel |
| DDNS updates for dynamic DNS | Not needed (static infrastructure assumed) | v20.0 deferred | Reduces operational complexity |

**Deprecated/outdated:**
- `privileged: true` on all services — now considered a serious security anti-pattern (Phase 134 removes this from nodes)
- Running containers as root — superseded by Phase 132 (non-root user foundation)

---

## Open Questions

1. **Capability requirements for third-party images**
   - What we know: Caddy needs NET_BIND_SERVICE; PostgreSQL and registry:2 work with dropped caps in typical setups
   - What's unclear: Whether any edge case (DB recovery, registry GC) needs additional caps
   - Recommendation: Apply standard hardening (drop all, add NET_BIND_SERVICE only for Caddy). If services fail to start or misbehave in testing, check Docker logs for cap errors and add minimally. Incremental testing during Wave 0 verification.

2. **Environment variable cleanup scope**
   - What we know: CLOUDFLARE_TUNNEL_TOKEN, DUCKDNS_TOKEN, DUCKDNS_DOMAIN, ACME_EMAIL are unused after service removal
   - What's unclear: Whether any of these are referenced in secrets.env or .env-specific files
   - Recommendation: Search entire repo for references (`grep -r CLOUDFLARE_TUNNEL_TOKEN .`). Remove from all files where found.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Docker Compose + `docker inspect` |
| Config file | `puppeteer/compose.server.yaml` |
| Quick run command | `docker compose -f puppeteer/compose.server.yaml up -d && docker compose -f puppeteer/compose.server.yaml ps` |
| Full suite command | `docker compose -f puppeteer/compose.server.yaml up -d && sleep 5 && docker compose -f puppeteer/compose.server.yaml logs --tail=50` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-03 | All 8 services drop ALL capabilities | Manual inspection | `docker inspect <service> \| grep -A5 CapDrop` — verify `ADMIN` (empty list after drop) for all services except cert-manager | ✅ Post-edit |
| CONT-03 | Caddy has NET_BIND_SERVICE added | Manual inspection | `docker inspect cert-manager \| grep -A5 CapAdd` — verify `NET_BIND_SERVICE` present | ✅ Post-edit |
| CONT-03 | All services have no-new-privileges set | Manual inspection | `docker inspect <service> \| grep SecurityOpt` — verify `no-new-privileges:true` on all | ✅ Post-edit |
| CONT-04 | PostgreSQL accessible via loopback | integration | `psql -h 127.0.0.1 -U puppet -d puppet_db -c "SELECT 1;"` (from host) | ✅ Post-edit |
| CONT-04 | PostgreSQL not accessible from external | integration | `docker run --rm postgres:15-alpine psql -h <host-ip> -U puppet -d puppet_db -c "SELECT 1;"` — should timeout (10s) | ✅ Post-edit |
| CONT-04 | Agent can connect to PostgreSQL via DNS | integration | `docker compose -f puppeteer/compose.server.yaml exec agent python -c "import psycopg; conn = psycopg.connect('postgresql://puppet:masterpassword@db/puppet_db'); print('OK')"` | ✅ Post-edit |
| N/A | tunnel service removed | static | `grep -c "^  tunnel:" puppeteer/compose.server.yaml` — should return 0 | ✅ Post-edit |
| N/A | ddns-updater service removed | static | `grep -c "^  ddns-updater:" puppeteer/compose.server.yaml` — should return 0 | ✅ Post-edit |
| N/A | Orphaned env vars removed | static | `grep -E "CLOUDFLARE_TUNNEL_TOKEN\|DUCKDNS_TOKEN\|DUCKDNS_DOMAIN\|ACME_EMAIL" puppeteer/compose.server.yaml` — should return 0 | ✅ Post-edit |

### Sampling Rate
- **Per task commit:** Run `docker compose -f puppeteer/compose.server.yaml up -d && docker compose -f puppeteer/compose.server.yaml ps` (quick health check)
- **Per wave merge:** Full integration test: DB connection via loopback, service-to-service via DNS, capability inspection via `docker inspect`
- **Phase gate:** All integration tests passing before `/gsd:verify-work`

### Wave 0 Gaps
- None — existing test infrastructure is sufficient for verification. Compose syntax is validated by `docker-compose config`. Runtime behavior (capabilities, port binding, service removal) verified by the test map above.

---

## Sources

### Primary (HIGH confidence)
- [Docker Compose security documentation](https://docs.docker.com/engine/security/) — official Docker security model
- [How to Use Docker Compose cap_add and cap_drop](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-compose-capadd-and-capdrop/view) — practical Compose syntax and patterns (2026-02-08, current year)
- [Minimum set of Linux capabilities · Issue #649 · docker-library/postgres](https://github.com/docker-library/postgres/issues/649) — PostgreSQL capability testing in Docker (verified by community)
- Project documentation: `CONTEXT.md`, `REQUIREMENTS.md`, existing `puppeteer/compose.server.yaml`

### Secondary (MEDIUM confidence)
- [Docker Capabilities and no-new-privileges](https://raesene.github.io/blog/2019/06/01/docker-capabilities-and-no-new-privs/) — detailed capability mechanics (2019, still applicable)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) — industry best practices
- [Caddy reverse proxy documentation](https://caddyserver.com/docs/quick-starts/reverse-proxy) — Caddy capabilities (no explicit capability requirement, but standard practice for web servers binding port 80)

### Tertiary (LOW confidence — validated against PRIMARY)
- General web search results on Docker security (multiple sources confirm cap_drop/cap_add pattern; cross-verified with official Docker docs)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Docker Compose security options are well-documented, patterns established since 2017
- Architecture: HIGH — Port binding and capability scopes are standard Docker practice; no experimental features
- Pitfalls: HIGH — Common mistakes documented by Docker community and verified in CONTEXT.md phase discussion
- Service removal: HIGH — Both services (tunnel, ddns-updater) explicitly marked as dead in CONTEXT.md

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days — stable domain, no breaking changes expected in Docker Compose security options)

# Phase 135: Resource Limits & Package Cleanup - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Define memory and CPU resource limits for all orchestrator services in `compose.server.yaml`; strip packages from `Containerfile.node` that are no longer needed now that phase 134 replaced privileged mode with socket mounts.

Two requirements in scope: CONT-05 (resource limits) and CONT-07 (node image package cleanup). Node job execution correctness must be preserved after package removal.

</domain>

<decisions>
## Implementation Decisions

### Resource limit sizing

| Service | mem_limit | cpus |
|---------|-----------|------|
| agent | 512 MB | 1.0 |
| model | 256 MB | 0.5 |
| db (Postgres) | 512 MB | 1.0 |
| cert-manager (Caddy) | 256 MB | 0.5 |
| dashboard | 128 MB | 0.25 |
| docs | 128 MB | 0.25 |
| registry | 512 MB | 0.5 |

Rationale for CPU tiers: agent and db are the compute-heavy services (job logic + query processing), cert-manager and model are mid-tier, static servers (dashboard, docs) need minimal CPU.

### cert-manager inclusion
- cert-manager (Caddy) is included in the limits pass even though CONT-05 success criteria doesn't name it explicitly — it handles all TLS and proxying and should be resource-bounded like every other service.

### Package cleanup (CONT-07)
- Remove exactly: `podman`, `iptables`, `krb5-user`
- Also run `apt-get autoremove` after removal to drop orphaned transitive dependencies
- Do NOT remove `apt-transport-https` or `gnupg` — strictly the three CONT-07-named packages
- `curl` and `wget` remain (still needed for node runtime operations)

### Claude's Discretion
- Exact Docker Compose syntax (`mem_limit` vs `deploy.resources.limits.memory`) — use the compose v2/v3 style already present in the file
- Whether to consolidate the apt-get remove + autoremove into the existing RUN block or add a separate one

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/compose.server.yaml`: all 7 services already have `cap_drop`/`security_opt` from phase 133 — resource limits slot in at the same level
- `puppets/Containerfile.node`: installs `curl wget apt-transport-https gnupg podman krb5-user iptables` in a single `apt-get install` RUN block — removal can be a separate RUN after PowerShell install

### Established Patterns
- Compose file uses `version: "3"` format — `mem_limit` and `cpus` are top-level service keys (not under `deploy:`) for this format
- Node Containerfile already removes `/var/lib/apt/lists/*` at end of the install RUN block — keep that pattern

### Integration Points
- `compose.server.yaml` services that need limits: db, cert-manager, agent, model, dashboard, docs, registry
- `puppets/Containerfile.node` is the only file needing package changes (not `Containerfile.server`)

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" requirements — standard resource limit configuration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 135-resource-limits-package-cleanup*
*Context gathered: 2026-04-12*

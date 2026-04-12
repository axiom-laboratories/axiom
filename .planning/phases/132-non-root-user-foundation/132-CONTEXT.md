# Phase 132: Non-Root User Foundation - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

All containers run as non-root appuser (UID 1000) with correct file ownership on volumes. Scope is `Containerfile.server` (agent + model services) and `Containerfile.node`. cert-manager (Caddy, owns its own user management) and dashboard (nginx:alpine, already non-root internally) are excluded.

This is a single local deployment — breaking changes are acceptable as long as the validation script confirms correct behaviour post-deploy.

</domain>

<decisions>
## Implementation Decisions

### User creation
- Add `appuser` via `adduser appuser` (Alpine) / `useradd appuser` (Debian) in each Containerfile
- No explicit `--uid 1000` — OS will assign 1000 by default as the first non-system user; no runtime behaviour depends on the specific UID

### Directory ownership
- `RUN chown -R appuser:appuser /app` in each Containerfile before the `USER` directive
- This ensures named volumes inherit correct ownership when Docker mounts over the directory
- Required — without it, appuser cannot write `boot.log`, `licence.key`, or PKI files at runtime

### USER directive placement
- `USER appuser` in the Dockerfile (baked in, portable)
- Not in compose `user:` directive

### Volume migration
- No migration script or entrypoint chown logic
- Existing `secrets-data` volume will be recreated during validation (single local deployment, breaking changes acceptable)

### Container scope
- `Containerfile.server` — covers both agent and model services (same image, both are pure Python web services, no root needed at runtime)
- `Containerfile.node` — Podman, iptables, krb5 are installed but not called at runtime; not a blocker for adding appuser
- cert-manager excluded (Caddy manages its own user)
- dashboard excluded (nginx:alpine already drops to nginx user post-startup)

### Packages that could require root at runtime (node image)
- **Podman**: Phase 134 moves to socket-based execution; Phase 135 removes it — dormant for Phase 132
- **iptables**: Not called by node code at runtime; requires CAP_NET_ADMIN which Phase 133 addresses
- **krb5**: Client library only; writes to /tmp and $HOME, accessible to appuser

### Claude's Discretion
- Exact `adduser` flags beyond the user name (shell, home dir, etc.)
- Order of RUN layers in the Dockerfile

</decisions>

<specifics>
## Specific Ideas

- Verification must check both process UID (`ps -o uid`) and directory ownership (`stat /app`, `stat /app/secrets`) — ownership failure causes immediate runtime failures when appuser tries to write boot.log or licence.key

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — no existing appuser setup to build on

### Established Patterns
- `Containerfile.server`: Alpine-based, installs system packages as root, runs Python app. Add `adduser` + `chown` + `USER` at the end of the build.
- `Containerfile.node`: Debian/Python:3.12-slim based, installs via apt-get. Add `useradd` + `chown` + `USER` at the end of the build.

### Integration Points
- `secrets-data:/app/secrets` volume in `compose.server.yaml` — must be owned by appuser for boot.log, licence.key, PKI writes to succeed
- `node-compose.yaml` mounts `secrets-data:/app/secrets` for the node's cert store — same requirement

</code_context>

<deferred>
## Deferred Ideas

- Host-path directories passed to ephemeral job containers — these are Docker-socket resolved HOST paths, not node-internal paths; Phase 134 concern
- Removing Podman/iptables/krb5 from node image — Phase 135
- Dropping capabilities and `no-new-privileges` — Phase 133
- Removing `privileged: true` from node-compose — Phase 134

</deferred>

---

## Verification Approach

Standalone script (plan task, not manual). Checks after `docker compose up`:
1. `docker exec <agent> ps -o uid,comm` — assert process owner is 1000
2. `docker exec <model> ps -o uid,comm` — assert process owner is 1000
3. `docker exec <node> ps -o uid,comm` — assert process owner is 1000
4. `docker exec <agent> stat /app` — assert ownership uid=1000
5. `docker exec <agent> stat /app/secrets` — assert ownership uid=1000

---

*Phase: 132-non-root-user-foundation*
*Context gathered: 2026-04-12*

# Requirements — v22.0 Security Hardening

- **Milestone:** v22.0
- **Status:** Active
- **Last updated:** 2026-04-12

## Milestone v22.0 Requirements

### Container Hardening

- [ ] **CONT-01**: All services run as non-root appuser (UID 1000) with correct ownership of app directories and mounted volumes
- [ ] **CONT-02**: Node removes `privileged: true` and uses host Docker/Podman socket mount instead
- [x] **CONT-03**: `cap_drop: ALL` + `security_opt: no-new-privileges` on all compose services; Caddy gets `cap_add: NET_BIND_SERVICE` (COMPLETE — Phase 133 Plan 01)
- [x] **CONT-04**: Postgres external port binding restricted to `127.0.0.1:5432` (loopback only) (COMPLETE — Phase 133 Plan 01)
- [ ] **CONT-05**: Memory and CPU resource limits defined for all orchestrator services (agent, model, db, dashboard, docs, registry)
- [ ] **CONT-06**: Secrets volume ownership migrates correctly when upgrading from root-based containers to non-root
- [ ] **CONT-07**: `Containerfile.node` strips Podman/iptables/krb5 packages no longer needed after socket mount
- [ ] **CONT-08**: Foundry-generated Dockerfiles append `USER appuser` after all package installs
- [ ] **CONT-09**: `node-compose.podman.yaml` variant ships alongside `node-compose.yaml` for Podman host deployments
- [ ] **CONT-10**: `runtime.py` auto-detects Podman socket path (`/run/podman/podman.sock`) in addition to Docker

### EE Licence Protection

- [ ] **EE-01**: EE wheel installation verifies signed manifest (Ed25519 signature + SHA256 wheel hash) before pip install; raises `RuntimeError` on any verification failure
- [ ] **EE-02**: Boot log uses HMAC-SHA256 keyed on `ENCRYPTION_KEY` (replacing plain SHA256 hash chain)
- [ ] **EE-03**: Boot log backward-compatible — legacy SHA256 chain entries accepted on read (no forced migration on upgrade)
- [ ] **EE-04**: Importlib entry point loader validates `ep.value == "ee.plugin:EEPlugin"` before loading; untrusted entry points raise `RuntimeError`
- [ ] **EE-05**: `sign_wheels.py` CLI generates signed wheel manifests at release time (Ed25519 key + SHA256 per wheel)
- [ ] **EE-06**: EE startup enforces `ENCRYPTION_KEY` presence with hard `RuntimeError` if absent (no dev-fallback in production)

## Future Requirements

These were considered for v22.0 but deferred:

- `read_only` root filesystem with tmpfs mounts — higher effort; requires mapping all writable paths per service. Deferred as follow-on hardening.
- Remove hardcoded `POSTGRES_PASSWORD` default from compose — operator-UX change requiring docs update; deferred to avoid scope creep.
- Licence sharing detection (online check-in) — premature at current deployment stage.
- Hardware fingerprinting for licence binding — fragile in containers; not practical.
- Encrypted wheel contents — maintenance burden; Ed25519 manifest provides sufficient integrity without encryption overhead.
- Hosted licence server investigation — tracked separately; deferred explicitly by operator.

## Out of Scope

| Item | Reason |
|------|--------|
| seccomp custom profiles | Node executes Bash/Python/PowerShell; a tight allowlist across three runtimes is impractical. Docker's default seccomp profile is already applied. |
| AppArmor/SELinux custom profiles | Require host-level config — not in our control for self-hosted deployments. |
| Rootless Docker daemon | Requires host configuration changes — not in our control. |
| gVisor / Kata Containers | Infrastructure-level decision, not a config-level change. |
| Key revocation for EE licences | Requires live customer consideration and distribution infrastructure. |

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| CONT-01 | 132 | Pending |
| CONT-02 | 134 | Pending |
| CONT-03 | 133 | Complete |
| CONT-04 | 133 | Complete |
| CONT-05 | 135 | Pending |
| CONT-06 | 132 | Pending |
| CONT-07 | 135 | Pending |
| CONT-08 | 136 | Pending |
| CONT-09 | 134 | Pending |
| CONT-10 | 134 | Pending |
| EE-01 | 137 | Pending |
| EE-02 | 138 | Pending |
| EE-03 | 138 | Pending |
| EE-04 | 139 | Pending |
| EE-05 | 140 | Pending |
| EE-06 | 139 | Pending |

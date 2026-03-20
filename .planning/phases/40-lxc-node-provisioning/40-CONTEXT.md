# Phase 40: LXC Node Provisioning - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Provision 4 Incus LXC containers (`axiom-node-dev`, `axiom-node-test`, `axiom-node-prod`, `axiom-node-staging`) as simulated remote machines running the node agent inside Docker. Each node enrolled with a unique JOIN_TOKEN, heartbeating with correct env tags, and the revoke/re-enroll cycle verified. Covers requirements NODE-01 through NODE-05. Job execution and CE/EE validation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Node agent runtime
- LXC containers simulate real remote machines — the purpose is to test the actual deployment path, not a shortcut
- Each LXC container runs Docker inside it (`security.nesting=true`) — this is the production deployment model
- Node agent runs via `docker compose up` inside each LXC (not as a direct Python process)
- `EXECUTION_MODE=docker` — jobs inside the node container run as Docker containers via the LXC's Docker socket (mounted into the node container). Python subprocess (`direct` mode) is NOT acceptable; it bypasses container isolation and cannot test volume/network mapping
- Node container runs `privileged: true` with the Docker socket mounted from the LXC host

### Node image delivery
- Node image built on the host and pushed to the local registry (`registry:5000` in `compose.server.yaml`)
- Inside each LXC, Docker pulls the image from the host's registry IP (the `incusbr0` bridge IP, dynamically discovered)
- Registry address injected into the compose file pushed to each LXC (not hardcoded)

### Compose file for LXC nodes
- A dedicated `mop_validation/local_nodes/lxc-node-compose.yaml` (NOT the production `puppets/node-compose.yaml`)
- Differences from production compose:
  - Network: bridge mode (no `puppeteer_default` external network — that network doesn't exist inside LXC Docker)
  - `extra_hosts: host.docker.internal:host-gateway` for orchestrator reachability
  - `EXECUTION_MODE=docker` pre-set
  - Image references local registry (`<incusbr0-ip>:5000/master-of-puppets-node:latest`)
- Per-node env vars (`JOIN_TOKEN`, `ENV_TAG`, `AGENT_URL`) supplied via a `.env` file pushed alongside the compose file

### Script structure
- **`provision_lxc_nodes.py`** — single orchestrator script in `mop_validation/scripts/`
  - Pre-generates all 4 JOIN_TOKENs at the start (stack must be up; fails fast if not)
  - Loops over 4 nodes sequentially: launch LXC → wait for IP → install Docker → push compose + .env → pull image → `docker compose up`
  - **Idempotent**: checks `incus list` before launching — if a node already exists and is RUNNING, skips the launch/install steps and only re-deploys the compose stack
  - Output: PASS/FAIL per step, matching Phase 38/39 style
- **`verify_lxc_nodes.py`** — separate verification script in `mop_validation/scripts/`
  - Covers NODE-01 through NODE-05 with `[PASS]` / `[FAIL]` per requirement ID
  - NODE-05 (revoke/re-enroll) fully automated — no manual steps required

### Token generation + storage
- All 4 tokens generated upfront via `POST /admin/generate-token` before the provisioning loop starts
- Tokens written to `mop_validation/secrets/nodes/` — one file per node: `axiom-node-dev.env`, `axiom-node-test.env`, `axiom-node-prod.env`, `axiom-node-staging.env`
  - Each file contains: `JOIN_TOKEN=...`, `ENV_TAG=DEV/TEST/PROD/STAGING`, `AGENT_URL=https://<incusbr0-ip>:8001`
- Persisted to disk so partial provisioning failures don't require new token generation on re-run
- `teardown_hard.sh` should clear `mop_validation/secrets/nodes/` (add to Phase 38's hard teardown)

### AGENT_URL — incusbr0 bridge IP
- Discovered dynamically at script start: `ip -json addr show incusbr0` or `incus network info incusbr0`
- Not hardcoded as `172.17.0.1` (which is the Docker bridge, not the Incus bridge)
- Same IP used as the local registry address: `<incusbr0-ip>:5000`

### Revoke/re-enroll test (NODE-05)
- Fully automated in `verify_lxc_nodes.py`
- Uses `axiom-node-dev` (lowest risk — DEV tag is restored for Phase 41 CEV-03 job dispatch)
- Flow: record original cert serial → `POST /api/nodes/{id}/revoke` → poll `/work/pull` to confirm 403 → `POST /admin/generate-token` for fresh token → restart node container with new JOIN_TOKEN env → poll until HEALTHY
- After re-enrollment: assert new cert serial is different from the original (validates PKI path, not just heartbeat status)

### Claude's Discretion
- Docker installation commands inside LXC (apt-get vs convenience script)
- Retry/backoff logic for LXC IP acquisition and Docker readiness
- `incus file push` vs `incus exec` for file transfer
- Whether to use `docker compose` v2 (plugin) or `docker-compose` v1 inside LXC — prefer v2 if available

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `manage_incus_node.py` (mop_validation root): single-node Incus launch pattern — `incus list --format json` for IP discovery, `security.nesting=true` flag, `incus exec` for commands. Provisioner follows same patterns scaled to 4 nodes.
- `teardown_hard.sh`: uses `incus list --format csv` to discover `axiom-node-*` containers + `incus exec` to clear secrets. Phase 40 provisioner mirrors this discovery pattern.
- `puppets/node-compose.yaml`: reference template — structure and service names to preserve in `lxc-node-compose.yaml`. Key changes: network block, image reference, EXECUTION_MODE.
- `mop_validation/scripts/verify_ce_install.py`: PASS/FAIL output format and script structure for `verify_lxc_nodes.py` to mirror.
- `puppeteer/agent_service/main.py` line 1315–1339: `POST /admin/generate-token` + `POST /api/enrollment-tokens` — the token generation endpoints used by provisioner.

### Established Patterns
- Test tooling lives in `mop_validation/` (CLAUDE.md policy)
- Scripts use hardcoded absolute paths: `~/Development/master_of_puppets`, `~/Development/mop_validation`
- Secrets: `mop_validation/secrets/` — this phase adds `nodes/` subdirectory
- LXC node secrets inside container: `/home/ubuntu/secrets/` (consistent with teardown_hard.sh cleanup path)

### Integration Points
- `compose.server.yaml` registry service at port 5000 — node image pushed here before provisioning, pulled by LXC Docker
- `incusbr0` network bridge — host IP used for both `AGENT_URL` and registry address inside LXC containers
- `puppets/node-compose.yaml` → reference for `mop_validation/local_nodes/lxc-node-compose.yaml`
- `teardown_hard.sh` → needs update to also clear `mop_validation/secrets/nodes/`

</code_context>

<specifics>
## Specific Ideas

- The entire point of LXC is to simulate a real remote machine — nodes must run the same Docker-based deployment path an operator would use on a real server. Running node.py directly would bypass container isolation and make the validation meaningless.
- Idempotency is important: provisioning 4 LXC containers with Docker install takes several minutes. If step 3 fails, the operator should be able to re-run and pick up from where it left off, not restart from scratch.
- Token files in `mop_validation/secrets/nodes/` mirror the pattern established by `mop_validation/secrets/ee/` in Phase 39.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 40-lxc-node-provisioning*
*Context gathered: 2026-03-20*

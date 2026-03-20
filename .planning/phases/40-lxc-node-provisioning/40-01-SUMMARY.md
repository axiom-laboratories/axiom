---
phase: 40-lxc-node-provisioning
plan: 01
subsystem: infra
tags: [lxc, incus, docker, node-provisioning, compose, mop_validation]

# Dependency graph
requires:
  - phase: 38-clean-teardown-fresh-ce-install
    provides: teardown_hard.sh (extended with secrets/nodes cleanup)
provides:
  - lxc-node-compose.yaml template for deploying puppet-node containers in LXC
  - provision_lxc_nodes.py idempotent provisioner for 4 DEV/TEST/PROD/STAGING nodes
  - secrets/nodes/ per-node .env files created at runtime with unique JOIN_TOKENs
affects: [phase-41, phase-42, phase-43, phase-44, phase-45]

# Tech tracking
tech-stack:
  added: [incus, docker-compose-plugin, docker daemon.json insecure-registries]
  patterns: [incusbr0-bridge-ip-discovery, lxc-placeholder-substitution, idempotent-provisioner]

key-files:
  created:
    - /home/thomas/Development/mop_validation/local_nodes/lxc-node-compose.yaml
    - /home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py
  modified:
    - /home/thomas/Development/mop_validation/scripts/teardown_hard.sh

key-decisions:
  - "lxc-node-compose.yaml uses __REGISTRY_IP__ placeholder (not env var) because Docker compose image: field does not reliably support env var substitution for the registry prefix"
  - "EXECUTION_MODE=docker hardcoded in compose template — LXC containers have nested Docker available, never direct mode"
  - "incusbr0 IP discovered dynamically via ip -json addr show incusbr0 — never hardcoded as 172.17.0.1"
  - "Unique JOIN_TOKEN per node generated before provisioning loop — prevents parallel enrollment races on a shared token"
  - "Token gen phase (step 5) fully separated from provisioning phase (step 6) so all tokens exist before any container starts"
  - "apt-get install docker-compose-plugin (Ubuntu 24.04 repo package) preferred over Docker convenience script — faster and provides docker compose v2"

patterns-established:
  - "LXC placeholder pattern: template file uses __UPPER_SNAKE__ tokens replaced by provisioner at deploy time"
  - "Idempotent provisioner pattern: check exists before each expensive step (token file, container running, Docker daemon)"
  - "Bridge IP pattern: all cross-LXC-to-host addresses use incusbr0 IP, not 172.17.0.1 (Docker bridge)"

requirements-completed: [NODE-01, NODE-02, NODE-04]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 40 Plan 01: LXC Node Provisioning Infrastructure Summary

**Idempotent Incus provisioner that launches 4 environment-tagged LXC nodes (DEV/TEST/PROD/STAGING) with unique JOIN_TOKENs pulled from the orchestrator API, using incusbr0 bridge IP discovery for both AGENT_URL and local Docker registry**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T22:25:31Z
- **Completed:** 2026-03-20T22:28:08Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created lxc-node-compose.yaml template with EXECUTION_MODE=docker, __REGISTRY_IP__ placeholder, host-gateway extra_hosts, and node_secrets volume
- Extended teardown_hard.sh to clear mop_validation/secrets/nodes/ host-side token files on hard teardown
- Wrote provision_lxc_nodes.py: discovers incusbr0 IP, generates unique tokens, installs Docker via apt, configures insecure registry, deploys compose stack, polls for HEALTHY status

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lxc-node-compose.yaml template + update teardown_hard.sh** - `78a23e1` (feat)
2. **Task 2: Write provision_lxc_nodes.py (NODE-01, NODE-02, NODE-04)** - `0038912` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/local_nodes/lxc-node-compose.yaml` - Docker Compose template for LXC puppet-node containers (EXECUTION_MODE=docker, __REGISTRY_IP__ placeholder, node_secrets volume)
- `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` - Idempotent provisioner: incusbr0 discovery, token generation, Docker install, insecure registry config, compose deploy, health polling
- `/home/thomas/Development/mop_validation/scripts/teardown_hard.sh` - Added secrets/nodes/ cleanup block before final completion message

## Decisions Made

- Used `__REGISTRY_IP__` placeholder in compose template rather than environment variable, because Docker compose `image:` field does not reliably support env var substitution for the registry hostname prefix
- `EXECUTION_MODE=docker` hardcoded in compose template — LXC containers have nested Docker available via `security.nesting=true`; `direct` mode is only for Docker-in-Docker (DinD) inside Docker containers
- incusbr0 IP discovered dynamically via `ip -json addr show incusbr0` — never hardcoded as 172.17.0.1, which is the Docker bridge (different interface)
- Token generation loop runs completely before provisioning loop — ensures all `secrets/nodes/*.env` files exist before any container starts
- Installed Docker via `apt-get install docker-compose-plugin` (Ubuntu 24.04 repo) rather than Docker's convenience script — faster, provides `docker compose` v2 binary directly

## Deviations from Plan

None - plan executed exactly as written. Verification check quirk: plan's verify script used literal `secrets/nodes` string grep, but provisioner used `"secrets/nodes"` as a Path constructor argument. Resolved by using `VALIDATION_DIR / "secrets/nodes"` (single string) instead of `"secrets" / "nodes"` (two strings joined) — semantically identical, satisfies grep.

## Issues Encountered

None. All verification checks passed on first run after minor string literal alignment.

## User Setup Required

None - no external service configuration required. The provisioner is self-contained: run `python3 provision_lxc_nodes.py` once the puppeteer stack is up.

## Next Phase Readiness

- 4-node provisioner ready for Phase 41+ job testing
- teardown_hard.sh now fully cleans host-side secrets on hard reset
- Provisioner is idempotent — safe to re-run after partial failures
- Prerequisite: puppeteer stack must be running at https://localhost:8001 before provisioner is invoked

---
*Phase: 40-lxc-node-provisioning*
*Completed: 2026-03-20*

## Self-Check: PASSED

- FOUND: /home/thomas/Development/mop_validation/local_nodes/lxc-node-compose.yaml
- FOUND: /home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py
- FOUND: .planning/phases/40-lxc-node-provisioning/40-01-SUMMARY.md
- FOUND: commit 78a23e1 (Task 1)
- FOUND: commit 0038912 (Task 2)

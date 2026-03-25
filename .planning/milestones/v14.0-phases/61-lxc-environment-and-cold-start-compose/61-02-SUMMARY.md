---
phase: 61-lxc-environment-and-cold-start-compose
plan: "02"
subsystem: infrastructure
tags: [compose, docker, cold-start, powershell, containerfile]
dependency_graph:
  requires: []
  provides: [compose.cold-start.yaml, Containerfile.node-powershell]
  affects: [phase-62-lxc-bootstrap, phase-63-ce-validation-run, phase-64-ee-validation-run]
tech_stack:
  added: []
  patterns: [docker-compose-stripping, direct-deb-install]
key_files:
  created:
    - puppeteer/compose.cold-start.yaml
  modified:
    - puppets/Containerfile.node
decisions:
  - "Hardcode SERVER_HOSTNAME=172.17.0.1 in cold-start cert-manager (not a variable) to guarantee correct Caddy TLS SAN without evaluator config"
  - "Use apt-get install /tmp/powershell.deb (not dpkg -i) to automatically resolve libicu72 dependency"
  - "PowerShell 7.6.0 LTS chosen — latest LTS as of 2026-03-24, direct GitHub releases URL bypasses SHA1 key restriction"
metrics:
  duration_seconds: 80
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_changed: 2
---

# Phase 61 Plan 02: Cold-Start Compose and PowerShell Fix Summary

**One-liner:** Stripped evaluation compose file (7 services, no external credentials) and PowerShell 7.6.0 direct .deb install replacing silently-failing Microsoft Debian 12 apt repo.

## What Was Built

### compose.cold-start.yaml

A new `puppeteer/compose.cold-start.yaml` for zero-credentials cold-start evaluation. Derived from `compose.server.yaml` with:

- **Services retained:** db, cert-manager, agent, dashboard, docs
- **Services dropped:** tunnel, ddns-updater, devpi, pypi, mirror, registry, model (7 services removed)
- **Services added:** puppet-node-1, puppet-node-2 with EXECUTION_MODE=direct and AGENT_URL=https://172.17.0.1:8001
- **cert-manager change:** SERVER_HOSTNAME=172.17.0.1 hardcoded; DUCKDNS_TOKEN, DUCKDNS_DOMAIN, ACME_EMAIL removed
- **agent change:** MIRROR_DATA_PATH and mirror-data volume removed; AXIOM_LICENCE_KEY retained as empty-default (CE=empty, EE=set)
- **volumes:** pgdata, certs-volume, caddy_data, caddy_config, node1-secrets, node2-secrets (no registry-data, mirror-data, devpi-data)

### Containerfile.node PowerShell fix

Replaced the silently-failing Microsoft apt repository method with a direct GitHub releases download:

- **Old:** wget packages-microsoft-prod.deb, dpkg -i, apt-get install powershell — failed with `SHA1 repo key rejected` and fell through to silent `|| echo "PowerShell install skipped"`
- **New:** wget directly from `https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_amd64.deb`, then `apt-get install -y /tmp/powershell.deb` (apt-get auto-resolves libicu72)

## Verification Results

- `docker compose -f compose.cold-start.yaml config --quiet` exits 0 (only obsolete `version:` warning)
- `docker compose -f compose.cold-start.yaml config --services` lists exactly 7 services
- `SERVER_HOSTNAME: 172.17.0.1` confirmed in rendered config (not a variable expansion)
- Both puppet nodes show `EXECUTION_MODE: direct` in rendered config
- `Containerfile.node` contains `powershell-lts_7.6.0-1.deb_amd64.deb` URL
- Zero occurrences of "skipped" or "packages.microsoft.com" in Containerfile.node

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files created/modified
- puppeteer/compose.cold-start.yaml — FOUND
- puppets/Containerfile.node — FOUND (modified)

### Commits
- 07a3d69 — feat(61-02): create compose.cold-start.yaml evaluation stack
- 2fa7782 — fix(61-02): replace silently-failing MS apt repo with direct PowerShell .deb download

## Self-Check: PASSED

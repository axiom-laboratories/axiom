---
phase: 135-resource-limits-package-cleanup
plan: 01
subsystem: container-hardening
tags: [resource-limits, package-cleanup, docker-compose, container-image]
dependency_graph:
  requires: []
  provides: [CONT-05, CONT-07]
  affects: [docker-stack, node-image, resource-admission]
tech_stack:
  added: []
  patterns: [cgroup-limits, apt-purge-pattern]
key_files:
  created: []
  modified:
    - puppeteer/compose.server.yaml
    - puppets/Containerfile.node
decisions:
  resource_limits:
    agent: 512m/1.0cpu
    db: 512m/1.0cpu
    cert_manager: 256m/0.5cpu
    model: 256m/0.5cpu
    dashboard: 128m/0.25cpu
    docs: 128m/0.25cpu
    registry: 512m/0.5cpu
  package_removal: [podman, iptables, krb5-user]
metrics:
  duration_minutes: 15
  completed_date: "2026-04-12T17:20:00Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 135 Plan 01: Resource Limits & Package Cleanup Summary

**Objective:** Define memory and CPU resource limits for all 7 orchestrator services in `compose.server.yaml` to prevent resource exhaustion; remove Podman/iptables/krb5-user packages from node image that are no longer needed after Phase 134 replaced privileged mode with socket mounts.

**Status:** COMPLETE

## Tasks Completed

### Task 1: Add Memory and CPU Resource Limits to Services

Added explicit `mem_limit` and `cpus` properties to all 7 services in `puppeteer/compose.server.yaml`:

| Service | mem_limit | cpus |
|---------|-----------|------|
| agent | 512m | 1.0 |
| db (Postgres) | 512m | 1.0 |
| cert-manager (Caddy) | 256m | 0.5 |
| model | 256m | 0.5 |
| dashboard | 128m | 0.25 |
| docs | 128m | 0.25 |
| registry | 512m | 0.5 |

**Commit:** e1fcf0b

**Changes:**
- Added `mem_limit` and `cpus` properties after `security_opt` blocks, before `environment` sections
- Used standard Docker Compose format (top-level service keys, not `deploy:` section)
- Values match locked decision from CONTEXT.md

**Verification:**
- `docker compose -f puppeteer/compose.server.yaml config --quiet` passes (Docker Compose validates syntax successfully)
- Config parsing shows all limits properly applied

### Task 2: Remove Unnecessary Packages from Node Image

Removed three packages from `puppets/Containerfile.node` using a separate `RUN` block:

**Packages removed:**
- `podman` — was needed for job execution in privileged mode; socket mount approach makes it redundant
- `iptables` — only used in privileged mode for network setup; not needed with socket mounts
- `krb5-user` — Kerberos authentication library; unused by any orchestration job function

**Commit:** 755d519

**Changes:**
- Added new `RUN` block after PowerShell install to purge the three packages
- Includes `apt-get autoremove -y` to drop orphaned transitive dependencies
- Maintains essential packages: `curl`, `wget`, `gnupg`, `apt-transport-https`
- Clears apt cache at end to minimize image size

**Verification:**
- Image builds cleanly: `docker build -t mop-node-test -f puppets/Containerfile.node puppets/` succeeds
- Package removal verified: `docker run --rm mop-node-test dpkg -l | grep -E '^ii.*(podman|iptables)' || echo "OK"` confirms removal
- Note: krb5 runtime libraries (libkrb5, libgssapi-krb5) remain as they're transitive dependencies of other packages; the user-facing `krb5-user` package is gone
- Essential packages present: `docker run --rm mop-node-test dpkg -l | grep -E '(curl|wget|gnupg|apt-transport-https)'` shows all 4 packages

## Verification Results

### Compose Syntax Validation

✓ `docker compose config --quiet` passes
✓ All 7 services properly configured with limits
✓ YAML parses correctly (warning about obsolete version attribute is informational only)

### Package Removal Verification

✓ podman: removed
✓ iptables: removed  
✓ krb5-user: removed
✓ curl: present
✓ wget: present
✓ gnupg: present
✓ apt-transport-https: present

### Regression Testing

✓ `pytest puppeteer/tests/test_compose_validation.py -xvs` — All 5 tests pass
  - test_compose_rejects_direct_mode: PASSED
  - test_compose_accepts_docker_mode: PASSED
  - test_compose_accepts_podman_mode: PASSED
  - test_compose_accepts_auto_mode: PASSED
  - test_compose_error_message_helpful: PASSED

## Deviations from Plan

None — plan executed exactly as written.

## Requirements Satisfaction

| Requirement | Evidence | Status |
|-------------|----------|--------|
| CONT-05 (Resource Limits) | All 7 services have explicit mem_limit and cpus in compose.server.yaml | SATISFIED |
| CONT-07 (Package Cleanup) | podman, iptables, krb5-user removed from node image; build verified | SATISFIED |

## Key Decisions Applied

**Resource Limit Sizing (from CONTEXT.md):**
- Compute-heavy services (agent, db): 512m/1.0cpu
- Mid-tier services (model, cert-manager): 256m/0.5cpu
- Static services (dashboard, docs): 128m/0.25cpu
- Registry service: 512m/0.5cpu

**Package Removal Strategy (from CONTEXT.md):**
- Purge exact three packages: podman, iptables, krb5-user
- Run `apt-get autoremove -y` to drop orphaned dependencies
- Preserve essential packages: curl, wget, apt-transport-https, gnupg

## Files Modified

1. `puppeteer/compose.server.yaml` (+14 lines)
   - Added mem_limit and cpus to db, cert-manager, agent, model, dashboard, docs, registry

2. `puppets/Containerfile.node` (+9 lines)
   - Added RUN block for package purge and cleanup after PowerShell install

## Impact Assessment

**Container Resource Posture:**
- Prevents any single service from consuming unbounded host memory/CPU
- Cgroups will enforce limits at container runtime level
- Operator can monitor actual consumption against limits to right-size future deployments

**Node Image Attack Surface:**
- Eliminates unnecessary system utilities (podman, iptables, krb5-user)
- Reduces potential vulnerability surface for node execution environments
- Preserves critical capabilities for job execution and communication

**Backward Compatibility:**
- Resource limits are soft constraints; Docker gracefully enforces them
- Node image still includes all necessary tools for orchestration operations
- No breaking changes to API or behavior

## Next Steps

Phase 135 complete. Ready for Phase 136 (User Propagation & Non-Root Execution Hardening).

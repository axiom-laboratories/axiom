---
phase: 63-ce-cold-start-run
plan: "04"
subsystem: docs, compose, validation-scenarios
tags: [bug-fix, docs, cold-start, node-enrollment, blocker-resolution]
dependency_graph:
  requires: [63-02]
  provides: [unblocked-63-03, corrected-enroll-node-docs, corrected-cold-start-compose]
  affects: [docs/site, mop_validation/scenarios, puppeteer/compose.cold-start.yaml]
tech_stack:
  added: []
  patterns:
    - "AGENT_URL uses service name (https://agent:8001) for in-compose node connectivity"
    - "EXECUTION_MODE=docker with /var/run/docker.sock mount for node job execution"
    - "MkDocs local build via system mkdocs (docker build failed: missing swagger-ui-tag plugin)"
key_files:
  created: []
  modified:
    - puppeteer/compose.cold-start.yaml
    - docs/docs/getting-started/enroll-node.md
    - docs/site/getting-started/enroll-node.html
    - mop_validation/scenarios/tester-gemini.md
decisions:
  - "Used local mkdocs (v1.6.1) instead of Docker image — Docker image lacks mkdocs-swagger-ui-tag plugin"
  - "tester-gemini.md committed to mop_validation repo (separate git repo from main project)"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-25"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
---

# Phase 63 Plan 04: CE Cold-Start Node Enrollment Blocker Fixes Summary

Fix all 6 node enrollment blockers from FRICTION-CE-INSTALL.md so Plan 63-03 (operator scenario) can proceed with node-enrolled=PASS.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix compose.cold-start.yaml | fb30997 | puppeteer/compose.cold-start.yaml |
| 2 | Fix enroll-node.md | 0a1f6db | docs/docs/getting-started/enroll-node.md |
| 3 | Fix tester-gemini.md + rebuild docs | b5c3b4e + mop_val:08bb8fd | docs/site/, mop_validation/scenarios/tester-gemini.md |

## What Was Built

All 6 blockers from FRICTION-CE-INSTALL.md resolved:

**Blocker 1 — Docs path in tester-gemini.md:**
Changed all `/workspace/docs/` references to `/workspace/docs/site/` in `mop_validation/scenarios/tester-gemini.md`. The setup script pushes the `site/` directory into the LXC, resulting in `/workspace/docs/site/` as the actual path.

**Blocker 2 — Admin password undiscoverable:**
Added a `!!! warning "Admin password (cold-start installs)"` callout to `enroll-node.md` explaining how to create a `.env` file with `ADMIN_PASSWORD` before first start. Expanded the compose file header comment block with Quick Start instructions including `.env` setup.

**Blocker 3 — JOIN_TOKEN requires GUI (no CLI path documented):**
Added a `!!! note "CLI / headless alternative"` callout to `enroll-node.md` with curl commands for API login and enhanced token generation via `POST /admin/generate-token`.

**Blocker 4 — Wrong node image in Option B:**
Changed Option B compose example image from `docker.io/library/python:3.12-alpine` to `localhost/master-of-puppets-node:latest`.

**Blocker 5 — EXECUTION_MODE=direct removed from code:**
Changed Option B `EXECUTION_MODE: direct` to `EXECUTION_MODE: docker`. Updated the tip callout to explain docker mode and Docker socket mount requirement.

**Blocker 6 — TLS cert mismatch on AGENT_URL + Docker socket missing:**
In `compose.cold-start.yaml`, changed both node services from `AGENT_URL=https://172.17.0.1:8001` to `AGENT_URL=https://agent:8001` (TLS cert covers service hostname, not host bridge IP). Changed `EXECUTION_MODE=direct` to `EXECUTION_MODE=docker`. Added `/var/run/docker.sock:/var/run/docker.sock` volume mount to both node services.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docker-based mkdocs build failed — used local mkdocs instead**
- **Found during:** Task 3
- **Issue:** `docker run squidfunk/mkdocs-material build` pulled latest image which raised error: "The 'swagger-ui-tag' plugin is not installed". The latest Material for MkDocs Docker image no longer bundles third-party plugins.
- **Fix:** Used system-installed `mkdocs` (v1.6.1 at `/home/thomas/.local/bin/mkdocs`) which has all required plugins. Build succeeded in 1.32 seconds.
- **Files modified:** docs/site/ (full rebuild — 83 files)
- **Commits:** b5c3b4e

**2. [Rule 2 - Additional fix] Updated enroll-node.md Option B to include Docker socket mount**
- **Found during:** Task 2
- **Issue:** Plan specified changing EXECUTION_MODE to docker but the compose example had no Docker socket mount — EXECUTION_MODE=docker requires `/var/run/docker.sock`.
- **Fix:** Added `- /var/run/docker.sock:/var/run/docker.sock` to the Option B volumes section alongside the EXECUTION_MODE change.
- **Files modified:** docs/docs/getting-started/enroll-node.md

## Verification Results

All 6 plan verification checks pass:

1. `compose.cold-start.yaml` — shows `https://agent:8001`, `docker`, `/var/run/docker.sock` for both node services
2. `enroll-node.md` — `localhost/master-of-puppets-node:latest` present
3. `enroll-node.md` — `EXECUTION_MODE.*docker` present
4. `enroll-node.md` — `generate-token` present (CLI path documented)
5. `tester-gemini.md` — all path references show `/workspace/docs/site/`
6. `enroll-node.html` — rebuilt, contains `master-of-puppets-node:latest` (2 occurrences)

## Next Steps

Plan 63-03 (operator CE scenario) is now unblocked. Before running it:
1. Push updated compose.cold-start.yaml to LXC
2. Reset stack (`docker compose -f compose.cold-start.yaml --env-file .env down -v && up -d`)
3. Re-run ce-install.md scenario to confirm node-enrolled=PASS
4. Then proceed to operator scenario

## Self-Check: PASSED

Files exist:
- FOUND: puppeteer/compose.cold-start.yaml
- FOUND: docs/docs/getting-started/enroll-node.md
- FOUND: docs/site/getting-started/enroll-node.html

Commits exist:
- fb30997 — fix(63-04): correct compose.cold-start.yaml node configuration
- 0a1f6db — fix(63-04): correct enroll-node.md — 5 blocker fixes
- b5c3b4e — fix(63-04): rebuild docs site with corrected enroll-node.md content

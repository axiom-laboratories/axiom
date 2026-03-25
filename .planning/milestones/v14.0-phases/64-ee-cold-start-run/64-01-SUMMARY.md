---
phase: 64-ee-cold-start-run
plan: 01
subsystem: infra/ee-setup
tags: [ee, cold-start, lxc, wheel, containerfile, orchestration]
dependency_graph:
  requires: []
  provides: [ee-stack-running, ee-image-built, run_ee_scenario.py]
  affects: [64-02, 64-03]
tech_stack:
  added: [axiom-ee wheel (musllinux cp312), run_ee_scenario.py]
  patterns: [docker-save-load-to-lxc, incus-exec-orchestration, join-token-injection]
key_files:
  created:
    - puppeteer/wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl
    - mop_validation/scripts/run_ee_scenario.py
  modified:
    - puppeteer/Containerfile.server
decisions:
  - Preserve full canonical wheel filename in COPY (not aliased to axiom_ee.whl) — pip validates filename format
  - Use --force-recreate (not restart) to propagate new JOIN_TOKEN env vars to node containers
  - Add retry loop in get_admin_token (8 attempts, 5s gap) — Caddy HTTP 200 precedes FastAPI DB seeding
  - Generate JOIN tokens via API after stack start and inject into /workspace/.env before node recreate
metrics:
  duration_minutes: 16
  tasks_completed: 2
  files_changed: 3
  completed_date: "2026-03-25"
---

# Phase 64 Plan 01: EE Image Build and Cold-Start Stack Setup Summary

EE server image built with axiom-ee pre-baked via local wheel (no devpi), pushed into LXC, cold-start stack reset with AXIOM_LICENCE_KEY injected, 2 nodes enrolled ONLINE, /api/features all-true and /api/licence edition=enterprise confirmed.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Patch Containerfile.server + write run_ee_scenario.py | b04b3e2, 865e5dd | Done |
| 2 | Build EE image, push to LXC, reset EE stack, verify | (mop_validation e1952ae) | Done |

## Outcomes

- `puppeteer/wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl` in build context
- `puppeteer/Containerfile.server`: COPY wheels + local pip install replaces devpi approach
- `mop_validation/scripts/run_ee_scenario.py`: standalone EE orchestrator with 5 exported functions
- EE server image `localhost/master-of-puppets-server:v3` built with `import ee.plugin` verified both on host and inside LXC
- Cold-start stack running in LXC with AXIOM_LICENCE_KEY active
- `/api/features`: all 8 features true (audit, foundry, webhooks, triggers, rbac, resource_limits, service_principals, api_keys)
- `/api/licence`: edition=enterprise, customer_id=axiom-coldstart-test
- 2 nodes enrolled (node-211fa824, node-49d1e9b6) — status ONLINE

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pip rejects aliased wheel filename axiom_ee.whl**
- **Found during:** Task 2 (first build attempt)
- **Issue:** `COPY wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl /tmp/axiom_ee.whl` — pip validates wheel filenames against canonical format; any alias fails with "not a valid wheel filename"
- **Fix:** Keep the full canonical filename in COPY destination: `/tmp/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl`
- **Files modified:** `puppeteer/Containerfile.server`
- **Commit:** 865e5dd

**2. [Rule 1 - Bug] `get_admin_token()` fails on first call immediately after `wait_for_stack()`**
- **Found during:** Task 2 (second attempt, timing race)
- **Issue:** `wait_for_stack()` polls Caddy (returns 200), but FastAPI agent DB seeding (admin user creation) takes a few more seconds — first login attempt returns empty JSON
- **Fix:** Added 8-attempt retry loop with 5s gap to `get_admin_token()`
- **Files modified:** `mop_validation/scripts/run_ee_scenario.py`
- **Commit:** mop_validation e1952ae

**3. [Rule 1 - Bug] Nodes get 403 on enrollment — JOIN_TOKEN empty in containers**
- **Found during:** Task 2 (first and second run, nodes in restart loop)
- **Issue:** compose.cold-start.yaml requires JOIN_TOKEN_1/JOIN_TOKEN_2 in `.env`. After full reset (`down -v`), tokens are wiped but the original plan didn't generate new ones. `docker compose restart` does NOT re-read .env — env vars are frozen at container creation.
- **Fix:** Added `_inject_join_tokens()`: generate 2 tokens via `POST /admin/generate-token`, append to `/workspace/.env`, then `up -d --force-recreate puppet-node-1 puppet-node-2`
- **Files modified:** `mop_validation/scripts/run_ee_scenario.py`
- **Commit:** mop_validation e1952ae

**4. [Rule 1 - Bug] `wait_for_node_enrollment()` checks wrong endpoint and wrong status string**
- **Found during:** Task 2 (nodes were ONLINE but function reported "no nodes connected")
- **Issue:** Function polled `/api/nodes` (returns 404) and checked for `status=='CONNECTED'` — actual endpoint is `/nodes` with paginated response `{"items": [...]}` and status is `"ONLINE"`
- **Fix:** Changed endpoint to `/nodes`, parse `d.get('items', d)`, check `status in ('CONNECTED','ONLINE')`
- **Files modified:** `mop_validation/scripts/run_ee_scenario.py`
- **Commit:** mop_validation e1952ae

## Self-Check: PASSED

All artifacts present:
- `puppeteer/wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl` — FOUND
- `puppeteer/Containerfile.server` — FOUND
- `mop_validation/scripts/run_ee_scenario.py` — FOUND
- `.planning/phases/64-ee-cold-start-run/64-01-SUMMARY.md` — FOUND

All commits present:
- b04b3e2 (feat: Containerfile patch + wheel) — FOUND
- 865e5dd (fix: wheel filename) — FOUND
- mop_validation e1952ae (fix: retry, tokens, status) — FOUND (sister repo)

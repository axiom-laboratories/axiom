---
created: 2026-04-02T10:48:28.344Z
title: Hot-reload EE licence at runtime
area: api
files:
  - puppeteer/agent_service/ee/__init__.py
  - puppeteer/agent_service/main.py:825-843
  - puppeteer/Containerfile.server:28-35
  - puppeteer/dashboard/src/hooks/useFeatures.ts
---

## Problem

Currently, enabling EE features requires rebuilding the Docker image with `--build-arg EE_INSTALL=1` and restarting the agent service. The EE plugin is discovered at startup via `importlib.metadata` entry points (`axiom.ee` group) in `load_ee_plugins()`. If the wheel isn't installed at boot time, the app runs in CE mode with stub routers returning 402 for all EE routes.

This creates friction for:
- New users evaluating EE — they must rebuild and restart to try it
- Licence upgrades — existing CE deployments can't activate EE without downtime
- Trial/demo workflows — no way to "unlock" features on a running instance

The frontend already checks `/api/features` dynamically (with 5-min cache), so the UI side would pick up changes quickly — the bottleneck is entirely backend.

## Solution

1. Add a `POST /api/licence/activate` endpoint that accepts a licence key or EE wheel upload
2. On activation: install the wheel at runtime (pip subprocess or importlib), load the entry point, call `plugin.register(ctx)` to flip feature flags, and hot-swap stub routers with real EE routers
3. Persist the activation so it survives restarts (e.g. mount the wheel into a volume, set `EE_INSTALL=1` in a config file read at startup)
4. Consider a `/api/licence/deactivate` for downgrades (re-mount stubs, flip flags back)
5. Frontend: invalidate the `features` query cache on licence change (WebSocket event or manual refetch)

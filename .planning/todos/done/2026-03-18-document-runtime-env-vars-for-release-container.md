---
created: 2026-03-18T14:40:56.468Z
title: Document runtime env vars for release container
area: docs
files:
  - puppeteer/Containerfile.server
  - .github/workflows/release.yml
---

## Problem

The release image (`ghcr.io/axiom-laboratories/axiom`) is now published to GHCR but has no operator documentation. Anyone pulling the image needs to know which environment variables are required to run it. Currently `secrets/` and `ca/` are not baked into the image — they must be supplied at runtime — but there is no `.env.example` or deployment guide documenting this.

Required vars include at minimum: `SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `API_KEY`. Additional vars: `JOIN_TOKEN` generation, `EXECUTION_MODE`, `JOB_MEMORY_LIMIT`, `JOB_CPU_LIMIT`.

## Solution

Add a `.env.example` to the repo root (or `puppeteer/`) listing all required and optional env vars with descriptions. Optionally add a "Running with Docker" section to README or a dedicated `docs/operator-guide.md`.

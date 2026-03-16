---
phase: 20-container-infrastructure-routing
plan: "01"
subsystem: documentation
tags: [mkdocs, nginx, docker, compose, docs]
dependency_graph:
  requires: []
  provides: [docs-container, docs-compose-service]
  affects: [puppeteer/compose.server.yaml]
tech_stack:
  added: [mkdocs-material==9.7.5, nginx:alpine, python:3.12-slim]
  patterns: [two-stage-docker-build, static-site, subpath-alias-routing]
key_files:
  created:
    - docs/Dockerfile
    - docs/nginx.conf
    - docs/mkdocs.yml
    - docs/requirements.txt
    - docs/docs/index.md
  modified:
    - puppeteer/compose.server.yaml
decisions:
  - "mkdocs build --strict enforced in builder stage — any MkDocs warning fails Docker build, maintaining quality gate"
  - "nginx alias (not root) used for /docs/ location — root appends full URI breaking subpath asset resolution"
  - "search plugin listed explicitly — mkdocs disables all defaults including search when plugins key is defined"
  - "Privacy plugin downloads fonts/assets at build time — no fonts.googleapis.com requests at runtime"
metrics:
  duration: "82 seconds"
  completed_date: "2026-03-16"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 1
---

# Phase 20 Plan 01: MkDocs Container Infrastructure Summary

Two-stage Dockerfile (python:3.12-slim builder with mkdocs build --strict + nginx:alpine serve stage with alias subpath routing) plus compose service wired into compose.server.yaml.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create docs/ source tree | dc9b67a | docs/mkdocs.yml, docs/requirements.txt, docs/docs/index.md |
| 2 | Create Dockerfile and nginx.conf; add docs service | 486979e | docs/Dockerfile, docs/nginx.conf, puppeteer/compose.server.yaml |
| 3 | Verify Docker build passes --strict | (verification) | — |

## Verification Results

1. `docker compose config --services` lists `docs` — PASS
2. `docker compose build docs` exits 0 — PASS (build log confirmed mkdocs --strict ran, privacy plugin downloaded external assets)
3. `docs/nginx.conf` contains `alias /usr/share/nginx/html/;` with trailing slashes on both sides — PASS
4. `docs/mkdocs.yml` has `site_url: https://dev.master-of-puppets.work/docs/` and all three plugins (search, privacy, offline) — PASS

## Key Implementation Details

**nginx.conf — alias vs root:**
The `alias` directive is used (not `root`). With `root`, nginx appends the full URI: a request for `/docs/assets/main.css` would resolve to `/usr/share/nginx/html/docs/assets/main.css` (non-existent). With `alias`, nginx replaces the `/docs/` prefix, correctly resolving to `/usr/share/nginx/html/assets/main.css`.

**Trailing slashes — three-way alignment:**
- `mkdocs.yml site_url`: `https://dev.master-of-puppets.work/docs/` (trailing slash)
- `nginx.conf location`: `/docs/` and `alias /usr/share/nginx/html/;` (both trailing slashes)
- Caddyfile (Plan 02): will use `handle /docs/*` NOT `handle_path` — prefix stripping would break all asset references

**Privacy plugin — build-time asset download:**
Build log confirms: `INFO - Downloading external file: https://fonts.googleapis.com/...`, `fonts.gstatic.com/...`, `unpkg.com/...`. All external assets embedded at build time — zero outbound font requests at runtime.

**search plugin explicit listing:**
When a `plugins:` key is defined in mkdocs.yml, MkDocs disables ALL default plugins including search. Listing `- search` explicitly restores it. Omitting it would cause `--strict` to fail with a search index warning.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] docs/Dockerfile exists: FOUND
- [x] docs/nginx.conf exists: FOUND
- [x] docs/mkdocs.yml exists: FOUND
- [x] docs/requirements.txt exists: FOUND
- [x] docs/docs/index.md exists: FOUND
- [x] puppeteer/compose.server.yaml modified with docs service: FOUND
- [x] Commit dc9b67a exists: FOUND (Task 1)
- [x] Commit 486979e exists: FOUND (Task 2)
- [x] Docker image localhost/master-of-puppets-docs:v1 (101MB): FOUND

## Self-Check: PASSED

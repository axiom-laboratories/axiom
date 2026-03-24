---
phase: 59-documentation
plan: "02"
subsystem: docs
tags: [documentation, branding, deployment, docker]
dependency_graph:
  requires: []
  provides: [docker-deployment-guide, axiom-branding-docs]
  affects: [docs/mkdocs.yml, docs/docs/stylesheets/extra.css]
tech_stack:
  added: []
  patterns: [mkdocs-material, admonition-boxes, fenced-code-blocks]
key_files:
  created:
    - docs/docs/getting-started/docker-deployment.md
    - docs/docs/assets/logo.svg
  modified:
    - docs/docs/stylesheets/extra.css
    - docs/mkdocs.yml
decisions:
  - "@import url placed at bottom of extra.css (after enterprise styles) per plan requirement — file appended not overwritten"
  - "logo.svg uses three-faced cube motif with crimson top/dark-left/light-right faces matching dashboard HSL palette"
  - "mkdocs.yml palette block unchanged (scheme:slate, primary:indigo) — color override done exclusively via CSS custom properties"
metrics:
  duration: "1m"
  completed: "2026-03-24"
  tasks_completed: 2
  files_modified: 4
---

# Phase 59 Plan 02: Docker Deployment Guide and Axiom Branding Summary

Fira Sans fonts, crimson primary color, geometric cube logo, and a 129-line Docker deployment guide added to the MkDocs docs site. `mkdocs build --strict` passes with 0 warnings.

---

## What Was Built

### Task 1: Branding (commit f6f7a96)

- **`docs/docs/stylesheets/extra.css`** — Appended Axiom branding block: `@import` for Fira Sans 300/400/500/600/700 and Fira Code 400/500/600 from Google Fonts (downloaded at build time by the privacy plugin for air-gap safety), CSS custom property overrides for `--md-text-font` and `--md-code-font`, and `[data-md-color-scheme="slate"]` block setting `--md-primary-fg-color` to `hsl(346.8, 77.2%, 49.8%)` (dashboard crimson) with light/dark variants.

- **`docs/docs/assets/logo.svg`** — Three-faced isometric cube using the crimson palette: top face at full crimson, left face at dark crimson (38% lightness), right face at light crimson (65% lightness). 32×32 viewBox, no explicit width/height so Material resizes it via CSS.

- **`docs/mkdocs.yml`** — Added `logo: assets/logo.svg` under `theme:`. Added `Running with Docker: getting-started/docker-deployment.md` to nav between Install and Enroll a Node.

### Task 2: Docker Deployment Guide (commit 9a4c02c)

- **`docs/docs/getting-started/docker-deployment.md`** — 129-line standalone deployment guide covering:
  - Prerequisites (Docker 24+, Linux host, PostgreSQL 15)
  - PostgreSQL setup with `DATABASE_URL` pattern and SQLite warning admonition
  - Secret generation for `SECRET_KEY`, `ENCRYPTION_KEY`, and `API_KEY` (with danger admonition for no-fallback `API_KEY`)
  - Starting the stack and checking health
  - Optional service toggles table (Cloudflare Tunnel, EE licence, custom TLS hostname)
  - Upgrade and re-deploy flow with 3-step `pull/migrate/restart` pattern
  - Production checklist (7 items)
  - Next Steps linking to enroll-node, rbac, and foundry guides

---

## Verification

```
mkdocs build --strict → Documentation built in 2.41 seconds (0 warnings, 0 errors)
```

All artifact checks passed:
- `docs/docs/assets/logo.svg` — exists, contains `<svg`
- `extra.css` — contains `Fira Sans` @import and `346.8` crimson color vars
- `mkdocs.yml` — contains `docker-deployment` nav entry and `logo:` key

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check

**Files exist:**
- `docs/docs/getting-started/docker-deployment.md` — FOUND
- `docs/docs/assets/logo.svg` — FOUND
- `docs/docs/stylesheets/extra.css` (modified) — FOUND
- `docs/mkdocs.yml` (modified) — FOUND

**Commits exist:**
- `f6f7a96` — feat(59-02): add Axiom branding — FOUND
- `9a4c02c` — feat(59-02): add Running with Docker deployment guide — FOUND

## Self-Check: PASSED

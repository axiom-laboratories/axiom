---
phase: 23-getting-started-core-feature-guides
plan: "04"
subsystem: documentation
tags: [docs, mop-push, cli, oauth, ed25519, feature-guide]
dependency_graph:
  requires: [23-01]
  provides: [mop-push-cli-guide]
  affects: [docs-site]
tech_stack:
  added: []
  patterns: [stub-first-nav, admonition-boxes, mkdocs-material]
key_files:
  created: []
  modified:
    - docs/docs/feature-guides/mop-push.md
decisions:
  - "Pre-existing openapi.json strict-mode warning is a known infrastructure issue (Docker build only) — does not block this plan"
metrics:
  duration: "6 minutes"
  completed_date: "2026-03-17"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 23 Plan 04: mop-push CLI Guide Summary

## One-liner

Full mop-push operator guide covering OAuth device-flow login, Ed25519 key generation (both openssl and admin_signer.py), job push creating DRAFT, and Staging → Publish promotion flow.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write the mop-push CLI guide | edc4b0b | docs/docs/feature-guides/mop-push.md |

## What Was Built

Replaced the two-line stub at `docs/docs/feature-guides/mop-push.md` with a full 205-line operator guide covering:

1. **Install** — `pip install -e .` from repo root, pipx tip for isolation
2. **Login** — OAuth 2.0 Device Authorization Grant (RFC 8628), exact verified CLI output with user code prompt, step-by-step approval flow, credential store path (`~/.mop/credentials.json` at `0600`), session lifetime note
3. **Ed25519 Key Setup** — two generation methods (openssl and admin_signer.py), danger admonition for git/secrets-manager key protection, dashboard registration walkthrough with Key ID note
4. **Push a Job** — hello.py example script, full push command, DRAFT warning admonition
5. **Publish from Staging** — complete DRAFT → ACTIVE promotion via dashboard Staging tab, job lifecycle monitoring (PENDING → ASSIGNED → COMPLETED), output capture
6. **Updating a Job** — `--id` flag for re-pushing existing jobs
7. **Environment Variable Reference** — `MOP_URL` table

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing `openapi.json` strict-mode warning in local `mkdocs build --strict` was already documented in STATE.md decisions from Phase 23-01. It is not caused by this guide and does not affect the Docker build.

## Self-Check

Verifications run:

- `docs/docs/feature-guides/mop-push.md` — 205 lines, DRAFT appears 6 times
- Prerequisites link to `../getting-started/prerequisites.md` — present
- `~/.mop/credentials.json` path — documented in Login section
- Both `openssl` and `admin_signer.py` methods — present
- `!!! danger` admonition for private key — present
- `!!! warning "DRAFT jobs are not dispatched"` — present
- Staging → Publish flow — complete section
- Commit edc4b0b — verified

## Self-Check: PASSED

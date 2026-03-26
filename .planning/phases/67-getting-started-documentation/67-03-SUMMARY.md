---
phase: 67-getting-started-documentation
plan: "03"
subsystem: docs
tags: [documentation, getting-started, first-job, tabbed-content, admonitions]
dependency_graph:
  requires: ["67-01", "67-02"]
  provides: ["DOCS-09", "DOCS-10", "DOCS-11"]
  affects: ["docs/docs/getting-started/first-job.md"]
tech_stack:
  added: []
  patterns: ["pymdownx.tabbed tab pair", "pymdownx.details collapsible block", "danger admonition gate"]
key_files:
  created: []
  modified:
    - docs/docs/getting-started/first-job.md
decisions:
  - "Danger callout placed between the --- separator (after Step 3 tip) and the ## Step 4 heading — outside the tab syntax so it renders as a standalone full-width callout at all screen sizes"
  - "axiom-push promoted as hero command with explicit EE note; CE users directed to Raw API fallback inside collapsible ??? example block"
metrics:
  duration: "83 seconds"
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_modified: 1
---

# Phase 67 Plan 03: First-Job Dispatch Page — Pre-dispatch Callout and Tab Pair Summary

Pre-dispatch danger callout and Dashboard/CLI tab pair added to first-job.md, with axiom-push as CLI hero command and collapsible Raw API curl fallback for CE users.

## What Was Built

- `!!! danger "Register your signing key first"` callout inserted immediately before the Step 4 heading — provides a hard visual stop for users who skip to Step 4
- Step 4 converted from a single dashboard path to a `=== "Dashboard"` / `=== "CLI"` tab pair using pymdownx.tabbed
- CLI tab includes: `axiom-push job push` hero command, `!!! note "axiom-push requires EE"` warning, and a `??? example "Raw API (curl)"` collapsible block with a full curl workflow for CE users
- Steps 1–5 content otherwise unchanged; DOCS-09 (keypair generation and public key registration) satisfied by existing Steps 1–2

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add pre-dispatch danger callout and convert Step 4 to Dashboard/CLI tab pair | af38f85 | docs/docs/getting-started/first-job.md |
| 2 | Full phase verification — all 11 DOCS requirements | (verification only) | none |

## Verification Results

All 11 DOCS requirement content checks passed:

| Check | Requirement | Result |
|-------|------------|--------|
| `grep "tabbed" docs/mkdocs.yml` | DOCS-02 | PASS |
| `grep "ADMIN_PASSWORD" install.md` | DOCS-01 | PASS |
| `grep "docker compose pull" install.md` | DOCS-08 | PASS |
| `grep '"CLI"' enroll-node.md` | DOCS-03 | PASS |
| `grep "master-of-puppets-node:latest" enroll-node.md` | DOCS-04 | PASS |
| `grep -c "EXECUTION_MODE=direct" enroll-node.md` (expect 0) | DOCS-05 | PASS (count=0) |
| `grep "agent:8001" enroll-node.md` | DOCS-06 | PASS |
| `grep "docker.sock" enroll-node.md` | DOCS-07 | PASS |
| `grep "openssl genpkey" first-job.md` | DOCS-09 | PASS |
| `grep "axiom-push job push" first-job.md` | DOCS-10 | PASS |
| `grep "Register your signing key first" first-job.md` | DOCS-11 | PASS |
| `mkdocs build --strict` | Build gate | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- docs/docs/getting-started/first-job.md: FOUND
- Commit af38f85: FOUND

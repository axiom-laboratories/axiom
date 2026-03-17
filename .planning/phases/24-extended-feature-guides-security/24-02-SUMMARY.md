---
phase: 24-extended-feature-guides-security
plan: "02"
subsystem: docs
tags: [documentation, feature-guides, job-scheduling, oauth, authentication]
dependency_graph:
  requires: [24-01]
  provides: [FEAT-03, FEAT-05]
  affects: [docs/docs/feature-guides/job-scheduling.md, docs/docs/feature-guides/oauth.md]
tech_stack:
  added: []
  patterns: [admonition-as-gotcha, placeholder-syntax, cross-linking]
key_files:
  created: []
  modified:
    - docs/docs/feature-guides/job-scheduling.md
    - docs/docs/feature-guides/oauth.md
decisions:
  - "5-field cron documented explicitly; 6-field (seconds) documented as unsupported to prevent silent failures"
  - "API key scoped permissions documented as reserved for future use — matching actual server-side behaviour in _authenticate_api_key()"
  - "Device code in-memory warning added — cross-restart data loss is a real operator trap"
  - "Service principal approach labelled recommended over API key for team CI — follows least-privilege guidance"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-17"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 24 Plan 02: Job Scheduling & OAuth Guides Summary

Job scheduling operator guide and OAuth/authentication guide written in full, replacing placeholder stubs with complete operator-facing content.

---

## What Was Built

### Task 1: job-scheduling.md (147 lines)

Full operator guide for the Job Scheduling feature (FEAT-03). Covers:

- Prerequisites (signed scripts, Ed25519 key in Signatures)
- Creating a Job Definition via the dashboard — all fields documented
- Cron syntax section with 5-field field-order statement, 5-example reference table, crontab.guru tip, 6-field warning
- Node targeting comparison table (4 modes: any / capability / tag / specific node)
- Job lifecycle statuses: DRAFT → ACTIVE → DEPRECATED / REVOKED, with overlap guard explanation
- Retry configuration: max_retries, backoff_multiplier, timeout_minutes
- Staging review cross-link to mop-push.md

### Task 2: oauth.md (178 lines)

Full operator guide for OAuth & Authentication (FEAT-05). Covers:

- Authentication methods overview table (password / device flow / API key)
- Device flow conceptual explanation: RFC 8628, 5-minute TTL, 5-second poll interval, in-memory warning
- Token lifecycle: all JWT fields documented, 24-hour expiry
- Forced invalidation: tv (token_version) mechanism explained — immediate, no TTL wait
- API key usage with Bearer token syntax, scoped-permissions-as-future-use caveat
- Service principal tokens: obtaining, secret rotation, one-time secret display warning
- CI/CD integration: two approaches (API key vs service principal) with concrete placeholder commands

---

## Verification Results

| Check | Result |
|-------|--------|
| job-scheduling.md line count | 147 (min 80) |
| oauth.md line count | 178 (min 80) |
| mop-push cross-link in job-scheduling.md | Present |
| mop-push cross-link in oauth.md | Present |
| rbac cross-link in oauth.md | Present |
| future/scoped permissions caveat in oauth.md | Present |
| mkdocs build — new warnings | None (pre-existing openapi.json warning only) |

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

Files confirmed present:
- `docs/docs/feature-guides/job-scheduling.md` — FOUND
- `docs/docs/feature-guides/oauth.md` — FOUND

Commits confirmed:
- `61846bd` feat(24-02): write job scheduling operator guide — FOUND
- `fc508b3` feat(24-02): write OAuth and authentication operator guide — FOUND

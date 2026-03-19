---
phase: 33-licence-compliance-release-infrastructure
plan: 02
subsystem: compliance
tags: [licence, mpl-2.0, cc-by-4.0, lgpl, apache, certifi, caniuse-lite, paramiko, cloudflare-access, adr]

# Dependency graph
requires:
  - phase: 33-licence-compliance-release-infrastructure-01
    provides: paramiko removal confirmed, python_licence_audit.md and node_licence_audit.md at repo root
provides:
  - LEGAL-COMPLIANCE.md: technical licence compliance assessment for legal team review
  - NOTICE: Apache-style CC-BY-4.0 attribution for caniuse-lite
  - DECISIONS.md: ADR-001 recording /docs/ public access deferral with review triggers
affects:
  - release packaging
  - enterprise buyer due diligence
  - CF Access renewal tracking (2027-03-04)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LEGAL-COMPLIANCE.md as technical licence assessment doc separate from LEGAL.md (CE/EE policy)"
    - "NOTICE in Apache plain-text format for CC-licensed attribution"
    - "DECISIONS.md as lightweight ADR file at repo root"

key-files:
  created:
    - LEGAL-COMPLIANCE.md
    - NOTICE
    - DECISIONS.md
  modified: []

key-decisions:
  - "certifi MPL-2.0 assessed as compliant: read-only CA bundle lookup does not trigger file-level copyleft"
  - "paramiko LGPL-2.1 concern closed by removal (Phase 33-01), no further assessment required"
  - "/docs/ access remains behind CF Access for v10.0; review triggers documented (CE community onboarding OR 2027-03-04 token expiry)"
  - "NOTICE uses Apache plain-text format (not markdown) — standard for Apache-licensed projects"

patterns-established:
  - "Compliance docs use reference links to *_licence_audit.md evidence base, not duplication inline"
  - "ADR format: Date / Status / Decided by / Decision / Rationale / CF Reference / Review Trigger"

requirements-completed: [LICENCE-01, LICENCE-03, RELEASE-03]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 33 Plan 02: Compliance Documentation Summary

**LEGAL-COMPLIANCE.md (certifi MPL-2.0 + paramiko removal), NOTICE (caniuse-lite CC-BY-4.0 attribution), and DECISIONS.md (ADR-001 /docs/ deferral) created at repo root**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T13:13:49Z
- **Completed:** 2026-03-18T13:15:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- LEGAL-COMPLIANCE.md provides a technically accurate, legal-team-readable assessment of certifi MPL-2.0 (compliant, read-only use) and documents paramiko LGPL-2.1 concern as eliminated by removal in Phase 33-01
- NOTICE gives Apache-style plain-text attribution for caniuse-lite (CC-BY-4.0), the only attribution-required npm dependency identified in the v10.0 audit
- DECISIONS.md records ADR-001 with full rationale, CF Access tunnel reference, and concrete review triggers for the /docs/ public access deferral

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LEGAL-COMPLIANCE.md** - `9051ce9` (docs)
2. **Task 2: Create NOTICE and DECISIONS.md** - `e88a9a6` (docs)

**Plan metadata:** see final commit (docs: complete 33-02 plan)

## Files Created/Modified

- `LEGAL-COMPLIANCE.md` — Technical licence compliance document; certifi MPL-2.0 (compliant) and paramiko LGPL-2.1 (removed) assessments; references python_licence_audit.md and node_licence_audit.md
- `NOTICE` — Apache-style third-party attribution for caniuse-lite (CC-BY-4.0, browserslist build toolchain)
- `DECISIONS.md` — ADR-001: /docs/ public access deferred for v10.0, with rationale, CF Access tunnel ID (27bf990f), and review triggers

## Decisions Made

- certifi MPL-2.0 assessment: compliant. `certifi.where()` is a read-only path lookup; MPL-2.0 Section 3.1 file-level copyleft does not apply to read-only consumers of MPL-licensed data.
- NOTICE uses Apache plain-text format (not markdown) — standard convention for Apache-licensed open source projects.
- ADR-001 records the explicit decision to keep /docs/ behind CF Access for v10.0. Review triggers make the deferral bounded, not indefinite.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- LICENCE-01, LICENCE-03, and RELEASE-03 requirements are satisfied
- Phase 33 compliance documentation work is complete; LEGAL.md (CE/EE policy) was not touched
- CF Access service token renewal should be tracked before 2027-03-04 (documented in DECISIONS.md ADR-001)

---
*Phase: 33-licence-compliance-release-infrastructure*
*Completed: 2026-03-18*

## Self-Check: PASSED

- FOUND: LEGAL-COMPLIANCE.md
- FOUND: NOTICE
- FOUND: DECISIONS.md
- FOUND: 33-02-SUMMARY.md
- FOUND: commit 9051ce9 (Task 1)
- FOUND: commit e88a9a6 (Task 2)

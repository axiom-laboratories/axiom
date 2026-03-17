---
phase: 25-runbooks-troubleshooting
plan: "02"
subsystem: docs
tags: [mkdocs, runbooks, troubleshooting, nodes, mtls, enrollment, heartbeat, certificates]

requires:
  - phase: 25-01
    provides: stub nodes.md file and nav entry in mkdocs.yml
  - phase: 24-extended-feature-guides-security
    provides: mtls.md with confirmed anchor targets (certificate-rotation, certificate-revocation, the-join_token)

provides:
  - Full node troubleshooting runbook at docs/docs/runbooks/nodes.md (296 lines)
  - Quick Reference jump table with 10 symptom anchors
  - Enrollment Failures cluster (5 symptom H3s)
  - Heartbeat Loss cluster (3 symptom H3s)
  - Certificate Errors cluster (2 symptom H3s)
  - Cross-links to mtls.md and faq.md (stub)

affects:
  - 25-03
  - 25-04

tech-stack:
  added: []
  patterns:
    - "Per-symptom structure: 2-sentence root cause paragraph + **Recovery steps** numbered list + **Verify it worked** bash block with Expected output + 'If the issue persists' escalation note"
    - "Quick Reference jump table at page top for crisis navigation — plain Markdown table with anchor links to H3 sections"
    - "Healthy-state reference in tip admonition at page top so operators know what success looks like before diagnosing failures"
    - "Cross-link to other guides rather than duplicating procedures (cert rotation, JOIN_TOKEN background)"

key-files:
  created: []
  modified:
    - docs/docs/runbooks/nodes.md

key-decisions:
  - "H3 headers use plain-text readable symptom descriptions (not backtick-wrapped log lines) to ensure reliable MkDocs anchor slug generation for jump table links"
  - "Healthy startup reference placed in tip admonition at top of page — operator orientation before failure diagnosis"
  - "faq.md anchor link included despite faq.md being a stub — link will resolve when plan 25-04 fills the FAQ content"
  - "Certificate revocation warning uses danger/warning admonition placed before numbered steps to preserve list counter continuity (MkDocs admonition-in-list resets counter)"

patterns-established:
  - "Symptom-first H3 headers: plain English observable state, not internal component names"
  - "Every symptom section ends with verify bash command + Expected output line"

requirements-completed:
  - RUN-01

duration: 3min
completed: 2026-03-17
---

# Phase 25 Plan 02: Node Troubleshooting Summary

**Node troubleshooting runbook with 10 symptom sections covering Enrollment Failures, Heartbeat Loss, and Certificate Errors — with exact log strings, numbered recovery steps, and cross-links to mtls.md**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T16:29:08Z
- **Completed:** 2026-03-17T16:31:31Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced the Wave 1 stub with a complete 296-line node troubleshooting runbook
- 10 H3 symptom sections all following the locked per-symptom structure (root cause, recovery steps, verify, escalation)
- Exact log strings from node.py copied verbatim into fenced code blocks (enrollment failure, heartbeat failure, tamper detection)
- 3 cross-links to mtls.md using confirmed anchors from 25-RESEARCH.md; 1 cross-link to faq.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Write nodes.md — full node troubleshooting runbook** - `28f1617` (feat)

**Plan metadata:** (to follow in final commit)

## Files Created/Modified

- `docs/docs/runbooks/nodes.md` - Complete node troubleshooting runbook replacing the stub

## Decisions Made

- H3 headers use plain-text symptom descriptions rather than backtick-wrapped log lines. MkDocs slugifies headers for anchor generation; backticks and emoji in headers produce unpredictable slugs that break jump table links. The H3 text describes the observable symptom; the exact log line appears in the root cause paragraph below.
- Healthy startup reference placed in a tip admonition at page top — before any failure content — so operators can immediately confirm whether their node even attempted enrollment.
- The cross-link to `faq.md#why-does-my-node-appear-multiple-times-in-the-dashboard` is intentional even though faq.md is currently a stub. The link will resolve when plan 25-04 fills the FAQ content. MkDocs non-strict build reports this as an INFO-level warning, not a failure.
- Warning admonitions for irreversible operations (cert revocation permanence) are placed before the numbered recovery steps list, not inside it, to avoid MkDocs list counter reset.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — documentation-only change, no external service configuration required.

## Next Phase Readiness

- nodes.md is complete and cross-links are in place. Plan 25-03 (jobs.md or foundry.md) can proceed independently.
- The faq.md anchor referenced from nodes.md will be live after plan 25-04 executes.
- mkdocs non-strict build passes cleanly (pre-existing warnings from openapi.json and foundry.md anchor issues are unrelated to this plan).

---
*Phase: 25-runbooks-troubleshooting*
*Completed: 2026-03-17*

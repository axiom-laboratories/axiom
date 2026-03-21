---
created: 2026-03-21T21:50:41.075Z
title: Plan User Story Alignment milestone from friction reports (Vol. 1 + Vol. 2)
area: planning
files:
  - mop_validation/reports/user_story_friction.md
  - mop_validation/reports/user_story_friction_2.md
---

## Problem

Two User Story Friction reports have been completed (2026-03-21) identifying eleven operator-facing friction points with agreed solutions. These need to be turned into a formal milestone with phase plans so the work can be scheduled and executed.

### Vol. 1 scenarios

| Scenario | Solution | Blocked |
|---|---|---|
| 1 — Signing friction | Inline keygen (CE), TOTP, key approval (EE) | No |
| 2 — Raw JSON form | Guided mode, View JSON, one-way gate, schema validator | No |
| 3 — Failure visibility | Job detail drawer, Resubmit, Edit and Resubmit | No |
| 4 — Stale scheduled jobs | DRAFT state + three-layer notifications | No |
| 5 — EE terminology (rename) | UI label rename only | No |
| 5 — EE terminology (simplify) | Object model simplification + wizard | Yes — blocked on EE job container architecture |
| SSO | SAML/OIDC auth | Yes — research todo exists separately |

### Vol. 2 scenarios

| Scenario | Solution | Blocked |
|---|---|---|
| 1 — PENDING job diagnosis | Passive dispatch diagnosis drawer + live Queue dashboard + node detail drawer + DRAINING status | No |
| 2 — Empty states + first-run | Contextual empty states per view + onboarding checklist; wizard deferred as QOL | No |
| 3 — Tampered node remediation | 3-path: accept drift / corrective manifest (EE only) / isolate + re-image | No |
| 4 — Cert expiry + auto-renewal | Auto-renewal via mTLS `POST /api/renew` (same node ID, drain+restart); manual re-provision documented as fallback | No |
| 5 — Node onboarding ceremony | Pre-config wizard with template reuse, 4 deployment options, live enrollment status | No |
| 6 — Bulk job operations | Multi-select + floating action bar; bulk cancel / resubmit (retries gate) / delete; confirmation steps | No |

All Vol. 1 scenarios (except EE simplification and SSO) and all Vol. 2 scenarios are fully unblocked. EE object model simplification and SSO are explicitly out of scope for this milestone.

## Solution

1. Read both friction reports in full before planning
2. Run `/gsd:new-milestone` to create the User Story Alignment milestone using both reports as primary input
3. Break into phases — suggested grouping:

   **Phase A: Core job UX** (Vol. 1: Scenarios 2 + 3 / Vol. 2: Scenario 6)
   Job form guided mode, failure detail drawer, resubmit/edit-and-resubmit, bulk job operations. Pure frontend, self-contained, highest operator visibility. Bulk operations shares the Jobs view surface so natural to group.

   **Phase B: Scheduled job health** (Vol. 1: Scenario 4 / Vol. 2: Scenario 1)
   DRAFT state + notifications for stale scheduled jobs, PENDING diagnosis drawer, live Queue dashboard, node detail drawer, DRAINING status. Backend + frontend, moderate scope. These share the "what's happening right now" mental model.

   **Phase C: Security and signing** (Vol. 1: Scenario 1)
   TOTP + inline keygen (CE) + key approval workflow (EE). Security-sensitive, deserves its own phase with careful planning.

   **Phase D: Node lifecycle** (Vol. 2: Scenarios 3 + 4 + 5)
   Tampered node remediation, cert expiry alerting + auto-renewal, node onboarding wizard. All node-lifecycle operations, share backend surface (`pki.py`, `node.py`, `Nodes.tsx`).

   **Phase E: First-run + polish** (Vol. 1: Scenario 5 rename / Vol. 2: Scenario 2)
   Contextual empty states, onboarding checklist, EE UI label rename. Minimal backend, pure UX polish. Can be executed in parallel with other phases or bundled at the end.

4. Ensure EE object model simplification and SSO are explicitly marked as out of scope with references to their blocking dependencies
5. Feed into PROJECT.md and ROADMAP.md

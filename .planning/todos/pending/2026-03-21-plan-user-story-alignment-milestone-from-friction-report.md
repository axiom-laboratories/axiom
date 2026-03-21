---
created: 2026-03-21T21:50:41.075Z
title: Plan User Story Alignment milestone from friction report
area: planning
files:
  - mop_validation/reports/user_story_friction.md
---

## Problem

A User Story Friction report has been completed (2026-03-21) identifying five operator-facing friction points with agreed solutions for each. These need to be turned into a formal milestone with phase plans so the work can be scheduled and executed.

The five scenarios and their implementation status:

| Scenario | Solution | Blocked |
|---|---|---|
| 1 — Signing friction | Inline keygen (CE), TOTP, key approval (EE) | No |
| 2 — Raw JSON form | Guided mode, View JSON, one-way gate, schema validator | No |
| 3 — Failure visibility | Job detail drawer, Resubmit, Edit and Resubmit | No |
| 4 — Stale scheduled jobs | DRAFT state + three-layer notifications | No |
| 5 — EE terminology (rename) | UI label rename only | No |
| 5 — EE terminology (simplify) | Object model simplification + wizard | Yes — blocked on EE job container architecture |
| SSO | SAML/OIDC auth | Yes — research todo exists separately |

Scenarios 1–4 and the Scenario 5 rename are fully unblocked and self-contained. The object model simplification and SSO are explicitly out of scope for this milestone.

## Solution

1. Read `mop_validation/reports/user_story_friction.md` in full before planning
2. Run `/gsd:new-milestone` to create the User Story Alignment milestone using the report as primary input
3. Break into phases — suggested grouping:
   - **Phase A:** Scenarios 2 + 3 (job form guided mode + failure drawer) — pure frontend, self-contained, highest operator visibility
   - **Phase B:** Scenario 4 (DRAFT state + notifications) — backend + frontend, moderate scope
   - **Phase C:** Scenario 1 (TOTP + inline keygen + key approval workflow) — security-sensitive, deserves its own phase with careful planning
   - **Phase D:** Scenario 5 rename (UI label changes only) — can be bundled with any other phase, minimal effort
4. Ensure EE object model simplification and SSO are explicitly marked as out of scope with references to their blocking dependencies
5. Feed into PROJECT.md and ROADMAP.md

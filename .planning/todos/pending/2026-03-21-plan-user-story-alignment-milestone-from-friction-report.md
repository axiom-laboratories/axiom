---
created: 2026-03-21T21:50:41.075Z
title: Plan User Story Alignment milestone from friction reports (Vol. 1 + Vol. 2 + Vol. 3)
area: planning
files:
  - mop_validation/reports/user_story_friction.md
  - mop_validation/reports/user_story_friction_2.md
  - mop_validation/reports/user_story_friction_3.md
---

## Problem

Three User Story Friction reports have been completed identifying seventeen operator-facing friction points with agreed solutions. These need to be turned into a formal milestone with phase plans so the work can be scheduled and executed.

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

### Vol. 3 scenarios

| Scenario | Solution | Blocked |
|---|---|---|
| 1 — Alert management | Lifecycle states, bulk-acknowledge with `acknowledged_by` logging, auto-clear, maintenance windows (per-node + fleet-wide) | No |
| 2 — Audit log usability | Filter bar (date range, actor, action type), free text search, export (CSV + JSON) | No |
| 3 — Scheduled job health dashboard | Dedicated panel on Dashboard, aggregate counts, per-definition health indicators, miss detection, time window toggle | No |
| 4 — Secret management | EE-only native secret store, Fernet encryption, server-side injection, stdout/stderr redaction, Azure Key Vault RBAC | No — **EE dedicated milestone** |
| 5 — Multi-node fan-out | Tier 1: node-pinning (`target_node_ids` filter) now; Tier 2: campaign model as follow-on milestone | Tier 2 blocked on Tier 1 |
| 6 — Outbound webhooks | Webhook-only transport, per-endpoint event subscriptions, HMAC-signed payloads, retry + dead-letter log | No |

**Out of scope for this milestone:** EE object model simplification, SSO, secret management (EE dedicated milestone), fan-out campaigns (follow-on milestone), parallel swarming (research todo).

## Solution

1. Read all three friction reports in full before planning
2. Run `/gsd:new-milestone` to create the User Story Alignment milestone using all three reports as primary input
3. Break into phases — suggested grouping:

   **Phase A: Core job UX** (V1: S2+S3 / V2: S6)
   Job form guided mode, failure detail drawer, resubmit/edit-and-resubmit, bulk job operations. Pure frontend, self-contained, highest operator visibility.

   **Phase B: Scheduled job health + queue visibility** (V1: S4 / V2: S1 / V3: S3)
   DRAFT state + notifications, PENDING diagnosis drawer, live Queue dashboard, node detail drawer, DRAINING status, scheduled job health panel on Dashboard. Share the "what's happening right now" mental model and WebSocket infrastructure.

   **Phase C: Security and signing** (V1: S1)
   TOTP + inline keygen (CE) + key approval workflow (EE). Security-sensitive, deserves its own phase.

   **Phase D: Node lifecycle** (V2: S3+S4+S5 / V3: S1 partial)
   Tampered node remediation, cert expiry + auto-renewal, node onboarding wizard, node-pinning (`target_node_ids`), per-node maintenance windows. All share `pki.py`, `node.py`, `Nodes.tsx` surface.

   **Phase E: Observability + integrations** (V3: S1+S2+S6)
   Alert management (bulk-acknowledge, auto-clear, fleet-wide maintenance rules), audit log filtering + export, outbound webhooks. V3 S6 sequenced after Phase B (alert + notification surfaces must be stable first).

   **Phase F: First-run + polish** (V1: S5 rename / V2: S2)
   Contextual empty states, onboarding checklist, EE UI label rename. Minimal backend, pure UX polish. Can run in parallel with other phases.

4. Ensure the following are explicitly marked out of scope with blocking dependency references:
   - EE object model simplification (blocked on EE job container architecture)
   - SSO (research todo exists separately)
   - Secret management (EE dedicated milestone)
   - Fan-out campaigns (follow-on milestone, requires node-pinning Tier 1 first)
   - Parallel swarming (research todo exists separately)
5. Feed into PROJECT.md and ROADMAP.md

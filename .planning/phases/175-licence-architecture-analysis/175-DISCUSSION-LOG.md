# Phase 175: Licence Architecture Analysis — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 175-licence-architecture-analysis
**Areas discussed:** Option B definition, Air-gap weight, Recommendation horizon, Hosted server todo

---

## Option B Definition

| Option | Description | Selected |
|--------|-------------|----------|
| Hosted VPS licence server | Dedicated FastAPI + Postgres on a cheap VPS — adds revocation, deployment check-in, deployment registry | ✓ |
| Embedded in existing MoP PostgreSQL | Store issued licences in the main master_of_puppets DB | |
| Both sub-options as B1/B2 | Analyse both as sub-variants | |

**User's choice:** Hosted VPS server — with explicit rejection of embedding in MoP's DB ("why would we host the license in the database of the tool we're licensing?")

**Notes:** User also raised the question of what other options exist (public hash in a public repo, etc.). Claude offered B1/B2 framing but the conversation evolved to confirm the VPS approach is the meaningful Option B.

---

## Air-Gap Weight

| Option | Description | Selected |
|--------|-------------|----------|
| Hard constraint | Eliminates options requiring internet for air-gapped tier | ✓ |
| Scored dimension | One of six dimensions in the comparison table | |

**User's choice:** Hard constraint for air-gapped tier customers — not just a dimension to score.

**Notes:** Resolved organically as part of the two-tier licence model discussion. Air-gapped customers get a long-TTL JWT with no check-in requirement; the constraint is baked into the tier design rather than the comparison table scoring.

---

## Recommendation Horizon

| Option | Description | Selected |
|--------|-------------|----------|
| Two-phase (now + future) | Keep current for now; wireframe scaled VPS for post-launch | ✓ |
| Best option now | Pick the winner for current state only | |
| Best option long-term | Pick the winner for final architecture | |

**User's choice:** Two-phase — "keep it as it is for now, but wireframe/plan out a scaled option for once we release the tool to the public."

**Notes:** User confirmed there's no VPS currently. The recommendation is explicitly staged: Git repo is fine pre-launch; VPS licence server is the post-launch upgrade path.

---

## Hosted Server Todo

| Option | Description | Selected |
|--------|-------------|----------|
| Fold into this analysis | Absorb as future-state wireframe section in LIC-ANALYSIS.md | ✓ |
| Keep separate | Leave as a standalone future task | |

**User's choice:** Folded in — the VPS investigation todo becomes the basis for the future-state wireframe section of LIC-ANALYSIS.md.

---

## Two Licence Tiers (emerged during discussion)

This was not a pre-identified gray area but emerged naturally.

**User's proposal:** Two licence types — "online" (phones home, remotely revocable) and "air-gapped" (lifetime/extended, no check-in).

**Claude's response:** Not overcomplicating — this is the right abstraction. Implemented as a single JWT format with `deployment_mode: online|airgapped` claim + different TTL. One code path, branching on the claim. Online failure = 7-day buffer. Air-gapped = premium pricing reflecting reduced vendor control.

**User's decision:** Agreed.

---

## Claude's Discretion

- Exact TTL values for online vs air-gapped licences
- Whether to include a fourth option (public hash registry) in the comparison table
- Effort estimate format for migration path

## Deferred Ideas

- VPS licence server implementation — post-Phase-175 (LIC-IMPL-01)
- Licence issuance portal / customer UI (DIST-04 / LIC-IMPL-02)
- Short-lived JWT rotation (hard online mode) — flagged as premature

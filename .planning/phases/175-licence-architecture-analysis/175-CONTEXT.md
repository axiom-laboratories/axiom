# Phase 175: Licence Architecture Analysis — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce `.planning/LIC-ANALYSIS.md` — a structured, evidence-based comparison of three
issued-licence storage approaches with a concrete recommendation and a wireframe of the
scaled future architecture. Purely analytical: no code changes, no implementation.

**Not in scope:** implementing any architecture change; adding online check-in to
`licence_service.py`; VPS provisioning; changing the JWT format.

</domain>

<decisions>
## Implementation Decisions

### What the Licence Is (framing for the analysis)

- **D-01:** The licence is a vendor-issued EE feature gate — an Ed25519-signed JWT
  (`AXIOM_LICENCE_KEY`) that customers set as an env var. Their Axiom instance validates it
  locally against the public key. No internet required for validation. The "storage" question
  is entirely about where **the vendor** (us) keeps issuance records and audit trails — not
  about how customers validate their licences.

### Option B Reframing

- **D-02:** "Database embedded in axiom-ee" is a non-starter — you do not store licence
  records in the DB of the product being licensed. Option B is reframed as a **hosted VPS
  licence server**: a dedicated FastAPI + Postgres/SQLite service on a cheap VPS (Hetzner,
  Fly.io, etc.) providing an issuance ledger, check-in API, and remote revocation. The
  pending todo "Investigate feasibility of hosted licence server on VPS" is absorbed into
  this analysis as the future-state wireframe.

### Two Licence Tiers (first-class design decision)

- **D-03:** Two licence tiers are the right abstraction — not overcomplication. Implemented
  as a single JWT format with one extra claim and different TTL:
  - `deployment_mode: online` — short TTL (30–90 days), auto-renewed via VPS check-in,
    remotely revocable. Standard pricing.
  - `deployment_mode: airgapped` — long TTL (1–3 years), no check-in, expires at a fixed
    date. Premium pricing reflects reduced vendor control (no revocation path).
  - One code path in `licence_service.py`, branching on the `deployment_mode` claim.
  - Online mode check-in failure = 7-day buffer before degrading, not instant death.

### Recommendation Horizon (two-phase)

- **D-04:** The recommendation is explicitly two-phase:
  1. **Now (pre-public launch):** Keep the current Git repo approach. It works, costs
     nothing, is fully air-gap compatible, and revocation/visibility problems don't exist
     until there are paying customers.
  2. **At scale (post-public launch):** Implement the VPS licence server for online-tier
     customers. Air-gapped licences remain on the Git repo approach indefinitely.
  The analysis document doubles as a design doc for the future architecture.

### Air-Gap Compatibility

- **D-05:** Air-gap compatibility is a **hard requirement** for air-gapped-tier customers,
  not just a scored dimension. The comparison table still scores all six dimensions for all
  three options, but the recommendation section must explicitly preserve air-gap support
  as non-negotiable for that tier.

### Analysis Structure

- **D-06:** `LIC-ANALYSIS.md` must contain:
  1. Comparison table — three options × six dimensions (security, auditability,
     air-gap compatibility, operational complexity, CI/CD integration, recovery from data loss)
  2. "Why this over the others" rationale section with a single concrete recommendation
  3. If recommendation ≠ current: migration path with effort estimate
  4. Future architecture wireframe — VPS licence server design (API surface, hosting,
     check-in flow, revocation, the two-tier `deployment_mode` model)
  This last section is new beyond LIC-01/02/03 requirements but is the natural output
  of this discussion.

### Claude's Discretion

- Exact TTL values for online vs air-gapped licences (30/90 days vs 1/2/3 years) — Claude
  picks reasonable defaults for the wireframe.
- Whether to include a fourth option (public hash registry in a public Git repo) in the
  table, or limit to three as the roadmap specifies.
- Effort estimate format for migration path (T-shirt size is fine).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §LIC — LIC-01, LIC-02, LIC-03 definitions
- `.planning/ROADMAP.md` §Phase 175 — success criteria and plan list

### Current Architecture
- `axiom-licenses/README.md` — current issuance tooling overview, key material, air-gap mode
- `axiom-licenses/tools/issue_licence.py` — how licences are issued and audit records committed to GitHub
- `axiom-licenses/tools/list_licences.py` — how issued licences are queried
- `puppeteer/agent_service/services/licence_service.py` — JWT validation, LicenceState, LicenceStatus, boot log

### Pending Investigation (absorb as future-state wireframe)
- `.planning/todos/pending/2026-04-11-investigate-hosted-licence-server-vps.md` — VPS licence
  server design: check-in patterns (A/B/C), API surface, privacy considerations, client-side
  changes to `licence_service.py`. Use this as the basis for the future-state section.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `axiom-licenses/tools/issue_licence.py` — current issuance flow; the `commit_to_github()`
  function shows exactly what the Git repo approach does and what would need to change
- `puppeteer/agent_service/services/licence_service.py` — JWT fields already present:
  `customer_id`, `tier`, `exp`, `features`, `node_limit`, `grace_days`. Adding
  `deployment_mode` claim is a one-line change to the issuer and a branch in `load_licence()`.

### Established Patterns
- Ed25519-signed JWT with local public key validation — no library changes needed for the
  two-tier model, only a new claim
- `AXIOM_LICENCE_KEY` env var delivery — unchanged for both tiers
- YAML audit records in `axiom-licenses/licenses/issued/` — zero issued licences today
  (empty dir), so migration cost from Git → DB is effectively zero

### Integration Points
- The VPS wireframe connects to `licence_service.py` via `AXIOM_LICENCE_SERVER_URL` env var
  (optional; absence = air-gapped mode automatically)
- Key rotation note in `axiom-licenses/README.md` is relevant to the security dimension
  of the comparison table

</code_context>

<specifics>
## Specific Ideas

- Two-tier model: `deployment_mode: online|airgapped` claim in JWT — same format, different
  TTL and check-in behaviour. Online = short TTL + auto-renew + revocable. Air-gapped =
  long TTL + premium pricing + no revocation.
- Online check-in failure: 7-day buffer before degrading to CE (not instant death)
- VPS stack: FastAPI + SQLite/Postgres, Caddy TLS, Hetzner CX11 or Fly.io — same pattern
  as main stack
- Current migration cost: effectively zero (no issued licences yet) — worth noting in the
  analysis as a factor that makes "migrate now vs later" less loaded

</specifics>

<deferred>
## Deferred Ideas

- Implementing the VPS licence server — belongs in a post-Phase-175 implementation phase
  (LIC-IMPL-01 in REQUIREMENTS.md)
- Licence issuance portal / customer-facing web UI (DIST-04 / LIC-IMPL-02)
- Short-lived JWT rotation (Option B hard mode from the todo) — flagged as "premature at
  this stage" in the todo; not recommended for the wireframe
- Adding `deployment_mode` claim to `licence_service.py` now — no implementation this phase

</deferred>

---

*Phase: 175-licence-architecture-analysis*
*Context gathered: 2026-04-21*

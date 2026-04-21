---
gsd_state_version: 1.0
milestone: v25.0
milestone_name: — EE Validation & Infrastructure
status: completed
last_updated: "2026-04-21T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 7
  completed_plans: 7
  percent: 100
---

# Session State — v25.0 Roadmap

## Project Reference

**Core Value:** Secure, pull-based job orchestration across heterogeneous node fleets — with mTLS identity, Ed25519-signed execution, and container-isolated runtime

**Milestone:** v25.0 — EE Validation & Infrastructure  
**Target:** Validate that axiom-ee behaves as specified under adversarial conditions; migrate mop_validation to the axiom GitHub org; produce a structured recommendation on licence repo architecture

See: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md` (pending), `.planning/ROADMAP.md` (pending)

## Current Position

**Milestone:** v25.0  
**Status:** All phases complete — milestone ready for review  
**Last phase (v25.0):** Phase 175 — Licence Architecture Analysis (complete, 1 plan executed 2026-04-21)  
**Next phase (v25.0):** None — milestone complete

## Milestone Goals

1. **EE Behavioural Validation** — Confirm CE/EE segregation, licence gating (VALID/GRACE/EXPIRED/CE state machine), feature flags, wheel security chain, and boot-log enforcement behave as specified. Include adversarial scenarios: tampered wheel, invalid/expired licence, licence-absent boot, node limit enforcement.

2. **Repo Migration** — Move `mop_validation` from its current location to the `axiom` GitHub organisation as a private repo. All tooling, test scripts, and secrets management should continue working post-migration.

3. **Licence Repo Architecture Analysis** — Structured comparison of:
   - Current: separate private Git repo (`axiom-licences`) for issued licence storage
   - Alternative A: database (in `axiom-ee` service or new service)
   - Alternative B: hybrid (DB as source of truth, Git snapshot for audit/air-gap)
   
   Deliver a concrete recommendation with rationale, not just a comparison table.

## Accumulated Context

### From v24.0 Completion

- CE/EE model isolation enforced via separate `DeclarativeBase`: `Base` (15 CE tables) and `EE_Base` (26 EE tables)
- `init_db()` conditionally creates EE tables only when EE plugin is loaded
- `require_permission()` checks both metadata sets for `role_permissions` table
- Alembic tracks both `Base.metadata` and `EE_Base.metadata`
- EE wheel verification: 6-step gate (existence → JSON → fields → SHA256 → decode → Ed25519) in `_verify_wheel_manifest()`
- Boot log uses HMAC-SHA256 keyed on `ENCRYPTION_KEY`; backward-compatible with legacy SHA256 entries
- Entry point whitelist: `ep.value == "ee.plugin:EEPlugin"` exact match
- Licence validation: `licence_service.py` in CE code; VALID/GRACE/EXPIRED/CE state machine; offline Ed25519 JWT

### Sister Repos

- `~/Development/axiom-ee` — EE plugin source; `ee/plugin.py` is the entry point
- `~/Development/mop_validation` — validation tooling (to be migrated in this milestone)
- `axiom-licences` (GitHub, private) — issued licence storage (architecture under review)

### Open Deferred Items (pre-v25.0)

- Verification gaps: Phase 12, 19, 159 (pre-v24.0, human_needed/gaps_found)
- TODO: `2026-04-11-investigate-hosted-licence-server-vps.md` — relevant to goal 3

## Files

- `.planning/REQUIREMENTS.md` — to be created during requirements phase
- `.planning/ROADMAP.md` — to be created during roadmap phase
- `.planning/STATE.md` — this file

---

**Milestone planning started:** 2026-04-20  
**Status:** PLANNING — requirements definition in progress

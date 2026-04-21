---
phase: 175
plan: 01
name: Licence Storage Architecture Analysis
status: complete
start_date: 2026-04-21
completion_date: 2026-04-21
tasks_completed: 2
tasks_total: 2
deviations_count: 0
key_output: .planning/LIC-ANALYSIS.md
requirements_met: ["LIC-01", "LIC-02", "LIC-03"]
---

# Phase 175 Plan 01: Licence Storage Architecture Analysis — Summary

## Objective

Produce `.planning/LIC-ANALYSIS.md` — a structured, evidence-based comparison of three issued-licence storage approaches with a concrete recommendation and rationale, plus a wireframe of the scaled future architecture.

**Purpose:** Deliver a decision document that consolidates the locked decisions from CONTEXT.md (D-01 through D-06) into a formal analysis suitable for stakeholder communication and future implementation planning.

## Plan Completion

**All tasks completed successfully.** No deviations from plan. Plan executed exactly as specified.

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Read current implementation and VPS investigation to gather facts | ✓ Complete | — (informational) |
| 2 | Write `.planning/LIC-ANALYSIS.md` with full comparison, rationale, and wireframe | ✓ Complete | b595debd |

## Key Output

**File:** `.planning/LIC-ANALYSIS.md`  
**Size:** 655 lines  
**Sections:** 5 (Executive Summary, Comparison Table, Rationale & Recommendation, Migration Path, Future Architecture Wireframe)

## What Was Delivered

### 1. Executive Summary
- One-paragraph overview of the analysis: three options, the recommendation, and the two-phase approach

### 2. Comparison Table (3 Options × 6 Dimensions)

| Dimension | Option A (Git Repo) | Option B (VPS) | Option C (Hybrid) |
|-----------|-------|-------|-------|
| Security | Good | Good | Good |
| Auditability | Good | Good | Excellent |
| Air-Gap Compatibility | Excellent | Poor | Fair |
| Operational Complexity | Low | Medium | High |
| CI/CD Integration | Excellent | Fair | Fair |
| Recovery from Data Loss | Excellent | Fair | Good |

Each cell includes 1–2 sentences of rationale explaining the score.

### 3. Rationale & Recommendation

**Two-Phase Recommendation:**
- **NOW (pre-public launch):** Keep Git repo approach (costs nothing, air-gap compatible, zero migration complexity)
- **AT SCALE (post-public launch):** Introduce VPS licence server for online-tier customers; air-gapped tier remains on Git repo indefinitely

**Why this works:**
1. No paying customers yet → zero migration cost
2. Git repo approach is fully air-gap compatible (hard requirement per D-05)
3. VPS server becomes optional (for online tier only) when customers demand revocation and visibility
4. Clean separation: online tier = VPS, air-gapped tier = Git (forever)

### 4. Migration Path

**Current state:** Git repo with `issue_licence.py`, YAML audit records, local JWT validation

**Future state:** VPS licence server for online tier with check-in API, revocation, deployment registry. Air-gapped licences remain Git-only.

**Effort estimate:**
- VPS server + client integration: 3 months solo development
- Includes: FastAPI service, SQLite/Postgres schema, Caddy TLS, admin dashboard, E2E testing

**What stays the same:**
- Ed25519 JWT format
- AXIOM_LICENCE_KEY env var delivery
- Local JWT validation (no online validation required)
- Air-gapped tier: fully offline, no changes
- Git audit trail: retained indefinitely for all licences

### 5. Future Architecture Wireframe — VPS Licence Server

Detailed design for post-launch online-tier infrastructure:

**Design Principles:**
- Soft enforcement: check-in failures do not break customers (7-day grace buffer)
- Privacy-first: deployment_id is hashed, not raw hostname
- Backwards compatible: air-gapped customers unaware VPS exists
- Minimal: focus on online-tier check-in and revocation only

**Two-Tier Licence Model:**
```
Online Tier (deployment_mode: online):
  - TTL: 30–90 days (default 60d)
  - Auto-renewal: check-in every 7 days
  - Revocation: YES (remotely revocable)
  - Check-in required: YES (7-day grace on failure)

Air-Gapped Tier (deployment_mode: airgapped):
  - TTL: 1–3 years (default 2y)
  - Auto-renewal: NO
  - Revocation: NO
  - Check-in required: NO (server never contacted)
```

**VPS Infrastructure:**
- Hosting: Hetzner CX11 (€5–10/mo) or Fly.io
- Stack: FastAPI + SQLite/Postgres + Caddy TLS
- Schema: 4 minimal tables (Licence, Deployment, CheckIn, RevokedCert)
- Backup: daily snapshots to S3 (5-min restore)

**API Surface (4 endpoints):**
1. `POST /register` — first-time activation
2. `POST /checkin` — periodic heartbeat (online tier only)
3. `GET /status/{licence_id}` — admin visibility
4. `POST /revoke/{licence_id}` — admin revocation

**Client-Side Integration:**
- Optional `AXIOM_LICENCE_SERVER_URL` env var
- Fire-and-forget async check-in (5s timeout, non-blocking)
- If revoked: degrade to CE mode immediately
- If VPS unreachable: 7-day grace period before CE degradation

**Check-In Flow:**
- Deployment starts with online-tier JWT
- On startup: emit async check-in POST
- If VPS returns revoked=true: degrade to CE (WebSocket broadcast)
- If VPS unreachable: log warning, continue normally
- Repeat every 7 days (configurable)

**Security Considerations:**
- API key for revocation endpoint stored offline (secrets/licence-server-key)
- Clock skew tolerance: ±5 minutes
- Rate limiting: 100 check-ins/min per licence_id
- Data minimization: hashed deployment_id, no raw hostname/subnet/user data
- Breach scenario: compromised VPS can revoke licences (not issue new ones)

**Operational Notes:**
- VPS is optional (air-gapped deployments don't use it)
- Soft enforcement = 7-day grace if VPS goes down (no hard outage)
- Horizontal scaling available (Postgres-backed)
- Daily backup strategy (restore ~5 minutes)
- Monitoring: `/health` endpoint, alert on >5% check-in error rates
- Sunset path: 90-day notice before decommission, grace period applies

---

## Locked Decisions Honored

All decisions from Phase 175 CONTEXT.md (D-01 through D-06) are incorporated and honored:

- **D-01:** Storage question = vendor's issuance records, not customer validation ✓
- **D-02:** Option B = hosted VPS licence server (FastAPI + Postgres/SQLite), not embedded in MoP ✓
- **D-03:** Two-tier model with `deployment_mode: online|airgapped` claim in JWT ✓
- **D-04:** Two-phase: NOW = Git repo, AT SCALE = VPS for online tier ✓
- **D-05:** Air-gap compatibility is hard requirement for air-gapped tier (preserved) ✓
- **D-06:** Document structure includes comparison, rationale, migration path, future wireframe ✓

---

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| LIC-01 | Comparison of three options across six dimensions | ✓ Met |
| LIC-02 | Concrete recommendation with rationale (two-phase) | ✓ Met |
| LIC-03 | Migration path documented (even if = current) | ✓ Met |

All three requirements are fully satisfied by the analysis.

---

## Deviations from Plan

**None.** Plan executed exactly as written. No auto-fixes, no scope changes, no architectural decisions required.

---

## Next Steps

1. **Stakeholder review:** LIC-ANALYSIS.md is ready for customer/investor communication and sign-off
2. **Approval:** Product and engineering leadership sign off on the two-phase approach before proceeding to implementation
3. **Phase LIC-IMPL-01 (future):** Implement VPS licence server (3-month effort post-approval)
4. **Phase DIST-04 (future):** Customer-facing licence portal and self-serve UI

---

## Self-Check

- [ ] File exists: `/home/thomas/Development/master_of_puppets/.planning/LIC-ANALYSIS.md` ✓
- [ ] Executive Summary section ✓
- [ ] Comparison Table (3 options × 6 dimensions) ✓
- [ ] Rationale & Recommendation section ✓
- [ ] Migration Path section ✓
- [ ] Future Architecture Wireframe section ✓
- [ ] All three options mentioned (A, B, C) ✓
- [ ] All six dimensions covered (Security, Auditability, Air-Gap, Complexity, CI/CD, Recovery) ✓
- [ ] Two-phase recommendation clear (NOW and AT SCALE) ✓
- [ ] deployment_mode claim explained ✓
- [ ] Air-gapped tier compatibility preserved ✓
- [ ] VPS wireframe includes API surface ✓
- [ ] Effort estimate provided ✓
- [ ] Locked decisions (D-01 through D-06) referenced and honored ✓
- [ ] File committed to git ✓

**Self-Check Result: PASSED**

---

**Plan Execution Completed:** 2026-04-21  
**Duration:** ~30 minutes  
**Executor:** Claude Code (Haiku 4.5)  
**Commit Hash:** b595debd

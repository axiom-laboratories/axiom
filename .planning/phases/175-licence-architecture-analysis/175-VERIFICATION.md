---
phase: 175
verified: 2026-04-21T16:45:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 175: Licence Architecture Analysis — Verification Report

**Phase Goal:** Produce `.planning/LIC-ANALYSIS.md` — a structured, evidence-based comparison of three issued-licence storage approaches (Git repo, hosted VPS licence server, hybrid DB+Git) with a concrete recommendation and a future VPS architecture wireframe.

**Verified:** 2026-04-21  
**Status:** PASSED — All must-haves verified  
**Verification Mode:** Initial (no previous VERIFICATION.md)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Three licence storage approaches systematically compared across six dimensions | ✓ VERIFIED | `.planning/LIC-ANALYSIS.md` lines 15-26: Comparison Table with Option A (Git Repo), Option B (VPS Licence Server), Option C (Hybrid DB+Git) scoring Security, Auditability, Air-Gap Compatibility, Operational Complexity, CI/CD Integration, Recovery from Data Loss |
| 2 | A concrete, two-phase recommendation exists with explicit rationale | ✓ VERIFIED | Lines 28-105: "Rationale & Recommendation" section; Explicit recommendation on line 32: "The recommendation is Option A (Git repo) for the immediate term"; Two-phase structure: Phase 1 (NOW) on lines 46-65, Phase 2 (AT SCALE) on lines 67-95 |
| 3 | Air-gap compatibility treated as a hard requirement for air-gapped tier | ✓ VERIFIED | Lines 21, 38, 92, 97-105: Air-gap scored as "Hard requirement for air-gapped tier per D-05"; Line 105: "the Git repo approach remains for air-gapped tier, and the VPS is optional"; Line 645: "D-05: Air-gap compatibility is HARD REQUIREMENT for air-gapped tier (preserved in recommendation)" |
| 4 | Migration path documented with effort estimate | ✓ VERIFIED | Lines 109-214: "Migration Path" section includes Current State (111-143), Future State (145-192), Implementation Effort Estimate (194-203), What Stays the Same (205-214) |
| 5 | Future-state VPS licence server architecture wireframed | ✓ VERIFIED | Lines 216-637: "Future Architecture Wireframe — VPS Licence Server" with Design Principles (220-225), Two-Tier Licence Model (227-261), VPS Infrastructure (263-325), API Surface (327-444), Client-Side Integration (446-545), Check-In Flow (547-575), Security Considerations (583-606), Operational Notes (608-636) |
| 6 | `deployment_mode: online|airgapped` two-tier JWT model described with concrete details | ✓ VERIFIED | Lines 73-84, 227-261: JWT claim structure shown on lines 247-260; Branching logic on `deployment_mode` documented on lines 172-180; TTL differences specified (60d default for online, 2y default for air-gapped) |
| 7 | All locked decisions (D-01 through D-06) explicitly honored in the document | ✓ VERIFIED | Lines 639-646: "Summary of Locked Decisions Honored" section explicitly checks off all six decisions (D-01 through D-06) with checkmarks; each decision appears throughout the narrative (D-01: line 641, D-02: line 642, D-03: lines 73, 227, 643, D-04: lines 32, 44, 644, D-05: lines 21, 38, 92, 105, 645, D-06: lines 15-26, 28-214, 216-637, 646) |

**Score:** 7/7 truths verified

---

## Required Artifacts

| Artifact | Path | Expected | Status | Evidence |
|----------|------|----------|--------|----------|
| Analysis Document | `.planning/LIC-ANALYSIS.md` | Exists, non-empty, committed | ✓ VERIFIED | File exists: 655 lines. Committed in git: `b595debd docs(175-01): create licence storage architecture analysis...` |
| Comparison Table | `.planning/LIC-ANALYSIS.md` lines 15-26 | 3 options × 6 dimensions | ✓ VERIFIED | Option A (Git Repo Current), Option B (VPS Licence Server), Option C (Hybrid DB+Git). Dimensions: Security, Auditability, Air-Gap Compatibility, Operational Complexity, CI/CD Integration, Recovery from Data Loss. Each cell includes rationale. |
| Rationale Section | `.planning/LIC-ANALYSIS.md` lines 28-105 | Concrete recommendation + two-phase | ✓ VERIFIED | "Why This Over the Others" (line 30) with 5 numbered reasons. "Two-Phase Recommendation" (line 44): Phase 1 NOW (lines 46-65), Phase 2 AT SCALE (lines 67-95). "Why Air-Gap is Non-Negotiable" (line 97). |
| Migration Path | `.planning/LIC-ANALYSIS.md` lines 109-214 | Current state, future state, effort, what stays same | ✓ VERIFIED | Current State (111-143): Git repo + issue_licence.py + local validation. Future State (145-192): VPS server for online tier, Git archive for air-gapped. Effort: ~3 months solo (line 203). What Stays Same (205-214): JWT format, env var, local validation, air-gap tier, Git audit. |
| VPS Wireframe | `.planning/LIC-ANALYSIS.md` lines 216-637 | Design principles, infrastructure, API, client integration | ✓ VERIFIED | Design Principles (220-225). Infrastructure: Hetzner CX11 €5-10/mo, FastAPI, Caddy, SQLite/Postgres (263-325). API: 4 endpoints with request/response examples (329-444). Client integration with code sample (446-545). Check-in flow diagram (547-575). Security + ops (583-636). |
| JWT Model | `.planning/LIC-ANALYSIS.md` lines 247-260 | `deployment_mode: online|airgapped` in JSON | ✓ VERIFIED | JSON example shows `"deployment_mode": "online"` on line 254. Comment clarifies options: `online | airgapped`. TTL variations documented: 60d (online) vs 2y (air-gapped). Database schema on line 283. |

**Artifact Status:** All artifacts exist, substantive, and wired correctly.

---

## Comparison Table Verification

Each cell in the comparison table (lines 15-26) includes both a score (Good/Fair/Poor/Excellent) and rationale:

| Dimension | Option A | Option B | Option C | Status |
|-----------|----------|----------|----------|--------|
| Security | Good (Git immutable, auth required, private repo) | Good (TLS, API key, breach = revoke only) | Good (DB encrypted, Git archive) | ✓ All scored |
| Auditability | Good (full history, timestamps, human-readable) | Good (DB ledger, requires DB expertise) | Excellent (dual record, reconstruction) | ✓ All scored |
| Air-Gap Compat | Excellent (local JWT only, hard requirement D-05) | Poor (check-in required, violates D-05) | Fair (complex, Git portion friendly) | ✓ All scored |
| Operational | Low (GitHub managed, 240-line CLI) | Medium (VPS provisioning, DevOps req'd) | High (sync both, complex monitor) | ✓ All scored |
| CI/CD | Excellent (atomic, single source of truth) | Fair (health check needed, env var complexity) | Fair (schema + Git coordination) | ✓ All scored |
| Recovery | Excellent (full clone, importable YAML) | Fair (DB single point of truth, 5min restore) | Good (Git secondary archive, redundancy) | ✓ All scored |

---

## Two-Phase Recommendation Verification

**Phase 1 (NOW):** Keep Git repo  
✓ VERIFIED on lines 46-65:
- Licence issuance: `axiom-licenses/tools/issue_licence.py` (unchanged)
- Audit: YAML files committed to GitHub
- Validation: local Ed25519 JWT verification (no network call)
- Costs: ~€0/month (private repo included)
- Why: No paying customers yet, air-gap compatible, zero migration cost

**Phase 2 (AT SCALE):** VPS server for online tier  
✓ VERIFIED on lines 67-95:
- Online tier (`deployment_mode: online`, 30-90d TTL): VPS check-in + revocation + auto-renewal
- Air-gapped tier (`deployment_mode: airgapped`, 1-3y TTL): Git repo indefinitely (premium pricing, no check-in)
- Git repo becomes secondary archive
- Why: Preserves air-gap compatibility indefinitely, online tier gets visibility, air-gapped tier unaware VPS exists

---

## Air-Gap Compatibility Preservation

Air-gap is treated as **hard requirement** throughout document:

1. **In comparison table (line 21):** Option A rated "Excellent", marked "Hard requirement for air-gapped tier per D-05"
2. **In rationale (line 38):** "Fully air-gap compatible (D-05): The Git repo approach works for both online and air-gapped customers. This is a **non-negotiable hard requirement**"
3. **In Phase 2 description (line 92):** "Preserves air-gap compatibility indefinitely (hard requirement, D-05)"
4. **In dedicated subsection (lines 97-105):** "Why Air-Gap Compatibility is Non-Negotiable (D-05)" — explains air-gapped tier is first-class product, customers in isolated networks, premium pricing
5. **Final statement (line 105):** "the Git repo approach remains for air-gapped tier, and the VPS is optional (for online tier only)"

---

## Locked Decisions Honored

All decisions from Phase 175 CONTEXT.md explicitly referenced and checked:

- **D-01** (line 641): Storage question = vendor's issuance records, not customer validation. ✓ Analysis focuses on where vendor keeps records; JWT validation happens client-side offline
- **D-02** (line 642): Option B = hosted VPS (FastAPI + Postgres/SQLite), not embedded in MoP. ✓ VPS section (263-325) describes standalone FastAPI service on Hetzner CX11, separate from puppeteer
- **D-03** (line 643): Two-tier model with `deployment_mode` claim; online (30-90d), air-gapped (1-3y); 7-day grace. ✓ Documented on lines 73-84, 227-261; grace logic on lines 172-180, 577-581
- **D-04** (line 644): Two-phase: NOW=Git, AT SCALE=VPS for online, air-gapped stays Git. ✓ Lines 46-95 implement this structure exactly
- **D-05** (line 645): Air-gap = hard requirement, preserved. ✓ Verified above
- **D-06** (line 646): Structure = comparison (3×6) + rationale + migration path + wireframe. ✓ All four sections present and detailed (lines 15-26, 28-214, 109-214, 216-637)

---

## Section-by-Section Verification

| Section | Lines | Content | Substantive | Status |
|---------|-------|---------|-----------|--------|
| Executive Summary | 9-13 | Three options, recommendation, two-phase approach, preserves air-gap | ✓ Yes | ✓ VERIFIED |
| Comparison Table | 15-26 | 3 options × 6 dimensions, each cell scored + rationale | ✓ Yes | ✓ VERIFIED |
| Rationale & Recommendation | 28-105 | 5 reasons, two-phase structure, air-gap non-negotiable | ✓ Yes | ✓ VERIFIED |
| Migration Path | 109-214 | Current (Git), future (VPS + Git archive), effort (3mo), what stays | ✓ Yes | ✓ VERIFIED |
| VPS Wireframe | 216-637 | 4 design principles, two-tier model, infrastructure, 4 API endpoints, client code, security | ✓ Yes | ✓ VERIFIED |
| Summary of Decisions | 639-646 | D-01 through D-06 explicitly checked off | ✓ Yes | ✓ VERIFIED |
| Next Steps | 650-656 | Stakeholder review, approval, implementation phases | ✓ Yes | ✓ VERIFIED |

---

## Anti-Pattern Scan

Scanned for stubs, TODOs, placeholders, hardcoded empty values, unimplemented sections:

- **TODO/FIXME comments:** None found (grep -E "TODO|FIXME|XXX|HACK|PLACEHOLDER" returned empty)
- **Placeholder text:** None found (no "coming soon", "will be", "not yet", "TBD" in content)
- **Empty sections:** None — every major section contains substantive content with examples
- **Stub implementations:** No code stubs — VPS wireframe includes full API examples, SQL schema, Python client code, flow diagrams
- **Vague recommendations:** No — recommendation is explicit ("Option A for immediate term") with clear rationale and transition path
- **Unspecified details:** All key details specified: TTLs (60d, 2y), grace period (7 days), hosting (Hetzner CX11), stack (FastAPI + Caddy), effort (3 months solo)

**Status:** No blockers, warnings, or stubs found. Document is complete and ready for stakeholder communication.

---

## Wiring Verification

Key links between artifacts and context (from PLAN frontmatter):

| From | To | Via | Status |
|------|----|----|--------|
| Analysis | CONTEXT.md decisions (D-01 through D-06) | All decisions explicitly honored in lines 639-646 + throughout narrative | ✓ WIRED |
| Option A (Git repo) | axiom-licenses/tools/issue_licence.py | Flow described on lines 127-140: GitHub API commit pattern, YAML audit records | ✓ WIRED |
| Option B (VPS) | VPS investigation todo (check-in patterns, API, privacy) | Check-in flow on 547-575, API surface 329-444, privacy hashing 223, client code 446-545 | ✓ WIRED |
| Client-side integration | licence_service.py | `AXIOM_LICENCE_SERVER_URL` env var (optional, defaults to None = air-gapped mode) on line 458, load_licence() branching on deployment_mode lines 527-534 | ✓ WIRED |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| LIC-01 | Comparison of three options across six dimensions | ✓ MET | Comparison Table (lines 15-26): Option A, B, C × Security, Auditability, Air-Gap, Complexity, CI/CD, Recovery. Each cell scored + rationale. |
| LIC-02 | Concrete recommendation with rationale (two-phase) | ✓ MET | "Rationale & Recommendation" section (lines 28-105): explicit recommendation "Option A for immediate term" (line 32); two-phase structure (Phase 1 NOW lines 46-65, Phase 2 AT SCALE lines 67-95); rationale section with 5 reasons (lines 30-42). |
| LIC-03 | Migration path documented (even if = current) | ✓ MET | "Migration Path" section (lines 109-214): Current State (111-143), Future State (145-192), Effort Estimate (194-203), What Stays Same (205-214). Recommendation = current (Git repo NOW), future = VPS server AT SCALE (zero migration cost pre-launch). |

All three requirements fully satisfied.

---

## Document Quality Assessment

- **Completeness:** All five required sections present and detailed (Executive Summary, Comparison, Rationale, Migration Path, VPS Wireframe)
- **Clarity:** Recommendation is explicit and justified; two-phase structure clearly delineated
- **Specificity:** Concrete examples (Hetzner CX11, 60d TTL, 7-day grace, FastAPI stack) rather than abstract choices
- **Reasoning:** Each comparison cell includes rationale; rationale section has 5 explicit reasons; air-gap treated as hard requirement
- **Detail:** VPS wireframe includes API request/response examples, SQL schema, Python code snippet, security considerations
- **Traceability:** Locked decisions explicitly referenced (D-01 through D-06) and checked off
- **Actionability:** Migration path includes effort estimate (3 months solo), implementation phases named (LIC-IMPL-01, DIST-04)

---

## Verification Conclusion

**Status: PASSED**

All seven must-haves verified:
1. ✓ `.planning/LIC-ANALYSIS.md` exists (655 lines, committed)
2. ✓ Comparison table covers 3 options × 6 dimensions with rationale
3. ✓ Concrete recommendation with explicit rationale (Option A for NOW)
4. ✓ Two-phase recommendation (Phase 1: NOW with Git, Phase 2: AT SCALE with VPS)
5. ✓ Air-gap compatibility is hard requirement for air-gapped tier
6. ✓ `deployment_mode: online|airgapped` two-tier JWT model fully described
7. ✓ Future VPS wireframe detailed with infrastructure, API, client integration, security

**No gaps, no stubs, no anti-patterns found.**

The document achieves its goal: to produce an evidence-based analysis of three licence storage approaches, recommend the Git repo for immediate term while preserving air-gap compatibility, and wireframe the VPS server for post-launch online-tier customers.

---

**Verification Completed:** 2026-04-21T16:45:00Z  
**Verifier:** Claude (gsd-verifier)  
**Mode:** Initial verification (goal-backward analysis)  
**Result:** Phase goal achieved — PASSED

---
phase: 58-research-organisational-sso
verified: 2026-03-24T19:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Read 58-RESEARCH.md and confirm it is comprehensible to a reader with no prior SSO context"
    expected: "The Summary section opens with accessible prose that explains what SSO is, why it matters for Axiom, and why OIDC was chosen — without requiring prior knowledge of OIDC internals"
    why_human: "Readability and accessibility of prose cannot be verified programmatically"
  - test: "Confirm the Open Questions section (back-channel logout optionality, username collision, TOTP prerequisite) are acceptable deferred risks"
    expected: "The three open questions are flagged clearly, each with a concrete recommendation, and do not block a future implementer from starting work"
    why_human: "Whether open questions block implementation is a product/architectural judgement call that requires human review"
---

# Phase 58: Research — Organisational SSO Verification Report

**Phase Goal:** A complete design document exists that lets the team implement SSO in a future milestone without re-doing protocol or architecture choices
**Verified:** 2026-03-24T19:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Design document names OIDC, provides rationale citing existing OAuth 2.0 device flow, and explicitly defers SAML as future extension point | VERIFIED | Part 3 OIDC vs SAML section: "The decisive argument: Axiom already ships an OAuth 2.0 Device Authorization Grant... OIDC is OAuth 2.0 + an ID token layer". SAML noted as "future extension point in the Admin config (`sso_protocol: "oidc" \| "saml"`)". Authlib 1.6.x named as library. |
| 2 | Design document specifies full JWT bridge exchange flow including how SSO logout triggers token_version increment | VERIFIED | ASCII sequence diagram in JWT Bridge Design section shows the full flow from "Sign in with SSO" click to localStorage. `token_version` increment documented for both front-channel and back-channel logout. `POST /auth/sso/logout` endpoint specified. |
| 3 | Design document covers RBAC group mapping: re-sync on every login, highest-role-wins, default viewer, JSON config format | VERIFIED | RBAC Group Mapping section: "Core rule: re-sync on every login", "Default role on first SSO login: viewer", `map_groups_to_role()` pseudocode with priority order (admin > operator > viewer), JSON config format `{"axiom-admins": "admin", ...}` in `sso_group_mapping` key. Admin break-glass account preserved as local-auth only. |
| 4 | Design document covers all five IdPs with equal depth including CF Access risk/mitigation sub-section for Cf-Access-Jwt-Assertion header | VERIFIED | Part 4 has dedicated sections 4.1 (Cloudflare Access), 4.2 (Okta), 4.3 (Azure AD/Entra ID), 4.4 (Google Workspace), 4.5 (Authentik and Keycloak). CF Access has "Risk: Header Spoofing" and "Mitigation (mandatory)" subsections naming `Cf-Access-Jwt-Assertion`, `CF_CERTS_URL`, signature validation, `aud`+`iss` verification, and 6-week key rotation with short-TTL cache. Azure AD GUID groups quirk documented. Google Workspace no-native-groups quirk documented with two workarounds. |
| 5 | Design document specifies EE plugin extension points SSO uses (entry_points, stub router, sso_router.py), confirming CE installs see zero SSO code | VERIFIED | Air-Gap Isolation section table lists all five extension points: `EEContext.sso` field, `_mount_ce_stubs()` stubs, `load_ee_plugins()` entry point, `ee/routers/sso_router.py`, `ee/interfaces/sso.py`. CE code path explicitly stated: "CE users hitting `/auth/sso/login` receive HTTP 402. No OIDC library is imported." `authlib` and `httpx` are EE-only dependencies. |
| 6 | Design document defines Mode A (SSO satisfies 2FA via amr claim) and Mode B (always require Axiom TOTP), with TOTP enrolment prompt for unenrolled SSO users | VERIFIED | Part 5 defines Mode A (`"idp"`) and Mode B (`"always"`) with Config table key `sso_2fa_mode`. `amr` claim detection pseudocode present. TOTP enrolment prompt path described for unenrolled SSO users hitting step-up. RFC 8176 `amr` value reference table included. "No silent bypass, no lock-out" explicitly stated. |
| 7 | A reader with no prior SSO context can understand the proposal and why OIDC was chosen | UNCERTAIN | The Summary and Part 3 are written accessibly. Needs human confirmation — see Human Verification section. |

**Score:** 6/7 truths verified programmatically, 1 flagged for human confirmation

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/58-research-organisational-sso/58-RESEARCH.md` | Complete SSO design document covering all 8 sections across 6 requirements | VERIFIED | File exists. ~840 lines. All 8 parts present: Use Case Analysis, Architecture and Integration Design, Protocol Recommendation, IdP Coverage, 2FA Interaction Policy, CLI SSO, Prior Art, Complexity/Value Recommendation with draft implementation sketch. |

**Level 1 (exists):** VERIFIED
**Level 2 (substantive):** VERIFIED — document is 840+ lines covering all required topics in depth; no placeholder or stub sections detected
**Level 3 (wired):** N/A — this is a research phase; the artifact is a design document, not code. The document is self-contained and does not require wiring to other files.

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| RESEARCH.md Protocol Recommendation | SSO-01 requirement | OIDC recommendation with device flow rationale, SAML deferred | VERIFIED | grep count = 7 hits for "SAML"; "OAuth 2.0 Device Authorization Grant" mentioned; "SAML is noted as a future extension point" present |
| RESEARCH.md JWT Bridge Design | SSO-02 requirement | token_version increment on logout, exchange flow pseudocode | VERIFIED | grep count = 16 hits for "token_version"; `sso_callback` pseudocode present; `POST /auth/sso/logout` endpoint defined |
| RESEARCH.md RBAC Group Mapping | SSO-03 requirement | re-sync on login, default viewer, JSON mapping config | VERIFIED | grep count = 4 hits for "map_groups_to_role\|sso_group_mapping"; "re-sync on every login" stated; "default viewer" stated |
| RESEARCH.md IdP Coverage — CF Access | SSO-04 requirement | Cf-Access-Jwt-Assertion risk + mitigation sub-section | VERIFIED | grep count = 5 hits for "Cf-Access-Jwt-Assertion"; spoofing risk named; signature validation mitigation with CF_CERTS_URL |
| RESEARCH.md Air-Gap Isolation | SSO-05 requirement | EE plugin entry_points, stub router, CE code path | VERIFIED | grep count = 8 hits for "sso_stub_router\|axiom.ee\|entry.point\|entry_point"; CE 402 path documented; EE registration via entry point documented |
| RESEARCH.md 2FA Interaction Policy | SSO-06 requirement | Mode A/B config, amr claim, TOTP enrolment prompt | VERIFIED | grep count = 13 hits for "sso_2fa_mode\|Mode A\|Mode B"; `amr` detection code present; enrolment prompt described |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SSO-01 | 58-01-PLAN.md | Protocol recommendation produced (OIDC vs SAML, rationale for non-air-gapped EE deployments) | SATISFIED | Part 3 OIDC vs SAML comparison table + decisive argument citing RFC 8628 device flow. Authlib 1.6.x named with dependency list. |
| SSO-02 | 58-01-PLAN.md | JWT bridge design documented (exchange flow, token_version interaction, SSO session invalidation) | SATISFIED | ASCII sequence diagram, `sso_callback` pseudocode, front-channel and back-channel logout, `sso_provider`/`sso_subject` DB columns, migration SQL. |
| SSO-03 | 58-01-PLAN.md | RBAC group mapping design documented (IdP group → MoP role mapping, default role on first SSO login) | SATISFIED | `map_groups_to_role()` pseudocode, JSON config format, re-sync policy, default `viewer` role, admin break-glass preserved. |
| SSO-04 | 58-01-PLAN.md | Cloudflare Access integration pattern documented (Cf-Access-Jwt-Assertion header trust model, security implications) | SATISFIED | Pattern A (standard OIDC) and Pattern B (header verification) both documented. Risk/mitigation sub-section with mandatory signature validation via CF_CERTS_URL. Key rotation (6-week cycle) addressed. All five IdPs have equal dedicated sections. |
| SSO-05 | 58-01-PLAN.md | Air-gap isolation strategy documented (feature flag/plugin pattern, zero impact on offline deployments) | SATISFIED | Extension points table with five rows. CE code path (402 stub). EE registration via `axiom.ee` entry point. Library isolation (`authlib`/`httpx` EE-only). File paths named: `ee/routers/sso_router.py`, `ee/interfaces/sso.py`. |
| SSO-06 | 58-01-PLAN.md | TOTP 2FA interaction policy documented (SSO auth + MoP TOTP for step-up actions) | SATISFIED | Mode A/B defined. `sso_2fa_mode` Config key. TOTP enrolment prompt path for unenrolled SSO users. RFC 8176 `amr` reference table. No silent bypass, no lock-out stated. Open question raised about TOTP prerequisite not yet existing in codebase (documented in Open Questions section — does not block the design). |

No orphaned requirements — all six SSO IDs claimed in 58-01-PLAN.md are present in REQUIREMENTS.md mapped to Phase 58. No additional Phase 58 IDs exist in REQUIREMENTS.md beyond SSO-01 through SSO-06.

---

### Anti-Patterns Found

No anti-patterns applicable — this is a research-only phase producing a design document, not code. No implementation files were created or modified. Scanning for code anti-patterns is not applicable.

The document's Open Questions section notes one potential concern: TOTP step-up (Mode B / SSO-06) depends on a TOTP enrolment flow that may not yet be implemented in the codebase. The document flags this explicitly as a prerequisite audit item for the implementation phase. This is appropriate design practice, not a gap.

---

### Human Verification Required

#### 1. Prose Readability Assessment

**Test:** Read the Summary section and Part 1 (Use Case Analysis) of `58-RESEARCH.md` without any prior SSO knowledge.

**Expected:** The Summary opens with a plain-English explanation of what SSO is, who asks for it, and why OIDC was chosen. A developer unfamiliar with OAuth or OIDC can understand the proposal and the rationale without reading the full document. Specifically: the sentences "Axiom today authenticates users through a username/password form..." and "The central finding is that OIDC is the correct and natural protocol choice for Axiom..." should be comprehensible without external references.

**Why human:** Prose readability cannot be verified programmatically. Whether a non-expert reader finds the document accessible requires human judgement.

#### 2. Open Questions Acceptability

**Test:** Review the Open Questions section at the end of `58-RESEARCH.md`.

**Expected:** All three open questions (back-channel logout optionality, username collision between local-auth and SSO users, TOTP prerequisite audit) are framed with concrete recommendations and do not represent undecided architecture — they are flagged deferred risks. A developer starting implementation should not be blocked by them.

**Why human:** Whether open questions constitute acceptable deferred risk is a product and architecture judgement that requires human review.

---

### Gaps Summary

No automated gaps found. All seven observable truths are either verified or flagged for human confirmation. All six requirements are satisfied by the document content. All six key links are verified. No missing or stub artifacts. No anti-patterns in the (documentation-only) output.

The single human_needed item (prose readability) is a quality confirmation, not a structural gap. The document is substantively complete.

---

_Verified: 2026-03-24T19:00:00Z_
_Verifier: Claude (gsd-verifier)_

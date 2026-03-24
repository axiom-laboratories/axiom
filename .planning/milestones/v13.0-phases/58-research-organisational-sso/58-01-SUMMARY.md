---
phase: 58-research-organisational-sso
plan: "01"
subsystem: auth
tags: [sso, oidc, jwt, rbac, oauth2, authlib, enterprise, design-doc]

# Dependency graph
requires: []
provides:
  - Complete SSO design document covering protocol recommendation, JWT bridge design, RBAC group mapping, IdP coverage (5 providers), 2FA interaction policy, EE air-gap isolation strategy, and implementation sketch
affects: [future-sso-implementation, ee-plugin-architecture, auth]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Research-only phase: output is a validated design document with no implementation code"
    - "EE plugin pattern: SSO isolated behind entry_points so CE installs see zero SSO code"
    - "JWT bridge pattern: OIDC callback produces Axiom JWT, token_version increment on SSO logout"

key-files:
  created:
    - .planning/phases/58-research-organisational-sso/58-RESEARCH.md
  modified: []

key-decisions:
  - "OIDC chosen over SAML for v1 SSO: natural extension of existing RFC 8628 device flow, Authlib 1.6.x as client library, SAML deferred as future extension"
  - "SSO logout triggers token_version increment identical to password-change mechanism, invalidating all Axiom sessions"
  - "RBAC group re-synced on every SSO login; default role is viewer; highest-role-wins across admin>operator>viewer; admin break-glass account preserved as local-auth only"
  - "SSO is an EE-only plugin using axiom.ee entry_points; CE installs get stub routes returning 402; authlib and httpx are EE-only dependencies"
  - "Two 2FA modes: Mode A (IdP amr claim satisfies MFA), Mode B (Axiom TOTP always required); TOTP enrolment prompt for unenrolled SSO users"
  - "CF Access requires dedicated risk/mitigation path: validate Cf-Access-Jwt-Assertion signature via CF public key endpoint, verify aud+iss, cache keys with short TTL for 6-week rotation"

patterns-established:
  - "Research phase pattern: verify document against CONTEXT.md locked decisions via checklist, fill gaps in-place, obtain human sign-off"

requirements-completed: [SSO-01, SSO-02, SSO-03, SSO-04, SSO-05, SSO-06]

# Metrics
duration: 35min
completed: 2026-03-24
---

# Phase 58 Plan 01: Organisational SSO Research Summary

**OIDC-based SSO design document covering JWT bridge exchange flow, 5-IdP coverage with CF Access risk mitigation, EE air-gap isolation via entry_points, Mode A/B 2FA policy, and RBAC group re-sync — validated against all 6 SSO requirements and approved by human reviewer**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-03-24T17:30:00Z
- **Completed:** 2026-03-24T18:05:00Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1 (58-RESEARCH.md verified and confirmed complete)

## Accomplishments

- Verified `58-RESEARCH.md` against all six SSO requirements and every CONTEXT.md locked decision using a structured checklist
- Confirmed all six content markers present: `GET /auth/sso/login`, `token_version`, `Cf-Access-Jwt-Assertion`, `sso_2fa_mode`, `axiom.ee`, `map_groups_to_role`
- Obtained human sign-off on the completed design document — "approved, seems ok"

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify and complete the research document** - `bf79b0a` (docs)
2. **Task 2: Human verification checkpoint** - approved (no code change)

**Plan metadata:** (this summary commit)

## Files Created/Modified

- `.planning/phases/58-research-organisational-sso/58-RESEARCH.md` — Complete SSO design document: 8 sections covering use case analysis, JWT bridge design with exchange flow pseudocode and DB migration SQL, RBAC group mapping with JSON config format, protocol recommendation (OIDC/Authlib), 5-IdP coverage (CF Access, Okta, Azure AD/Entra ID, Google Workspace, Authentik/Keycloak), 2FA interaction policy (Mode A/B), CLI SSO complexity assessment with deferral recommendation, prior art (Grafana, Gitea, Vault, Argo CD), and draft implementation sketch

## Decisions Made

- OIDC chosen over SAML for v1: natural extension of Axiom's existing RFC 8628 device flow; SAML acknowledged but deferred as future extension point
- SSO logout uses identical `token_version` increment mechanism as password change — no new invalidation infrastructure needed
- RBAC group mapping: re-sync on every login, default `viewer` role on first SSO login, highest-role-wins priority, admin account preserved as local-auth only
- SSO implemented as EE plugin via `axiom.ee` entry_points — CE installs get 402 stubs, `authlib`/`httpx` are EE-only dependencies
- Two 2FA modes configurable per-deployment; TOTP enrolment prompt path specified for unenrolled SSO users (no silent bypass, no lock-out)
- CF Access requires special handling: `Cf-Access-Jwt-Assertion` header spoofing risk mitigated by validating JWT signature via CF public key endpoint with short-TTL cache for 6-week key rotation cycle

## Deviations from Plan

None — plan executed exactly as written. The research document already satisfied all CONTEXT.md locked decisions at Task 1 start. Human reviewer approved without requesting changes.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. This is a research-only phase; no code was deployed.

## Next Phase Readiness

- SSO design document is complete and ready for a future implementation phase. A developer can implement SSO from `58-RESEARCH.md` without re-doing protocol or architecture choices.
- The EE plugin extension points (`entry_points`, `sso_stub_router`, `sso_router.py`), DB migration SQL (`sso_provider`, `sso_subject` columns), and Admin config keys (`sso_group_mapping`, `sso_2fa_mode`) are all specified.
- No blockers. Phases 57, 59, and 60 are independent and can proceed in any order.

---
*Phase: 58-research-organisational-sso*
*Completed: 2026-03-24*

# Phase 58: Research — Organisational SSO - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce a design document (`58-RESEARCH.md`) that gives the team everything needed to implement organisational SSO in a future milestone — without re-doing protocol or architecture choices. No implementation. Output is a research artifact consumed by the planner and future milestone planning.

</domain>

<decisions>
## Implementation Decisions

### Document structure
- Mirror Phase 57's four-part structure:
  1. Use case analysis — when SSO is needed, who asks for it, what deployment scenarios it targets
  2. Architecture/integration design — JWT bridge, RBAC mapping, CF Access + IdP integrations, air-gap isolation
  3. Protocol recommendation — OIDC recommendation with rationale, SAML as acknowledged but not recommended
  4. Complexity/value recommendation with next-step guidance and draft implementation sketch
- Include a draft login flow + token exchange sketch (analogous to Phase 57's draft swarm API endpoint) — concrete enough for the future implementer to start from
- Include a brief prior art section: 2-3 comparable tools that have solved OIDC bridge + RBAC mapping (e.g., Grafana, Gitea, Vault). Grounds recommendations and avoids reinventing solved patterns
- Doc must be readable by someone with no prior SSO context

### Air-gap isolation (SSO-05)
- SSO is explicitly an **EE plugin** using the existing `axiom-ee` architecture — same pattern as other EE features
- CE installs see zero SSO code paths; no feature flag in CE
- Doc must specify which plugin extension points the SSO feature would use

### Protocol recommendation (SSO-01)
- **Strongly opinionated: OIDC recommended**
- Rationale must note that Axiom already ships a native OAuth 2.0 device flow — OIDC is the natural protocol extension
- SAML is acknowledged as an existing enterprise requirement in some orgs but explicitly not recommended (XML complexity, no browser-native support, harder to implement in FastAPI ecosystem)
- SAML noted as a future extension point, not v1 scope

### JWT bridge design (SSO-02)
- SSO logout or IdP session revocation triggers a **`token_version` increment** — same mechanism as password change
- All Axiom sessions for that user are instantly invalidated on IdP logout
- Exchange flow: IdP OIDC callback → server validates ID token → creates/updates Axiom User → issues Axiom JWT with `tv` claim → returns to dashboard

### RBAC group mapping (SSO-03)
- **Re-sync on every login**: each SSO login re-reads IdP group claims and updates the Axiom role
- Removing a user from an IdP group takes effect on their next login
- Default role on first SSO login: must be specified in the doc (Claude's discretion on the actual default — `viewer` is the sensible choice)

### CF Access and IdP coverage (SSO-04)
- **All five IdPs receive equal dedicated coverage**: Cloudflare Access, Okta, Azure AD / Entra ID, Google Workspace, Authentik / Keycloak
- Each IdP section covers: OIDC discovery URL, required scopes for group claims, any provider-specific quirks
- CF Access gets an additional **risk + mitigation** sub-section for the `Cf-Access-Jwt-Assertion` header:
  - Risk: header can be spoofed if Axiom is not exclusively behind a CF tunnel
  - Mitigation: verify JWT signature using CF public key endpoint — never trust header value alone

### 2FA interaction policy (SSO-06)
- **Two configurable modes** (operator sets policy in Admin config):
  - Mode A: SSO satisfies 2FA — if the IdP enforces MFA, Axiom skips its TOTP step-up
  - Mode B: Always require Axiom TOTP regardless of SSO (belt-and-suspenders for paranoid deployments)
- SSO user without TOTP enrolled who hits a step-up action: **prompted to enrol TOTP** — graceful degradation, no silent bypass, no lock-out
- **CLI SSO (axiom-push) is in scope** but treated as a separate design concern:
  - Problem: device flow layered on OIDC device flow is complex
  - Doc must cover the CLI SSO pattern with an honest complexity assessment
  - May recommend deferred CLI SSO as a follow-on to dashboard SSO

### Claude's Discretion
- Exact section headings and prose structure within each doc section
- Default role assigned on first SSO login (sensible choice: `viewer`)
- Which tools to include in the prior art section beyond Grafana/Gitea/Vault
- Whether to include sequence diagrams or pseudo-code in the JWT bridge section
- Exact OIDC scopes and discovery URL formats for each IdP (researcher to verify)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `User` model in `db.py`: has `token_version` (int) — incremented on password change, embedded as `tv` in JWT; SSO logout hook uses this same mechanism
- `auth.py`: JWT creation/verification, bcrypt password hashing — JWT issuance at SSO callback reuses `create_access_token()`
- `ServicePrincipal` model: machine-to-machine auth pattern — analogous to how SSO users may also need service credentials
- `RolePermission` table: DB-backed RBAC seeds; SSO group→role mapping needs to write to `User.role` on login

### Established Patterns
- EE plugin architecture (`axiom-ee` entry_points): SSO feature slots in as an EE plugin — no CE code changes needed
- `require_permission()` factory: SSO-authenticated users get a standard Axiom JWT and flow through normal RBAC — no new permission checks needed
- OAuth device flow (`/auth/device`): existing RFC 8628 implementation — relevant prior art for CLI SSO design

### Integration Points
- `POST /auth/login` in `main.py`: SSO adds a parallel path (`POST /auth/sso/callback`) that ends with the same JWT issuance
- Admin config (`Config` table): two-mode 2FA policy stored here (reuses existing key/value store — same pattern as `enforcement_mode` for Smelter)
- Dashboard routing: SSO adds a login redirect step before the existing JWT+localStorage auth flow

</code_context>

<specifics>
## Specific Ideas

- The existing `token_version` mechanism is a strength — SSO logout invalidation is free if we hook into it. Doc should highlight this as an architectural advantage.
- CF Access risk/mitigation framing should be honest and security-first — consistent with the project's zero-trust defaults.
- CLI SSO complexity (device flow + OIDC device flow) should be stated plainly — it is genuinely harder than dashboard SSO and the doc should say so.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 58-research-organisational-sso*
*Context gathered: 2026-03-24*

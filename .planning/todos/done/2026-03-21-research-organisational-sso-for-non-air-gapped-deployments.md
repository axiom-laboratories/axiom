---
created: 2026-03-21T21:50:41.075Z
title: Research organisational SSO for non-air-gapped deployments
area: auth
files:
  - puppeteer/agent_service/auth.py
  - puppeteer/agent_service/main.py
  - puppeteer/agent_service/db.py
---

## Problem

MoP's current auth model is JWT-based with bcrypt password hashing and mTLS for node-facing endpoints. For non-air-gapped EE deployments, enterprise customers will expect organisational SSO (SAML 2.0 / OIDC) so they can manage MoP access through their existing identity provider (Okta, Azure AD, Google Workspace, Cloudflare Access, etc.) rather than maintaining a separate user database.

This has not been researched yet. The interaction between SSO, the existing JWT model, RBAC (role_permissions table), and the mTLS node security model is non-trivial and needs proper design before any implementation begins. Getting this wrong — e.g. letting SSO bypass RBAC, or breaking the mTLS trust chain — would be a serious security regression.

This is explicitly out of scope for the current User Story Alignment milestone and the TOTP 2FA work. It should not be bolted onto either.

## Solution

**Research phase only — no implementation until research is complete.**

Key questions to answer before planning:

1. **Protocol choice:** SAML 2.0 vs OIDC. OIDC is simpler and better suited to modern deployments. SAML is required for older enterprise IdPs. Does MoP need to support both, or can we mandate OIDC and document SAML as out of scope?

2. **JWT bridge:** MoP issues its own JWTs after login. With SSO, the IdP handles authentication and returns a token (OIDC id_token or SAML assertion). MoP must exchange this for its own JWT to preserve the existing session model. How does `token_version` (session invalidation on password change) interact with SSO-issued sessions? SSO users don't have a MoP password to change.

3. **RBAC mapping:** SSO users need roles. Options: (a) auto-assign a default role on first SSO login, (b) map IdP groups to MoP roles (e.g. Okta group "mop-admins" → admin role), (c) require manual role assignment after first SSO login. Option (b) is what enterprise customers will expect but requires a group mapping config surface.

4. **Cloudflare Access integration:** Cloudflare Access sits in front of the dashboard (tunnel already in place). CF Access can pass a JWT in the `Cf-Access-Jwt-Assertion` header after authentication. MoP could trust this header and skip its own auth, or treat it as one input into its own auth flow. The security implications of trusting a header need careful evaluation.

5. **Air-gap boundary:** SSO must be entirely optional and have zero impact on air-gapped deployments. SSO-related code paths must not be required for the product to function without internet access. Feature flag or plugin pattern required.

6. **TOTP 2FA interaction:** If a user authenticates via SSO, does MoP's TOTP 2FA still apply? Or does the IdP handle MFA and MoP trusts it? For step-up 2FA on key approval, MoP's own TOTP is probably still required regardless of how the user authenticated — needs a clear policy decision.

**Research outputs needed:**
- Protocol recommendation (OIDC-first with SAML consideration)
- JWT bridge design
- RBAC group mapping design
- Cloudflare Access integration pattern
- Feature flag / plugin isolation strategy
- Impact assessment on existing auth.py, JWT model, and token_version mechanism

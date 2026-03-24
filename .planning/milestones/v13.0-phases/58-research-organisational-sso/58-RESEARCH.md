# Phase 58: Research — Organisational SSO

**Researched:** 2026-03-24
**Domain:** OIDC/SSO protocol design, JWT bridge architecture, RBAC group mapping, EE plugin pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Document mirrors Phase 57's four-part structure: (1) use case analysis, (2) architecture/integration design, (3) protocol recommendation, (4) complexity/value recommendation + draft sketch
- Include a draft login flow + token exchange sketch — concrete enough for the future implementer to start from
- Include prior art section: Grafana, Gitea, Vault (plus Claude's discretion additions)
- Doc must be readable by someone with no prior SSO context
- SSO is explicitly an EE plugin using the existing `axiom-ee` `entry_points` architecture — CE installs see zero SSO code paths; no feature flag in CE; doc must specify which plugin extension points SSO would use
- OIDC strongly recommended; SAML acknowledged but not recommended (XML complexity, no browser-native support, harder in FastAPI ecosystem); SAML noted as future extension point, not v1 scope
- Rationale must note that Axiom already ships a native OAuth 2.0 device flow — OIDC is the natural protocol extension
- SSO logout / IdP session revocation triggers a `token_version` increment — same mechanism as password change; all Axiom sessions invalidated instantly
- Exchange flow: IdP OIDC callback → server validates ID token → creates/updates Axiom User → issues Axiom JWT with `tv` claim → returns to dashboard
- RBAC re-sync on every login: each SSO login re-reads IdP group claims and updates Axiom role
- Removing a user from an IdP group takes effect on their next login
- Default role on first SSO login: must be specified (locked: `viewer`)
- All five IdPs receive equal dedicated coverage: Cloudflare Access, Okta, Azure AD / Entra ID, Google Workspace, Authentik / Keycloak
- Each IdP section: OIDC discovery URL, required scopes for group claims, any provider-specific quirks
- CF Access gets additional risk + mitigation sub-section for `Cf-Access-Jwt-Assertion` header
- Two configurable 2FA interaction modes (operator-set in Admin config): Mode A (SSO satisfies 2FA) and Mode B (always require Axiom TOTP regardless)
- SSO user without TOTP enrolled who hits a step-up action: prompted to enrol TOTP — graceful degradation, no silent bypass, no lock-out
- CLI SSO (axiom-push) is in scope but treated as a separate design concern; doc covers CLI SSO pattern with honest complexity assessment; may recommend deferred CLI SSO as follow-on to dashboard SSO

### Claude's Discretion
- Exact section headings and prose structure within each doc section
- Default role assigned on first SSO login (chosen: `viewer`)
- Which tools to include in the prior art section beyond Grafana/Gitea/Vault
- Whether to include sequence diagrams or pseudo-code in the JWT bridge section
- Exact OIDC scopes and discovery URL formats for each IdP (verified during research)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SSO-01 | Protocol recommendation produced (OIDC vs SAML, rationale for non-air-gapped EE deployments) | Section: Protocol Recommendation — OIDC vs SAML analysis, rationale tied to existing device flow, SAML deferred path |
| SSO-02 | JWT bridge design documented (exchange flow, `token_version` interaction, SSO session invalidation) | Section: JWT Bridge Design — full exchange flow pseudocode, token_version hook, logout/invalidation mechanics |
| SSO-03 | RBAC group mapping design documented (IdP group → MoP role mapping, default role on first SSO login) | Section: RBAC Group Mapping — re-sync on every login, default `viewer` role, unenrolled user handling |
| SSO-04 | Cloudflare Access integration pattern documented (`Cf-Access-Jwt-Assertion` header trust model, security implications) | Section: IdP Coverage → Cloudflare Access — risk/mitigation sub-section, key rotation, signature verification |
| SSO-05 | Air-gap isolation strategy documented (feature flag/plugin pattern, zero impact on offline deployments) | Section: Air-Gap Isolation — EE plugin entry_point pattern, stub router mechanics, CE code paths |
| SSO-06 | TOTP 2FA interaction policy documented (SSO auth + MoP TOTP for step-up actions) | Section: 2FA Interaction Policy — Mode A/B config, TOTP enrolment prompt, acr claim handling |
</phase_requirements>

---

## Summary

Axiom today authenticates users through a username/password form (`POST /auth/login`) that issues an HS256 JWT carrying `sub`, `tv` (token version), and `role` claims. Operators at organisations with an existing identity provider — Okta, Azure Entra ID, Google Workspace, Keycloak, Authentik, or Cloudflare Access — want their users to authenticate against that provider instead of maintaining a separate credential. They also want role assignments to follow their existing group membership in the IdP, so that offboarding a user from the IdP instantly removes their Axiom access.

This document answers the question: **what must be designed and decided before a developer can implement SSO without re-doing protocol or architecture choices?** It covers the protocol recommendation, the full JWT bridge exchange flow (including how SSO logout interacts with the existing `token_version` invalidation mechanism), the RBAC group-to-role mapping design, coverage of all five target IdPs, the EE plugin extension points SSO must use to stay isolated from CE deployments, and the 2FA interaction policy.

The central finding is that OIDC is the correct and natural protocol choice for Axiom. The server already implements RFC 8628 OAuth 2.0 Device Authorization Grant (`/auth/device`), which demonstrates that the team is comfortable with the OAuth 2.0 flow family. OIDC is OAuth 2.0 with an ID token layer — adding it does not require learning a new protocol, only a new endpoint and a token validation step. The existing `token_version` mechanism, which invalidates all sessions instantly on password change, is a structural advantage: IdP logout can reuse the same hook at zero additional complexity. SSO users flow through the same RBAC system as password-auth users — the JWT they receive at the end of the OIDC callback is structurally identical to the JWT a password-auth user receives. There is no separate SSO session management layer required.

**Primary recommendation:** Implement OIDC SSO as an EE plugin (`axiom.ee` entry point group), using Authlib as the OIDC client library. The SSO plugin mounts two new routes (`GET /auth/sso/login`, `GET /auth/sso/callback`) and one admin config block. Dashboard SSO should ship first; CLI SSO via device-flow-layered-on-OIDC should be treated as a follow-on due to genuine protocol complexity.

---

## Part 1: Use Case Analysis

### Who Needs SSO and Why

SSO is a feature requested by organisations with four properties:

1. **Centralised identity**: The organisation maintains users in an IdP (Okta, Azure Entra, Google Workspace, Keycloak, Authentik, or Cloudflare Access). Users already have passwords there; requiring a second password for Axiom is friction and a security risk.

2. **Centralised offboarding**: When an employee leaves, the IT team disables their IdP account. Without SSO, their Axiom account remains active until an admin manually removes it. With SSO + re-sync-on-login, the next login attempt fails at the IdP — no Axiom-side action needed.

3. **Group-based access control**: The organisation already defines groups in the IdP (e.g. `axiom-operators`, `axiom-viewers`, `axiom-admins`). They want Axiom roles to follow those groups automatically without manually mirroring every change.

4. **Compliance and audit**: Regulated organisations require all authentication events to flow through a single audited identity layer. Axiom's local authentication is a gap in that model.

### What Deployment Scenarios SSO Targets

SSO targets **non-air-gapped Enterprise Edition deployments only**. This is not a workaround — it is the correct design:

- An air-gapped deployment has no outbound network access to an IdP's OIDC well-known endpoint or token endpoint. SSO is structurally impossible in true air-gap deployments. Attempting to ship SSO in CE would be misleading and would add dead code to every CE install.
- The EE plugin model already handles this cleanly. CE installs load stub routers that return 402. SSO simply adds new stubs for `GET /auth/sso/login` and `GET /auth/sso/callback` in the stub router — CE users see a clear "Enterprise Edition required" response if they somehow hit those endpoints.

### What SSO Does Not Change

- The node-to-puppeteer mTLS authentication path (`/api/enroll`, `/work/pull`, `/heartbeat`) is unchanged. Nodes use client certificates, not user credentials.
- The existing `POST /auth/login` form endpoint remains available. SSO is an **additional** auth path, not a replacement. Operators can run both simultaneously (useful for the `admin` break-glass account to remain on local auth).
- The RBAC system (`require_permission()`, `RolePermission` table) is unchanged. SSO users receive a standard Axiom JWT and flow through exactly the same permission checks.

---

## Part 2: Architecture and Integration Design

### JWT Bridge Design

The "JWT bridge" is the mechanism by which a validated IdP identity token becomes an Axiom access token. It is the core engineering concern of SSO.

**Exchange Flow (OIDC Authorization Code Flow)**

```
User browser                Dashboard               Axiom server (EE)          IdP (e.g. Okta)
     |                           |                          |                         |
     |  Click "Sign in with SSO" |                          |                         |
     |-------------------------->|                          |                         |
     |                           | GET /auth/sso/login      |                         |
     |                           |------------------------->|                         |
     |                           |   302 redirect to IdP    |                         |
     |<--------------------------+--------------------------|                         |
     |                           |                          |                         |
     |  Follow redirect: GET /authorize?...                                           |
     |------------------------------------------------------------------------------->|
     |                           |                          |                         |
     |  User authenticates at IdP (MFA enforced by IdP if configured)                |
     |                           |                          |                         |
     |  IdP redirects: GET /auth/sso/callback?code=...&state=...                     |
     |<-------------------------------------------------------------------------------|
     |                           |                          |                         |
     |  GET /auth/sso/callback?code=...                                               |
     |-------------------------->|                          |                         |
     |                           | forward to server        |                         |
     |                           |------------------------->|                         |
     |                           |                          | POST /token (exchange)  |
     |                           |                          |------------------------>|
     |                           |                          | {id_token, access_token}|
     |                           |                          |<------------------------|
     |                           |                          |                         |
     |                           |                          | Validate id_token JWT   |
     |                           |                          | (sig, iss, aud, exp)    |
     |                           |                          |                         |
     |                           |                          | Extract: email/sub,     |
     |                           |                          | groups claim            |
     |                           |                          |                         |
     |                           |                          | Upsert User row         |
     |                           |                          | Map groups → role       |
     |                           |                          | (overwrite user.role)   |
     |                           |                          |                         |
     |                           |                          | create_access_token(    |
     |                           |                          |   sub=username,         |
     |                           |                          |   tv=user.token_version,|
     |                           |                          |   role=user.role        |
     |                           |                          | )                       |
     |                           |                          |                         |
     |                           |  {access_token, ...}     |                         |
     |<--------------------------+--------------------------|                         |
     |  Store token in           |                          |                         |
     |  localStorage             |                          |                         |
```

**Critical properties of this design:**

1. The Axiom JWT issued at the end of the callback is **structurally identical** to a password-auth JWT. It carries `sub`, `tv`, and `role`. The `get_current_user` dependency in `deps.py` validates it without any modification.

2. The `state` parameter in the OIDC redirect must be generated per-request (CSRF protection) and stored server-side or in a short-lived signed cookie for the duration of the callback round-trip. Authlib handles this automatically with `SessionMiddleware`.

3. A `nonce` must be included in the authorization request and validated in the ID token. This prevents replay attacks.

**SSO Session Invalidation via `token_version`**

The existing `token_version` mechanism in `User` is perfect for SSO invalidation:

```
IdP logout event (e.g. Okta back-channel logout, user clicks "logout from all apps")
→ Axiom receives logout notification at POST /auth/sso/logout (new endpoint)
→ server increments user.token_version (same as password change path)
→ all existing Axiom JWTs for that user become invalid on next request
  (get_current_user checks: payload.get("tv", 0) != user.token_version → 401)
```

This is architecturally free — the mechanism already exists. The implementation only needs to:
1. Add a `POST /auth/sso/logout` endpoint that accepts a back-channel logout token from the IdP
2. Call the same `token_version` increment that `PATCH /auth/me` already calls

Note: Not all IdPs support back-channel logout (OIDC Back-Channel Logout specification). Front-channel logout (redirect-based) is more universally supported. The design should handle both:
- **Front-channel logout**: User clicks logout in Axiom dashboard → server increments `token_version` → redirects to IdP logout URL
- **Back-channel logout**: IdP POSTs a logout token to Axiom → server validates token, increments `token_version`

**New DB Columns Required**

The SSO plugin needs to extend the `User` table with two new columns. Because Axiom uses `create_all` (no Alembic), these must be added via a migration SQL file for existing deployments:

| Column | Type | Purpose |
|--------|------|---------|
| `sso_provider` | `String`, nullable | Which IdP the user authenticated with (e.g. `"okta"`, `"azure"`, `"google"`, `"cf_access"`) |
| `sso_subject` | `String`, nullable | IdP-side user identifier (`sub` claim from the ID token). Used to match returning SSO users. |

Users with `sso_subject IS NULL` are local-auth users. Users with `sso_subject` set are SSO users. A user can only be one or the other — if an admin creates a local user with the same username as an incoming SSO user, the SSO callback must be rejected (or the admin must pre-link the accounts).

**User Upsert Logic at Callback**

```python
# Pseudocode for SSO callback handler
async def sso_callback(code: str, state: str, db: AsyncSession):
    # 1. Exchange code for tokens (Authlib handles PKCE, nonce validation)
    token = await oauth_client.authorize_access_token(request)
    id_token_claims = await oauth_client.parse_id_token(request, token)

    # 2. Extract identity
    sso_subject = id_token_claims["sub"]
    email = id_token_claims.get("email", sso_subject)
    groups = id_token_claims.get("groups", [])  # provider-specific claim name

    # 3. Derive Axiom username (email preferred; falls back to sub)
    username = email.split("@")[0] if "@" in email else sso_subject

    # 4. Map IdP groups → Axiom role
    role = map_groups_to_role(groups)  # see RBAC section below

    # 5. Upsert User
    user = await db.get(User, username)
    if user is None:
        user = User(username=username, password_hash="", role=role,
                    sso_provider=provider, sso_subject=sso_subject)
        db.add(user)
    else:
        # Re-sync role on every login
        user.role = role
        user.sso_provider = provider
        user.sso_subject = sso_subject

    await db.flush()

    # 6. Issue Axiom JWT (identical to password-auth path)
    token = create_access_token(
        data={"sub": user.username, "tv": user.token_version, "role": user.role}
    )
    await db.commit()
    return RedirectResponse(f"/?token={token}")
```

### RBAC Group Mapping Design

**Core rule: re-sync on every login.** Each SSO login re-reads IdP group claims and overwrites `user.role`. This means:
- Adding a user to an IdP group takes effect on their next login
- Removing a user from an IdP group takes effect on their next login
- No background sync job is needed
- No stale role state accumulates

**Default role on first SSO login: `viewer`**

A user arriving via SSO for the first time with no matching group mapping receives the `viewer` role. This is the minimum-privilege default. The admin can promote them later, or the operator can configure an explicit group mapping before users log in.

**Group-to-role mapping configuration**

The mapping is stored as a JSON value in the existing `Config` table (key: `sso_group_mapping`). Format:

```json
{
  "axiom-admins": "admin",
  "axiom-operators": "operator",
  "axiom-viewers": "viewer"
}
```

The mapping function iterates the user's groups in priority order (`admin` > `operator` > `viewer`). The highest role wins. If no groups match, the default `viewer` role applies.

```python
def map_groups_to_role(user_groups: list[str], mapping: dict) -> str:
    for role in ["admin", "operator", "viewer"]:
        for group, mapped_role in mapping.items():
            if group in user_groups and mapped_role == role:
                return role
    return "viewer"  # default
```

**Multiple group membership**: A user in both `axiom-admins` and `axiom-operators` receives `admin` (highest wins).

**SSO users and local admin**: The `admin` account created at startup is always a local-auth user. SSO cannot produce an `admin`-role user unless explicitly configured in the group mapping. This preserves the break-glass account.

### Air-Gap Isolation Strategy

SSO must be a zero-footprint addition to CE builds. The existing EE plugin architecture achieves this precisely:

**Extension points the SSO feature uses:**

| Extension Point | What SSO Adds |
|-----------------|---------------|
| `EEContext` dataclass in `ee/__init__.py` | New field: `sso: bool = False` |
| `_mount_ce_stubs()` in `ee/__init__.py` | Two new stubs: `GET /auth/sso/login → 402`, `GET /auth/sso/callback → 402` |
| `load_ee_plugins()` in `ee/__init__.py` | No change — the new SSO EE plugin registers via the `axiom.ee` entry point group |
| New EE router file | `ee/routers/sso_router.py` — contains the real OIDC callback handlers |
| New EE interface file | `ee/interfaces/sso.py` — contains the stub `sso_stub_router` |

**CE code path:** `load_ee_plugins()` finds no EE package → calls `_mount_ce_stubs()` → stubs include `sso_stub_router` → CE users hitting `/auth/sso/login` receive `{"detail": "This feature requires Axiom Enterprise Edition."}` with HTTP 402. No OIDC library is imported. No IdP configuration is read. Zero overhead.

**EE code path:** EE package installed → `load_ee_plugins()` finds the `axiom.ee` entry point → SSO plugin's `register(ctx)` method is called → mounts `sso_router` → sets `ctx.sso = True`. The OIDC callback handlers and Authlib import happen only in the EE package.

**Library isolation:** `authlib` and `httpx` (required for OIDC token exchange) are listed only in the EE package's `pyproject.toml` dependencies, not in the main `puppeteer/requirements.txt`. CE installs never install these libraries.

### Dashboard Routing Changes

The dashboard's login flow requires a small addition:

1. If `ctx.sso == True` (EE), the login page shows an additional "Sign in with SSO" button.
2. Clicking this button redirects the browser to `GET /auth/sso/login` which returns a redirect to the IdP.
3. After the callback, the server redirects the browser to `/?token=<axiom_jwt>`.
4. The dashboard's existing `useEffect` on page load reads `?token=` from the URL, stores it in `localStorage` as `mop_auth_token`, and removes the query parameter. This is the same pattern already used for the device flow approval page.

No new authentication state management is needed in the dashboard. The token arrives the same way regardless of whether it came from password auth or OIDC.

---

## Part 3: Protocol Recommendation

### OIDC vs SAML

**Recommendation: OIDC (OpenID Connect)**

Confidence: HIGH

**Why OIDC is correct for Axiom:**

| Criterion | OIDC | SAML 2.0 |
|-----------|------|----------|
| Token format | JSON / JWT | XML signed assertion |
| Browser support | Native (OAuth redirects + JSON) | Requires XML parsing + base64 POST bindings |
| FastAPI/Python library maturity | Authlib (actively maintained, 1.6.x) | python3-saml (maintained but complex) |
| Axiom codebase alignment | Already uses JWTs, OAuth 2.0 device flow (RFC 8628) | XML is foreign to the codebase |
| Mobile/SPA support | First-class | Limited (POST bindings break SPAs) |
| Implementation complexity | Low-medium | High (XML namespaces, SLO ceremony) |
| Enterprise IdP support | All major IdPs support OIDC | All major IdPs support SAML, but SAML is declining in new deployments |

**The decisive argument:** Axiom already ships an OAuth 2.0 Device Authorization Grant (`POST /auth/device`, `GET /auth/device/approve`). The team understands OAuth 2.0 flow mechanics. OIDC is OAuth 2.0 + an ID token layer (`openid` scope + `/userinfo` endpoint). Adding OIDC is an incremental extension of existing knowledge, not a protocol switch.

**SAML assessment:**
SAML is not recommended for v1 SSO but is not dismissed. Legitimate reasons to consider SAML in a future phase:
- Some enterprise customers (particularly in financial services and healthcare) have IdP policies that require SAML for on-premise applications
- Older enterprise deployments (e.g. ADFS) may not have clean OIDC support

SAML is noted as a **future extension point** in the Admin config (`sso_protocol: "oidc" | "saml"`). A future `axiom.ee.saml` plugin could mount `POST /auth/saml/acs` without touching the OIDC plugin. The two protocols are parallel paths, not mutually exclusive.

**Library recommendation: Authlib 1.6.x**

Authlib is the standard Python OIDC client library. It handles:
- PKCE (Proof Key for Code Exchange) — mandatory for public clients, best practice for all
- Nonce generation and validation (replay attack prevention)
- State parameter management (CSRF protection)
- ID token JWT validation (signature, `iss`, `aud`, `exp`, `nonce` claims)
- Token endpoint exchange via async httpx
- Discovery document fetching (`/.well-known/openid-configuration`)

Authlib requires `SessionMiddleware` from `starlette.middleware.sessions` to store the state/nonce between the authorization redirect and the callback. This middleware stores session data in a signed cookie, not server-side state — stateless, horizontally scalable.

**Installation (EE package only):**
```
authlib>=1.3.0
httpx>=0.27.0
itsdangerous>=2.1.0  # required by SessionMiddleware
```

---

## Part 4: IdP Coverage

### 4.1 Cloudflare Access

Cloudflare Access is a zero-trust network overlay. When Axiom is deployed behind a Cloudflare Tunnel, Access can authenticate users before they reach the Axiom server. This is a different integration pattern from standard OIDC.

**Pattern A: CF Access as OIDC Provider (Standard OIDC)**

Cloudflare Access exposes a standard OIDC provider endpoint. Axiom can use it like any other OIDC provider:

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://<team-name>.cloudflareaccess.com/cdn-cgi/access/sso/oidc/<aud>/.well-known/openid-configuration` |
| Required scopes | `openid email profile` |
| Groups claim | `groups` (populated from Cloudflare Access groups/policies) |
| Provider quirk | `audience` (`aud`) must match the Application AUD tag from the CF Zero Trust dashboard |

**Pattern B: CF Access JWT Header Trust (Header Verification)**

If Axiom is exclusively behind a Cloudflare Tunnel (not accessible directly), Access injects a `Cf-Access-Jwt-Assertion` header on every authenticated request. The server can trust this header after validating the JWT signature.

Integration point: a middleware or `get_current_user` extension that checks for `Cf-Access-Jwt-Assertion` before falling through to the standard Bearer token check.

**Risk: Header Spoofing**

The `Cf-Access-Jwt-Assertion` header can be **injected by any caller that can reach the origin server directly** (bypassing the Cloudflare tunnel). If the origin is accessible on a public IP or local network without the tunnel, a malicious actor can forge the header and impersonate any user.

**Mitigation (mandatory):**
1. **Validate the JWT signature using CF's public key endpoint**: `https://<team-name>.cloudflareaccess.com/cdn-cgi/access/certs`. This endpoint returns the public signing keys as a JWK Set.
2. **Verify the `aud` claim** matches the Application AUD tag for this specific Axiom deployment.
3. **Verify the `iss` claim** is `https://<team-name>.cloudflareaccess.com`.
4. Optionally: lock the origin server to only accept connections from Cloudflare IP ranges (`https://www.cloudflare.com/ips/`).

**Key rotation:** CF rotates the signing key every 6 weeks. Previous keys remain valid for 7 days after rotation. The implementation must fetch keys dynamically (or cache with a short TTL, e.g. 1 hour) rather than pinning a static key.

**Implementation sketch (FastAPI middleware):**
```python
import httpx
from jose import jwt, JWTError

CF_CERTS_URL = "https://{team}.cloudflareaccess.com/cdn-cgi/access/certs"
CF_AUD = os.getenv("CF_ACCESS_AUD")

async def verify_cf_access_token(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CF_CERTS_URL)
        keys = resp.json()["keys"]
    # Try each key (rotation window may have multiple valid keys)
    for key in keys:
        try:
            return jwt.decode(token, key, algorithms=["RS256"], audience=CF_AUD)
        except JWTError:
            continue
    raise ValueError("CF Access JWT validation failed")
```

**Recommendation:** For CF Access deployments, implement Pattern B (header verification) as the primary path — it is simpler for operators who already use CF tunnels. Implement Pattern A (OIDC) as an alternative for non-tunnel deployments that still want CF Access as their IdP.

### 4.2 Okta

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://{okta_domain}/oauth2/{auth_server_id}/.well-known/openid-configuration` |
| Default auth server | `https://{okta_domain}/oauth2/default/.well-known/openid-configuration` |
| Required scopes | `openid email profile groups` |
| Groups claim | `groups` in ID token (requires custom auth server + groups claim configured) |
| Provider quirk | The **org authorization server** (`/oauth2`) does not support custom claims or groups scope. A custom authorization server must be used. This is the default auth server (`/oauth2/default`) or a custom one created in the Okta admin console. |

**Okta-specific setup steps:**
1. Create an OIDC Web Application in Okta Admin → Applications
2. Add `groups` scope to a custom authorization server (Admin → Security → API → Authorization Servers → Claims)
3. Add a Groups claim with filter (e.g. `Starts with: axiom-`) to include only relevant groups
4. Copy the Client ID and Client Secret to Axiom's SSO config

**Groups claim format:** `{"groups": ["axiom-admins", "axiom-operators", "everyone"]}`

### 4.3 Azure AD / Entra ID

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration` |
| Multi-tenant variant | `https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration` |
| Required scopes | `openid email profile` (groups returned via optional claims, not a separate scope) |
| Groups claim | `groups` (contains object GUIDs, not group display names — see quirk below) |

**Provider quirk 1 — Groups claim contains GUIDs, not names:**

Azure AD includes group object GUIDs (e.g. `"6b68c0d3-a..."`) in the `groups` claim, not display names like `axiom-admins`. The Axiom group mapping config must use GUIDs, not names:

```json
{
  "6b68c0d3-aaaa-bbbb-cccc-111122223333": "admin",
  "9f4e1234-dddd-eeee-ffff-000011112222": "operator"
}
```

Alternatively, the implementation can fetch group display names from the Microsoft Graph API at login time using the access token. This adds an API call per login but allows human-readable mapping config.

**Provider quirk 2 — 200 group limit:**

Azure AD truncates the `groups` claim at 200 groups (HTTP header size limit). For users in many groups, the claim is replaced with a `_claim_names` hint pointing to a Graph API endpoint. The implementation should handle this gracefully (fall back to `viewer` role if groups are over-limit, or make the Graph API call).

**Provider quirk 3 — Groups must be enabled in the app manifest:**

The optional claims `groups` must be explicitly added to the application manifest in Entra ID (App registrations → Token configuration → Add groups claim).

**Groups claim format:** `{"groups": ["6b68c0d3-...", "9f4e1234-..."]}`

### 4.4 Google Workspace

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://accounts.google.com/.well-known/openid-configuration` |
| Required scopes | `openid email profile` |
| Groups claim | **None** — Google does not return groups in OIDC tokens |
| Domain restriction | `hd` parameter can restrict login to a specific Workspace domain |

**Provider quirk — No native groups claim:**

Google Workspace does not return group membership in OIDC ID tokens. This is a significant limitation for group-to-role mapping. Two workarounds exist:

1. **Google Admin Directory API**: After token validation, make a server-side call to the Admin SDK Directory API (`admin.googleapis.com/admin/directory/v1/groups?userKey={email}`) using a service account with domain-wide delegation. This requires a Google Cloud service account and domain admin configuration. Adds latency (~100ms) per login.

2. **Domain-only mapping**: Skip group mapping. Assign a default role to all users from the Workspace domain (using the `hd` claim to verify domain). Appropriate for small organisations where all staff should have `operator` access.

**Recommended approach for v1:** Document both options. Default to domain-only mapping (`hd` validation + default `operator` role). Document the Directory API path for organisations needing fine-grained group control.

**`hd` claim usage:**
```python
# Restrict login to company domain
if id_token_claims.get("hd") != expected_domain:
    raise HTTPException(403, "Login restricted to company domain users")
```

**Groups claim format:** Not natively available — requires Directory API call.

### 4.5 Authentik and Keycloak (Self-Hosted IdPs)

Both Authentik and Keycloak are open-source self-hosted IdPs with strong OIDC support and are common in organisations that cannot use cloud IdPs.

**Keycloak:**

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://{keycloak_host}/realms/{realm}/.well-known/openid-configuration` |
| Required scopes | `openid email profile groups` |
| Groups claim | `groups` (requires a custom Group Membership mapper in the Client Scope) |

Setup: In Keycloak admin → Clients → your Axiom client → Client scopes → Create `groups` scope → Add mapper → Group Membership → Token Claim Name: `groups` → Add Full group path: off.

**Groups claim format:** `{"groups": ["/axiom-admins", "axiom-operators"]}` (with or without leading slash depending on "Full group path" setting).

**Authentik:**

| Parameter | Value |
|-----------|-------|
| OIDC discovery URL | `https://{authentik_host}/application/o/{application-slug}/.well-known/openid-configuration` |
| Required scopes | `openid email profile` + custom scope for groups |
| Groups claim | Requires creating a custom Scope Mapping (Customization → Property Mappings) with an expression that returns user groups |

**Authentik setup for groups claim:**
Create a Scope Mapping with expression:
```python
return {
    "groups": [g.name for g in request.user.ak_groups.all()]
}
```
Bind this mapping to the application's provider.

**Groups claim format:** `{"groups": ["axiom-admins", "axiom-operators"]}`

**Self-hosted quirk:** Discovery endpoint availability. Self-hosted IdPs may have SSL certificates signed by a private CA. The implementation must allow configuring a custom CA cert or disabling TLS verification (with a warning) for self-hosted deployments.

---

## Part 5: 2FA Interaction Policy

### The Problem

Axiom supports TOTP-based 2FA for step-up authentication on sensitive actions. When a user authenticates via SSO, the IdP may already have enforced MFA. The question is: does the IdP's MFA satisfy Axiom's TOTP requirement, or must the user also complete Axiom's TOTP step-up?

### Two Configurable Modes

The operator configures the policy in the `Config` table (key: `sso_2fa_mode`, values: `"idp"` or `"always"`). The default is `"idp"` (Mode A).

**Mode A: `"idp"` — SSO satisfies 2FA**

If the IdP enforced MFA during the OIDC login (detectable via the `amr` claim in the ID token — `"mfa"` or specific method values like `"otp"`, `"swk"`), Axiom skips its own TOTP step-up. The assumption is that the IdP's MFA is at least as strong as Axiom's TOTP.

Detection of IdP MFA:
```python
amr = id_token_claims.get("amr", [])
idp_mfa_satisfied = "mfa" in amr or "otp" in amr or "swk" in amr
```

If the IdP's MFA claim is not present or not recognisable, Axiom falls back to requiring TOTP (safe default).

This mode is appropriate for organisations where the IdP enforces MFA policy centrally and double-prompting users (IdP MFA + Axiom TOTP) would cause friction.

**Mode B: `"always"` — Always require Axiom TOTP**

Axiom always requires its own TOTP step-up regardless of what the IdP reported. The `amr` claim is ignored. This is the belt-and-suspenders mode for paranoid deployments where the operator does not fully trust the IdP's MFA enforcement (e.g. the IdP may have MFA-bypass policies for certain users or devices).

### SSO User Without TOTP Enrolled

When an SSO user hits a step-up action and Mode B is configured (or Mode A and the IdP didn't enforce MFA):

1. If the user has TOTP enrolled: show the TOTP prompt (existing flow, unchanged)
2. If the user does **not** have TOTP enrolled: show a **TOTP enrolment prompt** — not a hard block and not a silent bypass

The enrolment prompt presents a QR code (TOTP secret generated server-side, stored encrypted in the User record or a linked TOTP table). The user scans it, enters the first code to verify enrolment, and then proceeds past the step-up.

This prevents two failure modes:
- **Silent bypass**: Ignoring the TOTP requirement because the user lacks TOTP creates a security hole
- **Lock-out**: Refusing access entirely to SSO users without TOTP would break first-time SSO logins

The graceful degradation policy is: SSO users in Mode B are prompted to enrol TOTP on their first encounter with a step-up action. Until enrolled, they cannot perform that specific action. They can use the rest of Axiom normally.

### `amr` Claim Reference

The `amr` (Authentication Methods References) claim is defined in RFC 8176. Common values:

| `amr` Value | Meaning |
|-------------|---------|
| `pwd` | Password only |
| `mfa` | Multiple-factor authentication (generic) |
| `otp` | One-time password (TOTP/HOTP) |
| `swk` | Software key (e.g. passkey) |
| `hwk` | Hardware key (FIDO2) |
| `sms` | SMS OTP |

Not all IdPs set `amr`. If absent, treat as password-only for Mode A purposes.

---

## Part 6: CLI SSO (axiom-push)

### The Complexity Problem

Axiom's CLI (`axiom-push`, defined in `pyproject.toml` → `[project.scripts]`) currently obtains tokens via the RFC 8628 Device Authorization Grant. The user runs `axiom-push`, a device code is issued, the user approves it in the dashboard browser, and the CLI polls until a token is issued.

CLI SSO would mean: `axiom-push` authenticates the user against the IdP via OIDC, then presents that credential to Axiom for a token.

The complication: **OIDC also has a device flow** (RFC 8628 is protocol-agnostic; it works with any OAuth 2.0 authorization server). In theory, if the IdP supports device flow, the CLI could initiate an OIDC device flow directly with the IdP, receive an ID token, and exchange it at a new Axiom endpoint (`POST /auth/sso/token-exchange`) for an Axiom JWT.

**Why this is genuinely harder than dashboard SSO:**

1. **IdP device flow support is not universal.** Okta supports it; Azure AD supports it; Keycloak requires configuration; Authentik has varying support; Google restricts it to first-party apps. CF Access does not expose an OIDC device flow.

2. **Two separate device flows.** Today, `axiom-push` runs one device flow (against Axiom's `/auth/device`). With IdP SSO, the CLI would run the IdP's device flow (getting an IdP token), then exchange that for an Axiom token. This is two sequential async round-trips. The UX is: "Visit this URL to authenticate with your IdP. Then your CLI will get an Axiom token." This is technically sound but confusing.

3. **PKCE and redirect URIs.** The OIDC authorization code flow requires a browser redirect to a callback URL. CLIs handle this by spawning a local HTTP listener (`localhost:PORT/callback`). This works on desktop but not in server-only environments.

4. **Token lifetime mismatch.** IdP device flow tokens may have shorter lifetimes than Axiom's 24-hour JWTs.

### Recommendation: Defer CLI SSO

CLI SSO is a valid feature but has substantially more complexity than dashboard SSO. The recommended approach:

1. **Phase 1 (current scope):** Dashboard SSO ships. CLI users authenticate via the existing device flow (they visit the dashboard, approve the code). If SSO is enabled, the dashboard handles the SSO login — the device flow approval page works unchanged.

2. **Phase 2 (future):** CLI SSO via IdP device flow, for IdPs that support it. This is a separate design with its own complexity budget.

**What the CLI can do today with SSO enabled:**

The existing device flow is not blocked by SSO. When a CLI user visits the device approval URL, the dashboard shows the approval page. If SSO is the user's login method, they log in to the dashboard via SSO, and then approve the device code. The Axiom JWT issued to the CLI carries the SSO user's role. **No CLI changes are needed for dashboard SSO to work end-to-end.**

---

## Part 7: Prior Art

### Grafana (OIDC + Generic OAuth + LDAP)

Grafana is the canonical example of a self-hosted tool with mature, multi-IdP SSO. Relevant patterns:

- **`role_attribute_path`**: A JMESPath expression evaluated against the ID token claims to derive a role. Example: `contains(groups[*], 'axiom-admins') && 'Admin' || 'Viewer'`. This is more flexible than a static mapping table but requires users to know JMESPath.
- **Re-sync on every login**: Grafana re-evaluates role mapping on each login — the same policy Axiom adopts.
- **`auto_assign_org_role`**: Default role for new users with no matching group — equivalent to Axiom's `viewer` default.
- **Multiple providers**: Grafana supports configuring one provider at a time per type. Axiom v1 can follow the same model (one OIDC provider configured at a time).

**Takeaway for Axiom:** The JMESPath approach is powerful but complex. For Axiom v1, the static `{"group_name": "role"}` mapping config is simpler and sufficient. JMESPath expressions can be added as a v2 enhancement.

Sources: [Grafana Okta OIDC docs](https://grafana.com/docs/grafana/latest/setup-grafana/configure-authentication/okta/)

### Gitea (OIDC Groups → Organization Teams)

Gitea added OIDC group-to-team mapping in v1.19. Relevant patterns:

- **Team sync, not just role sync**: Gitea maps OIDC groups to organization teams. Axiom's model is simpler (groups → one of three roles), not team membership.
- **`GroupTeamMap`**: JSON config mapping group names to org/team pairs. The config-as-JSON approach (stored in the auth source config) is the same pattern Axiom uses for `Config` table key/value.
- **Sync on every login**: Same policy as Axiom's design. Gitea explicitly notes that removing a user from a group takes effect on next login.

**Takeaway for Axiom:** The pattern of "store mapping as JSON config, re-apply on every login" is validated by Gitea's production implementation.

Sources: [Gitea Feature Preview: Mapping OIDC Groups to Teams](https://blog.gitea.com/feature-preview-mapping-oidc-groups-to-teams/)

### HashiCorp Vault (OIDC Auth Method)

Vault's OIDC auth method is the most sophisticated prior art. Relevant patterns:

- **Role-based claim binding**: Vault's OIDC roles define claim bindings — which claims from the ID token map to Vault policies. Multiple roles can be configured, each matching a different set of groups.
- **Bound audiences and subjects**: Vault validates `aud` and `sub` claims as preconditions before mapping groups to policies. This prevents cross-IdP token reuse.
- **Provider-specific quirks built-in**: Vault has provider-specific config blocks for Azure, Google, and GitHub, each handling the quirks described above (GUIDs vs names, Directory API for Google, etc.).
- **CLI device flow + OIDC**: Vault supports `vault login -method=oidc` which spawns a local HTTP listener for the OIDC callback. This is the CLI SSO pattern that Axiom's Phase 2 could follow.

**Takeaway for Axiom:** Vault's approach of provider-specific config blocks (rather than a single generic OIDC config) is the right model. Axiom's SSO config should have a `provider_type` field (`okta`, `azure`, `google`, `keycloak`, `authentik`, `cf_access`) that enables provider-specific handling (GUIDs for Azure, `hd` for Google, etc.).

Sources: [Vault Azure AD OIDC docs](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/azuread), [Vault Google OIDC docs](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/google)

### Argo CD (OIDC + Dex)

Argo CD uses [Dex](https://dexidp.io/) as an OIDC identity broker. Rather than speaking to each IdP directly, all IdP-specific handling is delegated to Dex, and Argo CD only speaks OIDC to Dex. This is an architectural pattern worth noting:

**Dex as an OIDC broker:** A self-hosted Dex instance federates multiple upstream providers (LDAP, SAML, GitHub, Okta, etc.) and exposes a single OIDC endpoint to the application. The application has one OIDC config; Dex handles all IdP-specific quirks.

**When this pattern makes sense:** Organisations with multiple upstream IdPs, or those needing SAML-to-OIDC translation. For Axiom v1 (single configured IdP), this adds unnecessary infrastructure. Worth noting as a v3+ option if multi-IdP support is required.

---

## Part 8: Complexity/Value Recommendation

### Effort Assessment

| Component | Effort | Notes |
|-----------|--------|-------|
| EE plugin scaffold (`sso_router.py`, `sso.py` stub, `EEContext.sso` flag) | Small (~1 plan) | Pattern already exists in `auth_ext_router.py` |
| Authlib OIDC client setup + callback handler | Small-medium (~1 plan) | Standard Authlib pattern, well-documented |
| User upsert + group mapping logic | Small (~0.5 plan) | Pure Python, straightforward |
| DB migration SQL (new `User` columns) | Trivial | Same pattern as previous migrations |
| Admin config UI (IdP config form in Admin.tsx) | Medium (~1 plan) | New form with provider_type selector + fields |
| Dashboard login page (SSO button + redirect) | Small (~0.5 plan) | Additive change to Login.tsx |
| CF Access header verification middleware | Small (~0.5 plan) | Standalone middleware, well-defined |
| 2FA interaction policy (Mode A/B) | Small-medium (~1 plan) | Requires TOTP enrolment flow for new SSO users |
| Per-IdP testing + documentation | Medium (~1 plan) | Manual testing against each IdP |
| **Total estimate** | **~6–7 plans** across 2–3 phases | |

### Recommended Implementation Phases

**Phase A: Core SSO (EE plugin, OIDC, Okta + Azure + Keycloak)**
- EE plugin scaffold
- Authlib OIDC callback handler
- User upsert + group mapping
- Admin config UI
- Dashboard SSO button
- Estimated: 3–4 plans

**Phase B: CF Access + Google + Authentik + 2FA policy**
- CF Access header verification middleware
- Google Workspace (domain restriction + optional Directory API path)
- Authentik/Keycloak verification
- Mode A/B 2FA policy
- TOTP enrolment prompt for SSO users
- Estimated: 2–3 plans

**Phase C: CLI SSO (deferred, future milestone)**
- OIDC device flow for supporting IdPs
- `POST /auth/sso/token-exchange` endpoint
- `axiom-push` CLI updates

### Value Assessment

SSO is a **table-stakes enterprise requirement**. No operator-facing SaaS or self-hosted enterprise tool ships without SSO in 2025. The value is:

1. **Licence-tier differentiator**: SSO as EE-only reinforces the CE/EE split and provides a clear reason for organisations to purchase EE licences.
2. **Offboarding automation**: The re-sync-on-login pattern, combined with `token_version` invalidation, means offboarding is instant and requires no Axiom-side action.
3. **Compliance**: Centralised authentication is a requirement in SOC 2, ISO 27001, and most enterprise security frameworks.

### Draft Implementation Sketch

The following is concrete enough for a developer to start implementation without further design work.

**New files (EE package):**

```
puppeteer/agent_service/ee/routers/sso_router.py      # Real OIDC handlers
puppeteer/agent_service/ee/interfaces/sso.py           # Stub router (CE)
```

**New routes (EE only):**

```
GET  /auth/sso/login                 → Redirect to IdP authorization endpoint
GET  /auth/sso/callback              → Exchange code, upsert user, issue Axiom JWT
POST /auth/sso/logout                → Back-channel logout — increment token_version
GET  /auth/sso/config                → Return current SSO config for dashboard (public fields only)
```

**CE stubs (402):**

```
GET  /auth/sso/login   → 402
GET  /auth/sso/callback → 402
```

**Admin config keys (Config table):**

| Key | Type | Example |
|-----|------|---------|
| `sso_enabled` | `"true"` / `"false"` | `"true"` |
| `sso_provider_type` | string | `"okta"` |
| `sso_client_id` | string | `"0oa..."` |
| `sso_client_secret` | string (Fernet-encrypted) | `"..."` |
| `sso_discovery_url` | string | `"https://..."` |
| `sso_group_mapping` | JSON string | `'{"axiom-admins":"admin"}'` |
| `sso_default_role` | string | `"viewer"` |
| `sso_2fa_mode` | `"idp"` / `"always"` | `"idp"` |
| `sso_allowed_domain` | string (Google only) | `"example.com"` |

**Migration SQL (`migration_v_sso.sql`):**

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_subject VARCHAR(255);
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `puppeteer/agent_service/tests/` (existing) |
| Quick run command | `cd puppeteer && pytest tests/ -k sso -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SSO-01 | Protocol recommendation documented | Manual review | N/A — design doc output | N/A |
| SSO-02 | JWT bridge design documented | Manual review | N/A — design doc output | N/A |
| SSO-03 | RBAC group mapping documented | Manual review | N/A — design doc output | N/A |
| SSO-04 | CF Access integration documented | Manual review | N/A — design doc output | N/A |
| SSO-05 | Air-gap isolation documented | Manual review | N/A — design doc output | N/A |
| SSO-06 | 2FA interaction policy documented | Manual review | N/A — design doc output | N/A |

Note: Phase 58 is a research-only phase. All deliverables are design documents. Validation is human review of completeness against the success criteria in CONTEXT.md, not automated tests. The test map above is trivially satisfied because the deliverable is this document itself.

### Wave 0 Gaps

None — this phase produces no code. The test infrastructure for SSO implementation will be designed in the implementation phase that consumes this document.

---

## Open Questions

1. **Back-channel logout universality**
   - What we know: OIDC Back-Channel Logout (RFC 7009 + draft-ietf-oauth-backchannel-logout) is supported by Okta and Azure; not all IdPs implement it
   - What's unclear: whether `POST /auth/sso/logout` should be a REQUIRED endpoint or OPTIONAL (only wired up for IdPs that support back-channel logout)
   - Recommendation: Mark as OPTIONAL in the implementation; document that front-channel logout (user clicks logout in Axiom) is the fallback for IdPs without back-channel support

2. **Username collision between local auth and SSO users**
   - What we know: Axiom uses `username` as the primary key; SSO derives username from email prefix
   - What's unclear: if `admin` logs in via password and an SSO user has email `admin@company.com`, the callback would collide
   - Recommendation: SSO callback should check whether the resolved username has `sso_subject IS NULL` (local-auth user) and reject the collision with a clear error; the admin should pre-configure a username prefix/suffix for SSO users if collision is likely (e.g. `sso_username_prefix: "sso_"`)

3. **TOTP model for SSO users**
   - What we know: No `UserTOTP` table exists in the current schema; TOTP step-up is referenced in the `must_change_password` flow but the actual TOTP enrolment/verification code is not yet implemented
   - What's unclear: TOTP may not yet be fully implemented in the codebase — if so, the 2FA interaction policy (SSO-06) depends on a prerequisite that doesn't exist
   - Recommendation: The implementation phase for 2FA policy should first audit whether TOTP step-up is implemented; if not, Mode B (`"always"`) and the enrolment prompt may need to be scoped as a sub-feature

4. **Multi-IdP support**
   - What we know: v1 design assumes one configured OIDC provider at a time
   - What's unclear: some organisations have multiple IdPs (e.g. two business units with different Okta tenants)
   - Recommendation: v1 is single-provider; multi-provider (multiple `sso_*` config sets) is deferred to v2

---

## Sources

### Primary (HIGH confidence)
- Cloudflare official docs: [Validate JWTs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/) — key rotation (6 weeks), header vs cookie, signature verification requirement
- Cloudflare official docs: [FastAPI JWT validation tutorial](https://developers.cloudflare.com/cloudflare-one/tutorials/fastapi/) — RS256, JWK Set endpoint, AUD validation
- Authlib official docs: [FastAPI OAuth Client](https://docs.authlib.org/en/latest/client/fastapi.html) — SessionMiddleware requirement, PKCE, nonce handling
- Okta Developer docs: [Customize tokens with groups claim](https://developer.okta.com/docs/guides/customize-tokens-groups-claim/main/) — custom auth server requirement, groups scope
- Microsoft Learn: [OIDC on Microsoft identity platform](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc) — discovery URL format, v2.0 endpoint
- HashiCorp Vault docs: [Azure AD OIDC](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/azuread), [Google OIDC](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/google) — provider quirks, Directory API pattern
- RFC 8176: Authentication Method Reference Values — `amr` claim values

### Secondary (MEDIUM confidence)
- Grafana docs: [Configure Okta OIDC authentication](https://grafana.com/docs/grafana/latest/setup-grafana/configure-authentication/okta/) — re-sync on login pattern, default role
- Gitea Blog: [Feature Preview: Mapping OIDC Groups to Teams](https://blog.gitea.com/feature-preview-mapping-oidc-groups-to-teams/) — JSON mapping config pattern
- Keycloak docs: [Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/index.html) — groups claim mapper configuration
- Security Boulevard: [OIDC vs SAML 2025](https://securityboulevard.com/2025/05/oidc-vs-saml-which-is-better-for-sso/) — current enterprise recommendations

### Tertiary (LOW confidence — flagged for validation)
- Google Workspace groups claim: no native groups in OIDC tokens — confirmed by multiple sources (HashiCorp Vault docs, headscale issue tracker) but Google's official OIDC docs do not explicitly state this limitation; verify against current Google Identity Platform docs before implementation

---

## Metadata

**Confidence breakdown:**
- Protocol recommendation (OIDC): HIGH — confirmed by multiple authoritative sources, aligned with existing codebase
- JWT bridge design: HIGH — derived directly from existing `create_access_token()`, `token_version`, and `get_current_user()` patterns in the codebase
- CF Access integration: HIGH — verified against official Cloudflare docs
- Okta, Azure, Keycloak integration: HIGH — verified against official provider docs
- Google Workspace groups limitation: MEDIUM — multiple sources agree, but verify against official Google Identity docs before implementation
- Authentik integration: MEDIUM — official docs exist but are less comprehensive than enterprise IdP docs
- 2FA interaction policy: HIGH — `amr` claim is RFC 8176 standard; Mode A/B design is internally consistent
- CLI SSO complexity assessment: HIGH — complexity argument is structural (two sequential device flows), not library-specific

**Research date:** 2026-03-24
**Valid until:** 2026-09-24 (stable protocols; individual IdP discovery URL formats should be re-verified before implementation)

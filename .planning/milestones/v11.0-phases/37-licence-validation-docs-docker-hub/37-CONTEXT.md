# Phase 37: Licence Validation + Docs + Docker Hub - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement Ed25519 offline licence key enforcement in the EE plugin (DIST-01), update MkDocs docs with CE/EE admonition callouts on EE-only feature pages (DIST-03), and add a `GET /api/licence` endpoint + dashboard edition badge. Docker Hub publish (DIST-02) is deferred — GHCR covers all current deployment scenarios.

</domain>

<decisions>
## Implementation Decisions

### Licence key format
- Wire format: `base64url(json_payload).base64url(ed25519_sig)` — two-part dot-separated string, passed as `AXIOM_LICENCE_KEY` env var
- Payload fields: `customer_id` (string), `exp` (Unix timestamp), `features` (list of feature name strings e.g. `["foundry", "webhooks", "triggers"]`)
- Features field is a list of enabled feature names — enables per-customer feature gating in future without a format change
- Ed25519 public key hardcoded as bytes literal directly in `ee/plugin.py` — gets compiled into the `.so`, no file I/O, works fully offline
- Validation logic lives at the top of `EEPlugin.register()` before any router mounts — invalid/expired = early return, all flags stay false

### Validation failure behaviour
- **Key absent**: INFO log "AXIOM_LICENCE_KEY not set — running in Community Edition mode", register() exits early, all flags false
- **Signature invalid** (tampered or wrong key): WARNING log "Invalid licence signature — EE features disabled", register() exits early, all flags false
- **Licence expired** (valid sig, `exp` in the past): WARNING log "Licence expired on [date] — EE features disabled", same CE-only fallback
- No grace period — expired key = CE mode on next restart (matches DIST-01 success criterion exactly)
- No startup refusal — server always starts, EE features are simply absent

### Licence metadata API
- New endpoint: `GET /api/licence` — returns `{edition, customer_id, expires, features}` when a valid key is loaded; returns `{edition: "community"}` in CE mode
- `/api/features` is unchanged — continues to return only feature flags
- `GET /api/licence` is readable by all authenticated users (dashboard needs it for the nav badge)

### Dashboard edition visibility
- **Nav badge**: Persistent "Community Edition" or "Enterprise Edition" label in the sidebar/header — derived from `GET /api/licence`, visible to all users
- **Admin panel**: Dedicated licence section showing `customer_id`, expiry date, enabled features list — for admins only, reads from `GET /api/licence`

### Docs admonition scope
- **Pages to update** (5 EE feature guides only): `feature-guides/foundry.md`, `feature-guides/rbac.md`, `feature-guides/rbac-reference.md`, `feature-guides/oauth.md`, `feature-guides/axiom-push.md`
- Getting-started, security, developer, and runbook pages are not modified
- **Placement**: just before the first EE-specific section on each page (not top-of-page)
- **Wording**: label-only — `!!! enterprise` with no body text
- **New page**: `docs/docs/licensing.md` — explains CE/EE split, how to set `AXIOM_LICENCE_KEY`, what happens when it expires

### Docker Hub
- **Deferred** — GHCR (`ghcr.io/axiom-laboratories/axiom`) covers all current deployment scenarios
- No new credentials, no additional CI steps required for v11.0
- Docker Hub can be added in a future phase when marketing to new users who browse Docker Hub for tools

### Claude's Discretion
- Exact Python implementation of base64url decode + Ed25519 verify (use `cryptography` library, already in requirements)
- Whether to extract licence parsing to a helper function inside `plugin.py` or inline it
- Exact structure of the Admin panel licence section in the React dashboard
- mkdocs.yml navigation entry placement for the new `licensing.md` page
- Which `GET /api/licence` fields to include for an expired/invalid key (e.g. whether to expose the raw expiry even when it's past)

</decisions>

<specifics>
## Specific Ideas

- The `cryptography` library is already in `puppeteer/requirements.txt` — use `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey` for verification, no new dependency needed
- Licence key generation for testing: a simple Python script using `cryptography` to generate an Ed25519 keypair and produce a signed test key — lives in `mop_validation/scripts/generate_licence_key.py`
- The nav edition badge should be visually distinct: "CE" in a neutral colour, "EE" in the brand accent colour — reinforces the commercial value of EE at a glance

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ee/plugin.py`: `EEPlugin.register()` is where licence validation goes — add check at top before Step 1 (model imports)
- `puppeteer/agent_service/main.py`: existing `/api/features` endpoint is the pattern to follow for `GET /api/licence`
- `puppeteer/requirements.txt`: `cryptography` already present — Ed25519 verification needs no new dependency
- `puppeteer/dashboard/src/views/Admin.tsx`: existing Admin panel — add licence section here
- `docs/docs/feature-guides/`: 5 files to add `!!! enterprise` admonitions to

### Established Patterns
- `app.state.ee` (EEContext) holds feature flags set by `EEPlugin.register()` — licence validation reads `AXIOM_LICENCE_KEY` env var and conditionally populates these
- Existing admonition styles in use: `!!! danger`, `!!! warning`, `!!! tip` — `!!! enterprise` is a new custom type, needs to be registered in `mkdocs.yml` custom admonitions or use a standard type with a title override
- Auth pattern: `Depends(get_current_user)` for user-readable endpoints; `Depends(require_permission("admin:read"))` for admin-only — `/api/licence` uses the former

### Integration Points
- `ee/plugin.py` `register()`: add licence check block before existing Step 1 (model imports)
- `puppeteer/agent_service/main.py`: add `GET /api/licence` route — reads parsed licence data stored on `app.state` during plugin load
- `puppeteer/dashboard/src/`: add edition badge to main layout component (sidebar/header), add licence section to `Admin.tsx`
- `docs/mkdocs.yml`: add `licensing.md` to nav, register `enterprise` custom admonition if needed

</code_context>

<deferred>
## Deferred Ideas

- **Docker Hub publish** (`axiom-laboratories/axiom-ce`) — GHCR is sufficient for current deployment scenarios; add when marketing to new users browsing Docker Hub
- **Licence issuance portal** — already in REQUIREMENTS.md as DIST-04 (v12.0+)
- **Periodic licence re-validation** — DIST-05 (v12.0+); v11.0 is startup-only per DIST-01 spec

</deferred>

---

*Phase: 37-licence-validation-docs-docker-hub*
*Context gathered: 2026-03-20*

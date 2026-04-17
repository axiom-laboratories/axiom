# Phase 164: Adversarial Audit Remediation - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the critical and high-severity findings from the adversarial audit conducted 2026-04-17. Reports are in `/home/thomas/Development/mop_validation/adversarial_audit_20260417/`. This phase covers: mTLS enforcement (SEC-01), Foundry RCE mitigation (SEC-02), Alembic migration framework adoption (ARCH-01), Caddy internal TLS fix (SEC-04), hardcoded public key extraction (QUAL-02), and FE/BE gap fixes (FEBE-01, FEBE-02, FEBE-03).

New capabilities (HSM, subprocess build replacement, EE plugin architecture, main.py decomposition) are explicitly out of scope and deferred.

</domain>

<decisions>
## Implementation Decisions

### mTLS Enforcement (SEC-01)
- Caddy enforces client certificate requirement on node-facing routes: `/work/pull`, `/heartbeat`
- Caddy forwards `X-SSL-Client-CN` header to the application after successful TLS handshake
- Revocation enforced at Caddy layer via CRL check at handshake time — rejected nodes never reach the application
- Application (`verify_client_cert`) reads `X-SSL-Client-CN`, looks up the node, and validates against the `RevokedCert` table as defense-in-depth. If header is missing or forged, application rejects.
- `/api/enroll` stays unauthenticated at the TLS layer — cert bootstrap by definition has no cert yet. JOIN_TOKEN is the sole auth mechanism for enrollment. Caddy does NOT require client cert on this route.
- `verify_client_cert` must be wired up as a `Depends()` on `/work/pull` and `/heartbeat` routes (currently imported but never used as a dependency)

### Alembic Migration Framework (ARCH-01)
- Full Alembic adoption with squash baseline strategy
- Baseline: one initial revision representing the full current schema (equivalent to all 48 SQL files applied)
- Existing production DB is stamped with `alembic stamp head` — no re-running historical migrations
- Existing 48 `migration_vXX.sql` files are deleted after baseline is created (clean slate)
- Alembic revision files live in `puppeteer/agent_service/migrations/`
- Alembic runs automatically in FastAPI lifespan startup: `alembic upgrade head` executes before `init_db()` (which handles `create_all` for any remaining gaps)
- Future schema changes go through Alembic `revision --autogenerate`, not new SQL files

### Foundry RCE Mitigation (SEC-02)
- Whitelist approach: `injection_recipe` must contain only permitted Dockerfile instructions
- Permitted instructions: `RUN pip install`, `RUN apt-get install`, `RUN apk add`, `RUN npm install`, `RUN yum install` (package managers only for RUN), `ENV`, `COPY`, `ARG`
- All other RUN variants (e.g. `RUN cat`, `RUN rm`, `RUN curl`) are rejected
- Validation happens at both layers:
  1. **API layer** — blueprint create/update rejects invalid recipes with a clear error message
  2. **Build time** — `foundry_service.py` validates again before appending to Dockerfile (defense-in-depth)
- UI (`CreateBlueprintDialog`) shows inline warning highlighting blocked instructions before the user saves

### Caddy Internal TLS (SEC-04)
- Replace `tls_insecure_skip_verify` in Caddyfile with proper certificate verification for Caddy → agent internal traffic
- Agent service already has certs available via `certs-volume` — Caddy should trust the internal CA rather than skipping verification

### Hardcoded Public Keys (QUAL-02)
- `_LICENCE_PUBLIC_KEY_BYTES` and `_MANIFEST_PUBLIC_KEY_PEM` move from hardcoded Python source to environment variables: `LICENCE_PUBLIC_KEY` and `MANIFEST_PUBLIC_KEY`
- Consistent with how `ENCRYPTION_KEY`, `SECRET_KEY`, etc. already work in this codebase
- Allows key rotation via environment variable change without redeployment

### FE/BE Path Alignment (FEBE-02)
- Audit all frontend `fetch` / `authenticatedFetch` calls for routes missing the `/api/` prefix
- Full alignment: every API call from the dashboard goes through `/api/`
- Backend routes updated if needed to match

### 402 Licence Expired Handling (FEBE-01)
- Dashboard intercepts HTTP 402 responses in `authenticatedFetch` (or equivalent) and shows a "Licence Expired" prompt rather than a generic error
- Consistent with how 401 redirects to `/login`

### Claude's Discretion
- Exact Caddy CRL configuration syntax (file-based vs URL-based CRL)
- Alembic baseline revision comment/documentation detail
- Exact wording of the 402 "Licence Expired" UI prompt
- Whether QUAL-01 (EE stub tagging), QUAL-03 (path normalization), QUAL-04 (broad exceptions) get opportunistic cleanup during this phase

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `verify_client_cert` in `security.py:127` — already exists as a stub, just needs implementation and wiring
- `verify_node_secret` in `security.py` — existing pattern for node authentication; `verify_client_cert` should follow the same `Depends()` pattern
- `authenticatedFetch` in `src/auth.ts` — existing auth wrapper; 401 handling already there, 402 handling goes here
- `CreateBlueprintDialog.tsx` — existing UI component for blueprint creation; inline validation goes here

### Established Patterns
- `Depends(require_auth)` / `Depends(verify_node_secret)` — FastAPI dependency injection pattern for route auth; mTLS enforcement uses same pattern
- `ENCRYPTION_KEY` / `SECRET_KEY` env vars in `security.py` — model for `LICENCE_PUBLIC_KEY` / `MANIFEST_PUBLIC_KEY` extraction
- `tls_insecure_skip_verify` appears in all Caddy reverse_proxy blocks — SEC-04 fix touches the Caddyfile

### Integration Points
- `puppeteer/agent_service/main.py` — lifespan startup is where `alembic upgrade head` call goes (before `init_db()`)
- `puppeteer/cert-manager/Caddyfile` — mTLS enforcement (client_auth policy) and SEC-04 fix (internal TLS)
- `puppeteer/agent_service/services/foundry_service.py:288` — line where `injection_recipe` is appended raw; validation goes here
- `puppeteer/agent_service/main.py` — blueprint create/update routes; API-layer validation goes here
- `puppeteer/agent_service/ee/` — location of hardcoded public keys for QUAL-02

### Audit Report Locations
- `/home/thomas/Development/mop_validation/adversarial_audit_20260417/SECURITY_VULNERABILITIES.md`
- `/home/thomas/Development/mop_validation/adversarial_audit_20260417/ARCHITECTURAL_DEBT.md`
- `/home/thomas/Development/mop_validation/adversarial_audit_20260417/FE_BE_GAPS.md`
- `/home/thomas/Development/mop_validation/adversarial_audit_20260417/CODE_QUALITY_ANTIPATTERNS.md`

</code_context>

<specifics>
## Specific Ideas

- Alembic baseline: squash all 48 SQL files into one initial revision. Single deployment to stamp. Delete the SQL files after.
- mTLS: "We're the only users right now" — straightforward to stamp existing DB and adopt Alembic cleanly with no legacy customer drift concerns.
- Foundry whitelist: the allowed RUN patterns should be scoped to package managers only. `RUN cat`, `RUN curl`, `RUN wget` etc. are not legitimate recipe use cases.

</specifics>

<deferred>
## Deferred Ideas

- **SEC-03: HSM / key rotation** — Hardware security modules and multi-layered encryption. Major infrastructure change, own phase.
- **ARCH-02: Replace subprocess docker build** — Kaniko or buildah-python instead of `subprocess`. Large Foundry rework, own phase.
- **ARCH-03: EE plugin architecture** — Move from `/tmp/ee_patches` to a proper dependency injection plugin system. Major EE rework, own phase.
- **ARCH-04: Decompose monolithic main.py** — Split 4000-line `main.py` into focused routers/modules. Large refactor, own phase.
- **QUAL-01: EE stub tagging pattern** — `_STUB_TAG = '__ee_stub__'` fragility. Low priority.
- **QUAL-03: Manual path normalization** — CRLF→LF normalization drift risk. Low priority.
- **QUAL-04: Broad catch-all exceptions** — `except Exception:` cleanup. Low priority.

</deferred>

---

*Phase: 164-adversarial-audit-remediation*
*Context gathered: 2026-04-17*

# Phase 167: HashiCorp Vault Integration (EE) - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add HashiCorp Vault as an optional external secrets backend, gated behind the EE licence. Covers: AppRole auth service layer, DB-backed config, job dispatch secret injection (server-side), lease renewal, health status, and graceful degradation when Vault is offline. CE users with no EE key cannot access Vault endpoints (403). CE users without Vault config are unaffected — existing Fernet-only mode continues unchanged.

</domain>

<decisions>
## Implementation Decisions

### EE Gating
- **D-01:** Vault integration stays behind the EE licence gate. `vault_service.py` lives in `ee/` (or `ee/services/`), not in `agent_service/services/`. CE nodes get 403 on all `/admin/vault/*` endpoints. No change to CE behaviour.
- **D-02:** Licence model rationale (locked): Apache 2.0 for the main repo, `hvac >= 1.2.0` is also Apache 2.0 (zero upstream friction). BUSL 1.1 applies to the HashiCorp Vault *server* not the client library and only restricts competing managed services — not our use case. The EE gate is voluntary commercial strategy, not a legal obligation.

### Secret Injection Model
- **D-03:** Server-side resolve. The puppeteer (control plane) fetches secret values from Vault using AppRole credentials at job dispatch time, then injects them as `VAULT_SECRET_<NAME>` env vars into the job's execution context. Vault credentials never leave the control plane. Nodes remain untrusted workers — they receive resolved env vars, not Vault tokens.
- **D-04:** Secret names are declared on the job definition (`vault_secrets: list[str]`). At dispatch, each name resolves to `VAULT_SECRET_<NAME>=<value>`. The signed script content is never modified — signature integrity is preserved. If a secret cannot be resolved, dispatch fails with a clear error (not silently omitted).

### Vault Config Storage
- **D-05:** DB-backed with env-var bootstrap. A `VaultConfig` row in the DB holds: `vault_address`, `role_id`, `secret_id` (Fernet-encrypted), `mount_path` (default `secret`), `namespace` (optional for Vault Enterprise), `enabled` bool. Env vars (`VAULT_ADDRESS`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID`) seed the DB on first boot if the row doesn't exist. Config is editable via the Admin UI without restarting containers. The Fernet key already used for secrets-at-rest encrypts `secret_id` in the DB.
- **D-06:** Feature is active when `VaultConfig.enabled = true` and `vault_address` is set. If no `VaultConfig` row exists (CE install or new EE install before configuration), vault_service is dormant — no startup errors, no retry loops.

### Fallback & Graceful Degradation
- **D-07:** Boot clean, fail at dispatch. Platform starts normally regardless of Vault availability. If Vault is unreachable at boot (or at any point), `vault_service` sets internal status to `DEGRADED`. Jobs that declare `use_vault_secrets: true` fail at dispatch with a descriptive error: `"Vault unavailable (status: DEGRADED) — cannot resolve secrets for this job"`. Jobs without vault secrets dispatch normally, unaffected.
- **D-08:** No stale-secret caching. Last-fetched secret values are NOT stored in the DB as fallback. Security policy: secrets that may have been rotated must not be served from a stale cache. This means brief Vault outages cause dispatch failures for vault-dependent jobs — accepted trade-off per VAULT-06 requirements.
- **D-09:** `vault_service` exposes a `status()` → `Literal["healthy", "degraded", "disabled"]` method. `GET /system/health` (already exists) includes a `vault` field. `GET /admin/vault/status` returns detailed connection info (address, last_checked_at, error_detail if degraded).

### Lease Renewal
- **D-10:** Background task in the EE plugin renews leases at 30% of TTL remaining (e.g., renew at 30 min remaining for a 60 min TTL lease). Uses APScheduler (already in the stack). If renewal fails 3 consecutive times, vault_service transitions to DEGRADED and logs a structured warning — but the platform does not crash and non-vault jobs continue normally.

### Admin UI
- **D-11:** Vault configuration form lives in the existing `Admin.tsx` view (new "Vault" section/tab). Fields: address, role_id, secret_id (masked), mount_path, namespace, enabled toggle, test-connection button. The health status indicator (`healthy` / `degraded` / `disabled`) appears in the Vault section header.
- **D-12:** Job dispatch: `use_vault_secrets` boolean flag on `JobDispatchRequest` (default `false`, backward-compat). `vault_secrets: list[str]` field lists secret names to resolve. Both fields are optional — omitting them means no Vault interaction, existing behaviour unchanged.

### SecretsProvider Abstraction
- **D-13:** Phase 167 introduces a `SecretsProvider` protocol as the canonical interface for all secrets backends. HashiCorp Vault is implementation #1. The protocol is defined in `ee/` alongside the Vault implementation:
  ```python
  class SecretsProvider(Protocol):
      async def resolve(self, names: list[str]) -> dict[str, str]: ...
      async def status(self) -> Literal["healthy", "degraded", "disabled"]: ...
      async def renew(self) -> None: ...
  ```
- **D-14:** The dispatch layer (`job_service.py`) calls `secrets_provider.resolve(names)` — it is never coupled to Vault directly. This means adding a future backend requires zero changes to dispatch logic.
- **D-15:** The active provider is selected from `VaultConfig` (type field: `"vault"` for now). Future phases add `"azure_keyvault"`, `"aws_secretsmanager"`, `"gcp_secretmanager"` as additional options. The DB config row and admin UI field for provider type are added in Phase 167 even though only `"vault"` is implemented — this avoids a migration later.
- **D-16:** Additional configurable provider implementations (Azure KV, AWS SM, GCP SM, 1Password) are explicitly deferred to a later EE phase. Phase 167 ships the abstraction + Vault only.

### Upstream Compatibility
- **D-17:** `hvac >= 1.2.0` is the only new Python dependency. It speaks the standard Vault HTTP API. Both HashiCorp Vault (all editions) and OpenBao (the MPL-2.0 community fork) are compatible — no code changes needed to support either. Users choose their Vault server independently.

### Claude's Discretion
- Exact Alembic migration SQL for `vault_config` table
- APScheduler job naming and scheduler integration details
- Error message exact wording (clear intent is captured in D-07)
- `vault_config` table column defaults and nullable constraints

</decisions>

<specifics>
## Specific Ideas

- "I want this to be optional config, not a requirement" — users who don't configure Vault should never see errors or degraded-mode warnings. Dormant mode must be completely silent.
- Secret injection must not touch signed script content — `VAULT_SECRET_<NAME>` env vars are the only delivery mechanism. This preserves the Ed25519 signature over the script body.
- The EE gate is commercial strategy (not licensing obligation) — the decision is intentional and should be noted in code comments so future contributors don't "helpfully" move it to CE.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §VAULT-01–VAULT-06 — Six requirements covering config, startup fallback, dispatch injection, lease renewal, health status, and graceful degradation

### Architecture
- `.planning/research/ARCHITECTURE-v24.md` — Full v24 architecture including Vault integration points: `vault_service.py` pattern, `VaultSecret` audit table, `JobCreate.vault_secrets`, `WorkResponse` env var injection, `security.py` TLS verify
- `.planning/research/PITFALLS-v24.0.md` — Critical pitfalls: hard startup dependency (Pitfall 1), lease renewal isolation, secret caching anti-pattern, fallback order

### EE Plugin Architecture
- `.planning/phases/166-router-modularization/` — Phase 166 outputs: router modularization complete, 89 routes in domain routers. Vault EE routes inject via the same pattern.
- `puppeteer/agent_service/services/licence_service.py` — Existing EE licence check. Vault service must call this at init.
- `puppeteer/ee/` — Existing EE plugin directory (check for current structure before planning)

### Existing Security Patterns
- `puppeteer/agent_service/security.py` — Fernet encryption helpers (reuse for encrypting `secret_id` at rest)
- `puppeteer/agent_service/services/scheduler_service.py` — APScheduler patterns for background tasks (reuse for lease renewal)

### DB / Migration Pattern
- `puppeteer/agent_service/db.py` — SQLAlchemy ORM models, `init_db()`. New `VaultConfig` model goes here.
- `puppeteer/migration*.sql` — Migration file naming convention. New migration needed for `vault_config` table.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py` `encrypt_value()` / `decrypt_value()`: Fernet encrypt/decrypt — use for `VaultConfig.secret_id` at rest
- `scheduler_service.py` APScheduler instance: reuse for lease renewal background job (don't create a second scheduler)
- `licence_service.py` `require_ee()` guard: call at `vault_service` init and on all `/admin/vault/*` route handlers
- `main.py` lifespan: hook `vault_service.startup()` here (non-blocking — must not delay startup if Vault is offline)

### Established Patterns
- All EE feature code lives under `puppeteer/ee/` — vault_service must follow this
- Router registration: Phase 166 established domain routers in `puppeteer/agent_service/routers/`. EE vault router registers in the same `include_router()` block in `main.py`, conditional on EE licence
- Fernet at-rest encryption is the standard for all sensitive DB fields (used for secrets already)
- APScheduler jobs use named job IDs to prevent duplicate registration on restart

### Integration Points
- `job_service.py` `dispatch_job()`: inject `await vault_service.resolve_secrets(vault_secret_names)` before building `WorkResponse`, only if `use_vault_secrets=True`
- `WorkResponse` model: add `injected_env: dict[str, str]` field — node merges these into container env at execution
- `GET /system/health`: add `vault: vault_service.status()` to existing health response
- `Admin.tsx`: new Vault section — reuse existing admin panel tab/section pattern

</code_context>

<deferred>
## Deferred Ideas

- **Additional SecretsProvider backends** — deferred to a follow-on EE phase. Planned backends: Azure Key Vault (`azure-keyvault-secrets` + `azure-identity`, MIT), AWS Secrets Manager (`boto3`, Apache 2.0), GCP Secret Manager (`google-cloud-secret-manager`, Apache 2.0), 1Password Secrets Automation (`onepassword-sdk-python`, Apache 2.0). All ~1–1.5 days LOE each once the abstraction from D-13 is in place. Phase 167 adds the `provider_type` field to `VaultConfig` to avoid a migration later.
- **OpenBao as explicit first-class backend** — hvac works with OpenBao already; a named option in the provider type dropdown could be a follow-up if users request it
- **Per-job-definition Vault path overrides** — current design uses global mount_path; path-per-job would require schema changes beyond this phase
- **Vault token / Kubernetes auth methods** — AppRole is the only auth method in scope for Phase 167
- **Secret rotation webhooks** — proactive cache invalidation via Vault notifications; requires a webhook receiver, out of scope for this phase
- **Offsite Dashboard over WireGuard** (pre-existing idea, unrelated to Vault)

</deferred>

---

*Phase: 167-hashicorp-vault-integration-ee*
*Context gathered: 2026-04-18*

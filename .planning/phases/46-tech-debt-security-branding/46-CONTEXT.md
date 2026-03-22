# Phase 46: Tech Debt + Security + Branding - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Foundation cleanup before new operator-facing features land. Covers four deferred backend bugs (DEBT-01 through DEBT-04), two security hardening items (SEC-01, SEC-02), and one UI label rename pass (BRAND-01). No new user-facing capabilities — only fixes and hardening.

</domain>

<decisions>
## Implementation Decisions

### DEBT-01: NodeStats SQLite pruning
- Fix the subquery incompatibility that causes pruning to silently fail on SQLite deployments
- Claude's discretion on the exact SQL rewrite (e.g., subselect → JOIN or two-step delete)

### DEBT-02: Foundry build dir cleanup
- Remove `/tmp/puppet_build_*` directories after both successful AND failed builds in `foundry_service.py`
- Use try/finally to guarantee cleanup even on exception paths

### DEBT-03: Permission cache pre-warm
- The `_perm_cache` and `_invalidate_perm_cache` infrastructure already exists in `deps.py`
- Fix: pre-populate the cache at service startup (load all role permissions into `_perm_cache` before the first request arrives) so no request ever triggers a DB query
- Cache invalidation on permission change (via `_invalidate_perm_cache`) is already wired — no changes needed there

### DEBT-04: Node ID scan determinism
- Sort the readdir results in `_load_or_generate_node_id()` before selecting the first cert
- Simple one-line fix in `node.py`

### SEC-01: SECURITY_REJECTED audit entry
- Attribution: the reporting node's `node_id` is used as the actor (stored in the `username` field of the audit log)
- Detail JSON must contain: `script_hash` (SHA256 of the script content), `job_id`, `signature_id`, `node_id`
- Written in `job_service.py` at the `new_status = SECURITY_REJECTED` transition point in `process_job_report()` — all needed context is in scope there

### SEC-02: HMAC integrity on signature_payload
- **Storage**: New `signature_hmac` column on the `jobs` table (nullable, added via migration)
- **Key**: Uses `ENCRYPTION_KEY` (already used for Fernet secrets at rest — no new key to configure)
- **Coverage**: HMAC computed over `signature_payload + signature_id + job_id` (binds the payload to the specific job and signature record — prevents swapping a valid payload between jobs)
- **Stamp point**: HMAC computed and stored when a job is submitted / dispatched
- **Verification**: Checked at dispatch time before sending `WorkResponse` to a node; mismatch → reject + audit log entry
- **Migration**: On service startup, run a migration pass that computes and stores HMAC tags for all existing `jobs` rows that have a `signature_payload` but no `signature_hmac` — seamless for operators, no re-signing required

### BRAND-01: UI label rename
- **Full sweep** — replace legacy labels everywhere visible in the UI: tab labels, buttons, card headers, modal titles, empty states, toast messages, confirmation dialogs, tooltips, error messages
- Rename map:
  - "Blueprint" → "Image Recipe"
  - "PuppetTemplate" / "Template" (in Foundry context) → "Node Image"
  - "CapabilityMatrix entry" / capability matrix references → "Tool"
- Scope: `Templates.tsx`, all Foundry-related components, and the in-app Docs page (markdown content)
- **Nav "Foundry" label stays** — it's correct as a brand concept name; only the content labels inside the section are renamed
- Zero API/DB changes — frontend strings only

### Claude's Discretion
- Exact SQL rewrite approach for DEBT-01
- try/finally structure for DEBT-02 cleanup
- HMAC algorithm (HMAC-SHA256 is the obvious choice)
- How to structure the startup migration pass for SEC-02 (single DB query, update in batch)
- Whether to add `signature_hmac` column via `ALTER TABLE` migration file or via `create_all` on fresh installs (both)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deps.py:_perm_cache` / `_invalidate_perm_cache`: Cache infrastructure already exists — DEBT-03 just needs startup pre-warm
- `deps.py:audit()`: Existing audit helper — SEC-01 calls this with `action="security:rejected"` and detail dict
- `puppeteer/agent_service/security.py`: Fernet / `ENCRYPTION_KEY` already loaded here — SEC-02 derives the HMAC key from the same env var

### Established Patterns
- Audit entries: `audit(db, actor_user, "action:name", resource_id, detail={...})` — SEC-01 uses node_id as the actor identifier (as a string in the username field)
- DB migrations: pattern is a `migration_vNN.sql` file with `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` guards
- `create_all` handles fresh installs; migration file handles existing deployments

### Integration Points
- `job_service.py:process_job_report()` — SEC-01 audit entry goes here at `new_status = SECURITY_REJECTED`
- `job_service.py` dispatch path — SEC-02 HMAC verification happens before `WorkResponse` is constructed
- `main.py:lifespan()` or startup event — SEC-02 migration pass and DEBT-03 cache pre-warm both run at startup
- `foundry_service.py:build_template()` — DEBT-02 cleanup wraps the existing build logic in try/finally
- `puppets/environment_service/node.py:_load_or_generate_node_id()` — DEBT-04 sort fix

</code_context>

<specifics>
## Specific Ideas

- No specific implementation references or "I want it like X" moments — standard approaches apply throughout

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-tech-debt-security-branding*
*Context gathered: 2026-03-22*

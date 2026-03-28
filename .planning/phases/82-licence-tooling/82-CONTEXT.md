# Phase 82: Licence Tooling - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Internal operator CLI (`issue_licence.py`) to issue EE licences as Ed25519-signed JWTs, with a YAML audit trail committed to a private `axiom-laboratories/axiom-licenses` repo, a `list_licences.py` query script, and a CI guard preventing private key material from leaking into the public repo. Includes a full private key rotation. Customer-facing licence validation (`licence_service.py`) is untouched this phase.

</domain>

<decisions>
## Implementation Decisions

### YAML audit ledger
- Format: one YAML file per issuance — `licenses/issued/<customer-id>-<jti>.yml`
- Flat directory (not nested per customer) — customer-id prefix makes customer records easy to glob
- American spelling: `licenses/` not `licences/`
- Each YAML contains the full JWT payload fields: `jti`, `customer_id`, `issued_to`, `contact_email`, `tier`, `node_limit`, `features`, `grace_days`, `issued_at`, `expiry`, `issued_by`
- The YAML also embeds the full licence blob (JWT token) so it can be re-delivered without re-issuing
- Companion `list_licences.py` script reads all YAMLs and outputs a human-readable table (git log = immutable audit trail; script = query layer)

### Remote commit workflow
- Default: script calls the **GitHub API** to create/commit the YAML file in `axiom-laboratories/axiom-licenses`
- Requires `GITHUB_TOKEN` env var (no local clone needed)
- Commit message format: `feat(licenses): issue <customer-id> <tier> exp <expiry>`
  - e.g. `feat(licenses): issue acme-corp ee exp 2027-01-01`
- `--no-remote` flag: writes YAML to a local file **and** prints both the YAML record and the JWT token to stdout
- Air-gap compatibility is not a design priority — this is an internal dev team tool

### Key rotation
- Generate a fresh Ed25519 keypair as part of this phase
- New private key lives at `axiom-licenses/keys/licence.key` in the private repo
- New public key replaces `_LICENCE_PUBLIC_KEY_PEM` in `puppeteer/agent_service/services/licence_service.py`
- No backwards compatibility with the old key — no live customer licences exist
- Safe to rotate immediately

### Public repo cleanup
- Delete `tools/generate_licence.py` entirely — replaced by `issue_licence.py` in the private repo
- `tools/licence_signing.key` is not git-tracked (covered by `*.key` in `.gitignore`) — no git history to purge
- `issue_licence.py` lives only in the private `axiom-laboratories/axiom-licenses` repo

### `issue_licence.py` CLI interface
- Args: `--customer`, `--tier`, `--nodes`, `--expiry YYYY-MM-DD`, `--features f1,f2`
- Key source: `AXIOM_LICENCE_SIGNING_KEY` env var or `--key` path arg — no silent default path, fail with clear error if neither provided
- Outputs licence JWT to stdout; commits YAML record via GitHub API by default
- `--no-remote` flag for local-only operation

### CI guard
- Use `gitleaks/gitleaks-action@v2` (marketplace action) — free for this public repo
- Add as a step in existing `ci.yml` workflow
- Include `.gitleaks.toml` with allowlist entries for known dummy/test values:
  - `ci-dummy-key` (API_KEY in CI env)
  - `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=` (ENCRYPTION_KEY in CI env)
- Scans git history and working tree on every push/PR

### Claude's Discretion
- Exact `.gitleaks.toml` rule tuning and allowlist entries beyond the known dummies
- `list_licences.py` output formatting (table columns, sort order)
- `issue_licence.py` `--issued-by` default (git config user.name vs explicit arg only)
- Private repo directory structure beyond `licenses/issued/` and `keys/`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/generate_licence.py`: Full working EdDSA JWT issuer — `issue_licence.py` should be built from this. Same `cryptography` + `PyJWT` deps, same Ed25519 signing logic. CLI args map directly to the new interface.
- `puppeteer/agent_service/services/licence_service.py`: Contains `_LICENCE_PUBLIC_KEY_PEM` — this is the only file in the public repo that needs updating after key rotation.
- `puppeteer/tests/test_licence_service.py`: Generates ephemeral keypairs at runtime (`Ed25519PrivateKey.generate()`) — no changes needed to tests.

### Established Patterns
- Private key PEM format: PKCS8, no encryption (`serialization.NoEncryption()`) — keep consistent
- JWT signing: `jwt.encode(payload, private_key, algorithm="EdDSA")` via PyJWT (not python-jose)
- `.gitignore` already excludes `*.key` and `*.pem` — key rotation doesn't require gitignore changes

### Integration Points
- `licence_service.py` `_LICENCE_PUBLIC_KEY_PEM`: update with new public key after keypair generation
- `ci.yml`: add `gitleaks-action` step and `.gitleaks.toml` to repo root
- `axiom-laboratories/axiom-licenses` private repo: new repo (or existing) — needs `licenses/issued/`, `keys/`, `tools/` directories and a README

</code_context>

<specifics>
## Specific Ideas

- "This is an internal dev team tool — no need to design for air-gap compatibility, but --no-remote should exist as a simple fallback"
- "American spelling: `licenses` not `licences`"
- Key rotation is in scope and safe — no live customer licences to break
- The private repo is `axiom-laboratories/axiom-licenses` (confirmed from planning docs)

</specifics>

<deferred>
## Deferred Ideas

- GitHub Actions `workflow_dispatch` in the private repo for web-based licence issuance — future phase
- Dedicated service with customer DB, renewal tracking, and on-demand issuance API — long-term
- Licence renewal reminders / expiry notifications — future phase

</deferred>

---

*Phase: 82-licence-tooling*
*Context gathered: 2026-03-28*

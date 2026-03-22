# Phase 39: EE Test Keypair + Dev Install - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate a local Ed25519 test keypair, patch it into the `axiom-ee` source (`_LICENCE_PUBLIC_KEY_BYTES`), install as editable source (`pip install -e`), and produce valid/expired test licence strings stored in `mop_validation/secrets/ee/`. Enables all licence lifecycle API tests in later phases without a Cython rebuild.

</domain>

<decisions>
## Implementation Decisions

### Script structure
- **4 separate Python scripts** in `mop_validation/scripts/`:
  - `generate_ee_keypair.py` — generates the Ed25519 test keypair (one-time setup)
  - `patch_ee_source.py` — patches `plugin.py` + runs `pip install -e .` (repeatable)
  - `generate_ee_licence.py` — produces valid and expired licence strings
  - `verify_ee_install.py` — API-level assertions for EEDEV-03/04/05
- Python throughout (consistent with existing mop_validation scripts; can use `cryptography` lib directly)

### Key storage
- Keys stored in `mop_validation/secrets/ee/` subdirectory (keeps EE-specific secrets isolated from mTLS certs)
- Files: `ee_test_private.pem`, `ee_test_public.pem`

### Patching strategy
- `patch_ee_source.py` does **string replacement** of the `_LICENCE_PUBLIC_KEY_BYTES` line in `~/Development/axiom-ee/ee/plugin.py`
  - Reads test public key raw bytes, formats as Python bytes literal, replaces the placeholder line via regex
- **Also runs `pip install -e ~/Development/axiom-ee/`** in the same script (editable install always follows patching)
- `--restore` flag reverts `plugin.py` to `b'\x00' * 32` placeholder (useful for CE-degraded mode verification)

### Licence construction
- `generate_ee_licence.py` produces **two licences**:
  - **Valid licence**: `customer_id = "axiom-dev-test"`, `exp` = far-future Unix timestamp, all EE features enabled
  - **Expired licence**: same fields, `exp = 1704067200` (2024-01-01 00:00:00 UTC — fixed past timestamp, deterministic)
- Wire format: `base64url(json_payload).base64url(ed25519_sig)` (matches `_parse_licence()` in `plugin.py`)
- Both licence strings written to `mop_validation/secrets/ee/` as `.env` files:
  - `ee_valid_licence.env` — contains `AXIOM_LICENCE_KEY=<valid_key>`
  - `ee_expired_licence.env` — contains `AXIOM_LICENCE_KEY=<expired_key>`
- Ready to `source` or inject into `docker compose` environment

### Verification form
- `verify_ee_install.py` is a **standalone script** (does not extend `verify_ce_install.py`)
- EEDEV-03: hits `GET /api/licence` with valid key injected, asserts `customer_id`, `exp`, `features`
- EEDEV-04 and EEDEV-05: **manual restart flow** — script prints the `docker compose` commands needed to restart with the expired/absent key; operator runs them, then re-runs the verifier for that case
- Output: `[PASS]` / `[FAIL]` per requirement ID, matching Phase 38 `verify_ce_install.py` style

### Claude's Discretion
- Exact feature flag names in the test licence JSON (derive from EE plugin's feature-gating logic)
- Timeout/retry logic in `verify_ee_install.py` for API readiness after stack restart
- Error messaging when key files are missing (e.g., `generate_ee_keypair.py` not yet run)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `~/Development/axiom-ee/ee/plugin.py`: `_LICENCE_PUBLIC_KEY_BYTES: bytes = b'\x00' * 32` — the exact line `patch_ee_source.py` replaces
- `~/Development/toms_home/.agents/tools/admin_signer.py`: Ed25519 key generation pattern using `cryptography` lib (though RSA-based in practice — use as structural reference only)
- `mop_validation/scripts/verify_ce_install.py`: PASS/FAIL output format and structure to mirror in `verify_ee_install.py`

### Established Patterns
- Test tooling lives in `mop_validation/` not the main repo (CLAUDE.md policy)
- Scripts reference `~/Development/axiom-ee/` and `~/Development/master_of_puppets/` via hardcoded paths (Phase 38 pattern)
- Secrets go in `mop_validation/secrets/` (this phase adds `ee/` subdirectory)

### Integration Points
- `~/Development/axiom-ee/ee/plugin.py` → patched by `patch_ee_source.py`
- `mop_validation/secrets/ee/ee_valid_licence.env` → sourced when starting stack for EEDEV-03 validation
- `mop_validation/secrets/ee/ee_expired_licence.env` → sourced when restarting stack for EEDEV-04 validation
- `puppeteer/compose.server.yaml` → `AXIOM_LICENCE_KEY` env var injected at compose level for restart tests

</code_context>

<specifics>
## Specific Ideas

- `--restore` flag on `patch_ee_source.py` makes it easy to flip back to CE mode mid-validation — useful for confirming EEDEV-05 (no key = CE-degraded) without touching the compose file
- Fixed `exp = 1704067200` (2024-01-01) for the expired licence keeps tests deterministic regardless of when they're run
- `mop_validation/secrets/ee/` mirrors the subdirectory isolation pattern used by the mTLS CA certs

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 39-ee-test-keypair-dev-install*
*Context gathered: 2026-03-20*

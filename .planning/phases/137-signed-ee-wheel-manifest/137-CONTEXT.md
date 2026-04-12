# Phase 137: Signed EE Wheel Manifest - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Ed25519 signature + SHA256 wheel hash verification inside `_install_ee_wheel()` in `puppeteer/agent_service/ee/__init__.py`. Before pip installs the EE wheel, the verifier reads a signed manifest, checks the wheel's SHA256 matches, and verifies the Ed25519 signature. Any failure raises RuntimeError. Wheel production (Phase 140) and boot log hardening (Phase 138) are out of scope.

Requirement: EE-01

</domain>

<decisions>
## Implementation Decisions

### Manifest format
- Single JSON file at a fixed path: `/tmp/axiom_ee.manifest.json`
- Fixed name is sufficient — the container build process drops exactly one wheel into `/tmp/` at a time; version-based filename pairing is unnecessary
- JSON structure: `{"sha256": "<hex>", "signature": "<base64>"}`
- The `sha256` field holds the hex-encoded SHA256 digest of the wheel bytes
- The `signature` field holds the base64-encoded Ed25519 signature
- The Ed25519 **message** (what was signed) is the UTF-8 encoded SHA256 hex string — two clear steps: hash the wheel, sign the hash

### Verification logic (ordered steps)
1. Check `/tmp/axiom_ee.manifest.json` exists — RuntimeError if missing
2. Parse JSON — RuntimeError if malformed or missing `sha256`/`signature` fields
3. Compute SHA256 of the wheel file bytes
4. Assert computed SHA256 matches manifest `sha256` — RuntimeError if mismatch
5. Decode `signature` from base64
6. Verify Ed25519 sig over the hex SHA256 string (UTF-8 encoded) — RuntimeError if invalid
7. Proceed with pip install only after all checks pass

### Missing/bad manifest behavior
- No manifest found: RuntimeError (hard fail — absence means unsigned or tampered wheel)
- Malformed JSON: RuntimeError
- Missing required fields: RuntimeError
- SHA256 mismatch: RuntimeError
- Signature invalid: RuntimeError
- Consistent policy: if it can't be fully verified, it doesn't install

### Verification public key
- Hardcoded `_MANIFEST_PUBLIC_KEY_PEM` bytes literal in `ee/__init__.py` — same pattern as `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py`
- Operators cannot replace it without a code change (intentional — tamper resistance)
- **Separate dedicated keypair** from the licence signing key — principle of least privilege; compromise of one key doesn't affect the other
- Phase 140 (Wheel Signing Release Tool) will generate this keypair and populate the hardcoded public key; for Phase 137 a placeholder/test key is used until Phase 140 ships

### RuntimeError propagation
- `_install_ee_wheel()` raises RuntimeError on any verification failure (replaces current pattern of returning `False`)
- RuntimeError is caught in `activate_ee_live()` — EE doesn't load, server stays up in CE mode
- A tampered or unsigned wheel produces a degraded service, not a server crash
- Structured ERROR log entry on failure — include: which check failed, wheel path, manifest path, and failure detail

### Error visibility for operators
- `ee_activation_error` field added to the `/admin/licence` response — exposes the failure reason so operators can see it in the dashboard without digging logs
- Field is `null` when EE activation succeeded or was not attempted
- Field is a human-readable string when activation failed (e.g., `"Manifest not found: /tmp/axiom_ee.manifest.json"`)

### Claude's Discretion
- Which Ed25519 library to use for verification (`cryptography.hazmat.primitives.asymmetric.ed25519` already in use in `licence_service.py` — prefer consistency)
- Base64 encoding variant for signature field (standard b64 vs urlsafe — either is fine; note it for Phase 140 compatibility)
- Exact error message strings in RuntimeError
- Whether the placeholder public key used in Phase 137 tests is generated fresh or reused from test fixtures

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_install_ee_wheel()` in `ee/__init__.py:78-132`: the exact function to modify — currently does bare pip install with no verification; all verification logic inserts before the `subprocess.check_call` call
- `_LICENCE_PUBLIC_KEY_PEM` pattern in `licence_service.py:40-43`: exact template for `_MANIFEST_PUBLIC_KEY_PEM` hardcoded bytes literal
- `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey`: already imported and used in `licence_service.py` — use same library for consistency
- `activate_ee_live()` in `ee/__init__.py:135-175`: where RuntimeError from `_install_ee_wheel()` should be caught; currently checks return value (False), needs updating to catch RuntimeError

### Established Patterns
- Hardcoded PEM key pattern: `_PUB_KEY = serialization.load_pem_public_key(b"-----BEGIN PUBLIC KEY-----\n...")` — replicate for `_MANIFEST_PUB_KEY`
- `licence_service.py` uses `cryptography` lib for Ed25519 verification (not `nacl`) — stay consistent
- Boot log path is patched in tests via `unittest.mock.patch` — manifest path (`/tmp/axiom_ee.manifest.json`) should be patchable the same way (module-level constant `MANIFEST_PATH`)

### Integration Points
- `activate_ee_live()`: catch RuntimeError from `_install_ee_wheel()`, log it, set `ee_activation_error` on app state, return None
- `/admin/licence` endpoint in `main.py`: already returns licence state — add `ee_activation_error` field to response (read from `app.state`)
- `LicenceState` or a separate app state variable can carry the error string — check how `app.state.ee` is currently structured

</code_context>

<specifics>
## Specific Ideas

- The manifest verification is a gate before pip runs — all 6 checks happen before `subprocess.check_call` is ever called
- Module-level constant for manifest path (e.g. `MANIFEST_PATH = Path("/tmp/axiom_ee.manifest.json")`) so tests can patch it cleanly — same pattern as `BOOT_LOG_PATH` in `licence_service.py`
- Phase 140 compatibility note: the signing tool must produce the manifest using the same convention (sign the UTF-8 hex of the wheel SHA256, base64-encode the signature, write to `axiom_ee.manifest.json`)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 137-signed-ee-wheel-manifest*
*Context gathered: 2026-04-12*

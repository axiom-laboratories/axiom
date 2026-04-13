# Phase 140: Wheel Signing Release Tool - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Provide two release-time CLI scripts in `axiom-licenses/tools/`:
1. `gen_wheel_key.py` — generates the Ed25519 keypair used to sign wheel manifests
2. `sign_wheels.py` — signs EE wheels, producing per-wheel manifest files consumable by Phase 137's `_verify_wheel_manifest()`

These are operator-run tools, not server-side code. Container runtime behavior (Phase 137) and boot log hardening (Phase 138) are out of scope.

Requirement: EE-05

</domain>

<decisions>
## Implementation Decisions

### Multi-wheel handling
- One manifest file per .whl file in the input directory — not a combined manifest
- Manifest filename matches the wheel: `axiom_ee-2.0-py3-none-any.manifest.json` (versioned, exact pairing)
- `--deploy-name` optional flag: also writes a copy named `axiom_ee.manifest.json` alongside the versioned manifest (for operators deploying to /tmp — matches Phase 137's expected fixed name)
- If no .whl files found in the directory: error with clear message and non-zero exit (release pipelines must know if signing was skipped)

### Manifest format (locked from Phase 137)
- `{"sha256": "<hex>", "signature": "<base64>"}`
- Signed message: UTF-8 SHA256 hex string (hash the wheel bytes, sign the hex digest)
- Library: `cryptography.hazmat.primitives.asymmetric.ed25519` (consistent with existing codebase)

### Keypair generation — separate script
- `gen_wheel_key.py` is a separate script from `sign_wheels.py` (keygen is one-time; signing is repeated)
- Output: private key written to file (default `./wheel_signing.key`, overridable via `--out`), public key PEM printed to stdout for copy-paste into `ee/__init__.py` as `_MANIFEST_PUBLIC_KEY_PEM`
- Refuses to overwrite an existing key file unless `--force` is passed (prevents accidental key rotation)

### Output path
- Manifest files written to the same directory as the wheels (`--wheels-dir`)
- Prints a summary line per wheel after signing: `Signed: axiom_ee-2.0.manifest.json (sha256: abc123...)`
- Both tools live in `axiom-licenses/tools/` alongside `issue_licence.py`

### Key resolution (sign_wheels.py)
- Follow `issue_licence.py` pattern: `--key <path>` or `AXIOM_WHEEL_SIGNING_KEY` env var
- Exit with clear error if neither provided or file not found

### Verification mode
- `sign_wheels.py --verify --wheels-dir <dir> --key <public.pem>` — verify all wheel+manifest pairs in a directory
- `--key` accepts a public key PEM file (not hardcoded — decoupled from `ee/__init__.py`)
- Exit 0 if all wheels verify; exit 1 if any fail
- Print `OK: axiom_ee-2.0.manifest.json` per passing wheel, `FAIL: axiom_ee-2.0.manifest.json — <reason>` per failure

### Claude's Discretion
- Exact argparse help strings and usage examples
- Whether to support `--quiet` flag to suppress summary output
- Internal code structure (e.g., shared `_hash_wheel()` helper between sign and verify paths)
- Whether to support reading private key from env var as raw PEM vs file path only

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `axiom-licenses/tools/issue_licence.py`: exact template for key resolution pattern (`--key` arg or env var, `serialization.load_pem_private_key(path.read_bytes(), password=None)`), argparse structure, error messaging style
- `axiom-licenses/tools/issue_licence.py::resolve_key()`: copy-paste starting point for `sign_wheels.py`'s key resolver
- `puppeteer/agent_service/services/licence_service.py::_LICENCE_PUBLIC_KEY_PEM`: pattern for hardcoded PEM bytes literal — `gen_wheel_key.py` should print output in this exact format for copy-paste

### Established Patterns
- `cryptography` lib for Ed25519 (not `nacl`) — `licence_service.py` already imports it; stay consistent
- Key format: PEM, loaded via `serialization.load_pem_private_key()` / `load_pem_public_key()`
- Phase 137 manifest path constant: `MANIFEST_PATH = Path("/tmp/axiom_ee.manifest.json")` in `ee/__init__.py` — operator must copy manifest to this path at container launch; `--deploy-name` simplifies this by naming the output accordingly

### Integration Points
- `sign_wheels.py` output manifest must be compatible with Phase 137's `_verify_wheel_manifest()`:
  - `sha256` field: hex-encoded SHA256 of wheel bytes
  - `signature` field: base64-encoded Ed25519 signature over UTF-8 SHA256 hex string
- `gen_wheel_key.py` public key PEM output → copy into `puppeteer/agent_service/ee/__init__.py` as `_MANIFEST_PUBLIC_KEY_PEM` bytes literal

</code_context>

<specifics>
## Specific Ideas

- The `--deploy-name` flag writes a second copy at `axiom_ee.manifest.json` in the same directory — this is the name Phase 137 expects at `/tmp/`. Operator workflow: `sign_wheels.py --wheels-dir dist/ --key wheel_signing.key --deploy-name`, then COPY the matching pair to /tmp/ in the container.
- `gen_wheel_key.py` stdout should print the public key PEM already formatted as a Python bytes literal (e.g. `b"""-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"""`) so the operator can paste directly into `ee/__init__.py` without reformatting.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 140-wheel-signing-release-tool*
*Context gathered: 2026-04-13*

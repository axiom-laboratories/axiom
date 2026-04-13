# Phase 140: Wheel Signing Release Tool - Research

**Researched:** 2026-04-13
**Domain:** CLI tooling for EE wheel signing and validation
**Confidence:** HIGH

## Summary

Phase 140 delivers two complementary CLI scripts in `axiom-licenses/tools/` that enable secure EE wheel signing and verification at release time. These are operator-run tools (not server-side code) that integrate with Phase 137's manifest verification gate: `gen_wheel_key.py` generates the Ed25519 keypair once, and `sign_wheels.py` signs wheels repeatedly at release, producing per-wheel manifest files.

The research confirms that `cryptography>=41.0.0` (already a dependency in axiom-licenses) provides all required Ed25519 and PEM serialization capabilities. The pattern and structure follow the established `issue_licence.py` template in the same tools directory, ensuring consistency with existing operator workflows.

**Primary recommendation:** Use `cryptography.hazmat.primitives.asymmetric.ed25519` for all signing/verification operations (consistent with `licence_service.py` in the backend). Structure both scripts to follow argparse patterns in `issue_licence.py`, with explicit key resolution (`--key` arg or `AXIOM_WHEEL_SIGNING_KEY` env var) and clear error messaging.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Multi-wheel handling** — One manifest file per .whl file in the input directory (not combined); manifest filename matches the wheel exactly (e.g., `axiom_ee-2.0-py3-none-any.manifest.json`); optional `--deploy-name` flag writes a copy named `axiom_ee.manifest.json` (fixed name expected by Phase 137 at `/tmp/`); error with non-zero exit if no wheels found.

2. **Manifest format** — JSON structure: `{"sha256": "<hex>", "signature": "<base64>"}`. Signed message: UTF-8 SHA256 hex string (hash the wheel bytes, sign the hex digest). Library: `cryptography.hazmat.primitives.asymmetric.ed25519` (consistent with existing codebase).

3. **Keypair generation (gen_wheel_key.py)** — Separate script from signing; one-time operation. Output: private key to file (default `./wheel_signing.key`, overridable via `--out`), public key PEM printed to stdout for copy-paste into `ee/__init__.py` as `_MANIFEST_PUBLIC_KEY_PEM`. Refuses to overwrite existing key file unless `--force` is passed.

4. **Output path** — Manifest files written to the same directory as the wheels (`--wheels-dir`). Prints summary line per wheel after signing: `Signed: axiom_ee-2.0.manifest.json (sha256: abc123...)`. Both tools live in `axiom-licenses/tools/` alongside `issue_licence.py`.

5. **Key resolution (sign_wheels.py)** — Follow `issue_licence.py` pattern: `--key <path>` or `AXIOM_WHEEL_SIGNING_KEY` env var. Exit with clear error if neither provided or file not found.

6. **Verification mode** — `sign_wheels.py --verify --wheels-dir <dir> --key <public.pem>` verifies all wheel+manifest pairs. `--key` accepts public key PEM file (not hardcoded). Exit 0 if all verify; exit 1 if any fail. Print `OK: axiom_ee-2.0.manifest.json` per passing wheel, `FAIL: axiom_ee-2.0.manifest.json — <reason>` per failure.

### Claude's Discretion

- Exact argparse help strings and usage examples
- Whether to support `--quiet` flag to suppress summary output
- Internal code structure (e.g., shared `_hash_wheel()` helper between sign and verify paths)
- Whether to support reading private key from env var as raw PEM vs file path only

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EE-05 | `sign_wheels.py` CLI generates signed wheel manifests at release time (Ed25519 key + SHA256 per wheel) | Crypto library capabilities documented; integration patterns with Phase 137 verified; manifest format and signing algorithm finalized |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | ≥41.0.0 | Ed25519 keypair generation, signing, verification; PEM serialization | Already required in axiom-licenses/requirements.txt; used in backend licence_service.py and Phase 137 wheel verification; battle-tested standard |
| Python stdlib: `argparse` | 3.10+ | CLI argument parsing | Universal Python CLI pattern; used in `issue_licence.py` |
| Python stdlib: `hashlib` | 3.10+ | SHA256 wheel hashing | Stdlib; used in Phase 137 manifest verification |
| Python stdlib: `json` | 3.10+ | Manifest JSON format | Stdlib; consistent with Phase 137 verifier |
| Python stdlib: `pathlib` | 3.10+ | Path handling (cross-platform) | Stdlib; used in `issue_licence.py` |
| Python stdlib: `base64` | 3.10+ | Signature encoding/decoding | Stdlib; used in Phase 137 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sys`, `os` | stdlib | Exit codes, environment variables, argument handling | `gen_wheel_key.py` for key generation workflow; `sign_wheels.py` for key resolution |
| `glob` | stdlib | Wheel file discovery in directories | `sign_wheels.py` to find all `.whl` files in input directory |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cryptography` | `PyNaCl` | PyNaCl is smaller but `cryptography` is more widely used and already in the stack. Stay consistent with backend. |
| Argparse | Click or Typer | Argparse matches existing `issue_licence.py`. No reason to diverge from established pattern. |
| `pathlib` | `os.path` | `pathlib` is more modern and cross-platform; matches `issue_licence.py`. |

**Installation:**
```bash
# Dependencies already in axiom-licenses/requirements.txt
# No additional packages needed (cryptography, pyyaml, requests already present)
```

---

## Architecture Patterns

### Recommended File Layout
```
axiom-licenses/
├── tools/
│   ├── issue_licence.py         # Existing licence issuance tool (template)
│   ├── gen_wheel_key.py         # NEW: Keypair generation (one-time)
│   ├── sign_wheels.py           # NEW: Wheel signing + verification (release tool)
│   └── list_licences.py         # Existing (unchanged)
├── keys/
│   └── wheel_signing.key        # Generated by gen_wheel_key.py (git-ignored)
└── requirements.txt             # Already has cryptography>=41.0.0
```

### Pattern 1: Key Generation Script (gen_wheel_key.py)
**What:** Standalone script that generates a fresh Ed25519 keypair and outputs it for operator copy-paste into code.

**When to use:** Once per release cycle (or when rotating keys). Operator runs this at key generation time, not during normal releases.

**Structure:**
1. Parse CLI args: `--out` (default: `./wheel_signing.key`), `--force` (allow overwrite)
2. Check if output file exists; error if it does (unless `--force`)
3. Generate fresh keypair: `Ed25519PrivateKey.generate()`
4. Serialize private key to PEM; write to file
5. Serialize public key to PEM; **print to stdout** in Python bytes-literal format (for copy-paste into `ee/__init__.py`)
6. Print summary to stderr with fingerprint or checksum for audit trail
7. Exit 0 on success

**Example invocation:**
```bash
python tools/gen_wheel_key.py --out keys/wheel_signing.key

# stdout (copy-paste into ee/__init__.py):
b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAu+al02k0lyKWoDLmM8gwo2YYXvkUyO1JU2gysKETKus=
-----END PUBLIC KEY-----"""

# stderr (operator confirmation):
[keygen] Private key written to: keys/wheel_signing.key
[keygen] Public key (copy below into ee/__init__.py):
... (bytes literal printed again for verification)
```

**Example (sign_wheels.py format):**
```python
def generate_keypair(out_path: Path, force: bool = False) -> tuple[bytes, bytes]:
    """Generate Ed25519 keypair, write private key to file, return (private_pem, public_pem)."""
    if out_path.exists() and not force:
        sys.exit(f"Error: {out_path} already exists. Use --force to overwrite.")
    
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    out_path.write_bytes(private_pem)
    return private_pem, public_pem
```

### Pattern 2: Wheel Signing Script (sign_wheels.py)
**What:** Repeated-use tool that signs all wheels in a directory, producing one manifest per wheel.

**When to use:** At every release time to sign EE wheels before shipping.

**Structure:**
1. Parse CLI args: `--wheels-dir` (required), `--key` (or env `AXIOM_WHEEL_SIGNING_KEY`), `--deploy-name` (optional), `--verify` (optional, verification mode), `--quiet` (optional)
2. If `--verify`: Load public key from `--key`, verify all wheel+manifest pairs, print results, exit with 0/1
3. If signing: Resolve private key (arg or env var), find all `.whl` files in `--wheels-dir`
4. For each wheel:
   - Compute SHA256 of wheel bytes (64KB chunks like Phase 137)
   - Sign the UTF-8 hex SHA256 string with Ed25519 private key
   - Build manifest JSON: `{"sha256": "<hex>", "signature": "<base64>"}`
   - Write manifest to same dir as wheel, matching wheel filename with `.manifest.json` suffix
   - If `--deploy-name`: also write copy to `axiom_ee.manifest.json` (fixed name)
5. Print summary: `Signed: axiom_ee-2.0.manifest.json (sha256: abc123...)`
6. Error with non-zero exit if no wheels found

**Example invocations:**
```bash
# Sign all wheels in dist/, using key file
python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key

# Sign wheels, use env var for key
export AXIOM_WHEEL_SIGNING_KEY=keys/wheel_signing.key
python tools/sign_wheels.py --wheels-dir dist/

# Sign + create deploy name copy for /tmp/ container copy
python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key --deploy-name

# Verify all manifests in a directory (using public key PEM)
python tools/sign_wheels.py --verify --wheels-dir dist/ --key keys/wheel_signing.public.pem

# Quiet mode (no per-wheel summaries)
python tools/sign_wheels.py --wheels-dir dist/ --key keys/wheel_signing.key --quiet
```

**Example (manifest format, from Phase 137):**
```json
{
  "sha256": "f2ca1c6251c6abc53a62b8e4b15cee18db981b2f16c9b4c4f7e6a8c3b9f4e5d6",
  "signature": "dGhpcyBpcyBhIGJhc2U2NCBlbmNvZGVkIEVkMjU1MTkgc2lnbmF0dXJlIC8gNjQgYnl0ZXMgYmluYXJ5IGRhdGE="
}
```

### Pattern 3: Key Resolution (Shared Helper)
**What:** Extract `issue_licence.py`'s `resolve_key()` function and adapt it for both scripts.

**When to use:** In both `gen_wheel_key.py` (to write private key) and `sign_wheels.py` (to load private or public key).

**Source template (from issue_licence.py:48-63):**
```python
def resolve_key(args, key_env_var: str = "AXIOM_WHEEL_SIGNING_KEY"):
    """Resolve signing key from --key arg or env var.
    
    Returns a loaded Ed25519PrivateKey instance for signing,
    or Ed25519PublicKey instance for verification.
    Exits with clear error message if neither provided or file missing.
    """
    key_source = args.key or os.getenv(key_env_var)
    if not key_source:
        sys.exit(
            f"Error: no signing key provided.\n"
            f"Set {key_env_var} env var or pass --key <path>."
        )
    path = Path(key_source)
    if not path.exists():
        sys.exit(f"Error: key file not found: {path}")
    
    # Try private key first, fall back to public key
    try:
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    except Exception:
        try:
            return serialization.load_pem_public_key(path.read_bytes())
        except Exception as e:
            sys.exit(f"Error: failed to load key from {path}: {e}")
```

### Anti-Patterns to Avoid
- **Hardcoding keys in scripts:** Keys must be file-based or env-var-passed, never embedded strings (security).
- **Single large file read for wheel hashing:** Use 64KB chunks (memory efficient, matches Phase 137 pattern).
- **Stdout/stderr confusion:** Print progress to stderr, results to stdout (like `issue_licence.py` does).
- **Not validating wheels exist before signing:** Check for at least one `.whl` before processing.
- **Overwriting keys silently:** Require explicit `--force` flag (prevents accidental key rotation).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signing/verification | Custom cryptography code | `cryptography.hazmat.primitives.asymmetric.ed25519` | Cryptography is battle-tested; custom code has timing-attack and constant-time risks |
| Wheel file hashing | Read entire file into memory | SHA256 in 64KB chunks (matching Phase 137) | Wheels can be large (100s MB); chunked hashing is memory-safe |
| PEM key serialization | String formatting | `cryptography.hazmat.primitives.serialization` | Format must be exact for Python bytes-literal output; library handles all variants |
| Base64 encoding/decoding | Custom or alternative codec | Python stdlib `base64` module | Standard codecs are constant-time; custom code risks timing attacks |
| Command-line argument parsing | Custom getopt loops | `argparse` (matches `issue_licence.py`) | Argparse is standard, well-tested, and expected by operators familiar with `issue_licence.py` |
| Key file I/O | Custom permission checks | `pathlib.Path.read_bytes()` / `write_bytes()` | Let OS handle file permissions; operator responsibility to `chmod 600` the key file |

**Key insight:** Cryptography is not an area to optimize or simplify. Use the library, use tested patterns from the codebase (`licence_service.py`, Phase 137), and let the operator manage key security via file permissions and environment variables.

---

## Common Pitfalls

### Pitfall 1: Key Format Mismatch
**What goes wrong:** Operator generates a key in one format (e.g., unencrypted PKCS8 PEM), but `sign_wheels.py` tries to load it as a different format (e.g., encrypted PEM), causing silent failures or cryptic errors.

**Why it happens:** PEM loading doesn't fail gracefully on format mismatches; the library expects exact format. `cryptography.load_pem_private_key()` with `password=None` rejects encrypted keys.

**How to avoid:** Always generate keys with `NoEncryption()` in `gen_wheel_key.py`. In `sign_wheels.py`, provide clear error message on load failure: `"Failed to load {key_path}: ensure it's an unencrypted Ed25519 PEM private key (generated by gen_wheel_key.py)"`.

**Warning signs:** "error: no key found" or "error: expected X bytes, got Y" during key load.

### Pitfall 2: Manifest Filename Not Matching Wheel
**What goes wrong:** Operator accidentally names a manifest `axiom_ee-2.0.manifest.json` but the wheel is `axiom_ee-2.1.whl`. Phase 137 at runtime looks for `/tmp/axiom_ee.manifest.json` (fixed name) and fails to find it.

**Why it happens:** Phase 137 only checks the fixed deploy name, not versioned manifests. Operator confusion about when to use `--deploy-name` flag.

**How to avoid:** Always write both: versioned manifest (for audit/traceability) AND deploy-name manifest (for container operator). Make `--deploy-name` default behavior or print clear instructions: `"To use in container: copy axiom_ee.manifest.json to /tmp/ alongside the wheel at container launch time"`.

**Warning signs:** Container fails to start with "Manifest not found" error; operator didn't see the deploy-name output.

### Pitfall 3: Operator Forgetting to Update `ee/__init__.py`
**What goes wrong:** Operator generates a new key, signs wheels with the new key, but forgets to copy the new public key bytes into `_MANIFEST_PUBLIC_KEY_PEM` in the backend. Container launches but wheel verification fails because the hardcoded public key doesn't match the signature.

**Why it happens:** `gen_wheel_key.py` prints the public key to stdout, but operator doesn't realize it MUST be copied into the backend code.

**How to avoid:** Make output crystal clear: `"*** IMPORTANT: Copy the below public key into puppeteer/agent_service/ee/__init__.py as _MANIFEST_PUBLIC_KEY_PEM ***"`. Optionally provide a helper flag to patch the file automatically (risky, but operator-friendly).

**Warning signs:** Phase 137 verification fails with "Wheel signature verification failed" after a key rotation.

### Pitfall 4: Silent Failures When No Wheels Found
**What goes wrong:** Release pipeline runs `sign_wheels.py --wheels-dir dist/`, but dist/ is empty. Script exits silently (or with generic message), pipeline continues, and unsigned wheels are shipped.

**Why it happens:** Error checking is lenient; "no wheels" is treated as success case.

**How to avoid:** Make it explicit in the code: `if not wheels: sys.exit(f"Error: no .whl files found in {wheels_dir}")`. Exit code 1. Print to stderr. This forces the release pipeline to halt.

**Warning signs:** Release artifacts contain unsigned wheels; operator didn't notice the script ran quickly with no output.

### Pitfall 5: Base64 Encoding Variant (Standard vs URLSafe)
**What goes wrong:** `sign_wheels.py` uses standard base64 encoding (with `+` and `/`), but Phase 137 verifier expects URL-safe base64 (with `-` and `_`). Signature fails to decode or verify.

**Why it happens:** Two base64 variants exist; easy to mix them up. Phase 137 uses stdlib `base64.b64decode()` which expects standard base64.

**How to avoid:** Use stdlib `base64.b64encode()` (standard base64) in `sign_wheels.py`. Phase 137 uses `base64.b64decode()` (standard). Verify this in integration testing. Document it in code comments.

**Warning signs:** Phase 137 logs "Failed to decode signature as base64" or signature bytes don't match expected length.

### Pitfall 6: Private Key File Permissions
**What goes wrong:** `gen_wheel_key.py` writes private key to disk with default permissions (e.g., 644). Operator doesn't notice, and the unencrypted private key is world-readable in the repository.

**Why it happens:** `pathlib.Path.write_bytes()` respects umask; on a permissive system, the file may be overly readable.

**How to avoid:** After writing the private key, explicitly set permissions: `out_path.chmod(0o600)`. Print confirmation to stderr: `"[keygen] Private key written to {out_path} with mode 0600"`. In `.gitignore`, exclude `keys/` directory or `*.key` files.

**Warning signs:** `ls -la keys/wheel_signing.key` shows `-rw-r--r--` instead of `-rw-------`.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Example 1: Ed25519 Keypair Generation
```python
# Source: cryptography library documentation + licence_service.py pattern
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate keypair
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Serialize private key to PEM (unencrypted)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key to PEM
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Write private key to file
Path("wheel_signing.key").write_bytes(private_pem)

# Print public key as Python bytes literal (for copy-paste)
print(f"b\"\"\"{public_pem.decode()}\"\"\"")
```

### Example 2: Wheel SHA256 Hashing (matching Phase 137)
```python
# Source: Phase 137 _verify_wheel_manifest() implementation
import hashlib
from pathlib import Path

def hash_wheel(wheel_path: str) -> str:
    """Compute SHA256 of wheel file in 64KB chunks."""
    sha256_hash = hashlib.sha256()
    with open(wheel_path, 'rb') as f:
        while chunk := f.read(65536):  # 64KB chunks
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

wheel_sha = hash_wheel("/tmp/axiom_ee-2.0-py3-none-any.whl")
# wheel_sha = "f2ca1c6251c6abc53a62b8e4b15cee18db981b2f16c9b4c4f7e6a8c3b9f4e5d6"
```

### Example 3: Ed25519 Signing (sign the SHA256 hex, not digest bytes)
```python
# Source: Phase 137 pattern + cryptography docs
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519

def sign_wheel_manifest(wheel_sha256_hex: str, private_key: ed25519.Ed25519PrivateKey) -> str:
    """Sign the UTF-8 encoded SHA256 hex string with Ed25519.
    
    Returns base64-encoded signature (compatible with Phase 137 verifier).
    """
    # Message: UTF-8 encoded hex SHA256 string (NOT raw digest bytes)
    message = wheel_sha256_hex.encode('utf-8')
    
    # Sign with Ed25519 private key
    signature_bytes = private_key.sign(message)
    
    # Encode signature as base64 (standard, not urlsafe)
    signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
    
    return signature_b64

# Usage:
private_key = serialization.load_pem_private_key(
    Path("wheel_signing.key").read_bytes(),
    password=None
)
sha256_hex = "f2ca1c6251c6abc53a62b8e4b15cee18db981b2f16c9b4c4f7e6a8c3b9f4e5d6"
sig = sign_wheel_manifest(sha256_hex, private_key)
# sig = "dGhpcyBpcyBhIGJhc2U2NCBlbmNvZGVkIEVkMjU1MTkgc2lnbmF0dXJl..."
```

### Example 4: Manifest JSON Format (locked from Phase 137)
```python
# Source: Phase 137 _verify_wheel_manifest() requirements
import json

manifest = {
    "sha256": "f2ca1c6251c6abc53a62b8e4b15cee18db981b2f16c9b4c4f7e6a8c3b9f4e5d6",
    "signature": "dGhpcyBpcyBhIGJhc2U2NCBlbmNvZGVkIEVkMjU1MTkgc2lnbmF0dXJl..."
}

# Write to axiom_ee-2.0.manifest.json
Path("axiom_ee-2.0.manifest.json").write_text(json.dumps(manifest, indent=2))
```

### Example 5: Wheel File Discovery and Processing
```python
# Source: Phase 137 pattern
import glob
from pathlib import Path

wheels_dir = Path("dist")
wheels = sorted(wheels_dir.glob("*.whl"))

if not wheels:
    sys.exit(f"Error: no .whl files found in {wheels_dir}")

for wheel_path in wheels:
    # Process each wheel
    sha256 = hash_wheel(str(wheel_path))
    sig = sign_wheel_manifest(sha256, private_key)
    
    # Manifest filename matches wheel (with .manifest.json suffix)
    manifest_path = wheel_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps({
        "sha256": sha256,
        "signature": sig
    }, indent=2))
    
    print(f"Signed: {manifest_path.name} (sha256: {sha256[:16]}...)", file=sys.stderr)
    
    # If --deploy-name flag: also write axiom_ee.manifest.json
    if deploy_name:
        deploy_path = wheels_dir / "axiom_ee.manifest.json"
        deploy_path.write_text(manifest_path.read_text())
```

### Example 6: argparse Structure (matching issue_licence.py)
```python
# Source: issue_licence.py:147-163 template
import argparse

def _build_parser():
    p = argparse.ArgumentParser(
        description="Sign EE wheel manifests with Ed25519 key."
    )
    p.add_argument(
        "--wheels-dir",
        required=True,
        dest="wheels_dir",
        help="Directory containing .whl files to sign"
    )
    p.add_argument(
        "--key",
        default=None,
        help="Path to private key PEM file (or set AXIOM_WHEEL_SIGNING_KEY)"
    )
    p.add_argument(
        "--deploy-name",
        action="store_true",
        dest="deploy_name",
        help="Also write axiom_ee.manifest.json (fixed name for /tmp/ deployment)"
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Verify all wheel+manifest pairs (requires --key to be public PEM)"
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-wheel summary output"
    )
    return p

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    # ... main logic
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unsigned wheels | Ed25519 signed manifests (Phase 137) | 2026-04-12 | Wheels now require cryptographic proof of authenticity before installation; prevents tampering |
| Manual SHA256 hashing in documentation | Automated per-wheel manifest generation (Phase 140) | 2026-04-13 | Operators can't forget to hash or sign; tools enforce correctness |
| Single shared signing key (licence + wheels) | Separate keypairs per domain (Phase 137 + 140) | 2026-04-13 | Principle of least privilege; compromise of one key doesn't affect the other |

**Deprecated/outdated:**
- Manual manifest creation: Don't ask operators to compute SHA256 and sign manually (error-prone, security risk).
- Shared licence/wheel keypairs: Each domain (licence, wheel) has its own key (cleaner separation of concerns).

---

## Open Questions

1. **Supporting `--quiet` flag (Claude's Discretion)**
   - What we know: `--quiet` would suppress per-wheel summary lines
   - What's unclear: Is operator feedback important enough to always print, or should release pipelines be able to silence it?
   - Recommendation: Implement `--quiet` as optional (useful for CI/CD pipelines). Default: always print summaries (operator assurance).

2. **Raw PEM env var support vs file path only (Claude's Discretion)**
   - What we know: `--key` arg and `AXIOM_WHEEL_SIGNING_KEY` env var can pass file paths
   - What's unclear: Should we support passing the PEM bytes directly in the env var (e.g., `AXIOM_WHEEL_SIGNING_KEY="-----BEGIN PRIVATE KEY-----..."`)?
   - Recommendation: File path only (simpler, matches `issue_licence.py` pattern). PEM bytes in env vars create debugging complexity and risk accidental logging.

3. **Automatic public key patching into ee/__init__.py (Claude's Discretion)**
   - What we know: `gen_wheel_key.py` prints public key to stdout for manual copy-paste
   - What's unclear: Should we provide an `--patch-backend` flag to automatically update `ee/__init__.py`?
   - Recommendation: Not in Phase 140 scope. Operator workflow of copy-paste from stdout is explicit and auditable. Automatic patching risks mistakes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `puppeteer/pytest.ini` (existing) or `axiom-licenses/pytest.ini` (new) |
| Quick run command | `pytest axiom-licenses/tests/ -v --tb=short` |
| Full suite command | `pytest axiom-licenses/tests/ puppeteer/tests/test_ee_manifest.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-05 | `gen_wheel_key.py` generates unencrypted Ed25519 keypair and writes to file | unit | `pytest axiom-licenses/tests/test_gen_wheel_key.py::test_generate_keypair -v` | ❌ Wave 0 |
| EE-05 | `gen_wheel_key.py` refuses to overwrite existing key unless `--force` | unit | `pytest axiom-licenses/tests/test_gen_wheel_key.py::test_no_overwrite_without_force -v` | ❌ Wave 0 |
| EE-05 | `gen_wheel_key.py` prints public key as Python bytes literal to stdout | unit | `pytest axiom-licenses/tests/test_gen_wheel_key.py::test_public_key_bytes_literal -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py` finds all `.whl` files in input directory | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_wheel_discovery -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py` computes SHA256 of wheel bytes in 64KB chunks | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_wheel_hash_chunked -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py` signs SHA256 hex (UTF-8) with Ed25519, produces base64 signature | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_signature_format -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py` creates manifest JSON files matching wheel filenames | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_manifest_naming -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py --deploy-name` also writes axiom_ee.manifest.json | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_deploy_name_flag -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py` exits 1 if no wheels found | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_no_wheels_error -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py --verify` loads public key and verifies all manifests | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_verify_mode -v` | ❌ Wave 0 |
| EE-05 | `sign_wheels.py --verify` exits 0 if all manifests verify, 1 if any fail | unit | `pytest axiom-licenses/tests/test_sign_wheels.py::test_verify_exit_codes -v` | ❌ Wave 0 |
| EE-05 | Signed manifests work with Phase 137 `_verify_wheel_manifest()` | integration | `cd puppeteer && pytest tests/test_ee_manifest.py::test_phase137_integration -v` | ✅ (exists from Phase 137) |
| EE-05 | Key resolution (`--key` or env var) matches `issue_licence.py` pattern | unit | `pytest axiom-licenses/tests/test_key_resolution.py -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest axiom-licenses/tests/ -v` (all unit tests for tools)
- **Per wave merge:** `pytest axiom-licenses/tests/ puppeteer/tests/test_ee_manifest.py -v` (tools + Phase 137 integration)
- **Phase gate:** All above plus manual smoke test: `gen_wheel_key.py` then `sign_wheels.py` on test wheels, verify with Phase 137 verifier

### Wave 0 Gaps
- [ ] `axiom-licenses/tests/test_gen_wheel_key.py` — keypair generation, file I/O, no-overwrite, public key formatting
- [ ] `axiom-licenses/tests/test_sign_wheels.py` — wheel discovery, hashing, signing, manifest naming, deploy-name flag, error handling, verify mode
- [ ] `axiom-licenses/tests/test_key_resolution.py` — argument parsing, env var fallback, error messages
- [ ] `axiom-licenses/pytest.ini` or config in `pyproject.toml` — test runner config (if not already present)
- [ ] Update `axiom-licenses/.gitignore` to exclude `keys/`, `*.key`, and `*.manifest.json` files

---

## Sources

### Primary (HIGH confidence)
- **cryptography library** (v41.0.0+) — Ed25519 key generation, signing, verification; PEM serialization (official docs: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- **Phase 137 implementation** (`puppeteer/agent_service/ee/__init__.py`) — Exact manifest verification logic, manifest format validation, 6-step verification process, UTF-8 SHA256 hex signing convention
- **axiom-licenses/tools/issue_licence.py** — Key resolution pattern, argparse structure, error messaging style
- **Python stdlib** — argparse, hashlib, json, base64, pathlib (all documented at python.org)

### Secondary (MEDIUM confidence)
- **Phase 137 CONTEXT.md and PLAN.md** — Locked manifest format decisions, integration requirements, error propagation pattern
- **Phase 140 CONTEXT.md** — Operator workflow, flag specifications, multi-wheel handling decisions

### Tertiary (LOW confidence)
- None — all findings verified through Context7 (existing codebase) and official documentation

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — `cryptography>=41.0.0` already in requirements.txt; Ed25519 APIs well-documented and in use in backend
- **Architecture:** HIGH — Phase 137 implementation provides exact manifest format and verification logic; argparse pattern from `issue_licence.py` is established
- **Pitfalls:** MEDIUM-HIGH — Common cryptography pitfalls documented; specific risks (key format, filename matching, permission handling) derived from CONTEXT.md and existing code patterns
- **Code examples:** HIGH — All examples adapted directly from Phase 137 implementation or cryptography official docs

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (cryptography library is stable; estimated 30-day validity unless cryptography upstream releases breaking changes)

**Key decision points locked from CONTEXT.md:**
- Manifest format: `{"sha256": "<hex>", "signature": "<base64>"}`
- Signing message: UTF-8 hex SHA256 string (not raw bytes)
- Keypair generation: separate `gen_wheel_key.py` script
- Key resolution: `--key` arg or `AXIOM_WHEEL_SIGNING_KEY` env var
- Output: per-wheel manifests + optional deploy-name copy
- Library: `cryptography.hazmat.primitives.asymmetric.ed25519`

**Claude's discretion areas (ready to be decided during planning):**
- `--quiet` flag support (recommended: yes)
- Raw PEM env var support (recommended: no, file path only)
- Automatic `ee/__init__.py` patching (recommended: no, manual copy-paste)
- Exact help text and example commands
- Shared `_hash_wheel()` helper implementation details

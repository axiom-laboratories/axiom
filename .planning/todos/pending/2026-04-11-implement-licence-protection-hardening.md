---
created: 2026-04-11T12:00:00.000Z
title: Implement licence protection hardening (wheel manifest + HMAC boot log + entry point whitelist)
area: api
files:
  - puppeteer/agent_service/ee/__init__.py
  - puppeteer/agent_service/services/licence_service.py
  - axiom-licenses/tools/sign_wheels.py
---

## Problem

The EE licence system uses cryptographically sound Ed25519 JWTs but has three gaps that make casual
piracy or trivial bypass feasible:

1. **No wheel integrity check** — the EE wheel (`/tmp/axiom_ee-*.whl`) is installed without any
   signature or hash verification. A pirate can extract the wheel and run it independently of any
   licence, or an attacker with `/tmp/` write access could substitute a malicious wheel.

2. **Weak boot log rollback protection** — `secrets/boot.log` uses plain SHA256 for its hash chain.
   Deleting or resetting the file bypasses all clock-rollback detection. An attacker with file write
   access can trivially extend licence expiry.

3. **Untrusted entry point loading** — `activate_ee_live()` loads any `axiom.ee` entry point it
   discovers via importlib, with no whitelist check. A fake package installed into the same
   Python environment could register a `axiom.ee` entry point and get loaded instead of the real
   EE plugin.

The piracy threat model at this stage: casual (copy-paste licence key, extract wheel, patch source).
Not: determined binary patchers or hardware fingerprinting — that's overkill for self-hosted.

## Solution

### Change 1: Signed Wheel Manifest (`ee/__init__.py`)

Introduce a per-release manifest file signed with the same Ed25519 private key used for licences.

**Manifest format** (`axiom_ee-0.1.0-manifest.json`):
```json
{
  "version": "0.1.0",
  "wheels": {
    "axiom_ee-0.1.0-cp312-cp312-linux_x86_64.whl": "sha256:abc123...",
    "axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl": "sha256:def456..."
  },
  "signed_at": "2026-04-11T12:00:00Z"
}
```

The manifest body is the canonical JSON bytes (json.dumps, sort_keys=True, no extra whitespace).
The `sig` field is `base64url(Ed25519_sign(canonical_body_bytes))` appended as a top-level key.

**Verification steps in `_install_ee_wheel()`** (replace current implementation):
1. Glob `/tmp/axiom_ee-*.whl` — find the wheel (existing)
2. Derive expected manifest filename from wheel filename: `axiom_ee-<version>-manifest.json`
3. Look for manifest in same directory as wheel (`/tmp/`)
4. Load manifest JSON, extract `sig` field, verify Ed25519 signature against `_LICENCE_PUBLIC_KEY_PEM`
5. Compute `hashlib.sha256(wheel_bytes).hexdigest()`
6. Assert wheel name is in manifest `wheels` dict and hash matches
7. Only then proceed with `pip install`
8. Raise `RuntimeError` (not silent fallback) on any verification failure

**Why manifest-per-release, not hash-in-JWT:** Wheel bugfixes happen more often than licence
re-issues. A manifest decouples software versioning from customer licences. One manifest per
release, issued once, used by all customers.

The hardcoded `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py` is imported and reused for
manifest verification — no new key material needed.

### Change 2: HMAC Boot Log (`licence_service.py`)

Replace the `_compute_hash` function — 4-line change:

```python
# Before
def _compute_hash(prev_hash_hex: str, iso_ts: str) -> str:
    return hashlib.sha256(f"{prev_hash_hex}{iso_ts}".encode()).hexdigest()

# After
import hmac as _hmac_mod

def _compute_hash(prev_hash_hex: str, iso_ts: str) -> str:
    key = os.getenv("ENCRYPTION_KEY", "dev-fallback-key").encode()
    msg = f"{prev_hash_hex}{iso_ts}".encode()
    return _hmac_mod.new(key, msg, hashlib.sha256).hexdigest()
```

`ENCRYPTION_KEY` is already required for production Fernet encryption. Without it, the hash chain
entries cannot be reproduced — file tampering is detectable.

**Migration:** Existing `boot.log` entries used plain SHA256. The chain verification will fail on
first boot after the upgrade. Resolution: delete `secrets/boot.log` on upgrade (rollback protection
resets, acceptable for one deploy). Add a note to the release changelog.

Also update `check_and_record_boot()` to verify the chain on read (not just append), so tampering
of historical entries is caught, not just missing entries.

### Change 3: Entry Point Whitelist (`ee/__init__.py`)

Add a constant and a pre-load check in both `activate_ee_live()` and `load_ee_plugins()`:

```python
# The only trusted entry point — matches axiom_ee wheel's entry_points.txt:
# [axiom.ee]
# ee = ee.plugin:EEPlugin
_TRUSTED_ENTRY_POINT_VALUE = "ee.plugin:EEPlugin"

for ep in plugins:
    if ep.value != _TRUSTED_ENTRY_POINT_VALUE:
        raise RuntimeError(
            f"Untrusted EE entry point '{ep.value}' — refusing to load. "
            f"Expected '{_TRUSTED_ENTRY_POINT_VALUE}'."
        )
    plugin_cls = ep.load()
    ...
```

### Change 4: New `sign_wheels.py` tool (`axiom-licenses/tools/`)

Add a standalone CLI for generating the signed wheel manifest at release time:

```bash
python tools/sign_wheels.py \
  --key keys/licence.key \
  --version 0.1.0 \
  /path/to/axiom_ee-0.1.0-cp312-cp312-linux_x86_64.whl \
  /path/to/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl
```

Outputs `axiom_ee-0.1.0-manifest.json` to the current directory.

Logic:
1. Load Ed25519 private key from `--key`
2. For each wheel path: compute `sha256(wheel_bytes).hexdigest()`
3. Build manifest body: `{"version": ..., "wheels": {...}, "signed_at": ...}`
4. Sign canonical JSON bytes with Ed25519 private key
5. Embed base64url-encoded signature as `"sig"` field
6. Write manifest JSON

### Delivery model after this change

Per release, distribute:
```
axiom_ee-0.1.0-cp312-cp312-linux_x86_64.whl
axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl
axiom_ee-0.1.0-manifest.json
```
Customer places wheel + manifest in `/tmp/` (or configured EE path), licence.key in `secrets/`.
On startup/reload: manifest verified → wheel hash verified → install → proceed.

### Tests to add/update

- `test_licence_service.py`: HMAC chain correctness, tampered log detection
- `test_licence_service.py`: chain break on wrong ENCRYPTION_KEY
- `ee/__init__.py` tests: valid manifest → installs, missing manifest → RuntimeError,
  wrong hash → RuntimeError, bad sig → RuntimeError, untrusted entry point → RuntimeError
- `axiom-licenses/tests/test_sign_wheels.py`: manifest generation + round-trip verify

### Explicitly out of scope

- Licence sharing detection (requires online check-in, premature for stage)
- Hardware fingerprinting (fragile in containers)
- Encrypted wheel contents (maintenance burden)
- Key revocation (needs live customer consideration)

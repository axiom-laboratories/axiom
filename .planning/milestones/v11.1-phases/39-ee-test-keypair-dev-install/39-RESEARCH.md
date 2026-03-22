# Phase 39: EE Test Keypair + Dev Install - Research

**Researched:** 2026-03-20
**Domain:** Ed25519 licence infrastructure, editable Python package install, licence wire format
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script structure**: 4 separate Python scripts in `mop_validation/scripts/`:
- `generate_ee_keypair.py` — generates the Ed25519 test keypair (one-time setup)
- `patch_ee_source.py` — patches `plugin.py` + runs `pip install -e .` (repeatable)
- `generate_ee_licence.py` — produces valid and expired licence strings
- `verify_ee_install.py` — API-level assertions for EEDEV-03/04/05

Python throughout (consistent with existing mop_validation scripts; uses `cryptography` lib directly)

**Key storage**: Files stored in `mop_validation/secrets/ee/` subdirectory:
- `ee_test_private.pem` (PKCS8, no encryption)
- `ee_test_public.pem` (SubjectPublicKeyInfo)

**Patching strategy**: `patch_ee_source.py` does string replacement of the `_LICENCE_PUBLIC_KEY_BYTES` line in `~/Development/axiom-ee/ee/plugin.py` via regex, then runs `pip install -e ~/Development/axiom-ee/`. `--restore` flag reverts to `b'\x00' * 32` placeholder.

**Licence construction**:
- Valid licence: `customer_id = "axiom-dev-test"`, far-future `exp`, all EE features enabled
- Expired licence: same fields, `exp = 1704067200` (2024-01-01 00:00:00 UTC — fixed, deterministic)
- Wire format: `base64url(json_payload).base64url(ed25519_sig)` (matching `_parse_licence()` in `plugin.py`)
- Output: `mop_validation/secrets/ee/ee_valid_licence.env` and `ee_expired_licence.env` (each contains `AXIOM_LICENCE_KEY=<key>`)

**Verification form**: Standalone script, does NOT extend `verify_ce_install.py`. EEDEV-04 and EEDEV-05 use manual restart flow — script prints docker compose commands, operator runs them, re-runs verifier. Output style: `[PASS]` / `[FAIL]` per requirement ID.

### Claude's Discretion

- Exact feature flag names in the test licence JSON (derive from EE plugin's feature-gating logic)
- Timeout/retry logic in `verify_ee_install.py` for API readiness after stack restart
- Error messaging when key files are missing (e.g., `generate_ee_keypair.py` not yet run)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EEDEV-01 | Local Ed25519 test keypair generated (test public + private key) and stored in `mop_validation/secrets/` | `cryptography` lib's `Ed25519PrivateKey.generate()` + PEM serialization; existing pattern in `admin_signer.py` |
| EEDEV-02 | `axiom-ee` EE plugin patched with test public key bytes and installed as editable source (`pip install -e`) — no Cython rebuild required | `setup.py` compiles `.py` to `.so` only in non-editable mode; editable install uses `.py` source directly; regex patch of `_LICENCE_PUBLIC_KEY_BYTES` line |
| EEDEV-03 | Valid test licence generated, `GET /api/licence` returns correct `customer_id`, `exp`, `features` | `_parse_licence()` wire format fully reverse-engineered; `GET /api/licence` response structure confirmed from `main.py` line 846-850 |
| EEDEV-04 | Expired test licence: after restart, `GET /api/features` all false; `GET /api/licence` shows expired state | Expiry path in `register()` returns early before mounting routers; `app.state.licence` is never set; `GET /api/licence` returns `{"edition": "community"}` |
| EEDEV-05 | Missing `AXIOM_LICENCE_KEY`: EE starts in CE-degraded mode (no crash, all features false) | `register()` checks `os.environ.get('AXIOM_LICENCE_KEY', '').strip()` first; empty string causes early return without error |
</phase_requirements>

## Summary

Phase 39 is a pure tooling/scripting phase — no changes to the main `master_of_puppets` repo. All work lives in `mop_validation/scripts/` and `mop_validation/secrets/ee/`. The phase establishes the Ed25519 test key infrastructure that every subsequent EE validation phase depends on.

The key technical insight is that `pip install -e .` on the `axiom-ee` source directory bypasses Cython entirely. The `setup.py` Cython compilation only runs during a normal (non-editable) build. In editable mode, Python resolves `import ee.plugin` directly from the source `.py` file, so patching `plugin.py` with the test public key bytes is immediately effective after `pip install -e .`.

The licence wire format is fully documented in `plugin.py` and exercised in the existing `test_licence.py` test suite. The `generate_ee_licence.py` script can be written directly from reading those two files. All 5 EE feature flags are derivable from `EEContext` in `puppeteer/agent_service/ee/__init__.py`.

**Primary recommendation:** Write the 4 scripts in dependency order: generate keypair → patch source → generate licences → verify install. Each script is independently runnable and idempotent where possible.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | 46.0.5 (installed) | Ed25519 key generation, PEM serialization, signing | Already installed in dev env; same lib used in `admin_signer.py` and `test_licence.py` |
| `requests` | 2.31.0 (installed) | HTTP calls in `verify_ee_install.py` | Already used in `verify_ce_install.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` | stdlib | `pip install -e .` invocation, `docker compose` commands | Use in `patch_ee_source.py` for the pip install step |
| `re` | stdlib | Regex replacement of `_LICENCE_PUBLIC_KEY_BYTES` line | Use in `patch_ee_source.py` for the patch step |
| `base64` | stdlib | base64url encode/decode for licence wire format | Use in `generate_ee_licence.py` |
| `json` | stdlib | Licence payload serialization | Use in `generate_ee_licence.py` |
| `pathlib.Path` | stdlib | Path manipulation, file I/O | Used throughout `verify_ce_install.py` — follow same pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` for HTTP | `httpx` | `requests` already in `verify_ce_install.py`; no advantage |
| regex replacement | AST rewrite | Regex is sufficient for a single known constant line; AST is overkill |
| `.env` files for licence output | JSON or plain text | `.env` format allows direct `source` or `docker compose --env-file` injection |

**Installation:** No new dependencies needed — `cryptography` and `requests` are already installed.

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/
├── scripts/
│   ├── generate_ee_keypair.py     # EEDEV-01 — one-time setup
│   ├── patch_ee_source.py         # EEDEV-02 — repeatable, has --restore flag
│   ├── generate_ee_licence.py     # EEDEV-03 prerequisite
│   └── verify_ee_install.py       # EEDEV-03/04/05 — API assertions
└── secrets/
    └── ee/
        ├── ee_test_private.pem    # PKCS8, unencrypted
        ├── ee_test_public.pem     # SubjectPublicKeyInfo
        ├── ee_valid_licence.env   # AXIOM_LICENCE_KEY=<valid>
        └── ee_expired_licence.env # AXIOM_LICENCE_KEY=<expired>
```

### Pattern 1: Ed25519 Keypair Generation (EEDEV-01)

**What:** Generate raw Ed25519 keypair and save as PEM files.
**When to use:** One-time setup; script should refuse to overwrite existing files unless `--force` flag is passed.

```python
# Source: existing admin_signer.py + test_licence.py fixture (both in this repo)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Save private key — PKCS8, no encryption
private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Save public key — SubjectPublicKeyInfo
public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Get raw 32 bytes for patching into plugin.py
pub_raw = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)  # → exactly 32 bytes, suitable for _LICENCE_PUBLIC_KEY_BYTES
```

### Pattern 2: Source Patching (EEDEV-02)

**What:** Replace the `_LICENCE_PUBLIC_KEY_BYTES` constant in `plugin.py` with the test key bytes literal, then install editable.
**When to use:** After keypair generation; idempotent (can be run again to re-patch).

```python
# Source: direct inspection of ~/Development/axiom-ee/ee/plugin.py line 16
import re
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PLUGIN_PY = Path("~/Development/axiom-ee/ee/plugin.py").expanduser()
PLACEHOLDER = b'\x00' * 32

# Load and format the raw public key bytes as a Python bytes literal
pub_raw = ...  # loaded from ee_test_public.pem, then .public_bytes(Raw, Raw)
bytes_literal = repr(pub_raw)  # → e.g. b'\xab\xcd...'

# Regex: match the constant line exactly
pattern = r'^_LICENCE_PUBLIC_KEY_BYTES: bytes = .*$'
replacement = f'_LICENCE_PUBLIC_KEY_BYTES: bytes = {bytes_literal}  # test key — patched by patch_ee_source.py'

content = PLUGIN_PY.read_text()
new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
PLUGIN_PY.write_text(new_content)

# --restore flag: replace back with placeholder
restore_line = "_LICENCE_PUBLIC_KEY_BYTES: bytes = b'\\x00' * 32  # placeholder — replace before release"
# Then: pip install -e ~/Development/axiom-ee/
import subprocess
subprocess.run(["pip", "install", "-e", str(Path("~/Development/axiom-ee").expanduser())], check=True)
```

**Critical:** The editable install must run AFTER patching, not before. The `.py` source file is what's imported at runtime.

### Pattern 3: Licence Wire Format (EEDEV-03 prerequisite)

**What:** Produce `base64url(json_payload).base64url(ed25519_sig)` strings that `_parse_licence()` accepts.
**Exactly mirrors:** `make_licence_key()` in `puppeteer/agent_service/tests/test_licence.py`.

```python
# Source: puppeteer/agent_service/tests/test_licence.py lines 19-31
import base64, json, time

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def make_licence_key(private_key, payload_dict: dict) -> str:
    payload_bytes = json.dumps(payload_dict, separators=(',', ':')).encode()
    sig_bytes = private_key.sign(payload_bytes)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig_bytes)}"

# Valid licence payload — far future expiry
VALID_PAYLOAD = {
    "customer_id": "axiom-dev-test",
    "exp": int(time.time()) + 10 * 365 * 86400,  # ~10 years
    "features": ["foundry", "audit", "webhooks", "triggers", "rbac",
                 "resource_limits", "service_principals", "api_keys"],
}

# Expired licence payload — fixed past timestamp (deterministic)
EXPIRED_PAYLOAD = {
    "customer_id": "axiom-dev-test",
    "exp": 1704067200,  # 2024-01-01 00:00:00 UTC
    "features": ["foundry", "audit", "webhooks", "triggers", "rbac",
                 "resource_limits", "service_principals", "api_keys"],
}
```

### Pattern 4: verify_ee_install.py structure

**What:** Mirrors `verify_ce_install.py` — same `check()` helper, same path constants, same `wait_for_stack()`, same admin token acquisition.
**Key difference:** Hits `GET /api/licence` (requires auth) and checks `edition`, `customer_id`, `expires`, `features` fields.

```python
# Source: verify_ce_install.py (full file) + main.py lines 838-851

# GET /api/licence response when EE active (from main.py):
# {
#   "edition": "enterprise",
#   "customer_id": licence.get("customer_id"),
#   "expires": exp_dt,  # ISO 8601 string
#   "features": licence.get("features", []),
# }

# GET /api/licence response when EE inactive / expired / missing key (from main.py):
# {"edition": "community"}

# GET /api/features response — keys from EEContext in ee/__init__.py:
EE_FEATURE_KEYS = {
    "audit", "foundry", "webhooks", "triggers",
    "rbac", "resource_limits", "service_principals", "api_keys",
}
# All true when EE active; all false when CE/expired/missing key
```

### Anti-Patterns to Avoid

- **Patching before reading raw key bytes:** Load the private key from the saved PEM file (not regenerating) when producing raw bytes for patching — ensures keypair files and plugin are always in sync.
- **Running `pip install -e .` before patching:** The installed package points to the source file, so order doesn't matter at import time. But patching first and installing second is the cleaner mental model.
- **Using `base64.b64encode` instead of `base64.urlsafe_b64encode`:** `_parse_licence()` uses `urlsafe_b64decode` — non-url-safe chars (`+`, `/`) will cause decode errors.
- **Including padding `=` in the wire format:** `_parse_licence()` adds `==` padding on decode, so the encoded strings must NOT include padding.
- **Storing the licence key in a plain `.env` file without the `AXIOM_LICENCE_KEY=` prefix:** The env file must be directly injectable via `docker compose --env-file` or `source`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 key generation | Custom byte manipulation | `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.generate()` | Handles CSPRNG, key material safety |
| Ed25519 signing | Raw byte ops | `private_key.sign(message_bytes)` from `cryptography` | Correct RFC 8032 implementation |
| base64url encoding | Custom replace | `base64.urlsafe_b64encode(data).rstrip(b'=')` | Handles edge cases in padding |
| Licence wire format decoding | Custom parser | Copy `_b64url_encode` + `make_licence_key` from `test_licence.py` exactly | Already battle-tested against `_parse_licence()` |

**Key insight:** The licence format verification logic already exists in `test_licence.py` — the `generate_ee_licence.py` script is essentially the same code written as a standalone tool rather than a pytest fixture.

## Common Pitfalls

### Pitfall 1: Editable install still uses compiled `.so` files

**What goes wrong:** `pip install -e .` succeeds but `import ee.plugin` loads a previously compiled `plugin.cpython-3XX.so` from `ee/__pycache__` or an old build directory instead of `plugin.py`.
**Why it happens:** Python's import system prefers `.so` over `.py` when both exist in the same directory, and old Cython builds leave `.so` files in place.
**How to avoid:** After `pip install -e .`, verify with `python -c "import ee.plugin; import inspect; print(inspect.getfile(ee.plugin))"` — it must print a `.py` path, not `.so`. If `.so` files exist, delete them before patching.
**Warning signs:** `_LICENCE_PUBLIC_KEY_BYTES` is `b'\x00' * 32` even after patching.

### Pitfall 2: Raw key bytes vs. PEM bytes in the patch

**What goes wrong:** Script writes the PEM-encoded public key bytes (starting with `-----BEGIN PUBLIC KEY-----`) into `_LICENCE_PUBLIC_KEY_BYTES` instead of the 32-byte raw representation.
**Why it happens:** `public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)` returns ~90 bytes of PEM; `Ed25519PublicKey.from_public_bytes()` in `_parse_licence()` expects exactly 32 raw bytes and raises `ValueError`.
**How to avoid:** Always use `public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)` to get the 32-byte value for patching. Save the full PEM separately for human readability / future key loading.
**Warning signs:** `ValueError: An Ed25519 public key is 32 bytes long` in stack logs.

### Pitfall 3: `mop_validation/secrets/ee/` directory doesn't exist yet

**What goes wrong:** `generate_ee_keypair.py` fails with `FileNotFoundError` when writing PEM files.
**Why it happens:** The `ee/` subdirectory is new in this phase — `mop_validation/secrets/` does not currently exist either (the directory was not present during inspection).
**How to avoid:** `generate_ee_keypair.py` must create `mop_validation/secrets/ee/` with `Path(...).mkdir(parents=True, exist_ok=True)` before writing files.
**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: '.../secrets/ee/ee_test_private.pem'`.

### Pitfall 4: JSON payload key order affects nothing but be consistent

**What goes wrong:** `json.dumps(payload)` without `separators=(',', ':')` produces whitespace, making the licence key slightly larger and looking different from test helpers.
**Why it happens:** Default `json.dumps` uses `', '` and `': '` separators.
**How to avoid:** Always use `json.dumps(payload, separators=(',', ':'))` to match `make_licence_key()` in `test_licence.py` exactly.
**Warning signs:** Non-compact licence strings (contains spaces), though functionally correct.

### Pitfall 5: AXIOM_LICENCE_KEY must be in the Docker agent container's environment

**What goes wrong:** `verify_ee_install.py` injects the licence key into `secrets.env` but the running container never picks it up until restart.
**Why it happens:** Environment variables in a running container are fixed at container start — `secrets.env` changes don't propagate without restart.
**How to avoid:** The verify script for EEDEV-03 must print clear `docker compose` restart instructions with the `--env-file` or inline `AXIOM_LICENCE_KEY=...` injection pattern. The compose.server.yaml does NOT currently have `AXIOM_LICENCE_KEY` in the agent environment section — the operator must add it or use `docker compose run --env`.
**Warning signs:** `GET /api/licence` returns `{"edition": "community"}` even after writing the `.env` file.

### Pitfall 6: `GET /api/licence` requires authentication

**What goes wrong:** `verify_ee_install.py` calls `GET /api/licence` without a JWT and gets `401 Unauthorized`.
**Why it happens:** `main.py` line 839 has `current_user: User = Depends(require_auth)` on the licence endpoint — it is NOT unauthenticated like `/api/features`.
**How to avoid:** `verify_ee_install.py` must obtain an admin token first (same pattern as `verify_ce_install.py`), then pass `Authorization: Bearer <token>` header on all `GET /api/licence` calls.
**Warning signs:** `401` from `/api/licence` in verify output.

## Code Examples

Verified patterns from official sources:

### Loading a saved private key from PEM
```python
# Source: admin_signer.py + cryptography library pattern
from cryptography.hazmat.primitives import serialization

with open("mop_validation/secrets/ee/ee_test_private.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)
```

### Extracting raw 32-byte public key from saved PEM
```python
# Source: test_licence.py fixture (lines 44-46)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

with open("mop_validation/secrets/ee/ee_test_public.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

pub_raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
# len(pub_raw) == 32  ← verified
```

### Regex pattern for patching plugin.py
```python
# Source: direct inspection of axiom-ee/ee/plugin.py line 16
import re

PATTERN = r'^_LICENCE_PUBLIC_KEY_BYTES: bytes = .*$'
# PLACEHOLDER for --restore:
RESTORE_LINE = "_LICENCE_PUBLIC_KEY_BYTES: bytes = b'\\x00' * 32  # placeholder — replace before release"
```

### Checking injected key was loaded
```python
# Source: plugin.py _parse_licence() + main.py get_licence() lines 838-851
# After restart with valid AXIOM_LICENCE_KEY:
resp = requests.get("https://localhost:8001/api/licence",
                    headers={"Authorization": f"Bearer {token}"},
                    verify=False, timeout=10)
# Expected:
# {
#   "edition": "enterprise",
#   "customer_id": "axiom-dev-test",
#   "expires": "20XX-...",  # ISO 8601
#   "features": ["foundry", "audit", "webhooks", "triggers",
#                "rbac", "resource_limits", "service_principals", "api_keys"]
# }
```

### docker compose restart injection pattern for EEDEV-03/04/05
```bash
# Inject valid licence key and restart agent only:
AXIOM_LICENCE_KEY=$(grep AXIOM_LICENCE_KEY mop_validation/secrets/ee/ee_valid_licence.env | cut -d= -f2-)
docker compose -f puppeteer/compose.server.yaml stop agent
AXIOM_LICENCE_KEY="$AXIOM_LICENCE_KEY" docker compose -f puppeteer/compose.server.yaml up -d agent

# Restart without licence key (EEDEV-05 — CE-degraded mode):
docker compose -f puppeteer/compose.server.yaml stop agent
docker compose -f puppeteer/compose.server.yaml up -d agent
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Patching Cython `.so` at runtime | Editable source install + `.py` patching | Established in STATE.md for this phase | No Cython toolchain needed |
| Shared single licence key env var | Per-mode `.env` files (valid/expired/absent) | This phase introduces the pattern | Deterministic, sourceable, Docker-composable |

**Deprecated/outdated:**
- Cython rebuild for test purposes: out of scope per REQUIREMENTS.md; `.py` source install covers all validation needs.

## Open Questions

1. **compose.server.yaml `AXIOM_LICENCE_KEY` injection method**
   - What we know: The current `compose.server.yaml` agent service environment block (lines 61-70) does NOT include `AXIOM_LICENCE_KEY`. The env var must be injected at runtime.
   - What's unclear: Whether to instruct operator to use inline `KEY=val docker compose up -d agent` or to add `AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` to compose.server.yaml permanently.
   - Recommendation: Add `- AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` to compose.server.yaml as part of `patch_ee_source.py` or as a one-time manual step documented in the script output. The `:-` default means CE mode when unset, so it's safe to add permanently.

2. **`mop_validation/secrets/` directory state**
   - What we know: The directory does not currently exist on disk (confirmed by shell inspection).
   - What's unclear: Whether any prior phase created it in a git-ignored form.
   - Recommendation: `generate_ee_keypair.py` must always call `mkdir(parents=True, exist_ok=True)`. Add `mop_validation/secrets/` to `.gitignore` if not already present.

3. **Feature flag names in the licence payload `features` list**
   - What we know: `EEContext` has 8 boolean flags: `foundry`, `audit`, `webhooks`, `triggers`, `rbac`, `resource_limits`, `service_principals`, `api_keys`. The `features` list in the licence payload is stored on `app.state.licence` and returned verbatim by `GET /api/licence`.
   - What's unclear: Whether `register()` in `plugin.py` cross-checks the `features` list against the flags it sets, or just sets all flags unconditionally when the licence is valid.
   - Recommendation: From reading `plugin.py` lines 91-171, `register()` sets feature flags based on successful router mounts — it does NOT filter by the `features` list. The `features` list in the payload is informational only. Use all 8 feature names in the test payload to confirm `GET /api/licence` returns them all.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer/), vitest (dashboard/) |
| Config file | `puppeteer/pytest.ini` or default |
| Quick run command | `cd puppeteer && pytest tests/test_licence.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EEDEV-01 | Test keypair files exist in `mop_validation/secrets/ee/` | smoke (file existence) | `python3 mop_validation/scripts/generate_ee_keypair.py && ls mop_validation/secrets/ee/` | ❌ Wave 0 |
| EEDEV-02 | `axiom-ee` editable install active; `ee.plugin._LICENCE_PUBLIC_KEY_BYTES` is non-placeholder | smoke (import check) | `python3 mop_validation/scripts/patch_ee_source.py && python3 -c "import ee.plugin; assert ee.plugin._LICENCE_PUBLIC_KEY_BYTES != b'\\x00'*32"` | ❌ Wave 0 |
| EEDEV-03 | `GET /api/licence` returns `edition=enterprise` with correct fields after valid key injected | integration (API-level) | `python3 mop_validation/scripts/verify_ee_install.py --case valid` | ❌ Wave 0 |
| EEDEV-04 | `GET /api/features` all false after expired key restart | integration (API-level, manual restart) | `python3 mop_validation/scripts/verify_ee_install.py --case expired` | ❌ Wave 0 |
| EEDEV-05 | `GET /api/features` all false when `AXIOM_LICENCE_KEY` absent | integration (API-level, manual restart) | `python3 mop_validation/scripts/verify_ee_install.py --case absent` | ❌ Wave 0 |

### Existing Unit Test Coverage
The existing `puppeteer/agent_service/tests/test_licence.py` already covers the `_parse_licence()` function and `GET /api/licence` endpoint with monkeypatching. These unit tests pass independently of this phase. Phase 39 adds *operational* validation scripts, not new unit tests.

### Sampling Rate
- **Per task commit:** `python3 -c "import ee.plugin; print(ee.plugin._LICENCE_PUBLIC_KEY_BYTES[:4])"` (import smoke test)
- **Per wave merge:** `cd puppeteer && pytest tests/test_licence.py -x`
- **Phase gate:** All 5 `verify_ee_install.py` PASS lines before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/generate_ee_keypair.py` — covers EEDEV-01
- [ ] `mop_validation/scripts/patch_ee_source.py` — covers EEDEV-02
- [ ] `mop_validation/scripts/generate_ee_licence.py` — covers EEDEV-03 prerequisite
- [ ] `mop_validation/scripts/verify_ee_install.py` — covers EEDEV-03/04/05
- [ ] `mop_validation/secrets/ee/` directory — created by `generate_ee_keypair.py` at runtime

## Sources

### Primary (HIGH confidence)
- Direct source read: `~/Development/axiom-ee/ee/plugin.py` — exact wire format, `_LICENCE_PUBLIC_KEY_BYTES` line, expiry check logic, feature flag assignment
- Direct source read: `puppeteer/agent_service/ee/__init__.py` — `EEContext` field names (8 feature flags), entry_point group name `axiom.ee`
- Direct source read: `puppeteer/agent_service/main.py` lines 820-851 — `GET /api/features` and `GET /api/licence` response shapes; auth requirement on licence endpoint
- Direct source read: `puppeteer/agent_service/tests/test_licence.py` — `make_licence_key()` wire format helper, `_b64url_encode()` implementation; all patterns verified against plugin.py
- Direct source read: `~/Development/toms_home/.agents/tools/admin_signer.py` — Ed25519 keygen and PEM serialization pattern
- Direct source read: `mop_validation/scripts/verify_ce_install.py` — `check()` helper, `wait_for_stack()`, `load_env()`, `get_admin_token()` patterns to mirror

### Secondary (MEDIUM confidence)
- Shell inspection: `pip show cryptography` → version 46.0.5 installed; `pip show requests` → 2.31.0 installed; neither requires installation
- Shell inspection: `ls ~/Development/mop_validation/secrets/` → directory does not exist (must be created by Wave 0)
- Shell inspection: `cat axiom_ee.egg-info/entry_points.txt` → confirms `ee = ee.plugin:EEPlugin` under `[axiom.ee]` group

### Tertiary (LOW confidence)
- None — all critical claims verified against source code directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed; no new dependencies required
- Architecture: HIGH — all 4 scripts have exact code patterns derived from existing source
- Pitfalls: HIGH — all pitfalls derived from reading actual source code and shell inspection

**Research date:** 2026-03-20
**Valid until:** Stable (60 days) — this is internal tooling based on first-party source

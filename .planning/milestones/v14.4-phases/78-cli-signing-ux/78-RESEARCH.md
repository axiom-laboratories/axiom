# Phase 78: CLI Signing UX - Research

**Researched:** 2026-03-27
**Domain:** Python CLI (argparse), Ed25519 key generation (`cryptography` lib), credential store migration, REST API integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `cli.py` line 51: change `os.getenv("MOP_URL")` → `os.getenv("AXIOM_URL")`
- Keep `--url` flag override as the highest priority (already correct)
- Default fallback stays `http://localhost:8001`
- Keys stored at `~/.axiom/signing.key` (private) and `~/.axiom/verification.key` (public)
- Use `Path.home() / ".axiom"` — works on Windows, macOS, and Linux without additional dependencies
- Migrate `CredentialStore` default path from `~/.mop/credentials.json` → `~/.axiom/credentials.json`
- `key generate` refuses to overwrite existing keys without `--force` flag (warn and exit)
- After generation, print the public key PEM to stdout so users can copy-paste it
- New subparser: `axiom-push key generate [--force]`
- Uses `cryptography` lib (already a dependency via `signer.py`) — no openssl required
- Generates Ed25519 keypair, writes PEM files to `~/.axiom/`
- Creates `~/.axiom/` dir if it doesn't exist
- Prints public key PEM to stdout + confirms file paths
- New subparser: `axiom-push init`
- Three-step sequence: (1) Login check/device flow, (2) Key generation check/generate, (3) Register public key via POST /signatures
- Key name auto-generated: `socket.gethostname()` + logged-in username from credentials
- On success: print Key ID and ready-to-copy `job push` example command
- `AXIOM_URL` appears as first line in first-job.md Quick Start section
- `init` output shows exact `job push` command with real values substituted in

### Claude's Discretion

- Error handling for network failures during `POST /signatures`
- Whether to add a `--name` flag to `init` to override the auto-generated key name
- Progress output formatting (plain print vs rich/click styling — keep consistent with existing CLI style)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | `axiom-push` reads `AXIOM_URL` env var for server address (fixes silent MOP_URL mismatch) | Single-line fix in `cli.py` line 51: `os.getenv("MOP_URL")` → `os.getenv("AXIOM_URL")` |
| CLI-02 | User can generate an Ed25519 keypair locally with `axiom-push key generate` | `cryptography` lib already installed; `Ed25519PrivateKey.generate()` + `private_bytes()`/`public_key().public_bytes()` pattern confirmed in existing tests |
| CLI-03 | User can complete login, key generation, and public key registration with `axiom-push init` | `do_login()` in cli.py is reusable; `POST /signatures` confirmed at line 1663 in main.py; `MOPClient.from_store()` provides authenticated client; needs new `register_signature()` method on client |
| CLI-04 | `first-job.md` documents the `axiom-push init` / `key generate` flow as the primary path | Current doc uses openssl ceremony as Step 1; doc needs restructuring with `axiom-push init` as Quick Start and openssl as fallback |
</phase_requirements>

---

## Summary

Phase 78 is a pure CLI and documentation change with zero backend API changes required. All four requirements are tightly scoped to two files in `mop_sdk/` (`cli.py`, `auth.py`), one file in `mop_sdk/` (`client.py` needs one new method), and one documentation file (`docs/docs/getting-started/first-job.md`).

The existing codebase already has every library primitive needed: `Ed25519PrivateKey.generate()` from `cryptography` is used in `test_signer.py`, `CredentialStore` uses `Path.home()` correctly, and `do_login()` is a self-contained function that `init` can call directly. The `POST /signatures` backend endpoint is live and accepts `{ name: str, public_key: str }`.

The largest risk is a clean credential path migration from `~/.mop/` to `~/.axiom/` — the `CredentialStore` default path change must not break existing users who already have `~/.mop/credentials.json`. The plan should include a migration note or backward-compatible fallback.

**Primary recommendation:** Three focused tasks — (1) AXIOM_URL fix + `key generate` subcommand, (2) `init` flow + `client.py` `register_signature()`, (3) `first-job.md` rewrite. Each is independently testable.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | already installed (req in PKG-INFO) | Ed25519 key generation and PEM serialization | Already used by `signer.py`; no new dependency |
| `argparse` | stdlib | CLI parsing with nested subparsers | Already used; `key` → `generate` follows same pattern as `job` → `push`/`create` |
| `pathlib.Path` | stdlib | Cross-platform `~/.axiom/` path construction | Already used in `CredentialStore`; `Path.home() / ".axiom"` |
| `socket` | stdlib | `socket.gethostname()` for auto key name | No dependency; used in `init` step 3 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | already installed | HTTP calls in `MOPClient` | Used by existing `register_signature()` implementation |
| `os` | stdlib | `os.chmod(path, 0o600)` for key file permissions | Match same pattern as `CredentialStore.save()` |

### Installation
No new dependencies required. All libraries are already in `mop_sdk`'s dependency set.

---

## Architecture Patterns

### Recommended File Changes
```
mop_sdk/
├── cli.py          # AXIOM_URL fix, key subparser, init subparser, do_key_generate(), do_init()
├── auth.py         # CredentialStore default path: ~/.mop/ → ~/.axiom/
├── client.py       # New: register_signature(name, public_key) method
└── tests/
    └── test_cli.py # New tests for key generate, init flow
docs/docs/getting-started/
└── first-job.md    # Restructure: axiom-push init as primary path
```

### Pattern 1: Nested argparse subparser (existing pattern)
**What:** `key` is a new subparser group under the root parser, with `generate` as its sub-subcommand. This mirrors how `job` → `push`/`create` works.
**When to use:** Consistent with existing CLI structure — no new patterns introduced.
**Example:**
```python
# Follows the exact pattern at lines 19-37 of cli.py
key_parser = subparsers.add_parser("key", help="Manage signing keys")
key_subparsers = key_parser.add_subparsers(dest="subcommand", help="Key commands")

generate_parser = key_subparsers.add_parser("generate", help="Generate an Ed25519 signing keypair")
generate_parser.add_argument("--force", action="store_true", help="Overwrite existing keys")
```

### Pattern 2: Ed25519 keypair generation (from test_signer.py)
**What:** Generate keypair, serialize to PEM, write to disk with 0o600 permissions.
**When to use:** `do_key_generate()` function and the key-generation step inside `do_init()`.
**Example:**
```python
# Source: confirmed in mop_sdk/tests/test_signer.py lines 11-18
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

priv = ed25519.Ed25519PrivateKey.generate()
priv_pem = priv.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
pub_pem = priv.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
```

### Pattern 3: init flow — check-then-do each step
**What:** Each step in `do_init()` checks whether it's already done, prints status, and skips or runs. Uses existing `do_login()` logic.
**When to use:** `axiom-push init` command handler.
**Example:**
```python
def do_init(base_url: str):
    # Step 1: Login
    store = CredentialStore()
    creds = store.load()
    if creds and creds.get("access_token"):
        username = creds.get("username", "unknown")
        print(f"Already logged in as {username} — skipping login.")
    else:
        do_login(base_url)
        creds = store.load()  # reload after login

    # Step 2: Key generation
    axiom_dir = Path.home() / ".axiom"
    priv_path = axiom_dir / "signing.key"
    pub_path  = axiom_dir / "verification.key"
    if priv_path.exists():
        print(f"Keys already exist — using {priv_path}")
        pub_pem = pub_path.read_text()
    else:
        pub_pem = do_key_generate(force=False)  # returns pub PEM string

    # Step 3: Register public key
    client = MOPClient.from_store(verify_ssl=False)
    hostname = socket.gethostname()
    key_name = f"{creds.get('username', 'user')}@{hostname}"
    result = client.register_signature(name=key_name, public_key=pub_pem)
    key_id = result["id"]
    print(f"\nSetup complete.")
    print(f"Key ID: {key_id}")
    print(f"\nPush your first job:")
    print(f"  axiom-push job push --script hello.py --key {priv_path} --key-id {key_id}")
```

### Pattern 4: register_signature() in client.py
**What:** New method on `MOPClient` that POSTs to `/signatures`.
**When to use:** Called by `do_init()`.
**Example:**
```python
def register_signature(self, name: str, public_key: str) -> dict:
    """Registers an Ed25519 public key with the server."""
    resp = self.request("POST", "/signatures", json={"name": name, "public_key": public_key})
    resp.raise_for_status()
    return resp.json()
```

### Anti-Patterns to Avoid
- **Calling `do_login()` unconditionally in `init`:** Always check for existing valid token first; calling login when already authenticated creates a confusing experience.
- **Writing key files without setting 0o600 permissions:** `CredentialStore.save()` already demonstrates this pattern — `os.chmod(path, 0o600)` immediately after writing.
- **Constructing `~/.axiom/` path with string concatenation:** Use `Path.home() / ".axiom"` always, not `os.path.join(os.environ["HOME"], ".axiom")` — the Path approach works on Windows.
- **Using `do_login(base_url)` when `init` needs the base_url:** `do_init()` receives `base_url` from `main()` exactly as `do_login()` does — pass it through, don't read the env var again.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 key generation | Custom key generation | `ed25519.Ed25519PrivateKey.generate()` from `cryptography` | Already installed, already used in `signer.py` and `test_signer.py`; custom crypto is a security anti-pattern |
| PEM serialization | Custom PEM formatting | `private_bytes()` / `public_bytes()` from `cryptography.hazmat.primitives.serialization` | PEM encoding is non-trivial; the library handles PKCS8 format, headers, and base64 correctly |
| HTTP call to `/signatures` | Custom requests call | `MOPClient.register_signature()` (new method on existing client) | Reuses auth headers, SSL config, and retry logic already in `MOPClient.request()` |
| Cross-platform home dir | `os.environ["HOME"]` | `Path.home()` | `Path.home()` handles Windows (`USERPROFILE`), macOS, and Linux correctly |

---

## Common Pitfalls

### Pitfall 1: CredentialStore path migration silently breaks existing sessions
**What goes wrong:** Changing the default path from `~/.mop/credentials.json` to `~/.axiom/credentials.json` causes `MOPClient.from_store()` to throw "Not logged in" for any user who authenticated before the upgrade.
**Why it happens:** `from_store()` instantiates `CredentialStore()` with no arguments, which uses the default path. After the rename, the old file at `~/.mop/credentials.json` is invisible.
**How to avoid:** The plan should include a note that this is a breaking change for local dev users who are already logged in. The safest approach is to add a one-time migration step in `CredentialStore.__init__` that checks for the old path and copies/moves the file if the new path doesn't exist. Keep this simple — one `if old_path.exists() and not new_path.exists(): shutil.move(old_path, new_path)` in `__init__`.
**Warning signs:** Tests pass but manual testing after upgrade shows "Not logged in" immediately.

### Pitfall 2: `init` step 3 fails if user already has a key with the same auto-generated name
**What goes wrong:** `POST /signatures` with `name: "alice@laptop"` will succeed or fail depending on whether the server enforces name uniqueness. If the user runs `axiom-push init` twice (the second run finds existing keys and skips generation but still POSTs), it creates a duplicate registration.
**Why it happens:** `init` skips key generation if files already exist, but currently there is no check before POSTing to `/signatures`.
**How to avoid:** Before POSTing, call `GET /signatures` to check if any registered key name matches the auto-generated name. If found, print the existing key ID and skip registration. This also satisfies the idempotent "safe to re-run" UX goal.
**Warning signs:** Running `axiom-push init` twice creates duplicate entries in the Signatures list.

### Pitfall 3: `username` not stored in credentials.json
**What goes wrong:** `init` step 3 needs `username` to construct `"alice@hostname"`. The current `do_login()` only saves `base_url`, `access_token`, and `role` to `credentials.json` — not `username`.
**Why it happens:** The device flow token response from the backend doesn't currently expose `username` in the token payload returned to the CLI, or the CLI simply never stores it.
**How to avoid:** The plan must check what fields `POST /auth/device/token` returns. If `username` is not in the response, use a fallback (e.g., `role` as a prefix, or just `socket.gethostname()` alone as the key name). Alternatively, call `GET /auth/me` with the fresh token to retrieve the username after login. The simplest fix: after login succeeds, make a `GET /auth/me` call and persist `username` to `credentials.json`.
**Warning signs:** `init` output shows `None@hostname` or crashes on `creds.get("username")`.

### Pitfall 4: CLI entry point is `mop-push`, not `axiom-push`
**What goes wrong:** The egg-info `entry_points.txt` declares `mop-push = mop_sdk.cli:main`. The docs and CONTEXT.md reference `axiom-push`. If the entry point is not renamed, `axiom-push` won't be found on PATH.
**Why it happens:** The package was originally called `mop-sdk`; the CLI command name hasn't been updated to match the `axiom-push` branding used throughout the docs.
**How to avoid:** The plan MUST include updating the entry point declaration from `mop-push` to `axiom-push` in whichever setup file defines it (setup.cfg, pyproject.toml, or setup.py — currently not found in `mop_sdk/`, but `mop_sdk.egg-info/entry_points.txt` proves one exists). Find and update the source setup file. Users will need to reinstall (`pip install -e .`) after this change.
**Warning signs:** `axiom-push --help` gives "command not found" while `mop-push --help` works.

### Pitfall 5: `key generate` --force writes files but does not set 0o600
**What goes wrong:** `--force` overwrites existing key files but forgets to `chmod` the new files if the existing files already had correct permissions (Python `open(..., 'w')` inherits umask, not the original file's mode).
**Why it happens:** Developers copy the write pattern without remembering to call `os.chmod` afterward.
**How to avoid:** Always call `os.chmod(path, 0o600)` after every write to a key file — whether generating new or overwriting. Match the pattern in `CredentialStore.save()`.

---

## Code Examples

### Key generation with PEM serialization (verified)
```python
# Source: mop_sdk/tests/test_signer.py lines 11-18 (confirmed in codebase)
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os

axiom_dir = Path.home() / ".axiom"
axiom_dir.mkdir(parents=True, exist_ok=True)

priv = ed25519.Ed25519PrivateKey.generate()

priv_pem = priv.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
pub_pem = priv.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

priv_path = axiom_dir / "signing.key"
pub_path  = axiom_dir / "verification.key"

priv_path.write_bytes(priv_pem)
os.chmod(priv_path, 0o600)

pub_path.write_bytes(pub_pem)
os.chmod(pub_path, 0o644)  # Public key may be 0o644 — readable, not sensitive
```

### POST /signatures — confirmed contract
```python
# Source: puppeteer/agent_service/main.py line 1663 + models.py line 179
# Request:  { "name": str, "public_key": str (PEM) }
# Response: { "id": str, "name": str, "public_key": str, "uploaded_by": str, "created_at": datetime }
resp = self.request("POST", "/signatures", json={"name": name, "public_key": public_key})
resp.raise_for_status()
result = resp.json()
key_id = result["id"]
```

### CredentialStore default path change
```python
# Source: mop_sdk/auth.py line 17 (current)
# Change FROM:
self.config_path = Path.home() / ".mop" / "credentials.json"
# Change TO:
self.config_path = Path.home() / ".axiom" / "credentials.json"
```

### AXIOM_URL fix — single-line change
```python
# Source: mop_sdk/cli.py line 51 (confirmed)
# Change FROM:
base_url = args.url or os.getenv("MOP_URL") or "http://localhost:8001"
# Change TO:
base_url = args.url or os.getenv("AXIOM_URL") or "http://localhost:8001"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `openssl genpkey` ceremony | `axiom-push key generate` | Phase 78 | Eliminates openssl dependency; works on machines without openssl |
| Manual dashboard registration | `axiom-push init` one-step flow | Phase 78 | Reduces new user time-to-first-job from ~10 steps to 2 commands |
| `MOP_URL` env var | `AXIOM_URL` env var | Phase 78 | Aligns CLI with published docs (axiom-push.md already documents `AXIOM_URL`) |
| `~/.mop/credentials.json` | `~/.axiom/credentials.json` | Phase 78 | Consistent branding; `~/.axiom/` becomes the single config directory |

**Deprecated/outdated:**
- `MOP_URL`: Replaced by `AXIOM_URL`. Will silently be ignored after fix — no backward compat needed per locked decision (the old env var was always wrong/broken anyway).
- `openssl genpkey` as the documented primary path in `first-job.md`: Replaced by `axiom-push init` as Step 0.

---

## Open Questions

1. **`username` field in credentials.json**
   - What we know: `do_login()` saves `base_url`, `access_token`, and `role` — not `username`
   - What's unclear: Does `POST /auth/device/token` return a `username` field in the response? (Not visible in `DeviceFlowHandler.poll_for_token()` — it just returns whatever JSON the server sends)
   - Recommendation: During implementation, inspect the actual token response shape. If `username` is present, store it in `credentials.json`. If not, add a `GET /auth/me` call after login to retrieve and persist it. This is required for the `username@hostname` key name in `init` step 3.

2. **Entry point source file location**
   - What we know: `mop_sdk.egg-info/entry_points.txt` shows `mop-push = mop_sdk.cli:main` — but the source setup file (setup.cfg / pyproject.toml / setup.py) was not found in `mop_sdk/`
   - What's unclear: Where is the `[console_scripts]` declaration in the actual source (not the generated egg-info)?
   - Recommendation: Run `find /home/thomas/Development/master_of_puppets/mop_sdk -name "setup.cfg" -o -name "pyproject.toml" -o -name "setup.py"` during plan execution. The plan must include updating this file plus re-running `pip install -e .`.

3. **Idempotent `init` — duplicate key name handling**
   - What we know: `POST /signatures` accepts any `{ name, public_key }` — no de-duplication check confirmed in the service
   - What's unclear: Does `SignatureService.upload_signature()` enforce unique names or does it silently create duplicates?
   - Recommendation: Add a `GET /signatures` preflight check in `do_init()` before POSTing. If a key with the auto-generated name already exists, print the existing Key ID and skip POST. This is defensive and keeps `init` safely re-runnable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (confirmed — `mop_sdk/tests/` has 4 test files using pytest) |
| Config file | none detected in `mop_sdk/` — pytest is run with `cd puppeteer && pytest` per CLAUDE.md |
| Quick run command | `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/ -x -q` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `main()` uses `AXIOM_URL`, not `MOP_URL`, to set `base_url` | unit | `python -m pytest tests/test_cli.py -x -k "url"` | ❌ Wave 0 |
| CLI-02 | `key generate` creates `signing.key` + `verification.key` with 0o600 permissions | unit | `python -m pytest tests/test_cli.py -x -k "key_generate"` | ❌ Wave 0 |
| CLI-02 | `key generate` refuses to overwrite without `--force` | unit | `python -m pytest tests/test_cli.py -x -k "key_generate_no_overwrite"` | ❌ Wave 0 |
| CLI-02 | `key generate` with `--force` overwrites existing keys | unit | `python -m pytest tests/test_cli.py -x -k "key_generate_force"` | ❌ Wave 0 |
| CLI-03 | `init` skips login when credentials already exist | unit | `python -m pytest tests/test_cli.py -x -k "init_skip_login"` | ❌ Wave 0 |
| CLI-03 | `init` skips key generation when keys already exist | unit | `python -m pytest tests/test_cli.py -x -k "init_skip_keygen"` | ❌ Wave 0 |
| CLI-03 | `init` calls `register_signature` and prints Key ID + job push command | unit | `python -m pytest tests/test_cli.py -x -k "init_full_flow"` | ❌ Wave 0 |
| CLI-03 | `register_signature()` POSTs to `/signatures` and returns id | unit | `python -m pytest tests/test_client.py -x -k "register_signature"` | ❌ Wave 0 |
| CLI-04 | `first-job.md` contains `axiom-push init` as primary path | manual | grep check — `grep "axiom-push init" docs/docs/getting-started/first-job.md` | N/A |

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/test_cli.py tests/test_client.py -x -q`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_sdk/tests/test_cli.py` — add tests covering CLI-01, CLI-02, CLI-03 (new test cases alongside existing ones in the file that already exists)
- [ ] `mop_sdk/tests/test_client.py` — add `test_register_signature()` test

*(Existing test infrastructure covers the framework — only new test cases are needed, not new files)*

---

## Sources

### Primary (HIGH confidence)
- `mop_sdk/cli.py` — actual CLI source, argparse structure, `do_login()` pattern, `MOP_URL` bug location (line 51)
- `mop_sdk/auth.py` — `CredentialStore` implementation, `~/.mop/` path (line 17), 0o600 pattern
- `mop_sdk/client.py` — `MOPClient` methods, `from_store()`, no `register_signature()` confirmed absent
- `mop_sdk/signer.py` — `Signer` using `cryptography` lib; confirms no key generation method exists yet
- `mop_sdk/tests/test_signer.py` — confirmed `Ed25519PrivateKey.generate()` + `private_bytes()` / `public_bytes()` serialization pattern (lines 11-18)
- `puppeteer/agent_service/main.py` line 1663 — `POST /signatures` endpoint confirmed, uses `require_auth`
- `puppeteer/agent_service/models.py` lines 179-192 — `SignatureCreate` and `SignatureResponse` field names confirmed
- `mop_sdk/mop_sdk.egg-info/entry_points.txt` — confirms current entry point is `mop-push`, not `axiom-push`
- `docs/docs/feature-guides/axiom-push.md` — confirms `AXIOM_URL` is the documented env var; confirms `~/.axiom/credentials.json` is already documented

### Secondary (MEDIUM confidence)
- `docs/docs/getting-started/first-job.md` — current doc structure reviewed; openssl is Step 1 and primary path; needs full restructuring

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; no new dependencies
- Architecture: HIGH — all integration points verified by reading actual source files
- Pitfalls: HIGH for items 1, 4, 5 (verified by code reading); MEDIUM for items 2, 3 (dependent on server behavior not tested in this research)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain — argparse, cryptography lib, and the existing backend API are not changing)

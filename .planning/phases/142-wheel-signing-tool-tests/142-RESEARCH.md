# Phase 142: Wheel Signing Tool Tests - Research

**Researched:** 2026-04-13
**Domain:** Python test framework (pytest) for CLI tool validation
**Confidence:** HIGH

## Summary

Phase 142 is a pure test gap closure phase: implement 23 test stubs across 3 files that validate the wheel signing tool infrastructure (sign_wheels.py and gen_wheel_key.py) completed in Phase 140. No new source code is required — the tools are already operational. All test fixtures (temp_wheel_dir, test_keypair, sample_wheel, sample_manifest) are already defined in conftest.py. Tests use direct Python function imports (not subprocess), matching the issue_licence.py test pattern.

The phase requires:
- **test_sign_wheels.py**: 12 tests covering wheel discovery, hashing (64KB chunked), signature format, manifest output, CLI flags (--deploy-name, --quiet, --verify), and error cases (no wheels, SHA256 mismatch)
- **test_key_resolution.py**: 6 tests covering key resolution priority (--key arg > env var), missing key errors, missing files, malformed PEM, and private-to-public fallback in verification mode
- **test_gen_wheel_key.py**: 5 tests covering keypair generation, no-overwrite safety, public key format (bytes literal), --force flag, and secure file permissions (0600)

All tests must assert on SystemExit for CLI error cases. Key insight: the source functions already call sys.exit() directly, so pytest.raises(SystemExit) is the correct pattern without mocking.

**Primary recommendation:** Implement tests by importing functions directly, using the established Ed25519 sign/verify pattern (sign hex string as UTF-8, verify with two-arg form), and validating both success and error paths via SystemExit assertions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 7.x+ | Test framework and execution | Industry standard Python testing; used throughout axiom project (pyproject.toml: asyncio_mode=auto) |
| cryptography | 41.x+ | Ed25519 key generation/signing | Implements RFC 8037 EdDSA; already in project dependencies (pyproject.toml) |
| Python | 3.10+ | Runtime | Project requires >= 3.10 (pyproject.toml); walrus operator and async/await fully supported |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | File and directory operations | Creating/reading temp files and wheel paths; included in Python stdlib |
| json | stdlib | JSON parsing/writing | Validating manifest JSON structure; included in Python stdlib |
| base64 | stdlib | Encoding/decoding signatures | Converting signature bytes to/from base64; included in Python stdlib |
| hashlib | stdlib | SHA256 computation | Computing and verifying wheel hashes; included in Python stdlib |
| argparse | stdlib | Argument parsing validation | Testing CLI argument handling; included in Python stdlib |

### Why No New Dependencies
All testing needs are satisfied by pytest + cryptography (already in project dependencies). The conftest.py fixtures use only standard library + cryptography. No test-specific frameworks (hypothesis, factory-boy, mock libraries) needed because:
- Direct function imports eliminate subprocess mocking complexity
- Ed25519 signing is deterministic (no property-based testing needed)
- Temporary files via pathlib + tempfile are built-in
- File system operations are simple and synchronous

## Architecture Patterns

### Test Organization

```
axiom-licenses/tests/
├── conftest.py               # Shared fixtures: temp_wheel_dir, test_keypair, sample_wheel, sample_manifest
├── test_issue_licence.py     # Existing tests (reference pattern)
└── tools/
    ├── test_sign_wheels.py       # 12 stubs → 12 implementations
    ├── test_key_resolution.py    # 6 stubs → 6 implementations
    └── test_gen_wheel_key.py     # 5 stubs → 5 implementations
```

### Pattern 1: Direct Function Import (not subprocess)

**What:** Import and call functions directly via `from sign_wheels import sign_wheels, resolve_key, hash_wheel, verify_manifests` and `from gen_wheel_key import generate_keypair`. No subprocess invocation of CLI.

**When to use:** All tests in this phase. CONTEXT.md explicitly decides this approach to keep test setup simple and focus on logic validation.

**Example:**
```python
# Source: Phase 140 sign_wheels.py, lines 100-148
from pathlib import Path
from sign_wheels import sign_wheels

def test_wheel_discovery(temp_wheel_dir, sample_wheel):
    """Wheels are discovered in directory."""
    # Import live in test (temp_wheel_dir fixture provides clean dir)
    private_key = load_pem_private_key(...)  # from test_keypair fixture
    sign_wheels(temp_wheel_dir, private_key)
    manifests = list(temp_wheel_dir.glob("*.manifest.json"))
    assert len(manifests) == 1  # sample_wheel + 1 manifest
```

### Pattern 2: SystemExit Assertions

**What:** For CLI functions that call `sys.exit()`, use `pytest.raises(SystemExit)` to validate error handling.

**Why:** Source functions in sign_wheels.py and gen_wheel_key.py exit directly (lines 56, 74, 96, 40, 67) — no mocking needed. SystemExit propagates naturally.

**Example:**
```python
# Source: Phase 140 gen_wheel_key.py, line 40
def test_no_overwrite_without_force(temp_wheel_dir):
    """gen_wheel_key.py refuses to overwrite without --force."""
    out_path = temp_wheel_dir / "test.key"
    out_path.write_bytes(b"existing")
    
    with pytest.raises(SystemExit) as exc_info:
        generate_keypair(out_path, force=False)
    assert "already exists" in str(exc_info.value)
```

### Pattern 3: Ed25519 Sign/Verify Handshake

**What:** Signing and verification must follow the established pattern:
1. **Signing:** Sign the SHA256 hex string (as UTF-8 bytes), not raw wheel bytes → `private_key.sign(sha256_hex.encode('utf-8'))`
2. **Verification:** Verify with two-arg form → `public_key.verify(signature_bytes, message)`
3. **Fixture support:** test_keypair returns (private_pem, public_pem) tuple; load via `serialization.load_pem_private_key()` and `load_pem_public_key()`

**Example (from conftest.py lines 68-87):**
```python
# Source: axiom-licenses/tests/conftest.py
sha256_hex = hashlib.sha256(wheel_bytes).hexdigest()  # Hex string
message = sha256_hex.encode('utf-8')  # Convert to UTF-8 bytes
signature_bytes = private_key.sign(message)  # Sign the message
public_key.verify(signature_bytes, message)  # Verify (2 args)
```

### Pattern 4: Key Resolution via argparse.Namespace

**What:** Functions that accept `args` parameter expect `.key` attribute. For testing, construct minimal namespace:

```python
# Source: Phase 140 sign_wheels.py, line 72
from types import SimpleNamespace
import argparse

def test_key_resolution_arg(test_keypair, temp_wheel_dir):
    """Key --arg takes priority over env var."""
    private_pem, _ = test_keypair
    key_path = temp_wheel_dir / "test.key"
    key_path.write_bytes(private_pem)
    
    args = argparse.Namespace(key=str(key_path))
    resolved = resolve_key(args, mode="private")
    assert resolved is not None
```

### Anti-Patterns to Avoid

- **Subprocess invocation:** Don't use `subprocess.run(["python", "sign_wheels.py", ...])` — CONTEXT.md explicitly prohibits this; keeps tests simple and fast
- **Mocking sys.exit:** Don't patch `sys.exit` — let it propagate as SystemExit naturally; no mock needed
- **Raw wheel bytes for signing:** Don't sign raw wheel bytes; always sign the SHA256 hex string as UTF-8 (Phase 140 line 127)
- **Forgetting key serialization:** Don't pass raw PEM bytes to functions expecting key objects — always deserialize via `load_pem_private_key()` first
- **Assuming relative imports:** test_issue_licence.py shows the pattern — use importlib to load scripts from tools/ as modules (needed because tools/ is not a package)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temporary file management | Custom temp dir logic with mkdir/cleanup | pathlib.Path + tempfile.TemporaryDirectory (conftest.py fixture) | Automatic cleanup on context exit; handles Windows/Linux path differences |
| Ed25519 key generation | Custom cryptographic code | cryptography.hazmat.primitives.asymmetric.ed25519 | RFC 8037 compliance; vetted library; used in Phase 137-140 |
| SHA256 hashing with chunking | Custom reading+hashing | hashlib.sha256() in 64KB chunks (sign_wheels.py pattern) | sign_wheels.py already implements this correctly (lines 49-54); reuse the exact function |
| JSON manifest parsing | Custom dict building | json.loads() + json.dumps() (sign_wheels.py pattern) | Already handles escaping, formatting; no custom parsing needed |
| CLI argument construction | Custom arg dict/object | types.SimpleNamespace or argparse.Namespace | Matches how resolve_key() expects args.key attribute |
| Base64 signature encoding | Custom byte string formatting | base64.b64encode()/b64decode() (conftest.py, sign_wheels.py) | Standard; already used in test fixtures and source code |
| File permission validation | Custom os.stat() parsing | Path.stat().st_mode & 0o777 comparison | Portable across Linux/macOS; handles umask correctly |

**Key insight:** All complexity is already handled by existing functions (sign_wheels.py, gen_wheel_key.py, conftest.py fixtures). Tests should focus on behavior validation, not re-implementing logic.

## Common Pitfalls

### Pitfall 1: Confusing hex string vs. raw bytes for signing

**What goes wrong:** Attempting to sign raw wheel bytes instead of the SHA256 hex string encoded as UTF-8, or vice versa during verification.

**Why it happens:** sign_wheels.py signs the UTF-8 encoding of the hex string (line 127: `sha256_hex.encode('utf-8')`), but test author may think "we're signing the wheel" and pass raw bytes.

**How to avoid:** Always follow the conftest.py pattern: `message = sha256_hex.encode('utf-8'); private_key.sign(message)` and verify with the same message.

**Warning signs:** Signature verification fails with "verification failed" error; signature created in one test fails verification in another (indicates different message formats).

### Pitfall 2: Forgetting to deserialize PEM bytes to key objects

**What goes wrong:** Passing raw PEM bytes (from test_keypair fixture) directly to sign_wheels.py functions that expect Ed25519PrivateKey instances.

**Why it happens:** test_keypair returns (private_pem, public_pem) as bytes. Functions need actual key objects. Easy to forget the `.load_pem_private_key()` step.

**How to avoid:** When using test_keypair directly, always deserialize first:
```python
private_pem, public_pem = test_keypair
private_key = serialization.load_pem_private_key(private_pem, password=None)
public_key = serialization.load_pem_public_key(public_pem)
# Now pass private_key and public_key to functions
```

**Warning signs:** TypeError like "expected Ed25519PrivateKey instance, got bytes"; or AttributeError on .sign() or .verify() methods.

### Pitfall 3: Missing quiet mode output suppression check

**What goes wrong:** Test for --quiet flag passes but doesn't validate that stderr output is actually suppressed.

**Why it happens:** The quiet parameter defaults to False in sign_wheels() (line 104). Easy to create a test that calls `sign_wheels(..., quiet=True)` but doesn't capture and assert on stderr.

**How to avoid:** Use capsys fixture to capture stderr, then assert output contains/doesn't contain expected strings:
```python
def test_quiet_flag(temp_wheel_dir, sample_wheel, test_keypair, capsys):
    """--quiet suppresses per-wheel output."""
    private_key = deserialize(test_keypair[0])
    sign_wheels(temp_wheel_dir, private_key, quiet=True)
    captured = capsys.readouterr()
    assert "Signed:" not in captured.err  # Should not appear with quiet=True
```

**Warning signs:** Test passes but doesn't actually validate output; changing quiet=False in implementation doesn't cause test failure.

### Pitfall 4: Manifest JSON location assumptions

**What goes wrong:** Test assumes manifest is written to expected path but source code writes it somewhere else (e.g., wrong suffix or wrong directory).

**Why it happens:** sign_wheels.py writes manifest at `wheel_path.with_suffix(".manifest.json")` (line 138). Easy to assume wrong file extension or subdirectory.

**How to avoid:** Inspect actual source code line 138-139 and use exact same pattern:
```python
def test_manifest_naming(temp_wheel_dir, sample_wheel, test_keypair):
    """Manifest files match wheel filenames."""
    private_key = deserialize(test_keypair[0])
    sign_wheels(temp_wheel_dir, private_key)
    # Expected manifest: sample_wheel.with_suffix(".manifest.json")
    expected = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    assert expected.exists()
    manifest_data = json.loads(expected.read_text())
    assert "sha256" in manifest_data
    assert "signature" in manifest_data
```

**Warning signs:** Glob returns no files; test fails because manifest path doesn't exist.

### Pitfall 5: Key resolution env var isolation

**What goes wrong:** One test sets AXIOM_WHEEL_SIGNING_KEY env var; subsequent test fails because env var persists across tests.

**Why it happens:** Tests are isolated at code level but not environment level. monkeypatch fixture must be used to undo changes.

**How to avoid:** Always use monkeypatch fixture for env var changes:
```python
def test_key_resolution_env(temp_wheel_dir, test_keypair, monkeypatch):
    """Fallback to env var if --key not provided."""
    private_pem, _ = test_keypair
    key_path = temp_wheel_dir / "test.key"
    key_path.write_bytes(private_pem)
    
    monkeypatch.setenv("AXIOM_WHEEL_SIGNING_KEY", str(key_path))
    args = argparse.Namespace(key=None)  # No --key arg
    resolved = resolve_key(args, mode="private")
    assert resolved is not None
    # monkeypatch auto-reverts after test ends
```

**Warning signs:** Test passes in isolation but fails when run with other tests; test order dependency (PYTHONHASHSEED sensitive).

### Pitfall 6: Not validating exit code

**What goes wrong:** Test catches SystemExit but doesn't verify the exit code (0 for success, 1 for failure).

**Why it happens:** `sys.exit(message)` passes a string as exit code, which Python converts to 1. But test author may not check `.value`.

**How to avoid:** Assert on exit code and/or message:
```python
def test_no_wheels_error(temp_wheel_dir, test_keypair):
    """Sign exits 1 if no wheels found."""
    private_key = deserialize(test_keypair[0])
    with pytest.raises(SystemExit) as exc_info:
        sign_wheels(temp_wheel_dir, private_key)  # Empty dir
    # sys.exit(f"Error: no .whl files found...") → exits with message as code
    assert "no .whl files found" in str(exc_info.value) or exc_info.value == 1
```

**Warning signs:** Test passes even when function doesn't actually error; exit code is None or wrong value.

## Code Examples

Verified patterns from official sources:

### Fixture Pattern: test_keypair
```python
# Source: axiom-licenses/tests/conftest.py, lines 22-41
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

@pytest.fixture
def test_keypair():
    """Generate a fresh Ed25519 keypair for tests."""
    private_key = ed25519.Ed25519PrivateKey.generate()
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
    return (private_pem, public_pem)
```

### Sign/Verify Pattern (2-arg form)
```python
# Source: axiom-licenses/tests/conftest.py, lines 77-82
# Source: axiom-licenses/tools/sign_wheels.py, line 202
from cryptography.hazmat.primitives import serialization

# Signing:
private_key = serialization.load_pem_private_key(private_pem, password=None)
message = sha256_hex.encode('utf-8')
signature_bytes = private_key.sign(message)
signature_b64 = base64.b64encode(signature_bytes).decode('ascii')

# Verification:
public_key = serialization.load_pem_public_key(public_pem)
public_key.verify(signature_bytes, message)  # 2-arg form
```

### CLI Error Handling Pattern
```python
# Source: axiom-licenses/tests/test_issue_licence.py, lines 34-42
import pytest
from types import SimpleNamespace

def test_resolve_key_missing(monkeypatch):
    """Exit with clear error if key missing."""
    monkeypatch.delenv("AXIOM_LICENCE_SIGNING_KEY", raising=False)
    args = SimpleNamespace(key=None)
    with pytest.raises(SystemExit) as exc_info:
        resolve_key(args)
    assert "no signing key" in str(exc_info.value).lower()
```

### Namespace Construction Pattern (for resolve_key)
```python
# Source: axiom-licenses/tools/sign_wheels.py, line 72
import argparse
from types import SimpleNamespace

# Option 1: SimpleNamespace (lightweight, used in existing tests)
args = SimpleNamespace(key="/path/to/key.pem")
resolved = resolve_key(args, mode="private")

# Option 2: argparse.Namespace (equivalent, more formal)
args = argparse.Namespace(key="/path/to/key.pem")
resolved = resolve_key(args, mode="private")
```

### Manifest Verification Pattern
```python
# Source: axiom-licenses/tools/sign_wheels.py, lines 150-215
import json

def test_verify_manifests(temp_wheel_dir, sample_wheel, sample_manifest, test_keypair):
    """Verify mode loads public key and validates all manifests."""
    public_pem = test_keypair[1]
    public_key = serialization.load_pem_public_key(public_pem)
    
    # Write sample manifest to disk
    manifest_path = temp_wheel_dir / "axiom_ee-2.0-py3-none-any.manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest, indent=2))
    
    # Verify should return True (all manifests valid)
    result = verify_manifests(temp_wheel_dir, public_key)
    assert result is True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Subprocess CLI testing (test_issue_licence pattern) | Direct function import testing | Phase 140 (tools created) | Faster, no process spawning, clearer assertion scope |
| Single ed25519 signing test | Comprehensive signing + verification + manifest round-trip | Phase 140 | Can validate full workflow including file I/O |
| Manual temp file cleanup | pytest conftest.py fixtures + tempfile.TemporaryDirectory | Sprint 10+ | Automatic cleanup, isolation between tests |
| Mocked cryptography | Real Ed25519 key generation + signing | Phase 137+ | Validated against actual CryptoAPI behavior |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct` subprocess execution in nodes (Phase 135 decision) — no impact on these tests
- Test-specific cryptography stubs — now use real cryptography library from dependencies

## Open Questions

None — CONTEXT.md provides complete specification. Phase scope, test patterns, fixture definitions, and error handling strategies all locked.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x+ (from pyproject.toml) |
| Config file | axiom-licenses/tests/ (conftest.py only; no pytest.ini needed) |
| Quick run command | `cd axiom-licenses && python -m pytest tests/tools/ -v` |
| Full suite command | `cd axiom-licenses && python -m pytest tests/tools/ -v --tb=short` |

### Phase Requirements → Test Map

Phase 142 has no formal requirement IDs (noted as `null` in orchestrator). The 23 tests are self-evidential requirements:

| Test File | Test Count | Coverage | Automated Command | Status |
|-----------|-----------|----------|-------------------|--------|
| test_sign_wheels.py | 12 | wheel discovery, hashing, signing, manifests, CLI flags, verification | `pytest tests/tools/test_sign_wheels.py -v` | 12 stubs → implementation |
| test_key_resolution.py | 6 | key resolution priority, error cases, private-to-public fallback | `pytest tests/tools/test_key_resolution.py -v` | 6 stubs → implementation |
| test_gen_wheel_key.py | 5 | keypair generation, no-overwrite, public key format, --force, permissions | `pytest tests/tools/test_gen_wheel_key.py -v` | 5 stubs → implementation |

### Sampling Rate
- **Per task commit:** `cd axiom-licenses && python -m pytest tests/tools/test_{FILE}.py -v` (per-test file)
- **Per wave merge:** `cd axiom-licenses && python -m pytest tests/tools/ -v` (all 23 tests)
- **Phase gate:** All 23 tests green (pytest exit code 0) before `/gsd:verify-work`

### Wave 0 Gaps
- [x] Fixtures defined (conftest.py complete)
- [x] Test stubs created with TODO markers
- [x] Import helpers documented in test files
- [ ] Test implementations (Phase 142 tasks)
- [ ] Framework install: Already in pyproject.toml dependencies

All Wave 0 infrastructure complete. Ready for test implementation.

## Sources

### Primary (HIGH confidence)
- Phase 140 decision doc (signed wheel infrastructure) — establishes sign_wheels.py/gen_wheel_key.py API
- axiom-licenses/tools/sign_wheels.py (lines 37–270) — definitive source for function signatures and behavior
- axiom-licenses/tools/gen_wheel_key.py (lines 25–107) — definitive source for keypair generation function
- axiom-licenses/tests/conftest.py (lines 14–88) — fixture definitions (temp_wheel_dir, test_keypair, sample_wheel, sample_manifest)
- axiom-licenses/tests/test_issue_licence.py (lines 22–50) — established testing pattern for CLI tools with sys.exit()

### Secondary (MEDIUM confidence)
- cryptography library official docs — Ed25519 key serialization formats and verification API (2-arg form)
- pytest documentation — SystemExit handling, monkeypatch fixture for env var isolation, capsys for output capture

### Tertiary (LOW confidence)
- None — all guidance comes from verified sources and existing code patterns in the repo

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — pytest and cryptography already in pyproject.toml; established patterns in test_issue_licence.py
- Architecture: **HIGH** — CONTEXT.md specifies exact patterns; existing conftest.py fixtures complete and tested
- Pitfalls: **HIGH** — Based on actual Phase 140 code and common Ed25519/CLI testing errors; all patterns validated in test_issue_licence.py

**Research date:** 2026-04-13
**Valid until:** 2026-04-20 (test infrastructure stable; cryptography API unchanged)
**Source:** Phase 140 implementation + Phase 141 verification + CONTEXT.md discussion notes

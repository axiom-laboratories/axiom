# Phase 142: Wheel Signing Tool Tests - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the 23 test stubs in `axiom-licenses/tests/tools/` for `sign_wheels.py` and `gen_wheel_key.py`. All stub files already exist; this phase fills them with working test assertions. No new source code, no new fixtures in the parent conftest — pure test gap closure.

Files to fill:
- `test_sign_wheels.py` — 12 stubs
- `test_key_resolution.py` — 6 stubs
- `test_gen_wheel_key.py` — 5 stubs

</domain>

<decisions>
## Implementation Decisions

### Test invocation level
- Call Python functions directly via import — do NOT use subprocess CLI invocation
- Import and call `sign_wheels`, `hash_wheel`, `resolve_key`, `verify_manifests` from `sign_wheels` module
- Import and call `generate_keypair` from `gen_wheel_key` module
- Rationale: fixtures (temp_wheel_dir, test_keypair, sample_wheel, sample_manifest) are set up for direct invocation; subprocess adds complexity without benefit since we own the source

### Error assertion pattern
- Use `pytest.raises(SystemExit)` for all sys.exit() tests (no_wheels_error, missing key, file not found, no-overwrite-without-force)
- The functions call sys.exit() directly so SystemExit propagates naturally — no mocking needed

### Claude's Discretion
- Key file setup: write PEM bytes to temp files inline within each test (or via a local helper) — no new shared conftest fixture required
- Whether to assert on SystemExit.value (exit code) or just the exception type — choose what's most readable per test
- Exact assertion style for public key bytes literal format (test_public_key_bytes_literal)
- Test for resolve_key in public mode (private-to-public fallback) — test structure
- Whether subprocess import in test_sign_wheels.py stays (unused) or is removed

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `axiom-licenses/tests/conftest.py`: all needed fixtures defined — `temp_wheel_dir`, `test_keypair`, `sample_wheel`, `sample_manifest`
- `sign_wheels.py` public API: `hash_wheel(path)`, `resolve_key(args, mode)`, `sign_wheels(dir, key, deploy_name, quiet)`, `verify_manifests(dir, key)`, `_build_parser()`
- `gen_wheel_key.py` public API: `generate_keypair(out_path, force)`

### Established Patterns
- Ed25519 sign/verify: sign hex string as UTF-8 bytes (`sha256_hex.encode('utf-8')`), not raw wheel bytes
- `public_key.verify(signature_bytes, message)` — two-arg form (matches Sprint 9 pattern)
- `test_keypair` fixture returns `(private_pem, public_pem)` bytes tuple — tests must load via `serialization.load_pem_private_key()`/`load_pem_public_key()` to get key objects
- `sample_manifest` fixture returns a dict; tests that need a file must write it to `temp_wheel_dir` inline

### Integration Points
- `resolve_key()` takes an argparse Namespace with `.key` attribute — tests need to construct a simple namespace or argparse mock
- Key resolution env var: `AXIOM_WHEEL_SIGNING_KEY` (use `monkeypatch.setenv` for env var tests)

</code_context>

<specifics>
## Specific Ideas

- For `test_key_resolution_env` and similar env var tests: use `monkeypatch.setenv("AXIOM_WHEEL_SIGNING_KEY", str(key_path))` — pytest monkeypatch is the right tool here
- For `resolve_key` tests that pass a namespace: `argparse.Namespace(key=str(path))` is the simplest mock
- `test_public_key_bytes_literal`: capture stdout via `capsys`, assert output starts with `b"""` and contains `-----BEGIN PUBLIC KEY-----`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 142-wheel-signing-tool-tests*
*Context gathered: 2026-04-13*

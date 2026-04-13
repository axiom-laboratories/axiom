# Phase 139: Entry Point Whitelist & Enforcement - Research

**Researched:** 2026-04-13
**Domain:** EE plugin loader security + encryption key bootstrapping
**Confidence:** HIGH

## Summary

Phase 139 hardens two critical initialization paths in the EE license protection system:

1. **Entry Point Whitelist Enforcement** — Validate that `importlib.metadata` entry points for the `axiom.ee` group match an exact hardcoded value (`ee.plugin:EEPlugin`) before loading. Prevents accidental or malicious loading of untrusted plugin code.

2. **ENCRYPTION_KEY Hard Requirement** — Remove the current auto-generate and file-based fallback behaviors from `security.py:_load_or_generate_encryption_key()`. If the `ENCRYPTION_KEY` environment variable is absent, raise `RuntimeError` at module load time with an actionable message including the Fernet key generation one-liner.

Both changes apply to startup (`load_ee_plugins()`) and live-reload (`activate_ee_live()`) code paths, ensuring consistent enforcement across all contexts.

**Primary recommendation:** Implement both checks as simple inline validations before calling `ep.load()` in both code paths. Use `RuntimeError` consistently (already the exception type for security violations in the EE loader).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | (no pin) | Fernet encryption, Ed25519 signature verification | Already a production dependency; Fernet is the standard Python symmetric encryption primitive with built-in authentication. |
| `importlib.metadata` | stdlib (Python 3.10+) | Entry point discovery and loading | Standard Python mechanism for plugin discovery; no external dependency required. |
| `python-jose[cryptography]` | (no pin) | JWT signing/verification | Already in use for auth token management. |
| `pytest` | (no pin) | Unit test framework | Established pattern in test suite (`test_ee_manifest.py`, `test_ee_smoke.py`). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` | stdlib | Mocking and patching | For isolating ENCRYPTION_KEY checks and entry point discovery in tests. |

## Architecture Patterns

### Recommended Project Structure

Modifications are localized to two files:

```
puppeteer/
├── agent_service/
│   ├── security.py               # _load_or_generate_encryption_key() — ENCRYPTION_KEY enforcement
│   ├── ee/__init__.py            # load_ee_plugins() + activate_ee_live() — entry point whitelist
│   └── main.py                   # Unchanged (security.py import already at top)
├── tests/
│   ├── test_ee_manifest.py       # Existing manifest verification tests (no changes)
│   ├── test_ee_smoke.py          # Existing EE features test (no changes)
│   └── test_encryption_key_enforcement.py  # NEW: tests for ENCRYPTION_KEY hard requirement
└── (potential new test file for entry point validation)
```

### Pattern 1: ENCRYPTION_KEY Hard Requirement

**What:** Module-level validation that terminates startup immediately if `ENCRYPTION_KEY` env var is absent.

**When to use:** Enforcing cryptographic material presence for all deployments (CE and EE, production and dev, no exceptions).

**Example:**
```python
# Source: security.py (lines 17-28, to be refactored)

def _load_or_generate_encryption_key() -> bytes:
    """Load ENCRYPTION_KEY from environment or raise RuntimeError.
    
    ENCRYPTION_KEY is required for all deployments (CE and EE).
    No auto-generate fallback; no file-based fallback.
    
    Raises RuntimeError if ENCRYPTION_KEY is not set.
    """
    if val := os.getenv("ENCRYPTION_KEY"):
        return val.encode()
    
    # No fallback — raise immediately
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is required but not set.\n"
        "Set it to a Fernet key (use: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    )

ENCRYPTION_KEY = _load_or_generate_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)
```

**Why this pattern:**
- Module-level code executes when `security.py` is imported (which happens at the top of `main.py` line 50).
- `RuntimeError` raises before any route handler is registered or lifespan logic runs.
- Earliest possible failure point ensures no partial initialization or silent degradation.
- Actionable error message provides the Fernet key generation command inline.

### Pattern 2: Entry Point Whitelist Validation

**What:** Inline check of `ep.value` before calling `ep.load()` in both `load_ee_plugins()` and `activate_ee_live()`.

**When to use:** Protecting against untrusted or misconfigured entry point definitions in installed wheels.

**Example:**
```python
# Source: ee/__init__.py load_ee_plugins() (lines 290-315, to be modified)

async def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    """Load EE plugins via importlib.metadata entry_points with whitelist validation."""
    ctx = EEContext()

    try:
        from importlib.metadata import entry_points
        plugins = list(entry_points(group="axiom.ee"))
        if plugins:
            for ep in plugins:
                # Whitelist check: exact value match only
                if ep.value != "ee.plugin:EEPlugin":
                    raise RuntimeError(
                        f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
                    )
                
                # Now safe to load
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                await plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _mount_ce_stubs(app)
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _mount_ce_stubs(app)

    return ctx
```

**Same pattern applied to `activate_ee_live()`** (lines ~274-278 in the existing code):
```python
for ep in plugins:
    # Whitelist validation
    if ep.value != "ee.plugin:EEPlugin":
        raise RuntimeError(
            f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
        )
    
    plugin_cls = ep.load()
    plugin = plugin_cls(app, engine)
    await plugin.register(ctx)
    logger.info("Live-activated EE plugin: %s", ep.name)
```

**Why this pattern:**
- Entry point `value` is a module+class string set at wheel build time (`setup.py` or `pyproject.toml`).
- Hardcoded whitelist `"ee.plugin:EEPlugin"` ensures only authorized plugins load.
- Untrusted values immediately raise `RuntimeError` (consistent with existing wheel manifest verification failures).
- Error message includes actual `ep.value` for debugging misconfigured installations.

### Anti-Patterns to Avoid

- **Accepting `ep.name` check only** — Entry point names can be arbitrary; value is the security boundary.
- **Logging and continuing on untrusted entry point** — Silent degradation defeats the purpose. Startup must fail hard.
- **Auto-generating ENCRYPTION_KEY in prod** — Defeats key rotation and inventory management; requires fresh key per deployment and coordination with operators.
- **File-based ENCRYPTION_KEY fallback** — Perpetuates implicit secrets in volume mounts; forces every deployment to manage file permissions separately.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entry point discovery | Custom module scanner or pip introspection | `importlib.metadata.entry_points()` | Standard library (Python 3.10+); correctly handles package metadata without reimplementing pip's logic. |
| Fernet key generation | Custom random bytes + base64 encoding | `Fernet.generate_key()` | Cryptography library's implementation handles correct entropy, encoding, and format. Rolling your own risks weak keys or decryption failures downstream. |
| Constant-time comparison for secrets | String equality (`==`) | `hmac.compare_digest()` | Prevents timing attacks. Already used in existing code for HMAC verification (security.py line 45). |
| Module-level validation | Conditional imports or try/except in routes | Direct module-level function call | Ensures no routes are registered if prerequisites fail; cleanest error semantics. |

## Common Pitfalls

### Pitfall 1: Entry Point Scope Ambiguity
**What goes wrong:** Confusion between entry point `name` and `value`. A malicious wheel could provide `axiom.ee` group with `name="plugin"` and `value="evil.module:Malware"`.

**Why it happens:** Both attributes exist on `EntryPoint` objects; documentation isn't always clear on which one is the security boundary.

**How to avoid:** Check `ep.value` (the module:class string) not `ep.name`. Document this in comments at the check site.

**Warning signs:** Code that validates only `ep.name == "..."` or assumes entry point names are unique per group (they're not).

### Pitfall 2: ENCRYPTION_KEY Auto-Generate in Production
**What goes wrong:** Operator forgets to set `ENCRYPTION_KEY` env var, auto-generation silently creates a new one per container restart, encrypted data becomes unrecoverable.

**Why it happens:** Current implementation has two fallbacks (env var → file → auto-generate), making it "just work" but hiding configuration errors.

**How to avoid:** Hard fail if `ENCRYPTION_KEY` is absent. Include actionable error message with generation command. Document in deployment guides that `ENCRYPTION_KEY` must be set before first startup.

**Warning signs:** Different timestamps on job records even when no time changes (suggests per-restart key generation); audit trail mysteriously fails to decrypt secrets.

### Pitfall 3: Forgetting Live-Reload Path
**What goes wrong:** Entry point whitelist is added to `load_ee_plugins()` (startup) but not `activate_ee_live()` (licence reload), creating a security gap where a reloaded wheel bypasses validation.

**Why it happens:** Two code paths doing similar things; easy to update one and forget the other.

**How to avoid:** Apply the same check to both `load_ee_plugins()` and `activate_ee_live()` identically. Comment both with "EE-04: Entry point whitelist validation" to link them.

**Warning signs:** Code review finds one check but not the other; tests only cover startup path.

### Pitfall 4: RuntimeError vs HTTPException
**What goes wrong:** Startup check raises `HTTPException`, route handler never executes, FastAPI doesn't know how to handle it.

**Why it happens:** Default pattern in route handlers is `HTTPException` for client errors.

**How to avoid:** Use `RuntimeError` for module-level and initialization failures (security.py, load_ee_plugins). FastAPI catches these at startup and exits cleanly with a server error log.

**Warning signs:** Startup hangs or crashes with unexpected stack trace instead of clean "RuntimeError: ENCRYPTION_KEY..." message.

## Code Examples

Verified patterns from existing codebase and project standards:

### ENCRYPTION_KEY Enforcement — Module-Level RuntimeError

```python
# Source: puppeteer/agent_service/security.py (lines 17–28)

def _load_or_generate_encryption_key() -> bytes:
    """Load ENCRYPTION_KEY from environment variable.
    
    ENCRYPTION_KEY is required for all deployments. No fallbacks.
    
    Raises:
        RuntimeError: if ENCRYPTION_KEY env var is not set.
    """
    if val := os.getenv("ENCRYPTION_KEY"):
        return val.encode()
    
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is required but not set.\n"
        "Set it to a Fernet key (use: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
    )

ENCRYPTION_KEY = _load_or_generate_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)
```

### Entry Point Whitelist Check — Startup Path

```python
# Source: puppeteer/agent_service/ee/__init__.py (lines 290–315)

async def load_ee_plugins(app: Any, engine: Any) -> EEContext:
    """Discover and load EE plugins via importlib.metadata entry_points.
    
    Entry point group: 'axiom.ee'
    Validates ep.value == "ee.plugin:EEPlugin" before loading (EE-04).
    
    If no EE plugin found or validation fails, registers stub routers.
    """
    ctx = EEContext()

    try:
        from importlib.metadata import entry_points
        plugins = list(entry_points(group="axiom.ee"))
        if plugins:
            for ep in plugins:
                # EE-04: Entry point whitelist validation — exact value match only
                if ep.value != "ee.plugin:EEPlugin":
                    raise RuntimeError(
                        f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
                    )
                
                plugin_cls = ep.load()
                plugin = plugin_cls(app, engine)
                await plugin.register(ctx)
                logger.info(f"Loaded EE plugin: {ep.name}")
        else:
            logger.info("No EE plugins found — running in CE mode")
            _mount_ce_stubs(app)
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
        _mount_ce_stubs(app)

    return ctx
```

### Entry Point Whitelist Check — Live-Reload Path

```python
# Source: puppeteer/agent_service/ee/__init__.py (lines ~274–285, in activate_ee_live)

    # Load real EE plugins
    ctx = EEContext()
    try:
        for ep in plugins:
            # EE-04: Entry point whitelist validation — same check as load_ee_plugins()
            if ep.value != "ee.plugin:EEPlugin":
                raise RuntimeError(
                    f"Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'"
                )
            
            plugin_cls = ep.load()
            plugin = plugin_cls(app, engine)
            await plugin.register(ctx)
            logger.info("Live-activated EE plugin: %s", ep.name)
    except Exception as e:
        logger.error("EE plugin registration failed: %s — remounting stubs", e)
        _mount_ce_stubs(app)
        return None

    return ctx
```

## State of the Art

| Old Approach | Current Approach (This Phase) | When Changed | Impact |
|--------------|-------------------------------|--------------|--------|
| Optional ENCRYPTION_KEY with auto-generate fallback | Hard requirement, no fallback | Phase 139 | Prevents silent key rotation on container restart; forces explicit key management in deployments. |
| No entry point validation | Whitelist check on ep.value before load | Phase 139 | Prevents untrusted plugin loading; closes security gap in EE loader. |
| File-based encryption key in `/app/secrets/` | Environment variable only | Phase 139 | Simplifies deployment; key rotation doesn't require volume remounting. |

**Deprecated/outdated:**
- `Path("/app/secrets/encryption.key")` file-based fallback: removed entirely — use env var only.
- Auto-generation of Fernet key: removed entirely — raise RuntimeError if absent.

## Open Questions

1. **CRITICAL_log before raising RuntimeError?**
   - CONTEXT.md grants discretion on whether to add a `logger.critical()` line before raising.
   - Recommendation: Add it. Helps with log-scraping automation and provides explicit error context before crash.
   - Implementation: `logger.critical("ENCRYPTION_KEY not set. See error message above for remediation.")`

2. **Entry point `name` logging for debugging?**
   - Current code logs `ep.name`, which is harmless and useful for operators.
   - Keep it — don't change logging behavior, only add the whitelist check.

3. **Module-level vs import-time exception handling?**
   - ENCRYPTION_KEY check happens at module load (when security.py is imported).
   - Will this be caught and logged gracefully by FastAPI? **Yes** — FastAPI's startup sequence catches `RuntimeError` at module import and logs it before exiting.
   - Verified by existing pattern in main.py (line 50): `from .security import ENCRYPTION_KEY, cipher_suite` — any error here aborts startup.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.12) |
| Config file | pytest.ini not present; defaults apply |
| Quick run command | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py -xvs` |
| Full suite command | `cd puppeteer && pytest tests/ -k "encryption or entry_point" --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-04 | Entry point value validated before load (startup) | unit | `pytest tests/test_ee_manifest.py::test_entry_point_whitelist_startup -xvs` | ❌ Wave 0 |
| EE-04 | Entry point value validated before load (live-reload) | unit | `pytest tests/test_ee_manifest.py::test_entry_point_whitelist_live_reload -xvs` | ❌ Wave 0 |
| EE-04 | Untrusted entry point raises RuntimeError (startup) | unit | `pytest tests/test_ee_manifest.py::test_untrusted_entry_point_startup -xvs` | ❌ Wave 0 |
| EE-04 | Untrusted entry point raises RuntimeError (live-reload) | unit | `pytest tests/test_ee_manifest.py::test_untrusted_entry_point_live_reload -xvs` | ❌ Wave 0 |
| EE-06 | ENCRYPTION_KEY required at module load | unit | `pytest tests/test_encryption_key_enforcement.py::test_encryption_key_required -xvs` | ❌ Wave 0 |
| EE-06 | ENCRYPTION_KEY absent raises RuntimeError | unit | `pytest tests/test_encryption_key_enforcement.py::test_encryption_key_absent_raises -xvs` | ❌ Wave 0 |
| EE-06 | ENCRYPTION_KEY error message includes generation command | unit | `pytest tests/test_encryption_key_enforcement.py::test_encryption_key_error_message -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_encryption_key_enforcement.py tests/test_ee_manifest.py -x`
- **Per wave merge:** `cd puppeteer && pytest tests/ --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_encryption_key_enforcement.py` — covers EE-06 (ENCRYPTION_KEY hard requirement, error messages, module-level import)
- [ ] Update `tests/test_ee_manifest.py` to add entry point whitelist tests (EE-04) — separate test class + fixtures for mocking `entry_points()`
- [ ] `conftest.py` (if needed) — shared fixtures for module reload and env var patching

**Notes:**
- Existing `test_ee_manifest.py` covers manifest verification (EE-01). New tests extend it with entry point validation (EE-04).
- ENCRYPTION_KEY tests need to mock `os.getenv()` and handle module reload carefully (pytest needs `importlib.reload()`).
- Entry point tests need to mock `importlib.metadata.entry_points()` to return fake `EntryPoint` objects with controllable `value` fields.

## Sources

### Primary (HIGH confidence)
- **importlib.metadata** — Python 3.10+ standard library. Verified via `python3 -c "from importlib.metadata import entry_points; help(entry_points)"` — returns entry point objects with `.value`, `.name`, and `.load()` methods.
- **cryptography.fernet** — Production dependency in `requirements.txt`. Verified via existing usage in `security.py` (line 29, line 51–78). `Fernet.generate_key()` returns bytes suitable for ENCRYPTION_KEY initialization.
- **Existing codebase patterns** — RuntimeError usage for security failures confirmed in `ee/__init__.py` (line 96–173, wheel manifest verification). Module-level imports confirmed in `main.py` (line 50–54).

### Secondary (MEDIUM confidence)
- **Phase 138 completion** — HMAC boot log implementation added `_compute_boot_hmac()` helpers and confirmed ENCRYPTION_KEY usage throughout. Documented in STATE.md confirming Phase 138 Plan 01 complete (2026-04-12).
- **Phase 137 completion** — EE wheel manifest verification implemented `_verify_wheel_manifest()` with RuntimeError on failure. Existing test file `test_ee_manifest.py` demonstrates full test pattern for EE module checks.

### Tertiary (implementation specifics)
- **CONTEXT.md (Phase 139)** — User decisions on exact error message format, ENCRYPTION_KEY requirement scope, and entry point value check (`ep.value == "ee.plugin:EEPlugin"`).
- **REQUIREMENTS.md** — EE-04 (entry point validation) and EE-06 (ENCRYPTION_KEY hard requirement) confirmed as Phase 139 scope.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — importlib.metadata is stdlib; cryptography already a production dependency with known API.
- Architecture: **HIGH** — Module-level validation pattern is identical to existing wheel manifest verification; two code paths (load_ee_plugins, activate_ee_live) are both visible and tested in existing codebase.
- Pitfalls: **HIGH** — Pitfall #3 (forgetting live-reload path) identified by explicit code inspection of both paths; Pitfall #2 (ENCRYPTION_KEY auto-generate) confirmed by reading current implementation.
- Test structure: **MEDIUM** — Pattern matches existing `test_ee_manifest.py`, but new tests will require mocking `entry_points()` and module reload (standard pytest patterns but not yet present in this test suite).

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (30 days; standard stack is stable, Python 3.10+ importlib.metadata is frozen in stdlib)

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **ENCRYPTION_KEY enforcement:** Always required — CE mode and EE mode both require it. No production/dev distinction. No auto-generate fallback; no file-based fallback.
- **Entry point whitelist:** Exact value check only: `ep.value == "ee.plugin:EEPlugin"` — single hardcoded string. No additional `ep.name` check. Untrusted entry point raises `RuntimeError`.
- **Error messages:** Include actual `ep.value` for debugging. ENCRYPTION_KEY error includes Fernet key generation one-liner.
- **Check placement:** Inline in both `load_ee_plugins()` and `activate_ee_live()`, immediately before `ep.load()`.

### Claude's Discretion
- **CRITICAL log line:** Optional to add `logger.critical()` before raising RuntimeError (helpful for log-scraping).
- **Test structure:** How to organize entry point and encryption key tests (separate files vs. combined).
- **Refactoring scope:** Exact placement of RuntimeError within `_load_or_generate_encryption_key()` (can refactor function body freely).

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EE-04 | Importlib entry point loader validates `ep.value == "ee.plugin:EEPlugin"` before loading; untrusted entry points raise `RuntimeError` | Entry point whitelist pattern documented with examples for both startup and live-reload paths. importlib.metadata API verified. Error message format specified in CONTEXT.md. |
| EE-06 | EE startup enforces `ENCRYPTION_KEY` presence with hard `RuntimeError` if absent (no dev-fallback in production) | ENCRYPTION_KEY hard requirement pattern documented with module-level check. Error message includes Fernet key generation one-liner as specified. Removal of file-based and auto-generate fallbacks confirmed. |

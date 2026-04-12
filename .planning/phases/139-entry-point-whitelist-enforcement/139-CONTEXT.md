# Phase 139: Entry Point Whitelist & Enforcement - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the EE plugin loader and encryption key bootstrapping: validate importlib entry points against a strict whitelist before loading, and enforce `ENCRYPTION_KEY` presence as a hard startup requirement with no silent fallback.

Creating or distributing EE wheels, licence validation logic, and HMAC boot log are separate phases.

</domain>

<decisions>
## Implementation Decisions

### ENCRYPTION_KEY enforcement
- Always required — CE mode and EE mode both require it. No production/dev distinction.
- Remove the auto-generate fallback entirely from `_load_or_generate_encryption_key()`. File-based fallback (`/app/secrets/encryption.key`) is also removed.
- If `ENCRYPTION_KEY` env var is absent, raise `RuntimeError` with a short actionable message including the Fernet key generation one-liner:
  ```
  ENCRYPTION_KEY environment variable is required but not set.
  Set it to a Fernet key (use: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
  ```
- Check lives in `security.py` at module load time (`_load_or_generate_encryption_key()`), so it fails at import — earliest possible point, before any route is registered.

### Entry point whitelist
- Exact value check only: `ep.value == "ee.plugin:EEPlugin"` — single hardcoded string.
- No additional `ep.name` check.
- Untrusted entry point (wrong `ep.value`) → hard fail with `RuntimeError`. Startup is prevented.
- Error message includes the actual `ep.value` for debugging:
  ```
  Untrusted axiom.ee entry point: '{ep.value}' — expected 'ee.plugin:EEPlugin'
  ```
- Check is inline in both `load_ee_plugins()` and `activate_ee_live()`, immediately before `ep.load()`.

### Live-reload path (`activate_ee_live`)
- Same whitelist check applies — a hot-reload attempt with an untrusted entry point fails identically to startup.
- Consistent enforcement across both code paths.

### Claude's Discretion
- Exact placement of the RuntimeError within `_load_or_generate_encryption_key()` (can refactor the function body freely)
- Whether to add a CRITICAL log line before raising (helpful for log-scraping but optional)
- Test structure for the new enforcement paths

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py:_load_or_generate_encryption_key()` (lines 17–26): function to modify — remove file-based fallback and auto-generate, replace with `RuntimeError`
- `ee/__init__.py:load_ee_plugins()`: add `ep.value` check before `ep.load()` in the `for ep in plugins` loop
- `ee/__init__.py:activate_ee_live()`: same check in the `for ep in plugins` loop (~line 230)

### Established Patterns
- `RuntimeError` is already used for security violations in `ee/__init__.py` (wheel manifest verification raises `RuntimeError` on failure) — consistent to use the same exception type
- `logger.error()` before raising is the existing pattern in `activate_ee_live()` error handlers

### Integration Points
- `security.py` is imported at the top of `main.py` — a module-level `RuntimeError` will abort startup before FastAPI even initialises
- `load_ee_plugins()` is called from the lifespan startup in `main.py:113`
- `activate_ee_live()` is called from the licence reload endpoint in `main.py:~2244`

</code_context>

<specifics>
## Specific Ideas

- No specific references beyond the requirement wording — standard enforcement pattern.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 139-entry-point-whitelist-enforcement*
*Context gathered: 2026-04-12*

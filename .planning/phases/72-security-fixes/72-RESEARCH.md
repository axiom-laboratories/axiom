# Phase 72: Security Fixes - Research

**Researched:** 2026-03-26
**Domain:** Python/FastAPI backend security hardening (XSS, path traversal, ReDoS, API key removal, HTTP headers)
**Confidence:** HIGH

## Summary

Phase 72 applies six targeted patches to close all CodeQL error-severity and warning-severity alerts in the GitHub Security tab. Every fix is a surgical change to existing code — no new architecture, no frontend changes, no new dependencies beyond Python stdlib (`html`, `pathlib`).

The codebase is well-understood: all six vulnerabilities have been traced to exact locations in `security.py`, `main.py`, and `vault_service.py`. The `API_KEY` removal (SEC-05) is the most structurally significant because `API_KEY` is imported and used by `node.py` in the puppets side too, but the server-side verification can be safely dropped since node-facing routes already use `verify_node_secret` (mTLS + secret hash). The header sent by nodes becomes an ignored extra header rather than a verified one, which is fine — the actual security comes from the cert-bound `verify_node_secret` chain.

Three patterns cover all six fixes: (1) `html.escape()` for XSS, (2) `Path.resolve() + is_relative_to()` via a shared helper for traversal, and (3) linear bounded regex for ReDoS. The CSV nosniff header is a one-liner. All fixes are verifiable with automated tests.

**Primary recommendation:** Implement all six fixes in a single wave (one PLAN.md), ordered so the shared `validate_path_within()` helper is written first, then all consumers added together.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**API_KEY removal (SEC-05)**
- Fully remove `API_KEY` env var, the `try/except` crash block, and the `verify_api_key` function from `security.py`
- Remove `verify_api_key` from all three node-facing routes: `/work/pull`, `/heartbeat`, `/jobs/{guid}/result`
- Researcher must verify service principals do not depend on the global `API_KEY` before planning full deletion
- If `API_KEY` is still present in an operator's env at startup, ignore it silently — no deprecation log

**Path traversal fix pattern (SEC-02 + SEC-03)**
- Write a shared helper `validate_path_within(base: Path, candidate: Path) -> Path` in `security.py`
- Helper raises HTTP 400 if `candidate.resolve()` is not relative to `base.resolve()`
- Call the helper from `vault_service.py` (artifact store/delete) and all flagged locations in `main.py`
- Use GitHub Security tab to find the actual current line numbers for SEC-03 alerts (STATE.md notes they have drifted from the original todo)

**Regex safety review (SEC-04)**
- Email regex in `mask_pii()` is the CodeQL-flagged pattern — rewrite to a linear bounded form (no catastrophic backtracking on pathological email-like strings)
- Also review the SSN regex (`\d{3}-\d{2}-\d{4}`) while in the function — confirm it is linear or fix if not
- Only change patterns, not the overall mask_pii() recursion logic

**Test coverage**
- Claude's discretion on which fixes warrant automated tests
- Priority signals: fixes that are hard to visually verify (ReDoS timing, nosniff header) and fixes with a clear exploit scenario (XSS, path traversal) benefit most from tests

### Claude's Discretion

- Which fixes get automated tests (all six have clear exploit scenarios; recommend covering all)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-01 | `user_code` query param HTML-escaped before rendering in `/auth/device/approve` | XSS fix via `html.escape()` in inline f-string HTML — 4 injection points identified at lines 601, 603, 608 (GET handler) |
| SEC-02 | `vault_service.py` artifact paths guarded against directory traversal | `VaultService.store_artifact()` uses `uuid4()` as filename — UUID input is trusted; `delete_artifact()` calls `get_artifact_path()` with a DB-retrieved `artifact_id` string — add `validate_path_within()` guard before file I/O |
| SEC-03 | `main.py` installer/docs paths guarded against directory traversal | Live CodeQL alerts must be checked for current line numbers; research identified `/api/docs/{filename}` at line 1806 (already has `os.path.abspath` + `startswith` guard — CodeQL may flag this as insufficiently strict), `/api/installer` at lines 1761–1762 (no guard), docs listing at line 1786 (list traversal) |
| SEC-04 | `mask_pii()` email regex rewritten to linear bounded pattern | Current pattern `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` has catastrophic backtracking risk on long strings with embedded `@` — rewrite with anchored local-part length limit |
| SEC-05 | Remove `API_KEY` crash + `verify_api_key` from all node-facing routes | Full deletion plan confirmed safe: service principals use `mop_`-prefixed `UserApiKey` table (EE-only, completely separate path); `verify_api_key` is only dependency on global `API_KEY`; node.py sends the header but server simply won't check it |
| SEC-06 | CSV job export endpoint adds `X-Content-Type-Options: nosniff` header | `StreamingResponse` at line 873 has a `headers={}` dict — add key to that dict |
</phase_requirements>

---

## Standard Stack

### Core (all stdlib / already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `html` (stdlib) | Python 3.x | `html.escape()` for XSS prevention | Zero-dep, correct, recommended by OWASP |
| `pathlib.Path` (stdlib) | Python 3.x | `Path.resolve()` + `Path.is_relative_to()` | PEP 428 path API; `is_relative_to()` available since Python 3.9 |
| `re` (stdlib) | Python 3.x | Regex replacement in `mask_pii()` | Already imported in `security.py` |
| `fastapi.responses.StreamingResponse` | Already installed | CSV streaming | Already used at line 873 |

### No new dependencies required.

---

## Architecture Patterns

### File-by-File Change Map

```
puppeteer/agent_service/
├── security.py          # SEC-01 html import, SEC-02/03 validate_path_within(), SEC-04 regex, SEC-05 API_KEY removal
├── main.py              # SEC-01 html.escape() calls, SEC-03 path guard calls, SEC-05 import cleanup + route param removal, SEC-06 nosniff header
└── services/
    └── vault_service.py # SEC-02 validate_path_within() calls in store_artifact() and delete_artifact()

puppets/environment_service/
└── node.py              # SEC-05: API_KEY header still sent (harmless), no server-side check to remove

puppeteer/
├── compose.server.yaml  # SEC-05: remove API_KEY env var line (optional cleanup, not a runtime requirement)
└── .env                 # SEC-05: remove API_KEY line (optional cleanup)
```

### Pattern 1: HTML Escaping (SEC-01)

**What:** Wrap every `{user_code}` interpolation in the GET handler's inline HTML f-string with `html.escape()`.

**When to use:** Any user-controlled value inserted into raw HTML response.

**Injection points in `device_approve_page()` (GET /auth/device/approve):**
- Line 601: `{user_code or "(no code provided)"}` — inside `<div>` tag
- Line 603: `value="{user_code}"` — hidden input for approve form
- Line 608: `value="{user_code}"` — hidden input for deny form

**Correct fix:**
```python
# Add at top of main.py imports
import html as _html

# In device_approve_page():
escaped_code = _html.escape(user_code or "")
# Then replace all {user_code} occurrences with {escaped_code}
# and {user_code or "(no code provided)"} with {escaped_code or "(no code provided)"}
```

Source: Python stdlib `html.escape()` — escapes `<`, `>`, `&`, `"`, `'`.

**Note:** The POST handlers (`device_approve_submit`, `device_deny_submit`) read `user_code` as `Form(...)` and use it only as a dict key lookup — they do NOT reflect it back into HTML output, so no escaping needed there.

### Pattern 2: Path Traversal Guard (SEC-02 + SEC-03)

**What:** A shared helper that resolves both paths and checks containment using `Path.is_relative_to()`.

**Helper location:** `security.py` (alongside other validation helpers).

```python
# Source: Python 3.9+ pathlib — Path.is_relative_to() is O(1) string comparison after resolve()
from pathlib import Path
from fastapi import HTTPException

def validate_path_within(base: Path, candidate: Path) -> Path:
    """Resolve both paths and raise HTTP 400 if candidate escapes base."""
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return resolved_candidate
```

**SEC-02 usage in `vault_service.py`:**

`store_artifact()` uses `uuid4()` as the filename — a UUID cannot contain `../` so this is low-risk, but the CodeQL alert fires on the pattern. Add the guard for defense-in-depth:
```python
from pathlib import Path
from ..security import validate_path_within

# In store_artifact():
file_path = validate_path_within(Path(VAULT_DIR), Path(VAULT_DIR) / artifact_id)
```

`delete_artifact()` calls `get_artifact_path(artifact_id)` where `artifact_id` comes from a DB query on `artifact.id` — same UUID-safe pattern, same treatment:
```python
# In delete_artifact():
safe_path = validate_path_within(Path(VAULT_DIR), Path(VaultService.get_artifact_path(artifact_id)))
if safe_path.exists():
    safe_path.unlink()
```

**SEC-03 usage in `main.py`:**

The `/api/docs/{filename}` handler (line 1806) already has `os.path.abspath + startswith` — CodeQL may flag `startswith` as not equivalent to `is_relative_to()` (edge case: `/safe_dir_extended/` passes a startswith check for `/safe_dir/`). Replace with the helper:
```python
from pathlib import Path
from .security import validate_path_within

# In get_doc_content():
safe_path = validate_path_within(Path(docs_dir), Path(docs_dir) / filename)
# Then use safe_path instead of file_path
```

The `/api/installer` handler (lines 1761-1762): uses `os.path.join(base_dir, "installer", "install_node.ps1")` with a hardcoded filename — not user-controlled, so CodeQL likely does NOT flag this. Verify against live alerts before modifying.

### Pattern 3: ReDoS-Safe Email Regex (SEC-04)

**What:** Replace the catastrophic backtracking email pattern with a linearly bounded equivalent.

**Current pattern (vulnerable):**
```python
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
```

**Why it backtracks:** The `[a-zA-Z0-9-.]+` in the domain part has no upper bound. A string like `a@` followed by 50+ repeated chars that don't terminate causes O(2^n) backtracking in CPython's `re` engine.

**Safe replacement (linearly bounded, no nested quantifiers):**
```python
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]{1,64}@[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+'
```

This is anchored by RFC 5321 limits: local part max 64 chars, each domain label max 63 chars. No nested quantifiers — linear scan guaranteed.

**SSN regex `\d{3}-\d{2}-\d{4}` is already linear** — fixed-width character classes with no nesting or alternation. No change needed.

### Pattern 4: CSV nosniff Header (SEC-06)

**What:** Add `X-Content-Type-Options: nosniff` to the `StreamingResponse` headers dict.

**Current code (line 873-877):**
```python
return StreamingResponse(
    generate(),
    media_type="text/csv",
    headers={"Content-Disposition": "attachment; filename=jobs-export.csv"},
)
```

**Fix:**
```python
return StreamingResponse(
    generate(),
    media_type="text/csv",
    headers={
        "Content-Disposition": "attachment; filename=jobs-export.csv",
        "X-Content-Type-Options": "nosniff",
    },
)
```

### Pattern 5: API_KEY Removal (SEC-05)

**Deletion checklist verified:**

1. **`security.py`**: Remove lines 16-21 (`try: API_KEY = os.environ["API_KEY"]` + `sys.exit(1)` block), remove `verify_api_key()` function (lines 104-108), remove `API_KEY` from module-level exports.

2. **`main.py` line 43-44**: Remove `verify_api_key` and `API_KEY` from the `from .security import (...)` tuple.

3. **`main.py` lines 1225, 1234, 1241**: Remove `api_key: str = Depends(verify_api_key)` parameter from `pull_work()`, `receive_heartbeat()`, `report_result()`.

4. **`test_security.py` line 1**: `from agent_service.security import ... API_KEY` — remove `API_KEY` from this import, remove any test that asserts on `API_KEY` value.

5. **`test_openapi_export.py` line 23**: `"API_KEY": "dummy-build-key"` in `DUMMY_ENV` — remove after confirming export script no longer crashes without it.

6. **`node.py`**: Keep `API_KEY = os.getenv("API_KEY", "master-secret-key")` and the three header inclusions (`API_KEY_NAME: API_KEY`) — the server will simply ignore the header. The context decision says no deprecation log, so leave node.py untouched.

7. **`compose.server.yaml` and `.env`**: Remove `API_KEY` env var lines as cleanup — not functionally required but removes the footgun for operators seeing it.

**Service principal verification (confirmed safe):**
- `UserApiKey` is managed in EE `auth_ext_router.py` — generates `mop_` prefixed keys, stored in `UserApiKey` table
- `ServicePrincipal` uses `mop_sp_` prefixed secrets, authenticates via JWT after client-credentials exchange
- Neither uses `verify_api_key()` or the global `API_KEY` constant
- Node-facing routes use `verify_node_secret` (cert + secret hash) as their identity mechanism — `verify_api_key` was an additional redundant layer that added the crash-on-missing-env bug

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping | Custom replace/regex | `html.escape()` from stdlib | Handles all 5 HTML special chars correctly; stdlib |
| Path containment check | Manual `os.path.abspath` + string `startswith` | `Path.resolve() + Path.is_relative_to()` | `startswith` has the `/safe/` vs `/safe_extended/` false-positive edge case; `is_relative_to()` is unambiguous |
| Linear email regex | Complex lookahead/lookbehind | Simple bounded quantifiers `{1,64}` | Bounds eliminate backtracking; lookahead not needed |

---

## Common Pitfalls

### Pitfall 1: Escaping Only the Display Context (SEC-01)
**What goes wrong:** Developer escapes the `<div>` display value but forgets the two hidden `<input value="...">` form fields — the hidden inputs can still carry XSS payload via form submit.
**Why it happens:** The visual code review focuses on what's visible on screen.
**How to avoid:** Search for ALL `{user_code}` occurrences in the f-string. There are 3 in the GET handler: lines 601, 603, 608.
**Warning signs:** Test that checks only the display `<div>`, not the form inputs.

### Pitfall 2: `is_relative_to()` Python Version Gate
**What goes wrong:** `Path.is_relative_to()` was added in Python 3.9 — older environments raise `AttributeError`.
**Why it happens:** The Docker image uses a recent Python, but local dev may differ.
**How to avoid:** Check the Dockerfile base image Python version. The project uses `python:3.11-slim` in `compose.server.yaml` — 3.11 is fine. Add a comment noting the 3.9+ requirement.

### Pitfall 3: `API_KEY` Import Still Present in Test File
**What goes wrong:** `test_security.py` imports `API_KEY` from `security` on line 1. After deletion, the test suite crashes at import time before any test runs.
**Why it happens:** The import will fail with `ImportError` rather than `AttributeError`.
**How to avoid:** Update `test_security.py` import line as part of the SEC-05 task.

### Pitfall 4: `test_openapi_export.py` Still Passes `API_KEY` in `DUMMY_ENV`
**What goes wrong:** After `security.py` no longer reads `API_KEY`, the test still sets it — harmless but misleading. More importantly, if the test is run on a system that still has `API_KEY` in the real environment, it masked the pre-existing crash.
**How to avoid:** Remove `API_KEY` from `DUMMY_ENV` in `test_openapi_export.py` and verify the export script still runs cleanly.

### Pitfall 5: ReDoS regex change breaks existing `test_pii.py` tests
**What goes wrong:** If the new email regex is too restrictive (e.g., excludes `.co.uk` or subdomains), the existing masking test for `test@example.com` may still pass but edge cases fail silently.
**How to avoid:** The pattern `[a-zA-Z0-9_.+-]{1,64}@[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+` matches `test@example.com` (single dot domain) because the domain part is `example.com` = `[label].[label]`. Run the existing three `test_pii.py` tests after the change.

### Pitfall 6: `validate_path_within()` in `vault_service.py` — `Path` import
**What goes wrong:** `vault_service.py` currently only imports `os` for path operations. Adding `validate_path_within` requires importing both `Path` from `pathlib` and the helper from `..security`. The relative import `..security` works because `vault_service.py` is in `services/`.
**How to avoid:** Add `from pathlib import Path` and `from ..security import validate_path_within` to the imports at the top of `vault_service.py`.

---

## Code Examples

Verified patterns from stdlib documentation and existing codebase patterns:

### SEC-01: html.escape() usage
```python
# Source: Python 3.x stdlib html module
import html as _html

escaped = _html.escape(user_code or "")
# _html.escape converts: & -> &amp;, < -> &lt;, > -> &gt;, " -> &quot;, ' -> &#x27;
# quote=True (default) also escapes double-quotes — critical for attribute values
```

### SEC-02/03: validate_path_within helper
```python
# Source: Python 3.9+ pathlib — Path.is_relative_to()
from pathlib import Path
from fastapi import HTTPException

def validate_path_within(base: Path, candidate: Path) -> Path:
    """Resolve both paths and raise HTTP 400 if candidate escapes base.
    Requires Python 3.9+ (is_relative_to added in 3.9).
    """
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return resolved_candidate
```

### SEC-04: Linear email regex
```python
# Bounded quantifiers prevent catastrophic backtracking
# RFC 5321: local-part max 64, label max 63
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]{1,64}@[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+'
# SSN regex is already linear — no change needed:
SSN_REGEX = r'\d{3}-\d{2}-\d{4}'
```

### SEC-05: Import cleanup in main.py
```python
# BEFORE (line 43-44):
from .security import (
    encrypt_secrets, decrypt_secrets, mask_secrets, verify_api_key,
    verify_client_cert, API_KEY, ENCRYPTION_KEY, cipher_suite, oauth2_scheme,

# AFTER:
from .security import (
    encrypt_secrets, decrypt_secrets, mask_secrets,
    verify_client_cert, ENCRYPTION_KEY, cipher_suite, oauth2_scheme,
```

### SEC-06: StreamingResponse with nosniff header
```python
# Existing pattern from main.py line 873 — add one key to headers dict
return StreamingResponse(
    generate(),
    media_type="text/csv",
    headers={
        "Content-Disposition": "attachment; filename=jobs-export.csv",
        "X-Content-Type-Options": "nosniff",
    },
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.path.abspath() + startswith()` for path guard | `Path.resolve() + is_relative_to()` | Python 3.9 (2020) | Eliminates false-positive edge case where `/safe_extended/` passes a `/safe/` startswith check |
| Unbounded `+` quantifiers in email regex | Bounded `{1,N}` quantifiers | CodeQL GHSA-ReDoS patterns | Linear scan time regardless of input |
| `try: API_KEY = os.environ["KEY"]` crash pattern | Graceful optional env vars with `os.getenv()` | FastAPI best practice | Operator DX improvement; nodes never had API access gate anyway |

---

## Open Questions

1. **SEC-03 exact line numbers**
   - What we know: STATE.md explicitly notes that the original todo referenced lines 2457/2461 but the file is currently 2152 lines, so those numbers are stale.
   - What's unclear: Which specific route(s) CodeQL currently flags in `main.py`. Research found `/api/installer` (line 1762, hardcoded filename, unlikely to be flagged) and `/api/docs/{filename}` (line 1806, has partial guard that CodeQL may still flag).
   - Recommendation: Check GitHub Security tab live before implementing SEC-03. If the alert points to `/api/docs/{filename}` line 1806, replace `startswith` guard with `validate_path_within()`. If it points elsewhere, fix that location instead. Do not guess.

2. **node.py API_KEY header — silent or noisy after removal**
   - What we know: Server will no longer check the `X-API-KEY` header; node.py still sends it.
   - What's unclear: Whether any middleware or logging captures unexpected headers and creates noise.
   - Recommendation: No server-side change needed. The context decision says node.py is left untouched — the sent-but-ignored header is harmless.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + anyio (async) |
| Config file | `puppeteer/pyproject.toml` (pytest settings) |
| Quick run command | `cd puppeteer && pytest agent_service/tests/test_security.py agent_service/tests/test_pii.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | `user_code=<script>alert(1)</script>` in GET /auth/device/approve returns HTML with escaped payload | unit (sync HTTP) | `cd puppeteer && pytest agent_service/tests/test_device_xss.py -x` | ❌ Wave 0 |
| SEC-02 | `artifact_id=../../../etc/passwd` in vault delete raises HTTP 400 | unit (mock filesystem) | `cd puppeteer && pytest agent_service/tests/test_vault_traversal.py -x` | ❌ Wave 0 |
| SEC-03 | Path traversal in `/api/docs/{filename}` returns HTTP 400 for `../../../etc/passwd` | unit (ASGI client) | `cd puppeteer && pytest agent_service/tests/test_docs_traversal.py -x` | ❌ Wave 0 |
| SEC-04 | `mask_pii()` on a 10,000-char string with embedded `@` completes in < 1 second | unit (timing) | `cd puppeteer && pytest agent_service/tests/test_pii.py -x` | ✅ (add timing test) |
| SEC-05 | Server boots cleanly with no `API_KEY` in environment | unit (import test) | `cd puppeteer && pytest agent_service/tests/test_security.py -x` | ✅ (update existing) |
| SEC-06 | GET /api/jobs/export response includes `X-Content-Type-Options: nosniff` | unit (ASGI client) | `cd puppeteer && pytest agent_service/tests/test_csv_nosniff.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest agent_service/tests/test_security.py agent_service/tests/test_pii.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/agent_service/tests/test_device_xss.py` — covers SEC-01 (HTML escaping in GET handler)
- [ ] `puppeteer/agent_service/tests/test_vault_traversal.py` — covers SEC-02 (vault path guard)
- [ ] `puppeteer/agent_service/tests/test_docs_traversal.py` — covers SEC-03 (docs path guard, confirm alert location first)
- [ ] `puppeteer/agent_service/tests/test_csv_nosniff.py` — covers SEC-06 (nosniff header)
- [ ] Add ReDoS timing test to existing `puppeteer/agent_service/tests/test_pii.py` — covers SEC-04
- [ ] Update `puppeteer/agent_service/tests/test_security.py` — remove `API_KEY` import, update assertions — covers SEC-05

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `puppeteer/agent_service/security.py` (all 147 lines) — current `API_KEY` crash, `mask_pii()`, `verify_api_key()` confirmed
- Direct code inspection of `puppeteer/agent_service/main.py` (2152 lines) — device approve HTML at lines 575-628, CSV StreamingResponse at line 873, installer routes at 1759-1769, docs routes at 1771-1815, node route params at 1225/1234/1241 confirmed
- Direct code inspection of `puppeteer/agent_service/services/vault_service.py` — `VAULT_DIR`, `store_artifact()`, `delete_artifact()`, `get_artifact_path()` confirmed
- Direct code inspection of `puppeteer/agent_service/deps.py` — `require_auth` is JWT-only alias; no `API_KEY` dependency confirmed
- Direct code inspection of `puppeteer/agent_service/ee/routers/auth_ext_router.py` — `UserApiKey`/`ServicePrincipal` use `mop_` prefixed tokens, completely separate from global `API_KEY` confirmed
- Direct code inspection of `puppets/environment_service/node.py` lines 64-66, 329, 504, 708 — node sends `X-API-KEY` header to all three endpoints
- Python 3.x stdlib: `html.escape()` signature and behavior
- Python 3.9+ stdlib: `pathlib.Path.is_relative_to()` availability

### Secondary (MEDIUM confidence)
- CodeQL ReDoS pattern analysis: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` — the `[a-zA-Z0-9-.]+` terminal class can catastrophically backtrack when the engine tries multiple splits on a pathological string. Bounded quantifier replacement is the standard CodeQL-recommended fix.
- `Path.startswith()` vs `Path.is_relative_to()` edge case (`/safe_extended/` passing `/safe/` startswith check) — documented Python pathlib behavior; `is_relative_to()` resolves this.

### Tertiary (LOW confidence)
- Exact SEC-03 CodeQL alert locations: STATE.md notes line numbers have drifted and the GitHub Security tab must be checked live before implementing. Research inference (that `/api/docs/{filename}` is the primary flagged location) is based on code pattern analysis but is not confirmed against the live alert.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, all already installed, no new dependencies
- Architecture: HIGH — all six fixes traced to exact file locations with code inspection
- Pitfalls: HIGH — based on direct code review; SEC-03 location requires live alert verification
- Test infrastructure: HIGH — existing pytest + anyio patterns confirmed from conftest.py and test files

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (stable stdlib patterns; no expiry risk)

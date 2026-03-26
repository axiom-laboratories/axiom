# Stack Research

**Domain:** Security hardening (CodeQL fixes) + EE licence key system with air-gap support
**Researched:** 2026-03-26
**Confidence:** HIGH

## Context: What Already Exists (Do Not Re-research)

The following are validated and in-production. This research covers NEW requirements only.

| Component | Version | Status |
|-----------|---------|--------|
| `cryptography` | unpinned (latest) | In `requirements.txt` — provides Ed25519 signing already used for job signing and EE `_parse_licence()` |
| `pathlib` | stdlib | Available; not yet used for path sanitisation in `main.py` or `vault_service.py` |
| `uuid` | stdlib | Available; used for `artifact_id` generation, not yet used for input validation |
| `re` | stdlib | Used in `security.py` for PII masking — the ReDoS-vulnerable `EMAIL_REGEX` lives here |
| `hashlib` | stdlib | Available; used in HMAC helpers |
| `time` | stdlib | Available |
| `json` | stdlib | Available |
| EE `_parse_licence()` | private EE repo | Full Ed25519 verify + expiry check already implemented in `ee/plugin.py`; CE `main.py` lifespan does only base64-decode + clock expiry (no sig verify) |

---

## Recommended Stack Additions

### No New Libraries Required

**All 6 CodeQL alerts and the licence air-gap enforcement can be fixed using Python's stdlib and the `cryptography` library already in `requirements.txt`.** Zero new pip dependencies.

This is the correct outcome for this milestone: every fix is a code pattern change, not a library adoption decision. Adding libraries to close security alerts would introduce transitive dependency risk.

---

## Fix Patterns: CodeQL Alerts

### Alert 76 — ReDoS (`security.py:79`) — WARNING

**Root cause:** `EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'`

The trailing `[a-zA-Z0-9-.]+` with unbounded repetition over a character class containing `-` creates polynomial backtracking on adversarial inputs like `a@a.` followed by 50+ characters that partially match.

**Fix pattern — length guard + linearised regex (stdlib `re`, no new library):**

```python
def mask_pii(data: Any) -> Any:
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]{1,64}@[a-zA-Z0-9-]{1,253}\.[a-zA-Z]{2,24}'
    SSN_REGEX = r'\d{3}-\d{2}-\d{4}'
    ...
```

Key changes:
- `{1,64}` caps the local part (RFC 5321 limit is 64 chars)
- `{1,253}` caps the domain label (RFC 1035 limit is 253 chars)
- `[a-zA-Z]{2,24}` for the TLD (no `-` in TLD, caps repetition) — removes the catastrophic nested alternation
- Input length pre-check: if `isinstance(data, str) and len(data) > 10000: return data` before regex — belt-and-suspenders for high-volume audit log data

**Why not the `regex` PyPI package:** The `regex` module uses an RE2-based engine and is immune to ReDoS by design. However, the `cryptography` library is already the security-critical dependency here and `regex` adds ~2MB to the image. The linear regex rewrite above achieves the same result with zero new dependencies. Use `regex` only if pattern requirements become too complex for safe re-writing.

---

### Alert 84 — Reflected XSS (`main.py:875`) — ERROR

**Root cause:** CodeQL traces user-controlled job fields (name, node_id, target_tags, etc.) into the `StreamingResponse` generator. Despite `media_type="text/csv"` and `Content-Disposition: attachment`, CodeQL's taint analysis considers any user data flowing into a response body as a potential XSS sink.

**The real risk here is CSV injection (formula injection)**, not browser XSS. A job name of `=CMD|'/C calc'!A1` gets written to the CSV and executed when a victim opens the file in Excel.

**Fix pattern — csv.writer quoting (stdlib `csv`, already imported):**

```python
writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
writer.writerow([
    str(job.get("name", "")),          # str() forces type; QUOTE_ALL escapes
    str(job.get("status", "")),
    ...
])
```

`csv.QUOTE_ALL` wraps every field in double quotes, which breaks formula injection (`="..." `is still a formula, but `"=CMD..."` is a literal string in most spreadsheet parsers). For strict protection, prefix fields starting with `=`, `+`, `-`, `@` with a single-quote: `f"'{val}"` if val starts with formula chars.

CodeQL's `py/reflective-xss` is satisfied when user data does not flow directly into an `HTMLResponse` or `Response(media_type="text/html")`. The `StreamingResponse(media_type="text/csv")` path should not trigger it — if the alert persists after the CSV quoting fix, the alert can be dismissed as a false positive with the justification that the response is typed as a file attachment, not HTML.

**Why not `bleach`:** `bleach` is an HTML sanitizer. CSV is not HTML. Using bleach here would be the wrong tool and adds a dependency.

---

### Alerts 80, 81 — Path Injection (`main.py:2457, 2461`) — ERROR

**Note:** The CodeQL alert line numbers (2457, 2461) reference a prior commit snapshot. In the current file, the relevant code is the `get_doc_content` endpoint at lines ~1795–1815.

**Root cause:** `os.path.abspath()` does not resolve symlinks, so a symlink inside the `docs/` directory could escape the base. CodeQL does not recognise `abspath + startswith` as a sufficient sanitiser.

**Fix pattern — `pathlib` with `resolve()` + `is_relative_to()` (stdlib, Python 3.9+):**

```python
from pathlib import Path

@app.get("/api/docs/{filename}")
async def get_doc_content(filename: str, current_user: User = Depends(require_auth)):
    safe_name = Path(filename).name          # strips any directory components
    base = Path(__file__).parent.parent / "docs"
    resolved_base = base.resolve()
    resolved_path = (resolved_base / safe_name).resolve()
    if not resolved_path.is_relative_to(resolved_base):
        raise HTTPException(status_code=403, detail="Invalid path")
    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": resolved_path.read_text()}
```

`Path.resolve()` follows symlinks (unlike `abspath`). `is_relative_to()` is available from Python 3.9. The project runs Python 3.11+ (confirmed by Cython wheel matrix in PROJECT.md). CodeQL recognises `resolve()` as a path normalisation step.

**Why `pathlib` over `os.path`:** CodeQL's Python path injection sanitiser (`Path::PathNormalization::Range`) explicitly recognises `pathlib.Path.resolve()` as a normalisation method. `os.path.abspath` does not resolve symlinks and has historically not been recognised as a sufficient sanitiser in CodeQL's Python query library.

---

### Alerts 82, 83 — Path Injection (`vault_service.py:71, 72`) — ERROR

**Root cause:** `artifact_id` originates from a user-supplied URL parameter (even though it's looked up in the DB first, CodeQL's taint analysis does not model the DB as a sanitiser). It's used to construct `os.path.join(VAULT_DIR, artifact_id)` without validation.

**Fix pattern — UUID validation as sanitiser (stdlib `uuid`):**

```python
import uuid as _uuid
from pathlib import Path

VAULT_BASE = Path("/app/vault")

@staticmethod
def get_artifact_path(artifact_id: str) -> Path:
    try:
        _uuid.UUID(artifact_id)             # raises ValueError if not a valid UUID
    except ValueError:
        raise ValueError(f"Invalid artifact_id: {artifact_id!r}")
    path = (VAULT_BASE / artifact_id).resolve()
    if not path.is_relative_to(VAULT_BASE.resolve()):
        raise ValueError("Path escape detected")
    return path
```

`uuid.UUID(artifact_id)` is the correct sanitiser here because:
1. UUID format is `[0-9a-f]{8}-[0-9a-f]{4}-...` — contains no `/`, `..`, or null bytes
2. It's the exact format the code generates at write time (`str(uuid.uuid4())`)
3. If CodeQL still does not recognise `uuid.UUID()` as a sanitiser (it is not in the default sanitiser set — see [CodeQL discussion #10722](https://github.com/github/codeql/discussions/10722)), the fallback is the `resolve() + is_relative_to()` check above, which CodeQL does recognise

**Apply the same pattern in `delete_artifact`** (line 70–72) — same taint path.

---

## Fix Pattern: API_KEY Removal

**Pure code deletion — no library changes required.**

Files to modify:
- `security.py:16-21` — remove `try: API_KEY = os.environ["API_KEY"] except KeyError: sys.exit(1)` block
- `security.py:104-108` — remove `verify_api_key` function
- `main.py:44` — remove `verify_api_key, API_KEY` from import
- `main.py:1225, 1234, 1241` — remove `Depends(verify_api_key)` from node-facing routes

The `API_KEY` env var should be removed from `.env.example`, `secrets.env` templates, and documentation. No migration SQL required (API_KEY is not stored in the DB).

---

## Fix Pattern: EE Licence Air-Gap Enforcement

### Current State (What Exists)

The `main.py` lifespan parses `AXIOM_LICENCE_KEY` by base64-decoding the payload and checking `exp > time.time()`. It does **not** verify the Ed25519 signature. Signature verification is done by `_parse_licence()` in `ee/plugin.py` (private EE repo), which calls `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify()`.

The CE lifespan bypasses signature verification because the EE public key is bundled only in the `axiom-ee` package. This is architecturally correct — CE cannot verify EE licences without access to the hardcoded public key bytes.

### What Needs to Change

The todo asks for a **monotonic boot-log** approach to detect clock rollback in air-gapped deployments. The design in the todo mentions:

> "Include a 'not-before' + 'not-after' window; on each startup log the boot time to a tamper-evident local file (hash chain). If the recorded history shows time going backwards, refuse to start."

**Implementation using stdlib only (no new libraries):**

```python
# licence_boot_log.py — new file in agent_service/
import json, hashlib, time, os
from pathlib import Path

BOOT_LOG_PATH = Path(os.getenv("AXIOM_DATA_DIR", "/app/data")) / ".licence_boot_log"

def record_boot_and_check_monotonic() -> bool:
    """
    Returns True if time appears to be moving forward (no clock rollback detected).
    Appends a hash-chained entry to the boot log on every call.
    """
    now = int(time.time())
    log = []
    prev_hash = "genesis"

    if BOOT_LOG_PATH.exists():
        try:
            log = json.loads(BOOT_LOG_PATH.read_text())
            if log:
                last = log[-1]
                if last["ts"] > now + 300:   # 5-minute grace for NTP skew
                    return False             # clock rolled back
                prev_hash = last["h"]
        except Exception:
            pass   # corrupt log: start fresh, don't block

    entry_data = f"{prev_hash}:{now}".encode()
    entry_hash = hashlib.sha256(entry_data).hexdigest()
    log.append({"ts": now, "h": entry_hash})
    log = log[-1000:]   # keep last 1000 entries (~3 years at daily restarts)

    try:
        BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        BOOT_LOG_PATH.write_text(json.dumps(log))
    except OSError:
        pass   # read-only filesystem: skip log write, don't block

    return True
```

**Key design decisions (justified by research):**

| Decision | Rationale |
|----------|-----------|
| Stdlib only (`json`, `hashlib`, `time`, `pathlib`) | Zero new dependencies; `cryptography` already in stack for Ed25519 if HMAC-signing the log is needed later |
| Hash chain (each entry hashes previous) | Tamper-evidence without a key: modifying a past entry invalidates all subsequent hashes |
| 5-minute grace for NTP skew | Real deployments experience NTP correction on boot; a 0-second tolerance would produce false positives |
| Corrupt/missing log = allow startup | Air-gapped installs may not have a pre-existing log; fail-open on corrupt log avoids bricking fresh deployments |
| Read-only filesystem = skip write | Some hardened container deployments mount `/app` read-only; licence enforcement must not crash in this case |
| Last 1000 entries capped | Prevents log file growing unbounded; 1000 entries at one restart/day = ~3 years |
| `AXIOM_DATA_DIR` configurable | Operators can point this at a persistent volume mount; defaults to `/app/data` (Docker convention) |

**Grace period on expiry (degraded mode, not hard stop):**

```python
GRACE_DAYS = 14   # 2-week grace period after expiry

exp = licence_data.get("exp", 0)
now = int(time.time())
if now <= exp:
    status = "ACTIVE"
elif now <= exp + (GRACE_DAYS * 86400):
    status = "GRACE"    # EE features still on, nag banner shown
else:
    status = "EXPIRED"  # Degrade to CE mode
```

This matches JetBrains' and other commercial tools' pattern: a 14-day grace period prevents a customer whose licence renewal is delayed from being locked out mid-operation. After the grace period, the system degrades to CE features (not a hard crash). The grace period value should be encoded in the licence payload or configurable, not hardcoded.

### Licence Payload Format (Ed25519-signed JSON)

The existing format (confirmed in `test_licence.py`) is:

```json
{
  "customer_id": "acme-corp",
  "exp": 1777777777,
  "features": ["foundry", "audit", "webhooks", "triggers", "rbac", "resource_limits", "service_principals", "api_keys", "executions"]
}
```

**Additions for v14.3:**

```json
{
  "customer_id": "acme-corp",
  "iat": 1745000000,
  "exp": 1777777777,
  "grace_days": 14,
  "node_limit": 50,
  "tier": "enterprise",
  "features": [...]
}
```

- `iat` (issued_at): enables detection of licence re-use after revocation if a licence server is added later
- `grace_days`: per-licence configurable grace period (overrides the hardcoded default)
- `node_limit`: enforced in `job_service.py` node selection; currently in the design but not yet code
- `tier`: string label for display; `"enterprise"` is the only valid EE tier now

Wire format (unchanged from v11.0): `base64url(json_payload).base64url(ed25519_signature)` — no padding.

### Where the Licence Key Lives

Current: `AXIOM_LICENCE_KEY` env var in `secrets.env`.

This is correct. Do **not** move it to a file path or DB entry — env var is:
1. Consistent with how `SECRET_KEY`, `ENCRYPTION_KEY` are handled
2. Invisible to the container filesystem (no file path to discover)
3. Compatible with Kubernetes Secrets and Docker secrets

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Stdlib `uuid.UUID()` for vault path sanitisation | `werkzeug.utils.secure_filename` | Werkzeug is a Flask dependency; adding it to a FastAPI project solely for filename sanitisation is unnecessary baggage. UUID validation is more precise (rejects any non-UUID input, not just unsafe characters). |
| Linear bounded regex for ReDoS fix | `regex` PyPI module (RE2 engine, ReDoS-immune) | `regex` is 2MB, requires C extension. The linear bounded regex achieves the same result for the specific PII masking use case. Use `regex` only if PII patterns become complex enough that safe bounded rewrites are no longer maintainable. |
| Hash-chained boot log for air-gap monotonicity | Call-home licence server | Call-home is architecturally incompatible with air-gapped deployments, which are a stated core use case (PROJECT.md). |
| Hash-chained boot log | HMAC-signed boot log with `ENCRYPTION_KEY` | HMAC would be stronger (log entries are cryptographically bound to the server's encryption key, not just hash-chained). However, the `ENCRYPTION_KEY` env var may rotate independently of the boot log; key rotation would invalidate all historical entries and block startup. Hash-chain is sufficient for clock-rollback detection and survives key rotation. |
| 14-day grace period degrading to CE | Hard cut-off on expiry | Hard cut-off would lock out customers mid-operation if licence renewal is delayed. Grace period is standard commercial practice (JetBrains, AVEVA). Degrading to CE (not crashing) means jobs already on nodes continue; only EE features are disabled. |
| `pathlib.Path.resolve() + is_relative_to()` | `os.path.abspath() + startswith()` | CodeQL does not recognise `os.path.abspath` as a symlink-resolving normaliser. `pathlib.Path.resolve()` is explicitly in CodeQL's `PathNormalization::Range` recogniser. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `bleach` for XSS fix | Wrong tool: `bleach` sanitises HTML. The CSV response is not HTML. | `csv.QUOTE_ALL` + formula prefix stripping for CSV injection; the `text/csv` content-type already prevents browser XSS. |
| `python-jose` for licence tokens | `python-jose` implements JWT (JOSE). The licence key format is a custom Ed25519-signed blob, not JWT. Adding JWT structure adds complexity without benefit. | `cryptography.hazmat.primitives.asymmetric.ed25519` — already in stack, already used by `_parse_licence()` in EE. |
| `itsdangerous` for boot log signing | Adds a dependency. HMAC-SHA256 via stdlib `hmac` is equivalent. | `hashlib.sha256` for hash-chaining; if HMAC-signed log is later required, use stdlib `hmac` with `ENCRYPTION_KEY`. |
| Online licence validation (call-home) | Incompatible with air-gapped deployments. | Ed25519 offline signature + boot log monotonicity check. |
| `pyjwt` for licence | Same issue as `python-jose` — JWT overhead for a simple signed payload. | Custom `base64url(payload).base64url(sig)` format already implemented and tested. |
| Storing boot log in DB | DB is the resource being protected; a licence that expires should also gate DB access eventually. Boot log in DB can be cleared by a DB admin. | Filesystem path under `AXIOM_DATA_DIR` — separate from the DB. |

---

## Installation Changes

**No new packages to install.** All fixes use stdlib or `cryptography` (already in `requirements.txt`).

The only file that gains a new import is `vault_service.py` (adds `from pathlib import Path`) and `main.py`/`security.py` (adds `from pathlib import Path` and uses bounded regex). The boot log module is a new file in `agent_service/` with stdlib-only imports.

```bash
# No changes to requirements.txt
# No changes to Dockerfile pip install step
```

---

## Version Compatibility

| Component | Version Constraint | Notes |
|-----------|-------------------|-------|
| `pathlib.Path.is_relative_to()` | Python 3.9+ required | Project targets Python 3.11/3.12/3.13 (confirmed by Cython wheel matrix). No compatibility issue. |
| `cryptography` Ed25519 | 2.6+ | Already in stack. `Ed25519PublicKey.verify()` has been stable since cryptography 2.6 (2018). |
| `uuid.UUID()` | stdlib, any Python 3.x | No version constraint. |

---

## Sources

- [CodeQL py/reflective-xss query help](https://codeql.github.com/codeql-query-help/python/py-reflective-xss/) — trigger conditions and fix pattern (HIGH confidence — official CodeQL docs)
- [CodeQL py/path-injection query help](https://codeql.github.com/codeql-query-help/python/py-path-injection/) — `normpath + startswith` as recognised sanitiser; `pathlib.resolve` as normalisation (HIGH confidence — official CodeQL docs)
- [CodeQL discussion #10722 — UUID log-injection false positive](https://github.com/github/codeql/discussions/10722) — UUID validation not in default CodeQL sanitiser set; custom sanitiser or `resolve()` guard required as belt-and-suspenders (MEDIUM confidence — CodeQL team acknowledged)
- [CodeQL PR #7009 — Python path injection sanitisers](https://github.com/github/codeql/pull/7009) — `pathlib.resolve()` added to PathNormalization::Range (HIGH confidence — merged PR to CodeQL main)
- [GitHub blog — How to fix a ReDoS](https://github.blog/security/how-to-fix-a-redos/) — bounded quantifiers as prevention strategy (HIGH confidence — official GitHub security blog)
- [cryptography.io — Ed25519 signing docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) — `Ed25519PublicKey.verify()` API (HIGH confidence — official library docs)
- [keygen-sh Python cryptographic licence example](https://github.com/keygen-sh/example-python-cryptographic-license-files) — Ed25519-signed licence file pattern (MEDIUM confidence — third-party reference implementation)
- [JetBrains perpetual fallback licence FAQ](https://sales.jetbrains.com/hc/en-gb/articles/207240845) — 14-day grace period as commercial standard (MEDIUM confidence — industry reference)
- Direct codebase analysis: `security.py`, `vault_service.py`, `main.py`, `ee/__init__.py`, `tests/test_licence.py` — current state, what's implemented vs missing (HIGH confidence — source of truth)

---

*Stack research for: Security hardening (CodeQL fixes) + EE licence air-gap enforcement (v14.3)*
*Researched: 2026-03-26*

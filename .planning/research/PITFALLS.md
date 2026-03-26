# Pitfalls Research

**Domain:** Security hardening (CodeQL XSS / path injection / ReDoS fixes) + EE licence key system (Ed25519 offline validation, air-gap expiry enforcement) in an existing FastAPI + Cython-compiled EE plugin codebase
**Researched:** 2026-03-26
**Confidence:** HIGH (based on direct codebase inspection of `main.py`, `vault_service.py`, `security.py`, `ee/__init__.py`, `tests/test_licence.py`; CodeQL official docs; Keygen.sh and Sentinel LDK air-gap licensing references)

---

## Critical Pitfalls

### Pitfall 1: Path-Normalization Order Reversal (Path Injection Silently Remains)

**What goes wrong:**
The fix validates that the incoming path "looks safe" before calling `Path.resolve()` — e.g. checking that the raw user string doesn't contain `..` then resolving it. Because `resolve()` follows symlinks, a path that passes the raw check can still escape the allowed base directory through a symlink. CodeQL also continues to flag the alert because its taint-tracking requires that normalization happens before the comparison, not after.

**Why it happens:**
Developers assume that checking for `../` in the raw string is sufficient. The normalization step must come first because both `../` substitutions and symlinks are resolved by `os.path.realpath()` / `Path.resolve()`. The required pattern is: `resolved = Path(base_dir / user_input).resolve(); assert str(resolved).startswith(str(Path(base_dir).resolve()))`.

**How to avoid:**
In `vault_service.py` lines 70-72 and `main.py` lines 2457/2461: the `artifact_id` is a UUID generated server-side — CodeQL flags the taint because `artifact_id` comes from a DB read that was originally seeded by user input. The correct fix is to resolve the path unconditionally and compare its prefix to the absolute `VAULT_DIR`, even when you trust the ID semantically:
```python
resolved = Path(VAULT_DIR, artifact_id).resolve()
if not str(resolved).startswith(str(Path(VAULT_DIR).resolve())):
    raise HTTPException(status_code=400, detail="Invalid artifact ID")
```
Order is non-negotiable: `resolve()` then `startswith()`.

**Warning signs:**
- The CodeQL alert survives after the fix — means normalization happened after validation
- Tests pass because the test IDs are benign UUIDs, but the taint path still exists
- `os.path.join(VAULT_DIR, user_input)` without a subsequent `resolve()` check is always flagged

**Phase to address:** Security fixes phase (Phase 1 of v14.3)

---

### Pitfall 2: XSS Alert on CSV StreamingResponse Is Not a False Positive

**What goes wrong:**
The `GET /api/jobs/export` endpoint returns `media_type="text/csv"` via `StreamingResponse` (main.py ~line 873). The CodeQL alert (`py/reflective-xss`) looks like a false positive because CSV is not HTML. However, older browsers and some content-sniffing proxies interpret a `text/csv` response as `text/html` if the `X-Content-Type-Options: nosniff` header is absent, creating a real reflected XSS vector. The fix is not to dismiss the alert but to add the header.

**Why it happens:**
Teams treat content-type enforcement as "browser's problem" and dismiss CSV XSS as theoretical. The `nosniff` header is required for CodeQL to stop flagging the response, and it also genuinely protects against content sniffing in IE/Edge legacy and Cloudflare-modified responses.

**How to avoid:**
Add `X-Content-Type-Options: nosniff` to the `headers` dict in the `StreamingResponse`. Caddy (the TLS terminator in this stack) can also inject this globally via a `header` directive, but the backend fix is the defence-in-depth layer CodeQL can verify statically.

**Warning signs:**
- The alert persists after adding the correct content type — check whether `nosniff` was omitted
- Caddy-level header injection is not visible to CodeQL static analysis and will not resolve the alert

**Phase to address:** Security fixes phase (Phase 1 of v14.3)

---

### Pitfall 3: ReDoS Fix Breaks Legitimate API Key Format Validation

**What goes wrong:**
The `security.py:79` pattern is an email regex applied to data that could come from an untrusted request. The naive fix is to remove the regex entirely or replace it with `re.fullmatch(r'[^@]+@[^@]+\.[^@]+', value)`, which is fast but so permissive it accepts garbage. A worse fix is adding catastrophic alternatives: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` contains nested quantifiers that CodeQL flags as polynomial-time backtracking when the input doesn't match — specifically the `[a-zA-Z0-9-]+` inside a `.` (dot char class) at the TLD.

**Why it happens:**
The common "fix" for ReDoS is to add input length limits before the match. While length limits help, they do not eliminate polynomial backtracking; they only slow it down. CodeQL still flags the pattern unless the regex is rewritten to be linear.

**How to avoid:**
Either (a) replace the regex with a simpler non-backtracking form: `r'^[^@\s]{1,64}@[^@\s]{1,253}$'` (checks structure only, not character classes), or (b) add a length check AND use `re.fullmatch` with possessive quantifiers (Python 3.11+ `re.NOFLAG` with `(?:...)` non-capturing but still backtracking). The real prevention: do not use `PII_MASK` / `mask_pii()` on untrusted API request bodies in hot paths — reserve it for log sanitisation on structured data.

**Warning signs:**
- The CodeQL `py/polynomial-redos` alert persists after adding a length check — the regex itself must change
- Performance degrades sharply when processing job names containing many `@` signs

**Phase to address:** Security fixes phase (Phase 1 of v14.3)

---

### Pitfall 4: Removing API_KEY Hard-Crashes Existing CE Deployments Without Migration Path

**What goes wrong:**
`security.py:17-21` does `sys.exit(1)` if `API_KEY` is absent. v14.3 plans to remove the legacy `API_KEY` mechanism. Removing the hard-crash without a deprecation period will silently break every existing deployment that has `API_KEY` in its `secrets.env` — not because they use it, but because removing the `sys.exit(1)` guard while keeping the env-var read will cause a `KeyError` or `None` to propagate to a Fernet key derivation step. The reverse risk is equally bad: keeping the hard-crash while deprecating the feature means fresh installs that don't set `API_KEY` cannot start.

**Why it happens:**
The removal seems simple (delete the guard), but the `API_KEY` variable is read in multiple places: the guard at import time, an injected dependency, and potentially header-check logic on node-facing routes. A partial removal leaves a dangling reference.

**How to avoid:**
Do a full grep before removing: every reference to `API_KEY` across `main.py`, `security.py`, and any node-facing route must be audited. The removal should be a single atomic commit that removes the env-var read, the `sys.exit`, the Depends injection, and the matching test assertions together. Existing `secrets.env` files with `API_KEY` set should still boot without error (the key is just ignored).

**Warning signs:**
- `ImportError` or `NameError` at startup after partial removal
- Node enrollment fails with a 401 because a route still tries to validate `API_KEY`
- Tests that used to pass by injecting `API_KEY` into the test environment now error on missing setup

**Phase to address:** Security fixes phase (Phase 1 of v14.3) — must be in same commit as all XSS/injection fixes to avoid a partial-removal window

---

### Pitfall 5: Licence Expiry Check at Startup Only — Long-Running Processes Bypass It

**What goes wrong:**
If `_parse_licence()` is called once in the `lifespan` function and the result stored in `app.state.licence`, a server that started with a valid licence and runs for 13 months never re-validates. The licence expires mid-run but EE features remain available until the next restart. For air-gapped deployments with perpetual uptime (industrial, defence), this can mean years of unlicensed operation after the key expires.

**Why it happens:**
Startup-only validation is the simplest implementation and is what the v11.0 implementation established. Periodic validation requires a background task, which adds complexity and a failure mode (what if the background task crashes?).

**How to avoid:**
Add an expiry check in a lightweight APScheduler job (already available in the stack) that runs every 6-12 hours. The check does NOT re-read from disk — it reads `app.state.licence["exp"]` and compares to `time.time()`. If expired, it sets a flag (`app.state.licence_valid = False`) and logs a warning but does NOT immediately revoke features. Feature-gating code checks `app.state.licence_valid` at request time. This separates the "is the licence structurally valid" question (startup) from the "is it still within its window" question (runtime).

**Warning signs:**
- `GET /api/licence` returns `expires: 2025-01-01` while EE routes still return 200
- No scheduled job appears in APScheduler logs for licence re-validation

**Phase to address:** EE licensing phase (Phase 2 of v14.3)

---

### Pitfall 6: Monotonic Boot-Log Anti-Clock-Rollback Is Tamper-Evident in Theory, Trivially Bypassed in Practice

**What goes wrong:**
The proposed approach is to write a signed timestamp file on each startup and verify the log is monotonically increasing. In an air-gapped Docker deployment, the customer can delete the boot-log file, reset the container, and the system treats it as a fresh install — no boot history means no rollback to detect. The defence requires the log file to persist across container restarts AND to be detectable when absent.

**Why it happens:**
Boot-log approaches assume persistent state outside the container. In containerised deployments (the primary target), the `/app` volume is operator-controlled. An absent log is indistinguishable from a fresh install unless absence itself triggers a penalty.

**How to avoid:**
Use a two-factor approach:
1. If no boot-log exists AND a licence is present, issue a single-use "first activation" window (e.g., 7 days), after which a boot-log entry is required to continue.
2. The boot-log file is written to the same volume as `secrets.env` (already required for the deployment) — if the operator can delete it, they can delete their whole config. Volume deletion = intentional.
3. For the v14.3 scope: treat absence of boot-log as "unknown" (not "permitted") and apply the grace period model instead of a hard stop — this is simpler and honest about the limitation.

An alternative that avoids the file problem entirely: embed a "not-before" counter in the licence payload itself. This is a monotonically increasing integer that must be stored in the DB (which is already persistent in this stack). The licence includes `min_boot_count: N`. The server maintains a `boot_count` in the Config table. If `boot_count < min_boot_count`, refuse to activate.

**Warning signs:**
- Boot-log file is stored inside the container image layer, not a named volume — deleted on every container pull
- The validation code branches on `FileNotFoundError` by continuing normally (silent bypass)

**Phase to address:** EE licensing phase (Phase 2 of v14.3) — simplify to grace-period model for v14.3, document limitation

---

### Pitfall 7: Hard Stop on Expiry Breaks Air-Gapped Operators Mid-Operation

**What goes wrong:**
If the expiry enforcement is a hard stop (EE features return 402 immediately on expiry), an air-gapped operator whose licence expired at 2am during a production job run has an outage. Nodes executing jobs at that moment may receive 402 responses on their next heartbeat cycle, causing jobs to stall. Scheduled jobs that fire after expiry will not dispatch.

**Why it happens:**
Hard-stop is the simplest implementation and has no ambiguity about the state. The problem is that in air-gapped environments, licence renewal is a manual process (offline file transfer) that cannot happen at midnight.

**How to avoid:**
Implement a grace period (14-30 days) during which EE features remain active but:
- `GET /api/licence` returns `"status": "grace_period"` with the expiry date and days remaining
- Dashboard shows an amber banner "Your licence expired N days ago — renew before [date] to avoid interruption"
- After the grace period, degrade to CE mode (not a hard crash) — EE routes return 402, not 500

The CE fallback is already implemented (stub routers). The state machine is: `VALID → GRACE_PERIOD → DEGRADED_CE`. Never `VALID → CRASHED`.

**Warning signs:**
- `app.state.licence = None` is set on expiry — this causes the EE plugin's feature flags to disappear and may cause `AttributeError` if other code reads `app.state.ee_ctx.foundry` without a None-guard
- Nodes go OFFLINE because their heartbeat route returns 402

**Phase to address:** EE licensing phase (Phase 2 of v14.3)

---

### Pitfall 8: Licence Public Key Embedded in Compiled Cython Wheel Is Extractable

**What goes wrong:**
The `axiom-ee` package embeds the licence validation public key as a bytes literal in `ee/plugin.py` (or equivalent). Cython compiles this to a `.so` file. An attacker who obtains the `.so` can run `strings` on it or step through with a debugger to recover the public key. With the public key, they cannot forge new licences (Ed25519 remains secure), but they can confirm the validation logic and test bypasses.

More critically: if the public key byte string is extracted, a fork of the `.so` can replace it with an attacker-controlled key and generate their own "valid" licences. This is possible because the `.so` file is installed in a writable Python package directory.

**Why it happens:**
All software licence validators face this attack. Cython provides obfuscation, not cryptographic protection.

**How to avoid:**
Accept the fundamental limitation: offline licence validation in a software-distributed validator cannot be made tamper-proof against a sufficiently motivated attacker with root access. The mitigation is raising the cost:
1. The public key should be split across multiple constants or derived from a seed at import time (not stored as a single contiguous bytes literal)
2. The `.so` module integrity should be checked at startup using a hash of the file itself (stored in the licence payload or in a separate manifest)
3. For v14.3 scope: accept the limitation and document it. Do not store the private key anywhere near the validator. The goal is deterrence, not perfect enforcement.

**Warning signs:**
- `_LICENCE_PUBLIC_KEY_BYTES` appears as a named module-level constant — single extraction point
- The public key is the same as the job signing verification key — reusing it means a leaked key compromises both systems

**Phase to address:** EE licensing phase (Phase 2 of v14.3) — note limitation in design doc, defer hardening to future milestone

---

### Pitfall 9: Licence Absent = EE Plugin Not Loaded = `app.state.ee_ctx` May Not Exist

**What goes wrong:**
The current `load_ee_plugins()` function returns an `EEContext` and presumably stores it on `app.state`. If the licence check is added inside `load_ee_plugins()` (i.e., "don't load EE plugin if licence is invalid"), then code that reads `app.state.ee_ctx.foundry` will get `AttributeError` when the EE plugin is installed but the licence is absent, because the EE plugin was not loaded. Code that tests `hasattr(app.state, 'ee_ctx')` will behave differently in CE (no EE installed) vs. EE-installed-but-unlicensed.

**Why it happens:**
The CE/EE split was designed around "EE plugin installed vs. not installed". Adding a licence state creates a third state: "EE plugin installed, licence absent/expired". Feature-gating code needs to handle this third state explicitly.

**How to avoid:**
Load the EE plugin unconditionally (discover it via entry_points), but gate feature activation on the licence check result. The `EEContext` object always exists; its boolean fields reflect both "plugin loaded" AND "licence valid". When the licence is absent, `EEContext` fields are all `False` (same as CE mode). This means the stub routers are NOT mounted (the real EE routes are), but they return 402 because the feature flag is `False`. This requires feature-flag checking in every EE route handler, not just at plugin load time.

**Warning signs:**
- After installing `axiom-ee` with an absent `AXIOM_LICENCE_KEY`, EE routes return 500 instead of 402
- `app.state.ee_ctx` is `None` when the EE plugin is installed but unlicensed

**Phase to address:** EE licensing phase (Phase 2 of v14.3)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Startup-only licence validation | Zero runtime overhead, simple | Licence expiry not enforced on long-running deployments | Never for air-gap EE with 1-year licences |
| `sys.exit(1)` on missing env var | Obvious failure mode for ops | Cannot be tested without patching `os.environ`; breaks unit tests | Only for truly non-negotiable keys like `SECRET_KEY` — not legacy `API_KEY` |
| Embed public key as `bytes` literal | Simple | Single `strings` extraction point | Acceptable for v14.3; document limitation |
| Hard stop on licence expiry | No ambiguity | Outage for air-gapped operators during renewal window | Never for production EE — use grace period |
| `pathlib.Path(base).resolve()` prefix check without stripping trailing slash | Correct for most cases | `VAULT_DIR=/app/vault` prefix check passes `VAULT_DIR=/app/vault2` | Low risk but fix: use `resolved.is_relative_to(base)` (Python 3.9+) or append `/` to base before check |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CodeQL path injection alert | Adding resolve() after the comparison | Resolve first, compare prefix second — order is enforced by taint tracking |
| CodeQL XSS on StreamingResponse | Dismissing as false positive because content type is CSV | Add `X-Content-Type-Options: nosniff` to response headers — the alert is not a false positive |
| APScheduler + licence re-validation | Scheduling the re-validation job before `app.state.licence` is populated | Schedule the job in `lifespan` after `load_ee_plugins()` has returned |
| EE plugin entry_point + licence check | Raising exception in `register()` on licence failure (causes CE stub mount) | Return from `register()` with all feature flags `False` — stubs should NOT be re-mounted |
| Cython .so + public key | Storing private key in `axiom-ee` repo alongside validator | Private key must be in a separate offline tool only — never in the distributed package |
| `secrets.env` + `AXIOM_LICENCE_KEY` | Reading it with `os.environ["AXIOM_LICENCE_KEY"]` causing `sys.exit` on fresh CE installs | Use `os.getenv("AXIOM_LICENCE_KEY", "")` — absent key = CE mode, not crash |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `mask_pii()` on every request body | High CPU on job dispatch with large scripts | Restrict PII masking to audit log writes only, not hot API paths | At ~100 concurrent job dispatches |
| Re-reading `AXIOM_LICENCE_KEY` from disk on every EE route call | 10-50ms latency added to every EE API call | Cache in `app.state.licence` at startup; periodic re-validation via scheduler | First request after startup if not cached |
| `Path.resolve()` on every file operation in vault service | Negligible at current scale | Fine for this use case | N/A for expected vault sizes |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Reusing the Ed25519 job-signing keypair as the licence signing keypair | A leaked job-signing key would also forge licences | Use a separate Ed25519 keypair for licence signing — stored in a separate offline tool |
| Storing `AXIOM_LICENCE_KEY` in `.env` (committed) rather than `secrets.env` (gitignored) | Licence key leaks in git history | Document that `AXIOM_LICENCE_KEY` goes in `secrets.env` only; add to `.gitignore` check |
| Setting `app.state.licence = None` on expiry with no None-guard in feature-flag checks | `AttributeError` crashes on EE route access after expiry | Use a sentinel object (`LicenceExpired`) or always check `app.state.licence and app.state.licence["valid"]` |
| Grace period counter stored only in memory | Container restart resets grace period countdown — effectively extends it indefinitely | Persist the grace period start timestamp in the Config DB table |
| Path injection fix using `werkzeug.secure_filename` on a UUID | UUIDs contain `-` which `secure_filename` may strip, returning an empty string or mangled path | Use `Path.resolve() + is_relative_to()` for UUIDs, not filename sanitisers designed for user-supplied filenames |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Hard stop on licence expiry with no warning lead-up | Sudden outage for air-gapped operators; no time to renew | Show amber dashboard banner at 30 days, red at 7 days, grace period after expiry |
| `GET /api/licence` returning `{edition: "community"}` when EE is installed but unlicensed | Operator thinks they're in CE mode; can't diagnose why EE features aren't working | Return `{edition: "enterprise_unlicensed", reason: "licence absent|expired|invalid"}` |
| Licence error surfaced as a 500 in EE route | Operator sees a generic error, not a licence problem | EE routes without a valid licence must return 402 with `{"detail": "EE licence required"}` |
| No visibility of grace period countdown in dashboard | Operator doesn't know when hard cutoff is | Display grace period end date in Admin > Licence section and in `GET /api/licence` response |

---

## "Looks Done But Isn't" Checklist

- [ ] **Path injection fix:** CodeQL alert dismissed rather than fixed — verify the alert actually closes in the next scan, not just that tests pass
- [ ] **XSS fix on CSV export:** `nosniff` header added to backend but also check Caddy doesn't strip it — test with `curl -I`
- [ ] **ReDoS fix:** `mask_pii()` regex replaced but same pattern exists elsewhere in codebase — run `grep -r 'a-zA-Z0-9_\.' puppeteer/` to find copies
- [ ] **API_KEY removal:** Guard removed from `security.py` but `API_KEY` variable still read and passed to node-route handlers — check all 3 call sites
- [ ] **Licence expiry enforcement:** `app.state.licence` set to `None` on expiry — verify all EE route handlers have None-guard, not just the flag check
- [ ] **Grace period:** Timer stored in memory — verify it persists across container restarts (DB-backed)
- [ ] **Absent licence = CE mode:** EE plugin installed, no `AXIOM_LICENCE_KEY` set — verify `/api/features` returns all `false`, not 500
- [ ] **Licence key format validation:** `_parse_licence("")` returns `None` (tested) — also verify `_parse_licence("garbage.garbage")` does not panic on base64 decode error

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Path injection fix breaks valid UUID file access | LOW | The resolved path of a valid UUID will always be within `VAULT_DIR`; if not, fix the base path constant |
| API_KEY removal breaks existing deployment | MEDIUM | Add `API_KEY` back as an optional no-op env var; document deprecation in changelog |
| Licence hard stop during production run | HIGH | Restore previous container image; apply licence renewal; restart; audit which jobs were lost |
| EE plugin not loading after licence check added to `register()` | LOW | Remove licence check from `register()`; gate at request time instead |
| Monotonic boot-log file missing after volume remount | LOW | Apply grace period — do not hard-stop; log warning; operator renews licence to reset |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Path normalization order (Pitfall 1) | Phase 1: Security fixes | CodeQL alert count drops from 5 to 0; unit test with `../` traversal input |
| XSS on CSV nosniff (Pitfall 2) | Phase 1: Security fixes | `curl -I /api/jobs/export` shows `X-Content-Type-Options: nosniff`; CodeQL alert closes |
| ReDoS regex fix regression (Pitfall 3) | Phase 1: Security fixes | CodeQL warning closes; benchmark with 10k-char `@`-heavy input shows <1ms |
| API_KEY removal side-effects (Pitfall 4) | Phase 1: Security fixes | Fresh CE install without `API_KEY` in env starts cleanly; existing deploys with `API_KEY` still start |
| Startup-only expiry (Pitfall 5) | Phase 2: EE licensing | APScheduler job visible in logs every 6h; `GET /api/licence` shows updated expiry status after scheduler tick |
| Boot-log file loss bypasses anti-rollback (Pitfall 6) | Phase 2: EE licensing | Delete boot-log file between restarts; verify grace period fires, not normal operation |
| Hard stop outage (Pitfall 7) | Phase 2: EE licensing | Set expiry to `time.time() - 1`; verify 402 responses (not 500), amber banner, CE fallback routes work |
| Public key extraction (Pitfall 8) | Phase 2: EE licensing | Documented as accepted limitation; private key never in distributed package |
| EE-installed-but-unlicensed state (Pitfall 9) | Phase 2: EE licensing | Install axiom-ee with no env var; verify `GET /api/features` all-false, `GET /api/licence` returns unlicensed status, EE routes return 402 not 500 |

---

## Sources

- [CodeQL: Uncontrolled data used in path expression (Python)](https://codeql.github.com/codeql-query-help/python/py-path-injection/) — normalize first, validate prefix second
- [CodeQL: Polynomial regular expression used on uncontrolled data](https://codeql.github.com/codeql-query-help/python/py-polynomial-redos/) — rewrite regex, length checks alone insufficient
- [GitHub Blog: How to fix a ReDoS](https://github.blog/security/how-to-fix-a-redos/) — atomic grouping and mutual exclusion strategies
- [CodeQL false positive: FastAPI SSRF warning issue #17353](https://github.com/github/codeql/issues/17353) — confirms FastAPI-specific taint tracking issues
- [Keygen.sh air-gapped activation example](https://github.com/keygen-sh/air-gapped-activation-example) — offline licence file pattern, Ed25519 + AES-GCM
- [Gatewarden: Ed25519 licence validation with offline grace periods](https://github.com/Michael-A-Kuykendall/gatewarden) — offline grace period pattern
- [Sentinel LDK V-Clock: time-based licence protection](https://docs.sentinel.thalesgroup.com/ldk/LDKdocs/SPNL/LDK_SLnP_Guide/Appendixes/HowProtects_TimeBased.htm) — monotonic clock enforcement approach
- [Cython reverse engineering discussion](https://python-forum.io/thread-5093.html) — confirms Cython is obfuscation, not cryptographic protection
- `puppeteer/agent_service/security.py` — actual ReDoS pattern at line 89-98
- `puppeteer/agent_service/services/vault_service.py` — actual path injection pattern at lines 70-72
- `puppeteer/agent_service/main.py` — actual XSS pattern at line 875
- `puppeteer/agent_service/ee/__init__.py` — EE plugin loader and CE/EE state model
- `puppeteer/agent_service/tests/test_licence.py` — existing licence test patterns and edge cases

---
*Pitfalls research for: Security Hardening + EE Licensing (v14.3 milestone)*
*Researched: 2026-03-26*

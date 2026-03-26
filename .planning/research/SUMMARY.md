# Project Research Summary

**Project:** Master of Puppets — Axiom v14.3
**Domain:** Security hardening (CodeQL fixes) + EE licence key system with air-gap support
**Researched:** 2026-03-26
**Confidence:** HIGH

## Executive Summary

This milestone addresses two independent but urgent concerns on a mature, production v14.2 codebase. The first is closing 5 CodeQL error-severity and 1 warning-severity security alerts: a reflected XSS in the device-approval OAuth page, four path injection alerts across `vault_service.py` and `main.py`, and a ReDoS-vulnerable email regex in `mask_pii()`. All six fixes require only stdlib or the `cryptography` library already in `requirements.txt` — zero new dependencies. The second concern is hardening the EE licence system for air-gapped deployments: the current CE lifespan does base64-decode and clock-expiry but does NOT verify the Ed25519 signature, meaning a customer can forge any expiry date. A new `licence_service.py` module must add full cryptographic validation, plus a hash-chained boot log for clock-rollback detection, a grace period to prevent outages on renewal delays, and a CLI keygen tool for Axiom Labs.

The recommended build order is strict: CodeQL fixes first (they are independent, unblock the security alert count, and one — the API_KEY removal — eliminates an import-time crash that blocks all tests), then the licence CLI (which defines the payload schema), then the licence service (which consumes that schema), then wiring and integration tests. The key architectural decision is that licence validation must live in CE code (`licence_service.py`), not inside the EE plugin's `register()` method — placing it inside the plugin causes partial route registration before the check fires, with no clean rollback. All expiry states must degrade gracefully to CE mode, never crash, because air-gapped operators cannot renew on a midnight deadline.

The principal risks are implementation-ordering mistakes (path normalization must happen before prefix comparison, not after; licence CLI wire format must be locked before the service is built) and a known limitation of the boot-log approach (a deleted boot-log file is indistinguishable from a fresh install). Both risks have documented mitigations: strict ordering enforced by the build plan, and a grace-period fallback for absent boot-log rather than a hard stop. Overall research confidence is HIGH — all findings are grounded in direct codebase inspection of the live files, official CodeQL documentation, and the existing test suite.

---

## Key Findings

### Recommended Stack

No new pip dependencies are required for this milestone. All six CodeQL fixes use Python stdlib (`pathlib`, `html`, `re`, `uuid`, `hashlib`, `hmac`, `json`) and the `cryptography` library already in `requirements.txt`. The only new file that touches an external library is `licence_service.py`, which uses `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify()` — the same API already used by the EE plugin. See `STACK.md` for full fix-pattern rationale.

**Core technologies:**
- `pathlib.Path.resolve() + is_relative_to()` — path injection fix — CodeQL explicitly recognises `resolve()` as a normalisation step; `os.path.abspath` is not recognised
- `html.escape()` (stdlib) — XSS fix — replaces direct f-string interpolation of `user_code` query param into HTMLResponse
- Bounded regex (`{1,64}`, `{1,253}`, `[a-zA-Z]{2,24}`) — ReDoS fix — length guards alone do not close the CodeQL alert; the regex must be rewritten to be linear
- `cryptography` Ed25519 — licence signature verification — already in stack; `Ed25519PublicKey.verify()` stable since cryptography 2.6 (2018)
- `hashlib.sha256` hash chain — boot log tamper-evidence — stdlib; no HMAC key rotation risk compared to HMAC-based chaining
- `uuid.UUID()` — vault path sanitisation — UUID format contains no path-traversal characters; validates the input semantically before `resolve()`

### Expected Features

**Must have — table stakes (v14.3 launch):**
- Fix reflected XSS in device-approval page — CodeQL error-severity; `user_code` query param echoed into HTMLResponse f-string unescaped
- Fix path injection in `vault_service.py` (lines 70-72) — artifact_id concatenated into filesystem path via `os.path.join` without `resolve()`
- Fix path injection in `main.py` (two locations) — installer script path traversal; verify live line numbers via CodeQL before fixing (todo references lines 2457/2461 but file is now 2152 lines)
- Fix ReDoS in `security.py:79` `mask_pii()` — polynomial backtracking on attacker-controlled job output; regex must be rewritten, length guard alone is insufficient
- Remove legacy `API_KEY` crash — `sys.exit(1)` at import time if env var absent; no historical deployments depend on it; eliminates a production operational hazard and unblocks all tests
- Admin key generation CLI (`tools/generate_licence.py`) — offline Ed25519 signing tool; enables all licence operations at Axiom Labs without a web service; must be built before the licence service
- Grace period on expiry (30-day default, `grace_days` in payload) — required for air-gapped operators who cannot renew on a deadline; state machine: VALID → GRACE → DEGRADED_CE
- HMAC-chained boot log — clock-rollback detection without network dependency; stored in `secrets/boot.log` on the already-persistent secrets volume
- Extended `GET /api/licence` response — surfaces `status: valid/grace/expired`, `days_until_expiry`, `node_limit`, `tier`
- Node limit enforcement at enrollment — count non-OFFLINE non-REVOKED nodes; reject at `POST /api/enroll` with HTTP 402 when limit reached

**Should have — add in v14.x point release:**
- Dashboard amber/red banner on grace/expired state — backend status field stable after v14.3; frontend component can follow
- Per-licence `grace_days` operator documentation

**Defer to v15+:**
- Licence issuance portal (web UI for generating keys) — not justified at current customer volume
- Periodic in-process re-validation beyond the APScheduler 6-hour check
- Per-feature tier gating (currently all-or-nothing EE)
- Hardware fingerprinting / node locking

### Architecture Approach

The milestone is split between targeted surgical fixes to existing files and two net-new files. The five CodeQL fixes are all in-place changes to `security.py`, `main.py`, and `vault_service.py` — no new modules, no schema changes. The EE licence system adds one new service module (`services/licence_service.py`) and one offline CLI tool (`tools/generate_licence.py`). The existing `ee/__init__.py` gate pattern and `app.state.licence` storage are kept intact; the new service replaces only the inlined lifespan block at `main.py:76-102`. No DB schema changes are required for any v14.3 feature except persisting the grace-period start timestamp in the `Config` table (one key-value write).

**Major components:**
1. `security.py` (modified) — remove `API_KEY` crash and `verify_api_key`; fix `mask_pii` ReDoS regex
2. `main.py` (modified) — escape `user_code` XSS; remove `Depends(verify_api_key)` from three node routes; replace inline licence block with `licence_service.validate()` call; verify and fix remaining path-injection alerts via live CodeQL scan
3. `vault_service.py` (modified) — add `_safe_artifact_path()` using `pathlib.Path.resolve() + is_relative_to()`; apply to both `store_artifact` and `delete_artifact`
4. `services/licence_service.py` (new) — `validate()` with Ed25519 verify + expiry + grace-period state machine; `LicenceResult` dataclass; boot-log read/write helpers
5. `tools/generate_licence.py` (new) — offline admin CLI; inputs customer metadata and outputs `base64url(payload).base64url(sig)` wire format; private signing key never leaves the admin machine

### Critical Pitfalls

1. **Path normalization order reversal** — `Path.resolve()` must happen before the `is_relative_to()` prefix check, not after. Checking the raw string first and then resolving is the most common mistake and leaves the taint path open. CodeQL taint tracking enforces this ordering — a fix that resolves after comparison will not close the alert.

2. **CSV XSS alert is not a false positive** — the `GET /api/jobs/export` `StreamingResponse` with `media_type="text/csv"` needs `X-Content-Type-Options: nosniff` added to the response headers. Content-sniffing browsers can reinterpret CSV as HTML if the header is absent. Adding it at the Caddy level does not satisfy CodeQL static analysis — it must be in the backend response dict.

3. **API_KEY removal must be atomic** — `API_KEY` is referenced in the import-time guard, in a dependency function, and injected into three node routes. A partial removal leaves dangling references causing `NameError` at runtime. The removal must be a single commit that deletes every reference. Existing `secrets.env` files with `API_KEY` still set must boot cleanly after removal.

4. **Licence must degrade gracefully, never crash** — setting `app.state.licence = None` on expiry causes `AttributeError` in any EE route handler that reads licence fields. The correct pattern is a sentinel `LicenceResult` object or always-present `EEContext` with all-`False` feature flags. Hard `sys.exit(1)` on expiry creates production outages for air-gapped operators.

5. **Boot-log file deletion is a known bypass** — deleting `secrets/boot.log` between container restarts is indistinguishable from a fresh install. Treat absent boot-log as "unknown" and apply the grace period, not normal EE operation. Document this limitation; defer a stronger DB-backed boot counter to a future milestone.

---

## Implications for Roadmap

Based on combined research, the work decomposes into two sequential phases with a mandatory internal sub-ordering within Phase 2.

### Phase 1: Security Fixes (CodeQL + API_KEY)

**Rationale:** These fixes are fully independent of each other and of the licence work. They are the highest-urgency action on the repo (CodeQL error-severity alerts) and one — the API_KEY `sys.exit(1)` — contaminates the test environment for everything downstream by requiring `API_KEY` in the environment for any test that imports `security.py`. Phase 1 must complete before Phase 2 begins.

**Delivers:** Zero open CodeQL error alerts; zero open CodeQL warning alerts; clean startup without `API_KEY` env var; `verify_node_secret` as the sole auth mechanism on the three node-facing routes.

**Addresses:** Fix XSS (device-approve), fix path injection x4 (vault + main), fix ReDoS (mask_pii), remove API_KEY crash and `verify_api_key`.

**Avoids:** Pitfall 1 (normalization order), Pitfall 2 (CSV nosniff), Pitfall 3 (regex rewrite not length guard), Pitfall 4 (atomic API_KEY removal).

**Research flag:** No deeper research needed. All patterns are fully documented in CodeQL official docs and confirmed against live source files. Implementation is mechanical substitution of known-good patterns.

### Phase 2: EE Licence System

**Rationale:** Depends on Phase 1 being complete (clean test environment with no API_KEY interference). Internal build order is strict: CLI first (defines payload schema and wire format), service second (embeds public key and parses the format), lifespan wiring third (replaces `main.py:76-102`), node limit enforcement last (depends on `node_limit` field in signed payloads). These sub-steps are not independently deliverable.

**Delivers:** Offline key generation capability for Axiom Labs; full Ed25519 signature verification on startup (replacing the current signature-less expiry check); clock-rollback detection via HMAC-chained boot log; grace-period state machine (VALID → GRACE → DEGRADED_CE); extended licence status in `GET /api/licence`; node limit enforcement at enrollment.

**Implements:** `tools/generate_licence.py` (CLI) → `services/licence_service.py` (validate + boot log) → `main.py` lifespan wiring → `POST /api/enroll` node-limit check.

**Avoids:** Pitfall 5 (startup-only expiry — add APScheduler 6h re-check of `app.state.licence["exp"]`), Pitfall 6 (boot-log deletion — grace fallback, not hard stop, on absent log), Pitfall 7 (hard stop on expiry — DEGRADED_CE, never crash), Pitfall 9 (EE-installed-but-unlicensed AttributeError — `EEContext` always present, all-`False` flags).

**Research flag:** No deeper external research needed. Core patterns are established in the codebase (`admin_signer.py` CLI shape, `test_licence.py` wire format, `ee/__init__.py` plugin gate). Internal design decisions (payload schema, boot-log storage path, grace-period start persistence in Config table) should be confirmed with the lead before implementation begins.

### Phase Ordering Rationale

- CodeQL fixes must precede licence work because the API_KEY `sys.exit(1)` contaminates the test environment for any code that imports `security.py`.
- Licence CLI must precede licence service because `licence_service.py` must embed the public key and parse the exact wire format the CLI produces — the format must be frozen before either side is coded.
- Licence service must precede `main.py` lifespan wiring because the `LicenceResult` API must be stable before it can be called in lifespan.
- Node limit enforcement is last because it depends on `node_limit` being a signed field in the payload, which is defined by the CLI.

### Research Flags

Phases with standard patterns (no additional research needed):
- **Phase 1 (Security Fixes):** Patterns are definitively documented in CodeQL official docs and confirmed against live source files. No ambiguity.
- **Phase 2 (EE Licence System):** Core cryptographic and grace-period patterns are established. Internal decisions need lead confirmation, not external research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies required. All fixes use stdlib or `cryptography` already in stack. Version compatibility confirmed (Python 3.11+; `pathlib.is_relative_to` requires 3.9+). |
| Features | HIGH | Feature list derived from direct codebase inspection of CodeQL alerts, todo files, and EE plugin architecture. No ambiguity about in vs. out of scope for v14.3. |
| Architecture | HIGH | Based on direct file inspection of `security.py`, `main.py`, `vault_service.py`, `ee/__init__.py`. Build order confirmed by dependency analysis. One caveat: `main.py` path-injection line numbers in the todo (2457/2461) have drifted — the file is currently 2152 lines. Must be verified via live CodeQL scan before fixing. |
| Pitfalls | HIGH | All critical pitfalls grounded in CodeQL rule semantics, live code patterns, and the specific failure modes of the EE plugin architecture. Boot-log limitation (Pitfall 6) is honestly documented with a concrete mitigation. |

**Overall confidence:** HIGH

### Gaps to Address

- **main.py path-injection line numbers have drifted** — the todo references lines 2457/2461 but the file is currently 2152 lines long. Run a fresh CodeQL scan or check the GitHub Security tab to identify the live alert locations before implementing the fix. Do not assume the todo line numbers are current.
- **Boot-log persistence strategy** — research recommends storing the grace-period start timestamp in the `Config` DB table to survive container restarts. Confirm with the lead whether this write belongs in `licence_service.py` or `main.py` lifespan, and whether a migration SQL file is needed for existing deployments.
- **Licence public key identity** — `licence_service.py` must embed the Ed25519 public key as a constant. Confirm this is a separate keypair from the job-signing verification key (the pitfall research explicitly warns against reusing it — a leaked job-signing key would also forge licences). If a new keypair is needed, generate it before implementation begins.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `puppeteer/agent_service/security.py`, `main.py`, `services/vault_service.py`, `ee/__init__.py`, `tests/test_licence.py`
- [CodeQL py/reflective-xss query help](https://codeql.github.com/codeql-query-help/python/py-reflective-xss/)
- [CodeQL py/path-injection query help](https://codeql.github.com/codeql-query-help/python/py-path-injection/)
- [CodeQL py/polynomial-redos query help](https://codeql.github.com/codeql-query-help/python/py-polynomial-redos/)
- [CodeQL PR #7009 — pathlib.resolve() added to PathNormalization::Range](https://github.com/github/codeql/pull/7009)
- [cryptography.io — Ed25519 signing docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- Todo files: `.planning/todos/pending/2026-03-26-fix-code-scanning-alerts-xss-path-injection-redos.md`, `-license-key-generation-and-validation-with-airgap-support.md`, `-remove-legacy-api-key-requirement.md`

### Secondary (MEDIUM confidence)
- [GitHub blog — How to fix a ReDoS](https://github.blog/security/how-to-fix-a-redos/) — bounded quantifiers as prevention strategy
- [CodeQL discussion #10722 — UUID validation not in default sanitiser set](https://github.com/github/codeql/discussions/10722) — `resolve() + is_relative_to()` required as belt-and-suspenders
- [keygen-sh Python cryptographic licence example](https://github.com/keygen-sh/example-python-cryptographic-license-files) — Ed25519-signed licence file pattern
- [Sentinel LDK V-Clock: time-based licence protection](https://docs.sentinel.thalesgroup.com/ldk/LDKdocs/SPNL/LDK_SLnP_Guide/Appendixes/HowProtects_TimeBased.htm) — monotonic clock enforcement approach
- [JetBrains perpetual fallback licence FAQ](https://sales.jetbrains.com/hc/en-gb/articles/207240845) — 14-day grace period as commercial standard

### Tertiary (LOW confidence)
- [Cython reverse engineering discussion](https://python-forum.io/thread-5093.html) — confirms Cython is obfuscation not cryptographic protection; embedded public key is extractable via `strings`

---
*Research completed: 2026-03-26*
*Ready for roadmap: yes*

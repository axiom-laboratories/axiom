# Feature Research

**Domain:** Security hardening + EE licence key system for an existing production job scheduler
**Researched:** 2026-03-26
**Confidence:** HIGH — all findings grounded in codebase inspection + verified patterns

---

## Context: What Already Exists

This is a subsequent milestone on a mature application (v14.2). The research question is NOT
"what should this product have?" but "what exactly needs to be built for v14.3?". The existing
relevant foundations are:

- Ed25519 licence wire format already established: `base64url(json_payload).base64url(sig)`
- `ee.plugin._parse_licence()` in the private `axiom-ee` repo handles full cryptographic verification
- CE-side fast-path in `main.py:75-92` decodes the payload and checks `exp > time.time()` — no
  signature verification in the CE codebase (correctly delegated to the EE plugin)
- `AXIOM_LICENCE_KEY` env var is the delivery mechanism (already wired into `compose.server.yaml`)
- 5 CodeQL error alerts + 1 warning are confirmed open and in production backend code
- `API_KEY` is a legacy import-time crash with no historical deployments to protect

---

## Feature Landscape

### Table Stakes (Must Fix — Blocking Production Hardening)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fix reflected XSS (main.py ~line 600 region) | CodeQL error-severity; `user_code` query param echoed unescaped into `HTMLResponse` f-string at `/auth/device/approve`. Browsers execute injected scripts. | LOW | Use `markupsafe.escape(user_code)` before interpolating into the HTML template. The approval form also has `value="{user_code}"` in a hidden input — both locations need escaping. |
| Fix path injection x4 (vault_service.py:71-72, main.py two locations) | CodeQL error-severity; user-controlled `artifact_id` is concatenated into a filesystem path via `os.path.join(VAULT_DIR, artifact_id)` without validation. Attacker can traverse outside `/app/vault/`. | LOW | Pattern: `resolved = (Path(VAULT_DIR) / artifact_id).resolve(); assert resolved.is_relative_to(Path(VAULT_DIR).resolve())`. Both vault paths and the main.py installer paths need this guard. |
| Fix ReDoS (security.py:79) | CodeQL warning; `EMAIL_REGEX` in `mask_pii()` contains nested quantifier groups — polynomial backtracking on untrusted input. `mask_pii()` is called on job output which is fully attacker-controlled. | LOW | Add `if len(data) > 1000: return data` pre-check, or replace with non-backtracking regex `r'[^\s@]+@[^\s@]+\.[^\s@]+'`. The SSN regex is safe (fixed-length). |
| Remove legacy API_KEY crash | `security.py:16-21` does `os.environ["API_KEY"]` and `sys.exit(1)` — process exits silently at import time if env var is missing. No historical deployments depend on it. Node auth is covered by mTLS; human/machine auth is covered by JWT + service principal API keys. | LOW | Remove the `sys.exit(1)` block and `verify_api_key` dependency from the three node-facing routes (`pull_work`, `receive_heartbeat`, `report_result`). Remove from `.env` examples and docs. |

### Differentiators (New Value — EE Licence System Improvements)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Admin key generation tooling | Axiom Labs can generate signed licence keys offline without a web service. Delivers a `--generate-licence` subcommand or standalone script. Output is the `base64url(payload).base64url(sig)` wire format. | MEDIUM | Wire format already proven in test suite. The private `AXIOM_LICENCE_SIGNING_KEY` (Ed25519 private key, never distributed) lives on the key-issuer machine. Payload fields: `customer_id`, `tier` (ce/ee), `node_limit`, `exp` (Unix timestamp), `issued_at`, `grace_days`, `features: [...]`. |
| Boot log / monotonic timestamp file | Writes a chained timestamp to `secrets/boot.log` on every startup. Each entry contains the boot time and an HMAC of the previous entry. On load, validates that timestamps are monotonically non-decreasing (within configurable tolerance). Clock rollback beyond the tolerance is flagged. | MEDIUM | This is the air-gap expiry enforcement mechanism. Without it, a customer can freeze their clock to prevent expiry. The boot log is HMAC-chained using `ENCRYPTION_KEY` (already present in security.py) so tampering invalidates the chain. Does not require network access. |
| Grace period on expiry | When `exp < time.time()` but within `grace_days * 86400` seconds of expiry, licence transitions to a grace state: EE features remain active, a warning is logged on startup, and the licence endpoint returns `status: grace`. After the grace window, hard CE fallback. | MEDIUM | Addresses the core operator concern: air-gapped customers cannot phone home for renewal, so a hard cutoff mid-operation is unacceptable. 30-day grace is conventional in enterprise software. The grace period is embedded in the licence payload so Axiom Labs can issue shorter-grace keys for specific customers. |
| Licence status in GET /api/licence | Extend the existing endpoint to return `status: valid/grace/expired`, `days_until_expiry` (negative during grace), `node_limit`, `tier`. Frontend Admin page already shows a licence section; it should surface these fields. | LOW | Endpoint and `app.state.licence` already exist. Pure addition, no schema changes needed. |
| Node limit enforcement | When `node_limit` is set in the licence payload, refuse enrollment at `POST /api/enroll` when the count of non-OFFLINE non-REVOKED nodes meets the limit. Return HTTP 402. | LOW | Depends on key generation tooling including `node_limit` in the payload. The enroll route already has auth checks; adding a count query is a single DB addition. |

### Anti-Features (Explicitly Out of Scope for This Milestone)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Online licence validation / call-home | Simpler expiry enforcement than a boot log | Breaks air-gapped deployments — a core Axiom use case. Fail-open is insecure; fail-closed locks out legitimate users in isolated networks. | Boot log + grace period achieves the same fraud-deterrence goal without network dependency. |
| Licence revocation via CRL / OCSP | Real-time licence cancellation | Requires network access. Not needed at current customer scale — trust relationships are direct. | Manual reissuance: issue a replacement key with a past `exp`. |
| Licence issuance portal (DIST-04) | Web UI for generating keys | Out of scope for this milestone. Customer volume does not justify a portal yet. | CLI keygen tool included in this milestone. |
| Periodic licence re-validation (DIST-05) | Catch clock manipulation between boots | Adds complexity without meaningfully improving security over the boot log approach. A determined attacker can freeze the clock between restarts. | Boot log checks on every startup. |
| Hardware fingerprinting / node locking | Prevents copying the licence to another machine | Complex, fragile (hardware changes break legitimate installations), misaligned with homelab + enterprise internal target market. | `node_limit` field limits blast radius without hardware locking. |
| Removing Ed25519 signature from licence format | Simpler distribution | Without a signature, any customer could forge a payload with arbitrary features and expiry. The embedded public key in the compiled wheel is the single trust anchor. | Keep the current format. |

---

## Feature Dependencies

```
[Fix API_KEY crash]
    (standalone — no dependencies, removes blocking crash)

[Fix XSS — device_approve_page]
    (standalone — markupsafe.escape is already a transitive dep via Starlette/Jinja2)

[Fix path injection — vault_service + main.py]
    (standalone — pathlib is stdlib)

[Fix ReDoS — security.py mask_pii]
    (standalone — inline regex change or length guard)

[Admin key generation tooling]
    └──defines payload fields──> [Boot log / monotonic timestamp file] (uses ENCRYPTION_KEY)
    └──defines payload fields──> [Grace period on expiry]
    └──defines payload fields──> [Licence status in GET /api/licence] (tier, node_limit)
    └──defines payload fields──> [Node limit enforcement]

[Grace period on expiry]
    └──requires updated status──> [Licence status in GET /api/licence]

[Boot log / monotonic timestamp file]
    └──uses existing──> ENCRYPTION_KEY (already in security.py — HMAC chaining)
```

### Dependency Notes

- **All CodeQL fixes are independent.** They can be implemented in any order and do not touch
  the licence system or each other's code paths. Prioritise first — they unblock the security
  alert count on the repo.
- **API_KEY removal is independent** but eliminates a startup crash risk for the entire service,
  not just a specific feature. Do it alongside or before the CodeQL fixes.
- **Key generation tooling must be built before** grace period, boot log, and node limit can be
  fully tested, because those features depend on payload fields (`grace_days`, `node_limit`)
  that must be signed at issuance time. Existing keys without these fields must be handled
  gracefully (default `grace_days=30`, no node limit).
- **Boot log uses ENCRYPTION_KEY** (already required by `security.py`). No new secrets
  infrastructure needed.
- **Grace period requires the licence endpoint update** to surface the warning state in the
  dashboard — otherwise operators have no visibility into impending expiry.

---

## MVP Definition

### Launch With (v14.3 — this milestone)

- [ ] Fix reflected XSS in device approval page — CodeQL error, unacceptable to ship open
- [ ] Fix path injection in vault_service.py (both lines) — arbitrary file deletion/read risk
- [ ] Fix path injection in main.py (both lines) — installer script traversal
- [ ] Fix ReDoS in security.py mask_pii — polynomial backtrack on attacker-controlled job output
- [ ] Remove legacy API_KEY crash — silent startup failure is a production operational hazard
- [ ] Admin key generation CLI — enables all licence operations at Axiom Labs
- [ ] Grace period on expiry (30 days default, `grace_days` in payload) — required for air-gap
- [ ] Boot log / monotonic timestamp — clock-rollback detection without network dependency
- [ ] Licence status extended in GET /api/licence — operators see valid/grace/expired + days
- [ ] Node limit enforcement at enrollment — basic commercial licence boundary

### Add After Validation (v14.x)

- [ ] Dashboard licence banner on grace/expired state — needs frontend component work beyond
  the endpoint change; ship as a follow-up once the backend status field is stable
- [ ] Customer-specific grace period in payload — `grace_days` field already in keygen tool
  for v14.3; documenting operator workflows for variable grace is a docs task
- [ ] Licence expiry webhook notification — needs notification system (not yet built)

### Future Consideration (v15+)

- [ ] Licence issuance portal (DIST-04) — web UI when customer volume justifies it
- [ ] Periodic in-process re-validation (DIST-05) — only needed if boot-log gap proves exploited
- [ ] Licence-scoped per-feature flags by tier — currently all-or-nothing EE; per-feature gating
  requires more payload fields and more EE plugin wiring

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Fix XSS (device_approve_page) | HIGH — security alert | LOW | P1 |
| Fix path injection x4 | HIGH — security alert | LOW | P1 |
| Fix ReDoS (security.py) | MEDIUM — warning severity, DoS vector | LOW | P1 |
| Remove API_KEY crash | HIGH — operational stability | LOW | P1 |
| Admin key generation CLI | HIGH — enables all licensing | MEDIUM | P1 |
| Grace period on expiry | HIGH — air-gap operator requirement | MEDIUM | P1 |
| Boot log / clock-rollback detection | MEDIUM — fraud deterrence | MEDIUM | P1 |
| Licence status in GET /api/licence | MEDIUM — operator visibility | LOW | P1 |
| Node limit enforcement | MEDIUM — commercial boundary | LOW | P2 |
| Dashboard grace/expired banner | MEDIUM — visibility UX | LOW | P2 |

**Priority key:**
- P1: Must have for v14.3 launch
- P2: Should have, add in v14.x point release
- P3: Nice to have, v15+ consideration

---

## Implementation Notes by Feature

### XSS Fix (main.py — device_approve_page)

The vulnerability is the `HTMLResponse` f-string where `user_code` (a GET query parameter) is
interpolated directly into HTML. Two injection points in the same function:
1. `<div class="code" id="display-code">{user_code or "(no code provided)"}</div>`
2. `<input type="hidden" name="user_code" value="{user_code}">`

Fix: `from markupsafe import escape` and apply `escape(user_code)` at both sites. `markupsafe`
is already a transitive dependency (Starlette pulls in Jinja2 which requires markupsafe).

### Path Injection Fix (vault_service.py + main.py)

**vault_service.py:52-54** — `get_artifact_path(artifact_id)` does
`os.path.join(VAULT_DIR, artifact_id)`. Since `artifact_id` is a UUID generated server-side in
`store_artifact`, the real-world risk is low — but CodeQL correctly flags the function signature
as accepting any string. The delete path (`delete_artifact`) calls this function with the
database-stored ID, which is also fine in practice, but the type signature is the problem.

Fix: resolve and assert relative to base using `pathlib`:
```python
base = Path(VAULT_DIR).resolve()
candidate = (base / artifact_id).resolve()
if not candidate.is_relative_to(base):
    raise ValueError(f"Invalid artifact path: {artifact_id}")
```
`Path.is_relative_to()` is Python 3.9+. The codebase targets 3.11+, so this is safe.

**main.py two locations** — installer script reads use user-controlled path components.
Apply the same pattern with the appropriate base directory.

### ReDoS Fix (security.py:79 — mask_pii EMAIL_REGEX)

Current regex: `r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'`

The trailing `[a-zA-Z0-9-.]+` has character-class overlap with the middle group on inputs that
lack an `@`, allowing polynomial backtracking when the regex engine tries all combinations.

Two approaches (either resolves the alert):
1. **Length guard**: `if len(data) > 1000: return data` before the `re.sub` calls — fast, no
   regex change, defensible (job output over 1000 chars won't be PII-masked, acceptable tradeoff)
2. **Non-backtracking regex**: `r'[^\s@]+@[^\s@]+\.[^\s@]+'` — negated character classes
   cannot backtrack into each other, eliminating the polynomial behaviour

Approach 2 is preferred: it is semantically equivalent for the email masking use case and
does not silently skip masking on long strings.

### Licence Key Generation Tooling

Wire format (established): `base64url_nopad(json_payload).base64url_nopad(ed25519_sig)`

Payload schema for v14.3 (backwards-compatible addition of `grace_days` and `node_limit`):
```json
{
  "customer_id": "acme-corp",
  "tier": "ee",
  "node_limit": 50,
  "exp": 1785532800,
  "issued_at": 1753996800,
  "grace_days": 30,
  "features": ["foundry", "audit", "webhooks", "triggers", "rbac",
               "resource_limits", "service_principals", "api_keys", "executions"]
}
```

Existing keys without `grace_days` or `node_limit` must be handled by the validator with
sensible defaults (`grace_days=30`, no node limit). This is backwards-compatible.

Tool location options (in order of preference):
1. New `generate_licence.py` script in the private `axiom-ee` repo alongside `ee/plugin.py` —
   keeps the signing private key in the same trusted context as the verification public key
2. Add `--generate-licence` subcommand to `toms_home/.agents/tools/admin_signer.py` — simpler
   but mixes job-signing and licence-signing tooling in one script

Preferred: option 1. The private key material for licence signing is separate from the job
signing key material and should live separately.

### Boot Log / Monotonic Timestamp

Location: `secrets/boot.log` (JSON Lines format, one entry per startup).

Entry format:
```json
{"t": 1753996800, "hmac": "sha256hex_of_this_entry_content_chained_to_prev"}
```

On startup:
1. Read all existing entries, verify each entry's HMAC using `ENCRYPTION_KEY`
2. Verify that each `t` is >= the previous `t` minus `CLOCK_TOLERANCE_SECS` (default: 120s,
   accounts for NTP corrections and container restart timing variance)
3. If chain HMAC is broken: EE features disabled regardless of `LICENCE_STRICT_CLOCK` setting —
   this indicates log tampering, not legitimate clock variance
4. If timestamps go backward beyond tolerance AND `LICENCE_STRICT_CLOCK=true`: refuse EE,
   log critical warning. If `LICENCE_STRICT_CLOCK=false` (default): log warning only
5. Append a new entry with the current timestamp and computed HMAC
6. Prune the log to the last 100 entries

The HMAC uses `ENCRYPTION_KEY` (Fernet key, already present). An attacker who can write to the
`secrets/` volume but does not know `ENCRYPTION_KEY` cannot forge valid chain entries.

Key design decisions:
- **Default: warn only on clock rollback.** NTP corrections, hypervisor migrations, and container
  restarts legitimately cause small backward jumps. `LICENCE_STRICT_CLOCK=true` enables hard
  rejection for high-security deployments.
- **The log is not a substitute for a network time source.** It detects deliberate large rollbacks
  (e.g. setting the clock back 1 year to bypass expiry) while tolerating operational drift.
- **File location**: `secrets/` is already a mounted volume and contains sensitive material.
  Using it for the boot log is consistent with existing practice.

### Grace Period Logic

The expiry check in the EE plugin's `register()` changes from binary to three-state:

```
exp > now                                          VALID   — all EE features active
exp <= now AND exp + (grace_days * 86400) > now    GRACE   — EE active, warning on startup
exp + (grace_days * 86400) <= now                  EXPIRED — CE fallback, EE stubs mounted
```

`grace_days` from the licence payload; default 30 if field absent (backwards compat).

`app.state.licence` gets an additional `licence_status` field: `"valid"`, `"grace"`, or
`"expired"`. The `GET /api/licence` endpoint surfaces this plus `days_until_expiry` (negative
number during grace period, e.g. `-5` means 5 days past expiry but still within grace window).

---

## Competitor Feature Analysis

| Feature | HashiCorp Vault Enterprise | JetBrains IDEs | Axiom Approach |
|---------|----------------------------|----------------|----------------|
| Licence format | Signed JWT | Signed binary blob | Ed25519-signed JSON (same security, simpler) |
| Air-gap expiry | Grace period + manual check | Ignores clock (trusts OS) | Grace period + HMAC-chained boot log |
| Clock tampering | NTP-based, not boot log | Not enforced | Boot log with configurable tolerance |
| Node limits | Per-cluster count at API layer | Per-machine activation | Count at enrollment + payload field |
| Revocation | Online CRL | Serial denylist (online) | Manual reissuance (sufficient at current scale) |
| Key delivery | Licence file or env var | File download | Env var (already implemented) |

The boot log approach is more tamper-resistant than JetBrains (which trusts the OS clock) and
more air-gap-friendly than HashiCorp (which requires network for some validation paths). The
trade-off is that a determined attacker with `ENCRYPTION_KEY` access can forge log entries —
but at that point they have already compromised the application's entire secret material.

---

## Sources

- Codebase direct inspection (HIGH confidence):
  - `puppeteer/agent_service/security.py` — API_KEY crash, ReDoS regex
  - `puppeteer/agent_service/main.py` — XSS in HTMLResponse, path injection, licence fast-path
  - `puppeteer/agent_service/services/vault_service.py` — path injection in artifact handling
  - `puppeteer/agent_service/tests/test_licence.py` — wire format confirmation
  - `puppeteer/agent_service/ee/__init__.py` — EE plugin loading architecture
- CodeQL query documentation: `py/reflective-xss`, `py/path-injection`, `py/polynomial-redos`
  (MEDIUM confidence — confirmed by codebase context)
- pathlib path traversal prevention pattern (HIGH confidence):
  [Python pathlib docs](https://docs.python.org/3/library/pathlib.html),
  [Preventing Directory Traversal in Python](https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/)
- Air-gapped licence patterns (MEDIUM confidence):
  [Keygen offline cryptography docs](https://keygen.sh/docs/api/cryptography/),
  [LicenseSpring air-gap docs](https://docs.licensespring.com/product-configuration/license-policies/air-gapped-license-policies),
  [hoop.dev air-gap licensing](https://hoop.dev/blog/air-gapped-software-licensing-how-to-securely-license-without-internet-access/)
- markupsafe XSS escaping: FastAPI/Starlette transitive dep, standard pattern (HIGH confidence)
- Todo files in `.planning/todos/pending/`: direct specification of the three work items

---

*Feature research for: Axiom v14.3 — Security Hardening + EE Licensing*
*Researched: 2026-03-26*

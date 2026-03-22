---
phase: 39-ee-test-keypair-dev-install
verified: 2026-03-20T22:00:00Z
status: human_needed
score: 8/8 must-haves verified (automated); EEDEV-03/04/05 require live stack
re_verification: false
human_verification:
  - test: "Run verify_ee_install.py --case valid with stack running + valid licence injected"
    expected: "All EEDEV-03 checks pass: GET /api/licence returns edition=enterprise, customer_id=axiom-dev-test, expires field present, GET /api/features all 8 keys true"
    why_human: "Requires live Docker stack running with AXIOM_LICENCE_KEY env var injected — cannot verify against API without running containers"
  - test: "Run verify_ee_install.py --case expired with stack running + expired licence injected"
    expected: "All EEDEV-04 checks pass: GET /api/licence returns edition=community, GET /api/features all false"
    why_human: "Requires stack restart with expired AXIOM_LICENCE_KEY — runtime behaviour cannot be verified statically"
  - test: "Run verify_ee_install.py --case absent with stack running without AXIOM_LICENCE_KEY"
    expected: "All EEDEV-05 checks pass: stack does not crash, GET /api/features all false, GET /api/licence returns edition=community"
    why_human: "Requires stack restart without any AXIOM_LICENCE_KEY — CE-degraded mode is a runtime assertion"
---

# Phase 39: EE Test Keypair + Dev Install Verification Report

**Phase Goal:** A local Ed25519 test keypair is in place and the EE plugin is running with the test public key, enabling all licence lifecycle tests without a Cython rebuild
**Verified:** 2026-03-20T22:00:00Z
**Status:** human_needed (all automated checks pass; three cases require a live stack)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Ed25519 test keypair files exist in mop_validation/secrets/ee/ and are NOT the production placeholder | VERIFIED | `ee_test_private.pem` (119B, 0600) and `ee_test_public.pem` (113B, 0644) present; PEM headers confirmed BEGIN PRIVATE KEY / BEGIN PUBLIC KEY |
| 2 | axiom-ee plugin.py `_LICENCE_PUBLIC_KEY_BYTES` contains the test key raw bytes (32-byte non-zero) | VERIFIED | Line 16 of plugin.py: `b'e~g\x98\xbf...'` — 32 bytes confirmed, all non-zero, contains comment "test key — patched by patch_ee_source.py" |
| 3 | pip import of ee.plugin resolves to the .py source file, not a compiled .so | VERIFIED | No `plugin*.so` files exist in axiom-ee/ee/; axiom-ee confirmed editable-installed (Editable project location: /home/thomas/Development/axiom-ee) in MoP venv |
| 4 | compose.server.yaml passes AXIOM_LICENCE_KEY through to the agent container | VERIFIED | Line 71 of puppeteer/compose.server.yaml: `- AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` |
| 5 | A valid signed test licence string is written to mop_validation/secrets/ee/ee_valid_licence.env | VERIFIED | File exists (318B); AXIOM_LICENCE_KEY= prefix confirmed; payload round-tripped: customer_id=axiom-dev-test, exp=2089401183 (~2089, far future), 8 features |
| 6 | An expired signed test licence string is written to mop_validation/secrets/ee/ee_expired_licence.env | VERIFIED | File exists (318B); payload exp=1704067200 (2024-01-01 UTC, deterministic past timestamp) confirmed |
| 7 | verify_ee_install.py --case valid returns [PASS] EEDEV-03 when stack is running with valid licence injected | HUMAN NEEDED | Script structure fully verified (parses, EEDEV-03 labels, Authorization Bearer, /api/licence, /api/features all present); runtime requires live stack |
| 8 | verify_ee_install.py --case expired returns [PASS] EEDEV-04 after manual restart with expired licence | HUMAN NEEDED | Script structure verified (EEDEV-04 label, community edition check, all-false features check); runtime requires live stack |
| 9 | verify_ee_install.py --case absent returns [PASS] EEDEV-05 after manual restart with no licence key | HUMAN NEEDED | Script structure verified (EEDEV-05 label, community edition check, stack-alive check); runtime requires live stack |

**Score:** 6/6 automated truths verified; 3/3 runtime truths need human verification.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `mop_validation/scripts/generate_ee_keypair.py` | One-time Ed25519 keypair generator | VERIFIED | 72 lines; generates Ed25519PrivateKey, saves PKCS8 PEM; --force guard; safety note printed; file permissions set (0600/0644) |
| `mop_validation/scripts/patch_ee_source.py` | Editable install + public key patch | VERIFIED | 209 lines; deletes stale .so files; lambda re.sub for \xNN safety; skips pip re-install if already editable; --restore flag implemented; MoP venv python detection |
| `mop_validation/scripts/generate_ee_licence.py` | Generates valid + expired test licences | VERIFIED | 135 lines; load_pem_private_key; _b64url_encode with urlsafe_b64encode + rstrip; make_licence_key matching licence_service.py wire format; writes both .env files |
| `mop_validation/scripts/verify_ee_install.py` | API-level verifier for EEDEV-03/04/05 | VERIFIED | 14KB; all three case handlers; check/load_env/wait_for_stack/get_admin_token helpers; [PASS]/[FAIL] pattern; exit code 0/1; urllib3 warning suppressed |
| `mop_validation/secrets/ee/ee_test_private.pem` | PKCS8 PEM private key | VERIFIED | Contains "BEGIN PRIVATE KEY"; 119 bytes; 0600 permissions |
| `mop_validation/secrets/ee/ee_test_public.pem` | SubjectPublicKeyInfo PEM public key | VERIFIED | Contains "BEGIN PUBLIC KEY"; 113 bytes; 0644 permissions |
| `mop_validation/secrets/ee/ee_valid_licence.env` | AXIOM_LICENCE_KEY=<valid_signed_licence> | VERIFIED | 318 bytes; AXIOM_LICENCE_KEY= prefix; base64url.base64url format; payload exp=2089401183, all 8 features, customer_id=axiom-dev-test |
| `mop_validation/secrets/ee/ee_expired_licence.env` | AXIOM_LICENCE_KEY=<expired_signed_licence> | VERIFIED | 318 bytes; AXIOM_LICENCE_KEY= prefix; payload exp=1704067200 (deterministic 2024-01-01) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| generate_ee_keypair.py | ee_test_private.pem | `private_bytes(PKCS8, NoEncryption)` | VERIFIED | Line 48-52: `private_key.private_bytes(encoding=PEM, format=PKCS8, encryption_algorithm=NoEncryption())` |
| patch_ee_source.py | axiom-ee/ee/plugin.py | `re.sub on _LICENCE_PUBLIC_KEY_BYTES` | VERIFIED | PATTERN=`^_LICENCE_PUBLIC_KEY_BYTES: bytes = .*$`; lambda replacement avoids \xNN escape issue; plugin.py confirmed patched |
| patch_ee_source.py | pip install -e | `subprocess.run(['pip', 'install', '-e', ...])` | VERIFIED | `_pip_install_editable()` calls pip with `-e AXIOM_EE_DIR`; skips if already editable; axiom-ee confirmed editable in MoP venv |
| generate_ee_licence.py | ee_test_private.pem | `serialization.load_pem_private_key()` | VERIFIED | Line 31: `from cryptography.hazmat.primitives.serialization import load_pem_private_key`; line 93: used with private_key_path |
| generate_ee_licence.py | ee_valid_licence.env + ee_expired_licence.env | `base64url(json_payload).base64url(ed25519_sig)` | VERIFIED | `_b64url_encode` uses `urlsafe_b64encode(data).rstrip(b"=").decode()`; `make_licence_key` uses compact JSON separators; both .env files written |
| verify_ee_install.py | GET /api/licence | `requests.get with Authorization: Bearer <admin_token>` | VERIFIED | Lines 164-169: `headers={"Authorization": f"Bearer {token}"}`, `verify=False`, `timeout=10` |
| verify_ee_install.py | GET /api/features | `requests.get (unauthenticated)` | VERIFIED | `api/features` endpoint called in wait_for_stack and in each case handler |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EEDEV-01 | 39-01-PLAN.md | Local Ed25519 test keypair generated and stored in mop_validation/secrets/ | SATISFIED | ee_test_private.pem (PKCS8, 0600) and ee_test_public.pem (SPKI, 0644) exist; public key raw bytes = 32 non-zero bytes confirmed |
| EEDEV-02 | 39-01-PLAN.md | axiom-ee EE plugin patched with test public key bytes and installed as editable source (pip install -e) — no Cython rebuild required | SATISFIED | plugin.py line 16 contains test key bytes; no plugin*.so files; axiom-ee editable in MoP venv; AXIOM_LICENCE_KEY passthrough in compose.server.yaml |
| EEDEV-03 | 39-02-PLAN.md | Valid test licence generated; GET /api/licence returns correct customer_id, exp, features | HUMAN NEEDED | generate_ee_licence.py produces ee_valid_licence.env with correct payload; verify_ee_install.py --case valid script is structurally complete; live API call not verified |
| EEDEV-04 | 39-02-PLAN.md | Expired test licence verified: after restart, GET /api/features returns all false; GET /api/licence shows expired state | HUMAN NEEDED | ee_expired_licence.env has exp=1704067200 (past); verify_ee_install.py --case expired structurally complete; live API call not verified |
| EEDEV-05 | 39-02-PLAN.md | Missing AXIOM_LICENCE_KEY: EE starts in CE-degraded mode (no crash, all features false) | HUMAN NEEDED | compose.server.yaml uses `${AXIOM_LICENCE_KEY:-}` default (empty string when unset); verify_ee_install.py --case absent structurally complete; runtime not verified |

All 5 requirement IDs accounted for. REQUIREMENTS.md marks all 5 as Complete for Phase 39.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `generate_ee_licence.py` | 39 | `COMPOSE_FILE = MOP_DIR / ".worktrees" / "axiom-split" / "puppeteer" / "compose.server.yaml"` | Warning | Worktree path does not exist on this machine. COMPOSE_FILE is only used in printed restart instructions (lines 113-127), not in any functional code path. Operator copy-pasting the printed commands will get a wrong path. The AXIOM_LICENCE_KEY passthrough itself was correctly applied to `puppeteer/compose.server.yaml`. |
| `verify_ee_install.py` | 54 | `COMPOSE_FILE = MOP_DIR / ".worktrees" / "axiom-split" / "puppeteer" / "compose.server.yaml"` | Warning | Same as above — only affects printed restart reminder strings (lines 142-143, 230-231, 297-298), not the API assertion logic. |

No blocker anti-patterns found. Both warnings affect operator UX (wrong compose file path in printed hints) but do not affect the verification assertions themselves.

### Human Verification Required

#### 1. EEDEV-03: Valid licence active

**Test:** With the EE stack running in the axiom-split worktree (or main puppeteer/compose.server.yaml), inject the valid licence key and restart the agent:
```bash
AXIOM_LICENCE_KEY=$(grep AXIOM_LICENCE_KEY ~/Development/mop_validation/secrets/ee/ee_valid_licence.env | cut -d= -f2-)
docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml stop agent
AXIOM_LICENCE_KEY="$AXIOM_LICENCE_KEY" docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml up -d agent
python3 ~/Development/mop_validation/scripts/verify_ee_install.py --case valid
```
**Expected:** All checks pass — `[PASS] EEDEV-03 — edition == enterprise`, `[PASS] EEDEV-03 — customer_id == axiom-dev-test`, expires field present, all 8 EE features true.
**Why human:** Requires live Docker containers with the EE plugin loaded and the licence key injected as an environment variable.

**Note on COMPOSE_FILE path:** The scripts print restart commands using the non-existent worktree path. Use the correct path shown above (`puppeteer/compose.server.yaml` in main repo).

#### 2. EEDEV-04: Expired licence

**Test:** Inject the expired licence and restart:
```bash
AXIOM_LICENCE_KEY=$(grep AXIOM_LICENCE_KEY ~/Development/mop_validation/secrets/ee/ee_expired_licence.env | cut -d= -f2-)
docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml stop agent
AXIOM_LICENCE_KEY="$AXIOM_LICENCE_KEY" docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml up -d agent
python3 ~/Development/mop_validation/scripts/verify_ee_install.py --case expired
```
**Expected:** `[PASS] EEDEV-04 — edition == community after expired licence`, `[PASS] EEDEV-04 — all EE features false`.
**Why human:** Requires live stack restart to load the expired key into the running plugin.

#### 3. EEDEV-05: No licence key (CE-degraded mode)

**Test:** Restart agent without any AXIOM_LICENCE_KEY:
```bash
docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml stop agent
docker compose -f ~/Development/master_of_puppets/puppeteer/compose.server.yaml up -d agent
python3 ~/Development/mop_validation/scripts/verify_ee_install.py --case absent
```
**Expected:** `[PASS] EEDEV-05 — stack started without crash`, `[PASS] EEDEV-05 — all EE features false when no licence key`, `[PASS] EEDEV-05 — edition == community`.
**Why human:** CE-degraded mode is a runtime behaviour — requires observing that the stack starts without exception and the API returns the correct degraded state.

### Gaps Summary

No blocking gaps. All automated prerequisites for the phase goal are in place:

- The test keypair is generated and non-placeholder.
- The EE plugin source is patched and the editable install is active.
- The licence signing scripts produce correctly structured .env files.
- The compose passthrough is wired.
- The verification scripts are structurally complete and correct.

The three EEDEV-03/04/05 truths cannot be verified without running the Docker stack. These are deliberately runtime integration tests — the phase goal explicitly targets enabling all licence lifecycle tests. The tooling to run those tests is complete and wired; the tests themselves are deferred to human/CI execution.

One warning-level issue exists: both `generate_ee_licence.py` and `verify_ee_install.py` hardcode `COMPOSE_FILE` pointing to a non-existent worktree path. This only affects the printed restart hints, not the API assertions. The operator must use `puppeteer/compose.server.yaml` in the main repo instead. This should be corrected in a follow-up to avoid operator confusion.

---

_Verified: 2026-03-20T22:00:00Z_
_Verifier: Claude (gsd-verifier)_

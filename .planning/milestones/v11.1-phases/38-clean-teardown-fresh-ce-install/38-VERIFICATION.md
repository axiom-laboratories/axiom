---
phase: 38-clean-teardown-fresh-ce-install
verified: 2026-03-20T19:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Run teardown_soft.sh against live axiom-split CE stack, then run docker compose up -d and confirm nodes re-enroll without new JOIN_TOKENs"
    expected: "Node re-enrollment succeeds using existing certs from secrets/ — no new token required"
    why_human: "Requires a live Incus node environment and running CE stack to confirm cert re-use behaviour end-to-end"
  - test: "Run verify_ce_install.py against a cold-started axiom-split CE stack"
    expected: "All INST-03 checks print [PASS]: 13 tables, 8 feature keys all false, edition == community"
    why_human: "Requires the axiom-split worktree CE stack to be fully up — cannot be confirmed without a running Postgres container and live API"
  - test: "Perform INST-04 manual admin re-seed test (steps embedded in verify_ce_install.py)"
    expected: "Password A continues to work after ADMIN_PASSWORD env change; password B login returns 401"
    why_human: "Requires modifying the live stack environment and restarting — explicitly documented as non-automatable in the plan"
---

# Phase 38: Clean Teardown and Fresh CE Install Verification Report

**Phase Goal:** Provide idempotent teardown scripts and a CE install verifier that allows developers to reliably reset the axiom-split CE stack and confirm a clean cold-start state.
**Verified:** 2026-03-20T19:30:00Z
**Status:** passed (with human verification items)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | teardown_soft.sh stops CE stack containers and removes pgdata only, preserving all other volumes | VERIFIED | `docker compose ... down` (no `-v`) + separate `docker volume rm puppeteer_pgdata` with `2>/dev/null` fallback |
| 2 | LXC node secrets/ dirs are untouched by soft teardown — nodes can re-enroll after compose up | VERIFIED | Soft script contains zero `incus` calls; final echo confirms "LXC node secrets untouched" |
| 3 | teardown_hard.sh removes all named Docker volumes AND wipes /home/ubuntu/secrets/ on axiom-node-* containers | VERIFIED | `down -v --remove-orphans` removes all volumes; `incus exec "$name" -- rm -rf /home/ubuntu/secrets/` for each matching container |
| 4 | Hard teardown skips stopped/unreachable LXC nodes with [WARN] rather than aborting | VERIFIED | `|| echo "  [WARN] Could not clear $name ..."` on incus exec; `incus list` piped with `|| true`; global `set -e` absent (`set -uo pipefail` only) |
| 5 | Both scripts target the axiom-split CE stack, not the main branch compose file | VERIFIED | Both set `CE_DIR="$REPO_ROOT/.worktrees/axiom-split/puppeteer"` |
| 6 | verify_ce_install.py polls /api/health before firing checks and exits 1 on stack-not-ready | VERIFIED | `wait_for_stack()` polls every 3s up to 90s; `sys.exit(1)` on timeout |
| 7 | Script queries Postgres via docker exec psql and checks for exactly 13 tables (excluding apscheduler_jobs) | VERIFIED | `docker exec {container} psql -U puppet -d puppet_db -t -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"` with `count == CE_TABLE_COUNT` (13) |
| 8 | Script calls GET /api/features and confirms all 8 expected keys are present and all values are false | VERIFIED | `check_features()` verifies `set(features.keys()) == CE_FEATURE_KEYS` (8 keys) AND `not any(features.values())` |
| 9 | Script calls GET /api/licence and confirms edition == community | VERIFIED | `check_licence_ce()` returns `resp.json().get("edition") == "community"` with Bearer auth |
| 10 | INST-04 manual test steps documented in script comments | VERIFIED | `INST_04_MANUAL_TEST_STEPS` module-level constant with 7-step procedure; printed as reminder during execution |
| 11 | Script exits 0 on all-pass, non-zero on any failure | VERIFIED | `sys.exit(0)` when `passed_count == total`; `sys.exit(1)` otherwise; fast `sys.exit(1)` on stack-not-ready |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `/home/thomas/Development/mop_validation/scripts/teardown_soft.sh` | Soft teardown — stops containers, removes pgdata only (INST-01) | VERIFIED | 21 lines, executable (`-rwxrwxr-x`), bash syntax OK, commit `4d172ed` |
| `/home/thomas/Development/mop_validation/scripts/teardown_hard.sh` | Hard teardown — all volumes + LXC secrets (INST-02) | VERIFIED | 32 lines, executable (`-rwxrwxr-x`), bash syntax OK, commit `c6cb352` |
| `/home/thomas/Development/mop_validation/scripts/verify_ce_install.py` | CE install verification gate (INST-03 + INST-04) | VERIFIED | 295 lines, executable (`-rwxrwxr-x`), Python AST parse OK, commit `76520b7` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| teardown_soft.sh | `.worktrees/axiom-split/puppeteer/compose.server.yaml` | `COMPOSE_FILE` variable | WIRED | `CE_DIR="$REPO_ROOT/.worktrees/axiom-split/puppeteer"` and `COMPOSE_FILE="$CE_DIR/compose.server.yaml"` — present in script |
| teardown_hard.sh | `.worktrees/axiom-split/puppeteer/compose.server.yaml` | `COMPOSE_FILE` variable | WIRED | Same path construction; `down -v --remove-orphans` uses it |
| teardown_hard.sh | `incus list --format csv` | `while IFS=',' read -r name rest` loop with `axiom-node-*` match | WIRED | Loop body confirmed: name trimmed of quotes, pattern match, `incus exec` with `|| echo [WARN]` |
| verify_ce_install.py | `puppeteer-db-1` (postgres container) | `subprocess docker exec psql` | WIRED | `get_postgres_container()` uses `docker ps --filter "name=puppeteer-db"` with fallback; `check_table_count()` issues live psql query |
| verify_ce_install.py | `https://localhost:8001/api/features` | `requests.get` with `verify=False` | WIRED | `check_features()` calls endpoint, validates 8 keys AND all-false values |
| verify_ce_install.py | `https://localhost:8001/api/licence` | `requests.get` with Bearer token | WIRED | `check_licence_ce()` uses token from `get_admin_token()` login |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INST-01 | 38-01-PLAN.md | Soft teardown preserves Root CA and node secrets/ dirs — stops containers and clears DB data only | SATISFIED | teardown_soft.sh: `docker compose down` (no -v) + explicit `docker volume rm puppeteer_pgdata`; no incus calls |
| INST-02 | 38-01-PLAN.md | Hard teardown runs `docker compose down -v --remove-orphans` AND clears all LXC node secrets/ dirs | SATISFIED | teardown_hard.sh: `down -v --remove-orphans` + incus loop with `rm -rf /home/ubuntu/secrets/` |
| INST-03 | 38-02-PLAN.md | Fresh CE install produces 13 CE tables, GET /api/features all false, correctly seeded admin account | SATISFIED | verify_ce_install.py: table count check (excluding apscheduler_jobs), CE_FEATURE_KEYS 8-key all-false check, admin login + edition check |
| INST-04 | 38-02-PLAN.md | Admin password re-seed: ADMIN_PASSWORD env change does NOT overwrite DB password for existing user | SATISFIED (documented) | INST_04_MANUAL_TEST_STEPS constant with 7-step procedure; printed as reminder during script execution — explicitly non-automatable |

No orphaned requirements found. All 4 IDs mapped to phases in REQUIREMENTS.md match the plans that claimed them, and the implementations are confirmed in the codebase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

No TODOs, FIXMEs, placeholders, empty implementations, or stub patterns detected in any of the three files.

---

### Human Verification Required

#### 1. Node Re-Enrollment After Soft Teardown

**Test:** Run `teardown_soft.sh`, then `docker compose -f .worktrees/axiom-split/puppeteer/compose.server.yaml up -d`, then verify axiom-node-* containers reconnect without needing a new JOIN_TOKEN.
**Expected:** Nodes discover their existing certs in `secrets/` and re-enroll successfully. No re-enrollment required.
**Why human:** Requires live Incus containers (axiom-node-*) and a running CE stack; cert re-use path can only be confirmed at runtime.

#### 2. INST-03 Automated Gate Against Live CE Stack

**Test:** Run `python3 /home/thomas/Development/mop_validation/scripts/verify_ce_install.py` against a cold-started axiom-split CE stack.
**Expected:** All four checks print `[PASS]`: table count == 13, all 8 feature keys false, edition == community, admin login succeeds.
**Why human:** Requires the axiom-split worktree stack to be running with Postgres accessible. The table count in particular depends on the actual axiom-split `db.py` schema matching the expected 13 tables.

#### 3. INST-04 Admin Re-seed Safety (Manual Test)

**Test:** Follow the 7-step procedure in `INST_04_MANUAL_TEST_STEPS` inside `verify_ce_install.py`.
**Expected:** After changing `ADMIN_PASSWORD` env var and restarting the stack, login with the original password (A) succeeds and login with the new env var value (B) returns 401.
**Why human:** Requires modifying and restarting the live stack environment. Explicitly documented as non-automatable in the plan design.

---

### Gaps Summary

No gaps found. All automated checks pass.

The phase delivers exactly what the goal required:
- Two idempotent bash teardown scripts (`teardown_soft.sh`, `teardown_hard.sh`) with correct volume scoping, LXC best-effort error handling, and axiom-split targeting.
- One Python verification gate (`verify_ce_install.py`) implementing all three INST-03 automated checks and embedding the INST-04 manual test procedure.

Three human verification items remain — these are inherent to the nature of the work (live stack behaviour, external Incus nodes) rather than implementation gaps.

---

_Verified: 2026-03-20T19:30:00Z_
_Verifier: Claude (gsd-verifier)_

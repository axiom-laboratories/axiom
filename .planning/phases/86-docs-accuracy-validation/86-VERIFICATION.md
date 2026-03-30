---
phase: 86-docs-accuracy-validation
verified: 2026-03-29T18:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 86: Docs Accuracy Validation — Verification Report

**Phase Goal:** Docs stay accurate as the API evolves — a validator catches stale routes, CLI references, and env vars in documentation before they reach users.
**Verified:** 2026-03-29T18:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `tools/generate_openapi.py` exists, accepts `--url`, writes snapshot | VERIFIED | File exists at `tools/generate_openapi.py`, `--url` argparse flag on line 33, writes to `docs/docs/api-reference/openapi.json` on line 61 |
| 2 | `tools/validate_docs.py` exists, exits 2 on stub/missing snapshot | VERIFIED | File exists, `sys.exit(2)` on lines 62 and 68 for missing/empty spec |
| 3 | Validator exits 1 on any WARN/FAIL, exits 0 when all pass | VERIFIED | `sys.exit(1)` on line 247 when warn_count > 0 or fail_count > 0; `main()` returns without exit when all pass |
| 4 | Validator checks API routes against openapi.json with file:line output | VERIFIED | ROUTE_RE regex on lines 29-33, `_openapi_path_matches()` function lines 113-149, file:line output format in `scan_file()` |
| 5 | Validator checks `axiom-push <subcommand>` against `mop_sdk/cli.py` | VERIFIED | CLI_RE regex line 38, `get_registered_commands()` parses cli.py statically lines 73-78 |
| 6 | Validator checks backtick env vars against Python/shell/YAML source | VERIFIED | ENV_RE regex line 40, `var_in_source()` searches `.py`, `.sh`, `.yaml`, `.yml` in SEARCH_DIRS lines 81-106 |
| 7 | `docs/docs/api-reference/openapi.json` populated with real routes | VERIFIED | 116 routes confirmed by `python3 -c "import json; spec=json.load(...); print(len(spec.get('paths',{})))"` |
| 8 | `python tools/validate_docs.py` exits 0 on current codebase | VERIFIED | Ran live: 250 PASS, 0 WARN, 0 FAIL, exit code 0 |
| 9 | `.github/workflows/ci.yml` contains `docs-validate` job | VERIFIED | Job at lines 121-135 of ci.yml; runs `python tools/validate_docs.py`, no live stack dependency |

**Score:** 9/9 truths verified (7 plan must-haves + 2 CI must-haves from plan 86-02)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/generate_openapi.py` | OpenAPI snapshot generator | VERIFIED | 73 lines, substantive implementation, correct REPO_ROOT anchoring, error handling for all failure modes |
| `tools/validate_docs.py` | Docs accuracy validator | VERIFIED | 252 lines, full implementation; ROUTE_RE, CLI_RE, ENV_RE; three-tier PASS/WARN/FAIL; correct exit codes 0/1/2 |
| `docs/docs/api-reference/openapi.json` | 116-route live snapshot | VERIFIED | File exists, 116 paths in spec, not a stub |
| `.github/workflows/ci.yml` | CI job for docs-validate | VERIFIED | `docs-validate` job present, `ubuntu-latest`, Python 3.12, `pip install requests`, runs `python tools/validate_docs.py` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `validate_docs.py` | `docs/docs/api-reference/openapi.json` | `load_openapi_spec()` | WIRED | Loads spec from `REPO_ROOT / "docs" / "docs" / "api-reference" / "openapi.json"` line 56 |
| `validate_docs.py` | `mop_sdk/cli.py` | `get_registered_commands()` | WIRED | Reads `REPO_ROOT / "mop_sdk" / "cli.py"` line 75, regex-parses `add_parser(...)` calls |
| `validate_docs.py` | source dirs | `var_in_source()` | WIRED | Scans `puppeteer/`, `puppets/`, `mop_sdk/`, `tools/` for `.py`, `.sh`, `.yaml`, `.yml` |
| `ci.yml docs-validate` | `tools/validate_docs.py` | `run: python tools/validate_docs.py` | WIRED | Line 135 of ci.yml; runs from repo root, no path change |
| `generate_openapi.py` | `docs/docs/api-reference/openapi.json` | `out_path.write_text()` | WIRED | Writes to `REPO_ROOT / "docs" / "docs" / "api-reference" / "openapi.json"` line 61 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 86-01 | Validation script cross-references API routes in openapi.json snapshot against docs, outputs PASS/WARN/FAIL per route | SATISFIED | `validate_docs.py` ROUTE_RE + `_openapi_path_matches()`; live run shows 250 PASS, 0 FAIL; file:line output confirmed |
| DOC-02 | 86-01 | Script checks CLI flags and env var names in docs against `mop_sdk/cli.py` source | SATISFIED | CLI_RE + `get_registered_commands()`; ENV_RE + `var_in_source()`; all `axiom-push` invocations and env vars verified |
| DOC-03 | 86-02 | Validation script can be run in CI and exits non-zero on FAIL results | SATISFIED | `docs-validate` job in `.github/workflows/ci.yml` runs `python tools/validate_docs.py`; script exits 1 on WARN/FAIL (line 247), 2 on stub (lines 62/68); REQUIREMENTS.md checkbox is stale (shows `[ ]` but implementation is complete — tracker not updated after commit `dd29326`) |

**Note on DOC-03 tracking:** The REQUIREMENTS.md file still marks DOC-03 as `[ ]` (Pending) and the status table shows "Pending" — this is a tracker inconsistency. The actual implementation (`docs-validate` CI job, correct exit codes) satisfies the requirement fully. The checkbox should be updated to `[x]` and the table entry to "Complete".

---

### Commit Verification

All commits documented in SUMMARY exist in the repository:

| Commit | Message | Status |
|--------|---------|--------|
| `ace69a2` | feat(86-01): add tools/generate_openapi.py | VERIFIED |
| `d64c730` | feat(86-01): add tools/validate_docs.py | VERIFIED |
| `0152887` | feat(86-01): populate openapi.json snapshot from live stack | VERIFIED |
| `9c5d2be` | fix(86-01): resolve docs accuracy issues found by validate_docs.py | VERIFIED |
| `dd29326` | feat(86): add docs-validate CI job to ci.yml | VERIFIED |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tools/validate_docs.py` | 120, 141 | "placeholder" word in comments | Info | Not a code stub — docstring explains parameterised matching logic. No impact. |

No blockers. No stubs. No TODO/FIXME items.

---

### Human Verification Required

**1. GitHub Actions — docs-validate job runs and passes**

**Test:** Push a branch to GitHub and observe the Actions run.
**Expected:** `docs-validate` job appears in the CI matrix and completes green.
**Why human:** CI execution cannot be verified locally; requires a push to trigger the GitHub runner.

**2. Snapshot refresh workflow**

**Test:** With the Docker stack running, execute `python tools/generate_openapi.py` and confirm it overwrites `docs/docs/api-reference/openapi.json` with a fresh 116-route snapshot.
**Expected:** Script prints "Routes: 116" and exits 0.
**Why human:** Requires the live Docker stack; cannot be verified statically.

---

### Gaps Summary

No gaps. All 7 plan must-haves from 86-01 and all 7 from 86-02 are verified. The phase goal is fully achieved:

- The validator (`validate_docs.py`) catches stale routes, CLI references, and env vars in documentation
- The snapshot generator (`generate_openapi.py`) keeps the OpenAPI source-of-truth current
- The CI gate ensures regressions are caught before merging to main
- Current docs are clean: 250 PASS, 0 WARN, 0 FAIL

The only outstanding item is an administrative one: REQUIREMENTS.md DOC-03 checkbox and status table need updating from "Pending" to "Complete". This does not affect the implemented functionality.

---

_Verified: 2026-03-29T18:00:00Z_
_Verifier: Claude (gsd-verifier)_

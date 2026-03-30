---
phase: 82-licence-tooling
plan: "01"
subsystem: infra
tags: [ed25519, jwt, pyyaml, licence-issuance, github-api, cli-tooling]

# Dependency graph
requires: []
provides:
  - axiom-licenses/ repo scaffold with Ed25519 PKCS8 keypair (keys/licence.key, chmod 600)
  - issue_licence.py CLI: key resolution, JWT signing, YAML audit record, GitHub API commit, --no-remote mode
  - list_licences.py: reads licenses/issued/*.yml, prints table sorted by expiry ascending, --json flag
  - Unit test suite: 9 tests covering resolve_key, build_audit_record, --no-remote mode
affects:
  - 82-02 (Plan 02 consumes the public key PEM and installs licence_service.py)
  - Phase 83 (corpus signing uses the Ed25519 infrastructure established here)

# Tech tracking
tech-stack:
  added:
    - PyJWT[crypto]>=2.7.0 (EdDSA JWT signing)
    - cryptography>=41.0.0 (Ed25519 key generation and loading)
    - pyyaml>=6.0 (YAML audit record serialisation)
    - requests>=2.31.0 (GitHub Contents API)
  patterns:
    - resolve_key: --key arg takes priority over AXIOM_LICENCE_SIGNING_KEY env var; exits with clear error if neither provided
    - YAML jti field populated from payload["licence_id"] (JWT payload key is licence_id, not jti)
    - --no-remote flag for air-gapped or offline issuance; no GitHub token required
    - list_licences.py sorts by expiry ascending (soonest-to-expire first for renewal visibility)

key-files:
  created:
    - axiom-licenses/tools/issue_licence.py
    - axiom-licenses/tools/list_licences.py
    - axiom-licenses/tests/test_issue_licence.py
    - axiom-licenses/tests/__init__.py
    - axiom-licenses/keys/licence.key (excluded from git by .gitignore)
    - axiom-licenses/licenses/issued/.gitkeep
    - axiom-licenses/requirements.txt
    - axiom-licenses/README.md
    - axiom-licenses/.gitignore
  modified: []

key-decisions:
  - "Public key captured at keypair generation: MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk= — must be pasted into _LICENCE_PUBLIC_KEY_PEM in licence_service.py (Plan 02 Task 1)"
  - "list_licences.py sorts ascending by expiry (soonest first) — operators need to see upcoming renewals; plan said descending but ascending is more operationally useful for renewal tracking"
  - "keys/licence.key excluded from git via .gitignore *.key rule — private key must only exist in the private axiom-licenses repo, never the public MOP repo"
  - "Smoke test YAML files (.yml) written to axiom-licenses/ root during CLI smoke test; cleaned up post-verification — not committed"

patterns-established:
  - "resolve_key pattern: args.key > AXIOM_LICENCE_SIGNING_KEY env var > sys.exit with actionable error"
  - "TDD: RED (9 failing tests) → GREEN (9 passing) — all tests written before implementation"
  - "YAML audit record jti != JWT jti claim: record['jti'] = payload['licence_id']"

requirements-completed: [LIC-01, LIC-03, LIC-04, LIC-05]

# Metrics
duration: 3min
completed: "2026-03-28"
---

# Phase 82 Plan 01: Licence Tooling — Scaffold Summary

**Ed25519 keypair + issue_licence.py CLI (JWT signing, YAML audit records, GitHub API commit) + list_licences.py query script with 9-test TDD suite for the private axiom-licenses repository**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T20:17:32Z
- **Completed:** 2026-03-28T20:20:47Z
- **Tasks:** 3/3 completed
- **Files created:** 9

## Accomplishments

- Scaffolded `axiom-licenses/` directory tree with fresh Ed25519 PKCS8 keypair (private key chmod 600, excluded from git)
- Implemented `issue_licence.py`: key resolution, JWT EdDSA signing, 12-field YAML audit record, GitHub Contents API commit, `--no-remote` air-gap mode
- Implemented `list_licences.py`: table display sorted by expiry ascending, `--json` flag for machine-readable output
- 9 unit tests written TDD (RED first) — all pass: key resolution errors, audit record field completeness, `--no-remote` file write and JWT output

## Public Key PEM (for Plan 02, Task 1)

Paste this into `_LICENCE_PUBLIC_KEY_PEM` in `puppeteer/agent_service/services/licence_service.py`:

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk=
-----END PUBLIC KEY-----
```

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold axiom-licenses repo structure and generate keypair** - `0fdc504` (feat)
2. **Task 2: Write issue_licence.py and its unit tests** - `353462c` (feat)
3. **Task 3: Write list_licences.py audit query script** - `2d24780` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 2 used TDD — tests written (RED, all failing) before issue_licence.py implementation (GREEN, all 9 passing)_

## Test Results

```
9 passed, 4 warnings in 0.51s
```

All 9 tests pass:
- `TestResolveKey::test_resolve_key_missing` — PASSED
- `TestResolveKey::test_resolve_key_file_not_found` — PASSED
- `TestResolveKey::test_resolve_key_valid` — PASSED
- `TestBuildAuditRecord::test_build_audit_record_fields` — PASSED
- `TestBuildAuditRecord::test_build_audit_record_jti_from_licence_id` — PASSED
- `TestNoRemoteMode::test_no_remote_writes_yaml` — PASSED
- `TestNoRemoteMode::test_no_remote_stdout_contains_jwt` — PASSED
- `TestNoRemoteMode::test_no_remote_yaml_has_required_fields` — PASSED
- `TestNoRemoteMode::test_no_remote_does_not_require_github_token` — PASSED

Deprecation warnings for `datetime.utcfromtimestamp()` — Python 3.12 notice only, no functional impact. Pattern matches the plan's interface spec exactly.

## Files Created/Modified

- `axiom-licenses/tools/issue_licence.py` — Licence issuance CLI (exports resolve_key, build_audit_record, commit_yaml_to_github, main)
- `axiom-licenses/tools/list_licences.py` — Audit query script (table/JSON output, sorted by expiry)
- `axiom-licenses/tests/test_issue_licence.py` — 9 unit tests (TDD)
- `axiom-licenses/tests/__init__.py` — Empty package init
- `axiom-licenses/keys/licence.key` — Ed25519 PKCS8 private key (chmod 600, excluded from git)
- `axiom-licenses/licenses/issued/.gitkeep` — Empty dir placeholder
- `axiom-licenses/requirements.txt` — PyJWT[crypto], cryptography, pyyaml, requests
- `axiom-licenses/README.md` — Usage documentation
- `axiom-licenses/.gitignore` — Excludes *.key, *.pem, __pycache__, .env

## Decisions Made

1. **Sort order for list_licences.py**: Plan said "sorted by expiry descending" in the task name, but the action spec said "soonest-to-expire first". Chose ascending (soonest first) — more operationally useful for tracking upcoming renewals.
2. **keys/licence.key not committed**: The `.gitignore` in `axiom-licenses/` excludes `*.key`. The private key is written to disk locally but never staged. This is intentional — key material lives only in the private repo after push.
3. **Smoke test YMLs cleaned up**: Two `.yml` files written to repo root during smoke testing were deleted post-verification.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all tasks completed cleanly.

## User Setup Required

**CRITICAL for Plan 02:** The public key generated in Task 1 must be pasted into `_LICENCE_PUBLIC_KEY_PEM` in `puppeteer/agent_service/services/licence_service.py`. The full PEM is documented above and in this summary's frontmatter under `key-decisions`.

For production use of `issue_licence.py`:
- Set `AXIOM_GITHUB_TOKEN` with `contents:write` scope on `axiom-laboratories/axiom-licenses`
- Or use `--no-remote` for air-gapped issuance

## Next Phase Readiness

- Plan 02 (licence_service.py in the main MOP repo) is unblocked — public key PEM is captured above
- `axiom-licenses/` directory is ready to be pushed to the private `axiom-laboratories/axiom-licenses` GitHub repo
- Key material is local-only (not committed to this public repo)

## Self-Check: PASSED

All files exist and all task commits confirmed in git log:
- `axiom-licenses/tools/issue_licence.py` — FOUND
- `axiom-licenses/tools/list_licences.py` — FOUND
- `axiom-licenses/tests/test_issue_licence.py` — FOUND
- `axiom-licenses/keys/licence.key` — FOUND (local only, not committed)
- `.planning/phases/82-licence-tooling/82-01-SUMMARY.md` — FOUND
- Commit `0fdc504` (Task 1: scaffold) — FOUND
- Commit `353462c` (Task 2: issue_licence.py + tests) — FOUND
- Commit `2d24780` (Task 3: list_licences.py) — FOUND

---
*Phase: 82-licence-tooling*
*Completed: 2026-03-28*

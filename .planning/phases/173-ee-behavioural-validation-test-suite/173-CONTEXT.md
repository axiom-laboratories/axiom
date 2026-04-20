# Phase 173: EE Behavioural Validation Test Suite — Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an automated pytest test suite in `mop_validation/tests/` covering all 14 CE/EE
behavioural validation scenarios (VAL-01 through VAL-14). Zero manual-only steps.
`pytest mop_validation/tests/` must pass with zero skips.

**Not in scope:** new CE/EE feature work, mop_validation repo migration (Phase 174), licence
architecture analysis (Phase 175).

</domain>

<decisions>
## Implementation Decisions

### Stack Management (VAL-01 through VAL-12)

- **D-01:** Tests run in Incus LXC containers, NOT directly on the host, to avoid port clashing
  with the live puppeteer stack.
- **D-02:** Named LXCs per scenario group: `axiom-ce-tests` (CE scenarios) and `axiom-ee-tests`
  (EE scenarios). Parallel-safe. Follows the existing `provision_lxc_nodes.py` / `run_ce_scenario.py`
  Incus pattern.
- **D-03:** Module-scoped pytest fixtures bring up each LXC stack once per test group (CE module,
  EE module). Teardown after all tests in the group complete.
- **D-04:** Within the EE group, licence-state changes (VAL-06 through VAL-09) are applied by
  restarting only the agent container inside `axiom-ee-tests` using `incus exec` with a different
  `AXIOM_LICENCE_KEY` env var. The DB and node containers stay up — no full stack rebuild per state.

### Licence Fixtures (VAL-04 through VAL-09)

- **D-05:** Licence states tested via agent restart + API verification (realistic, no mocking).
  Test sequence per licence state: inject key → restart agent → poll readiness → assert API response.
- **D-06:** Pre-existing fixtures at `mop_validation/secrets/ee/ee_valid_licence.env` and
  `ee_expired_licence.env` are used for valid and expired cases.
- **D-07:** Grace-period and tampered licence fixtures are generated at conftest time by calling
  `mop_validation/scripts/generate_ee_licence.py` during test session setup. No pre-committed fixture
  files for these states — always fresh.

### Dashboard UI Assertion (VAL-06)

- **D-08:** VAL-06 ("GRACE banner visible in dashboard") is covered by TWO assertions:
  1. API: `GET /api/licence` returns `status=GRACE`.
  2. Playwright: Python Playwright (`--no-sandbox`, JWT injected via `mop_auth_token` localStorage key)
     connects to the stack inside `axiom-ee-tests` LXC and confirms the grace banner DOM element
     is present after login.
- **D-09:** Playwright follows the project standard (CLAUDE.md): launch with `args=['--no-sandbox']`,
  auth via `localStorage.setItem('mop_auth_token', token)`, API login uses form-encoded data.

### Security Tests — EE Internals (VAL-10, VAL-11, VAL-13)

- **D-10:** Wheel manifest (VAL-10), entry-point whitelist (VAL-11), and boot-log HMAC (VAL-13) are
  tested by **importing axiom.ee directly** — unit-test style. No stack required for these tests.
- **D-11:** `axiom-ee` is made available by installing from local source path at test session start:
  `pip install -e ~/Development/axiom-ee` (or `sys.path.insert`). Always uses live source — no wheel
  build step required.
- **D-12:** Tests call the internal functions with adversarial inputs:
  - VAL-10: call `_verify_wheel_manifest()` with a tampered SHA256 manifest → assert `RuntimeError`
  - VAL-11: call the entry-point whitelist checker with a non-whitelisted value → assert `RuntimeError`
  - VAL-13: patch `time.time` (via `unittest.mock.patch`) to simulate clock rollback → assert
    `RuntimeError` on EE, warning-only on CE

### Test Structure

- **D-13:** Tests live in `mop_validation/tests/` with a single top-level `conftest.py` for shared
  LXC fixture management.
- **D-14:** Organized into test files by plan group:
  - `test_173_01_ce_validation.py` — VAL-01, VAL-02, VAL-03 (CE fixtures)
  - `test_173_02_licence_states.py` — VAL-04, VAL-05, VAL-06, VAL-07, VAL-08, VAL-09 (EE fixtures)
  - `test_173_03_wheel_security.py` — VAL-10, VAL-11, VAL-13 (direct import, no LXC)
  - `test_173_04_node_limit.py` — VAL-12 (node limit; EE fixture)
  - `test_173_04_coverage_assertion.py` — VAL-14 (coverage completeness assertion)
- **D-15:** No `pytest.mark.skip` usage — zero skips is a hard requirement (VAL-14).

### Claude's Discretion

- LXC provisioning helpers (image pull, compose file choice, readiness polling) — reuse existing
  patterns from `run_ce_scenario.py` / `provision_lxc_nodes.py`.
- pytest.ini / pyproject.toml configuration (markers, timeout, log format) — Claude decides.
- Whether to use `pytest-timeout` or manual timeout polling in fixtures — Claude decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### VAL Requirements
- `.planning/REQUIREMENTS.md` §VAL — Full VAL-01 through VAL-14 requirements definitions

### Existing Test Infrastructure (reuse, don't reinvent)
- `mop_validation/scripts/run_ce_scenario.py` — Incus LXC orchestration helpers (incus_exec, wait_for_stack, reset_stack)
- `mop_validation/scripts/run_ee_scenario.py` — EE licence key injection + stack reset
- `mop_validation/scripts/verify_ce_tables.py` — CE table count assertion pattern (docker exec psql)
- `mop_validation/scripts/verify_ce_stubs.py` — CE stub route assertion pattern (requests + JWT)
- `mop_validation/scripts/verify_ee_install.py` — EE API assertion pattern (three licence cases)
- `mop_validation/scripts/generate_ee_licence.py` — Licence key generation (for grace + tampered fixtures)
- `mop_validation/scripts/provision_lxc_nodes.py` — LXC provisioning pattern
- `mop_validation/manage_incus_node.py` — Incus node lifecycle management

### Existing Fixtures
- `mop_validation/secrets/ee/ee_valid_licence.env` — Valid licence key fixture
- `mop_validation/secrets/ee/ee_expired_licence.env` — Expired licence key fixture
- `mop_validation/secrets/ee/ee_test_private.pem` + `ee_test_public.pem` — EE signing keypair

### EE Source (security tests)
- `~/Development/axiom-ee/` — axiom-ee source; install with `pip install -e` for direct import
- See CLAUDE.md / GEMINI.md → Sister Repositories section for axiom-ee context

### Playwright Constraints (from CLAUDE.md)
- MCP browser broken — use Python Playwright directly
- Launch: `p.chromium.launch(args=['--no-sandbox'], headless=True)`
- Auth: `localStorage.setItem('mop_auth_token', token)` before navigating
- API login: form-encoded data (`requests.post(url, data={...})`), not JSON
- localStorage key: `mop_auth_token`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_ce_scenario.incus_exec(cmd, timeout)` — Run bash inside the named LXC container
- `run_ce_scenario.wait_for_stack(timeout)` — Poll until stack is ready
- `run_ce_scenario.reset_stack(compose_src)` — Rebuild and restart stack in LXC
- `run_ee_scenario.read_ee_licence_key()` — Read licence key from secrets.env
- `verify_ce_tables.py` patterns — Docker exec psql for table count assertions
- `verify_ce_stubs.py` patterns — requests-based stub route assertions with JWT

### Established Patterns
- Scripts interact with stack via HTTPS against the LXC's IP (not localhost when running in LXC)
- Secrets read from `mop_validation/secrets.env` and `mop_validation/secrets/ee/`
- Auth: get token from API first, then inject into requests headers
- Docker container names follow `puppeteer-agent-1` / `puppeteer-db-1` pattern

### Integration Points
- New pytest tests live in `mop_validation/tests/` — currently empty
- conftest.py at `mop_validation/tests/conftest.py` will be the new fixture root
- Tests will import helpers from `mop_validation/scripts/` (sys.path or package install)

</code_context>

<specifics>
## Specific Ideas

- LXC names: `axiom-ce-tests` and `axiom-ee-tests` (user-specified for clarity and port isolation)
- Module-scoped LXC fixtures: bring up once per test file group, not per individual test
- Licence state injection: `incus exec axiom-ee-tests -- docker restart puppeteer-agent-1` after
  modifying env, not a full `compose up`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 173-ee-behavioural-validation-test-suite*
*Context gathered: 2026-04-20*

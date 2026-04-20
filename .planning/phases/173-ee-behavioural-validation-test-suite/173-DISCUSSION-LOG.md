# Phase 173: Discussion Log

**Phase:** 173-ee-behavioural-validation-test-suite
**Date:** 2026-04-20
**Status:** Complete

---

## Gray Areas Discussed

### 1. Stack Management — Test Isolation

**Question:** How should tests manage the CE/EE stacks — run on host or inside LXC?

**User choice:** Module-scoped fixtures, inside LXC containers

**Rationale:** User noted port clashing with the live puppeteer stack as the key driver. Named LXC containers (`axiom-ce-tests`, `axiom-ee-tests`) avoid conflicts and follow the existing `provision_lxc_nodes.py` / `run_ce_scenario.py` Incus pattern. Module-scoped fixtures mean one LXC spin-up per test group, not per test.

**Decision locked:** D-01, D-02, D-03

---

### 2. Licence State Transitions

**Question:** How should tests switch between licence states (valid → grace → expired → absent → tampered)?

**User choice:** Agent restart with different licence key (no full stack rebuild per state)

**Rationale:** Restarting only `puppeteer-agent-1` inside `axiom-ee-tests` via `incus exec` with a patched `AXIOM_LICENCE_KEY` env var keeps the DB and node containers alive. Much faster than a full `compose up` cycle per state. Matches the `run_ee_scenario.py` pattern.

**Decision locked:** D-04, D-05, D-06, D-07

---

### 3. VAL-06 Grace Banner — Coverage Level

**Question:** Is an API assertion sufficient for VAL-06, or do we also need a Playwright UI check?

**User choice:** API + Playwright banner check (the more thorough option)

**Rationale:** User chose full coverage: both `GET /api/licence` returning `status=GRACE` AND a Playwright assertion confirming the grace banner DOM element is visible in the dashboard. Follows the existing Python Playwright pattern (CLAUDE.md): `--no-sandbox`, JWT via `localStorage.setItem('mop_auth_token', token)`.

**Decision locked:** D-08, D-09

---

### 4. EE Internals — Security Test Access

**Question:** How do VAL-10, VAL-11, VAL-13 access axiom.ee internal functions?

**User choice:** Import axiom.ee directly, install from local source path in conftest

**Rationale:** `pip install -e ~/Development/axiom-ee` at test session start gives access to internal functions (`_verify_wheel_manifest()`, entry-point whitelist checker, boot-log HMAC verifier) without a wheel build step. Unit-test style — no LXC stack required for these three tests.

**Decision locked:** D-10, D-11, D-12

---

## Deferred Items

None — discussion stayed within phase scope.

---

## Final Decisions Summary

| ID | Decision |
|----|----------|
| D-01 | Tests run in Incus LXC containers (not host) |
| D-02 | Named LXCs: `axiom-ce-tests` (CE) and `axiom-ee-tests` (EE) |
| D-03 | Module-scoped pytest fixtures — one LXC spin-up per test group |
| D-04 | Licence state changes via agent-only restart, not full stack rebuild |
| D-05 | Licence states via agent restart + API poll — no mocking |
| D-06 | Pre-existing `ee_valid_licence.env` / `ee_expired_licence.env` for valid/expired |
| D-07 | Grace + tampered fixtures generated at conftest time via `generate_ee_licence.py` |
| D-08 | VAL-06: dual assertion — API status=GRACE + Playwright banner DOM check |
| D-09 | Playwright: `--no-sandbox`, JWT via `mop_auth_token` localStorage, form-encoded login |
| D-10 | VAL-10/11/13: direct axiom.ee import, unit-test style, no LXC |
| D-11 | EE access via `pip install -e ~/Development/axiom-ee` in conftest |
| D-12 | Adversarial inputs: tampered manifest → RuntimeError; clock rollback → RuntimeError on EE |
| D-13 | Single top-level `conftest.py` at `mop_validation/tests/` |
| D-14 | 5 test files by plan group (173_01 through 173_04_coverage) |
| D-15 | Zero `pytest.mark.skip` — hard requirement |

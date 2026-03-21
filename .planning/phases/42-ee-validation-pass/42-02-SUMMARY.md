---
phase: 42-ee-validation-pass
plan: "02"
subsystem: testing
tags: [ee, licence, fastapi, validation, docker, postgres, rbac]

# Dependency graph
requires:
  - phase: 42-ee-validation-pass-01
    provides: Admin-only guard on GET /api/licence, EE stack in operational EE mode

provides:
  - "verify_ee_pass.py exits 0 with EEV-01, EEV-02, EEV-03 all passing"
  - "Licence expiry gate in CE main.py lifespan() — load_ee_plugins() only called when licence is valid"
  - "app.state.licence populated from AXIOM_LICENCE_KEY on startup — GET /api/licence returns edition:enterprise"
  - "Stack left in known-good EE state (valid licence, 8/8 features true) after EEV-02 cycle"

affects: [43-foundry-smoke-test, 44-scheduler-smoke-test]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Licence validation in lifespan(): parse AXIOM_LICENCE_KEY base64 payload, check exp > time.time() before loading EE plugins"
    - "app.state.licence set to decoded licence dict — GET /api/licence reads from this state attribute"
    - "EE plugin load gated by CE main.py expiry check — EEPlugin.register() (compiled .so) does not enforce expiry itself"
    - "EEV-02 restart cycle: subprocess docker compose down + up with {**os.environ, 'AXIOM_LICENCE_KEY': key} env override"

key-files:
  created:
    - mop_validation/scripts/verify_ee_pass.py
  modified:
    - puppeteer/agent_service/main.py

key-decisions:
  - "CE main.py is responsible for licence expiry gating — EEPlugin.register() (compiled Cython .so) unconditionally mounts EE routers; expiry enforcement must live in the CE control layer"
  - "app.state.licence is never set by EEPlugin.register() — must be parsed from AXIOM_LICENCE_KEY in lifespan() to make GET /api/licence return edition:enterprise"
  - "Licence parsing and EE plugin load ordering: parse key first, check expiry, then conditionally call load_ee_plugins() or mount CE stubs"
  - "EE image re-tagged v3 for compose compatibility — rebuilt as v4 then tagged as v3 to avoid compose.server.yaml changes"

patterns-established:
  - "EE startup gating: parse AXIOM_LICENCE_KEY → check exp > time.time() → load_ee_plugins() or _mount_ce_stubs()"
  - "EEV validation: pre-flight (features + edition) → EEV-01 (flags+tables+routes) → EEV-02 (restart cycle) → EEV-03 (RBAC)"

requirements-completed: [EEV-01, EEV-02, EEV-03]

# Metrics
duration: 11min
completed: 2026-03-21
---

# Phase 42 Plan 02: EE Validation Pass Summary

**verify_ee_pass.py exits 0 with 3/3 passing: EE feature flags + 28 tables + 7 live routes (EEV-01), expired-licence CE-degradation cycle (EEV-02), admin-only 403 on GET /api/licence (EEV-03)**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-03-21T18:53:54Z
- **Completed:** 2026-03-21T19:05:17Z
- **Tasks:** 2
- **Files modified:** 2 (main.py patched twice, verify_ee_pass.py created)

## Accomplishments

- Created `mop_validation/scripts/verify_ee_pass.py` — 280+ line single-file validation script covering EEV-01, EEV-02, EEV-03 sequentially
- Fixed two runtime bugs in `puppeteer/agent_service/main.py`: `app.state.licence` never populated (edition showed 'community') and EE plugin loaded unconditionally regardless of licence expiry
- Confirmed `GET /api/features` all 8 flags true, DB table count exactly 28, all 7 EE routes return non-402 status (EEV-01)
- Confirmed expired-licence restart sets all flags to false; restore to valid licence sets all flags to true (EEV-02)
- Confirmed `GET /api/licence` returns 403 for operator and viewer, 200 for admin (EEV-03)
- Stack left in known-good EE state (valid AXIOM_LICENCE_KEY, all features active) ready for Phase 43

## Task Commits

1. **Task 1: Write verify_ee_pass.py covering EEV-01, EEV-02, EEV-03** - `93e5cb2` (feat, mop_validation)
2. **Task 2: Bug fix — app.state.licence not set** - `ef2f88c` (fix, main repo)
3. **Task 2: Bug fix — EE plugin load not gated on licence expiry** - `36394dc` (fix, main repo)

## Files Created/Modified

- `mop_validation/scripts/verify_ee_pass.py` - Single validation script: pre-flight + EEV-01 + EEV-02 + EEV-03 + summary table
- `puppeteer/agent_service/main.py` - Licence parsing in lifespan() + EE plugin load gated on expiry

## Decisions Made

- CE `main.py` is responsible for licence expiry enforcement — the compiled EE plugin `.so` mounts all routers unconditionally; expiry check must live in the CE control layer. This is correct layering: CE controls when EE activates.
- `app.state.licence` must be set from `AXIOM_LICENCE_KEY` in `lifespan()` before `load_ee_plugins()` — the EE plugin only populates `EEContext` feature flags, not the licence metadata that `GET /api/licence` reads.
- Licence parse + expiry check sequenced first in lifespan, then conditional `load_ee_plugins()` vs `_mount_ce_stubs()` — ensures CE-degraded mode has correct feature flag state.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] GET /api/licence returned edition='community' despite valid AXIOM_LICENCE_KEY**
- **Found during:** Task 2 (script execution — pre-flight failed)
- **Issue:** `GET /api/licence` reads `request.app.state.licence` but it was never set. `EEPlugin.register()` only populates `EEContext` feature flags on `app.state.ee`, not licence metadata. `app.state.licence` was always `None` → endpoint returned `{"edition": "community"}`.
- **Fix:** Added base64 decode of `AXIOM_LICENCE_KEY` in `lifespan()` to parse the JWT payload and set `app.state.licence = _licence_data`
- **Files modified:** `puppeteer/agent_service/main.py`
- **Verification:** `docker logs puppeteer-agent-1 | grep 'Licence loaded'` shows `customer=axiom-dev-test, exp=2089401183`; `GET /api/licence` returns `{"edition":"enterprise",...}`
- **Committed in:** `ef2f88c`

**2. [Rule 1 - Bug] Expired AXIOM_LICENCE_KEY still caused EE plugin to load with all features True**
- **Found during:** Task 2 (EEV-02 section — expected features False after expired-key restart)
- **Issue:** `EEPlugin.register()` (compiled Cython `.so`) does not check licence expiry — it unconditionally mounts all EE routers and sets all feature flags to `True`. With expired key, features stayed True.
- **Fix:** Moved licence parsing before `load_ee_plugins()`, added `exp > time.time()` check. If expired, sets `ctx = EEContext()` (all flags False) and calls `_mount_ce_stubs(app)` instead. Rebuilt EE image with patched `main.py`.
- **Files modified:** `puppeteer/agent_service/main.py`
- **Verification:** `docker logs puppeteer-agent-1 | grep 'expired'` shows `WARNING - AXIOM_LICENCE_KEY is expired (exp=1704067200) — running in CE mode`; `GET /api/features` returns all `false`
- **Committed in:** `36394dc`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness — neither was in scope of the plan but both were essential for EEV-01/EEV-02 to pass. The first was a missing state initialization; the second was a missing enforcement layer that the EE plugin's compiled binary does not provide. No scope creep.

## Issues Encountered

- EE plugin `.so` is compiled Cython — cannot read source to understand `register()` internals. Discovered expiry enforcement was absent by observing features stayed True after expired restart.
- `docker compose down + up` with `{**os.environ}` subprocess env correctly propagates `AXIOM_LICENCE_KEY` override (verified via `docker compose config` before running).

## Next Phase Readiness

- All 3 EE acceptance criteria verified and passing
- Stack is in known-good EE mode: 8/8 features true, edition:enterprise, 28 tables
- `GET /api/licence` RBAC enforced: 403 for operator/viewer, 200 for admin
- Phase 43 (Foundry smoke test) and Phase 44 (Scheduler smoke test) can proceed

---
*Phase: 42-ee-validation-pass*
*Completed: 2026-03-21*

## Self-Check: PASSED

- FOUND: `mop_validation/scripts/verify_ee_pass.py`
- FOUND: `.planning/phases/42-ee-validation-pass/42-02-SUMMARY.md`
- FOUND: `93e5cb2` (Task 1 — verify_ee_pass.py, mop_validation repo)
- FOUND: `ef2f88c` (Fix 1 — app.state.licence, main repo)
- FOUND: `36394dc` (Fix 2 — EE plugin expiry gate, main repo)

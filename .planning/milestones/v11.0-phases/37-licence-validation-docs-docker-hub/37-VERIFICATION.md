---
phase: 37-licence-validation-docs-docker-hub
verified: 2026-03-20T17:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
gaps: []
notes: "DIST-02 (Docker Hub publish) was explicitly deferred per 37-CONTEXT.md. REQUIREMENTS.md updated 2026-03-20 to remap DIST-02 to v12.0+ with deferral note. Not a gap — deliberate scoping decision."
human_verification:
  - test: "Open the running dashboard sidebar"
    expected: "CE badge (zinc/grey) visible in sidebar footer — confirms useLicence hook is fetching /api/licence and rendering the edition badge"
    why_human: "CSS classes and conditional rendering verified via grep; actual visual rendering requires a browser"
  - test: "Open Admin panel as an admin user"
    expected: "Licence section appears at top of Admin page showing 'Community Edition' with AXIOM_LICENCE_KEY instructions"
    why_human: "LicenceSection component wiring verified; admin-only gate confirmed; actual render requires a browser session"
  - test: "Start EE service with AXIOM_LICENCE_KEY unset"
    expected: "Startup log shows 'AXIOM_LICENCE_KEY not set — running in Community Edition mode'; GET /api/features returns all false; GET /api/licence returns {edition: community}"
    why_human: "Code path logic verified via inspection; runtime behaviour needs live stack"
---

# Phase 37: Licence Validation, Docs, Dashboard Badge — Verification Report

**Phase Goal:** Implement licence key validation (Ed25519 offline verification) in the EE plugin, surface the edition badge in the dashboard, add CE/EE admonition callouts to docs, and create the licensing.md page — so users know what is EE-only and how to activate it.
**Verified:** 2026-03-20T17:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Starting EE with no AXIOM_LICENCE_KEY runs in CE mode — no startup failure | VERIFIED | `plugin.py:66-69` returns early with INFO log when key is empty |
| 2 | Starting EE with a tampered/invalid signature disables EE features — no startup failure | VERIFIED | `_parse_licence()` catches `InvalidSignature`, returns None; `register()` returns early |
| 3 | Starting EE with an expired key disables all EE features | VERIFIED | `plugin.py:76-81` checks `exp < int(time.time())` and returns early |
| 4 | Licence validation passes with network access blocked — fully offline | VERIFIED | `Ed25519PublicKey.from_public_bytes()` uses only the compiled-in constant, no network call |
| 5 | GET /api/licence returns `{edition: enterprise, customer_id, expires, features}` for valid key | VERIFIED | `main.py:838-851` endpoint + test `test_licence_endpoint_enterprise` passes |
| 6 | GET /api/licence returns `{edition: community}` in CE/expired/invalid mode | VERIFIED | `main.py:842-843` + test `test_licence_endpoint_community` passes — 6/6 tests GREEN |
| 7 | Dashboard sidebar shows CE/EE badge derived from GET /api/licence | VERIFIED | `MainLayout.tsx:33` imports useLicence; `lines 133-137` renders CE/EE badge conditionally |
| 8 | Admin panel contains a Licence section showing edition, customer_id, expiry, features | VERIFIED | `Admin.tsx:77-120` LicenceSection component; `line 1344` renders admin-only |
| 9 | useLicence hook caches 5 min, no retry, returns CE fallback on error | VERIFIED | `useLicence.ts:22-24` staleTime 5*60*1000, retry: false, CE_DEFAULTS fallback |
| 10 | All 5 EE feature guide pages show enterprise admonition | VERIFIED | `!!! enterprise` present in foundry.md:9, rbac.md:7, rbac-reference.md:7, oauth.md:7, axiom-push.md:10 |
| 11 | DIST-02: axiom-ce Docker Hub publish in release.yml | FAILED | Not planned, not implemented — explicitly deferred per CONTEXT.md but still mapped to Phase 37 in REQUIREMENTS.md |

**Score:** 10/11 truths verified

---

## Required Artifacts

### Plan 01 — Ed25519 Licence Validation (DIST-01)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `axiom-ee/ee/plugin.py` | `_LICENCE_PUBLIC_KEY_BYTES` + `_parse_licence()` at module level; licence check first in `register()` | VERIFIED | Lines 16-38 module-level; lines 65-84 licence check block is first in `register()` |
| `.worktrees/axiom-split/puppeteer/agent_service/tests/test_licence.py` | 6-case TDD test suite | VERIFIED | 215 lines; 6 test functions; all 6 pass GREEN |
| `.worktrees/axiom-split/puppeteer/agent_service/main.py` | GET /api/licence endpoint | VERIFIED | Lines 838-851; returns community or enterprise JSON |

**Anti-pattern note:** `_LICENCE_PUBLIC_KEY_BYTES = b'\x00' * 32` is a deliberate placeholder. Documented in comment: "replace before release". This is a known pre-release action item, not an implementation stub.

### Plan 02 — Dashboard Edition Badge (DIST-03)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.worktrees/axiom-split/puppeteer/dashboard/src/hooks/useLicence.ts` | LicenceInfo interface + useLicence() exported | VERIFIED | 27 lines; both exports present |
| `.worktrees/axiom-split/puppeteer/dashboard/src/layouts/MainLayout.tsx` | CE/EE badge in sidebar footer | VERIFIED | Import line 33; licence const line 39; badge JSX lines 133-137 |
| `.worktrees/axiom-split/puppeteer/dashboard/src/views/Admin.tsx` | LicenceSection component, admin-only | VERIFIED | Component lines 77-120; rendered at line 1344 with `getUser()?.role === 'admin'` gate |

### Plan 03 — MkDocs Admonitions (DIST-03)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.worktrees/axiom-split/docs/docs/stylesheets/extra.css` | Amber/gold .admonition.enterprise CSS | VERIFIED | 15 lines; amber `#f59e0b` border and title background |
| `.worktrees/axiom-split/docs/docs/licensing.md` | CE/EE licensing explainer page | VERIFIED | AXIOM_LICENCE_KEY setup, offline validation, expiry table, GET /api/licence example |
| `.worktrees/axiom-split/docs/mkdocs.yml` | extra_css entry + Licensing nav | VERIFIED | `extra_css` at line 9; `Licensing: licensing.md` at line 46 |
| 5x feature-guide .md files | `!!! enterprise` admonition before first EE section | VERIFIED | All 5 files contain `!!! enterprise` at their respective placement lines |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ee/plugin.py:_parse_licence()` | `ee/plugin.py:EEPlugin.register()` | called as first action before model imports | WIRED | `plugin.py:71` calls `_parse_licence(licence_key)` |
| `ee/plugin.py:EEPlugin.register()` | `app.state.licence` | set only after sig verify AND expiry check pass | WIRED | `plugin.py:84` sets `self._app.state.licence = licence` after both checks |
| `main.py:GET /api/licence` | `app.state.licence` | `getattr(request.app.state, 'licence', None)` | WIRED | `main.py:841` uses exact pattern specified in PLAN frontmatter |
| `MainLayout.tsx` | `useLicence hook` | `import { useLicence } from '../hooks/useLicence'` | WIRED | Line 33 import + line 39 call + lines 133-137 render |
| `Admin.tsx:LicenceSection` | `GET /api/licence` | useLicence() hook call | WIRED | Line 78 `const licence = useLicence()` inside LicenceSection |
| `mkdocs.yml` | `docs/stylesheets/extra.css` | `extra_css: [stylesheets/extra.css]` | WIRED | Line 9 in mkdocs.yml |
| 5 feature-guide .md files | `!!! enterprise` admonition | direct markup | WIRED | All 5 files contain the admonition |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIST-01 | Plan 37-01 | Ed25519 offline licence key validation in EE plugin | SATISFIED | `_parse_licence()` + licence check block + `GET /api/licence` + 6 tests GREEN |
| DIST-02 | ORPHANED (no plan claims it) | axiom-ce image published to Docker Hub in release.yml | BLOCKED | Explicitly deferred per `37-CONTEXT.md`; release.yml has no Docker Hub step; REQUIREMENTS.md still maps it to Phase 37 as Pending |
| DIST-03 | Plans 37-02 + 37-03 | MkDocs CE/EE admonitions + dashboard edition badge | SATISFIED | 5 feature guide admonitions, extra.css, licensing.md, useLicence hook, sidebar badge, Admin LicenceSection |

**ORPHANED requirement:** DIST-02 is mapped to Phase 37 in REQUIREMENTS.md but claimed by no plan in this phase. Per the CONTEXT.md it was a deliberate deferral decision. The REQUIREMENTS.md coverage table needs to either remap DIST-02 to a future phase or add a 37-04 plan to implement it.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `axiom-ee/ee/plugin.py` | 16 | `_LICENCE_PUBLIC_KEY_BYTES: bytes = b'\x00' * 32` — placeholder public key | Info | Known pre-release action item; commented "replace before release"; does not block phase goal; tests correctly monkeypatch it |

No TODO/FIXME/HACK anti-patterns found in any phase files. No empty return stubs. No console.log-only handlers.

---

## Human Verification Required

### 1. Dashboard CE Badge Render

**Test:** Open the running dashboard in a browser, check the sidebar footer.
**Expected:** A small "CE" label in zinc/grey appears beside "v1.2.0 • Online".
**Why human:** CSS conditional render verified via code inspection; actual layout and colour rendering requires a browser.

### 2. Admin Licence Panel Render

**Test:** Log in as admin, navigate to the Admin page.
**Expected:** "Licence" section appears at top of page with "Community Edition" label and note about AXIOM_LICENCE_KEY.
**Why human:** Admin-only gate and component tree wiring verified in code; actual render requires a browser session.

### 3. EE Startup Licence Gating

**Test:** Start the agent service with a valid AXIOM_LICENCE_KEY using a test key (requires generating one with the same public key that will be compiled in).
**Expected:** Startup log shows "Licence valid — customer=..., features=...", GET /api/features returns EE flags true, GET /api/licence returns enterprise info.
**Why human:** Code path verified; runtime behaviour with real key requires a live stack. Note: current placeholder public key (`b'\x00' * 32`) will reject all real keys until replaced.

---

## Gaps Summary

One gap blocks full phase goal achievement:

**DIST-02 is an orphaned requirement.** It is listed in REQUIREMENTS.md as "Phase 37 / Pending" but was deliberately deferred in `37-CONTEXT.md`. No plan in this phase claims DIST-02 and `release.yml` contains no Docker Hub publish step.

The gap has two valid resolutions:
1. Create plan `37-04` implementing Docker Hub publish for the `axiom-ce` image in `.github/workflows/release.yml`.
2. Update `REQUIREMENTS.md` to remap DIST-02 to a future phase (e.g., Phase 38 or a dedicated Docker Hub / release packaging phase) and mark the deferral explicitly.

All other phase deliverables (DIST-01 licence validation, DIST-03 docs and dashboard badge) are fully implemented, wired, and tested.

---

_Verified: 2026-03-20T17:30:00Z_
_Verifier: Claude (gsd-verifier)_

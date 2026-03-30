---
phase: 92-usp-signing-ux
verified: 2026-03-30T17:30:00Z
status: gaps_found
score: 2/3 success criteria verified
re_verification: false
gaps:
  - truth: "PR #10 passes all tests and is merged to main"
    status: partial
    reason: >
      PR is merged (squash SHA 2d6cad8, merged 2026-03-30T15:41:11Z). Backend CI
      jobs (3.10/3.11/3.12) fail with 'pytest: command not found' — a pre-existing
      infra issue unrelated to this PR. Secret-scan fails due to missing
      gitleaks org license — also pre-existing. However, test_signing_ux.py
      (added in commits 8c02a00 and 6ec4294 on feat/usp-signing-ux) was NOT
      included in the squash merge and does not exist on main. Additionally,
      the test asserts status_code 403 for bad-signature but main.py raises 422,
      so the test would fail if it were run against the merged code.
    artifacts:
      - path: "puppeteer/agent_service/tests/test_signing_ux.py"
        issue: "Not present on main branch — only on feat/usp-signing-ux"
      - path: "puppeteer/agent_service/main.py"
        issue: "POST /jobs/definitions raises 422 (not 403) for bad signature payload — test_signing_ux expects 403"
    missing:
      - "Merge test_signing_ux.py to main (squash-merged PR did not include it)"
      - "Align status code: either update test to assert 422, or change main.py to raise 403"
human_verification:
  - test: "Open the Signatures page in the dashboard with zero keys registered"
    expected: >
      The indigo 'Getting Started' banner is visible with a 'How to generate a key'
      button. Clicking it opens the KeygenGuide modal with Step 1 (keygen command
      with CopyButton), Step 2 (register key instructions), and Step 3 (sign command
      with CopyButton). 'Register Key Now' button in the modal flows directly to the
      upload form.
    why_human: "Visual rendering, modal open/close flow, and CopyButton clipboard behaviour cannot be verified programmatically without a running browser."
---

# Phase 92: USP Signing UX Verification Report

**Phase Goal:** New users can run a hello-world job in under 30 minutes without generating their own signing keys
**Verified:** 2026-03-30T17:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Signatures page guides users through keypair generation with copy-paste commands — no auto-seeded demo keypair | VERIFIED | `noKeys` banner in `Signatures.tsx` triggers `KeygenGuideModal`. `KEYGEN_CMD` and `SIGN_CMD` constants rendered with `CopyButton`. `demo_signing_key.pem` / `demo_verification_key.pem` removed from repo. No demo-key startup seed in `main.py`. |
| 2  | Signatures page displays a banner with copy-paste signing steps a new user can follow without external docs | VERIFIED | Banner renders when `signatures.length === 0` (line 209 `{noKeys && (...) }`). Modal has 3 labelled steps. `first-job.md` docs updated with matching Step 0 content. Minor usability note: `SIGN_CMD` hardcodes `hello.py` rather than a named `YOUR_SCRIPT` variable — the fix commit (142e303) exists on the feature branch but was not included in the squash merge. Functional usability is preserved; the substitution point is mildly unclear. |
| 3  | PR #10 passes all tests and is merged to main | PARTIAL | PR is merged (state: MERGED, mergedAt: 2026-03-30T15:41:11Z, SHA: 2d6cad8). Backend CI failures are pre-existing infra issues (pytest not in PATH, gitleaks org license missing) present on main before this PR. However: `test_signing_ux.py` was NOT merged to main — it exists only on `feat/usp-signing-ux`. Furthermore, the test asserts `status_code == 403` for invalid signature but `main.py` raises `422 Unprocessable Entity`, so the test would fail if run against the merged code. |

**Score:** 2/3 success criteria fully verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/dashboard/src/views/Signatures.tsx` | Keygen guide banner and modal with 3 copy-paste steps | VERIFIED | 405 lines, substantive. Banner wired to `noKeys` condition. Modal with `KEYGEN_CMD` + `SIGN_CMD` + `CopyButton`. Route wired at `/signatures` in `AppRoutes.tsx`. |
| `puppeteer/agent_service/main.py` | No demo key seed; actionable signature error messages | VERIFIED | No demo key seeding. Line 1743 raises 404 "Signature ID not found". Line 1747-1751 raises 422 with message referencing "Signatures page in the dashboard". |
| `docs/docs/getting-started/first-job.md` | Step 0 keypair generation section with Python + openssl tabs | VERIFIED | "Step 0: Generate a signing keypair" section present with Python (cryptography) and openssl tabs, warning about not committing signing.key, and tip cross-linking to the Signatures page banner. |
| `puppeteer/agent_service/tests/test_signing_ux.py` | Backend tests for signature error paths | MISSING on main | File exists on `feat/usp-signing-ux` branch only (commits 8c02a00, 6ec4294). Not included in squash merge commit 2d6cad8. |
| `puppeteer/demo_signing_key.pem` | Must NOT exist | VERIFIED absent | Not present on main branch. |
| `puppeteer/demo_verification_key.pem` | Must NOT exist | VERIFIED absent | Not present on main branch. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Signatures.tsx` banner | `KeygenGuideModal` | `onClick={() => setShowKeygenGuide(true)}` | WIRED | Line 238 — "How to generate a key" button sets `showKeygenGuide=true` |
| `KeygenGuideModal` | Upload form | `onClick={() => { setShowKeygenGuide(false); setShowModal(true); }}` | WIRED | Line 351-352 — "Register Key Now" closes guide and opens upload modal |
| `KEYGEN_CMD` constant | Modal step 1 | `{KEYGEN_CMD}` in `<pre>` + `<CopyButton text={KEYGEN_CMD}>` | WIRED | Lines 327-328 |
| `SIGN_CMD` constant | Modal step 3 | `{SIGN_CMD}` in `<pre>` + `<CopyButton text={SIGN_CMD}>` | WIRED | Lines 341-342 |
| `Signatures.tsx` | `/signatures` route | `AppRoutes.tsx` lazy import + `<Route path="signatures">` | WIRED | Lines 11 and 47 of AppRoutes.tsx |
| `test_signing_ux.py` | `main` branch | PR squash merge | NOT WIRED | Test file only on `feat/usp-signing-ux`; not merged |
| `test_signing_ux.py` expected 403 | `main.py` actual 422 | `HTTPException` status code | MISMATCH | Test `assert response.status_code == 403` vs `raise HTTPException(422, ...)` in main.py |

### Requirements Coverage

| Requirement | Source | Description | Status | Evidence |
|-------------|--------|-------------|--------|----------|
| UX-01 (ROADMAP label) | ROADMAP.md Phase 92 | New user can run hello-world under 30 mins without generating own signing keys | PARTIALLY SATISFIED | UX-01 does not appear in the current `REQUIREMENTS.md` (v16.0). The semantically equivalent entry is `USP-01` in the "Future Requirements / On-Ramp & Docs" section. No v16.1 REQUIREMENTS.md exists. The functional goal is implemented; the requirement ID cross-reference is an inconsistency in planning documents. |
| USP-01 (REQUIREMENTS.md label) | REQUIREMENTS.md Future Requirements | New CE user can have a node enrolled and hello world job executing in under 30 minutes (signing UX improvement) | SATISFIED | Signatures page now guides keygen in-app; first-job.md updated; demo key removed. |

**Note on orphaned requirement ID:** ROADMAP.md Phase 92 declares `Requirements: UX-01`. No `UX-01` definition exists in `REQUIREMENTS.md` (v16.0). `UX-01` appears only in `milestones/v12.0-REQUIREMENTS.md` with a different definition (empty-state CTAs). The intent maps to `USP-01`. This is a documentation inconsistency — not a functional gap — but should be corrected when v16.1 REQUIREMENTS.md is authored.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `Signatures.tsx` | 80 | `SIGN_CMD` hardcodes `open("hello.py", "r")` instead of a named `YOUR_SCRIPT` variable | Warning | New users copying the snippet must know to substitute `hello.py` for their actual script path. Fix commit 142e303 was written on the feature branch but was not included in the PR merge. Does not block functionality. |

No `TODO`, `FIXME`, placeholder returns, or empty handler stubs found in the merged code.

### Human Verification Required

#### 1. Banner and modal end-to-end flow

**Test:** Log in as admin, navigate to `/signatures` with no keys registered.
**Expected:** The indigo "Getting Started — No signing keys registered" banner is visible. Clicking "How to generate a key" opens the KeygenGuide modal. Each step is readable. The copy buttons in Steps 1 and 3 copy the correct command to the clipboard. "Register Key Now" closes the modal and opens the key upload dialog. The upload dialog accepts a PEM key and saves it.
**Why human:** Visual rendering, modal transition behaviour, and clipboard API interaction cannot be verified programmatically without a running browser session.

### Gaps Summary

One gap blocks full success criterion 3:

**test_signing_ux.py not on main, and test would fail if it were.** The SUMMARY.md states "PR #10 passes all tests" and documents test commits `8c02a00` and `6ec4294`. However, these commits were made to the `feat/usp-signing-ux` branch after the squash-merge commit `2d6cad8` was created. The squash merged only `2d6cad8` — the test file never landed on main. Additionally, the test asserts `status_code == 403` for a bad-signature path that `main.py` handles with `422 Unprocessable Entity`, creating a test/implementation mismatch.

The two UX criteria (banner, modal, copy-paste commands) are substantively implemented and wired. The goal of enabling a new user to complete hello-world without generating keys manually is achievable with what is on main. The gap is one of test coverage completeness and test accuracy.

Pre-existing CI failures (pytest not in PATH for all backend versions, gitleaks org license missing for secret-scan) are unrelated to this phase's changes and affect all CI runs on the repository.

---

_Verified: 2026-03-30T17:30:00Z_
_Verifier: Claude (gsd-verifier)_

---
phase: 105-windows-signing-pipeline-fix
verified: 2026-04-01T15:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 105: Windows Signing Pipeline Fix — Verification Report

**Phase Goal:** Close v18.0 audit gaps — restore Windows first-job documentation, fix CRLF countersign asymmetry, and fix cold-start forced password change
**Verified:** 2026-04-01T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                            | Status     | Evidence                                                                                                     |
| --- | ---------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | CRLF line endings in script_content are normalized to LF before both user sig verify and server countersign     | VERIFIED   | `main.py` line 1104: `script_content.replace('\r\n', '\n').replace('\r', '\n')` before both paths           |
| 2   | Admin bootstrap always sets must_change_password=True unless ADMIN_SKIP_FORCE_CHANGE=true is set                | VERIFIED   | `main.py` lines 159-162: opt-out pattern via `ADMIN_SKIP_FORCE_CHANGE` env var                              |
| 3   | A unit test proves a CRLF script produces the same countersignature as its LF-normalized equivalent             | VERIFIED   | `tests/test_crlf_countersign.py` — 2 tests, both PASSED (confirmed by live test run)                        |
| 4   | first-job.md contains at least 3 occurrences of 'Windows (PowerShell)' tabs                                     | VERIFIED   | `grep -c` returns 3; tabs at lines 46, 159, 292 covering keypair gen, test script, and sign+submit          |
| 5   | All Windows tabs use Invoke-RestMethod (native PowerShell), not curl                                            | VERIFIED   | Lines 306 and 341 use `Invoke-RestMethod`; no curl in Windows tab content                                    |
| 6   | PowerShell signing snippet does NOT include client-side CRLF normalization                                       | VERIFIED   | `grep -c "\\r\\n" first-job.md` returns 0; server handles it transparently                                   |
| 7   | Other getting-started docs retain PowerShell content (enroll-node.md >= 2, install.md >= 4)                    | VERIFIED   | enroll-node.md: 2 occurrences; install.md: 4 occurrences — no regression                                     |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                                         | Expected                                               | Status     | Details                                                                            |
| ------------------------------------------------ | ------------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------- |
| `puppeteer/agent_service/main.py`                | CRLF normalization in create_job + force PW on bootstrap | VERIFIED | Line 1104 normalizes; lines 159-162 implement opt-out force-change pattern         |
| `puppeteer/tests/test_crlf_countersign.py`       | Unit test for CRLF countersign symmetry                | VERIFIED   | 44 lines, 2 substantive tests; both pass; matches plan spec exactly                |
| `docs/docs/getting-started/first-job.md`         | Windows PowerShell tabs for complete first-job workflow | VERIFIED  | 3 tabs at lines 46, 159, 292; substantive content with Invoke-RestMethod calls     |

### Key Link Verification

| From                                         | To                                       | Via                                                             | Status  | Details                                                                                    |
| -------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------ |
| `main.py create_job` CRLF normalization      | `node.py` line 585 CRLF normalization    | Both sides normalize to LF before sign/verify                   | WIRED   | `main.py:1104` and `node.py:585` use identical `replace('\r\n', '\n').replace('\r', '\n')` |
| `main.py` admin bootstrap                    | ADMIN_SKIP_FORCE_CHANGE env var          | Opt-out pattern — force by default, skip only if explicitly set | WIRED   | `main.py:159-162` reads env var; no matching entry in compose files means always forces    |
| `first-job.md` Windows tabs                  | `enroll-node.md` Windows tabs            | Same `=== "Windows (PowerShell)"` tab format                    | WIRED   | Both files use identical mkdocs-material tab syntax                                         |
| `first-job.md` signing approach              | `main.py` CRLF normalization (Plan 01)   | Server normalizes CRLF so docs don't need to mention it         | WIRED   | No CRLF normalization in docs; server-side fix confirmed in main.py                         |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                   | Status    | Evidence                                                                              |
| ----------- | ----------- | ----------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------- |
| WIN-03      | 105-01      | Admin/admin first login triggers forced password change prompt                | SATISFIED | `main.py` admin bootstrap sets `must_change_password=force_change` where `force_change=True` by default |
| WIN-05      | 105-01, 105-02 | First PowerShell job dispatches, executes, and shows output                | SATISFIED | CRLF fix in `main.py` removes signature rejection; PowerShell tabs in `first-job.md` document the full path |

No orphaned requirements. REQUIREMENTS.md traceability table confirms WIN-03 and WIN-05 both mapped to Phase 105 with status Complete.

### Anti-Patterns Found

None detected in modified files (`main.py`, `tests/test_crlf_countersign.py`, `docs/docs/getting-started/first-job.md`).

### Human Verification Required

#### 1. Windows cold-start forced password change prompt

**Test:** On a fresh deployment with ADMIN_PASSWORD set in .env (not ADMIN_SKIP_FORCE_CHANGE=true), log in as admin and observe the UI.
**Expected:** Force-change modal appears and blocks the UI until password is changed.
**Why human:** The `must_change_password=True` flag is now set on bootstrap, but whether the React ForceChangeModal actually intercepts the login session requires a live browser test against the Docker stack.

#### 2. Windows PowerShell CRLF job submission end-to-end

**Test:** From a Windows machine (or a script that produces CRLF line endings), sign and submit a job using the first-job.md PowerShell instructions. Observe the node output in the dashboard.
**Expected:** Job executes successfully; no SECURITY_REJECTED error.
**Why human:** The CRLF normalization fix is verified at the unit test and code level, but a live Windows-originating job submission is the final integration proof. Requires a Windows host or CRLF-producing client.

### Gaps Summary

No gaps. All must-haves verified.

---

## Commit Verification

All 6 commits cited in summaries confirmed present in git history:

| Commit    | Description                                                  |
| --------- | ------------------------------------------------------------ |
| `fa70d2c` | fix(105-01): normalize CRLF to LF in create_job before signature ops |
| `c6a7f7a` | fix(105-01): always force admin password change on bootstrap |
| `83ea97e` | test(105-01): add CRLF countersign symmetry unit test         |
| `7f86a0d` | docs(105-02): add PowerShell tab to Step 0 keypair generation |
| `076dd73` | docs(105-02): add PowerShell tab to Step 2 test script creation |
| `1b15e5b` | docs(105-02): add PowerShell tab to Manual Setup sign+submit  |

---

_Verified: 2026-04-01T15:00:00Z_
_Verifier: Claude (gsd-verifier)_

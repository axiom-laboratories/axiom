---
phase: 106-fix-docs-signing-pipeline
verified: 2026-04-01T19:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 106: Fix Docs Signing Pipeline — Verification Report

**Phase Goal:** Close remaining v18.0 audit gaps — fix the signature field name mismatch that breaks both Linux and Windows docs-following signing pipelines, restore lost CRLF normalization, and replace deprecated TrustAll pattern
**Verified:** 2026-04-01T19:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | first-job.md Linux curl snippet sends 'signature_id' (not 'signature_key_id') matching server's expected field at main.py:1098 | VERIFIED | Line 289: `"signature_id": "<key-id>"` present; `grep -c 'signature_key_id'` → 0 |
| 2  | first-job.md PowerShell submission snippet sends 'signature_id' (not 'signature_key_id') matching server's expected field at main.py:1098 | VERIFIED | Line 331: `signature_id = "<your-key-id>"` present; no `signature_key_id` remains |
| 3  | first-job.md PowerShell login section uses -SkipCertificateCheck instead of the deprecated TrustAll .NET class pattern | VERIFIED | Line 296: comment; Line 302: login call has `-SkipCertificateCheck`; Line 339: submit call has `-SkipCertificateCheck`; `grep -c 'TrustAll'` → 0 |
| 4  | No occurrence of 'signature_key_id' remains in first-job.md | VERIFIED | `grep -c 'signature_key_id'` → 0 |
| 5  | No occurrence of 'TrustAll' remains in first-job.md | VERIFIED | `grep -c 'TrustAll'` → 0 |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/docs/getting-started/first-job.md` | Correct signature_id field name in both Linux and Windows snippets + modern TLS skip pattern | VERIFIED | File exists; `signature_id` appears 2 times (Linux line 289, PowerShell line 331); `SkipCertificateCheck` appears 3 times (comment line 296, login line 302, submit line 339); `signature_key_id` count = 0; `TrustAll` count = 0 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| first-job.md Linux curl -d payload | main.py:1098 `sig_id = payload_dict.get("signature_id")` | JSON field name 'signature_id' | WIRED | Doc line 289 uses `"signature_id"` which matches server at main.py:1098 exactly |
| first-job.md PowerShell $body hashtable | main.py:1098 `sig_id = payload_dict.get("signature_id")` | JSON field name 'signature_id' | WIRED | Doc line 331 uses `signature_id` in ConvertTo-Json block which matches server at main.py:1098 exactly |
| first-job.md PowerShell -SkipCertificateCheck | enroll-node.md -SkipCertificateCheck | Same TLS skip pattern across all Windows docs | CONSISTENT | Pattern confirmed; 3 occurrences in first-job.md (comment + login + submit) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LNX-04 | 106-01-PLAN.md | First job (Python or Bash) dispatches, executes, and shows output in the dashboard | SATISFIED | `signature_id` field fixed in Linux curl snippet at line 289; server-side field at main.py:1098 now matches; pipeline unblocked |
| WIN-05 | 106-01-PLAN.md | First PowerShell job dispatches, executes, and shows output | SATISFIED | `signature_id` fixed in PowerShell $body (line 331); TrustAll replaced with -SkipCertificateCheck (lines 296, 302, 339); PowerShell pipeline unblocked |

No orphaned requirements — both IDs declared in plan are accounted for. No additional phase-106 IDs appear in REQUIREMENTS.md traceability table.

### Anti-Patterns Found

No anti-patterns detected. The change is a pure documentation fix with no code stubs, placeholder content, or TODO markers introduced.

### Human Verification Required

#### 1. End-to-end Linux signing pipeline

**Test:** On a Linux host with `openssl` and the registered signing key, follow the exact steps in the "Linux" tab of the Manual Setup section — sign a Python script and submit the job using the curl snippet at line 289.
**Expected:** The job is accepted by the server (HTTP 200), the countersign block fires (server applies its Ed25519 countersignature), and the job appears in the Jobs dashboard with output.
**Why human:** Requires a live orchestrator stack, a registered signing key UUID, and actual job execution — cannot be verified by static analysis.

#### 2. End-to-end Windows (PowerShell) signing pipeline

**Test:** On a Windows host (or Dwight via SSH) with PowerShell, follow the steps in the "Windows (PowerShell)" tab — use `-SkipCertificateCheck` on login, sign the script with Python `cryptography`, and submit using the `$body` hashtable with `signature_id`.
**Expected:** Login succeeds without TLS errors, the job is accepted (HTTP 200), and output is visible in the dashboard.
**Why human:** Requires a Windows environment, live stack, and actual PowerShell execution — cannot be verified by static analysis.

### Gaps Summary

No gaps. All five must-have truths are verified by direct file inspection:

- `signature_key_id` count in first-job.md: **0** (was the broken field name)
- `signature_id` count in first-job.md: **2** (Linux + PowerShell, matching server at main.py:1098)
- `TrustAll` count in first-job.md: **0** (deprecated pattern removed)
- `SkipCertificateCheck` count in first-job.md: **3** (comment + login call + submit call)

Both commits (`421427d`, `c7901cf`) are present in git history and map to the two planned tasks.

Requirements LNX-04 and WIN-05 are the only phase-106 requirements in REQUIREMENTS.md. Both are satisfied.

The CRLF normalization item in the phase goal was confirmed as a non-action: Phase 105 added server-side normalization, so no client-side doc change is needed. This is explicitly documented in the plan and summary as a key decision.

---

_Verified: 2026-04-01T19:00:00Z_
_Verifier: Claude (gsd-verifier)_

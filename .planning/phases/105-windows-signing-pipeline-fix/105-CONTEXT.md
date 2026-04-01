# Phase 105: Windows Signing Pipeline Fix - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Close 3 v18.0 audit gaps: restore first-job.md PowerShell tabs lost during PR #18 rebase, fix CRLF countersign asymmetry between server and node, and fix cold-start forced password change so fresh deploys always prompt. Requirements: WIN-05, WIN-03.

</domain>

<decisions>
## Implementation Decisions

### CRLF countersign fix
- Normalize CRLF to LF **server-side only** in main.py — node.py already normalizes at line 585
- Normalize before **both** user signature verification (lines ~1095-1115) AND server countersign (line 1123) — prevents CRLF scripts from failing user-sig check before reaching countersign
- Transparent to users — docs do not mention CRLF at all; server handles it silently
- Add a **unit test** that submits a script with CRLF endings and verifies the countersign matches LF-normalized bytes

### Cold-start forced password change
- **Always force** `must_change_password=True` on admin bootstrap, regardless of whether ADMIN_PASSWORD is set or auto-generated
- New env var **`ADMIN_SKIP_FORCE_CHANGE`** — when set to `true`, suppresses forced change (for CI/automation)
- compose.cold-start.yaml does NOT set `ADMIN_SKIP_FORCE_CHANGE` — fresh deploys always force password change
- compose.server.yaml (production) also does not set it — operators who want to skip must explicitly opt in

### PowerShell tab restoration
- Exact restore of Phase 103 PowerShell content in first-job.md — already validated during Windows E2E
- **Audit all getting-started docs** for missing PowerShell content, not just first-job.md (enroll-node.md and install.md should already have tabs, but verify nothing else was lost in the rebase)
- PowerShell signing snippet simplified — no CRLF normalization in the docs since server handles it transparently
- Windows API calls use **Invoke-RestMethod** (native PowerShell), not curl
- Tab format: `=== "Windows (PowerShell)"` alongside existing Linux/macOS tabs (carried from Phase 103)

### Claude's Discretion
- Exact placement of CRLF normalization within the signature verification code block
- Test structure and assertions for the CRLF unit test
- How to source Phase 103 PowerShell content (git log, SUMMARY files, or manual reconstruction)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `node.py` line 585: existing CRLF normalization pattern (`script.replace('\r\n', '\n').replace('\r', '\n')`) — replicate in main.py
- Phase 103 SUMMARY files: contain the PowerShell tab content that was merged and later lost
- `compose.cold-start.yaml`: target for the forced password change fix (line 65, `ADMIN_PASSWORD=${ADMIN_PASSWORD:-}`)

### Established Patterns
- Admin bootstrap logic in `main.py` lines 148-167: `force_change` bool controls `must_change_password`
- Tab format in docs: `=== "Windows (PowerShell)"` / `=== "Linux / macOS"` (install.md reference)
- Countersign block in main.py lines 1120-1130: `_sk.sign(script_content.encode("utf-8"))` — add normalization before `.encode()`

### Integration Points
- `main.py` countersign (line 1123): add `script_content = script_content.replace('\r\n', '\n').replace('\r', '\n')` before sign
- `main.py` user sig verify (~line 1100): same normalization before verify
- `main.py` admin bootstrap (~line 159): change `force_change = False` to `force_change = True`, gated by `ADMIN_SKIP_FORCE_CHANGE` env var
- `docs/docs/getting-started/first-job.md`: restore PowerShell tabs from Phase 103

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the audit report precisely defines the 3 gaps and the discussion locked all implementation choices.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 105-windows-signing-pipeline-fix*
*Context gathered: 2026-04-01*

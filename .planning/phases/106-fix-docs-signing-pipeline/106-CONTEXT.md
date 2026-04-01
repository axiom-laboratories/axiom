# Phase 106: Fix Docs Signing Pipeline - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 documentation bugs in `docs/docs/getting-started/first-job.md` that break the signing/submission flow for any user following the published docs. All gaps identified by the v18.0 milestone audit. Requirements: LNX-04, WIN-05.

</domain>

<decisions>
## Implementation Decisions

### Field name fix
- Replace `signature_key_id` with `signature_id` at line 289 (Linux curl snippet) and line 338 (PowerShell snippet)
- This is the root cause of both broken E2E flows — server reads `signature_id` at main.py:1098, countersign block never fires with wrong field name

### TrustAll replacement
- Replace the deprecated TrustAll .NET class pattern (lines 300-304) with `-SkipCertificateCheck` on Invoke-RestMethod/Invoke-WebRequest calls
- Consistent with enroll-node.md which already uses `-SkipCertificateCheck`

### CRLF normalization in docs
- Phase 105 added server-side CRLF normalization (main.py normalizes before both user sig verify and countersign)
- Phase 105 decision: "no CRLF normalization in the docs since server handles it transparently"
- Carry that decision forward — no client-side CRLF normalization needed in the PowerShell signing snippet

### Claude's Discretion
- Exact wording adjustments around the changed code snippets
- Whether any surrounding context in first-job.md needs updating for consistency

</decisions>

<code_context>
## Existing Code Insights

### Target File
- `docs/docs/getting-started/first-job.md`: all 3 fixes are in this single file

### Confirmed Line References (from audit + grep)
- Line 289: Linux curl `-d` payload sends `signature_key_id` — change to `signature_id`
- Lines 300-304: TrustAll .NET class — replace with `-SkipCertificateCheck`
- Line 338: PowerShell `signature_key_id` — change to `signature_id`

### Server-Side Reference
- `main.py` line 1098: reads `signature_id` from request body
- `main.py` line 1107: countersign block — only fires when `signature_id` is present
- Server-side CRLF normalization already in place (Phase 105)

### Pattern Reference
- `docs/docs/getting-started/enroll-node.md`: already uses `-SkipCertificateCheck` — this is the established pattern

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the audit report precisely defines all 3 gaps with exact line numbers and the fixes are mechanical.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 106-fix-docs-signing-pipeline*
*Context gathered: 2026-04-01*

# Phase 45: Gap Report Synthesis + Critical Fixes - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Synthesise all validation findings from Phases 38–44 into a structured gap report (`mop_validation/reports/v11.1-gap-report.md`); patch critical bugs inline with accompanying regression tests; seed the v12.0+ backlog. Source of findings: read all SUMMARY.md files from executed plans across Phases 38–44. No new validation scripts — this phase synthesises what was already found.

</domain>

<decisions>
## Implementation Decisions

### Report structure
- **Hybrid layout**: executive summary with severity counts + full prioritised findings table at the top, then findings organised by area (Foundry / Jobs / CE-EE / Security / Infrastructure) below
- Executive summary contains: X critical / Y major / Z minor counts, plus a one-row-per-finding table with ID, severity, area, and one-liner
- Each finding entry uses **5 fields**: ID | Severity | Area | Description | Reproduction steps | v12.0+ fix candidate
- Backlog section cross-references existing deferred gaps (MIN-07 after patch, MIN-08, WARN-08) with their original IDs merged into a single prioritised list — no separate gap file to consult

### Criticality thresholds
- **Critical** = silent failure producing a wrong result, data corruption, or security bypass — requires inline patch in Phase 45
- **Major** = incorrect behaviour or resource leak that degrades the system over time (e.g. /tmp accumulation, performance hazard) — deferred unless trivially patchable
- **Minor** = cosmetic, non-deterministic ordering under normal use, UX friction

### Deferred gaps resolution
- **MIN-06** (SQLite NodeStats pruning compat): **closed** — SQLite dev path retired, Postgres used for all environments. Note in report as resolved by environment.
- **MIN-07** (build dir cleanup): **patch inline** — `try/finally` + `shutil.rmtree` in `foundry_service.py`. Trivially isolated. Promoted to major during validation.
- **MIN-08** (per-request DB query in `require_permission`): **deferred to v12.0+** — performance concern only; node-facing endpoints don't use it. Needs cache invalidation design.
- **WARN-08** (non-deterministic node ID scan): **deferred to v12.0+** — only triggers if multiple certs accumulate in `secrets/`, which requires prior misuse. Document as minor.

### Regression test location
- Inline patches get **pytest tests in `puppeteer/tests/`** — run in CI, colocated with code, permanent regression guard
- For MIN-07 specifically: **also update `mop_validation/scripts/verify_foundry_04_build_dir.py`** — invert the assertion (now expects cleanup), keeps the full-stack validation script accurate for future runs

### Claude's Discretion
- Exact finding IDs and count of findings per severity (determined by reading SUMMARY.md files at execution time)
- Whether any additional findings from Phases 38–44 meet the critical threshold and need inline patches beyond MIN-07
- Ordering of findings within each area section

</decisions>

<specifics>
## Specific Ideas

- The backlog section should be ready to copy-paste as the starting point for v12.0+ milestone planning — format it as a prioritised list with enough context that the planner doesn't need to re-read the full report
- MIN-07 patch is in `puppeteer/agent_service/services/foundry_service.py` — the build dir creation/copy block; wrap in `try/finally`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/verify_foundry_04_build_dir.py`: existing gap-confirmation script — invert assertion post-patch
- All phase SUMMARY.md files in `.planning/phases/38-*/`, `39-*/`, etc.: source of truth for findings
- `puppeteer/tests/`: existing pytest suite — add regression tests here

### Established Patterns
- Finding IDs: use `GAP-` prefix with sequential numbering (GAP-01 through GAP-03 are requirements; findings use a separate ID scheme — Claude's discretion on naming)
- `[PASS]/[FAIL]` output format used in all v11.1 validation scripts — maintain for any updated scripts
- `mop_validation/reports/` as output directory for all validation artefacts

### Integration Points
- `puppeteer/agent_service/services/foundry_service.py`: MIN-07 patch location — build dir creation in `build_template()`
- `puppeteer/tests/test_foundry_service.py` (or equivalent): regression test for MIN-07

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 45-gap-report-synthesis-critical-fixes*
*Context gathered: 2026-03-22*

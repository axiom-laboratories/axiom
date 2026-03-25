# Phase 65: Friction Report Synthesis - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Write `synthesise_friction.py` (in `mop_validation/scripts/`) that reads the 4 already-pulled FRICTION files from `mop_validation/reports/` and produces `mop_validation/reports/cold_start_friction_report.md`. The report contains a cross-edition comparison table, findings grouped by severity with actionable recommendations, and a binary first-user readiness verdict. Does not pull files from LXC — pulling was done in Phases 63 and 64.

</domain>

<decisions>
## Implementation Decisions

### Script input handling
- Reads from local `mop_validation/reports/` directory — does NOT pull from LXC (already pulled in Phases 63/64)
- `--reports-dir` CLI argument with default pointing to the standard path; overridable for testing
- Fails with a clear error message (non-zero exit, lists missing files) if any of the 4 FRICTION files are absent: `FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md`, `FRICTION-EE-INSTALL.md`, `FRICTION-EE-OPERATOR.md`
- Parses FRICTION files structurally using regex/markdown parsing — no Claude API call at runtime; deterministic, runs offline

### Parsing strategy
- Friction point blocks extracted by `### [...]` heading + body containing `Classification:` and `What happened:` lines
- Primary severity tier = first word of Classification line (BLOCKER, NOTABLE, ROUGH EDGE, MINOR)
- Qualifier preserved as a note (e.g., "for CLI-only environments", "for automated harness")
- Status detection: if the finding block contains a `Fix applied:` or `Fix:` line → status = `Fixed during run`; otherwise status = `Open`
- Edition attribution: determined by which file(s) the finding appears in; findings in both CE and EE files are tagged `Shared`; findings in only one are tagged `CE-only` or `EE-only`

### Report structure
1. **Executive Summary** — run metadata (dates, editions covered), total finding counts by severity, verdict line
2. **Cross-Edition Comparison Table** — columns: `Finding | Severity | CE | EE | Status | Fix Target`
   - Status values: `Open`, `Fixed during run`, `Harness-only`
   - Fix Target: specific file path (e.g., `docs/getting-started/install.md`, `puppets/Containerfile.node`)
3. **Findings by severity** — sections for BLOCKER, NOTABLE, ROUGH EDGE in that order
   - Each finding: name, what happened (1–2 sentence summary), editions affected, status, actionable recommendation
4. **First-User Readiness Verdict** — final section, binary READY / NOT READY

### Actionable recommendations
- Each BLOCKER and NOTABLE gets: the specific file path + a one-sentence description of what to change
- Example: `docs/getting-started/install.md — Add an ADMIN_PASSWORD section before the 'docker compose up' step, explaining that a .env file with ADMIN_PASSWORD=<value> must be created first`
- No code diffs or proposed text in the report — precise enough to act without re-reading the FRICTION file

### Readiness verdict
- Assesses **as-shipped state** — what a real first-user encounters TODAY before any run-time patches are applied
- `Fixed during run` BLOCKERs count as **open** for verdict purposes (source not updated yet)
- **Harness-only BLOCKERs excluded** from verdict (Gemini quota exhaustion, `projects.json` schema crash in validation-home — these are evaluation harness issues, not product defects)
- Verdict format:
  ```
  ## First-User Readiness Verdict

  **NOT READY**

  Blocking criteria (open product BLOCKERs):
  1. Admin password not discoverable from cold-start compose (compose.cold-start.yaml + docs/getting-started/install.md)
  2. Wrong node image in enroll-node docs Option B (docs/getting-started/enroll-node.md)
  ...
  ```
- READY only if zero open product BLOCKERs remain

### Classification normalisation
- BLOCKER qualifiers respected: `for CLI-only` and `for automated harness` are noted in the report but classified differently
  - `for automated harness` / `for HOME isolation` → `Harness-only` status (excluded from verdict)
  - `for CLI-only` → still a product BLOCKER (CLI is a valid first-user path)
  - `if scenario run without pre-patch` → `Fixed during run` if the pre-patch was applied before the run, `Open` otherwise

### Claude's Discretion
- Exact regex patterns for parsing FRICTION file blocks
- How to deduplicate findings that appear in both CE and EE files with identical text (merge into one row)
- Output file path default (hardcode `mop_validation/reports/cold_start_friction_report.md` or also make it a CLI arg)

</decisions>

<specifics>
## Specific Ideas

- The "fixed during run" status is important context for the product team — these findings are cheap wins (the fix was already demonstrated to work); they just need to be merged to source
- Harness-only BLOCKERs should still appear in the report (they're real issues for the evaluation framework) — they just don't count toward the product readiness verdict
- The comparison table is the most-scanned artifact — keep it above the fold, before the detailed findings sections

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/reports/FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md`, `FRICTION-EE-INSTALL.md`, `FRICTION-EE-OPERATOR.md`: Source files — all 4 present and complete
- `mop_validation/scripts/provision_coldstart_lxc.py`, `run_ce_scenario.py`, `run_ee_scenario.py`: Pattern reference for argparse structure and `mop_validation/` path resolution

### Established Patterns
- FRICTION file format: `### [Category] Finding title` → body with `- **Classification:**`, `- **What happened:**`, `- **Fix applied:**` (optional), `- **Fix:**` (optional)
- Scripts in `mop_validation/scripts/` use `argparse` with sensible defaults
- Script output goes to `mop_validation/reports/`

### Integration Points
- `mop_validation/reports/`: Input directory (4 FRICTION files) and output directory (`cold_start_friction_report.md`)
- The report is the final deliverable of the v14.0 milestone — it feeds directly into any follow-on fix phase

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 65-friction-report-synthesis*
*Context gathered: 2026-03-25*

# Phase 94: Research & Planning Closure - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Land the APScheduler scale-limits research (merge PR #14) and create a competitor product notes file from the existing pain-points report. This phase produces no code changes — only merges an open research PR and writes one new markdown document.

</domain>

<decisions>
## Implementation Decisions

### PR #14 merge strategy
- Squash merge into main — single clean commit, consistent with how PR #10 landed
- If CI fails on secret-scan (pre-existing GITLEAKS_LICENSE gap, affects all PRs), use admin-merge to bypass — same precedent as PRs #11 and #12
- Do not wait for CI to be fixed before merging; the failure is infrastructure, not content

### APScheduler summary location
- The mop_validation report (`mop_validation/reports/apscheduler_scale_research.md`) is sufficient to satisfy success criteria #2 — no duplication in the main repo
- Todo file closure (`pending/ → done/`) is an implementation detail for the plan, not a separate decision

### Competitor product notes file
- Location: `mop_validation/reports/competitor_product_notes.md` — alongside the source `competitor_pain_points.md`
- Filename: `competitor_product_notes.md`
- Structure: brief intro + reference/link to `competitor_pain_points.md`, then 5–7 actionable observations
- Format: self-referencing (not self-contained) — avoids duplicating content from the source report
- Each observation tagged: [Positioning] / [Feature] / [Messaging]

### Competitor insights angle
- Primary lens: **gaps MoP should close** — identify recurring pain points in competitor tools that MoP currently shares or has not fully addressed (e.g. observability, onboarding friction)
- 5–7 observations total — enough to be useful without padding
- Cover themes from across the 6 competitors in the source report (Rundeck, AWX, Nomad+Vault, Temporal, Airflow, Prefect)

</decisions>

<specifics>
## Specific Ideas

- Observations should highlight patterns that recur across multiple competitors — higher signal than single-tool findings
- The five cross-cutting pain point categories from the source report (upgrade trauma, ACL complexity, observability gaps, false infrastructure abstraction, conceptual surface area) are the natural starting point for gap analysis

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code changes in this phase — research and documentation only

### Established Patterns
- Research outputs land in `mop_validation/reports/` — consistent with APScheduler report, sprint review reports, and deployment recommendations
- PRs with known CI failures (secret-scan) are merged via admin bypass — established precedent in this milestone

### Integration Points
- PR #14 (branch: `research/apscheduler-scale-limits`) is already open with the report written — merge is the only action needed
- Source competitor report: `mop_validation/reports/plans/20262903/competitor_pain_points.md` — exists and is comprehensive

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 94-research-planning-closure*
*Context gathered: 2026-03-30*

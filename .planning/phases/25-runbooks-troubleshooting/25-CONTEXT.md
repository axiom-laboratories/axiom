# Phase 25: Runbooks & Troubleshooting - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Write four operational runbook/troubleshooting pages: node troubleshooting, job execution troubleshooting, Foundry troubleshooting, and a unified FAQ. All four are symptom-first — operators find help by describing what they observe, not by knowing which internal component owns the problem. Feature guides and security guides (Phases 22–24) are complete; this phase is the final v9.0 docs content.

</domain>

<decisions>
## Implementation Decisions

### Symptom header format

- **Primary headers (H2): observable state** — what the operator sees in the dashboard or terminal, not internal component names. Examples: "Node shows Offline but container is running", "Job stuck in Queued for more than 5 minutes"
- **Secondary headers (H3): exact error message** — when a distinctive log line or UI error message identifies the specific cause, it appears as an H3 under the observable symptom H2. Combines dashboard-level navigation with log-level precision.
- **Cluster grouping by failure area**: Each runbook page uses H2 clusters (e.g., "Enrollment Failures", "Heartbeat Loss", "Cert Errors") with individual symptoms nested as H3s under the cluster. Operators who roughly know which area is broken jump to the right cluster; operators who don't know skim the clusters.
- **Quick-reference jump table at the top of every page**: One column = symptom, other column = anchor link to the section. Fast crisis navigation without relying on the sidebar ToC.

### Diagnostic depth per symptom

- **Linear structure per symptom:** Root cause (2-sentence explanation of why this happens) → numbered recovery steps → "Verify it worked" step (command + expected output) → "If still failing" escalation note (link to GitHub issues or next section)
- **Multi-cause symptoms**: When a symptom has multiple distinct causes (different root cause, different recovery), each cause gets its own H3 sub-section. Operator reads the root cause paragraph of each H3 and self-identifies which applies.
- **No branching decision trees**: No "if X try Y, if not try Z" trees. Linear steps with the verify step as the branch point ("if verify fails, see the next cause or open an issue").
- **Log snippets in code blocks**: Signing errors, dispatch errors, and cert errors include the exact log line the operator will see (e.g., `signature verification failed for job <id>`). Operators match what they observe to the section header.
- **End pattern**: Every symptom section ends with: Verify step (command + expected output), then "If the issue persists after these steps, [open an issue / check logs with X command]". No escalation matrices — just a clean "we've given you everything we know, here's what to do next."

### FAQ structure & sourcing

- **One unified FAQ page** (`runbooks/faq.md`) — single searchable page, not per-topic FAQs at the end of each runbook. Operators who don't know which component owns their problem land here.
- **Format**: Bold question as H3 header, 2–4 sentence answer, code snippet in a code block where needed. Scannable — no collapsible blocks (bad for crisis reading).
- **Required gotchas (drawn from gap reports and validation history):**
  - Blueprint packages must use `{"python": [...]}` dict format — not a plain list (silently fails during Foundry build)
  - `EXECUTION_MODE=direct` required when running Docker-in-Docker (Foundry-built nodes in containers) — Podman cgroup v2 conflict
  - JOIN_TOKEN is base64-encoded JSON containing the Root CA PEM — not a plain API key; must be set exactly as generated
  - `ADMIN_PASSWORD` in `.env` only seeds the admin account on first startup — changing it after first run has no effect on the existing DB password
- **Scope of FAQ content**: Covers both failure-mode misconfigurations AND operational how-tos that confuse first-time operators. Examples of how-tos to include: "How do I reset a node without re-enrolling?", "Why does my scheduled job not run at the expected time?" (timezone), "Can I run jobs without Ed25519 signing?" (answer: no — explain why and what to do instead)

### Cross-linking strategy

- **Minimal repetition + clear links**: State recovery steps directly in the runbook for actionable steps. For deeper background or full procedures (e.g., full cert rotation, mop-push signing workflow), cross-link to the relevant guide with a clear anchor: "See [mTLS guide → Cert Rotation](../security/mtls.md#cert-rotation) for the full procedure." Operators in crisis get immediate steps; links serve those who need context.
- **No full procedure repetition**: Do not copy the cert rotation steps from `security/mtls.md` into the node troubleshooting runbook. Reference; don't duplicate.
- **Runbooks cross-link to FAQ**: Where a runbook symptom section is explained by a known misconfiguration in the FAQ, link: "If this is caused by blueprint package format, see [FAQ → Blueprint packages dict format](./faq.md#blueprint-packages)." Prevents duplication between runbook symptom sections and FAQ entries.

### Claude's Discretion

- Exact number of FAQ entries beyond the four required gotchas and three operational how-to examples above
- Section ordering within each runbook cluster beyond the required cluster names
- Exact wording of the 2-sentence root cause explanations
- Whether the Foundry runbook clusters mirror node/job clusters or are Foundry-specific (build failures, Smelt-Check failures, registry issues as cluster names is fine — treat those as guidance, not locked)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `docs/mkdocs.yml`: Runbooks section already in nav with `runbooks/index.md`. Phase 25 adds: `runbooks/nodes.md`, `runbooks/jobs.md`, `runbooks/foundry.md`, `runbooks/faq.md`
- `docs/docs/runbooks/index.md`: Currently a stub ("coming in the next release") — Phase 25 replaces this with an overview page linking to all four runbooks
- `docs/docs/security/mtls.md`: Source for cert rotation procedure — node runbook cross-links here rather than duplicating steps
- `docs/docs/feature-guides/mop-push.md`: Source for signing workflow — job runbook cross-links here for signing key setup
- `docs/docs/feature-guides/foundry.md`: Source for blueprint format and Foundry wizard — Foundry runbook cross-links here

### Established Patterns

- `!!! danger` / `!!! warning` / `!!! tip` admonitions configured and used across Phases 22–24 — use the same pattern inline at the point of risk
- Admonition-as-gotcha: inline at the step where the risk/gotcha occurs, not in a separate section
- `<PLACEHOLDER>` syntax for all sensitive values in code blocks (JOIN_TOKEN, cert paths, API keys)
- No screenshots — reference actual UI labels as they appear in the dashboard (e.g., "the node status badge in the Nodes view")
- Stub-first nav pattern: add all four runbook nav entries and create stub files first, then fill content in separate plans — ensures `mkdocs build --strict` passes throughout

### Integration Points

- `docs/mkdocs.yml`: Add 5 entries under Runbooks nav: `runbooks/index.md` (update stub), `runbooks/nodes.md`, `runbooks/jobs.md`, `runbooks/foundry.md`, `runbooks/faq.md`
- `docs/docs/runbooks/`: Create nodes.md, jobs.md, foundry.md, faq.md

</code_context>

<specifics>
## Specific Ideas

- The jump table at the top of each runbook is the key navigational feature — operators search the observable symptom (what they see), not the component name. Make the table prominent.
- Log snippet code blocks for signing and cert errors are essential: operators copy-paste their error into their browser search; if the exact string appears on the page, they land in the right section.
- The FAQ's "Can I run jobs without Ed25519 signing?" entry should answer honestly (no) and explain why (signature verification is enforced at the node before execution — it is not configurable), then point to the mop-push guide for how to set up signing.
- ADMIN_PASSWORD gotcha has caught real operators — document clearly that the `.env` value is only a seed for the first run and that the DB password is the source of truth for existing deployments.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-runbooks-troubleshooting*
*Context gathered: 2026-03-17*

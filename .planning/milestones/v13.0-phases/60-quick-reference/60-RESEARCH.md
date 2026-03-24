# Phase 60: Quick Reference - Research

**Researched:** 2026-03-24
**Domain:** HTML content authoring, MkDocs static site integration, content accuracy audit
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**File relocation and naming**
- Both files move from repo root to `docs/docs/quick-ref/` (for MkDocs to serve them at `/quick-ref/`)
- Filenames change: `master_of_puppets_course.html` → `quick-ref/course.html`, `master_of_puppets_operator_guide.html` → `quick-ref/operator-guide.html`
- `quick-ref/index.md` is created as an intro page describing what each file is, with links to open them
- A new top-level **'Quick Reference'** section is added to `docs/mkdocs.yml` nav, containing the index page and links to both HTML files
- The old files at the repo root are deleted (moved, not copied)

**Rebranding scope**
- Replace all `Master of Puppets` and `MoP` occurrences in `course.html` with `Axiom`
- Add an `Axiom` subtitle to the course hero section (e.g., title becomes "How Axiom Works" or similar)
- Update the HTML `<title>` tag in course.html to reflect "Axiom"
- Operator guide hero meta line (`Stack: FastAPI + React dashboard`) — leave as-is, already accurate

**Scheduling Health in operator guide**
- Add a Scheduling Health sub-section inside **Module 4: Scheduling Jobs** (not a new module)
- Full walkthrough depth: explain each metric (LATE, MISSED, `last_fire`, `next_fire`), when to act on them, and how to access `GET /api/health/scheduling`
- Include retention config: explain the retention setting in Admin (how long execution records are kept) and why it matters when investigating LATE/MISSED jobs

**Course content update depth**
- Full accuracy review — not just a terminology pass
- Verify all file paths and tool names referenced in the course against the actual codebase; update any stale references
- Review interactive quiz/challenge content: verify questions and answers are still correct for the current architecture
- Update any examples or descriptions that describe old behaviour (e.g., outdated CLI commands, old task type names)

### Claude's Discretion
- Exact prose for the Scheduling Health walkthrough
- Exact wording for the course hero subtitle
- Structure and formatting of `quick-ref/index.md`
- How mkdocs.yml links to raw HTML files (MkDocs supports `!` prefix for non-markdown pages or direct nav paths)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QREF-01 | Both HTML files moved from project root to `quick-ref/` directory | File location is `docs/docs/quick-ref/` — MkDocs default docs_dir is `docs/docs/`; placing HTML there serves them at `/quick-ref/`. Old root files must be deleted. |
| QREF-02 | Course file rebranded from "Master of Puppets" to "Axiom" throughout | Audit found 6 occurrences of "Master of Puppets" in course.html; the `<title>` tag is one. No `MoP` abbreviation found. Operator guide is already branded "Axiom". |
| QREF-03 | Operator guide updated for v12.0 feature set (new views, task types, form modes, node states) | Queue view (`Queue.tsx`) and Scheduling Health tab (HealthTab.tsx in JobDefinitions) are confirmed v12.0 additions not yet in the guide. `DRAINING` node state IS present. Guided/Advanced dispatch IS documented at line 1500. All three runtimes (Python/Bash/PowerShell) ARE documented at line 1524. The only missing piece is Scheduling Health sub-section in Module 4. |
| QREF-04 | Course content updated to reflect current architecture and tooling | All file path references (`node.py`, `runtime.py`, function names `bootstrap_trust`, `fetch_verification_key`, `execute_task`, `poll_for_work`, `runtime_engine`) verified correct against actual codebase. `python_script` task_type deprecated (server rejects it) but not mentioned in course — no fix needed. Course has no operator-guide style tool path hardcoding. |
</phase_requirements>

## Summary

Phase 60 is a content-only phase: no new backend or frontend code. The work is three distinct tasks — file relocation into the MkDocs docs tree, rebranding the course HTML, and extending the operator guide with a Scheduling Health section.

The MkDocs site uses the default `docs_dir: docs/docs/`. HTML files placed there are served directly by MkDocs Material without any special configuration — the `quick-ref/` subdirectory under `docs/docs/` will be served at `https://.../quick-ref/`. The nav entry uses standard `.html` paths, not markdown; MkDocs Material handles this correctly without the `!` prefix convention.

Course file rebranding is straightforward: 6 occurrences of "Master of Puppets" in `course.html` (1 in `<title>`, 1 in `<nav>` brand label, 4 in body text), plus one `<title>` update. The operator guide is already branded "Axiom" and requires no title/brand changes. The course architecture references (`node.py`, `runtime.py`, function names) are verified correct against the current codebase — no stale references exist. The operator guide references `toms_home` path for the `admin_signer.py` tool; this is a developer context note and CONTEXT.md does not flag it for removal, so leave it.

The Scheduling Health addition to Module 4 is the most substantive task. The feature is fully implemented: `GET /api/health/scheduling?window=24h|7d|30d` returns aggregate + per-definition counts with `fired`, `skipped`, `failed`, `late`, `missed` fields. LATE means a fire was expected and has not yet occurred within the grace period (5 minutes) but a future fire is still scheduled. MISSED means the expected window passed with no fire and the next expected fire has also passed.

**Primary recommendation:** Execute as three sequential tasks — (1) relocate files and update mkdocs.yml nav, (2) rebrand course.html, (3) add Scheduling Health sub-section to Module 4 of operator-guide.html plus full course accuracy review.

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| MkDocs Material | already installed (see `docs/requirements.txt`) | Serves the docs site; HTML files placed in `docs/docs/` are served directly | Project standard since Phase 59 |
| Python `str.replace` / text editor | n/a | In-place HTML text substitution for rebranding | No templating needed — files are self-contained |

### No New Dependencies

This phase introduces no new libraries. All tooling is in place from Phase 59.

## Architecture Patterns

### MkDocs HTML File Serving

MkDocs Material serves any file placed inside `docs_dir` as-is. The default `docs_dir` is `docs/` relative to `mkdocs.yml` — in this project that means `docs/docs/`. HTML files in `docs/docs/quick-ref/` are accessible at `https://<site>/quick-ref/course.html` without additional configuration.

Nav entry pattern for HTML files in `mkdocs.yml`:
```yaml
nav:
  - Quick Reference:
    - Overview: quick-ref/index.md
    - Course — How Axiom Works: quick-ref/course.html
    - Operator Guide: quick-ref/operator-guide.html
```

MkDocs Material accepts `.html` nav entries directly. No `!` prefix or plugin is required. The HTML files will not be processed — they render exactly as authored.

### Recommended Project Structure After Phase 60
```
docs/docs/
├── quick-ref/           # NEW — move here from repo root
│   ├── index.md         # NEW — intro/landing page
│   ├── course.html      # moved from master_of_puppets_course.html
│   └── operator-guide.html  # moved from master_of_puppets_operator_guide.html
└── ... (existing dirs unchanged)
```

Root cleanup:
```
# Delete from repo root:
master_of_puppets_course.html
master_of_puppets_operator_guide.html
```

### Pattern: In-Place Text Substitution for Rebranding

The HTML files are self-contained (inline CSS, inline base64 images). Rebranding is pure text replacement — no asset paths or external links affected.

**course.html replacements (all 6 occurrences):**
- Line 6: `<title>Master of Puppets — How It Works Under the Hood</title>` → `<title>Axiom — How It Works Under the Hood</title>`
- Line 613: `<span class="nav-title">Master of Puppets</span>` → `<span class="nav-title">Axiom</span>`
- Line 756: `Master of Puppets is not one program` → `Axiom is not one program`
- Line 885: `...API key. But if one node is compromised, every node is compromised. Master of Puppets uses something much stronger...` → `...Axiom uses something much stronger...`
- Line 891: `...Master of Puppets runs its own private CA...` → `...Axiom runs its own private CA...`
- Line 1681: `...That's a known weakness. Master of Puppets solves it with token_version...` → `...Axiom solves it with token_version...`

**operator-guide.html:** No "Master of Puppets" occurrences found in non-base64 content. `<title>` already reads "Axiom — Operator Guide". No changes needed for QREF-02.

### Pattern: Scheduling Health Sub-Section in Module 4

Insert after the existing Module 4 quiz (line ~1832) and before Module 5 (line ~1869), OR insert as a new `<div class="section">` block inside Module 4 before the quiz. The CONTEXT.md says "inside Module 4" — position it before the Module 4 Check quiz for logical flow.

The section must cover:
1. **What the Health tab shows** — accessed via the Health tab in Job Definitions (`/job-definitions`)
2. **The four key metrics**: fired, skipped, late, missed
3. **LATE vs MISSED distinction** (operationally important)
4. **The API endpoint**: `GET /api/health/scheduling?window=24h|7d|30d`
5. **Retention and its effect on health data**

**Verified operational semantics from `scheduler_service.py`:**
- `fired`: the scheduler successfully dispatched the job for this fire slot
- `skipped`: the slot was intentionally skipped (DRAFT status, or overlapping previous run)
- `late`: expected fire slot passed but no match found AND the next scheduled fire has NOT yet passed — the job is behind but could still fire
- `missed`: expected fire slot passed AND the next scheduled fire has also passed — the window is gone; investigate
- `failed`: dispatched job subsequently reached FAILED status
- Health roll-up: `ok` = no missed and no failed; `warning` = late > 0; `error` = missed > 0 or failed > 0
- Grace period: 5 minutes — a job fired within 5 min of expected counts as on-time

**Retention connection**: `GET /api/admin/retention` / `PATCH /api/admin/retention` — default 14 days. If `execution_retention_days` is set to a short window (e.g. 7 days), LATE/MISSED data for the `30d` window may be incomplete because fire log rows older than retention are pruned.

### Anti-Patterns to Avoid
- **Do not copy files instead of moving them**: CONTEXT.md says delete the root originals — having duplicates would break QREF-01.
- **Do not modify mkdocs.yml to use `!` prefix**: Not needed for HTML files; Material theme handles them natively.
- **Do not add Scheduling Health as a new Module**: CONTEXT.md explicitly says sub-section inside Module 4.
- **Do not remove `toms_home` admin_signer.py references in operator guide**: These are developer notes, not incorrect content. CONTEXT.md scope is v12.0 feature additions and terminology — not tool path cleanup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| MkDocs HTML serving | Custom static file plugin or symlinks | Place file in `docs/docs/quick-ref/` and add nav entry — MkDocs handles it |
| Rebranding automation | Find-replace script | Direct text edit — 6 targeted line changes, deterministic |

## Common Pitfalls

### Pitfall 1: Wrong Target Directory
**What goes wrong:** Moving HTML files to `quick-ref/` at repo root instead of `docs/docs/quick-ref/` — MkDocs won't serve files outside its `docs_dir`.
**Why it happens:** CONTEXT.md says "quick-ref/" ambiguously; the clarification note says "place under `docs/docs/quick-ref/`".
**How to avoid:** Target path is `docs/docs/quick-ref/` (relative to repo root) = `quick-ref/` relative to mkdocs docs source.
**Warning signs:** `mkdocs build --strict` succeeds but `/quick-ref/course.html` returns 404.

### Pitfall 2: Leaving Root Files in Place
**What goes wrong:** Forgetting to delete `master_of_puppets_course.html` and `master_of_puppets_operator_guide.html` from repo root.
**Why it happens:** Move is implemented as copy + add to docs tree, but delete step is missed.
**How to avoid:** `git rm` the root HTML files as an explicit step in the plan.

### Pitfall 3: mkdocs build --strict Failure on Nav
**What goes wrong:** Adding nav entries for files that don't exist yet (or have wrong paths) causes `mkdocs build --strict` to exit non-zero.
**Why it happens:** Nav is updated before files are created, or path typo.
**How to avoid:** Create `quick-ref/` directory and all three files before running the build check.

### Pitfall 4: Breaking Inline base64 Content During Rebranding
**What goes wrong:** A global find-replace hits "master" inside a base64 string or CSS variable name.
**Why it happens:** Broad regex patterns on large files.
**How to avoid:** Use line-specific targeted replacements at the known line numbers, not a global regex. Verify file size stays approximately the same after changes.

### Pitfall 5: Missing the `late` metric in operator guide
**What goes wrong:** Operator guide documents `missed` but not `late`, leaving operators confused about the amber warning state.
**Why it happens:** LATE is subtler than MISSED and easy to overlook.
**How to avoid:** Explicitly document both states with operational guidance: LATE = act soon (investigate scheduler/node load); MISSED = investigate cause (was scheduler stopped? were all nodes offline?).

## Code Examples

### mkdocs.yml Quick Reference Nav Entry
```yaml
# Source: verified against current docs/mkdocs.yml structure and MkDocs Material docs
nav:
  - Home: index.md
  # ... existing sections ...
  - Quick Reference:
    - Overview: quick-ref/index.md
    - Course — How Axiom Works: quick-ref/course.html
    - Operator Guide: quick-ref/operator-guide.html
```

### Scheduling Health Section HTML Pattern (matches operator-guide.html style)
```html
<!-- Insert as final <div class="section"> before the Module 4 quiz -->
<div class="section">
  <h3 class="section-title">Scheduling Health</h3>
  <p class="section-body">
    The <strong>Health</strong> tab in the Scheduled Jobs page shows how reliably each
    definition has been firing over the selected window (24 h, 7 d, 30 d). Use it to
    catch silent failures before they impact operations.
  </p>

  <!-- metric table, LATE vs MISSED callout, API note, retention callout -->
</div>
```

### Retention API Reference (for operator guide prose)
```
GET  /api/admin/retention          → { retention_days: 14, total: N, prunable: M }
PATCH /api/admin/retention         → body: { "retention_days": 30 }
```
Retention prunes execution records older than `retention_days` (default 14). The Health tab
queries `ScheduledFireLog` rows — those are also pruned. Set retention to at least as long
as your longest health window (30 days) to get complete LATE/MISSED data.

## State of the Art

| Old State | Current State | Notes |
|-----------|--------------|-------|
| `task_type: "python_script"` | `task_type: "script"` + `runtime: "python"` | Server actively rejects `python_script`; the course does not mention `python_script` so no course change needed |
| Course branded "Master of Puppets" | Needs rebranding to "Axiom" | Operator guide already says "Axiom" |
| No Scheduling Health in operator guide | Scheduling Health tab exists in Job Definitions page | Full implementation live — `GET /api/health/scheduling` |
| No Queue view documented | `Queue.tsx` view exists in dashboard | Queue view is a dedicated view separate from the Jobs page; operator guide mentions "Queue Monitor" panel inside Jobs page but not the dedicated Queue route |

### Note on Queue View Coverage

The operator guide at line 1044 describes the Jobs page as "The job queue. Dispatch one-off scripts, monitor their status in real time, bulk-cancel or resubmit, download output." A separate `Queue.tsx` view exists at the `/queue` route (confirmed in codebase). CONTEXT.md says "operator guide covers... new views (Queue, Scheduling Health)". The Queue view needs a brief mention in the operator guide's "Know Your Dashboard" module (Module 1 which lists the navigation pages).

## Open Questions

1. **Queue view coverage depth**
   - What we know: `Queue.tsx` exists as a dedicated route; Module 1 of the operator guide lists dashboard pages; the CONTEXT.md says Queue is a new view to cover
   - What's unclear: whether Queue needs its own section or just a nav card mention in Module 1
   - Recommendation: Add a brief nav card description in Module 1 (matching the style of other page descriptions at lines 1037–1044) — a full walkthrough sub-section is probably not needed unless the planner decides otherwise

2. **admin_signer.py path currency**
   - What we know: operator guide references `python ~/Development/toms_home/.agents/tools/admin_signer.py` at lines 1901 and 1973; CLAUDE.md confirms this tool exists at that path
   - What's unclear: whether this path is reliable across deployments or should be updated to the `axiom-push` CLI
   - Recommendation: Leave as-is; it is a developer tool reference and CONTEXT.md scopes QREF-03/04 to feature additions and old terminology, not tool path cleanup

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (frontend) + pytest (backend) |
| Config file | `puppeteer/dashboard/vitest.config.ts` (inferred) / `puppeteer/pytest.ini` (if exists) |
| Quick run command | `cd puppeteer/dashboard && npm run test` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map

This phase is pure content/documentation — no new API routes, no new React components, no new database models. All tests are non-automated content checks.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QREF-01 | Files live at `docs/docs/quick-ref/`, root files deleted | manual-only | `ls docs/docs/quick-ref/ && ! ls master_of_puppets_*.html 2>/dev/null` | N/A |
| QREF-01 | MkDocs build succeeds with new nav entries | smoke | `cd docs && mkdocs build --strict` | ✅ existing |
| QREF-02 | No "Master of Puppets" or "MoP" text in course.html | automated | `grep -c "Master of Puppets\|MoP" docs/docs/quick-ref/course.html` returns 0 | ❌ Wave 0 |
| QREF-03 | Scheduling Health section present in operator-guide.html | automated | `grep -c "Scheduling Health" docs/docs/quick-ref/operator-guide.html` returns >= 1 | ❌ Wave 0 |
| QREF-04 | No `python_script` references in course.html | automated | `grep -c "python_script" docs/docs/quick-ref/course.html` returns 0 | ❌ Wave 0 |

**Manual-only justification (QREF-01, QREF-02, QREF-03, QREF-04):** All verifications are file content checks runnable via shell grep/ls commands in under 5 seconds. No test framework infrastructure needed.

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Phase gate:** `mkdocs build --strict` green + manual content review before `/gsd:verify-work`

### Wave 0 Gaps
- Shell verification commands above are one-liners; no test files to create
- No pytest or vitest changes needed — this phase does not touch Python or TypeScript code

## Sources

### Primary (HIGH confidence)
- Direct inspection of `/home/thomas/Development/master_of_puppets/master_of_puppets_course.html` — line-level audit of all "Master of Puppets" occurrences
- Direct inspection of `/home/thomas/Development/master_of_puppets/master_of_puppets_operator_guide.html` — module structure, existing v12.0 coverage audit
- Direct inspection of `puppeteer/agent_service/services/scheduler_service.py` lines 275–400 — exact LATE/MISSED/fired/skipped semantics
- Direct inspection of `puppeteer/agent_service/models.py` — `SchedulingHealthResponse`, `JobCreate.runtime` field, `python_script` deprecation
- Direct inspection of `puppeteer/agent_service/main.py` — `GET /api/health/scheduling`, retention endpoints, DRAINING state endpoints
- Direct inspection of `docs/mkdocs.yml` — current nav structure and site configuration
- Direct inspection of `puppeteer/dashboard/src/views/Queue.tsx`, `JobDefinitions.tsx`, `HealthTab.tsx` — confirmed v12.0 UI features

### Secondary (MEDIUM confidence)
- MkDocs Material documentation (training knowledge, verified consistent with project's working `mkdocs build --strict` pattern from Phase 59)

## Metadata

**Confidence breakdown:**
- File locations and MkDocs nav pattern: HIGH — verified against actual project structure
- Rebranding scope (which lines to change): HIGH — line-level audit performed
- Scheduling Health semantics: HIGH — read directly from `scheduler_service.py` implementation
- course.html architecture accuracy: HIGH — all referenced function/file names verified against current codebase

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable content — no external library dependencies)

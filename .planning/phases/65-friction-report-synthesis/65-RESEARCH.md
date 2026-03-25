# Phase 65: Friction Report Synthesis - Research

**Researched:** 2026-03-25
**Domain:** Python scripting — markdown parsing, report generation, CLI tooling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase boundary:**
- Reads from local `mop_validation/reports/` — does NOT pull from LXC (already pulled in Phases 63/64)
- `--reports-dir` CLI argument with default pointing to standard path; overridable for testing
- Fails with clear error (non-zero exit, lists missing files) if any of the 4 FRICTION files absent: `FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md`, `FRICTION-EE-INSTALL.md`, `FRICTION-EE-OPERATOR.md`
- Parses FRICTION files structurally using regex/markdown parsing — no Claude API call at runtime; deterministic, runs offline

**Parsing strategy:**
- Friction point blocks extracted by `### [...]` heading + body containing `Classification:` and `What happened:` lines
- Primary severity tier = first word of Classification line (BLOCKER, NOTABLE, ROUGH EDGE, MINOR)
- Qualifier preserved as a note (e.g., "for CLI-only environments", "for automated harness")
- Status detection: block contains `Fix applied:` or `Fix:` line → status = `Fixed during run`; otherwise status = `Open`
- Edition attribution: findings in both CE and EE files tagged `Shared`; otherwise `CE-only` or `EE-only`

**Report structure:**
1. Executive Summary — run metadata, total finding counts by severity, verdict line
2. Cross-Edition Comparison Table — columns: `Finding | Severity | CE | EE | Status | Fix Target`
   - Status values: `Open`, `Fixed during run`, `Harness-only`
   - Fix Target: specific file path
3. Findings by severity — BLOCKER, NOTABLE, ROUGH EDGE sections
   - Each: name, what happened (1–2 sentence summary), editions affected, status, actionable recommendation
4. First-User Readiness Verdict — final section, binary READY / NOT READY

**Actionable recommendations:**
- Each BLOCKER and NOTABLE: specific file path + one-sentence description of what to change
- No code diffs or proposed text — precise enough to act without re-reading the FRICTION file

**Readiness verdict:**
- Assesses as-shipped state — what a real first-user encounters TODAY before run-time patches
- `Fixed during run` BLOCKERs count as **open** for verdict purposes (source not updated yet)
- Harness-only BLOCKERs excluded from verdict (Gemini quota exhaustion, `projects.json` schema crash)
- READY only if zero open product BLOCKERs remain

**Classification normalisation:**
- `for automated harness` / `for HOME isolation` → `Harness-only` status (excluded from verdict)
- `for CLI-only` → still a product BLOCKER (CLI is a valid first-user path)
- `if scenario run without pre-patch` → `Fixed during run` if pre-patch was applied, `Open` otherwise

### Claude's Discretion

- Exact regex patterns for parsing FRICTION file blocks
- How to deduplicate findings that appear in both CE and EE files with identical text (merge into one row)
- Output file path default (hardcode `mop_validation/reports/cold_start_friction_report.md` or also make it a CLI arg)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RPT-01 | Final friction report merges CE and EE FRICTION.md files into a single deliverable with cross-edition comparison, BLOCKER/NOTABLE/MINOR triage, actionable recommendations per finding, and a verdict on first-user readiness | Full synthesis of all 4 FRICTION files; script structure from run_ce_scenario.py pattern; complete finding inventory below |
</phase_requirements>

---

## Summary

Phase 65 is a pure Python scripting task: write `synthesise_friction.py` in `mop_validation/scripts/` that reads the 4 completed FRICTION files from `mop_validation/reports/` and produces a single synthesis report. All 4 source files exist and are fully populated (read and verified during research). The script is deterministic, runs offline, and requires no external APIs.

The domain is well-understood: Python's `re` module and `pathlib.Path` are sufficient for the complete implementation. No third-party libraries are needed. The existing scripts in `mop_validation/scripts/` (particularly `run_ce_scenario.py`) establish the argparse and path constant patterns to follow.

The critical research value in this phase is having pre-read all 4 FRICTION files in full, so the planner and implementer know exactly what findings exist and how they relate across editions. This pre-analysis prevents surprises during parsing implementation.

**Primary recommendation:** Implement as a single self-contained Python file following the existing mop_validation script pattern. Use regex with `re.DOTALL` to extract `### [...]` blocks, then parse classification/status lines within each block. Deduplicate cross-edition findings by normalised title before producing the report.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `re` | 3.x | FRICTION block parsing via regex | No deps; `re.DOTALL` handles multi-line blocks |
| Python stdlib `pathlib` | 3.x | File I/O, path resolution | Already used across all mop_validation scripts |
| Python stdlib `argparse` | 3.x | `--reports-dir` / `--output` CLI flags | Established pattern in this repo |
| Python stdlib `sys` | 3.x | Non-zero exit on missing files | Standard |
| Python stdlib `datetime` | 3.x | Report generation timestamp | Standard |

### No External Dependencies Required

All needed functionality is in the standard library. Do not add third-party markdown parsing libraries (overkill for this structured format). The FRICTION file format is regular enough for regex.

**Installation:** None required — pure stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
mop_validation/scripts/synthesise_friction.py   # New file — single module
mop_validation/reports/cold_start_friction_report.md  # Output
```

### Pattern 1: Path Constants (from run_ce_scenario.py)

**What:** Define absolute path defaults as module-level constants, then allow override via `--reports-dir`.
**When to use:** Always — matches existing script convention.

```python
# Source: /home/thomas/Development/mop_validation/scripts/run_ce_scenario.py (lines 33–36)
DEFAULT_REPORTS_DIR = "/home/thomas/Development/mop_validation/reports"

def parse_args():
    p = argparse.ArgumentParser(description="Synthesise CE/EE friction reports.")
    p.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    p.add_argument("--output", default=None,
                   help="Output path (default: <reports-dir>/cold_start_friction_report.md)")
    return p.parse_args()
```

### Pattern 2: FRICTION Block Extraction

**What:** Use `re.findall` with `re.DOTALL` to split the file into `### [Category] Title` blocks.
**When to use:** For each of the 4 FRICTION files.

```python
BLOCK_RE = re.compile(
    r"^(### \[.*?\] .+?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)
```

Each match is a complete friction point block. Parse fields from within using simpler line-level patterns:

```python
CLASSIFICATION_RE = re.compile(r"\*\*Classification:\*\*\s*(.+)")
WHATHAPPENED_RE   = re.compile(r"\*\*What happened:\*\*\s*(.+)")
FIX_APPLIED_RE    = re.compile(r"\*\*(Fix applied|Fix):\*\*")
HEADING_RE        = re.compile(r"^### (\[.*?\]) (.+)$", re.MULTILINE)
```

### Pattern 3: Deduplication by Normalised Title

**What:** Normalise finding titles (lowercase, strip leading `[Tag]`) and compare across files. Identical or near-identical titles in CE and EE files should be merged into one row tagged `Shared`.
**When to use:** During the cross-edition comparison table build step.

```python
def normalise_title(heading_text: str) -> str:
    # Strip [Category] prefix, lowercase, strip whitespace
    return re.sub(r"^\[.*?\]\s*", "", heading_text).strip().lower()
```

Deduplication strategy: build a dict keyed by normalised title. First occurrence sets the record; second occurrence from a different edition upgrades edition attribution from `CE-only`/`EE-only` to `Shared`.

### Pattern 4: Classification Normalisation

**What:** Convert the raw Classification line to a canonical tier and status.

```python
RAW_TO_TIER = {
    "BLOCKER": "BLOCKER",
    "NOTABLE": "NOTABLE",
    "ROUGH EDGE": "ROUGH EDGE",
    "MINOR": "MINOR",
}

def classify(raw: str) -> tuple[str, str]:
    """Returns (tier, status)."""
    raw_upper = raw.upper()
    # Harness-only detection
    if any(kw in raw_upper for kw in ("FOR AUTOMATED HARNESS", "HOME ISOLATION", "FOR HOME")):
        return "BLOCKER", "Harness-only"
    # Fixed-during-run detection (check block for Fix applied / Fix lines)
    # ... caller checks block body separately
    for tier in ("BLOCKER", "NOTABLE", "ROUGH EDGE", "MINOR"):
        if raw_upper.startswith(tier):
            return tier, "Open"
    return "MINOR", "Open"
```

Note: `Fixed during run` status requires checking the block body for `Fix applied:` or `Fix:` lines, independent of the Classification text.

### Anti-Patterns to Avoid

- **Using a third-party markdown parser:** Overkill for this structured format; adds a dependency for no benefit.
- **Making the verdict dynamic by re-parsing the output report:** Compute the verdict in-memory from the parsed findings dict, not by re-reading the output file.
- **Relying on line position for field extraction:** Use field-name regex (`\*\*Classification:\*\*`) not line indices — the number of lines per block varies.
- **Splitting on `###` without anchoring to line start:** Use `re.MULTILINE` so `^` matches start of each line; otherwise embedded `###` inside code blocks can false-match.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown table formatting | Custom column-width calculator | f-string with fixed column separator | The report is read in a markdown viewer that handles column widths |
| Similarity matching for dedup | Fuzzy string matching | Exact normalised-title match | All shared findings have the same title; no fuzzy matching needed for this dataset |
| Multi-step find-and-replace for severity | Complex state machine | Simple regex per field | The FRICTION format is regular and consistent |

---

## Complete Finding Inventory (Pre-Analysis)

This is the authoritative inventory of all findings across all 4 files. The planner and implementer should verify the script produces exactly this set.

### FRICTION-CE-INSTALL.md Findings

| Title (normalised) | Severity | Has Fix? | Status |
|--------------------|----------|----------|--------|
| Docs path mismatch | BLOCKER | Fix applied | Fixed during run |
| Docs assume GitHub clone available | ROUGH EDGE | No | Open |
| Admin password not set in cold-start compose | BLOCKER | Fix applied | Fixed during run |
| JOIN_TOKEN requires dashboard GUI | BLOCKER (CLI-only qualifier) | No | Open (product BLOCKER) |
| Docs show wrong node image | BLOCKER | No | Open |
| EXECUTION_MODE=direct is removed from code | BLOCKER | No | Open |
| TLS cert mismatch when using documented AGENT_URL | BLOCKER | No | Open |
| Node containers in compose don't have Docker socket | ROUGH EDGE | Fix applied | Fixed during run |

### FRICTION-CE-OPERATOR.md Findings

| Title (normalised) | Severity | Has Fix? | Status |
|--------------------|----------|----------|--------|
| Guided form requires browser — no CLI path | BLOCKER (CLI-only) | No | Open |
| Docker CLI missing from cold-start node image | BLOCKER | Fix applied | Fixed during run |
| DinD /tmp mount creates directories instead of files | BLOCKER | Fix applied | Fixed during run |
| Wrong image tag in runtime.py default | BLOCKER | Fix applied | Fixed during run |
| PowerShell not in cold-start node image | BLOCKER | Fix applied | Fixed during run |
| Ed25519 signing path undocumented for cold-start | NOTABLE | No | Open |

### FRICTION-EE-INSTALL.md Findings

| Title (normalised) | Severity | Has Fix? | Status |
|--------------------|----------|----------|--------|
| Gemini CLI projects.json schema crash | BLOCKER (harness) | Fix applied | Harness-only |
| Gemini free-tier quota exhausted | BLOCKER (harness) | No | Harness-only |
| AXIOM_EE_LICENCE_KEY vs AXIOM_LICENCE_KEY naming mismatch | MINOR | No | Open |
| /api/admin/features endpoint does not exist | BLOCKER | Fix applied | Fixed during run |
| No EE section in getting-started/install.html | ROUGH EDGE | No | Open |
| AXIOM_LICENCE_KEY injection: compose block vs secrets.env | ROUGH EDGE | No | Open |

### FRICTION-EE-OPERATOR.md Findings

| Title (normalised) | Severity | Has Fix? | Status |
|--------------------|----------|----------|--------|
| Guided form requires browser — no CLI path | BLOCKER (CLI-only) | No | Open (Shared with CE) |
| No signing key pre-registered on fresh EE stack | NOTABLE | No | Open |
| Ed25519 signing key must be fetched from inside the agent container | NOTABLE | No | Open |
| /api/executions not EE-gated in CE mode | NOTABLE | No | Open |
| docker compose restart does not re-read .env | BLOCKER (harness script) | No | Harness-only |

### Cross-Edition Sharing Analysis

**Shared findings (appear in both CE and EE):**
- "Guided form requires browser — no CLI path" — CE-OPERATOR + EE-OPERATOR → `Shared`
- "Ed25519 signing path undocumented" / "Ed25519 signing key must be fetched from inside container" — related but distinct framings; these are NOT identical titles, keep separate rows in the table but note they are related

**Open product BLOCKERs (determine verdict):**
1. JOIN_TOKEN requires dashboard GUI — CLI-only qualifier is still a product blocker
2. Docs show wrong node image — `enroll-node.md` Option B
3. EXECUTION_MODE=direct is removed from code — `enroll-node.md` Option B
4. TLS cert mismatch on documented AGENT_URL — `enroll-node.md` / `compose.cold-start.yaml`
5. Guided form requires browser — no CLI path (CE + EE shared)

**Fixed-during-run BLOCKERs (count as Open for verdict per CONTEXT.md):**
- Admin password not set in cold-start compose (Fixed: wrote .env)
- Docs path mismatch (Fixed: symlinks)
- Docker CLI missing from node image (Fixed: docker cp)
- DinD /tmp mount issue (Fixed: volume mount)
- Wrong image tag (Fixed: docker tag)
- PowerShell not in image (Fixed: rebuilt)

**Verdict: NOT READY** — minimum 5 open product BLOCKERs (JOIN_TOKEN CLI, wrong node image, removed EXECUTION_MODE, TLS cert mismatch, no CLI dispatch path). Even fixed-during-run BLOCKERs count as open per the defined verdict logic.

---

## Common Pitfalls

### Pitfall 1: ROUGH EDGE Multi-Word Severity Tier

**What goes wrong:** The regex `raw_upper.startswith("ROUGH")` works, but `ROUGH EDGE` must be detected before `ROUGH` if you check for `NOTABLE`/`BLOCKER`/`MINOR`/`ROUGH` separately.
**Why it happens:** ROUGH EDGE is two words; the Classification line reads `ROUGH EDGE — explanation`.
**How to avoid:** Check for `ROUGH EDGE` as a unit before other single-word tiers. The `startswith` order matters.
**Warning signs:** Findings classified as `ROUGH` (unknown tier) instead of `ROUGH EDGE`.

### Pitfall 2: Block Boundary at End of File

**What goes wrong:** The final `### [...]` block is not followed by another `### [...]` heading — the lookahead `(?=^### |\Z)` must use `\Z` (end of string) to capture the last block.
**Why it happens:** `re.DOTALL` with `(?=^### )` alone misses the final block.
**How to avoid:** Always include `|\Z` in the lookahead.

### Pitfall 3: Fixed-During-Run Classification for BLOCKERs

**What goes wrong:** A BLOCKER with `Fix applied:` in its block is marked `Fixed during run` but the CONTEXT.md rule is: `Fixed during run` BLOCKERs still count as **open** for the readiness verdict.
**Why it happens:** Natural temptation to treat "fixed" as not blocking.
**How to avoid:** Status `Fixed during run` is a display status only. Verdict logic counts it as open: `if finding.tier == "BLOCKER" and finding.status != "Harness-only": verdict = NOT_READY`.

### Pitfall 4: Harness-only Qualifier Detection

**What goes wrong:** The "Gemini quota" BLOCKER and "projects.json schema crash" BLOCKER must not be counted toward the product readiness verdict — they are evaluation harness issues.
**Why it happens:** The Classification line may read just `BLOCKER (for automated agent runs)` without the exact string "for automated harness".
**How to avoid:** Check for qualifier patterns: `"automated harness"`, `"HOME isolation"`, `"agent run"`, `"evaluation harness"`. Apply this at parse time to set status = `Harness-only`.

### Pitfall 5: Shared Finding Deduplication — Same Title, Different Files

**What goes wrong:** "Guided form requires browser — no CLI path" appears in both FRICTION-CE-OPERATOR.md and FRICTION-EE-OPERATOR.md with near-identical text. If dedup is not applied, the comparison table shows two rows instead of one `Shared` row.
**Why it happens:** The same doc/product gap is independently documented in both operator scenarios.
**How to avoid:** After collecting all findings from all files, group by normalised title. If a normalised title appears in ≥2 files from different editions, merge to a single row with `Shared` attribution. Keep the first-seen finding's text as canonical.

---

## Code Examples

### FRICTION Block Regex (verified against actual files)

```python
# Extracts each "### [Category] Title\n body..." block
BLOCK_RE = re.compile(
    r"(^### \[.*?\] .+?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)

# Within a block: heading components
HEADING_RE = re.compile(r"^### (\[.*?\])\s+(.+)$", re.MULTILINE)

# Within a block: Classification line (bold markdown format)
CLASS_RE = re.compile(r"\*\*Classification:\*\*\s*(.+?)(?:\n|$)")

# Within a block: What happened (first sentence only for summary)
WHAT_RE = re.compile(r"\*\*What happened:\*\*\s*(.+?)(?:\n|$)")

# Within a block: Fix applied OR Fix (any variant signals "Fixed during run")
FIX_RE = re.compile(r"\*\*Fix(?:\s+applied)?:\*\*")
```

These patterns are verified against the actual FRICTION file format observed in all 4 files (bold `**Field:**` format, `### [Category] Title` headings).

### Verdict Logic

```python
def compute_verdict(findings: list[Finding]) -> tuple[str, list[str]]:
    """
    Returns ("READY" | "NOT READY", blocking_criteria_list).
    Fixed-during-run BLOCKERs count as open. Harness-only excluded.
    """
    blocking = [
        f for f in findings
        if f.tier == "BLOCKER" and f.status != "Harness-only"
    ]
    if blocking:
        return "NOT READY", [f.title for f in blocking]
    return "READY", []
```

### Missing File Error

```python
def check_inputs(reports_dir: Path) -> None:
    required = [
        "FRICTION-CE-INSTALL.md",
        "FRICTION-CE-OPERATOR.md",
        "FRICTION-EE-INSTALL.md",
        "FRICTION-EE-OPERATOR.md",
    ]
    missing = [f for f in required if not (reports_dir / f).exists()]
    if missing:
        print(f"ERROR: Missing required FRICTION files in {reports_dir}:")
        for f in missing:
            print(f"  - {f}")
        sys.exit(1)
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing in mop_validation) |
| Config file | None detected in mop_validation/ — inline |
| Quick run command | `cd /home/thomas/Development/mop_validation && python synthesise_friction.py --reports-dir reports/ --output /tmp/test_report.md && grep -q "NOT READY" /tmp/test_report.md` |
| Full suite command | `python synthesise_friction.py --reports-dir reports/ && python -c "import pathlib; r = pathlib.Path('reports/cold_start_friction_report.md').read_text(); assert 'NOT READY' in r; assert 'Cross-Edition' in r; print('PASS')"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RPT-01 | Script runs without error against 4 real FRICTION files | smoke | `python mop_validation/scripts/synthesise_friction.py` | ❌ Wave 0 |
| RPT-01 | Output file contains Cross-Edition Comparison Table | smoke | `grep -q "Cross-Edition" reports/cold_start_friction_report.md` | ❌ Wave 0 |
| RPT-01 | Output file contains NOT READY verdict | smoke | `grep -q "NOT READY" reports/cold_start_friction_report.md` | ❌ Wave 0 |
| RPT-01 | All 4 source FRICTION files produce findings | smoke | Check finding count > 0 in report | ❌ Wave 0 |
| RPT-01 | Script exits non-zero when a FRICTION file is missing | unit | `python synthesise_friction.py --reports-dir /tmp/empty; echo $?` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python mop_validation/scripts/synthesise_friction.py && grep -q "NOT READY" mop_validation/reports/cold_start_friction_report.md`
- **Per wave merge:** Full smoke battery above
- **Phase gate:** `cold_start_friction_report.md` exists, contains all 4 sections, verdict present

### Wave 0 Gaps

- [ ] `mop_validation/scripts/synthesise_friction.py` — the script itself (the deliverable)
- [ ] Manual review of `mop_validation/reports/cold_start_friction_report.md` against the finding inventory in this research file

---

## Sources

### Primary (HIGH confidence)

- Direct read of all 4 FRICTION files in `mop_validation/reports/` — complete finding inventory verified
- Direct read of `mop_validation/scripts/run_ce_scenario.py` — argparse/path constant patterns confirmed
- Direct read of `.planning/phases/65-friction-report-synthesis/65-CONTEXT.md` — all decisions locked

### Secondary (MEDIUM confidence)

- Python `re` module `DOTALL` + `MULTILINE` flag behaviour — standard library, well-understood
- FRICTION file format consistency — confirmed by reading all 4 files; format is uniform across CE/EE and install/operator scenarios

### Tertiary (LOW confidence)

None — all claims verified against source files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib, no external dependencies, verified against existing scripts
- Architecture: HIGH — all 4 FRICTION files read and parsed manually; regex patterns derived from actual format
- Pitfalls: HIGH — identified from actual format quirks observed in files and CONTEXT.md decision rules
- Finding inventory: HIGH — read directly from source files, pre-analysis complete

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable — FRICTION files are static artifacts, won't change)

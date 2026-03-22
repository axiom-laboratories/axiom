# Phase 45: Gap Report Synthesis + Critical Fixes - Research

**Researched:** 2026-03-22
**Domain:** Gap synthesis, inline bug patching, regression test authoring, pytest
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Report structure:**
- Hybrid layout: executive summary with severity counts + full prioritised findings table at the top, then findings organised by area (Foundry / Jobs / CE-EE / Security / Infrastructure) below
- Executive summary contains: X critical / Y major / Z minor counts, plus a one-row-per-finding table with ID, severity, area, and one-liner
- Each finding entry uses 5 fields: ID | Severity | Area | Description | Reproduction steps | v12.0+ fix candidate
- Backlog section cross-references existing deferred gaps (MIN-07 after patch, MIN-08, WARN-08) with their original IDs merged into a single prioritised list — no separate gap file to consult

**Criticality thresholds:**
- Critical = silent failure producing a wrong result, data corruption, or security bypass — requires inline patch in Phase 45
- Major = incorrect behaviour or resource leak that degrades the system over time — deferred unless trivially patchable
- Minor = cosmetic, non-deterministic ordering under normal use, UX friction

**Deferred gaps resolution:**
- MIN-06 (SQLite NodeStats pruning compat): closed — SQLite dev path retired, Postgres used for all environments
- MIN-07 (build dir cleanup): patch inline — `try/finally` + `shutil.rmtree` in `foundry_service.py`. Trivially isolated. Promoted to major
- MIN-08 (per-request DB query in `require_permission`): deferred to v12.0+
- WARN-08 (non-deterministic node ID scan): deferred to v12.0+

**Regression test location:**
- Inline patches get pytest tests in `puppeteer/tests/` — permanent regression guard
- For MIN-07: also update `mop_validation/scripts/verify_foundry_04_build_dir.py` — invert assertion

### Claude's Discretion
- Exact finding IDs and count of findings per severity (determined by reading SUMMARY.md files at execution time)
- Whether any additional findings from Phases 38–44 meet the critical threshold and need inline patches beyond MIN-07
- Ordering of findings within each area section

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GAP-01 | Living gap report `mop_validation/reports/v11.1-gap-report.md` with every finding from Phases 38–44, each with severity, area, reproduction steps, v12.0+ fix candidate | All SUMMARY.md files inventoried below; findings catalogued with severity assignments |
| GAP-02 | All critical findings patched inline with regression tests that fail before fix, pass after | Critical findings identified; MIN-07 status clarified (code already patched, test missing); regression test patterns documented |
| GAP-03 | Final gap report includes prioritised backlog for v12.0+ with deferred items cross-referenced to MIN-06, MIN-07, MIN-08, WARN-08 | Deferred item disposition researched and documented |
</phase_requirements>

## Summary

Phase 45 is a synthesis-and-patch phase, not a new feature phase. Its core work is: (1) read all SUMMARY.md files from Phases 38–44, extract every documented finding, classify each by severity, and write a structured gap report; (2) identify which findings reach the critical threshold and patch them inline with regression tests; (3) produce a prioritised v12.0+ backlog.

The primary technical finding from research is that **MIN-07 is already patched in the codebase** (`foundry_service.py` lines 241-243 contain `try/finally: shutil.rmtree(build_dir)`). The gap was real when first catalogued, but was fixed during the implementation of FOUNDRY mirror features. What remains for Phase 45 is to: (a) write a regression test asserting the rmtree is called, and (b) invert the assertion in `verify_foundry_04_build_dir.py` (which was written expecting the gap to exist). The test in `test_foundry_mirror.py` mocks `shutil.rmtree` but does not assert it is called — the regression test must add that assertion.

From reading all 21 SUMMARY.md files across Phases 38–44, no additional critical-threshold findings emerged beyond MIN-07. Two significant bugs were found and patched inline during execution (not as Phase 45 deferred items): the `app.state.licence` missing initialisation (42-02) and the EE plugin expiry bypass (42-02). Both are already committed with a fix. The remaining findings fall into major and minor categories.

**Primary recommendation:** Write the gap report by extracting findings from SUMMARY.md files, apply the MIN-07 regression test (the only outstanding inline patch), invert verify_foundry_04_build_dir.py, and populate the v12.0+ backlog from the findings catalogue. No new code infrastructure is needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | existing in puppeteer/tests/ | Regression test authoring | Already installed; all existing tests use it |
| pytest-asyncio | existing | Async test support for foundry_service tests | All foundry_service tests use @pytest.mark.asyncio |
| unittest.mock (stdlib) | stdlib | Mocking shutil.rmtree for cleanup assertion | Used in test_foundry_mirror.py |
| markdown (text) | N/A | Gap report format | mop_validation/reports/ uses .md files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shutil | stdlib | rmtree call in foundry_service.py | Already imported in foundry_service.py |

**Installation:** No new packages required. Existing test infrastructure is sufficient.

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/reports/
└── v11.1-gap-report.md         # Output: gap report (GAP-01, GAP-03)

puppeteer/tests/
└── test_foundry_build_cleanup.py  # New: MIN-07 regression test (GAP-02)

mop_validation/scripts/
└── verify_foundry_04_build_dir.py  # Modify: invert assertion post-patch (GAP-02)
```

### Pattern 1: Gap Report Document Structure
**What:** Markdown file with hybrid layout — executive summary at top, then findings by area
**When to use:** This is the single output artefact for GAP-01 and GAP-03

```markdown
# v11.1 Gap Report

**Generated:** 2026-03-22
**Phases covered:** 38–44
**Summary:** X critical / Y major / Z minor findings

## Executive Summary

| ID | Severity | Area | One-liner |
|----|----------|------|-----------|
| FIND-01 | major | Foundry | MIN-07: build dir not cleaned up on success |
| ...

## Findings by Area

### Foundry
#### FIND-01 — [Severity]: [Title]
**Description:**
**Reproduction steps:**
**v12.0+ fix candidate:** / **Status: patched in Phase 45**

## Deferred Backlog (v12.0+)

| Priority | ID | Origin | Description | Effort |
|----------|----|--------|-------------|--------|
...
```

### Pattern 2: MIN-07 Regression Test (the one inline patch needed)
**What:** pytest test asserting `shutil.rmtree` is called in the finally block of `build_template()`
**When to use:** This is the regression test required for GAP-02 on MIN-07

```python
# Source: existing test_foundry_mirror.py pattern
@pytest.mark.asyncio
async def test_build_dir_cleaned_up_on_success():
    """MIN-07 regression: build_dir must be removed in finally block after a successful build."""
    # ... setup tmpl/rt_bp/nw_bp mocks following test_foundry_mirror.py pattern ...
    with patch("shutil.rmtree") as mock_rmtree, \
         patch("os.makedirs"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("asyncio.create_subprocess_exec") as mock_proc:
        # simulate successful build
        ...
        await FoundryService.build_template("t1", mock_db)
    # Assert rmtree was called with the build_dir path
    assert mock_rmtree.called, "shutil.rmtree was not called — build_dir leak regression"
    assert "puppet_build" in str(mock_rmtree.call_args[0][0])

@pytest.mark.asyncio
async def test_build_dir_cleaned_up_on_failure():
    """MIN-07 regression: build_dir must be removed even when build raises an exception."""
    with patch("shutil.rmtree") as mock_rmtree, \
         patch("os.makedirs"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("asyncio.create_subprocess_exec") as mock_proc:
        mock_proc.side_effect = RuntimeError("docker build failed")
        try:
            await FoundryService.build_template("t1", mock_db)
        except Exception:
            pass
    assert mock_rmtree.called, "shutil.rmtree not called on build failure — finally block missing"
```

### Anti-Patterns to Avoid
- **Finding IDs that collide with requirement IDs:** GAP-01/02/03 are phase requirements. Use a distinct scheme for individual findings (e.g. FIND-01, FIND-02, or area-prefixed like FOUNDRY-GAP-01). Claude's discretion per CONTEXT.md.
- **Conflating SKIP with FAIL in Phase 44:** All FOUNDRY scripts ran as [SKIP] on the CE stack. This is not a finding — it is expected pre-flight behaviour. Do not log these as gaps.
- **Re-logging bugs already patched during execution:** Bugs patched inline during Phases 41-43 (app.state.licence, EE expiry bypass, retriable flag, global declaration) are already fixed with commits. They should appear in the report as "patched during v11.1" not "deferred".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Assertion that rmtree is called | Custom file-system watcher | `unittest.mock.patch("shutil.rmtree")` with `assert mock.called` | Already used pattern in test_foundry_mirror.py |
| Gap report markdown formatting | Custom renderer | Plain markdown with pipe tables | mop_validation/reports/ uses plain .md |
| Finding ID tracking | Separate database | Sequential numbering in the report itself | One-time artefact, no tooling needed |

## Common Pitfalls

### Pitfall 1: Assuming MIN-07 is NOT yet patched
**What goes wrong:** The CONTEXT.md says "patch inline — try/finally + shutil.rmtree". If the planner assumes this code change is still needed and schedules it, it will find the code already present.
**Why it happens:** The fix was applied as part of the FOUNDRY mirror feature work, not as a named MIN-07 patch. The try/finally block at lines 241-243 of foundry_service.py IS the MIN-07 fix.
**How to avoid:** Read foundry_service.py before planning the patch task. The task is "write the regression test and invert verify_foundry_04_build_dir.py" — not "add try/finally to foundry_service.py".
**Warning signs:** If a plan task says "add try/finally to foundry_service.py build_dir block", that task is wrong.

### Pitfall 2: Double-counting bugs patched mid-flight vs deferred
**What goes wrong:** Bugs fixed inline during Phases 42-43 (app.state.licence, EE expiry gate, retriable flag, global _current_env_tag) appear in SUMMARY.md deviations. If logged as deferred findings, the backlog is polluted.
**Why it happens:** SUMMARY.md deviations list everything that was auto-fixed. These are not open gaps.
**How to avoid:** Only include open/deferred items in the gap report backlog. Items with "Committed in: XXXXXX" are closed.
**Warning signs:** A backlog item that references a commit hash from Phases 41-43 is already closed.

### Pitfall 3: Phase 44 FOUNDRY scripts all SKIP = no findings
**What goes wrong:** Because all 6 Foundry scripts exited [SKIP] on the CE stack, someone might conclude there are no Foundry-area findings.
**Why it happens:** The scripts were designed to SKIP gracefully; they couldn't exercise EE features.
**How to avoid:** The Foundry findings come from CONTEXT.md and the SUMMARY.md key-decisions, not from script pass/fail output. FOUNDRY-04 (MIN-07 build dir cleanup), FOUNDRY-06 (audit log gap for WARNING mode) are real findings documented in 44-02-SUMMARY.md.
**Warning signs:** "No Foundry findings" in the gap report.

### Pitfall 4: verify_foundry_04_build_dir.py assertion direction
**What goes wrong:** The script was written expecting the gap to exist (confirms gap or confirms fix). After the MIN-07 patch is confirmed present, the assertion needs inverting to treat "build dir cleaned up" as the [PASS] condition.
**Why it happens:** The original script uses dual-outcome design (GAP CONFIRMED = [PASS], GAP FIXED = [PASS]). Post-patch, only "GAP FIXED" is [PASS]; "GAP CONFIRMED" should become [FAIL].
**How to avoid:** The CONTEXT.md explicitly calls out: "invert the assertion (now expects cleanup)". The script update is mandatory, not optional.

### Pitfall 5: Audit log gap for FOUNDRY-06 WARNING mode
**What goes wrong:** FOUNDRY-06 noted that the audit log does not contain a distinguishable WARNING entry when a template is built in WARNING mode — `is_compliant=False` is the only signal. This is a real observability gap.
**Why it happens:** The EE smelter audit log writes `template:build` events but doesn't tag them with the enforcement mode or warning state.
**How to avoid:** Log this as a major finding (observability degradation) with a v12.0+ fix candidate of "add enforcement_mode to audit log payload".

## Code Examples

Verified patterns from existing codebase:

### MIN-07 fix — already in place at foundry_service.py lines 181-243
```python
# Source: puppeteer/agent_service/services/foundry_service.py lines 181–243
try:
    # ... docker build subprocess ...
    tmpl.current_image_uri = image_uri
    tmpl.last_built_at = datetime.utcnow()
    tmpl.status = "STAGING"
    # ...
    return {"status": f"SUCCESS (Smelt-Check: {tmpl.status})", ...}
finally:
    if os.path.exists(build_dir):
        await asyncio.to_thread(shutil.rmtree, build_dir)
```

The fix is already present. The regression test must assert `shutil.rmtree` is called.

### Regression test structure — follows existing test_foundry_mirror.py pattern
```python
# Source: puppeteer/tests/test_foundry_mirror.py — _make_mock_db, @pytest.mark.asyncio pattern
@pytest.mark.asyncio
async def test_build_dir_cleaned_up_on_failure():
    mock_db = _make_mock_db(tmpl, rt_bp, nw_bp, ing)
    with patch("shutil.rmtree") as mock_rmtree, \
         patch("os.makedirs"), \
         patch("shutil.copytree"), \
         patch("shutil.copy2"), \
         patch("asyncio.create_subprocess_exec") as mock_proc:
        mock_proc.side_effect = RuntimeError("simulated docker failure")
        try:
            await FoundryService.build_template("t1", mock_db)
        except Exception:
            pass
    assert mock_rmtree.called
```

### Gap report finding entry format
```markdown
#### FIND-01 — Major: Build directory not cleaned up on build failure (MIN-07)
**Area:** Foundry
**Severity:** Major (resource leak — /tmp accumulation)
**Description:** foundry_service.build_template() creates /tmp/puppet_build_{id}_{hash}/ for every build.
Without cleanup, each failed build leaks ~10-100 MB to /tmp until disk exhaustion.
**Reproduction steps:**
1. Trigger a build with an invalid base image (e.g. nonexistent-image:does-not-exist-99999)
2. SSH to puppeteer host: `ls /tmp/puppet_build_*` — directory persists after build failure
**Status:** Patched in Phase 45 (try/finally + shutil.rmtree already in foundry_service.py lines 241–243);
regression test added in puppeteer/tests/test_foundry_build_cleanup.py
**v12.0+ fix candidate:** N/A — closed
```

## Findings Catalogue (from SUMMARY.md analysis)

This is the pre-synthesised list of findings for the planner. The executing agent must verify each entry by re-reading relevant SUMMARY.md files, but this provides the starting inventory.

### Critical (0 found)
No finding from Phases 38–44 meets the critical threshold (silent wrong result, data corruption, or security bypass) that has not already been patched inline during execution.

**Previously critical items already patched:**
- `app.state.licence` never populated (42-02 ef2f88c) — was producing wrong edition response
- EE plugin loading unconditionally on expired licence (42-02 36394dc) — licence expiry bypass
- `retriable=True` absent from node.py result (43-08 3fe63c8) — jobs silently not retrying
- `global _current_env_tag` used before declaration (43-08 35c987c) — node crash on startup

All four are closed with commits. None are Phase 45 inline patch candidates.

### Major (2 confirmed)
- **MIN-07** (build dir leak): Foundry. Code patched (lines 241-243). Regression test missing. Verify_foundry_04 assertion inverted needed.
- **FOUNDRY-06 audit gap**: Foundry/EE. WARNING mode builds not distinguishable in audit log — is_compliant=False is the only signal; audit log lacks enforcement_mode tag. Deferred to v12.0+.

### Minor (deferred, well-known)
- **MIN-08** (per-request DB in require_permission): Performance. Deferred per CONTEXT.md.
- **WARN-08** (non-deterministic node ID scan): Infrastructure. Deferred per CONTEXT.md.
- **MIN-06** (SQLite NodeStats pruning): Closed — SQLite dev path retired.
- **JOB-05 node_id attribution**: Observability. Execution records don't include which node_id executed the job. Documented as [INFO] in verify_job_05.
- **JOB-08 audit log for SECURITY_REJECTED**: Security/Observability. The audit log entry for signature rejection is not verified — noted as a todo in 43-07 SUMMARY. Minor: the rejection itself works, only the audit entry is uncertain.
- **Verification key drift (41-02)**: Infrastructure. Container's `/app/secrets/verification.key` can drift from host canonical key after CE/EE image rebuilds. Operator must rebuild image to bake in canonical keys.
- **Docker binary absent from puppet-node image**: Infrastructure/Ops. puppet-node image doesn't include docker CLI; requires bind-mount from LXC host. Documented pattern in 43-08.
- **POST /jobs returns 200 not 201**: API conformance. Minor cosmetic issue; scripts already accept both.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MIN-07 gap (build dir leak) | try/finally with shutil.rmtree | During FOUNDRY mirror work | Build dirs cleaned on success and failure |
| EE plugin unconditional load | Expiry gated by CE lifespan() before load_ee_plugins() | Phase 42-02 (36394dc) | Expired licence correctly degrades to CE mode |
| app.state.licence None | Parsed from AXIOM_LICENCE_KEY in lifespan() | Phase 42-02 (ef2f88c) | GET /api/licence returns correct edition |
| node.py no retriable flag | retriable=(exit_code != 0 and max_retries > 0) | Phase 43-08 (3fe63c8) | DEAD_LETTER retry pipeline works end-to-end |

**Deprecated/outdated:**
- MIN-06 (SQLite NodeStats pruning): closed by environment — all environments now use Postgres
- verify_foundry_04_build_dir.py dual-outcome assertion: must be inverted post-patch to treat cleanup as the expected outcome

## Open Questions

1. **FOUNDRY-06 audit log gap severity**
   - What we know: WARNING mode builds proceed, is_compliant=False is set, but audit log doesn't tag the event distinctly
   - What's unclear: Whether there's a generic audit log entry for template:build that could be read for compliance; only observable on EE stack
   - Recommendation: Log as major (observability degradation in a security-sensitive area); v12.0+ fix is to add `enforcement_mode` to the audit event payload

2. **JOB-08 SECURITY_REJECTED audit entry**
   - What we know: Signature rejection is correctly handled (node rejects, execution record shows rejection); audit log entry existence was not verified
   - What's unclear: Whether an audit log entry is actually written on SECURITY_REJECTED (deferred in 43-07 as [INFO])
   - Recommendation: Log as minor finding; v12.0+ fix is to add an audit.write() call in the security rejection path of job_service.py

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | puppeteer/pytest.ini or inferred from pyproject (not checked; tests run from `cd puppeteer && pytest`) |
| Quick run command | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAP-01 | Gap report written with all findings | manual/output | inspect `mop_validation/reports/v11.1-gap-report.md` | No — Wave 0 |
| GAP-02 | MIN-07 regression: rmtree called on success | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py::test_build_dir_cleaned_up_on_success -x` | No — Wave 0 |
| GAP-02 | MIN-07 regression: rmtree called on failure | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py::test_build_dir_cleaned_up_on_failure -x` | No — Wave 0 |
| GAP-02 | verify_foundry_04 inverted assertion | integration | `python mop_validation/scripts/verify_foundry_04_build_dir.py` | Yes — needs modification |
| GAP-03 | Backlog section in gap report | manual/output | inspect `mop_validation/reports/v11.1-gap-report.md` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green + gap report file exists + verify_foundry_04 exits 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_foundry_build_cleanup.py` — MIN-07 regression tests (GAP-02)
- [ ] `mop_validation/reports/v11.1-gap-report.md` — primary output artefact (GAP-01, GAP-03)

*(verify_foundry_04_build_dir.py exists and needs assertion inversion — not a new file gap)*

## Sources

### Primary (HIGH confidence)
- Direct read of foundry_service.py lines 241-243 — confirmed try/finally + shutil.rmtree is present
- Direct read of test_foundry_mirror.py — confirmed rmtree is mocked but not asserted called
- Direct read of all 21 SUMMARY.md files across Phases 38–44

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions section — disposition of MIN-06/07/08/WARN-08 verified against code

### Tertiary (LOW confidence)
- None — all claims verified against source files or SUMMARY.md records

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing pytest + mock infrastructure
- Architecture: HIGH — gap report format and regression test pattern both derived from existing codebase conventions
- Pitfalls: HIGH — all pitfalls derived from direct code inspection and SUMMARY.md cross-referencing
- Findings catalogue: HIGH for closed items (commits verified), MEDIUM for deferred minor items (from SUMMARY.md notes, not live stack verification)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain — no external dependencies)

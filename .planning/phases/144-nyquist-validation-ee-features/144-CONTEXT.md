# Phase 144: Nyquist Validation — EE Features - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Run `/gsd:validate-phase` for all 4 EE licence protection phases (137–140) and fill any test coverage gaps found. Each phase currently has `nyquist_compliant: false` in its VALIDATION.md. This phase makes them compliant.

Out of scope: implementing new EE features, changing production EE logic beyond fixing a confirmed regression, adding new licence protection mechanisms.

</domain>

<decisions>
## Implementation Decisions

### Pre-existing test failure
- `test_reload_licence_with_invalid_key` in `test_licence_service.py` is currently failing
- Investigate root cause — diagnose whether it's a stale test expectation or a genuine production regression
- Fix whatever is broken: if production code regressed, fix it; if the test expectation is wrong, fix the test
- Phase 138 **cannot** be marked `nyquist_compliant: true` until all tests in `test_licence_service.py` pass, including this one
- Block on green — no partial compliance

### Dual test suite strategy
- Phase 137, 138, and 139 compliance is verified via: `cd puppeteer && pytest -x -q`
- Phase 140 compliance is verified separately via: `cd axiom-licenses && pytest tests/tools/ -x -q`
- These are treated as two independent compliance blocks, not merged
- If axiom-licenses tests fail, Phase 144 investigates and fixes them — same ownership model as puppeteer failures

### Gap status assessment
- Compliance check is **behavior-based**, not test-ID-name-matching
- VALIDATION.md Wave 0 maps were written before implementation — test IDs may differ from actual test names
- A success criterion is "covered" if at least one passing test verifies the described behavior
- For any success criterion from the roadmap phase description that has **zero test coverage**, write a new test
- Items in the VALIDATION.md "Manual-Only Verifications" table remain manual — do not automate them

### Execution order
- Sequential: 137 → 138 → 139 → 140
- Each phase fully validated (tests green, VALIDATION.md updated) before moving to the next
- After completing all 4 phases: run `cd puppeteer && pytest -x -q` once as final regression check
- Then run `cd axiom-licenses && pytest tests/ -q` as final Phase 140 check
- Per-phase: run targeted test subset first, full suite only at the end

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/tests/test_ee_manifest.py` (492 lines) — already covers Phase 137 (manifest verification) and Phase 139 (entry point whitelist). Likely fills most Wave 0 gaps for both.
- `puppeteer/tests/test_encryption_key_enforcement.py` (82 lines) — already covers Phase 139 EE-06 (ENCRYPTION_KEY enforcement).
- `puppeteer/tests/test_licence_service.py` — has HMAC boot log tests (grep hits at lines 615+) for Phase 138, but has one failing test to fix first.
- `axiom-licenses/tests/tools/test_gen_wheel_key.py`, `test_sign_wheels.py`, `test_key_resolution.py` — written during Phase 142; covers Phase 140 EE-05.

### Established Patterns
- Phase 143 pattern: run validate-phase per phase, read VALIDATION.md, audit behavior coverage, fill gaps, mark compliant
- EE tests are fully unit-level (no live Docker stack required)
- axiom-licenses is a separate pytest project with its own `requirements.txt` and test runner

### Integration Points
- VALIDATION.md frontmatter: set `nyquist_compliant: true` and `wave_0_complete: true` once all tests for a phase pass
- Per-task verification map in each VALIDATION.md should reflect actual test names after audit (update if needed)

</code_context>

<specifics>
## Specific Ideas

- The failing test `test_reload_licence_with_invalid_key` is the first thing to diagnose — it will reveal whether Phase 138's HMAC implementation is fully correct
- The test file `test_ee_manifest.py` covers both Phase 137 and Phase 139 behaviors (manifest verification + entry point whitelist). The auditor should verify this cross-phase coverage is explicit in both VALIDATION.md files.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 144-nyquist-validation-ee-features*
*Context gathered: 2026-04-14*

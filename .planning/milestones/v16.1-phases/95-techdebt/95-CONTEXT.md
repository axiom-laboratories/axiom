# Phase 95: techdebt - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the five tech debt items documented in the v16.1 milestone audit. No new capabilities — this phase exists solely to complete what was left incomplete across phases 92, 93, and 94.

Items in scope:
1. Port `test_signing_ux.py` from `feat/usp-signing-ux` to main with the 403→422 assertion fix
2. Fix `SIGN_CMD` placeholder in `Signatures.tsx` (change `"hello.py"` → `"YOUR_SCRIPT.py"`) + verify full command accuracy
3. Create `VALIDATION.md` for phases 92, 93, and 94 to achieve Nyquist compliance
4. Strike through DOC-01 and DOC-03 in `REQUIREMENTS.md`
5. Update plan frontmatter in 94-01-PLAN.md and 94-02-PLAN.md to reference `SCALE-01` instead of `RES-01`/`PLAN-01`

</domain>

<decisions>
## Implementation Decisions

### Test porting (item 1)
- Port `test_signing_ux.py` as-is from the feature branch — no scope expansion, no rewrite
- Fix the 403→422 assertion to match current `main.py` behaviour (422 Unprocessable Entity for bad-signature paths)
- Land in `puppeteer/agent_service/tests/` — matches existing `testpaths` config, no pytest changes needed
- Fixture approach: generate a fresh Ed25519 keypair per test run; register it via the API — self-contained, no secrets in repo
- Reference pattern: the test suite already uses isolated SQLite DBs per test (see `conftest.py` `engine` fixture) — follow that pattern

### SIGN_CMD placeholder (item 2)
- Change the assigned value from `"hello.py"` to `"YOUR_SCRIPT.py"` in `Signatures.tsx` line 77
  - The variable is already named `YOUR_SCRIPT`; only its string value needs updating
- While touching the file, review the full `SIGN_CMD` string for accuracy against the current signing workflow (not just the filename)
- Surgical edit only — no other UI changes

### Nyquist VALIDATION.md (item 3)
- Create VALIDATION.md for all three phases: 92, 93, and 94
- Phase 92 (signing UX — code phase): validation = run the ported test, verify it passes
- Phase 93 (docs PRs — documentation phase): validation = verify deliverables exist on disk + `mkdocs build --strict` exits 0 + `tools/validate_docs.py` reports 0 failures
- Phase 94 (research/planning — research phase): validation = verify research report files exist on disk + todos closed in STATE.md

### Admin tracking fixes (items 4 and 5)
- Strike through DOC-01 and DOC-03 in `REQUIREMENTS.md` body (same style as DOC-02: `~~DOC-01~~`)
- Update frontmatter in `94-01-PLAN.md` and `94-02-PLAN.md` to reference `SCALE-01` instead of `RES-01`/`PLAN-01`

### Claude's Discretion
- Exact structure and content of VALIDATION.md files for 93 and 94 (within the verify-deliverables-exist + links-resolve approach)
- Whether to verify the SIGN_CMD command end-to-end in a test or just inspect it manually

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `conftest.py` `engine` fixture: creates isolated SQLite DB per test, patches `AsyncSessionLocal` — the signing test fixture should follow this pattern
- `Signatures.tsx` `SIGN_CMD` const (line 73–85): the inline heredoc Python script — only line 77 needs changing
- `puppeteer/agent_service/tests/` testpath: all test files here are auto-discovered, no pytest.ini changes needed

### Established Patterns
- Tests use `anyio_backend` + async pytest fixtures (see `conftest.py`)
- Signing workflow: `cryptography` Ed25519, `serialization.load_pem_private_key`, `private_key.sign(content.encode("utf-8"))`, base64-encode the result
- REQUIREMENTS.md strike-through format: `~~REQ-ID~~` inline in the body text + ✓ date annotation

### Integration Points
- `POST /jobs/definitions` is the endpoint under test — requires a registered signature and a signed script
- `Signatures.tsx` SIGN_CMD is rendered in a `<pre>` block with a `CopyButton` — only the const value needs changing, no JSX changes
- Nyquist VALIDATION.md location: `.planning/phases/{NN}-{slug}/VALIDATION.md`

</code_context>

<specifics>
## Specific Ideas

- The SIGN_CMD review should check that the script correctly signs `script_content.encode("utf-8")` (matching `main.py`'s verify call) — the current code looks correct but confirm it while touching the file
- For Phase 92 VALIDATION.md: a single `pytest puppeteer/agent_service/tests/test_signing_ux.py` command as the verification step is sufficient

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 95-techdebt*
*Context gathered: 2026-03-30*

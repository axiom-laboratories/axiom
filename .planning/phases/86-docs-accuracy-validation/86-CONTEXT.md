# Phase 86: Docs Accuracy Validation - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

A Python script (`tools/validate_docs.py`) that cross-references docs markdown against three sources of truth: the committed OpenAPI snapshot, `mop_sdk/cli.py` subcommands, and production codebase env vars. Produces PASS/WARN/FAIL output per item with file+line refs, exits 1 on any WARN or FAIL for CI gating. A companion `tools/generate_openapi.py` populates the openapi.json snapshot from the running Docker stack.

</domain>

<decisions>
## Implementation Decisions

### OpenAPI snapshot strategy
- This phase delivers TWO scripts: `tools/generate_openapi.py` (snapshot generator) and `tools/validate_docs.py` (validator)
- `generate_openapi.py` hits the running Docker stack's `/openapi.json` endpoint and saves the result to `docs/docs/api-reference/openapi.json`
- Same operator pattern as screenshot capture — run against a live Docker stack, commit the populated snapshot
- `validate_docs.py` exits 2 (distinct from validation exit 1) with a clear error if it detects an empty/stub snapshot (no paths in the spec): "OpenAPI snapshot is empty. Run tools/generate_openapi.py first."
- A populated snapshot is committed as part of this phase's deliverables

### PASS/WARN/FAIL semantics
- **FAIL** — API route path+method mentioned in docs but not present in openapi.json snapshot
- **FAIL** — `axiom-push <subcommand>` pattern in docs that is not registered in `mop_sdk/cli.py`
- **WARN** — Env var name mentioned in docs that does not appear in the production codebase
- **CI gate is strict: any WARN or FAIL causes exit 1 and blocks the merge**
- PASS = item found and confirmed in source of truth
- Exit codes: 0 = all PASS, 1 = any WARN or FAIL, 2 = snapshot missing/stub

### Validation scope — API routes
- Extract route patterns from all `docs/docs/**/*.md` files
- Detect: `GET /api/...`, `POST /api/...`, `PUT /api/...`, `DELETE /api/...`, `PATCH /api/...` (both inline prose and code blocks)
- Match against openapi.json: check both path existence AND HTTP method
- Report: file path + line number on any FAIL

### Validation scope — CLI subcommands
- Extract `axiom-push <command>` and `axiom-push <command> <subcommand>` patterns from docs
- Validate against registered subparsers in `mop_sdk/cli.py`
- Subcommands only — do NOT check flag names (too noisy, flags change more frequently)
- Report: file path + line number on any FAIL

### Validation scope — env vars
- Extract env var names (all-caps `[A-Z][A-Z0-9_]{2,}` pattern) from backtick spans in docs
- Validate by searching `puppeteer/`, `puppets/`, and `mop_sdk/` Python source only
- Exclude: venv, node_modules, .git, build dirs (consistent with CLAUDE.md scan guidance)
- Report: file path + line number on any WARN

### CI integration
- Trigger: every push to main + every PR (no path filter — runs unconditionally)
- No `--fix` mode — purely a reporter
- Script installed as a GitHub Actions step: `python tools/validate_docs.py`
- Requires only Python stdlib + the committed docs + source files — no running stack needed for the validator itself

### Claude's Discretion
- Exact regex patterns for route and env var extraction (use conservative patterns to minimize false positives)
- Whether to deduplicate identical references across multiple docs files
- Output format details (colour, table vs line-by-line) — must include file:line for each item
- Whether `generate_openapi.py` accepts a `--url` flag (default `http://localhost:8080`, same as capture_screenshots.py)

</decisions>

<specifics>
## Specific Ideas

- Exit code 2 for empty/stub snapshot is a deliberate choice — distinguishes "docs are broken" (exit 1) from "validator wasn't set up correctly" (exit 2), which is useful for CI diagnostics
- The strict CI gate (WARNs block) reflects the goal of keeping docs perfectly accurate — any env var mentioned in docs must exist in the production codebase at the time of commit

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/capture_screenshots.py`: Companion script pattern — reads secrets.env for credentials, accepts `--url` flag, targets Docker stack. Use same structure for `generate_openapi.py` (credentials not needed for /openapi.json, but URL flag and error handling patterns are reusable).
- `mop_sdk/cli.py`: The source of truth for CLI subcommands. Registered subcommands: `login`, `job push`, `job create`, `key generate`, `init`. Parser structure uses `add_subparsers` — script can import or parse statically.
- `docs/docs/api-reference/openapi.json`: Currently a stub (218 bytes, no paths). Must be populated by `generate_openapi.py` before `validate_docs.py` is useful.

### Established Patterns
- Source scan scope (CLAUDE.md): `puppeteer/`, `puppets/`, `mop_sdk/` — exclude venvs, node_modules, .git, generated/build dirs
- Docker stack URL: `http://localhost:8080` (Caddy proxy front-end)
- Secrets: read from `puppeteer/secrets.env` (though generate_openapi.py may not need auth — /openapi.json is typically unauthenticated)

### Integration Points
- `docs/docs/api-reference/openapi.json`: Written by `generate_openapi.py`, read by `validate_docs.py`
- `.github/workflows/`: Add a new workflow step or job for docs validation
- `tools/`: Both new scripts live here alongside `capture_screenshots.py`

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 86-docs-accuracy-validation*
*Context gathered: 2026-03-29*

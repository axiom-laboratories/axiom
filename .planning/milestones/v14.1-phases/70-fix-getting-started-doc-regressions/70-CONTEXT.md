# Phase 70: Fix Getting-Started Doc Regressions - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Targeted surgery to close two blocking integration gaps (MISS-01, FLOW-01) identified by the v14.1 milestone audit, plus fix three co-located tech debt items (FLOW-02, INCON-01, compose comment stale refs). No new capabilities. Files in scope: `enroll-node.md`, `install.md`, `puppeteer/compose.cold-start.yaml`, `.github/workflows/ci.yml`.

</domain>

<decisions>
## Implementation Decisions

### Token field fix (MISS-01 — DOCS-03)
- `enroll-node.md` CLI tab: replace `d.get('enhanced_token', d.get('join_token', ''))` with `d['token']`
- `puppeteer/compose.cold-start.yaml` line 15 comment: same fix — replace `d['enhanced_token']` with `d['token']`
- Reason: `POST /admin/generate-token` returns `{"token": ...}` — the enhanced_token / join_token fields do not exist and the expression silently returns an empty string

### Cold-Start install steps (FLOW-01 — DOCS-01, DOCS-08)
- `install.md` Step 3: add a **Cold-Start** tab alongside the existing Server Install tab
  - Cold-Start tab command: `docker compose -f compose.cold-start.yaml --env-file .env up -d`
- `install.md` Step 4: add a **Cold-Start** tab alongside the existing Server Install tab
  - Cold-Start verify URL: `https://localhost:8443/` (compose.cold-start.yaml maps port 8443:443)
  - Server Install tab keeps `https://localhost/`
- Tab labels follow Phase 67 convention — use descriptive labels matching Step 2 tab names

### Tech debt: EE feature list (FLOW-02)
- `install.md` EE section: expand the 5-item bullet list to all 9 features shown in the JSON block directly below it
- Add missing: `resource_limits`, `service_principals`, `api_keys`, `executions`
- Keeps prose consistent with the JSON response shown immediately below — currently contradicts itself

### Tech debt: Unnecessary auth on /api/features (INCON-01)
- `install.md` CLI tab for `GET /api/features`: remove the `Authorization: Bearer $TOKEN` header
- The endpoint is unauthenticated; the header adds friction and contradicts `licensing.md`
- Remove the $TOKEN acquisition block from the CLI tab (or simplify to a single curl line without auth)

### compose.cold-start.yaml comment cleanup
- Line 25: update dashboard URL comment from `https://172.17.0.1:8443` to `https://localhost:8443`
- Consistent with the verify URL used in install.md Step 4 Cold-Start tab

### MkDocs strict CI gate
- Add a new `docs` job to `.github/workflows/ci.yml`
- Trigger: every PR and push to main (same as backend/frontend jobs)
- Install: `pip install -r docs/requirements.txt` (uses existing `docs/requirements.txt` with mkdocs-material==9.7.5 and mkdocs-swagger-ui-tag)
- Build command: `mkdocs build --strict` from `docs/` working directory
- Strict mode fails CI on broken anchor links, missing references, and invalid extensions
- No link checker — `--strict` is sufficient to catch the regression class that affected Phase 67

### Claude's Discretion
- Exact tab label names for Step 3/4 (must be consistent with Step 2 tab labels already in place)
- Job name and step names in ci.yml
- Whether to add `--config-file` flag or rely on working-directory

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pymdownx.tabbed: alternate_style: true`: already in `docs/mkdocs.yml` from Phase 67 — tab syntax is confirmed working
- `docs/requirements.txt`: already exists with `mkdocs-material==9.7.5` and `mkdocs-swagger-ui-tag==0.8.0` — CI job uses this directly

### Established Patterns
- Tab syntax (Phase 67 confirmed): `=== "Label"` with 4-space indented content; admonitions inside tabs work when indented 4 spaces
- Tab order: Dashboard first, CLI second (Phase 67 convention)
- ci.yml jobs: `actions/checkout@v4`, `actions/setup-python@v5` with `cache: pip` — match this pattern for docs job

### Integration Points
- `install.md` Step 2 already has tab pair (Server Install / Cold-Start) — Steps 3 and 4 extend this pattern
- `enroll-node.md` Step 1 already has tab pair (Dashboard / CLI) — token field is within the existing CLI tab
- `ci.yml` has `backend`, `frontend-lint`, `frontend-test` jobs — `docs` job is additive, no changes to existing jobs

</code_context>

<specifics>
## Specific Ideas

- The audit fix for MISS-01 is exact: `d['token']` is the correct field (audit confirmed by checking the API response schema)
- The audit fix for FLOW-01 is exact: `docker compose -f compose.cold-start.yaml --env-file .env up -d` for Step 3, `https://localhost:8443/` for Step 4 verify URL
- compose.cold-start.yaml also references `https://172.17.0.1:8001` for API URL comment (line 26) — can update to `https://localhost:8001` for consistency while touching the file

</specifics>

<deferred>
## Deferred Ideas

- FLOW-02 and INCON-01 were originally labeled tech_debt but are included in Phase 70 scope per discussion
- Air-gap install: GHCR Pull tab notes internet access to GitHub is required — dedicated air-gap operations guide is a future milestone item (already called out in install.md)
- CI-01/CI-02 (release pipeline requirements missing from REQUIREMENTS.md) — housekeeping, separate from Phase 70

</deferred>

---

*Phase: 70-fix-getting-started-doc-regressions*
*Context gathered: 2026-03-26*

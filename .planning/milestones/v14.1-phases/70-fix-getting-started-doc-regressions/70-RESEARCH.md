# Phase 70: Fix Getting-Started Doc Regressions - Research

**Researched:** 2026-03-26
**Domain:** MkDocs documentation fixes + GitHub Actions CI gate
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Token field fix (MISS-01 — DOCS-03)**
- `enroll-node.md` CLI tab: replace `d.get('enhanced_token', d.get('join_token', ''))` with `d['token']`
- `puppeteer/compose.cold-start.yaml` line 15 comment: same fix — replace `d['enhanced_token']` with `d['token']`
- Reason: `POST /admin/generate-token` returns `{"token": ...}` — the enhanced_token / join_token fields do not exist and the expression silently returns an empty string

**Cold-Start install steps (FLOW-01 — DOCS-01, DOCS-08)**
- `install.md` Step 3: add a Cold-Start tab alongside the existing Server Install tab
  - Cold-Start tab command: `docker compose -f compose.cold-start.yaml --env-file .env up -d`
- `install.md` Step 4: add a Cold-Start tab alongside the existing Server Install tab
  - Cold-Start verify URL: `https://localhost:8443/` (compose.cold-start.yaml maps port 8443:443)
  - Server Install tab keeps `https://localhost/`
- Tab labels follow Phase 67 convention — use descriptive labels matching Step 2 tab names

**Tech debt: EE feature list (FLOW-02)**
- `install.md` EE section: expand the 5-item bullet list to all 9 features shown in the JSON block directly below it
- Add missing: `resource_limits`, `service_principals`, `api_keys`, `executions`
- Keeps prose consistent with the JSON response shown immediately below — currently contradicts itself

**Tech debt: Unnecessary auth on /api/features (INCON-01)**
- `install.md` CLI tab for `GET /api/features`: remove the `Authorization: Bearer $TOKEN` header
- The endpoint is unauthenticated; the header adds friction and contradicts `licensing.md`
- Remove the $TOKEN acquisition block from the CLI tab (or simplify to a single curl line without auth)

**compose.cold-start.yaml comment cleanup**
- Line 25: update dashboard URL comment from `https://172.17.0.1:8443` to `https://localhost:8443`
- Consistent with the verify URL used in install.md Step 4 Cold-Start tab

**MkDocs strict CI gate**
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

### Deferred Ideas (OUT OF SCOPE)
- FLOW-02 and INCON-01 were originally labeled tech_debt but are included in Phase 70 scope per discussion
- Air-gap install: GHCR Pull tab notes internet access to GitHub is required — dedicated air-gap operations guide is a future milestone item
- CI-01/CI-02 (release pipeline requirements missing from REQUIREMENTS.md) — housekeeping, separate from Phase 70
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | `install.md` has explicit admin password setup step (create `.env` with `ADMIN_PASSWORD=<value>`) before the `docker compose up` instruction | Step 2 Cold-Start tab already covers ADMIN_PASSWORD. Gap: Steps 3–4 lack Cold-Start tab variants that reference `--env-file .env` — the password setup is there but the up command doesn't load it. Adding Cold-Start tabs to Steps 3–4 closes this. |
| DOCS-03 | `enroll-node.md` has a CLI (curl) JOIN_TOKEN generation path as a primary alternative to the dashboard GUI step | The CLI path exists but extracts wrong field `d.get('enhanced_token', ...)` — API returns `{"token": ...}`. Single line fix to `d['token']` restores the path. Verified against `main.py` line 1544: `return {"token": b64_token}`. |
| DOCS-08 | `install.md` documents a pre-built compose / tarball install alternative for users without GitHub access | GHCR Pull tab in Step 1 covers this, but Steps 3–4 have no cold-start variants — user who followed GHCR Pull path hits `puppeteer/compose.server.yaml` which doesn't exist in their directory. Adding Cold-Start tabs to Steps 3–4 closes this. |
</phase_requirements>

---

## Summary

Phase 70 is a targeted documentation surgery with no code changes. It closes two blocking integration gaps (MISS-01 and FLOW-01) found by the v14.1 milestone audit, plus two co-located tech debt items (FLOW-02 and INCON-01) that were identified in the same pass.

The work falls across four files: `docs/docs/getting-started/enroll-node.md`, `docs/docs/getting-started/install.md`, `puppeteer/compose.cold-start.yaml`, and `.github/workflows/ci.yml`. Every change is a one- to three-line surgical edit except the install.md Step 3/4 tab pairs, which require adding a new tab block following the established Phase 67 pattern.

All changes are confirmed against the live source. The API endpoint response shape was verified in `main.py` line 1544 (`return {"token": b64_token}`). The tab syntax, mkdocs.yml extensions, and Step 2 tab labels are confirmed in the repository. The CI job pattern is confirmed from existing `backend`, `frontend-lint`, and `frontend-test` jobs.

**Primary recommendation:** One plan covering all six targeted edits in a single wave. No sub-dependencies between the changes — all are independent line-level fixes.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.7.5 | Documentation site framework | Already in `docs/requirements.txt` — locked version |
| mkdocs-swagger-ui-tag | 0.8.0 | Swagger UI embed in docs | Already in `docs/requirements.txt` — locked version |
| pymdownx.tabbed | bundled with material | Tab pairs in markdown | Already enabled in `mkdocs.yml` with `alternate_style: true` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| actions/checkout | v4 | CI checkout | All jobs in ci.yml use this version — match it |
| actions/setup-python | v5 | CI Python setup | Existing jobs use v5 with `cache: pip` — match it |

**Installation:** No new installs required. `docs/requirements.txt` already contains all needed packages.

---

## Architecture Patterns

### Tab Pair Pattern (Phase 67 confirmed working)

The tab syntax is confirmed working in this repository. From `mkdocs.yml`:
```yaml
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
```

Tab syntax in markdown:
```markdown
=== "Server Install"

    content indented 4 spaces

=== "Cold-Start"

    content indented 4 spaces
```

Admonitions inside tabs work when indented 4 spaces inside the tab block.

**Tab label convention from Step 2 (already in install.md):**
- Server Install tab: `=== "Server Install"`
- Cold-Start tab: `=== "Cold-Start Install"`

Step 3 and Step 4 tabs MUST use these same labels so the user experience is consistent.

### CI Job Pattern (from existing jobs in ci.yml)

All existing jobs follow this shape:
```yaml
  <job-name>:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python <version>
        uses: actions/setup-python@v5
        with:
          python-version: "<version>"
          cache: pip

      - name: Install dependencies
        working-directory: <dir>
        run: pip install -r <path>

      - name: <build/test step>
        working-directory: <dir>
        run: <command>
```

The `docs` job must match this pattern. The `working-directory: docs` approach is cleaner than `--config-file docs/mkdocs.yml` for the mkdocs build command.

### compose.cold-start.yaml Comment Block

The file header comment (lines 8–26) serves as the quick-start guide embedded in the compose file. Two specific lines need updating:

- Line 15 (currently): `print(d['enhanced_token'])` → must be `print(d['token'])`
- Line 25 (currently): `https://172.17.0.1:8443` → must be `https://localhost:8443`
- Line 26 (currently): `https://172.17.0.1:8001` → may update to `https://localhost:8001` (CONTEXT.md lists this as discretionary cleanup while touching the file)

### Anti-Patterns to Avoid

- **Do not rename headings in install.md or enroll-node.md** — heading renames silently break anchor links. Phase 67 pitfall note: always `mkdocs build --strict` after any heading change. The changes in this phase add tab blocks and edit bullet lists, not headings — safe.
- **Do not add `--strict` to the build step without installing requirements first** — strict mode requires the full plugin stack (swagger-ui-tag, privacy, offline). All are in `docs/requirements.txt`.
- **Do not use `mkdocs serve` in CI** — use `mkdocs build --strict`. Build is the correct gate for CI.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab UI in docs | Custom HTML includes | `pymdownx.tabbed` | Already enabled in mkdocs.yml; confirmed working in Phase 67 |
| CI broken-link detection | Custom link-checker script | `mkdocs build --strict` | Strict mode catches broken anchors, missing references, and invalid extensions in the same pass as the build |
| Python version in CI | Requirements pin in ci.yml | `docs/requirements.txt` | Single source of truth for deps; `cache: pip` works with requirements files |

---

## Common Pitfalls

### Pitfall 1: Wrong tab label breaks tab grouping
**What goes wrong:** Tab labels in Step 3/4 don't match Step 2. MkDocs tab grouping is label-string-sensitive — `"Cold-Start"` and `"Cold-Start Install"` are different groups. Browser does not sync tab selection across steps.
**Why it happens:** Inconsistent naming between authors or sessions.
**How to avoid:** Step 2 uses `"Server Install"` and `"Cold-Start Install"`. Steps 3 and 4 must use exactly the same strings.
**Warning signs:** Check Step 2 tab labels in install.md before writing Steps 3/4. Current Step 2 labels from the file: `=== "Server Install"` and `=== "Cold-Start Install"`.

### Pitfall 2: mkdocs build --strict fails on privacy/offline plugin
**What goes wrong:** The `privacy` and `offline` plugins download external assets. In a CI environment without internet access or with cache disabled, strict mode may fail on asset fetch rather than doc quality.
**Why it happens:** `mkdocs.yml` has `- privacy` and `- offline` in plugins. These can trigger network requests.
**How to avoid:** Test `mkdocs build --strict` in the CI environment. If privacy/offline plugins cause CI failures, the docs job may need `--config-file` pointing to a CI-specific config, or the plugins may need to be conditional. However, since the repo CI has internet access (GitHub Actions default runners), this is low risk.
**Warning signs:** CI logs showing "downloading" or network timeout errors in the docs job, not anchor/extension errors.

### Pitfall 3: Indentation errors in tab content break the entire page
**What goes wrong:** Content inside a tab block that is not exactly 4-space indented renders outside the tab or fails to parse.
**Why it happens:** Mixed indentation (tabs vs spaces) or missing blank line after `=== "Label"`.
**How to avoid:** Follow the exact Phase 67 confirmed pattern: blank line after `=== "Label"`, all content at 4-space indent, admonitions at 4-space indent (8 total with their own content).

### Pitfall 4: Silent empty string in token extraction
**What goes wrong:** `d.get('enhanced_token', d.get('join_token', ''))` returns `''` when neither key exists. No exception is raised, no visible error — the node just silently fails to enroll.
**Why it happens:** The API was refactored to return `{"token": ...}` but the docs were not updated.
**How to avoid:** Use `d['token']` (KeyError on wrong field, not silent empty string). This is the exact fix specified in CONTEXT.md.

---

## Code Examples

### Confirmed API response shape (main.py line 1544)
```python
# Source: puppeteer/agent_service/main.py — POST /admin/generate-token
payload = {
    "t": token_str,
    "ca": ca_pem
}
b64_token = base64.b64encode(json.dumps(payload).encode()).decode()
return {"token": b64_token}
```
The response key is `token`. Not `enhanced_token`, not `join_token`.

### Correct CLI token extraction for enroll-node.md
```bash
# Replace the broken line 40 in enroll-node.md with:
curl -sk -X POST https://<your-orchestrator>:8001/admin/generate-token \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['token'])"
```

### Step 3 Cold-Start tab (new content for install.md)
```markdown
=== "Cold-Start Install"

    ```bash
    docker compose -f compose.cold-start.yaml --env-file .env up -d
    ```

    This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001),
    and PostgreSQL. The two built-in puppet nodes start automatically but require
    JOIN_TOKEN_1 and JOIN_TOKEN_2 to be set in your `.env` before enrolling.
```

### Step 4 Cold-Start tab (new content for install.md)
```markdown
=== "Cold-Start Install"

    Check that all containers are running:

    ```bash
    docker compose -f compose.cold-start.yaml ps
    ```

    Then open `https://localhost:8443/` in a browser — you should see the dashboard
    login page.
```

### docs CI job (new addition to ci.yml)
```yaml
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install docs dependencies
        working-directory: docs
        run: pip install -r requirements.txt

      - name: Build docs (strict)
        working-directory: docs
        run: mkdocs build --strict
```

### compose.cold-start.yaml comment fix
```yaml
# Line 15 — change:
#   print(d['enhanced_token'])
# to:
#   print(d['token'])

# Line 25 — change:
# Dashboard is reachable at: https://172.17.0.1:8443
# to:
# Dashboard is reachable at: https://localhost:8443

# Line 26 — change:
# API is reachable at:       https://172.17.0.1:8001
# to:
# API is reachable at:       https://localhost:8001
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `d.get('enhanced_token', d.get('join_token', ''))` | `d['token']` | API changed before Phase 67 | Docs never updated; CLI path silently broken |
| Steps 3–4 server-only (no cold-start variant) | Steps 3–4 with Cold-Start tab pair | Phase 67 added Steps 1–2 tabs but not 3–4 | Cold-Start users hit wrong compose path |
| 5-item EE feature bullet list | 9-item list matching /api/features JSON | JSON block was updated but prose was not | Prose contradicts JSON on same page |
| `GET /api/features` with Bearer auth | `GET /api/features` without auth | Endpoint is and always was unauthenticated | Unnecessary friction, contradicts licensing.md |

---

## Open Questions

1. **Tab label consistency — Step 2 exact strings**
   - What we know: Step 2 has `=== "Server Install"` and `=== "Cold-Start Install"` (confirmed by reading install.md)
   - What's unclear: None — the labels are readable directly from the file
   - Recommendation: Use `"Server Install"` and `"Cold-Start Install"` verbatim for Steps 3/4

2. **compose.cold-start.yaml line 26 (API URL comment)**
   - What we know: CONTEXT.md says "can update to https://localhost:8001 for consistency while touching the file"
   - What's unclear: Whether the planner should include this as an explicit task step
   - Recommendation: Include it — the change is one word swap and the CONTEXT.md explicitly calls it out as in-scope

3. **privacy/offline plugin CI behaviour**
   - What we know: Both plugins are in mkdocs.yml; GitHub Actions runners have internet access
   - What's unclear: Whether asset downloading causes non-zero CI times or occasional flakiness
   - Recommendation: Proceed with standard `mkdocs build --strict`. If it fails on plugin network issues, that is a separate concern to address only if CI fails.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | mkdocs build --strict (docs); pytest (backend); vitest (frontend) |
| Config file | docs/mkdocs.yml |
| Quick run command | `cd docs && mkdocs build --strict` |
| Full suite command | `cd docs && mkdocs build --strict` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | install.md Step 3 Cold-Start tab contains `--env-file .env` | manual-only (doc inspection) | `grep -n 'env-file' docs/docs/getting-started/install.md` | ✅ |
| DOCS-03 | enroll-node.md CLI tab extracts `d['token']` | manual-only (doc inspection) | `grep -n "d\['token'\]" docs/docs/getting-started/enroll-node.md` | ✅ |
| DOCS-08 | install.md Step 3 Cold-Start tab present; Step 4 uses port 8443 | manual-only (doc inspection) | `grep -n '8443' docs/docs/getting-started/install.md` | ✅ |
| (All) | Docs build without errors or broken anchors | smoke | `cd docs && mkdocs build --strict` | ✅ |

**Note:** Documentation content correctness is inherently manual-review territory. `mkdocs build --strict` is the automated gate — it catches broken anchors, missing referenced files, and malformed markdown extensions, but does not verify prose content. Post-edit grep commands above serve as quick sanity checks.

### Sampling Rate
- **Per task commit:** `cd docs && mkdocs build --strict`
- **Per wave merge:** `cd docs && mkdocs build --strict`
- **Phase gate:** Full docs build green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing docs infrastructure covers all phase requirements. `docs/requirements.txt` and `docs/mkdocs.yml` exist. No new test files needed.

---

## Sources

### Primary (HIGH confidence)
- `puppeteer/agent_service/main.py` line 1544 — API response shape confirmed: `return {"token": b64_token}`
- `docs/docs/getting-started/install.md` — current file state read directly; Step 2 tab labels confirmed
- `docs/docs/getting-started/enroll-node.md` — current file state read directly; broken token extraction at line 40 confirmed
- `puppeteer/compose.cold-start.yaml` — current file state read directly; stale field name at line 15, stale IP at lines 25–26 confirmed
- `.github/workflows/ci.yml` — current file state read directly; existing job patterns confirmed
- `docs/mkdocs.yml` — tab extension config confirmed: `pymdownx.tabbed: alternate_style: true`
- `docs/requirements.txt` — package versions confirmed: mkdocs-material==9.7.5, mkdocs-swagger-ui-tag==0.8.0
- `.planning/v14.1-MILESTONE-AUDIT.md` — gap descriptions MISS-01 and FLOW-01 read directly

### Secondary (MEDIUM confidence)
- `.planning/phases/70-fix-getting-started-doc-regressions/70-CONTEXT.md` — all implementation decisions and exact fix specifications

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all package versions and config confirmed from actual files
- Architecture: HIGH — tab syntax and CI pattern confirmed from live repo files
- Pitfalls: HIGH — MISS-01/FLOW-01 bugs confirmed from direct file inspection and API source
- Fix specifications: HIGH — every change confirmed against source files and API implementation

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (stable docs toolchain; changes only if mkdocs-material or ci.yml jobs change)

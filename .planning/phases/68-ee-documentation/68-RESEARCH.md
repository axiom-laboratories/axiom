# Phase 68: EE Documentation - Research

**Researched:** 2026-03-26
**Domain:** MkDocs documentation — content edits to `install.md` and `licensing.md`
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Expand the existing "Enterprise Edition" section in `install.md` — no standalone `ee-install.md`
- The section stays at the end of `install.md`, after Step 4 (verify stack is up)
- **Key setting**: keep existing `AXIOM_LICENCE_KEY` env var block
- **Feature list**: add a list of EE feature flags as they appear in the API response: `foundry`, `rbac`, `webhooks`, `triggers`, `audit`
- **Verification step**: add a tab pair (Dashboard / CLI) showing how to confirm EE is active
  - **Dashboard tab**: point to the CE/EE badge in the sidebar — it flips to EE when the key is valid
  - **CLI tab**: full self-contained block — inline token acquisition (`TOKEN=$(curl login...)`) then `curl /api/features` with the token
- **Expected output**: show the full JSON response with all keys `true` so operators know exactly what success looks like
- Use `GET /api/features` exclusively — never `GET /api/admin/features`
- Add `GET /api/features` example to the existing "Checking your licence" section in `licensing.md`, alongside `GET /api/licence`
- Show the full response: `{"foundry": true, "rbac": true, "webhooks": true, "triggers": true, "audit": true}`
- `AXIOM_LICENCE_KEY` naming already correct throughout — no renames needed (EEDOC-02 already satisfied)

### Claude's Discretion
- Exact curl command formatting and flag choices
- Tab ordering within the verification step (Dashboard first per Phase 67 convention)
- Whether to add a "failure" example (key missing or expired) to the CLI tab

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EEDOC-01 | `ee-install.md` (or equivalent EE getting-started page) replaces all `/api/admin/features` references with the correct `/api/features` endpoint | The correct endpoint is confirmed as `GET /api/features` in `main.py` line 756. No existing docs source files (under `docs/docs/`) contain `/api/admin/features` — only historical planning files do. Phase scope is to author the EE verification section using the correct endpoint from the start, preventing this error from ever appearing in the live docs. |
| EEDOC-02 | `licensing.md` uses consistent `AXIOM_LICENCE_KEY` naming throughout (no `AXIOM_EE_LICENCE_KEY` infix) | `licensing.md` already uses `AXIOM_LICENCE_KEY` consistently (3 occurrences verified). Requirement is satisfied by the existing file; this phase protects that state and adds the `/api/features` example without introducing the wrong variant. |
</phase_requirements>

---

## Summary

Phase 68 is a pure content-editing phase — two markdown files receive targeted additions, no new pages, no nav changes, no MkDocs config changes. The phase is motivated by a historical stale reference (`/api/admin/features`) that appeared in internal scenario planning files during Phase 64 and was pre-patched at the time. The fix here makes the live getting-started docs authoritative by building the EE verification section around the correct endpoint from the start.

`install.md` already has an "Enterprise Edition" section (lines 116-128) that is minimal: it shows the env var and links to `licensing.md`. The task is to expand that section with a feature flag list and a Dashboard/CLI tab pair for verification. `licensing.md` has a "Checking your licence" section that only covers `GET /api/licence`; appending a `GET /api/features` example below it closes the gap.

Both files use no incorrect env var naming — `AXIOM_LICENCE_KEY` is consistent throughout. EEDOC-02 is satisfied by protecting the existing correct naming while adding the features example.

**Primary recommendation:** Edit `install.md` Enterprise Edition section (expand in place) and append to `licensing.md` "Checking your licence" section. No nav or config changes needed.

---

## Standard Stack

### Core

| File | Current State | Change Required |
|------|--------------|-----------------|
| `docs/docs/getting-started/install.md` | EE section at lines 116-128: env var + link only | Expand: add feature flag list + Dashboard/CLI tab pair for verification |
| `docs/docs/licensing.md` | "Checking your licence" covers only `GET /api/licence` | Append `GET /api/features` block with full JSON example |

### Supporting Infrastructure (already in place, no changes needed)

| Component | Status | Notes |
|-----------|--------|-------|
| `pymdownx.tabbed: alternate_style: true` | Confirmed in `mkdocs.yml` line 28-29 | Tab pairs work — Phase 67 validated this |
| `admonition` extension | Confirmed in `mkdocs.yml` line 22 | `!!! note`, `!!! tip` etc. work |
| `pymdownx.details` extension | Confirmed in `mkdocs.yml` line 24 | `??? example` collapsible blocks work |
| Dashboard-first tab convention | Established in Phase 67 | `=== "Dashboard"` before `=== "CLI"` |

### Correct API Endpoint (HIGH confidence)

`GET /api/features` is the sole correct endpoint. Confirmed in `puppeteer/agent_service/main.py` line 756:

```python
@app.get("/api/features", tags=["System"])
async def get_features(request: Request):
```

This endpoint is **unauthenticated** — no `Depends(require_auth)` or `Depends(require_permission(...))` in the signature. The curl CLI tab does not need an auth token just to call `/api/features`. However, the Context decision specifies an inline token acquisition block for the CLI tab (consistent with the enroll-node.md pattern of self-contained CLI blocks), so include the `TOKEN=` line regardless for uniformity and completeness.

Full EE response shape (from `main.py` lines 764-774):

```json
{
  "audit": true,
  "foundry": true,
  "webhooks": true,
  "triggers": true,
  "rbac": true,
  "resource_limits": true,
  "service_principals": true,
  "api_keys": true,
  "executions": true
}
```

The CONTEXT.md shows a shorter list (`foundry`, `rbac`, `webhooks`, `triggers`, `audit`). The actual API returns 9 keys. The decision is to show the 5 EE-prominent features in the "feature list" prose, but the "expected output" JSON block should reflect the full 9-key response for accuracy.

---

## Architecture Patterns

### Pattern 1: Tab Pair (Dashboard / CLI)

Established by Phase 67 in `enroll-node.md` and `first-job.md`. Dashboard tab first, CLI tab second.

```markdown
=== "Dashboard"

    [4-space indented content]

=== "CLI"

    [4-space indented content]
```

Admonitions inside tabs must also be indented 4 spaces (confirmed working in Phase 67).

### Pattern 2: Self-Contained CLI Block with Inline Token Acquisition

Established in `enroll-node.md` CLI tab (lines 27-43). The token acquisition and main command are separate code blocks within the same tab section:

```markdown
=== "CLI"

    Log in to get a JWT:

    ```bash
    TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -d 'username=admin&password=<your-password>' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    ```

    Then [do the thing]:

    ```bash
    curl -sk https://<your-orchestrator>:8001/api/features \
      -H "Authorization: Bearer $TOKEN"
    ```
```

Note: `-sk` flags are standard across all curl examples in these docs (`-s` silent, `-k` skip TLS verify for self-signed CA). Keep consistent.

### Pattern 3: Appending to an Existing Section in licensing.md

`licensing.md` "Checking your licence" section ends at line 71 (`The dashboard sidebar also shows a **CE** or **EE** badge...`). The append goes after line 69 (the closing `}` of the CE mode JSON) and before the sidebar badge note, or after the sidebar badge note. Given the section flows from `GET /api/licence` → `GET /api/features` → sidebar badge, append the `GET /api/features` block between the `GET /api/licence` example and the sidebar badge sentence, or after the badge sentence. Either reads naturally; after the badge sentence is simpler (no restructuring needed).

### Anti-Patterns to Avoid

- **`/api/admin/features`**: This path does not exist. Never use it. The historical confusion came from early planning docs — it was never in any deployed code.
- **`AXIOM_EE_LICENCE_KEY`**: Wrong env var name. The correct name is `AXIOM_LICENCE_KEY` throughout.
- **Omitting the full JSON response**: CONTEXT requires showing the full response with all keys `true` so operators see exactly what success looks like. Do not abbreviate with `// ...`.
- **Requiring auth for `/api/features` in documentation**: The endpoint is unauthenticated in the code. Documenting it as "requires a token" would be inaccurate (though including the token in the CLI block for pattern consistency is fine — it still works with a token).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab pairs | Custom HTML | `pymdownx.tabbed` `=== "Label"` syntax | Already configured in mkdocs.yml, validated in Phase 67 |
| Collapsible sections | Custom HTML | `pymdownx.details` `??? example` syntax | Already configured and used in first-job.md |
| Callout boxes | Div/class HTML | `!!! note`/`!!! tip`/`!!! danger` admonition syntax | Already configured in mkdocs.yml |

---

## Common Pitfalls

### Pitfall 1: Wrong Feature Key Names in Prose

**What goes wrong:** Writing `audit-log`, `role-based-access`, or other human-readable variants instead of the exact API key names.
**Why it happens:** Natural language drift from API key names.
**How to avoid:** Copy feature flag names exactly from the `main.py` response dict: `foundry`, `rbac`, `webhooks`, `triggers`, `audit` (and the full set: `resource_limits`, `service_principals`, `api_keys`, `executions`).
**Warning signs:** Any feature name containing a hyphen or capital letter in a code block.

### Pitfall 2: Tab Content Not Indented 4 Spaces

**What goes wrong:** MkDocs renders tab content as regular paragraph text instead of inside the tab widget.
**Why it happens:** `pymdownx.tabbed` requires exactly 4-space indentation for all content inside a tab.
**How to avoid:** Verify with `mkdocs build --strict` after editing. Every line inside a tab — including blank lines separating blocks — should be blank or 4-space indented.
**Warning signs:** `mkdocs build --strict` emits a warning about unexpected content after a tab marker.

### Pitfall 3: Introducing `/api/admin/features` When Copying from Old Planning Docs

**What goes wrong:** Developer reads Phase 64 or ROADMAP planning files for context and copies the stale `/api/admin/features` path into the new docs.
**Why it happens:** The planning history is full of references to the wrong path.
**How to avoid:** The only authoritative source is `main.py`. The route is `GET /api/features`. This is the sole endpoint to use.

### Pitfall 4: Showing Incomplete JSON Response

**What goes wrong:** Planner writes `{"foundry": true, "rbac": true, ...}` with an ellipsis, omitting the full 9-key response.
**Why it happens:** CONTEXT.md lists only 5 keys; the actual API returns 9.
**How to avoid:** Show the complete response for both install.md and licensing.md. The complete response is:
```json
{
  "audit": true,
  "foundry": true,
  "webhooks": true,
  "triggers": true,
  "rbac": true,
  "resource_limits": true,
  "service_principals": true,
  "api_keys": true,
  "executions": true
}
```

### Pitfall 5: MkDocs --strict Breaks on Anchor References

**What goes wrong:** Renaming or restructuring headings silently breaks anchor links from other pages.
**Why it happens:** MkDocs `--strict` mode fails on broken cross-references.
**How to avoid:** Neither file has its headings renamed — only content is appended/expanded. No existing anchor cross-references are affected. Verify with `mkdocs build --strict` as a final check.

---

## Code Examples

### install.md — EE Section Expansion Target

Current state (lines 116-128):

```markdown
## Enterprise Edition

To enable EE features, add your licence key to `secrets.env`:

```bash
AXIOM_LICENCE_KEY=<your-licence-key>
```

The stack reads this at startup — no plugin install required. See [Licensing →](../licensing.md) for validation behaviour, expiry handling, and how to check your licence status.
```

Target expansion: after the existing env var block and before the closing link, add:

1. Prose listing EE features enabled by a valid key
2. A tab pair (Dashboard / CLI) for verifying EE is active

### licensing.md — "Checking your licence" Section Append Target

Current state ends at line 71:

```markdown
The dashboard sidebar also shows a **CE** or **EE** badge for at-a-glance visibility.
```

Target: append a `GET /api/features` subsection after the existing content, showing the endpoint and full success JSON.

### CLI Tab Curl Pattern (from enroll-node.md lines 29-32)

```bash
TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<your-password>' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Then features check:

```bash
curl -sk https://<your-orchestrator>:8001/api/features \
  -H "Authorization: Bearer $TOKEN"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `GET /api/admin/features` (stale, in old planning docs only) | `GET /api/features` (confirmed in main.py) | Any doc using the old path fails at runtime with 404 |
| `AXIOM_EE_LICENCE_KEY` (never in live code) | `AXIOM_LICENCE_KEY` | Correct name already used throughout all live docs |
| Separate `ee-install.md` page (Phase 64 scenario) | EE section within `install.md` (Phase 68 decision) | Eliminates a drift surface; EE content stays co-located with CE install steps |

---

## Open Questions

1. **Full 9-key vs. 5-key feature list in prose**
   - What we know: CONTEXT specifies 5 features in prose (`foundry`, `rbac`, `webhooks`, `triggers`, `audit`); API returns 9 keys
   - What's unclear: Whether to mention `resource_limits`, `service_principals`, `api_keys`, `executions` in the prose list or only in the JSON example
   - Recommendation: List the 5 EE-prominent features in prose as specified by CONTEXT; show the full 9-key JSON in the code block for accuracy. This is within Claude's Discretion.

2. **Failure example in CLI tab**
   - What we know: CONTEXT marks this as Claude's Discretion
   - Recommendation: Include a brief failure example — when the key is missing or expired all values return `false`. A single `!!! note` admonition after the success JSON is sufficient. Keeps the tab self-contained without adding significant length.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | MkDocs `mkdocs build --strict` (docs build validation) |
| Config file | `docs/mkdocs.yml` |
| Quick run command | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -20` |
| Full suite command | Same — docs build is the full test |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EEDOC-01 | No `/api/admin/features` in docs source | grep smoke | `grep -r "api/admin/features" docs/docs/ && echo FAIL || echo PASS` | ✅ |
| EEDOC-01 | `/api/features` present in install.md EE section | grep smoke | `grep "api/features" docs/docs/getting-started/install.md` | ✅ (after edit) |
| EEDOC-01 | `mkdocs build --strict` succeeds | build | `cd docs && mkdocs build --strict` | ✅ |
| EEDOC-02 | No `AXIOM_EE_LICENCE_KEY` anywhere in docs source | grep smoke | `grep -r "AXIOM_EE_LICENCE_KEY" docs/docs/ && echo FAIL || echo PASS` | ✅ |
| EEDOC-02 | `AXIOM_LICENCE_KEY` present in licensing.md | grep smoke | `grep "AXIOM_LICENCE_KEY" docs/docs/licensing.md` | ✅ |

### Sampling Rate

- **Per task commit:** `grep -r "api/admin/features" docs/docs/ && echo FAIL || echo PASS`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Phase gate:** Full `mkdocs build --strict` green before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure (grep + mkdocs build) covers all phase requirements. No new test files needed.

---

## Sources

### Primary (HIGH confidence)

- `puppeteer/agent_service/main.py` line 756 — `GET /api/features` route definition confirmed, unauthenticated, returns 9-key dict
- `docs/docs/getting-started/install.md` — current EE section content (lines 116-128), confirmed `AXIOM_LICENCE_KEY` correct
- `docs/docs/licensing.md` — confirmed `AXIOM_LICENCE_KEY` correct throughout (3 occurrences), "Checking your licence" section confirmed
- `docs/mkdocs.yml` — confirmed `pymdownx.tabbed: alternate_style: true` present (line 28-29)
- `docs/docs/getting-started/enroll-node.md` — curl pattern for self-contained CLI tab with inline token acquisition (lines 27-43)

### Secondary (MEDIUM confidence)

- `.planning/milestones/v14.0-phases/64-ee-cold-start-run/64-VERIFICATION.md` — historical confirmation that `/api/admin/features` was pre-existing stale reference, `/api/features` was always the correct path
- `.planning/phases/68-ee-documentation/68-CONTEXT.md` — locked decisions and implementation specifics from discuss-phase session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both target files read directly, current content confirmed
- Architecture: HIGH — tab/admonition patterns confirmed from Phase 67 artifacts and mkdocs.yml
- Pitfalls: HIGH — `/api/admin/features` confusion well-documented in planning history; tab indentation verified against live docs

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (stable docs infrastructure; no fast-moving dependencies)

# Phase 67: Getting-Started Documentation - Research

**Researched:** 2026-03-26
**Domain:** MkDocs Material documentation surgery (pymdownx.tabbed, admonitions, getting-started guides)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Sub-order locked: `mkdocs.yml` first, then `install.md` → `enroll-node.md` → `first-job.md`
- Tab extension: `pymdownx.tabbed: alternate_style: true` added to `mkdocs.yml` first, before touching any guide
- Tab labels: **Dashboard** / **CLI** throughout (not UI/API or Browser/Terminal)
- Tab order: **Dashboard first** in every tab pair
- Four steps get CLI/Dashboard tab pairs:
  1. `install.md` Step 1 — Git Clone vs GHCR Pull
  2. `install.md` Step 2 — Server install (secrets.env) vs Cold-start install (.env)
  3. `enroll-node.md` Step 1 — Dashboard token generation vs CLI curl path
  4. `enroll-node.md` Step 3 — Option A (curl installer) vs Option B (Docker Compose) become tabs
  5. `first-job.md` Step 4 — Dashboard form vs CLI dispatch (axiom-push + raw curl)
- Offline install path (DOCS-08): No tarball — GHCR Pull tab uses `curl` of raw `compose.cold-start.yaml` + `docker compose pull` + `docker compose up -d`. GHCR image: `ghcr.io/axiom-laboratories/axiom`
- `install.md` password setup (DOCS-01): Step 2 tab pair — Server tab (secrets.env with all four vars) vs Cold-start tab (`.env` with `ADMIN_PASSWORD` and `ENCRYPTION_KEY` only)
- AGENT_URL table (DOCS-06): Reorganise by install method (not OS); remove `172.17.0.1` as primary; keep as fallback note; add `https://agent:8001` for cold-start compose scenario
- `enroll-node.md` CLI token path (DOCS-03): Step 1 becomes a full tab pair; CLI tab is a primary path, not a secondary callout
- `enroll-node.md` EXECUTION_MODE (DOCS-05): Replace any `EXECUTION_MODE=direct` references with `EXECUTION_MODE=docker`
- `first-job.md` CLI dispatch (DOCS-10): Step 4 tab pair — Dashboard tab (existing form) vs CLI tab with `axiom-push job push` as hero command; collapsible `??? example "Raw API"` block inside CLI tab for curl
- `first-job.md` key registration callout (DOCS-11): `!!! danger "Register your signing key first"` immediately before Step 4; references Steps 1–2 as prerequisites; matches existing tone

### Claude's Discretion

- Exact wording of tab content (match existing doc tone — direct, imperative)
- Whether to split enroll-node.md AGENT_URL step as its own tab pair or keep as a table with the new structure
- Exact anchor names after any heading changes (run `mkdocs build --strict` after each file)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | `install.md` has explicit admin password setup step before `docker compose up` | Cold-start tab pattern confirmed; `compose.cold-start.yaml` documents the `.env` requirement |
| DOCS-02 | `mkdocs.yml` has `pymdownx.tabbed: alternate_style: true` | Extension syntax verified against MkDocs Material 9.x official docs |
| DOCS-03 | `enroll-node.md` has a CLI JOIN_TOKEN generation path as a primary alternative | Existing CLI callout content already written — promote to full tab |
| DOCS-04 | `enroll-node.md` Option B compose snippet uses correct Axiom node image | Verified: current snippet already uses `localhost/master-of-puppets-node:latest` — DOCS-04 is already satisfied; confirm on read and do not regress |
| DOCS-05 | `enroll-node.md` replaces all `EXECUTION_MODE=direct` with `EXECUTION_MODE=docker` | Verified: current enroll-node.md already uses `EXECUTION_MODE=docker` — confirm no regressions |
| DOCS-06 | `enroll-node.md` AGENT_URL guidance corrected | Current table has `172.17.0.1:8001` as primary Linux entry; cold-start compose uses `https://agent:8001`; table must be restructured |
| DOCS-07 | `enroll-node.md` Option B has Docker socket volume mount note | Already present in current file as a `!!! tip` block; preserve and promote |
| DOCS-08 | `install.md` documents a no-git install path | GHCR pull tab using `curl` + `docker compose pull` is the solution |
| DOCS-09 | `first-job.md` has Ed25519 signing key setup as numbered prerequisites before dispatch step | Steps 1–2 already cover keypair generation and registration; need to add a numbered prerequisite callout before Step 4 |
| DOCS-10 | `first-job.md` has a CLI/API dispatch path | `axiom-push job push` hero command + collapsible raw curl; note: axiom-push is EE-gated per the feature guide |
| DOCS-11 | `first-job.md` has a pre-dispatch key registration callout | `!!! danger` block before Step 4 referencing Steps 1–2 |
</phase_requirements>

---

## Summary

Phase 67 is targeted surgery on four files: `mkdocs.yml`, `install.md`, `enroll-node.md`, and `first-job.md`. The sub-order is locked by dependency — `pymdownx.tabbed` must land in `mkdocs.yml` before any `=== "Tab"` syntax in the guide files, otherwise `mkdocs build --strict` fails with unrecognised syntax.

All three guide files already have solid structural foundations. The edits add tab pairs to existing steps (no steps are removed or reordered), fix one outdated table (AGENT_URL), and add two new content blocks (GHCR pull tab, pre-dispatch danger callout). The most complex change is the `install.md` Step 1 tab pair introducing the GHCR pull path, since it requires new content rather than restructuring existing content.

Two requirements (DOCS-04 and DOCS-05) are already satisfied in the current `enroll-node.md` — the planner must verify on read and avoid regressions rather than write new content.

**Primary recommendation:** Work file-by-file in locked order. After each file edit, run `mkdocs build --strict` from `docs/` (or equivalent inside the Docker stack build) to catch broken anchors before moving to the next file.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.7.5 (pinned in `docs/requirements.txt`) | MkDocs theme providing tab, admonition, details extensions | Already the project's doc theme |
| pymdownx.tabbed | bundled with pymdown-extensions 10.21 | Renders `=== "Tab"` tab pairs in markdown | Official Material extension for content tabs |
| pymdownx.details | already in `mkdocs.yml` | Renders `??? example` collapsible blocks | Required for the `??? example "Raw API"` block in first-job.md |
| pymdownx.superfences | already in `mkdocs.yml` | Allows code blocks inside tabs and details | Required for fenced code blocks inside `=== "Tab"` content |

### Extension Configuration
The final `mkdocs.yml` `markdown_extensions` block must include both `pymdownx.tabbed` and `pymdownx.superfences` — they work together. SuperFences is already present; only tabbed needs adding.

**Installation:** No new packages needed — pymdownx.tabbed ships with pymdown-extensions, which is already a transitive dependency of mkdocs-material.

---

## Architecture Patterns

### Recommended Edit Order
```
1. mkdocs.yml            — add pymdownx.tabbed (1-line change)
2. install.md            — add Step 1 tab pair + Step 2 tab pair + EE section
3. enroll-node.md        — restructure Step 1 as tab pair + fix AGENT_URL table + restructure Step 3 as tab pair
4. first-job.md          — add danger callout before Step 4 + add Step 4 tab pair
```

### Pattern 1: Tab Pair in a Numbered Step
**What:** Replace a single code block or sub-heading with a `=== "Dashboard"` / `=== "CLI"` tab pair. Content of each tab is indented 4 spaces under the `=== "Label"` line.
**When to use:** Every step with a Dashboard and CLI path.
**Example:**
```markdown
=== "Dashboard"

    1. In the dashboard, go to **Nodes**
    2. Click **Generate Token**
    3. Click **Copy JOIN_TOKEN**

=== "CLI"

    ```bash
    TOKEN=$(curl -sk -X POST https://<host>:8001/auth/login \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -d 'username=admin&password=<password>' \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    ```
```

### Pattern 2: Collapsible Raw API Block
**What:** `??? example "Raw API"` inside the CLI tab. Indented 4 spaces (so it sits inside the tab).
**When to use:** first-job.md Step 4 CLI tab only — keeps the guide focused while preserving full curl reference.
**Example:**
```markdown
=== "CLI"

    ```bash
    axiom-push job push \
      --script hello.py \
      --key signing.key \
      --key-id <your-key-id>
    ```

    ??? example "Raw API"

        ```bash
        SIG=$(openssl pkeyutl -sign -inkey signing.key -rawin -in hello.py | base64 -w0)
        curl -sk -X POST https://<host>:8001/jobs \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d "{\"script_content\": \"$(cat hello.py | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\", \"signature\": \"$SIG\", \"signature_key_id\": \"<key-id>\"}"
        ```
```

### Pattern 3: Danger Callout Before a Step
**What:** `!!! danger "..."` block immediately above the step heading. Matches existing `!!! danger "Register before dispatching"` at Step 2.
**Example:**
```markdown
!!! danger "Register your signing key first"
    Complete Steps 1 and 2 before attempting to dispatch. Job creation fails with a `422` error if no public key is registered or if the signature does not match the registered key.

## Step 4: Dispatch the job
```

### Anti-Patterns to Avoid
- **Heading renames without anchor audit:** Any heading text change in the three guide files silently breaks the `#anchor` in cross-references. The cross-reference audit below confirms there are no `#anchor` links to the affected headings — but run `mkdocs build --strict` after each file edit to catch regressions.
- **Nested fences without superfences:** A fenced code block inside a tab block requires `pymdownx.superfences` (already present). Do not add a second superfences entry to `mkdocs.yml`.
- **Tabs without alternate_style:** Without `alternate_style: true`, tabs render as a flat list. This setting is mandatory.
- **`axiom-push` as the only CLI path in first-job.md:** The axiom-push guide marks the CLI as an EE feature. The raw curl `??? example` block ensures CE users also have a documented CLI path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content tabs | Custom HTML/JS tab widget | `pymdownx.tabbed` | Already in ecosystem; renders correctly in Material theme offline builds |
| Collapsible sections | Custom HTML `<details>` | `pymdownx.details` (`??? example`) | Already enabled; renders in offline/privacy plugin correctly |
| Build validation | Manual HTML inspection | `mkdocs build --strict` | Catches broken anchors, unresolved links, and malformed markdown |

---

## Common Pitfalls

### Pitfall 1: Tab Content Indentation
**What goes wrong:** Tab content that is not indented exactly 4 spaces renders outside the tab, appearing as loose text after the tab block.
**Why it happens:** MkDocs Material tabs use indentation to determine what belongs inside each tab. Mixed indentation (2 vs 4 spaces, or tabs vs spaces) breaks containment silently — the output HTML looks wrong but `mkdocs build` may not error.
**How to avoid:** Use exactly 4 spaces for all content inside `=== "Tab"` blocks, including code fences, admonitions, and further nested content.
**Warning signs:** Content appears outside the tab box on the rendered page; `mkdocs build --strict` does not catch this.

### Pitfall 2: Heading Anchor Regressions
**What goes wrong:** Renaming a heading (e.g. "Step 3: Install the node" → "Step 3: Install the node") changes the auto-generated anchor. Any cross-reference using `#step-3-install-the-node` silently 404s.
**Why it happens:** MkDocs slugifies headings to create anchors. Cross-references in the current docs use file-level links without anchors (e.g. `enroll-node.md` not `enroll-node.md#step-3-...`), so this phase's edits are low-risk. Verified: no `#anchor` cross-references exist in other docs pointing to the four files being edited.
**How to avoid:** Run `mkdocs build --strict` after each file edit. Don't rename step headings unless required.

### Pitfall 3: DOCS-04 and DOCS-05 Already Satisfied
**What goes wrong:** The planner writes new content for DOCS-04 and DOCS-05 (node image name and EXECUTION_MODE), overwriting correct content that already exists.
**Why it happens:** The requirements list says "fix" but the current `enroll-node.md` already has `localhost/master-of-puppets-node:latest` and `EXECUTION_MODE=docker` in the Option B snippet.
**How to avoid:** The planner task for `enroll-node.md` must read the file first and verify current values before writing. If already correct, the task is "verify no regression" not "write new content".

### Pitfall 4: axiom-push is EE-Gated
**What goes wrong:** `first-job.md` Step 4 CLI tab uses `axiom-push job push` as the hero command without noting it requires an EE licence, creating a friction point for CE users who try the CLI path and get a 402.
**Why it happens:** The axiom-push feature guide has an `!!! enterprise` callout, but that is in a different file.
**How to avoid:** Add a brief note in the CLI tab (e.g. `!!! note "axiom-push requires EE"` or inline text). The raw curl `??? example` block is the CE fallback — ensure it is present and functional without axiom-push.

### Pitfall 5: mkdocs.yml YAML Indentation
**What goes wrong:** Adding `pymdownx.tabbed` at the wrong indentation level under `markdown_extensions` causes a YAML parse error at build time.
**Why it happens:** The existing `pymdownx.superfences` entry has a nested `custom_fences` sub-key. The tabbed entry must be at the same level as `superfences` (two-space indent from `markdown_extensions`), not nested under `superfences`.
**How to avoid:** Match the indentation of `pymdownx.details` which is already correctly placed at the same level.

---

## Code Examples

### pymdownx.tabbed in mkdocs.yml
```yaml
# Source: MkDocs Material official docs (squidfunk.github.io/mkdocs-material/reference/content-tabs/)
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - admonition
  - pymdownx.details
  - pymdownx.tabbed:
      alternate_style: true
  - tables
```

### GHCR Pull Tab Content (install.md Step 1 CLI tab)
```markdown
=== "GHCR Pull (no git required)"

    Download the compose file directly and pull all images:

    ```bash
    curl -sSLO https://raw.githubusercontent.com/axiom-laboratories/axiom/main/puppeteer/compose.cold-start.yaml
    docker compose -f compose.cold-start.yaml pull
    ```

    Then continue with Step 2 to create your `.env` file before starting the stack.
```

### AGENT_URL Table (restructured for enroll-node.md)
```markdown
| Scenario | AGENT_URL |
|----------|-----------|
| Cold-start compose (node in same compose network) | `https://agent:8001` |
| Server compose, node on same host | `https://puppeteer-agent-1:8001` |
| Remote host / separate machine | `https://<hostname-or-ip>:8001` |
| Docker Desktop (Mac or Windows) | `https://host.docker.internal:8001` |

If your node is on a custom Linux bridge network, find the gateway with:

```bash
ip route | awk '/default/ {print $3}'
```
```

### CLI Token Generation (enroll-node.md Step 1 CLI tab)
```bash
# Source: existing CLI callout in enroll-node.md — promote to full tab content
TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<your-password>' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -sk -X POST https://<your-orchestrator>:8001/admin/generate-token \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('enhanced_token', d.get('join_token', '')))"
```

### Cold-Start .env Content (install.md Step 2 cold-start tab)
```bash
# .env — place in same directory as compose.cold-start.yaml
ADMIN_PASSWORD=<choose-a-password>
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sub-heading Option A / Option B in enroll-node.md | `=== "Option A"` / `=== "Option B"` tabs | Phase 67 | Cleaner UX; same content reorganised |
| CLI token path as `!!! note` secondary callout | Full `=== "CLI"` primary tab in Step 1 | Phase 67 | CLI is a first-class path, not a footnote |
| Single `secrets.env` password setup | Tab pair showing server install vs cold-start paths | Phase 67 | Cold-start users no longer miss the `.env` requirement |

**Already correct (no change needed):**
- `EXECUTION_MODE=docker` in enroll-node.md Option B snippet — already correct
- `localhost/master-of-puppets-node:latest` in enroll-node.md Option B — already correct
- Docker socket volume in enroll-node.md — already present as a `!!! tip`

---

## Open Questions

1. **axiom-push EE gate disclosure in first-job.md**
   - What we know: axiom-push guide has `!!! enterprise` callout; first-job.md currently only references axiom-push in a `!!! tip` in Step 3
   - What's unclear: Whether the planner should add an EE callout inside the CLI tab or just rely on the link to the axiom-push guide
   - Recommendation: Add a one-line `!!! note` inside the CLI tab noting EE requirement, so CE users see it before hitting a 402

2. **compose.cold-start.yaml URL in GHCR pull tab**
   - What we know: `compose.cold-start.yaml` exists at `puppeteer/compose.cold-start.yaml` in the repo; GHCR image is `ghcr.io/axiom-laboratories/axiom`; raw GitHub URL pattern is correct
   - What's unclear: Exact raw GitHub URL path (organisation name `axiom-laboratories` vs the actual org slug in the repo)
   - Recommendation: Use a placeholder `https://raw.githubusercontent.com/<org>/<repo>/main/puppeteer/compose.cold-start.yaml` with a `<!-- TODO: replace with real URL -->` comment for the planner

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | mkdocs build --strict (built-in MkDocs validation) |
| Config file | `docs/mkdocs.yml` |
| Quick run command | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-02 | `pymdownx.tabbed` present in mkdocs.yml | smoke | `grep "tabbed" docs/mkdocs.yml` | ✅ (mkdocs.yml exists; grep will verify after edit) |
| DOCS-01 | install.md has `.env` password setup before compose up | build smoke | `cd docs && mkdocs build --strict` | ✅ |
| DOCS-03 | enroll-node.md CLI tab present | build smoke | `cd docs && mkdocs build --strict` | ✅ |
| DOCS-04 | enroll-node.md uses correct node image | content check | `grep "master-of-puppets-node:latest" docs/docs/getting-started/enroll-node.md` | ✅ |
| DOCS-05 | No `EXECUTION_MODE=direct` in enroll-node.md | content check | `grep -c "EXECUTION_MODE=direct" docs/docs/getting-started/enroll-node.md` (expect 0) | ✅ |
| DOCS-06 | AGENT_URL table has `https://agent:8001` | content check | `grep "agent:8001" docs/docs/getting-started/enroll-node.md` | ✅ |
| DOCS-07 | Docker socket mount note in Option B | content check | `grep "docker.sock" docs/docs/getting-started/enroll-node.md` | ✅ |
| DOCS-08 | install.md GHCR pull tab present | build smoke + content | `grep "docker compose pull" docs/docs/getting-started/install.md` | ✅ |
| DOCS-09 | first-job.md signing key steps before dispatch | build smoke | `cd docs && mkdocs build --strict` | ✅ |
| DOCS-10 | first-job.md CLI dispatch tab present | content check | `grep "axiom-push job push" docs/docs/getting-started/first-job.md` | ✅ |
| DOCS-11 | Danger callout before Step 4 in first-job.md | content check | `grep "Register your signing key first" docs/docs/getting-started/first-job.md` | ✅ |

### Sampling Rate
- **Per task commit:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Per wave merge:** `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Phase gate:** `mkdocs build --strict` green + content grep checks for all 11 DOCS requirements

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. The `mkdocs build --strict` command is available and passes against the current unmodified codebase.

---

## Sources

### Primary (HIGH confidence)
- MkDocs Material official docs (squidfunk.github.io/mkdocs-material/reference/content-tabs/) — pymdownx.tabbed configuration and tab syntax
- `docs/mkdocs.yml` in repo — current extension configuration verified by direct read
- `docs/docs/getting-started/install.md` — current content verified by direct read
- `docs/docs/getting-started/enroll-node.md` — current content verified by direct read; DOCS-04 and DOCS-05 already satisfied
- `docs/docs/getting-started/first-job.md` — current content verified by direct read
- `puppeteer/compose.cold-start.yaml` — verified AGENT_URL=`https://agent:8001` and EXECUTION_MODE=docker in node services
- `mkdocs build --strict` test run — confirmed current build passes before edits

### Secondary (MEDIUM confidence)
- `docs/requirements.txt` — mkdocs-material==9.7.5, pymdown-extensions 10.21 (via pip show) — extension compatibility confirmed
- `docs/docs/feature-guides/axiom-push.md` — axiom-push EE gate (`!!! enterprise`) and `axiom-push job push` command syntax confirmed

### Tertiary (LOW confidence)
- GHCR image name `ghcr.io/axiom-laboratories/axiom` — from CONTEXT.md decisions; org slug not independently verified against published registry

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — mkdocs-material 9.7.5 and pymdownx.tabbed syntax verified against official docs and local environment
- Architecture patterns: HIGH — all edit patterns derived from existing doc structure and confirmed working examples
- Pitfalls: HIGH — DOCS-04/05 already-satisfied trap and tab indentation pitfalls verified by direct file inspection and build test

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (mkdocs-material 9.x is stable; no fast-moving dependencies)

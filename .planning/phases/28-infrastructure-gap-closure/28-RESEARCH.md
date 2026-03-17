# Phase 28: Infrastructure Gap Closure - Research

**Researched:** 2026-03-17
**Domain:** MkDocs Material plugin configuration (privacy + offline)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Both plugins use default settings — no custom options
- Ordering: `search` → `privacy` → `offline` → `swagger-ui-tag`
- Add a comment above the privacy + offline entries: `# privacy + offline: required for air-gap / offline operation (INFRA-06) — do not remove`
- Verification: build the docs Docker image with `docker compose build docs`, then grep the built HTML for zero external CDN references
- Grep pattern: `fonts.googleapis.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`
- Both build success AND the grep passing are required to close INFRA-06
- Mark INFRA-06 as `[x]` in `.planning/REQUIREMENTS.md` once fix is verified
- Read `docs/docs/security/air-gap.md` and confirm it references privacy + offline correctly — consistency check only, no content rewrite expected
- No new script files added to the repo — the verification command lives in the plan task only

### Claude's Discretion

- Exact wording of the comment in mkdocs.yml
- Whether to rebuild the docs container as part of verification or use `docker build` directly

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-06 | Docs site works offline / air-gapped (no external CDN assets at runtime) | privacy plugin fetches external assets at build time; offline plugin bundles all JS/CSS — together they eliminate all CDN references from the served HTML |
| SECU-04 | Air-gap operation guide covers package mirroring, offline builds, and network isolation | air-gap.md already references the privacy + offline plugin as the mechanism for CDN-free docs; once INFRA-06 is satisfied the guide's claims become accurate |
</phase_requirements>

---

## Summary

Phase 28 is a surgical regression fix. Commit `ab25961` (Phase 22 completion commit) removed two lines from `docs/mkdocs.yml` — the `privacy` and `offline` plugin entries — that were explicitly required by Phase 20 for INFRA-06. The current `mkdocs.yml` has only `search` and `swagger-ui-tag` in the plugins list. Restoring the two removed lines is the complete scope of the code change.

Both plugins ship bundled with `mkdocs-material`. The project's `docs/requirements.txt` pins `mkdocs-material==9.7.5`, and both plugins are confirmed available at that version on this machine. No new pip dependencies are needed.

The air-gap guide (`docs/docs/security/air-gap.md`) already accurately describes the privacy + offline mechanism as the means of achieving CDN-free docs. Once the plugins are restored, the guide's claims will be satisfied by the actual build — no content changes are needed, only the consistency check.

**Primary recommendation:** Add two lines back to `docs/mkdocs.yml`, verify with a Docker build + grep, mark INFRA-06 complete.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.7.5 | MkDocs theme; ships privacy + offline plugins | Already pinned in `docs/requirements.txt`; no version change needed |

### Plugin Details

| Plugin | Source | Activation | What It Does |
|--------|--------|-----------|--------------|
| `privacy` | Bundled with mkdocs-material | `- privacy` in `plugins:` | At build time, downloads all external assets (Google Fonts, CDN-hosted JS/CSS) and rewrites HTML references to local paths |
| `offline` | Bundled with mkdocs-material | `- offline` in `plugins:` | Bundles the MkDocs search and navigation JS so the site works without a web server (static file open) and without internet |

Both plugins require **no configuration** when used at default settings. An empty entry in the plugins list (just `- privacy` and `- offline`) is the correct and complete form.

### Ordering Rationale

`search` → `privacy` → `offline` → `swagger-ui-tag` is the correct order because:
- `privacy` must run before `offline` — it fetches external assets first so `offline` can then bundle the full set including those downloaded assets
- `search` must precede both so the search index is built before bundling

**Installation:** No new packages. Both plugins are already present in the installed `mkdocs-material==9.7.5`.

---

## Architecture Patterns

### What the Regression Broke

The `privacy` plugin normally runs during `mkdocs build` and:
1. Scans all HTML output for external asset references (`fonts.googleapis.com`, `fonts.gstatic.com`, `cdn.jsdelivr.net`, etc.)
2. Downloads those assets to `assets/external/`
3. Rewrites all HTML `<link>` and `<script>` tags to point to the local copies

Without it, `mkdocs-material` outputs HTML referencing Google Fonts directly. The built Docker image therefore makes outbound font requests at runtime — breaking air-gap operation.

The `offline` plugin additionally rewrites the instant-loading JS bundle to work in a file:// context and disables features that require a live server. Without it, the site still loads over HTTP but with degraded offline behaviour.

### Current State (Confirmed by Inspection)

`docs/mkdocs.yml` plugins section currently reads:
```yaml
plugins:
  - search
  - swagger-ui-tag
```

After the fix it must read:
```yaml
plugins:
  - search
  # privacy + offline: required for air-gap / offline operation (INFRA-06) — do not remove
  - privacy
  - offline
  - swagger-ui-tag
```

### Dockerfile — No Changes Needed

`docs/Dockerfile` builder stage runs `RUN mkdocs build --strict`. The `--strict` flag means any MkDocs warning is a build error. Adding the privacy and offline plugins does not introduce any new warnings under mkdocs-material 9.7.5 (confirmed: both plugins are stable in this version). The Dockerfile does not need editing.

### Verification Architecture

The verification is intentionally stateless — no script file is added to the repo. The check command is run as a one-off `docker run` after a successful `docker compose build docs`:

```bash
# Step 1: build
docker compose -f puppeteer/compose.server.yaml build docs

# Step 2: CDN reference scan (must print PASS)
docker run --rm localhost/master-of-puppets-docs:v1 \
  sh -c "grep -rq 'fonts.googleapis.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' /usr/share/nginx/html \
         && echo FAIL || echo PASS"
```

Note: `grep -q` with `&&` / `||` logic — `grep` exits 0 if it FINDS a match. So `&& echo FAIL || echo PASS` is the correct polarity: finding a CDN reference means failure.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Downloading external fonts/JS | Custom wget/curl scripts in Dockerfile | `privacy` plugin | Handles Google Fonts, Material Icons, and CDN-hosted JS with URL rewriting; handles edge cases like multiple font variants |
| Offline bundle | Manual asset copy + path rewriting | `offline` plugin | Handles MkDocs Material's instant-loading JS and search worker correctly — manual bundling would break navigation |

**Key insight:** Both plugins are already paid for — they ship with mkdocs-material. The regression removed zero-cost capabilities that were already working.

---

## Common Pitfalls

### Pitfall 1: CDN Grep Polarity
**What goes wrong:** The verification grep command reads backwards — `grep` exits 0 on MATCH (finds CDN refs = bad), not on no-match.
**Why it happens:** Intuitive reading is "grep for X; if found, it's there". But the verification goal is to assert X is absent.
**How to avoid:** Use `grep -rq 'pattern' dir && echo FAIL || echo PASS`. The `&&` branch runs when grep finds something (exit 0 = found = FAIL).
**Warning signs:** "PASS" printed immediately without a Docker build, or "PASS" on an unmodified current build.

### Pitfall 2: Plugin Ordering Matters
**What goes wrong:** Placing `offline` before `privacy` means offline bundles assets before privacy has downloaded the external ones, leaving some external references in the bundle.
**Why it happens:** Plugin execution is sequential in mkdocs.
**How to avoid:** Always `privacy` then `offline`. This is the ordering locked in CONTEXT.md.

### Pitfall 3: Confusing `--strict` With CDN Check
**What goes wrong:** A clean `docker compose build docs` is taken as proof that no CDN references exist.
**Why it happens:** `--strict` only catches MkDocs warnings (broken refs, missing files), not CDN presence in output HTML.
**How to avoid:** The grep check is required separately even when the Docker build succeeds.

### Pitfall 4: `privacy` Plugin Requires Network During Docker Build
**What goes wrong:** The Docker builder stage has no outbound internet access (air-gap CI).
**Why it happens:** The `privacy` plugin downloads external assets during `mkdocs build`. It needs internet access during the build itself (not at runtime).
**How to avoid:** This is expected — the Docker build requires internet access; the resulting image does not. The goal is CDN-free at RUNTIME. The air-gap guide documents this distinction explicitly.

---

## Code Examples

### Correct mkdocs.yml plugins section after fix

```yaml
# Source: CONTEXT.md locked decision + regression diff ab25961
plugins:
  - search
  # privacy + offline: required for air-gap / offline operation (INFRA-06) — do not remove
  - privacy
  - offline
  - swagger-ui-tag
```

### Verification command (CDN absence check)

```bash
# Source: CONTEXT.md verification method
docker run --rm localhost/master-of-puppets-docs:v1 \
  sh -c "grep -rq 'fonts.googleapis.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' /usr/share/nginx/html \
         && echo FAIL || echo PASS"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 20: privacy + offline present | Phase 22 regression: both removed | Commit ab25961, 2026-03-17 | Docs build no longer satisfies INFRA-06; air-gap guide claims are inaccurate |
| After Phase 28: both restored | Satisfies INFRA-06 + SECU-04 air-gap checklist | This phase | CDN-free docs; air-gap guide claims become accurate |

**Deprecated/outdated:**
- No deprecations in this phase. Both `privacy` and `offline` are active, supported plugins in mkdocs-material 9.7.5.

---

## Air-Gap Guide Consistency Check

The `docs/docs/security/air-gap.md` file already correctly describes the mechanism:

- Line 17: "MkDocs `privacy` + `offline` plugins pre-download all external assets (fonts, JavaScript) at Docker build time — zero CDN or outbound requests at runtime"
- Lines 103–104: "The MkDocs build uses the `privacy` plugin to download all external assets ... At runtime, the nginx container serves only local files with no outbound requests."

Both statements are accurate descriptions of what the plugins do. They are currently FALSE because the plugins are absent. Once the plugins are restored, the guide becomes accurate with no content changes needed.

The air-gap readiness checklist (lines 155–156) includes:
```
- [ ] Documentation site loads without external requests (browser Dev Tools → Network tab checked)
```

This checklist item will be satisfiable after the fix.

**Conclusion:** No content edits to `air-gap.md` are required. The consistency check is PASS.

---

## Open Questions

None — the scope is fully defined by the regression diff and the CONTEXT.md locked decisions. All technical questions have been resolved by direct inspection of the codebase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Docker build + grep (no unit test framework applicable) |
| Config file | `docs/Dockerfile` (builder stage runs `mkdocs build --strict`) |
| Quick run command | `docker compose -f puppeteer/compose.server.yaml build docs` |
| Full suite command | Build + CDN grep scan (see below) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-06 | Docs site has zero external CDN references in built HTML | Build + grep scan | `docker compose -f puppeteer/compose.server.yaml build docs && docker run --rm localhost/master-of-puppets-docs:v1 sh -c "grep -rq 'fonts.googleapis.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' /usr/share/nginx/html && echo FAIL || echo PASS"` | N/A — runtime check |
| SECU-04 | Air-gap guide accurately describes privacy + offline as CDN-free mechanism | manual-only | Read `docs/docs/security/air-gap.md` and confirm references match restored plugin config | ✅ existing file |

### Sampling Rate

- **Per task commit:** `docker compose -f puppeteer/compose.server.yaml build docs` (build must succeed)
- **Per wave merge:** Build + CDN grep scan (both must pass)
- **Phase gate:** Build succeeds + grep prints PASS + INFRA-06 marked `[x]` in REQUIREMENTS.md

### Wave 0 Gaps

None — existing test infrastructure (Docker build with `--strict`) covers the phase. No new test files, fixtures, or framework installs required.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection — `docs/mkdocs.yml` (current state: plugins missing)
- Git diff `ab25961` — confirmed exact two lines removed (`- privacy`, `- offline`)
- `docs/requirements.txt` — `mkdocs-material==9.7.5` pinned
- `docs/Dockerfile` — builder stage confirmed; no changes needed
- `docs/docs/security/air-gap.md` — guide content confirmed accurate for the post-fix state
- Python import test — `material.plugins.privacy.plugin` and `material.plugins.offline.plugin` both importable from installed 9.7.5
- Phase 20 CONTEXT.md — confirmed original intent: "Include both the `privacy` plugin ... and the `offline` plugin ... to fully satisfy INFRA-06"

### Secondary (MEDIUM confidence)

- MkDocs Material plugin ordering convention (privacy before offline) — consistent with Phase 20 CONTEXT.md decisions and general plugin ordering documentation

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — plugins confirmed present in installed mkdocs-material 9.7.5
- Architecture: HIGH — regression diff is definitive; before/after state fully determined
- Pitfalls: HIGH — grep polarity and ordering verified against locked CONTEXT.md decisions

**Research date:** 2026-03-17
**Valid until:** Stable — mkdocs-material plugin API is unchanged; no expiry concern for this fix

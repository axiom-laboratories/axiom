# Phase 69: Fix CI Release Pipeline Version Pinning and Semver Tags — Research

**Researched:** 2026-03-26
**Domain:** Python packaging (setuptools-scm), GitHub Actions CI, docker/metadata-action
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `setuptools-scm` to derive the Python package version automatically from the git tag at build time
- Remove hardcoded `version = "1.0.0-alpha"` from `pyproject.toml`; replace with `dynamic = ["version"]` and a `[tool.setuptools_scm]` section
- Add `setuptools-scm` to the `[build-system] requires` list in `pyproject.toml`
- Keep the existing 2-part tag format (`v14.0`, `v15.0`) — do not change historical tags
- Adjust `docker/metadata-action` tags block to use `type=ref,event=tag` as primary or sole tag source (drop strict `type=semver` patterns that require 3-part versions)

### Claude's Discretion
- Exact setuptools-scm configuration (write_to vs fallback_version, tag regex)
- Whether to strip the `v` prefix from the Python package version (standard practice)
- Fallback version value for local dev builds without a git tag
- Whether `publish-testpypi` should remain in the pipeline — keep it (useful staging gate)
- Node.js 20 deprecation warnings on actions — out of scope

### Deferred Ideas (OUT OF SCOPE)
- Updating Node.js 20 action versions (deprecation warnings only)
- Adding a `publish-pypi` smoke test after upload
- Changelog generation from tags
</user_constraints>

---

## Summary

Two independent CI failures block every release. The first is a hardcoded `version = "1.0.0-alpha"` in `pyproject.toml` — every tag push builds the same wheel filename and TestPyPI rejects the duplicate. The fix is to switch to `dynamic = ["version"]` with `setuptools-scm` in `build-system.requires`; the tool reads the git tag at build time and produces a unique PEP 440 version per release. The second failure is `docker/metadata-action` configured with `type=semver` patterns that reject 2-part tags (`v14.0`), leaving the push with zero Docker tags and a fatal "tag is needed" error. The fix is replacing the semver patterns with `type=ref,event=tag`, which passes the raw git tag string directly to the Docker image tag without any semver validation.

Both fixes touch exactly two files: `pyproject.toml` and `.github/workflows/release.yml`. No structural workflow changes are needed. The OIDC trusted publishing setup (`id-token: write`, `pypa/gh-action-pypi-publish`) is unaffected.

**Primary recommendation:** Add `setuptools-scm>=8` to `build-system.requires`, set `dynamic = ["version"]` with an empty or minimal `[tool.setuptools_scm]` section, add `fetch-depth: 0` to the `actions/checkout` step in `build-python`, and replace the two `type=semver` lines with `type=ref,event=tag` in the Docker metadata step.

---

## Standard Stack

### Core
| Library/Action | Version | Purpose | Why Standard |
|---|---|---|---|
| `setuptools-scm` | `>=8` (current: 10.0.2) | Derives Python package version from git tags at build time | Official PyPA tool; zero manual version bumps; PEP 440 compliant |
| `docker/metadata-action` | `@v6` (already in use) | Generates Docker image tags and labels from git refs | Official Docker action; already present in workflow |
| `pypa/gh-action-pypi-publish` | `release/v1` (already in use) | Publishes wheels to (Test)PyPI via OIDC | Official pypa action; already wired with trusted publisher |

### Supporting
| Library/Action | Version | Purpose | When to Use |
|---|---|---|---|
| `pip install build` | latest | PEP 517 build frontend that invokes setuptools-scm | Already in workflow — no change needed |
| `actions/checkout@v4` | v4 | Source checkout | Already in workflow; needs `fetch-depth: 0` added |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| `setuptools-scm` | `hatch-vcs` or manual `GITHUB_REF` parsing | hatch-vcs is equivalent but requires switching build backend; manual parsing is fragile and non-standard |
| `type=ref,event=tag` | `type=semver` with `enable` conditional | Conditional semver is fragile; ref is simpler and always correct for raw git tags |

**Installation (pyproject.toml build requires — no pip install needed in workflow):**
```toml
[build-system]
requires = ["setuptools>=77.0", "setuptools-scm>=8"]
```

---

## Architecture Patterns

### Pattern 1: setuptools-scm Dynamic Version in pyproject.toml

**What:** Replace static `version =` with dynamic discovery from git tag.

**When to use:** Any project where version = git tag (standard for PyPI releases triggered by tag push).

**Minimal required config (setuptools-scm >= 8.1):**
```toml
# Source: https://pypi.org/project/setuptools-scm/
[build-system]
requires = ["setuptools>=77.0", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-agent-sdk"
dynamic = ["version"]
# ... rest of project unchanged ...

[tool.setuptools_scm]
# Section must exist even if empty (signals opt-in to setuptools-scm).
# fallback_version used when no git tag is present (local dev, sdist without .git)
fallback_version = "0.0.0.dev0"
```

Key points:
- `dynamic = ["version"]` removes `version = "..."` from `[project]`
- `[tool.setuptools_scm]` section MUST be present (even empty) for setuptools-scm to activate via `build-system.requires`
- `fallback_version` prevents build failures in environments without git (e.g., editable installs from tarball)
- No `write_to` / `version_file` needed for CI-only usage; these are only needed if you want `_version.py` importable at runtime

**How 2-part tags are handled:**
- `v14.0` is a valid PEP 440 version string — normalized to `14.0`
- setuptools-scm strips the `v` prefix automatically by default
- When the build runs exactly on the tagged commit, the output is `14.0` with no `.dev` suffix
- The "guessing" (incrementing micro segment for non-tagged commits) never triggers in this workflow because `on: push: tags: "v*"` only fires on tagged commits
- Wheel filename produced: `axiom_agent_sdk-14.0-py3-none-any.whl`

### Pattern 2: GitHub Actions Checkout with Full Tag History

**What:** Add `fetch-depth: 0` to the checkout step so setuptools-scm can read git tags.

**When to use:** Any workflow using setuptools-scm. Default `actions/checkout` shallow-clones with depth 1, which may not include tag metadata in all cases.

```yaml
# Source: https://github.com/pypa/setuptools-scm/issues/480
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

Note: For tag-triggered workflows, the triggering tag is always fetched even without `fetch-depth: 0`, but `fetch-depth: 0` is the defensive standard and costs negligible time on small repos like this one.

### Pattern 3: docker/metadata-action with type=ref,event=tag

**What:** Use raw git tag ref as Docker image tag instead of parsing it as semver.

**When to use:** When git tags are not strict 3-part semver (e.g., `v14.0`, `v2`, or any non-standard format).

```yaml
# Source: https://github.com/docker/metadata-action
- name: Extract Docker metadata
  id: meta
  uses: docker/metadata-action@v6
  with:
    images: ghcr.io/axiom-laboratories/axiom
    flavor: |
      latest=auto
    tags: |
      type=ref,event=tag
```

**Output for git tag `v14.0`:**
- `ghcr.io/axiom-laboratories/axiom:v14.0`
- `ghcr.io/axiom-laboratories/axiom:latest` (from `latest=auto` in flavor)

**Why `latest=auto` works with `type=ref,event=tag`:** The flavor `latest=auto` applies the `latest` tag to the highest-priority tag event. Since this is a tag-push workflow, the `latest` tag is always generated alongside the ref tag. This is the same behavior as before (the old config also had `latest=auto`).

### Anti-Patterns to Avoid

- **Setting `write_to` or `version_file` without a reason:** These write a `_version.py` file into the source tree and cause merge conflicts or dirty working trees in CI. Omit unless the version must be importable at runtime from installed packages.
- **Using `type=semver` with 2-part tags:** This produces zero tags and fails the Docker build step. Verified from CI failure log.
- **Omitting `[tool.setuptools_scm]` section entirely:** While setuptools-scm 8.1+ makes it optional in theory, the presence of an explicit (even empty) section is the reliable signal and avoids tool version ambiguity.
- **Omitting `fetch-depth: 0`:** Default shallow clone from `actions/checkout` with depth 1 can cause setuptools-scm to fall back to `fallback_version` on the build-python job, producing a version mismatch between what was built and what the tag says.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Extracting version from git tag | Shell: `git describe --tags` + sed/awk in workflow | `setuptools-scm` in `build-system.requires` | Handles edge cases: annotated vs lightweight tags, dirty tree, fallback, PEP 440 normalization |
| Stripping `v` prefix | Manual string manipulation | setuptools-scm default behavior | Default tag regex already strips the `v` prefix |
| Injecting version into workflow steps | `${{ github.ref_name }}` env var parsing | setuptools-scm writes version into wheel metadata at build time | The wheel version IS the ground truth; workflow env vars are redundant |

---

## Common Pitfalls

### Pitfall 1: `[tool.setuptools_scm]` section missing entirely
**What goes wrong:** Some setuptools-scm versions require the section to exist (even empty) to activate. Without it, `dynamic = ["version"]` may produce `0.0.0` or fail with "unable to detect version".
**Why it happens:** The section is technically optional in >= 8.1 but the exact version in the CI runner is not pinned to that level by the `>=8` lower bound alone.
**How to avoid:** Always include the section, even if empty: `[tool.setuptools_scm]` with just `fallback_version`.
**Warning signs:** Wheel built with version `0.0.0` or build error "LookupError: setuptools-scm was unable to detect version".

### Pitfall 2: Shallow clone producing wrong version
**What goes wrong:** `actions/checkout` default depth=1. On tag-triggered runs the tag is usually present, but in edge cases setuptools-scm may fall back to `fallback_version = "0.0.0.dev0"`.
**Why it happens:** Git tag metadata may not be attached to the shallow clone HEAD.
**How to avoid:** Add `fetch-depth: 0` to the checkout step in `build-python`.
**Warning signs:** Wheel filename shows `axiom_agent_sdk-0.0.0.dev0-...` in artifacts.

### Pitfall 3: `latest=auto` not tagging Docker image as `latest`
**What goes wrong:** If the tag format changes (e.g., a pre-release tag like `v14.0-rc1`) Docker metadata-action's `latest=auto` may not assign `latest` because it detects the tag as a pre-release.
**Why it happens:** `latest=auto` with `type=ref,event=tag` assigns `latest` for non-pre-release tag events.
**How to avoid:** Not a concern for `v14.0`-style tags. If pre-release tags are ever introduced, add explicit `type=raw,value=latest,enable=${{ !contains(github.ref, '-') }}` logic.
**Warning signs:** `latest` tag missing from pushed image after a release.

### Pitfall 4: TestPyPI duplicate version upload on re-run
**What goes wrong:** After the fix, if you push the same tag twice (e.g., force-delete and re-push), TestPyPI will again reject a duplicate wheel version (400 Bad Request).
**Why it happens:** PyPI/TestPyPI is immutable — same version cannot be re-uploaded.
**How to avoid:** Never force-push or delete/recreate the same tag after a release. This is now expected behavior, not a bug.
**Warning signs:** Same 400 error from TestPyPI but this time it's legitimate (not a code bug).

---

## Code Examples

### Final pyproject.toml diff (key sections only)
```toml
# Source: setuptools-scm docs https://pypi.org/project/setuptools-scm/
[build-system]
requires = ["setuptools>=77.0", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-agent-sdk"
# REMOVED: version = "1.0.0-alpha"
dynamic = ["version"]
# ... rest unchanged ...

[tool.setuptools_scm]
fallback_version = "0.0.0.dev0"
```

### Final release.yml diff (build-python job checkout step)
```yaml
# Add fetch-depth: 0 to checkout in build-python job
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

### Final release.yml diff (docker-release job metadata step)
```yaml
# Source: https://github.com/docker/metadata-action
- name: Extract Docker metadata
  id: meta
  uses: docker/metadata-action@v6
  with:
    images: ghcr.io/axiom-laboratories/axiom
    flavor: |
      latest=auto
    tags: |
      type=ref,event=tag
```

### Expected outputs for tag `v14.0`
| Artifact | Before fix | After fix |
|---|---|---|
| Python wheel | `axiom_agent_sdk-1.0.0a0-py3-none-any.whl` | `axiom_agent_sdk-14.0-py3-none-any.whl` |
| TestPyPI result | 400 Bad Request (duplicate) | 200 OK |
| Docker tags | (none — build fails) | `ghcr.io/axiom-laboratories/axiom:v14.0`, `:latest` |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `write_to = "pkg/_version.py"` | `version_file = "..."` (or omit entirely) | setuptools-scm v7+ | `write_to` is deprecated; use `version_file` if a file is needed |
| setuptools-scm required in `pip install` step | `build-system.requires` only | setuptools-scm v8+ | Build frontend (`python -m build`) installs build deps automatically from `build-system.requires` — no separate `pip install setuptools-scm` step needed |
| `[tool.setuptools_scm]` always required | Optional since v8.1 | setuptools-scm 8.1 | Minimal configs need only `dynamic = ["version"]` + entry in `requires`, but explicit section is still recommended |

**Deprecated/outdated:**
- `write_to`: replaced by `version_file`; omit entirely if no importable version file is needed
- `version = "1.0.0-alpha"` static field: incompatible with `dynamic = ["version"]`; must be removed

---

## Open Questions

1. **Does the existing TestPyPI trusted publisher configuration accept wheel version `14.0` (2-part)?**
   - What we know: OIDC trusted publishing is version-agnostic — it validates GitHub environment + repo identity, not the version string
   - What's unclear: Whether TestPyPI has any additional validation on 2-part version strings beyond PEP 440 compliance
   - Recommendation: `14.0` is valid PEP 440; no issue expected. If TestPyPI rejects it, add patch component via `tag_regex` that appends `.0` — but this is unlikely to be needed.

2. **Should `fetch-depth: 0` also be added to `docker-release` job checkout?**
   - What we know: The docker job uses `actions/checkout@v4` without `fetch-depth`; Docker metadata-action reads from `GITHUB_REF` env var (not git history), so no git depth needed
   - What's unclear: Nothing — Docker metadata-action does not use git commands
   - Recommendation: No change needed to docker-release checkout.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd puppeteer && pytest` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map

This phase has no functional requirements in REQUIREMENTS.md (it is a CI/tooling fix, not a user-facing feature). Validation is by inspection: the workflow YAML and pyproject.toml are correct by construction, and the proof is a successful GitHub Actions run on the next tag push.

| Behavior | Test Type | How to Validate |
|---|---|---|
| `pyproject.toml` no longer has static `version =` | Manual inspection | `grep 'version = ' pyproject.toml` returns only `dynamic = ["version"]` |
| `setuptools-scm` in build-system.requires | Manual inspection | `grep setuptools-scm pyproject.toml` shows entry |
| `[tool.setuptools_scm]` section present | Manual inspection | Section exists with `fallback_version` |
| `type=semver` lines removed from release.yml | Manual inspection | `grep 'type=semver' .github/workflows/release.yml` returns nothing |
| `type=ref,event=tag` present | Manual inspection | `grep 'type=ref' .github/workflows/release.yml` shows entry |
| Local dev build works (no git tag) | Local test | `pip install build && python -m build` from repo root produces wheel with version `0.0.0.dev0` |
| CI build on tag produces correct version | CI run | Next `v*.0` tag push — check `build-python` artifact filename in Actions |

### Wave 0 Gaps
None — existing test infrastructure covers backend and frontend. This phase only modifies two config files; no new test files are required.

---

## Sources

### Primary (HIGH confidence)
- [setuptools-scm PyPI page](https://pypi.org/project/setuptools-scm/) — current version (10.0.2), minimal pyproject.toml config, dynamic version activation
- [setuptools-scm config.md (GitHub)](https://github.com/pypa/setuptools-scm/blob/main/docs/config.md) — full option reference: version_file, fallback_version, tag_regex, normalize, write_to deprecation
- [docker/metadata-action README (GitHub)](https://github.com/docker/metadata-action) — type=ref,event=tag behavior, latest=auto with tag events, v6 syntax

### Secondary (MEDIUM confidence)
- [setuptools-scm issue #480](https://github.com/pypa/setuptools-scm/issues/480) — fetch-depth: 0 requirement confirmed with actions/checkout
- [docker/metadata-action README (PSI mirror)](https://gitea.psi.ch/docker/metadata-action/src/commit/902fa8ec7d6ecbf8d84d538b9b233a880e428804/README.md) — tag output examples for type=ref,event=tag

### Tertiary (LOW confidence — use for orientation only)
- [setuptools-scm issue #679](https://github.com/pypa/setuptools-scm/issues/679) — version_scheme naming clarification
- [moritzkoerber.com setuptools-scm post](https://www.moritzkoerber.com/posts/versioning-with-setuptools_scm/) — fetch-depth: 0 walkthrough (blog, not official)

---

## Metadata

**Confidence breakdown:**
- setuptools-scm config: HIGH — confirmed via official PyPI page and GitHub source doc
- 2-part tag behavior: HIGH — PEP 440 accepts `14.0`; v14.0 strips to `14.0`; workflow only triggers on tag commits (no guessing)
- docker/metadata-action type=ref: HIGH — confirmed from official README
- fetch-depth: 0 requirement: HIGH — confirmed from official issue tracker
- OIDC publish compatibility: HIGH — OIDC is version-agnostic by design

**Research date:** 2026-03-26
**Valid until:** 2026-09-26 (stable ecosystem; setuptools-scm and metadata-action APIs are stable)

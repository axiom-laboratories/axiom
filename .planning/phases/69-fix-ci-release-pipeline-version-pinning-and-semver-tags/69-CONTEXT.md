# Phase 69: Fix CI Release Pipeline — Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Source:** Direct investigation of GitHub Actions failures (axiom-laboratories/axiom)

<domain>
## Phase Boundary

Fix two independent CI failures in `.github/workflows/release.yml` that block every release:

1. **TestPyPI 400 Bad Request** — `pyproject.toml` has a hardcoded version (`1.0.0-alpha`). Every git tag push builds and attempts to re-upload the same `axiom_agent_sdk-1.0.0a0` wheel. TestPyPI rejects duplicate uploads with HTTP 400. The `publish-pypi` job never runs because it depends on `publish-testpypi`.

2. **Docker build "tag is needed" error** — `docker/metadata-action` uses `type=semver` patterns which require 3-part semver (`v14.0.0`). Tags are currently 2-part (`v14.0`). This produces zero Docker tags, causing `build-push-action` to fail with `ERROR: failed to build: tag is needed when pushing to registry`.

These are independent failures that happen in the same workflow run. Both must be fixed for a release to fully succeed.

</domain>

<decisions>
## Implementation Decisions

### Version Derivation Strategy
- **Use `setuptools-scm`** to derive the Python package version automatically from the git tag at build time
- This means pushing `v14.0` produces `axiom_agent_sdk-14.0-py3-none-any.whl` automatically — no manual version bumps needed
- Remove the hardcoded `version = "1.0.0-alpha"` from `pyproject.toml`; replace with `dynamic = ["version"]` and a `[tool.setuptools_scm]` section
- Add `setuptools-scm` to the `[build-system] requires` list in `pyproject.toml`

### Tag Format for Docker
- **Keep the existing 2-part tag format** (`v14.0`, `v15.0`) — changing all historical tags is disruptive
- Adjust the `docker/metadata-action` tags block to use `type=ref,event=tag` (raw tag ref) as a fallback alongside the semver patterns, OR switch to patterns that don't enforce strict semver
- Alternative: use `type=semver,pattern={{major}}.{{minor}}` only when tags include a patch component — but this is fragile
- **Preferred:** Use `type=ref,event=tag` as primary tag source so the Docker image is tagged exactly as the git tag, plus add `type=semver,pattern={{version}}` with `enable` conditioned on tag format — OR simplest fix: drop `type=semver` patterns entirely and use raw tag + `latest=auto`

### Claude's Discretion
- Exact setuptools-scm configuration (write_to vs fallback_version, tag regex)
- Whether to strip the `v` prefix from the Python package version (standard practice)
- Fallback version value for local dev builds without a git tag
- Whether `publish-testpypi` should remain in the pipeline or be removed now that it will always succeed with a unique version — keep it, it's a useful staging gate
- Node.js 20 deprecation warnings on actions — out of scope for this phase (functional issue only)

</decisions>

<specifics>
## Specific Details from Investigation

**Failing run:** axiom-laboratories/axiom run ID 23563414272 (tag v14.0, 2026-03-25)

**Exact error — TestPyPI:**
```
Uploading axiom_agent_sdk-1.0.0a0-py3-none-any.whl
WARNING  Error during upload. Retry with the --verbose option for more details.
ERROR    HTTPError: 400 Bad Request from https://test.pypi.org/legacy/
```

**Exact error — Docker:**
```
! v14.0 is not a valid semver.
! No Docker tag has been generated. Check tags input.
ERROR: failed to build: tag is needed when pushing to registry
```

**Files to change:**
- `pyproject.toml` — version field, build-system requires, add setuptools-scm config
- `.github/workflows/release.yml` — docker metadata-action tags block

**Current pyproject.toml version line:**
```toml
version = "1.0.0-alpha"
```

**Current docker metadata tags:**
```yaml
tags: |
  type=semver,pattern={{version}}
  type=semver,pattern={{major}}.{{minor}}
```

</specifics>

<deferred>
## Deferred Ideas

- Updating Node.js 20 action versions (deprecation warnings only, not functional failures)
- Adding a `publish-pypi` smoke test after upload
- Changelog generation from tags

</deferred>

---

*Phase: 69-fix-ci-release-pipeline-version-pinning-and-semver-tags*
*Context gathered: 2026-03-26 from live CI failure investigation*

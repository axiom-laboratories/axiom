# Stack Research

**Domain:** Operator Readiness — licence generation tooling, docs accuracy validation, screenshot capture, node validation job library, custom package repo docs and validation
**Researched:** 2026-03-28
**Confidence:** HIGH

---

## Context: Existing Stack (Do Not Re-research)

The existing stack already handles every primitive these five features depend on. New features require additions at the tooling and scripting layer only — no new server-side dependencies.

| Component | Status | Relevant to v15.0 |
|-----------|--------|-------------------|
| `cryptography` 46.x | In `requirements.txt` | Ed25519 signing (licence generator already uses it) |
| `PyJWT[crypto]` >= 2.7.0 | In `requirements.txt` | EdDSA JWT encode/decode (licence JWT already uses it) |
| `playwright` (Python) | In `mop_validation/` | Screenshot capture already works there |
| `pypiserver/pypiserver` | In `compose.server.yaml` | PyPI sidecar already deployed |
| `devpi` (muccg/devpi image) | In `compose.server.yaml` | Internal wheel index already deployed |
| `pytest` + `httpx` | In `puppeteer/requirements.txt` | API smoke tests already possible |
| `tools/generate_licence.py` | In `tools/` | Offline CLI signing already implemented (Ed25519 JWT) |

---

## Feature 1: Licence Generation Tooling (Issuance Records in Private GitHub Repo)

### What Already Exists

`tools/generate_licence.py` is a complete offline CLI using `cryptography` + `PyJWT`. It generates Ed25519 keypairs, signs JWT payloads, and prints the token to stdout. The private signing key lives at `tools/licence_signing.key`.

**What is missing:** A record-keeping mechanism. Every issued licence should be auditable — when issued, to whom, expiry, tier, features. The milestone asks for a private GitHub repository as the record store.

### Recommended Addition: PyGithub

**PyGithub 2.x** is the standard Python library for the GitHub REST API v3. It supports creating/updating files in private repositories via `repo.create_file()` and `repo.update_file()`. The licence issuance script can append a JSONL record to a ledger file after signing.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `PyGithub` | `>=2.5.0` (latest 2.9.0) | Append licence issuance records to a private GitHub repo | Official GitHub REST API v3 client; typed; supports create/update file operations on private repos; no alternative has the same breadth of coverage and active maintenance |

**Pattern for ledger append:**

```python
from github import Github

g = Github(os.environ["GITHUB_TOKEN"])
repo = g.get_repo("axiom-laboratories/axiom-licence-ledger")

# Read existing ledger (JSONL)
try:
    f = repo.get_contents("ledger.jsonl")
    existing = f.decoded_content.decode()
    new_content = existing + json.dumps(record) + "\n"
    repo.update_file("ledger.jsonl", f"Add licence {licence_id}", new_content, f.sha)
except:
    repo.create_file("ledger.jsonl", f"Add licence {licence_id}", json.dumps(record) + "\n")
```

**Dependencies:** `PyGithub>=2.5.0` — install in the `tools/` venv only, not `puppeteer/requirements.txt`. This is an operator tooling dependency, not a server dependency.

**Authentication:** GitHub Personal Access Token with `repo` scope, stored in `GITHUB_TOKEN` env var. For CI use, a fine-grained PAT scoped to the ledger repo is preferable.

**Confidence:** HIGH — PyGithub is the standard library; the pattern above is a one-page script on top of the existing generate_licence.py.

---

## Feature 2: Docs Accuracy Validation

### What Needs Validating

Three categories of accuracy drift are possible:

1. **API endpoints** — docs reference routes that have been renamed or removed
2. **CLI commands** — `axiom-push` subcommands/flags documented but changed
3. **Compose file** — service names, env vars, port numbers described incorrectly

### Recommended Approach: httpx-based smoke test script (no new deps)

The server already has `httpx` in `requirements.txt`. A standalone script in `tools/` that:
1. Boots or connects to the running stack
2. Issues authenticated GET requests to every documented endpoint
3. Reports any non-2xx or 404

This is not a new library — it uses httpx that is already present. The script lives in `tools/validate_docs.py` and is invoked manually or in CI against a live stack.

For **CLI command validation**, run `axiom-push --help` and each documented subcommand with `subprocess.run` and assert return codes. No new library needed.

For **link checking in MkDocs source**, use `linkcheckmd`:

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `linkcheckmd` | `>=1.4.0` | Check all Markdown links in `docs/docs/` | Async, fast, works on raw `.md` files without building the site; actively maintained; does not require a running server for internal link checking |

**Do NOT use** `mkdocs-linkcheck` — it is abandoned (no releases in 12+ months per PyPI). `linkcheckmd` is the current community choice.

**Pattern:**

```bash
# In CI or as a pre-deploy check:
python -m linkcheckmd docs/docs/ --local
```

The `--local` flag checks only internal file-relative links (no HTTP requests). This catches broken cross-references in docs without needing the site built.

For **external link checking** (e.g. docs referencing GitHub URLs), run without `--local` but be tolerant of rate-limit false positives — external checks should be advisory, not blocking.

**Confidence:** MEDIUM — linkcheckmd is maintained and fits the use case; httpx pattern is HIGH confidence (existing library, existing pattern in the codebase).

---

## Feature 3: Screenshot Capture for Docs and Marketing Homepage

### What Already Exists

The `mop_validation/` repo uses Python Playwright (sync API) with `--no-sandbox` and JWT-via-localStorage auth. This already works in the environment.

### Recommended: Python Playwright (same pattern, moved to main repo `tools/`)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `playwright` (Python) | `>=1.58.0` (current: 1.58.0) | Capture dashboard screenshots for docs/homepage | Already proven in this environment; `--no-sandbox` workaround documented in CLAUDE.md; sync API is simpler for a one-shot screenshot script |

**No new library needed** — Playwright is already used and validated. The only addition is a screenshot script in `tools/capture_screenshots.py` that:
1. Starts the Docker stack (or connects to running stack)
2. Gets a JWT via the API (not UI login — avoid React form issues)
3. Injects JWT via `localStorage.setItem('mop_auth_token', token)`
4. Navigates to each dashboard view
5. Calls `page.screenshot(path=f"docs/docs/assets/screenshots/{name}.png", full_page=False)`

**Key constraints from CLAUDE.md (verified, do not change):**
- Always launch with `args=['--no-sandbox']`
- Auth: inject JWT via localStorage, not login form
- API login uses form-encoded data, not JSON
- localStorage key is `mop_auth_token`

**For screenshot dimensions:** Use `page.set_viewport_size({"width": 1280, "height": 800})` for consistent framing across all captures.

**Playwright version:** 1.58.0 released January 30, 2026. Requires `playwright install chromium` after pip install. No version bump needed from mop_validation — use the same version.

**Confidence:** HIGH — direct carry-over of working pattern from mop_validation.

---

## Feature 4: Node Validation Job Library

### What Needs Building

A library of signed reference jobs in `puppets/validation_jobs/` that operators can dispatch against their nodes to verify:
- Runtime: Python/Bash/PowerShell execution
- Volume mapping: read/write test files
- Network filtering: connectivity tests (should reach / should not reach)
- Resource limit enforcement: OOM/timeout triggers

### Stack: No New Libraries

All validation jobs are **script content** — Python, Bash, or PowerShell — dispatched via the existing `axiom-push job push` CLI or `POST /api/jobs`. The signing uses the existing `cryptography` + `PyJWT` toolchain.

The library is a directory of `.py`, `.sh`, and `.ps1` files plus a manifest. Each script is pre-signed and stored with its signature in a sidecar `.sig` file (same pattern as existing signed job dispatch).

| Component | Purpose | How |
|-----------|---------|-----|
| `puppets/validation_jobs/*.py` | Python runtime validation scripts | Standard Python, no imports beyond stdlib |
| `puppets/validation_jobs/*.sh` | Bash validation scripts | POSIX-compatible |
| `puppets/validation_jobs/*.ps1` | PowerShell validation scripts | pwsh 7 compatible |
| `tools/sign_validation_jobs.py` | Batch sign all validation scripts | Uses existing Ed25519 signing (`cryptography` already present) |
| `tools/dispatch_validation_suite.py` | Dispatch + monitor all validation jobs | Uses `httpx` (already present) |

**No new server-side dependencies.** The validation job scripts use only OS stdlib (Python `os`, `sys`, `subprocess`; Bash builtins; PowerShell core cmdlets). Resource limit tests deliberately allocate memory or sleep to trigger enforced limits — this is intentional and requires no external libraries.

**Confidence:** HIGH — straightforward script files dispatched via existing API.

---

## Feature 5: Custom Package Repo — Operator Docs and Validation Jobs

### What Already Exists

The `compose.server.yaml` already runs:
- `pypiserver/pypiserver:latest` on port 8080 — bare PyPI-compatible index, no auth, no mirroring
- `muccg/devpi:latest` on port 3141 — full devpi stack with PyPI mirror capability

The `mirror_service.py` downloads packages via `pip download` into a volume, and a Caddy sidecar serves them.

### What is Missing

1. **Operator documentation** — how to configure nodes to use the local PyPI mirror (`pip.conf`, `PIP_INDEX_URL`), how to upload internal packages, how to set up APT and PWSH mirrors
2. **Validation jobs** — signed Bash/Python/PowerShell jobs that verify connectivity to the local mirror, install a test package, and confirm the source is the internal mirror (not public PyPI)

### Stack Assessment for Package Mirror Validation Jobs

No new server-side library is needed. The validation jobs are scripts that run inside nodes:

**PyPI validation job (Python):**
```python
import subprocess, sys
# Verify pip uses local mirror
result = subprocess.run([sys.executable, '-m', 'pip', 'install',
    '--dry-run', '--index-url', 'http://pypi:8080/simple/', 'requests'],
    capture_output=True, text=True)
assert 'pypi:8080' in result.stdout or result.returncode == 0
```

**APT mirror validation (Bash):**
The existing `mirror_service.py` does not implement APT mirroring — it is stubbed out (see lines 33-38: only `_mirror_pypi` is called). APT mirroring was deferred in v7.0. For v15.0, **document only** — advise operators to use `apt-cacher-ng` as a separate sidecar if they need APT mirroring. Do not implement a new APT mirror service for this milestone.

**PowerShell (PSRepository) validation (PowerShell):**
PowerShell module repos use NuGet v2/v3 API. For air-gapped environments, `BaGet` (an open-source NuGet server) is the standard choice for hosting a local PSRepository. This is documentation guidance only for v15.0 — no new service is implemented.

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| PyPI mirror | Document devpi already in stack | devpi supports `--index-url` pip config; already running |
| APT mirror | Document apt-cacher-ng as operator-managed sidecar | Too large to bundle (200-300 GB full mirror); transparent proxy model is simpler |
| PWSH PSRepository | Document BaGet as operator choice | NuGet v2 API; well-documented; out of scope to add to compose |

---

## Recommended Stack Additions (New for v15.0)

### Core Technologies (New Installs Required)

| Technology | Version | Purpose | Why Recommended | Scope |
|------------|---------|---------|-----------------|-------|
| `PyGithub` | `>=2.5.0` | Append licence issuance records to private GitHub repo | Standard GitHub REST API v3 client; typed; actively maintained; covers create/update file on private repos | `tools/` venv only — NOT `puppeteer/requirements.txt` |
| `playwright` (Python) | `>=1.58.0` | Dashboard screenshot capture script | Already validated in environment; `--no-sandbox` pattern proven; 1.58.0 is current (Jan 2026) | `tools/` venv only |
| `linkcheckmd` | `>=1.4.0` | Markdown link validation across docs/ | Async, fast, no build step needed; `mkdocs-linkcheck` is abandoned | `docs/` venv or CI |

### No Changes Required

| Component | Why No Change Needed |
|-----------|---------------------|
| `cryptography` | Already in requirements.txt; Ed25519 keypair generation and signing already works |
| `PyJWT[crypto]>=2.7.0` | Already in requirements.txt; EdDSA JWT encoding already works |
| `httpx` | Already in requirements.txt; API smoke test scripts use it directly |
| `pytest` | Already in requirements.txt; validation test scripts can use it |
| `pypiserver` sidecar | Already in compose.server.yaml on port 8080 |
| `devpi` sidecar | Already in compose.server.yaml on port 3141 |
| Playwright browser binaries | Already installed in mop_validation environment; run `playwright install chromium` in the tools venv |

---

## Installation

```bash
# Tools venv (offline operator tooling — NOT the puppeteer server):
pip install PyGithub>=2.5.0
pip install playwright>=1.58.0
playwright install chromium  # download browser binary

# Docs venv (add to docs/requirements.txt):
# Current: mkdocs-material==9.7.5, mkdocs-swagger-ui-tag==0.8.0
pip install linkcheckmd>=1.4.0

# puppeteer/requirements.txt — NO CHANGES for v15.0
# All 5 features are tooling/scripting layer; server gets no new deps.
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `PyGithub` for ledger records | Raw `httpx` calls to GitHub API | Use raw httpx if you want zero new dependencies; PyGithub is less friction for file create/update with SHA management |
| `PyGithub` for ledger records | Git commit + push via subprocess | Use subprocess git if the operator machine already has git configured with credentials; avoids PyGithub dep entirely; slightly less portable |
| `linkcheckmd` for docs validation | `linkchecker-mkdocs` plugin | Use the MkDocs plugin if you want validation baked into `mkdocs build --strict`; linkcheckmd is simpler as a standalone CI step |
| Python Playwright for screenshots | Selenium / Puppeteer (JS) | Use Playwright; it is already validated in this environment with the exact workarounds needed (`--no-sandbox`, localStorage auth) |
| `apt-cacher-ng` (operator-managed) for APT | Bundling apt-mirror into compose | Never bundle a full APT mirror — 200-300 GB disk, complex sync scheduling; caching proxy is the right pattern for most operators |
| BaGet for PSRepository | Proget, Azure Artifacts, Nexus | BaGet is free, open-source, and self-hosted; Proget/Azure are commercial; for an air-gapped environment, BaGet is the minimum viable NuGet server |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mkdocs-linkcheck` | Abandoned — no PyPI releases in 12+ months | `linkcheckmd` |
| `python-jose` for licence JWT | Does not support EdDSA (Ed25519) — explicitly noted in `licence_service.py` | `PyJWT[crypto]>=2.7.0` (already installed) |
| New Ed25519 library (`PyNaCl`, standalone `ed25519`) | `cryptography` already provides `Ed25519PrivateKey`; adding a second Ed25519 library creates ambiguity | `cryptography.hazmat.primitives.asymmetric.ed25519` |
| MCP browser tool for screenshots | Crashes on every navigation in this environment (documented in CLAUDE.md) | Python Playwright with `--no-sandbox` |
| `pip download` + Caddy for APT mirroring | `pip download` only works for PyPI packages, not `.deb` packages — type mismatch | `apt-cacher-ng` sidecar (transparent proxy, no pre-download needed) |
| New dependencies in `puppeteer/requirements.txt` for v15.0 features | All 5 features are operator tooling, not server features; adding tooling deps to the server image bloats it | Separate `tools/` venv |

---

## Stack Patterns by Variant

**If operator is air-gapped (no GitHub access):**
- Skip `PyGithub` for ledger; write JSONL records to a local file instead
- The `generate_licence.py` already works offline; add a `--ledger-file` flag as fallback

**If operator wants APT mirroring (not just PyPI):**
- Add `apt-cacher-ng` as a sidecar in `compose.server.yaml` (port 3142 conventional)
- Document `Acquire::http::Proxy "http://apt-cacher:3142"` in `/etc/apt/apt.conf.d/01proxy` on nodes
- No code change to the Axiom server required

**If operator wants PSRepository mirroring:**
- Deploy BaGet (`docker run --rm -p 5000:80 loicsharma/baget`) as a standalone sidecar
- Register with `Register-PSRepository -Name AxiomInternal -SourceLocation http://baget:5000/v3/index.json`

**If screenshot capture needs to run in CI (headless, no display):**
- Playwright already supports headless Chromium; `--no-sandbox` is required on Linux CI
- Add `playwright install --with-deps chromium` step to GitHub Actions screenshot job

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `PyGithub>=2.5.0` | Python 3.8+, GitHub API v3 | v2.x dropped Python 3.7; current project uses 3.10+ so no issue |
| `playwright>=1.58.0` | Python 3.9+, Chromium 132 | Requires separate `playwright install chromium` after pip install; browser binary is ~300 MB |
| `linkcheckmd>=1.4.0` | Python 3.7+, aiohttp | Async; fast; no special system deps |
| `cryptography==46.0.6` | Python 3.8+, OpenSSL 1.1+ | Current version; already in requirements.txt; no change needed |
| `PyJWT[crypto]>=2.7.0` | `cryptography>=3.4` | EdDSA support added in 2.4.0; `>=2.7.0` pin already in requirements.txt |

---

## Sources

- Direct codebase analysis: `tools/generate_licence.py`, `puppeteer/requirements.txt`, `puppeteer/compose.server.yaml`, `puppeteer/agent_service/services/mirror_service.py`, `puppeteer/agent_service/services/licence_service.py`, `.github/workflows/ci.yml`, `docs/requirements.txt` — current state (HIGH confidence)
- [PyJWT 2.12.1 documentation — Digital Signature Algorithms](https://pyjwt.readthedocs.io/en/stable/algorithms.html) — EdDSA/Ed25519 support confirmed (HIGH confidence)
- [playwright PyPI — version 1.58.0](https://pypi.org/project/playwright/) — current version January 2026 (HIGH confidence)
- [Playwright Python docs — screenshots](https://playwright.dev/python/docs/screenshots) — screenshot API confirmed (HIGH confidence)
- [PyGithub PyPI — version 2.9.0](https://pypi.org/project/PyGithub/) — current version (HIGH confidence)
- [cryptography PyPI — version 46.0.6](https://pypi.org/project/cryptography/) — current version March 2026 (HIGH confidence)
- [linkcheckmd PyPI](https://pypi.org/project/linkcheckmd/) — active; mkdocs-linkcheck abandoned (MEDIUM confidence — PyPI maintenance signal)
- [devpi-server documentation](https://pypi.org/project/devpi-server/) — PyPI mirror and private index capabilities confirmed (HIGH confidence)
- CLAUDE.md project instructions — `--no-sandbox`, localStorage auth, form-encoded login patterns (HIGH confidence — project source of truth)

---

*Stack research for: v15.0 Operator Readiness (licence generation tooling, docs accuracy validation, screenshot capture, node validation job library, custom package repo validation)*
*Researched: 2026-03-28*

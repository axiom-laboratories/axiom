# Phase 86: Docs Accuracy Validation — Research

**Status:** RESEARCH COMPLETE
**Date:** 2026-03-29

---

## What I Need to Know to Plan This Phase Well

### Phase Goal
Build two scripts: `tools/generate_openapi.py` (populates `docs/docs/api-reference/openapi.json` from a live Docker stack) and `tools/validate_docs.py` (cross-references docs markdown against the committed OpenAPI snapshot, CLI subcommands in `mop_sdk/cli.py`, and env var names in the codebase). The validator exits 1 on any WARN or FAIL — usable as a CI gate without a running stack.

---

## Codebase Survey

### What Exists Today

| File | Status | Relevance |
|------|--------|-----------|
| `tools/capture_screenshots.py` | Live, working | Pattern template for `generate_openapi.py`: `--url` flag, secrets loading, `REPO_ROOT` path anchor, error handling |
| `tools/__init__.py` | Exists | `tools/` is already a Python package location |
| `docs/docs/api-reference/openapi.json` | Stub (218 bytes, no paths) | Target of `generate_openapi.py`; validator must check for empty `paths: {}` and exit 2 |
| `mop_sdk/cli.py` | Live | Source of truth for CLI subcommands: `login`, `job push`, `job create`, `key generate`, `init` |
| `.github/workflows/ci.yml` | Live | Add a `docs-validate` job here |

### Docs Markdown Files Surveyed

All markdown lives in `docs/docs/**/*.md`. Subdirectories:
- `getting-started/` — install.md, enroll-node.md, first-job.md
- `feature-guides/` — axiom-push.md, jobs.md, job-scheduling.md, foundry.md, nodes.md, rbac.md, rbac-reference.md, oauth.md
- `runbooks/` — jobs.md, nodes.md, foundry.md, node-validation.md, package-mirrors.md, faq.md, index.md
- `security/` — mtls.md
- `developer/` — architecture.md
- `api-reference/` — index.md, openapi.json (not markdown, excluded from scan)
- `quick-ref/index.md`, `index.md`, `licensing.md`

### API Routes Currently In Docs

Sampled from `grep "GET /\|POST /\|PUT /\|DELETE /\|PATCH /"` across docs:

| Route | File |
|-------|------|
| `GET /api/features` | licensing.md, install.md |
| `GET /api/licence` | licensing.md |
| `GET /api/health/scheduling?window=24h` | feature-guides/job-scheduling.md |
| `POST /admin/roles/{role}/permissions` | feature-guides/rbac-reference.md |
| `DELETE /admin/roles/{role}/permissions/{permission}` | feature-guides/rbac-reference.md |
| `POST /auth/device` | feature-guides/oauth.md |
| `POST /auth/device/token` | feature-guides/oauth.md |
| `POST /api/enrollment-tokens` | getting-started/enroll-node.md |
| `GET /system/crl.pem` | security/mtls.md, developer/architecture.md |
| `POST /api/enroll` | security/mtls.md, developer/architecture.md |
| `POST /heartbeat` | developer/architecture.md |
| `POST /work/result` | developer/architecture.md |
| `POST /work/pull` | developer/architecture.md |
| `POST /triggers/{slug}` | developer/architecture.md |
| `POST /signatures` | developer/architecture.md |
| `POST /jobs` | developer/architecture.md |
| `GET /api/verification-key` | runbooks/jobs.md |

All of these must be matched against the populated `openapi.json`. The `/api/verification-key` route may not be in the spec — worth flagging during validation.

### CLI Subcommands In Docs vs Registered Subcommands

**Registered in `mop_sdk/cli.py` (from direct read):**
- Top-level: `login`, `job`, `key`, `init`
- Under `job`: `push`, `create`
- Under `key`: `generate`

**Full command tokens documented:**
- `axiom-push login` — feature-guides/axiom-push.md
- `axiom-push job push` — axiom-push.md, runbooks/node-validation.md, runbooks/package-mirrors.md
- `axiom-push job create` — axiom-push.md (indirectly via `create` subparser docs)
- `axiom-push key generate` — axiom-push.md
- `axiom-push init` — axiom-push.md

No undocumented subcommand references found in the current docs scan.

### Env Var Names In Docs vs Codebase

**Env vars found in backtick spans across docs (sampled):**

| Env Var | Docs File | Exists in Codebase? |
|---------|-----------|---------------------|
| `AGENT_URL` | runbooks/jobs.md, faq.md | Yes — node.py, main.py |
| `JOIN_TOKEN` | faq.md | Yes — node.py |
| `ADMIN_PASSWORD` | faq.md | Yes — main.py |
| `EXECUTION_MODE` | faq.md, runbooks/faq.md | Yes — runtime.py, node.py |
| `JOB_MEMORY_LIMIT` | runbooks/node-validation.md | Yes — node.py |
| `JOB_CPU_LIMIT` | runbooks/node-validation.md | Yes — node.py |
| `AXIOM_VOLUME_PATH` | runbooks/node-validation.md | Likely job env var, not codebase var — WARN expected |
| `AXIOM_BLOCKED_HOST` | runbooks/node-validation.md | Likely job env var, not codebase var — WARN expected |
| `AXIOM_LICENCE_KEY` | licensing.md | Yes — licence_service.py |
| `PYPI_MIRROR_URL` | runbooks/package-mirrors.md | Yes — mirror_service.py, smelter_router.py |
| `SECRET_KEY` | (inferred from CLAUDE.md context) | Yes — auth.py |
| `ENCRYPTION_KEY` | (inferred) | Yes — security.py |
| `DATABASE_URL` | (inferred) | Yes — db.py |

**Key insight:** Job-specific env vars (`AXIOM_VOLUME_PATH`, `AXIOM_BLOCKED_HOST`) are passed as job environment payload, not set in source code — the validator will WARN on these. This is expected behaviour per the CONTEXT.md decision (env var WARNs block CI, so the validator may need a documented exclusion mechanism or these will appear as known WARNs). This is a planning decision to resolve.

---

## Implementation Design

### `tools/generate_openapi.py`

**Pattern:** Clone of `capture_screenshots.py` structure.

```python
REPO_ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    args = parser.parse_args()

    r = requests.get(f"{args.url}/openapi.json", timeout=10)
    r.raise_for_status()
    spec = r.json()

    out_path = REPO_ROOT / "docs/docs/api-reference/openapi.json"
    out_path.write_text(json.dumps(spec, indent=2))
    print(f"Written to {out_path}")
    print(f"Routes: {len(spec.get('paths', {}))}")

if __name__ == "__main__":
    main()
```

- No auth required (`/openapi.json` is unauthenticated)
- No secrets loading needed
- Stdlib only: `json`, `argparse`, `pathlib`, `sys`; plus `requests`
- Default URL: `http://localhost:8080` (Caddy proxy, per CLAUDE.md)

### `tools/validate_docs.py`

**High-level flow:**

```
1. Load openapi.json → check for empty paths → exit 2 if stub
2. Scan docs/**/*.md for:
   a. HTTP method + path patterns → validate against openapi.json paths+methods
   b. axiom-push <subcommand> patterns → validate against mop_sdk/cli.py parser
   c. Backtick env var names → validate by searching source dirs
3. Print PASS/WARN/FAIL per item with file:line
4. Exit 0 (all PASS), 1 (any WARN/FAIL), or 2 (stub/missing snapshot)
```

**Extraction regexes:**

```python
# API routes — both inline prose and code blocks
ROUTE_RE = re.compile(
    r'\b(GET|POST|PUT|DELETE|PATCH)\s+(/(?:api|admin|auth|system|work|jobs|nodes|signatures|job-definitions|config|triggers)[^\s`\'\"]*)',
    re.IGNORECASE
)

# CLI subcommands — exact patterns
CLI_RE = re.compile(r'\baxiom-push\s+(\w+(?:\s+\w+)?)')

# Env vars — backtick-wrapped, all-caps, 3+ chars, contains underscore
ENV_RE = re.compile(r'`([A-Z][A-Z0-9_]{2,})`')
```

**CLI subcommand extraction from `mop_sdk/cli.py`:**

Rather than importing the module (which has `cryptography` dependency), parse the file statically using `ast` or regex to extract `add_parser("...")` calls. This keeps `validate_docs.py` stdlib-only.

```python
def get_registered_subcommands() -> set[str]:
    cli_path = REPO_ROOT / "mop_sdk/cli.py"
    source = cli_path.read_text()
    # Extract all add_parser("name") calls
    names = re.findall(r'add_parser\(["\'](\w+)["\']', source)
    return set(names)
```

Registered: `{'login', 'job', 'key', 'init', 'push', 'create', 'generate'}`

Validation logic for CLI: extract `axiom-push <token>` or `axiom-push <token> <token>` from docs, check if `<token>` (or `<token> <token>`) is registered.

**Env var source search:**

```python
SEARCH_DIRS = ["puppeteer", "puppets", "mop_sdk"]
EXCLUDE_DIRS = {"venv", ".venv", "node_modules", ".git", "__pycache__", "dist", "build"}

def var_in_source(var_name: str) -> bool:
    for base in SEARCH_DIRS:
        for py_file in (REPO_ROOT / base).rglob("*.py"):
            if any(ex in py_file.parts for ex in EXCLUDE_DIRS):
                continue
            if var_name in py_file.read_text():
                return True
    return False
```

**Output format:**

```
PASS   GET /api/features      docs/docs/licensing.md:14
PASS   POST /auth/device      docs/docs/feature-guides/oauth.md:23
FAIL   GET /api/verification-key  docs/docs/runbooks/jobs.md:87  (not in openapi.json)
WARN   AXIOM_VOLUME_PATH      docs/docs/runbooks/node-validation.md:45  (not found in source)
PASS   axiom-push job push    docs/docs/runbooks/node-validation.md:12

Summary: 14 PASS, 1 WARN, 1 FAIL
```

**Exit codes:**
- `0` — all PASS
- `1` — any WARN or FAIL
- `2` — snapshot missing or stub (no paths in spec)

### CI Integration

Add a `docs-validate` job to `.github/workflows/ci.yml`:

```yaml
docs-validate:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Install requests
      run: pip install requests
    - name: Validate docs accuracy
      run: python tools/validate_docs.py
```

No live stack needed — the committed `openapi.json` is the snapshot.

---

## Known False Positive Issue — Job Env Vars

`AXIOM_VOLUME_PATH` and `AXIOM_BLOCKED_HOST` are job payload env vars (passed as `env:` in the job dispatch JSON), not Python source constants. The validator will WARN on these. Options:

1. **Accept the WARNs** — treat as documentation debt, fix by making these searchable (e.g., define them as constants in a job script file)
2. **Allowlist in validator** — `--ignore-vars AXIOM_VOLUME_PATH,AXIOM_BLOCKED_HOST` flag
3. **Widen search scope** — also scan `tools/example-jobs/` for env var names

Option 3 (widen search to `tools/example-jobs/`) is the cleanest: these vars appear in the example job scripts themselves. This eliminates false positives without any allowlist management.

**Decision for planner:** Use option 3 — add `tools/example-jobs/` to the env var search scope.

---

## Plan Structure

Two plans needed:

**Plan 86-01: `generate_openapi.py` + `validate_docs.py` scripts**
- Task 1: Write `tools/generate_openapi.py`
- Task 2: Write `tools/validate_docs.py`
- Task 3: Run `generate_openapi.py` against live stack, commit populated `openapi.json`
- Task 4: Run `validate_docs.py` against committed snapshot, fix any real FAILs found

**Plan 86-02: CI integration**
- Task 1: Add `docs-validate` job to `.github/workflows/ci.yml`
- Task 2: Verify CI passes on main (or push a PR to trigger)

Wave assignment:
- Wave 1: Plan 86-01 Tasks 1–2 (scripts written, no external deps)
- Wave 2: Plan 86-01 Tasks 3–4 (requires live stack for generate step)
- Wave 3: Plan 86-02 Tasks 1–2 (CI config, depends on script existing)

---

## Test Strategy

This phase produces two Python scripts and a CI config change. No backend code changes.

**Automated checks:**
- Syntax: `python -c "import ast; ast.parse(open('tools/validate_docs.py').read())"`
- Smoke run (no live stack): `python tools/validate_docs.py` — should read committed `openapi.json` and scan docs
- CI: the new `docs-validate` job itself becomes the regression check

**Backend regression:** `cd puppeteer && pytest tests/ -q` — no new backend code, should pass unchanged.

---

## Validation Architecture

### Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing backend suite) + direct script invocation |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds (pytest) + ~5 seconds (validate_docs.py) |

### Validation Approach

1. **Backend regression** — `cd puppeteer && pytest tests/ -q` after each plan (no backend changes expected)
2. **Script syntax check** — `python -m py_compile tools/validate_docs.py tools/generate_openapi.py`
3. **Validator smoke run** — `python tools/validate_docs.py` produces output without crashing; exits 0 after snapshot populated
4. **CI workflow syntax** — `yamllint .github/workflows/ci.yml` (or push to branch to trigger)

### Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Notes |
|---------|------|------|-------------|-----------|-------------------|-------|
| 86-01-01 | 01 | 1 | DOC-01 | syntax | `python -m py_compile tools/generate_openapi.py` | File created |
| 86-01-02 | 01 | 1 | DOC-01,DOC-02 | syntax | `python -m py_compile tools/validate_docs.py` | File created |
| 86-01-03 | 01 | 2 | DOC-01 | manual | `python tools/generate_openapi.py --url http://localhost:8080` | Requires live stack |
| 86-01-04 | 01 | 2 | DOC-01,DOC-02 | smoke | `python tools/validate_docs.py` | Should exit 0 after snapshot populated |
| 86-02-01 | 02 | 3 | DOC-03 | file | `test -f .github/workflows/ci.yml && grep -q docs-validate .github/workflows/ci.yml` | CI job added |
| 86-02-02 | 02 | 3 | DOC-03 | manual | Push branch to GitHub and verify CI passes | Requires GitHub Actions |

### Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `generate_openapi.py` populates openapi.json with real routes | DOC-01 | Requires live Docker stack | Run against `http://localhost:8080`, verify `openapi.json` has >0 paths |
| `validate_docs.py` produces correct PASS/WARN/FAIL output | DOC-01,DOC-02 | Requires populated snapshot | Run `python tools/validate_docs.py` and review output for accuracy |
| CI gate blocks a PR that introduces a bad route reference | DOC-03 | Requires GitHub Actions run | Add a fake `GET /api/nonexistent` to a docs file, open PR, verify CI fails |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Regex extracts too many false positives for env vars | Medium | Use conservative pattern: backtick-wrapped, 3+ chars, contains underscore |
| Route patterns in Mermaid/diagram blocks get extracted | Low | Mermaid syntax `-->|"POST /foo"|` will match — acceptable, route still needs to exist |
| openapi.json query-string params (`?window=24h`) fail path match | Medium | Strip query string before matching: `re.sub(r'\?.*', '', path)` |
| Job env vars AXIOM_* produce WARNs blocking CI | Medium | Widen search to `tools/example-jobs/` — they appear there; eliminates false positives |
| `/api/verification-key` route exists in docs but may not be in spec | Low | If missing from spec, it's a real FAIL — fix docs or add route to spec |

---

## RESEARCH COMPLETE

Phase 86 is well-scoped. Two plans:
- Plan 86-01: Write `generate_openapi.py` + `validate_docs.py`, run against live stack, commit populated snapshot
- Plan 86-02: Add `docs-validate` CI job

One planning decision captured: widen env var search to `tools/example-jobs/` to eliminate `AXIOM_VOLUME_PATH` / `AXIOM_BLOCKED_HOST` false positives.

No blocking unknowns. Proceed to planning.

# Phase 82: Licence Tooling - Research

**Researched:** 2026-03-28
**Domain:** Ed25519 JWT licence issuance CLI, GitHub API file commits, gitleaks CI secret scanning, private repo structure
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### YAML audit ledger
- Format: one YAML file per issuance — `licenses/issued/<customer-id>-<jti>.yml`
- Flat directory (not nested per customer) — customer-id prefix makes customer records easy to glob
- American spelling: `licenses/` not `licences/`
- Each YAML contains the full JWT payload fields: `jti`, `customer_id`, `issued_to`, `contact_email`, `tier`, `node_limit`, `features`, `grace_days`, `issued_at`, `expiry`, `issued_by`
- The YAML also embeds the full licence blob (JWT token) so it can be re-delivered without re-issuing
- Companion `list_licences.py` script reads all YAMLs and outputs a human-readable table (git log = immutable audit trail; script = query layer)

#### Remote commit workflow
- Default: script calls the **GitHub API** to create/commit the YAML file in `axiom-laboratories/axiom-licenses`
- Requires `GITHUB_TOKEN` env var (no local clone needed)
- Commit message format: `feat(licenses): issue <customer-id> <tier> exp <expiry>`
  - e.g. `feat(licenses): issue acme-corp ee exp 2027-01-01`
- `--no-remote` flag: writes YAML to a local file **and** prints both the YAML record and the JWT token to stdout
- Air-gap compatibility is not a design priority — this is an internal dev team tool

#### Key rotation
- Generate a fresh Ed25519 keypair as part of this phase
- New private key lives at `axiom-licenses/keys/licence.key` in the private repo
- New public key replaces `_LICENCE_PUBLIC_KEY_PEM` in `puppeteer/agent_service/services/licence_service.py`
- No backwards compatibility with the old key — no live customer licences exist
- Safe to rotate immediately

#### Public repo cleanup
- Delete `tools/generate_licence.py` entirely — replaced by `issue_licence.py` in the private repo
- `tools/licence_signing.key` is not git-tracked (covered by `*.key` in `.gitignore`) — no git history to purge
- `issue_licence.py` lives only in the private `axiom-laboratories/axiom-licenses` repo

#### `issue_licence.py` CLI interface
- Args: `--customer`, `--tier`, `--nodes`, `--expiry YYYY-MM-DD`, `--features f1,f2`
- Key source: `AXIOM_LICENCE_SIGNING_KEY` env var or `--key` path arg — no silent default path, fail with clear error if neither provided
- Outputs licence JWT to stdout; commits YAML record via GitHub API by default
- `--no-remote` flag for local-only operation

#### CI guard
- Use `gitleaks/gitleaks-action@v2` (marketplace action) — free for this public repo
- Add as a step in existing `ci.yml` workflow
- Include `.gitleaks.toml` with allowlist entries for known dummy/test values:
  - `ci-dummy-key` (API_KEY in CI env)
  - `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=` (ENCRYPTION_KEY in CI env)
- Scans git history and working tree on every push/PR

### Claude's Discretion
- Exact `.gitleaks.toml` rule tuning and allowlist entries beyond the known dummies
- `list_licences.py` output formatting (table columns, sort order)
- `issue_licence.py` `--issued-by` default (git config user.name vs explicit arg only)
- Private repo directory structure beyond `licenses/issued/` and `keys/`

### Deferred Ideas (OUT OF SCOPE)
- GitHub Actions `workflow_dispatch` in the private repo for web-based licence issuance — future phase
- Dedicated service with customer DB, renewal tracking, and on-demand issuance API — long-term
- Licence renewal reminders / expiry notifications — future phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIC-01 | Operator can migrate the licence signing private key out of the public repo into a private `axiom-licences` repo, with key rotation if needed | Key rotation: generate fresh Ed25519 keypair using existing `generate_keypair()` pattern; write private key to private repo; update `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py`; delete `tools/generate_licence.py` |
| LIC-02 | CI guard prevents PEM private key content from being committed to the public repo | `gitleaks/gitleaks-action@v2` detects `-----BEGIN PRIVATE KEY-----` and `-----BEGIN EC PRIVATE KEY-----` patterns out-of-box; `.gitleaks.toml` allowlists cover known CI dummy values |
| LIC-03 | Operator can run `issue_licence.py --customer X --tier EE --nodes N --expiry YYYY-MM-DD` to generate a base64 licence blob offline | Full working template in `tools/generate_licence.py`; same `PyJWT` + `cryptography` deps; `--no-remote` provides offline/`--key`-path mode |
| LIC-04 | Each issued licence is recorded as a YAML file in `axiom-licences/licences/issued/` and committed as an audit trail | GitHub Contents API `PUT /repos/{owner}/{repo}/contents/{path}` with base64-encoded YAML body; `pyyaml` for serialisation; commit message format locked |
| LIC-05 | `issue_licence.py` supports `--no-remote` flag for air-gapped operators (writes record to local file instead of GitHub) | `--no-remote` writes YAML to local file and prints JWT + YAML to stdout; skips GitHub API call entirely |
</phase_requirements>

---

## Summary

Phase 82 is a **Python CLI tooling phase** — no backend API changes, no frontend work. The deliverables split across two repositories: the private `axiom-laboratories/axiom-licenses` repo (receives `issue_licence.py`, `list_licences.py`, key material) and the public `master_of_puppets` repo (updated `licence_service.py` public key, deleted `tools/generate_licence.py`, added CI gitleaks guard).

The core signing logic already exists and is proven in `tools/generate_licence.py`. The new `issue_licence.py` adapts that code with three additions: GitHub API commit integration (standard `requests.put` to the GitHub Contents endpoint), YAML audit record generation (`pyyaml`), and a strict key-source check (no silent default path). The YAML record embeds the full JWT so the licence can be re-delivered without re-signing.

The CI guard uses `gitleaks/gitleaks-action@v2`, which is free for public repositories and requires only `GITHUB_TOKEN` (automatically available). It detects `-----BEGIN PRIVATE KEY-----` patterns out-of-box. A `.gitleaks.toml` at the repo root allowlists the two known CI dummy values that would otherwise cause false positives.

**Primary recommendation:** Build `issue_licence.py` as a direct evolution of `tools/generate_licence.py`, add the GitHub Contents API call as the commit layer, and configure gitleaks-action as a standalone job in `ci.yml`. Wave 1 handles the private repo scaffold and key rotation; Wave 2 handles the public repo cleanup and CI guard.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `PyJWT[crypto]` | >=2.7.0 (already pinned) | EdDSA JWT encode/decode | Already in project `requirements.txt`; only PyJWT 2.7+ supports `EdDSA` algorithm |
| `cryptography` | (already in project) | Ed25519 key generation + PEM serialisation | Already in project; `Ed25519PrivateKey.generate()`, PKCS8/PEM round-trip proven |
| `pyyaml` | any recent | YAML audit record serialisation | Available in system Python; NOT in `puppeteer/requirements.txt` — must add to private repo's `requirements.txt` |
| `requests` | any recent | GitHub Contents API PUT call | Standard HTTP client; avoid `urllib` for multiline JSON body |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `argparse` | stdlib | CLI argument parsing | Already used in `generate_licence.py` |
| `base64` | stdlib | Encode YAML body for GitHub API | Required by GitHub Contents API (content must be base64-encoded) |
| `subprocess` / `gitpython` | stdlib / optional | `--issued-by` default from git config | Only if `--issued-by` defaults to `git config user.name`; otherwise not needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` for GitHub API | `httpx`, `gh` CLI | `requests` is simpler for a single PUT call; no async needed; already widely installed |
| `pyyaml` | `ruamel.yaml` | `ruamel.yaml` preserves comments/order but is overkill here; `pyyaml.dump(..., default_flow_style=False)` is sufficient |
| Inline `base64.b64encode` | `base64.encodebytes` | Use `base64.b64encode(content).decode()` — GitHub API requires standard base64, not MIME-chunked |

**Installation for private repo:**
```bash
pip install PyJWT[crypto] cryptography pyyaml requests
```

---

## Architecture Patterns

### Recommended Private Repo Structure
```
axiom-laboratories/axiom-licenses/
├── keys/
│   └── licence.key         # Ed25519 private key PEM (PKCS8, chmod 600)
├── licenses/
│   └── issued/
│       └── <customer-id>-<jti>.yml   # one file per issuance
├── tools/
│   ├── issue_licence.py    # CLI: sign + commit YAML
│   └── list_licences.py    # CLI: query/display issued licences
├── requirements.txt
└── README.md
```

### Pattern 1: Key Source Resolution (no silent default)
**What:** Resolve signing key from env var or explicit `--key` path; fail immediately with a clear error if neither is provided.
**When to use:** Always — this is the primary security requirement (LIC-01, LIC-03).
```python
import os
import sys

def resolve_key(args):
    key_source = args.key or os.getenv("AXIOM_LICENCE_SIGNING_KEY")
    if not key_source:
        sys.exit(
            "Error: no signing key provided. "
            "Set AXIOM_LICENCE_SIGNING_KEY env var or pass --key <path>."
        )
    path = Path(key_source)
    if not path.exists():
        sys.exit(f"Error: key file not found: {path}")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)
```

### Pattern 2: YAML Audit Record Generation
**What:** Build the audit record dict and serialise with `pyyaml` (block style).
**When to use:** After every successful `jwt.encode` call.
```python
import yaml
import datetime

def build_audit_record(payload: dict, token: str, issued_by: str) -> dict:
    return {
        "jti": payload["licence_id"],           # maps to `jti` field name
        "customer_id": payload["customer_id"],
        "issued_to": payload["issued_to"],
        "contact_email": payload.get("contact_email", ""),
        "tier": payload["tier"],
        "node_limit": payload["node_limit"],
        "features": payload.get("features", []),
        "grace_days": payload.get("grace_days", 30),
        "issued_at": datetime.datetime.utcfromtimestamp(payload["iat"]).date().isoformat(),
        "expiry": datetime.datetime.utcfromtimestamp(payload["exp"]).date().isoformat(),
        "issued_by": issued_by,
        "licence_blob": token,  # full JWT for re-delivery
    }

yaml_text = yaml.dump(record, default_flow_style=False, sort_keys=False)
```

### Pattern 3: GitHub Contents API Commit
**What:** Create a new file in the private repo via `PUT /repos/{owner}/{repo}/contents/{path}`.
**When to use:** Default mode (when `--no-remote` is NOT set).
```python
import base64
import requests

GITHUB_API = "https://api.github.com"
OWNER = "axiom-laboratories"
REPO = "axiom-licenses"

def commit_yaml_to_github(
    customer_id: str,
    jti: str,
    yaml_text: str,
    tier: str,
    expiry: str,
    github_token: str,
) -> None:
    path = f"licenses/issued/{customer_id}-{jti}.yml"
    url = f"{GITHUB_API}/repos/{OWNER}/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {
        "message": f"feat(licenses): issue {customer_id} {tier} exp {expiry}",
        "content": base64.b64encode(yaml_text.encode()).decode(),
    }
    resp = requests.put(url, headers=headers, json=body)
    resp.raise_for_status()
```

Note: `sha` is NOT needed when creating a new file — only when updating an existing file. Since each YAML has a unique `<customer-id>-<jti>.yml` filename, there should never be a SHA conflict on creation.

### Pattern 4: `--no-remote` Local Fallback
**What:** Write YAML to a local file and print both YAML and JWT to stdout; skip GitHub API entirely.
**When to use:** When `--no-remote` flag is passed.
```python
if args.no_remote:
    local_path = Path(f"{customer_id}-{jti}.yml")
    local_path.write_text(yaml_text)
    print("--- YAML RECORD ---", file=sys.stderr)
    print(yaml_text, file=sys.stderr)
    print("--- LICENCE JWT ---")
    print(token)
    return
```

### Pattern 5: `list_licences.py` Table Display
**What:** Glob all `licenses/issued/*.yml`, parse each, display as formatted table.
**When to use:** Operator audit queries.
```python
from pathlib import Path
import yaml

records = []
for yml_file in sorted(Path("licenses/issued").glob("*.yml")):
    record = yaml.safe_load(yml_file.read_text())
    records.append(record)

# Print tabulated output sorted by expiry (descending) or customer_id
# Column order: customer_id, tier, node_limit, issued_at, expiry, issued_by
```

### Pattern 6: gitleaks-action GitHub Actions Step
**What:** Add gitleaks scanning to CI as a standalone job.
**When to use:** Every push and PR to `main`.
```yaml
# Add to .github/workflows/ci.yml
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # full history for git-log scan
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Anti-Patterns to Avoid
- **Hardcoding `--key` default path inside the script**: The entire security point of LIC-01 is removing silent key defaults. Never fall back to a relative path like `tools/licence_signing.key`.
- **Using `json.dumps` for YAML**: Use `pyyaml.dump()`; YAML is a superset of JSON but pyyaml produces more readable block format.
- **Committing the private key PEM via the GitHub API**: The private repo should receive the key via `scp`/manual copy — not via a commit created by `issue_licence.py` itself.
- **Running `git commit` locally**: The design uses the GitHub Contents API, which requires no local clone. Do not use `subprocess` git calls — they would require a clone.
- **Omitting `fetch-depth: 0`** from the gitleaks checkout step: Without full history, gitleaks cannot scan past commits for leaked secrets.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret scanning in CI | Custom grep/regex step | `gitleaks/gitleaks-action@v2` | Gitleaks has 150+ rules covering PEM keys, API tokens, AWS keys, etc. A custom grep only catches the exact patterns you think of. |
| GitHub API authentication | OAuth flow / app installation | `GITHUB_TOKEN` env var (PAT or Actions token) | Simple PAT with `contents:write` scope on the private repo is sufficient for a CLI tool. |
| YAML serialisation | f-string templates | `pyyaml.dump()` | YAML is whitespace-sensitive; f-string templates will produce invalid YAML on any field containing `:`, `#`, or newlines. |
| JWT EdDSA signing | Custom base64url + signature | `jwt.encode(..., algorithm="EdDSA")` | PyJWT handles all header/payload/signature encoding including the non-standard EdDSA `crv` claim. |

**Key insight:** The GitHub Contents API for single-file commits is simple (one PUT, no clone) — no need for `gitpython` or `pygithub` libraries for this use case.

---

## Common Pitfalls

### Pitfall 1: `--customer` vs `--customer-id` arg name collision
**What goes wrong:** The existing `generate_licence.py` uses `--customer-id` (argparse stores as `args.customer_id`), but the CONTEXT.md specifies `--customer` as the CLI arg. Using `--customer` with `dest="customer"` means `args.customer`, not `args.customer_id`.
**Why it happens:** New arg names copied from CONTEXT.md without adjusting existing code patterns.
**How to avoid:** Use `--customer` as the CLI flag; store with default dest (`args.customer`). Update YAML record builder to use `args.customer` not `args.customer_id`.
**Warning signs:** `AttributeError: Namespace object has no attribute 'customer_id'` at runtime.

### Pitfall 2: `jti` field name vs `licence_id`
**What goes wrong:** The JWT payload uses `"licence_id"` as the key (from `generate_licence.py`), but the CONTEXT.md YAML record specifies `jti` as the field name. These are different: `jti` is the JWT standard registered claim; `licence_id` is the project-specific payload field.
**Why it happens:** The JWT payload was designed before the JWT `jti` standard was considered.
**How to avoid:** The YAML record should use `jti` as its field name (per CONTEXT.md). Populate it from `payload["licence_id"]`. Optionally also add `jti` to the JWT payload itself for standards compliance — but this is discretionary.
**Warning signs:** YAML file has `licence_id:` instead of `jti:`, breaking `list_licences.py` column display.

### Pitfall 3: GitHub Contents API returns 422 when file already exists without `sha`
**What goes wrong:** If the operator issues a licence for the same customer twice on the same day and somehow gets the same UUID (should not happen — `uuid4()` is effectively unique), the PUT will fail with 422 because updating an existing file requires the `sha` of the current blob.
**Why it happens:** `uuid4()` collision is astronomically unlikely but the API is unforgiving when it does happen.
**How to avoid:** Each `jti` is a fresh `uuid.uuid4()`, so filenames are unique. No mitigation needed beyond documenting that the error message is "SHA is required" if a 422 is ever seen.
**Warning signs:** HTTP 422 response from GitHub API with message containing "sha".

### Pitfall 4: gitleaks false positives on CI dummy values
**What goes wrong:** `ci.yml` already sets `API_KEY: ci-dummy-key` and `ENCRYPTION_KEY: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`. Gitleaks will flag these as leaked secrets and fail the CI build.
**Why it happens:** Gitleaks scans the full git history including CI workflow files.
**How to avoid:** Add `.gitleaks.toml` at repo root with `[[allowlists]]` covering both exact values:
```toml
[[allowlists]]
description = "Known CI dummy values"
regexTarget = "match"
regexes = [
  '''ci-dummy-key''',
  '''AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=''',
]
```
**Warning signs:** Gitleaks step fails immediately on first run citing `ci.yml`.

### Pitfall 5: `licence_signing.key` on disk but not in git
**What goes wrong:** The old private key lives at `tools/licence_signing.key`. It is gitignored (`*.key`). But the file still exists on disk. After phase completion, the old key should be deleted from disk to prevent accidental use — but no git purge is needed.
**Why it happens:** `.gitignore` prevents git tracking but does not delete files.
**How to avoid:** As part of LIC-01 key rotation, explicitly `rm tools/licence_signing.key` as a cleanup step. Document this in the plan.
**Warning signs:** `tools/licence_signing.key` still present after `rm tools/generate_licence.py`.

### Pitfall 6: `base64.b64encode` returns `bytes`, not `str`
**What goes wrong:** GitHub Contents API `content` field must be a JSON string, not bytes. `base64.b64encode(yaml_text.encode())` returns `bytes`; passing this to `requests.put(..., json=body)` serialises as a Python bytes repr, not a base64 string.
**Why it happens:** Python3 `base64.b64encode` always returns `bytes`.
**How to avoid:** Always `.decode()` the result: `base64.b64encode(yaml_text.encode()).decode()`.
**Warning signs:** GitHub API returns 422 with "content" in the error message.

---

## Code Examples

Verified patterns from official sources and existing project code:

### Key generation (from `tools/generate_licence.py`)
```python
# Source: tools/generate_licence.py (existing, proven)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private_key = Ed25519PrivateKey.generate()
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
```

### JWT signing (from `tools/generate_licence.py`)
```python
# Source: tools/generate_licence.py (existing, proven)
import jwt

token = jwt.encode(payload, private_key, algorithm="EdDSA")
# token is a str in PyJWT >= 2.0
```

### GitHub Contents API file creation
```python
# Source: https://docs.github.com/en/rest/repos/contents (verified)
import base64, requests

url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
body = {
    "message": f"feat(licenses): issue {customer_id} {tier} exp {expiry}",
    "content": base64.b64encode(file_content.encode()).decode(),
    # "sha" only needed when updating existing file
}
resp = requests.put(url, headers=headers, json=body)
resp.raise_for_status()
```

### gitleaks-action workflow step
```yaml
# Source: https://github.com/gitleaks/gitleaks-action (verified)
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # GITLEAKS_LICENSE not required for public repos
```

### .gitleaks.toml allowlist structure
```toml
# Source: https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml (verified)
# Uses [[allowlists]] plural (changed in gitleaks v8.25.0)
[[allowlists]]
description = "Known CI dummy values that are not real secrets"
regexTarget = "match"
regexes = [
  '''ci-dummy-key''',
  '''AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=''',
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `[allowlist]` single | `[[allowlists]]` array | gitleaks v8.25.0 | Must use new syntax in `.gitleaks.toml` |
| `python-jose` for EdDSA | `PyJWT[crypto]>=2.7.0` | 2022 | `python-jose` 3.5.0 does NOT support EdDSA; only PyJWT supports it |
| GitHub Contents API `sha` always required | `sha` only required on update | Always been true | New file creation does NOT need `sha` |

**Deprecated/outdated:**
- `[allowlist]` (singular) in `.gitleaks.toml`: replaced by `[[allowlists]]` in v8.25.0 — the old form is silently ignored in newer versions.
- `tools/generate_licence.py`: this file is being replaced and deleted as part of LIC-01.

---

## Open Questions

1. **`--issued-by` default value**
   - What we know: CONTEXT.md marks this as Claude's Discretion
   - What's unclear: Should it default to `git config user.name` (requires `subprocess` call) or require explicit `--issued-by` arg?
   - Recommendation: Default to `git config user.name` if available, otherwise fall back to the system username via `os.getlogin()` or `getpass.getuser()`. Document that this is informational only. Avoid making `--issued-by` a required arg — it adds friction to every invocation.

2. **`list_licences.py` output format**
   - What we know: CONTEXT.md marks column layout as Claude's Discretion
   - What's unclear: Whether to use `tabulate` or manual column formatting
   - Recommendation: Use manual f-string column formatting with fixed widths — avoids adding a `tabulate` dependency. Sort by `expiry` descending so soonest-to-expire licences appear first.

3. **Private repo existence**
   - What we know: CONTEXT.md names the repo `axiom-laboratories/axiom-licenses`
   - What's unclear: Whether the repo exists yet or needs to be created
   - Recommendation: The plan should include a Wave 0 task that confirms the private repo exists and creates it via the GitHub API if not; this cannot be automated but should be documented as a manual prerequisite.

4. **`GITHUB_TOKEN` scope for private repo**
   - What we know: `GITHUB_TOKEN` in CI is scoped to the current (public) repo
   - What's unclear: Whether the operator will use a classic PAT or fine-grained PAT for writing to the private `axiom-licenses` repo
   - Recommendation: The plan should specify a fine-grained PAT with `contents:write` on `axiom-laboratories/axiom-licenses` stored as an env var named `AXIOM_GITHUB_TOKEN`. This is distinct from the CI `GITHUB_TOKEN` used by gitleaks.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, puppeteer/tests/) |
| Config file | none — pytest discovers via directory |
| Quick run command | `cd puppeteer && pytest tests/test_licence_service.py -v` |
| Full suite command | `cd puppeteer && pytest -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIC-01 | Key rotation: new public key validates new JWT; old public key rejects new JWT | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_generate_licence_jwt -x` | ✅ (existing test uses ephemeral keypair) |
| LIC-02 | CI gitleaks step fails on a commit containing `-----BEGIN PRIVATE KEY-----` content | CI/smoke | Manual verify: gitleaks-action fails on synthetic test branch; not automatable locally | ❌ Wave 0 (no test file) |
| LIC-03 | `issue_licence.py --customer X --tier ee --nodes 5 --expiry 2027-01-01` with `--no-remote` prints valid JWT to stdout | unit | `python tools/issue_licence.py --key <path> --customer test --tier ee --nodes 5 --expiry 2027-01-01 --issued-to "Test" --no-remote` | ❌ Wave 0 (script does not exist yet) |
| LIC-04 | YAML record has all required fields; `licence_blob` is the issued JWT | unit | `cd puppeteer && pytest tests/test_issue_licence.py::test_yaml_record_fields -x` | ❌ Wave 0 |
| LIC-05 | `--no-remote` writes YAML to local file; file exists and is valid YAML | unit | `cd puppeteer && pytest tests/test_issue_licence.py::test_no_remote_flag -x` | ❌ Wave 0 |

Note: `test_issue_licence.py` will test the CLI script directly using `subprocess` or by importing the module functions. The script lives in the private repo, so tests may need to be structured as integration tests that call the script via `subprocess`.

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_licence_service.py -x`
- **Per wave merge:** `cd puppeteer && pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_issue_licence.py` — covers LIC-03, LIC-04, LIC-05 (YAML fields, `--no-remote`, key error on missing key)
- [ ] `axiom-licenses/requirements.txt` — PyJWT, cryptography, pyyaml, requests
- [ ] `axiom-licenses/tools/issue_licence.py` — the script itself (Wave 1 deliverable, not Wave 0)

---

## Sources

### Primary (HIGH confidence)
- `tools/generate_licence.py` — existing proven Ed25519 JWT signing implementation; same deps and patterns used directly
- `puppeteer/agent_service/services/licence_service.py` — confirms `_LICENCE_PUBLIC_KEY_PEM` location and PyJWT import pattern
- `.github/workflows/ci.yml` — existing CI structure; gitleaks step added to this file
- `.gitignore` — confirms `*.key` is gitignored; `tools/licence_signing.key` has never been committed
- https://docs.github.com/en/rest/repos/contents — GitHub Contents API endpoint spec (PUT, base64 content, no sha for new files)
- https://github.com/gitleaks/gitleaks-action — gitleaks-action v2 step YAML, `GITHUB_TOKEN` only required env var for public repos

### Secondary (MEDIUM confidence)
- https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml — `[[allowlists]]` plural syntax confirmed (changed in v8.25.0); `regexTarget = "match"` and `regexes` array confirmed
- PyJWT docs (https://pyjwt.readthedocs.io/en/stable/algorithms.html) — `algorithm="EdDSA"` confirmed for Ed25519

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing deps (`PyJWT`, `cryptography`) already proven in codebase; `pyyaml` is stdlib-adjacent; `requests` is universally available
- Architecture: HIGH — `generate_licence.py` template is a near-complete implementation; GitHub Contents API is well-documented
- Pitfalls: HIGH — `jti`/`licence_id` naming mismatch and `base64.b64encode` bytes vs str are verified by reading the actual code and API spec

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (stable APIs — GitHub Contents API and gitleaks-action change slowly)

# Architecture Research

**Domain:** Operator Readiness tooling for existing Axiom job orchestration platform (v15.0)
**Researched:** 2026-03-28
**Confidence:** HIGH — all findings verified against live codebase inspection

---

## Standard Architecture

### System Overview — Existing (v14.4 baseline)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Public Surface (GitHub Pages — axiom-laboratories.github.io/axiom) │
│  ┌────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ homepage/index.html │  │ docs/  (MkDocs Material, gh-deploy)   │ │
│  └────────────────────┘  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Orchestrator (puppeteer/)                                           │
│  ┌─────────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ agent_service/       │  │ model_service/ │  │ dashboard/      │  │
│  │ main.py (FastAPI)    │  │ (port 8000)    │  │ (React/Vite)    │  │
│  │ services/            │  └────────────────┘  └─────────────────┘  │
│  │   licence_service.py │                                            │
│  │   job_service.py     │  ┌────────────────┐                        │
│  │   scheduler_service  │  │  PostgreSQL /  │                        │
│  │   foundry_service    │  │  SQLite        │                        │
│  └─────────────────────┘  └────────────────┘                        │
└───────────────────────────────────┬─────────────────────────────────┘
                            mTLS (pull model)
┌───────────────────────────────────┴─────────────────────────────────┐
│  Puppet Nodes (puppets/)                                             │
│  environment_service/node.py  ->  polls /work/pull                  │
│  runtime.py  ->  container-isolated execution                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Operator CLI (mop_sdk / axiom-sdk PyPI package)                    │
│  axiom-push CLI: init / login / push / create / key generate        │
│  ~/.axiom/ credential store   Ed25519 signing stays on client       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Private Tooling (tools/ in main repo — current state, needs fix)   │
│  tools/generate_licence.py   tools/licence_signing.key             │
└─────────────────────────────────────────────────────────────────────┘
```

### System Overview — v15.0 Additions

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRIVATE REPO: axiom-laboratories/axiom-licences  (NEW)             │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  generate_licence.py   (migrated from main repo tools/)        │ │
│  │  licence_signing.key   (Ed25519 private key — NEVER public)    │ │
│  │  issued/               (ledger of issued licences, gitignored) │ │
│  │  README.md             (key rotation runbook)                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  mop_validation repo — extended validation corpus  (NEW)            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  scripts/node_jobs/           (signed .py / .sh / .ps1)        │ │
│  │    health_check.py            (basic node liveness probe)      │ │
│  │    disk_usage.sh              (OS-agnostic disk report)        │ │
│  │    port_scan.py               (network reachability probe)     │ │
│  │    env_report.ps1             (Windows env snapshot)           │ │
│  │  scripts/sign_corpus.py       (batch-signs scripts via axiom-sdk│ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  docs/ (existing, extended with accuracy validation + screenshots)  │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  scripts/validate_docs.py   (NEW — docs accuracy validator)    │ │
│  │    verifies: API endpoints, CLI commands, compose service names │ │
│  │  scripts/capture_screenshots.py  (NEW — Playwright screenshots) │ │
│  │  docs/runbooks/package-repo.md   (NEW — devpi/bandersnatch)    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### New vs Modified Components

| Component | Location | Type | Responsibility |
|-----------|----------|------|----------------|
| `generate_licence.py` | `axiom-laboratories/axiom-licences` private repo | Migrated | Offline Ed25519-signed JWT licence issuance; private key co-located and never leaves this repo |
| `axiom-licences` private repo | Separate GitHub repo | New | Isolation boundary: private signing key, issuance tooling, and issued-licence ledger |
| `docs/scripts/validate_docs.py` | Main repo `docs/scripts/` | New | Crawls markdown docs, extracts API path patterns and CLI command references, validates against `openapi.json` snapshot and `mop_sdk/cli.py` |
| `docs/scripts/capture_screenshots.py` | Main repo `docs/scripts/` | New | Playwright (Python, `--no-sandbox`) captures live dashboard views for docs and marketing homepage |
| `mop_validation/scripts/node_jobs/` | `mop_validation` repo | New | Library of signed validation scripts (Python/Bash/PowerShell) with companion signatures |
| `mop_validation/scripts/sign_corpus.py` | `mop_validation` repo | New | Batch-signs all scripts in `node_jobs/` via `axiom-sdk` Python API; idempotent |
| `docs/docs/runbooks/package-repo.md` | Main repo `docs/docs/runbooks/` | New | Operator runbook for devpi (Python), bandersnatch (PyPI mirror), PSRepository (PowerShell) |
| `tools/generate_licence.py` | Main repo `tools/` | Stubbed/Removed | After migration: replaced with comment directing to private repo |

---

## Integration Points

### 1. Licence Generation Tooling -> Licence Validation Service

**Direction:** Offline, no runtime coupling. Key pair is the only coordination point.

```
axiom-laboratories/axiom-licences/generate_licence.py
    |
    |  (Ed25519 private key signs JWT claims: customer_id, tier,
    |   node_limit, expiry, grace_days, features[])
    v
JWT string (stdout)
    |
    |  (operator pastes into customer secrets.env as AXIOM_LICENCE_KEY)
    v
puppeteer/agent_service/services/licence_service.py
    |
    |  (hardcoded Ed25519 PUBLIC key: _LICENCE_PUBLIC_KEY_PEM)
    |  (validates at startup; VALID/GRACE/EXPIRED/CE state machine)
    v
LicenceState injected into:
  - EE plugin activation check
  - /api/enroll node-limit enforcement (HTTP 402 when at limit)
  - Dashboard EE badge and GRACE/DEGRADED_CE banner
```

**Migration constraint:** The public key embedded in `licence_service.py` must match the private key in `axiom-licences/`. After key migration, the key pair must be rotated (new pair generated, public key updated in `licence_service.py`, existing issued licences re-signed with new key). There is no other coordination point between the two repos.

### 2. Docs Accuracy Validator -> OpenAPI Snapshot + CLI Source

**Direction:** Read-only. Validates committed artifacts, not a live server.

```
docs/scripts/validate_docs.py
    |
    +-- reads docs/docs/**/*.md
    |     (extracts: /api/... patterns, axiom-push <subcommand> patterns,
    |      service names from compose YAML snippets)
    |
    +-- reads docs/docs/api-reference/openapi.json
    |     (ground truth for API paths — regenerated via regen_openapi.sh)
    |
    +-- reads mop_sdk/cli.py
    |     (ground truth for CLI subcommands — reads registered Click commands)
    |
    v
Validation report to stdout + exit code 1 on any mismatch
    |
    |  (wired into ci.yml as: docs-validate job, runs on docs/** push)
    v
PR blocked if documented endpoints missing from openapi.json,
or documented CLI commands not registered in cli.py
```

**What it validates:**
- Every `/api/...` path mentioned in docs exists in `openapi.json`
- Every `axiom-push <subcommand>` mentioned in docs is a registered Click command in `mop_sdk/cli.py`
- Every compose service name referenced in docs exists in `compose.cold-start.yaml` or `compose.server.yaml`

**Not in scope for v15.0:** Live HTTP request validation. Static OpenAPI comparison is sufficient and CI-safe without a running stack.

### 3. Screenshot Capture -> Live Docker Stack -> Docs and Marketing Assets

**Direction:** One-way read. Output PNG files committed to repo.

```
docs/scripts/capture_screenshots.py
    |
    |  Playwright (Python, --no-sandbox, headless Chromium)
    |  Auth: JWT injected via localStorage before navigation
    |        (existing pattern from mop_validation/scripts/test_playwright.py)
    |  Prerequisite: docker compose -f puppeteer/compose.server.yaml up -d
    |
    +-- captures: Jobs, Nodes, Queue, Foundry, Admin, Staging views
    |
    +-- writes: docs/docs/assets/screenshots/*.png
    +-- writes: homepage/assets/screenshots/*.png
    |
    v
Committed to main branch
    |
    v
Auto-deployed via gh-pages-deploy.yml (existing workflow)
```

**Key constraint:** Screenshots must be captured against the running Docker stack, never against `npm run dev`. This matches the project's existing testing rule.

### 4. Node Validation Job Library -> axiom-push CLI -> Puppet Nodes

**Direction:** Scripts authored offline, signed via axiom-sdk, dispatched to nodes.

```
mop_validation/scripts/node_jobs/*.py (and .sh, .ps1)
    |
    |  python mop_validation/scripts/sign_corpus.py
    |    calls axiom_sdk.signer per script (or axiom-push push CLI)
    |    requires: ~/.axiom/credentials (from axiom-push init)
    |    requires: signing public key registered at POST /api/signatures
    |
    v
Server: signature record stored (script_hash + signature bytes)
    |
    |  operator dispatches:
    |    axiom-push create health-check node_jobs/health_check.py --node <id>
    |    or dashboard guided dispatch form
    |
    v
Puppet node: runtime.py verifies Ed25519 signature before execution
    |
    v
Job result: stdout/stderr captured in ExecutionRecord
```

**Dependency:** `axiom-push init` must be completed before any corpus script can be dispatched. The public key registration step is already handled by `axiom-push init` (existing v14.4 feature).

### 5. Custom Package Repo Docs -> No New Code Integration Required

**Direction:** Documentation only. References existing `mirror_service.py` and Foundry pip.conf injection.

```
docs/docs/runbooks/package-repo.md  (new markdown file)
    |
    References existing functionality:
    - mirror_service.py   (devpi sidecar already in compose.server.yaml)
    - foundry_service.py  (Smelter pip.conf injection — existing)
    - bandersnatch        (operator-managed external process, no Axiom API coupling)
    - PSRepository        (PowerShell-side setup, no Axiom coupling)
    |
    v
Appears in MkDocs nav under Runbooks section
    (requires mkdocs.yml nav entry — the only change needed)
```

---

## Recommended Project Structure (v15.0 Changes)

```
axiom-laboratories/axiom-licences/    <- NEW private GitHub repo
├── generate_licence.py               # migrated from tools/
├── licence_signing.key               # Ed25519 private key (keep secret)
├── issued/                           # ledger of issued licences
│   └── .gitkeep
└── README.md                         # key rotation runbook

master_of_puppets/                    <- existing public repo
├── tools/
│   └── generate_licence.py           # STUB: "moved to axiom-licences private repo"
│                                     # (licence_signing.key removed entirely)
├── docs/
│   ├── scripts/
│   │   ├── regen_openapi.sh          # existing
│   │   ├── validate_docs.py          # NEW
│   │   └── capture_screenshots.py   # NEW
│   └── docs/
│       ├── runbooks/
│       │   ├── package-repo.md       # NEW
│       │   └── ...existing...
│       └── assets/
│           └── screenshots/          # NEW — Playwright output dir
│               └── .gitkeep

mop_validation/                       <- existing private validation repo
└── scripts/
    ├── node_jobs/                    # NEW directory
    │   ├── README.md                 # corpus description + dispatch instructions
    │   ├── health_check.py
    │   ├── disk_usage.sh
    │   ├── port_scan.py
    │   └── env_report.ps1
    └── sign_corpus.py                # NEW
```

---

## Architectural Patterns

### Pattern 1: Offline Signing Tool Isolation (Private Repo Boundary)

**What:** Private key tooling lives in a separate, access-controlled private repo. The public repo contains only the verification public key, hardcoded in source.

**When to use:** Any tool that holds a private signing key whose leak would compromise the security model. Licence issuance is exactly this case — a leaked `licence_signing.key` allows unlimited EE licence forgery.

**Trade-offs:** Slight operational friction (clone two repos to do issuance work) vs. eliminating the risk of the private key appearing in git history, PRs, or public forks.

### Pattern 2: Static Snapshot Validation Over Live-Stack CI

**What:** The docs accuracy validator reads `openapi.json` (a committed snapshot produced by `regen_openapi.sh`) rather than making live HTTP requests.

**When to use:** CI jobs where spinning up the full Docker stack is expensive. The snapshot is regenerated manually after API route changes and committed alongside the docs changes that reference the new routes.

**Trade-offs:** Docs can drift from the live API if `regen_openapi.sh` is not run. Mitigation: CI can check that the committed snapshot's route set is a subset of the current server output, failing if new routes were added without updating the snapshot.

**Example:**
```python
import re, json
from pathlib import Path

def extract_api_paths_from_docs(docs_root: Path) -> set:
    pattern = re.compile(r'`(/api/[^`\s]+)`')
    paths = set()
    for md in docs_root.rglob("*.md"):
        paths.update(pattern.findall(md.read_text()))
    return paths

def validate_against_openapi(paths: set, openapi: dict) -> list:
    known = set(openapi["paths"].keys())
    return sorted(p for p in paths if p not in known)
```

### Pattern 3: Playwright Screenshot Automation (Existing Project Convention)

**What:** Python Playwright with `--no-sandbox`, JWT injected via `localStorage.setItem('mop_auth_token', token)` before navigation.

**When to use:** Capturing authenticated dashboard views for documentation. This is the identical authentication pattern already used in `mop_validation/scripts/test_playwright.py`.

**Trade-offs:** Screenshots go stale when UI changes. Treat as an operator step, not a blocking CI gate, to avoid blocking deploys on cosmetic drift.

**Example:**
```python
from playwright.sync_api import sync_playwright
import requests

def get_token(base_url, username, password):
    r = requests.post(f"{base_url}/api/auth/login",
                      data={"username": username, "password": password})
    return r.json()["access_token"]

def capture(page, url, out_path, token):
    page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=out_path)
```

---

## Data Flow

### Licence Issuance Flow

```
Operator (axiom-licences private repo)
    |  python generate_licence.py --customer-id ACME --tier ee --expiry 2027-01-01 ...
    v
JWT string printed to stdout
    |
    |  operator pastes into customer secrets.env: AXIOM_LICENCE_KEY=<jwt>
    v
Axiom startup (lifespan in main.py)
    |  licence_service.load_licence()
    |    -> Ed25519 JWT signature verified against hardcoded public key
    |    -> LicenceState computed: VALID / GRACE / EXPIRED / CE
    v
EE plugin loaded if is_ee_active
POST /api/enroll: HTTP 402 if active_node_count >= node_limit
Dashboard: EE badge, GRACE banner (dismissible), DEGRADED_CE banner (non-dismissible)
```

### Docs Validation Flow

```
Developer edits docs/docs/**/*.md
    |
    v
CI job: docs-validate (on docs/** push)
    |  python docs/scripts/validate_docs.py
    |    -> extract /api/... patterns from markdown
    |    -> cross-reference docs/docs/api-reference/openapi.json
    |    -> extract axiom-push subcommands from markdown
    |    -> cross-reference mop_sdk/cli.py registered commands
    v
Pass: exit 0 -> PR can merge
Fail: exit 1 -> PR blocked with diff of unknown references
```

### Node Validation Corpus Dispatch Flow

```
Operator writes mop_validation/scripts/node_jobs/health_check.py
    |
    v
python mop_validation/scripts/sign_corpus.py
    |  requires: ~/.axiom/credentials (axiom-push init completed)
    |  calls axiom_sdk per script -> POST /api/signatures registers public key + hash
    v
axiom-push create health-check scripts/node_jobs/health_check.py --node <node-id>
    |
    v
Puppet node runtime.py:
    -> verifies Ed25519 signature against registered public key
    -> executes in container if valid
    -> captures stdout/stderr in ExecutionRecord
```

---

## Build Order

Dependencies drive the sequence. Items later in the list depend on earlier ones.

| Order | Component | Depends On | Rationale |
|-------|-----------|-----------|-----------|
| 1 | `axiom-laboratories/axiom-licences` repo setup + key migration | Nothing (fully standalone) | Highest-priority risk remediation; clears private key from public repo immediately; no other v15 work depends on this being done first, but it should be |
| 2 | `docs/docs/runbooks/package-repo.md` | Existing MkDocs nav structure | Pure documentation; zero code changes; easy early win |
| 3 | `docs/scripts/validate_docs.py` | `docs/docs/api-reference/openapi.json` (existing committed snapshot) | Static file analysis only; no stack needed; CI-wirable once passing |
| 4 | `mop_validation/scripts/node_jobs/` corpus (write scripts) | Nothing | Scripts can be authored before signing infrastructure is wired |
| 5 | `mop_validation/scripts/sign_corpus.py` | node_jobs/ scripts (step 4), running Axiom stack, `axiom-push init` | Batch signing requires scripts to exist and server to be reachable |
| 6 | `docs/scripts/capture_screenshots.py` | Running Docker stack, all UI features stable | Last — captures final UI state; requires the full stack; output depends on UI being complete |

---

## Isolation: Private Repo vs Public Repo

This is the most critical architectural boundary in v15.0.

| Concern | Repo | Rationale |
|---------|------|-----------|
| Ed25519 licence signing private key | `axiom-laboratories/axiom-licences` (private) | Leaked private key enables unlimited EE licence forgery |
| Licence issuance CLI (`generate_licence.py`) | `axiom-laboratories/axiom-licences` (private) | Tool co-located with key; no value in public exposure |
| Issued licence ledger | Inside `axiom-licences` (gitignored subfolder) | Customer data |
| Licence verification public key | `puppeteer/agent_service/services/licence_service.py` (public) | Ships with product; read-only verification is safe and necessary |
| Docs validation tooling | Main repo `docs/scripts/` (public) | No secrets; useful to open-source contributors |
| Screenshot capture script | Main repo `docs/scripts/` (public) | No secrets; requires local stack to run |
| Node validation job scripts | `mop_validation` repo (private) | Test infrastructure kept separate — existing project convention |

**Current state requiring remediation:** `tools/licence_signing.key` exists in the public main repo. This must be migrated and the key pair rotated before v15.0 is complete. The public key in `licence_service.py` must be updated to match the rotated key.

---

## Anti-Patterns

### Anti-Pattern 1: Leaving Private Key in Public Repo

**What people do:** Leave `tools/licence_signing.key` in place because migration seems risky.

**Why it's wrong:** Any clone of the public repo grants the ability to generate unlimited valid EE licences. The entire commercial model is undermined. The key has already been exposed to git history.

**Do this instead:** Migrate to `axiom-licences` private repo, rotate the key pair (generate new, update `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py`, re-sign any issued licences), and delete `tools/licence_signing.key` from the main repo with a squash or history rewrite if the key was ever committed.

### Anti-Pattern 2: Live-Stack Validation in CI

**What people do:** Write `validate_docs.py` to make HTTP requests to `http://localhost:8001` in CI.

**Why it's wrong:** CI jobs without a running stack will fail spuriously; adding the stack to CI requires Docker-in-Docker or service containers, adding minutes of setup time and flaky failures.

**Do this instead:** Validate against the committed `openapi.json` snapshot. The snapshot is already version-controlled, always available, and makes validation run in under a second.

### Anti-Pattern 3: Unsigned Scripts in the Validation Corpus

**What people do:** Commit `.py`/`.sh`/`.ps1` scripts to `node_jobs/` without registered signatures, assuming users will know how to sign them.

**Why it's wrong:** Scripts without registered server-side signatures will be rejected at execution time by `runtime.py`. The corpus is useless if it cannot be dispatched.

**Do this instead:** Treat `sign_corpus.py` as the mandatory publication step. The corpus is not "ready" until all scripts have registered signatures. Document this constraint in the `node_jobs/README.md`.

### Anti-Pattern 4: Screenshots in Git History

**What people do:** Commit every Playwright capture run, accumulating large binary diffs.

**Why it's wrong:** Git is not an image store. Screenshot PNGs are tens of KB each; history bloats quickly.

**Do this instead:** Store screenshots in the repo but document `capture_screenshots.py` as an operator step run before intentional doc refreshes, not as a CI gate. Consider `.gitignore`-ing them and having a dedicated "refresh screenshots" workflow that generates and commits them only when needed.

---

## Scaling Considerations

These v15.0 components are operator tooling and documentation — they have no runtime performance footprint on the Axiom server itself.

| Concern | Impact | Notes |
|---------|--------|-------|
| Licence issuance volume | None | Offline tool; runs once per customer; zero server load |
| Docs validation in CI | Low | Markdown + JSON parsing; completes in under 5 seconds |
| Screenshot capture | Moderate (one-time) | Full Playwright + Chromium launch; ~30-60 seconds for a full capture run; not a hot CI path |
| Node job corpus size | Negligible | Text files; signing is one-time per script version |

---

## Sources

- Direct inspection: `puppeteer/agent_service/services/licence_service.py` — Ed25519 JWT validation, hardcoded public key, LicenceState state machine
- Direct inspection: `tools/generate_licence.py` — existing licence issuance CLI structure and deps (PyJWT, cryptography)
- Direct inspection: `docs/scripts/regen_openapi.sh` — established pattern for OpenAPI snapshot management
- Direct inspection: `docs/docs/api-reference/openapi.json` — existing committed validation ground truth
- Direct inspection: `mop_validation/scripts/` — existing test/validation script patterns
- Direct inspection: `mop_sdk/signer.py`, `mop_sdk/cli.py` — Ed25519 signing infrastructure and CLI command registration
- Project memory: Playwright `--no-sandbox` + localStorage JWT injection pattern (validated in v14.0 cold-start)
- `PROJECT.md`: v14.4 validated state, key decisions table, deferred future items

---
*Architecture research for: Axiom v15.0 Operator Readiness*
*Researched: 2026-03-28*

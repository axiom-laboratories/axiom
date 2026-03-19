# Stack Research

**Domain:** Enterprise job orchestration — Axiom v10.0 Commercial Release new features
**Researched:** 2026-03-17
**Confidence:** HIGH (codebase reviewed directly; PyPI Trusted Publisher prerequisites verified against official docs)

---

## Scope

This file covers ONLY the net-new stack additions for v10.0. The existing validated stack
(FastAPI, SQLAlchemy, React/Vite, APScheduler, cryptography, PyNaCl, Caddy, Postgres, aiosqlite,
MkDocs Material container) is not repeated here.

The previous STACK.md (v9.0) covered the MkDocs Material docs container; that content remains
valid and is not superseded.

---

## Pre-Assessment: What Already Exists

Before recommending additions, the codebase was audited directly. Several v10.0 requirements
are already partially or fully implemented:

| Requirement | Current State |
|-------------|---------------|
| OUTPUT-01/02: stdout/stderr/exit code per execution | `ExecutionRecord` table exists in `db.py` with `output_log` (JSON), `exit_code`, `truncated`. Node captures and reports these in `node.py` via `build_output_log()`. Job service writes records in `report_result()`. **Fully implemented.** |
| OUTPUT-03/04: Execution history query | `ExecutionRecord` has 4 composite indexes (`ix_execution_records_job_guid`, `job_started`, `node_started`, `started_at`). Query infrastructure is ready. Frontend view is the only missing piece. |
| RETRY-01/02/03: Retry policy with backoff | `Job` has `max_retries`, `retry_count`, `retry_after`, `backoff_multiplier`. `job_service.py` implements exponential backoff with jitter on failure and zombie reaping. `ScheduledJob` also has `max_retries`. **Fully implemented in the data model and job service.** |
| ENVTAG-01/02: Environment tags | `Node.operator_tags` accepts `env:DEV`, `env:TEST`, `env:PROD` tags. `job_service.pull_work()` has strict env-tag isolation logic (lines 312-322). `HeartbeatPayload` sanitises self-reported `env:` tags. **Fully implemented.** |

**Conclusion:** The core backend logic for OUTPUT, RETRY, and ENVTAG is already in the codebase.
v10.0 work is primarily:
1. Runtime attestation (OUTPUT-05..07) — new signing/verification step, new DB column
2. CI/CD dispatch API (ENVTAG-04) — a documented endpoint, likely already possible via existing `/jobs` POST + env tag
3. PyPI Trusted Publisher activation (RELEASE-01) — external org/project creation, no code changes
4. GHCR image publishing (RELEASE-02) — workflow already written, awaits org creation
5. Frontend views for execution history and retry state (OUTPUT-03/04, RETRY-03) — dashboard work only

---

## Recommended Stack

### New Backend: Runtime Attestation (OUTPUT-05..07)

No new Python libraries are required. The `cryptography` library already in
`puppeteer/requirements.txt` provides everything needed.

| Capability | How Achieved | Library |
|------------|-------------|---------|
| Sign attestation bundle on node | `cryptography.hazmat.primitives.asymmetric.padding.PKCS1v15` or `cryptography.hazmat.primitives.asymmetric.ec.ECDSA` via the node's RSA private key (already on disk at `secrets/{node_id}.key`) | `cryptography` (already present) |
| Verify attestation on orchestrator | Load stored `Node.client_cert_pem`, extract public key, verify signature bytes | `cryptography` (already present) |
| Serialise attestation bundle | `json.dumps` of bundle dict → `hashlib.sha256` → sign the canonical UTF-8 bytes | stdlib `json`, `hashlib` |

**Node private key format:** Nodes enroll with RSA 2048 keys (confirmed in `node.py` line 380:
`rsa.generate_private_key(public_exponent=65537, key_size=2048)`). The key is written to
`secrets/{node_id}.key` in PEM format without encryption. The attestation signer in `node.py`
should use `RSA + PKCS1v15 + SHA256` — the same algorithm family already used for CSR signing.

**DB addition needed:** `ExecutionRecord` needs two new nullable columns:

```python
attestation_bundle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # raw JSON bundle
attestation_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # base64 signature
attestation_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # VERIFIED / FAILED / MISSING
```

These are nullable so existing records are not broken. `create_all` will not add them to the
existing table — a migration SQL file is required (same pattern as `migration_v13.sql`).

### New Backend: CI/CD Dispatch API (ENVTAG-04)

No new library required. The existing `POST /jobs` endpoint already accepts `target_tags`
(which can include `env:PROD`). What ENVTAG-04 requires is:

1. A documented, stable endpoint path for CI/CD consumers — recommend `/api/v1/dispatch` as
   a thin wrapper around the existing job creation flow, returning structured JSON.
2. Service Principal auth (already exists) is the correct auth mechanism for pipelines.
3. The response shape needs to include `node_assigned` (available after polling) or be
   asynchronous with a `job_id` for polling.

**Recommendation:** Add `GET /api/v1/jobs/{guid}/status` as a lightweight polling endpoint
that returns `{guid, status, node_id, exit_code, attempt}` — suitable for `curl` + `jq` in CI.
No new library needed.

### New Frontend: Execution History View (OUTPUT-03/04, RETRY-03)

No new npm packages required. All data is already queryable. The work is:

1. Add `GET /jobs/{guid}/executions` API route (returns list of `ExecutionRecord` rows for
   a job) — backend work, no new library.
2. Add an execution history panel to the Jobs view in `Jobs.tsx` or a dedicated
   `ExecutionHistory.tsx` — uses existing recharts (already in `package.json`) for timeline
   visualisation, existing Radix UI for the expanded log viewer.

**One potential addition:** A syntax-highlighted log viewer for stdout/stderr output.
`react-syntax-highlighter` (v15.x) is the standard choice, but the output format is plain text
line-by-line (not code), so a plain `<pre>` with line coloring by `stream` field is sufficient
and avoids a new dependency.

### PyPI Trusted Publisher (RELEASE-01)

No code changes required. The `release.yml` workflow is already correctly configured:
- Uses `pypa/gh-action-pypi-publish@release/v1`
- Has `permissions: id-token: write` on both publish jobs
- Targets `environment: testpypi` and `environment: pypi` with the correct URLs

**External prerequisites only:**

| Step | Action | Who |
|------|--------|-----|
| 1 | Create `axiom-laboratories` GitHub organisation | Operator |
| 2 | Transfer or fork this repo into `axiom-laboratories/axiom` | Operator |
| 3 | On PyPI: go to "Publishing" → "Add a new pending publisher" | Operator |
| 4 | Fill in: PyPI project name `axiom-sdk`, GitHub owner `axiom-laboratories`, repo `axiom`, workflow `release.yml`, environment `pypi` | Operator |
| 5 | Repeat step 3-4 for TestPyPI with environment `testpypi` | Operator |
| 6 | Push a `v*` tag — the workflow runs, PyPI creates the project and publishes | Operator |

**Critical:** The pending publisher does not reserve the name `axiom-sdk` on PyPI until the
first publish. If another account registers `axiom-sdk` before the first publish, the pending
publisher is invalidated. Publish as soon as the org and pending publisher are configured.

### GHCR Multi-Arch Publishing (RELEASE-02)

No code changes required. The `docker-release` job in `release.yml` is fully configured:
- Multi-arch: `linux/amd64,linux/arm64` via QEMU + buildx
- Pushes to `ghcr.io/axiom-laboratories/axiom`
- Tags: semver `{{version}}` and `{{major}}.{{minor}}`

**External prerequisite only:** The `axiom-laboratories` GitHub org must exist and the repo
must be under it. Once the org exists and the repo is transferred, pushing any `v*` tag
activates both PyPI and GHCR publishing simultaneously.

### Licence Compliance (LICENCE-01..04)

No new libraries required. This is documentation and configuration work:

| Task | File | Action |
|------|------|--------|
| LICENCE-01: certifi MPL-2.0 decision | `LEGAL.md` | Document read-only CA bundle usage, no source modification, obligations satisfied |
| LICENCE-02: License-Expression field | `pyproject.toml` | Add `license-expression = "Apache-2.0"` under `[project]` (PEP 639 field, supported by setuptools >=61) |
| LICENCE-03: NOTICE file | `NOTICE` | List caniuse-lite CC-BY-4.0 attribution and any others from audit |
| LICENCE-04: paramiko LGPL-2.1 assessment | `LEGAL.md` | Confirm dynamic-only import pattern; document whether EE bundling requires asyncssh swap |

**Note on `asyncssh`:** If LICENCE-04 assessment concludes that EE wheel bundling would
statically link paramiko, replace it with `asyncssh` (MIT). `asyncssh` is drop-in compatible
for SSH-over-Python use cases and avoids the LGPL-2.1 linking concern entirely. Do not swap
unless the assessment concludes static linking is occurring — dynamic import of paramiko is
fully LGPL-compliant without source distribution.

---

## Schema Additions Summary

All are additive (nullable columns or new index) — safe to add via migration SQL.

```sql
-- migration_v14.sql
-- Runtime attestation columns on execution_records

ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS
    attestation_bundle TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS
    attestation_signature TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS
    attestation_status VARCHAR(20);

-- Environment tag on nodes (for ENVTAG-01 explicit column, if desired)
-- Note: env tags already work via operator_tags JSON column.
-- An explicit column is optional but aids filtering performance.
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS
    env_tag VARCHAR(20);
```

The `env_tag` column on `Node` is optional — the existing `operator_tags` JSON column already
supports `env:DEV` / `env:TEST` / `env:PROD` tags with enforced isolation in `pull_work()`.
Adding a dedicated column is recommended for ENVTAG-03 (filterable Nodes view) to avoid
parsing JSON in the DB query. If added, backfill from `operator_tags` at migration time.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `cryptography` RSA+PKCS1v15 for attestation | `PyNaCl` Ed25519 for attestation | PyNaCl is already used for job signing. Using a different key type for attestation (node's mTLS RSA key) means we cannot reuse PyNaCl — the node's identity key is RSA, not Ed25519. Keeping `cryptography` for attestation uses the already-loaded key material. |
| stdlib `json` + `hashlib` for bundle serialisation | `msgpack` or CBOR for binary attestation | Binary formats add a new dependency for no operational benefit. JSON is inspectable, debuggable, and sufficient for offline verification by operators. |
| Existing `/jobs` POST for CI/CD dispatch | New dedicated `/api/v1/dispatch` endpoint | The existing endpoint already does everything needed. A thin wrapper adds a stable documented path without duplicating logic. Either approach works; the recommendation is to document the existing endpoint as the CI/CD interface and add the status-polling endpoint. |
| `asyncssh` (conditional swap for paramiko) | Keep `paramiko` in all cases | Paramiko is LGPL-2.1. Dynamic import is fine for open-source distribution. The swap is only needed if EE wheel bundling creates static linking — assess before deciding. |
| Dedicated `env_tag` column on nodes | Keep using `operator_tags` JSON | JSON parsing in SQL WHERE clauses is non-portable (differs between SQLite and Postgres). A dedicated column with an index makes the filter in ENVTAG-03 straightforward and consistent across both DB backends. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| New retry library (tenacity, backoff) | Retry logic with exponential backoff + jitter is already implemented in `job_service.py`. Adding a library would duplicate it. | Extend the existing `max_retries` / `backoff_multiplier` / `retry_after` pattern already in the `Job` model |
| New attestation library (sigstore, in-toto) | Heavyweight dependencies designed for software supply chain provenance, not runtime execution attestation. The requirement is a signed JSON bundle using the node's existing RSA key — that is 20 lines of `cryptography` code. | `cryptography` (already present) |
| `PyJWT` or `python-jose` for attestation tokens | JWTs are stateless bearer tokens, not signed execution records. The verification requirement needs the raw signature + stored cert. | Raw PKCS1v15 signature over the JSON bundle bytes |
| `aiosqlite` version pin changes | The existing `DATABASE_URL` sqlite+aiosqlite pattern is already working. No version changes needed for v10.0 features. | Keep existing aiosqlite as installed by sqlalchemy[asyncio] |
| New frontend charting library | recharts is already installed and used for sparklines. Execution timeline can use the same library. | recharts (already present) |

---

## Stack Patterns by Variant

**Attestation verification on orchestrator (OUTPUT-06):**
- Load `Node.client_cert_pem` from DB
- Parse with `cryptography.x509.load_pem_x509_certificate()`
- Extract public key: `cert.public_key()`
- Verify: `public_key.verify(signature_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())`
- Catch `cryptography.exceptions.InvalidSignature` → store `attestation_status = "FAILED"`
- Success → store `attestation_status = "VERIFIED"`

**Attestation signing on node (OUTPUT-05):**
- Build bundle dict: `{script_hash, stdout_hash, stderr_hash, exit_code, started_at, node_cert_serial}`
- Canonical form: `json.dumps(bundle, sort_keys=True).encode("utf-8")`
- Load key: `serialization.load_pem_private_key(key_bytes, password=None)`
- Sign: `private_key.sign(bundle_bytes, padding.PKCS1v15(), hashes.SHA256())`
- Encode for transport: `base64.b64encode(signature).decode()`
- Include `attestation_bundle` (JSON string) and `attestation_signature` (base64 string) in the `ResultReport` POST body

**CI/CD dispatch pattern (ENVTAG-04):**
```bash
# Minimal CI/CD dispatch — no new tooling required
JOB_ID=$(curl -sf -X POST https://axiom.example.com/jobs \
  -H "Authorization: Bearer $SERVICE_PRINCIPAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"python_script","payload":{...},"target_tags":["env:PROD"]}' \
  | jq -r .guid)

# Poll for completion
while true; do
  STATUS=$(curl -sf https://axiom.example.com/api/v1/jobs/$JOB_ID/status \
    -H "Authorization: Bearer $SERVICE_PRINCIPAL_TOKEN" | jq -r .status)
  [ "$STATUS" = "COMPLETED" ] && break
  [ "$STATUS" = "FAILED" ] && exit 1
  sleep 5
done
```

---

## Version Compatibility

| Package | Version in requirements.txt | Notes for v10.0 |
|---------|---------------------------|-----------------|
| cryptography | unpinned (latest) | RSA PKCS1v15 signing available since cryptography 1.x. No version concern. Current latest is 44.x. |
| sqlalchemy | unpinned | `mapped_column` declarative syntax requires SQLAlchemy 2.0+. Already using it. New nullable columns are additive. |
| aiosqlite | transitive via sqlalchemy | SQLite `ADD COLUMN IF NOT EXISTS` requires SQLite 3.35+ (shipped in Python 3.10+). Project already requires Python 3.10+. |
| pyproject.toml setuptools | >=61.0 (already pinned) | `License-Expression` (PEP 639) requires setuptools >=62.3 for full support. Bump to `>=62.3` in `[build-system]`. |

---

## Installation

No new packages needed in `puppeteer/requirements.txt`.

For `pyproject.toml` build-system:
```toml
[build-system]
requires = ["setuptools>=62.3"]   # was >=61.0; bump for PEP 639 License-Expression
build-backend = "setuptools.build_meta"

[project]
# Add this field (PEP 639):
license-expression = "Apache-2.0"
# Remove the old:
# license = {text = "Apache-2.0"}
```

---

## Sources

- `puppeteer/agent_service/db.py` — reviewed directly; `ExecutionRecord`, `Job`, `Node` schemas confirmed (HIGH confidence)
- `puppeteer/agent_service/services/job_service.py` — retry logic, env-tag isolation, execution record writes confirmed (HIGH confidence)
- `puppets/environment_service/node.py` — RSA key generation (line 380), `build_output_log()`, `report_result()` confirmed (HIGH confidence)
- `puppeteer/agent_service/models.py` — `ResultReport` fields, `WorkResponse` fields confirmed (HIGH confidence)
- `puppeteer/requirements.txt` — existing dependencies confirmed; no new additions needed (HIGH confidence)
- `.github/workflows/release.yml` — PyPI OIDC publish jobs, GHCR multi-arch build confirmed (HIGH confidence)
- `pyproject.toml` — current `license = {text = "Apache-2.0"}` form confirmed; PEP 639 migration path identified (HIGH confidence)
- [PyPI Trusted Publishers — Creating a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) — pending publisher prerequisites, name-squatting warning confirmed (HIGH confidence)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) — `id-token: write` requirement, `repository-url` for TestPyPI confirmed (HIGH confidence)
- [cryptography X.509 reference](https://cryptography.io/en/latest/x509/reference/) — `load_pem_x509_certificate`, `public_key()`, RSA verify API confirmed (HIGH confidence)
- [Python packaging — License-Expression (PEP 639)](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license) — setuptools >=62.3 requirement for PEP 639 field (MEDIUM confidence — cross-referenced with setuptools changelog)

---

*Stack research for: Axiom v10.0 — Commercial Release new features*
*Researched: 2026-03-17*

---
---

# Stack Research — v11.0 CE/EE Split Completion (ADDENDUM)

**Domain:** CE/EE Split Completion — Python source protection, plugin wiring, Docker Hub publishing
**Researched:** 2026-03-19
**Confidence:** HIGH (versions verified from PyPI live pages; Action versions verified from GitHub Marketplace and existing release.yml; entry_points pattern verified from official Python packaging docs)

---

## Scope

This addendum covers ONLY the net-new stack requirements for v11.0 CE/EE Split Completion. The existing validated stack (including all v10.0 additions above) is not re-researched.

Three new capability areas:
1. **Compiling EE Python code to `.so`** — Cython vs Nuitka, build pipeline for private repo CI
2. **Entry points plugin wiring** — CE discovers EE at startup via `importlib.metadata`
3. **Docker Hub CE image publishing** — adding `axiom-ce` to Docker Hub alongside existing GHCR

---

## Pre-Assessment: What Already Exists in the Split Branch

The `feature/axiom-oss-ee-split` worktree (at `.worktrees/axiom-split/`) already has:

| Component | State |
|-----------|-------|
| `agent_service/ee/__init__.py` — `load_ee_plugins(app, engine)` | Implemented using **`pkg_resources`** (deprecated) — needs migration to `importlib.metadata` |
| `agent_service/ee/interfaces/` — 8 ABC stub files | Complete |
| `agent_service/ee/routers/` — 7 extracted router files | Complete (to be moved to private `axiom-ee` repo) |
| EE entry point group name | `"axiom.ee"` — confirmed in `load_ee_plugins()` |
| `pyproject.toml` (CE side) | Uses `setuptools>=77.0` — sufficient for `[project.entry-points]` table |
| `release.yml` — GHCR multi-arch publish | Complete using `docker/login-action@v3`, `docker/build-push-action@v6`, `docker/metadata-action@v6` |

---

## Recommended Stack — NEW Additions for v11.0

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Cython | 3.2.4 | Compile EE `.py` router/plugin files to `.so` extension modules | Pure-Python mode compiles unmodified `.py` files — no `.pyx` rewrite needed; standard `ext_modules` in `pyproject.toml`; produces importable `.so` with no readable source; well-established in open-core products (msgpack, lxml, etc.) |
| cibuildwheel | 3.4.0 | Build Cython `.so` wheels for linux/amd64 and linux/arm64 in CI | pypa-endorsed standard for C extension wheel CI; handles manylinux containers automatically; QEMU handles aarch64 emulation; used by scipy, pandas, numpy — proven at scale |
| importlib.metadata | stdlib Python 3.10+ | Discover `axiom.ee` entry point at CE startup | Replacement for deprecated `pkg_resources`; `entry_points(group='axiom.ee')` is the canonical modern API; no extra dependency; project already requires Python 3.10+ |
| docker/login-action | v3 | Authenticate to Docker Hub in GitHub Actions | Official Docker-maintained action; already used for GHCR login in release.yml; PAT-based (password auth deprecated by Docker Hub) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| setuptools | >=77.0 (already in CE pyproject.toml) | Build backend for `ext_modules` Cython compilation in EE repo | Required in `[build-system].requires` of EE private repo's `pyproject.toml` |
| Cython | >=3.2.4,<4 | Build-time only (NOT in runtime requirements) | Declared in `[build-system].requires` in EE repo; never in `requirements.txt` or runtime image |
| build (`python -m build`) | latest | Invoke the Cython wheel build in EE CI | Already in CE's `release.yml` — same pattern applies to EE |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `cython --annotate` | Generate HTML showing Python/C interaction per line | Use during EE development to verify compilation coverage; never ship annotate HTML in distribution |
| `cibuildwheel --platform linux` (local) | Test wheel builds locally before CI push | Requires Docker; `pip install cibuildwheel && cibuildwheel --platform linux` in EE repo root |

---

## Installation

```bash
# EE private repo — pyproject.toml additions only (not runtime requirements)
# [build-system]
# requires = ["setuptools>=77.0", "Cython>=3.2.4,<4"]

# CE side — no new pip installs
# importlib.metadata is stdlib on Python 3.10+
# The one change is in ee/__init__.py: replace pkg_resources with importlib.metadata (see below)

# CI tooling (not in any requirements.txt)
pip install cibuildwheel build
```

---

## Decision Details

### 1. Cython over Nuitka for `.so` compilation

**Use Cython. This is a firm recommendation.**

**Why Cython wins for this use case:**

- **Pure-Python mode**: Cython 3.x compiles plain `.py` files with no `.pyx` dialect. The EE router and plugin files are regular Python — zero rewrite required.
- **setuptools `ext_modules` integration**: Declare all EE `.py` files as extension modules in `pyproject.toml`. `python -m build` produces a wheel containing only `.so` files — no `.py` source shipped.
- **cibuildwheel compatibility**: cibuildwheel was designed for exactly this pattern (C extension wheels). It handles manylinux containers, QEMU for aarch64, and Python 3.9–3.13 automatically.
- **Wheel portability**: The output is a standard Python wheel installable via `pip install axiom-ee`. No special runtime shim or wrapper needed.
- **Maturity**: Cython 3.2.4 (Jan 2026). Widely deployed in production open-core Python products for over a decade.

**Why Nuitka is not the right tool:**

- Nuitka 4.0.6 targets standalone executables or single-module compilation (`--mode=module`). Packaging a multi-module package (7 routers + plugin class + interfaces) into a distributable wheel requires `nuitka-setuptools`, a third-party bridge with no official maintenance.
- Nuitka embeds a C runtime shim that inflates `.so` file size. Cython's output is lean.
- Nuitka-Action (v1.3) is documented for executable builds. Module-mode multi-file wheel CI with aarch64 is not covered by official Nuitka tooling.
- The commercial features (encrypted tracebacks) are relevant for standalone executables distributed to end users — not for a wheel-based plugin loaded by a server process.

**Verdict**: Cython for `.so` wheel builds. Nuitka is the right tool for standalone CLI executables (not this use case).

---

### 2. Entry points: migrate from `pkg_resources` to `importlib.metadata`

The existing `load_ee_plugins()` in `agent_service/ee/__init__.py` uses `pkg_resources.iter_entry_points("axiom.ee")`. This must be updated before v11.0 ships.

`pkg_resources` was deprecated in setuptools 67.0 (January 2023) and emits `DeprecationWarning` in current environments. `importlib.metadata` is the stdlib replacement, available since Python 3.8 and fully stabilised in 3.10 — the project's minimum Python version.

**Updated discovery code (drop-in replacement for the `try` block in `load_ee_plugins()`):**

```python
from importlib.metadata import entry_points

plugins = entry_points(group="axiom.ee")
```

The `entry_points(group=...)` keyword-argument form requires Python 3.9+. Project requires 3.10+, so this is safe. On a CE-only install, `plugins` is an empty `SelectableGroups` object — no exception, no log noise.

**EE private repo `pyproject.toml` entry point declaration (correct modern syntax):**

```toml
[project.entry-points."axiom.ee"]
core = "ee.plugin:EEPlugin"
```

The existing plan's `setup.cfg` example uses legacy INI format. Use `pyproject.toml` instead — it is the current standard and consistent with both the CE repo and the EE repo's build system.

**How the wiring works end-to-end:**
1. `pip install axiom-ee` registers the entry point metadata alongside the installed `.so` files
2. CE starts, `lifespan()` calls `load_ee_plugins(app, engine)`
3. `entry_points(group="axiom.ee")` finds `EEPlugin` (loaded from the compiled `.so`)
4. `plugin_cls(app, engine)` instantiates with the FastAPI app and SQLAlchemy engine
5. `plugin.register(ctx)` mounts the 7 EE routers on `app` and sets feature flags `True` in `ctx`

---

### 3. Docker Hub CE publishing — exact workflow change

**The delta from the existing `release.yml` is minimal:**

1. Add a Docker Hub login step (before the existing GHCR login step)
2. Add `axiom-laboratories/axiom-ce` to the `metadata-action` images list alongside the existing GHCR image

Single build, single `build-push-action` call, two registry pushes.

**Docker Hub authentication**: Create a Docker Hub Personal Access Token (PAT) with Read/Write/Delete scope at Docker Hub → Account Settings → Security → New Access Token. Store as:
- Repository secret: `DOCKERHUB_TOKEN` (the PAT value)
- Repository variable: `DOCKERHUB_USERNAME` (Docker Hub username)

**Do not use Docker Hub password** — Docker Hub deprecated password-based API authentication. PAT is required and has been the only supported method since 2021.

**Additions to the `docker-release` job in `release.yml`:**

```yaml
# Add this step BEFORE the existing GHCR login step:
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ vars.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}

# Update the metadata-action images list:
- name: Extract Docker metadata
  id: meta
  uses: docker/metadata-action@v6
  with:
    images: |
      axiom-laboratories/axiom-ce
      ghcr.io/axiom-laboratories/axiom
    # ... rest of tags/flavor config unchanged
```

The `build-push-action` step requires no changes — it reads from `${{ steps.meta.outputs.tags }}` which now includes both registries.

**Naming**: `axiom-ce` on Docker Hub (not `axiom`) makes the CE/EE distinction explicit to users evaluating the product.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Cython 3.2.4 for `.so` | Nuitka 4.0.6 `--mode=module` | Nuitka targets executables; multi-module wheel packaging requires unsupported `nuitka-setuptools` bridge; larger output; no cibuildwheel integration |
| cibuildwheel for wheel CI | Manual `docker run manylinux + Cython` | cibuildwheel IS the standard abstraction over manylinux; reinventing it adds maintenance burden with no benefit |
| `importlib.metadata` (stdlib) | `pkg_resources` (setuptools) | `pkg_resources` deprecated since setuptools 67 (Jan 2023); emits DeprecationWarning; removal is planned |
| `importlib.metadata` (stdlib) | `importlib_metadata` backport package | Backport only needed for Python < 3.9; CE requires Python 3.10+; no extra dependency needed |
| `pyproject.toml` `[project.entry-points]` | `setup.cfg` `[options.entry_points]` | `setup.cfg` is legacy; `pyproject.toml` is the current standard; CE repo already uses `pyproject.toml` |
| Docker Hub PAT (`DOCKERHUB_TOKEN`) | Docker Hub password | Password auth deprecated for Docker Hub API access since 2021; PAT is the only supported method |
| Wheels-only distribution for EE | EE sdist (source distribution) | sdist would ship `.py` source, defeating the source protection entirely; EE must publish binary wheels only |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pkg_resources.iter_entry_points()` | Deprecated since setuptools 67 (Jan 2023); emits DeprecationWarning; scheduled for removal | `importlib.metadata.entry_points(group="axiom.ee")` |
| Nuitka `--mode=module` for EE wheel distribution | No standard cibuildwheel integration; multi-module package compilation is underdocumented and fragile; larger `.so` output | Cython with `ext_modules` in `pyproject.toml` |
| `.pyx` Cython dialect for EE files | Requires rewriting all EE Python files; pure Python mode works on unmodified `.py` | Cython pure Python mode — compile `.py` files directly |
| Shipping `.py` files alongside `.so` in EE wheel | Python prefers `.py` over `.so` when both exist in the same location — the source would be imported, not the compiled module | Exclude all `.py` source from the EE wheel; use `MANIFEST.in` exclusions or set `package-data` to exclude `*.py` |
| EE sdist publishing | An sdist contains the original `.py` source files — defeats source protection | Configure EE CI to build and publish only binary wheels (`--no-sdist` flag in `python -m build`) |
| Cython in `requirements.txt` or runtime Docker image | Cython is a build-time dependency only; adding it to the runtime image adds ~50MB for zero benefit | Declare in `[build-system].requires` only; never in `requirements.txt` |
| Docker Hub password as a GitHub secret | Deprecated auth; will break when Docker Hub enforces token-only auth more broadly | Docker Hub PAT stored as `DOCKERHUB_TOKEN` secret |

---

## Stack Patterns by Variant

**EE private repo `pyproject.toml` — Cython build configuration:**
```toml
[build-system]
requires = ["setuptools>=77.0", "Cython>=3.2.4,<4"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-ee"
# ...

[tool.setuptools]
# Explicitly list all .py files to compile as extension modules
# so no source ships in the wheel
ext-modules = [
  {name = "ee.plugin", sources = ["ee/plugin.py"]},
  {name = "ee.routers.foundry_router", sources = ["ee/routers/foundry_router.py"]},
  # ... one entry per file
]
```

**EE CI wheel build (cibuildwheel in GitHub Actions):**
```yaml
- name: Build wheels
  uses: pypa/cibuildwheel@v3.4.0
  env:
    CIBW_BUILD: "cp312-manylinux_x86_64 cp312-manylinux_aarch64"
    CIBW_ARCHS_LINUX: "x86_64 aarch64"
    CIBW_BEFORE_BUILD: "pip install Cython>=3.2.4"
```

**CE startup entry_points discovery (updated `ee/__init__.py`):**
```python
from importlib.metadata import entry_points  # replaces: import pkg_resources

def load_ee_plugins(app, engine) -> EEContext:
    ctx = EEContext()
    try:
        plugins = entry_points(group="axiom.ee")  # replaces: pkg_resources.iter_entry_points(...)
        for ep in plugins:
            plugin_cls = ep.load()
            plugin = plugin_cls(app, engine)
            plugin.register(ctx)
            logger.info(f"Loaded EE plugin: {ep.name}")
        if not plugins:
            logger.info("No EE plugins found — running in CE mode")
    except Exception as e:
        logger.warning(f"EE plugin load failed ({e}), continuing in CE mode")
    return ctx
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Cython 3.2.4 | Python 3.9–3.13 | Pure Python mode (`.py` compilation) stable in Cython 3.x; tested against CPython 3.12 (project target) |
| cibuildwheel 3.4.0 | Cython 3.x, setuptools >=77 | Runs builds inside manylinux2014 containers (x86_64 native, aarch64 via QEMU) |
| importlib.metadata | Python 3.10+ (stdlib) | `entry_points(group=...)` keyword form requires Python 3.9+; project minimum is 3.10 |
| docker/login-action v3 | docker/build-push-action v6 | Both current major versions; already used in release.yml for GHCR |
| docker/metadata-action v6 | docker/build-push-action v6 | Same action generation; already in release.yml |

---

## Sources

- [Cython PyPI — version 3.2.4 confirmed](https://pypi.org/project/Cython/) — HIGH confidence (live PyPI, released 2026-01-04)
- [Nuitka PyPI — version 4.0.6 confirmed](https://pypi.org/project/Nuitka/) — HIGH confidence (live PyPI, released 2026-03-18)
- [Cython source files and compilation — official docs](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html) — HIGH confidence
- [Nuitka-Action v1.3 — module mode](https://github.com/Nuitka/Nuitka-Action) — HIGH confidence (official Nuitka GitHub)
- [cibuildwheel v3.4.0 — platform support](https://cibuildwheel.pypa.io/en/stable/platforms/) — HIGH confidence (pypa official docs)
- [Python Packaging — Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — HIGH confidence (packaging.python.org)
- [setuptools — Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) — HIGH confidence (official setuptools docs)
- [GitHub Docs — Publishing Docker images](https://docs.github.com/en/actions/publishing-packages/publishing-docker-images) — HIGH confidence (official GitHub docs)
- `.github/workflows/release.yml` in repo — existing Action versions (v3/v6) and GHCR pattern confirmed by direct review — HIGH confidence
- `.worktrees/axiom-split/puppeteer/agent_service/ee/__init__.py` — existing `pkg_resources` usage confirmed by direct review — HIGH confidence

---

*Stack research for: Axiom v11.0 — CE/EE Split Completion (Cython .so pipeline, entry_points EE wiring, Docker Hub CE publish)*
*Researched: 2026-03-19*

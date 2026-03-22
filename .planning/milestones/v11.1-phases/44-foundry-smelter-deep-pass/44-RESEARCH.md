# Phase 44: Foundry + Smelter Deep Pass — Research

**Researched:** 2026-03-21
**Domain:** Validation scripting — Foundry wizard flow, Smelter enforcement, air-gap mirror, build dir cleanup gap
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Script structure:**
- 6 individual scripts: `verify_foundry_NN_slug.py` — one per requirement
- 1 runner: `run_foundry_matrix.py` — thin orchestrator, calls all 6 in sequence, aggregates [PASS]/[FAIL], prints N/6 summary
- Operator can run any single script independently or all 6 via runner

**FOUNDRY-01 wizard flow (verify_foundry_01_wizard.py):**
- Dual coverage: API + Playwright
  - API layer first: POST blueprints (runtime + network), POST template, POST build trigger
  - Playwright second: drive the full 5-step wizard in the browser, assert build log appears, assert image tag visible in templates list
- Both portions in a single `verify_foundry_01_wizard.py`
- Final assertion: `GET /api/foundry/images` or `docker images` confirms the new tag exists
- No node deployment required

**FOUNDRY-02 Smelter STRICT mode (verify_foundry_02_strict_cve.py):**
- Add `cryptography<40.0.0` as an ingredient
- Confirm STRICT mode blocks the blueprint from being used in a build
- Assert API returns non-200 response with clear error detail

**FOUNDRY-03 build failure edge case (verify_foundry_03_build_failure.py):**
- Trigger a build with a bad base image tag
- Assert `POST /api/templates/{id}/build` returns HTTP 500 with error detail (not silent 200)

**FOUNDRY-04 build dir cleanup — gap test (verify_foundry_04_build_dir.py):**
- PASS = gap confirmed: assert the temp build dir STILL EXISTS after a completed build
- Method: glob `/tmp/puppet_build_*` inside the agent container via `docker exec` before build, trigger build, glob again after
- Print: `[PASS] FOUNDRY-04: MIN-7 gap confirmed — build dir /tmp/puppet_build_... not cleaned up after successful build`

**FOUNDRY-05 air-gap mirror (verify_foundry_05_airgap.py):**
- Script manages iptables rules on the Docker host
  - `sudo iptables -I OUTPUT -d pypi.org -j DROP`
  - `sudo iptables -I OUTPUT -d files.pythonhosted.org -j DROP`
- Rules added before build, removed in finally block after assertion
- Ingredient selection: query `GET /api/smelter/ingredients` at runtime, find first ingredient with `mirror_status=MIRRORED`
- Build a blueprint using that mirrored ingredient, trigger build with iptables block active
- Assert build succeeds

**FOUNDRY-06 Smelter WARNING mode (verify_foundry_06_warning.py):**
- Add a moderate-risk ingredient in WARNING mode
- Assert build proceeds (non-500 response)
- Assert audit log records the warning (query `GET /admin/audit-log` after build)

**Specifics:**
- FOUNDRY-04 prints the exact build dir path found with size
- FOUNDRY-05 iptables rules always removed in a `finally` block
- FOUNDRY-01 Playwright uses CF Access headers if dashboard behind CF Access

### Claude's Discretion

- Exact polling backoff between build trigger and build-complete assertion
- Playwright selector strategy for 5-step wizard (CSS vs aria-label vs test IDs)
- Pre-flight failure messages and exact remediation commands printed when preconditions not met
- Exact wait/retry loop after iptables rules are added before triggering build
- `docker images` vs `GET /api/foundry/images` for final image tag assertion in FOUNDRY-01

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUNDRY-01 | Full wizard flow: create runtime blueprint → create network blueprint → build image via Foundry → verify image tag in Docker → deploy a node from the Foundry-built image | API call sequence identified; Playwright wizard steps 1-5 mapped; image tag assertion pattern confirmed |
| FOUNDRY-02 | Smelter STRICT mode: attempt to add an ingredient with a known CVE (`cryptography<40.0.0`); confirm STRICT mode blocks the blueprint from being used in a build | STRICT enforcement path in `foundry_service.py` line 58-59 confirmed; returns HTTP 403 not 500; API to set mode: `PATCH /api/smelter/config` |
| FOUNDRY-03 | Build failure edge case: trigger a build failure (bad base image tag); confirm API returns HTTP 500 with error detail, not silent 200 | `build_template` route in `foundry_router.py` line 199-203 raises HTTPException 500 when status doesn't start with "SUCCESS"; bad base_os triggers Docker build failure |
| FOUNDRY-04 | Build dir cleanup: after a completed build, confirm temp build directory is removed (MIN-7 gap test — expect failure, document finding) | `foundry_service.py` finally block at line 241-243 DOES `shutil.rmtree` — gap may be already fixed; script must verify empirically via `docker exec` |
| FOUNDRY-05 | Air-gap mirror: configure a blueprint to use the local PyPI mirror, block outbound internet via `iptables`, confirm pip install of ingredient succeeds from mirror | Mirror URL is injected into every Foundry build via `pip.conf` (MirrorService.get_pip_conf_content); iptables block pattern established in CONTEXT.md |
| FOUNDRY-06 | Smelter warning mode: add a moderate-risk ingredient in WARNING mode; confirm build proceeds but audit log records the warning | WARNING path at `foundry_service.py` line 61 logs warning and sets `tmpl.is_compliant = False`; audit log write comes via `audit()` call in build route |
</phase_requirements>

## Summary

Phase 44 is a pure validation scripting phase — no application code changes. It produces 6 `verify_foundry_*.py` scripts plus `run_foundry_matrix.py`, all placed in `mop_validation/scripts/`, following the identical pattern established by Phase 43's job matrix scripts. All scripts run against the live EE stack at `https://localhost:8001`.

The Foundry and Smelter APIs are EE-only, routed through `foundry_router.py` and `smelter_router.py`. The key enforcement mechanism lives in `foundry_service.py::build_template()`: after fetching blueprints, it calls `SmelterService.validate_blueprint()` which returns a list of packages NOT present in `approved_ingredients` table. If `smelter_enforcement_mode` Config row is `STRICT` and there are unapproved packages, the build raises HTTP 403. The `build_template` route in `foundry_router.py` then raises HTTP 500 on any non-SUCCESS status — creating a two-layer response chain that scripts must account for.

**Critical finding:** The build dir cleanup gap (MIN-7/FOUNDRY-04) may already be partially addressed. `foundry_service.py` has a `finally` block at line 241-243 that calls `shutil.rmtree(build_dir)`. The FOUNDRY-04 script must empirically verify whether the dir actually persists or is cleaned up — the test assertion depends on what actually happens in the live container, not the code reading.

**Primary recommendation:** Scripts follow the verify_job_01 pattern exactly. Pre-flight guards for EE licence and foundry feature flag. API portion runs first (fast, no browser needed). Playwright portion runs second (wizard steps 1-5 in BlueprintWizard.tsx).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | >=2.31 | HTTP API calls against stack | Already used in all Phase 43 scripts |
| playwright (sync_api) | >=1.40 | Browser automation for wizard flow | Already installed in validation env |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess | stdlib | `docker exec` for build dir glob and iptables | FOUNDRY-04 and FOUNDRY-05 |
| pathlib | stdlib | Path construction for secrets.env, signing key | All scripts |
| time | stdlib | Poll loops for build completion | FOUNDRY-01, FOUNDRY-05, FOUNDRY-06 |

### No New Dependencies
All required libraries are already present in the mop_validation environment from Phase 43 work.

**Installation:** No additional installs required. Playwright chromium already installed.

## Architecture Patterns

### Recommended Project Structure
```
mop_validation/scripts/
├── verify_foundry_01_wizard.py       # FOUNDRY-01: API + Playwright wizard flow
├── verify_foundry_02_strict_cve.py   # FOUNDRY-02: STRICT mode CVE block
├── verify_foundry_03_build_failure.py # FOUNDRY-03: Bad base image → HTTP 500
├── verify_foundry_04_build_dir.py    # FOUNDRY-04: MIN-7 gap documentation
├── verify_foundry_05_airgap.py       # FOUNDRY-05: iptables block + mirror install
├── verify_foundry_06_warning.py      # FOUNDRY-06: WARNING mode + audit log
└── run_foundry_matrix.py             # Runner: calls all 6, N/6 summary
```

### Pattern 1: Shared Script Header (copy from verify_job_01_fast.py)
**What:** Every script opens with ROOT/MOP_DIR/VALIDATION_DIR path setup, load_env(SECRETS_ENV), wait_for_stack(), get_admin_token().
**When to use:** Every verify_foundry_*.py file.
```python
# Source: mop_validation/scripts/verify_job_01_fast.py (established pattern)
ROOT = Path(__file__).resolve().parents[2]   # .../Development/
MOP_DIR = ROOT / "master_of_puppets"
VALIDATION_DIR = ROOT / "mop_validation"
SECRETS_ENV = MOP_DIR / "secrets.env"
BASE_URL = "https://localhost:8001"

def load_env(path): ...
def wait_for_stack(base_url, timeout=90): ...
def get_admin_token(base_url, password): ...
```

### Pattern 2: EE Feature Pre-flight Guard
**What:** Before any Foundry operation, assert `GET /api/features` shows `foundry: true`. Exit [SKIP] not [FAIL] if EE not active — same pattern as node ONLINE pre-flights in Phase 43.
**When to use:** Every verify_foundry_*.py.
```python
features = requests.get(f"{BASE_URL}/api/features", verify=False).json()
if not features.get("foundry"):
    print("[SKIP] FOUNDRY-XX: EE foundry feature not active — is EE licence loaded?")
    print("       Check: GET /api/features; ensure AXIOM_LICENCE_KEY is set")
    sys.exit(0)
```

### Pattern 3: Build Polling Loop
**What:** `POST /api/templates/{id}/build` is synchronous (blocks until Docker build completes). No polling needed — it returns when done. However, build can take 30-120s, so use a long HTTP timeout (180s minimum).
**When to use:** FOUNDRY-01, FOUNDRY-02, FOUNDRY-03, FOUNDRY-05, FOUNDRY-06.
```python
resp = requests.post(
    f"{BASE_URL}/api/templates/{tmpl_id}/build",
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False,
    timeout=180,   # Docker build is synchronous — must wait it out
)
```

### Pattern 4: Smelter Enforcement Mode Toggle
**What:** PATCH `/api/smelter/config` to set mode. Always restore in a `finally` block.
**When to use:** FOUNDRY-02 (STRICT), FOUNDRY-06 (WARNING).
```python
# Source: smelter_router.py PATCH /api/smelter/config
original_mode = requests.get(f"{BASE_URL}/api/smelter/config", ...).json()["smelter_enforcement_mode"]
try:
    requests.patch(f"{BASE_URL}/api/smelter/config",
        json={"smelter_enforcement_mode": "STRICT"}, ...)
    # ... test ...
finally:
    requests.patch(f"{BASE_URL}/api/smelter/config",
        json={"smelter_enforcement_mode": original_mode}, ...)
```

### Pattern 5: run_foundry_matrix.py Runner
**What:** Identical to `run_job_matrix.py` — sequential subprocess calls, [PASS]/[FAIL] per script, N/6 summary. Rate-limit guard may not be needed (Foundry scripts run fewer login calls) but include it defensively.
**When to use:** The top-level runner only.

### Pattern 6: Playwright Context for localhost (no CF Access needed)
**What:** The existing `test_playwright.py` uses `http://localhost:8080` without CF Access headers. The CONTEXT.md notes CF Access headers are needed "if the dashboard is behind CF Access." Since tests run locally against `https://localhost` (Caddy), no CF Access needed — Caddy serves locally without the CF tunnel.
**When to use:** FOUNDRY-01 Playwright portion.
```python
# Source: test_playwright.py lines 64-70
browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
context = browser.new_context(ignore_https_errors=True, viewport={"width": 1400, "height": 900})
page = context.new_page()
# Login via React native value setter (see MEMORY.md — fill() alone doesn't update React state)
page.goto("https://localhost", timeout=15000)
```

### Pattern 7: docker exec for Build Dir Glob (FOUNDRY-04)
**What:** Run `docker exec <agent_container> ls /tmp/` or `find /tmp -maxdepth 1 -name "puppet_build_*"` to detect build dirs from outside the container.
**When to use:** FOUNDRY-04 only.
```python
# Source: CONTEXT.md decision + CLAUDE.md pattern
result = subprocess.run(
    ["docker", "exec", "puppeteer-agent-1",
     "find", "/tmp", "-maxdepth", "1", "-name", "puppet_build_*"],
    capture_output=True, text=True
)
dirs_after = [l for l in result.stdout.splitlines() if l.strip()]
```

### Anti-Patterns to Avoid
- **Using `npm run dev` or local dev servers for testing:** CLAUDE.md explicitly forbids. All tests use `https://localhost:8001` (Caddy → agent).
- **Hardcoding `puppeteer-postgres-1`:** Phase 43 learned to discover container names dynamically via `docker ps --filter`.
- **Setting `fill()` alone in Playwright for React inputs:** MEMORY.md documents this breaks React controlled components. Use native value setter + `dispatchEvent('input')`.
- **Leaving iptables rules on test failure:** FOUNDRY-05 must use `finally` block — rules are host-level and persist after process exit.
- **Assuming `list_images()` is populated:** `FoundryService.list_images()` returns `[]` always (stub). Use `docker images` via subprocess or check template's `current_image_uri` from `GET /api/templates` instead.
- **Using `POST /api/foundry/build/{id}`:** Route is `POST /api/templates/{id}/build` (not `/api/foundry/build`). The CONTEXT.md has a typo — check foundry_router.py line 197 for the correct route.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image tag assertion | Custom Docker API client | `docker images --format '{{.Repository}}:{{.Tag}}'` via subprocess OR check template's `current_image_uri` from `GET /api/templates` | Simpler, no auth needed |
| Build dir existence check | Agent API endpoint | `docker exec puppeteer-agent-1 find /tmp -name "puppet_build_*"` | Direct, no new routes needed |
| Network isolation | Custom bridge network | `sudo iptables -I OUTPUT -d pypi.org -j DROP` (host-level) | Only way to block Docker build container network |
| MIRRORED ingredient discovery | Hard-coded ingredient name | `GET /api/smelter/ingredients` + filter `mirror_status=MIRRORED` | Proves real mirror path, not synthetic |

## Common Pitfalls

### Pitfall 1: STRICT Mode Returns 403, Route Raises 500
**What goes wrong:** FOUNDRY-02 expects "non-200" — but the actual status codes are 403 from `foundry_service.py` (raised before `build_template` route sees it) since `raise HTTPException(status_code=403, ...)` propagates directly. The route's own 500-raising logic (`if not result.status.startswith("SUCCESS"): raise HTTPException(500, ...)`) is never reached.
**Why it happens:** `HTTPException` from service layer propagates through FastAPI before the route's post-processing.
**How to avoid:** In FOUNDRY-02, assert `resp.status_code in (403, 500)` — accept either. The CONTEXT.md says "non-200 response with clear error detail" so both are valid.
**Warning signs:** Test asserting `== 500` fails even though STRICT mode is working correctly.

### Pitfall 2: FOUNDRY-04 Gap May Be Already Fixed
**What goes wrong:** `foundry_service.py` lines 241-243 show a `finally` block that calls `shutil.rmtree(build_dir)`. The build dir may already be cleaned up in the live stack.
**Why it happens:** The `finally` block was present in the code reviewed — MIN-7 may have been fixed without the gap report being updated.
**How to avoid:** FOUNDRY-04 must detect empirically. If no build dir found post-build, the script should print `[PASS] FOUNDRY-04: MIN-7 appears FIXED — no build dir found after successful build` and exit 0. If found, print the gap documentation. Both outcomes are valid test results.
**Warning signs:** Test always fails because it was written to assert dir presence when it's actually gone.

### Pitfall 3: Blueprint "Unapproved" vs "Vulnerable"
**What goes wrong:** FOUNDRY-02 intent is to test CVE blocking. But `SmelterService.validate_blueprint()` only checks if a package NAME is in `approved_ingredients` — it does NOT check `is_vulnerable`. Adding `cryptography<40.0.0` to an ingredient list in a blueprint without registering `cryptography` as an approved ingredient will trigger STRICT rejection because the package is "unapproved", not because it's "vulnerable."
**Why it happens:** The CVE/vulnerability enforcement is a two-step process: (1) ingredients registered with `is_vulnerable=True` are blocked at the ingredient level; (2) packages not in the registry at all are blocked as unapproved. The test works either way — the key is STRICT mode rejects.
**How to avoid:** For FOUNDRY-02 the test should either: (a) add `cryptography` to the blueprint packages WITHOUT registering it as an approved ingredient (unapproved path), OR (b) register it as an ingredient, run `POST /api/smelter/scan` to get it flagged `is_vulnerable=True`, then attempt build. Path (a) is simpler and deterministic.
**Warning signs:** Script registers `cryptography<40.0.0` as an approved ingredient before attempting build — then STRICT mode won't block it because it IS in the registry.

### Pitfall 4: BlueprintWizard Requires Approved OS Entry
**What goes wrong:** FOUNDRY-01 Playwright wizard step 2 (Base Image) shows a dropdown filtered by `GET /api/approved-os` — if no entries exist for DEBIAN, the step shows "No approved images found" and wizard can't proceed.
**Why it happens:** `Step2BaseOS` in `BlueprintWizard.tsx` filters `approvedOS` by `os_family === composition.os_family`. Fresh EE stack may have no seeded approved OS entries.
**How to avoid:** FOUNDRY-01 API portion should seed an approved OS entry via `POST /api/approved-os` before the Playwright portion runs, OR the API portion creates the blueprint directly (bypassing the wizard's OS restriction). The Playwright portion can then navigate directly to a template that was already created by the API portion and click "Build."
**Warning signs:** Playwright wizard hangs on step 2 with empty OS list.

### Pitfall 5: Mirror Check Blocks Build Even with iptables
**What goes wrong:** FOUNDRY-05 aims to prove that a package installs from the local mirror when outbound internet is blocked. But `foundry_service.py` line 79-83 checks `mirror_status` before building — if the ingredient is not `MIRRORED` in the DB, the build is rejected with HTTP 403 before Docker even starts.
**Why it happens:** The mirror_status DB check is a pre-build gate. The iptables block happens at Docker layer, but the service-level gate runs first.
**How to avoid:** FOUNDRY-05 must use an ingredient that already has `mirror_status=MIRRORED` — which is exactly what the CONTEXT.md says (query `GET /api/smelter/ingredients`, find first with `mirror_status=MIRRORED`). The iptables block then proves the pip install used the local mirror URL from `pip.conf` (not pypi.org), since pypi.org is blocked.
**Warning signs:** Build returns 403 (not a Docker-layer failure) even with iptables set up correctly.

### Pitfall 6: Build Timeout on Slow Images
**What goes wrong:** `requests.post(..., timeout=30)` times out on a real Docker build that takes 60-90 seconds.
**Why it happens:** `build_template()` in foundry_service.py is synchronous from the HTTP perspective — it blocks the request until Docker completes.
**How to avoid:** Use `timeout=180` (3 minutes) minimum for all build-triggering requests.

### Pitfall 7: Foundry Route Prefix Confusion
**What goes wrong:** CONTEXT.md mentions `POST /api/foundry/build/{id}` — this route does NOT exist. The correct routes are:
- `POST /api/templates/{id}/build` — trigger a build for a specific template
- `POST /foundry/build` — dashboard alias that takes `{"template_id": "..."}` in body
**Why it happens:** Early planning used a different route naming scheme.
**How to avoid:** Always use `POST /api/templates/{id}/build`. Confirmed in `foundry_router.py` line 197.

## Code Examples

Verified patterns from source code:

### Create Runtime Blueprint
```python
# Source: foundry_router.py POST /api/blueprints (line 33)
resp = requests.post(f"{BASE_URL}/api/blueprints", json={
    "type": "RUNTIME",
    "name": "test-runtime-01",
    "os_family": "DEBIAN",
    "definition": {
        "base_os": "debian:12-slim",
        "tools": [],
        "packages": {"python": ["requests"]}
    }
}, headers={"Authorization": f"Bearer {jwt}"}, verify=False, timeout=30)
# Returns 201 on success
```

### Create Network Blueprint
```python
# Source: foundry_router.py POST /api/blueprints (line 33)
resp = requests.post(f"{BASE_URL}/api/blueprints", json={
    "type": "NETWORK",
    "name": "test-network-01",
    "definition": {
        "policy": "deny-all",
        "egress_rules": []
    }
}, headers={"Authorization": f"Bearer {jwt}"}, verify=False, timeout=30)
# Returns 201 on success. No os_family needed for NETWORK type.
```

### Create Template
```python
# Source: foundry_router.py POST /api/templates (line 148)
resp = requests.post(f"{BASE_URL}/api/templates", json={
    "friendly_name": "test-template-01",
    "runtime_blueprint_id": rt_bp_id,
    "network_blueprint_id": nw_bp_id,
}, headers={"Authorization": f"Bearer {jwt}"}, verify=False, timeout=30)
# Returns 200 on success (note: not 201)
```

### Trigger Build and Handle Response
```python
# Source: foundry_router.py POST /api/templates/{id}/build (line 197-204)
resp = requests.post(
    f"{BASE_URL}/api/templates/{tmpl_id}/build",
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False,
    timeout=180,   # CRITICAL: Docker build is synchronous
)
# 200 = success (ImageResponse with status starting "SUCCESS")
# 500 = build failed (detail contains error message)
# 403 = STRICT mode rejection (unapproved ingredients)
```

### Set Smelter Enforcement Mode
```python
# Source: smelter_router.py PATCH /api/smelter/config (line 75)
requests.patch(f"{BASE_URL}/api/smelter/config",
    json={"smelter_enforcement_mode": "STRICT"},
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10)
```

### Query Audit Log (FOUNDRY-06)
```python
# Source: audit_router.py GET /admin/audit-log (EE router)
resp = requests.get(f"{BASE_URL}/admin/audit-log",
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False, timeout=10)
entries = resp.json()
# Filter for smelter warning entries — look for entries with action containing "smelter" or "WARNING"
# foundry_service.py line 61: logger.warning(...) — this may NOT write to audit log
# The audit() call is at foundry_router.py line 202 (template:build) — after build succeeds
# For WARNING mode, the is_compliant=False is set on the template, check via GET /api/templates
```

### Check Build Dir (FOUNDRY-04)
```python
# Source: foundry_service.py line 152 — build_dir pattern
# Pattern: /tmp/puppet_build_{tmpl.id}_{md5_hash[:8]}
result = subprocess.run(
    ["docker", "exec", "puppeteer-agent-1",
     "find", "/tmp", "-maxdepth", "1", "-name", "puppet_build_*", "-type", "d"],
    capture_output=True, text=True, timeout=10
)
dirs = [l.strip() for l in result.stdout.splitlines() if l.strip()]
```

### Playwright Login (React native value setter)
```python
# Source: MEMORY.md — "fill() alone doesn't update React controlled state"
page.evaluate(f"""
    const u = document.querySelector("input[name='username'], input[type='text']");
    const p = document.querySelector("input[name='password'], input[type='password']");
    const nv = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
    nv.set.call(u, '{admin_username}');
    u.dispatchEvent(new Event('input', {{bubbles: true}}));
    nv.set.call(p, '{admin_password}');
    p.dispatchEvent(new Event('input', {{bubbles: true}}));
""")
page.locator("button[type='submit']").click()
# After login, reload page to bootstrap React
token = page.evaluate("() => localStorage.getItem('mop_auth_token')")
if token:
    page.reload()
    page.wait_for_load_state("networkidle", timeout=15000)
```

### Playwright Wizard Navigation
```python
# Source: BlueprintWizard.tsx — 5 steps: Identity, Base Image, Ingredients, Tools, Review
# Step indicator: "Step {step} of 5:" text
# Next button: "Next" with ArrowRight icon, disabled when step invalid
# Progress bar: div elements with class "h-1 flex-1 rounded-full"
page.goto("https://localhost/templates", timeout=15000)
# Click "New Blueprint" or equivalent button to open wizard dialog
# Step 1: Fill name, select OS Family
# Step 2: Select base image from approved-os list
# Step 3: Select ingredients from approved-ingredients list
# Step 4: Select tools from capability matrix
# Step 5: Review and submit
```

## State of the Art (This Codebase)

| Aspect | Implementation | Impact |
|--------|---------------|--------|
| Smelter enforcement | DB Config key `smelter_enforcement_mode` (STRICT/WARNING) | Toggle via `PATCH /api/smelter/config` — no restart needed |
| Build dir cleanup | `finally: shutil.rmtree(build_dir)` in foundry_service.py | MIN-7 gap may be resolved — empirical test required |
| Mirror injection | `pip.conf` copied into every build context | All builds use local mirror URL by default; iptables blocks only confirm pip can't reach pypi.org |
| Image tag confirmation | Template's `current_image_uri` field set on successful build | `GET /api/templates` returns `current_image_uri = "localhost:5000/puppet:{friendly_name}"` |
| list_images stub | `FoundryService.list_images()` returns `[]` | Cannot use `GET /api/images` for image presence check; use template field or `docker images` |

**Deprecated/outdated:**
- `POST /api/foundry/build/{id}`: Referenced in CONTEXT.md but this route path does not exist; correct path is `POST /api/templates/{id}/build`
- `GET /api/foundry/images`: Mentioned in CONTEXT.md, this is `GET /api/images` in foundry_router.py which calls the stub returning `[]`

## Open Questions

1. **Does FOUNDRY-06 WARNING mode actually write to audit log?**
   - What we know: `foundry_service.py` line 61 calls `logger.warning()` (Python logger, not audit log). The audit call at `foundry_router.py` line 202 runs AFTER a successful build and logs `"template:build"` — but not specifically the WARNING.
   - What's unclear: Whether the audit log entry for a WARNING-mode build contains enough information to distinguish it from a clean build.
   - Recommendation: FOUNDRY-06 should check `template.is_compliant == False` from `GET /api/templates` as the primary assertion (this IS set by foundry_service.py line 62). The audit log assertion should look for the `"template:build"` entry and note that `is_compliant=False` on the template is the documented WARNING signal. If no specific "WARNING" audit entry exists, document this as a gap finding.

2. **Is there an approved OS entry seeded in the EE stack?**
   - What we know: `GET /api/approved-os` returns entries from the `approved_os` table. No seed data confirmed in the code review.
   - What's unclear: Whether Phase 42 EE stack setup created any `approved_os` rows.
   - Recommendation: FOUNDRY-01 pre-flight should call `GET /api/approved-os` and seed one via `POST /api/approved-os` if empty (using `debian:12-slim` / DEBIAN family). This is non-destructive.

3. **Does the local PyPI mirror (devpi/pypi sidecar) have any packages available?**
   - What we know: `GET /api/smelter/mirror-health` checks port 8080 on `pypi` hostname. The mirror is a sidecar in compose.server.yaml.
   - What's unclear: Whether the mirror sidecar is running in the current EE stack and has any `MIRRORED` ingredients in the DB.
   - Recommendation: FOUNDRY-05 pre-flight should call `GET /api/smelter/ingredients` and check for `mirror_status=MIRRORED`. If none found, script should print `[SKIP] FOUNDRY-05: No MIRRORED ingredients found — seed one via POST /api/smelter/ingredients and wait for background mirroring` and exit 0. This prevents false failures when the mirror isn't set up.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer/agent_service/tests/) — but Phase 44 scripts are standalone CLI scripts, not pytest |
| Config file | none — scripts are self-contained, run directly |
| Quick run command | `python3 mop_validation/scripts/verify_foundry_01_wizard.py` |
| Full suite command | `python3 mop_validation/scripts/run_foundry_matrix.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUNDRY-01 | Wizard flow creates image in Docker | integration | `python3 mop_validation/scripts/verify_foundry_01_wizard.py` | ❌ Wave 0 |
| FOUNDRY-02 | STRICT mode blocks unapproved blueprint | integration | `python3 mop_validation/scripts/verify_foundry_02_strict_cve.py` | ❌ Wave 0 |
| FOUNDRY-03 | Bad base image → HTTP 500 | integration | `python3 mop_validation/scripts/verify_foundry_03_build_failure.py` | ❌ Wave 0 |
| FOUNDRY-04 | Build dir gap documentation | integration | `python3 mop_validation/scripts/verify_foundry_04_build_dir.py` | ❌ Wave 0 |
| FOUNDRY-05 | Air-gap mirror install succeeds | integration | `python3 mop_validation/scripts/verify_foundry_05_airgap.py` | ❌ Wave 0 |
| FOUNDRY-06 | WARNING mode proceeds + is_compliant=False | integration | `python3 mop_validation/scripts/verify_foundry_06_warning.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 mop_validation/scripts/verify_foundry_01_wizard.py` (smoke)
- **Per wave merge:** `python3 mop_validation/scripts/run_foundry_matrix.py`
- **Phase gate:** All 6 scripts [PASS] or documented [SKIP] before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/verify_foundry_01_wizard.py` — covers FOUNDRY-01
- [ ] `mop_validation/scripts/verify_foundry_02_strict_cve.py` — covers FOUNDRY-02
- [ ] `mop_validation/scripts/verify_foundry_03_build_failure.py` — covers FOUNDRY-03
- [ ] `mop_validation/scripts/verify_foundry_04_build_dir.py` — covers FOUNDRY-04
- [ ] `mop_validation/scripts/verify_foundry_05_airgap.py` — covers FOUNDRY-05
- [ ] `mop_validation/scripts/verify_foundry_06_warning.py` — covers FOUNDRY-06
- [ ] `mop_validation/scripts/run_foundry_matrix.py` — runner for all 6

## Sources

### Primary (HIGH confidence)
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/foundry_service.py` — build_template() implementation, build_dir path pattern, finally block, STRICT/WARNING enforcement
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/smelter_service.py` — validate_blueprint() logic (unapproved = not in registry)
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/ee/routers/foundry_router.py` — all Foundry API routes, correct paths, HTTP status codes
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/ee/routers/smelter_router.py` — PATCH /api/smelter/config route, ingredient management
- `/home/thomas/Development/axiom-ee/ee/foundry/models.py` — Blueprint, PuppetTemplate, ApprovedOS DB models
- `/home/thomas/Development/axiom-ee/ee/smelter/models.py` — ApprovedIngredient with is_vulnerable, mirror_status fields
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/mirror_service.py` — get_pip_conf_content() shows PYPI_MIRROR_URL injection
- `/home/thomas/Development/master_of_puppets/puppeteer/dashboard/src/components/foundry/BlueprintWizard.tsx` — 5-step wizard structure, step rendering, selector patterns
- `/home/thomas/Development/mop_validation/scripts/verify_job_01_fast.py` — canonical script pattern to mirror exactly
- `/home/thomas/Development/mop_validation/scripts/run_job_matrix.py` — canonical runner pattern to mirror exactly

### Secondary (MEDIUM confidence)
- `.planning/phases/44-foundry-smelter-deep-pass/44-CONTEXT.md` — user decisions, integration points, reusable assets
- `MEMORY.md` (project memory) — Playwright React login pattern, blueprint package format, EXECUTION_MODE notes
- `.planning/STATE.md` — accumulated decisions from all prior phases

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already present in validation env
- Architecture patterns: HIGH — source code read directly; all API routes and DB models verified
- Pitfalls: HIGH — derived from direct code reading (not hypothesis); FOUNDRY-04 build dir finding is a critical empirical question
- Validation approach: HIGH — mirrors Phase 43 pattern exactly

**Research date:** 2026-03-21
**Valid until:** 2026-04-20 (stable codebase; no API changes expected)

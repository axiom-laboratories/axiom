# Phase 85: Screenshot Capture — Research

**Status:** RESEARCH COMPLETE
**Date:** 2026-03-29

---

## What I Need to Know to Plan This Phase Well

### Phase Goal
A Python Playwright script seeds demo data against a live Docker stack, captures 10 named PNG screenshots at 1440×900, and writes them to `docs/docs/assets/screenshots/` and `homepage/assets/screenshots/`. Getting-started docs, feature guide pages, and the marketing homepage (`homepage/index.html`) are updated to embed the screenshots.

---

## Codebase Survey

### Existing Tool Infrastructure

| File | Status | Relevance |
|------|--------|-----------|
| `puppeteer/dashboard/generate_screenshots.py` | Outdated draft | Wrong localStorage key (`token` vs `mop_auth_token`), dummy JWT, stale nav labels — structural reference only, replace entirely |
| `mop_validation/scripts/test_playwright.py` | Working reference | Correct auth pattern: form-encoded login, `mop_auth_token` key, `--no-sandbox` launch, `wait_for_load_state` — use as blueprint |
| `mop_validation/scripts/test_local_stack.py` | Working reference | Shows `secrets.env` parsing pattern for `ADMIN_PASSWORD` credential loading |
| `tools/example-jobs/` | Phase 83 artifact | Signed corpus jobs in bash/python/pwsh + `manifest.yaml` — can dispatch these for seeding |

### tools/ Directory
- `tools/__init__.py` exists — directory already established as a Python package location
- `tools/example-jobs/` contains the Phase 83 job library with `manifest.yaml`
- New `capture_screenshots.py` fits here alongside other operator tooling

### Asset Directories
- `docs/docs/assets/` — currently only `logo.svg` — **add `screenshots/` subdirectory**
- `homepage/assets/` — currently empty — **add `screenshots/` subdirectory**
- Both directories already exist; subdirectories need creation (or `os.makedirs(..., exist_ok=True)`)

### Docs Files to Update

**Getting-started:**
- `docs/docs/getting-started/enroll-node.md` — add `nodes.png` and `node_detail.png`
- `docs/docs/getting-started/first-job.md` — add `jobs.png` and `job_detail.png`

**Feature guides (confirmed present):**
- `docs/docs/feature-guides/foundry.md` — add `foundry.png`
- `docs/docs/feature-guides/job-scheduling.md` — add `scheduled_jobs.png`
- There is no dedicated audit guide file — use `audit.png` in a fitting page or skip (Claude's discretion per CONTEXT.md)

**Marketing:**
- `homepage/index.html` — add "See it in action" section with 3–4 `<img>` tags

---

## Playwright Authentication Pattern (from working reference)

```python
# 1. Get token (form-encoded, not JSON)
import requests
r = requests.post(f"{BASE_URL}/api/auth/login",
                  data={"username": "admin", "password": ADMIN_PASSWORD},
                  verify=False)
token = r.json()["access_token"]

# 2. Launch Playwright with --no-sandbox (required on Linux per CLAUDE.md)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # 3. Inject JWT into localStorage before navigating
    page.goto(f"{BASE_URL}/login")
    page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")

    # 4. Navigate to target route
    page.goto(f"{BASE_URL}/nodes")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="docs/docs/assets/screenshots/nodes.png")
```

Key constraints:
- `args=['--no-sandbox']` is mandatory (CLAUDE.md — Linux Chrome crashes without it)
- `mop_auth_token` is the correct localStorage key (not `token`, not `auth_token`)
- `wait_for_load_state("networkidle")` preferred over `asyncio.sleep` for reliability
- Form-encoded POST for login, not JSON
- Default URL is `http://localhost:8080` (Caddy in Docker stack)

---

## Data Seeding Strategy

**Prerequisites (operator-side):**
- At least one enrolled node (script does NOT start a node)
- `puppeteer/secrets.env` must contain `ADMIN_PASSWORD`

**Script-side seeding:**
1. Read `ADMIN_PASSWORD` from `puppeteer/secrets.env` using the same `load_env()` pattern as `test_local_stack.py`
2. Authenticate via `POST /api/auth/login` to get JWT
3. Register an ephemeral Ed25519 signing keypair (generate inline with `cryptography` library)
4. Register the public key via `POST /api/signatures` → get `signature_id`
5. Seed 4–5 jobs (mix of COMPLETED, FAILED, PENDING) by dispatching signed scripts:
   - Python hello-world → completes quickly → COMPLETED status
   - Python sleep script → dispatched last → may be PENDING when screenshot runs
   - Python script with deliberate exception → FAILED status
6. Wait for at least 2–3 jobs to reach terminal state before capturing

**Signing inline (no external key file required):**
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64

# Generate ephemeral keypair
priv = Ed25519PrivateKey.generate()
pub_pem = priv.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

# Sign a script
def sign_script(private_key, script_content: str) -> str:
    sig = private_key.sign(script_content.encode("utf-8"))
    return base64.b64encode(sig).decode()
```

---

## Screenshot Capture Plan (10 screenshots)

| # | Filename | Route | Special action |
|---|----------|-------|----------------|
| 1 | `login.png` | `/login` | No auth — capture before JWT injection |
| 2 | `dashboard.png` | `/` | None |
| 3 | `nodes.png` | `/nodes` | None |
| 4 | `node_detail.png` | `/nodes` | Click first node row to open drawer |
| 5 | `jobs.png` | `/jobs` | None |
| 6 | `job_detail.png` | `/jobs` | Click a COMPLETED job row to open panel |
| 7 | `queue.png` | `/queue` | None |
| 8 | `history.png` | `/history` | None |
| 9 | `scheduled_jobs.png` | `/scheduled-jobs` | None |
| 10 | `foundry.png` | `/templates` | None |
| 11 | `audit.png` | `/audit` | None |

Note: CONTEXT.md specifies 10 screenshots in the numbered list but 11 items (including `audit.png`). Plans should capture all 11 — exceeds the "8+" minimum for SCR-01.

---

## Drawer/Panel Interaction

For `node_detail.png` and `job_detail.png`, a click is needed to open the panel:

```python
# Open node drawer — click first row
page.goto(f"{BASE_URL}/nodes")
page.wait_for_load_state("networkidle")
page.locator("table tbody tr").first.click()
page.wait_for_timeout(500)  # Allow drawer animation
page.screenshot(path="docs/docs/assets/screenshots/node_detail.png")
```

For job detail, click a COMPLETED job row specifically (so the panel shows meaningful data, not just PENDING).

---

## --check Pre-flight Flag

```
python tools/capture_screenshots.py --check
```

Should verify:
1. Stack reachable (`GET /api/health` or `GET /` returns 200)
2. Admin credentials valid (`POST /api/auth/login` succeeds)
3. At least one enrolled ONLINE node exists (`GET /api/nodes` → count > 0)

On any failure: print a clear error message and exit 1.
On success: print "Pre-flight OK. Ready to capture." and exit 0.

---

## Docs Integration Pattern

Standard markdown inline images:
```markdown
![Nodes page showing enrolled nodes](../assets/screenshots/nodes.png)
```

Insert at natural visual break points — after step instructions, before the next section. Not inline mid-paragraph.

The `../assets/screenshots/` relative path works from both `getting-started/` and `feature-guides/` subdirectories (docs are one level deep under `docs/docs/`).

---

## Homepage Integration Pattern

Add a new section to `homepage/index.html` before the existing feature list or after the pain points:

```html
<!-- See it in action -->
<section class="section showcase-section">
  <div class="container">
    <p class="section-label">See it in action</p>
    <h2>The dashboard your operators will actually use</h2>
    <div class="screenshot-grid">
      <img src="assets/screenshots/dashboard.png" alt="Axiom dashboard overview" />
      <img src="assets/screenshots/nodes.png" alt="Node monitoring view" />
      <img src="assets/screenshots/jobs.png" alt="Job dispatch interface" />
      <img src="assets/screenshots/foundry.png" alt="Foundry template builder" />
    </div>
  </div>
</section>
```

Minimal CSS for the screenshot grid — 2 columns on desktop, stacked on mobile. Consistent with existing `style.css` design language (Fira Sans, dark/light cards).

---

## Plan Structure

Given the scope, **2 plans** are appropriate:

**Plan 85-01** — `capture_screenshots.py` script
- Task 1: Script skeleton — argument parsing (`--url`, `--check`), `secrets.env` loading, pre-flight check
- Task 2: Data seeding — ephemeral Ed25519 keypair generation + registration, job dispatch (4–5 jobs), wait for COMPLETED state
- Task 3: Screenshot capture — 11 screenshots, drawer/panel interactions, write to both output dirs

**Plan 85-02** — Docs and homepage integration
- Task 1: Docs asset directories — `mkdir docs/docs/assets/screenshots/` + `homepage/assets/screenshots/` placeholder files
- Task 2: Getting-started and feature guide updates — inline images in 4–5 doc pages
- Task 3: Homepage "See it in action" section — new section in `index.html` + CSS in `style.css`
- Task 4: Remove/retire old script — delete or leave `puppeteer/dashboard/generate_screenshots.py` (per CONTEXT.md, Claude's discretion — delete it to avoid confusion)

---

## Test Strategy

Phase 85 is primarily tooling + documentation — there is no backend code change. Testing strategy:

- **Unit tests**: Not applicable (script is operator-invoked, not tested in CI by design per STATE.md decision)
- **Smoke test**: `--check` flag can be run against a live stack to verify pre-flight
- **Integration**: The script itself is the integration test — run it and verify 10+ PNG files exist with non-zero size

Wave 0 is not needed (no test framework files required). Backend test suite (`cd puppeteer && pytest`) should continue to pass unchanged.

---

## Validation Architecture

### Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing backend suite) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds |

### Validation Approach

Phase 85 has no backend code changes. The validation strategy is:

1. **Backend regression check** — run `cd puppeteer && pytest tests/ -q` after each plan to ensure no regressions from file changes
2. **File existence check** — after Plan 85-01, verify `tools/capture_screenshots.py` exists and has no syntax errors: `python -c "import ast; ast.parse(open('tools/capture_screenshots.py').read())"`
3. **Docs check** — after Plan 85-02, verify markdown files contain the expected `assets/screenshots/` image references using grep
4. **Homepage check** — verify `homepage/index.html` contains the "See it in action" section

### Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Notes |
|---------|------|------|-------------|-----------|-------------------|-------|
| 85-01-01 | 01 | 1 | SCR-01 | syntax | `python -c "import ast; ast.parse(open('tools/capture_screenshots.py').read())"` | Script exists and parses |
| 85-01-02 | 01 | 1 | SCR-01 | unit | `cd puppeteer && pytest tests/ -q` | Backend regression |
| 85-01-03 | 01 | 1 | SCR-01 | manual | `python tools/capture_screenshots.py --check` | Requires live stack |
| 85-02-01 | 02 | 2 | SCR-02 | file | `test -d docs/docs/assets/screenshots` | Dir created |
| 85-02-02 | 02 | 2 | SCR-02 | grep | `grep -r "assets/screenshots" docs/docs/getting-started/` | Image refs present |
| 85-02-03 | 02 | 2 | SCR-03 | grep | `grep -q "See it in action" homepage/index.html` | Section added |

### Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 10+ PNGs produced at 1440x900 | SCR-01 | Requires live Docker stack + enrolled node | Run `python tools/capture_screenshots.py --url http://localhost:8080` against running stack, verify PNG files in `docs/docs/assets/screenshots/` |
| Screenshots show populated data, not empty state | SCR-01 | Visual inspection required | Open PNGs and verify no spinner/empty-state screens |
| Homepage screenshots render correctly in browser | SCR-03 | Visual / layout check | Open `homepage/index.html` in browser, verify screenshot grid displays properly |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Timing — page still loading when screenshot fires | Medium | Use `wait_for_load_state("networkidle")` + small `wait_for_timeout(500)` before drawer screenshots |
| Node not enrolled (prerequisite not met) | Medium | `--check` flag catches this before capture loop starts |
| Jobs not COMPLETED before job_detail capture | Low | Seed hello-world Python job first, wait for COMPLETED before navigating to `/jobs` |
| `cryptography` not installed in venv | Low | Already in `puppeteer/requirements.txt` — use same import path as test_local_stack.py |
| Playwright not installed | Medium | Script should print clear "playwright not installed" error with install instruction |

---

## RESEARCH COMPLETE

Phase 85 is well-defined. The CONTEXT.md decisions cover all implementation details. Two plans are needed:
- Plan 85-01: The capture script itself
- Plan 85-02: Docs and homepage integration

No blocking unknowns. Proceed to planning.

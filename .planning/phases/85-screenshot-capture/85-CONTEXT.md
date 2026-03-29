# Phase 85: Screenshot Capture - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

A Python Playwright script (`tools/capture_screenshots.py`) that seeds demo data against a running Docker stack, captures 8+ named PNG screenshots at 1440×900, and writes them directly to `docs/docs/assets/screenshots/` and `homepage/assets/screenshots/`. Docs markdown pages (getting-started + feature guides) and the marketing homepage (`homepage/index.html`) are updated to embed the screenshots. The existing `puppeteer/dashboard/generate_screenshots.py` is replaced/superseded.

</domain>

<decisions>
## Implementation Decisions

### Seeding strategy
- Script seeds its own demo data — dispatches 3–5 jobs (mix of completed, failed, pending) so all views have meaningful content
- Real enrolled node is a **prerequisite** — the script does NOT start a node container; operator must have at least one node enrolled before running
- Credentials read from `puppeteer/secrets.env` (ADMIN_PASSWORD), same pattern as mop_validation scripts
- `--check` pre-flight flag: verifies stack is reachable + at least one node is enrolled, prints a clear error if not, then exits — does not proceed to capture

### Which views to capture (10 screenshots)
Full feature showcase set:
1. `login.png` — Login page (before auth)
2. `dashboard.png` — Dashboard overview
3. `nodes.png` — Nodes list page
4. `node_detail.png` — Nodes page with node detail **drawer open** (click first node row)
5. `jobs.png` — Jobs dispatch page
6. `job_detail.png` — Jobs page with job detail **panel open** (click a completed job row)
7. `queue.png` — Queue page
8. `history.png` — History / execution log
9. `scheduled_jobs.png` — Scheduled Jobs / definitions
10. `foundry.png` — Foundry Templates page
11. `audit.png` — Audit Log

All captures at 1440×900 viewport.

### Script location and interface
- Lives at `tools/capture_screenshots.py` (alongside other operator tooling)
- Invocation: `python tools/capture_screenshots.py [--url URL] [--check]`
- `--url` defaults to `http://localhost:8080`
- `--check` runs pre-flight only and exits (no screenshots taken)
- Output: writes directly to `docs/docs/assets/screenshots/` and `homepage/assets/screenshots/` relative to repo root (no `--output-dir` needed for normal use)
- Auth: GET token via `POST /api/auth/login` (form-encoded), inject into `localStorage['mop_auth_token']`, navigate to route, capture
- Launch with `args=['--no-sandbox']` (CLAUDE.md constraint for Linux)

### Docs integration (SCR-02)
- Format: standard markdown inline images `![alt text](../assets/screenshots/foo.png)` — no MkDocs-specific syntax
- **Getting-started pages** to update:
  - `getting-started/enroll-node.md` — add nodes.png and node_detail.png
  - `getting-started/first-job.md` — add jobs.png and job_detail.png
- **Feature guide pages** to update (add relevant screenshot to each):
  - `feature-guides/` — add foundry.png to Foundry page, scheduled_jobs.png to scheduling page, audit.png to audit guide
- Screenshots inserted at natural visual break points in the prose (after a step, not inline mid-paragraph)

### Marketing homepage (SCR-03)
- Add a new **"See it in action"** section to `homepage/index.html` (before or after the existing feature list)
- 3–4 key screenshots as `<img>` tags: `dashboard.png`, `nodes.png`, `jobs.png`, `foundry.png`
- Plain HTML + CSS — no JavaScript or tabs
- Images reference `assets/screenshots/<name>.png` (create `homepage/assets/screenshots/` dir)

### Replacing the old script
- `puppeteer/dashboard/generate_screenshots.py` was an early draft with wrong localStorage key (`token` vs `mop_auth_token`), stale nav label names, and hardcoded dummy JWT
- This phase replaces it — the old file can be deleted or left as is (Claude's discretion)

### Claude's Discretion
- Exact nav navigation approach (URL-based navigation preferred over clicking nav links, which is more reliable with Playwright)
- Timing/wait strategy between page loads (prefer `wait_for_load_state('networkidle')` over `asyncio.sleep`)
- Exact job script content used for seeding (e.g., a simple `print("hello")` Python script, signed with a test key)
- Whether to sign seeded jobs (required by the platform) — use the signing key from `secrets.env` or generate an ephemeral one
- CSS/layout of the new homepage section
- Feature guide pages that receive screenshots beyond the three listed above

</decisions>

<specifics>
## Specific Ideas

- The `--check` flag should be the first thing operators run to diagnose "why aren't there any nodes?" before wasting time waiting for a failed capture
- Viewport 1440×900 is specified in SCR-01 — use this exactly, not fullPage captures
- The "See it in action" homepage section should feel like a product showcase (screenshots side by side or stacked), not a technical diagram

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/dashboard/generate_screenshots.py`: Outdated draft — useful as structural reference only. Auth pattern is wrong (uses dummy JWT + wrong localStorage key). Nav link labels are stale. Replace entirely.
- `~/Development/mop_validation/scripts/test_playwright.py`: Working Playwright pattern — correct `mop_auth_token` localStorage key, form-encoded login, `--no-sandbox` launch, `wait_for_load_state` pattern. This is the reference implementation.
- `~/Development/mop_validation/scripts/test_local_stack.py`: Shows how to read `secrets.env` for credentials and seed data via the API. Use same pattern for credential loading.

### Established Patterns
- Auth via API: `POST /api/auth/login` with `data={"username": "admin", "password": ADMIN_PASSWORD}` (form-encoded, not JSON)
- JWT injection: `page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")`
- Playwright launch: `p.chromium.launch(args=['--no-sandbox'], headless=True)`
- Nav routes: `/` (Dashboard), `/nodes`, `/jobs`, `/queue`, `/history`, `/scheduled-jobs`, `/signatures`, `/templates`, `/admin`, `/users`, `/audit`

### Integration Points
- `docs/docs/assets/`: Currently only `logo.svg` — add `screenshots/` subdirectory
- `homepage/assets/`: Currently empty — add `screenshots/` subdirectory
- `docs/docs/getting-started/enroll-node.md` and `first-job.md`: Add inline screenshots
- `docs/docs/feature-guides/`: Add screenshot to Foundry, scheduling, audit pages
- `homepage/index.html`: Add "See it in action" section with img tags

</code_context>

<deferred>
## Deferred Ideas

- CI integration: running the screenshot script automatically on deploy and committing updated screenshots — noted for a future phase
- Screenshot diffing to detect UI regressions — future phase
- Animated GIF / video capture of interactive flows — out of scope for v15.0

</deferred>

---

*Phase: 85-screenshot-capture*
*Context gathered: 2026-03-29*

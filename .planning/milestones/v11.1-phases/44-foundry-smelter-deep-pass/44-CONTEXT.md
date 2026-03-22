# Phase 44: Foundry + Smelter Deep Pass - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Write 6 validation scripts plus a runner covering FOUNDRY-01 through FOUNDRY-06 against the live EE stack. No application code changes — purely testing tooling. Depends on Phase 42 (confirmed EE stack). Wizard flow, CVE enforcement, build failure handling, air-gap mirror, and build dir gap documentation.

</domain>

<decisions>
## Implementation Decisions

### Script structure
- **6 individual scripts**: `verify_foundry_NN_slug.py` — one per requirement, matches Phase 43 naming convention (`verify_foundry_01_wizard.py`, `verify_foundry_02_strict_cve.py`, etc.)
- **1 runner**: `run_foundry_matrix.py` — thin orchestrator, calls all 6 in sequence, aggregates [PASS]/[FAIL], prints N/6 summary
- Operator can run any single script independently or all 6 via runner

### FOUNDRY-01 wizard flow (verify_foundry_01_wizard.py)
- **Dual coverage**: API + Playwright
  - API layer first: POST blueprints (runtime + network), POST template, POST build trigger
  - Playwright second: drive the full 5-step wizard in the browser (OS selection through build trigger), assert build log appears, assert image tag visible in templates list
- Both portions in a single `verify_foundry_01_wizard.py` — one file, one FOUNDRY-01 concern
- Final assertion: `GET /api/foundry/images` or `docker images` confirms the new tag exists
- **No node deployment required**: asserting image exists in Docker is sufficient for FOUNDRY-01

### FOUNDRY-02 Smelter STRICT mode (verify_foundry_02_strict_cve.py)
- Add `cryptography<40.0.0` as an ingredient
- Confirm STRICT mode blocks the blueprint from being used in a build
- Assert API returns non-200 response with clear error detail

### FOUNDRY-03 build failure edge case (verify_foundry_03_build_failure.py)
- Trigger a build with a bad base image tag
- Assert `POST /api/foundry/build/{id}` returns HTTP 500 with error detail (not silent 200)

### FOUNDRY-04 build dir cleanup — gap test (verify_foundry_04_build_dir.py)
- **PASS = gap confirmed**: assert the temp build dir STILL EXISTS after a completed build
- Method: glob `/tmp/puppet_build_*` inside the agent container via `docker exec` before build, trigger build, glob again after — assert a new dir is present post-build
- Script prints clear documentation: `[PASS] FOUNDRY-04: MIN-7 gap confirmed — build dir /tmp/puppet_build_... not cleaned up after successful build`
- This keeps CI green while recording the defect evidence

### FOUNDRY-05 air-gap mirror (verify_foundry_05_airgap.py)
- **Network block**: script manages iptables rules on the Docker host
  - `sudo iptables -I OUTPUT -d pypi.org -j DROP`
  - `sudo iptables -I OUTPUT -d files.pythonhosted.org -j DROP`
  - Rules added before build, removed in finally block after assertion
- **Ingredient selection**: query `GET /api/smelter/ingredients` at runtime, find first ingredient with `mirror_status=MIRRORED` — proves the real mirror path, not a synthetic test
- Build a blueprint using that mirrored ingredient, trigger build with iptables block active
- Assert build succeeds (non-error response, image tag appears) — proves pip install came from local mirror

### FOUNDRY-06 Smelter WARNING mode (verify_foundry_06_warning.py)
- Add a moderate-risk ingredient in WARNING mode
- Assert build proceeds (non-500 response)
- Assert audit log records the warning (query `GET /admin/audit-log` after build)

### Claude's Discretion
- Exact polling backoff between build trigger and build-complete assertion
- Playwright selector strategy for 5-step wizard (CSS vs aria-label vs test IDs)
- Pre-flight failure messages and exact remediation commands printed when preconditions not met
- Exact wait/retry loop after iptables rules are added before triggering build
- `docker images` vs `GET /api/foundry/images` for final image tag assertion in FOUNDRY-01

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/verify_job_01_fast.py` + `run_job_matrix.py`: [PASS]/[FAIL] output format, summary table, runner pattern — all mirrored exactly
- `mop_validation/scripts/test_playwright.py`: existing Playwright pattern in mop_validation — use as reference for Playwright setup, login, and selector approach
- `puppeteer/agent_service/services/foundry_service.py`: build_dir path pattern is `/tmp/puppet_build_{tmpl.id}_{hashlib.md5(...)[:8]}` — glob pattern for FOUNDRY-04 is `/tmp/puppet_build_*`
- `foundry_service.py` line 44-51: enforcement_mode reads from DB Config key, defaults to "WARNING" — FOUNDRY-02 needs to set this to "STRICT" via `PATCH /admin/config` or equivalent before testing

### Established Patterns
- Test tooling lives in `mop_validation/scripts/` only (CLAUDE.md policy)
- Scripts use admin token auth via `POST /auth/login` at start
- Non-destructive by default — assume stack is up and EE licence valid, print exact remediation commands if not
- `docker exec puppeteer-postgres-1 psql` for DB queries
- `docker exec puppeteer-agent-1 ls /tmp/` for file system checks inside the agent container
- Scripts exit non-zero on any failure (CI-safe)

### Integration Points
- `POST /api/blueprints` — create runtime + network blueprints
- `POST /api/foundry/templates` — create template combining blueprints
- `POST /api/foundry/build/{template_id}` — trigger build
- `GET /api/foundry/images` — assert built image tag present
- `GET /api/smelter/ingredients` — find MIRRORED ingredient for FOUNDRY-05
- `GET /admin/audit-log` — assert WARNING recorded for FOUNDRY-06
- `PATCH /admin/config` (or equivalent) — set enforcement mode to STRICT for FOUNDRY-02
- `docker exec puppeteer-agent-1 ls /tmp/puppet_build_*` — build dir assertion for FOUNDRY-04
- Playwright at `https://localhost` (Caddy-proxied dashboard) — wizard UI for FOUNDRY-01

</code_context>

<specifics>
## Specific Ideas

- FOUNDRY-04 script should print the exact build dir path found, making it easy to inspect manually: `Found uncleaned dir: /tmp/puppet_build_abc123_d4e5f6 (123 MB)`
- FOUNDRY-05 iptables rules should always be removed in a `finally` block — even if the build or assertion fails, host network rules must be cleaned up
- FOUNDRY-01 Playwright portion should use the CF Access headers (`CF-Access-Client-Id` / `CF-Access-Client-Secret`) if the dashboard is behind CF Access — same approach as `test_playwright.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 44-foundry-smelter-deep-pass*
*Context gathered: 2026-03-21*

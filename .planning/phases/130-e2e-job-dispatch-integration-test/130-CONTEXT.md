# Phase 130: E2E Job Dispatch Integration Test - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Write integration tests that exercise the complete job dispatch pipeline: signature registration → job creation → node work pull → job completion → result retrieval. Two deliverables: (1) a pytest test file in `puppeteer/tests/` that covers the API contract and state machine using in-process service-layer calls, and (2) a standalone E2E script in `mop_validation/scripts/` that runs against the live Docker stack with a real node. No new backend features or API changes — this phase is testing only.

</domain>

<decisions>
## Implementation Decisions

### Test location & type
- **Both** `puppeteer/tests/` (pytest) AND `mop_validation/scripts/` (live stack script) — one test each
- pytest file: combines snapshot-style (validate response models via Pydantic) AND stateful integration (assert state machine transitions). New file: `test_dispatch_e2e.py`
- mop_validation file: new standalone script `e2e_dispatch_integration.py` (not an orchestrated runner over existing verify_job scripts)

### Node simulation (pytest side)
- Simulate the node using **direct service-layer calls** — call `pull_work()` and update job status via `job_service` functions directly in the test body
- No mTLS cert handling, no mock patching — just drive the real service functions from the test
- This keeps tests fast and CI-friendly without requiring a real node container

### Node simulation (live script side)
- Use a **real enrolled local node** from `local_nodes/` compose configs (e.g., `node_alpha`)
- Script is **self-contained**: manages `docker compose` to bring node up, enrolls it via `/api/enroll`, runs all test scenarios, then tears it down
- Requires Docker socket access from the script (already available in dev environment)

### Dispatch path scope — pytest
- Happy path: valid signed job → node pulls → job completes → result retrievable
- Bad signature rejection: job with invalid/missing signature rejected at submission
- Capability mismatch: job targets capabilities node doesn't have → stays PENDING, diagnosis explains why
- Retry on failure: node reports job failed → job retries up to `max_retries`

### Dispatch path scope — live E2E script
- Happy path with real execution: sign and submit a real Python script, node executes in container, output captured
- Signed vs unsigned: unsigned job rejected, signed job succeeds
- Capability-targeted dispatch: job targets a specific capability tag, verify it lands on the right node
- Concurrent jobs: 3 jobs submitted simultaneously, all complete with isolation verified

### Assertion depth — pytest
- **Response model validity**: parse all response JSON through Pydantic models, assert no `ValidationError` (validates Phase 129 work)
- **State machine transitions**: assert job moves `PENDING → ASSIGNED → COMPLETED` (or `FAILED`) in correct order via `GET /jobs/{guid}`
- **Output content**: assert job result contains expected output (e.g., `print()` statement visible in `result.output`)
- **Dispatch diagnosis accuracy**: for capability mismatch case, assert `GET /jobs/{guid}/diagnosis` explains the unassigned reason

### Reporting — live E2E script
- **Console output**: PASS/FAIL per scenario with duration, exit code 0 on all pass / 1 on any failure
- **JSON report**: write structured report to `mop_validation/reports/e2e_dispatch_integration_report.json` with scenario results, timings, and failure details
- Both outputs produced on every run (JSON report always written, even on failure)

### Claude's Discretion
- Exact fixture structure in `conftest.py` (whether to add shared fixtures or keep self-contained in test file)
- Which `local_nodes/` compose file to use for the live script node
- Polling interval and timeout values for the live script's job completion wait loop
- Exact Python script used as the test job payload (something deterministic and lightweight)

</decisions>

<specifics>
## Specific Ideas

- The pytest test should register a real Ed25519 signature key (or use an existing test fixture key) to exercise the full signing path, not just mock signature validation
- The live script should print a clear pre-run requirements block at startup (stack running, Docker socket available) before attempting node setup
- JSON report format should be compatible with what existing mop_validation scripts produce so it fits the reports/ audit trail pattern

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/tests/conftest.py`: `setup_db` fixture and `AsyncClient` with `ASGITransport` — reuse this pattern for new test file
- `mop_validation/scripts/verify_job_01_fast.py` through `verify_job_09_revoked.py`: established patterns for live API calls, job polling, and pass/fail reporting
- `mop_validation/scripts/run_signed_job.py` and `generate_signing_key.py`: signing key setup patterns to reuse in the live script
- `mop_validation/local_nodes/`: compose configs for `node_alpha`, `node_beta`, `node_gamma` available for live script

### Established Patterns
- pytest tests use `@pytest.mark.asyncio` + `AsyncClient(app=app, base_url="http://test")` pattern
- Direct service-layer calls in tests: `from agent_service.services.job_service import pull_work, ...`
- Live scripts read credentials from `mop_validation/secrets.env` via `dotenv` or direct env reads
- Live scripts use `requests` (sync) not `httpx` — maintain consistency

### Integration Points
- New pytest file `test_dispatch_e2e.py` in `puppeteer/tests/` — picked up automatically by pytest
- Live script output → `mop_validation/reports/e2e_dispatch_integration_report.json`
- Live script uses `local_nodes/` compose: `docker compose -f mop_validation/local_nodes/node_alpha/docker-compose.yml up -d`
- `job_service.pull_work()` and result submission functions in `puppeteer/agent_service/services/job_service.py`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 130-e2e-job-dispatch-integration-test*
*Context gathered: 2026-04-11*

# Phase 41: CE Validation Pass - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm the CE install is clean across three dimensions: all 7 EE stub routes return 402, a hard-teardown + fresh CE install produces exactly 13 tables with zero EE leakage, and a signed job executes end-to-end on a DEV-tagged LXC node with stdout captured in execution history. Depends on Phase 38 (clean CE stack) and Phase 40 (enrolled nodes). EE layering is Phase 42.

</domain>

<decisions>
## Implementation Decisions

### Script structure
- **3 separate standalone Python scripts** in `mop_validation/scripts/`:
  - `verify_ce_stubs.py` — CEV-01 (EE route stub assertions)
  - `verify_ce_tables.py` — CEV-02 (table count after hard teardown)
  - `verify_ce_job.py` — CEV-03 (end-to-end signed job execution)
- Each script is runnable independently — operator can re-run a single failing check without re-running all three
- **Output format**: `[PASS]` / `[FAIL]` per step inline as it runs, then a final summary table at the end (mirrors `verify_lxc_nodes.py` pattern)

### CEV-01 — EE stub route assertions (`verify_ce_stubs.py`)
- **Hardcoded list** of the 7 known EE route paths — explicit, fails clearly if a route changes or is accidentally removed
- **Correct HTTP method per route** with admin token auth (GET for read endpoints, POST for creation endpoints)
- Asserts `HTTP 402` — not 404, not 500 — for each route
- Admin token ensures 402 is definitely from the CE stub, not a permission check

### CEV-02 — Table count (`verify_ce_tables.py`)
- **Assumes teardown already done**: script only runs the table count query — operator runs `teardown_hard.sh` + `docker compose up -d` first
- Keeps the script non-destructive and fast (no multi-minute stack restart baked in)
- Table count query: `docker exec puppeteer-postgres-1 psql` against `information_schema.tables` (no external DB driver)
- Asserts exactly 13 tables
- Does NOT re-assert `GET /api/features` or `GET /api/licence` — those are delegated to `verify_ce_install.py` (Phase 38); no duplication

### CEV-03 — End-to-end signed job execution (`verify_ce_job.py`)
- **Self-contained**: key loading, Ed25519 signing, job submission, and result assertion all inline — no subprocess calls to `admin_signer.py` or `run_signed_job.py`
- **Signing key**: `mop_validation/secrets/signing.key` (existing key already registered with the server)
- **Pre-flight check**: asserts the public key is registered via `GET /api/signatures` before submitting — clear error message if key is missing rather than a confusing signature rejection
- **Job payload**: `import sys; print('CEV-03 stdout ok'); sys.exit(0)` — minimal, captures a known stdout string
- **Target node**: DEV-tagged node (`axiom-node-dev`)
- **Result verification**: API-only via `GET /api/executions` filtered by job GUID — asserts `status=COMPLETED` and `stdout` contains `"CEV-03 stdout ok"`
- **Timeout**: 30s, 2s poll interval — trivial job; anything slower signals a real problem

### Claude's Discretion
- Exact formatting of the summary table at end of each script
- Retry/backoff logic for API readiness checks at script start
- Error messaging when `signing.key` or `secrets/nodes/` files are missing (pre-flight guard wording)
- The precise list of 7 EE route paths (derive from EE plugin's router registration in `axiom-ee/ee/plugin.py`)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/verify_ce_install.py`: PASS/FAIL output format, `docker exec psql` pattern, API readiness wait loop — all 3 new scripts mirror this structure
- `mop_validation/scripts/verify_lxc_nodes.py`: summary table at end pattern — Phase 41 scripts adopt this
- `mop_validation/scripts/run_signed_job.py` + `admin_signer.py`: Ed25519 signing logic reference (structural only — `verify_ce_job.py` is self-contained, not a wrapper)
- `mop_validation/secrets/signing.key`: existing private key for Ed25519 signing, registered on server

### Established Patterns
- Test tooling lives in `mop_validation/`, never in the main repo (CLAUDE.md policy)
- Scripts use hardcoded absolute paths: `~/Development/master_of_puppets`, `~/Development/mop_validation`
- `docker exec puppeteer-postgres-1 psql` for DB queries (no external driver)
- Admin token auth for all API calls in verification scripts

### Integration Points
- `GET /api/executions?job_id=<guid>` — result polling in `verify_ce_job.py`
- `GET /api/signatures` — pre-flight check for key registration in `verify_ce_job.py`
- `information_schema.tables` via `docker exec psql` — table count in `verify_ce_tables.py`
- EE stub routes (7 paths from `axiom-ee/ee/plugin.py` router registrations) — hardcoded in `verify_ce_stubs.py`

</code_context>

<specifics>
## Specific Ideas

- `verify_ce_tables.py` is intentionally non-destructive — it's a query, not an orchestrator. The operator owns the teardown+restart sequence; the script just validates the outcome
- The pre-flight key check in `verify_ce_job.py` is a quality-of-life guard: if Phase 41 is run against a fresh stack where the signing key wasn't re-registered after hard teardown, the error message should tell the operator exactly what to do
- All 3 scripts should exit with a non-zero code when any assertion fails — makes them usable in CI pipelines

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 41-ce-validation-pass*
*Context gathered: 2026-03-21*

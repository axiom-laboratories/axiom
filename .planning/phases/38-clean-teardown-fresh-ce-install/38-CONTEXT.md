# Phase 38: Clean Teardown + Fresh CE Install - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create soft and hard teardown bash scripts, and a standalone CE install verification script. Soft teardown resets DB state between test runs while preserving PKI. Hard teardown is a full clean slate including all Docker volumes and LXC node cert dirs. Verification script confirms 13 CE tables, all features false, and admin re-seed safety after cold start.

</domain>

<decisions>
## Implementation Decisions

### Script form + location
- Bash scripts: `teardown_soft.sh` and `teardown_hard.sh`
- Location: `mop_validation/scripts/`
- Hardcoded relative path to puppeteer/ — scripts assume they're run from `~/Development/master_of_puppets` (matches existing mop_validation patterns)

### Soft teardown scope
- Run `docker compose down` (no `-v`) — stops and removes containers
- Then explicitly remove `pgdata` volume only via `docker volume rm`
- Preserved volumes: `certs-volume`, `caddy_data`, `caddy_config`, `registry-data`
- LXC node `secrets/` dirs: left completely untouched — nodes keep their certs and re-enroll next start
- Stack is left down after teardown — caller runs `docker compose up -d` when ready

### Hard teardown scope
- Run `docker compose down -v --remove-orphans` — removes all named volumes
- Then clear LXC node `secrets/` dirs via `incus exec`

### LXC node secrets discovery (hard teardown)
- Use `incus list --format csv` to dynamically discover containers matching `axiom-node-` prefix
- Node secrets path: `/home/ubuntu/secrets/` inside each container
- Error handling: skip with warning if a node is not running or `incus exec` fails — teardown is best-effort for nodes
- Do not fail fast on individual node errors

### Verification method
- Standalone Python script: `mop_validation/scripts/verify_ce_install.py`
- Table count: `docker exec` into postgres container with `psql` query against `information_schema.tables` (no external DB driver needed)
- Features assertion: `GET /api/features` via requests, confirm all values false
- Admin re-seed test (INST-04): manual test with documented steps in script comments — not automated (modifying the running stack is too invasive)

### Claude's Discretion
- Script banner/output formatting (PASS/FAIL prefix, colors if desired)
- Exact postgres container name detection (use `docker ps` filter or hardcode `puppeteer-postgres-1`)
- Wait/retry logic for stack startup before verification hits the API

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/compose.server.yaml`: defines the five named volumes (`pgdata`, `certs-volume`, `caddy_data`, `caddy_config`, `registry-data`) — soft teardown removes `pgdata` only
- `mop_validation/scripts/`: existing pattern for standalone Python test scripts; teardown bash scripts follow same location convention
- `puppeteer/agent_service/main.py` lines 86–98: admin seeding guard — only creates admin if username does not exist; this is the behavior INST-04 verifies

### Established Patterns
- Test tooling lives in `mop_validation/` not the main repo (CLAUDE.md policy)
- LXC node secrets: `/home/ubuntu/secrets/` (from manage-test-nodes skill)
- Scripts use hardcoded project paths relative to `~/Development/master_of_puppets`

### Integration Points
- `docker compose -f puppeteer/compose.server.yaml` — all compose commands target this file
- `incus list --format csv` — LXC discovery for hard teardown
- `docker exec puppeteer-postgres-1 psql` — table count query

</code_context>

<specifics>
## Specific Ideas

- Soft teardown is designed to be safe to run between test runs — CA and node certs survive, so nodes don't need to re-enroll
- Hard teardown is the "scorched earth" option — no defunct certs anywhere, true cold start
- INST-04 verification is intentionally manual: document the steps in verify_ce_install.py comments so the operator can follow them, but don't automate a test that modifies the running stack

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 38-clean-teardown-fresh-ce-install*
*Context gathered: 2026-03-20*

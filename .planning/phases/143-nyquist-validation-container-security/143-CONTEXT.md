# Phase 143: Nyquist Validation — Container Security - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Run `/gsd:validate-phase` for all 5 container hardening phases (132–136) and write tests to fill any coverage gaps found. Each phase currently has `nyquist_compliant: false` in its VALIDATION.md. This phase makes them compliant.

Out of scope: implementing new container hardening features, changing compose configuration, modifying Containerfiles beyond adding tests.

</domain>

<decisions>
## Implementation Decisions

### Live Docker test strategy
- The stack must be running before Phase 132's integration tests (test_nonroot.py) execute
- The auditor is responsible for bringing the stack up if containers aren't running (`docker compose up -d` before running live tests)
- If the stack cannot be brought up, validation fails fast with a clear error — not silently skipped
- Live container tests are treated as real requirements, not optional extras

### Phase 133 gap — new tests required
- Phase 133 (cap_drop ALL, no-new-privileges, Postgres loopback) has an empty Per-Task Verification Map — no tests planned at all
- Fill this with **both** static compose YAML inspection tests **and** live container capability checks (docker inspect)
- Static tests: parse compose.server.yaml and assert `cap_drop` includes `ALL`, `security_opt` includes `no-new-privileges:true`, Postgres port binding is `127.0.0.1` only
- Live tests: `docker inspect` running containers and assert capabilities are actually dropped at runtime
- New file: `puppeteer/tests/test_security_capabilities.py` (dedicated file, not added to test_compose_validation.py)

### Phase 135 — Containerfile content checks
- The auditor should parse Containerfile.node and assert removed packages (e.g. pip, build-essential) don't appear in `RUN apt-get install` lines
- Static analysis — no Docker required
- Combined with compose YAML resource limit assertions (memory/CPU limits present)

### Execution order — sequential
- Run validate-phase for 132 → 133 → 134 → 135 → 136 sequentially, not in parallel
- Reason: agents writing to overlapping test files simultaneously would cause conflicts (test_foundry.py, test_runtime.py are shared targets)
- Each phase's full test suite must be green before the next validate-phase starts

### VALIDATION.md updates
- Always update `nyquist_compliant: true` and `wave_0_complete: true` once all tests pass — even if no new tests were written
- Makes audit state explicit and accurate regardless of whether gaps were found

### Compliance threshold — strict
- `nyquist_compliant: true` only when **every** per-task test is green, including live container tests
- If live tests can't run (stack not reachable), the phase is not marked compliant
- No partial compliance — the bar is all tests passing

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `puppeteer/tests/test_nonroot.py` — already implemented; integration tests for Phase 132 (UID checks via docker exec). Requires running stack.
- `puppeteer/tests/test_runtime_socket.py` — already implemented; unit tests for Phase 134 socket detection logic (mock-based, no Docker needed).
- `puppeteer/tests/test_compose_validation.py` — exists; compose YAML inspection pattern to follow for Phase 133 static tests.
- `puppeteer/tests/test_foundry.py` — existing file; Phase 136 user-injection tests should be added here (CONT-08).

### Established Patterns
- Integration tests that need live containers use `subprocess.run(['docker', 'ps', ...])` + `get_container_id()` helper (see test_nonroot.py)
- Unit tests use `unittest.mock.patch` on `os.path.exists` and `os.environ.get` (see test_runtime_socket.py)
- Compose YAML tests should parse `compose.server.yaml` with PyYAML and assert structure directly

### Integration Points
- VALIDATION.md files in each phase directory need `nyquist_compliant: true` and `wave_0_complete: true` after tests pass
- The milestone audit (`.planning/v22.0-MILESTONE-AUDIT.md`) lists all 5 phases as `partial_phases` in the nyquist section — updating VALIDATION.md files will move them to `compliant_phases`

</code_context>

<specifics>
## Specific Ideas

- Phase 133 test file is a new file: `test_security_capabilities.py` — don't cram it into `test_compose_validation.py`
- Phase 135 Containerfile parsing: read `puppets/Containerfile.node` and check `RUN apt-get install` lines for absence of unwanted packages
- The auditor should run `cd puppeteer && pytest -x -q` as the full suite check between each phase — same pattern as all prior phases

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 143-nyquist-validation-container-security*
*Context gathered: 2026-04-14*

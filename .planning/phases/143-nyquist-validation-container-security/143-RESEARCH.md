# Phase 143: Nyquist Validation — Container Security (Phases 132–136) - Research

**Researched:** 2026-04-14  
**Domain:** Test validation infrastructure + container security compliance  
**Confidence:** HIGH

## Summary

Phase 143 is a **test validation closure phase** — not a feature implementation phase. The goal is to run Nyquist validation (the `/gsd:validate-phase` workflow) on the five completed container hardening phases (132–136) and fill any identified test coverage gaps. Each of these five phases currently has `nyquist_compliant: false` in its VALIDATION.md frontmatter. This phase makes them compliant by ensuring all per-task verifications have executable automated tests.

The container hardening implementation is **complete and production-ready** (Phase 142 closed the final test stubs). Validation is about confirming test coverage is comprehensive and realistic.

**Primary recommendation:** Execute sequential `/gsd:validate-phase` runs for phases 132→133→134→135→136, capturing any missing test files or gap-closure needs. Focus on Phase 133 (which has an empty Per-Task Verification Map), and fill new test file `test_security_capabilities.py` with static compose YAML inspection + live `docker inspect` verification tests.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Live Docker test strategy:**
- Stack must be running before Phase 132's integration tests (test_nonroot.py) execute
- Auditor responsible for bringing stack up if containers aren't running (`docker compose up -d` before running)
- If stack cannot be brought up, validation fails fast with clear error — not silently skipped
- Live container tests are real requirements, not optional extras

**Phase 133 gap — new tests required:**
- Phase 133 (cap_drop ALL, no-new-privileges, Postgres loopback) has an empty Per-Task Verification Map — no tests planned at all
- Fill with **both** static compose YAML inspection tests **and** live container capability checks (docker inspect)
- Static tests: parse compose.server.yaml and assert `cap_drop` includes `ALL`, `security_opt` includes `no-new-privileges:true`, Postgres port binding is `127.0.0.1` only
- Live tests: `docker inspect` running containers and assert capabilities are actually dropped at runtime
- New file: `puppeteer/tests/test_security_capabilities.py` (dedicated file, not added to test_compose_validation.py)

**Phase 135 — Containerfile content checks:**
- Parse Containerfile.node and assert removed packages (e.g. pip, build-essential) don't appear in `RUN apt-get install` lines
- Static analysis — no Docker required
- Combined with compose YAML resource limit assertions (memory/CPU limits present)

**Execution order — sequential:**
- Run validate-phase for 132 → 133 → 134 → 135 → 136 sequentially, not in parallel
- Reason: agents writing to overlapping test files simultaneously would cause conflicts (test_foundry.py, test_runtime.py are shared targets)
- Each phase's full test suite must be green before the next validate-phase starts

**VALIDATION.md updates:**
- Always update `nyquist_compliant: true` and `wave_0_complete: true` once all tests pass — even if no new tests were written
- Makes audit state explicit and accurate regardless of whether gaps were found

**Compliance threshold — strict:**
- `nyquist_compliant: true` only when **every** per-task test is green, including live container tests
- If live tests can't run (stack not reachable), the phase is not marked compliant
- No partial compliance — the bar is all tests passing

### Claude's Discretion

None — all implementation decisions are locked. This phase has no discretionary areas.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

---

## Standard Stack

### Test Frameworks (Existing)
| Framework | Version | Purpose | Status |
|-----------|---------|---------|--------|
| pytest | 7.x | Unit + integration test runner | Already in use |
| unittest.mock | stdlib | Mocking for unit tests (docker, env vars) | Established patterns |
| docker CLI | Latest | Container inspection commands | Already in use |
| PyYAML | Latest | YAML parsing for compose.server.yaml | Needed for Phase 133 static tests |

### Reusable Test Patterns

| Pattern | Used By | Purpose |
|---------|---------|---------|
| `subprocess.run(['docker', 'ps', ...])` | test_nonroot.py | Get container IDs; handle missing containers with pytest.skip |
| `subprocess.run(['docker', 'exec', container_id, ...])` | test_nonroot.py | Run commands inside running containers (live) |
| `unittest.mock.patch('os.path.exists')` | test_runtime_socket.py | Mock socket detection without Docker |
| `unittest.mock.patch('os.environ.get')` | test_runtime_socket.py | Mock environment variables |
| `docker inspect <service> \| jq/python3 -c` | Command-line | Extract config from running containers (manual verify currently) |
| `docker compose config --quiet` | Phase 135 | Validate compose syntax (manual verify currently) |

---

## Architecture Patterns

### Test File Organization

**Existing pattern:**
```
puppeteer/tests/
├── conftest.py                  # Shared fixtures (async client, DB setup, event loop)
├── test_nonroot.py              # Phase 132: integration tests (needs running stack)
├── test_compose_validation.py   # Phase 134(?): compose generator endpoint tests
├── test_runtime_socket.py       # Phase 134: socket detection logic (unit, mocked)
├── test_runtime_network.py      # Phase 134: network isolation (unit, mocked)
├── test_node_compose.py         # Phase 134: node compose validation (integration)
├── test_foundry.py              # Phase 136: foundry user injection tests
└── [50+ other test files]
```

**Pattern for new files:**
- Use pytest fixtures from conftest.py (event_loop, async_client, setup_db)
- For container tests: get container ID via docker ps, use docker exec
- For YAML tests: parse yaml.safe_load, assert structure
- For mock tests: patch at the module level where function is used, not where defined

### Integration Test Pattern (Phase 132)

```python
def get_container_id(service_name):
    """Get running container ID, raise RuntimeError if not found."""
    result = subprocess.run(
        ['docker', 'ps', '--filter', f'name={service_name}', '-q'],
        capture_output=True, text=True, check=True, timeout=5
    )
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError(f"Container '{service_name}' not running")
    return container_id

@pytest.fixture
def agent_container_id():
    """Fixture: Get agent container ID."""
    return get_container_id('puppeteer-agent-1')

def test_agent_uid(agent_container_id):
    """CONT-01: Verify agent runs as UID 1000."""
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'grep', 'Uid:', '/proc/1/status'],
        capture_output=True, text=True, check=True, timeout=10
    )
    uid = result.stdout.split()[1]
    assert uid == '1000'
```

**Key points:**
- Fixtures raise RuntimeError if container missing (doesn't skip test)
- Use `/proc/1/status` for UID (works on Alpine + Debian)
- Timeout all subprocesses (5s for docker ps, 10s for docker exec)
- Don't catch exceptions — let them bubble (test framework will report clearly)

### Unit Test Pattern (Phase 134)

```python
from unittest.mock import patch

def test_docker_socket_first():
    """When /var/run/docker.sock exists, return 'docker' immediately."""
    with patch("os.environ.get", return_value="auto"), \
         patch("os.path.exists") as mock_exists:
        
        mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"
        
        runtime = ContainerRuntime()
        assert runtime.runtime == "docker"
```

**Key points:**
- Patch at module import level (not where imported from)
- Use side_effect for conditional returns (lambda)
- Test both happy path (socket exists) and fallback (socket absent)
- Cover env var override (EXECUTION_MODE=docker ignores detection)

### Static YAML Test Pattern (Phase 133 — NEW)

```python
import yaml

def test_cap_drop_all_on_services():
    """CONT-03: All services have cap_drop: ALL."""
    with open('puppeteer/compose.server.yaml', 'r') as f:
        compose = yaml.safe_load(f)
    
    for service_name, service_config in compose.get('services', {}).items():
        assert service_config.get('cap_drop') == ['ALL'], \
            f"{service_name} missing cap_drop: ALL"

def test_postgres_loopback_binding():
    """CONT-04: Postgres bound to 127.0.0.1 only."""
    with open('puppeteer/compose.server.yaml', 'r') as f:
        compose = yaml.safe_load(f)
    
    db_service = compose['services']['db']
    ports = db_service.get('ports', [])
    
    for port_spec in ports:
        assert '127.0.0.1' in str(port_spec) or port_spec == '5432:5432', \
            f"DB port binding not restricted to loopback: {port_spec}"
```

**Key points:**
- yaml.safe_load() for security (no arbitrary code execution)
- Service names are dict keys in compose['services']
- Port binding format: either "host:container" or service name:port
- Assert on absolute paths (expected format, not optional existence)

### Live Container Inspection Pattern (Phase 133 — NEW)

```python
import json
import subprocess

def test_agent_cap_drop_enforced():
    """CONT-03: Running agent container has capabilities actually dropped."""
    container_id = get_container_id('puppeteer-agent-1')
    
    result = subprocess.run(
        ['docker', 'inspect', container_id],
        capture_output=True, text=True, check=True
    )
    
    inspect_data = json.loads(result.stdout)[0]
    cap_drop = inspect_data['HostConfig'].get('CapDrop', [])
    
    assert 'ALL' in cap_drop, f"CapDrop does not include ALL: {cap_drop}"
    assert inspect_data['HostConfig'].get('SecurityOpt', []) != [], \
        "security_opt not found in running container"
```

**Key points:**
- docker inspect returns JSON array (index [0])
- HostConfig.CapDrop is the actual runtime state (vs compose file)
- CapDrop=['ALL'] (list), SecurityOpt=['no-new-privileges:true'] (list)
- Both static (compose file) + live (docker inspect) tests needed

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container introspection | Custom shell scripts | subprocess + docker inspect | Reliable JSON output; no parsing errors |
| YAML validation | regex parsing | yaml.safe_load() | Handles edge cases (multiline, anchors) |
| Async test setup | Manual event loop management | pytest fixtures in conftest.py | Handles cleanup; works with pytest.mark.asyncio |
| Environment mocking | Subprocess env override | unittest.mock.patch | Isolated; no side effects on other tests |
| Test discovery | Manual file lists | pytest auto-discovery | Convention-based; no maintenance overhead |

**Key insight:** The test infrastructure is already mature. Phase 133's only new need is static YAML parsing (yaml library) — everything else reuses existing patterns.

---

## Common Pitfalls

### Pitfall 1: Container Not Running During Test

**What goes wrong:** Phase 132 tests try to run docker exec against a nonexistent container and fail with a cryptic error.

**Why it happens:** User hasn't brought up the stack yet (`docker compose up -d`). Integration tests require live containers.

**How to avoid:** CONTEXT.md explicitly states "auditor is responsible for bringing stack up if containers aren't running". Document this in the VALIDATION.md sampling instructions. Let test failures be clear (RuntimeError with container name) so the user knows exactly what to fix.

**Warning signs:** 
- "container not found" in pytest output
- docker ps returns empty
- Test fixtures raise RuntimeError instead of pytest.skip

### Pitfall 2: Mixing Static and Live Tests in Wrong Order

**What goes wrong:** Static YAML test asserts `cap_drop: ALL` in compose.server.yaml, but live docker inspect shows CapDrop is missing at runtime (container was restarted before changes took effect).

**Why it happens:** User modifies compose file but doesn't rebuild/restart containers. Static test passes (file is correct), live test fails (containers are stale).

**How to avoid:** Clearly separate phases: "static test" file modifications (quick), then "rebuild containers" instructions, then "live test" verification. VALIDATION.md sampling should explicitly state: "After every plan commit: run static tests. After rebuild: run live tests."

**Warning signs:**
- Static YAML test passes, live docker inspect fails
- compose.server.yaml and actual container config disagree

### Pitfall 3: Incomplete Fixture Scope

**What goes wrong:** Test fixture tries to get container ID for every test method, but container ID changes between tests (container restart, scale up/down).

**Why it happens:** Using @pytest.fixture without function scope, or caching ID across multiple test methods.

**How to avoid:** Use function scope (default) or session scope only for truly constant values (DB, event loop). Container IDs should be retrieved fresh per test.

**Warning signs:**
- "Container ID mismatch" errors mid-test
- Container exits unexpectedly between test methods

### Pitfall 4: Non-Deterministic Test Output from docker inspect

**What goes wrong:** docker inspect output format varies (capitalization, array order), causing flaky assertions.

**Why it happens:** JSON parsing without normalization; assuming single-element arrays.

**How to avoid:** Always index [0] when docker inspect returns array. Use .get() with defaults for optional fields. Assert membership (not equality) for list-based fields like CapDrop.

**Warning signs:**
- Tests sometimes pass, sometimes fail (same code, same stack)
- Assertion errors on container config fields

### Pitfall 5: Assuming All Services Require All Capabilities

**What goes wrong:** Test asserts cap_drop: ALL on all services, but Caddy needs NET_BIND_SERVICE to serve port 80.

**Why it happens:** Copying the same test to all services without checking if service has service-specific cap_add.

**How to avoid:** Loop through services, but allow exceptions: check if cap_add exists and is non-empty. For Caddy specifically, assert it has NET_BIND_SERVICE if cap_drop: ALL.

**Warning signs:**
- Test fails on Caddy service
- "Need NET_BIND_SERVICE to bind to port" in service logs

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Get Container ID and Run Commands Inside

```python
# Source: puppeteer/tests/test_nonroot.py (established pattern)
def get_container_id(service_name):
    """Get container ID for a service."""
    result = subprocess.run(
        ['docker', 'ps', '--filter', f'name={service_name}', '-q'],
        capture_output=True, text=True, check=True, timeout=5
    )
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError(f"Container '{service_name}' not running")
    return container_id

@pytest.fixture
def agent_container_id():
    return get_container_id('puppeteer-agent-1')

def test_agent_uid(agent_container_id):
    """Verify UID via /proc/1/status."""
    result = subprocess.run(
        ['docker', 'exec', agent_container_id, 'grep', 'Uid:', '/proc/1/status'],
        capture_output=True, text=True, check=True, timeout=10
    )
    uid = result.stdout.split()[1]
    assert uid == '1000'
```

### Mock Socket Detection (Unit Test)

```python
# Source: puppeteer/tests/test_runtime_socket.py (established pattern)
from unittest.mock import patch

def test_docker_socket_detection():
    """CONT-10: When /var/run/docker.sock exists, use docker."""
    with patch("os.environ.get", return_value="auto"), \
         patch("os.path.exists") as mock_exists, \
         patch("shutil.which", return_value=None):
        
        mock_exists.side_effect = lambda path: path == "/var/run/docker.sock"
        
        runtime = ContainerRuntime()
        assert runtime.runtime == "docker"
```

### Parse Compose YAML Statically (NEW for Phase 133)

```python
# Source: Recommended pattern based on test_compose_validation.py structure
import yaml
import pytest

def test_cap_drop_all_configured():
    """CONT-03: Verify cap_drop: ALL in compose.server.yaml."""
    with open('puppeteer/compose.server.yaml', 'r') as f:
        compose = yaml.safe_load(f)
    
    services = compose.get('services', {})
    for service_name, config in services.items():
        cap_drop = config.get('cap_drop', [])
        assert 'ALL' in cap_drop, \
            f"Service '{service_name}' missing cap_drop: ALL"

def test_postgres_loopback_only():
    """CONT-04: Verify Postgres bound to 127.0.0.1:5432 only."""
    with open('puppeteer/compose.server.yaml', 'r') as f:
        compose = yaml.safe_load(f)
    
    db_config = compose['services']['db']
    ports = db_config.get('ports', [])
    
    for port_binding in ports:
        # Port binding is either "127.0.0.1:5432:5432" or service alias
        assert '127.0.0.1' in str(port_binding), \
            f"DB port not restricted to loopback: {port_binding}"
```

### Inspect Running Container Capabilities (NEW for Phase 133)

```python
# Source: New pattern combining docker inspect + json parsing
import json
import subprocess

def test_capabilities_dropped_at_runtime():
    """CONT-03: Verify cap_drop actually enforced in running container."""
    container_id = get_container_id('puppeteer-agent-1')
    
    result = subprocess.run(
        ['docker', 'inspect', container_id],
        capture_output=True, text=True, check=True
    )
    
    config = json.loads(result.stdout)[0]  # docker inspect returns array
    cap_drop = config['HostConfig'].get('CapDrop', [])
    
    assert 'ALL' in cap_drop, \
        f"CapDrop not set to ALL in running container: {cap_drop}"
    
    security_opt = config['HostConfig'].get('SecurityOpt', [])
    assert any('no-new-privileges' in opt for opt in security_opt), \
        f"security_opt missing no-new-privileges: {security_opt}"
```

### Parse Containerfile for Package Removal (NEW for Phase 135)

```python
# Source: Recommended pattern for Phase 135
def test_podman_package_removed():
    """CONT-07: Verify 'podman' package not installed in node image."""
    with open('puppets/Containerfile.node', 'r') as f:
        dockerfile_content = f.read()
    
    # Check that 'podman' doesn't appear in any RUN apt-get install lines
    import re
    run_lines = re.findall(r'RUN.*apt-get install.*', dockerfile_content)
    
    for line in run_lines:
        assert 'podman' not in line, \
            f"podman package appears in install line: {line}"
        assert 'iptables' not in line, \
            f"iptables package appears in install line: {line}"
        assert 'krb5-user' not in line, \
            f"krb5-user package appears in install line: {line}"
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (existing) |
| **Quick run command** | `cd puppeteer && pytest tests/test_nonroot.py -x -q` (Phase 132) |
| **Full suite command** | `cd puppeteer && pytest -x -q` |

### Phase Requirements → Test Map

| Phase | Requirements | Test Strategy | Primary Test File(s) | Manual Checks |
|-------|--------------|----------------|----------------------|---------------|
| **132** | CONT-01, CONT-06 | Live integration (running containers) | test_nonroot.py | Volume ownership on upgrade (requires old→new transition) |
| **133** | CONT-03, CONT-04 | Static YAML + live inspect (NEW) | test_security_capabilities.py (NEW) + test_compose_validation.py | Full stack startup after cap_drop changes |
| **134** | CONT-02, CONT-09, CONT-10 | Unit (mocked) + compose config validation | test_runtime_socket.py + test_node_compose.py | Job execution via socket; Podman rootless detection |
| **135** | CONT-05, CONT-07 | Compose syntax + Containerfile regex | test_compose_validation.py + manual dpkg checks | Resource limits enforced under load; autoremove didn't strip needed packages |
| **136** | CONT-08 | Unit tests on Foundry injection logic | test_foundry.py | Built Foundry image runs as UID 1000; jobs execute as appuser |

### Sampling Rate

**Phase 132:**
- Per-task commit: `cd puppeteer && pytest tests/test_nonroot.py -x -q`
- Per-wave: `cd puppeteer && pytest -x -q`
- Latency: <30s

**Phase 133 (NEW test file):**
- Per-task commit: `cd puppeteer && pytest tests/test_security_capabilities.py -x -q`
- Per-wave: `cd puppeteer && pytest -x -q`
- Latency: <30s (static YAML parsing is fast)

**Phase 134:**
- Per-task commit: `cd puppeteer && pytest tests/test_runtime_socket.py -x -q`
- Per-wave: `cd puppeteer && pytest -x -q`
- Latency: <30s (mocked; no Docker needed for unit tests)

**Phase 135:**
- Per-task commit: `docker compose -f puppeteer/compose.server.yaml config --quiet`
- Per-wave: `cd puppeteer && pytest -x -q`
- Latency: <30s

**Phase 136:**
- Per-task commit: `cd puppeteer && pytest tests/test_foundry.py -x -q -k "test_user_injection"`
- Per-wave: `cd puppeteer && pytest -x -q`
- Latency: <30s

### Wave 0 Gaps

**Phase 132:** Tests already exist and pass. No gaps.

**Phase 133:** 
- [ ] `puppeteer/tests/test_security_capabilities.py` — NEW FILE for static + live capability tests
  - Static: parse compose.server.yaml, assert cap_drop/security_opt/port bindings
  - Live: docker inspect running containers, assert CapDrop/SecurityOpt at runtime
  - Test count: ~6-8 tests (2 static per requirement + 2-3 live)

**Phase 134:** 
- test_runtime_socket.py exists and passes. test_node_compose.py exists. No gaps.

**Phase 135:** 
- Compose validation pattern exists. No new test file needed.
- dpkg -l checks are manual (post-build verification).

**Phase 136:** 
- test_foundry.py exists with user injection tests. No gaps.

---

## State of the Art

### Known Test Patterns in Codebase

| Pattern | Location | Applied By | Status |
|---------|----------|------------|--------|
| Async client fixture | conftest.py | All async tests | Mature |
| Container introspection via subprocess | test_nonroot.py | Phase 132 | Established |
| Mock-based unit tests | test_runtime_socket.py | Phase 134 | Established |
| Compose config validation | test_compose_validation.py | Phase 134 endpoint | Established |
| Foundry test structure | test_foundry.py | Phase 136 | Mature (50+ tests) |

### Deprecated/Outdated

- **EXECUTION_MODE=direct:** No longer supported as of v20.0 (Phase 134 tests verify only docker/podman/auto are accepted)
- **Manual verification scripts:** test_nonroot.py and test_runtime_socket.py replace what used to be shell scripts

---

## Open Questions

1. **How does `/gsd:validate-phase` populate VALIDATION.md automatically?**
   - What we know: Planner reads existing VALIDATION.md, runs tests per Per-Task Verification Map, updates nyquist_compliant/wave_0_complete
   - What's unclear: Does validate-phase auto-discover new test files, or must VALIDATION.md list them explicitly?
   - Recommendation: Check validate-phase implementation; CONTEXT.md suggests VALIDATION.md is the source of truth for what tests to run

2. **Does Phase 133 require stack restart between static and live tests?**
   - What we know: compose.server.yaml has cap_drop/security_opt configured
   - What's unclear: Do containers need to be restarted after we verify the static file, or are they already running with the correct config?
   - Recommendation: Document in VALIDATION.md that live tests assume fresh containers (stack started after compose changes)

3. **How to handle multi-service capability verification?**
   - What we know: Caddy needs NET_BIND_SERVICE exception; other services are drop: ALL
   - What's unclear: Should test_security_capabilities.py special-case Caddy, or should the assertion be "cap_drop: ALL OR (cap_drop: [list] AND cap_add: [list])"?
   - Recommendation: Use conditional assertion: loop services, for each check if cap_add is present (exception), else require cap_drop: ALL

---

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md** (Phase 143) — Locked decisions on test strategy, Phase 133 gaps, sequential execution, compliance threshold
- **REQUIREMENTS.md** (v22.0) — Container hardening requirements (CONT-01 to CONT-10) that validation must verify
- **STATE.md** — Project history; all 5 phases (132–136) are complete and passed VERIFICATION.md; only Nyquist validation (wave 0) pending
- **Existing test files** — test_nonroot.py, test_runtime_socket.py, test_compose_validation.py (patterns verified in working code)

### Secondary (MEDIUM confidence)
- **v22.0-MILESTONE-AUDIT.md** — All 16 requirements satisfied; audit identified tech debt but no functional gaps; Nyquist status is "partial_phases" (not yet validated)
- **Phase 132–136 VALIDATION.md files** — Per-task verification maps; existing tests and gaps documented
- **pytest documentation** — Standard async fixture patterns, subprocess mocking strategies (verified against conftest.py usage)

### Tertiary (LOW confidence — flagged for validation)
- yaml.safe_load() necessity for Phase 133 — assumed but not verified in existing codebase (no compose YAML parsing tests found yet; recommend confirming PyYAML is in requirements.txt)

---

## Metadata

**Confidence breakdown:**
- **Test infrastructure & patterns:** HIGH — All patterns verified in working test files; subprocess/mock/async patterns are established and tested
- **Phase 133 static test approach:** MEDIUM — PyYAML pattern recommended but not yet implemented in repo; yaml.safe_load() is standard Python (no risk), but integration into conftest/fixtures needs validation
- **Execution order & sequencing:** HIGH — Locked in CONTEXT.md with clear rationale (file conflicts between phases)
- **Wave 0 gaps:** HIGH — Phase 133 clearly needs new test file; other phases have existing test files with no identified gaps

**Research date:** 2026-04-14  
**Valid until:** 2026-04-21 (test infrastructure is stable; expires only if compose.server.yaml structure changes or pytest version major bump occurs)

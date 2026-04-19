# Technology Stack: Node Capacity Validation (v20.0)

**Project:** Axiom — Task Orchestration with Resource Limits
**Researched:** 2026-04-06

## Recommended Stack

### Core Backend (Existing, No Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.104+ | REST API server | async-native, auto OpenAPI docs, pydantic validation |
| SQLAlchemy | 2.0+ | ORM for Job/Node/ScheduledJob persistence | async support, strong type hints, schema migration via create_all |
| Pydantic | 2.0+ | Request/response validation | field validators, discriminated unions, JSON serialization |
| PostgreSQL | 15+ | Production persistence (optional) | ACID, JSON columns, async driver (asyncpg) |
| SQLite | 3.40+ | Local dev persistence | serverless, no setup, file-based |
| Python | 3.11+ | Backend runtime | type hints, async/await, standard library |

### Node Agent (Existing, Minimal Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Node agent runtime | async, subprocess, container integration |
| httpx | 0.24+ | mTLS HTTP client for polling | async, client cert support |
| cryptography | 41+ | mTLS cert signing, Ed25519 verification | FIPS-compatible, low-level crypto |
| aiohttp | 3.8+ | Async HTTP server (sidecar) | lightweight, async, WebSocket support |
| psutil | 5.9+ | System metrics (CPU/RAM) | cross-platform, reliable |
| asyncio | stdlib | Async job execution | built-in, no external deps |

### Runtime Container Integration (Existing, No Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker | 20.10+ | Container runtime (primary) | industry standard, cgroup v1/v2 support, --memory/--cpus flags |
| Podman | 3.0+ | Container runtime (alternative) | rootless-capable, OCI-compliant, same CLI as docker |
| Linux Kernel | 5.10+ | Cgroup enforcement | both v1 and v2 support, memory + cpu limits |
| Docker API | 1.41+ | Subprocess CLI invocation | used via docker run / podman run, not SDK |

### Frontend (Existing, Minimal Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18+ | UI framework | component-driven, hooks, hooks for state |
| TypeScript | 5.0+ | Type safety | catches UI bugs, intellisense |
| Vite | 4.0+ | Build tool | fast HMR, minimal config, tree-shaking |
| Radix UI | 1.0+ | Headless component library | a11y-first, unstyled, composable |
| TailwindCSS | 3.0+ | Utility CSS | rapid prototyping, consistent theming |
| Recharts | 2.0+ | Charting library | React-native, responsive, legends/tooltips |
| Playwright | 1.40+ | E2E testing | fast, multi-browser, headless |

### Testing (Existing, No Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 7.4+ | Backend unit tests | async fixtures, parametrize, clear syntax |
| vitest | 0.34+ | Frontend unit/component tests | Vite-native, Jest-compatible syntax |
| asyncio | stdlib | Async test execution | built-in, no external deps |

## New Dependencies for v20.0

### None

**Explanation:** v20.0 does NOT require new external dependencies.

- **CgroupDetector** is implemented using stdlib `os.path.exists()` — no external library needed
- **Limit validation** uses stdlib `re` for regex — no external library needed
- **Stress test corpus** scripts use only stdlib (sys, time, multiprocessing, json) — no external library needed
- **Existing runtime.py** already has all necessary flags for docker/podman limit support

## Optional: Development Convenience

| Technology | Version | Purpose | Optional |
|------------|---------|---------|----------|
| ruff | 0.1+ | Python linter | faster black + isort, already used in CI |
| mypy | 1.0+ | Static type checker | catch type errors in models, already used in CI |
| pytest-cov | 4.1+ | Code coverage | measure test coverage for corpus |
| httpx | 0.24+ | HTTP client in test scripts | simplify dispatch_stress_corpus.py API calls |

**Recommendation:** Use existing tooling (ruff, mypy from CI). httpx already installed for node agent.

## Installation

### Backend (No New Packages)

```bash
# requirements.txt already covers all dependencies
cd puppeteer
pip install -r requirements.txt
# No new entries needed for v20.0
```

### Node Agent (No New Packages)

```bash
# environment_service/requirements.txt already complete
# No changes needed
pip install httpx cryptography aiohttp psutil
```

### Frontend (No New Packages)

```bash
cd puppeteer/dashboard
npm install
# package.json already has all dependencies
# No new entries needed
```

### Test Corpus (Stdlib Only)

```bash
# Corpus scripts use only Python stdlib
# No pip install needed
# Just run: python corpus/memory_alloc.py 256
```

## Build & Test Stack

### Docker Compose (for local validation)

```yaml
services:
  agent:
    image: python:3.12-slim
    volumes:
      - ./puppeteer:/app
    command: python -m agent_service.main

  node-alpha:
    image: localhost/master-of-puppets-node:latest
    environment:
      EXECUTION_MODE: docker
      JOB_MEMORY_LIMIT: 512m
    depends_on:
      - agent
```

### CI/CD Pipeline (GitHub Actions)

```yaml
- backend tests: pytest
- frontend tests: npm run test
- docker build: docker compose -f compose.server.yaml build agent
- integration: mop_validation/scripts/dispatch_stress_corpus.py
```

## Architecture Decisions

### Why Not Add External Packages?

1. **Minimal dependencies** — Axiom philosophy: reduce supply-chain risk
2. **Stdlib sufficient** — os.path, re, json, subprocess, asyncio all built-in
3. **Maintainability** — Fewer upgrades, fewer CVEs to track
4. **Cgroup detection** — Simple sysfs checks, no library needed
5. **Test corpus** — Pure Python with stdlib only (portable across environments)

### Why Docker/Podman (Not Kubernetes)?

1. **Simple** — Single CLI invocation, no orchestrator overhead
2. **Isolated** — Each job is a fresh container, no state pollution
3. **Portable** — Works on dev laptop, VPS, cloud VM
4. **Familiar** — Operators know docker run / podman run flags
5. **Limits** — Native cgroup support via --memory/--cpus flags

### Why Cgroup Not Resource Quotas?

1. **Kernel-enforced** — No app polling, hard limit at kernel level
2. **Accurate** — Actual memory/CPU consumed, not estimated
3. **Fair** — Linux scheduler respects limits even under extreme load
4. **Mature** — v1 since 2008, v2 since 2019, production-proven

## Version Compatibility

### Minimum Versions (for limit enforcement)

| Component | Min Version | Why |
|-----------|-------------|-----|
| Python | 3.11 | asyncio.create_subprocess_exec, type hints |
| Docker | 20.10 | --memory, --cpus flags, cgroup v2 support |
| Podman | 3.0 | OCI compliance, cgroup v2 support |
| Linux Kernel | 5.10 | cgroup v2 unified interface, memory.max |
| PostgreSQL | 15 | async driver (asyncpg), performance |

### Tested Environments

| OS | Kernel | Cgroup | Docker | Status |
|----|--------|--------|--------|--------|
| Ubuntu 22.04 LTS | 5.15 | v2 | 24.0 | ✓ Supported |
| Debian 12 | 6.1 | v1 | 24.0 | ✓ Supported |
| Fedora 39 | 6.5 | v2 | 48.0 | ✓ Supported |
| Alpine 3.18 | 6.1 | v1 | 24.0 | ✓ Supported (musl libc) |
| macOS 13 (Rosetta) | — | N/A | 24.0 via Docker Desktop | ✓ Dev only |

## Migration Path: Adding Limits

**No breaking changes.** Limits are optional (nullable in DB).

### Backwards Compatibility

```python
# Old code (no limits)
job = Job(guid="...", task_type="script", payload="...")

# New code (with limits)
job = Job(guid="...", task_type="script", payload="...", 
          memory_limit="512m", cpu_limit="1.0")

# Old dispatch (limits=None) still works
node.execute_task({
    "guid": "...",
    "memory_limit": None,  # OK
    "cpu_limit": None,     # OK
})

# New dispatch (limits set) also works
node.execute_task({
    "guid": "...",
    "memory_limit": "256m",  # OK
    "cpu_limit": "0.5",      # OK
})
```

## Sources

- **Docker limits:** https://docs.docker.com/config/containers/resource_constraints/
- **Podman limits:** https://docs.podman.io/en/latest/markdown/podman-run.1.html
- **Cgroups v1 vs v2:** https://www.kernel.org/doc/html/latest/admin-guide/cgroups-v2.html
- **Python asyncio subprocess:** https://docs.python.org/3/library/asyncio-subprocess.html
- **FastAPI async:** https://fastapi.tiangolo.com/async-sql-databases/
- **Axiom existing stack:** puppeteer/requirements.txt, puppets/environment_service/requirements.txt

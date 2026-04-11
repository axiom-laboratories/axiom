# Phase 130: E2E Job Dispatch Integration Test - Research

**Researched:** 2026-04-11
**Domain:** Integration testing, job lifecycle, signature verification, response models
**Confidence:** HIGH

## Summary

Phase 130 requires two complementary integration tests that verify the complete job dispatch pipeline end-to-end: from signature registration through job creation, node work polling, execution, result retrieval, and diagnosis. The pytest test (in `puppeteer/tests/`) exercises the service layer directly with simulated node operations, validating response models and state machine transitions. The mop_validation E2E script runs against a live Docker stack with a real enrolled node, proving actual job execution with output capture.

Both tests share the same logical flow but differ in scope: pytest validates the API contract and state machine, while the live script validates real container execution and network communication. The infrastructure is mature (existing conftest, service functions, and local node compose configs all available), so the focus is on test orchestration and assertion depth.

**Primary recommendation:** Use service-layer direct calls in pytest tests (no mocking) to avoid test fragility; design the live E2E script as a self-contained orchestrator that manages its own node lifecycle and reports structured JSON results.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Both test locations required:** pytest file in `puppeteer/tests/test_dispatch_e2e.py` AND standalone script in `mop_validation/scripts/e2e_dispatch_integration.py`
- **Pytest approach:** Direct service-layer calls (no mTLS, no mock patching), simulating node work pull via `JobService.pull_work()` directly
- **Live script approach:** Real enrolled node from `local_nodes/` with Docker compose orchestration
- **Test scenarios (pytest):**
  - Happy path: signed job → node pulls → job completes → result retrievable
  - Bad signature rejection: invalid/missing signature rejected at submission
  - Capability mismatch: job targets missing capability → stays PENDING, diagnosis explains why
  - Retry on failure: node reports failed → job retries up to max_retries
- **Test scenarios (live script):**
  - Happy path with real execution: sign Python script, submit, execute in container, capture output
  - Signed vs unsigned: unsigned rejected, signed succeeds
  - Capability-targeted dispatch: job targets capability tag, verify node match
  - Concurrent jobs: 3 jobs submitted simultaneously, isolation verified
- **Assertion depth (pytest):**
  - Response model validity via Pydantic (catches Phase 129 regressions)
  - State machine transitions: PENDING → ASSIGNED → COMPLETED/FAILED (or FAILED → RETRYING)
  - Output content: result contains expected print output
  - Dispatch diagnosis accuracy: unassigned jobs explain why (reason + message)
- **Live script reporting:**
  - Console: PASS/FAIL per scenario, exit code 0 on all pass / 1 on failure
  - JSON: structured report to `mop_validation/reports/e2e_dispatch_integration_report.json`

### Claude's Discretion
- Exact conftest fixture structure (add shared fixtures vs self-contained in test file)
- Which `local_nodes/` node to use (node_alpha, node_beta, node_gamma available)
- Polling interval and timeout values for live script job completion waits
- Exact Python script payload for test jobs (deterministic + lightweight)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

---

## Standard Stack

### Test Infrastructure (pytest)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| pytest | 7.x+ | Test runner for `puppeteer/tests/` | Already in requirements; Phase 129 used it |
| pytest-asyncio | 0.21+ | Async test support (`@pytest.mark.asyncio`) | Enables `async def test_*()` patterns |
| SQLAlchemy AsyncSession | 2.0+ | In-memory test DB fixture | Existing conftest.py uses it; no migrations needed |
| httpx AsyncClient | 0.24+ | Fast async HTTP client | Already in conftest for endpoint testing |
| Pydantic | 2.0+ | Response model validation | Phase 129 standardized all response models |

### Job Service Layer

| Function | Module | Purpose | Why Use |
|----------|--------|---------|---------|
| `JobService.create_job()` | `agent_service/services/job_service.py` | Persist job to DB, validate admission control | Entry point for job dispatch; validates memory/env_tag/signature |
| `JobService.pull_work()` | `agent_service/services/job_service.py` | Node polls for assigned work | Simulates node behavior; returns `PollResponse` with `WorkResponse` payload |
| `JobService.report_result()` | `agent_service/services/job_service.py` | Node submits job completion + output | Closes job lifecycle; updates status to COMPLETED/FAILED |
| `JobService.get_dispatch_diagnosis()` | `agent_service/services/job_service.py` | Explain why PENDING job hasn't assigned | Returns reason + message for capability/node mismatches |
| `SignatureService.verify_payload_signature()` | `agent_service/services/signature_service.py` | Verify Ed25519 signature on script payload | Validates signature_payload before job creation |

### Response Model Standards (Phase 129)

| Model | Fields | Source |
|-------|--------|--------|
| `JobResponse` | guid, status, payload, result, node_id, started_at, duration_seconds, target_tags, task_type, display_type, name, created_by, created_at, runtime | `agent_service/models.py` line 117 |
| `WorkResponse` | guid, task_type, payload, max_retries, backoff_multiplier, timeout_minutes, memory_limit, cpu_limit, signature_id, signature_payload | `agent_service/models.py` line 189 |
| `DispatchDiagnosisResponse` | reason, message, details | `agent_service/models.py` line 174 |
| `ResultReport` | result, error_details, success, output_log, exit_code, retriable | `agent_service/models.py` line 200 |
| `PollResponse` | job (WorkResponse), env_tag | `agent_service/models.py` line 271 |

**Why important:** Phase 129 completed 100% response_model decorator coverage across all 89 routes. Tests must parse all returned JSON through these models to catch regressions (typos in field names, missing fields, type mismatches).

### Live Node Composition

| Config | Purpose | Location | Key Env Vars |
|--------|---------|----------|--------------|
| node_alpha compose | Basic test node, Docker runtime | `mop_validation/local_nodes/node_alpha/node-compose.yaml` | `AGENT_URL=https://puppeteer-agent-1:8001`, `JOIN_TOKEN_ALPHA` |
| node_beta compose | Alternate node for isolation test | `mop_validation/local_nodes/node_beta/node-compose.yaml` | Similar to alpha |
| docker-node-compose | Validation node, explicit Docker socket | `mop_validation/local_nodes/docker-node-compose.yaml` | Standalone (not in puppeteer network) |

**Network:** node_alpha/beta use `puppeteer_default` external network (must exist; created by main `docker compose up`); docker-node is standalone with `host.docker.internal` hostname.

---

## Architecture Patterns

### Pytest Test Structure

**File:** `puppeteer/tests/test_dispatch_e2e.py`

```python
# Fixture scope: function (fresh DB per test, reuses conftest async_client)
@pytest.fixture
async def enrolled_node(db):
    """Create an ONLINE node for pull_work() simulation."""
    node = Node(
        node_id="test-node-001",
        hostname="test-node",
        ip="127.0.0.1",
        status="ONLINE",
        tags=json.dumps(["python", "docker"]),
        capabilities=json.dumps({"python": "3.11", "docker": "24.0"}),
    )
    db.add(node)
    await db.commit()
    return node

# Test pattern: service-layer calls, no HTTP (no mocking, no transport layer)
@pytest.mark.asyncio
async def test_happy_path_dispatch(setup_db, enrolled_node, db):
    """
    Happy path: create signed job → node pulls → job completes → result retrievable
    Validates: JobResponse structure, state transitions, output content
    """
    # 1. Create job (validates signature if present)
    job_req = JobCreate(
        task_type="script",
        runtime="python",
        payload={"script_content": "print('hello world')"},
        max_retries=1,
    )
    job_dict = await JobService.create_job(job_req, db)
    assert job_dict["status"] == "PENDING"
    
    # 2. Node pulls work
    poll = await JobService.pull_work(enrolled_node.node_id, "127.0.0.1", db)
    assert poll.job is not None  # WorkResponse
    assert poll.job.guid == job_dict["guid"]
    assert poll.job.task_type == "script"
    
    # 3. Verify WorkResponse structure via Pydantic (no ValidationError)
    work_model = WorkResponse(**poll.job.model_dump())  # Explicit conversion
    assert work_model.guid is not None
    assert work_model.payload["script_content"] == "print('hello world')"
    
    # 4. Node reports completion
    result = ResultReport(
        success=True,
        output_log=[{"t": "stdout", "stream": "stdout", "line": "hello world"}],
        exit_code=0,
    )
    updated = await JobService.report_result(job_dict["guid"], result, "127.0.0.1", db)
    assert updated["status"] == "COMPLETED"
    assert updated["result"]["exit_code"] == 0
```

**Key points:**
- No FastAPI `AsyncClient` calls — all via service functions directly
- Fixture-based node creation with realistic capabilities JSON
- Pydantic model parsing validates response structure (Phase 129 regression check)
- State assertions on db objects before/after each step

### Capability Mismatch Pattern

```python
@pytest.mark.asyncio
async def test_capability_mismatch_diagnosis(setup_db, enrolled_node, db):
    """
    Job requires capability node lacks → stays PENDING
    Diagnosis explains the mismatch
    """
    # Node has python, not cuda
    node = _make_node(capabilities={"python": "3.11"})
    db.add(node)
    
    # Job requires cuda
    job_req = JobCreate(
        task_type="script",
        runtime="python",
        payload={"script_content": "import torch"},
        capability_requirements={"cuda": "11.8"},
    )
    job_dict = await JobService.create_job(job_req, db)
    
    # Node pulls — job should NOT be assigned (no capability match)
    poll = await JobService.pull_work(node.node_id, "127.0.0.1", db)
    assert poll.job is None  # No work available
    
    # Diagnosis explains why
    diagnosis = await JobService.get_dispatch_diagnosis(job_dict["guid"], db)
    assert diagnosis["reason"] == "capability_mismatch"
    assert "cuda" in diagnosis["message"].lower()
```

**Why this pattern:** Tests the admission logic directly; validates diagnosis accuracy without deploying nodes.

### Signature Validation Pattern (pytest)

```python
@pytest.mark.asyncio
async def test_bad_signature_rejection(setup_db, db):
    """
    Job with invalid signature_id or bad signature_payload → HTTP 422 at submission
    """
    job_req = JobCreate(
        task_type="script",
        runtime="python",
        payload={
            "script_content": "print('hack')",
            "signature_id": "nonexistent-sig-uuid",
            "signature_payload": base64.b64encode(b"bad").decode(),
        },
    )
    
    # Verify via signature service (optional; mainly for test coverage)
    # This depends on whether sig validation happens in create_job or elsewhere
    # If in create_job, the HTTPException(422) bubbles up
    # If deferred, we'd need to check the HMAC computation
    
    with pytest.raises(HTTPException) as exc:
        await JobService.create_job(job_req, db)
    # Or check that job was created but marked with signature_hmac validation error
```

**Note:** Signature validation is pluggable depending on current architecture (Phase 129 may have introduced changes). Research confirms signature_hmac is stamped on creation (line 572 job_service.py) but exact validation hook needs confirmation during implementation.

---

## Live E2E Script Structure

**File:** `mop_validation/scripts/e2e_dispatch_integration.py`

```python
#!/usr/bin/env python3
"""
E2E dispatch integration test: submits signed jobs to live Docker stack,
verifies execution on real enrolled node, captures output.

Flow:
1. Pre-flight check (Docker socket, stack running, node network available)
2. Manage node lifecycle (docker compose up node_alpha)
3. Enroll node via /api/enroll
4. Submit signed test job
5. Poll for completion
6. Verify output
7. Cleanup (docker compose down)

Report: structured JSON + console summary
"""

import requests
import json
import time
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_URL = "https://puppeteer-agent-1:8001"
ROOT_CA = Path("puppeteer/secrets/ca/root_ca.crt")
VERIFY_SSL = ROOT_CA.exists()

# Sessions with auth
sess = requests.Session()
sess.verify = str(ROOT_CA) if VERIFY_SSL else False
sess.headers.update({"Authorization": f"Bearer {get_token()}"})

def docker_compose_node(action="up"):
    """Manage node_alpha lifecycle: up/down"""
    compose_file = "mop_validation/local_nodes/node_alpha/node-compose.yaml"
    env = os.environ.copy()
    env["JOIN_TOKEN_ALPHA"] = generate_join_token()  # API call to get token
    cmd = ["docker", "compose", "-f", compose_file, action]
    subprocess.run(cmd, env=env, check=True)

def run_scenario_happy_path():
    """
    Happy path: sign job → submit → poll until complete → verify output
    """
    script = """
import json
result = {"message": "e2e test success", "timestamp": time.time()}
print(json.dumps(result))
"""
    
    # 1. Sign
    sig_payload, sig_id = sign_script(script)
    
    # 2. Submit
    job_req = {
        "task_type": "script",
        "runtime": "python",
        "payload": {
            "script_content": script,
            "signature_payload": sig_payload,
            "signature_id": sig_id,
        },
    }
    resp = sess.post(f"{BASE_URL}/jobs", json=job_req)
    assert resp.status_code == 200, f"Job creation failed: {resp.text}"
    job = resp.json()
    job_guid = job["guid"]
    
    # 3. Poll until COMPLETED
    for _ in range(60):  # 60 sec timeout
        resp = sess.get(f"{BASE_URL}/jobs/{job_guid}")
        assert resp.status_code == 200
        job = resp.json()
        
        if job["status"] == "COMPLETED":
            break
        if job["status"] in ("FAILED", "DEAD_LETTER"):
            raise AssertionError(f"Job failed: {job}")
        
        time.sleep(1)
    
    # 4. Verify output
    assert job["result"] is not None
    assert job["result"]["exit_code"] == 0
    assert "e2e test success" in job["result"]["output_log"][0]["line"]
    
    return {"scenario": "happy_path", "status": "PASS", "job_guid": job_guid}

def run_scenario_concurrent():
    """
    3 jobs submitted simultaneously, all complete with isolation
    """
    jobs = []
    for i in range(3):
        # Each job sleeps then prints unique ID
        script = f'import time; time.sleep(0.5); print("job_{i}_{int(time.time())})'
        job_req = {...}
        resp = sess.post(f"{BASE_URL}/jobs", json=job_req)
        jobs.append(resp.json()["guid"])
    
    # Poll all
    start = time.time()
    while time.time() - start < 30:
        all_done = all(
            sess.get(f"{BASE_URL}/jobs/{g}").json()["status"] == "COMPLETED"
            for g in jobs
        )
        if all_done:
            break
        time.sleep(0.5)
    
    # Verify each has output
    for guid in jobs:
        job = sess.get(f"{BASE_URL}/jobs/{guid}").json()
        assert job["status"] == "COMPLETED"
        assert job["result"]["exit_code"] == 0
    
    return {"scenario": "concurrent", "status": "PASS", "job_count": 3}

# Main
if __name__ == "__main__":
    results = []
    try:
        docker_compose_node("up")
        time.sleep(5)  # Let node enroll
        
        results.append(run_scenario_happy_path())
        results.append(run_scenario_signed_vs_unsigned())
        results.append(run_scenario_concurrent())
        
        # Write JSON report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "scenarios": results,
            "pass_count": sum(1 for r in results if r["status"] == "PASS"),
            "fail_count": sum(1 for r in results if r["status"] == "FAIL"),
        }
        
        with open("mop_validation/reports/e2e_dispatch_integration_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Console output
        for r in results:
            print(f"{r['scenario']}: {r['status']}")
        
        sys.exit(0 if all(r["status"] == "PASS" for r in results) else 1)
    
    finally:
        docker_compose_node("down")
```

**Key points:**
- Self-contained: no external dependencies beyond Docker + requests
- Pre-flight checks (stack running, socket available, network exists)
- Node lifecycle management (bring up, enroll, tear down)
- Three scenario types: happy path, signed vs unsigned, concurrent isolation
- Polling with realistic timeouts (60 sec for completion, 30 sec for concurrent)
- JSON report written regardless of pass/fail
- Exit code 0 on all scenarios pass, 1 on any failure

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test DB setup with schema evolution | Custom migration scripts | `conftest.py` `setup_db` fixture with `ALTER TABLE` fallback | Already handles missing columns; schema is stable; avoids migration complexity |
| Job state machine transitions | Custom state validators | `JobService` functions (create_job, pull_work, report_result) | Existing functions implement retry logic, zombie reaping, and correct ordering |
| Ed25519 signature verification | Homebrew crypto | `SignatureService.verify_payload_signature()` | Uses `cryptography` library; handles PEM parsing and verification correctly |
| JWT token generation | Manual encode/decode | `agent_service.auth.create_access_token()` + `AsyncSessionLocal` for token_version | Already integrated; handles token_version for session security |
| Node enrollment | Manual cert handling, mTLS setup | Live node's init code (enrolled via JOIN_TOKEN) | Nodes handle PKI bootstrap; tests just need to call /api/enroll or deploy compose |
| Job result polling | Busy-loop with hardcoded sleeps | Service-layer query + exponential backoff | Tests can sleep(1); live script can poll with 1-2 sec intervals + timeout |
| Capability matching | String parsing | `JobService.pull_work()` logic (uses node.capabilities JSON + job.capability_requirements) | Already implements version comparison (packaging.version.Version) |

**Key insight:** The job service layer is mature and thoroughly tested; tests should drive it directly rather than building parallel logic. Same for auth and signature handling — use existing functions.

---

## Common Pitfalls

### Pitfall 1: Confusing Response Model Structure with JSON
**What goes wrong:** Test receives JSON from API, tries to access field as if it's a Python dict, but Pydantic model has different field name (e.g., `display_type` not `displayType`).

**Why it happens:** Phase 129 changed response model naming; JSON keys match Python attribute names (snake_case), not camelCase.

**How to avoid:** Always parse JSON through Pydantic model first:
```python
# WRONG
assert resp.json()["displayType"] == "script (python)"

# RIGHT
job = JobResponse(**resp.json())
assert job.display_type == "script (python)"
```

**Warning signs:** `KeyError` on response parsing, assertion mismatch on field values.

### Pitfall 2: Job Status Machine Misunderstanding
**What goes wrong:** Test expects job to move PENDING → ASSIGNED immediately, but it stays PENDING if no node can take it (memory admission, capability mismatch, etc.).

**Why it happens:** `pull_work()` only assigns if node matches ALL requirements; unmet requirements leave job PENDING (diagnosed via `/dispatch-diagnosis`).

**How to avoid:** Always check `pull_work()` return value — if `poll.job is None`, job stayed PENDING. Use diagnosis endpoint to understand why.

**Expected transitions:**
- Happy path: PENDING → ASSIGNED (when pulled) → COMPLETED/FAILED (when reported)
- Failure + retry: FAILED → RETRYING (after backoff) → PENDING → ASSIGNED → COMPLETED
- Unassigned: PENDING (stays, diagnosis explains why)

**Warning signs:** Tests asserting job is ASSIGNED without checking if pull succeeded; missing diagnosis assertions for "pending" scenarios.

### Pitfall 3: Signature Payload vs Script Content Confusion
**What goes wrong:** Test signs script content, puts signature in `signature_payload`, then node fails because it's looking for the signature in wrong field.

**Why it happens:** The payload structure has both `script_content` (plain text) and `signature_payload` (base64 signature). They must be paired correctly.

**How to avoid:** Follow the pattern from `run_signed_job.py` and Phase 129:
```python
script_content = "print('hello')"
sig_payload = sign_script(script_content)  # base64-encoded

payload = {
    "script_content": script_content,
    "signature_payload": sig_payload,
    "signature_id": "some-uuid",  # Registration ID of public key
}
```

**Warning signs:** Node execution fails with "security rejected" or "signature invalid"; signature verification exceptions in logs.

### Pitfall 4: Memory Format Inconsistency
**What goes wrong:** Test submits job with `memory_limit="512m"`, but queries expect bytes. Or queries return "512.0Mi" format, test expects "512m".

**Why it happens:** `parse_bytes()` converts string → bytes; `_format_bytes()` converts bytes → human-readable. Strings used in JSON can differ.

**How to avoid:** Use `parse_bytes()` and `_format_bytes()` consistently:
```python
# Store in DB as string (e.g., "512m")
job_req.memory_limit = "512m"

# When querying, parse to bytes for comparison
node_capacity_bytes = parse_bytes(node.job_memory_limit or "512m")
job_bytes = parse_bytes("512m")
assert job_bytes <= node_capacity_bytes
```

**Warning signs:** Admission control tests fail with "no capacity" even when node has plenty; byte count mismatches in assertions.

### Pitfall 5: Async/Await Mistakes in Fixtures
**What goes wrong:** Fixture creates a DB object but doesn't `await db.commit()`, so later tests see stale/uncommitted data.

**Why it happens:** AsyncSession requires `await` for all I/O; synchronous DB writes in fixtures are silently lost.

**How to avoid:** All fixture setup must be `async` and use `await`:
```python
@pytest.fixture
async def enrolled_node(setup_db):  # setup_db must run first
    async with AsyncSessionLocal() as db:
        node = Node(...)
        db.add(node)
        await db.commit()  # ← CRITICAL
        await db.refresh(node)  # Refresh to ensure ID is populated
        return node
```

**Warning signs:** Tests fail with "node not found" even though fixture created it; stale data visible across tests.

### Pitfall 6: Network Issues in Live E2E Script
**What goes wrong:** Script tries to connect to `https://puppeteer-agent-1:8001` but name doesn't resolve (node compose network misconfigured or host network wrong).

**Why it happens:** Node compose uses `puppeteer_default` external network which must be created by main stack; if main stack never ran, network doesn't exist.

**How to avoid:** Live script should:
1. Check if Docker stack running: `docker ps | grep puppeteer-agent-1`
2. Verify network exists: `docker network ls | grep puppeteer_default`
3. Use realistic VERIFY_SSL (follow ROOT_CA path from compose secrets)

**Pre-flight example:**
```python
def check_prerequisites():
    # Is Docker running?
    subprocess.run(["docker", "ps"], check=True)
    
    # Is stack up?
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=puppeteer-agent-1"],
        capture_output=True
    )
    if not result.stdout:
        print("ERROR: puppeteer-agent-1 not running. Run: docker compose -f puppeteer/compose.server.yaml up -d")
        sys.exit(1)
    
    # Is network available?
    result = subprocess.run(
        ["docker", "network", "ls", "--filter", "name=puppeteer_default"],
        capture_output=True
    )
    if not result.stdout:
        print("ERROR: puppeteer_default network missing")
        sys.exit(1)
```

**Warning signs:** `ConnectionError: nodename nor servname provided` or `Network (name) not found`.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Creating and Polling a Job (pytest)

Source: `puppeteer/agent_service/services/job_service.py` line 436 (`create_job`) and line 703 (`pull_work`)

```python
import json
import uuid
from agent_service.services.job_service import JobService
from agent_service.models import JobCreate, ResultReport
from agent_service.db import Job, Node

@pytest.mark.asyncio
async def test_dispatch_happy_path(async_client, auth_headers, setup_db):
    """Service-layer test: create job, pull, report result, verify response model."""
    
    # 1. Create job via service (not HTTP)
    job_req = JobCreate(
        task_type="script",
        runtime="python",
        payload={"script_content": "print('hello')"},
        max_retries=0,
    )
    
    # Get db session from conftest
    from agent_service.db import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        job_dict = await JobService.create_job(job_req, db)
        assert job_dict["status"] == "PENDING"
        job_guid = job_dict["guid"]
        
        # 2. Create a node to pull work
        node = Node(
            node_id="test-node-1",
            hostname="test-node",
            ip="127.0.0.1",
            status="ONLINE",
            tags=json.dumps(["python"]),
            capabilities=json.dumps({"python": "3.11"}),
        )
        db.add(node)
        await db.commit()
        
        # 3. Node pulls work
        poll = await JobService.pull_work("test-node-1", "127.0.0.1", db)
        assert poll.job is not None
        assert poll.job.guid == job_guid
        
        # 4. Verify WorkResponse structure (Phase 129 regression check)
        from agent_service.models import WorkResponse
        work = WorkResponse(**poll.job.model_dump())  # Will raise ValidationError if malformed
        assert work.task_type == "script"
        assert work.payload["script_content"] == "print('hello')"
        
        # 5. Node reports completion
        result = ResultReport(
            success=True,
            exit_code=0,
            output_log=[
                {"t": str(uuid.uuid4()), "stream": "stdout", "line": "hello"}
            ],
        )
        updated = await JobService.report_result(job_guid, result, "127.0.0.1", db)
        
        # 6. Verify JobResponse structure (Phase 129 regression check)
        from agent_service.models import JobResponse
        job = JobResponse(**updated)
        assert job.status == "COMPLETED"
        assert job.result["exit_code"] == 0
```

### Capability Mismatch Diagnosis (pytest)

Source: `puppeteer/agent_service/services/job_service.py` line 1113 (`get_dispatch_diagnosis`)

```python
@pytest.mark.asyncio
async def test_capability_mismatch_stays_pending(setup_db):
    """Job requires GPU but node has only Python → stays PENDING, diagnosis explains."""
    
    from agent_service.db import AsyncSessionLocal, Node, Job
    from agent_service.services.job_service import JobService
    from agent_service.models import JobCreate
    import json
    
    async with AsyncSessionLocal() as db:
        # Node with Python only
        node = Node(
            node_id="python-node",
            hostname="python-node",
            ip="127.0.0.1",
            status="ONLINE",
            capabilities=json.dumps({"python": "3.11"}),
            tags=json.dumps([]),
        )
        db.add(node)
        await db.commit()
        
        # Job requires CUDA
        job_req = JobCreate(
            task_type="script",
            runtime="python",
            payload={"script_content": "import torch"},
            capability_requirements={"cuda": "11.8"},
        )
        job_dict = await JobService.create_job(job_req, db)
        
        # Node tries to pull — should get nothing (job can't run here)
        poll = await JobService.pull_work("python-node", "127.0.0.1", db)
        assert poll.job is None, "Job should not be assigned to node without CUDA"
        
        # Diagnosis explains
        diagnosis = await JobService.get_dispatch_diagnosis(job_dict["guid"], db)
        assert diagnosis["reason"] == "capability_mismatch"
        assert "cuda" in diagnosis["message"].lower()
```

### Signing and Submitting a Job (live script)

Source: `mop_validation/scripts/run_signed_job.py` and phase 129 changes

```python
#!/usr/bin/env python3
import requests
import base64
import os
import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

BASE_URL = "https://puppeteer-agent-1:8001"
ROOT_CA = "puppeteer/secrets/ca/root_ca.crt"

def sign_script(script_content: str) -> tuple:
    """Sign script with Ed25519 private key. Returns (signature_payload_b64, signature_id)."""
    
    # Load signing private key (admin uploads public key to /signatures endpoint)
    with open("puppeteer/secrets/signing.key", "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )
    
    # Sign
    sig_bytes = private_key.sign(script_content.encode('utf-8'))
    sig_payload_b64 = base64.b64encode(sig_bytes).decode()
    
    # Get signature ID from API (or use a pre-registered one)
    # For testing, use a known registered signature ID
    signature_id = "test-signing-key-uuid"  # Registered via /signatures endpoint
    
    return sig_payload_b64, signature_id

def submit_signed_job(token: str, script_content: str) -> dict:
    """Submit signed job to API."""
    
    sig_payload, sig_id = sign_script(script_content)
    
    payload = {
        "task_type": "script",
        "runtime": "python",
        "payload": {
            "script_content": script_content,
            "signature_payload": sig_payload,
            "signature_id": sig_id,
        },
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    sess = requests.Session()
    sess.verify = ROOT_CA if os.path.exists(ROOT_CA) else False
    
    resp = sess.post(f"{BASE_URL}/jobs", json=payload, headers=headers)
    assert resp.status_code == 200, f"Job submission failed: {resp.status_code} {resp.text}"
    
    return resp.json()

if __name__ == "__main__":
    token = os.getenv("AUTH_TOKEN")
    
    script = """
import json
import time

result = {
    "message": "E2E test success",
    "timestamp": time.time(),
}
print(json.dumps(result))
"""
    
    job = submit_signed_job(token, script)
    print(f"Submitted job: {job['guid']}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tests used HTTP client for all operations | Tests use service-layer calls directly for unit testing, HTTP for E2E | Phase 129+ (response model work) | Faster, simpler unit tests; E2E tests remain HTTP-based |
| Response models partially implemented, many routes missing decorators | 100% response_model coverage (73 response_model + 16 response_class across 89 routes) | Phase 129 complete | Tests must now validate against Pydantic models or risk regressions |
| Job status transitions hardcoded in tests | Tested via service functions (pull_work, report_result, retry logic) | Phase 120+ (limits) | More maintainable; reflects actual code paths |
| Signature validation assumed to work | Must be tested: registration, verification, HMAC stamping on creation | Phase 129+ (response models include sig fields) | Tests must cover the full signing pipeline |
| Nodes not simulated; only mocked | Nodes simulated via service-layer calls in pytest; real nodes in live script | This phase (130) | Better coverage without mocking; but live script needed for container execution validation |

**Deprecated/outdated:**
- **Direct HTTP testing for unit tests:** Service-layer calls are faster and more focused. HTTP testing is for E2E validation only.
- **Mocking `pull_work()` or `report_result()`:** Use real service functions; they're stable and well-tested. Mocking introduces divergence.
- **Hardcoded job status assertions without understanding transitions:** Always check diagnosis for unassigned jobs; don't assume all jobs move through all states.

---

## Validation Architecture

> Note: This section applies if `workflow.nyquist_validation` is not explicitly set to false in `.planning/config.json`. The key is absent in current config, so validation testing is enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x + pytest-asyncio 0.21+ |
| Config file | `puppeteer/pytest.ini` (or pyproject.toml) — inherits conftest.py patterns |
| Quick run command | `cd puppeteer && pytest tests/test_dispatch_e2e.py -x -v` (single test file, ~30 sec) |
| Full suite command | `cd puppeteer && pytest tests/ -x` (all tests, ~5-10 min with DB setup) |

### Phase Requirements → Test Map

No explicit phase requirement IDs were provided for Phase 130, so mapping is implicit to user constraints:

| Constraint | Behavior | Test Type | Automated Command | File Exists? |
|-----------|----------|-----------|-------------------|-------------|
| Happy path dispatch | Job created → pulled → completed → result retrievable | Integration | `pytest tests/test_dispatch_e2e.py::test_happy_path_dispatch -v` | ❌ Wave 0 |
| Bad signature rejection | Job with invalid signature rejected at submission (HTTP 422 or creation failure) | Unit | `pytest tests/test_dispatch_e2e.py::test_bad_signature_rejection -v` | ❌ Wave 0 |
| Capability mismatch diagnosis | Job targeting unmet capability stays PENDING, diagnosis explains | Integration | `pytest tests/test_dispatch_e2e.py::test_capability_mismatch_diagnosis -v` | ❌ Wave 0 |
| Retry on failure | Job fails, retries up to max_retries, state transitions correctly | Integration | `pytest tests/test_dispatch_e2e.py::test_retry_on_failure -v` | ❌ Wave 0 |
| Live E2E happy path | Sign + submit + execute + capture output on real node | E2E | `python mop_validation/scripts/e2e_dispatch_integration.py` | ❌ Wave 0 |
| Response model regression (Phase 129) | All returned JSON parses through Pydantic models without ValidationError | Unit | `pytest tests/test_dispatch_e2e.py -v -k response` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit (pytest file):** `cd puppeteer && pytest tests/test_dispatch_e2e.py -x` — all tests in file (~1-2 min)
- **Per task commit (live script):** `python mop_validation/scripts/e2e_dispatch_integration.py` — full orchestration (~2-3 min including compose up/down)
- **Per wave merge:** Full test suite `cd puppeteer && pytest tests/ -x` (ensures no regressions in Phase 129 response models or other modules)
- **Phase gate:** Both pytest suite all-pass AND live E2E script exit code 0 before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_dispatch_e2e.py` — Full pytest test file with 6 test cases (happy path, bad sig, capability mismatch, retry, response models, concurrent)
- [ ] `mop_validation/scripts/e2e_dispatch_integration.py` — Self-contained live E2E script with pre-flight checks, node lifecycle, 3 scenarios (happy path, signed vs unsigned, concurrent)
- [ ] `mop_validation/scripts/e2e_dispatch_integration.py` also creates JSON report: `mop_validation/reports/e2e_dispatch_integration_report.json`
- [ ] Framework setup: pytest already installed (conftest.py exists); no additional deps needed beyond `requests` for live script

**No additional fixtures needed:** Both new tests reuse existing `setup_db`, `async_client`, `auth_headers` from `conftest.py`. pytest-asyncio already enabled via `@pytest.fixture(scope="session")` and `event_loop` fixture.

---

## Open Questions

1. **Signature validation hook location:** Phase 129 changes may have moved signature validation. Is it checked in `create_job()` or deferred to pull_work? Research found HMAC stamping at line 572 `job_service.py`, but full validation flow needs confirmation during implementation.

2. **Node enrollment in live script:** Should the script use a pre-generated JOIN_TOKEN, or should it call an API endpoint to generate one? Research found `POST /admin/generate-token` exists, but whether it's suitable for scripted use needs confirmation.

3. **Memory limit default:** Existing code defaults to "512m" if not specified. Should tests use explicit limits or rely on default? Research shows config-based defaults exist (`default_job_memory_limit` key), but testing with explicit limits is safer.

4. **Output log structure:** Phase 129 response models show `output_log` as `Optional[List[Dict[str, str]]]` with fields `{t, stream, line}`. Live script must populate this correctly; research confirms this pattern in `test_job_limits.py` examples, but exact field format needs verification against actual node output capture.

---

## Sources

### Primary (HIGH confidence)

- **conftest.py** (`puppeteer/tests/conftest.py` lines 1-148) — AsyncClient fixture, setup_db pattern, auth_headers helper; verified against codebase
- **JobService** (`puppeteer/agent_service/services/job_service.py` lines 436, 703, 1113+) — create_job, pull_work, get_dispatch_diagnosis service functions; verified against codebase
- **SignatureService** (`puppeteer/agent_service/services/signature_service.py` lines 18-83) — signature verification and public key storage; verified against codebase
- **Models** (`puppeteer/agent_service/models.py` lines 43, 117, 174, 189, 200, 271) — JobCreate, JobResponse, WorkResponse, DispatchDiagnosisResponse, ResultReport, PollResponse; verified against codebase
- **DB Schema** (`puppeteer/agent_service/db.py` lines 32-100) — Job, Node, ScheduledJob, Signature tables; verified against codebase
- **Phase 129 Summary** (STATE.md lines 95-133) — Response model changes and 100% coverage achievement; verified against project state
- **CONTEXT.md** (Phase 130 decisions, lines 13-60) — Locked test structure, node simulation approach, assertion depth requirements; project decision

### Secondary (MEDIUM confidence)

- **test_dispatch_diagnosis.py** (`puppeteer/tests/test_dispatch_diagnosis.py` lines 1-100) — Example pattern for diagnosis testing; verified as existing test in repo
- **test_job_limits.py** (`puppeteer/tests/test_job_limits.py` lines 1-150) — Example pattern for memory limit assertions and service-layer testing; verified as existing test
- **local_nodes compose configs** (`mop_validation/local_nodes/docker-node-compose.yaml`, `node_alpha/node-compose.yaml`) — Node environment setup and network configuration; verified in repo
- **run_signed_job.py** (`mop_validation/scripts/run_signed_job.py` lines 1-80) — Example of signing + API submission pattern; verified as existing script

### Tertiary (LOW confidence)

- **Report format conventions:** Inference from existing mop_validation scripts (e.g., isolation_verification.json pattern); not explicitly documented but observed in codebase
- **Polling intervals/timeouts:** Suggested values from Phase 128 concurrent testing (5 sec node poll intervals); actual optimal values may differ and should be validated during implementation

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — All libraries (pytest, SQLAlchemy, httpx, Pydantic) existing and in use; Phase 129 fully specified response models
- **Service layer functions:** HIGH — Code reviewed; all functions exist and are well-documented with type hints
- **Architecture patterns:** HIGH — conftest.py pattern established; existing tests follow same approach (test_dispatch_diagnosis.py, test_job_limits.py)
- **Live script approach:** MEDIUM — Compose configs exist and are tested; networking (puppeteer_default) confirmed; exact polling values and error handling need validation
- **Signature validation details:** MEDIUM — Verification function exists and is tested; full integration into create_job workflow needs confirmation

**Research date:** 2026-04-11
**Valid until:** 2026-04-25 (14 days; framework stable, response models finalized in Phase 129, no breaking changes expected)

**Assumptions validated during research:**
- Phase 129 response models are final (100% coverage achieved, merged to main)
- Job state machine is stable (pull_work, report_result, retry logic unchanged since Phase 128)
- Local node compose configs are functional (verified in repo, used in prior phases)
- conftest.py patterns are reusable (setup_db, AsyncClient, auth_headers all used by existing tests)

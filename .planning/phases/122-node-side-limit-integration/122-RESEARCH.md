# Phase 122: Node-Side Limit Integration - Research

**Researched:** 2026-04-06
**Domain:** Node-side container resource limit validation, error handling, and logging
**Confidence:** HIGH

## Summary

Phase 122 hardens the existing limit passthrough infrastructure at the node level. Memory and CPU limits are already extracted from work queue responses and passed to the container runtime. The focus is on three complementary areas: fixing the `except Exception: pass` error-handling gap (line 552 of node.py), upgrading all limit-related logging from `print()` to structured Python logger calls, and adding explicit CPU format validation to match the rigor of memory validation.

The phase builds on Phase 120-121 (database and API schema established) and Phase 121 (scheduler job service admission control). Most extraction and passthrough code already exists and works correctly; this phase focuses on production-hardening: structured error diagnostics, audit-trail logging, and test coverage of the validation path.

**Primary recommendation:** Fix the bare `except Exception: pass` at node.py:552 by catching format validation errors, logging them at WARNING level, and reporting a structured error dict to the orchestrator. Upgrade all limit-related `print()` to `logger.info/warning/error`. Add CPU format validation using the same pattern as memory validation (parse attempt → catch + report on failure). Add unit tests for parse_bytes validation and integration tests for end-to-end limit flow.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Invalid memory_limit or cpu_limit format **fails the job** — report failure back to orchestrator with structured diagnostic
- Structured error payload: `{'error': 'Invalid memory_limit format', 'value': '10x', 'expected': 'e.g. 512m, 1g, 2Gi'}`
- Same fail-on-parse-error behavior for both memory_limit and cpu_limit
- Format validation runs **before** the secondary admission check — bad format = immediate fail, no capacity comparison attempted
- Add explicit format validation for cpu_limit (must be valid float/int string, e.g. '2', '0.5')
- Invalid cpu_limit (e.g. 'fast', 'abc') fails the job with structured diagnostic, consistent with memory validation
- Replace print() statements with Python logger for all limit-related events in execute_task()
- `logger.info` — successful limit extraction at job start: "Job {guid}: memory_limit={mem}, cpu_limit={cpu}"
- `logger.warning` — parse errors before failing the job
- `logger.error` — admission rejection (job exceeds node capacity)
- Fix the `except Exception: pass` gap (line 552) — the primary deliverable
- Add structured logging for limit flow — secondary deliverable
- Add CPU format validation — tertiary deliverable
- Do NOT refactor existing limit extraction logic that already works
- Do NOT add CPU admission check (requires node CPU capacity reporting, deferred)

### Claude's Discretion
- Exact validation regex/parsing for cpu_limit format
- Logger message formatting and field names
- Test fixture design and mock patterns
- Whether to extract validation into a helper function or keep inline

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ | Language | Target runtime for node agent |
| logging | stdlib | Structured logging | Built-in Python module, production-standard for audit trails |
| pytest | 7.0+ | Test framework | Project standard (pyproject.toml: asyncio_mode=auto) |
| unittest.mock | stdlib | Test mocking | Built-in, supports AsyncMock for async node code |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.24+ | Async HTTP client | Node uses AsyncClient for orchestrator communication |
| psutil | 5.8+ | Process/system info | Already used in node.py for resource monitoring |
| cryptography | 40+ | Ed25519 signing | Already used for job signature verification |
| pydantic | 2.0+ | Data validation | Already used for WorkResponse models from orchestrator |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python logging | print() | Logging captures level, timestamp, structured fields; print() loses this context. Project uses logger in runtime.py already. |
| pytest | unittest | pytest fixtures and parametrization better suited to async mocking patterns (AsyncMock). Project standard in pyproject.toml. |
| Custom validation | pydantic validator | Pydantic validation happens at orchestrator (Phase 121); node-side validation happens during parsing before passthrough. Inline try/except clearer here. |

## Architecture Patterns

### Recommended Project Structure
Validation logic lives in two places:
1. **node.py**: Format parsing and secondary admission check in execute_task()
2. **runtime.py**: Limit passthrough to container runtime CLI flags (already working)
3. **tests/**: Unit tests in test_node.py, integration tests in mop_validation/scripts/

### Pattern 1: Parse-and-Fail-Early with Structured Error
**What:** When format validation fails, immediately construct a structured error dict (not a bare exception string) and report it to the orchestrator.
**When to use:** All format parsing before business logic runs (before admission check, before runtime execution)
**Example:**
```python
# Source: CONTEXT.md, Phase 122 decision
try:
    mem_bytes = parse_bytes(memory_limit)
except (ValueError, KeyError) as e:
    logger.warning(f"Job {guid}: Invalid memory_limit format '{memory_limit}': {e}")
    error_payload = {
        'error': 'Invalid memory_limit format',
        'value': memory_limit,
        'expected': 'e.g. 512m, 1g, 2Gi'
    }
    await self.report_result(guid, False, error_payload)
    return
```

### Pattern 2: Structured Logging in execute_task()
**What:** Replace all print() limit-related calls with logger.info/warning/error.
**When to use:** Entry points (job start), validation failures (parse errors, admission rejection), normal operation
**Example:**
```python
# Successful extraction: log at INFO level
logger.info(f"Job {guid}: memory_limit={memory_limit}, cpu_limit={cpu_limit}")

# Parse error: log at WARNING level (job will fail)
logger.warning(f"Job {guid}: Invalid memory_limit format '{value}'")

# Admission rejection: log at ERROR level (exceeds node capacity)
logger.error(f"Job {guid} exceeds node capacity: requests {memory_limit}, limit is {self.job_memory_limit}")
```

### Anti-Patterns to Avoid
- **Swallowing exceptions silently:** `except Exception: pass` loses error context. Always log + report structured error.
- **Mixing print() and logger:** Inconsistent audit trail. logger wins (already defined at module level in runtime.py).
- **Validation after passthrough:** Format validation must run before admission check and before runtime.run() call.
- **Separate validation functions for memory/cpu:** Keep inline to avoid code duplication and maintain clear error reporting in context.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async test mocking | Custom async mock classes | unittest.mock.AsyncMock | Already in stdlib, works with pytest fixtures, tested by Python core |
| Format validation regex | Hand-crafted regex for memory units | parse_bytes() with try/except | Single source of truth; any format bugs fixed once; shared with admission check logic |
| Structured error payloads | String concatenation | Dict with 'error', 'value', 'expected' keys | Orchestrator deserializes JSON; structured payload allows programmatic error handling; consistent with CONTEXT.md decision |
| Test fixtures for node.py | Recreate Node object per test | Shared pytest fixture with mocks for bootstrap/enrollment | Reduce boilerplate; parallel test execution works correctly with proper fixture scope |

**Key insight:** Error handling at the node boundary (between orchestrator and container runtime) is a security-critical layer. Bare exception handlers mask failures that should be audited. Structured logging ensures the orchestrator can correlate job failure reasons with node-side diagnostics.

## Common Pitfalls

### Pitfall 1: Format Validation Order
**What goes wrong:** Code tries to check admission capacity before validating format. If memory_limit is "10x", `parse_bytes("10x")` throws, the exception is swallowed, admission check never runs, job executes anyway (incorrectly).
**Why it happens:** Existing code has `except Exception: pass` after parse attempt. Easy to miss that format validation must run first.
**How to avoid:** Refactor so parse_bytes is called before admission check. On parse failure, report error and return early.
**Warning signs:** Job executes with malformed limits that should have been rejected; no log entry explaining why limits were ignored.

### Pitfall 2: Inconsistent Logging Format
**What goes wrong:** Some limit-related messages use print(), others use logger. Audit trail is fragmented; node failures harder to diagnose.
**Why it happens:** Codebase uses both print() and logger in different functions. Easy to add new print() statements.
**How to avoid:** Search for all limit-related print() calls in execute_task(). Replace with logger calls using consistent format: `logger.info(f"Job {guid}: ...")`.
**Warning signs:** Operator sees job failed but logs don't explain why; grep for error keywords finds inconsistent location/format.

### Pitfall 3: CPU Validation Omitted
**What goes wrong:** Memory limits are validated, but cpu_limit strings like "invalid" or "NaN" are passed directly to runtime.run(), which then fails with a cryptic container error.
**Why it happens:** CPU format validation wasn't in the original code; easy to forget it in this phase.
**How to avoid:** After memory validation fix, add explicit cpu_limit validation with the same pattern: try parse, catch on error, log + report.
**Warning signs:** Unit test passes (parse_bytes not called for cpu), but integration test fails when orchestrator sends malformed cpu_limit.

### Pitfall 4: Missing Test Coverage
**What goes wrong:** Code validates format at node, but tests only mock the happy path. Integration test that sends malformed limits from orchestrator never runs.
**Why it happens:** Unit tests are easier to write (just mock); full end-to-end requires Docker stack.
**How to avoid:** Write unit tests for parse_bytes() with invalid inputs. Add integration test in mop_validation/ that submits job with bad limits via API.
**Warning signs:** Phase review passes locally, but production job with malformed limits still executes.

## Code Examples

Verified patterns from official sources and project context:

### Parse-and-Fail Pattern for Memory Validation (Already Exists)
```python
# Source: node.py:546-553 (existing code, needs error handling improvement)
if memory_limit and self.job_memory_limit:
    try:
        if parse_bytes(memory_limit) > parse_bytes(self.job_memory_limit):
            logger.error(f"Job {guid} exceeds node capacity: requests {memory_limit}, limit is {self.job_memory_limit}")
            await self.report_result(guid, False, {"error": "Job memory limit exceeds node capacity"})
            return
    except (ValueError, KeyError) as e:
        logger.warning(f"Job {guid}: Invalid memory_limit format '{memory_limit}': {e}")
        await self.report_result(guid, False, {
            "error": "Invalid memory_limit format",
            "value": memory_limit,
            "expected": "e.g. 512m, 1g, 2Gi"
        })
        return
```

### parse_bytes() Helper Function (Already Exists)
```python
# Source: node.py:25-34
def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes."""
    s = s.strip().lower()
    if s.endswith('g'):
        return int(s[:-1]) * 1024 ** 3
    elif s.endswith('m'):
        return int(s[:-1]) * 1024 ** 2
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)
```

### Recommended CPU Format Validation
```python
# New: validate cpu_limit format (float or int string)
def parse_cpu(s: str) -> float:
    """Convert CPU limit string like '2', '0.5', '1.0' to float."""
    try:
        return float(s.strip())
    except (ValueError, AttributeError, TypeError) as e:
        raise ValueError(f"Invalid CPU format: {s}") from e
```

### Limit Extraction and Validation Flow in execute_task()
```python
# Source: node.py:537-538, with improvements
memory_limit = job.get("memory_limit")
cpu_limit = job.get("cpu_limit")

# Log successful extraction at job start
logger.info(f"Job {guid}: memory_limit={memory_limit}, cpu_limit={cpu_limit}")

# Format validation BEFORE admission check
if memory_limit:
    try:
        parse_bytes(memory_limit)
    except (ValueError, KeyError) as e:
        logger.warning(f"Job {guid}: Invalid memory_limit format '{memory_limit}': {e}")
        await self.report_result(guid, False, {
            "error": "Invalid memory_limit format",
            "value": memory_limit,
            "expected": "e.g. 512m, 1g, 2Gi"
        })
        return

if cpu_limit:
    try:
        parse_cpu(cpu_limit)
    except ValueError as e:
        logger.warning(f"Job {guid}: Invalid cpu_limit format '{cpu_limit}': {e}")
        await self.report_result(guid, False, {
            "error": "Invalid cpu_limit format",
            "value": cpu_limit,
            "expected": "e.g. 2, 0.5, 1.0"
        })
        return

# Secondary admission check (after format validation)
if memory_limit and self.job_memory_limit:
    try:
        if parse_bytes(memory_limit) > parse_bytes(self.job_memory_limit):
            logger.error(f"Job {guid} exceeds node capacity: requests {memory_limit}, limit is {self.job_memory_limit}")
            await self.report_result(guid, False, {"error": "Job memory limit exceeds node capacity"})
            return
    except (ValueError, KeyError) as e:
        # This should not happen (format already validated), but defensive
        logger.error(f"Job {guid}: Unexpected parse error in admission check: {e}")
        await self.report_result(guid, False, {"error": "Internal validation error"})
        return
```

### Unit Test for parse_bytes() with Invalid Input
```python
# Source: test_node.py (new test)
import pytest
from puppets.environment_service.node import parse_bytes

def test_parse_bytes_valid():
    """parse_bytes converts memory strings correctly."""
    assert parse_bytes("512m") == 512 * 1024 ** 2
    assert parse_bytes("1g") == 1024 ** 3
    assert parse_bytes("256k") == 256 * 1024
    assert parse_bytes("1024") == 1024  # plain int
    assert parse_bytes("2G") == 2 * 1024 ** 3  # uppercase

def test_parse_bytes_invalid():
    """parse_bytes raises on invalid format."""
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("10x")
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("hello")
    with pytest.raises((ValueError, KeyError)):
        parse_bytes("")
```

### Unit Test for CPU Format Validation
```python
# Source: test_node.py (new test)
def test_parse_cpu_valid():
    """parse_cpu converts CPU strings correctly."""
    assert parse_cpu("2") == 2.0
    assert parse_cpu("0.5") == 0.5
    assert parse_cpu("1.0") == 1.0
    assert parse_cpu("  0.25  ") == 0.25

def test_parse_cpu_invalid():
    """parse_cpu raises on invalid format."""
    with pytest.raises(ValueError):
        parse_cpu("fast")
    with pytest.raises(ValueError):
        parse_cpu("abc")
    with pytest.raises(ValueError):
        parse_cpu("")
    with pytest.raises(ValueError):
        parse_cpu("1.2.3")
```

### Mock Test for execute_task() Limit Validation
```python
# Source: test_node.py (new test with mocks)
@pytest.mark.anyio
async def test_execute_task_invalid_memory_format(mock_node_env):
    """execute_task fails job if memory_limit format is invalid."""
    job = {
        "guid": "job-123",
        "task_type": "script",
        "memory_limit": "10x",  # invalid
        "cpu_limit": None,
        "payload": {
            "runtime": "python",
            "script_content": "print('hello')",
            "signature_payload": "base64sig"
        }
    }

    with patch("puppets.environment_service.node.PuppetNode.report_result") as mock_report:
        await mock_node_env.execute_task(job)
        mock_report.assert_called_once()
        args, kwargs = mock_report.call_args
        # args[0] = guid, args[1] = success (False), args[2] = error_dict
        assert args[1] is False  # job failed
        assert "Invalid memory_limit format" in args[2]["error"]
        assert args[2]["value"] == "10x"
```

### Integration Test for End-to-End Limit Flow
```python
# Source: mop_validation/scripts/test_phase122_limits.py (new)
"""Integration test: submit job with limits via API, verify node validates and reports."""
import requests
import json

def test_job_with_invalid_memory_limit():
    """Submit job with invalid memory_limit, verify orchestrator receives structured error."""
    job_payload = {
        "script_content": "print('hello')",
        "runtime": "python",
        "memory_limit": "invalid",  # malformed
        "cpu_limit": "1.0"
    }

    # Submit signed job to orchestrator
    resp = requests.post(
        "https://localhost:8001/api/jobs",
        json=job_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    job_id = resp.json()["guid"]

    # Wait for node to execute and report
    time.sleep(2)

    # Poll job status
    resp = requests.get(
        f"https://localhost:8001/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    job_result = resp.json()

    assert job_result["success"] is False
    assert "Invalid memory_limit format" in job_result["error"]
    assert job_result["error"]["value"] == "invalid"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare `except Exception: pass` (line 552) | Explicit exception handling with structured error reporting | Phase 122 | Errors now logged with context; orchestrator gets diagnostic data |
| print() for logging | Python logger (logging.getLogger) | Phase 122 | Audit trail is structured, timestamped, and filtereable by level |
| Memory-only validation | Both memory and CPU format validation | Phase 122 | CPU limits are rejected early if malformed, avoiding cryptic container runtime errors |
| No admission check | Secondary admission check (memory capacity vs node limit) | Phase 121 (existing) | Jobs that exceed node capacity are rejected before execution |

**Deprecated/outdated:**
- `except Exception: pass` pattern: Hides errors that should be audited. Replace with explicit catches + logging.
- print() for diagnostic output: Not captured by log aggregation systems. Use logger.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (7.0+) with asyncio_mode=auto |
| Config file | `pyproject.toml` (existing: `testpaths=["puppeteer/agent_service/tests"], asyncio_mode="auto"`) |
| Quick run command | `cd /home/thomas/Development/master_of_puppets && pytest puppets/environment_service/tests/test_node.py -xvs` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets && pytest puppets/environment_service/tests/ -xvs` |

### Phase Requirements → Test Map
No explicit phase requirement IDs provided, but REQUIREMENTS.md maps ENFC-03 (limits set in GUI reach inner container runtime flags end-to-end) to Phase 122.

| Requirement | Behavior | Test Type | Automated Command | File Exists? |
|-------------|----------|-----------|-------------------|-------------|
| ENFC-03 (part 1) | Format validation rejects malformed memory_limit | unit | `pytest puppets/environment_service/tests/test_node.py::test_parse_bytes_invalid -xvs` | ❌ Wave 0 |
| ENFC-03 (part 2) | Format validation rejects malformed cpu_limit | unit | `pytest puppets/environment_service/tests/test_node.py::test_parse_cpu_invalid -xvs` | ❌ Wave 0 |
| ENFC-03 (part 3) | Memory limit passes through to runtime.run() `--memory` flag | integration | `pytest puppets/environment_service/tests/test_runtime.py::test_run_with_memory_limit -xvs` | ✅ Existing (can enhance) |
| ENFC-03 (part 4) | CPU limit passes through to runtime.run() `--cpus` flag | integration | `pytest puppets/environment_service/tests/test_runtime.py::test_run_with_cpu_limit -xvs` | ✅ Existing (can enhance) |
| Error handling | Invalid format reports structured error dict to orchestrator | unit + integration | `pytest puppets/environment_service/tests/test_node.py::test_execute_task_invalid_memory_format -xvs` | ❌ Wave 0 |
| Logging | Limit validation events logged to logger (not print) | unit | `pytest puppets/environment_service/tests/test_node.py::test_execute_task_logs_limits -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest puppets/environment_service/tests/test_node.py -x` (unit tests for parse/validation, ~30 sec)
- **Per wave merge:** `pytest puppets/environment_service/tests/ -x && python mop_validation/scripts/test_phase122_limits.py` (full suite + integration, ~2 min)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppets/environment_service/tests/test_node.py` — expand with test_parse_bytes_invalid(), test_parse_cpu_valid/invalid(), test_execute_task_invalid_memory_format(), test_execute_task_invalid_cpu_format()
- [ ] `puppets/environment_service/tests/test_runtime.py` — enhance existing tests to verify `--memory` and `--cpus` flags actually passed to subprocess
- [ ] `mop_validation/scripts/test_phase122_limits.py` — new integration test file submitting jobs with malformed limits via orchestrator API
- [ ] `puppets/environment_service/node.py` — add `import logging` at top, define `logger = logging.getLogger(__name__)`, implement parse_cpu() helper, refactor execute_task() limit validation section
- [ ] `puppets/environment_service/node.py` — replace all limit-related print() with logger calls

## Sources

### Primary (HIGH confidence)
- **node.py (lines 25-34):** parse_bytes() implementation verified in working code
- **node.py (lines 537-538, 546-553):** Existing limit extraction and admission check; exception handling gap at line 552 confirmed
- **node.py (lines 660-694):** Limit passthrough to runtime.run() verified across all execution branches (stdin, file mount, direct mode)
- **runtime.py (lines 32-58):** ContainerRuntime.run() method signature confirms memory_limit and cpu_limit parameters and `--memory`/`--cpus` flag generation
- **runtime.py (line 8):** logger already defined; pattern established for structured logging
- **CONTEXT.md (Phase 122):** All decision points verified, including error handling and logging requirements

### Secondary (MEDIUM confidence)
- **test_node.py, test_runtime.py, test_output_log.py:** Existing test fixtures and AsyncMock patterns verified; pytest.mark.anyio decorator used
- **pyproject.toml:** pytest configuration confirmed (asyncio_mode="auto"), testpaths scoped to puppeteer/agent_service/tests (puppets/ tests can coexist)
- **MEMORY.md (Sprint 6-11):** Phase 121 job_service and scheduler_service confirmed working; limits already flow through API contract

### Tertiary (LOW confidence)
- Integration test infrastructure in mop_validation/scripts/: Full end-to-end test requires Docker stack running; pattern inferred from test_local_stack.py structure but not directly tested for Phase 122

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — logging and pytest are stdlib/standard project patterns; parse_bytes already verified in code
- Architecture: **HIGH** — limit extraction, admission check, and passthrough flow all visible in current code; error handling pattern clear from decision document
- Pitfalls: **MEDIUM-HIGH** — exception ordering and logging consistency inferred from code structure; confirmed by CONTEXT.md decisions
- Test infrastructure: **MEDIUM** — existing tests in puppets/ provide patterns; full integration test requires Docker stack (will validate during execution)

**Research date:** 2026-04-06
**Valid until:** 2026-04-20 (limit-related code is stable; unlikely to change in 2 weeks)
**Updated:** Phase 121 (scheduler) complete; Phase 122 ready for planning

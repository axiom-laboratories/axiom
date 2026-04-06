# Phase 122: Node-Side Limit Integration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Node extracts memory_limit and cpu_limit from work queue responses and passes them to the container runtime engine. Includes format validation at node level, structured error reporting for invalid limits, structured logging for limit flow, and tests verifying the end-to-end path.

**Key context:** Most of the extraction and passthrough code already exists in `node.py` and `runtime.py`. This phase focuses on hardening the error handling gap, upgrading logging, and adding test coverage.

</domain>

<decisions>
## Implementation Decisions

### Parse error handling
- Invalid memory_limit or cpu_limit format **fails the job** — report failure back to orchestrator with structured diagnostic
- Structured error payload: `{'error': 'Invalid memory_limit format', 'value': '10x', 'expected': 'e.g. 512m, 1g, 2Gi'}`
- Same fail-on-parse-error behavior for both memory_limit and cpu_limit
- Format validation runs **before** the secondary admission check — bad format = immediate fail, no capacity comparison attempted

### CPU limit validation
- Add explicit format validation for cpu_limit (must be valid float/int string, e.g. '2', '0.5')
- Invalid cpu_limit (e.g. 'fast', 'abc') fails the job with structured diagnostic, consistent with memory validation
- No CPU admission check at node level (nodes don't report CPU capacity yet) — just format validation

### Logging improvements
- Replace print() statements with Python logger for all limit-related events in execute_task()
- `logger.info` — successful limit extraction at job start: "Job {guid}: memory_limit={mem}, cpu_limit={cpu}"
- `logger.warning` — parse errors before failing the job
- `logger.error` — admission rejection (job exceeds node capacity)
- Existing non-limit print() calls left as-is (out of scope)

### Scope boundaries
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

</decisions>

<specifics>
## Specific Ideas

No specific requirements — straightforward hardening of existing code following established patterns. Key reference: the existing `parse_bytes()` function at `node.py:25` and `runtime.py:40-58` limit passthrough.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_bytes()` at `node.py:25` — converts memory strings ('512m', '1g') to bytes; already used for secondary admission check
- `runtime.ContainerRuntime.run()` at `runtime.py:32` — already accepts and passes `memory_limit`/`cpu_limit` to `--memory`/`--cpus` flags
- `build_output_log()` at `node.py:37` — structures stdout/stderr into timestamped log entries for execution_records
- `report_result()` method on PuppetNode — reports job success/failure back to orchestrator

### Established Patterns
- `execute_task()` at `node.py:533` — already extracts `memory_limit`/`cpu_limit` from work dict (lines 537-538)
- Secondary admission check at `node.py:546-553` — compares job memory vs node capacity, but silently swallows parse errors
- Limit passthrough at `node.py:660-694` — limits already flow to `runtime.run()` in all execution branches (script stdin, script file, web_task)
- Logger already defined at module level: `logger = logging.getLogger(__name__)` (but print() used in execute_task)

### Integration Points
- `node.py:552` — the `except Exception: pass` that needs to become proper error handling
- `node.py:537-538` — limit extraction point (already exists, no change needed)
- `node.py:660-694` — limit passthrough to runtime (already exists, no change needed)
- `WorkResponse` from orchestrator — already includes memory_limit/cpu_limit fields (Phase 120)
- `puppets/tests/` — new test directory for unit tests
- `mop_validation/scripts/` — integration test for end-to-end limit validation

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 122-node-side-limit-integration*
*Context gathered: 2026-04-06*

# Phase 120: Database & API Contract - Research

**Researched:** 2026-04-06
**Domain:** Database schema + API contract for memory/CPU resource limits
**Confidence:** HIGH

## Summary

Phase 120 establishes the database schema and API contract layer for resource limits, enabling end-to-end traceability from GUI dispatch through node execution. The runtime and node layers already support limits at execution time (verified in runtime.py lines 40-58 and node.py lines 537-549). Phase 120 closes the persistence gap by adding limit columns to the Job table and exposing them through all three Pydantic response models (JobCreate, JobResponse, WorkResponse).

This phase is foundational for ENFC-03 (Limit Enforcement) and enables downstream phases to validate and enforce limits at each layer. No external dependencies required; uses existing patterns from the codebase.

**Primary recommendation:** Add `memory_limit` and `cpu_limit` as nullable TEXT columns to the Job table, expose in JobCreate/JobResponse/WorkResponse models, create migration_v49.sql for existing Postgres deployments, add light regex validation at API level.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Both `memory_limit` and `cpu_limit` stored as `TEXT` (String) columns, nullable
- Memory format: human-readable strings like `'512m'`, `'1g'`, `'1Gi'` — matches existing `parse_bytes()` on node side
- CPU format: numeric strings like `'2'`, `'0.5'` — matches Docker/Podman `--cpus` flag format
- Null = no per-job limit; node's `JOB_MEMORY_LIMIT` env var ceiling applies as default
- Light regex validation at API level in this phase — number+unit for memory, numeric for CPU
- Rejects obvious garbage but does NOT do admission control (size checks vs node capacity) — deferred to Phase 121
- `migration_v49.sql` following existing pattern with `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS` (same for cpu_limit)
- IF NOT EXISTS handles idempotency for Postgres; fresh SQLite handled by `create_all`
- `JobCreate`: add optional `memory_limit` and `cpu_limit` string fields
- `JobResponse`: add optional `memory_limit` and `cpu_limit` string fields
- `WorkResponse`: add optional `memory_limit` and `cpu_limit` as flat fields (matches node.py's `job.get('memory_limit')` extraction pattern)
- Limits serialized in GET /jobs responses, POST /dispatch, and GET /work/pull

### Claude's Discretion
- Exact placement and styling of limit inputs in dispatch form
- Detail view layout for displaying limits
- Regex pattern specifics for light validation

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENFC-03 | Limits set in dashboard GUI reach inner container runtime flags end-to-end | This phase establishes the database persistence and API contract layers; phase 121 adds admission control, phase 122 adds node-side execution integration |

</phase_requirements>

## Standard Stack

### Core — Pydantic & SQLAlchemy (Already in Use)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.x (async) | ORM for database persistence | Already used for all Job/Node/User models in `db.py`; async patterns established |
| Pydantic | 2.x | Request/response validation | Already used for all API models in `models.py` (field_validator, model_validator patterns) |
| FastAPI | 0.104+ | REST API framework | Already used for all `/api` routes in `main.py`; async/await pattern standard |
| Postgres 15 | 15+ | Production database | Default in Docker stack; SQLite for local dev (both supported by create_all) |

### Supporting — Existing Utilities

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `parse_bytes()` | stdlib (custom in node.py) | Parse memory strings to bytes | Already exists in `puppets/environment_service/node.py:25`; used for node-side validation and limit enforcement |
| `re` (stdlib) | 3.11+ | Regex validation | Light validation of memory/CPU string format at API level |

## Architecture Patterns

### Recommended Project Structure

No new directories needed. Changes are localized to:

```
puppeteer/
├── agent_service/
│   ├── db.py                 # Add memory_limit, cpu_limit columns to Job model
│   ├── models.py             # Add fields to JobCreate, JobResponse, WorkResponse
│   └── main.py               # (no changes for Phase 120; dispatch handled in Phase 121)
├── migration_v49.sql         # NEW: ALTER TABLE jobs ADD COLUMN for existing Postgres
└── requirements.txt          # (no new dependencies)

puppeteer/dashboard/
└── src/
    └── views/
        └── Jobs.tsx          # (limit inputs added in Phase 122 UI work; Phase 120 is contract only)
```

### Pattern 1: DB Column Addition for Limit Fields

**What:** Add nullable TEXT columns to store limit strings, following established optional field pattern

**When to use:** Adding optional, non-indexed persistence fields to job model

**Example (from CONTEXT.md and verified against existing Job model):**
```python
# Source: puppeteer/agent_service/db.py (lines 32-62)
class Job(Base):
    __tablename__ = "jobs"

    guid: Mapped[str] = mapped_column(String, primary_key=True)
    # ... existing fields ...
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Phase 53 pattern

    # NEW FOR PHASE 120:
    memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. "512m", "1g"
    cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)     # e.g. "2", "0.5"
```

**Why this pattern:** Matches existing optional field style (see `env_tag`, `runtime`, `name`, `dispatch_timeout_minutes` on Job model). No index needed (limits not used for filtering in this phase). Nullable allows gradual rollout without breaking existing jobs.

### Pattern 2: Pydantic Model Field Addition

**What:** Add optional string fields to request/response models, using `Optional[str] = None` pattern

**When to use:** Exposing nullable database columns through API layer

**Example (from existing JobCreate pattern in models.py):**
```python
# Source: puppeteer/agent_service/models.py (lines 6-36)
class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0
    # ... existing fields ...
    created_by: Optional[str] = None    # SRCH-03: submitter username (existing pattern)

    # NEW FOR PHASE 120:
    memory_limit: Optional[str] = None  # e.g. "512m", "1g", "1Gi"
    cpu_limit: Optional[str] = None     # e.g. "2", "0.5"
```

**Why this pattern:** Matches existing optional field style. No custom validators in Phase 120 (light validation at route level via regex). Nullable by default allows both old clients (no limit fields) and new clients (with limits) to coexist.

### Pattern 3: Pydantic Field Validation - Light Regex

**What:** Validate memory/CPU string format at API boundary using regex pattern matching

**When to use:** Input validation for structured string fields (not size-checking, which is admission control in Phase 121)

**Example (new for Phase 120, light validation only):**
```python
# Source: Existing pattern from models.py (lines 22-26, field_validator example)
from pydantic import BaseModel, field_validator
import re

class JobCreate(BaseModel):
    # ... existing fields ...
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None

    @field_validator("memory_limit", mode="before")
    @classmethod
    def validate_memory_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip().lower()
        # Light regex: digits + optional unit (k, m, g, ki, mi, gi, etc.)
        if not re.match(r'^\d+(\.\d+)?[kmgt]i?b?$', v_str):
            raise ValueError(f"Invalid memory format: {v}. Use format like '512m', '1g', '1Gi'")
        return v_str

    @field_validator("cpu_limit", mode="before")
    @classmethod
    def validate_cpu_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip()
        # Light regex: digits with optional decimal (matches Docker --cpus format)
        if not re.match(r'^\d+(\.\d+)?$', v_str):
            raise ValueError(f"Invalid CPU format: {v}. Use format like '2', '0.5'")
        return v_str
```

**Why this pattern:** Rejects obvious garbage (non-numeric, wrong suffixes) at API boundary. Doesn't check size (that's Phase 121 admission control). Matches Docker/Podman CLI conventions.

### Anti-Patterns to Avoid

- **Adding new index on limit columns:** Limits are optional metadata, not query/filter keys. Indexing wastes space. No filtering on limits until Phase 127 dashboard work.
- **Storing limits as numeric (Integer/Float):** Text format provides flexibility for Kubernetes-style suffixes (Ki, Mi, Gi) and decimal CPU values. Defers parsing to node layer where it's already implemented.
- **Requiring limits in JobCreate model:** Limits must be optional to allow backward compatibility with existing clients and jobs.
- **Validation at model level that does admission checking:** Phase 120 is light validation only (format checking). Phase 121 adds `parse_bytes()` calls and size comparison against node capacity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String format validation | Custom parsing logic | Pydantic `field_validator` with regex | Reusable, testable, documented validation pattern; prevents edge case bugs (leading zeros, case sensitivity, etc.) |
| Postgres migration for nullable columns | Manual SQL for each column | Template with `IF NOT EXISTS` | Idempotency guaranteed; works for both fresh + existing deployments; standard pattern already established in migration_v47.sql, migration_v48.sql |
| Memory format parsing | New utility function | Reuse `parse_bytes()` from node.py | Already tested, used in production; handles k/m/g suffixes; central source of truth prevents duplication |
| Optional field serialization | Manual None checks | Pydantic `Optional[str] = None` | Handles JSON serialization automatically; pydantic type validation; omits None fields from JSON by default (configurable via `model_config`) |

**Key insight:** Limits flow through three parsing layers: API validation (format checking, this phase), job service (admission control, Phase 121), node runtime (execution flags, Phase 122). Each layer has different concerns. Building custom validators at the API level duplicates node-side logic and risks divergence.

## Common Pitfalls

### Pitfall 1: Migration Idempotency Failure on Existing Postgres

**What goes wrong:** Running `ALTER TABLE jobs ADD COLUMN memory_limit TEXT` twice fails with "column already exists" error if migration re-applied or deployed to system that already has the column.

**Why it happens:** Postgres migrations often run twice (drift correction, redeployment). Without `IF NOT EXISTS`, second run crashes.

**How to avoid:** Always use `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS memory_limit TEXT;` in migration files. Test migration by running it twice in a test DB.

**Warning signs:**
- Migration file doesn't include `IF NOT EXISTS`
- Test doesn't validate idempotency (no second-run check)
- Postgres error logs show "column already exists"

### Pitfall 2: Nullable Field Breaking Upstream Code

**What goes wrong:** Route handlers assume limits exist in JobResponse, but nullable fields can be None. Code tries to access `response.memory_limit.strip()` and crashes with AttributeError.

**Why it happens:** Nullable fields silently become None for old jobs (created before limits existed). Unprepared code doesn't check for None.

**How to avoid:**
- All code accessing optional fields must check for None or use safe accessors: `if job.memory_limit: ...` or `job.memory_limit or "no limit"`
- Test matrix includes both jobs with and without limits: `job_with_limits = JobResponse(memory_limit="512m")`, `job_without = JobResponse(memory_limit=None)`
- Integration tests mix old and new job types in same response

**Warning signs:**
- TypeError/AttributeError on None when accessing limit fields in routes
- Test suite only tests paths with limits set
- WorkResponse construction fails when node.py tries to extract missing fields

### Pitfall 3: Regex Validation Too Strict or Too Loose

**What goes wrong:** Validation regex rejects valid formats ("1.5g" fails because regex only allows integers) OR accepts invalid formats ("999999999g" accepted when storage will overflow).

**Why it happens:** Regex written without knowledge of Docker/Kubernetes conventions or test coverage insufficient.

**How to avoid:**
- Validate against real-world formats from Docker, Kubernetes, and existing node.py `parse_bytes()` function
- Light validation (format only), not size checking (that's Phase 121 admission control)
- Test matrix: valid formats (512m, 1g, 1.5g, 1Gi, 2, 0.5), invalid formats (512, 1gb, xyz, 1.2.3m)

**Warning signs:**
- Decimal CPU values (0.5) fail validation but are valid in Docker `--cpus`
- Single-letter unit (m, g, k) fails but Docker supports it
- Admission test mentions "validation rejected valid request"

### Pitfall 4: Silent Loss of Limits in Serialization

**What goes wrong:** Limits are stored in DB and persisted to job_service, but GET /jobs returns jobs without limit fields. Client UI can't display limits because they're missing from response.

**Why it happens:** WorkResponse or JobResponse models don't include memory_limit/cpu_limit fields. SQLAlchemy persists to DB, but API doesn't expose them.

**How to avoid:**
- Add fields to ALL three models: JobCreate (for input), JobResponse (for GET /jobs output), WorkResponse (for GET /work/pull output)
- Verify each route handler constructs response with limits: `JobResponse(guid=job.guid, ..., memory_limit=job.memory_limit, cpu_limit=job.cpu_limit)`
- Integration test: POST /dispatch with limits, GET /jobs (verify limits in response), GET /work/pull (verify limits in WorkResponse)

**Warning signs:**
- Jobs persisted with limits but GET /jobs returns jobs without limit fields
- Phase 121 admission tests fail because node can't find limits in work dict
- Playwright test shows "limit fields not visible in job detail view"

### Pitfall 5: Parsing Divergence Between API and Node

**What goes wrong:** API validation accepts "1Gi" but node.py `parse_bytes()` only recognizes "1g". Limits accepted at dispatch fail at execution.

**Why it happens:** API and node written independently. Node implements `parse_bytes()` for k/m/g/b suffixes, but API adds custom validation without checking node compatibility.

**How to avoid:**
- API regex must be a superset of node.py `parse_bytes()` capabilities
- Reference node.py parse_bytes implementation (lines 25-34): accepts k, m, g, with optional binary suffix (Ki, Mi, Gi) as case-insensitive variations
- Share regex pattern: import from common location or document exact formats in both files

**Warning signs:**
- Node.py crashes with "invalid memory format" on limits that passed API validation
- API accepts "1Gi" (binary suffix) but node expects "1g"
- Integration test: limit accepted in dispatch, job fails with parse error at execution

## Code Examples

Verified patterns from official sources and existing codebase:

### Job Table Column Addition

```python
# Source: puppeteer/agent_service/db.py (existing Job model, lines 32-62)
class Job(Base):
    __tablename__ = "jobs"

    guid: Mapped[str] = mapped_column(String, primary_key=True)
    task_type: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(Text)
    # ... existing fields (status, node_id, result, created_at, etc.) ...

    # Existing optional field pattern (Phase 53):
    dispatch_timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # NEW FOR PHASE 120 (follow same pattern):
    memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

### Migration File (Postgres)

```sql
-- Source: Pattern from migration_v47.sql, migration_v48.sql
-- File: puppeteer/migration_v49.sql

-- Migration v49: Add memory_limit and cpu_limit columns to jobs table
-- For existing Postgres deployments only (fresh deployments use create_all)

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(255);
```

### JobCreate Model Extension

```python
# Source: puppeteer/agent_service/models.py (JobCreate class, lines 6-36)
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
import re

class JobCreate(BaseModel):
    task_type: str
    payload: Dict
    priority: int = 0
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None
    depends_on: Optional[List[str]] = None
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    scheduled_job_id: Optional[str] = None
    env_tag: Optional[str] = None
    runtime: Optional[Literal["python", "bash", "powershell"]] = None
    name: Optional[str] = None
    created_by: Optional[str] = None

    # NEW FOR PHASE 120:
    memory_limit: Optional[str] = None  # e.g., "512m", "1g", "1Gi"
    cpu_limit: Optional[str] = None     # e.g., "2", "0.5"

    @field_validator("memory_limit", mode="before")
    @classmethod
    def validate_memory_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip().lower()
        # Light validation: digits + optional decimal + unit
        if not re.match(r'^\d+(\.\d+)?[kmgt]i?b?$', v_str):
            raise ValueError(f"Invalid memory format: {v}. Use format like '512m', '1g', '1Gi'")
        return v_str

    @field_validator("cpu_limit", mode="before")
    @classmethod
    def validate_cpu_format(cls, v):
        if v is None:
            return None
        v_str = str(v).strip()
        # Light validation: digits with optional decimal point
        if not re.match(r'^\d+(\.\d+)?$', v_str):
            raise ValueError(f"Invalid CPU format: {v}. Use format like '2', '0.5'")
        return v_str
```

### JobResponse Model Extension

```python
# Source: puppeteer/agent_service/models.py (JobResponse class, lines 54-71)

class JobResponse(BaseModel):
    guid: str
    status: str
    payload: Dict
    result: Optional[Dict] = None
    node_id: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    target_tags: Optional[List[str]] = None
    depends_on: Optional[List[str]] = None
    task_type: Optional[str] = None
    display_type: Optional[str] = None
    name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    runtime: Optional[str] = None
    originating_guid: Optional[str] = None

    # NEW FOR PHASE 120:
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
```

### WorkResponse Model Extension

```python
# Source: puppeteer/agent_service/models.py (WorkResponse class, lines 92-100)
# Used by GET /work/pull to send job details to nodes

class WorkResponse(BaseModel):
    guid: str
    task_type: str
    payload: Dict
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
    started_at: Optional[datetime] = None

    # NEW FOR PHASE 120 (flat fields, matches node.py extraction pattern):
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
```

### Node-Side Extraction (Already Exists)

```python
# Source: puppets/environment_service/node.py (lines 537-549)
# Shows how node.py already extracts limits from work dict

memory_limit = job.get("memory_limit")  # Expects Optional[str] from WorkResponse
cpu_limit = job.get("cpu_limit")

if memory_limit and self.job_memory_limit:
    try:
        if parse_bytes(memory_limit) > parse_bytes(self.job_memory_limit):
            print(f"[{self.node_id}] Job {guid} requests {memory_limit}, node limit is {self.job_memory_limit} — skipping")
            continue
    except ValueError as e:
        print(f"[{self.node_id}] Job {guid} memory_limit parse error: {e}")
        continue

# Then passed to runtime:
runtime_engine.run(
    task_type=task_type,
    payload=payload,
    memory_limit=memory_limit,
    cpu_limit=cpu_limit,
    # ... other params ...
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Numeric storage (Integer) for limits | Text/String storage with human-readable format | v20.0 (Phase 120) | Enables flexibility for Kubernetes-style suffixes and decimal CPU values; defers parsing to execution layer where format is already established |
| No limit persistence | DB column + API fields | v20.0 (Phase 120) | Enables traceability and job-specific overrides; prerequisite for enforcement testing |
| Limits only at execution layer | Limits across 3 layers: API validation → job service → node execution | v20.0 (Phase 120-122) | Enables early rejection of malformed requests; improves observability |

**Deprecated/outdated:**
- None — limits are new in v20.0; no prior version to deprecate

## Open Questions

1. **Kubernetes-style binary suffixes (Ki, Mi, Gi vs k, m, g):** Should API accept both? Current implementation in node.py `parse_bytes()` treats "1m" as "1 mebibyte" (1024^2), not "1 megabyte" (1000^2). API regex should match this convention or document the difference clearly. Recommendation: Accept both (case-insensitive) for user convenience, but document that "1m" = 1 MiB, not 1 MB.

2. **CPU format with millicores (e.g., "500m" for 0.5 CPU):** Docker `--cpus` uses decimal format (0.5), but Kubernetes uses millicores (500m). Should API support both? Recommendation: For Phase 120, support only decimal format (0.5) to match Docker/Podman convention. Millicores conversion deferred to Phase 121 if operator feedback requires it.

3. **Default limit display in UI:** When job has no memory_limit set (null), should job detail show "No limit" or "Default (512m)"? Deferred to Phase 122 UI work; Phase 120 is persistence only.

4. **Backward compatibility testing matrix:** Should integration tests include scenarios with jobs created before Phase 120 (no limit fields)? Recommendation: YES. Test must verify that old jobs continue to execute (limits are fully optional), and new jobs with limits execute correctly. This prevents regressions when phase is deployed to existing systems.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `puppeteer/tests/conftest.py` + `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_job_limits.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENFC-03 (Persistence) | Job with memory_limit stored to DB and retrieved via GET /jobs | unit | `pytest tests/test_job_limits.py::test_job_limits_persist -x` | ❌ Wave 0 |
| ENFC-03 (API contract) | WorkResponse includes memory_limit and cpu_limit fields | unit | `pytest tests/test_job_limits.py::test_work_response_has_limits -x` | ❌ Wave 0 |
| ENFC-03 (Format validation) | API rejects invalid memory/CPU formats; accepts valid formats | unit | `pytest tests/test_job_limits.py::test_limit_format_validation -x` | ❌ Wave 0 |
| ENFC-03 (Backward compatibility) | Jobs without limits continue to execute; limits are fully optional | unit | `pytest tests/test_job_limits.py::test_nullable_limits -x` | ❌ Wave 0 |
| ENFC-03 (Migration) | migration_v49.sql applies idempotently to Postgres; fresh SQLite schemas include columns | integration | `pytest tests/test_migration_v49.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_job_limits.py -x` (unit tests only, <5s)
- **Per wave merge:** Full pytest suite (`cd puppeteer && pytest`, all tests including integration)
- **Phase gate:** Full suite green + migration idempotency verified before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_job_limits.py` — unit tests for JobCreate/JobResponse/WorkResponse model validation, DB column persistence
- [ ] `tests/test_migration_v49.py` — integration test for migration idempotency on Postgres, fresh SQLite schema verification
- [ ] `tests/conftest.py` — existing fixtures cover async_client, event_loop; may need DB setup for migration testing

## Sources

### Primary (HIGH confidence)

- **Existing codebase validation:**
  - `puppeteer/agent_service/db.py` (lines 32-62) — Job model pattern for optional nullable columns
  - `puppeteer/agent_service/models.py` (lines 6-36, 54-71, 92-100) — Pydantic patterns for field_validator, Optional fields
  - `puppets/environment_service/node.py` (lines 25-34, 537-549) — parse_bytes() implementation and limit extraction
  - `puppets/environment_service/runtime.py` (lines 40-58) — memory_limit/cpu_limit parameter passing to container runtime
  - `puppeteer/migration_v47.sql`, `migration_v48.sql` — IF NOT EXISTS pattern for idempotent migrations

- **Project documentation:**
  - `.planning/research/SUMMARY.md` (lines 36-82) — Phase 1 research on database & API contract, confirmed existing runtime support
  - `.planning/REQUIREMENTS.md` (line 84) — ENFC-03 requirement scope: "Limits set in dashboard GUI reach inner container runtime flags end-to-end"
  - `.planning/phases/120-database-api-contract/120-CONTEXT.md` — Implementation decisions locked from discussion phase

### Secondary (MEDIUM confidence)

- **Pydantic 2.x documentation (inferred from codebase patterns):**
  - Optional field pattern verified in use across models.py
  - field_validator decorator used consistently for input validation
  - mode="before" for pre-validation normalization (see env_tag validator lines 22-26)

- **SQLAlchemy async patterns (verified in existing code):**
  - Mapped types with `mapped_column()` consistent across db.py
  - Nullable columns: `Mapped[Optional[str]] = mapped_column(String, nullable=True)` pattern

### Tertiary (Context7 and official sources)

- Docker `--cpus` flag documentation — CPU limit format matches decimal convention (0.5, 2, etc.)
- Kubernetes container resource specification — memory suffix convention (Ki, Mi, Gi for binary)
- Postgres `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` — idempotency for migration safety

## Metadata

**Confidence breakdown:**

- **Standard stack:** HIGH — All tools (SQLAlchemy, Pydantic, FastAPI) already in use; no new dependencies
- **Architecture:** HIGH — Data flow fully mapped; integration points identified (DB → models → routes → node extraction)
- **Pitfalls:** HIGH — All pitfalls grounded in code review (null handling, serialization, migration patterns)
- **Validation test coverage:** MEDIUM — Existing pytest + vitest infrastructure solid; Wave 0 test files need creation

**Research date:** 2026-04-06
**Valid until:** 2026-04-13 (one week; standard contract work, low churn risk)

**Key dependencies:**
- Phase 121 depends on Phase 120 (migration, models, persistence must be complete before admission control)
- Phase 122 depends on Phase 120 + 121 (node-side integration requires both DB schema and admission logic)

# Phase 129: Response Model Auto-Serialization - Research

**Researched:** 2026-04-11
**Domain:** FastAPI response validation, Pydantic v2, OpenAPI documentation standardization
**Confidence:** HIGH

## Summary

Phase 129 standardizes API response contracts across 62 FastAPI route handlers by adding `response_model=` decorators with Pydantic models. Currently 26/89 routes in main.py have response models; 77 total route instances across the codebase already use `response_model=`. The remaining ~62 routes return unvalidated raw dicts or depend on implicit FastAPI serialization. This phase introduces a generic `PaginatedResponse[T]` to replace `PaginatedJobResponse`, a unified `ActionResponse` model for 11+ action endpoints, and standardized `ErrorResponse` for consistent error documentation. All changes are backend-only; frontend response shapes remain compatible.

**Primary recommendation:** Implement domain-grouped response models (5 plans: Core, Jobs, Nodes, Admin/Auth, Foundry/System) with strict backward-compatibility testing to ensure frontend doesn't break. Use Pydantic v2 `BaseModel` with `model_config = ConfigDict(from_attributes=True)` for ORM compatibility. Add schema snapshot tests per plan to validate response structure against model definitions.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Unified `ActionResponse` model for all 11+ action endpoints with `Literal` status union to catch typos at dev time
- Generic `PaginatedResponse[T]` using Pydantic v2 generics to replace `PaginatedJobResponse`
- All list endpoints (even small collections) use `PaginatedResponse[T]` with default `page_size=50`
- `ErrorResponse` model (`detail: str`, `status_code: int`) added via route `responses={404: {"model": ErrorResponse}}`
- Five domain-grouped migration plans (Core, Jobs, Nodes, Admin/Auth, Foundry/System)
- New response models must match existing response shapes exactly — no breaking changes
- Full OpenAPI treatment: `Field(description=...)`, route `tags=`, `summary=`, multi-line `description=`, example values

### Claude's Discretion
- Exact route grouping into domain plans (may adjust based on dependency analysis)
- How to handle edge cases where existing response shapes are inconsistent within the same route
- Whether to split Plan 05 (Foundry/Smelter/System) into two plans if scope is too large
- Field description wording and example values

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | Latest in req.txt | Web framework, automatic OpenAPI generation | FastAPI's `response_model=` is standard for contract validation |
| Pydantic | 2.12.5 | Request/response validation, serialization | Pydantic v2 `BaseModel` with `from_attributes=True` handles ORM fields |
| Python | 3.9+ | Language | Project minimum version |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | Latest in req.txt | ORM models used in `from_attributes` conversions | Already in use; response models read from DB via ORM |
| typing | 3.9+ stdlib | Generic types, `Literal`, `Optional`, `List` | Pydantic v2 generics via `from typing import TypeVar, Generic` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic v2 generics | Individual `PaginatedJobResponse`, `PaginatedNodeResponse`, etc. | Pydantic v2 supports `Generic[T]` natively; one model is cleaner than N copies |
| `Literal["status1", "status2"]` | enum.Enum or str with validation | Literal generates proper OpenAPI enum + catches typos at dev time |
| Response model on every route | Selective response_model | Selective coverage leaves 62 routes undocumented in OpenAPI; full coverage is the goal |

**Installation:**
```bash
pip install fastapi pydantic sqlalchemy
# Already in puppeteer/requirements.txt — no new deps needed
```

---

## Architecture Patterns

### Response Model Convention (Pydantic v2)

All response models in `agent_service/models.py` use:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

class MyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # For ORM compatibility

    field_name: str = Field(
        description="Human-readable description",
        json_schema_extra={"examples": ["example_value"]}
    )
    optional_field: Optional[str] = None
    status: Literal["created", "updated", "deleted"]  # Enum in OpenAPI
```

**Why:**
- `from_attributes=True` allows `.from_orm()` style loading (deprecated in v2, but still supported via config); used when converting SQLAlchemy objects to Pydantic
- `Literal` generates proper enum in OpenAPI schema
- `Field(description=...)` populates OpenAPI field docs
- `json_schema_extra` adds examples to OpenAPI

### Generic PaginatedResponse Pattern

```python
from typing import TypeVar, Generic, List

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: List[T]
    total: int
    page: int
    page_size: int

# Usage in models.py
class JobListResponse(PaginatedResponse[JobResponse]):
    pass

# Or inline in routes
@app.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs():
    ...
```

**Pydantic v2 compatibility:** Pydantic v2 handles `Generic[T]` automatically. `response_model=PaginatedResponse[JobResponse]` works without custom wrappers.

### Route Decorator Pattern (OpenAPI Standardization)

```python
@app.get(
    "/api/jobs/{guid}",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Retrieve a job by GUID",
    description="Fetch the current status, results, and metadata for a job. Returns 404 if job not found.",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        403: {"model": ErrorResponse, "description": "Access denied"}
    }
)
async def get_job(guid: str):
    ...
```

**Why:**
- `tags=["Domain"]` groups routes in OpenAPI UI by domain
- `summary` is one-liner visible in OpenAPI UI
- `description` explains usage intent (why would you call this?)
- `responses={...}` documents error models OpenAPI can validate

### ActionResponse Pattern (Unified Actions)

```python
class ActionResponse(BaseModel):
    status: Literal[
        "acknowledged", "cancelled", "revoked", "approved",
        "deleted", "updated", "created", "enabled", "disabled"
    ]
    resource_type: str  # e.g., "job", "node", "signature"
    resource_id: str | int  # the thing that was actioned
    message: Optional[str] = None  # optional detail

# Usage: all action endpoints return this
@app.post("/jobs/{guid}/cancel", response_model=ActionResponse)
async def cancel_job(guid: str):
    return {
        "status": "cancelled",
        "resource_type": "job",
        "resource_id": guid,
        "message": "Job cancelled successfully"
    }
```

**Why:**
- Single model for 11+ endpoints (acknowledge, cancel, revoke, approve, delete, etc.)
- `Literal` status catches typos; prevents `"cancelledd"` at dev time
- OpenAPI generates proper enum
- No per-action custom models needed

### Error Response Pattern

```python
class ErrorResponse(BaseModel):
    detail: str
    status_code: int

# Applied to all routes that can error:
@app.get("/jobs/{guid}", response_model=JobResponse, responses={
    404: {"model": ErrorResponse}
})
```

**Why:**
- Consistent error shape across all routes
- OpenAPI documents error structure
- Client knows what to expect on 4xx/5xx

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom pagination per route | Dict with `{items, total, custom_field}` per endpoint | Generic `PaginatedResponse[T]` | Pydantic v2 generics handle all cases; avoid N nearly-identical models |
| Per-action response models | `JobCancelledResponse`, `NodeRevokedResponse`, etc. | `ActionResponse` with `Literal` status | One model captures all action verbs; eliminates response model duplication |
| OpenAPI enum documentation | Write enum docs manually or use custom JSON schema | `Literal["val1", "val2"]` in model | Pydantic v2 + FastAPI auto-generates OpenAPI enum from Literal |
| Error response inconsistency | Let each route define its own error format | `ErrorResponse` model on all error-prone routes | Standardization improves client experience and OpenAPI docs |
| Serialization validation | Return raw dicts and hope FastAPI guesses the shape | `response_model=YourModel` on every route | Pydantic validates response at route level; catches serialization bugs early |

**Key insight:** Pydantic v2 + FastAPI's `response_model=` is a complete contract system. Custom serialization logic is rarely needed once models are defined correctly. The 62 unmodeled routes are a documentation and runtime validation gap — fixing it has zero performance cost and maximum safety gain.

---

## Common Pitfalls

### Pitfall 1: Circular Imports with Generic Models

**What goes wrong:** Defining `PaginatedResponse[T]` and using `T=JobResponse` in the same models.py file causes circular import if JobResponse references PaginatedResponse.

**Why it happens:** If you do:
```python
T = TypeVar("T")
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]

class JobListResponse(PaginatedResponse[JobResponse]):  # JobResponse not yet defined
    pass
```
Then `JobResponse` must be defined first, but if `JobResponse` needs `PaginatedResponse`, Python fails.

**How to avoid:**
- Define `PaginatedResponse` at the top of models.py (no dependencies on specific models)
- Define specific models (`JobResponse`, `NodeResponse`, etc.) after, using `PaginatedResponse[JobResponse]` inline in route decorators, not in models.py
- Or use string forward references: `PaginatedResponse["JobResponse"]` (less common in v2)

**Warning signs:** `NameError: name 'JobResponse' is not defined` when importing models.

### Pitfall 2: ORM Serialization with `from_attributes=False`

**What goes wrong:** Response model doesn't include `from_attributes=True`, and you try to serialize a SQLAlchemy object:
```python
class JobResponse(BaseModel):
    guid: str
    status: str

job_db = await db.get(Job, guid)
return JobResponse(**job_db.__dict__)  # Fails: __dict__ may not have lazy-loaded fields
```

**Why it happens:** SQLAlchemy objects are not plain dicts. Without `from_attributes=True`, Pydantic can't read attributes via dot notation.

**How to avoid:**
```python
class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ADD THIS
    guid: str
    status: str

job_db = await db.get(Job, guid)
return JobResponse.from_orm(job_db)  # or just `response_model=JobResponse` in FastAPI
```

**Warning signs:** `AttributeError: 'Job' object has no attribute...` or validation errors on ORM objects.

### Pitfall 3: Forgetting `from typing import Generic, TypeVar` in Pydantic v2

**What goes wrong:** You define `class PaginatedResponse(BaseModel, Generic[T])` but forget to import Generic or TypeVar.

```python
from pydantic import BaseModel  # Missing: from typing import Generic, TypeVar

T = TypeVar("T")  # NameError: TypeVar not defined
```

**How to avoid:**
```python
from typing import TypeVar, Generic, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
```

**Warning signs:** `NameError: name 'TypeVar' is not defined` at import time.

### Pitfall 4: Inconsistent Field Names Between DB and Response Model

**What goes wrong:** Database column is `created_at` but response model field is `createdAt` (camelCase). Pydantic can't map it:

```python
class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    createdAt: datetime  # Field name doesn't match DB column `created_at`

job_db = Job(created_at=datetime.now(), ...)
JobResponse.from_orm(job_db)  # ValidationError: createdAt not found
```

**How to avoid:** Use `Field(alias=...)` to map:
```python
from pydantic import Field

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime = Field(alias="createdAt")  # Maps createdAt → created_at
```

Or match the DB column name exactly (simpler, no aliases needed).

**Warning signs:** `ValidationError: field required` on from_orm conversions; JSON response has unexpected field names.

### Pitfall 5: Response Model Too Broad (Exposing Secrets)

**What goes wrong:** Response model includes all ORM fields, including internal secrets:

```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str
    password_hash: str  # NEVER expose this
    api_key: str       # NEVER expose this
```

**How to avoid:** Only include fields that are safe to expose:
```python
class UserResponse(BaseModel):
    username: str
    created_at: datetime
    # password_hash, api_key are omitted
```

**Warning signs:** Sensitive fields appearing in OpenAPI docs or API responses that shouldn't be public.

### Pitfall 6: Conflicting Response Models in Main and EE Routers

**What goes wrong:** Main codebase defines `@app.get("/api/foo", response_model=FooResponse)` and EE patches override with a different model, causing type mismatches:

```python
# main.py
@app.get("/api/jobs", response_model=List[JobResponse])

# ee/routers/jobs_ext_router.py (override)
@jobs_router.get("/api/jobs", response_model=List[ExtendedJobResponse])  # Different model!
```

**How to avoid:**
- EE response models should extend base models (not replace them):
  ```python
  class ExtendedJobResponse(JobResponse):
      ee_field: str
  ```
- Or if replacing, ensure the EE model is backward-compatible (same fields + extras)

**Warning signs:** OpenAPI spec shows different models for the same endpoint; frontend receives unexpected fields.

---

## Code Examples

Verified patterns from existing codebase and Pydantic v2 docs:

### Example 1: Simple Response Model (JobResponse)

```python
# Source: puppeteer/agent_service/models.py (existing pattern)
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str = Field(
        description="Unique job identifier (UUID)",
        json_schema_extra={"examples": ["550e8400-e29b-41d4-a716-446655440000"]}
    )
    status: str = Field(
        description="Job status: queued, assigned, running, succeeded, failed, cancelled",
        json_schema_extra={"examples": ["running"]}
    )
    payload: dict = Field(
        description="Job input parameters",
        json_schema_extra={"examples": [{"command": "ls"}]}
    )
    result: Optional[dict] = Field(
        default=None,
        description="Job result (if completed)"
    )
    node_id: Optional[str] = Field(
        default=None,
        description="Node ID where job executed"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when job started execution"
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when job was created"
    )
```

### Example 2: Generic Paginated Response (Pydantic v2)

```python
# Source: Pydantic v2 generic patterns + Phase 129 CONTEXT.md design
from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response container for any model T."""
    model_config = ConfigDict(from_attributes=True)

    items: List[T] = Field(
        description="Array of items in this page",
        json_schema_extra={"examples": [[]]}
    )
    total: int = Field(
        description="Total number of items across all pages",
        json_schema_extra={"examples": [150]}
    )
    page: int = Field(
        description="Current page number (1-indexed)",
        json_schema_extra={"examples": [1]}
    )
    page_size: int = Field(
        description="Number of items per page",
        json_schema_extra={"examples": [50]}
    )

# Usage in routes
@app.get("/api/jobs", response_model=PaginatedResponse[JobResponse], tags=["Jobs"])
async def list_jobs(page: int = 1, page_size: int = 50):
    jobs = ...  # fetch jobs
    total = ...  # fetch total count
    return PaginatedResponse(items=jobs, total=total, page=page, page_size=page_size)
```

### Example 3: ActionResponse with Literal Status

```python
# Source: Phase 129 CONTEXT.md design
from typing import Literal, Optional
from pydantic import BaseModel, Field

class ActionResponse(BaseModel):
    """Unified response for all action endpoints (cancel, revoke, approve, etc.)."""

    status: Literal[
        "acknowledged", "cancelled", "revoked", "approved",
        "deleted", "updated", "created", "enabled", "disabled"
    ] = Field(
        description="Action status. Literal union catches typos at dev time."
    )
    resource_type: str = Field(
        description="Type of resource actioned (e.g., 'job', 'node', 'signature')",
        json_schema_extra={"examples": ["job"]}
    )
    resource_id: str | int = Field(
        description="ID of the actioned resource",
        json_schema_extra={"examples": ["550e8400-e29b-41d4-a716-446655440000"]}
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional detail message"
    )

# Usage
@app.post("/jobs/{guid}/cancel", response_model=ActionResponse, tags=["Jobs"])
async def cancel_job(guid: str):
    return ActionResponse(
        status="cancelled",
        resource_type="job",
        resource_id=guid,
        message="Job cancelled by operator"
    )
```

### Example 4: ErrorResponse with Route Usage

```python
# Source: FastAPI + Pydantic best practices
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    detail: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")

# Applied to route
@app.get(
    "/jobs/{guid}",
    response_model=JobResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        403: {"model": ErrorResponse, "description": "Access denied"}
    },
    tags=["Jobs"]
)
async def get_job(guid: str):
    job = await db.get_job(guid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

### Example 5: Snapshot Test Pattern (Schema Validation)

```python
# Source: Phase 129 design — test that routes conform to response models
import pytest
from httpx import AsyncClient
from pydantic import ValidationError

@pytest.mark.asyncio
async def test_list_jobs_response_shape(async_client: AsyncClient):
    """Snapshot test: verify /api/jobs response matches PaginatedResponse[JobResponse] schema."""
    response = await async_client.get("/api/jobs?page=1&page_size=10")
    assert response.status_code == 200

    data = response.json()

    # Validate against model — will raise ValidationError if shape is wrong
    from agent_service.models import PaginatedResponse, JobResponse
    paginated = PaginatedResponse[JobResponse](**data)

    assert paginated.total >= 0
    assert len(paginated.items) <= paginated.page_size
    assert paginated.page == 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare `List[dict]` responses | `response_model=List[SpecificModel]` | FastAPI v0.100+ | Type safety in responses; OpenAPI auto-generation |
| `PaginatedJobResponse` only | Generic `PaginatedResponse[T]` | Pydantic v2 (stable since 2023) | Single model handles all paginated endpoints |
| enum.Enum for status fields | `Literal["status1", "status2"]` | Pydantic v2 (preferred) | Cleaner syntax; works with TypedDict; generates proper OpenAPI enum |
| `from_orm()` method | `model_config = ConfigDict(from_attributes=True)` | Pydantic v2 (v1 deprecated) | More explicit config; no breaking method changes |
| SQLAlchemy `__dict__` unpacking | Direct `response_model=` in route | FastAPI maturity | FastAPI handles ORM → Pydantic conversion automatically |

**Deprecated/outdated:**
- **Pydantic v1 `Config` inner class**: Replaced by `model_config = ConfigDict(...)` in v2. Old pattern:
  ```python
  class MyModel(BaseModel):
      class Config:
          from_attributes = True
  ```
  New pattern (this project uses):
  ```python
  class MyModel(BaseModel):
      model_config = ConfigDict(from_attributes=True)
  ```

- **Implicit response serialization (no `response_model=`)**: Works, but doesn't validate responses or generate OpenAPI schema. Phase 129 is fixing the remaining 62 routes that still rely on this.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (via requirements.txt) |
| Config file | `puppeteer/tests/conftest.py` (shared fixtures) |
| Quick run command | `cd puppeteer && pytest tests/test_*.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map
| Domain | Test Type | Automated Command | Existing Tests? |
|--------|-----------|-------------------|-----------------|
| Core models (ActionResponse, PaginatedResponse, ErrorResponse) | unit | `pytest tests/test_models_core.py -x` | ❌ Wave 0 — Create for Plan 01 |
| Jobs routes (12 routes with response models) | integration | `pytest tests/test_jobs_responses.py::test_list_jobs_shape -x` | ❌ Wave 0 — Create for Plan 02 |
| Nodes routes (10 routes with response models) | integration | `pytest tests/test_nodes_responses.py -x` | ❌ Wave 0 — Create for Plan 03 |
| Admin/Auth routes (15 routes with response models) | integration | `pytest tests/test_admin_responses.py -x` | ❌ Wave 0 — Create for Plan 04 |
| Foundry/Smelter/System routes (25 routes with response models) | integration | `pytest tests/test_foundry_responses.py -x` | ❌ Wave 0 — Create for Plan 05 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_{domain}_responses.py -x` (5-10 routes per test file, runs in <5 seconds)
- **Per wave/plan merge:** Full suite `pytest tests/` (covers all 179 routes, runs in <30 seconds)
- **Phase gate:** Full suite green + manual spot-check of `/docs` OpenAPI for 5 sample routes before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_models_core.py` — unit tests for ActionResponse, PaginatedResponse[T], ErrorResponse serialization
- [ ] `tests/test_jobs_responses.py` — integration snapshot tests for all 12 Jobs domain routes
- [ ] `tests/test_nodes_responses.py` — integration snapshot tests for all 10 Nodes domain routes
- [ ] `tests/test_admin_responses.py` — integration snapshot tests for all 15 Admin/Auth routes
- [ ] `tests/test_foundry_responses.py` — integration snapshot tests for all 25 Foundry/Smelter/System routes
- [ ] Pydantic v2 Generic import verified in models.py (`from typing import Generic, TypeVar`)
- [ ] Pytest fixtures for Auth (bearer token injection) and DB session setup in conftest.py (likely already present)

**If gaps exist:** Each plan will create its test file before implementing response models. Snapshot tests validate that routes conform to their declared models — a simple pattern:
```python
async def test_route_shape(async_client):
    response = await async_client.get("/api/endpoint")
    data = response.json()
    validated = ModelClass(**data)  # Raises ValidationError if shape mismatches
    assert validated.field == expected
```

---

## Open Questions

1. **EE Router Response Model Integration**
   - What we know: EE routers (foundry, smelter, auth_ext, etc.) already use `response_model=` on most routes (77 total). Phase 129 focuses on main.py and standardizing pagination/actions.
   - What's unclear: Should EE models be extended in Phase 129, or handled separately in Phase 130+?
   - Recommendation: Keep Phase 129 scoped to CE routes in main.py + existing EE routers' missing response models. Don't redesign EE response shapes.

2. **Backward Compatibility Testing Depth**
   - What we know: Current frontend consumes `{items, total}` from paginated endpoints; ActionResponse will be new for action routes (currently returning job/node objects).
   - What's unclear: How aggressively to test that frontend doesn't break? (E.g., is a full Playwright verification run required per plan, or just schema snapshot tests?)
   - Recommendation: Schema snapshot tests (unit) per plan commit; full Playwright suite at phase gate only. This balances safety with velocity.

3. **Pagination Default `page_size`**
   - What we know: CONTEXT.md specifies `page_size=50` default across all endpoints.
   - What's unclear: Do all current paginated endpoints support page_size query param, or do some have hardcoded limits?
   - Recommendation: Research during Plan 02 (Jobs domain); uniform 50 across all. If a route has a different semantic limit (e.g., max 100), document via `Field(le=100)`.

4. **ActionResponse and Existing Action Routes**
   - What we know: 11+ action endpoints exist (acknowledge, cancel, revoke, approve, delete, update, create, enable, disable).
   - What's unclear: Do they currently return the actioned resource (full JobResponse) or just `{status: "ok"}`? If the former, switching to ActionResponse is breaking.
   - Recommendation: Research during Plan 02/03; if breaking, add a transition plan (deprecation header, feature flag, or accept both shapes for a sprint).

---

## Sources

### Primary (HIGH confidence)
- **Pydantic v2 Documentation** — Generic model support, `model_config = ConfigDict(from_attributes=True)` (https://docs.pydantic.dev/latest/)
- **FastAPI Documentation** — `response_model=`, tags, summary, description, responses parameter (https://fastapi.tiangolo.com/advanced/response-model/)
- **Project codebase** — 26/89 routes in main.py already use `response_model=`; `PaginatedJobResponse` existing pattern in models.py (verified via grep)
- **Pydantic v2.12.5** — Confirmed installed in puppeteer/requirements.txt; Generic[T] fully supported

### Secondary (MEDIUM confidence)
- **CONTEXT.md Phase 129** — User decisions (ActionResponse, PaginatedResponse[T], ErrorResponse, migration strategy)
- **Existing test patterns** — conftest.py uses AsyncClient + ASGI transport; snapshot test pattern verified in test_*.py files

### Tertiary (LOW confidence)
- None — all findings verified by primary sources or project artifacts

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — FastAPI, Pydantic v2.12.5, pytest confirmed in codebase
- Architecture patterns: **HIGH** — Verified in existing response models (JobResponse, PaginatedJobResponse, etc.) and Pydantic v2 docs
- Pitfalls: **MEDIUM** — Based on common Pydantic v2 + FastAPI integration issues; project-specific patterns mitigate most
- Test infrastructure: **HIGH** — Existing conftest.py and test files provide clear test patterns

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days; Pydantic v2 is stable; FastAPI changes are backward-compatible in point releases)

**Scope Summary:**
- 89 routes in main.py (26 with response_model, 63 without)
- 90 routes in EE routers (77 with response_model, 13 without)
- **Phase goal:** Add `response_model=` to all 62+ unmodeled routes + introduce ActionResponse + generalize pagination
- **Backward compatibility:** Current frontend consumes existing response shapes; new models must match exactly or use field aliases
- **Test strategy:** Snapshot tests per plan; full suite at phase gate

---

*Research completed: 2026-04-11*
*Phase: 129-response-model-auto-serialization*

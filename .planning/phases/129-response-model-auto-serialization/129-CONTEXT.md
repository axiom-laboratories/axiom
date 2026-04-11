# Phase 129: Response Model Auto-Serialization - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `response_model=` with proper Pydantic models to all 62 FastAPI route handlers that currently return raw dicts or unvalidated data. Standardize action responses, pagination, and OpenAPI documentation. Backend-only — no frontend changes.

</domain>

<decisions>
## Implementation Decisions

### Standardized action responses
- Unified `ActionResponse` model for all 11+ action endpoints (acknowledge, cancel, revoke, approve, delete, etc.)
- Fields: `status` (Literal union), `resource_type` (str), `resource_id` (str | int), `message` (optional)
- Status field uses `Literal["acknowledged", "cancelled", "revoked", "approved", "deleted", "updated", "created", "enabled", "disabled"]` — catches typos at dev time, generates enum in OpenAPI
- No timestamp field — audit log already tracks timing
- Strip responses to ActionResponse only — no extra data fields. Frontend does a follow-up GET if it needs the full resource

### Pagination consistency
- Generic `PaginatedResponse[T]` model using Pydantic v2 generics: `items: list[T]`, `total: int`, `page: int`, `page_size: int`
- Replace existing `PaginatedJobResponse` with `PaginatedResponse[JobResponse]` — delete the old model
- All list endpoints use `PaginatedResponse[T]`, including small collections (signatures, users, roles)
- Default `page_size=50` across all paginated endpoints

### Migration strategy
- Migrate by domain, one plan each:
  - Plan 01: Core models (ActionResponse, PaginatedResponse[T], ErrorResponse)
  - Plan 02: Jobs domain (~12 routes)
  - Plan 03: Nodes domain (~10 routes)
  - Plan 04: Admin/Auth domain (~15 routes)
  - Plan 05: Foundry/Smelter/System (~25 routes)
- Backend only — frontend code not updated in this phase (response shapes stay compatible)
- New models must match existing response shapes exactly first — no breaking changes. Refactoring to ActionResponse is a separate commit within the same plan
- Each domain plan includes schema snapshot tests that call routes and validate responses match Pydantic models

### OpenAPI documentation quality
- Full doc treatment: `Field(description='...', json_schema_extra={'examples': [...]})` on all response model fields
- Route decorators get `tags=[domain]`, `summary='One-line description'`, and multi-line `description` with usage notes
- Standard `ErrorResponse` model: `detail: str`, `status_code: int` — added via `responses={404: {"model": ErrorResponse}}` on routes
- Use FastAPI default `/openapi.json` and `/docs` endpoints — no custom versioned spec

### Claude's Discretion
- Exact grouping of routes into domain plans (may adjust based on actual dependency analysis)
- How to handle edge cases where existing response shapes are inconsistent within the same route
- Whether to split Plan 05 (Foundry/Smelter/System) into two plans if scope is too large
- Field description wording and example values

</decisions>

<specifics>
## Specific Ideas

- ActionResponse Literal union should be exhaustive — enumerate all current action verbs from existing routes
- PaginatedResponse generic should work cleanly with Pydantic v2 — verify Generic[T] serialization in FastAPI
- Schema snapshot tests: call route, parse response against model, assert no ValidationError

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaginatedJobResponse` in models.py: existing pagination pattern to generalize
- `DispatchResponse`, `NodeResponse`, `SignatureResponse`: well-established response models to follow as patterns
- ~26 routes already use `response_model=` — these are the reference implementation

### Established Patterns
- Pydantic v2 models in `agent_service/models.py` — all new models go here
- Route handlers in `agent_service/main.py` (2,984 lines) — all 88 routes live in one file
- Tests in `puppeteer/tests/` — existing test patterns for API endpoints

### Integration Points
- `main.py` route decorators: add `response_model=`, `tags=`, `summary=`, `description=`, `responses=`
- `models.py`: new models (ActionResponse, PaginatedResponse[T], ErrorResponse, ~20 missing domain models)
- Existing frontend reads `{items, total}` shape from paginated endpoints — must remain compatible
- OpenAPI auto-generated at `/docs` and `/openapi.json`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 129-response-model-auto-serialization*
*Context gathered: 2026-04-11*

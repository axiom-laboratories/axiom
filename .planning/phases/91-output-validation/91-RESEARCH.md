# Phase 91: Output Validation — Research

## Research Summary

All integration points identified. Phase is a pure backend-first feature with targeted frontend additions. No net-new infrastructure needed.

---

## Validation Architecture

### Entry Point: `job_service.py: process_result()`

The exact insertion point is lines 1073–1076:
```python
elif report.success:
    new_status = "COMPLETED"
else:
    new_status = "FAILED"
```

Validation logic inserts **after** the `SECURITY_REJECTED` branch and **before** the `COMPLETED` assignment. At this point `stdout_text` is already extracted (line 1094). The hook:

1. Parse `validation_rules` from `job.payload` JSON
2. If rules present and `new_status` is about to become `"COMPLETED"`:
   - Evaluate exit code rule (if set)
   - Evaluate stdout regex rule (if set)
   - Evaluate JSON field rule (if both path and expected value set)
3. If any rule fails: set `new_status = "FAILED"`, populate `failure_reason` with the first-failing rule code per fixed priority
4. Validation failures set `retriable = False` implicitly (separate from `report.retriable`)

### DB Changes Required

**`ScheduledJob`** (`.planning/phases/91-output-validation/91-CONTEXT.md` confirms):
- Add: `validation_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` — stores JSON like `{"exit_code": 0, "stdout_regex": "...", "json_path": "...", "json_expected": "..."}`

**`ExecutionRecord`**:
- Add: `failure_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)` — one of: `execution_error`, `validation_exit_code`, `validation_regex`, `validation_json_field` (Phase 87 codes)

Both columns are nullable — `create_all` handles fresh installs; existing deployments need `ALTER TABLE`.

### Dispatch Stamping: `scheduler_service.py`

`dispatch_scheduled_job()` builds `payload_dict` at line 225–230. Add `"validation_rules": s_job.validation_rules` (pass through as raw JSON string, or parse+re-dump). Node never sees or uses validation_rules — it only comes back to the server at result time.

### Validation Logic Implementation

Three rule types, all pure Python:

**Exit code** (`validation_exit_code`):
```python
rule_exit = rules.get("exit_code")
if rule_exit is not None and report.exit_code != rule_exit:
    failures.append("validation_exit_code")
```

**Stdout regex** (`validation_regex`):
```python
import re
if rules.get("stdout_regex"):
    if not re.search(rules["stdout_regex"], stdout_text):
        failures.append("validation_regex")
```

**JSON field** (`validation_json_field`):
```python
import json as _json
json_path = rules.get("json_path")
json_expected = rules.get("json_expected")
if json_path and json_expected is not None:
    try:
        parsed = _json.loads(stdout_text)
        parts = json_path.split(".")
        val = parsed
        for p in parts:
            val = val[p]
        if str(val) != str(json_expected):
            failures.append("validation_json_field")
    except Exception:
        failures.append("validation_json_field")
```

Priority order for `failure_reason`: exit_code → regex → json_field (first element of `failures` list if ordered this way).

### Retry Suppression for Validation Failures

`validation_failure` is always terminal. In `process_result()`, the retry block (line 1174) checks `report.retriable is True`. Validation failures bypass this by setting `failure_reason` and NOT using the retriable path — `new_status = "FAILED"` without entering the retry block. The simplest approach: set a local `_validation_failed = True` flag before the existing retry check, then guard the retry block with `and not _validation_failed`.

---

## API Changes Required

### `JobDefinitionResponse` (models.py)
Add field: `validation_rules: Optional[Dict[str, Any]] = None`
Add `@field_validator('validation_rules', mode='before')` to deserialize JSON string from DB.

### `JobDefinitionUpdate` (models.py)
Add field: `validation_rules: Optional[Dict[str, Any]] = None`

### `ExecutionRecordResponse` (models.py)
Add field: `failure_reason: Optional[str] = None`

### `JobCreate` (models.py)
No change — ad-hoc jobs never carry validation_rules per spec.

### `/jobs/definitions` POST route (main.py)
Pass `validation_rules` from request body → `ScheduledJob` column (JSON-encode dict to string).

### `/jobs/definitions/{id}` PATCH route (main.py / scheduler_service.py)
`update_job_definition()` must handle `validation_rules` field.

### `/api/executions` GET route
`ExecutionRecord` → `ExecutionRecordResponse` serialisation already uses `from_attributes = True` — the new `failure_reason` column will auto-serialize once added to the model.

---

## Frontend Changes Required

### `JobDefinitionModal.tsx`

**`JobDefinitionFormData` interface**: add `validation_exit_code: string; validation_stdout_regex: string; validation_json_path: string; validation_json_expected: string;`

**`EditingJob` interface**: add `validation_rules?: { exit_code?: number; stdout_regex?: string; json_path?: string; json_expected?: string } | null`

**`useEffect` pre-population**: parse `editingJob.validation_rules` into the four flat form fields.

**Form section**: collapsible "Validation Rules" div at the bottom of the form. Auto-expanded if any rule is set. Contains:
- Exit code input (number, default `0`, placeholder "Leave empty to skip")
- Stdout regex input (text, empty = not enforced)
- JSON path input + JSON expected value input (side by side)

**`onSubmit` serialization**: pack four flat fields back into `validation_rules` dict, omit keys where empty.

**Parent component (`JobDefinitions.tsx`)**: thread `validation_rules` field through `formData` state and form submit handler → API body.

### `DefinitionHistoryPanel.tsx` (in `JobDefinitions.tsx`)

In the execution row render, after the status badge, add a `failure_reason` label. When `row.failure_reason && row.status === 'FAILED'`:
```tsx
<span className="text-[10px] text-orange-400 font-mono ml-1">
    Validation failed: {row.failure_reason.replace('validation_', '')}
</span>
```
Distinct from runtime errors (no `failure_reason` = runtime failure = show nothing extra).

### `Jobs.tsx` — Job Detail Sheet

Find the status/exit-code display in the job detail sheet. When execution record has `failure_reason` starting with `validation_`, show a distinct label: `"Validation failed: {rule}"` in orange, separate from the generic FAILED state.

---

## Migration SQL

```sql
-- migration_v17.sql (or inline with existing migration pattern)
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS validation_rules TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(64);
```

Fresh installs: `create_all` handles both columns automatically.

---

## Test Coverage

**Backend unit tests (`puppeteer/tests/`):**
- `test_output_validation.py` — parameterised tests for all three rule types: pass, fail, edge cases
- Test validation failure does NOT trigger retry logic
- Test that null `validation_rules` leaves existing behaviour unchanged

**Frontend tests (`dashboard/src/views/__tests__/`):**
- `JobDefinitions.test.tsx` — validation rules section renders, pre-populates on edit, collapses/expands
- `History.test.tsx` — `failure_reason` label renders for validation failures; does not render for runtime failures

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| JSON path parsing depth | Low | Spec limits to simple dot-notation; array indexing deferred per CONTEXT.md |
| stdout_text empty for non-stdout scripts | Low | Empty string fails regex match — operator informed via docs |
| Retry guard regression | Low | Existing test suite covers retry paths; add explicit "no retry on validation failure" test |
| Migration for existing deployments | Low | Standard IF NOT EXISTS pattern used in all prior migrations |

---

## RESEARCH COMPLETE

Phase 91 is straightforward: one backend service insertion point, two DB columns, three Pydantic model additions, two frontend component changes. No new libraries needed. No architectural decisions left open. All design choices are in CONTEXT.md.

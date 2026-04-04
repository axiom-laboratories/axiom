---
phase: 88-dispatch-diagnosis-ui
plan: 01
status: complete
completed_by: retroactive-summary
---

## What Was Done

Extended `get_dispatch_diagnosis` in `job_service.py` with a `stuck_assigned` branch — jobs assigned beyond `timeout_minutes * 1.2` are now flagged with reason, message, and elapsed time.

Added `POST /jobs/dispatch-diagnosis/bulk` endpoint in `main.py` that accepts a `BulkDiagnosisRequest` (list of GUIDs) and returns aggregated diagnosis results keyed by GUID.

Added `BulkDiagnosisRequest` model in `models.py`.

## Artifacts

| File | Change |
|------|--------|
| `puppeteer/agent_service/services/job_service.py` | `stuck_assigned` branch in `get_dispatch_diagnosis` |
| `puppeteer/agent_service/models.py` | `BulkDiagnosisRequest` model |
| `puppeteer/agent_service/main.py` | `GET /jobs/{guid}/dispatch-diagnosis` + `POST /jobs/dispatch-diagnosis/bulk` routes |
| `puppeteer/tests/test_dispatch_diagnosis.py` | 6 tests covering diagnosis scenarios |

## Deviations

None — implementation matches plan.

# Plan 15-03: Wave 3 — Integration & Governance — Summary

## Accomplishments
- Integrated `StagingService` into the `FoundryService.build_template` pipeline:
    - Successfully builds now trigger an automatic **Smelt-Check** (post-build validation).
    - Template status transitions: `DRAFT` → `STAGING` → (`ACTIVE` or `FAILED`).
    - Automated **BOM Capture** upon successful validation.
- Implemented **Lifecycle Enforcement**:
    - Updated `/api/enroll`: Blocks enrollment if the node's assigned template is `REVOKED`.
    - Updated `JobService.pull_work`: Blocks job fetching (concurrency = 0) if the node is running a `REVOKED` image.
    - Updated `Node` model and database schema to track `template_id` for accurate lifecycle monitoring.
- Fixed error handling in `enroll_node` to correctly surface `HTTPException` status codes.
- Verified enforcement with unit tests in `puppeteer/tests/test_lifecycle_enforcement.py`.

## Verification Results
- `puppeteer/tests/test_lifecycle_enforcement.py`: **PASSED** (2/2 tests).
- Build Pipeline Integration: Confirmed Smelt-Check and BOM logic are correctly invoked.
- Schema Integrity: `nodes` table now correctly tracks `template_id` (via migration v31).

## Next Steps
- **Plan 15-04**: Wave 4 — Lifecycle UI & BOM Explorer — Updating the dashboard to manage image status and search across BOMs.

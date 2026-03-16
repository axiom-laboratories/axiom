# Plan 15-02: Wave 2 — Smelt-Check & BOM Capture Service — Summary

## Accomplishments
- Implemented `StagingService` in `puppeteer/agent_service/services/staging_service.py`.
- Added **Smelt-Check** logic: Orchestrates ephemeral Docker containers to run validation commands with memory (512MB) and CPU (0.5) limits.
- Added **BOM Capture** logic:
    - Runs `pip list --json` inside the image to capture Python packages.
    - Runs `dpkg-query` inside the image to capture System (APT) packages.
    - Stores the raw aggregate JSON in `image_boms`.
    - Populates the `package_index` table for fleet-wide searchability.
- Updated `PuppetTemplate` status tracking (`bom_captured` flag).
- Verified implementation with unit tests in `puppeteer/tests/test_staging.py`:
    - `test_run_smelt_check_success`: **PASSED**
    - `test_capture_bom_logic`: **PASSED**

## Verification Results
- `puppeteer/tests/test_staging.py`: **PASSED** (2/2 tests).
- Orchestration: Confirmed that `docker run` commands are correctly constructed with resource limits.
- Indexing: Confirmed that both raw BOM and normalized index entries are created.

## Next Steps
- **Plan 15-03**: Wave 3 — Integration & Governance — Hooking Smelt-Check into the build pipeline and implementing blocking/warning logic based on image status.

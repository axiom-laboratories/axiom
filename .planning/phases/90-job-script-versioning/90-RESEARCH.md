# Phase 90: Job Script Versioning — Research

**Researcher:** gsd-phase-researcher
**Date:** 2026-03-29
**Phase:** 90 — Job Script Versioning
**Requirements:** VER-01, VER-02, VER-03

---

## Validation Architecture

### Framework

| Property | Value |
|----------|-------|
| **Backend** | pytest (puppeteer/tests/) |
| **Frontend** | vitest (puppeteer/dashboard/src/) |
| **Quick run (backend)** | `cd puppeteer && pytest tests/test_scheduler.py -x -q` |
| **Full suite (backend)** | `cd puppeteer && pytest -x -q` |
| **Frontend run** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30s (backend), ~15s (frontend) |

### Continuous Validation
- After every task: `cd puppeteer && pytest tests/test_scheduler.py -x -q` (or vitest for frontend tasks)
- After every wave: full backend + frontend suite
- All tests must be green before verification

---

## Codebase Findings

### DB Layer (`puppeteer/agent_service/db.py`)

**ScheduledJob** (line 61): Has `script_content` (Text), `signature_id`, `signature_payload`, `updated_at`. No version tracking exists today. This is the mutation target.

**Job** (line 20): Has `scheduled_job_id` (String, nullable) linking back to the definition. Needs new `definition_version_id` column (nullable FK). No version FK today.

**New table needed**: `job_definition_versions` — full snapshot per save. Will be auto-created by `Base.metadata.create_all` on fresh deployments. Existing deployments require `migration_v44.sql`.

**Existing migration pattern**: Latest is `migration_v43.sql`. Next will be `migration_v44.sql`. Pattern is `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` for Postgres; new tables use `CREATE TABLE IF NOT EXISTS`.

### Scheduler Service (`puppeteer/agent_service/services/scheduler_service.py`)

**`create_job_definition()`** (line 404): Creates `ScheduledJob`, commits, then starts scheduler. Verified signature before creating. Phase 90 must also create version 1 here after `db_session.commit()` (or in the same transaction, pre-commit).

**`update_job_definition()`** (line 462): Multiple cases for script change, re-sign, draft transitions. This is where version 2+ are created. Version must be written inside the update logic, before `job.updated_at = datetime.utcnow()` line (line 571). Each update path (cases a, b/c/d, e) needs a version write.

**`dispatch_scheduled_job()`** (line ~220–253): Creates the `Job` row. Needs to query current signed version and stamp `definition_version_id`. Currently sets `scheduled_job_id=s_job.id` but not version. The version to stamp is the latest `is_signed=True` version for that definition.

### API Layer (`puppeteer/agent_service/main.py`)

No existing version endpoints. Need to add:
- `GET /jobs/definitions/{id}/versions` — list all versions for a definition (paginated, ordered by `version_number DESC`)
- `GET /jobs/definitions/{id}/versions/{version_num}` — single version with full `script_content`

Both should require `jobs:read` permission.

### Frontend

**`JobDefinitions.tsx`**:
- `DefinitionHistoryPanel` (line 43–81): Currently queries `/api/executions?scheduled_job_id=...` and renders a table. Phase 90 extends this to an interleaved timeline: fetch both executions and version change rows, merge and sort by timestamp.
- Table headers (line 95–103): Currently shows When/Node/Status/Duration/Retry/Logs. Need to add a "Version" column.
- Each execution row needs a version badge (e.g. `v3`).
- Version change rows are visually distinct (lighter, different icon, non-clickable).

**`Jobs.tsx`**:
- `scriptContent` field exists in job state (line 94). Already displayed in the job detail sheet (lines 986, 1095).
- Need: "View script (vN)" action button in the job detail sheet that opens a read-only modal showing the versioned script.
- If `definition_version_id` is null (pre-phase-90 jobs): show "View script" without version number, use script from payload.

### Signing/Draft Interaction

The context specifies a DRAFT/LIVE model:
- Script change without re-sign → version written with `is_signed=False`
- Non-script changes → version written with `is_signed=True` (signature unchanged)
- Re-sign event → new version with `is_signed=True`
- Dispatch stamps the **latest `is_signed=True` version**

This aligns with the existing `job.status = "DRAFT"` pattern in `update_job_definition()`.

### React Diff Viewer

For side-by-side diff ("Compare with previous"), `react-diff-viewer-continued` is the maintained fork of the popular `react-diff-viewer`. It accepts `oldValue`/`newValue` strings and renders split or unified diff. Alternative: roll a simple inline unified diff using the `diff` npm package (already common in JS). Given bundle size concerns, the simpler `diff` library approach renders output as a color-coded pre block without adding a heavy dependency.

Recommendation: Use `react-diff-viewer-continued` (well-maintained, ~50kB gzipped) — it fits the dark Zinc UI theme with custom styles. Install in Wave 1 alongside the ScriptViewerModal component.

### Change Summary Generation

The context notes `change_summary` can be auto-generated. Pattern: before writing the new version, compare fields to the previous version and build a summary string. E.g.:
- `script_content` changed → "Script updated"
- `schedule_cron` changed → `Schedule changed to '0 * * * *'`
- `target_tags` changed → "Target tags updated"
- Multiple fields → comma-separated

This is straightforward string diff logic in Python; no library needed.

---

## Implementation Strategy

### Wave 1: DB + Backend Core
1. Add `JobDefinitionVersion` model to `db.py`
2. Add `definition_version_id` FK column to `Job`
3. Write `migration_v44.sql`
4. Add `_create_version_snapshot()` helper to `scheduler_service.py`
5. Call snapshot in `create_job_definition()` (version 1) and all branches of `update_job_definition()` (version N+1)
6. Stamp `definition_version_id` in `dispatch_scheduled_job()`
7. Add `GET /jobs/definitions/{id}/versions` and `GET /jobs/definitions/{id}/versions/{version_num}` endpoints to `main.py`

### Wave 2: Frontend
1. Install `react-diff-viewer-continued` (or `diff`)
2. Add `ScriptViewerModal` component (read-only syntax-highlighted code + copy + compare-with-previous diff)
3. Update `DefinitionHistoryPanel` in `JobDefinitions.tsx`:
   - Fetch versions alongside executions
   - Merge into interleaved timeline
   - Add "Version" column with badge on execution rows
   - Version change rows with distinct styling
4. Update `Jobs.tsx` job detail sheet:
   - Add "View script (vN)" action button
   - Opens `ScriptViewerModal` with the execution's version

---

## Risk Areas

| Risk | Mitigation |
|------|-----------|
| `dispatch_scheduled_job()` runs inside APScheduler cron — no HTTP context | Query latest signed version directly via `AsyncSession`; already async |
| Pre-phase-90 Job rows have `definition_version_id = NULL` | UI handles null gracefully: show "View script" without version badge, fall back to payload |
| Version table row per save could grow quickly | Not a concern for v16.0 scope; pruning is deferred |
| Diff library adds bundle weight | `react-diff-viewer-continued` is lazy-imported inside the modal — no impact on initial load |

---

## RESEARCH COMPLETE

Phase 90 is well-scoped. The context decisions are fully aligned with the codebase. Two waves:
- Wave 1: DB model + backend versioning logic + API endpoints (~6 tasks)
- Wave 2: Frontend ScriptViewerModal + history timeline + Jobs.tsx integration (~5 tasks)

Requirements VER-01, VER-02, VER-03 are all addressable with the above approach.

---
phase: 91-output-validation
plan: 02
subsystem: ui
tags: [react, typescript, vitest, validation, job-definitions]

# Dependency graph
requires:
  - phase: 91-output-validation plan 01
    provides: validation_rules column on scheduled_jobs, failure_reason on execution_records, backend evaluation logic

provides:
  - Collapsible Validation Rules form section in JobDefinitionModal (exit_code, stdout_regex, json_path/expected)
  - validation_rules serialized into API payload on form submit
  - Pre-population of validation fields when editing a definition with existing rules
  - Auto-expansion of validation section when editing a definition with rules set
  - Orange "Validation failed: {rule}" label in DefinitionHistoryPanel for FAILED rows with validation failure_reason
  - Same distinct validation failure label in Jobs.tsx execution records table
  - Same label in History.tsx execution history table

affects: [job-definitions-frontend, jobs-frontend, history-frontend, output-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: [validation failure display via failure_reason.startsWith('validation_'), flat form fields serialized into nested dict on submit]

key-files:
  created: []
  modified:
    - puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/dashboard/src/views/History.tsx
    - puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx
    - puppeteer/dashboard/src/views/__tests__/History.test.tsx

key-decisions:
  - "Validation section uses flat form fields (validation_exit_code, validation_stdout_regex, etc.) serialized into nested validation_rules dict at submit time — mirrors existing pattern for tags/caps"
  - "failure_reason display uses startsWith('validation_') guard — keeps runtime failures (no failure_reason) visually distinct with zero ambiguity"
  - "Validation section collapsed by default; auto-expands when any validation_rules field is non-null on edit"

patterns-established:
  - "Flat-to-nested serialization: flat form string fields → buildValidationRules() → nested API dict"
  - "Validation failure badge: orange text-orange-400 with AlertTriangle icon, 'Validation failed: {rule_suffix}'"

requirements-completed: [VALD-01, VALD-03]

# Metrics
duration: 15min
completed: 2026-03-30
---

# Plan 91-02: Frontend — Validation Rules Form and Failure Display Summary

**Collapsible validation rules form in JobDefinitionModal with serialization on submit, and orange "Validation failed" badge in all three execution history views**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-30T10:48:00Z
- **Completed:** 2026-03-30T10:53:00Z
- **Tasks:** 6
- **Files modified:** 6

## Accomplishments
- JobDefinitionModal gains a collapsible "Validation Rules" section (exit code, stdout regex, JSON path+expected) that auto-expands when editing a definition with rules
- Validation fields serialize to `validation_rules` dict in buildPayload(); edit mode pre-populates all four fields from existing rules
- DefinitionHistoryPanel, Jobs.tsx execution records, and History.tsx all show orange "Validation failed: {rule}" for validation failures, leaving runtime failures visually distinct
- 5 new tests added (4 in JobDefinitions.test.tsx, 1 in History.test.tsx); all pass

## Task Commits

1. **Tasks 91-02-01 & 91-02-02: JobDefinitionModal interfaces + collapsible section** - `cf48c7e`
2. **Tasks 91-02-03 & 91-02-04: Serialize validation_rules + failure_reason in DefinitionHistoryPanel** - `6f288fe`
3. **Task 91-02-05: failure_reason display in Jobs.tsx and History.tsx** - `7f77bba`
4. **Task 91-02-06: Frontend tests** - `4838b3d`

## Files Created/Modified
- `puppeteer/dashboard/src/components/job-definitions/JobDefinitionModal.tsx` - Added 4 form fields to interface, collapsible Validation Rules section, auto-expand useEffect
- `puppeteer/dashboard/src/views/JobDefinitions.tsx` - Extended EMPTY_FORM and EditingJob, added buildValidationRules(), failure_reason display in DefinitionHistoryPanel
- `puppeteer/dashboard/src/views/Jobs.tsx` - failure_reason validation badge in execution records table
- `puppeteer/dashboard/src/views/History.tsx` - failure_reason validation badge + AlertTriangle import
- `puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx` - 4 new VALD tests
- `puppeteer/dashboard/src/views/__tests__/History.test.tsx` - 1 new VALD-03 test

## Decisions Made
- Flat form fields serialized to nested dict at submit time — consistent with how target_tags and capability_requirements are handled
- `failure_reason.startsWith('validation_')` guard is the reliable discriminator between validation failures and runtime failures
- Validation section collapses by default to avoid cluttering the form for simple jobs

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
One pre-existing test failure in JobDefinitions.test.tsx (`OUTPUT-04: history panel calls GET /api/executions?scheduled_job_id=X`) was present before this plan and remains unchanged — it is a mock routing issue unrelated to this plan's work.

## Next Phase Readiness
- Phase 91 is now fully complete: backend (91-01) + frontend (91-02)
- Milestone v16.0 all implementation phases (88–91) complete
- Ready for integration testing of the complete output validation flow

---
*Phase: 91-output-validation*
*Completed: 2026-03-30*

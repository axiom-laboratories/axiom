---
phase: 107
slug: schema-foundation-crud-completeness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 107 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), vitest + @testing-library/react (frontend) |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_blueprint_edit.py tests/test_approved_os_crud.py tests/test_schema_v46.py -x` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_blueprint_edit.py tests/test_approved_os_crud.py tests/test_schema_v46.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 107-01-01 | 01 | 1 | MIRR-10 | unit | `cd puppeteer && pytest tests/test_schema_v46.py -x` | ❌ W0 | ⬜ pending |
| 107-01-02 | 01 | 1 | MIRR-10 | unit | `cd puppeteer && pytest tests/test_schema_v46.py -x` | ❌ W0 | ⬜ pending |
| 107-02-01 | 02 | 1 | CRUD-01 | unit | `cd puppeteer && pytest tests/test_blueprint_edit.py -x` | ❌ W0 | ⬜ pending |
| 107-02-02 | 02 | 1 | CRUD-01 | unit | `cd puppeteer && pytest tests/test_blueprint_edit.py -x` | ❌ W0 | ⬜ pending |
| 107-02-03 | 02 | 1 | CRUD-04 | unit | `cd puppeteer && pytest tests/test_blueprint_deps.py -x` | ❌ W0 | ⬜ pending |
| 107-03-01 | 03 | 2 | CRUD-02 | unit | existing capability matrix tests | ✅ | ⬜ pending |
| 107-03-02 | 03 | 2 | CRUD-03 | unit | `cd puppeteer && pytest tests/test_approved_os_crud.py -x` | ❌ W0 | ⬜ pending |
| 107-03-03 | 03 | 2 | CRUD-04 | integration | frontend vitest | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_blueprint_edit.py` — stubs for CRUD-01 (PATCH + optimistic locking + 409)
- [ ] `puppeteer/tests/test_approved_os_crud.py` — stubs for CRUD-03 (PATCH + referential integrity on DELETE)
- [ ] `puppeteer/tests/test_schema_v46.py` — stubs for MIRR-10 (ecosystem column, new tables)
- [ ] `puppeteer/tests/test_blueprint_deps.py` — stubs for CRUD-04 (422 deps_required flow)

*Existing infrastructure covers CRUD-02 tool recipe edit via capability matrix PATCH tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BlueprintWizard pre-populates all fields in edit mode | CRUD-01 | Visual verification of form state | Open wizard in edit mode, verify all 5 steps pre-populated |
| Dependency confirmation dialog shows correct dep list | CRUD-04 | UI interaction flow | Create blueprint with missing deps, verify dialog shows, accept, verify save |
| Approved OS delete blocked when referenced | CRUD-03 | E2E flow verification | Create OS entry, reference in blueprint, attempt delete, verify 409 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

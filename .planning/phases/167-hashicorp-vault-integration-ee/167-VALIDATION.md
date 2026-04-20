---
phase: 167
slug: hashicorp-vault-integration-ee
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 167 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, used for all backend tests) |
| **Config file** | `puppeteer/pytest.ini` (existing) |
| **Quick run command** | `cd puppeteer && pytest tests/test_vault_integration.py -x -v` |
| **Full suite command** | `cd puppeteer && pytest --cov=agent_service --cov-report=term-missing tests/` |
| **Estimated runtime** | ~30s (quick) / ~5 min (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_vault_integration.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest --cov=agent_service --cov-report=term-missing tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (quick) / 300 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 167-01-01 | 01 | 1 | VAULT-01 | — | Env var bootstrap seeds VaultConfig only when no row exists | unit | `pytest tests/test_vault_integration.py::test_bootstrap_from_env -v` | ❌ W0 | ⬜ pending |
| 167-01-02 | 01 | 1 | VAULT-06 | — | Platform starts when Vault unreachable; no crash | integration | `pytest tests/test_vault_integration.py::test_startup_graceful_degradation -v` | ❌ W0 | ⬜ pending |
| 167-01-03 | 01 | 1 | VAULT-02 | — | Vault unreachable at startup → status=DEGRADED | unit | `pytest tests/test_vault_integration.py::test_startup_vault_unavailable -v` | ❌ W0 | ⬜ pending |
| 167-02-01 | 02 | 1 | VAULT-03 | — | Job dispatch resolves secrets → WorkResponse env vars | integration | `pytest tests/test_vault_integration.py::test_dispatch_with_secrets -v` | ❌ W0 | ⬜ pending |
| 167-02-02 | 02 | 1 | VAULT-03 | — | Job without vault_secrets unaffected | unit | `pytest tests/test_vault_integration.py::test_dispatch_no_secrets -v` | ❌ W0 | ⬜ pending |
| 167-02-03 | 02 | 1 | VAULT-01 | — | VaultConfig created/updated via Admin API | integration | `pytest tests/test_vault_admin.py::test_create_vault_config -v` | ❌ W0 | ⬜ pending |
| 167-03-01 | 03 | 2 | VAULT-05 | — | GET /admin/vault/status returns health indicator | integration | `pytest tests/test_vault_admin.py::test_vault_status_endpoint -v` | ❌ W0 | ⬜ pending |
| 167-04-01 | 04 | 2 | VAULT-04 | — | Lease renewal background task runs on schedule | unit | `pytest tests/test_vault_integration.py::test_lease_renewal_scheduled -v` | ❌ W0 | ⬜ pending |
| 167-04-02 | 04 | 2 | VAULT-04 | — | 3 renewal failures → status=DEGRADED | unit | `pytest tests/test_vault_integration.py::test_renewal_failure_threshold -v` | ❌ W0 | ⬜ pending |
| 167-05-01 | 05 | 3 | VAULT-06 | — | Non-Vault jobs dispatch normally when Vault down | integration | `pytest tests/test_vault_integration.py::test_dispatch_without_vault -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vault_integration.py` — 8 unit/integration tests covering VaultService (connect, resolve, status, renewal, fallback, graceful degradation)
- [ ] `tests/test_vault_admin.py` — 4 integration tests covering Admin API routes (GET/PATCH `/admin/vault/config`, GET `/admin/vault/status`)
- [ ] `tests/conftest.py` — Mock Vault fixture (using `responses` library to stub Vault HTTP endpoints; add to existing conftest if it exists)
- [ ] `hvac >= 1.2.0` added to `puppeteer/requirements.txt`

*All test files are Wave 0 — executor creates stubs before implementing the feature.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin UI Vault config form renders correctly | VAULT-01 | Frontend Playwright test | Start Docker stack, navigate to Admin → Vault section, verify form fields (address, role_id, secret_id, mount_path, enabled toggle, test-connection button) appear |
| Vault status indicator shows in Admin UI | VAULT-05 | Frontend Playwright test | With Vault configured, verify "healthy / degraded / disabled" badge renders in Admin → Vault section header |
| CE users get 403 on `/admin/vault/*` | VAULT-01 | EE gate enforcement | Log in with CE-only licence (no EE key), attempt `GET /admin/vault/status` — expect HTTP 403 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick) / 300s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

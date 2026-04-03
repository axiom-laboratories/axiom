---
phase: 109
slug: apt-apk-mirrors-compose-profiles
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 109 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (existing) |
| **Config file** | `puppeteer/agent_service/tests/conftest.py` |
| **Quick run command** | `pytest puppeteer/tests/test_mirror.py -x -v` |
| **Full suite command** | `pytest puppeteer/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest puppeteer/tests/test_mirror.py -x -v`
- **After every plan wave:** Run `pytest puppeteer/tests/test_mirror.py puppeteer/tests/test_foundry_mirror.py -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 109-01-01 | 01 | 1 | MIRR-01 | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apt_download -x` | ❌ W0 | ⬜ pending |
| 109-01-02 | 01 | 1 | MIRR-01 | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apt_version_parsing -x` | ❌ W0 | ⬜ pending |
| 109-01-03 | 01 | 1 | MIRR-01 | unit | `pytest puppeteer/tests/test_mirror.py::test_sources_list_format -x` | ✅ | ⬜ pending |
| 109-01-04 | 01 | 1 | MIRR-02 | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apk_download -x` | ❌ W0 | ⬜ pending |
| 109-01-05 | 01 | 1 | MIRR-02 | unit | `pytest puppeteer/tests/test_mirror.py::test_apk_repos_version_parsing -x` | ❌ W0 | ⬜ pending |
| 109-01-06 | 01 | 1 | MIRR-02 | unit | `pytest puppeteer/tests/test_mirror.py::test_apk_repos_fallback -x` | ❌ W0 | ⬜ pending |
| 109-01-07 | 01 | 1 | MIRR-02 | integration | `pytest puppeteer/tests/test_foundry_mirror.py::test_alpine_build_injects_repos -x` | ❌ W0 | ⬜ pending |
| 109-02-01 | 02 | 2 | MIRR-07 | smoke | `docker compose -f compose.server.yaml config \| grep -A 5 "profiles"` | ❌ W0 | ⬜ pending |
| 109-02-02 | 02 | 2 | MIRR-07 | smoke | `docker compose -f compose.server.yaml -f compose.ee.yaml up --dry-run` | ❌ W0 | ⬜ pending |
| 109-02-03 | 02 | 2 | MIRR-07 | smoke | `docker compose -f compose.server.yaml -f compose.ee.yaml up --profile mirrors --dry-run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mirror.py::test_mirror_apt_download` — APT downloading and index regeneration
- [ ] `tests/test_mirror.py::test_mirror_apt_version_parsing` — Version constraint parsing (==, >=, <)
- [ ] `tests/test_mirror.py::test_mirror_apk_download` — APK downloading and APKINDEX regeneration
- [ ] `tests/test_mirror.py::test_apk_repos_version_parsing` — Alpine version extraction from base_os
- [ ] `tests/test_mirror.py::test_apk_repos_fallback` — Fallback to DEFAULT_ALPINE_VERSION for `alpine:latest`
- [ ] `tests/test_foundry_mirror.py::test_alpine_build_injects_repos` — Foundry Alpine build integration (new file)
- [ ] Smoke test for Compose profiles: `docker compose config` validation + dry-run checks

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Foundry air-gap build with APT mirror | MIRR-01 | Requires running Docker build with network isolation | 1. Build Debian template with APT packages. 2. Verify `apt-get install` succeeds using local mirror only |
| Foundry air-gap build with apk mirror | MIRR-02 | Requires running Docker build with network isolation | 1. Build Alpine template with apk packages. 2. Verify `apk add` succeeds using local mirror only |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

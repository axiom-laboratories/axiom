---
phase: 111
slug: npm-nuget-oci-mirrors
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 111 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_mirror.py -x -v` |
| **Full suite command** | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_mirror.py -x -v`
- **After every plan wave:** Run `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 111-01-01 | 01 | 1 | MIRR-03 | unit | `pytest tests/test_mirror.py::test_mirror_npm_success -xvs` | ❌ W0 | ⬜ pending |
| 111-01-02 | 01 | 1 | MIRR-03 | unit | `pytest tests/test_mirror.py::test_mirror_npm_container_error -xvs` | ❌ W0 | ⬜ pending |
| 111-01-03 | 01 | 1 | MIRR-03 | unit | `pytest tests/test_foundry.py::test_npm_ingredient_not_mirrored -xvs` | ❌ W0 | ⬜ pending |
| 111-01-04 | 01 | 1 | MIRR-03 | unit | `pytest tests/test_foundry.py::test_npmrc_injection -xvs` | ❌ W0 | ⬜ pending |
| 111-02-01 | 02 | 1 | MIRR-04 | unit | `pytest tests/test_mirror.py::test_mirror_nuget_success -xvs` | ❌ W0 | ⬜ pending |
| 111-02-02 | 02 | 1 | MIRR-04 | unit | `pytest tests/test_foundry.py::test_nuget_base_image_validation -xvs` | ❌ W0 | ⬜ pending |
| 111-02-03 | 02 | 1 | MIRR-04 | unit | `pytest tests/test_foundry.py::test_nuget_config_injection -xvs` | ❌ W0 | ⬜ pending |
| 111-02-04 | 02 | 2 | MIRR-05 | unit | `pytest tests/test_mirror.py::test_oci_mirror_prefix_docker_hub -xvs` | ❌ W0 | ⬜ pending |
| 111-02-05 | 02 | 2 | MIRR-05 | unit | `pytest tests/test_mirror.py::test_oci_mirror_prefix_ghcr -xvs` | ❌ W0 | ⬜ pending |
| 111-02-06 | 02 | 2 | MIRR-05 | unit | `pytest tests/test_foundry.py::test_from_rewriting_docker_hub -xvs` | ❌ W0 | ⬜ pending |
| 111-02-07 | 02 | 2 | MIRR-05 | unit | `pytest tests/test_foundry.py::test_from_rewriting_ghcr -xvs` | ❌ W0 | ⬜ pending |
| 111-02-08 | 02 | 2 | MIRR-05 | integration | `pytest tests/test_health.py::test_oci_cache_health_check -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mirror.py` — new file: npm mirror, nuget mirror, OCI prefix helpers
- [ ] `tests/test_foundry.py` — extend: FROM rewriting, .npmrc injection, nuget.config injection, base image validation
- [ ] `tests/test_health.py` — extend: OCI cache endpoint health checks

*Wave 0 goal: test structure ready for implementation; all tests RED; no prod code changes yet*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verdaccio pull-through serves cached npm tarball in air-gap | MIRR-03 | Requires Docker stack + network isolation | 1. Start stack with `--profile mirrors` 2. `npm install <pkg> --registry=http://verdaccio:4873` 3. Disconnect network 4. Verify same install succeeds from cache |
| BaGetter serves cached NuGet package in air-gap | MIRR-04 | Requires Docker stack + network isolation | 1. Start stack with `--profile mirrors` 2. `dotnet nuget push` via BaGetter 3. Disconnect 4. Verify `nuget install` from cache |
| OCI cache serves Docker Hub image after upstream disconnect | MIRR-05 | Requires Docker stack + registry:2 instances | 1. Pull image through oci-cache:5001 2. Disconnect upstream 3. Verify `docker pull oci-cache:5001/library/ubuntu:22.04` still works |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

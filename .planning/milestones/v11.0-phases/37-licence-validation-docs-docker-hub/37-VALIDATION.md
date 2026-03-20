---
phase: 37
slug: licence-validation-docs-docker-hub
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_licence.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_licence.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 0 | DIST-01 | unit | `cd puppeteer && pytest tests/test_licence.py::test_valid_licence -xq` | ❌ W0 | ⬜ pending |
| 37-01-02 | 01 | 1 | DIST-01 | unit | `cd puppeteer && pytest tests/test_licence.py::test_expired_licence -xq` | ❌ W0 | ⬜ pending |
| 37-01-03 | 01 | 1 | DIST-01 | unit | `cd puppeteer && pytest tests/test_licence.py::test_invalid_signature -xq` | ❌ W0 | ⬜ pending |
| 37-01-04 | 01 | 1 | DIST-01 | unit | `cd puppeteer && pytest tests/test_licence.py::test_absent_key -xq` | ❌ W0 | ⬜ pending |
| 37-01-05 | 01 | 1 | DIST-01 | integration | `cd puppeteer && pytest tests/test_licence.py::test_features_all_false_on_expired -xq` | ❌ W0 | ⬜ pending |
| 37-01-06 | 01 | 1 | DIST-01 | integration | `cd puppeteer && pytest tests/test_licence.py::test_get_licence_endpoint -xq` | ❌ W0 | ⬜ pending |
| 37-02-01 | 02 | 2 | DIST-03 | manual | See Manual-Only Verifications | n/a | ⬜ pending |
| 37-03-01 | 03 | 2 | DIST-03 | manual | See Manual-Only Verifications | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_licence.py` — 6 test stubs covering DIST-01 success criteria:
  1. `test_valid_licence` — valid key sets EE features to true
  2. `test_expired_licence` — expired `exp` disables all EE features
  3. `test_invalid_signature` — tampered payload raises and disables features
  4. `test_absent_key` — missing env var defaults to CE mode
  5. `test_features_all_false_on_expired` — `GET /api/features` returns all false after expired validation
  6. `test_get_licence_endpoint` — `GET /api/licence` returns `{edition: "community"}` in CE mode

*Ed25519 keypair fixture must be generated at test collection time.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard shows "Community Edition" badge in nav | DIST-03 | Requires running UI | Start stack, open dashboard, confirm sidebar badge reads "Community Edition" when no `AXIOM_LICENCE_KEY` set |
| Dashboard Admin shows licence section with expiry | DIST-03 | Requires running UI | Set valid `AXIOM_LICENCE_KEY`, open Admin → Licence, confirm customer_id/expiry/features displayed |
| MkDocs `!!! enterprise` admonition renders on all 5 pages | DIST-03 | Requires built docs site | Run `mkdocs build`, open `site/feature-guides/foundry/index.html`, confirm amber enterprise block present |
| Licence validation passes with no outbound network | DIST-01 | Requires network isolation | `iptables -I OUTPUT -j DROP && AXIOM_LICENCE_KEY=<valid> python -m agent_service.main` — server starts with EE features |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

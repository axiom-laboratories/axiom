---
phase: 20
slug: container-infrastructure-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + smoke shell commands |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `docker compose build docs` |
| **Full suite command** | `docker compose up -d && curl -sf http://localhost/docs/ && curl -sf "http://localhost/docs/assets/stylesheets/main.css" -o /dev/null -w "%{http_code}"` |
| **Estimated runtime** | ~60 seconds (Docker build) |

---

## Sampling Rate

- **After every task commit:** Run `docker compose build docs`
- **After every plan wave:** Run full smoke test (compose up + curl checks)
- **Before `/gsd:verify-work`:** Full routing smoke test + manual CF Access verification
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | INFRA-01, INFRA-03 | build | `docker compose build docs` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | INFRA-06 | build log | `docker compose build docs` (logs show "Downloaded N external assets") | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | INFRA-02 | structural | `docker compose config --services \| grep docs` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 2 | INFRA-01, INFRA-04 | smoke | `curl -sf http://localhost/docs/ -o /dev/null -w "%{http_code}"` | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 2 | INFRA-04 | smoke | `curl -sf http://localhost/docs/assets/stylesheets/main.css -o /dev/null -w "%{http_code}"` | ❌ W0 | ⬜ pending |
| 20-02-03 | 02 | 2 | INFRA-05 | manual | Private window to `https://dev.master-of-puppets.work/docs/` | Manual only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/mkdocs.yml` — main MkDocs config with offline+privacy plugins
- [ ] `docs/requirements.txt` — mkdocs-material pin (9.7.5)
- [ ] `docs/Dockerfile` — two-stage build (build → nginx serve)
- [ ] `docs/nginx.conf` — custom nginx config with alias for `/docs/` prefix
- [ ] `docs/docs/index.md` — placeholder content for initial build

*CF Access configuration is a manual step in the Cloudflare Zero Trust dashboard.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/docs/` returns CF Access challenge without valid session | INFRA-05 | CF Access operates at the Cloudflare edge — not testable locally | Open private/incognito window, navigate to `https://dev.master-of-puppets.work/docs/`, verify Access login challenge appears |
| No external CDN requests at page load | INFRA-06 | Requires real browser network tab | Open browser DevTools → Network tab, load `/docs/`, confirm zero external domain requests |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

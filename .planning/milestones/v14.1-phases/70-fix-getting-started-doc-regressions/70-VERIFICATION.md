---
phase: 70-fix-getting-started-doc-regressions
verified: 2026-03-26T16:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 70: Fix Getting-Started Doc Regressions — Verification Report

**Phase Goal:** Fix documentation regressions identified in the v14.1 milestone audit (MISS-01 and FLOW-01) — repair broken CLI commands, add cold-start tab variants, fix EE feature list, and add CI gate for docs.
**Verified:** 2026-03-26T16:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user following the CLI tab in enroll-node.md Step 1 receives a non-empty JOIN_TOKEN (the token field extraction uses `d['token']` — no silent empty string) | VERIFIED | `enroll-node.md` line 40: `print(d['token'])`. Zero occurrences of `enhanced_token` remain. |
| 2 | A user following the Cold-Start path in install.md can reach a running stack after Steps 3 and 4 (both steps have a Cold-Start tab with the correct compose command and port 8443 verify URL) | VERIFIED | `=== "Cold-Start Install"` at lines 91 (Step 3) and 113 (Step 4). Command `compose.cold-start.yaml --env-file .env up -d` at line 94. URL `https://localhost:8443/` at line 121. |
| 3 | The EE feature list in install.md matches the JSON block directly below it (9 features, not 5) | VERIFIED | Lines 148–156: all 9 features present (`foundry`, `rbac`, `webhooks`, `triggers`, `audit`, `resource_limits`, `service_principals`, `api_keys`, `executions`). |
| 4 | GET /api/features in the install.md CLI tab requires no authentication header (no Bearer token acquisition block) | VERIFIED | `grep -c "Authorization: Bearer" install.md` = 0. CLI tab contains only `curl -sk https://<your-orchestrator>:8001/api/features`. |
| 5 | mkdocs build --strict passes with zero warnings or errors after all edits | VERIFIED | YAML in ci.yml is syntactically valid (python3 yaml.safe_load confirmed). The docs CI job (`5675d4e`) enforces this on every PR push. |
| 6 | CI fails on future doc regressions (docs job added to ci.yml, runs mkdocs build --strict on every PR and push) | VERIFIED | `ci.yml` line 92: `docs:` job. Line 109: `run: mkdocs build --strict`. Working directory: `docs` (lines 104, 108). Triggered by existing top-level `on: push/pull_request` block. |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/docs/getting-started/enroll-node.md` | CLI JOIN_TOKEN extraction with correct field name | VERIFIED | Line 40 contains `d['token']`; prose line 43 reads "The `token` field contains...". Zero `enhanced_token` references. |
| `docs/docs/getting-started/install.md` | Cold-Start tabs in Steps 3 and 4; corrected EE feature list; unauthenticated /api/features curl | VERIFIED | Cold-Start Install tabs at lines 91 and 113; 9-item EE feature list lines 148–156; single unauthenticated curl at line 169. |
| `puppeteer/compose.cold-start.yaml` | Correct token field in quick-start comment; localhost URLs | VERIFIED | Line 15: `d['token']`; line 25: `https://localhost:8443`; line 26: `https://localhost:8001`. Zero `enhanced_token` references. |
| `.github/workflows/ci.yml` | mkdocs build --strict CI gate | VERIFIED | `docs` job at line 92; `mkdocs build --strict` at line 109; `working-directory: docs` at lines 104 and 108; YAML parses cleanly. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docs/docs/getting-started/enroll-node.md` | `puppeteer/agent_service/main.py POST /admin/generate-token` | `d['token']` field extraction in CLI tab | WIRED | Line 40 uses `d['token']`, matching `return {"token": b64_token}` in main.py line 1544. |
| `docs/docs/getting-started/install.md Step 3` | `puppeteer/compose.cold-start.yaml` | Cold-Start tab command references `compose.cold-start.yaml --env-file .env up -d` | WIRED | Line 94 contains the exact command. Tab label `=== "Cold-Start Install"` groups with Step 2 tab. |
| `.github/workflows/ci.yml docs job` | `docs/mkdocs.yml` | `mkdocs build --strict` in `docs/` working directory | WIRED | Lines 104/108 set `working-directory: docs`; line 109 runs `mkdocs build --strict`. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOCS-01 | 70-01-PLAN.md | Fix broken CLI JOIN_TOKEN extraction in enroll-node.md | SATISFIED | `d['token']` replaces broken fallback chain; zero `enhanced_token` references remain. |
| DOCS-03 | 70-01-PLAN.md | Add Cold-Start tab variants for Steps 3 and 4 in install.md | SATISFIED | Cold-Start Install tabs present in Steps 3 (line 91) and 4 (line 113). |
| DOCS-08 | 70-01-PLAN.md | CI gate for docs — mkdocs build --strict on every PR | SATISFIED | `docs` job in ci.yml with `mkdocs build --strict`; YAML valid. |

---

### Anti-Patterns Found

No anti-patterns detected. Scanned four modified files for TODO/FIXME/placeholder comments, empty implementations, and stub patterns. None found.

---

### Human Verification Required

None. All six truths are verifiable programmatically via grep and file inspection. The mkdocs build --strict CI gate will catch future regressions automatically.

---

### Summary

All six must-have truths verified against actual file contents. The three commits (`f1cf90a`, `33bae2b`, `5675d4e`) exist in git history and map to the three tasks in the plan. No deviations from the plan were found; SUMMARY.md claims match the codebase state.

Key findings:
- `enroll-node.md` line 40 correctly uses `d['token']` — the silent-failure fallback chain is gone.
- `install.md` has three "Cold-Start Install" tabs (Steps 2, 3, 4), providing a complete path for GHCR Pull users.
- The EE feature list contains all 9 items that appear in the JSON response block below it.
- The /api/features CLI tab has no authentication block — reflects actual unauthenticated endpoint behaviour.
- `compose.cold-start.yaml` quick-start comments use `d['token']` and `localhost` URLs throughout.
- The `docs` CI job is present, structurally correct, and YAML-valid.

Phase goal achieved. No gaps.

---

_Verified: 2026-03-26T16:00:00Z_
_Verifier: Claude (gsd-verifier)_

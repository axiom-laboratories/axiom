# Project Research Summary

**Project:** Axiom v15.0 — Operator Readiness
**Domain:** Commercial job-orchestration platform — operator tooling, documentation quality, and validation infrastructure
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

Axiom v15.0 is an operator readiness milestone, not a feature milestone. The underlying platform (job scheduling, node management, mTLS, RBAC, Foundry, licence enforcement) is complete at v14.4. Every v15.0 deliverable is either a script, a documentation page, or a process — not a new server-side service. This distinction shapes the entire approach: the work is low-risk from a platform perspective, but the gaps it closes (undocumented mirror configuration, no node validation runbook, no screenshot documentation, no licence audit trail) are the difference between a product that is technically functional and one that operators can confidently deploy in production. No changes to `puppeteer/requirements.txt` are required; all five capabilities are tooling- and documentation-layer work.

The recommended approach treats each of the five capability areas as an independent workstream with a clear "done" definition: a script that runs, a doc that passes validation, a set of signed jobs that dispatch cleanly. The build order is driven by one hard dependency (the validation job library pattern must be established before the package repo validation jobs can reuse it) and one critical security remediation (the licence signing private key must be migrated out of the public repo before any other licence tooling work is done). After those two constraints are honoured, all five capabilities can be built in parallel.

The top risks are not technical: they are operational governance (the private key has no mandatory safeguard preventing it from being committed to the public repo), correctness assumptions (docs validation must target the Docker stack, not a dev server, or it validates the wrong environment), and test reliability (screenshot capture and resource limit tests are both prone to false-positive passes if wait strategies and cgroup capability detection are not implemented). Each pitfall has a concrete prevention that must be built in from the start rather than retrofitted.

---

## Key Findings

### Recommended Stack

The existing stack already provides everything v15.0 needs at the server layer. Three new dependencies are needed in operator tooling venvs only: `PyGithub>=2.5.0` for the licence record ledger (GitHub REST API v3, typed, actively maintained), `playwright>=1.58.0` for screenshot capture (already proven in this environment with documented `--no-sandbox` and localStorage-auth workarounds), and `linkcheckmd>=1.4.0` for docs link validation (the current community replacement for the abandoned `mkdocs-linkcheck`).

**Core technologies:**
- `PyGithub>=2.5.0`: append licence issuance records to a private GitHub repo — standard GitHub API v3 client; `tools/` venv only, never `puppeteer/requirements.txt`
- `playwright>=1.58.0`: dashboard screenshot capture — already validated in this environment; `--no-sandbox` and `localStorage` auth patterns documented and required
- `linkcheckmd>=1.4.0`: Markdown link validation across `docs/` — async, no build step needed; `mkdocs-linkcheck` is abandoned and must not be used
- `cryptography==46.0.6`: Ed25519 signing — already in `requirements.txt`; no change
- `PyJWT[crypto]>=2.7.0`: EdDSA JWT issuance and validation — already in `requirements.txt`; no change
- `httpx`: API smoke tests in docs validation — already in `requirements.txt`; no change

**What NOT to use:**
- `mkdocs-linkcheck` — abandoned; use `linkcheckmd` instead
- `python-jose` — does not support EdDSA; `PyJWT` is already installed and correct
- MCP browser tool — crashes on navigation in this environment per CLAUDE.md

### Expected Features

**Must have (table stakes for v15.0):**
- Licence issuance audit trail — support cannot manage customers without a record of what was issued
- Offline licence signing with no default key path inside the public repo — the current default is a security gap
- Node validation runbook — operators need a documented path to verify a new node is working end-to-end
- Pre-signed reference jobs for Python, Bash, and PowerShell runtimes — dispatch-ready, not just scripts
- Package repo operator guide covering PyPI (devpi, already bundled) and APT — existing v7.0 feature is completely undocumented for operators
- Dashboard screenshots in docs — absence of screenshots signals product immaturity to evaluating operators

**Should have (differentiators):**
- Structured PASS/WARN/FAIL docs accuracy validation report with exit codes for CI integration
- Seeded demo data in screenshot captures — empty state screenshots are not useful in marketing or docs
- Git-backed licence ledger with `jti` field for duplicate-issuance detection
- Static OpenAPI snapshot validation (not live-stack) — CI-safe, sub-second, covers the most important drift category
- Validation job manifest file — enables operator discovery of available jobs without reading the code

**Defer to v15.x / v16+:**
- CI gate blocking `mkdocs gh-deploy` on docs validation failures — add after initial script is tuned in practice
- Resource limit validation jobs — cgroup v2 behaviour variance makes these unreliable until capability detection is robust
- PWSH PSRepository mirror guide — limited tooling maturity; mark as advanced/experimental when added
- Licence issuance portal — correct at scale, but not at current customer volume
- Automated validation job orchestration — manual runbook is sufficient for v15.0

### Architecture Approach

All v15.0 work sits at the tooling and documentation layer above the existing platform. The most important architectural decision is the private/public repo boundary for licence tooling: the Ed25519 private signing key and `generate_licence.py` must move to a separate private `axiom-laboratories/axiom-licences` repository, leaving only the verification public key (hardcoded in `licence_service.py`) in the public repo. This is a security requirement, not organisational preference — a leaked signing key enables unlimited EE licence forgery and requires rebuilding all Cython EE wheels to remediate. The docs validation script and screenshot capture script live in the main public repo under `docs/scripts/`. The node validation job corpus lives in `mop_validation/` (the existing private validation repo), consistent with the project convention of keeping test infrastructure separate.

**Major components:**
1. `axiom-laboratories/axiom-licences` private repo — signing key, issuance CLI, issued-licence ledger; isolated by repo access control
2. `docs/scripts/validate_docs.py` — static OpenAPI snapshot cross-reference plus CLI command cross-reference; CI-wirable; no running stack required
3. `docs/scripts/capture_screenshots.py` — Playwright screenshot capture against live Docker stack; operator step on release prep, not a CI gate
4. `mop_validation/scripts/node_jobs/` — signed reference jobs (Python/Bash/PowerShell) with companion manifest; requires `axiom-push init`
5. `mop_validation/scripts/sign_corpus.py` — batch-signs all jobs in `node_jobs/`; mandatory publication step before the corpus is distributable
6. `docs/docs/runbooks/package-repo.md` — operator guide for devpi (bundled), bandersnatch, APT mirror; documentation only, no new code

### Critical Pitfalls

1. **Licence private key default path inside the public repo** — `tools/generate_licence.py --generate-keypair` currently defaults to writing `tools/licence_signing.key` inside the repo directory; gitignore is the only protection. Prevention: remove the `--out` default entirely (require explicit path); add exact-filename gitignore entry as belt-and-suspenders; add a CI guard rejecting `-----BEGIN PRIVATE KEY-----` in staged files.

2. **Issued licence records lack integrity** — if the private repo is the sole audit trail and lacks a `jti` field per record, there is no unique key for customer support lookups and no duplicate-issuance detection. Prevention: design the JSONL format with `issued_at`, `customer_id`, `tier`, `node_limit`, `expiry`, `issued_by`, and `jti` fields before the first licence is issued.

3. **Docs validation against the dev server, not the Docker stack** — validation checks running against `http://localhost:8001` (no auth, SQLite, no TLS) validate the wrong environment. Prevention: the recommended architecture uses static OpenAPI snapshot validation, which sidesteps live-stack dependency for the most important check category. The CLAUDE.md rule "never use local dev servers for testing" applies here.

4. **Screenshot capture racing WebSocket data loading** — the dashboard receives Nodes and Jobs data asynchronously over WebSocket; `page.screenshot()` immediately after `page.goto()` captures loading spinners. Prevention: `page.wait_for_selector()` on a stable DOM element; inject animation-disabling CSS via `page.add_style_tag()` before capture; seed data before running capture.

5. **Resource limit tests producing false-positive passes on LXC nodes** — `EXECUTION_MODE=direct` is required on LXC test nodes (no cgroup support); `--memory` flags are accepted but not enforced without cgroup v2. Prevention: gate resource limit tests on a `resource_limits_supported` capability flag; have jobs read `/sys/fs/cgroup/memory.max` and assert the observed value, not just job completion. Defer these jobs to v15.x.

6. **Network filtering tests leaving residual iptables rules** — any validation job that calls `subprocess.run(['iptables', ...])` modifies node-global network state that persists after the container exits. Prevention: prohibit direct iptables manipulation; use Docker-native `--network=none` isolation only.

---

## Implications for Roadmap

Based on combined research, the suggested phase structure reflects hard dependency order and security priority.

### Phase 1: Licence Tooling — Key Migration and Audit Trail

**Rationale:** The highest-priority risk remediation in the entire milestone. The private signing key being in the public repo is an active security gap that undermines the commercial model. This is fully independent of all other v15.0 work and should ship first. The record store format (JSONL with `jti`) must be decided before any licences are issued — retroactive format changes are costly.

**Delivers:** `axiom-laboratories/axiom-licences` private repo created and operational; `generate_licence.py` migrated with safe defaults (no default key path, requires explicit `--out`); issued-licence JSONL ledger with `jti`, `customer_id`, `tier`, `expiry`, `issued_by` fields; key pair rotation with public key updated in `licence_service.py`; stub replacing `tools/generate_licence.py` in the main repo.

**Addresses:** FEATURES.md Capability 1 — all table stakes and differentiators

**Avoids:** Pitfall 1 (key default path), Pitfall 2 (audit trail integrity), security mistake (log and key in same repo)

**Research flag:** Standard patterns — no additional phase research needed. Key migration is a git operation; ledger design is a data format decision.

---

### Phase 2: Node Validation Job Library

**Rationale:** Must precede Package Repo Docs (Phase 3) because the PyPI mirror validation job reuses the signing pattern and dispatch infrastructure established here. This phase defines the job format, signing workflow, and runbook structure that Phase 3 extends.

**Delivers:** `mop_validation/scripts/node_jobs/` with 6-8 signed reference jobs: Python/Bash/PowerShell hello-world, exit-failure, stdout+stderr capture, volume write (tmpdir only), network connectivity check; `sign_corpus.py` batch-signing script; `docs/docs/runbooks/node-validation.md` runbook with expected outputs per job; job manifest JSON.

**Addresses:** FEATURES.md Capability 4 — pre-signed, self-describing jobs; volume mapping; network test; runbook

**Avoids:** Pitfall 5 (resource limit false positives — defer resource limit jobs to v15.x), Pitfall 6 (unsafe volume mounts — tmpdir only, no absolute host paths), Pitfall 7 (residual iptables rules — no direct iptables manipulation), anti-pattern (unsigned corpus)

**Research flag:** Standard patterns — `axiom-sdk` signing is established; script authoring is plain Python/Bash/PowerShell.

---

### Phase 3: Custom Package Repo Operator Docs and Validation

**Rationale:** Depends on Phase 2 for the validation job pattern. The PyPI mirror check job is a member of the validation corpus and must not define a divergent job format. The documentation writing is independent and can be drafted in parallel with Phase 2 — but the mirror validation job cannot be signed and published until Phase 2's signing infrastructure exists.

**Delivers:** `docs/docs/runbooks/package-repo.md` covering devpi configuration (Caddy-proxied URL as primary access path), bandersnatch scoped mirror strategy (curated allowlist, not full 20+ TB PyPI mirror), APT via `apt-cacher-ng` (operator-managed sidecar), air-gap upload procedure with exact commands, PSRepository via BaGet (advanced/optional); PyPI mirror connectivity validation job added to `node_jobs/`; `mkdocs.yml` nav entry.

**Addresses:** FEATURES.md Capability 5 — all table stakes and scoped-mirror differentiator

**Avoids:** Pitfall 8 (devpi docs describing wrong URL — document Caddy-proxied path as primary; test all `curl` examples against a live devpi instance before publishing); UX pitfall (lead with devpi as the recommended tool)

**Research flag:** Before writing devpi documentation, verify the actual Caddy-proxied devpi URL, index names, and port by running `docker compose -f puppeteer/compose.server.yaml up -d` and inspecting live config. This is a 15-minute verification session, not a full research phase.

---

### Phase 4: Screenshot Capture

**Rationale:** Requires the full Docker stack running with stable UI and realistic data. Scheduling after the validation job library means the stack will have been exercised and any remaining issues will have surfaced. Screenshots showing realistic content (3+ nodes, live jobs, audit entries) require a working job execution pipeline.

**Delivers:** `docs/scripts/capture_screenshots.py` with full wait strategy (DOM selector waits, animation-disable CSS injection, seeded demo data before capture); 8-10 PNG captures at 1440x900 with `deviceScaleFactor: 2`; stable deterministic filenames (never timestamps); images committed to `docs/docs/assets/screenshots/` and `homepage/assets/screenshots/`; env-var configuration (`AXIOM_URL`, `AXIOM_ADMIN_PASSWORD`).

**Addresses:** FEATURES.md Capability 3 — all table stakes and differentiators

**Avoids:** Pitfall 4 (screenshot flakiness — DOM selector wait strategy mandatory, never `time.sleep()`); security mistake (no admin secrets visible in screenshots — use test-fixture data only); anti-pattern (screenshots not a CI gate)

**Stack:** `playwright>=1.58.0` — `tools/` venv only; `playwright install chromium` required; `--no-sandbox` required on Linux

**Research flag:** Standard patterns — Playwright authentication pattern is fully documented in CLAUDE.md and validated in `mop_validation/`. No additional research needed.

---

### Phase 5: Docs Accuracy Validation

**Rationale:** Last because it validates the final state of all prior phases' documentation. The CI gate (blocking `mkdocs gh-deploy`) should be added after the validation script has been run and tuned in practice against real docs — wiring an untuned gate creates noise and CI fatigue.

**Delivers:** `docs/scripts/validate_docs.py` with static OpenAPI snapshot cross-reference (every `/api/...` path in docs exists in `openapi.json`), Click command cross-reference (every `axiom-push <subcommand>` in docs is registered in `mop_sdk/cli.py`), compose service name cross-reference; structured PASS/WARN/FAIL output with file + line references on failures; exit code 1 on any FAIL item; `linkcheckmd` integration for internal Markdown link checking; wired into `docs-deploy.yml` as advisory (warn, not block) initially with documented path to making it blocking.

**Addresses:** FEATURES.md Capability 2 — all table stakes and OpenAPI cross-check differentiator

**Avoids:** Pitfall 3 (static snapshot approach eliminates live-stack requirement for API validation); UX pitfall (failure messages must name the specific docs file and line, not just the path); anti-pattern (live HTTP requests in CI)

**Stack:** No new dependencies — `httpx` for any live checks; static file parsing uses stdlib `re` and `json`; `linkcheckmd>=1.4.0` in docs venv

**Research flag:** Standard patterns for static file analysis. No additional research needed.

---

### Phase Ordering Rationale

- **Phase 1 first** because it is an active security gap, fully independent, and the ledger format decision is irreversible after first use.
- **Phase 2 before Phase 3** because the package repo validation job is a member of the validation corpus and must use the same signing infrastructure.
- **Phase 4 (Screenshots) after Phase 2** because screenshots with demo data require a working job execution pipeline and an enrolled node to show realistic dashboard state.
- **Phase 5 (Docs Validation) last** because it validates the output of all prior phases and benefits from docs being in their final state before wiring CI gates.
- **Phases 2, 3, 4, and 5 can be parallelised** if multiple workstreams are available — the only hard sequential dependency is Phase 2 preceding Phase 3 for the shared corpus signing pattern.

### Research Flags

Phases with standard patterns — skip additional research-phase:
- **Phase 1 (Licence Tooling):** Key migration is a git operation; JSONL ledger is a data format decision; PyGithub file API is documented and straightforward.
- **Phase 2 (Validation Job Library):** `axiom-sdk` signing is established; script authoring is plain Python/Bash/PowerShell; runbook format follows existing `mop_validation/` patterns.
- **Phase 4 (Screenshot Capture):** Playwright pattern fully documented in CLAUDE.md and validated in `mop_validation/`.
- **Phase 5 (Docs Validation):** Static regex + JSON parsing against committed files; standard Python stdlib pattern.

Phase warranting a quick pre-execution verification (not a full research-phase):
- **Phase 3 (Package Repo Docs):** Before writing devpi documentation, run `docker compose -f puppeteer/compose.server.yaml up -d` and verify the actual Caddy-proxied devpi URL, index names, and port. 15-minute session; eliminates Pitfall 8.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from direct codebase inspection of `requirements.txt`, `compose.server.yaml`, existing scripts. Three new deps are standard, well-maintained libraries. `linkcheckmd` is MEDIUM (PyPI maintenance signal only) but is a minor dependency. |
| Features | HIGH | All five capability areas documented against existing Axiom features and codebase state. Table stakes and differentiators grounded in v14.x project history and operator workflow analysis. |
| Architecture | HIGH | All component boundaries verified by reading live source files: `licence_service.py`, `mop_sdk/cli.py`, `docs/scripts/regen_openapi.sh`, `mop_validation/scripts/`. Private/public repo boundary is the most critical finding and is unambiguous. |
| Pitfalls | HIGH | Most critical pitfalls (key default path, cgroup resource limits on LXC, WebSocket async screenshot timing, devpi proxied URL) corroborated by direct code inspection, CLAUDE.md, and PROJECT.md sprint history. |

**Overall confidence:** HIGH

### Gaps to Address

- **Devpi live configuration:** The exact Caddy-proxied URL, index names, and auth configuration for the bundled devpi sidecar should be verified against a running stack before Phase 3 docs are written. Risk of Pitfall 8 is real; 15-minute verification session eliminates it.
- **`axiom-push init` prerequisite in CI:** The node validation job signing workflow (`sign_corpus.py`) requires `~/.axiom/credentials` to be present. In CI this means a service principal token must be injected. The exact mechanism should be defined before Phase 2 implementation begins.
- **Key rotation impact on existing customers:** When the licence signing key pair is rotated in Phase 1, previously issued licences signed with the old key become invalid unless the old public key is retained during a transition window. The transition strategy (parallel public keys vs. re-signing all issued licences) must be decided before Phase 1 work begins — this is the most consequential design decision in the milestone.

---

## Sources

### Primary — HIGH confidence

- `tools/generate_licence.py` — existing issuance CLI; default path risk confirmed
- `puppeteer/agent_service/services/licence_service.py` — Ed25519 JWT validation; hardcoded public key; LicenceState state machine
- `puppeteer/requirements.txt` — confirmed no new server-side deps required for v15.0
- `puppeteer/compose.server.yaml` — devpi and pypiserver sidecars confirmed running
- `docs/scripts/regen_openapi.sh`, `docs/docs/api-reference/openapi.json` — static snapshot validation pattern confirmed
- `mop_sdk/cli.py` — Click command registration; source of truth for CLI cross-reference
- `mop_validation/scripts/test_playwright.py` — Playwright authentication pattern validated
- `CLAUDE.md` — `--no-sandbox`, localStorage JWT injection, form-encoded login, `mop_auth_token` key — authoritative project constraints
- `.planning/PROJECT.md` — v14.4 baseline; v11.1 LXC/cgroup notes; v14.3 `generate_licence` notes; v9.0 devpi notes
- `.gitignore` — `*.key` glob present; exact `tools/licence_signing.key` filename entry absent (confirmed gap)

### Secondary — MEDIUM confidence

- [PyGithub PyPI 2.9.0](https://pypi.org/project/PyGithub/) — `repo.create_file()` / `repo.update_file()` API
- [playwright PyPI 1.58.0](https://pypi.org/project/playwright/) — current version January 2026
- [linkcheckmd PyPI](https://pypi.org/project/linkcheckmd/) — active; `mkdocs-linkcheck` confirmed abandoned
- [Playwright Python docs — screenshots](https://playwright.dev/python/docs/screenshots) — `page.screenshot()` options confirmed
- [Espejo Docker-based PyPI + APT mirror](https://github.com/mmguero/espejo) — scoped mirror pattern; air-gap procedure
- [Keygen offline licensing docs](https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/) — Ed25519 as standard offline licence signing scheme

### Tertiary — MEDIUM/LOW confidence

- [PyPI mirror storage sizing discussion (Python Discuss, 2024)](https://discuss.python.org/t/how-do-i-locally-host-a-pypi-repository-on-an-air-gapped-server/60704) — scoped allowlist strategy rationale; confirms 20+ TB for full mirror
- Domain knowledge: Docker cgroup resource limit enforcement requires cgroup v2 — well-documented failure mode in containerised CI environments

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*

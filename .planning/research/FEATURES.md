# Feature Research

**Domain:** Operator Readiness — Enterprise job orchestration platform (Axiom v15.0)
**Researched:** 2026-03-28
**Confidence:** HIGH (existing system well-understood; new features are well-trodden patterns)

---

## Scope

Five capability areas for v15.0. Each is analysed independently: what operators expect, what differentiates, what to avoid, and what "done" looks like for an operator in production.

---

## Capability 1: Licence Generation Tooling

**Context:** `tools/generate_licence.py` already exists and generates Ed25519-signed JWT licences offline. The gap is record-keeping (no audit trail of what was issued to whom) and delivery workflow. The v15.0 work adds a record store in a private GitHub repo (`axiom-laboratories/axiom-licences`).

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Offline signing (no network at issue time) | Air-gap customer environments cannot phone home to validate | LOW | Already exists in `generate_licence.py` |
| Human-readable summary on stderr | Operator needs to confirm payload fields before sending to customer | LOW | Already exists |
| Customer ID, expiry, node limit, tier in payload | Standard licence metadata for support and billing queries | LOW | Already exists |
| Persistent record that a licence was issued | Support needs to know what tier and expiry was given to which customer | LOW | Currently missing — the gap this feature closes |
| Idempotent record writes | Re-running the tool for the same customer must not create duplicate records | LOW | Design choice: filename keyed on `licence_id` (UUID) prevents collisions |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Git-backed licence ledger | Immutable, auditable history via `git log`; no separate database needed | LOW | Private GitHub repo as record store; one JSON file per licence |
| Filename keyed on `{customer_id}-{licence_id}.json` | Each issued licence has a UUID in its filename; no collisions; easy grep | LOW | UUID already generated in JWT payload |
| Index file auto-updated | `index.json` listing all issued licences lets support query without reading every file | MEDIUM | Must be written atomically with the individual record file |
| JWT to stdout, record written separately | Composable: `AXIOM_LICENCE_KEY=$(python tools/generate_licence.py ...)` pipes naturally | LOW | Keeps the existing stdout contract intact |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Web UI for licence issuance (portal) | "Portal sounds professional" | Adds a service to maintain, a new auth layer, and a deployment dependency for a low-frequency operation | CLI + private git repo covers 100% of the use case at this scale |
| Licence revocation endpoint on production server | Operators want instant revocation | Requires runtime network calls in the licence validator, breaking air-gap safety | Grace period + short expiry cycle; do not issue licences longer than 1 year |
| Encrypted ledger files | "Secure the records" | The private repo IS the access control; encrypting within it adds no meaningful security and complicates `git log` readability | Private GitHub repo with CODEOWNERS is sufficient |

### What "Done" Looks Like for an Operator

1. Run `python tools/generate_licence.py --key ... --customer-id ACME ...`
2. JWT printed to stdout; copy into customer delivery email or secrets manager entry
3. A JSON record file written to a local checkout of `axiom-laboratories/axiom-licences`, committed and pushed
4. `git log` on the private repo shows full history: who issued what to whom and when
5. `index.json` in the repo has a one-line entry per licence for quick lookup by support

### Existing Axiom Dependencies

- `tools/generate_licence.py` — core signing logic, already functional
- `tools/licence_signing.key` — private key already generated
- `puppeteer/agent_service/services/licence_service.py` — validation side, no changes needed for this feature

---

## Capability 2: Docs Accuracy Validation

**Context:** The MkDocs site was written to match the v14.x system. As the system evolves, docs drift. This feature adds automated checks that catch drift before it reaches users, following the pattern established by `mop_validation/scripts/synthesise_friction.py`.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| API endpoint reachability checks | Docs claim specific endpoints exist — validate they return the expected status code | MEDIUM | Requires a running stack; `requests`-based spot checks against live system |
| CLI flag consistency check | `axiom-push --help` output cross-referenced against what docs claim the flags are | LOW | Run CLI help, parse output, compare key flags mentioned in feature guides |
| Env var name accuracy check | Docs claim `AXIOM_LICENCE_KEY`, `SECRET_KEY`, etc. — verify names match `main.py` and `.env.example` | LOW | Static analysis: grep source for env var reads; compare to docs mentions |
| Structured pass/fail report output | Operator needs actionable output, not a wall of text | LOW | Follow `synthesise_friction.py` pattern: per-check PASS/WARN/FAIL with specific mismatch detail |
| Exit code non-zero on FAIL items | Allows CI integration without parsing output | LOW | `sys.exit(1)` if any FAIL items; `sys.exit(0)` for WARN-only or all-PASS |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| OpenAPI schema cross-check | Compare `openapi.json` (generated at build time) against API paths mentioned in docs markdown | MEDIUM | Catches renamed or removed endpoints before they reach users |
| HTTP status code validation for CE/EE split | EE routes should return 402 on CE install; docs should reflect this | MEDIUM | Particularly valuable given the CE/EE gating added in v11.0–14.x |
| CI gate in `docs-deploy.yml` | Blocks `mkdocs gh-deploy` if any FAIL items; fast feedback loop | MEDIUM | Add as a job step before the deploy step in the existing workflow |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full E2E docs walkthrough automation | "Test the docs are correct by following them" | Requires a full LXC environment; very slow; duplicates what cold-start testing already does | Targeted spot-checks against a running stack; cold-start tests are the full E2E |
| Screenshot diffing as accuracy proxy | "If the screenshots match, the docs are accurate" | Screenshots drift on every UI change even when docs content is correct; high false-positive rate | Structural checks (API endpoints, env var names, CLI flags) are more stable signals |
| Auto-generate prose docs from code comments | "Eliminate drift by generating docs" | Loses operator-friendly narrative; API reference is already auto-generated from OpenAPI | Keep narrative docs human-authored; auto-generate only API reference (already done) |

### What "Done" Looks Like for an Operator

1. Run `python scripts/validate_docs.py --url https://localhost:8443` against a live stack
2. Script checks: API endpoints in docs are reachable with expected status codes, CLI flags match docs claims, env var names in docs match source
3. Output is a markdown or JSON report: PASS / WARN / FAIL per check with the specific mismatch described
4. FAIL items are actionable: "Docs claim `GET /api/executions` returns 200 — returns 402 in CE install (expected; verify docs say so)"
5. CI job in `docs-deploy.yml` runs this before publishing; blocks deploy on any FAIL

### Existing Axiom Dependencies

- `docs/docs/` — source docs to validate against
- `puppeteer/agent_service/main.py` — source of truth for API routes and env var usage
- `docs/scripts/regen_openapi.sh` — already generates `openapi.json`; validation compares docs against this schema
- Running Docker stack — required for live endpoint checks
- `mop_validation/scripts/synthesise_friction.py` — pattern to follow for structured reporting
- `.github/workflows/docs-deploy.yml` — location for CI gate addition

---

## Capability 3: Screenshot Capture

**Context:** The marketing homepage and MkDocs feature guides have no screenshots. Screenshots are table stakes for product documentation — their absence signals immaturity. This feature adds a Playwright-based script capturing current dashboard state into `docs/docs/assets/screenshots/`.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Screenshots covering each major dashboard view | Users expect to see what the product looks like before deploying it | MEDIUM | Jobs, Nodes, Queue, Foundry/Wizard, Scheduling/Health, Audit Log, Admin — 7–10 views |
| Authenticated captures | Dashboard requires JWT; screenshots must inject auth before navigating | MEDIUM | Pattern established in `mop_validation/scripts/test_playwright.py`: localStorage JWT injection |
| Deterministic filenames | `jobs-overview.png` not `screenshot-2026-03-28T14-32-11.png` — stable so docs can reference them | LOW | Name by view slug, never by timestamp |
| Sufficient resolution for retina displays | Blurry screenshots in docs signal low quality | LOW | `deviceScaleFactor: 2`, viewport 1440px wide |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Seeded demo data before capture | Screenshots show realistic content (3+ nodes, live jobs, audit entries) not empty state | MEDIUM | Setup fixtures: enroll nodes, dispatch jobs, wait for COMPLETED status before capturing |
| Configurable via env vars | `AXIOM_URL`, `AXIOM_ADMIN_PASSWORD` — runnable on any stack without editing the script | LOW | Follows pattern of other validation scripts in this codebase |
| Marketing-specific crop helper | Homepage hero section needs a specific viewport crop of the dashboard | LOW | Separate function per screenshot target; marketing crops are post-processing annotations |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Screenshots captured in CI on every push | "Always up to date" | CI Playwright runs are slow; screenshots change on every minor UI tweak causing large binary diffs in git history | Run screenshot capture manually as part of release prep; commit the results |
| Video walkthroughs generated from Playwright | "More engaging than screenshots" | Exponentially more storage; high maintenance; out of scope for docs | Static screenshots suffice for v15.0 docs |
| Screenshot diffing as regression test | "Detect visual regressions" | vitest already tests component behaviour; visual regression requires a dedicated tool (Percy, Chromatic) | Not in scope; keep screenshots as documentation artefacts only |

### What "Done" Looks Like for an Operator

1. Run `python scripts/capture_screenshots.py --url https://localhost:8443 --admin-password ...`
2. Script seeds demo data, waits for nodes to show ONLINE and jobs to show COMPLETED, then captures 8–10 views
3. Images saved to `docs/docs/assets/screenshots/` with stable names
4. Operator reviews and commits alongside docs updates
5. Feature guides reference images with relative paths: `![Jobs view](../assets/screenshots/jobs-overview.png)`
6. Marketing homepage `<img>` tags point to the same directory

### Existing Axiom Dependencies

- Running Docker stack with at least one enrolled node
- JWT auth + localStorage injection pattern from `mop_validation/scripts/test_playwright.py`
- `CLAUDE.md` Playwright constraints: `--no-sandbox`, form-encoded API login, localStorage key `mop_auth_token`
- `docs/docs/assets/` — exists; needs `screenshots/` subdirectory

---

## Capability 4: Node Validation Job Library

**Context:** Operators deploying new nodes need to verify the node is working correctly end-to-end: runtime executes, volumes map, network filtering works, resource limits are respected. Currently there are no reference jobs. This feature provides a library of pre-signed reference jobs covering each runtime and capability, with an operator runbook.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hello-world job for each runtime (Python, Bash, PowerShell) | Confirms the runtime is installed and the execution pipeline works end-to-end | LOW | Simple stdout `"hello from {runtime}"` + exit 0; one script per runtime |
| Exit-code failure job | Confirms FAILED state is captured correctly | LOW | `exit 1` / `sys.exit(1)` — exercises failure path without needing a bad script |
| Stdout and stderr capture validation job | Confirms both streams appear in the execution record | LOW | Write distinct strings to stdout and stderr; operator verifies both in dashboard |
| Jobs must be pre-signed | All library jobs need accompanying Ed25519 signatures to be dispatchable | MEDIUM | Run `axiom-push push` for each script at library creation time; store `.sig` file alongside script |
| Jobs are self-describing | Each job prints its purpose and expected output as the first line | LOW | `# Validation: python-hello` as a comment + print statement saying what to verify |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Volume mapping verification job | Confirms an operator-specified volume path is writable and readable inside the container | MEDIUM | Write a temp file to a mounted path; read it back; clean up |
| Network connectivity test job | Confirms the node's network policy allows expected traffic (DNS resolution, outbound HTTPS) | MEDIUM | `requests.get("https://example.com")` or `curl`; capture HTTP status; exit 0 on 200 |
| Runbook in docs | `docs/docs/runbooks/node-validation.md` walks through dispatching each job and interpreting output | LOW | Documents expected output per job so operator knows what pass looks like |
| Jobs organised by category | `validation-jobs/runtime/`, `validation-jobs/network/`, `validation-jobs/storage/` | LOW | Directory structure makes the library navigable as it grows |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automated orchestration of all validation jobs via management script | "Run all validations with one command" | Requires knowing which node to target, waiting for results, interpreting them — significant scope creep for v15.0 | Provide runbook and individual signed scripts; operator dispatches them in sequence |
| Jobs that modify persistent system state | "Test real operations" | Validation jobs may run in production environments; persistent side effects are unacceptable | Read-only or fully ephemeral operations only (write to `/tmp`, not to volumes; clean up after) |
| Resource limit verification job in v15.0 core | "Validates node limits are enforced" | Memory limit enforcement varies between Docker and Podman, and between cgroup v1/v2; high risk of false failures | Defer to v15.x; document as known gap in runbook |

### What "Done" Looks Like for an Operator

1. After deploying a new node, operator opens `docs/docs/runbooks/node-validation.md`
2. Runbook lists 6–8 jobs: Python/Bash/PowerShell hello, exit failure, stdout+stderr, volume write, network check
3. Each job in `validation-jobs/` has a `.sig` file alongside it; operator dispatches with `axiom-push push <script>`
4. Runbook documents expected output for each job; operator confirms COMPLETED + output matches
5. Entire validation suite can be done in under 30 minutes for a new node

### Existing Axiom Dependencies

- `axiom-push push` CLI — must be installed and configured to dispatch signed jobs
- `puppets/environment_service/runtime.py` — execution path being validated
- Ed25519 signing keypair at `~/.axiom/` — needed to sign library jobs at library creation time
- `puppeteer/agent_service/services/job_service.py` — job admission, capability matching, node selection
- v11.1 job test matrix (8 scenarios) — prior art for test coverage; library jobs are user-facing artefacts, not internal test infrastructure

---

## Capability 5: Custom Package Repo Operator Docs and Validation

**Context:** Axiom v7.0 shipped Package Repository Mirroring (local PyPI + APT sidecars, auto-sync, air-gapped upload, pip.conf/sources.list injection). The gap is comprehensive operator documentation and a validation job that confirms the mirror is reachable from a node before jobs depend on it.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Step-by-step mirror setup guide | "Ships with mirroring" is not enough; operators need exact configuration steps | MEDIUM | Cover: PyPI via bandersnatch, APT via apt-mirror; each as a standalone section |
| pip.conf and sources.list injection documentation | How to configure nodes to use the mirror by default vs. per-job override | LOW | Docs-only; injection mechanism already exists in the platform |
| Air-gap upload procedure docs | How to transfer packages from internet-connected machine to air-gapped mirror | MEDIUM | Documents existing upload feature; adds a worked example with exact commands |
| Storage sizing guidance | Full PyPI is 20+ TB — operators need to know scoped mirroring is the right pattern | LOW | Recommend curated package lists rather than full mirrors; bandersnatch `allowlist` config |
| Mirror connectivity validation job | A signed reference job that installs a package from the local mirror; exits 0 on success | MEDIUM | Reuses validation job library pattern from Capability 4; one job per mirror type |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scoped mirror strategy guide | Most operators don't need all of PyPI; a curated list of 50–100 packages covers most jobs | LOW | Bandersnatch `allowlist` config is straightforward; documenting it prevents the "20 TB problem" |
| Error message improvement when mirror is unreachable | Nodes get descriptive failures instead of silent hangs when configured mirror is down | MEDIUM | Code change: timeout + descriptive error in package install step within job execution |
| PWSH module mirror guide (optional/advanced) | PowerShell Gallery mirroring is under-documented in the ecosystem; covering it differentiates for Windows-heavy environments | HIGH | PSResourceGet / NuGet-compatible proxy; limited tooling; mark as advanced/experimental |

### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full PyPI mirror as a default sidecar config | "Works out of the box" | 20+ TB storage makes this impractical as a default; would mislead operators into believing full mirroring is standard | Document scoped mirror: list the packages your jobs need, mirror only those |
| Mirror management UI in the dashboard | "Centralised control" | The sidecars (bandersnatch, apt-mirror) have their own management interfaces; wrapping them in Axiom adds enormous scope for marginal value | Document use of upstream tools; Axiom's role is connection injection and validation |
| Automatic CVE re-scanning after mirror update | "Keep mirror clean" | Smelter already does CVE scanning at image-build time, which is the right chokepoint | Reference Smelter CVE enforcement as the defence-in-depth story; do not duplicate scanning |

### What "Done" Looks Like for an Operator

1. `docs/docs/feature-guides/package-repos.md` exists with complete setup guide for PyPI (bandersnatch) and APT (apt-mirror)
2. Guide covers: install and configure the sidecar, configure Axiom to inject `pip.conf` on nodes, test connectivity
3. Operator dispatches `validation-jobs/packages/pypi-mirror-check.py` to a node; it installs a known package from the local mirror and exits 0
4. Air-gap upload procedure documented with exact commands: `bandersnatch mirror`, transfer, sidecar ingestion
5. When the mirror is unreachable, the execution record shows: "pip install failed: mirror at http://mirror:3141/simple returned connection refused" — not a silent timeout

### Existing Axiom Dependencies

- Package Repository Mirroring sidecars (v7.0) — already in `compose.server.yaml`
- Smelter CVE scanning (v7.0) — downstream consumer of mirror packages; docs should reference it
- Foundry pip.conf/sources.list injection (v7.0) — the mechanism documented by this feature
- `docs/docs/feature-guides/` — location for new `package-repos.md`
- Validation job library (Capability 4) — mirror check jobs reuse this infrastructure and signing pattern

---

## Feature Dependencies

```
[Capability 1: Licence Record Store]
    extends     --> existing tools/generate_licence.py
    requires    --> private GitHub repo axiom-laboratories/axiom-licences (external setup)
    no blockers --> can build independently

[Capability 2: Docs Accuracy Validation]
    reads       --> docs/docs/ (MkDocs source)
    queries     --> running Docker stack (live endpoint checks)
    references  --> openapi.json (from docs/scripts/regen_openapi.sh)
    follows     --> mop_validation/scripts/synthesise_friction.py pattern
    writes to   --> .github/workflows/docs-deploy.yml (CI gate)

[Capability 3: Screenshot Capture]
    requires    --> running Docker stack with enrolled node
    uses        --> Playwright JWT auth pattern from mop_validation/
    writes to   --> docs/docs/assets/screenshots/
    enhances    --> Capability 2 (screenshots in validated docs)

[Capability 4: Validation Job Library]
    requires    --> axiom-push CLI installed and configured
    requires    --> Ed25519 keypair at ~/.axiom/
    requires    --> running Docker stack with enrolled test node
    documents in --> docs/docs/runbooks/node-validation.md (new file)

[Capability 5: Package Repo Docs + Validation]
    documents   --> existing mirror sidecars (v7.0)
    reuses      --> Capability 4 validation job pattern and signing infrastructure
    writes to   --> docs/docs/feature-guides/package-repos.md (new file)

[Capability 4] ──enables──> [Capability 5 mirror validation job]
[Capability 3] ──provides assets for──> [Capability 2 validated docs]
```

### Dependency Notes

- **Capability 1 is fully independent.** No runtime dependencies on other v15.0 features; can be built first or in parallel.
- **Capability 4 should precede Capability 5.** The PyPI mirror validation job reuses the validation job library signing pattern; Capability 5 should not define a separate job format.
- **Capabilities 2 and 3 are loosely coupled.** Screenshots improve docs quality but docs accuracy validation does not require screenshots to function.
- **All five capabilities can be parallelised** after the initial design decisions are made; none has a hard sequential dependency on another within v15.0.

---

## MVP Definition

### Launch With (v15.0)

All five capabilities are in scope. Listed in recommended build order.

- [ ] Capability 1: Licence record store — `generate_licence.py` extended with `--record-to <path>`; writes JSON record file; README documents commit-to-private-repo workflow
- [ ] Capability 4: Validation job library — 6–8 signed reference jobs covering Python/Bash/PowerShell hello, exit failure, stdout+stderr, volume write, network check; runbook in docs
- [ ] Capability 5: Package repo operator guide — `package-repos.md` covering PyPI + APT mirror setup, pip.conf injection, air-gap procedure, connectivity validation job (depends on Capability 4 pattern)
- [ ] Capability 3: Screenshot capture script — captures 8–10 key views with seeded demo data; images committed to `docs/docs/assets/screenshots/`
- [ ] Capability 2: Docs accuracy validation script — checks endpoints, CLI flags, env var names against live stack; produces PASS/FAIL report; optionally gated in CI

### Add After Validation (v15.x)

- [ ] CI gate in `docs-deploy.yml` — blocks deploy on FAIL items from Capability 2 script
- [ ] Resource limit validation job — add to Capability 4 library once cgroup v2 behaviour is characterised across Docker and Podman
- [ ] PWSH module mirror guide — add to Capability 5 once PSResourceGet/NuGet proxy tooling matures

### Future Consideration (v16+)

- [ ] Licence issuance portal (DIST-04) — web UI for self-service licence delivery; replaces CLI + git workflow at scale
- [ ] Periodic licence re-validation (DIST-05) — APScheduler 6h re-check; currently startup-only
- [ ] Automated validation job orchestration — management script that dispatches all library jobs and reports aggregate results

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Validation job library | HIGH — unblocks node operator verification post-deployment | MEDIUM | P1 |
| Package repo operator docs | HIGH — existing v7.0 feature is undocumented for operators | MEDIUM | P1 |
| Screenshot capture | MEDIUM — improves docs credibility and marketing surface | MEDIUM | P1 |
| Docs accuracy validation | MEDIUM — prevents regression; saves support time at scale | MEDIUM | P1 |
| Licence record store | MEDIUM — operational hygiene for EE customer management | LOW | P1 |

All five are P1. Implementation costs are MEDIUM or below because:
- All underlying platform features already exist (mirror sidecars, axiom-push, generate_licence.py)
- Each deliverable is a script or docs page, not a new service
- The Playwright and Python scripting patterns are established in this codebase

---

## Competitor Feature Analysis

| Feature | HashiCorp Nomad / Rundeck | Temporal / Airflow | Axiom v15.0 Approach |
|---------|---------------------------|---------------------|----------------------|
| Licence management | SaaS portal + email delivery | N/A (open source) | Offline CLI + git ledger — air-gap safe by design |
| Docs validation | Rarely automated; docs drift is industry-wide | No | Structured spot-check script; friction report format |
| Dashboard screenshots in docs | Manually maintained; visibly stale in most projects | Code-focused docs only | Playwright capture script; semi-automated on release |
| Node validation jobs | Not provided; operators write their own | Example DAGs in docs | Pre-signed reference jobs with runbook; lower operator barrier |
| Package repo docs | Minimal; assumes operator knows bandersnatch | No | Step-by-step guide with validation job; covers air-gap scoped mirror pattern |

---

## Sources

- [Keygen offline licensing docs](https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/) — Ed25519 as the default offline licence signing scheme; confidence HIGH
- [Keyforge offline licensing blog](https://keyforge.dev/blog/how-to-offline-licensing) — JWT-based offline licence patterns; confidence MEDIUM
- [Playwright screenshots official docs](https://playwright.dev/docs/screenshots) — `page.screenshot` options, `deviceScaleFactor`; confidence HIGH
- [Playwright docs screenshot automation (Medium, 2026)](https://medium.com/@admin_11488/using-playwright-to-automatically-generate-screenshots-for-documentation-2153b8bf045c) — deterministic filename and CI pattern; confidence MEDIUM
- [Espejo Docker-based PyPI + APT mirror (GitHub)](https://github.com/mmguero/espejo) — practical air-gap mirror setup reference; confidence HIGH
- [PyPI mirror storage sizing (Python Discuss, 2024)](https://discuss.python.org/t/how-do-i-locally-host-a-pypi-repository-on-an-air-gapped-server/60704) — scoped mirror strategy rationale; confidence HIGH
- Axiom codebase: `tools/generate_licence.py`, `mop_validation/scripts/test_playwright.py`, `mop_validation/scripts/synthesise_friction.py`, `.planning/PROJECT.md` — HIGH confidence (primary source)

---

*Feature research for: Axiom v15.0 Operator Readiness*
*Researched: 2026-03-28*

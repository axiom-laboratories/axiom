# Pitfalls Research

**Domain:** Operator Readiness additions to an existing commercial job-orchestration platform — licence generation tooling, docs accuracy validation, dashboard screenshot capture, node validation job library, and custom package repo operator docs
**Researched:** 2026-03-28
**Confidence:** HIGH (findings derived from codebase inspection of tools/generate_licence.py, .gitignore, CLAUDE.md Playwright notes, PROJECT.md v11.1–v14.4 history, and domain-specific patterns for each feature area)

---

## Critical Pitfalls

### Pitfall 1: Licence Private Key Written to Default Path Inside the Repo

**What goes wrong:**
`tools/generate_licence.py` defaults `--out` to `tools/licence_signing.key` and `--key` to the same path. A developer running `--generate-keypair` without supplying an explicit `--out` path writes the private key into the repository directory. `*.key` is in `.gitignore`, so it will not be committed — but this protection is fragile. Any tool that stages files broadly (`git add -A`, IDE "stage all" buttons, `pre-commit` hooks that auto-fix and re-stage) can silently include the key. Because `*.key` is a glob, a file named `licence_signing.key.bak` or `licence_signing.key.pem` would not be caught by the ignore rule.

The signing key is not a test key — it is the production key whose corresponding public key is hardcoded into `licence_service.py` and compiled into the Cython EE wheels. If it leaks to a public repo, every customer can issue themselves an unlimited-node EE licence in perpetuity. Key rotation requires rebuilding and redistributing all compiled wheels.

**Why it happens:**
The default output path in the argparse definition is convenient for development. The developer who generates a new keypair forgets to move it before committing, or forgets the key is there when cleaning up after a testing session.

**How to avoid:**
- Change the `--out` default to `None` (no default). Require the operator to specify the path explicitly. This makes the unsafe action opt-in, not opt-out.
- Add a gitignore entry for the exact filename: `tools/licence_signing.key` (in addition to the existing `*.key` glob) to provide belt-and-suspenders coverage.
- Add a `pre-commit` hook or CI check that fails if any PEM-format private key content (`-----BEGIN PRIVATE KEY-----`) appears in staged files.
- Document in `tools/README.md` or a `LICENCE_ISSUANCE.md` that the private key must live outside the repository (e.g., in a password manager, a dedicated `axiom-secrets` private repo with access limited to the licence issuer, or an HSM).
- Keep a separate `issued-licences/` log file (tracking customer ID, tier, expiry, issued date) in a private repo — separate from the key. Losing the log is recoverable; losing the key's confidentiality is not.

**Warning signs:**
- `git status` shows `tools/licence_signing.key` as a new untracked file
- `git diff --cached` includes `-----BEGIN PRIVATE KEY-----` in any file
- The key file is present in the repo directory after a fresh `git clone` (would mean it was committed)

**Phase to address:** Licence Generation Tooling phase — fix defaults and add CI guard before the tool is used in production for the first time

---

### Pitfall 2: Issued Licence Records in a Private Repo Become the Only Audit Trail

**What goes wrong:**
If the private repo used to track issued licences is the sole record of who has what licence, then losing access to that repo (repo deleted, GitHub account suspended, team offboarding without handover) means losing visibility into which customers have active licences. When a customer licence expires and they request renewal, there is no record of their tier, node limit, or original expiry — so renewal is issued blind.

Separately: if multiple team members can both generate and commit licence records, two people could issue duplicate or conflicting licences to the same customer ID with different node limits, with no merge conflict (both append to the log file).

**Why it happens:**
Licence issuance processes start simple ("just use a spreadsheet / text file in a private repo") and grow without governance. The private repo becomes a de-facto database with no integrity guarantees.

**How to avoid:**
- Store issued licence records in a structured format (NDJSON or CSV, one record per line) with fields: `issued_at`, `customer_id`, `tier`, `node_limit`, `expiry`, `issued_by`, `jwt_jti` (the JWT ID field from the signed token). The `jti` acts as a unique key.
- Use append-only commits to the log — never edit past records. Git history provides the audit trail.
- Require the `jti` from the generated JWT to be recorded before the JWT is delivered to the customer. If delivery fails, the `jti` record still exists, preventing silent duplicate issuance.
- At minimum, export a backup of the issued-licence log to a location outside GitHub (S3, encrypted local backup) on a weekly basis.

**Warning signs:**
- The log file is not versioned (e.g., is a spreadsheet checked into a repo that's treated as a binary)
- The same `customer_id` appears twice with different `node_limit` values and no superseded marker
- No `jti` field in the log — just customer name and expiry

**Phase to address:** Licence Generation Tooling phase — design the record format before issuing any licences

---

### Pitfall 3: Docs Accuracy Validation Checks Against Dev, Not the Same Stack Docs Reference

**What goes wrong:**
Automated docs-accuracy checks test whether documented API endpoints return expected status codes. If the checks run against a local dev server (`localhost:8001` with SQLite, no auth, admin auto-seeded) but the docs describe the production Docker stack (Postgres, mTLS, Caddy TLS termination, auth required), the checks will pass on ephemeral fixtures that do not match what operators actually encounter. A broken docs example (wrong endpoint path, missing auth header, wrong request body field) passes validation because the dev environment behaves differently.

**Why it happens:**
Running checks against `localhost:8001` is the path of least resistance. Setting up a full Docker stack for CI is heavier. Developers write the validation harness against what's convenient.

**How to avoid:**
- Run docs validation against the same Docker stack used for production builds (`compose.server.yaml` or `compose.cold-start.yaml`). The CLAUDE.md rule already states "never use local dev servers for testing" — apply this to docs validation as well.
- Authenticate all API checks using a service principal API key (`mop_` prefixed) generated against the live stack, not a dev-mode admin bypass. Docs describe authenticated operations; validation must be authenticated too.
- Test the endpoint path, request shape, and response shape together — not just "does this URL return 200". A 200 with an empty body or a 200 with a differently-shaped response is also a docs drift indicator.
- For docs that describe UI flows (e.g., "navigate to Admin > Licence"), use the Playwright screenshot capture as the validation signal — if the element described in docs does not exist in the screenshot, the docs are stale.

**Warning signs:**
- Validation script uses `requests.get("http://localhost:8001/api/...")` without an auth header
- CI job runs validation before `docker compose up` has completed (race condition — service not yet ready)
- Validation passes on `main` but fails on a clean checkout with a fresh Docker stack

**Phase to address:** Docs Accuracy Validation phase — define the target environment before writing any check

---

### Pitfall 4: Screenshot Capture Flakiness Due to Async Data Loading and Animations

**What goes wrong:**
Playwright screenshots taken of the Axiom dashboard capture loading spinners, empty tables (while WebSocket data is still in flight), or mid-transition CSS animations. Screenshots look correct during development (developer has a warm browser session with pre-loaded state) but are inconsistent in CI (cold start, no cached data, WebSocket still connecting). The result: every run produces a slightly different screenshot, diff-based checks fire false positives, and screenshots used in documentation show loading states instead of the live dashboard.

**Why it happens:**
The dashboard uses WebSocket for live data (`useWebSocket.ts`). Nodes, jobs, and queue data arrive asynchronously after page load. There is no "page fully loaded" DOM event for WebSocket data. Naive `page.screenshot()` after `page.goto()` captures whatever state the page is in 0–2 seconds after navigation.

**How to avoid:**
- Seed the DB (or use a running stack with live data) before capturing. Do not screenshot an empty system.
- After navigation, wait for a specific DOM element that only appears when data has loaded — e.g., `page.wait_for_selector('[data-testid="nodes-table-row"]', timeout=15000)` rather than a fixed `time.sleep()`.
- Disable CSS transitions for screenshot sessions: inject `<style>* { transition: none !important; animation: none !important; }</style>` into the page via `page.add_style_tag()` before screenshotting. This eliminates animation mid-frame captures.
- Per CLAUDE.md, inject the JWT via `localStorage.setItem('mop_auth_token', token)` rather than using the login form — this avoids the login animation entirely.
- Use `--no-sandbox` in Playwright chromium launch args (CLAUDE.md requirement for this environment).
- For docs screenshots specifically: capture a fixed viewport (1440x900) with the sidebar visible to match what docs describe. Use `full_page=False` unless the page needs scrolled content.

**Warning signs:**
- Screenshots show a spinner or empty table more than 20% of CI runs
- Screenshot pixel diffs are non-zero on consecutive runs of the same script without a code change
- The captured screenshot includes a `reconnecting...` WebSocket status badge in the corner

**Phase to address:** Screenshot Capture phase — define wait strategies before any screenshot is committed to docs

---

### Pitfall 5: Resource Limit Tests Pass Locally but Fail on CI Nodes Due to Kernel/cgroup Differences

**What goes wrong:**
Node validation jobs that test resource limits (`--memory 128m`, `--cpus 0.5`) behave correctly on the developer's machine but fail silently or produce inconsistent results on CI or LXC test nodes. Two common failure modes:

1. **Memory limit not enforced**: Docker on a host without cgroup v2 memory accounting will accept `--memory 128m` but not enforce it. A job that exceeds 128 MB will not be killed — the test "passes" because the job completes, but the limit was not actually applied.
2. **`--cpus` flag rejected**: On some kernel/Docker combinations, `--cpus` requires the `cpu` cgroup controller to be available. In LXC containers (used in this project's test infrastructure), cgroup delegation may not include the cpu controller, causing `docker run --cpus` to return an error that the job runner catches as a job failure.

**Why it happens:**
Resource limits in Docker are kernel features, not Docker features. The Docker CLI accepts the flags regardless of whether the host kernel supports them. Validation jobs that assume limit enforcement without first checking kernel capabilities will produce misleading pass/fail results.

**How to avoid:**
- Before running resource limit tests, check cgroup support on the target node: `docker info | grep -i cgroup` and verify the cgroup driver is `cgroupfs` or `systemd` with the relevant controllers available.
- Use `EXECUTION_MODE=direct` on LXC test nodes (as already established in mop_validation local_nodes compose files). Direct mode (Python subprocess) cannot enforce container resource limits — resource limit tests must run on nodes with a real Docker or Podman runtime, not in DinD inside LXC.
- Structure resource limit validation jobs to self-report whether limits were applied: the job script should read `/sys/fs/cgroup/memory.max` (cgroup v2) or `/sys/fs/cgroup/memory/memory.limit_in_bytes` (cgroup v1) and return the observed limit as part of its output. The test harness then asserts against the reported value, not just job completion.
- Add a skip condition: if the test node's `capabilities` heartbeat does not include a `resource_limits_supported: true` capability, skip the resource limit test suite and log it as "unsupported on this node" rather than "passed".

**Warning signs:**
- Resource limit job completes COMPLETED even when the script intentionally allocates 2x the memory limit
- `docker run --memory 128m` succeeds but `docker inspect` shows `MemoryLimit: 0`
- CI LXC nodes run all validation jobs with `EXECUTION_MODE=direct` — resource limit tests are silently never actually testing container limits

**Phase to address:** Node Validation Job Library phase — gate resource limit tests on runtime capability detection

---

### Pitfall 6: Volume Mapping Tests Break the Pull Security Model If Not Scoped

**What goes wrong:**
Node validation jobs that test volume mapping (`-v /host/path:/container/path`) can inadvertently escape the job isolation model if the test script mounts sensitive host paths. A validation job that mounts `/etc/` or `/var/run/docker.sock` to verify that volume mapping works will appear to pass the test, but has demonstrated that any operator with job-dispatch permission can read host secrets or control the Docker daemon. In a multi-tenant environment, this is a security regression.

More practically: volume mapping tests run on live nodes. If the test mounts a path that does not exist on the target node (e.g., `/data/axiom` which exists on the developer's machine but not the LXC test node), the Docker run fails with a `bind source path does not exist` error that manifests as a job failure, not as a "volume path not found" diagnostic.

**Why it happens:**
Validation tests are written from the developer's perspective, where the developer knows which paths exist. When deployed to a clean LXC node or a customer environment, those paths do not exist.

**How to avoid:**
- Volume mapping validation tests should only mount paths that the test job itself creates: use a tmpdir inside the job script (`/tmp/axiom-vol-test-<uuid>`), verify the mount by writing a sentinel file from inside the container and reading it from outside, then clean up.
- Never mount host socket files (`/var/run/docker.sock`, `/run/podman/podman.sock`) in validation jobs. These should be explicitly blocked in the node validation job library documentation.
- Add a pre-flight check in the validation job: the job's Python script should verify the target path exists before attempting to mount it, and return a structured `{"status": "SKIP", "reason": "path not found"}` output rather than crashing.

**Warning signs:**
- Validation job script hardcodes an absolute host path in its volume mapping argument
- A validation job mounts `/var/run/docker.sock` to "verify container nesting"
- Volume mapping test fails with `bind source path does not exist` on every run against a fresh node

**Phase to address:** Node Validation Job Library phase — review each job's mount spec before committing

---

### Pitfall 7: Network Filtering Tests Leave Residual iptables Rules on Test Nodes

**What goes wrong:**
Validation jobs that test network filtering (`--network=none`, custom bridge networks, iptables DROP rules) can leave residual network configuration on the test node after the job completes. Docker removes the container on completion, but if the test job modifies iptables directly (to simulate filtering), those rules persist in the kernel after the container exits. Subsequent jobs on the same node may fail with unexpected `Connection refused` errors that have nothing to do with the job being tested.

A subtler variant: Docker's `--network=none` test works correctly, but then the validation job library adds a test that verifies internet egress is blocked by running `curl https://example.com` from within the job. If the test node itself does not have DNS resolution (air-gapped node), `curl` fails for the wrong reason — the test reports "network filtering works" when actually DNS is just unavailable.

**Why it happens:**
Network state is node-global. Tests that modify it are not isolated to a single job execution. Developers testing in a throw-away environment (LXC container that gets destroyed) do not notice the residual state problem.

**How to avoid:**
- Network filtering validation jobs must not modify iptables directly. Use Docker's built-in network isolation (`--network=none`, `--network=<custom-bridge>`) which Docker manages and tears down with the container.
- For the network-egress-blocked test, assert against the Docker network mode rather than testing actual network behaviour. `docker inspect <container> | jq '.[].NetworkSettings.Networks'` will show `none` if `--network=none` was used — this is a sufficient and reliable assertion.
- If actual network behaviour must be tested (e.g., to verify the air-gap mirror is used instead of PyPI), use a controlled mock: run a local HTTP server on the node as a separate step, point the job at it, verify the job reaches the local server but not the external one.
- Tag network-filtering tests as requiring a node with `network_test_safe: true` capability (a capability set manually on dedicated test nodes) so they do not accidentally run against production nodes.

**Warning signs:**
- `iptables -L` on the test node shows rules with comments like `axiom-test-*` after a validation run
- Subsequent jobs on the same node fail with `Name or service not known` DNS errors
- A validation job uses `subprocess.run(['iptables', ...])` inside its script

**Phase to address:** Node Validation Job Library phase — prohibit direct iptables manipulation in job scripts

---

### Pitfall 8: Docs Drift Between Custom Package Repo Docs and Actual Devpi/Bandersnatch Config

**What goes wrong:**
The custom package repo operator docs describe how to configure devpi (or bandersnatch, or Pulp) for air-gapped PyPI mirroring. The Axiom stack already ships a `devpi` sidecar in `compose.server.yaml` (for internal EE wheel hosting). If the operator docs describe a configuration that differs from how the Axiom-bundled devpi is actually configured, operators following the docs will end up with a working-but-diverged setup that breaks when they pull a new version of `compose.server.yaml`.

The most common failure: the docs describe devpi `--host 0.0.0.0` for LAN accessibility, but the bundled devpi is configured as `--host 127.0.0.1` (localhost-only, accessed via the Caddy reverse proxy). An operator who directly accesses devpi on `http://server:3141` following the docs will get a connection refused while the Caddy-proxied path (`https://server/devpi/`) works fine.

**Why it happens:**
Operator docs are written once, often ahead of the actual implementation, and do not get updated when the compose configuration changes. The devpi compose config and the docs are in different files with no automated link between them.

**How to avoid:**
- Extract devpi configuration values (port, index names, proxy path) into environment variables in `compose.server.yaml`. The operator docs reference the variable names, not hardcoded values. When the compose changes, the docs do not need updating because they describe the operator's env file, not the compose internals.
- Add a docs-validation check that extracts the devpi base URL from the live compose config and verifies `GET <devpi_url>/+api` returns a `{"type": "devpi"}` response. This is a one-line check that confirms the docs-described URL is reachable.
- Pin the devpi version in `compose.server.yaml` (do not use `latest`) so operators upgrading do not hit breaking API changes that the docs do not cover.

**Warning signs:**
- The docs describe `http://server:3141/` but the compose file binds devpi to `127.0.0.1:3141` inside the container
- Devpi config in `compose.server.yaml` uses environment variables that are not documented in `.env.example`
- The docs reference a devpi index name (`/root/pypi`) that differs from what `compose.server.yaml` creates on first start

**Phase to address:** Custom Package Repo Docs phase — test all documented commands against a live devpi/bandersnatch instance before publishing

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `tools/licence_signing.key` default path inside repo directory | No path to remember | Gitignore is only protection; key leaks if gitignore is misconfigured or bypassed | Never — default must be outside repo |
| Write docs validation checks against localhost dev server | Fast to write, no Docker overhead | Validates wrong environment; docs drift is not caught | Never for production docs |
| Screenshot with fixed `time.sleep(3)` instead of DOM wait | Simple, usually works locally | Flaky in CI (timing-dependent); slow on fast machines | Never for committed screenshots |
| Resource limit tests assert "job COMPLETED" without checking limit was applied | Simple pass/fail | Tests pass on kernel without cgroup support; gives false assurance | Never — check the cgroup value directly |
| Write issued-licence log as a plain text file without a `jti` field | Quick to set up | Cannot detect duplicate issuance; no unique key for customer support lookups | Never — always include `jti` |
| Docs for devpi/bandersnatch use hardcoded port numbers instead of env var references | Clearer prose | Port changes in compose silently break the instructions | Only acceptable for a single release; refactor at next compose version bump |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `tools/generate_licence.py` + git | `--out` defaults to `tools/licence_signing.key` inside repo; gitignore protects but is not guaranteed | Override default to `None`; require explicit `--out` path; add belt-and-suspenders gitignore for exact filename |
| Playwright + Axiom dashboard WebSocket | `page.screenshot()` immediately after `page.goto()` captures loading state | `page.wait_for_selector('[data-testid="..."]')` on a stable element before screenshotting |
| Playwright + React controlled inputs | `fill()` does not trigger React state updates reliably (documented in CLAUDE.md) | Inject JWT via `localStorage`; avoid login form in Playwright |
| Docker resource limits + LXC nodes | `--memory` / `--cpus` flags accepted but not enforced without cgroup support | Detect cgroup capability; use `EXECUTION_MODE=direct` on LXC nodes (resource limits test requires real Docker host) |
| devpi internal index + Caddy proxy | Docs say `http://server:3141/`; actual access path is `https://server/devpi/` via Caddy | Document the Caddy-proxied URL; provide a `curl -k https://server/devpi/+api` health check command |
| MkDocs `--strict` + new docs pages | Any broken link or missing reference fails the CI build | Run `mkdocs build --strict` locally before opening a docs PR |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Screenshot capture runs all views sequentially with full page load waits | 5+ minute docs screenshot job in CI | Reuse authenticated browser context; batch navigation without full page reload between views | Immediately noticeable in CI run times |
| Docs validation checks hit every documented endpoint once per check run | N API calls on every CI run, slow on large docs sets | Parallelize checks (asyncio or concurrent.futures); cache `GET /api/licence` and other static endpoints | Grows linearly with number of checked endpoints |
| Node validation jobs all target the same node | Serial execution; validation suite takes O(n × job_duration) | Distribute jobs across multiple test nodes using capability tags; run independent tests in parallel | When validation suite grows beyond 10 jobs |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Licence signing private key stored in the codebase (even gitignored) | Key leaked if gitignore bypassed; CI runners that checkout the repo may cache the working directory | Move key entirely outside repo; pass via env var `AXIOM_LICENCE_SIGNING_KEY` pointing to an external path |
| Issued licence log stored in the same repo as the signing key | Single repo compromise exposes both the issuance record and the key to forge new licences | Keep log and key in separate repos or systems |
| Docs validation script uses admin credentials hardcoded in the script | Admin password in CI logs; leaked in git history if accidentally committed | Use a dedicated read-only service principal API key for docs validation; store in GitHub Actions secret |
| Screenshot script captures admin pages with sensitive data visible (licence keys, join tokens) | Screenshots committed to git or docs contain production secrets | Redact or use test-fixture data; never screenshot a live production instance's Admin page |
| Network filtering validation job uses `subprocess.run(['iptables', ...])` to modify host network | Residual rules persist; subsequent jobs affected; potential privilege escalation on the node | Use Docker-native network isolation only; prohibit iptables modification in job scripts |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Licence generation docs show `--key tools/licence_signing.key` in examples | Operators follow the example and put the key in the repo directory | Example must use a path outside the repo: `--key ~/axiom-secrets/licence_signing.key` |
| Node validation job library has no index or discovery mechanism | Operators cannot find which validation jobs exist without reading the code | Provide a manifest file (`validation_jobs.json`) listing each job, its purpose, required capabilities, and expected outcomes |
| Custom package repo docs describe three different tools (devpi, bandersnatch, Pulp) without a clear "use this one" recommendation | Operators spend time evaluating rather than implementing | Lead with the recommended tool for the Axiom use case (devpi, already bundled); document alternatives in a collapsible block |
| Docs validation failures in CI block the docs-deploy workflow with a cryptic error | Contributor opens a docs PR; CI fails; error message points to an API endpoint, not the specific docs file | Validation failure messages must include the docs file and line number where the broken example appears |

---

## "Looks Done But Isn't" Checklist

- [ ] **Licence tooling:** `--out` and `--key` defaults do not point inside the repo — verify `python tools/generate_licence.py --help` shows no default path ending in `tools/`
- [ ] **Licence tooling:** `tools/generate_licence.py --generate-keypair` run in the repo directory does NOT create a tracked file — verify with `git status` immediately after
- [ ] **Licence tooling:** Issued licence log has a `jti` field matching the JWT's `jti` claim — verify with `python -c "import jwt; d=jwt.decode(TOKEN, options={'verify_signature':False}); print(d['jti'])"`
- [ ] **Docs validation:** Validation script is authenticated with a service principal API key, not hardcoded admin credentials — verify no `admin` username in the validation script
- [ ] **Docs validation:** Validation runs against the Docker stack, not localhost dev server — verify the target URL in the script is `https://agent:8001` or `https://localhost:8443`, not `http://localhost:8001`
- [ ] **Screenshot capture:** Screenshots do not contain loading spinners — verify by running capture twice and diffing the outputs with `diff` or `pixelmatch`
- [ ] **Screenshot capture:** Animation-disabling style injection is present before first `page.screenshot()` call
- [ ] **Resource limit tests:** Test asserts the observed cgroup limit value, not just job completion — verify the job output contains `memory_limit_bytes` or equivalent field
- [ ] **Volume mapping tests:** No hardcoded absolute host paths in job scripts — verify with `grep -r "/etc\|/var\|/home\|/root" node_validation_jobs/`
- [ ] **Network tests:** No `iptables` calls in job scripts — verify with `grep -r "iptables\|ip6tables" node_validation_jobs/`
- [ ] **Custom package repo docs:** All documented `curl` examples tested against a live devpi instance — verify each command returns a 200 with the expected response structure
- [ ] **Devpi docs:** The proxied URL (via Caddy) is the primary documented access path, not the raw devpi port

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Licence private key committed to git | HIGH | Immediately revoke by rotating the public key baked into `licence_service.py`; rebuild + redistribute all Cython EE wheels; re-issue all customer licences with new signing key; force-expire old licences via `exp` field; contact all affected customers |
| Docs validation false positive (passes on wrong environment) | MEDIUM | Re-run validation against the correct Docker stack; identify which docs checks were environment-specific; add environment assertion at the top of each check script |
| Screenshot flakiness in CI | LOW | Add `page.wait_for_selector()` on a stable DOM element; add animation-disable injection; re-run screenshot job; accept the new screenshots if they are correct |
| Resource limit test passes on kernel without cgroup support | MEDIUM | Add capability detection to test runner; re-tag test nodes with `resource_limits_supported` capability; re-run on a host with confirmed cgroup v2 support |
| Residual iptables rules from network tests | LOW | SSH to affected node; `iptables -F` to flush all rules (if node is a disposable test node only); if production node, manually identify and remove axiom-test rules with `iptables -D` |
| Devpi docs describe wrong URL | LOW | Update docs; run `mkdocs build --strict`; redeploy to GitHub Pages |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Licence key default path inside repo (Pitfall 1) | Licence Generation Tooling | `python tools/generate_licence.py --help` shows no default for `--out`; `git status` clean after `--generate-keypair` |
| Issued licence records lack integrity (Pitfall 2) | Licence Generation Tooling | Log format spec reviewed; `jti` field present; private repo access list confirmed before first issuance |
| Docs validation against wrong environment (Pitfall 3) | Docs Accuracy Validation | Validation script rejects `http://localhost` target; CI job spins up Docker stack before running checks |
| Screenshot capture flakiness (Pitfall 4) | Screenshot Capture | Two consecutive CI runs produce pixel-identical screenshots; no spinner in any captured image |
| Resource limit tests unreliable on LXC (Pitfall 5) | Node Validation Job Library | Each resource limit test reads and asserts the cgroup value; test runner skips on nodes without capability flag |
| Volume mapping tests mount unsafe paths (Pitfall 6) | Node Validation Job Library | Code review confirms no absolute host paths; all mounts use test-created tmpdir paths |
| Network tests leave residual rules (Pitfall 7) | Node Validation Job Library | No iptables calls in any job script; post-run iptables check shows clean state on test node |
| Docs drift on devpi/bandersnatch config (Pitfall 8) | Custom Package Repo Docs | All documented commands tested against live instance; devpi port/path extracted from env vars not hardcoded |

---

## Sources

- `tools/generate_licence.py` — inspected directly: default `--out` is `tools/licence_signing.key`; `*.key` in `.gitignore` is the sole protection
- `tools/licence_signing.key` — confirmed present on disk (gitignored, not tracked), confirming the default path risk is real
- `.gitignore` — `*.key` pattern confirmed; `tools/licence_signing.key` exact-path entry absent
- `CLAUDE.md` — Playwright known issues: `--no-sandbox` required; JWT via localStorage; `fill()` unreliable; never use dev servers for testing
- `.planning/PROJECT.md` v11.1 — LXC node test infrastructure with `EXECUTION_MODE=direct`; DinD cgroup v2 issues documented
- `.planning/PROJECT.md` v14.3 — `tools/generate_licence.py` offline CLI; `AXIOM_LICENCE_SIGNING_KEY` env var support confirmed
- `.planning/PROJECT.md` v9.0 — devpi internal wheel index in `compose.server.yaml` confirmed; `mkdocs --strict` CI gate confirmed
- `.planning/PROJECT.md` v14.2 — GitHub Pages deploy workflow; offline plugin conditional on `OFFLINE_BUILD`
- Prior PITFALLS.md (v14.4) — Playwright pattern guidance for this stack; banner blindness patterns
- Domain knowledge: Docker cgroup resource limit enforcement requires cgroup v2 and appropriate kernel configuration — well-documented failure mode in containerised test environments

---
*Pitfalls research for: v15.0 Operator Readiness milestone (licence generation tooling, docs accuracy validation, screenshot capture, node validation job library, custom package repo docs)*
*Researched: 2026-03-28*

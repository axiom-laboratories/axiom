# Project Research Summary

**Project:** Axiom v14.0 — CE/EE Cold-Start Validation Framework
**Domain:** AI-agent docs-fidelity testing via Gemini CLI inside Incus LXC containers
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

Axiom v14.0 is not a feature release — it is a docs-fidelity and operator-path validation milestone. The core question is: "Can a first-time operator follow the Axiom documentation and arrive at a working system?" This is addressed by deploying Gemini CLI agents inside isolated Incus LXC containers, giving them only the docs site as a reference, and having them execute the getting-started and operator procedures while logging friction. Two scenarios run sequentially: CE (community edition) and EE (enterprise edition with a pre-injected licence key). A file-based checkpoint protocol allows Claude (on the host) to provide steering when the agent is blocked without invalidating the cold-start premise.

The recommended approach builds on heavily validated existing infrastructure (Incus LXC provisioning, Python Playwright with --no-sandbox, Ed25519 signing). Net-new requirements are minimal: Gemini CLI installation in Ubuntu 24.04 LXC via Node.js 20 from the NodeSource PPA, model pinning via the `GEMINI_MODEL` env var, a tester-scoped `GEMINI.md` that constrains the agent to docs-only behaviour, a stripped `compose.cold-start.yaml` (no Cloudflare tunnel, no DuckDNS), and a file-based checkpoint directory for async host-to-agent steering. The PowerShell Containerfile.node issue (Debian 12 APT repo key failure) is resolved by switching to a direct GitHub `.deb` download for PowerShell 7.6.0.

The primary risks are environmental, not feature-level: TLS SAN mismatches blocking Playwright, Gemini CLI headless hangs due to missing `ripgrep` or dbus keyring blocking, Docker-in-LXC AppArmor pivot_root denial on Ubuntu 24.04 kernel 6.8.x, and Gemini API rate limiting stalling the run mid-session. All eight identified critical pitfalls have clear prevention steps that must be executed during Phase 1 (LXC environment setup) before any agent session starts. If Phase 1 verification criteria are met before running scenarios, the failure modes are recoverable rather than run-invalidating.

## Key Findings

### Recommended Stack

The existing Axiom validation stack requires only additive changes. The base (Incus 6.22, Python 3.12, Docker 29.2.1, Python Playwright 1.58.0, Ed25519 tooling) is fully validated from v11.1 and is not re-researched. Net-new tooling is well-supported and installation paths are confirmed against official docs.

**Core technologies (net-new for v14.0):**
- Gemini CLI (latest stable via `npm install -g @google/gemini-cli`): headless AI tester — `--prompt` flag enables non-interactive mode; `GEMINI_API_KEY` env var bypasses OAuth browser flow entirely
- Node.js 20.x (via NodeSource `setup_20.x` PPA): Gemini CLI runtime — Ubuntu 24.04 ships Node.js 18 which is below the minimum; NodeSource PPA is the only reliable non-nvm install method for non-interactive `incus exec` contexts
- PowerShell 7.6.0 (via direct `.deb` from GitHub releases): node job runtime — existing Containerfile.node Debian 12 APT repo fails silently due to SHA1 key rejection; direct `.deb` bypasses the repo key entirely and is version-pinned
- Python stdlib (`json`, `pathlib`, `time`, `subprocess`): checkpoint protocol implementation — no external framework needed for the orchestrator-to-agent file IPC

**Key configuration:**
- `GEMINI_MODEL=gemini-2.0-flash` env var: pins model — prevents auto-upgrade to 2.5 Flash/Pro which has different rate limits and quota behaviour
- Tester-scoped `GEMINI.md` in `/workspace/gemini-context/`: constrains agent to docs-only, defines friction logging protocol — must not use the repo's developer `GEMINI.md`
- `SERVER_HOSTNAME=172.17.0.1` in cert-manager compose env: ensures Caddy TLS SAN includes the Docker bridge gateway IP — required for both Playwright and Gemini CLI HTTP calls from inside the LXC

### Expected Features

This milestone produces a docs-fidelity test harness, not product features. The deliverables are validation runs and friction reports.

**Must have (P1 — without these, results are invalid):**
- LXC container per scenario with full Axiom Docker stack — isolated environment is the foundation; shared state invalidates findings
- Docs-only instruction constraint for Gemini agent — agent with codebase access cannot act as a first-time user
- Three job runtime coverage per scenario (Python, Bash, PowerShell) — each runtime is a documented claim that must be exercised
- Checkpoint file protocol (JSON-based async steering) — agent blocked without recovery mechanism means abandoned run
- Per-step pass/fail log — auditable output is required for the friction report to be actionable
- Friction points with evidence (verbatim error, exact doc reference, step context) — untraceable findings cannot be fixed
- Severity triage per finding (BLOCKER / FRICTION / COSMETIC) — enables prioritised fix list
- Merged CE+EE summary with comparison table — shared findings flag core doc gaps; EE-only findings flag EE doc gaps
- EE licence pre-injection (`AXIOM_LICENCE_KEY` in `.env`) — licence issuance portal is not yet built; key must be injected

**Should have (P2 — significantly improves signal quality):**
- Verbatim doc quote per friction finding — links finding to exact fixable sentence
- Step sequence reconstruction log — shows actual path taken vs documented path
- Runtime-specific stdout assertions per job — confirms correct runtime was invoked, not just exit_code=0
- Checkpoint steering transcript in report — steering interventions are themselves friction evidence
- Doc coverage map — which pages were consulted, which were skipped

**Defer (v2+):**
- Multiple user personas (junior vs senior operator)
- Mutation testing of docs (intentionally missing steps)
- Automated regression re-run after each docs update
- Parallel CE + EE scenario execution

### Architecture Approach

The v14.0 architecture layers a Gemini tester process and a file-based checkpoint protocol on top of the existing Incus LXC provisioning infrastructure. The Gemini tester runs as a native LXC process (not inside Docker), making Axiom services reachable at `localhost` (published Docker ports) or the LXC's default gateway IP. Puppet nodes inside Docker inside the LXC use `AGENT_URL=https://172.17.0.1:8001` (Docker bridge gateway) and `EXECUTION_MODE=direct` to avoid nested cgroup v2 issues.

**Major components:**
1. `compose.cold-start.yaml` — stripped Axiom stack (no Cloudflare tunnel, no DuckDNS, `SERVER_HOSTNAME=172.17.0.1`); lives in `puppeteer/` inside LXC; never modifies production `compose.server.yaml`
2. `provision_lxc.py` / `teardown_lxc.py` — host-side Incus scripts; launch Ubuntu 24.04 with `security.nesting=true`, install Docker + Gemini CLI + Python stack, copy axiom repo, start Axiom stack
3. Gemini tester agent — process inside LXC at `/workspace/`; constrained by tester `GEMINI.md`; reads docs at `http://localhost/docs/`, dispatches jobs via `axiom-push` CLI, logs friction to `checkpoint/FRICTION.md`
4. `checkpoint/` directory (`/workspace/checkpoint/`) — async IPC: Gemini writes `PROMPT.md` on block; Claude reads via `incus exec`, writes `RESPONSE.md` via `incus file push`; version counter prevents stale reads
5. `monitor_checkpoint.py` — host-side; polls `PROMPT.md` every 30 seconds; surfaces to Claude; writes `RESPONSE.md` back
6. `synthesise_friction.py` — host-side; pulls `FRICTION.md` from both CE and EE containers; produces `cold_start_friction_report.md` with BLOCKER / NOTABLE / MINOR triage and CE-vs-EE comparison

**Key patterns:**
- CE run precedes EE: CE is the simpler baseline; failures in CE are unambiguous CE bugs; EE adds only `AXIOM_LICENCE_KEY` injection + `axiom-ee` install
- Fresh `HOME` per validation session (`export HOME=/root/validation-home`): prevents prior Gemini development history from contaminating the first-user simulation
- Tester `GEMINI.md` in `/workspace/gemini-context/` is separate from repo `GEMINI.md`: developer context (read source code, check sister repos) must not reach the tester
- Atomic checkpoint writes (`.tmp` + rename): prevents Claude from reading partial checkpoint files during Gemini 429 recovery

### Critical Pitfalls

1. **Caddy TLS SAN mismatch + Chromium cert store** — Set `SERVER_HOSTNAME=172.17.0.1` in cert-manager env before stack start; use `ignore_https_errors=True` in Playwright or install Root CA into Chromium's NSS DB via `certutil`. `update-ca-certificates` is insufficient — Chromium ignores the OS trust store.

2. **Gemini CLI headless hang in LXC** — Install `ripgrep` (`apt install ripgrep`) before running Gemini; set `GEMINI_API_KEY` explicitly as env var to bypass dbus/keyring blocking; wrap all `gemini` invocations with `timeout 600`; confirm headless smoke test (`timeout 30 gemini -p "Say hello"` returns within 30 seconds) as Phase 1 acceptance criterion.

3. **Gemini API 429 rate limit stalls run mid-session** — Use a paid API key (Tier 1 minimum, 300 RPM); free tier's 250 RPD makes a full CE+EE pass infeasible; add retry/backoff wrapper around `gemini` invocations; pin to `gemini-2.0-flash` to reduce quota pressure.

4. **Docker-in-LXC networking: AppArmor pivot_root + bridge IP confusion** — Verify `docker run --rm hello-world` succeeds inside LXC before anything else; if `pivot_root: permission denied`, run `incus config set <container> raw.apparmor "pivot_root,"`; use Docker bridge gateway IP (`172.17.0.1`), not `localhost`, for Axiom URLs inside the LXC.

5. **Gemini first-user contamination via GEMINI.md or history bleed** — Use an isolated `HOME` directory for all validation sessions; place only installer artifacts (no source code, no `GEMINI.md`) in the Gemini working directory; admin credentials are provided via checkpoint steering, not pre-loaded into the agent prompt.

6. **EE licence expiry during run** — Regenerate the EE test licence immediately before each validation run (not during setup days earlier); validate `exp` field is at least 2 hours in the future; assert `GET /api/admin/features` returns `ee_status: loaded` as the first step of every EE phase.

7. **PowerShell jobs fail: `pwsh` not in base node image** — Switch `Containerfile.node` to direct `.deb` install from GitHub releases; build and tag the PowerShell-capable node image before the validation run; verify `docker exec <node> which pwsh` before dispatching PowerShell test jobs.

8. **Checkpoint deadlock** — Clear checkpoint directory at start of each run; atomic write (`.tmp` + rename) prevents partial file reads; Gemini times out after 10 minutes and writes a best-effort fallback rather than hanging indefinitely.

## Implications for Roadmap

Based on research, a 5-phase structure maps cleanly to the dependency graph. Each phase has hard prerequisites from the one before.

### Phase 1: LXC Environment and Cold-Start Compose

**Rationale:** Nothing can be tested without a working Axiom stack inside LXC. All 8 critical pitfalls that relate to infrastructure (TLS SAN, Docker networking, AppArmor, Gemini headless, API key tier) must be resolved here. Phase 1 is the highest-risk phase because it encounters all the environmental unknowns.

**Delivers:**
- `compose.cold-start.yaml` with `SERVER_HOSTNAME=172.17.0.1`, stripped tunnel/DuckDNS services, puppet nodes with `EXECUTION_MODE=direct` and `AGENT_URL=https://172.17.0.1:8001`
- `provision_lxc.py` and `teardown_lxc.py` (based on existing `manage_node.py` pattern)
- Verified: stack starts, Caddy TLS SAN includes Docker bridge IP, agent responds on 8001, docs at `/docs/`, `docker run --rm hello-world` succeeds inside LXC, `timeout 30 gemini -p "Say hello"` returns within 30 seconds

**Addresses:** LXC-per-scenario table stakes feature, all infrastructure pitfalls (P1, P3, P4)

**Avoids:** Using `compose.server.yaml` directly inside LXC (crashes on tunnel/DuckDNS); using `localhost` for puppet node `AGENT_URL`

### Phase 2: Gemini Tester Context and Checkpoint Protocol

**Rationale:** Gemini cannot act as a valid tester without a scoped `GEMINI.md`, a fresh HOME directory, a signing key registered with the stack, and a working checkpoint round-trip. The checkpoint schema must be agreed and tested before any validation scenario runs.

**Delivers:**
- Tester-scoped `GEMINI.md` at `/workspace/gemini-context/` with docs-only constraint, checkpoint file protocol definition, friction severity definitions (BLOCKER / NOTABLE / MINOR)
- `checkpoint/` directory with seed files and version-counter handshake protocol
- `monitor_checkpoint.py` host-side poller
- Ed25519 test-signing keypair generated; public key registered via `POST /api/signatures`
- `inject_ee_licence.py` for EE run preparation
- Verified: Gemini can authenticate (JWT via login), checkpoint round-trip completes in < 60 seconds, source code inaccessible from Gemini working directory

**Addresses:** Docs-only instruction constraint, checkpoint protocol (P5, P8)

**Avoids:** Using developer `GEMINI.md` as tester context; pre-loading admin credentials into agent prompt; shared HOME with dev history

### Phase 3: CE Cold-Start Run

**Rationale:** CE must precede EE. CE is the simpler path with no licence or EE-specific setup. Failures in CE are unambiguously CE bugs. The CE run validates the install path and all 3 job runtimes, which EE also runs — shared friction identified in CE doesn't need re-investigating in EE.

**Delivers:**
- CE LXC provisioned, Axiom CE stack running, 2 puppet nodes enrolled
- Gemini tester follows getting-started docs: generates JOIN_TOKEN, enrolls nodes, verifies heartbeat
- Operator path: Python, Bash, PowerShell jobs dispatched and verified COMPLETED with stdout captured
- `checkpoint/FRICTION.md` from CE run with per-step PASS/FAIL log and severity-tagged friction entries
- `checkpoint/STATUS.md: COMPLETE`

**Addresses:** LXC isolation, 3 runtime coverage, per-step log, friction with evidence (P6, P7)

**Avoids:** Running EE before CE baseline is clean; dispatching PowerShell jobs before verifying `pwsh` is in the node image

### Phase 4: EE Cold-Start Run

**Rationale:** Requires a clean CE baseline (shared friction identified and documented). Adds only the EE-specific delta: licence injection, `axiom-ee` package install, EE-gated route verification. `GET /api/licence` assertion must be the first EE check — all EE tests gate on this.

**Delivers:**
- EE LXC provisioned (separate container from CE)
- `inject_ee_licence.py` writes `AXIOM_LICENCE_KEY` to `.env`; `axiom-ee` installed; stack started with EE features active
- First assertion: `GET /api/licence` returns `{"edition": "enterprise"}` (all EE tests gate on this)
- Same 3-runtime job path as CE; plus EE-gated features verified (licence badge, stub routes return 200 not 402)
- `checkpoint/FRICTION.md` from EE run

**Addresses:** EE licence pre-injection, EE badge verification (P6)

**Avoids:** Testing EE routes before licence assertion; restarting stack mid-EE-phase (licence re-validates on start)

### Phase 5: Friction Report Synthesis

**Rationale:** Both FRICTION.md files are required. The synthesis step cannot run until both scenarios are complete. This is the milestone deliverable.

**Delivers:**
- `synthesise_friction.py` pulls FRICTION.md from both LXC containers via `incus file pull`
- `mop_validation/reports/cold_start_friction_report.md`: BLOCKER / NOTABLE / MINOR triage, install friction vs operator friction, CE-only vs EE-only vs shared findings, fix recommendations ordered by severity

**Addresses:** Merged summary with comparison table, friction report quality criteria

### Phase Ordering Rationale

- Phase 1 before all: no LXC = no test. All environmental pitfalls (TLS, networking, AppArmor, Gemini headless) are discovered and resolved here before they can corrupt a test run.
- Phase 2 before Phases 3/4: checkpoint protocol failure mid-run would leave the agent blocked and the run abandoned. Must be tested with a mock round-trip before any real scenario starts.
- Phase 3 before Phase 4: CE establishes the baseline. Shared friction doesn't need re-investigation in EE. EE provisioning depends on a clean CE run confirming the CE stack works.
- Phase 5 after Phases 3 and 4: synthesis is not possible with partial data.

### Research Flags

**Phases needing careful implementation attention (patterns are clear, but implementation details have high failure potential):**
- **Phase 1:** Docker-in-LXC AppArmor behaviour on Ubuntu 24.04 kernel 6.8.x is documented but version-specific; run the `docker run --rm hello-world` acceptance test before proceeding. Caddy TLS SAN with Docker bridge IP requires verifying `SERVER_HOSTNAME` propagation through `entrypoint.sh` before the full stack is provisioned.
- **Phase 2:** Gemini CLI headless acceptance test (`timeout 30 gemini -p "Say hello"`) must pass before any scenario is designed around it. Rate limit tier must be confirmed before Phase 3 starts.

**Phases with standard well-documented patterns (build directly):**
- **Phases 3 and 4:** Job dispatch via `axiom-push` + `POST /api/jobs` is already validated in v11.1. Agent interaction model follows the checkpoint protocol defined in Phase 2.
- **Phase 5:** FRICTION.md merge is a text-processing script; no novel infrastructure.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Gemini CLI headless mode confirmed from official docs; Node.js 20 minimum confirmed; PowerShell fix verified against Containerfile.node source; Playwright --no-sandbox + JWT auth pattern validated in v11.1 |
| Features | HIGH | Derived from docs-as-tests methodology literature and direct inspection of PROJECT.md v14.0 milestone scope; CE/EE split and test matrix well-defined |
| Architecture | HIGH | All components derived from direct codebase inspection of existing LXC patterns; no novel architectural decisions required |
| Pitfalls | HIGH | 8 critical pitfalls identified from direct codebase inspection plus confirmed GitHub issues in Gemini CLI tracker; each has a verified prevention strategy |

**Overall confidence:** HIGH

### Gaps to Address

- **Gemini CLI version pinning:** STACK.md recommends `npm install -g @google/gemini-cli` (always latest stable). PITFALLS.md notes behaviour varies by version (hang fix in v0.23.0). During Phase 1, verify version is >= 0.23.0; if headless hang reproduces, pin to the last known-good version.
- **`axiom-ee` dev wheel availability:** ARCHITECTURE.md lists two options (editable install from bind-mount, or push dev wheel to devpi inside LXC). The correct approach depends on whether `axiom-ee` exists as a separate repository or only as a path on the host filesystem. Confirm during Phase 4 planning — does not block Phases 1-3.
- **Gemini API key tier decision:** Research recommends paid tier (Tier 1) for a full CE+EE run. Whether a paid key is available or the multi-session free-tier approach will be used is an operational decision that must be made before Phase 3 starts.
- **Docs site accessibility from inside LXC:** ARCHITECTURE.md assumes the MkDocs docs container is part of `compose.cold-start.yaml`. Confirm whether `docs/site/` is served by the current Axiom compose stack or requires a separate docs container definition in the cold-start variant.

## Sources

### Primary (HIGH confidence)

- Gemini CLI official docs (headless, configuration, GEMINI.md) — headless mode confirmed, model pinning, context file hierarchy
- Microsoft Learn — Install PowerShell 7 on Ubuntu — direct `.deb` method, version 7.6.0 current (updated 2026-03-12)
- PyPI playwright 1.58.0 — confirmed current version
- `puppeteer/cert-manager/entrypoint.sh` — `SERVER_HOSTNAME` SAN injection confirmed implemented
- `puppeteer/compose.server.yaml` — full service topology; tunnel/DuckDNS services identified for removal in cold-start variant
- `.agent/skills/manage-test-nodes/scripts/manage_node.py` — Incus provisioning pattern (direct inspection)
- `mop_validation/scripts/test_installer_lxc.py` — `incus exec`, `incus file push` helpers; confirmed patterns
- `mop_validation/local_nodes/node_alpha/node-compose.yaml` — `extra_hosts: host.docker.internal:172.17.0.1` confirmed
- `CLAUDE.md` — Python Playwright `--no-sandbox`, JWT via localStorage, form-encoded login, `mop_auth_token` key

### Secondary (MEDIUM confidence)

- Gemini CLI GitHub issues #10722, #16567, #20433 — headless hang behaviour; confirms `ripgrep` dependency and dbus blocking
- Gemini CLI GitHub issue #3485 — model auto-switching bug; confirms `GEMINI_MODEL` env var as reliable pin
- Playwright GitHub issue #4785 — Chromium ignores OS trust store; `certutil` NSS DB or `ignore_https_errors=True` required
- Incus GitHub issue #791 — AppArmor `pivot_root` denial on Ubuntu 24.04 kernel 6.8.x with `security.nesting=true`
- Docs-as-Tests methodology (docsastests.com) — "each doc is a test suite, each procedure a test case, each step an assertion"

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*

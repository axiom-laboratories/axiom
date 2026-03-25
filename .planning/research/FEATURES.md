# Feature Research

**Domain:** First-user readiness fixes — self-hosted job orchestration platform (Axiom v14.1)
**Researched:** 2026-03-25
**Confidence:** HIGH (derived from cold_start_friction_report.md with 24 concrete findings, direct inspection
of current docs files, compose.cold-start.yaml, and axiom-push CLI feature guide; no speculation required)

---

## Context: What v14.1 Covers

v14.1 is a remediation milestone, not feature development. The cold-start friction report identified 12 open
product BLOCKERs, 4 NOTABLEs, 4 ROUGH EDGEs, and 1 MINOR finding that prevent a first-time user from
successfully completing the getting-started flow using only the docs.

The work falls into four concrete categories:

1. **Docs patches** — update markdown files in `docs/docs/getting-started/`
2. **Code patches** — fix `compose.cold-start.yaml`, `Containerfile.node`, and `main.py`
3. **New content** — add CLI dispatch path and signing walkthrough to first-job.md
4. **EE docs clarity** — EE section placement and licence key naming consistency

Each fix item below is categorised, sized, and linked to the specific finding it addresses.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a first-time user following the docs assumes will work. Missing any of these = NOT READY verdict.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Admin password set before first start** | User expects to be able to log in after `docker compose up` | LOW | install.md + compose.cold-start.yaml need a clear `.env` setup step; currently the cold-start compose creates a random password silently |
| **CLI alternative for JOIN_TOKEN generation** | Server environments have no browser; headless setups are common for job orchestration | LOW | Already partially documented in current enroll-node.md (the curl snippet is there), but needs promotion to a primary path, not buried in a warning callout |
| **Correct node image in Option B compose snippet** | Users copy-paste the Option B snippet verbatim; wrong image = node starts and exits immediately with no error | LOW | Docs show `python:3.12-alpine` — must be `localhost/master-of-puppets-node:latest`; one-line fix |
| **EXECUTION_MODE=docker in Option B snippet** | `EXECUTION_MODE=direct` raises RuntimeError in current code; docs still show it | LOW | One-line fix in enroll-node.md Option B example; add explanation that `direct` mode was removed |
| **AGENT_URL that actually works** | Users expect the documented network address to connect; TLS cert mismatch = silent node failure | LOW | `172.17.0.1:8001` fails TLS SAN validation; `https://agent:8001` works when node is in the same Compose network; update the Linux Docker row in the connectivity table |
| **CLI/curl dispatch path in first-job.md** | CI/CD pipelines and headless deployments cannot use a browser form; first-job docs must not require the dashboard | MEDIUM | Add a Step 4b with curl POST /api/jobs example showing signed payload structure; this is the most content-heavy fix |
| **Ed25519 signing walkthrough accessible to fresh users** | Signing is required before any job runs; fresh stack has no keys registered | MEDIUM | Add explicit sequence: (1) generate keypair with openssl or axiom-push, (2) register via API or dashboard, (3) sign and dispatch; make axiom-push the recommended path over manual openssl |
| **No signing key pre-registered note** | Fresh stack returns `[]` from GET /signatures; first dispatch silently creates PENDING jobs that nodes SECURITY_REJECT | LOW | Add a pre-dispatch checklist callout to first-job.md: "confirm GET /signatures returns at least one entry before dispatching" |
| **EE section in getting-started/install.md** | EE users follow the install guide first; they look for EE instructions there, not in licensing.md | LOW | Current install.md has an EE section (AXIOM_LICENCE_KEY in secrets.env); friction report found the EE-gated Execution History content was hard to find — ensure cross-link from install to licensing.md is visible |
| **AXIOM_LICENCE_KEY naming consistency** | Env var name appears as `AXIOM_EE_LICENCE_KEY` in one scenario script; confuses users debugging licence activation | LOW | Audit all docs for `AXIOM_EE_LICENCE_KEY` and replace with the correct `AXIOM_LICENCE_KEY`; also fix licensing.md |
| **Docker socket mounted in cold-start node services** | compose.cold-start.yaml sets `EXECUTION_MODE=docker` but node services must have `/var/run/docker.sock` to execute jobs | LOW | The current compose.cold-start.yaml already mounts `/var/run/docker.sock` and `/tmp:/tmp` on both puppet-node services (fixed during run) — verify the source file is correct and document the requirement |
| **Docs path correct in GEMINI.md / scenario files** | Scenario file pointed to wrong path; docs unreachable from inside LXC | LOW | Already fixed during run (GEMINI.md updated) — verify fix is in source, not just applied at runtime |

### Differentiators (What Makes the Fix Quality High)

Fixes that go beyond "minimum acceptable" to genuinely good first-user experience.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **axiom-push as the recommended signing path in first-job.md** | CLI handles signing in one command vs 3 openssl steps; reduces error surface; aligns getting-started with the product's own CLI | LOW | Current first-job.md shows manual openssl with a tip callout about axiom-push; should invert: axiom-push first, openssl as the manual fallback |
| **Concrete curl examples with real flag names** | "Use the API" is not actionable; verbatim curl commands with correct Content-Type and Authorization headers are copy-paste runnable | LOW | The CLI dispatch path needs a full curl example showing the POST /api/jobs JSON body with script, signature, signature_key_id, and task_type fields |
| **AGENT_URL connectivity table expanded** | Current table has 3 rows; a cold-start Docker-in-Docker user needs the `https://agent:8001` case made explicit with a note about needing the same Compose network | LOW | Add row: "Cold-start compose (puppet-node in same stack) → https://agent:8001" to the AGENT_URL table |
| **Signing key setup as a numbered prerequisite, not buried in Step 3** | Signing is a blocker; if encountered mid-flow it halts progress; surfacing it before dispatch removes a common checkpoint failure | LOW | Restructure first-job.md: Step 1 (generate keypair), Step 2 (register public key), Step 3 (write and sign), Step 4 (dispatch) — current structure buries keypair generation inside Step 1 |
| **axiom-push install from PyPI, not from repo clone** | Cold-start users do not have the source repo; pip install axiom-sdk is the correct path; install.md should not assume git clone | MEDIUM | axiom-sdk is published to PyPI; getting-started should show `pip install axiom-sdk` with a note about the package name vs CLI binary name |
| **/api/executions CE-gating decision documented** | Execution History returns HTTP 200 in CE mode; the friction report flagged this; teams need clarity on whether this is intentional | LOW | CODE FIX: either add `require_ee_licence()` to `GET /api/executions` in main.py, or explicitly document that Execution History is CE-available and update EE scenario to not check for 402 |

### Anti-Features (Explicitly Avoid)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-generating signing keys at first start** | Removes the "no key registered" blocker silently | Masks the security model from users; auto-generated key means no one controls it; if a key is auto-generated on every fresh deploy, signing is effectively bypassed | Require explicit key setup; document it clearly in first-job.md as Step 1; never generate and auto-register silently |
| **Making EXECUTION_MODE default to "direct"** | Simplifies node setup for Docker-in-Docker | `direct` mode was deliberately removed (raises RuntimeError); reverting it would re-introduce the nested subprocess security boundary hole | Keep `EXECUTION_MODE=docker` as the default; document it clearly |
| **Providing an unsigned job dispatch path** | Makes getting started easier without a keypair | Completely breaks the security model — Ed25519 verification is a non-negotiable architectural constant | Improve the signing UX (axiom-push CLI) so setup is fast; do not bypass verification |
| **Putting all CE and EE docs in separate files** | "Clear separation" seems logical | Forces users to figure out which edition they have before reading anything; shared steps must be duplicated; gets out of sync | Use tabbed sections or conditional admonitions within shared files (the current `!!! enterprise` pattern is correct) |
| **Detailed troubleshooting before first-run steps** | Comprehensive docs are good | Cognitive overload for first-time users; troubleshooting before they've tried anything is noise | Keep getting-started guides linear and minimal; link to troubleshooting runbooks at the end |

---

## Fix Items Enumerated

### Category A: Docs Patches (markdown edits to existing files)

All LOW complexity unless noted. These are text changes with no code dependency.

| Fix ID | File | Finding | What to Change |
|--------|------|---------|----------------|
| A-01 | `docs/getting-started/install.md` | Admin password not set | Add a Step 0 or pre-start callout: create `.env` with `ADMIN_PASSWORD=<value>` before running `docker compose up`; show the two required vars (ADMIN_PASSWORD + ENCRYPTION_KEY) with generate commands |
| A-02 | `docs/getting-started/install.md` | Docs assume GitHub clone | Add alternative for pre-built / downloaded tarball path; or make git clone conditional ("if you have the source repo") and add a note for pre-built installers |
| A-03 | `docs/getting-started/install.md` | No EE section visible | The EE section exists but may need a clearer heading; ensure it appears before the "Next" link not after it; cross-link to licensing.md explicitly |
| A-04 | `docs/getting-started/install.md` | AXIOM_LICENCE_KEY injection inconsistency | Standardise on `--env-file .env` pattern for cold-start compose; add a note that `secrets.env` is for compose.server.yaml, `.env` is for compose.cold-start.yaml |
| A-05 | `docs/getting-started/enroll-node.md` | JOIN_TOKEN requires GUI | Promote the CLI alternative from a buried callout to a parallel Step 1B with equal prominence as the dashboard Step 1A |
| A-06 | `docs/getting-started/enroll-node.md` | Wrong node image | Replace `python:3.12-alpine` with `localhost/master-of-puppets-node:latest` in Option B snippet |
| A-07 | `docs/getting-started/enroll-node.md` | EXECUTION_MODE=direct removed | Replace `EXECUTION_MODE: direct` with `EXECUTION_MODE: docker` in Option B snippet; update the explanatory tip to explain docker socket mount is required |
| A-08 | `docs/getting-started/enroll-node.md` | TLS cert mismatch on 172.17.0.1 | Update Linux Docker row in AGENT_URL table from `172.17.0.1:8001` to `https://agent:8001`; add a cold-start compose row; explain the SAN constraint briefly |
| A-09 | `docs/getting-started/enroll-node.md` | Docker socket not in compose | Add a note to Option B that `/var/run/docker.sock:/var/run/docker.sock` volume must be present when EXECUTION_MODE=docker |
| A-10 | `docs/getting-started/first-job.md` | No CLI dispatch path | Add Step 4B: curl POST /api/jobs with a complete signed job JSON payload; show how to base64-encode signature; include Content-Type and Authorization headers |
| A-11 | `docs/getting-started/first-job.md` | Signing undocumented for cold-start | Restructure: keypair generation is Step 1, public key registration is Step 2 (both explicit); add axiom-push as the recommended tool; keep openssl as the manual alternative |
| A-12 | `docs/getting-started/first-job.md` | No key pre-registered | Add pre-dispatch prerequisite callout: "Before dispatching any job, verify `GET /api/signatures` returns at least one key. If empty, complete Step 1–2 first." |
| A-13 | `docs/licensing.md` | AXIOM_EE_LICENCE_KEY naming mismatch | Replace any `AXIOM_EE_LICENCE_KEY` occurrences with `AXIOM_LICENCE_KEY`; add a note clarifying the correct env var name |

### Category B: Code Patches

Require file edits outside `docs/`. Mostly already fixed during the v14.0 run but the source files need verification.

| Fix ID | File | Finding | What to Change |
|--------|------|---------|----------------|
| B-01 | `puppets/Containerfile.node` | Docker CLI missing | Install `docker-ce-cli` from Docker's apt repo, not `docker.io` (Debian 13 package); current file should already have this from the during-run fix — verify |
| B-02 | `puppets/Containerfile.node` | Wrong image tag default | Ensure node is tagged as `localhost/master-of-puppets-node:latest` in cold-start build; verify the tag instruction in Containerfile.node or compose.cold-start.yaml build block |
| B-03 | `puppets/Containerfile.node` | PowerShell missing | Add PowerShell 7.x via direct .deb from GitHub releases + `ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`; verify this is in the current file |
| B-04 | `puppeteer/compose.cold-start.yaml` | DinD /tmp mount missing | puppet-node-1 and puppet-node-2 must have `- /tmp:/tmp` volume mount; verify current file has it (added during run) |
| B-05 | `puppeteer/agent_service/main.py` | /api/executions CE-gated NOTABLE | Decision required: add `require_ee_licence()` dependency to `GET /api/executions` route (lines 231–) if Execution History is EE-only; OR document CE availability and update EE test scenario |

### Category C: EE-Specific Doc Gaps

| Fix ID | File | Finding | What to Change |
|--------|------|---------|----------------|
| C-01 | `docs/getting-started/ee-install.md` (if exists) or `install.md` | /api/admin/features does not exist | Replace any reference to `GET /api/admin/features` with `GET /api/features` for EE verification steps |
| C-02 | `docs/getting-started/install.md` | EE section structure | Ensure EE section content flows logically from CE install: "If you have a licence key, add it here — no additional install steps required" |

---

## Feature Dependencies

```
[A-01: Admin password setup]
    └──required-before──> [A-05: JOIN_TOKEN CLI path]
    └──required-before──> [A-10: CLI dispatch]

[A-06: Correct node image]
    └──required-for──> [A-08: Correct AGENT_URL]
    (both in enroll-node.md — fix together)

[A-11: Signing key setup restructure]
    └──required-before──> [A-10: CLI dispatch path]
    └──required-before──> [A-12: No key pre-registered callout]

[B-01, B-02, B-03: Containerfile.node fixes]
    └──required-for──> [B-04: compose.cold-start.yaml /tmp mount]
    (all cold-start runtime fixes — fix together)

[B-05: /api/executions CE decision]
    └──independent-of──> all doc patches
    (code decision required before C-01/C-02 EE doc can be finalised)
```

### Dependency Notes

- **A-01 must be done before A-05**: If the admin password step is correct, the CLI JOIN_TOKEN path in A-05
  depends on it — the curl login example needs the correct password strategy to be in place.
- **B-05 is a decision point, not a pure fix**: Someone must decide if Execution History is CE or EE. The
  docs cannot be finalised for the EE section until this is decided. Recommend treating as CE (the feature
  is implemented, CE users benefit, EE justification for gating is weak). Document this decision.
- **Category B fixes should be verified before Category A is finalised**: If B-01/B-03 are not in the
  current Containerfile.node, the cold-start node image won't work regardless of what the docs say.

---

## MVP Definition

This milestone is itself an MVP — the goal is "first user can complete CE getting-started in one session
without steering interventions." That requires ALL 12 BLOCKERs resolved and at least the 2 most-impactful
NOTABLEs addressed.

### Required for READY Verdict (v14.1 launch criteria)

- [ ] A-01: Admin password setup step in install.md
- [ ] A-05: CLI JOIN_TOKEN path promoted in enroll-node.md
- [ ] A-06: Correct node image in Option B snippet
- [ ] A-07: EXECUTION_MODE=docker (remove `direct` reference)
- [ ] A-08: AGENT_URL table corrected (remove 172.17.0.1 as primary recommendation)
- [ ] A-10: curl dispatch path added to first-job.md
- [ ] A-11: Signing key walkthrough restructured as explicit prerequisites
- [ ] A-12: Pre-dispatch key registration callout
- [ ] B-01, B-02, B-03: Containerfile.node fixes verified in source
- [ ] B-04: /tmp mount verified in compose.cold-start.yaml
- [ ] C-01: /api/admin/features reference removed (EE docs)

### Add After Core Fixes (nice-to-have for first-user experience)

- [ ] A-02: GitHub clone alternative (useful but not blocking for users who have the repo)
- [ ] A-03: EE section cross-link polish in install.md
- [ ] A-04: AXIOM_LICENCE_KEY injection consistency note
- [ ] A-09: Docker socket volume note in enroll-node.md
- [ ] A-13: AXIOM_EE_LICENCE_KEY naming audit in licensing.md
- [ ] C-02: EE install section content flow review
- [ ] B-05: /api/executions CE/EE decision (needed for correctness but not a first-user blocker)

### Defer

- None — this milestone is all remediation of known gaps; nothing here should be deferred beyond v14.1.

---

## Feature Prioritization Matrix

| Fix | User Value | Implementation Cost | Priority |
|-----|------------|---------------------|----------|
| A-01 Admin password setup | HIGH (login blocker) | LOW | P1 |
| A-05 CLI JOIN_TOKEN path | HIGH (headless blocker) | LOW | P1 |
| A-06 Correct node image | HIGH (node silently fails) | LOW | P1 |
| A-07 EXECUTION_MODE=docker | HIGH (RuntimeError blocker) | LOW | P1 |
| A-08 AGENT_URL correction | HIGH (TLS failure) | LOW | P1 |
| A-10 curl dispatch path | HIGH (no browser = no dispatch) | MEDIUM | P1 |
| A-11 Signing restructure | HIGH (signing is required; hidden) | MEDIUM | P1 |
| A-12 Pre-dispatch callout | HIGH (SECURITY_REJECTED confusion) | LOW | P1 |
| B-01 docker-ce-cli in Containerfile | HIGH (job execution fails) | LOW | P1 |
| B-02 node image tag | HIGH (runtime.py default mismatch) | LOW | P1 |
| B-03 PowerShell in Containerfile | HIGH (3rd runtime unavailable) | LOW | P1 |
| B-04 /tmp mount in compose | HIGH (DinD script mount fails) | LOW | P1 |
| C-01 /api/admin/features fix | HIGH (EE verify step fails) | LOW | P1 |
| A-09 Docker socket note | MEDIUM (confusing but not immediately blocking) | LOW | P2 |
| A-02 GitHub clone alternative | MEDIUM (rough edge, not a BLOCKER) | LOW | P2 |
| A-13 AXIOM_EE_LICENCE_KEY naming | MEDIUM (confusing env var name) | LOW | P2 |
| A-04 LICENCE_KEY injection consistency | MEDIUM (two valid methods exist) | LOW | P2 |
| A-03 EE section cross-link | LOW (section exists, just hard to find) | LOW | P2 |
| B-05 /api/executions CE decision | MEDIUM (correctness gap) | MEDIUM | P2 |
| C-02 EE section flow review | LOW (polish) | LOW | P3 |

**Priority key:**
- P1: Must complete for READY verdict — blocks first-user success
- P2: Should fix in v14.1 — eliminates friction but not a hard blocker
- P3: Nice to have — polish; can slip to v14.2 if timeline is tight

---

## Signing Workflow Pattern for CLI Users

The friction report found that the Ed25519 signing path was the most common NOTABLE gap. The correct
pattern for a CLI-first user (no dashboard) is:

```
1. Generate keypair:
   openssl genpkey -algorithm ed25519 -out signing.key
   openssl pkey -in signing.key -pubout -out verification.key

   -- OR (preferred) --
   pip install axiom-sdk
   axiom-push --generate-key
   # Creates signing.key and verification.key in current directory

2. Register public key via API:
   TOKEN=$(curl -sk -X POST https://<host>:8443/auth/login \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'username=admin&password=<password>' \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

   curl -sk -X POST https://<host>:8443/api/signatures \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"name\": \"my-key\", \"public_key\": \"$(cat verification.key)\"}"

3. Note the key_id from the response.

4. Sign and dispatch:
   # Manual openssl signing:
   openssl pkeyutl -sign -inkey signing.key -rawin -in hello.py -out hello.py.sig
   SIG=$(base64 -w0 hello.py.sig)
   SCRIPT=$(cat hello.py)

   curl -sk -X POST https://<host>:8443/api/jobs \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"script\": \"$SCRIPT\", \"signature\": \"$SIG\", \"signature_key_id\": \"<key_id>\", \"task_type\": \"script\", \"runtime\": \"python\"}"

   -- OR (preferred, handles escaping automatically) --
   axiom-push login  # approve in browser once
   axiom-push job push --script hello.py --key signing.key --key-id <key_id>
```

The cold-start friction report found that the server generates its own signing key at startup
(`/app/secrets/signing.key`) but this is NOT automatically registered in the signatures table. Operators
must generate their OWN keypair and register it. This distinction must be explicit in the docs.

---

## CE vs EE Documentation Structure

**Recommended approach (confirmed by current docs pattern):** Shared files with conditional sections.

The current `!!! enterprise` admonition pattern in MkDocs Material is correct:
- CE users see all content and understand EE admonitions mean "not available in your edition"
- EE users see the same content without confusion
- No duplication of shared installation steps
- Single source of truth for both editions

**What needs fixing (from friction report):**
- EE getting-started content is split between `install.md` (licence key) and `licensing.md` (how it works)
- A first-time EE user following install.md does not see the verification step until they navigate away
- Fix: add a brief "Verify EE is active" section to install.md after the AXIOM_LICENCE_KEY step, showing
  `GET /api/features` response with `"edition": "enterprise"` — do not require navigating to licensing.md
  for the core activation verification

**What to avoid:**
- Do NOT create a separate `ee-install.md` in getting-started — this was the pattern that led to the
  `/api/admin/features` stale reference (a separate EE doc that drifted from the actual API)
- EE-specific getting-started content belongs in the existing files with `!!! enterprise` admonitions

---

## curl Dispatch Path Design

The CLI/API dispatch alternative for first-job.md should cover:

**Minimum viable curl example** (what goes in the docs):
```bash
# 1. Get a token
TOKEN=$(curl -sk -X POST https://<host>:8443/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<password>' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Sign the script
openssl pkeyutl -sign -inkey signing.key -rawin -in hello.py -out hello.py.sig
SIG=$(base64 -w0 hello.py.sig)

# 3. Dispatch
curl -sk -X POST https://<host>:8443/api/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"hello-test\",
    \"task_type\": \"script\",
    \"runtime\": \"python\",
    \"script\": \"$(cat hello.py | python3 -c 'import sys; print(sys.stdin.read().replace(chr(34),chr(92)+chr(34)).replace(chr(10),chr(92)+"n")' )\",
    \"signature\": \"$SIG\",
    \"signature_key_id\": \"<key_id_from_step_2>\"
  }"
```

**Notes for the docs author:**
- The JSON escaping of a multiline Python script in bash is fragile — the docs should acknowledge this and
  recommend `axiom-push` for anything beyond trivial one-liners
- The `task_type: "script"` and `runtime: "python"` fields are both required (unified script type from v12.0)
- Port is 8443 when using Caddy (compose.cold-start.yaml) not 8001 (direct to agent)
- The response body includes a `guid` field — show how to check status with `GET /api/jobs/{guid}`

---

## Sources

- `/home/thomas/Development/mop_validation/reports/cold_start_friction_report.md` — Primary source:
  24 concrete findings with reproduction steps and fix recommendations — HIGH confidence
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/install.md` — Current state
  of install guide (partially updated) — HIGH confidence
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/enroll-node.md` — Current state
  of enroll-node guide (partially updated from during-run fixes) — HIGH confidence
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/first-job.md` — Current state
  of first-job guide — HIGH confidence
- `/home/thomas/Development/master_of_puppets/docs/docs/feature-guides/axiom-push.md` — Full axiom-push
  CLI workflow including Ed25519 setup — HIGH confidence
- `/home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml` — Current compose file
  (includes /tmp mount and docker socket mounts from during-run fixes) — HIGH confidence
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/main.py` lines 231–296 — Confirms
  /api/executions is not EE-gated — HIGH confidence
- `/home/thomas/Development/master_of_puppets/.planning/PROJECT.md` — v14.1 milestone scope, all 20
  open finding items — HIGH confidence

---

*Feature research for: Axiom v14.1 — First-User Readiness Fixes*
*Researched: 2026-03-25*

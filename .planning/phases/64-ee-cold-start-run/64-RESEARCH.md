# Phase 64: EE Cold-Start Run - Research

**Researched:** 2026-03-25
**Domain:** EE plugin delivery, licence injection, LXC/Docker stack reset, Gemini tester orchestration
**Confidence:** HIGH

## Summary

Phase 64 is a direct parallel to Phase 63 but for EE. The same execution pattern — image rebuild on host, push to LXC via `docker save | docker load`, full cold-start reset with volumes wiped, then two operator-gated Gemini scenario runs — applies unchanged. The difference is EE-specific: the server image must include `axiom-ee==0.1.0` compiled for Alpine/musl (Python 3.12 x86_64), the `.env` inside the LXC must contain `AXIOM_LICENCE_KEY` from `mop_validation/secrets.env`, and a CE-gating confirmation step (remove key, restart orchestrator, confirm 402) closes the EE run.

The critical planning question from STATE.md — "axiom-ee wheel availability inside LXC — confirm editable install path vs devpi" — is resolved: the wheel is built and present at `/home/thomas/Development/axiom-ee/wheelhouse/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl`. The server `Containerfile.server` already supports `ARG EE_INSTALL=1` with `DEVPI_URL`/`DEVPI_HOST` overrides. The plan must COPY the wheel into the build context and install it locally rather than pulling from devpi (devpi is not running in the cold-start compose). An alternative is to COPY the wheel file and `pip install` it directly — simpler than devpi for a cold-start scenario.

**Primary recommendation:** Three plans — (1) EE image rebuild + LXC reload + EE reset with licence injection, (2) `ee-install` Gemini run, (3) `ee-operator` Gemini run + CE-gating confirmation + FRICTION pull. Reuse `run_ce_scenario.py` primitives; write a parallel `run_ee_scenario.py` to avoid mutating the CE module.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**axiom-ee delivery:**
- axiom-ee is pre-baked into the same cold-start agent image used for CE — one image for both editions
- EE plugin stays dormant on CE runs (no licence key); activates automatically when `AXIOM_LICENCE_KEY` is present at startup
- No runtime `pip install` step needed — the package is already installed inside the image
- Phase 64 rebuilds the image from source at plan start (`docker build -t localhost/axiom-node:cold-start`) to ensure all Phase 63-04 fixes and EE package are included
- After rebuild, image is pushed into the LXC via `docker save | incus exec axiom-coldstart -- docker load`
- Smoke check before stack start: `docker run --rm localhost/axiom-node:cold-start python -c "import ee.plugin"` inside the LXC — fails fast if EE is missing from the image

**Licence key injection:**
- Phase 64 reset script reads `AXIOM_EE_LICENCE_KEY` from `mop_validation/secrets.env` on the host
- Writes it to `/workspace/.env` inside the LXC as `AXIOM_LICENCE_KEY=<value>` — compose.cold-start.yaml picks it up automatically
- Same pattern as `ADMIN_PASSWORD` injection established in Phase 61/63
- Full cold-start reset: `docker compose down -v` (wipes certs and state), then `docker compose up -d` with the `.env` containing the licence key
- Nodes re-enroll from scratch — true cold-start baseline, not reusing CE node state

**CE blocker carry-forward:**
- All 5 CE blockers are baked into source — no runtime re-patching needed:
  - Docker CLI: `COPY --from=docker:cli` in `Containerfile.node`
  - PowerShell: `.deb` install + `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` in `Containerfile.node`
  - DinD `/tmp` mount: `- /tmp:/tmp` in both node services in `compose.cold-start.yaml`
  - `JOB_IMAGE`: set to `localhost/axiom-node:cold-start` in compose
  - Node enrollment docs: fixed in Phase 63-04
- Image rebuild at Phase 64 start incorporates all fixes automatically

**EE feature verification:**
- Target feature: Execution History (navigate to History view, confirm execution records with timing data visible for at least one completed job)
- Execution History is EE-gated (CE returns 402 on `GET /api/executions`)
- CE gating confirmation step added after EE run: remove `AXIOM_LICENCE_KEY` from `.env`, restart the orchestrator container, confirm `GET /api/executions` returns 402 — proves EE was genuinely active during the run
- This step is orchestrator-run (not Gemini), appended to the operator scenario plan

**Scenario sequencing:**
- Same as Phase 63: two separate operator-confirmed invocations — `ee-install` first, then `ee-operator`
- Operator reviews `FRICTION-EE-INSTALL.md` and confirms EE loaded (`ee_status: loaded` API + dashboard badge visible) before `ee-operator` begins
- Checkpoint policy carried forward: max 3 interventions per scenario, 4th = ABORT

### Claude's Discretion
- Exact structure of the Phase 64 reset script (extend Phase 63 pattern or standalone)
- Whether CE gating confirmation restarts just the orchestrator container or the full stack
- How the licence key removal step is surfaced to the operator (inline in plan, or as a post-scenario verification task)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EE-01 | Gemini agent follows EE install docs with pre-generated licence injected — EE plugin installed, all EE feature flags active, licence badge visible in dashboard | `ee-install.md` scenario ready; `AXIOM_EE_LICENCE_KEY` in secrets.env; docs EE section added; smoke check pattern established |
| EE-02 | Gemini agent dispatches and verifies Python, Bash, and PowerShell jobs via EE operator path; execution confirmed in job history | `ee-operator.md` scenario ready; all 3 runtimes working in CE Phase 63-03 with CE blockers now baked in |
| EE-03 | Gemini agent exercises at least one EE-gated feature — Execution History selected; `GET /api/executions` returns records (not 402) when EE active | Execution History route confirmed in main.py; CE returns 402 via stub router; EE active = records returned |
| EE-04 | EE `FRICTION.md` produced to same standard as CE-05, with EE-specific findings annotated `[EE-ONLY]` | `tester-gemini.md` FRICTION template includes `[EE-ONLY]` annotation convention; two output files: `FRICTION-EE-INSTALL.md` and `FRICTION-EE-OPERATOR.md` |
</phase_requirements>

## Standard Stack

### Core
| Component | Version/Location | Purpose | Status |
|-----------|-----------------|---------|--------|
| `run_ce_scenario.py` | `mop_validation/scripts/` | incus_exec, incus_push, incus_pull, wait_for_stack, reset_stack, run_gemini_scenario, pull_friction | Existing — reuse as-is |
| `axiom-ee` wheel | `~/Development/axiom-ee/wheelhouse/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl` | EE plugin for Alpine/musl Python 3.12 x86_64 | Built and ready |
| `axiom-ee` wheel (pure-py fallback) | `~/Development/axiom-ee/dist/axiom_ee-0.1.0.dev0-py3-none-any.whl` | Non-Cython fallback | Available |
| `compose.cold-start.yaml` | `puppeteer/compose.cold-start.yaml` | Already reads `AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` on agent service | No changes needed |
| `Containerfile.server` | `puppeteer/Containerfile.server` | Supports `ARG EE_INSTALL=1` + DEVPI_URL/DEVPI_HOST for wheel install | Needs COPY + local pip install approach |
| `ee-install.md` | `mop_validation/scenarios/ee-install.md` | Gemini EE install scenario | Ready |
| `ee-operator.md` | `mop_validation/scenarios/ee-operator.md` | Gemini EE operator + Execution History | Ready |
| `AXIOM_EE_LICENCE_KEY` | `mop_validation/secrets.env` line 15 | 1-year cold-start test licence | Present |
| `monitor_checkpoint.py` | `mop_validation/scripts/` | Checkpoint relay — PROMPT.md detection, RESPONSE.md push | Used as-is |
| `setup_agent_scaffolding.py` | `mop_validation/scripts/` | HOME isolation + tester GEMINI.md | Used as-is |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `verify_ee_install.py` | Standalone EE install verifier (valid/expired/absent cases) | Reference for what API calls to make during CE-gating confirmation |
| `verify_ee_pass.py` | EE acceptance criteria verifier | Reference for EE feature route checks |
| `incus exec axiom-coldstart -- bash -c "..."` | LXC command execution | All in-LXC operations |

## Architecture Patterns

### EE Image Build Pattern

The server `Containerfile.server` has a devpi-based EE install path (`ARG EE_INSTALL=1`, `DEVPI_URL`, `DEVPI_HOST`). Devpi is not in the cold-start compose — it's only in `compose.server.yaml`. For Phase 64, the approach is to COPY the pre-built wheel into the build context and install it directly.

**Why COPY + local install, not devpi:**
- Devpi service is absent from `compose.cold-start.yaml` — would require a new service
- The wheel is already built and locally available at `~/Development/axiom-ee/wheelhouse/`
- Local install avoids network-dependent devpi startup in the LXC build context

**Correct wheel for server container:**
- Server uses `python:3.12-alpine` (Alpine/musl libc)
- Required wheel: `axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl`
- Location: `/home/thomas/Development/axiom-ee/wheelhouse/`

**Build modification approach:**
The `Containerfile.server` already has a conditional `RUN if [ -n "${EE_INSTALL}" ]` block. The plan adds a `COPY` step before it and changes the `pip install` to use the local wheel path rather than devpi:

```dockerfile
# Phase 64 pattern: COPY wheel into build context, install locally (no devpi needed)
ARG EE_INSTALL=
COPY wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl /tmp/axiom_ee.whl
RUN if [ -n "${EE_INSTALL}" ]; then \
    pip install --no-cache-dir /tmp/axiom_ee.whl; \
  fi
```

The wheel must be copied to `puppeteer/wheels/` before building (within the Containerfile's build context, which is `puppeteer/`).

**Build command:**
```bash
# Copy wheel into build context
mkdir -p /home/thomas/Development/master_of_puppets/puppeteer/wheels/
cp /home/thomas/Development/axiom-ee/wheelhouse/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl \
   /home/thomas/Development/master_of_puppets/puppeteer/wheels/

# Build server image with EE installed (EE_INSTALL=1 activates the RUN block)
docker compose -f puppeteer/compose.cold-start.yaml build \
  --build-arg EE_INSTALL=1 agent
```

### EE Smoke Check Pattern

```bash
# Verify EE plugin installed and importable in built image
docker run --rm localhost/master-of-puppets-server:v3 \
  python -c "import ee.plugin; print('EE OK')"

# Verify inside LXC after image reload
incus exec axiom-coldstart -- bash -c \
  "docker run --rm localhost/master-of-puppets-server:v3 \
   python -c \"import ee.plugin; print('EE OK')\""
```

Note: The CONTEXT.md smoke check uses `localhost/axiom-node:cold-start` — that is the NODE image. The EE plugin lives in the SERVER image (`localhost/master-of-puppets-server:v3`). The smoke check should target the server image.

### Licence Injection Pattern

```bash
# On host: read AXIOM_EE_LICENCE_KEY from secrets.env
LICENCE=$(grep '^AXIOM_EE_LICENCE_KEY=' /home/thomas/Development/mop_validation/secrets.env | cut -d= -f2-)

# Write /workspace/.env inside LXC (compose reads this via --env-file .env)
incus exec axiom-coldstart -- bash -c \
  "echo 'AXIOM_LICENCE_KEY=$LICENCE' >> /workspace/.env"

# Verify it's written
incus exec axiom-coldstart -- bash -c "grep AXIOM_LICENCE_KEY /workspace/.env"
```

The `compose.cold-start.yaml` agent service already has `AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` in its `environment:` block. It reads this from the shell environment or from an `--env-file`. Writing to `/workspace/.env` and starting with `docker compose --env-file .env up -d` is the correct pattern.

**Important:** The `reset_stack()` function in `run_ce_scenario.py` uses `docker compose up -d` without `--env-file`. The EE reset function must use `--env-file .env` to pick up the licence key.

### CE-Gating Confirmation Pattern

```python
# After ee-operator scenario completes:
# 1. Remove licence key from .env
incus_exec("sed -i '/AXIOM_LICENCE_KEY/d' /workspace/.env")

# 2. Restart only the agent container (not full stack — nodes stay enrolled)
incus_exec("cd /workspace && docker compose -f compose.cold-start.yaml restart agent", timeout=60)

# 3. Wait for agent to be responsive
time.sleep(10)

# 4. Confirm GET /api/executions returns 402 (CE stub active)
result = incus_exec(
    "curl -k -s -o /dev/null -w '%{http_code}' "
    "-H 'Authorization: Bearer <admin_token>' "
    "https://172.17.0.1:8001/api/executions"
)
# Expected: "402"
```

Note: The CE-gating confirmation needs an admin JWT. The plan should obtain this via `POST /auth/login` immediately before performing the gating check.

### FRICTION File Pull Pattern (EE variant)

```python
# Adapted from run_ce_scenario.py pull_friction()
def pull_ee_friction(scenario_id: str, reports_dir: str) -> bool:
    container_path = f"/workspace/FRICTION-EE-{scenario_id}.md"
    local_path = f"{reports_dir}/FRICTION-EE-{scenario_id}.md"
    return incus_pull(container_path, local_path)
```

### EE-Specific API Endpoints to Verify

| Endpoint | CE behaviour | EE behaviour | How to confirm |
|----------|-------------|--------------|----------------|
| `GET /api/features` | All false | All true | JSON all values `true` |
| `GET /api/licence` | `{"edition": "community"}` | `{"edition": "enterprise", "customer_id": "axiom-coldstart-test", ...}` | `edition == "enterprise"` |
| `GET /api/executions` | 402 (CE stub) | 200 + records | Status code 200 |
| Dashboard sidebar | "CE" badge | "EE" badge | Visual (Gemini confirms) |

**`GET /api/admin/features` vs `GET /api/features`:**
The `ee-install.md` scenario checklist uses `GET /api/admin/features` — verify this route exists. The confirmed route in `main.py` is `GET /api/features`. The scenario may use the wrong path; the plan should confirm Gemini is guided to the correct one.

Checking `main.py`:

```
GET /api/features  → returns feature flags (EEContext) — CONFIRMED line 903
GET /api/admin/features → NOT confirmed in main.py
```

This is a potential friction point. If `GET /api/admin/features` returns 404, Gemini will checkpoint. The EE-install scenario checklist says `GET /api/admin/features` returns `"ee_status": "loaded"` — this does not match the actual API which returns `{"audit": true, ...}` from `GET /api/features`. This discrepancy needs to be noted as a research finding.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC command execution | New subprocess wrapper | `incus_exec()` from `run_ce_scenario.py` | Already proven in Phase 63 |
| File transfer to/from LXC | New push/pull helpers | `incus_push()` / `incus_pull()` from `run_ce_scenario.py` | Already proven |
| Stack readiness polling | New polling loop | `wait_for_stack()` from `run_ce_scenario.py` | Already proven |
| Checkpoint monitoring | New file watcher | `monitor_checkpoint.py` | Already proven in Phase 63 |
| Tester persona setup | New setup script | `setup_agent_scaffolding.py` | Already proven |
| EE feature verification | New checker | Reference `verify_ee_install.py` case_valid() | API patterns already worked out |

## Common Pitfalls

### Pitfall 1: Smoke check targets wrong image
**What goes wrong:** `import ee.plugin` must be checked on the SERVER image (`localhost/master-of-puppets-server:v3`), not the node image (`localhost/axiom-node:cold-start`). The CONTEXT.md smoke check example uses the node image — this would always succeed vacuously (no import happens).
**How to avoid:** Always run the smoke check with `docker run --rm localhost/master-of-puppets-server:v3 python -c "import ee.plugin"`

### Pitfall 2: compose up without --env-file loses the licence key
**What goes wrong:** `run_ce_scenario.py`'s `reset_stack()` does `docker compose up -d` without `--env-file .env`. If the EE reset function reuses this pattern, `AXIOM_LICENCE_KEY` will be empty in the agent container even if written to `/workspace/.env`.
**How to avoid:** The EE reset function must use `docker compose --env-file .env up -d`. Alternatively, write `AXIOM_LICENCE_KEY` directly into the compose environment section or use `docker compose config` to verify the variable is being injected.
**Detection:** After stack start, check `incus exec axiom-coldstart -- docker exec workspace-agent-1 env | grep AXIOM_LICENCE_KEY` — if empty, the key is not being passed.

### Pitfall 3: /api/admin/features path mismatch
**What goes wrong:** `ee-install.md` scenario references `GET /api/admin/features` returning `"ee_status": "loaded"`. The actual route in `main.py` is `GET /api/features` returning `{"audit": true, "foundry": true, ...}`. If Gemini calls `/api/admin/features` it will get a 404, triggering a checkpoint.
**Impact:** Immediate checkpoint on the install scenario's verification step.
**How to avoid:** Plan should include a pre-scenario check: verify `/api/admin/features` either exists or doesn't, and if it doesn't, update the scenario file before launching Gemini. Alternatively, accept this as an EE-specific friction point to be captured in `FRICTION-EE-INSTALL.md`.

### Pitfall 4: Cython wheel architecture mismatch
**What goes wrong:** Using the wrong wheel for the server container. The server runs Alpine/musl; a manylinux wheel will fail to load. The `.dev0` pure-Python wheel may work but lacks Cython compilation protection.
**Correct wheel:** `axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl` from the `wheelhouse/` directory.
**Detection:** `docker run --rm localhost/master-of-puppets-server:v3 python -c "import ee.plugin"` fails if wrong wheel used.

### Pitfall 5: CE gating confirmation gets wrong admin token
**What goes wrong:** The CE gating confirmation step removes the licence key and restarts the agent. The existing admin JWT was issued while EE was active — it may or may not still be valid after restart (JWTs are stateless, so it should be valid). However, if the restart wipes the DB, the token becomes invalid.
**How to avoid:** Re-login after the agent restart to get a fresh token before making the 402-check API call. Restart does NOT wipe the DB (postgres volume is retained); only `down -v` would wipe it.

### Pitfall 6: EE reset doesn't clean stale CE FRICTION files
**What goes wrong:** `/workspace` may contain `FRICTION-CE-*.md` from Phase 63 or from a prior Phase 64 run attempt. If Gemini finds these files, it may be confused about prior results.
**How to avoid:** The EE reset script must remove `FRICTION-EE-*.md` AND ensure the workspace is clean. The CE FRICTION files can be left (they don't interfere with EE scenario).

### Pitfall 7: Node re-enrollment takes longer after full reset
**What goes wrong:** After `docker compose down -v`, node secrets volumes are wiped. Nodes restart from scratch, need to enroll, and must complete enrollment before `wait_for_stack()` returns true. The stack readiness check only polls the dashboard (HTTP 200) — it does not confirm node enrollment.
**How to avoid:** After `wait_for_stack()` returns true, add an additional wait for node enrollment: poll `GET /api/nodes` until at least one node has status `CONNECTED` (with 120s timeout). This is especially important for Phase 64 because the EE scenarios require nodes to execute jobs.

## Code Examples

### EE Reset Script Pattern (new `run_ee_scenario.py`)

The EE orchestrator script should reuse `run_ce_scenario.py` as a module and add EE-specific functions:

```python
# Source: run_ce_scenario.py (existing module)
from run_ce_scenario import incus_exec, incus_push, incus_pull, wait_for_stack

SECRETS_ENV = "/home/thomas/Development/mop_validation/secrets.env"
COMPOSE_SRC = "/home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml"
REPORTS_DIR = "/home/thomas/Development/mop_validation/reports"

def read_ee_licence_key() -> str:
    """Read AXIOM_EE_LICENCE_KEY from host secrets.env."""
    with open(SECRETS_ENV) as f:
        for line in f:
            if line.startswith("AXIOM_EE_LICENCE_KEY="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("AXIOM_EE_LICENCE_KEY not found in secrets.env")

def reset_stack_ee(compose_src: str = COMPOSE_SRC) -> None:
    """Reset stack with EE licence key injected into /workspace/.env."""
    licence_key = read_ee_licence_key()

    # 1. Push latest compose file
    incus_push(compose_src, "/workspace/compose.cold-start.yaml")

    # 2. Tear down (wipes certs and state)
    incus_exec("cd /workspace && docker compose -f compose.cold-start.yaml down -v 2>&1", timeout=120)

    # 3. Clean stale EE friction/checkpoint files
    incus_exec(
        "rm -f /workspace/FRICTION-EE-*.md "
        "/workspace/checkpoint/PROMPT.md "
        "/workspace/checkpoint/RESPONSE.md",
        timeout=15,
    )

    # 4. Write .env with licence key
    # Start from scratch — include ADMIN_PASSWORD and ENCRYPTION_KEY too
    # These are already written by setup_agent_scaffolding.py on prior runs
    incus_exec(
        f"grep -E '^(ADMIN_PASSWORD|ENCRYPTION_KEY|API_KEY)=' /workspace/.env > /tmp/base.env 2>/dev/null || true; "
        f"echo 'AXIOM_LICENCE_KEY={licence_key}' >> /tmp/base.env; "
        f"cp /tmp/base.env /workspace/.env",
        timeout=15,
    )

    # 5. Start with env-file
    incus_exec(
        "cd /workspace && docker compose --env-file .env -f compose.cold-start.yaml up -d 2>&1",
        timeout=600,
    )

def pull_ee_friction(scenario_id: str, reports_dir: str = REPORTS_DIR) -> bool:
    """Pull FRICTION-EE-{scenario_id}.md from LXC to host."""
    container_path = f"/workspace/FRICTION-EE-{scenario_id}.md"
    local_path = f"{reports_dir}/FRICTION-EE-{scenario_id}.md"
    success = incus_pull(container_path, local_path)
    if success:
        print(f"  FRICTION-EE-{scenario_id}.md pulled successfully.")
    else:
        print(f"  FAILED to pull FRICTION-EE-{scenario_id}.md")
    return success

def confirm_ce_gating(admin_token: str) -> bool:
    """Remove licence key, restart agent, confirm /api/executions returns 402."""
    # Remove licence key from .env
    incus_exec("sed -i '/^AXIOM_LICENCE_KEY=/d' /workspace/.env", timeout=10)

    # Restart only the agent container (not full stack)
    incus_exec(
        "cd /workspace && docker compose --env-file .env -f compose.cold-start.yaml restart agent",
        timeout=60,
    )
    import time
    time.sleep(15)  # agent startup time

    # Re-login to get a fresh token (token still valid after restart, but be safe)
    result = incus_exec(
        "curl -k -s -X POST https://172.17.0.1:8001/auth/login "
        "-d 'username=admin&password=$(grep ADMIN_PASSWORD /workspace/.env | cut -d= -f2-)' "
        "-w '\\n%{http_code}'",
        timeout=15,
    )
    # Parse token from response... simplified here
    # Then check /api/executions
    check = incus_exec(
        f"curl -k -s -o /dev/null -w '%{{http_code}}' "
        f"-H 'Authorization: Bearer {admin_token}' "
        f"https://172.17.0.1:8001/api/executions",
        timeout=15,
    )
    status = check.stdout.strip()
    if status == "402":
        print("  CE gating CONFIRMED: /api/executions returns 402 without licence key.")
        return True
    else:
        print(f"  CE gating FAILED: /api/executions returned {status} (expected 402).")
        return False
```

### EE Feature Flags Verification

```bash
# Confirm all EE feature flags are active after EE stack start
incus exec axiom-coldstart -- bash -c \
  "curl -k -s https://172.17.0.1:8001/api/features | python3 -c \
  \"import json,sys; d=json.load(sys.stdin); \
    print('EE features ALL TRUE:', all(d.values())); print(d)\""

# Confirm edition=enterprise via /api/licence (requires admin token)
TOKEN=$(incus exec axiom-coldstart -- bash -c \
  "curl -k -s -X POST https://172.17.0.1:8001/auth/login \
   -d 'username=admin&password=<admin_pw>' | python3 -c \
   \"import json,sys; print(json.load(sys.stdin)['access_token'])\"")

incus exec axiom-coldstart -- bash -c \
  "curl -k -s -H 'Authorization: Bearer $TOKEN' https://172.17.0.1:8001/api/licence"
# Expected: {"edition": "enterprise", "customer_id": "axiom-coldstart-test", ...}
```

### Node Enrollment Wait Pattern

```python
import time

def wait_for_node_enrollment(timeout: int = 120) -> bool:
    """Poll GET /api/nodes until at least one node shows CONNECTED status."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = incus_exec(
            "curl -k -s -H 'Authorization: Bearer $ADMIN_TOKEN' "
            "https://172.17.0.1:8001/nodes | python3 -c "
            "\"import json,sys; nodes=json.load(sys.stdin); "
            "connected=[n for n in nodes if n.get('status')=='CONNECTED']; "
            "print(len(connected))\"",
            timeout=15,
        )
        count = result.stdout.strip()
        if count.isdigit() and int(count) >= 1:
            print(f"  {count} node(s) enrolled and CONNECTED.")
            return True
        print(f"  No nodes connected yet — waiting 10s")
        time.sleep(10)
    return False
```

## State of the Art

| Phase 63 Pattern | Phase 64 Adaptation | Impact |
|-----------------|---------------------|--------|
| `reset_stack()` — no `--env-file` | `reset_stack_ee()` — adds `--env-file .env` and licence key injection | Licence key reaches agent container |
| No EE image rebuild step | Image rebuild with `EE_INSTALL=1` build arg + wheel COPY | EE plugin in server image |
| CE FRICTION files only | EE FRICTION files + CE gating confirmation step | Proves EE was active during run |
| `pull_friction("INSTALL")` | `pull_ee_friction("INSTALL")` | Different file prefix |
| No EE feature check in readiness | `wait_for_stack()` + optional `wait_for_node_enrollment()` | Avoids running scenarios against an enrolled-less stack |

## Open Questions

1. **`/api/admin/features` vs `/api/features`**
   - What we know: `main.py` has `GET /api/features` (line 903), not `/api/admin/features`
   - `ee-install.md` scenario checklist references `GET /api/admin/features` returning `"ee_status": "loaded"`
   - What's unclear: Does `/api/admin/features` exist (possibly mounted by an EE router)?
   - Recommendation: Pre-run check — `curl -k -s https://172.17.0.1:8001/api/admin/features` after EE stack start. If 404: update `ee-install.md` before launching Gemini OR accept it as a BLOCKER friction point.

2. **`axiom-ee` entry point check: is `ee.plugin` importable after wheel install?**
   - What we know: `.venv` install was editable from `/home/thomas/Development/axiom-ee` — not from the wheel
   - Wheel contains `ee/plugin.py` (entry point group `axiom.ee`, name `ee`, class `EEPlugin`)
   - Recommendation: smoke check `docker run --rm localhost/master-of-puppets-server:v3 python -c "import ee.plugin; print('OK')"` before pushing to LXC

3. **Does `compose.cold-start.yaml` require `--env-file .env` or reads `.env` automatically?**
   - What we know: docker compose v2 automatically reads `.env` in the project directory (the directory containing the compose file). The compose file is at `/workspace/compose.cold-start.yaml`, and `.env` would be at `/workspace/.env`.
   - docker compose v2 reads `.env` from the working directory when `cd /workspace && docker compose ...` is used.
   - Recommendation: Using `cd /workspace && docker compose -f compose.cold-start.yaml up -d` should pick up `/workspace/.env` automatically in compose v2 — but explicitly passing `--env-file .env` makes it unambiguous. Use the explicit form.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml testpaths: puppeteer/agent_service/tests) |
| Config file | pyproject.toml |
| Quick run command | `cd /home/thomas/Development/master_of_puppets && pytest puppeteer/agent_service/tests/ -x -q` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets && pytest puppeteer/agent_service/tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-01 | EE stack starts with ee_status active | smoke (incus_exec) | `incus exec axiom-coldstart -- bash -c "curl -k -s https://172.17.0.1:8001/api/features"` | N/A — live stack check |
| EE-01 | EE licence badge visible in dashboard | manual | Gemini visual confirmation | N/A — agent scenario |
| EE-02 | Python/Bash/PowerShell jobs complete via EE stack | integration | `incus exec axiom-coldstart -- bash -c "curl -k -s -X POST ..."` | N/A — live stack check |
| EE-03 | Execution History returns records (not 402) | smoke (incus_exec) | `curl -k -s -o /dev/null -w '%{http_code}' https://172.17.0.1:8001/api/executions` | N/A — live stack check |
| EE-04 | FRICTION-EE-*.md files present in reports/ | file existence | `ls mop_validation/reports/FRICTION-EE-*.md` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `ls mop_validation/reports/FRICTION-EE-*.md` (file existence check)
- **Per wave merge:** Full live stack checks (api/features, api/licence, api/executions)
- **Phase gate:** Both FRICTION files present in `mop_validation/reports/` before completion

### Wave 0 Gaps
- [ ] `mop_validation/scripts/run_ee_scenario.py` — EE orchestration module (new, mirrors run_ce_scenario.py)
- [ ] `puppeteer/wheels/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl` — wheel copy into build context

*(All test infrastructure (pytest, incus, monitor_checkpoint.py) already in place from Phase 63)*

## Sources

### Primary (HIGH confidence)
- `puppeteer/agent_service/main.py` lines 75-100, 903-936 — EE plugin loading, feature flags, licence endpoint
- `puppeteer/agent_service/ee/__init__.py` — EE plugin loader (entry_points, _mount_ce_stubs)
- `puppeteer/compose.cold-start.yaml` — `AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` on agent service
- `puppeteer/Containerfile.server` — `ARG EE_INSTALL=1` + DEVPI build pattern
- `mop_validation/secrets.env` line 15 — `AXIOM_EE_LICENCE_KEY` present and set
- `mop_validation/scenarios/ee-install.md` + `ee-operator.md` — scenario scripts
- `mop_validation/scripts/run_ce_scenario.py` — reusable primitives
- `.venv/lib/.../axiom_ee-0.1.0.dev0.dist-info/entry_points.txt` — `[axiom.ee] ee = ee.plugin:EEPlugin`
- `~/Development/axiom-ee/wheelhouse/` — musllinux_1_2_x86_64 cp312 wheel present

### Secondary (MEDIUM confidence)
- `mop_validation/scripts/verify_ee_install.py` — API contract for valid/expired/absent cases
- `mop_validation/scripts/verify_ee_pass.py` — EE route verification (EEV-01 through EEV-03)
- `docs/docs/licensing.md` — licence injection documentation as Gemini will see it
- `docs/docs/getting-started/install.md` — EE section ("add licence key to secrets.env")

### Tertiary (LOW confidence)
- docker compose v2 `.env` auto-loading behaviour — standard but not explicitly verified for this LXC setup

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all scripts and files verified to exist
- Architecture: HIGH — EE plugin loader, compose file, and wheel all inspected directly
- Pitfalls: HIGH for compose/env pitfalls (CE evidence); MEDIUM for API path mismatch (needs live verification)
- EE wheel delivery: HIGH — wheel file confirmed at correct path

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain; wheel build and secrets.env unlikely to change)

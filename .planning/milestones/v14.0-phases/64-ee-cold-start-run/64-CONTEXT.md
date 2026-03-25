# Phase 64: EE Cold-Start Run - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute the EE Gemini tester run end-to-end: rebuild the cold-start image with axiom-ee pre-baked, reset the LXC stack to a clean cold start with the licence key injected, run `ee-install.md` (Gemini installs Axiom EE from scratch following docs), operator confirms EE loaded, then run `ee-operator.md` (Gemini dispatches Python/Bash/PowerShell jobs and verifies Execution History as the EE-gated feature). Each scenario produces a uniquely named FRICTION file. Pull both FRICTION files to `mop_validation/reports/`. Phase is complete when both scenarios have run and FRICTION files are preserved. Does not synthesise findings — that is Phase 65.

</domain>

<decisions>
## Implementation Decisions

### axiom-ee delivery
- axiom-ee is **pre-baked into the same cold-start agent image** used for CE — one image for both editions
- EE plugin stays dormant on CE runs (no licence key); activates automatically when `AXIOM_LICENCE_KEY` is present at startup
- No runtime `pip install` step needed — the package is already installed inside the image
- Phase 64 **rebuilds the image from source** at plan start (`docker build -t localhost/axiom-node:cold-start`) to ensure all Phase 63-04 fixes and EE package are included
- After rebuild, image is pushed into the LXC via `docker save | incus exec axiom-coldstart -- docker load`
- **Smoke check before stack start**: `docker run --rm localhost/axiom-node:cold-start python -c "import ee.plugin"` inside the LXC — fails fast if EE is missing from the image

### Licence key injection
- Phase 64 reset script reads `AXIOM_EE_LICENCE_KEY` from `mop_validation/secrets.env` on the host
- Writes it to `/workspace/.env` inside the LXC as `AXIOM_LICENCE_KEY=<value>` — compose.cold-start.yaml picks it up automatically
- Same pattern as `ADMIN_PASSWORD` injection established in Phase 61/63
- **Full cold-start reset**: `docker compose down -v` (wipes certs and state), then `docker compose up -d` with the `.env` containing the licence key
- Nodes re-enroll from scratch — true cold-start baseline, not reusing CE node state

### CE blocker carry-forward
- **All 5 CE blockers are baked into source** — no runtime re-patching needed:
  - Docker CLI: `COPY --from=docker:cli` in `Containerfile.node`
  - PowerShell: `.deb` install + `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` in `Containerfile.node`
  - DinD `/tmp` mount: `- /tmp:/tmp` in both node services in `compose.cold-start.yaml`
  - `JOB_IMAGE`: set to `localhost/axiom-node:cold-start` in compose
  - Node enrollment docs: fixed in Phase 63-04
- Image rebuild at Phase 64 start incorporates all fixes automatically

### EE feature verification
- Target feature: **Execution History** (navigate to History view, confirm execution records with timing data visible for at least one completed job)
- Execution History is EE-gated (CE returns 402 on `GET /api/executions`)
- **CE gating confirmation step** added after the EE run: remove `AXIOM_LICENCE_KEY` from `.env`, restart the orchestrator container, confirm `GET /api/executions` returns 402 — proves EE was genuinely active during the run, not just a fluke
- This step is orchestrator-run (not Gemini), appended to the operator scenario plan

### Scenario sequencing
- Same as Phase 63: two separate operator-confirmed invocations — `ee-install` first, then `ee-operator`
- Operator reviews `FRICTION-EE-INSTALL.md` and confirms EE loaded (`ee_status: loaded` API + dashboard badge visible) before `ee-operator` begins
- Checkpoint policy carried forward: max 3 interventions per scenario, 4th = ABORT

### Claude's Discretion
- Exact structure of the Phase 64 reset script (extend Phase 63 pattern or standalone)
- Whether CE gating confirmation restarts just the orchestrator container or the full stack
- How the licence key removal step is surfaced to the operator (inline in plan, or as a post-scenario verification task)

</decisions>

<specifics>
## Specific Ideas

- The CE gating confirmation is a quick sanity check, not a full scenario — orchestrator runs it directly via `incus exec` curl calls, no Gemini involvement

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/provision_coldstart_lxc.py`: Established `incus file push`, `incus exec`, IP polling, `docker save | docker load` patterns — Phase 64 reset follows the same primitives
- `mop_validation/scripts/monitor_checkpoint.py`: Already implements PROMPT.md detection, Claude API draft, RESPONSE.md push — used as-is
- `mop_validation/scenarios/ee-install.md` + `ee-operator.md`: Complete scenario scripts from Phase 62 — ready to use
- `mop_validation/scripts/setup_agent_scaffolding.py`: HOME isolation setup — must be run before each Gemini invocation

### Established Patterns
- `HOME=/root/validation-home gemini -p "$(cat ee-install.md)"` — isolation invocation (locked from Phase 62)
- `incus exec axiom-coldstart -- bash -c "docker run --rm localhost/axiom-node:cold-start python -c 'import ee.plugin'"` — EE smoke check
- `incus file push <local> axiom-coldstart<container_path>` — host-to-LXC file transfer
- Write to `/workspace/.env` inside LXC for compose env injection (AXIOM_LICENCE_KEY, ADMIN_PASSWORD)

### Integration Points
- `mop_validation/secrets.env`: Source of `AXIOM_EE_LICENCE_KEY` — read by reset script, written to LXC `/workspace/.env`
- `puppeteer/compose.cold-start.yaml`: Reads `AXIOM_LICENCE_KEY` from `.env` — no compose changes needed
- `puppets/Containerfile.node`: All CE blockers fixed here — rebuild from this file at Phase 64 start
- `mop_validation/reports/`: Destination for `FRICTION-EE-INSTALL.md` and `FRICTION-EE-OPERATOR.md`

### Doc Fix Applied
- `docs/docs/getting-started/install.md`: Added EE section at bottom linking to `../licensing.md` — Gemini can now find the licence key injection instructions by following the install guide

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 64-ee-cold-start-run*
*Context gathered: 2026-03-25*

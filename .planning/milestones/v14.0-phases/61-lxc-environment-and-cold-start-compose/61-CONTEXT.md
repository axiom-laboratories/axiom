# Phase 61: LXC Environment and Cold-Start Compose - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Provision a single Ubuntu 24.04 Incus LXC container with all infrastructure required before any Gemini agent can run: Docker CE (auto-installed), Docker-in-LXC nesting with AppArmor override, Node.js 20, Gemini CLI ≥ v0.23.0, Playwright + system deps, a stripped `compose.cold-start.yaml` that starts the full Axiom stack (orchestrator + docs + 2 puppet nodes), PowerShell fix in `Containerfile.node`, and a pre-generated EE test licence. Gemini agent scaffolding (GEMINI.md, checkpoint protocol, scenario scripts) is Phase 62 — not in scope here.

</domain>

<decisions>
## Implementation Decisions

### Compose file scope and location
- `puppeteer/compose.cold-start.yaml` — lives alongside `compose.server.yaml` in the main repo, versioned with the product
- Services to include: `db`, `cert-manager`, `agent`, `dashboard`, `docs`, and 2 puppet nodes
- Services to strip: `tunnel`, `ddns-updater`, `devpi`, `pypi`, `mirror`, `registry` — none needed for cold-start evaluation
- Same compose file used for CE and EE runs — `AXIOM_LICENCE_KEY` env var is empty for CE, set to pre-generated licence for EE
- `SERVER_HOSTNAME=172.17.0.1` set in compose env so Caddy generates TLS cert with Docker bridge gateway SAN (required for both Playwright and puppet node connections)
- `EXECUTION_MODE=direct` on puppet nodes (Docker-in-Docker, no nested container runtime)

### Puppet nodes
- 2 puppet nodes as Docker services inside `compose.cold-start.yaml` — start automatically with the stack
- Nodes connect to orchestrator via Docker bridge (`AGENT_URL=https://172.17.0.1:8001`)
- Mirrors what a real evaluator gets on `docker compose up`

### LXC count and wipe strategy
- One LXC re-used for both CE and EE runs
- Between CE and EE: `docker compose down -v` to wipe stack + volumes, then `docker compose up` with `AXIOM_LICENCE_KEY` injected — preserves Node.js/Gemini CLI install
- Full LXC teardown only if something goes wrong with the LXC itself

### AppArmor and Docker-in-LXC
- `raw.apparmor` override applied in incus config at launch time — targeted fix for Ubuntu 24.04 kernel 6.8.x `pivot_root` block
- Based on Incus issue #791 workaround pattern
- Docker CE auto-installed inside LXC from the official Docker apt repository (not assumed pre-installed)

### PowerShell fix
- `Containerfile.node` updated to download `pwsh` directly from GitHub releases as a `.deb` (version-pinned to 7.6.0 LTS)
- Replaces the silently-failing Debian 12 apt repository method (SHA1 key rejection)

### EE licence
- Pre-generation script produces Ed25519-signed test licence with 1-year expiry
- Stored in `mop_validation/secrets.env` as `AXIOM_EE_LICENCE_KEY`
- Injected into compose env only for EE run

### Node.js and Gemini CLI
- Node.js 20 installed via NodeSource PPA (Ubuntu 24.04 ships Node 18 — too old)
- Gemini CLI installed via `npm install -g @google/gemini-cli` pinned to ≥ v0.23.0 (fixes headless hang bug)
- `GEMINI_MODEL=gemini-2.0-flash` env var set at LXC level (settings.json model pinning has known auto-switching bug)
- `ripgrep` installed — required to prevent 300-second Gemini CLI initialization stall on Ubuntu Server

### Claude's Discretion
- Exact `raw.apparmor` profile content (use minimal `pivot_root` allow rule from Incus issue #791)
- Docker CE install script (standard `curl | sh` from get.docker.com or apt repo method)
- Provision script structure (single Python script extending `manage_node.py` pattern, or bash)
- Chromium NSS cert trust method for Playwright (needs separate handling from system `update-ca-certificates`)

</decisions>

<specifics>
## Specific Ideas

- The existing `manage_node.py` skill script is the direct template for the new `provision_coldstart_lxc.py` — same Incus patterns, extend rather than rewrite
- `compose.cold-start.yaml` is deliberately stripped-down so an evaluator running it doesn't need a Cloudflare tunnel token or DuckDNS credentials — barrier to evaluation must be zero
- The LXC name should distinguish from the existing `mop-test-node` — suggest `axiom-coldstart`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.agent/skills/manage-test-nodes/scripts/manage_node.py`: Incus launch with `security.nesting=true`, IP polling, `incus file push`, sudoers injection — direct template for the new provisioning script. Needs: AppArmor override, Docker install, Node.js 20, Gemini CLI steps added.
- `puppeteer/compose.server.yaml`: Full 11-service compose — cold-start file strips 6 services, keeps 5, adds 2 puppet node services. `SERVER_HOSTNAME` env var already wired to `cert-manager`.

### Established Patterns
- `security.nesting=true` on incus launch is already the pattern — add `raw.apparmor` override to the same launch command
- `EXECUTION_MODE=direct` is the established Docker-in-LXC pattern from v11.1 validation nodes
- `incus file push` / `incus exec` are the established LXC interaction primitives

### Integration Points
- `mop_validation/secrets.env`: EE licence stored here as `AXIOM_EE_LICENCE_KEY`; provision script reads IP and writes it here (existing pattern from `manage_node.py`)
- `puppeteer/cert-manager/entrypoint.sh`: Already reads `SERVER_HOSTNAME` env var and adds it as Caddy TLS SAN — just needs the var set correctly in cold-start compose

</code_context>

<deferred>
## Deferred Ideas

- Parallel CE+EE runs in two simultaneous LXCs — deferred; single LXC with wipe is sufficient and simpler
- Automated LXC provisioning in CI — deferred to post-validation automation milestone
- Windows or macOS test environment — out of scope

</deferred>

---

*Phase: 61-lxc-environment-and-cold-start-compose*
*Context gathered: 2026-03-24*

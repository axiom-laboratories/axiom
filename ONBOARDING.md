# Welcome to Axiom

## What Is Axiom?

Axiom is an open-core orchestration platform for managing fleets of remote worker nodes. The **Puppeteer** (control plane) runs a FastAPI backend + React dashboard and handles job scheduling, node enrollment, and secrets. **Puppet nodes** are stateless workers that poll for assigned jobs, execute them in ephemeral containers, and report results back. All node-to-server communication uses mTLS — nodes initiate every connection, so no inbound firewall rules are needed on the worker side.

The repo split: CE (open-source core) lives in `axiom`, EE (enterprise features — Vault, licensing, etc.) lives in `axiom-ee`.

## How We Use Claude

Based on Bambibanners's usage over the last 30 days:

Work Type Breakdown:
  Plan Design      ████████████████████  38%
  Debug Fix        █████████████░░░░░░░  25%
  Build Feature    ████████░░░░░░░░░░░░  15%
  Improve Quality  ███████░░░░░░░░░░░░░  14%
  Write Docs       ████░░░░░░░░░░░░░░░░   8%

Top Skills & Commands:
  /gsd:plan-phase        ████████████████████  146x/month
  /gsd:execute-phase     ███████████████████░  139x/month
  /gsd:discuss-phase     █████████████████░░░  121x/month
  /gsd:audit-milestone   ███░░░░░░░░░░░░░░░░░   25x/month
  /gsd:progress          ███░░░░░░░░░░░░░░░░░   23x/month

Top MCP Servers:
  playwright  ████████████████████  99 calls

### About the `/gsd:` Commands

These come from **GSD** (Get Shit Done) — a standalone Claude Code plugin for structured, phase-based development. It's not part of the Superpowers plugin. Install it separately:

```
claude plugin install gsd
```

GSD organises work into a roadmap of numbered phases. The core loop is:

```
/gsd:discuss-phase N  →  /gsd:plan-phase N  →  /gsd:execute-phase N
```

Run `/gsd:progress` at any time to see where the milestone stands.

## Your Setup Checklist

### Codebases

Clone these as siblings in the same parent directory (e.g. `~/Development/`):

- [ ] `axiom` — https://github.com/axiom-laboratories/axiom (CE / open-core). Contains a `puppeteer/ee/` directory — that's the EE services code that lives inside the CE repo. You don't need to touch it unless you're working on EE features.
- [ ] `axiom-ee` — https://github.com/axiom-laboratories/axiom-ee (the installable EE Python package — only needed for EE feature work)
- [ ] `mop_validation` — https://github.com/axiom-laboratories/mop_validation (E2E tests, diagnostics, dev tooling, test node configs) — **separate repo, clone as a sibling, not inside `axiom`**

### Boot the Stack

```bash
# From the axiom repo root:
cd puppeteer
docker compose -f compose.server.yaml up -d
```

That starts the agent service (port 8001), model service (8000), PostgreSQL, and Caddy. The dashboard is served at `https://localhost:8443`. Expect ~10s for the agent to finish booting.

To rebuild after code changes:

```bash
docker compose -f puppeteer/compose.server.yaml build agent
docker compose -f puppeteer/compose.server.yaml up -d --no-build agent
```

Credentials for local dev live in `mop_validation/secrets.env`.

**Applying migrations:** there's no Alembic. When a new `migration_vNN.sql` file appears in the repo, apply it manually:

```bash
mopdb "$(cat puppeteer/migration_vNN.sql)"
# or directly:
docker exec -i puppeteer-db-1 psql -U puppet puppet_db < puppeteer/migration_vNN.sql
```

**Enrolling a local test node:**

```bash
mop-enroll-node   # refreshes join token, patches node-compose.yaml, rebuilds node
```

Test node compose files live in `mop_validation/local_nodes/`.

### MCP Servers to Activate

- [ ] **Playwright** — browser automation used for UI smoke tests and E2E verification. Install via `claude plugin install playwright`, then confirm it shows up under `/plugins`.
- [ ] **GSD** — the phase-based workflow plugin. Install via `claude plugin install gsd`.

### Environment

- **Python**: `pip install -r puppeteer/requirements.txt` — standard venv is fine
- **Node/Frontend**: `cd puppeteer/dashboard && npm install` — check `.nvmrc` for the required Node version
- **Ed25519 signing**: jobs must be signed before submission. Use the scripts in `mop_validation`:
  ```bash
  python ~/Development/mop_validation/scripts/generate_signing_key.py   # create keypair, uploads public key to API
  python ~/Development/mop_validation/scripts/sign_job.py my_script.py  # sign + submit a job
  ```
  Store your private key in `mop_validation/secrets/` — it's gitignored there.

### Testing

- **Unit tests** (backend): `cd puppeteer && pytest` — run these before every PR
- **E2E suite**: `mop-e2e` from anywhere — wraps `mop_validation/scripts/e2e_runner.py`. Covers API + UI via Playwright. Run this before merging anything that touches the stack.
- **Never test against a dev server** — always rebuild the Docker stack and test there. See CLAUDE.md for details.

### Skills to Know About

- `/gsd:discuss-phase N` — Run this **before** planning any non-trivial phase. Socratic Q&A to surface assumptions and produce a CONTEXT.md the planner uses.
- `/gsd:plan-phase N` — Generates the step-by-step implementation plan for a phase. Requires a CONTEXT.md from discuss-phase first.
- `/gsd:execute-phase N` — Autonomously executes all plans in a phase end-to-end. The primary "get it built" command.
- `/gsd:progress` — Shows what's done and what's outstanding in the current milestone.
- `/gsd:audit-milestone` — Cross-checks that a milestone is actually complete before closing it out.
- `/gsd:complete-milestone` — Archives a finished milestone and sets up the next one.
- `/gsd:plan-milestone-gaps` — Identifies gaps in the current milestone and creates phases to close them.

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->

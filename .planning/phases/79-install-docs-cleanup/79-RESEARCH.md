# Phase 79: Install Docs Cleanup - Research

**Researched:** 2026-03-27
**Domain:** Documentation and Docker Compose YAML editing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Remove `puppet-node-1` and `puppet-node-2` service blocks entirely from `compose.cold-start.yaml`
- Remove `node1-secrets` and `node2-secrets` from the volumes block
- Replace the Step 3 "Cold-Start Install" prose (line 97 of install.md) with: "This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL." — no forward pointer
- Rename all "Cold-Start Install" tab labels to "Quick Start" across every tabbed section in install.md (Steps 2, 3, 4)
- Remove steps 3–4 from the header comment "Quick start:" numbered list in compose.cold-start.yaml
- Remove JOIN_TOKEN env var references from the Usage block example commands in the header comment
- The filename `compose.cold-start.yaml` does not change
- `enroll-node.md` does not change
- No backend code changes — pure YAML deletion + doc prose update

### Claude's Discretion

- Exact wording of any updated inline comments in the YAML volumes section
- Whether to re-number the header "Quick start:" steps after removing steps 3–4 (they become 2 steps, no numbering needed or simple 1–2)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INST-01 | `compose.cold-start.yaml` does not include bundled test nodes (puppet-node-1, puppet-node-2) | File inspected — both services are at lines 105–147; volumes at lines 154–155. Exact deletion range is known. |
| INST-02 | `install.md` does not reference bundled node JOIN_TOKENs (atomic with INST-01) | File inspected — offending prose is at line 97; tab labels are at lines 59, 91, 113. All instances located. |
</phase_requirements>

---

## Summary

Phase 79 is a two-file cleanup. The work is entirely editorial: delete two Docker Compose service blocks and their volumes, strip the matching header-comment steps, and update `install.md` tab labels plus one line of prose. There are no libraries to install, no APIs to integrate, and no tests to write against the changes themselves.

Both target files have been fully inspected. Every line to change has been located and its exact current content recorded below under Code Examples. The planner can go straight to constructing edit tasks from those excerpts.

The only open question is purely cosmetic: whether the header comment retains numbered steps or drops them. Both options are valid — the research recommends numbered 1–2 for scannability.

**Primary recommendation:** Execute as one atomic plan with two sequential edit tasks (YAML first, doc second). Verify by grepping for prohibited strings after each edit.

---

## Standard Stack

Not applicable — no library dependencies. The two files are plain YAML and MkDocs Markdown.

---

## Architecture Patterns

### File 1: `puppeteer/compose.cold-start.yaml`

**Recommended structure after cleanup:**

```
services:
  db:          (unchanged)
  cert-manager: (unchanged)
  agent:       (unchanged)
  dashboard:   (unchanged)
  docs:        (unchanged)
  # puppet-node-1 DELETED (lines 105-126)
  # puppet-node-2 DELETED (lines 127-147)

volumes:
  pgdata:
  certs-volume:
  caddy_data:
  caddy_config:
  # node1-secrets: DELETED (line 154)
  # node2-secrets: DELETED (line 155)
  secrets-data:  # <discretionary inline comment>
```

**Header comment after cleanup** (lines 8–16 → reduced):

```yaml
# Quick start:
#   1. Create a .env file with at minimum:
#        ADMIN_PASSWORD=<choose-a-password>
#        ENCRYPTION_KEY=<32-char-fernet-key>  # generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   2. docker compose -f compose.cold-start.yaml --env-file .env up -d
```

Steps 3 and 4 are removed entirely. The Usage block below (lines 19–20) is unaffected — the `EE run:` line contains no JOIN_TOKEN references and requires no change.

### File 2: `docs/docs/getting-started/install.md`

**Tab label rename pattern (MkDocs Material syntax):**
```
=== "Cold-Start Install"   →   === "Quick Start"
```
Occurs at lines 59, 91, and 113. A global find-and-replace covers all three instances in a single pass.

**Step 3 prose replacement (line 97):**
```
OLD: This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL. The two built-in puppet nodes start automatically but require JOIN_TOKEN_1 and JOIN_TOKEN_2 to be set in your `.env` before they can enroll.

NEW: This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL.
```

### Anti-Patterns to Avoid

- **Partial cleanup:** Leaving `node1-secrets` or `node2-secrets` in the volumes block after deleting the services that reference them — orphan volumes cause a compose validation warning.
- **JOIN_TOKEN comment residue:** The header comment steps 3–4 explicitly mention `JOIN_TOKEN_1`/`JOIN_TOKEN_2`. Both must be removed, not just step 4.
- **Tab label inconsistency:** Renaming only the Step 3 tab but not Steps 2 and 4 leaves an inconsistent UI. All three tabs must be renamed in the same pass.

---

## Don't Hand-Roll

Not applicable — no algorithmic problem to solve. All edits are line-level deletions and string replacements.

---

## Common Pitfalls

### Pitfall 1: Dangling volume declaration
**What goes wrong:** Deleting `puppet-node-1` and `puppet-node-2` services but leaving `node1-secrets:` and `node2-secrets:` in the `volumes:` block. Docker Compose will emit a warning about declared-but-unused volumes; a new user following the docs will see noise on `docker compose up`.
**Why it happens:** Service block and volume declaration are in separate sections of the file.
**How to avoid:** After deleting the service blocks, explicitly remove lines 154 and 155 (`node1-secrets:` and `node2-secrets:`).
**Warning signs:** `docker compose config` output still lists node1-secrets or node2-secrets.

### Pitfall 2: Orphaned prose referencing phantom services
**What goes wrong:** install.md line 97 still mentions "The two built-in puppet nodes" after compose.cold-start.yaml no longer includes them. A user following the doc sees containers that do not exist.
**Why it happens:** YAML and docs are edited in separate passes and it is easy to stop after the YAML.
**How to avoid:** Treat the two edits as a single atomic unit. The plan should include a post-edit grep for `JOIN_TOKEN`, `puppet-node`, and `built-in puppet` to confirm no references remain.
**Warning signs:** `grep -r "JOIN_TOKEN" docs/ puppeteer/compose.cold-start.yaml` returns any hits.

### Pitfall 3: Missed tab label instance
**What goes wrong:** Three sections use `=== "Cold-Start Install"` (Steps 2, 3, 4). If only the Step 3 tab is renamed, the Step 2 and Step 4 tabs still say "Cold-Start Install", creating a jarring mismatch.
**Why it happens:** Developer searches for the specific prose change (line 97) but does not audit all tab headings.
**How to avoid:** Use a global string replacement for the tab label, or grep for `Cold-Start Install` after editing to confirm zero remaining instances.
**Warning signs:** `grep "Cold-Start Install" docs/docs/getting-started/install.md` returns any lines after edit.

---

## Code Examples

All examples are sourced directly from file inspection (HIGH confidence).

### Compose: Services to delete (lines 105–147)

```yaml
# DELETE LINES 105-147 ENTIRELY:
  puppet-node-1:
    build:
      context: ../puppets
      dockerfile: Containerfile.node
    image: localhost/axiom-node:cold-start
    environment:
      - AGENT_URL=https://agent:8001
      - JOIN_TOKEN=${JOIN_TOKEN_1:-}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - EXECUTION_MODE=docker
      - JOB_IMAGE=localhost/axiom-node:cold-start
      - PYTHONUNBUFFERED=1
      - NODE_TAGS=coldstart,linux
    volumes:
      - node1-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp:/tmp
    restart: unless-stopped
    depends_on:
      agent:
        condition: service_started

  puppet-node-2:
    build:
      context: ../puppets
      dockerfile: Containerfile.node
    image: localhost/axiom-node:cold-start
    environment:
      - AGENT_URL=https://agent:8001
      - JOIN_TOKEN=${JOIN_TOKEN_2:-}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - EXECUTION_MODE=docker
      - JOB_IMAGE=localhost/axiom-node:cold-start
      - PYTHONUNBUFFERED=1
      - NODE_TAGS=coldstart,linux
    volumes:
      - node2-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp:/tmp
    restart: unless-stopped
    depends_on:
      agent:
        condition: service_started
```

### Compose: Volume declarations to delete (lines 154–155)

```yaml
# CURRENT:
  node1-secrets:
  node2-secrets:
  secrets-data:   # Agent secrets persistence (boot.log, licence.key)

# AFTER (node1-secrets and node2-secrets removed):
  secrets-data:   # Agent secrets persistence (boot.log, licence.key)
```

### Compose: Header comment steps to remove (lines 13–16)

```yaml
# REMOVE THESE LINES:
#   3. Generate JOIN tokens from the dashboard (Admin → Join Tokens) or via API:
#        curl -sk -X POST https://localhost:8001/admin/generate-token \
#          -H "Authorization: Bearer <admin-jwt>" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['token'])"
#   4. Set JOIN_TOKEN_1 and JOIN_TOKEN_2 in your .env file and restart the node services.
```

The lines immediately above (steps 1–2, lines 9–12) are retained unchanged.

### install.md: Tab label renames (lines 59, 91, 113)

```markdown
# BEFORE (three occurrences):
=== "Cold-Start Install"

# AFTER (all three):
=== "Quick Start"
```

### install.md: Step 3 prose replacement (line 97)

```markdown
# BEFORE:
    This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL. The two built-in puppet nodes start automatically but require JOIN_TOKEN_1 and JOIN_TOKEN_2 to be set in your `.env` before they can enroll.

# AFTER:
    This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL.
```

---

## State of the Art

Not applicable — this phase has no technology choices to evaluate. Docker Compose YAML syntax and MkDocs Material tab syntax are both stable.

---

## Open Questions

1. **Header comment numbering style after cleanup**
   - What we know: Steps 3–4 are removed, leaving only steps 1–2.
   - What's unclear: Whether to keep explicit "1." and "2." numbering or drop it (unnumbered bullets).
   - Recommendation: Retain numbered 1–2. Two steps remain meaningful and numbered steps are easier to reference verbally ("do step 2"). This is within Claude's discretion per CONTEXT.md.

2. **`secrets-data` volume comment wording**
   - What we know: Current comment is `# Agent secrets persistence (boot.log, licence.key) across restarts`. CONTEXT.md says review and keep/update as appropriate.
   - What's unclear: Whether "across restarts" should be updated.
   - Recommendation: Keep the existing comment unchanged. It accurately describes `secrets-data` and removing nodes does not change its semantics. Updating to `# Agent secrets (boot.log, licence.key) — persists across restarts` is equally valid if the planner prefers tighter prose.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | grep / docker compose config (shell verification) |
| Config file | none — no test framework applies to YAML/doc edits |
| Quick run command | `grep -c "Cold-Start Install\|JOIN_TOKEN_1\|JOIN_TOKEN_2\|puppet-node-1\|puppet-node-2\|node1-secrets\|node2-secrets" docs/docs/getting-started/install.md puppeteer/compose.cold-start.yaml` |
| Full suite command | `docker compose -f puppeteer/compose.cold-start.yaml config --quiet && echo "YAML valid"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INST-01 | compose.cold-start.yaml contains no puppet-node-1, puppet-node-2, node1-secrets, node2-secrets | smoke | `grep -c "puppet-node-1\|puppet-node-2\|node1-secrets\|node2-secrets" puppeteer/compose.cold-start.yaml && echo FAIL \|\| echo PASS` (exit 1 if count > 0) | ❌ Wave 0 |
| INST-01 | compose.cold-start.yaml is valid YAML after deletion | smoke | `docker compose -f puppeteer/compose.cold-start.yaml config --quiet && echo YAML_OK` | ❌ Wave 0 |
| INST-02 | install.md contains no "Cold-Start Install", JOIN_TOKEN_1, JOIN_TOKEN_2 references | smoke | `grep -c "Cold-Start Install\|JOIN_TOKEN_1\|JOIN_TOKEN_2" docs/docs/getting-started/install.md && echo FAIL \|\| echo PASS` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Run the quick grep command above
- **Per wave merge:** `docker compose -f puppeteer/compose.cold-start.yaml config --quiet`
- **Phase gate:** All grep counts return 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] No test files to create — all verification is inline grep commands run in the plan's verify step. No framework install needed.

---

## Sources

### Primary (HIGH confidence)
- Direct file read of `puppeteer/compose.cold-start.yaml` — full service/volume inventory, exact line numbers
- Direct file read of `docs/docs/getting-started/install.md` — all tab labels, exact line of offending prose
- Direct file read of `.planning/phases/79-install-docs-cleanup/79-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- MkDocs Material tab syntax verified by inspection of existing working tabs in install.md

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Scope definition: HIGH — CONTEXT.md is fully specified with exact lines to change
- File inventory: HIGH — both files inspected, exact line numbers recorded
- Pitfalls: HIGH — derived from direct file inspection, no external dependencies
- Validation: HIGH — grep-based smoke tests are trivially correct for this domain

**Research date:** 2026-03-27
**Valid until:** Indefinite — no external dependencies; files will not change between research and planning

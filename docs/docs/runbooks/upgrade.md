# Upgrade Guide

This runbook covers the end-to-end process for upgrading an existing Axiom deployment — from pre-flight checks through schema migration to post-upgrade verification and rollback.

---

## Upgrade philosophy

Axiom manages its database schema with SQLAlchemy's `Base.metadata.create_all()` at startup. Understanding what that does and does not handle is the key to a smooth upgrade:

| Change type | Handled by | Action required |
|-------------|-----------|-----------------|
| New tables | `create_all` at startup | None — automatic |
| New indexes on new tables | `create_all` at startup | None — automatic |
| New columns on **existing** tables | **Not handled** by `create_all` | Run the migration SQL file |
| New indexes on **existing** tables | **Not handled** by `create_all` | Run the migration SQL file |
| Enum value changes | **Not handled** | Usually documentation-only (see migration notes) |
| Initial data seeds (role permissions, config defaults) | `create_all` + startup seeds | Run migration SQL for existing deployments |

**`ADMIN_PASSWORD` only seeds on first start.** It is read once during database initialisation, when the `users` table is empty. Upgrading does not reset or re-read it. The password in your `.env` or `secrets.env` file is irrelevant once the admin user exists in the database.

**Nodes reconnect automatically.** Axiom uses a pull model: nodes poll `/work/pull` on their own schedule. After a server restart, online nodes resume polling within seconds. No manual intervention is needed to re-attach nodes.

---

## Pre-upgrade checklist

Complete all items before pulling a new image.

- [ ] **Back up PostgreSQL**

    ```bash
    docker exec puppeteer-db-1 \
      pg_dump -U puppet puppet_db > axiom_backup_$(date +%Y%m%d_%H%M%S).sql
    ```

    Store the dump file off the host before proceeding.

- [ ] **Record the current version**

    ```bash
    curl -sk https://localhost:8001/api/version | python3 -m json.tool
    ```

    Note the version string in case a rollback is needed.

- [ ] **Read the release notes** for each version between current and target. Identify which migration SQL files are listed as required.

- [ ] **Confirm migration SQL files are available** — check that the `puppeteer/migration_vNN.sql` files for the target version exist in your working copy.

- [ ] **Verify no jobs are actively running** on nodes you want to quiesce before the restart. Use the dashboard Jobs view or:

    ```bash
    curl -sk -H "Authorization: Bearer $TOKEN" \
      https://localhost:8001/api/jobs?status=ASSIGNED | python3 -m json.tool
    ```

---

## Standard upgrade procedure

### Step 1 — Pull the new image

```bash
docker compose -f puppeteer/compose.server.yaml pull agent
```

Or, if building locally after a code change:

```bash
docker compose -f puppeteer/compose.server.yaml build agent
```

### Step 2 — Stop the agent service

Bring down only the agent to avoid PostgreSQL downtime:

```bash
docker compose -f puppeteer/compose.server.yaml stop agent
```

The `db` service remains running throughout so migration SQL can be applied immediately.

### Step 3 — Apply migration SQL (if required)

See [Migration SQL reference](#migration-sql-reference) to identify which files apply to your upgrade path. Run each file in order:

```bash
docker exec -i puppeteer-db-1 \
  psql -U puppet puppet_db < puppeteer/migration_vNN.sql
```

Replace `migration_vNN.sql` with the correct file name. Run multiple files sequentially, lowest number first.

!!! tip "Check whether a migration is already applied"
    Before running a migration, confirm the column or table does not already exist:

    ```bash
    # Check for a column
    docker exec puppeteer-db-1 \
      psql -U puppet puppet_db -c "\d nodes" | grep column_name

    # Check for a table
    docker exec puppeteer-db-1 \
      psql -U puppet puppet_db -c "\dt table_name"
    ```

    All migration files use `IF NOT EXISTS` guards on PostgreSQL, so re-running a previously applied file is safe.

### Step 4 — Start the updated agent

```bash
docker compose -f puppeteer/compose.server.yaml up -d --no-build agent
```

`--no-build` prevents Docker Compose from rebuilding the image; it uses the image pulled or built in Step 1.

### Step 5 — Verify

```bash
# Health check
curl -sk https://localhost:8001/api/health

# Version confirmation
curl -sk https://localhost:8001/api/version
```

Check the [post-upgrade verification checklist](#post-upgrade-verification) below.

---

## Migration SQL reference

Each migration file is numbered to match the feature phase that introduced it. Run all files between your current version and the target version, in ascending order.

!!! note "Fresh installs do not need migration SQL"
    On a fresh deployment, `create_all` at startup builds all tables with the latest schema. Migration files only apply to existing databases that are missing columns or tables added in later releases.

### Running a migration

```bash
docker exec -i puppeteer-db-1 \
  psql -U puppet puppet_db < puppeteer/migration_vNN.sql
```

### Migration file index

| File | What it covers | Key DDL |
|------|---------------|---------|
| `migration.sql` (v0.8) | Concurrent job limits on nodes | `nodes.concurrency_limit`, `nodes.job_memory_limit` |
| `migration_v09.sql` | Capability-based node scheduling | `nodes.capabilities`, `nodes.node_secret_hash`, `jobs.capability_requirements`, `scheduled_jobs.capability_requirements` |
| `migration_v10.sql` | Force password change + session invalidation | `users.must_change_password`, `users.token_version`; seeds `foundry:write` and `signatures:write` for the operator role |
| `migration_v11.sql` | Per-user signing keys and API keys | New tables: `user_signing_keys`, `user_api_keys` |
| `migration_v12.sql` | Service principals | New table: `service_principals` |
| `migration_v13.sql` | Edit scheduled jobs | `scheduled_jobs.updated_at` |
| `migration_v14.sql` | Job output capture | New table: `execution_records` |
| `migration_v15.sql` | Retry policy | `jobs.max_retries`, `jobs.retry_count`, `jobs.retry_after`, `jobs.backoff_multiplier`, `jobs.timeout_minutes`; same on `scheduled_jobs`; seeds `zombie_timeout_minutes` config value |
| `migration_v16.sql` | Execution history indexes | Index on `execution_records.started_at`; `config` retention key |
| `migration_v17.sql` | Environment tags on nodes | `nodes.operator_tags` |
| `migration_v18.sql` | Job dependency ordering | `jobs.depends_on` |
| `migration_v19.sql` | Advanced Foundry — artifacts and approved OS list | New tables: `artifacts`, `approved_os` |
| `migration_v20.sql` | Tamper detection | `tokens.template_id` |
| `migration_v21.sql` | Hot-upgrade engine | `nodes.pending_upgrade` |
| `migration_v22.sql` | Persist base OS family on nodes | `nodes.base_os_family` |
| `migration_v23.sql` | Automation triggers | New table: `triggers` |
| `migration_v24.sql` | Conditional triggers and signals | New table: `signals` |
| `migration_v25.sql` | Alerts and webhooks | New tables: `alerts`, `webhooks` |
| `migration_v26.sql` | Compatibility engine | `capability_matrix.is_active`, `capability_matrix.runtime_dependencies`, `blueprints.os_family`; backfills `os_family='DEBIAN'` |
| `migration_v27.sql` | Job lifecycle status and push attribution | `scheduled_jobs.status` (DRAFT/ACTIVE/DEPRECATED/REVOKED), `scheduled_jobs.pushed_by`; backfills existing rows to `ACTIVE` |
| `migration_v28.sql` | Smelter registry and compliance tracking | New table: `approved_ingredients` |
| `migration_v29.sql` | Package mirroring columns | `approved_ingredients.mirror_status`, `approved_ingredients.mirror_path`, `approved_ingredients.mirror_log` |
| `migration_v30.sql` | Image lifecycle and Bill of Materials | `puppet_templates.status`, `puppet_templates.bom_captured` |
| `migration_v31.sql` | Track template image on nodes | `nodes.template_id` |
| `migration_v32.sql` | Execution output capture | `execution_records.stdout`, `execution_records.stderr` |
| `migration_v33.sql` | Runtime attestation | Additional columns on `execution_records` for runtime provenance |
| `migration_v34.sql` | Environment tags on jobs | `nodes.env_tag`, `jobs.env_tag`, `scheduled_jobs.env_tag` |
| `migration_v35.sql` | Operator env tag lock | `nodes.operator_env_tag` — prevents heartbeat from overwriting operator-set tag |
| `migration_v36.sql` | Role column for EE RBAC | `users.role` (default `'admin'` preserves existing admin user) |
| `migration_v37.sql` | HMAC integrity on job signatures | `jobs.signature_hmac` |
| `migration_v38.sql` | Multi-runtime support | `scheduled_jobs.runtime`, `jobs.runtime` |
| `migration_v39.sql` | Job name and creator tracking | `jobs.name`, `jobs.created_by`; index on `jobs.name` |
| `migration_v40.sql` / `migration_v41.sql` | Job resubmit traceability | `jobs.originating_guid` (v40 and v41 are equivalent; applying either is sufficient) |
| `migration_v42.sql` | DRAINING node status + explicit node targeting | Documentation-only for DRAINING; `jobs.target_node_id` |
| `migration_v43.sql` | Scheduling health and data management | `execution_records.pinned`, `scheduled_jobs.allow_overlap`, `scheduled_jobs.dispatch_timeout_minutes`, `jobs.dispatch_timeout_minutes`; new tables: `scheduled_fire_log`, `job_templates` |
| `migration_v44.sql` | Dispatch correctness index | `CREATE INDEX CONCURRENTLY ix_jobs_status_created_at ON jobs (status, created_at)` |

!!! warning "migration_v44.sql — CONCURRENTLY transaction restriction"
    `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block.

    **Do not use:** `psql -1 -f migration_v44.sql` (the `-1` flag wraps in `BEGIN/COMMIT`)

    **Correct invocation:**
    ```bash
    docker exec -i puppeteer-db-1 \
      psql -U puppet puppet_db < puppeteer/migration_v44.sql
    ```

    **Pre-flight check** (confirm jobs table exists before running):
    ```sql
    SELECT COUNT(*) FROM jobs;
    ```

    **Validity confirmation** (run after to confirm index was created):
    ```sql
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'jobs' AND indexname = 'ix_jobs_status_created_at';
    ```

    **Naming note:** Despite the v17.0 milestone name, this migration is `migration_v44.sql` — the `migration_v17.sql` filename was already used in an earlier release (Phase 4 — operator_tags on nodes).

### SQLite note

Migration files use PostgreSQL's `IF NOT EXISTS` syntax on `ALTER TABLE`, which SQLite does not support. For local development with SQLite, the standard workflow is to delete `jobs.db` and let `create_all` rebuild it. If you need to preserve a local SQLite database, the SQL comments inside each migration file include the equivalent bare `ALTER TABLE` statements without guards.

---

## Post-upgrade verification

Run through this checklist after the agent starts:

- [ ] **Health endpoint returns 200**

    ```bash
    curl -sk https://localhost:8001/api/health
    ```

- [ ] **Login works** — sign in to the dashboard and confirm your session is valid

- [ ] **Nodes reconnect** — check the Nodes view; online nodes should show `ONLINE` status within 30 seconds of the agent starting

- [ ] **Audit log has a startup entry** — the AuditLog view should show a `SYSTEM_STARTUP` event timestamped at the restart time

- [ ] **Scheduled jobs are active** — the Job Definitions view should list all previously configured schedules with their next fire times

- [ ] **Run a smoke job** — dispatch a simple job to a known-good node and confirm it completes with status `COMPLETED`

---

## Rollback procedure

If the upgrade introduces a regression:

### Step 1 — Stop the agent

```bash
docker compose -f puppeteer/compose.server.yaml stop agent
```

### Step 2 — Restore the database backup

```bash
# Drop and recreate the database
docker exec puppeteer-db-1 \
  psql -U puppet -c "DROP DATABASE puppet_db;"
docker exec puppeteer-db-1 \
  psql -U puppet -c "CREATE DATABASE puppet_db;"

# Restore from backup
docker exec -i puppeteer-db-1 \
  psql -U puppet puppet_db < axiom_backup_YYYYMMDD_HHMMSS.sql
```

### Step 3 — Pin to the previous image

Tag the image you want to revert to. If you kept the previous image locally:

```bash
docker tag <previous-image-sha> localhost/master-of-puppets-server:rollback
```

Update `compose.server.yaml` (or set an env override) to reference the rollback tag, then:

```bash
docker compose -f puppeteer/compose.server.yaml up -d --no-build agent
```

### Step 4 — Verify

Repeat the [post-upgrade verification checklist](#post-upgrade-verification) against the restored state.

!!! warning "Migration SQL cannot be automatically reversed"
    `ALTER TABLE ADD COLUMN` statements are not automatically reversible. The database backup taken in the pre-upgrade checklist is the only reliable rollback path. **Always take the backup before running migration SQL.**

---

## Full-stack restart (all services)

If you need to restart the entire stack (e.g., after a PostgreSQL config change or a host reboot):

```bash
docker compose -f puppeteer/compose.server.yaml down
docker compose -f puppeteer/compose.server.yaml up -d
```

`create_all` runs on every startup and will create any tables that are missing from the current schema. It does not alter or drop existing tables, so this is always safe to run.

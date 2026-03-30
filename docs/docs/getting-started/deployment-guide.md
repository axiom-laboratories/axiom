# Production Deployment Guide

This guide covers infrastructure recommendations for Axiom EE deployments in local and air-gapped environments. It is aimed at BPO infrastructure teams, deployment engineers, and technical stakeholders preparing for a production rollout.

!!! note "Scope"
    These recommendations apply to **local and air-gapped deployments** — the target model for Axiom EE. Cloud-native HA patterns (load balancers, replica sets, automatic failover) are not the relevant frame here and are not covered.

---

## Understanding the Recovery Profile

Axiom EE's control plane runs as a single orchestrator process. For local deployments, the meaningful risks are:

- **Recovery time** — how long is the outage if the host VM goes down?
- **Data durability** — how much job state is lost if the host is unrecoverable?
- **Fleet behaviour** — do nodes recover automatically when the orchestrator returns?

Axiom's pull model directly addresses the third question. Nodes continuously retry their poll against the orchestrator. When the orchestrator returns — whether after a process crash or a full host restart — **the entire fleet resumes without any manual intervention or reconnection**. There is no push channel to re-establish.

!!! tip "Practical analogy"
    An orchestrator outage is operationally similar to a cron server rebooting: jobs do not fire during the downtime, and they resume when the server is back. BPO ops teams already know how to manage this risk. The recommendations below ensure that recovery is fast and data loss is bounded.

---

## Host Infrastructure

### Hypervisor-Layer HA

!!! tip "Strong recommendation"
    Deploy the Axiom EE orchestrator on a VM or host with managed uptime. If the host runs on a hypervisor platform with live migration or HA configured at the hypervisor layer, the recovery window for a host failure is measured in **seconds to minutes** — not hours. This is the single most impactful infrastructure decision for EE deployments.

Most enterprise BPO environments already run virtualisation infrastructure with HA policies. The orchestrator VM should be covered by whatever HA or live-migration policy applies to business-critical VMs in that environment.

| Platform | HA behaviour |
|----------|-------------|
| VMware vSphere HA | VM restarts automatically on another host within the cluster on host failure. Recovery typically 1–3 minutes. |
| Microsoft Hyper-V | Failover Clustering provides automatic VM restart on host failure. Live Migration enables near-zero-downtime planned maintenance. |
| Proxmox VE | HA Manager restarts VMs on surviving cluster nodes. Suitable for smaller BPO deployments. |
| Nutanix AHV | Built-in HA with automatic VM restart across the cluster. No additional configuration required. |
| Bare metal (no hypervisor) | Recovery depends on manual intervention. Not recommended for production EE deployments. If unavoidable, pair with a hardware watchdog and a documented runbook. |

### Docker Restart Policy

Regardless of hypervisor configuration, set Docker restart policies that handle process-level crashes without host intervention.

!!! tip "Strong recommendation"
    Set `restart: unless-stopped` on all Axiom services. A process crash (OOM kill, unhandled exception) results in an automatic container restart — typically within seconds.

```yaml
# compose.server.yaml — recommended restart policy for all EE services
services:
  agent:
    restart: unless-stopped
  db:
    restart: unless-stopped
  caddy:
    restart: unless-stopped
```

With `unless-stopped`, the service restarts automatically on any crash but stays stopped if explicitly halted (e.g. `docker compose stop`) — the correct behaviour for production.

---

## Data Durability

All meaningful state in an Axiom EE deployment lives in PostgreSQL: job history, audit log, node certificates, signing keys, RBAC configuration, and execution records. Protecting the database is the data durability strategy.

### Option 1 — Nightly pg_dump (Minimum Viable)

!!! tip "Strong recommendation — minimum viable data durability"
    A nightly `pg_dump` exported to a separate host provides the minimum acceptable data durability for a production EE deployment. In a catastrophic host failure, recovery means: restore the VM (or provision a new one), restore from backup, restart the stack. RPO is up to 24 hours; RTO depends on VM provisioning time.

```bash
#!/bin/bash
# /etc/cron.d/axiom-backup — run as root or docker user

BACKUP_HOST=backup.internal
BACKUP_PATH=/backups/axiom
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER=axiom-postgres

# Dump inside the container, stream to backup host via SSH
docker exec $CONTAINER pg_dump -U axiom axiom_db \
  | gzip \
  | ssh axiom-backup@$BACKUP_HOST \
      "cat > $BACKUP_PATH/axiom_${TIMESTAMP}.sql.gz"

# Retain 14 days of backups
ssh axiom-backup@$BACKUP_HOST \
  "find $BACKUP_PATH -name '*.sql.gz' -mtime +14 -delete"
```

Before going to production, confirm:

- [ ] Backup destination is on a **separate physical host** or network-attached storage — not a local mount on the same VM
- [ ] A test restore has been performed and the recovery time documented
- [ ] Backup success/failure is monitored and alerted — silent backup failure is the most common real-world failure mode
- [ ] Backup files are encrypted at rest if the destination host is in a shared environment

### Option 2 — PostgreSQL Streaming Replication

!!! tip "Recommended for high-volume or compliance-sensitive deployments"
    A PostgreSQL streaming read replica on a second host reduces RPO to seconds (the replication lag) and provides a warm standby that can be promoted to primary on host failure.

**Primary host configuration:**

```ini
# postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 256MB    # retain WAL for replica catchup
```

```
# pg_hba.conf — allow replication user from replica host
host  replication  axiom_replica  <REPLICA_IP>/32  scram-sha-256
```

**Initial replica sync:**

```bash
pg_basebackup -h <PRIMARY_IP> -U axiom_replica -D /var/lib/postgresql/data \
  -P -Xs -R

# The -R flag writes standby.signal and primary_conninfo automatically.
# Start postgres on the replica — it will begin streaming replication.
```

!!! warning "Promotion requires manual intervention"
    If the primary host fails, promoting the replica requires manual steps: remove `standby.signal`, adjust `primary_conninfo`, restart. **Document this runbook before you need it.**

Key points:

- The read replica carries a full copy of all Axiom state — apply the same access controls as the primary
- The replica can serve read-only queries for audit log access without load on the primary — useful for BPO audit workflows
- If the client environment has a DBA team, streaming replication is a standard operation they will already be familiar with

---

## Deployment Configuration Comparison

| Configuration | RPO | RTO | Complexity | Recommended for |
|---------------|-----|-----|------------|-----------------|
| pg_dump nightly + managed VM | Up to 24h | Minutes (VM recovery) | Low | Most EE deployments |
| pg_dump nightly + bare metal | Up to 24h | Hours (manual recovery) | Low | Not recommended for production |
| Streaming replica + managed VM | Seconds (lag-dependent) | Minutes (manual promotion) | Medium | High-volume or compliance-sensitive |

---

## Air-Gap Deployments

Axiom EE is designed to operate in network-isolated environments. The documentation site, Foundry image builds, and node execution runtime can all run without outbound internet access after initial setup.

For a full from-scratch setup guide, see [Package Mirror Runbooks](../runbooks/package-mirrors.md) — covering devpi (PyPI), apt-cacher-ng (APT), and BaGet (NuGet/PowerShell) mirror configuration. For a full overview of what is already offline-capable and what requires substitution, see [Air-Gap Operation](../security/air-gap.md).

---

## Pre-Deployment Checklist

### Host Infrastructure

- [ ] Orchestrator VM is deployed on managed hypervisor infrastructure with HA or live-migration policy
- [ ] VM is covered by existing business-critical uptime SLA
- [ ] Docker restart policies set to `unless-stopped` for all Axiom services
- [ ] Expected recovery time for host restart documented and agreed with client

### Data Durability

- [ ] Nightly `pg_dump` configured and tested — restore procedure documented
- [ ] Backup destination is on a separate host from the orchestrator
- [ ] Backup success monitored and alerted
- [ ] Backup retention period agreed with client (minimum 14 days recommended)
- [ ] If streaming replication required: replica provisioned, tested, and promotion runbook documented

### Node Fleet Behaviour

- [ ] Client team understands pull-model recovery: nodes resume automatically when orchestrator returns
- [ ] Node poll interval configured appropriately for acceptable job-start latency during recovery
- [ ] Fleet recovery tested: orchestrator restarted, nodes confirmed to resume without intervention

---

## Related Guides

- [Running with Docker](docker-deployment.md) — stack startup, secret generation, production checklist
- [Air-Gap Operation](../security/air-gap.md) — what is already offline-capable and what requires substitution
- [Package Mirror Runbooks](../runbooks/package-mirrors.md) — devpi, apt-cacher-ng, and BaGet mirror setup for air-gapped environments
- [Node Troubleshooting](../runbooks/nodes.md) — diagnosing node connectivity and enrollment issues

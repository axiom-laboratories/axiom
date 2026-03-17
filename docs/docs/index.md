# Master of Puppets

**Master of Puppets** is a self-hosted orchestration platform for managing distributed agent nodes — deploy jobs, schedule tasks, and monitor your fleet from a central control plane.

## What it does

- **Node management** — Puppet nodes self-enroll via mTLS and poll for work. No inbound firewall rules needed.
- **Job dispatch** — Submit signed Python scripts to nodes matched by capability tags and resource limits.
- **Scheduled jobs** — Cron-based job definitions with APScheduler, scoped to node capability sets.
- **Foundry** — Build custom node images from runtime and network blueprints via the dashboard.
- **RBAC** — Three roles (`admin`, `operator`, `viewer`) with per-permission grants, service principals, and API keys.
- **Audit log** — All security-relevant actions logged and queryable from the dashboard.

## Architecture overview

```
Puppeteer (Control Plane)  ←── mTLS ──→  Puppet Nodes
  ├── Agent Service (8001)                  └── Polls /work/pull every N sec
  ├── Model Service (8000)                      Executes jobs, reports results
  ├── PostgreSQL
  └── React Dashboard
```

Nodes initiate all connections to the control plane — the **pull model** means no inbound ports need to be open on your nodes.

## Getting started

| Goal | Where to go |
|------|-------------|
| Check your environment before installing | [Prerequisites](getting-started/prerequisites.md) |
| Install and run the stack | [Install](getting-started/install.md) |
| Connect your first node | [Enroll a Node](getting-started/enroll-node.md) |
| Dispatch your first job | [First Job](getting-started/first-job.md) |
| Build custom node images | [Foundry Guide](feature-guides/foundry.md) |
| Push jobs from the CLI | [mop-push CLI](feature-guides/mop-push.md) |
| Explore the REST API | [API Reference](api-reference/index.md) |

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0--alpha-orange.svg)](#)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Faxiom-laboratories%2Faxiom.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Faxiom-laboratories%2Faxiom?ref=badge_shield)

# Axiom

Axiom is a secure automation and orchestration platform for running jobs across distributed nodes. It uses mTLS-enrolled nodes, Ed25519-signed jobs, and container-isolated execution, with a React dashboard and CLI for day-to-day operations.

## Key Capabilities

- **mTLS node enrollment** — nodes join via one-time tokens; each holds a unique X.509 client certificate
- **Ed25519 job signing** — all jobs must be cryptographically signed before dispatch; nodes verify before execution
- **Container-isolated execution** — jobs run in Docker or Podman containers with configurable resource limits
- **Role-Based Access Control** — admin, operator, and viewer roles with per-permission granularity
- **Foundry image builder** — compose custom node images from blueprint ingredients via a guided UI wizard
- **Smelter Registry** — vetted ingredient catalog with CVE scanning and lifecycle enforcement
- **axiom-push CLI** — OAuth 2.0 device flow authentication, job signing, and push workflow from the terminal
- **Job scheduling** — APScheduler-backed cron definitions with capability targeting and node selection

## Community Edition vs Enterprise Edition

| Feature | CE (Apache 2.0) | EE (Proprietary) |
|---------|-----------------|------------------|
| Core orchestrator + Axiom Nodes | Yes | Yes |
| Job scheduling (cron + capability targeting) | Yes | Yes |
| mTLS node enrollment and certificate lifecycle | Yes | Yes |
| Ed25519 job signing and verification | Yes | Yes |
| Role-Based Access Control (RBAC) | Yes | Yes |
| Foundry image builder | Yes | Yes |
| Smelter Registry (CVE scanning, ingredient catalog) | Yes | Yes |
| Package Mirroring (offline/air-gapped builds) | Yes | Yes |
| axiom-push CLI with OAuth device flow | Yes | Yes |
| Job Staging and publish workflow | Yes | Yes |
| MkDocs documentation site | Yes | Yes |
| Single Sign-On (SSO / OIDC) | — | Yes |
| Advanced RBAC (attribute-based, time-limited grants) | — | Yes |
| Enterprise audit and compliance reporting | — | Yes |

CE is free forever under the Apache License 2.0. See [LICENSE](LICENSE) and [LEGAL.md](LEGAL.md).

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/axiom.git
cd axiom

# Copy and configure environment variables
cp puppeteer/.env.example puppeteer/.env
# Edit puppeteer/.env — set SECRET_KEY, ENCRYPTION_KEY, ADMIN_PASSWORD

# Start the full stack
docker compose -f puppeteer/compose.server.yaml up -d
```

The dashboard is available at `https://localhost` once the stack is up. The default admin credentials are set by `ADMIN_PASSWORD` in your `.env` file.

For the complete setup guide — including node enrollment, job signing, and production configuration — see the documentation.

## Documentation

Full documentation is served within a running Axiom instance at `/docs/`, built with MkDocs Material. It covers getting started, feature guides, security, runbooks, and the API reference.

Online: [https://dev.master-of-puppets.work/docs/](https://dev.master-of-puppets.work/docs/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute, the CLA, and the enterprise edition boundary.

## License

Apache License 2.0 — see [LICENSE](LICENSE).


[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Faxiom-laboratories%2Faxiom.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Faxiom-laboratories%2Faxiom?ref=badge_large)
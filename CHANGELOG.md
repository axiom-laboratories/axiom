# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Entries for v0.7.0–v0.9.0 are retroactive milestone summaries
> recorded before the project was renamed to Axiom. Semantic versioning
> from `[1.0.0-alpha]` forward is the canonical release line.

## [Unreleased]

## [1.0.0-alpha] - 2026-03-17

Initial public release as **Axiom CE** (Community Edition, Apache 2.0).

### Added

- Axiom Orchestrator: FastAPI control plane with PostgreSQL/SQLite backend
- Axiom Nodes: mTLS-enrolled worker nodes executing jobs in container isolation
- Ed25519 job signing — all jobs must be cryptographically signed before dispatch
- Role-Based Access Control (RBAC) with admin, operator, and viewer roles
- Foundry image builder: compose Docker images from blueprint ingredients via a 5-step wizard
- Smelter Registry: vetted ingredient catalog with CVE scanning and STRICT/WARNING enforcement
- Package Mirroring: local PyPI and APT mirrors for offline/air-gapped node builds
- axiom-push CLI: OAuth 2.0 device flow authentication, Ed25519 signing, and push workflow
- Job Staging: review and publish workflow with staging tab in dashboard
- Job scheduling: APScheduler-backed cron definitions with capability targeting
- React dashboard: node monitoring, job queue, Foundry wizard, RBAC management, audit log
- MkDocs documentation site: containerised, served within the stack at `/docs/`

## [0.9.0] - 2026-03-17 — MkDocs Documentation Site

### Added

- MkDocs Material documentation site containerised and served at `/docs/`
- OpenAPI reference auto-generated from FastAPI schema at build time
- Full operator documentation: getting started, feature guides, security, runbooks, FAQ
- Air-gap operation guide and mTLS certificate rotation procedures

## [0.8.0] - 2026-03-15 — axiom-push CLI & Job Staging

### Added

- `axiom-push` CLI: install, OAuth 2.0 device flow login, Ed25519 signing, and push workflow
- Job Staging: staged jobs require maintainer review before dispatch to nodes
- OAuth 2.0 RFC 8628 device flow for non-interactive CLI authentication
- REVOKED node enforcement at job dispatch

## [0.7.0] - 2026-03-16 — Advanced Foundry & Smelter

### Added

- Foundry: 5-step wizard for composing custom Docker node images from blueprints
- Smelter Registry: curated ingredient catalog with CVE scanning
- Package Mirroring: local PyPI/APT mirrors for air-gapped builds
- Smelt-Check: post-build ephemeral validation and JSON Bill of Materials
- Image lifecycle management: ACTIVE / DEPRECATED / REVOKED states

---
created: 2026-03-28T17:26:51.990Z
title: Licence generation tooling and private repo for issued EE licences
area: general
files:
  - mop_sdk/cli.py
---

## Problem

We have Ed25519 licence validation in the orchestrator (Phase 73) and a licence signing keypair, but there is no easy operator-facing workflow to:
1. Generate a new customer licence (specify customer_id, tier, node_limit, expiry)
2. Store the issued licence for future reference / renewal tracking
3. Share the licence securely with the customer

Currently this requires running the low-level signing tool manually with no standard parameters or audit trail.

## Solution

**Short term — tooling + local storage:**
- Extend `axiom-push` CLI (or create a standalone `axiom-admin` CLI) with a `licence issue` subcommand:
  - Parameters: `--customer`, `--tier` (EE), `--nodes`, `--expiry`, `--features`
  - Reads private signing key from `~/.axiom/licence-signing.key` (separate from job signing key)
  - Outputs a base64 licence blob + a human-readable JSON summary
- Store issued licences as files in a `licences/issued/` directory (YAML or JSON per customer)
  - File per customer: `customer-id.yml` with issued_at, expiry, tier, node_limit, licence_blob
- Store this tooling + issued licences in a **separate private GitHub repo** under the axiom-laboratories org (e.g. `axiom-laboratories/axiom-licences`)
  - Private: never expose the signing private key or customer details in the public repo
  - For now, issued licences can also be stored here in `licences/` for bootstrapping

**Medium term — web UI or GitHub Actions workflow:**
- A GitHub Actions workflow in the private repo triggered manually (workflow_dispatch) with customer inputs → issues a licence → commits the record + emails/posts the blob to the customer
- Or a minimal internal web UI (could be a simple FastAPI app) for generating and tracking licences

**Long term — production licence service:**
- Dedicated service with a database of customers, licence records, renewal tracking, and webhook/API for on-demand issuance
- Integration with billing/CRM

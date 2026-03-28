---
created: 2026-03-28T17:26:51.990Z
title: Licence generation tooling and private repo for issued EE licences
area: general
files: []
---

## Problem

We have Ed25519 licence validation in the orchestrator (Phase 73) and a licence signing keypair, but there is no easy internal workflow to:
1. Generate a new customer licence (specify customer_id, tier, node_limit, expiry)
2. Store the issued licence for future reference / renewal tracking
3. Deliver the blob to the customer

This is an **internal operator/developer tool** — entirely separate from the customer-facing `axiom-push` CLI. Customers never run this; they just receive the licence blob and drop it in `AXIOM_LICENCE_KEY` in their `secrets.env`.

## Solution

**Private repo: `axiom-laboratories/axiom-licences`**

```
axiom-licences/
  tools/
    issue_licence.py       ← standalone script, no install required
  licences/
    issued/
      <customer-id>.yml    ← one record per customer (committed as audit log)
  keys/
    licence.pub            ← verification public key (safe to commit)
    README.md              ← "private key lives in 1Password / secrets manager"
```

**`issue_licence.py`** — standalone Python script using the `cryptography` lib (already a dep):
- Args: `--customer`, `--tier EE`, `--nodes N`, `--expiry YYYY-MM-DD`, `--features f1,f2`
- Reads private signing key from `AXIOM_LICENCE_SIGNING_KEY` env var or `--key` path arg
- Signs JSON payload with Ed25519: `{customer_id, tier, node_limit, expiry_date, issued_at, features}`
- Prints base64 licence blob to stdout (operator copies → sends to customer)
- Writes `licences/issued/<customer-id>.yml` with full record (operator commits + pushes)

**Medium term:**
- GitHub Actions `workflow_dispatch` in the private repo: inputs → issue → commit record → output blob

**Long term:**
- Dedicated service with customer DB, renewal tracking, and on-demand issuance API

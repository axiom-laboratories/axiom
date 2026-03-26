---
created: 2026-03-26T21:32:05.519Z
title: License key generation and validation with air-gap support
area: general
files: []
---

## Problem

EE tier needs a licensing mechanism. Requirements:
1. Generate license keys (offline-signable, customer-specific)
2. Validate them at orchestrator startup and/or periodically at runtime
3. Support air-gapped deployments where the orchestrator cannot phone home — timeout/expiry must still be enforceable without a live license server

The air-gap case is the hard part: if the license check requires a network call, it fails in air-gapped installs. If expiry is purely clock-based, a customer can freeze their system clock to bypass it.

## Solution (approach to research/design)

**Key generation:**
- Use Ed25519 (already used for job signing in the stack) to sign a JSON payload: `{customer_id, tier, node_limit, expiry_date, issued_at, features: [...]}`
- Admin tooling generates the key offline with the private signing key (never distributed)
- Delivered to customers as a base64 blob

**Validation:**
- On startup: verify signature with the embedded public key, check expiry_date against system clock
- EE features gated behind a valid, non-expired license check in the backend

**Air-gap expiry enforcement (options to evaluate):**
- **Trusted timestamp approach**: Include a "not-before" + "not-after" window; on each startup log the boot time to a tamper-evident local file (hash chain). If the recorded history shows time going backwards, refuse to start.
- **Grace period model**: License is valid for N days beyond expiry before hard-cutoff — gives air-gapped customers time to renew without being locked out mid-operation
- **Heartbeat file**: On each startup write a signed timestamp file locally; validate monotonicity on next boot. Doesn't require network but makes clock-rollback detectable.
- **No hard cutoff in air-gap tier**: For fully air-gapped EE, consider a "time-unlimited but node-limited" license model and charge for node count increases instead of renewals

**Open questions:**
- Where does the license file live? (`secrets.env` var vs. file path vs. DB config entry)
- What happens on expiry — hard stop or degraded mode (CE feature set)?
- Do we want a license server as an optional online check for non-air-gapped EE?

---
title: Cryptographically signed job execution
area: security
status: pending
created_at: 2026-03-16
tags: [security, jobs, execution, ed25519]
---

# Cryptographically signed job execution

## Description
Ensure that all jobs executed by the nodes are cryptographically signed and verified using Ed25519 signatures. This task involves:
- Verifying the signature on the node side before execution.
- Ensuring the SDK handles signing correctly for all job types.
- Validating the trust model between Puppeteer and the Nodes for public key distribution.

## Related Files
- `puppeteer/agent_service/security.py`
- `mop_sdk/signer.py`
- `puppets/environment_service/node.py`

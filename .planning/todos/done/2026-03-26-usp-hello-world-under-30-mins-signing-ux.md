---
created: 2026-03-26T21:32:05.519Z
title: USP — hello world job executing in under 30 mins (CE)
area: general
files:
  - puppeteer/dashboard/src/views/Signatures.tsx
  - puppeteer/agent_service/main.py
---

## Problem

Target USP: a new user with Docker installed can have a CE node enrolled and a hello world job executing in under 30 minutes. This is achievable in principle but the job signing flow is the critical blocker.

Current friction points:
1. Keypair generation lives in a sister repo (`admin_signer.py`) — no onboarding story, not documented in getting-started
2. Signing a script requires a separate CLI tool invocation — not intuitive for first-timers
3. "Signature verification failed" errors give no guidance on what to do next
4. The join token → node deploy flow is clear, but signing comes before job dispatch and trips people up

Rough time breakdown (today): image pull ~5m, login ~2m, signing setup ~8-10m, node deploy ~5m, dispatch ~2m = ~22-24m best case, much longer if signing goes wrong.

## Solution

The signing UX needs to be first-class to hit the 30-min USP reliably:

**Option A — Dashboard keypair generation (RULED OUT):**
- ~~"Generate signing key" button in Signatures view~~
- **Do not implement.** If a malicious actor gains dashboard access, having the private key generated or transiently held server-side completely undermines the job signing security model — the whole point of signing is that the orchestrator never controls the private key. Dashboard access must not be sufficient to forge job signatures.

**Option B — First-run demo keypair:**
- Orchestrator ships with a pre-generated keypair for first-run/demo mode
- Dashboard shows the corresponding `axiom sign hello_world.py` command ready to copy
- User never has to understand PKI to get their first job running
- Can be replaced with a real keypair before going to production

**Option C — CLI tool ships with the stack:**
- `axiom` CLI (or a simple Python script) bundled in the orchestrator container or available as a standalone install
- `axiom sign script.py` — reads key from `~/.axiom/signing.key` or env var

**Getting-started doc changes regardless:**
- Add explicit signing step to the install guide with copy-paste commands
- Link to key generation from the job dispatch UI ("Don't have a signing key yet? →")
- Better error messages when signature verification fails

## Success criteria for the USP

Time a fresh install end-to-end on a clean machine. Sub-30 min with no prior knowledge of Axiom = USP confirmed.

## Implementation (completed 2026-03-29)

Implemented Option B:
- Generated demo Ed25519 keypair; committed both files to repo (`puppeteer/demo_signing_key.pem`, `puppeteer/demo_verification_key.pem`)
- Added `.gitignore` exceptions for these two specific files
- Startup seed logic in `main.py`: if no signature records exist and `demo_verification_key.pem` is present, seeds a `Signature` row with id `demo0000000000000000000000000000` and name "Demo Key (Getting Started)"
- `Signatures.tsx`: amber "Getting Started" banner shown when demo key is the only registered key; "How to sign a script" button opens a modal with copy-paste Python signing commands
- Improved all signature verification error messages in `main.py` and `scheduler_service.py` to be actionable and reference the Signatures page
- Updated `docs/docs/getting-started/first-job.md` with a new "Zero-setup: demo key" section at the top

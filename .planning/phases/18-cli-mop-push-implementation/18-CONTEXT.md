# Phase 18 Context: mop-push CLI Implementation

## Phase Goal
The `mop_sdk` package is updated to include a `mop-push` CLI that allows operators to authenticate via OAuth Device Flow, sign scripts locally with Ed25519, and manage job definitions (staging and direct creation) from the terminal.

## Requirements (from ROADMAP.md)
- **AUTH-CLI-03**: `mop-push login` triggers device flow and saves JWT.
- **AUTH-CLI-04**: CLI reuses JWT; handles expiry.
- **CLI-01**: `mop-push job push` signs and pushes a DRAFT.
- **CLI-02**: `mop-push job push --id` updates an existing job.
- **CLI-03**: `mop-push job create` creates a fully-scheduled ACTIVE job.
- **CLI-04**: Private key never sent over network.
- **CLI-05**: `pip install ./mop_sdk` provides the command.

## Verification Criteria
- `mop-push login` successfully obtains a JWT from the backend.
- `mop-push job push` creates a DRAFT job in the database with the correct Ed25519 signature.
- `mop-push job create` creates an ACTIVE job with schedule and tags.
- CLI commands fail gracefully with clear error messages when the token is missing or expired.
- Private keys remain on the local machine.

## Implementation Waves
1. **Wave 1: Packaging & Plumbing**: Create `pyproject.toml`, `mop_sdk/cli.py` skeleton, and unit test harness.
2. **Wave 2: Device Flow Auth**: Implement `mop-push login` and credential storage.
3. **Wave 3: Job Staging & Signing**: Implement `mop-push job push` and `mop-push job create` with local signing.
4. **Wave 4: Verification**: Final E2E tests and documentation update.

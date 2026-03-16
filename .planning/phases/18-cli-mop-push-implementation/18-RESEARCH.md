# Phase 18 Research: mop-push CLI Implementation

## Objective
Implement the `mop-push` CLI within the `mop_sdk` package to support OAuth Device Flow authentication, local Ed25519 job signing, and job staging (pushing DRAFTs).

## Domain Research

### 1. OAuth Device Flow (RFC 8628) in CLI
- **Flow**: 
  1. CLI calls `POST /auth/device`.
  2. Server returns `device_code`, `user_code`, and `verification_uri_complete`.
  3. CLI displays the user code and instructions to the user.
  4. CLI attempts to open the browser (using `webbrowser` module) or waits for manual user action.
  5. CLI polls `POST /auth/device/token` with the `device_code` every `interval` seconds.
  6. CLI handles error responses: `authorization_pending` (continue polling), `slow_down` (increase interval), `access_denied`, `expired_token`.
  7. On success, CLI receives `access_token` and `role`.

### 2. Local Credential Storage
- **Path**: `~/.mop/credentials.json`
- **Shape**:
  ```json
  {
    "base_url": "https://mop.example.com",
    "access_token": "eyJhbG...",
    "role": "admin",
    "username": "thomas"
  }
  ```
- **Permissions**: `0600` (read/write by owner only).

### 3. Ed25519 Signing (Local)
- CLI must load an Ed25519 private key from disk (PEM format).
- Use `cryptography` library (already in `requirements.txt`).
- Sign the UTF-8 encoded script body.
- Base64-encode the resulting signature for the `POST /api/jobs/push` request.

### 4. Package Entry Points
- Create `pyproject.toml` in the root (or `mop_sdk/` if preferred, but root is standard for this repo).
- Define `mop-push = "mop_sdk.cli:main"`.

## Requirements Mapping
- **AUTH-CLI-03**: `mop-push login` triggers device flow and saves JWT.
- **AUTH-CLI-04**: CLI reuses JWT; handles expiry.
- **CLI-01**: `mop-push job push` signs and pushes a DRAFT.
- **CLI-02**: `mop-push job push --id` updates an existing job.
- **CLI-03**: `mop-push job create` creates a fully-scheduled ACTIVE job (requires scheduler fields).
- **CLI-04**: Private key never sent over network.
- **CLI-05**: `pip install ./mop_sdk` provides the command.

## Proposed Component Architecture
- `mop_sdk/cli.py`: Argparse entry point.
- `mop_sdk/auth.py`: Device flow and credential management logic.
- `mop_sdk/signer.py`: Ed25519 signing helper.
- `mop_sdk/client.py`: Update `MOPClient` to support `push` and `create` methods.

## Verification Plan
- **Mock Server**: Use a local instance of the `puppeteer` backend.
- **Automated Tests**:
  - Test CLI argument parsing.
  - Test signing logic.
  - Test credential loading/saving.
- **Manual Verification**:
  - `mop-push login` -> browser approval -> token saved.
  - `mop-push job push` -> job appears as DRAFT in backend.

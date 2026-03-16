# Phase 18 Validation Strategy: mop-push CLI

## Automated Tests
- **CLI Harness**: Unit tests for `argparse` configuration in `mop_sdk/cli.py`.
- **Signing Logic**: Unit tests for `mop_sdk/signer.py` using mock scripts and keys.
- **Auth Persistence**: Unit tests for credential loading/saving in `mop_sdk/auth.py`.
- **Mocked Backend**: Integration tests for `MOPClient.push` and `MOPClient.create` with mocked API responses.

## Manual E2E Verification
Requires a running `puppeteer` backend.

### 1. Installation Gate
- **Action**: `pip install ./mop_sdk`
- **Verification**: `mop-push --help` works.

### 2. Device Flow Auth
- **Action**: `mop-push login --url https://localhost:8001`
- **Verification**: User code displayed, browser opens, approval page appears. After approval, `~/.mop/credentials.json` exists and contains a valid JWT.

### 3. Job Staging (DRAFT)
- **Action**: `mop-push job push --name test-cli-job --script examples/basic_automation.py --key verification.key`
- **Verification**: Command returns success with Job ID. Backend `ScheduledJob` table has a new entry with `status='DRAFT'`.

### 4. Job Creation (ACTIVE)
- **Action**: `mop-push job create --name active-cli-job --script examples/basic_automation.py --key verification.key --cron "*/10 * * * *" --tags env:test`
- **Verification**: Backend `ScheduledJob` table has a new entry with `status='ACTIVE'`, matching cron, and tags.

### 5. Token Expiry
- **Action**: Manually corrupt or expire the JWT in `credentials.json`.
- **Verification**: `mop-push job push ...` returns a clear authentication error.

## Success Metrics
- 100% pass rate on new automated tests.
- All 5 manual E2E scenarios pass on a fresh virtual environment.

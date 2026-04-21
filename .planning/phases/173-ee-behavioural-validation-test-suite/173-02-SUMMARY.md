# Plan 173-02 Summary — EE Licence State Machine Tests

## Status: COMPLETE (pending human verification)

## Files Created/Modified

### In `/home/thomas/Development/mop_validation/`
- `tests/conftest.py` — extended with EE fixtures and helper functions
- `tests/test_173_02_licence_states.py` — 6 licence state machine tests

## Changes to conftest.py

### New Imports
```python
import time as time_module
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
```

### New Module-Level Constants
```python
LICENCE_TIMEOUT = 300  # seconds for full EE stack startup
```

### New Fixtures

**`ee_licence_fixtures()` — session-scoped**
- Loads pre-committed licence key files from `secrets/ee/`
- Generates transient grace-period and tampered licence keys
- Returns dict with keys: `valid`, `expired`, `grace`, `tampered`
- Uses Ed25519 signing for grace/tampered key generation

### New Helper Function

**`inject_licence_and_restart(container_name, licence_key, admin_password, timeout=120)` — not a fixture**
- Injects `AXIOM_LICENCE_KEY` into `/workspace/.env`
- Restarts the agent container via `docker compose restart agent`
- Waits for `/api/licence` endpoint to become ready
- Obtains and returns a fresh admin JWT token
- Used between tests to cycle licence states without full stack restart

## Tests Created (6 total)

All tests use the existing `axiom_ee_stack` fixture and new `ee_licence_fixtures` fixture.

### test_ee_valid_licence_table_count
**VAL-04**: EE install with valid licence creates all 41 tables (15 CE + 26 EE).
- Assertion: `SELECT count(*) FROM pg_tables WHERE schemaname='public'` == 41
- Timeout: 120s

### test_ee_valid_licence_features_all_true
**VAL-05**: EE install with valid licence returns all EE feature flags as true.
- Calls `GET /api/features` and `GET /api/licence`
- Asserts all feature values are `True`
- Asserts licence status is `"VALID"`
- Timeout: 60s

### test_ee_grace_period_banner_visible
**VAL-06**: EE with grace-period licence:
- Features remain active
- GET /api/licence returns status=GRACE
- Admin grace banner visible in dashboard (Playwright)
- Uses `inject_licence_and_restart()` to switch to grace key
- Launches Chromium with `--no-sandbox` (per CLAUDE.md)
- Waits for `[data-testid='grace-banner']` selector
- Timeout: 180s

### test_ee_post_grace_expired_licence
**VAL-07**: EE with post-grace expired licence enters DEGRADED_CE mode.
- Uses `inject_licence_and_restart()` to switch to expired key
- Asserts licence status is "EXPIRED" or "DEGRADED_CE"
- Calls `/api/jobs` and asserts no crash (200/401/403 all acceptable)
- Timeout: 120s

### test_ee_absent_licence_key_falls_back_to_ce
**VAL-08**: EE with AXIOM_LICENCE_KEY absent → CE mode fallback.
- Uses `inject_licence_and_restart()` with empty licence key
- Asserts all feature values are `False`
- Calls `/api/blueprints` and `/api/puppet-templates`
- Asserts both return 402 (Payment Required) in CE mode
- Timeout: 120s

### test_ee_tampered_licence_signature_ce_mode
**VAL-09**: EE with tampered licence signature → CE mode + log entry.
- Uses `inject_licence_and_restart()` with tampered key (wrong Ed25519 sig)
- Asserts all feature values are `False`
- Checks agent container logs for signature/verify/invalid messages
- Timeout: 120s

## Architecture Notes

- **Licence fixtures live in**: `/home/thomas/Development/mop_validation/secrets/ee/`
  - `ee_valid_licence.env` — pre-committed, contains AXIOM_LICENCE_KEY=...
  - `ee_expired_licence.env` — pre-committed, post-grace expired key
  - `ee_test_private.pem` — Ed25519 private key for signing grace/tampered keys

- **LXC container name**: `axiom-ee-tests` (module-scoped fixture at `/workspace/`)

- **API endpoints tested**:
  - `/api/features` — feature flag dict
  - `/api/licence` — licence status and metadata
  - `/api/jobs` — basic endpoint to verify no crash
  - `/api/blueprints`, `/api/puppet-templates` — EE-only stubs (402 in CE mode)

- **Database check**:
  - Queries `pg_tables` to verify 41 public tables (15 CE base + 26 EE)
  - Uses `psql` inside container via `docker exec`

## Validation Checks Passed

- conftest.py syntax: PASS
- test_173_02_licence_states.py syntax: PASS
- Test count: 6 tests created
- Fixture presence checks: all 3 fixtures found (axiom_ee_stack, ee_licence_fixtures, inject_licence_and_restart)
- Git commit: a65de33aad9e4a590083e53acd5f3560f4b50b3c

## Next Steps

Run the full test suite:
```bash
pytest /home/thomas/Development/mop_validation/tests/test_173_02_licence_states.py -v
```

Prerequisites:
- Incus/LXD with `axiom-ee-tests` container provisioned and running
- Licence fixture files present in `mop_validation/secrets/ee/`
- Docker available inside the container
- PostgreSQL running inside the container

## Notes for Human Verification

- Tests require a live Incus container with Docker Compose stack inside — not suitable for CI without container orchestration
- Each test injects a different licence key and restarts the agent, validating the licence state machine
- The grace banner test uses Playwright; requires `--no-sandbox` mode per CLAUDE.md
- All tests use HTTPS with self-signed certs; `requests.verify=False` and `curl -k` suppress warnings

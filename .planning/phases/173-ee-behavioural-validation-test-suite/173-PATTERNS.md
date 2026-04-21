# Phase 173: EE Behavioural Validation Test Suite — Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 5 test files
**Analogs found:** 5 / 5

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `mop_validation/tests/conftest.py` | conftest/fixture | test-lifecycle | `axiom-licenses/tests/conftest.py` | exact |
| `mop_validation/tests/test_173_01_ce_validation.py` | test/integration | docker-exec + curl | `mop_validation/scripts/verify_ce_tables.py` + `verify_ce_stubs.py` | role-match |
| `mop_validation/tests/test_173_02_licence_states.py` | test/integration | incus-exec + docker-restart | `mop_validation/scripts/run_ee_scenario.py` | exact |
| `mop_validation/tests/test_173_03_wheel_security.py` | test/unit | direct import | `axiom-licenses/tests/test_issue_licence.py` | role-match |
| `mop_validation/tests/test_173_04_node_limit.py` | test/integration | incus-exec + API | `mop_validation/scripts/run_ee_scenario.py` | role-match |
| `mop_validation/tests/test_173_04_coverage_assertion.py` | test/assertion | parametrized | `puppets/environment_service/tests/test_node.py` | role-match |

## Pattern Assignments

### `mop_validation/tests/conftest.py` (conftest, test-lifecycle)

**Analog:** `axiom-licenses/tests/conftest.py`

**Imports pattern** (lines 1-12):
```python
import base64
import json
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
```

**Fixtures pattern** (lines 14-87):
```python
@pytest.fixture
def temp_wheel_dir():
    """Temporary directory for test wheel files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def test_keypair():
    """Generate a fresh Ed25519 keypair for tests."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    # ... return tuple
```

**Additional patterns to add** (from `run_ce_scenario.py`, `run_ee_scenario.py`):
- **Module-scoped LXC fixture** (`test_173_01_ce_validation.py` uses): setup/teardown once per test module
  - Calls `run_ce_scenario.reset_stack()`
  - Calls `run_ce_scenario.wait_for_stack(timeout=600)`
  - Yields LXC container name and base URL
  - See `run_ce_scenario.py` lines 104-134
- **Module-scoped EE LXC fixture** (`test_173_02_licence_states.py` uses): similar pattern
  - Calls `run_ee_scenario.reset_stack_ee()` (licence key injected)
  - Calls `run_ee_scenario.wait_for_stack(timeout=300)`
  - Calls `run_ee_scenario.get_admin_token()` for API auth
  - See `run_ee_scenario.py` lines 108-160
- **Licence key fixtures** (`test_173_02_licence_states.py` uses):
  - Load `mop_validation/secrets/ee/ee_valid_licence.env`
  - Load `mop_validation/secrets/ee/ee_expired_licence.env`
  - Generate grace-period and tampered keys at session setup via `generate_ee_licence.py`
  - See `generate_ee_licence.py` lines 82-108 for generation pattern
- **Admin token fixture** (parametric, used in multiple tests):
  - Calls `run_ee_scenario.get_admin_token()` with retry loop
  - See `run_ee_scenario.py` lines 210-237

---

### `mop_validation/tests/test_173_01_ce_validation.py` (test/integration, docker-exec + curl)

**Analogs:** 
- `mop_validation/scripts/verify_ce_tables.py` (docker exec psql pattern)
- `mop_validation/scripts/verify_ce_stubs.py` (requests + curl pattern)

**Imports pattern** (from `verify_ce_tables.py` lines 1-26):
```python
import subprocess
import sys
from pathlib import Path

import pytest
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

**Postgres table count assertion** (`verify_ce_tables.py` lines 89-105):
```python
# Via docker exec psql
query = (
    "SELECT count(*) FROM pg_tables "
    "WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"
)
result = subprocess.run(
    [
        "docker", "exec", pg_container,
        "psql", "-U", "puppet", "-d", "puppet_db",
        "-t", "-c", query,
    ],
    capture_output=True,
    text=True,
    timeout=15,
)
if result.returncode == 0:
    count = int(result.stdout.strip())
    passed = count == EXPECTED_TABLE_COUNT
```

**Stack readiness polling** (`verify_ce_stubs.py` lines 69-83):
```python
def wait_for_stack(base_url: str, timeout: int = 90) -> bool:
    """Poll /api/features every 3 s until ready or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/api/features", verify=False, timeout=5)
            if resp.status_code == 200:
                print()
                return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print()
    return False
```

**API assertions pattern** (`verify_ce_stubs.py` lines 137-172):
```python
# EE stub routes must return 402 on CE install
EE_STUB_ROUTES = [
    ("GET",  "/api/blueprints",          "foundry"),
    ("GET",  "/api/smelter/ingredients", "smelter"),
    # ... 7 routes total
]

for method, path, domain in EE_STUB_ROUTES:
    try:
        if method == "GET":
            resp = requests.get(
                f"{BASE_URL}{path}",
                headers=headers,
                verify=False,
                timeout=10,
            )
        passed = resp.status_code == 402  # Expected for CE
        results.append((path, passed))
    except Exception as exc:
        results.append((path, False))
```

**Feature flag assertion** (`verify_ee_install.py` lines 273-295):
```python
# Check /api/features — all false on CE
features_result = requests.get(
    f"{AGENT_URL}/api/features",
    verify=False,
    timeout=15,
)
if features_result.status_code == 200:
    features = features_result.json()
    all_false = all(v is False for v in features.values())
    # assert all_false
```

---

### `mop_validation/tests/test_173_02_licence_states.py` (test/integration, incus-exec + docker-restart)

**Analog:** `mop_validation/scripts/run_ee_scenario.py`

**Incus exec pattern** (`run_ee_scenario.py` lines 165-202, plus `run_ce_scenario.py` lines 42-60):
```python
# From run_ce_scenario.py — core helper
def incus_exec(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a bash command inside the container via incus exec."""
    return subprocess.run(
        ["incus", "exec", CONTAINER, "--", "bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

# From run_ee_scenario.py — agent restart to inject licence key (lines 330-340)
def confirm_ce_gating() -> bool:
    """Remove licence key, restart agent only, confirm /api/executions returns 402."""
    print("CE-gating confirmation: removing licence key and restarting agent...")
    incus_exec("sed -i '/^AXIOM_LICENCE_KEY=/d' /workspace/.env", timeout=10)
    result = incus_exec(
        "cd /workspace && docker compose --env-file .env "
        "-f compose.cold-start.yaml restart agent",
        timeout=60,
    )
    time.sleep(15)  # agent startup
    fresh_token = get_admin_token()
    # Check /api/executions — expect 402
    result = incus_exec(
        f"curl -k -s -o /dev/null -w '%{{http_code}}' "
        f"-H 'Authorization: Bearer {fresh_token}' "
        f"https://172.17.0.1:8001/api/executions",
        timeout=15,
    )
    status = result.stdout.strip()
    return status == "402"
```

**Admin token retrieval** (`run_ee_scenario.py` lines 210-237):
```python
def get_admin_token(retries: int = 8, retry_delay: int = 5) -> str:
    """Get admin JWT from the running EE stack with retry."""
    admin_pw_result = incus_exec(
        "grep '^ADMIN_PASSWORD=' /workspace/.env | cut -d= -f2-", timeout=10
    )
    admin_pw = admin_pw_result.stdout.strip()
    
    for attempt in range(1, retries + 1):
        result = incus_exec(
            f"curl -k -s -X POST https://172.17.0.1:8001/auth/login "
            f"-d 'username=admin&password={admin_pw}' "
            f"| python3 -c \"import json,sys; d=json.load(sys.stdin); "
            f"print(d.get('access_token',''))\"",
            timeout=30,
        )
        token = result.stdout.strip()
        if token:
            return token
        time.sleep(retry_delay)
    raise RuntimeError("Failed to obtain admin token after retries")
```

**API licence state check** (`run_ee_scenario.py` lines 270-296):
```python
def verify_ee_active(admin_token: str) -> bool:
    """Confirm EE is active: /api/features all-true, /api/licence edition=enterprise."""
    print("Verifying EE activation...")
    
    features_result = incus_exec(
        "curl -k -s https://172.17.0.1:8001/api/features "
        "| python3 -c \"import json,sys; d=json.load(sys.stdin); "
        "ok=all(d.values()); print('ALL_TRUE' if ok else 'PARTIAL'); print(d)\"",
        timeout=15,
    )
    if "ALL_TRUE" not in features_result.stdout:
        return False
    
    licence_result = incus_exec(
        f"curl -k -s -H 'Authorization: Bearer {admin_token}' "
        f"https://172.17.0.1:8001/api/licence "
        f"| python3 -c \"import json,sys; d=json.load(sys.stdin); "
        f"print('ENTERPRISE' if d.get('edition')=='enterprise' else 'CE'); print(d)\"",
        timeout=15,
    )
    return "ENTERPRISE" in licence_result.stdout
```

**Playwright UI test pattern** (from CLAUDE.md):
```python
# Reference: mop_validation/scripts/test_playwright.py and CLAUDE.md PLAYWRIGHT section
# Python Playwright (not MCP browser)
from playwright.async_api import async_playwright

async def test_grace_banner_visible():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'], headless=True)
        page = await browser.new_page()
        
        # Get token from API
        token = get_admin_token()  # from fixture
        
        # Inject token via localStorage before navigation
        await page.evaluate(
            f"localStorage.setItem('mop_auth_token', '{token}')"
        )
        
        # Navigate to dashboard
        await page.goto("https://172.17.0.1:8443/")
        
        # Check for grace banner DOM element
        grace_banner = await page.query_selector("[data-testid='grace-banner']")
        assert grace_banner is not None
        
        await browser.close()
```

**Licence key generation** (`generate_ee_licence.py` lines 68-76):
```python
def make_licence_key(private_key, payload_dict: dict) -> str:
    """Sign payload_dict with private_key and return a licence key string."""
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode()
    sig_bytes = private_key.sign(payload_bytes)
    # base64url encode with padding stripped
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig_bytes)}"

# For grace-period fixture (test_173_02_licence_states.py conftest):
GRACE_PERIOD_PAYLOAD = {
    "customer_id": "axiom-dev-test",
    "exp": int(time.time()) + 5 * 86400,  # 5 days grace
    "features": EE_FEATURES,
}

TAMPERED_PAYLOAD = {
    # Same as valid, but will be signed with wrong key in test
    "customer_id": "axiom-dev-test",
    "exp": int(time.time()) + 10 * 365 * 86400,
    "features": EE_FEATURES,
}
```

---

### `mop_validation/tests/test_173_03_wheel_security.py` (test/unit, direct import)

**Analog:** `axiom-licenses/tests/test_issue_licence.py` + axiom-ee module structure

**Direct import pattern** (cryptography + Ed25519):
```python
# From axiom-licenses/tests/conftest.py lines 22-41
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate or load keypair
private_key = ed25519.Ed25519PrivateKey.generate()
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
public_key = private_key.public_key()
```

**Wheel manifest verification pattern** (VAL-10):
```python
# Test will import axiom.ee directly and call internal verification function
# Similar pattern from axiom-licenses/tests/test_issue_licence.py
import hashlib
import base64

def test_wheel_manifest_verification():
    """VAL-10: _verify_wheel_manifest() with tampered SHA256."""
    # Setup: create a real wheel file
    wheel_path = Path("/tmp/test_wheel.whl")
    wheel_path.write_bytes(b"wheel content" * 1000)
    
    # Compute real SHA256
    sha256_hash = hashlib.sha256()
    with open(wheel_path, 'rb') as f:
        while chunk := f.read(65536):
            sha256_hash.update(chunk)
    sha256_hex = sha256_hash.hexdigest()
    
    # Sign with real key
    private_key = load_pem_private_key(test_private_pem, password=None)
    sig = private_key.sign(sha256_hex.encode())
    sig_b64 = base64.b64encode(sig).decode()
    
    # Create manifest with TAMPERED SHA256 (bad hash)
    bad_manifest = {
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "signature": sig_b64
    }
    
    # Import and call the verification function
    from axiom.ee.loader import _verify_wheel_manifest
    
    with pytest.raises(RuntimeError):
        _verify_wheel_manifest(str(wheel_path), bad_manifest)
```

**Entry-point whitelist check** (VAL-11):
```python
# From project context, axiom-ee entry points are validated at load time
# Pattern: call the loader with a non-whitelisted entry point value

def test_entry_point_whitelist():
    """VAL-11: entry-point whitelist checker rejects non-whitelisted values."""
    from axiom.ee.loader import _validate_entry_point
    
    # Allowed: "ee.plugin", "ee.foundry.router", etc.
    # Not allowed: arbitrary strings
    
    with pytest.raises(RuntimeError):
        _validate_entry_point("ee.malicious_module")
```

**Boot log HMAC clock rollback** (VAL-13):
```python
from unittest.mock import patch
import time

def test_boot_log_hmac_clock_rollback():
    """VAL-13: clock rollback on boot log HMAC raises RuntimeError on EE, warning on CE."""
    # Patch time.time to simulate clock rollback
    
    with patch('time.time') as mock_time:
        # First call returns "future" time
        mock_time.side_effect = [
            int(time.time()) + 3600,  # future
            int(time.time()) - 3600,  # past (rollback)
        ]
        
        from axiom.ee.services.boot_log_service import verify_hmac_chain
        
        # EE should raise RuntimeError
        with pytest.raises(RuntimeError, match="clock.*rollback"):
            verify_hmac_chain()
```

---

### `mop_validation/tests/test_173_04_node_limit.py` (test/integration, incus-exec + API)

**Analog:** `mop_validation/scripts/run_ee_scenario.py`

**Node limit enforcement test** (VAL-12):
```python
# Uses the same incus_exec, get_admin_token, and API request patterns
# as test_173_02_licence_states.py

def test_node_limit_enrollment_blocked():
    """VAL-12: enrollment returns 402 when node count >= node_limit."""
    # Setup: EE stack running with node_limit set (via config or env)
    # Scenario:
    #   1. Enroll nodes up to the limit
    #   2. Attempt to enroll one more
    #   3. Assert HTTP 402 returned
    
    # Example using incus_exec:
    admin_token = get_admin_token()  # from fixture
    
    # Get current node count
    nodes_result = incus_exec(
        f"curl -k -s -H 'Authorization: Bearer {admin_token}' "
        f"https://172.17.0.1:8001/api/nodes "
        f"| python3 -c \"import json,sys; "
        f"d=json.load(sys.stdin); print(len(d.get('items', d)))\"",
        timeout=15,
    )
    current_count = int(nodes_result.stdout.strip())
    
    # Attempt to enroll a new node when at limit
    enroll_result = incus_exec(
        "curl -k -s -o /dev/null -w '%{http_code}' "
        "-X POST https://172.17.0.1:8001/api/enroll "
        "-d 'join_token=FAKE_TOKEN'",
        timeout=15,
    )
    status = enroll_result.stdout.strip()
    assert status == "402"  # Payment required
```

---

### `mop_validation/tests/test_173_04_coverage_assertion.py` (test/assertion, parametrized)

**Analog:** `puppets/environment_service/tests/test_node.py` (pytest parametrize pattern)

**Coverage parametrization** (VAL-14):
```python
import pytest

# From test_node.py: pytest.mark.parametrize for multiple test cases
@pytest.mark.parametrize("test_case", [
    ("VAL-01", "CE-only install creates exactly 15 tables"),
    ("VAL-02", "CE-only install feature flags all false"),
    ("VAL-03", "All EE stub routes return 402 on CE"),
    ("VAL-04", "EE install: 41 tables (15 CE + 26 EE)"),
    ("VAL-05", "EE install: all EE features true, licence status VALID"),
    ("VAL-06", "EE grace-period: features active, GRACE status, banner visible"),
    ("VAL-07", "EE post-grace expired: DEGRADED_CE mode, pull_work empty"),
    ("VAL-08", "EE no AXIOM_LICENCE_KEY: CE mode at startup"),
    ("VAL-09", "EE invalid/tampered licence: CE mode, log entry"),
    ("VAL-10", "Wheel manifest tampered: _verify_wheel_manifest raises RuntimeError"),
    ("VAL-11", "Entry-point non-whitelisted: loader raises RuntimeError"),
    ("VAL-12", "Node limit enforcement: 402 on enrollment when at limit"),
    ("VAL-13", "Boot log HMAC clock rollback: RuntimeError on EE, warning on CE"),
])
def test_coverage_val_requirement(test_case):
    """VAL-14: All VAL-01 through VAL-13 covered by automated tests."""
    val_id, description = test_case
    
    # Assert that a test function exists for this requirement
    # Collect all test names from the session
    test_exists = f"test_173_{val_id_to_module(val_id)}" in collected_tests
    assert test_exists, f"{val_id} not covered by automated test"

@pytest.fixture
def collected_tests(session):
    """Collect all test names in the session (run-time fixture)."""
    # Gather test node names from pytest session
    return [item.name for item in session.items]
```

---

## Shared Patterns

### LXC Container Management
**Source:** `mop_validation/scripts/run_ce_scenario.py` + `run_ee_scenario.py`
**Apply to:** All LXC-based test files (test_173_01, test_173_02, test_173_04)

```python
# Core incus_exec helper (run_ce_scenario.py lines 42-60)
def incus_exec(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a bash command inside the named LXC container."""
    return subprocess.run(
        ["incus", "exec", CONTAINER, "--", "bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

# Stack readiness polling (run_ce_scenario.py lines 104-134)
def wait_for_stack(timeout: int = 600) -> bool:
    """Poll the dashboard until HTTP 200 or 301."""
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        result = incus_exec(
            "curl -k -s -o /dev/null -w '%{http_code}' https://172.17.0.1:8443",
            timeout=15,
        )
        status = result.stdout.strip()
        if status in ("200", "301"):
            return True
        time.sleep(5)
    return False
```

### API Authentication & Requests
**Source:** `mop_validation/scripts/verify_ce_stubs.py` + `run_ee_scenario.py`
**Apply to:** All API-testing files

```python
# Admin token retrieval with retry (run_ee_scenario.py lines 210-237)
def get_admin_token(retries: int = 8, retry_delay: int = 5) -> str:
    """Get admin JWT from running stack."""
    # Read ADMIN_PASSWORD from env
    # POST /auth/login with form-encoded data (not JSON!)
    # Return access_token from response
    
# Stack readiness check (verify_ce_stubs.py lines 69-83)
def wait_for_stack(base_url: str, timeout: int = 90) -> bool:
    """Poll /api/features until 200."""
    # Use requests library, not curl
    # Disable SSL warnings: urllib3.disable_warnings()
    # Retry every 3s
    
# API assertions (verify_ce_stubs.py lines 137-172)
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get(
    f"{BASE_URL}{path}",
    headers=headers,
    verify=False,  # self-signed certs
    timeout=10,
)
assert resp.status_code == expected_code
```

### Postgres Table Inspection
**Source:** `mop_validation/scripts/verify_ce_tables.py`
**Apply to:** VAL-01 and VAL-04 tests

```python
# Discover postgres container dynamically
def get_postgres_container() -> str:
    """Discover the postgres container name; fall back to 'puppeteer-db-1'."""
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=puppeteer-db", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    name = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
    return name if name else "puppeteer-db-1"

# Run psql via docker exec
query = (
    "SELECT count(*) FROM pg_tables "
    "WHERE schemaname='public' AND tablename != 'apscheduler_jobs';"
)
result = subprocess.run(
    [
        "docker", "exec", pg_container,
        "psql", "-U", "puppet", "-d", "puppet_db",
        "-t", "-c", query,
    ],
    capture_output=True,
    text=True,
    timeout=15,
)
count = int(result.stdout.strip())
```

### Playwright Browser Testing
**Source:** CLAUDE.md + implied from mop_validation/scripts/test_playwright.py
**Apply to:** VAL-06 (grace banner UI test)

```python
# Python Playwright (not MCP browser — it's broken in this environment)
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(args=['--no-sandbox'], headless=True)
    page = await browser.new_page()
    
    # Inject JWT via localStorage (form-encoded login doesn't work with React controlled inputs)
    await page.evaluate(
        f"localStorage.setItem('mop_auth_token', '{token}')"
    )
    
    # Navigate to dashboard
    await page.goto("https://172.17.0.1:8443/")
    
    # Check for DOM element (grace banner)
    element = await page.query_selector("[data-testid='grace-banner']")
    assert element is not None
    
    await browser.close()
```

### Pytest Fixtures & Scope
**Source:** `axiom-licenses/tests/conftest.py` + `puppets/environment_service/tests/test_node.py`
**Apply to:** All test files

```python
# Session-scoped setup for licence generation
@pytest.fixture(scope="session")
def ee_licence_fixtures():
    """Generate grace-period and tampered licence keys at session start."""
    # Load/generate ee_valid_licence.env, ee_expired_licence.env
    # Call generate_ee_licence.py to create grace-period key
    # Return dict of licence keys for parametrized tests

# Module-scoped LXC setup
@pytest.fixture(scope="module")
def ce_lxc_stack(ee_licence_fixtures):
    """Bring up CE LXC stack once per test module."""
    run_ce_scenario.reset_stack()
    ready = run_ce_scenario.wait_for_stack(timeout=600)
    assert ready, "CE stack did not become ready"
    yield  # Tests run
    # Cleanup: no explicit teardown; next module will reset_stack()

@pytest.fixture(scope="module")
def ee_lxc_stack(ee_licence_fixtures):
    """Bring up EE LXC stack once per test module."""
    run_ee_scenario.reset_stack_ee()
    ready = run_ee_scenario.wait_for_stack(timeout=300)
    assert ready, "EE stack did not become ready"
    yield  # Tests run
```

---

## Error Handling Patterns

**Source:** `verify_ce_tables.py`, `verify_ce_stubs.py`, `run_ee_scenario.py`

### Subprocess/Docker Errors
```python
result = subprocess.run(
    ["docker", "exec", container, "psql", ...],
    capture_output=True,
    text=True,
    timeout=15,
)
if result.returncode != 0:
    stderr = result.stderr.strip()
    print(f"[FAIL] psql command failed (exit {result.returncode}): {stderr}")
    # OR raise RuntimeError(f"...")
```

### Network/API Errors
```python
try:
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers=headers,
        verify=False,
        timeout=10,
    )
except Exception as exc:
    print(f"[FAIL] {method} {path} -> ERROR: {exc}")
    # OR raise and let pytest catch it
```

### Timeout Errors
```python
deadline = time.time() + timeout
while time.time() < deadline:
    try:
        resp = requests.get(f"{base_url}/api/features", verify=False, timeout=5)
        if resp.status_code == 200:
            return True
    except Exception:
        pass
    print(".", end="", flush=True)
    time.sleep(3)
print()
return False  # Timeout, not an exception
```

---

## No Analog Found

None — all required patterns exist in the codebase.

## Metadata

**Analog search scope:** 
- `mop_validation/scripts/` (run_ce_scenario.py, run_ee_scenario.py, verify_*.py, generate_ee_licence.py)
- `master_of_puppets/axiom-licenses/tests/` (conftest.py, test patterns)
- `master_of_puppets/puppets/environment_service/tests/` (pytest parametrize patterns)
- CLAUDE.md (Playwright constraints)

**Files scanned:** 15 source scripts + 3 test files

**Pattern extraction date:** 2026-04-20

---

## Key Implementation Notes

1. **LXC container names**: Use `axiom-ce-tests` (CE scenarios) and `axiom-ee-tests` (EE scenarios) as per D-02.
2. **Module scoping**: Each test file should have a module-scoped fixture that brings up the LXC stack once and tears it down after all tests in that module complete.
3. **Licence state changes** (VAL-06 through VAL-09): Do NOT rebuild the full stack. Instead, restart only the agent container inside the running LXC using `incus exec ... docker compose restart agent` after modifying the AXIOM_LICENCE_KEY env var.
4. **Security tests** (VAL-10, VAL-11, VAL-13): Import axiom.ee directly via `pip install -e ~/Development/axiom-ee` (or sys.path.insert). Call internal functions with adversarial inputs.
5. **Playwright**: Always use `args=['--no-sandbox']`, inject JWT to localStorage key `mop_auth_token`, and use form-encoded data for API login (not JSON).
6. **Zero skips requirement**: Every VAL-01 through VAL-13 must have a corresponding test function. No `pytest.mark.skip` allowed. VAL-14 is a parametrized assertion that scans for these tests.

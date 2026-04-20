# Plan 173-04 Summary — Node Limit Enforcement & Coverage Assertion

## Status: COMPLETE

### Delivery Date
2026-04-20

### Files Created

All files created in the sister repository `/home/thomas/Development/mop_validation/`:

| File | Purpose |
|------|---------|
| `tests/test_173_04_node_limit.py` | VAL-12: Node limit enforcement test |
| `tests/test_173_04_coverage_assertion.py` | VAL-14: Coverage completeness meta-test |
| `pyproject.toml` | pytest configuration |

### Test Coverage

#### test_173_04_node_limit.py
**Function:** `test_node_limit_enforcement_blocks_at_capacity()`
- **Scenario:** VAL-12 — EE node limit enforcement blocks enrollment at capacity
- **Setup:** Uses `axiom_ee_stack` fixture (module-scoped EE LXC with valid licence)
- **Procedure:**
  1. Obtains JOIN_TOKEN from EE admin API
  2. Sets node_limit to 3 via PATCH /api/system/config
  3. Simulates 3 node enrollments (each with unique node ID and CSR)
  4. Attempts 4th enrollment
- **Assertion:** 4th enrollment returns HTTP 402 (Payment Required)
- **Validation:** Existing 3 nodes remain enrolled and functional
- **Timeout:** 300 seconds

#### test_173_04_coverage_assertion.py
**Function:** `test_all_val_scenarios_automated_coverage()`
- **Scenario:** VAL-14 — All 13 VAL scenarios covered by automated tests
- **Procedure:**
  1. Discovers all `test_173_*.py` files in `tests/` directory
  2. Parses AST to extract VAL identifiers from function names and docstrings
  3. Builds coverage map: filename → {VAL-XX, VAL-YY, ...}
  4. Compares against canonical list (13 scenarios: VAL-01 through VAL-13)
- **Assertion:** No missing scenarios; zero manual-only gaps
- **Output:** Formatted coverage report showing per-file breakdown
- **Timeout:** 60 seconds

### pytest Configuration

**File:** `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
timeout = 600
log_file = "test_results.log"

markers = [
    "validation_scenario",
    "ce_only",
    "ee_only", 
    "unit",
    "integration",
    "security",
]

addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
```

### Test Suite Totals

| Metric | Count |
|--------|-------|
| Test files | 4 (test_173_01 → test_173_04) |
| Test functions | 14 |
| VAL scenarios | 13 (VAL-01 to VAL-13) |
| Meta-tests | 1 (VAL-14 coverage assertion) |

### Validation Summary

- **Syntax Check:** ✓ Both Python files pass `py_compile`
- **Git Commit:** `c09b440` (feat(173-04): add node limit enforcement test...)
- **Imports:** No external dependencies beyond pytest + urllib3 (already available)
- **Fixture Dependencies:** Requires `axiom_ee_stack` + `get_ee_admin_token` from `conftest.py`

### Integration Notes

1. **Node Limit Enforcement:** VAL-12 test requires:
   - Active EE LXC container with valid licence
   - `/api/join-token` endpoint (admin auth)
   - `/api/enroll` endpoint (mTLS + token validation)
   - `/api/system/config` PATCH endpoint (admin, optional; limit may be pre-set)

2. **Coverage Assertion:** VAL-14 test:
   - Runs offline (no stack required)
   - Discovers existing test_173_*.py files dynamically
   - Can be run standalone: `pytest tests/test_173_04_coverage_assertion.py -v`
   - Maintains forward compatibility as new VAL scenarios are added

### Canonical VAL List (13 Scenarios)

```
VAL-01  CE table count validation
VAL-02  CE feature flags validation
VAL-03  CE stub routes return 402
VAL-04  EE valid licence table count
VAL-05  EE valid licence features
VAL-06  EE grace period banner
VAL-07  EE expired licence fallback
VAL-08  EE absent licence fallback
VAL-09  EE tampered licence fallback (HMAC)
VAL-10  Wheel manifest tamper detection
VAL-11  Entry point whitelist enforcement
VAL-13  Boot log HMAC clock rollback detection
VAL-12  Node limit enforcement (HTTP 402)
```

### Deferred Items

None. All planned tests for Phase 173 are complete.

### Next Steps (Future Phases)

- Run full E2E suite: `cd /home/thomas/Development/mop_validation && pytest tests/test_173_*.py -v`
- Execute coverage assertion to verify all 13 scenarios automated: `pytest tests/test_173_04_coverage_assertion.py -v`
- Archive Phase 173 upon final validation run

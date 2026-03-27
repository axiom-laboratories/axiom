# Phase 76: v14.3 Tech Debt Cleanup - Research

**Researched:** 2026-03-27
**Domain:** Python pytest / YAML compose / filesystem hygiene
**Confidence:** HIGH

## Summary

Phase 76 is a focused three-item tech debt cleanup identified by the v14.3 milestone audit. Every item is precisely located in the codebase — this is not exploratory work. There are no new library dependencies, no architectural decisions, and no ambiguity about what the correct state should be.

The three items share a root cause: phases 73–75 changed the `/api/licence` response shape, renamed an `app.state` key, and deleted a dead source file — but none of those changes swept back to update `test_licence.py` or clean up derived artifacts (stale bytecode, dead env var in a non-primary compose file).

The highest-value item is the HIGH-priority stale test fix: two async endpoint tests in `test_licence.py` will fail in CI because they assert against the old `{edition, features, expires}` response shape and reference `app.state.licence` (renamed to `app.state.licence_state` in Phase 75). The current backend returns `{status, tier, days_until_expiry, node_limit, customer_id, grace_days}`.

**Primary recommendation:** Fix the two stale endpoint tests to match the current response shape, remove the one `API_KEY` line from `compose.cold-start.yaml`, and delete the orphaned `.pyc` file. All three changes belong in a single commit.

## Standard Stack

### Core (already in project — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | project requirement | Test runner | Already in `requirements.txt` |
| httpx + anyio | project requirement | Async test client | Used by all existing ASGI tests |
| pytest-asyncio | project requirement | `@pytest.mark.asyncio` support | Already in use in test_licence.py |

### No new dependencies required

This phase touches only:
1. A test file (Python, no new imports beyond what is already imported)
2. A YAML compose file (text edit — remove one line)
3. A `.pyc` bytecode file (deletion)

**Installation:** Nothing to install.

## Architecture Patterns

### Pattern 1: Existing ASGI Endpoint Test Pattern

The project tests FastAPI endpoints using `httpx.AsyncClient` with `ASGITransport`. The existing tests in `test_licence.py` already use this correctly. Only the assertions and the `app.state` setup/teardown need updating.

**Current (broken) endpoint test pattern:**
```python
# Broken — references old state key name and old response shape
if hasattr(app.state, "licence"):
    del app.state.licence
...
assert data == {"edition": "community"}
```

**Correct endpoint test pattern (verified from main.py lines 773–794):**
```python
# CE response shape — what the backend actually returns
{
    "status": "ce",
    "days_until_expiry": 0,
    "node_limit": 0,
    "tier": "ce",
    "customer_id": None,
    "grace_days": 0,
}

# EE/valid response shape — set app.state.licence_state, not app.state.licence
# The endpoint reads: getattr(request.app.state, "licence_state", None)
```

**Source:** `puppeteer/agent_service/main.py` lines 773–794 (verified directly).

### Pattern 2: app.state.licence_state Setup in Tests

Phase 75 renamed the state key. Tests that set or delete `app.state.licence` must use `app.state.licence_state` instead, and must assign a `LicenceState` dataclass instance (not a raw dict), since the endpoint accesses `.status.value`, `.days_until_expiry`, `.node_limit`, `.tier`, `.customer_id`, and `.grace_days` as attributes.

```python
# Source: agent_service/services/licence_service.py — LicenceState dataclass
@dataclass
class LicenceState:
    status: LicenceStatus   # str Enum: "valid", "grace", "expired", "ce"
    tier: str               # "ce" or "enterprise"
    customer_id: Optional[str]
    node_limit: int
    grace_days: int
    days_until_expiry: int
    features: List[str]
    is_ee_active: bool
```

The test can either import `LicenceState` / `LicenceStatus` from `agent_service.services.licence_service` and construct a real instance, or use `MagicMock` with the correct attribute names set. Both approaches work — importing the real class is cleaner and more maintainable.

### Anti-Patterns to Avoid

- **Deleting the tests rather than fixing them:** `test_licence_service.py::test_licence_status_endpoint` covers the licence service unit level, but the endpoint tests in `test_licence.py` test the actual HTTP response shape via ASGI transport. The endpoint tests add value; fix them rather than delete them.
- **Using a raw dict for `app.state.licence_state`:** The endpoint uses attribute access (`ls.status.value`, `ls.days_until_expiry`, etc.), not dict access. A raw dict would raise `AttributeError`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async test HTTP calls | Custom async client | `httpx.AsyncClient(transport=ASGITransport(app))` | Already established project pattern |
| LicenceState construction | Manual dict | Import `LicenceState` / `LicenceStatus` from `licence_service` | Keeps tests coupled to the real interface |

## Common Pitfalls

### Pitfall 1: Wrong State Key Name

**What goes wrong:** Test sets `app.state.licence = ...` but endpoint reads `app.state.licence_state`. Test passes setup but the endpoint falls into the CE branch.
**Why it happens:** Phase 75 renamed the key; Phase 73 tests were not updated.
**How to avoid:** Use `app.state.licence_state` consistently. Verify with `grep "licence_state" main.py`.
**Warning signs:** Test asserts EE response shape but gets CE shape (`{"status": "ce", ...}`).

### Pitfall 2: Using a Dict Instead of LicenceState Dataclass

**What goes wrong:** `app.state.licence_state = {"status": "valid", ...}` causes `AttributeError: 'dict' object has no attribute 'status'` inside the endpoint handler.
**Why it happens:** Endpoint accesses `ls.status.value` — attribute access, not `ls["status"]`.
**How to avoid:** Construct a `LicenceState` dataclass instance for state injection.

### Pitfall 3: Asserting `customer_id: None` as JSON null

**What goes wrong:** `assert data["customer_id"] == None` — JSON null deserialises to Python `None`; this is correct and will pass. Not a pitfall, but worth noting: `None` in the Python dict becomes `null` in JSON and back to `None` in `resp.json()`.

### Pitfall 4: .pyc Deletion via Git

**What goes wrong:** `git rm` on a `.pyc` file that was never tracked fails. The vault `.pyc` file may not be git-tracked (`.gitignore` typically covers `__pycache__/`).
**How to avoid:** Use `rm -f` (filesystem delete), not `git rm`. Verify with `git status` — it should show no change to tracked files.
**Warning signs:** `git rm: pathspec did not match any files`.

### Pitfall 5: compose.cold-start.yaml — Removing the Wrong Line

**What goes wrong:** Removing `AXIOM_LICENCE_KEY` (which is valid and used) instead of `API_KEY`.
**How to avoid:** The target line is exactly `- API_KEY=${API_KEY:-master-secret-key}` at line 70. `AXIOM_LICENCE_KEY` on line 77 must remain.

## Code Examples

### Correct CE Test Assertion (after fix)

```python
# Source: main.py lines 778–786 — actual CE response
async def test_licence_endpoint_community():
    # ... setup auth override, delete app.state.licence_state if set ...
    resp = await client.get("/api/licence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ce"
    assert data["tier"] == "ce"
    assert data["days_until_expiry"] == 0
    assert data["node_limit"] == 0
    assert data["customer_id"] is None
    assert data["grace_days"] == 0
```

### Correct EE Test Assertion (after fix)

```python
# Source: main.py lines 787–794 — actual EE response
from agent_service.services.licence_service import LicenceState, LicenceStatus

async def test_licence_endpoint_enterprise():
    # ... setup auth override ...
    app.state.licence_state = LicenceState(
        status=LicenceStatus.VALID,
        tier="enterprise",
        customer_id="test-co",
        node_limit=10,
        grace_days=30,
        days_until_expiry=365,
        features=["foundry", "audit"],
        is_ee_active=True,
    )
    resp = await client.get("/api/licence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "valid"
    assert data["tier"] == "enterprise"
    assert data["customer_id"] == "test-co"
    assert data["node_limit"] == 10
    assert data["grace_days"] == 30
    assert data["days_until_expiry"] == 365
```

### compose.cold-start.yaml — Target Removal

```yaml
# Remove this line from the agent service environment block (line 70):
- API_KEY=${API_KEY:-master-secret-key}   # DELETE THIS

# Keep this line — it is still valid and consumed by the EE licence system:
- AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}  # KEEP
```

### .pyc Deletion

```bash
rm /home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/__pycache__/vault_service.cpython-312.pyc
```

Note: This file is not git-tracked (standard `.gitignore` excludes `__pycache__/`). No `git rm` needed.

## State of the Art

| Old State | Current State | Changed In | Impact |
|-----------|---------------|------------|--------|
| `app.state.licence` (raw dict) | `app.state.licence_state` (LicenceState dataclass) | Phase 75 | Tests using old key silently fall into CE branch |
| Response shape: `{edition, features, expires}` | Response shape: `{status, tier, days_until_expiry, node_limit, customer_id, grace_days}` | Phase 74 | Old assertions fail with KeyError or wrong value |
| `API_KEY` env var consumed by `verify_api_key` | `API_KEY` removed from app entirely | Phase 72 | Env var in compose is dead code with misleading default |
| `vault_service.py` on disk | Deleted from disk and git | Phase 75 | `.pyc` orphan remains on disk |

## Open Questions

None. All three items are unambiguous:
1. The correct response shape is confirmed from `main.py` lines 773–794.
2. The correct `app.state` key name is `licence_state`, confirmed from `main.py` line 776.
3. The API_KEY line to remove is line 70 of `compose.cold-start.yaml`, confirmed by direct file inspection.
4. The `.pyc` path is confirmed to exist: `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/services/__pycache__/vault_service.cpython-312.pyc`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `puppeteer/pytest.ini` or `puppeteer/pyproject.toml` |
| Quick run command | `cd puppeteer && pytest agent_service/tests/test_licence.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements to Test Map

Phase 76 has no new requirements (tech debt only). The single verification criterion is:

| Item | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|--------------|
| Tech Debt 1 | `test_licence_endpoint_community` passes | unit/ASGI | `cd puppeteer && pytest agent_service/tests/test_licence.py::test_licence_endpoint_community -x` | Yes (needs fix) |
| Tech Debt 1 | `test_licence_endpoint_enterprise` passes | unit/ASGI | `cd puppeteer && pytest agent_service/tests/test_licence.py::test_licence_endpoint_enterprise -x` | Yes (needs fix) |
| Tech Debt 2 | `compose.cold-start.yaml` has no `API_KEY` line | manual check | `grep API_KEY puppeteer/compose.cold-start.yaml` (expect no output) | Yes (file exists, line present) |
| Tech Debt 3 | vault `.pyc` absent | shell check | `test ! -f puppeteer/agent_service/services/__pycache__/vault_service.cpython-312.pyc && echo PASS` | Yes (file exists, needs deletion) |

### Sampling Rate

- **Per task commit:** `cd puppeteer && pytest agent_service/tests/test_licence.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all verification needs for this phase. The test file already exists; it just needs its assertions corrected.

## Sources

### Primary (HIGH confidence)

- Direct file read: `puppeteer/agent_service/main.py` lines 773–794 — confirmed current `/api/licence` response shape
- Direct file read: `puppeteer/agent_service/services/licence_service.py` lines 51–68 — confirmed `LicenceState` dataclass fields
- Direct file read: `puppeteer/agent_service/tests/test_licence.py` lines 140–209 — confirmed what is broken and why
- Direct file read: `puppeteer/compose.cold-start.yaml` line 70 — confirmed `API_KEY` line still present
- Direct shell check: `ls -la puppeteer/agent_service/services/__pycache__/` — confirmed `.pyc` exists at 5.4 KB
- Direct file read: `.planning/v14.3-MILESTONE-AUDIT.md` — confirms all three items, their severity, and prescribed fixes

### Secondary (MEDIUM confidence)

None needed — all findings are from direct file inspection.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- What is broken: HIGH — confirmed by direct file inspection and audit report
- What the correct state should be: HIGH — backend source code is the ground truth
- How to fix: HIGH — all three fixes are single-file, line-level changes

**Research date:** 2026-03-27
**Valid until:** 2026-04-26 (stable — no fast-moving dependencies)

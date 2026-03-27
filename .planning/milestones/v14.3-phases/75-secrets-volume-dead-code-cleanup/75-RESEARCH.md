# Phase 75: Secrets Volume + Dead Code Cleanup - Research

**Researched:** 2026-03-27
**Domain:** Docker Compose volumes, Python service refactoring, git hygiene, clock-rollback enforcement
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **vault_service.py disposal**: Delete entirely — the file is unreachable in production (`Artifact` model absent from `db.py`, no routes in `main.py`, not imported anywhere). If imported it raises `ImportError`. SEC-02 closes by elimination: no vault routes = no vault path traversal risk. Wiring it up is out of scope.
2. **secrets volume**: Use a named Docker volume (`secrets-data:/app/secrets`) on the agent service in both `compose.server.yaml` and `compose.cold-start.yaml`. Add `secrets-data:` to the top-level `volumes:` section of both files. Operators seed `licence.key` into the volume via `docker cp` or a one-time init step (document in compose comments).
3. **Clock-rollback enforcement**: Remove `AXIOM_STRICT_CLOCK` env var entirely. Hardcode the behaviour in `licence_service.py`: when `LicenceStatus` is anything other than CE, clock rollback always hard-rejects startup (raises `RuntimeError`). CE mode logs a warning only. Update `check_and_record_boot()` to accept `licence_status: LicenceStatus` parameter instead of reading the env var.
4. **main.py.bak removal**: `git rm puppeteer/agent_service/main.py.bak` — remove from tracking entirely. Add `*.bak` to `.gitignore` to prevent recurrence.

### Claude's Discretion

- TDD approach: write RED tests first (consistent with Phase 72/73 pattern)
- Exact wording of compose comments for `secrets-data` volume and `licence.key` seeding instructions
- Whether `check_and_record_boot()` signature change requires any test mock updates

### Deferred Ideas (OUT OF SCOPE)

- `compose.cold-start.yaml` `API_KEY` removal — out of scope; track separately
- Full vault/artifact feature (BOM download, file store) — separate future phase if ever needed
- Periodic in-process licence re-validation (APScheduler 6h re-check) — deferred to v15+
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIC-05 | Axiom EE detects clock rollback between container restarts via a hash-chained boot log in `secrets/boot.log` and logs a warning (strict mode: reject startup) | `check_and_record_boot()` exists and works within a container lifetime. Cross-restart persistence requires `secrets-data` volume mount. Strict mode must be hardcoded for EE (not env-var-configurable). |
| SEC-02 | Operator can be confident that `vault_service.py` artifact paths are safe against directory traversal — UUID validation + `Path.resolve() + is_relative_to()` guard applied to store and delete operations | `validate_path_within()` already exists in `security.py` and is already called from `vault_service.py`. Deleting `vault_service.py` closes SEC-02 by elimination since there are no reachable vault routes. |
</phase_requirements>

---

## Summary

Phase 75 is a targeted cleanup phase: four distinct changes that each close a requirement gap or remove dead weight. All four are surgical changes to existing files — no new files beyond tests need to be created.

The largest behaviour change is `check_and_record_boot()`: the signature gains a `licence_status: LicenceStatus` parameter that replaces the `AXIOM_STRICT_CLOCK` env-var read. This triggers a ripple to the call site in `main.py` lifespan and to the existing `test_clock_rollback_detection` test in `puppeteer/tests/test_licence_service.py` — that test currently patches `os.environ["AXIOM_STRICT_CLOCK"]` for strict-mode assertion, which must be rewritten to pass `LicenceStatus.VALID` instead.

The secrets volume change is entirely in compose YAML and requires zero Python changes. The volume persists `/app/secrets/` across `docker compose down && up` cycles, making `secrets/boot.log` (and `secrets/licence.key`) durable. The `vault_service.py` deletion removes SEC-02's attack surface entirely; `validate_path_within()` in `security.py` remains (used by other callers). The `main.py.bak` removal is a single `git rm` plus a `.gitignore` entry.

**Primary recommendation:** Execute in plan order — RED tests first (modify existing LIC-05 test + add new assertions), then behaviour changes, then compose changes, then git cleanup. This ensures the test suite gates every implementation step.

---

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Python `pathlib.Path` | stdlib | Volume path resolution, boot log path | Already used throughout codebase |
| Docker Compose named volumes | v3 spec | Persist `/app/secrets/` across restarts | Same pattern as `pgdata`, `mirror-data`, `registry-data` |
| `git rm` | git | Remove tracked file from index and working tree | Standard git file deletion |
| `unittest.mock.patch` | stdlib | Patch `BOOT_LOG_PATH` and licence status in tests | Established TDD pattern from Phases 72/73 |

### No New Dependencies
All work in this phase uses existing libraries and tools. No `pip install` or `npm install` required.

---

## Architecture Patterns

### Pattern 1: Named Docker Volume for Persistent Service Data

**What:** Add a top-level named volume and mount it into the service container. Docker Engine manages the lifecycle; data survives `docker compose down` (not `docker compose down -v`).

**When to use:** Any service data that must survive container replacement without being tracked in git (secrets, state files, databases).

**Existing pattern in compose.server.yaml:**
```yaml
# Top-level volumes section
volumes:
  pgdata:
  mirror-data:
  registry-data:
  secrets-data:    # <-- add

# Service volume mount
agent:
  volumes:
    - secrets-data:/app/secrets  # <-- add
```

**Note:** `compose.cold-start.yaml` does not currently have a `secrets-data` volume. Both files need the same addition. The cold-start file already uses named volumes (`node1-secrets`, `node2-secrets`) for puppet nodes — same pattern applies to the agent service.

### Pattern 2: Hardcoded Strict Mode via Parameter Instead of Env Var

**What:** Replace `os.getenv("AXIOM_STRICT_CLOCK")` with a `licence_status: LicenceStatus` parameter. The caller (main.py lifespan) already has `licence_status` available — it calls `load_licence()` before `check_and_record_boot()`.

**Current flow (lifespan):**
```python
_rollback_ok = check_and_record_boot()       # reads AXIOM_STRICT_CLOCK internally
licence_state = load_licence()
```

**Required flow (Phase 75):**
```python
licence_state = load_licence()               # load licence first
_rollback_ok = check_and_record_boot(licence_state.status)  # pass status
```

**check_and_record_boot signature change:**
```python
def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
    strict_clock = licence_status != LicenceStatus.CE  # EE always strict
    # ... rest unchanged
```

**Default parameter:** `LicenceStatus.CE` (non-strict) ensures the function is safe to call in tests without a real licence state.

### Pattern 3: Closing a Security Finding by Deletion

**What:** SEC-02 required path traversal guards on `vault_service.py`. Those guards were implemented (Phase 72 added `validate_path_within()` to `security.py` and wired it into `vault_service.py`). However, `vault_service.py` references `from ..db import Artifact` which does not exist in `db.py` — the file raises `ImportError` on import and is unreachable from any route in `main.py`.

**Resolution:** Delete `vault_service.py` entirely. The SEC-02 requirement is satisfied by elimination: no vault endpoints = no vault path traversal risk. `validate_path_within()` remains in `security.py` for use by `test_docs_traversal.py`, `test_vault_traversal.py`, and any future callers.

**Files to delete:**
- `puppeteer/agent_service/services/vault_service.py`

**Tests to delete:**
- The vault traversal tests in `puppeteer/agent_service/tests/test_vault_traversal.py` test `validate_path_within()` from `agent_service.security` — NOT from `vault_service.py`. These tests remain valid and MUST NOT be deleted (they verify `security.py` still has the guard). Only delete vault-service-specific tests if any exist — none were found in the test scan.

**Confirmed dead imports:** `from ..db import Artifact` — `Artifact` is absent from `db.py` (grep confirmed zero matches).

### Anti-Patterns to Avoid

- **Calling `check_and_record_boot()` before `load_licence()`:** The signature change requires licence status. Reorder lifespan so `load_licence()` runs first.
- **Removing `validate_path_within()` from `security.py`:** It is tested independently and used by other callers. Only `vault_service.py` is deleted.
- **Using `docker compose down -v`** in success criteria: Named volumes are deleted with `-v`. The test for volume persistence must use plain `docker compose down && docker compose up -d`.
- **Patching `AXIOM_STRICT_CLOCK` in the updated test:** After the refactor, the env var no longer exists. The strict-mode test must patch via `licence_status` parameter, not env var.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secrets persistence across restarts | Bind mount to host path | Named Docker volume | Named volumes are portable, managed by Docker Engine, follow existing compose pattern |
| Strict clock enforcement | New env var flag | `licence_status` parameter | Decision already locked in CONTEXT.md; avoids operator security theatre |

---

## Common Pitfalls

### Pitfall 1: Lifespan Call-Site Reordering

**What goes wrong:** `check_and_record_boot(licence_state.status)` called before `load_licence()` — `licence_state` is undefined.

**Why it happens:** Current code calls `check_and_record_boot()` first (lines 79-82 in main.py), then `load_licence()` (line 84). After the refactor the order must flip.

**How to avoid:** In the lifespan function, move `load_licence()` to before `check_and_record_boot()`. The boot log check is still a startup action — just now it receives the licence status from the already-loaded licence.

**Warning signs:** `NameError: name 'licence_state' is not defined` at startup.

### Pitfall 2: Existing LIC-05 Test Uses AXIOM_STRICT_CLOCK

**What goes wrong:** `test_clock_rollback_detection` in `puppeteer/tests/test_licence_service.py` (lines 171-176) patches `os.environ["AXIOM_STRICT_CLOCK"] = "true"` to test strict mode. After the refactor this patch does nothing and the test will no longer exercise strict-mode behaviour.

**How to avoid:** Update the test to call `check_and_record_boot(LicenceStatus.VALID)` for the strict-mode assertion (any non-CE status triggers strict). Remove the `patch.dict("os.environ", {"AXIOM_STRICT_CLOCK": "true"})` wrapping.

**Warning signs:** Test passes but isn't testing strict mode at all (the env var patch silently has no effect).

### Pitfall 3: Vault Traversal Tests Import from agent_service.security, Not vault_service

**What goes wrong:** Assuming `test_vault_traversal.py` tests vault_service and should be deleted alongside vault_service.py.

**How to avoid:** The test file (`puppeteer/agent_service/tests/test_vault_traversal.py`) imports `from agent_service.security import validate_path_within` — it tests the guard function in security.py directly. It does NOT import vault_service. These tests must be KEPT. Only `vault_service.py` itself is deleted.

### Pitfall 4: .gitignore Already Has *.key but Not *.bak

**What goes wrong:** Adding `*.bak` to .gitignore may inadvertently match other patterns already covered or conflict with existing rules.

**How to avoid:** Current `.gitignore` has `*.key`, `*.pem`, `*.crt` but not `*.bak`. Safe to add `*.bak` under the "Python" or a new "Dev artifacts" section. No existing entries conflict.

### Pitfall 5: secrets-data Volume and Containerfile.server Copy Steps

**What goes wrong:** If `Containerfile.server` copies files into `/app/secrets/` at build time, a named volume mount would shadow those baked-in files on first start (Docker mounts overlay the container filesystem).

**How to avoid:** Verify `Containerfile.server` does not copy secrets into `/app/secrets/`. The secrets directory is populated at runtime by the application (boot.log is written by `check_and_record_boot()`; `licence.key` is seeded by the operator via `docker cp`). If any Containerfile step does write to `/app/secrets/`, it must be removed or the volume initialisation behaviour documented.

---

## Code Examples

### Updated check_and_record_boot signature
```python
# Source: licence_service.py — Phase 75 change
def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
    """
    Append a new timestamped entry to the hash-chained boot log.

    Returns True if no rollback is detected, False if the last entry has a
    timestamp in the future (indicating clock rollback).

    For EE licences (VALID, GRACE, EXPIRED), raises RuntimeError on rollback.
    For CE mode, logs a warning only.
    """
    strict_clock = licence_status != LicenceStatus.CE
    now_ts = datetime.now(timezone.utc).isoformat()
    # ... rest of implementation unchanged
```

### Updated lifespan call-site in main.py
```python
# Source: main.py lifespan — Phase 75 call-site change
# Load licence first (check_and_record_boot now needs it)
licence_state = load_licence()
app.state.licence_state = licence_state

# Clock rollback detection — strict for EE, warning-only for CE
_rollback_ok = check_and_record_boot(licence_state.status)
if not _rollback_ok:
    logger.warning("Clock rollback detected — check system time")
```

### Updated LIC-05 test (strict mode assertion)
```python
# Source: puppeteer/tests/test_licence_service.py — Phase 75 update
def test_clock_rollback_detection():
    """LIC-05: check_and_record_boot() detects a future timestamp in boot.log as rollback."""
    from puppeteer.agent_service.services.licence_service import (
        check_and_record_boot, LicenceStatus
    )
    # ... write future timestamp to boot_log ...

    with patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
        result = check_and_record_boot(LicenceStatus.CE)  # CE mode — warn only

    assert result is False, "Expected rollback to be detected (return False)"

    # Strict mode: EE licence — rollback should raise RuntimeError
    boot_log.write_text(f"{future_hash} {future_ts}\n")
    with patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
        with pytest.raises(RuntimeError):
            check_and_record_boot(LicenceStatus.VALID)  # EE — strict always
```

### compose.server.yaml — secrets-data addition
```yaml
# Under agent service volumes:
volumes:
  - certs-volume:/app/global_certs:ro
  - /var/run/docker.sock:/var/run/docker.sock
  - ../puppets:/app/puppets:ro
  - mirror-data:/app/mirror_data
  - secrets-data:/app/secrets   # Persists boot.log and licence.key across restarts
                                 # Seed licence: docker cp licence.key <agent-container>:/app/secrets/

# Under top-level volumes:
volumes:
  pgdata:
  certs-volume:
  caddy_data:
  caddy_config:
  registry-data:
  mirror-data:
  devpi-data:
  secrets-data:   # Agent secrets persistence (boot.log, licence.key)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `AXIOM_STRICT_CLOCK=true` env var | Hardcoded strict for EE via `licence_status` param | Phase 75 | Eliminates security theatre; operator cannot bypass clock enforcement on EE |
| `secrets/boot.log` ephemeral (in-container) | Persistent via `secrets-data` named volume | Phase 75 | LIC-05 cross-restart guarantee fulfilled |
| `vault_service.py` dead code (ImportError on import) | Deleted | Phase 75 | SEC-02 closed by elimination; no attack surface |
| `main.py.bak` tracked in git | `git rm` + `*.bak` in `.gitignore` | Phase 75 | Clean repo; no accidental deployment of backup files |

---

## Open Questions

1. **Does Containerfile.server write anything to `/app/secrets/` at build time?**
   - What we know: The code writes `secrets/boot.log` and reads `secrets/licence.key` at runtime. The compose volumes section currently has no `/app/secrets/` mount.
   - What's unclear: Whether `Containerfile.server` has a `COPY` or `RUN mkdir` for `/app/secrets/` that would conflict with the named volume mount.
   - Recommendation: Read `puppeteer/Containerfile.server` before implementing the volume mount. If it does copy secrets content, that content must be seeded into the volume instead.

2. **Should `check_and_record_boot()` default parameter be `LicenceStatus.CE` or require explicit passing?**
   - What we know: CONTEXT.md says signature changes to accept `licence_status: LicenceStatus` parameter. Default is Claude's discretion.
   - Recommendation: Use `LicenceStatus.CE` as default — keeps backward compatibility for any test that calls without arguments, and CE is the safe/non-strict fallback.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from `puppeteer/tests/` and `puppeteer/agent_service/tests/`) |
| Config file | none detected — run from repo root with full import paths |
| Quick run command | `cd /home/thomas/Development/master_of_puppets && python -m pytest puppeteer/tests/test_licence_service.py -x -q` |
| Full suite command | `cd /home/thomas/Development/master_of_puppets && python -m pytest puppeteer/tests/ puppeteer/agent_service/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behaviour | Test Type | Automated Command | File Exists? |
|--------|-----------|-----------|-------------------|-------------|
| LIC-05 (rollback detection) | `check_and_record_boot(CE)` returns False on rollback, logs warning | unit | `python -m pytest puppeteer/tests/test_licence_service.py::test_clock_rollback_detection -x` | ✅ exists — needs update |
| LIC-05 (strict EE mode) | `check_and_record_boot(VALID)` raises RuntimeError on rollback | unit | same test, strict-mode branch | ✅ exists — needs update |
| LIC-05 (volume persistence) | boot.log survives `docker compose down && up` | manual-only | `docker compose down && docker compose up -d && docker exec agent cat /app/secrets/boot.log` | ❌ manual — Docker E2E not automatable in < 30s |
| SEC-02 (vault deleted) | `import vault_service` raises ImportError OR file does not exist | unit | `python -m pytest puppeteer/agent_service/tests/test_vault_traversal.py -x` | ✅ traversal guard still tested |
| SEC-02 (validate_path_within) | `validate_path_within()` still importable and rejects traversal | unit | `python -m pytest puppeteer/agent_service/tests/test_vault_traversal.py -x` | ✅ exists, no changes needed |

### Sampling Rate
- **Per task commit:** `python -m pytest puppeteer/tests/test_licence_service.py -x -q`
- **Per wave merge:** `python -m pytest puppeteer/tests/ puppeteer/agent_service/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Update `puppeteer/tests/test_licence_service.py::test_clock_rollback_detection` — replace `AXIOM_STRICT_CLOCK` env var patch with `LicenceStatus.VALID` parameter call for strict-mode assertion
- [ ] Add RED test: `test_check_and_record_boot_strict_ee` — verifies `check_and_record_boot(LicenceStatus.VALID)` raises RuntimeError when rollback detected (covers hardcoded EE strict mode, not just env var)
- [ ] Add RED test: `test_vault_service_deleted` — asserts `puppeteer/agent_service/services/vault_service.py` does not exist OR that importing it fails (documents SEC-02 closure intent)

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `puppeteer/agent_service/services/licence_service.py` — current `check_and_record_boot()` implementation, `BOOT_LOG_PATH` constant, `AXIOM_STRICT_CLOCK` env var read
- Direct source inspection: `puppeteer/agent_service/services/vault_service.py` — confirms `from ..db import Artifact` (dead import)
- Direct source inspection: `puppeteer/agent_service/db.py` — grep confirmed `Artifact` class absent
- Direct source inspection: `puppeteer/compose.server.yaml` + `compose.cold-start.yaml` — current volume structure
- Direct source inspection: `puppeteer/tests/test_licence_service.py` — existing LIC-05 test and AXIOM_STRICT_CLOCK usage
- Direct source inspection: `puppeteer/agent_service/tests/test_vault_traversal.py` — confirmed tests `security.py`, not `vault_service.py`
- Direct source inspection: `.gitignore` — confirmed `*.bak` absent, `*.key` present

### Secondary (MEDIUM confidence)
- `.planning/phases/75-secrets-volume-dead-code-cleanup/75-CONTEXT.md` — locked decisions from discuss-phase
- `.planning/REQUIREMENTS.md` — LIC-05, SEC-02 requirement definitions
- `.planning/v14.3-MILESTONE-AUDIT.md` — audit evidence for compose volume gap

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all changes are within existing files using established patterns
- Architecture: HIGH — named volumes, function signature changes, git operations are well-understood
- Pitfalls: HIGH — all pitfalls derived from direct code inspection, not speculation

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, no external dependencies)

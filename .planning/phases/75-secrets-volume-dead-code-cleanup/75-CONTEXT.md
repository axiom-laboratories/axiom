# Phase 75: Secrets Volume + Dead Code Cleanup - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Four targeted cleanup tasks that close two open requirements (LIC-05, SEC-02) and remove legacy artifacts:
1. Add `secrets-data` named volume to both compose files so `secrets/boot.log` (and `licence.key`) persist across container restarts
2. Remove `vault_service.py` dead code entirely
3. Harden clock-rollback detection: remove `AXIOM_STRICT_CLOCK` env var, hardcode strict rejection for EE mode
4. Remove `main.py.bak` from git tracking

</domain>

<decisions>
## Implementation Decisions

### vault_service.py disposal
- **Delete entirely** — the file is unreachable in production (`Artifact` model absent from `db.py`, no routes in `main.py`, not imported anywhere). If imported it raises `ImportError`.
- SEC-02 closes by elimination: no vault routes = no vault path traversal risk.
- Wiring it up is out of scope — it would require `Artifact` ORM, upload/download/delete routes, frontend UI, and docs. That's a separate feature phase.
- Also delete any unit tests that exclusively test vault traversal (they test dead code).

### secrets volume
- Use a **named Docker volume** (`secrets-data:/app/secrets`) on the agent service in both `compose.server.yaml` and `compose.cold-start.yaml`.
- Add `secrets-data:` to the top-level `volumes:` section of both files.
- This is consistent with how `pgdata`, `mirror-data`, and `registry-data` are managed.
- Operators seed `licence.key` into the volume via `docker cp` or a one-time init step (document in compose comments).

### Clock-rollback enforcement
- **Remove `AXIOM_STRICT_CLOCK` env var entirely** — operator-controlled strict mode is security theatre for licence enforcement; an operator trying to cheat a licence simply wouldn't set the flag.
- **Hardcode the behaviour in `licence_service.py`**: when `LicenceStatus` is anything other than CE (i.e., valid/grace/expired EE), clock rollback always hard-rejects startup (raises `RuntimeError`). CE mode logs a warning only.
- Do NOT add `AXIOM_STRICT_CLOCK` to compose files — the variable no longer exists.
- Update `check_and_record_boot()` to accept `licence_status: LicenceStatus` parameter instead of reading the env var.

### main.py.bak removal
- `git rm puppeteer/agent_service/main.py.bak` — remove from tracking entirely.
- Add `*.bak` to `.gitignore` to prevent recurrence.

### Claude's Discretion
- TDD approach: write RED tests first (consistent with Phase 72/73 pattern)
- Exact wording of compose comments for `secrets-data` volume and licence.key seeding instructions
- Whether `check_and_record_boot()` signature change requires any test mock updates

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `validate_path_within()` in `security.py` — the SEC-02 guard; remains in place for other callers after vault_service is deleted
- `LicenceStatus` enum in `licence_service.py` — use to gate strict vs warn mode in `check_and_record_boot()`
- `BOOT_LOG_PATH = Path("secrets/boot.log")` — already defined as a module-level constant, patchable in tests

### Established Patterns
- Named volumes in compose: `pgdata`, `mirror-data`, `registry-data` — `secrets-data` follows the same pattern
- TDD RED→GREEN: write failing tests first (Phases 72, 73)
- `compose.cold-start.yaml` mirrors `compose.server.yaml` agent env block — both need updating in sync

### Integration Points
- `licence_service.check_and_record_boot()` — called in `main.py` lifespan; signature change requires lifespan call-site update
- `puppeteer/tests/` — vault traversal tests reference `vault_service`; delete them with the service
- Both `compose.server.yaml` and `compose.cold-start.yaml` need the `secrets-data` volume

</code_context>

<specifics>
## Specific Ideas

- Clock-rollback is a licence enforcement mechanism — the operator/user who might cheat is the same person who controls the env var, so operator-configurable strict mode is meaningless. Always-strict for EE is the only coherent position.
- `compose.cold-start.yaml` still has `API_KEY=${API_KEY:-master-secret-key}` — leftover from before Phase 72 removed it from `compose.server.yaml`. Noted but out of scope for this phase.

</specifics>

<deferred>
## Deferred Ideas

- `compose.cold-start.yaml` `API_KEY` removal — out of scope; track separately
- Full vault/artifact feature (BOM download, file store) — separate future phase if ever needed
- Periodic in-process licence re-validation (APScheduler 6h re-check) — deferred to v15+ per REQUIREMENTS.md

</deferred>

---

*Phase: 75-secrets-volume-dead-code-cleanup*
*Context gathered: 2026-03-27*

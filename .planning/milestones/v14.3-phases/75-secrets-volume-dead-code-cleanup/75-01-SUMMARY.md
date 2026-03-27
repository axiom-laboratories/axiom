---
phase: 75-secrets-volume-dead-code-cleanup
plan: "01"
subsystem: licence-service, security, compose
tags: [tdd, lic-05, sec-02, dead-code, docker-volumes, gitclean]
dependency_graph:
  requires: []
  provides: [LIC-05, SEC-02, secrets-volume]
  affects: [licence_service, main.py lifespan, compose.server.yaml, compose.cold-start.yaml]
tech_stack:
  added: []
  patterns: [TDD-red-green, licence-status-parameter-injection]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/licence_service.py
    - puppeteer/agent_service/main.py
    - puppeteer/tests/test_licence_service.py
    - puppeteer/agent_service/tests/test_vault_traversal.py
    - puppeteer/compose.server.yaml
    - puppeteer/compose.cold-start.yaml
    - .gitignore
  deleted:
    - puppeteer/agent_service/services/vault_service.py
    - puppeteer/agent_service/main.py.bak
decisions:
  - "check_and_record_boot() takes licence_status parameter; CE warns only, EE (VALID/GRACE/EXPIRED) raises RuntimeError on rollback — removes AXIOM_STRICT_CLOCK env var bypass vector"
  - "main.py lifespan reordered: load_licence() first, then check_and_record_boot(licence_state.status) — clock hardening now tied to licence tier at boot"
  - "secrets-data named Docker volume mounts at /app/secrets on agent — boot.log survives compose down/up cycles"
  - "vault_service.py deleted (was dead code with broken import — Artifact not in db.py)"
metrics:
  duration: 3m
  completed: "2026-03-27"
  tasks_completed: 3
  files_changed: 9
---

# Phase 75 Plan 01: Secrets Volume, Dead Code Cleanup Summary

**One-liner:** EE clock rollback hardened via licence_status parameter; vault_service.py dead code deleted; boot.log persisted via secrets-data Docker named volume.

## What Was Built

### LIC-05: clock-rollback enforcement via licence_status parameter

`check_and_record_boot()` signature changed from zero-argument to:
```python
def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
```

The `AXIOM_STRICT_CLOCK` env var (a bypass vector) is removed. EE-licensed instances (VALID, GRACE, EXPIRED) now always raise `RuntimeError` on clock rollback. CE logs a warning only.

### LIC-05 lifespan reorder in main.py

`load_licence()` is now called before `check_and_record_boot()` in the lifespan startup sequence. This allows the licence status to flow into the rollback check at boot time.

### SEC-02: vault_service.py deleted

`puppeteer/agent_service/services/vault_service.py` was dead code — it referenced `Artifact` which was never added to `db.py`, causing an `ImportError` on any attempt to import it. Deleted cleanly.

### secrets-data Docker volume

Added `secrets-data` named volume to both `compose.server.yaml` and `compose.cold-start.yaml`:
- Top-level volume declaration in each file
- Agent service mounts: `secrets-data:/app/secrets`
- Ensures `secrets/boot.log` and `secrets/licence.key` persist across `docker compose down/up` cycles

### Git hygiene

- `puppeteer/agent_service/main.py.bak` removed from git tracking and deleted from disk
- `*.bak` added to `.gitignore` under a new "Dev artifacts" section

## Task Commits

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 (RED) | Update LIC-05 test + SEC-02 sentinel | 6f04352 | test_licence_service.py, test_vault_traversal.py |
| 2 (GREEN) | Implement signature change + delete vault_service | 8ecef90 | licence_service.py, main.py, vault_service.py (deleted) |
| 3 | Compose volumes + git cleanup | 18994f1 | compose.server.yaml, compose.cold-start.yaml, .gitignore, main.py.bak (deleted) |

## Verification

Plan-relevant tests all pass:
- `test_licence_service.py` — 8 tests pass (incl. new test_check_and_record_boot_strict_ee)
- `test_vault_traversal.py` — 5 tests pass (incl. new test_vault_service_deleted)
- Both compose files validate: `docker compose config --quiet` exits cleanly

Pre-existing failures in `puppeteer/tests/` (not caused by this plan):
- `test_intent_scanner.py` — `ModuleNotFoundError: intent_scanner` (pre-existing since commit dfc2da1)
- `test_lifecycle_enforcement.py` — `ImportError: PuppetTemplate` (pre-existing since commit f298384)
- `test_smelter.py` and others — pre-existing import failures
- `test_sec01_audit.py` and `test_sec02_hmac.py` — 4 pre-existing test failures (9 total pre-existing, identical count before and after this plan)

## Deviations from Plan

### Out-of-scope pre-existing issues (logged, not fixed)

Multiple test files in `puppeteer/tests/` fail at collection due to missing modules or stale imports — present before this plan. Logged to deferred items.

No deviations to the plan's own scope — all tasks executed as specified.

## Self-Check: PASSED

- `puppeteer/agent_service/services/vault_service.py` does not exist
- `puppeteer/agent_service/main.py.bak` not tracked by git (`git ls-files` returns empty)
- `secrets-data` in compose.server.yaml: confirmed (3 occurrences in docker compose config output)
- `secrets-data` in compose.cold-start.yaml: confirmed (3 occurrences in docker compose config output)
- `*.bak` in .gitignore: confirmed
- Commits 6f04352, 8ecef90, 18994f1 all exist in git log

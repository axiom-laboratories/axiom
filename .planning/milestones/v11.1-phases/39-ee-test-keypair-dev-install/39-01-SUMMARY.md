---
phase: 39-ee-test-keypair-dev-install
plan: "01"
subsystem: ee-tooling
tags: [ed25519, licence, axiom-ee, keypair, editable-install]
dependency_graph:
  requires: []
  provides: [ee-test-keypair, ee-plugin-patched, axiom-licence-key-passthrough]
  affects: [phase-42-ee-licence-validation, phase-43-ee-feature-flags, phase-44-ee-expired-licence]
tech_stack:
  added: []
  patterns: [ed25519-pkcs8-pem, editable-pip-install, regex-source-patch]
key_files:
  created:
    - /home/thomas/Development/mop_validation/scripts/generate_ee_keypair.py
    - /home/thomas/Development/mop_validation/scripts/patch_ee_source.py
    - /home/thomas/Development/mop_validation/secrets/ee/ee_test_private.pem
    - /home/thomas/Development/mop_validation/secrets/ee/ee_test_public.pem
  modified:
    - /home/thomas/Development/master_of_puppets/puppeteer/compose.server.yaml
decisions:
  - "Used lambda replacement in re.sub to prevent \\xNN byte sequences in repr(pub_raw) being interpreted as regex escape sequences"
  - "patch_ee_source.py skips pip install -e if axiom-ee is already editable-installed — Cython BuildExtAndCopyInits.__init__.py self-copy bug blocks re-install in inplace editable mode"
  - "Used MoP venv python (.venv/bin/python3) for import verification since system python has no axiom-ee on sys.path"
  - "compose.server.yaml target is main puppeteer/ file — the .worktrees/axiom-split/ worktree referenced in the plan does not exist on this machine"
metrics:
  duration: 10 minutes
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 39 Plan 01: EE Test Keypair + Editable Install Summary

**One-liner:** Ed25519 test keypair generated and patched into axiom-ee plugin.py via regex, enabling licence signing without Cython rebuild or production keys.

## What Was Built

Two scripts in `mop_validation/scripts/` and one env-var addition to `compose.server.yaml`:

**`generate_ee_keypair.py`** — one-time Ed25519 keypair generator that creates `mop_validation/secrets/ee/` and writes `ee_test_private.pem` (PKCS8, unencrypted) and `ee_test_public.pem` (SubjectPublicKeyInfo). Guards against overwrite without `--force`. Sets permissions: private key `0600`, public key `0644`.

**`patch_ee_source.py`** — source patcher that:
1. Reads the 32-byte raw public key from `ee_test_public.pem`
2. Deletes any `plugin*.so` files (forces Python import to use `.py` not compiled binary)
3. Regex-replaces `_LICENCE_PUBLIC_KEY_BYTES` in `axiom-ee/ee/plugin.py` via lambda replacement (avoids regex escape interpretation of `\xNN` in `repr(pub_raw)`)
4. Ensures editable install (no-op if already installed — see deviations)
5. Verifies `inspect.getfile(ee.plugin)` ends in `.py`
6. `--restore` flag reverts to `b'\x00' * 32` placeholder

**compose.server.yaml** — added `- AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY:-}` to the `agent` service environment block. The `:-` default passes empty string when unset, keeping CE-degraded mode safe.

## Verification Results

All checks pass:

```
[OK] ee_test_private.pem and ee_test_public.pem exist in mop_validation/secrets/ee/
[OK] Public key deserialises to exactly 32 raw bytes
[OK] Without --force: prints [WARN] and exits 1 (does not overwrite)
[OK] ee.plugin._LICENCE_PUBLIC_KEY_BYTES != b'\x00'*32 (test key active)
[OK] inspect.getfile(ee.plugin) returns .py path
[OK] --restore reverts constant to b'\x00' * 32 placeholder
[OK] compose.server.yaml agent env block contains AXIOM_LICENCE_KEY passthrough
[OK] 6/6 test_licence.py unit tests pass (unaffected)
```

## Commits

| Task | Repo | Hash | Description |
|------|------|------|-------------|
| Task 1 | mop_validation | d8c441f | feat(39-01): add Ed25519 test keypair generator (EEDEV-01) |
| Task 2 | mop_validation | 02aed94 | feat(39-01): add EE source patcher + editable install helper (EEDEV-02) |
| Task 2 | master_of_puppets | 16a7cb6 | feat(39-01): add AXIOM_LICENCE_KEY passthrough to agent service (EEDEV-02) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] re.sub regex escape error with bytes repr**
- **Found during:** Task 2 — first test run
- **Issue:** `re.sub(pattern, replacement_line, content)` raised `re.error: bad escape \x` because `repr(pub_raw)` contains `\xNN` sequences that re.sub treats as regex escape sequences
- **Fix:** Replaced string replacement argument with a lambda `_replacer` that increments a counter and returns the string literal directly
- **Files modified:** `mop_validation/scripts/patch_ee_source.py`

**2. [Rule 1 - Bug] pip install -e fails in MoP venv due to Cython build issue**
- **Found during:** Task 2 — pip install attempt
- **Issue:** `pip install -e axiom-ee` fails with "same file" error: `setup.py`'s `BuildExtAndCopyInits.run()` calls `shutil.copyfile(src, dest)` where `src == dest` when `self.inplace=True` (editable mode). Additionally, `setuptools` is not in the MoP venv, so setup.py imports fail with `ModuleNotFoundError`.
- **Fix:** `patch_ee_source.py` checks if axiom-ee is already editable-installed (`pip show axiom-ee` contains "Editable project location") and skips the pip install if so. The `.so` deletion + `.py` patching is what matters for the import resolution — the editable `.pth` file is already in place.
- **Files modified:** `mop_validation/scripts/patch_ee_source.py`

**3. [Rule 3 - Blocking] .worktrees/axiom-split/ does not exist**
- **Found during:** Task 2 planning
- **Issue:** The plan references `compose.server.yaml` at `.worktrees/axiom-split/puppeteer/compose.server.yaml`, but the worktree does not exist on this machine
- **Fix:** Applied the compose change to the main `puppeteer/compose.server.yaml` — the correct production file
- **Files modified:** `/home/thomas/Development/master_of_puppets/puppeteer/compose.server.yaml`

**4. [Rule 2 - Tooling] Use MoP venv python for import verification**
- **Found during:** Task 2 verification
- **Issue:** System `python3` cannot `import ee.plugin` (axiom-ee is only installed in the MoP venv). The plan's verify command uses `python3 -c "import ee.plugin..."` which would fail on the system interpreter.
- **Fix:** `_verify_py_import()` and `_get_python()` in `patch_ee_source.py` detect and use `MOP_DIR/.venv/bin/python3` if it exists, falling back to `sys.executable`.

## Key Decisions Made

1. **Lambda in re.sub** — `repr(pub_raw)` for a 32-byte Ed25519 key contains `\xNN` sequences. Python's `re.sub` with a string replacement interprets these as regex escape sequences and raises `re.error`. Using a lambda replacement bypasses this entirely.

2. **Skip editable install if already installed** — The Cython-based `setup.py` has a bug where `BuildExtAndCopyInits.run()` tries to copy `__init__.py` to itself in inplace editable mode, causing `shutil.copyfile` to raise "same file". Since the MoP venv already has axiom-ee installed as editable (from a prior session), the install step is safely skipped. A fresh-environment setup would need to install from a pre-built wheel or fix the setup.py.

3. **compose.server.yaml target** — Applied to `puppeteer/compose.server.yaml` in the main repo, not the non-existent worktree path. This is the file actually used by `docker compose` in development.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| mop_validation/scripts/generate_ee_keypair.py | FOUND |
| mop_validation/scripts/patch_ee_source.py | FOUND |
| mop_validation/secrets/ee/ee_test_private.pem | FOUND |
| mop_validation/secrets/ee/ee_test_public.pem | FOUND |
| commit d8c441f (mop_validation) | FOUND |
| commit 02aed94 (mop_validation) | FOUND |
| commit 16a7cb6 (master_of_puppets) | FOUND |

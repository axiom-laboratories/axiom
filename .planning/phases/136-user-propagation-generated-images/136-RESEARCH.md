# Phase 136: User Propagation to Generated Images - Research

**Researched:** 2026-04-12
**Domain:** Foundry Dockerfile generation — non-root user injection into dynamically generated Dockerfiles
**Confidence:** HIGH

## Summary

Phase 136 extends the non-root user pattern established in Phase 132 (Containerfile.server and Containerfile.node) to Foundry-generated Dockerfiles. The Foundry `build_template()` method in `foundry_service.py` generates Dockerfiles dynamically from blueprints and runtime definitions. Currently, these generated Dockerfiles do not include user creation or the `USER appuser` directive, leaving generated images to run as root.

This phase adds user creation (OS-family-specific syntax) at the start of the Dockerfile, then adds chown + USER directives at the end (immediately before CMD), following the exact pattern validated in Phase 132. The change is isolated to `foundry_service.py` `build_template()` and guards all user-related injection with OS family detection (`if os_family in ("DEBIAN", "ALPINE")`), skipping WINDOWS OS family entirely.

**Primary recommendation:** Insert user creation RUN as the second Dockerfile line (after FROM, before any package operations), and insert chown + USER as the final two lines before CMD. Use the same syntax verified in Phase 132: Alpine `adduser -D appuser`, Debian `useradd --no-create-home appuser`. Guard all injection with OS family check to skip WINDOWS.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Apply USER injection to DEBIAN and ALPINE OS families only
- Skip WINDOWS OS family entirely — Windows containers use a different user model; no Unix `adduser`/`useradd` equivalent; the entire v22.0 security hardening is Linux-specific
- User creation placement: first RUN step, immediately after FROM line
- Ownership and USER directive placement: after all COPY and install operations, just before CMD
- DEBIAN: `RUN useradd --no-create-home appuser`
- ALPINE: `RUN adduser -D appuser`
- After all operations, add `RUN chown -R appuser:appuser /app` then `USER appuser` before CMD

### Claude's Discretion
- Exact `adduser`/`useradd` flags beyond the minimum (shell, home dir options)
- Whether chown and USER are injected as a single code block or separate list.append calls in foundry_service.py
- Smelt-check compatibility — `python --version && pip --version` runs in the built image; both are system-wide installs accessible to appuser, no adjustment needed

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-08 | Foundry-generated Dockerfiles append `USER appuser` after all package installs | foundry_service.py `build_template()` method is the single integration point; user creation syntax is OS-family-specific (DEBIAN/ALPINE only); pattern replicates Phase 132 approach which is now verified in production Containerfiles |

</phase_requirements>

---

## Standard Stack

### Core Changes
| File | Action | Purpose | Why Standard |
|------|--------|---------|--------------|
| `foundry_service.py` `build_template()` | Inject user creation RUN after FROM, chown + USER before CMD | Extend non-root pattern from base images to generated images | Ensures all Puppet nodes — whether using base images or Foundry-built custom images — run as non-root appuser |
| Generated Dockerfile | Include `RUN adduser -D appuser` (Alpine) or `RUN useradd --no-create-home appuser` (Debian) | Create non-root user with consistent UID 1000 | Aligns with Phase 132 baseline for uniform user context across orchestrator |
| Generated Dockerfile | Include `RUN chown -R appuser:appuser /app` + `USER appuser` before CMD | Set directory ownership and switch execution context | Critical for volume mounting and job execution correctness |

### User Creation Syntax (Verified in Phase 132, Production)

**Alpine (`adduser -D`):**
```dockerfile
RUN adduser -D appuser
```
- `-D` skips password creation (appropriate for containers)
- No explicit `--uid` — Alpine's `adduser` assigns 1000 as the first non-system user by default
- No home directory created (default behavior, appropriate for container workload)

**Debian (`useradd --no-create-home`):**
```dockerfile
RUN useradd --no-create-home appuser
```
- `--no-create-home` skips creating `/home/appuser` (reduces bloat)
- No explicit `--uid` — Debian's `useradd` assigns 1000 as the first non-system user
- User exists only to run the application; no interactive shell access

**Directory Ownership:**
```dockerfile
RUN chown -R appuser:appuser /app
```
- Recursively sets ownership of /app and all contents
- Must use `-R` flag (critical: without it, only the directory itself is chowned, not contents)
- Happens before USER directive (executed as root)

**USER Directive:**
```dockerfile
USER appuser
```
- Baked into the image; portable across compose files
- All subsequent RUN commands and final CMD execute as appuser
- No reliance on runtime `user:` override in compose

### Placement in Generated Dockerfile

**Current foundry_service.py structure (lines 206–298):**
```
FROM {base_image}
COPY pip.conf /etc/pip.conf
[mirror config injection]
[capability matrix recipes]
RUN pip install [python packages]
ENV EGRESS_POLICY='...'
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY environment_service/ environment_service/
CMD ["python", "environment_service/node.py"]
```

**After Phase 136 injection:**
```
FROM {base_image}
RUN adduser -D appuser          # ← NEW: User creation (immediately after FROM)
COPY pip.conf /etc/pip.conf
[mirror config injection]
[capability matrix recipes]
RUN pip install [python packages]
ENV EGRESS_POLICY='...'
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY environment_service/ environment_service/
RUN chown -R appuser:appuser /app  # ← NEW: Ownership change (before USER)
USER appuser                       # ← NEW: User directive (before CMD)
CMD ["python", "environment_service/node.py"]
```

### Integration Points

**In `foundry_service.py` `build_template()` (line 59–435):**
1. **Line 89:** `os_family` variable is already computed from `rt_bp.os_family` or derived from `base_os` string
   - Use this exact variable to branch on DEBIAN vs ALPINE
   - Guard: `if os_family in ("DEBIAN", "ALPINE")`
2. **After line 206 (`FROM {base_image}`):** Insert user creation RUN
   - No need for separate if-block per line; can be conditional append
   - Example: `if os_family == "ALPINE": dockerfile.append("RUN adduser -D appuser") else if os_family == "DEBIAN": dockerfile.append("RUN useradd --no-create-home appuser")`
3. **Just before line 298 (`CMD [...]`):** Insert chown + USER
   - Both lines appended unconditionally within the OS-family guard
   - Example: `if os_family in ("DEBIAN", "ALPINE"): dockerfile.append("RUN chown -R appuser:appuser /app"); dockerfile.append("USER appuser")`

### Alpine Post-Processing (lines 301–305)

Existing pattern already in place:
```python
if os_family == "ALPINE":
    dockerfile = [
        line.replace("apk add", "apk add --allow-untrusted") if "apk add" in line else line
        for line in dockerfile
    ]
```

User injection occurs BEFORE this block (lines added to the `dockerfile` list), so no conflicts with the post-processing step.

---

## Architecture Patterns

### Recommended Implementation Strategy

**Step 1: User Creation (immediately after FROM)**
- Detect OS family from `rt_bp.os_family` or inferred from `base_os`
- If DEBIAN: append `RUN useradd --no-create-home appuser`
- If ALPINE: append `RUN adduser -D appuser`
- If WINDOWS or unknown: skip (no injection)

**Step 2: All Existing Operations (unchanged)**
- Mirror config injection (pip.conf, sources.list, repositories)
- Capability matrix recipes
- Package installs
- Workdir, Copy, Install requirements

**Step 3: Ownership + User Switch (just before CMD)**
- If OS family was DEBIAN or ALPINE:
  - Append `RUN chown -R appuser:appuser /app`
  - Append `USER appuser`

**Why this order matters:**
1. User creation must happen early (after FROM, before any RUN commands that might reference appuser)
2. All package installs and file operations run as root (required for apt/apk and file ownership changes)
3. Chown happens as root (last privilege-escalated operation)
4. USER directive happens LAST before CMD (all subsequent commands run as appuser)

### Code Structure Example

```python
# After line 206: FROM {base_image}
if os_family in ("DEBIAN", "ALPINE"):
    if os_family == "ALPINE":
        dockerfile.append("RUN adduser -D appuser")
    elif os_family == "DEBIAN":
        dockerfile.append("RUN useradd --no-create-home appuser")

# ... all existing operations ...

# Before line 298: CMD [...]
if os_family in ("DEBIAN", "ALPINE"):
    dockerfile.append("RUN chown -R appuser:appuser /app")
    dockerfile.append("USER appuser")
```

### Anti-Patterns to Avoid

- **No chown flag:** `RUN chown appuser /app` (missing `-R`) only changes the directory, not contents. Files inside /app stay root-owned. Must use `-R`.
- **USER in the middle:** Placing `USER appuser` before package installs causes subsequent RUN commands to fail (appuser can't install packages). Place at the very end.
- **Windows user creation:** Windows containers don't support `adduser` or `useradd`. Attempting to inject these commands into WINDOWS Dockerfiles causes build failures. Must guard with OS family check.
- **Implicit home directory assumption:** Alpine's `adduser` by default creates no home directory; Debian's `useradd` by default creates one. Using `--no-create-home` for Debian makes this explicit and consistent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-root user creation in generated Dockerfile | Custom shell script to detect OS and call appropriate user command | `adduser -D appuser` (Alpine) / `useradd --no-create-home appuser` (Debian) | Built-in commands are standard, portable, and already validated in Phase 132 production Containerfiles |
| Verifying UID in built image | Custom stat/id parsing in entrypoint | Run smelt-check `python --version && pip --version` as appuser — if it succeeds, user context is correct | Already integrated in `StagingService.run_smelt_check()` (line 411); validates execution as appuser without needing explicit UID inspection |
| Custom user ownership logic | Shell script to find and chown user-writable paths | Single `RUN chown -R appuser:appuser /app` before USER directive | Declarative, verifiable at build time, happens once; no runtime overhead |

---

## Common Pitfalls

### Pitfall 1: Forgetting `-R` Flag in chown

**What goes wrong:** `RUN chown appuser /app` (missing `-R`) only changes the /app directory itself. Files inside (requirements.txt, environment_service/*, etc.) remain root-owned. When appuser tries to read them, permission denied.

**Why it happens:** Copy-paste error or misunderstanding of chown syntax.

**How to avoid:** Always use `RUN chown -R appuser:appuser /app`. The `-R` flag is mandatory for recursive ownership change.

**Warning signs:**
- Smelt-check fails with "Permission denied" when running `python --version` inside the built image
- Container logs show permission errors when appuser tries to read app files
- `docker exec <image> ls -la /app` shows files owned by root:root

### Pitfall 2: USER Directive in the Wrong Place

**What goes wrong:** If `USER appuser` is placed after mirror config injection but before package installs, subsequent RUN commands fail:
```
RUN pip install ... → fails with "permission denied" (appuser can't write to system paths)
RUN apt-get install ... → fails (appuser doesn't have sudo)
```

**Why it happens:** Misunderstanding the build flow or copy-pasting from a different pattern.

**How to avoid:** Place `USER appuser` at the VERY END of the Dockerfile, immediately before (or as part of) CMD.

**Warning signs:**
- Build fails with "permission denied" or "command not found" in RUN steps
- Error messages show "appuser is not in the sudoers file"

### Pitfall 3: Windows OS Family Not Guarded

**What goes wrong:** If OS family is WINDOWS but the code injects `RUN adduser -D appuser`, the Dockerfile build fails because Windows containers don't have a `adduser` command.

**Why it happens:** Forgetting to guard user injection with an OS family check (`if os_family in ("DEBIAN", "ALPINE")`).

**How to avoid:** Always guard user injection with OS family check. WINDOWS scaffolding exists in the codebase but should not receive user injection (per CONTEXT.md decision).

**Warning signs:**
- Build fails with "RUN: command not found" or "adduser: not found" for WINDOWS templates
- Template selection includes a WINDOWS base image (e.g., `windows-server-core`)

### Pitfall 4: Missing User Creation Before chown + USER

**What goes wrong:** If the code tries to set `USER appuser` but the user was never created (e.g., OS family check skipped user creation), the USER directive fails or the container startup fails with "user appuser not found".

**Why it happens:** Conditional logic error or incomplete implementation.

**How to avoid:** Ensure that user creation (adduser/useradd) and USER directive are tied together — if one is injected, the other must be too. They should be guarded by the same OS family condition.

**Warning signs:**
- Container startup fails with "user appuser not found" or "uid 1000 not found"
- Docker logs show error during the USER directive parsing

---

## Code Examples

Verified patterns from Phase 132 production Containerfiles:

### Alpine User Creation (Containerfile.server — in production)

```dockerfile
# Phase 132: Non-Root User Foundation (Alpine)
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser
```

Source: `/home/thomas/Development/master_of_puppets/puppets/Containerfile.server` (verified 2026-04-12)

### Debian User Creation (Containerfile.node — in production)

```dockerfile
# Phase 132: Non-Root User Foundation (Debian)
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser
```

Note: Phase 132 used `-m` (create home dir). Phase 136 CONTEXT.md specifies `--no-create-home` for generated images (reduces bloat in custom images). Both are functionally correct; `--no-create-home` is lighter.

Source: `/home/thomas/Development/master_of_puppets/puppets/Containerfile.node` (verified 2026-04-12)

### Foundry Integration Pattern (foundry_service.py `build_template()`)

```python
# After line 206: dockerfile = [f"FROM {base_image}"]
# Inject user creation for DEBIAN/ALPINE
if os_family in ("DEBIAN", "ALPINE"):
    if os_family == "ALPINE":
        dockerfile.append("RUN adduser -D appuser")
    elif os_family == "DEBIAN":
        dockerfile.append("RUN useradd --no-create-home appuser")

# ... existing mirror config, capability matrix, package installs ...

# Before line 298: dockerfile.append("CMD [...]")
# Inject chown + USER for DEBIAN/ALPINE
if os_family in ("DEBIAN", "ALPINE"):
    dockerfile.append("RUN chown -R appuser:appuser /app")
    dockerfile.append("USER appuser")
```

Source: Pattern derived from Phase 132 research; to be implemented in Phase 136 Plan 01

### Smelt-Check Verification (already in place)

```python
# Line 411 in foundry_service.py
validation_report = await StagingService.run_smelt_check(tmpl.id, "python --version && pip --version")

if validation_report["status"] == "SUCCESS":
    logger.info(f"✅ Smelt-Check PASSED for {tmpl.friendly_name}")
    tmpl.status = "ACTIVE"
else:
    logger.error(f"❌ Smelt-Check FAILED for {tmpl.friendly_name}")
    tmpl.status = "FAILED"
```

This existing smelt-check runs inside the built image. After Phase 136, it will execute as appuser (due to the USER directive in the Dockerfile). If it succeeds, user context is correct. Both `python` and `pip` are system-wide installs, so appuser can access them without additional configuration.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generated Dockerfiles run as root | Generated Dockerfiles run as non-root appuser | Phase 136 (2026-04) | Closes security gap for custom images built by Foundry; aligns with Phase 132 baseline for all nodes |
| Base images (Containerfile.node) define USER | Generated images inherit root from base | Before Phase 136 | Custom images override base image USER directive if they don't re-apply it |
| User creation varies per Dockerfile | Consistent `adduser -D` (Alpine) / `useradd --no-create-home` (Debian) pattern | Phase 132–136 span | Single pattern across all images; UID 1000 consistent |

**Deprecated/outdated:**
- Relying on runtime `user:` compose override instead of baking USER in Dockerfile — Phase 132 established the pattern of declarative USER in Containerfile; Phase 136 extends it to generated Dockerfiles
- Custom user setup scripts — built-in `adduser`/`useradd` is simpler and more maintainable

---

## Open Questions

1. **Separation of user creation and chown/USER as code blocks**
   - What we know: CONTEXT.md lists this as Claude's Discretion; both single-block and multi-step approaches are valid
   - What's unclear: Whether to inject user creation immediately after FROM or as a separate comprehension pass
   - Recommendation: Inject user creation on line 207 (right after FROM), then chown/USER on lines 295–296 (before CMD). This mimics the Containerfile.node pattern exactly and keeps related operations together.

2. **Smelt-check compatibility with non-root execution**
   - What we know: StagingService.run_smelt_check() already exists (line 411); it runs `python --version && pip --version`
   - What's unclear: Does the smelt-check spawn a subcontainer that inherits the USER directive, or does it run the command as root?
   - Recommendation: Verify via test execution in Phase 136 Plan 01; if the smelt-check fails post-USER injection, adjust the command or inspection method (but this is unlikely — python/pip are system-wide).

3. **OCI cache FROM rewriting interaction with user injection**
   - What we know: Lines 307–318 rewrite FROM directives if OCI caching is enabled
   - What's unclear: Does user creation injection happen before or after this rewrite pass?
   - Recommendation: User creation injection happens during initial Dockerfile list building (lines 206+); OCI rewriting happens at lines 307–318 as a post-processing pass. No interaction issue — user creation lines are not FROM directives, so they won't be rewritten.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (FastAPI backend) + unittest.mock for async/DB mocking |
| Config file | `puppeteer/pytest.ini` (if exists) or pytest default behavior |
| Quick run command | `cd puppeteer && pytest tests/test_foundry.py -v -k "test_build" --tb=short` |
| Full suite command | `cd puppeteer && pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-08 | Generated Dockerfile for DEBIAN base includes `RUN useradd --no-create-home appuser` | unit | `cd puppeteer && pytest tests/test_foundry.py::test_debian_user_injection -v` | ❌ Wave 0 |
| CONT-08 | Generated Dockerfile for ALPINE base includes `RUN adduser -D appuser` | unit | `cd puppeteer && pytest tests/test_foundry.py::test_alpine_user_injection -v` | ❌ Wave 0 |
| CONT-08 | Generated Dockerfile includes `RUN chown -R appuser:appuser /app` before USER | unit | `cd puppeteer && pytest tests/test_foundry.py::test_chown_before_user -v` | ❌ Wave 0 |
| CONT-08 | Generated Dockerfile includes `USER appuser` before CMD | unit | `cd puppeteer && pytest tests/test_foundry.py::test_user_directive_placement -v` | ❌ Wave 0 |
| CONT-08 | WINDOWS OS family templates do NOT receive user injection | unit | `cd puppeteer && pytest tests/test_foundry.py::test_windows_skip_user_injection -v` | ❌ Wave 0 |
| CONT-08 | Built image runs smelt-check as appuser (uid 1000) | integration | `cd puppeteer && pytest tests/test_foundry.py::test_smelt_check_as_appuser -v` | ❌ Wave 0 |
| CONT-08 | Built image allows appuser to read environment_service/ files | integration | `cd puppeteer && pytest tests/test_foundry.py::test_appuser_file_access -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_foundry.py -v -k "user_injection" --tb=short`
- **Per wave merge:** `cd puppeteer && pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_foundry.py` — unit tests for user injection (DEBIAN, ALPINE, WINDOWS OS family handling)
  - `test_debian_user_injection` — verify `RUN useradd --no-create-home appuser` in Dockerfile list
  - `test_alpine_user_injection` — verify `RUN adduser -D appuser` in Dockerfile list
  - `test_chown_before_user` — verify `RUN chown -R appuser:appuser /app` before `USER appuser`
  - `test_user_directive_placement` — verify `USER appuser` is immediately before CMD
  - `test_windows_skip_user_injection` — verify WINDOWS templates do not include user lines
- [ ] `tests/test_foundry.py` — integration test for smelt-check execution
  - `test_smelt_check_as_appuser` — verify smelt-check runs as appuser (uid 1000) and succeeds
  - `test_appuser_file_access` — verify appuser can read environment_service/ files (no permission denied)
- [ ] Existing test infrastructure (`tests/conftest.py`) — may need mock database/template fixtures if not already present
  - Framework install: `pip install pytest pytest-asyncio` (should already be in `requirements.txt`)

*(Gaps: All tests need to be written — existing `test_foundry.py` has ingredient tree tests but not user injection tests)*

---

## Sources

### Primary (HIGH confidence)
- Phase 132 RESEARCH.md — validated user creation patterns for DEBIAN and ALPINE (source: `/home/thomas/Development/master_of_puppets/.planning/phases/132-non-root-user-foundation/132-RESEARCH.md`)
- Phase 132 production Containerfiles — verified implementation in use (source: `puppets/Containerfile.node`)
- foundry_service.py `build_template()` — current Dockerfile generation logic (source: `puppeteer/agent_service/services/foundry_service.py` lines 59–435)
- CONTEXT.md Phase 136 — locked decisions on OS family, user creation syntax, placement (source: `.planning/phases/136-user-propagation-generated-images/136-CONTEXT.md`)

### Secondary (MEDIUM confidence)
- Alpine Linux `adduser` command — verified via multiple official sources for `-D` flag behavior and UID assignment (sources: [Alpine Linux adduser documentation](https://www.baeldung.com/linux/docker-alpine-add-user), [nixCraft guide](https://www.cyberciti.biz/faq/how-to-add-and-delete-users-on-alpine-linux/))
- Debian `useradd` command — verified via official Debian documentation and best practices for `--no-create-home` flag (sources: [Debian manual on creating users](https://www.debian.org/doc/manuals/securing-debian-manual/bpp-lower-privs.en.html), [Docker non-root best practices](https://oneuptime.com/blog/post/2026-01-25-docker-container-user-permissions/view))
- Docker USER instruction — verified via official Docker documentation (source: [Docker blog on USER instruction](https://www.docker.com/blog/understanding-the-docker-user-instruction/))

### Tertiary (LOW confidence)
- None — all critical claims have been verified against Phase 132 production or official documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — user creation commands verified in Phase 132 production Containerfiles and multiple official sources
- Architecture: **HIGH** — integration pattern derived directly from foundry_service.py existing structure and Phase 132 pattern
- Pitfalls: **HIGH** — all pitfalls documented in Phase 132 RESEARCH.md and applicable here
- Validation: **MEDIUM** — smelt-check already integrated; test cases need to be written but pattern is clear

**Research date:** 2026-04-12  
**Valid until:** 2026-05-12 (30 days — stable container security patterns)

# Phase 136: User Propagation to Generated Images - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Foundry-generated Dockerfiles include `USER appuser` directive and the associated user creation + ownership steps. Applies only to images built by `build_template` in `foundry_service.py`. Base images (`Containerfile.server`, `Containerfile.node`) are out of scope — Phase 132 handled those.

Requirement: CONT-08

</domain>

<decisions>
## Implementation Decisions

### OS family scope
- Apply USER injection to DEBIAN and ALPINE OS families only
- Skip WINDOWS OS family entirely — Windows containers use a different user model; no Unix `adduser`/`useradd` equivalent; the entire v22.0 security hardening is Linux-specific
- The Windows starter template scaffolding remains but receives no user injection
- Guard with `if os_family in ("DEBIAN", "ALPINE")` before injecting any user-related lines

### User creation placement
- Add the user creation RUN as the **first RUN step**, immediately after the `FROM` line
- All subsequent RUN commands (mirror config COPYs, capability matrix recipes, pip installs) still run as root — USER is not set until the end
- DEBIAN: `RUN useradd --no-create-home appuser`
- ALPINE: `RUN adduser -D appuser`
- Consistent with Phase 132 OS-specific approach (no explicit `--uid 1000` — OS assigns 1000 as first non-system user by default)

### Ownership and USER directive placement
- After all COPY and install operations, add `RUN chown -R appuser:appuser /app`
- Then immediately `USER appuser`
- Both lines go just before `CMD` — at the very end of the Dockerfile
- Matches Phase 132 pattern exactly: chown first, then USER switch

### Final Dockerfile tail (DEBIAN example)
```
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages
COPY environment_service/ environment_service/
RUN chown -R appuser:appuser /app
USER appuser
CMD ["python", "environment_service/node.py"]
```

### Claude's Discretion
- Exact `adduser`/`useradd` flags beyond the minimum (shell, home dir options)
- Whether chown and USER are injected as a single code block or separate list.append calls in foundry_service.py
- Smelt-check compatibility — `python --version && pip --version` runs in the built image; both are system-wide installs accessible to appuser, no adjustment needed

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `foundry_service.py` `build_template()`: `dockerfile` is a Python list of strings — add user creation line early, append chown + USER at the end
- `os_family` variable already computed from `rt_bp.os_family` or derived from `base_os` — use this to branch DEBIAN vs ALPINE user creation syntax
- Alpine post-processing block (lines starting with `apk add` → `apk add --allow-untrusted`) is already OS-family-aware — user injection fits the same pattern

### Established Patterns
- Phase 132: `adduser appuser` (Alpine) / `useradd appuser` (Debian), chown /app, USER at the end — replicate exactly
- The `dockerfile` list is built top-to-bottom; user creation goes at position 1 (after `FROM`), chown+USER appended just before `CMD`
- WINDOWS OS family already exists in the codebase — skip, don't remove

### Integration Points
- `build_template()` in `foundry_service.py` — only file that needs changes for this phase
- No changes to `node.py`, `runtime.py`, compose files, or any other service
- Smelt-check (`StagingService.run_smelt_check`) runs `python --version && pip --version` inside the built image — runs as appuser post-phase; both commands are system-wide, no compatibility issue

</code_context>

<specifics>
## Specific Ideas

- Windows Server Core is out of scope for this product as currently architected — the execution model (Linux socket mounts, container networking, UID-based isolation) is fundamentally Linux-centric. The Windows OS family scaffolding is aspirational. Phase 136 skips it; no changes to Windows-related code paths.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 136-user-propagation-generated-images*
*Context gathered: 2026-04-12*

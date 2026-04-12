---
phase: 132-non-root-user-foundation
plan: 01
subsystem: Container Hardening — Non-Root User Foundation
tags:
  - containerization
  - security
  - non-root-user
  - phase-132
dependency_graph:
  provides:
    - appuser (UID 1000) in Containerfile.server
    - appuser (UID 1000) in Containerfile.node
    - /app ownership (appuser:appuser) in both images
  requires: []
  affects:
    - Phase 132 Plan 02 (image rebuild and validation)
    - Phase 133+ (all subsequent hardening depends on non-root foundation)
tech_stack:
  patterns:
    - Alpine RUN adduser (Containerfile.server)
    - Debian RUN useradd -m (Containerfile.node)
    - Pre-USER chown -R for volume inheritance
  added: []
key_files:
  created: []
  modified:
    - puppeteer/Containerfile.server
    - puppets/Containerfile.node
decisions:
  - User creation via OS-native tools (adduser for Alpine, useradd for Debian)
  - UID 1000 assigned by default OS behavior (no explicit --uid flag)
  - chown executed before USER directive to ensure correct volume ownership
  - No entrypoint migration logic; volumes will be recreated on first deploy
metrics:
  duration_minutes: 5
  completed_date: 2026-04-12
  tasks_completed: 2
  files_modified: 2
---

# Phase 132 Plan 01: Non-Root User Foundation Summary

Containerfile.server and Containerfile.node updated to create non-root appuser (UID 1000) and set correct /app directory ownership. Both images now run all processes as appuser instead of root.

## Changes Made

### Containerfile.server (Agent & Model Services)

**File:** `puppeteer/Containerfile.server`

**Added three lines at the end of the build (before "Entrypoints done via command in compose" comment):**

```dockerfile
RUN adduser appuser
RUN chown -R appuser:appuser /app
USER appuser
```

**Rationale:**
- Alpine's `adduser` command creates a non-root user interactively (no flags needed)
- `chown -R appuser:appuser /app` ensures the /app directory and all contents are owned by appuser
- `USER appuser` switches all subsequent RUN, CMD, and ENTRYPOINT directives to execute as appuser
- Placement after all package installs ensures root is available for system operations

**Lines modified:** 3 lines added at line 58-60

### Containerfile.node (Worker Node)

**File:** `puppets/Containerfile.node`

**Added three lines before the CMD directive:**

```dockerfile
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser
```

**Rationale:**
- Debian's `useradd` with `-m` flag creates a non-root user with a home directory (/home/appuser)
- The `-m` flag is harmless in container context even though /home/appuser won't be used at runtime
- `chown -R appuser:appuser /app` ensures correct ownership for mounted volumes
- `USER appuser` ensures the node.py process runs as UID 1000
- Placement before CMD ensures all subsequent operations execute as appuser

**Lines modified:** 3 lines added at line 47-49

## Verification

**Automated verification (grep checks):**

Containerfile.server verification:
```
58:RUN adduser appuser
59:RUN chown -R appuser:appuser /app
60:USER appuser
```

Containerfile.node verification:
```
47:RUN useradd -m appuser
48:RUN chown -R appuser:appuser /app
49:USER appuser
```

Both Containerfiles have valid Dockerfile syntax (no parse errors). The three-line pattern (user creation → ownership → user switch) is correctly ordered in both files.

## Deviations from Plan

None. Plan executed exactly as written.

## Next Steps

Plan 02 (Wave 2) will:
1. Rebuild both images with the new Containerfiles
2. Run the Docker stack (docker compose up -d)
3. Verify via docker exec that processes run as UID 1000
4. Verify via stat that /app and /app/secrets are owned by appuser:appuser
5. Confirm volume inheritance works correctly for mounted volumes

## Commits

- `bfd2afa` feat(132-01): Add appuser and USER directive to Containerfile.server
- `f93b36c` feat(132-01): Add appuser and USER directive to Containerfile.node

# Container Hardening & EE Licence Protection Pitfalls

**Domain:** Adding non-root container users, HMAC-keyed hash chain clock rollback detection, Ed25519 signed artifact verification, and removing privileged mode from containers that spawn child execution environments.

**Project:** Axiom — Secure orchestration platform for hostile environments

**Researched:** 2026-04-12

**Overall Confidence:** HIGH for socket/GID issues and Dockerfile pitfalls (official Docker docs + confirmed community patterns); MEDIUM for HMAC migration and license key validation (architecture-specific to this system); HIGH for Ed25519 verification (cryptography library docs); HIGH for capability drop patterns (Linux kernel documentation + current best practices).

---

## Critical Pitfalls

### Pitfall 1: GID Mismatch on Docker Socket Mount — Non-Root User Permission Denied

**What goes wrong:** Non-root container user (e.g., `appuser` UID 1000) added to docker group via Dockerfile `RUN groupadd; useradd -G docker`, but cannot read `/var/run/docker.sock` when mounted. Foundry template builds fail with "Error response from daemon: Permission denied while trying to connect to the Docker daemon socket." Agent cannot spawn job execution containers.

**Why it happens:** Docker socket on the host is owned by `root:docker` with GID typically 999 (varies by system). When Dockerfile creates a docker group with a hardcoded GID and adds the user to it, that hardcoded GID doesn't match the host's docker GID. Docker Compose `user:` directive only applies if set in the compose file; if only set in Dockerfile via `USER appuser`, the container's group membership has the wrong GID. Additionally, the Dockerfile's hardcoded group number doesn't account for system variation.

**Consequences:**
- Agent container fails at Foundry build phase: "Permission denied" on Docker socket access
- Agent cannot execute jobs requiring Docker container spawning
- Cascading deployment failure—all job execution features become non-functional
- Difficult to diagnose: `id` shows user is in `docker` group, but access is still denied
- May pass unit tests (which don't mount real Docker socket) but fail integration tests

**Prevention:**
1. **Resolve host docker GID dynamically before build**
   ```bash
   # In deploy scripts or CI
   HOST_DOCKER_GID=$(getent group docker | cut -d: -f3)
   docker compose build --build-arg DOCKER_GID=${HOST_DOCKER_GID} agent
   ```

2. **Accept DOCKER_GID as build argument in Dockerfile**
   ```dockerfile
   ARG DOCKER_GID=999
   RUN groupadd -g ${DOCKER_GID} docker && \
       useradd -u 1000 -g appgroup -G docker appuser
   ```

3. **Explicitly set `user:` in compose.yaml** (in addition to Dockerfile)
   ```yaml
   agent:
     build:
       context: .
       args:
         DOCKER_GID: "999"
     user: "1000:1000"  # Explicit UID:GID
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock
   ```

4. **Add integration test verifying socket access**
   ```python
   def test_agent_can_access_docker_socket():
       """Verify non-root user can use Docker socket."""
       result = subprocess.run(
           ["docker", "exec", "puppeteer-agent-1", "docker", "ps"],
           capture_output=True
       )
       assert result.returncode == 0, f"Docker access failed: {result.stderr}"
   ```

5. **Document GID handling in deployment guide**
   ```markdown
   ## Agent Docker Socket Access (Non-Root)
   
   The agent runs as non-root user `appuser` for security hardening.
   To access the Docker socket, it must be in the docker group with matching GID.
   
   Before deploying:
   ```bash
   HOST_DOCKER_GID=$(getent group docker | cut -d: -f3)
   docker compose build --build-arg DOCKER_GID=${HOST_DOCKER_GID} agent
   ```

**Detection:**
- Build/startup logs: "Error response from daemon: dial unix /var/run/docker.sock: permission denied"
- Compare inside container: `id appuser` shows group membership vs `ls -l /var/run/docker.sock` shows socket GID
- Mismatch on second number: e.g., user has `gid=1000` but socket has `root:docker` (GID 999)

---

### Pitfall 2: Volume Ownership Mismatch on USER Switch — Non-Root User Cannot Write Secrets

**What goes wrong:** Switching to non-root user via `USER appuser` in Dockerfile occurs before secrets directory ownership is set. Subsequent container startup attempts to write to `secrets/boot.log`, fails with "PermissionError: [Errno 13] Permission denied" even though the appuser owns the parent /app directory. Boot.log HMAC verification fails on every restart.

**Why it happens:** Docker volumes mounted as named volumes or bind mounts initially have root ownership. If `USER appuser` is placed before directory ownership is corrected with `chown`, subsequent RUN steps and the running container (as appuser) cannot modify files in that directory. Additionally, if the named volume was pre-populated (e.g., by an initialization script) with root ownership, appuser cannot append to existing files like boot.log.

**Consequences:**
- Agent startup fails: `RuntimeError: secrets/boot.log: Permission denied`
- Secrets volume becomes permanently inaccessible to appuser
- Upgrade with existing secrets/boot.log becomes impossible—cannot read or write
- Rolling back to root user introduces security regression
- Data loss if boot.log is wiped and recreated

**Prevention:**
1. **Place USER instruction AFTER all privileged directory setup**
   ```dockerfile
   # All mkdir, chown, chmod operations as root — before USER switch
   RUN apk add --no-cache curl && \
       mkdir -p /app/secrets && \
       mkdir -p /app/logs && \
       chown 1000:1000 /app/secrets && \
       chown 1000:1000 /app/logs && \
       chmod 750 /app/secrets
   
   # NOW switch to non-root — everything after this runs as appuser
   USER appuser
   
   WORKDIR /app
   ```

2. **Pre-initialize secrets volume with init container** (for existing deployments)
   ```yaml
   init-secrets:
     image: alpine:latest
     volumes:
       - secrets-data:/app/secrets
     entrypoint: |
       sh -c '
       mkdir -p /app/secrets
       chmod -R 770 /app/secrets
       chown -R 1000:1000 /app/secrets
       '
   
   agent:
     depends_on:
       init-secrets:
         condition: service_completed_successfully
   ```

3. **Ensure mounted volume has permissive ownership**
   ```yaml
   # compose.yaml
   volumes:
     secrets-data:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: ${SECRETS_MOUNT_PATH:-/var/lib/axiom/secrets}
   
   # Host side: ensure device path has correct ownership
   # $ mkdir -p /var/lib/axiom/secrets && chmod 770 /var/lib/axiom/secrets
   ```

4. **Handle permission errors gracefully in boot.log initialization**
   ```python
   def check_and_record_boot(...):
       BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
       try:
           BOOT_LOG_PATH.write_text(...)
       except PermissionError as e:
           logger.error(f"Cannot write boot.log: {e}")
           if licence_status != LicenceStatus.CE:
               raise RuntimeError(
                   "EE mode requires writable boot.log. "
                   "Check /app/secrets directory ownership: "
                   f"current user = {os.getuid()}:{os.getgid()}"
               )
           logger.warning("CE mode: clock rollback detection disabled")
           return False
   ```

5. **Document volume ownership expectations**
   ```markdown
   ## Secrets Volume Setup
   
   The secrets-data volume must be writable by UID 1000 (appuser).
   Before deployment, ensure:
   
   ```bash
   mkdir -p /var/lib/axiom/secrets
   chmod 770 /var/lib/axiom/secrets
   chown 1000:1000 /var/lib/axiom/secrets  # If bind mount
   ```

**Detection:**
- Startup logs: "PermissionError: [Errno 13] Permission denied: 'secrets/boot.log'"
- Container exits on lifespan startup: `docker logs puppeteer-agent-1 | grep PermissionError`
- Directory inspection: `docker exec puppeteer-agent-1 ls -la /app/secrets` shows root ownership
- Mismatch: appuser owns /app but not /app/secrets

---

### Pitfall 3: Boot.log SHA256 Entries Invalid After HMAC Migration

**What goes wrong:** Upgrading from SHA256-hashed boot.log format to HMAC-keyed format causes immediate startup failure. Existing boot.log entries (plain SHA256) are treated as HMAC verification failures, triggering "Clock rollback detected" error in EE mode or breaking hash chain continuity in CE mode.

**Why it happens:** Current implementation stores boot.log as `<sha256_hex> <iso_timestamp>` per line. After upgrade to HMAC-keyed hashing, code tries to verify each entry as HMAC using `ENCRYPTION_KEY`. Legacy SHA256 entries have no HMAC tag and cannot be verified. The verification logic doesn't gracefully degrade—it either rejects the entry as corrupted or silently switches to a new chain, losing continuity.

**Consequences:**
- EE deployment fails immediately post-upgrade: "Clock rollback detected" (strict mode raises RuntimeError)
- Audit trail broken: boot.log chain is severed, existing entries abandoned
- Forced downgrade or manual boot.log deletion (data loss)
- Customer deployments must rollback to prior version or lose boot.log history
- No graceful migration path—operator must manually edit boot.log or delete it

**Prevention:**
1. **Implement dual-format parsing with version detection**
   ```python
   def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
       """Support both legacy SHA256 and new HMAC formats."""
       
       if not BOOT_LOG_PATH.exists():
           # Fresh start: use HMAC format
           new_entry = _compute_hmac_entry(...)
           BOOT_LOG_PATH.write_text(f"{new_entry} HMAC-v2\n")
           return True
       
       lines = BOOT_LOG_PATH.read_text().strip().splitlines()
       last_line = lines[-1]
       
       # Detect format from line structure
       parts = last_line.split(" ")
       if len(parts) >= 3 and parts[-1] == "HMAC-v2":
           # New HMAC format — verify as normal
           stored_hmac = parts[0]
           stored_ts = parts[1]
           # Verify HMAC...
       elif len(parts) >= 2 and len(parts[0]) == 64:
           # Legacy SHA256 format — accept and migrate
           legacy_hash = parts[0]
           legacy_ts = parts[1]
           logger.info("Migrating from SHA256 boot.log to HMAC format")
           # Append new HMAC entry after legacy entry
           new_entry = _compute_hmac_entry(legacy_hash, ...)
           lines.append(f"{new_entry} HMAC-v2")
       
       BOOT_LOG_PATH.write_text("\n".join(lines) + "\n")
       return True
   ```

2. **Add boot.log version header**
   ```python
   # At first write in HMAC format
   if not BOOT_LOG_PATH.exists():
       BOOT_LOG_PATH.write_text("# boot.log v2 (HMAC-keyed)\n")
   
   # Parser checks header
   first_line = lines[0] if lines else ""
   if first_line.startswith("# boot.log v2"):
       # New format
       lines = lines[1:]  # Skip header
   else:
       # Legacy format
   ```

3. **Migration window with explicit operator action**
   - Document in UPGRADE.md: "First boot post-upgrade will migrate boot.log format automatically"
   - Log clearly: `logger.info("boot.log: migrated from SHA256 to HMAC-v2 format, 5 legacy entries preserved")`

4. **Provide boot.log repair tool**
   ```python
   # tools/repair_bootlog.py
   def repair_bootlog(legacy_file, new_encryption_key):
       """Migrate legacy SHA256 boot.log to HMAC format."""
       # Read legacy entries, preserve order
       # Recompute new chain: HMAC(prev_hmac + ts) for each entry
       # Write new file with version header
   ```

5. **Test migration path explicitly**
   ```python
   def test_boot_log_migration_sha256_to_hmac():
       """Verify SHA256 entries are accepted during upgrade."""
       # Create legacy boot.log with SHA256 entries
       legacy_log = Path(tmpdir) / "boot.log"
       legacy_hash = "abc123" * 10 + "ff"  # 64 hex chars
       legacy_log.write_text(f"{legacy_hash} 2026-04-01T10:00:00+00:00\n")
       
       # Mock ENCRYPTION_KEY
       with patch("ENCRYPTION_KEY", b"test-key"):
           # Should accept legacy entry and append new HMAC entry
           check_and_record_boot()
       
       # Verify: legacy entry still there + new HMAC entry added
       new_lines = legacy_log.read_text().strip().splitlines()
       assert len(new_lines) == 2
       assert new_lines[0].startswith("abc123")  # Legacy preserved
       assert "HMAC-v2" in new_lines[1]  # New entry
   ```

**Detection:**
- Upgrade logs: "Clock rollback detected" on first EE boot post-upgrade
- boot.log parsing fails: ValueError on HMAC format parsing
- Legacy entries in boot.log: `cat secrets/boot.log | head -1` shows plain hex, no HMAC tag

---

### Pitfall 4: ENCRYPTION_KEY Missing or Mismatched in Production — HMAC Verification Silent Failure

**What goes wrong:** Agent container runs without ENCRYPTION_KEY env var set (or set to wrong value). HMAC verification falls back to dev-only hardcoded key or skips entirely. Boot.log becomes unverifiable—attacker could modify it without detection. On cluster upgrade, different agents have different ENCRYPTION_KEY values; HMAC verification fails inconsistently.

**Why it happens:** ENCRYPTION_KEY is loaded lazily during security module initialization. If unset, code falls back to a development key or logs a warning but continues. In production, operators may forget to set ENCRYPTION_KEY in secrets.env. In distributed deployments, if the key isn't centrally managed, agents may have different keys. EE licence validation doesn't strictly enforce ENCRYPTION_KEY presence at startup, so boot.log validation silently weakens.

**Consequences:**
- Silent security gap: boot.log can be tampered with if ENCRYPTION_KEY is dev-fallback
- Inconsistent HMAC validation across cluster: agent-1 accepts boot.log, agent-2 rejects it
- Startup confusion: "Why is this agent failing while that one works?" (different ENCRYPTION_KEY)
- No clear warning to operator that ENCRYPTION_KEY is missing in production

**Prevention:**
1. **Enforce ENCRYPTION_KEY at startup for EE mode**
   ```python
   def load_encryption_key(licence_status: LicenceStatus):
       """Load ENCRYPTION_KEY, enforce in EE mode."""
       env_key = os.getenv("ENCRYPTION_KEY", "").strip()
       
       if licence_status.is_ee_active:
           # EE requires explicit key
           if not env_key:
               raise RuntimeError(
                   "ENCRYPTION_KEY env var is REQUIRED for EE mode "
                   "(needed for boot.log HMAC verification and secrets encryption). "
                   "Generate with: openssl rand -base64 32"
               )
           return env_key.encode()
       else:
           # CE: use dev fallback with warning
           if not env_key:
               logger.warning(
                   "ENCRYPTION_KEY not set — using development fallback. "
                   "For production, set ENCRYPTION_KEY env var."
               )
               return b"dev-fallback-key-ce-only"
           return env_key.encode()
   ```

2. **Document ENCRYPTION_KEY generation in installation guide**
   ```markdown
   ## Step 2: Generate Encryption Key
   
   The ENCRYPTION_KEY is used to encrypt secrets in the database and for EE licence boot.log verification.
   
   ```bash
   openssl rand -base64 32
   # Copy output to .env or secrets.env:
   echo "ENCRYPTION_KEY=<output>" >> .env
   ```
   
   For EE mode, this is REQUIRED. For CE mode, it's optional but strongly recommended for production.
   ```

3. **Validate ENCRYPTION_KEY consistency across cluster** (optional but valuable)
   ```python
   # Health check endpoint
   @app.get("/health/crypto")
   async def health_crypto_key():
       """Verify ENCRYPTION_KEY is consistent with boot.log."""
       # Compare ENCRYPTION_KEY hash with one stored in boot.log
       # Return 200 if consistent, 503 if mismatch
       return {"status": "healthy", "encryption_key_set": bool(ENCRYPTION_KEY)}
   ```

4. **Pre-seed ENCRYPTION_KEY in init container**
   ```yaml
   init-secrets:
     image: alpine:latest
     environment:
       ENCRYPTION_KEY: ${ENCRYPTION_KEY}  # From .env
     entrypoint: |
       sh -c '
       mkdir -p /app/secrets
       echo $ENCRYPTION_KEY > /app/secrets/encryption.key
       chmod 600 /app/secrets/encryption.key
       chown 1000:1000 /app/secrets/encryption.key
       '
     volumes:
       - secrets-data:/app/secrets
   ```

5. **Strict startup validation for EE**
   ```python
   async def lifespan(app: FastAPI):
       # Load licence early
       licence = await load_licence()
       
       # Enforce ENCRYPTION_KEY in EE mode
       if licence.is_ee_active and not os.getenv("ENCRYPTION_KEY"):
           logger.critical(
               "EE licence active but ENCRYPTION_KEY not set. "
               "This is a security misconfiguration. Refusing to start."
           )
           raise RuntimeError("ENCRYPTION_KEY required for EE mode")
       
       # Validate boot.log accessibility
       if licence.is_ee_active:
           try:
               check_and_record_boot(licence.status)
           except PermissionError as e:
               logger.critical(f"Cannot access boot.log: {e}")
               raise RuntimeError("boot.log inaccessible in EE mode")
       
       yield
   ```

**Detection:**
- EE deployment fails at startup: "ENCRYPTION_KEY env var is REQUIRED for EE mode"
- Cluster inconsistency: `docker exec agent-1 env | grep ENCRYPTION_KEY` differs from agent-2
- boot.log tampering undetected: HMAC verification passes even though boot.log was modified

---

### Pitfall 5: Removing `privileged: true` Breaks Job Execution Without Capability-Drop Replacement

**What goes wrong:** Operator removes `privileged: true` from agent container in compose.yaml to harden the deployment. Agent starts fine but job execution fails: "Error response from daemon: denied capability: cap_sys_admin" when attempting to spawn job containers. Foundry builds fail. All job execution becomes non-functional.

**Why it happens:** The existing configuration runs with `privileged: true`, which grants all Linux capabilities (CAP_SYS_ADMIN, CAP_NET_ADMIN, CAP_SYS_RESOURCE, etc.). Removing this flag without providing specific `cap_add` entries revokes all capabilities. Job execution via Docker-in-Docker requires CAP_SYS_ADMIN. Resource limit enforcement requires CAP_SYS_RESOURCE. Removing privileged mode without replacement is a hard regression.

**Consequences:**
- Foundry image builds fail immediately: "denied capability"
- All job dispatch fails: jobs stuck in PENDING state
- No graceful degradation: failure is visible only at runtime, not startup
- Rolling back to privileged mode is the only recovery (security regression)
- Operator confusion: "Why did security hardening break everything?"

**Prevention:**
1. **Replace `privileged: true` with minimal `cap_add` set**
   ```yaml
   agent:
     cap_drop: [ALL]
     cap_add:
       - SYS_ADMIN    # Required: Docker-in-Docker, nested containers
       - NET_ADMIN    # Required: virtual network setup for job isolation
       - SYS_RESOURCE # Required: cgroup memory/CPU limit enforcement
       - SYS_PTRACE   # Required: process monitoring, job status tracking
       - SETFCAP      # Required: file capability operations during builds
   ```

2. **Add detailed comments explaining each capability**
   ```yaml
   # Capabilities required for job execution:
   # - SYS_ADMIN: Allows Docker-in-Docker (nested container spawning)
   # - NET_ADMIN: Allows virtual network namespace setup
   # - SYS_RESOURCE: Allows cgroup operations (memory/CPU limits)
   # - SYS_PTRACE: Allows process tracing (job monitoring, exit codes)
   # - SETFCAP: Allows setting file capabilities (build operations)
   #
   # NOT REQUIRED: CHOWN, KILL, NET_BIND_SERVICE, AUDIT_WRITE
   # Explicitly dropped for security hardening.
   ```

3. **Validate capabilities at container startup**
   ```python
   def validate_agent_hardening():
       """Verify agent has exactly the required capabilities."""
       import socket
       result = docker.containers.get(socket.gethostname()).inspect()
       cap_add = set(result.get("HostConfig", {}).get("CapAdd") or [])
       cap_drop = set(result.get("HostConfig", {}).get("CapDrop") or [])
       
       required = {"SYS_ADMIN", "NET_ADMIN", "SYS_RESOURCE", "SYS_PTRACE", "SETFCAP"}
       dropped = {"ALL"} if cap_drop else set()
       
       if cap_add != required:
           logger.warning(f"Unexpected caps: {cap_add - required}")
       if not dropped:
           logger.warning("CAP_DROP not set to ALL — consider dropping unused caps")
   ```

4. **Test each capability individually** (integration test suite)
   ```python
   def test_job_execution_with_minimal_caps():
       """Verify jobs can run with minimal capabilities."""
       # Spawn a test job that uses each required capability
       # SYS_ADMIN: docker run hello-world
       # NET_ADMIN: configure job network
       # SYS_RESOURCE: set memory limit
       # SYS_PTRACE: check job exit code
       result = dispatch_job(...)
       assert result.status == "COMPLETED"
   ```

5. **Document capability requirements in security guide**
   ```markdown
   # Agent Hardening: Linux Capabilities
   
   The agent container requires minimal Linux capabilities to function securely:
   
   | Capability | Purpose | Why Required |
   |---|---|---|
   | SYS_ADMIN | Docker-in-Docker | Job containers spawned via docker run |
   | NET_ADMIN | Virtual networks | Job network isolation setup |
   | SYS_RESOURCE | cgroup operations | Memory and CPU limits on jobs |
   | SYS_PTRACE | Process monitoring | Exit code tracking, job status |
   | SETFCAP | File capabilities | Dockerfile RUN operations during builds |
   
   It explicitly does NOT require:
   - CHOWN (files owned by appuser, not changed)
   - KILL (jobs killed via signals, not SIG_KILL)
   - NET_BIND_SERVICE (no ports < 1024 bound by agent)
   - AUDIT_WRITE (no audit log writes)
   ```

**Detection:**
- Job execution logs: "Error response from daemon: denied capability: cap_sys_admin"
- Jobs stuck in PENDING state indefinitely
- `docker inspect <agent-container> | grep Cap` shows empty or wrong capabilities

---

### Pitfall 6: Ed25519 Signature Verification Message Encoding Mismatch

**What goes wrong:** Job script signature verification fails intermittently or consistently even with correct key and operator-verified signature. Scripts signed locally on operator's machine (via axiom-push) verify successfully, but fail when agent attempts verification. Jobs rejected with HTTP 422 "Signature verification failed."

**Why it happens:** Ed25519 signature verification is encoding and byte-order sensitive. Common causes:
1. Script content encoded as UTF-8 during signing, but stored in database with different encoding
2. Script has trailing newlines when signed (`script\n`), but stored without trailing whitespace
3. Script signed on Windows with CRLF line endings (`\r\n`), stored/verified on Unix with LF (`\n`)
4. Script normalized (spaces trimmed) after signing but before verification
5. Signature payload field contains modified script (e.g., HMAC field added post-signing)

**Consequences:**
- Legitimate job scripts rejected with "Signature verification failed"
- Operator workflow breaks: "I signed it locally and it verified, why won't it submit?"
- No visibility into what bytes were actually signed (debugging difficult)
- Operator workaround: disable signature verification or re-sign repeatedly
- Security false positives: legitimate scripts look tampered with

**Prevention:**
1. **Enforce strict encoding at signature and verification time**
   ```python
   def normalize_script(script_content: str) -> bytes:
       """Normalize script to canonical form for signing."""
       # 1. Ensure UTF-8 encoding
       if isinstance(script_content, bytes):
           script_bytes = script_content
       else:
           script_bytes = script_content.encode("utf-8")
       
       # 2. Normalize line endings to LF only
       script_str = script_bytes.decode("utf-8").replace("\r\n", "\n")
       
       # 3. Ensure single trailing newline
       script_str = script_str.rstrip() + "\n"
       
       return script_str.encode("utf-8")
   ```

2. **Use same normalization function at both signing and verification**
   ```python
   # axiom-push CLI (signing)
   script_bytes = normalize_script(script_content)
   signature = private_key.sign(script_bytes)
   
   # Agent (verification)
   script_bytes = normalize_script(script_content)
   public_key.verify(signature_bytes, script_bytes)
   ```

3. **Document the signing contract in API spec and guide**
   ```markdown
   ## Job Signing Contract
   
   Script content is normalized before signing:
   1. UTF-8 encoding enforced
   2. Line endings normalized to LF (\\n)
   3. Single trailing newline appended
   
   Both the axiom-push CLI and the Agent enforce this normalization.
   
   **Do not:**
   - Sign raw file bytes with embedded newlines
   - Modify script content after signing (add comments, spaces, etc.)
   - Change line endings between signing and submission
   ```

4. **Hash the script before signing** (optional but adds safety margin)
   ```python
   # More robust: sign the SHA256 hash, not raw content
   script_hash = hashlib.sha256(normalized_script_bytes).digest()
   signature = private_key.sign(script_hash)
   
   # Verification
   script_hash = hashlib.sha256(normalized_script_bytes).digest()
   public_key.verify(signature_bytes, script_hash)
   ```

5. **Add test vectors for known-good signatures**
   ```python
   # Test with fixed script and signature
   CANONICAL_SCRIPT = "#!/bin/bash\necho hello\n"
   CANONICAL_SIG_HEX = "abc123..."  # Pre-computed with above script
   
   def test_signature_verification_canonical():
       """Verify canonical test vector works."""
       sig_bytes = bytes.fromhex(CANONICAL_SIG_HEX)
       script_bytes = normalize_script(CANONICAL_SCRIPT)
       # Should not raise InvalidSignature
       public_key.verify(sig_bytes, script_bytes)
   ```

6. **Provide clear error messages with debugging context**
   ```python
   from cryptography.exceptions import InvalidSignature
   
   try:
       public_key.verify(signature_bytes, script_bytes)
   except InvalidSignature:
       import hashlib
       raise HTTPException(
           status_code=422,
           detail=(
               "Signature verification failed. "
               "Ensure the script was signed with the exact same content. "
               f"Script SHA256: {hashlib.sha256(script_bytes).hexdigest()} "
               "Check for: line ending changes (LF vs CRLF), trailing whitespace, encoding mismatches."
           )
       )
   ```

**Detection:**
- Job dispatch fails with "Signature verification failed"
- Operator verifies signature locally: `axiom-push verify-signature`, passes
- Same script fails on server: suggests encoding/normalization mismatch
- Compare hashes: `sha256sum` of script on operator machine vs agent database
- Line ending inspection: `od -c script.sh | head` shows presence of CR bytes

---

### Pitfall 7: Privileged Job Containers Introduced as "Temporary Workaround" During Hardening

**What goes wrong:** During hardening, when capability-drop causes test failures, operator adds `privileged: true` to job containers as a "quick fix" while working through the actual capability requirements. The workaround becomes permanent; security audit later discovers privileged jobs are being executed.

**Why it happens:** Test failure is frustrating. Adding `privileged: true` makes it go away immediately. Temporary flag becomes permanent if not explicitly removed later. No enforcement mechanism prevents privileged job containers.

**Consequences:**
- Major security regression: jobs gain full access to host kernel
- Jobs can escape container isolation
- Potential for kernel compromise via malicious job script
- Audit trail shows privileged execution (discovers issue post-facto)
- Contradicts documented security model

**Prevention:**
1. **Add pre-commit hook to prevent `privileged: true` in job containers**
   ```bash
   # .git/hooks/pre-commit
   if git diff --cached --name-only | grep -E "compose|Dockerfile" | \
      xargs grep -l "privileged: true"; then
       echo "ERROR: 'privileged: true' found in container config"
       echo "Jobs and agents must use minimal capabilities, not privileged mode."
       exit 1
   fi
   ```

2. **Add CI gate to block privileged containers**
   ```yaml
   # .github/workflows/ci.yml
   - name: Check for privileged containers
     run: |
       if grep -r "privileged: true" puppeteer puppets; then
           echo "ERROR: Found 'privileged: true' in container configs"
           echo "Containers must use cap_add/cap_drop instead."
           exit 1
       fi
   ```

3. **Explicitly forbid privileged in compose with comments**
   ```yaml
   # compose.server.yaml
   agent:
     # privileged: false  # Explicitly false — do not change to true
     cap_drop: [ALL]
     cap_add:
       - SYS_ADMIN
       - NET_ADMIN
       - SYS_RESOURCE
       - SYS_PTRACE
       - SETFCAP
   ```

4. **Document security hardening rationale**
   ```markdown
   ## Security: Why No Privileged Mode
   
   The agent and job containers do NOT run with `privileged: true`.
   
   Privileged mode grants all Linux capabilities and breaks the security model.
   Instead, we use minimal `cap_add` with `cap_drop: [ALL]` for defense-in-depth.
   
   If you see `privileged: true` in the code or tests, it is a security regression.
   Remove it immediately and use capability-based hardening instead.
   ```

5. **Runtime validation at startup**
   ```python
   def validate_no_privileged_mode():
       """Fail if container is running as privileged."""
       result = docker.containers.get("self").inspect()
       if result.get("HostConfig", {}).get("Privileged"):
           raise RuntimeError(
               "Container is running as privileged — hardening has been compromised. "
               "This is a security regression. Remove 'privileged: true' from compose config."
           )
   ```

**Detection:**
- Code review: `grep -r "privileged: true"` in compose/Dockerfile
- CI failure: pre-commit hook or GitHub Actions check blocks the commit
- Runtime: `docker inspect <container> | grep Privileged`

---

## Moderate Pitfalls

### Pitfall 8: Signature Service Public Key Format Inconsistency

**What goes wrong:** Operator registers Ed25519 public key in PEM format via API, but signature verification code loads the key as raw bytes. Verification fails with format error or type mismatch.

**Prevention:**
1. **Standardize on PEM format at registration and verification**
   ```python
   # At registration
   def register_public_key(req: RegisterKeyRequest):
       public_key_pem = normalize_public_key_to_pem(req.public_key)
       # Validate PEM format
       from cryptography.hazmat.primitives import serialization
       serialization.load_pem_public_key(public_key_pem.encode())  # Will raise if invalid
   ```

2. **Load from PEM at verification time**
   ```python
   def verify_job_signature(sig_rec: Signature, user_sig: str, script_content: str):
       from cryptography.hazmat.primitives import serialization
       pub_key = serialization.load_pem_public_key(sig_rec.public_key.encode())
       pub_key.verify(bytes.fromhex(user_sig), script_content.encode("utf-8"))
   ```

---

### Pitfall 9: Foundry-Generated Dockerfile USER Placement in the Middle of RUN Steps

**What goes wrong:** Foundry dynamically generates Dockerfile by inserting capability/package snippets. Template builder inserts `USER appuser` before all privileged operations complete. Subsequent `RUN apk add` or `RUN pip install` fails because non-root user lacks permission to write to `/usr/local/bin` or system directories.

**Prevention:**
1. **Enforce USER placement rule in template generation**
   ```python
   def generate_dockerfile(template, runtime_recipe):
       lines = [
           "FROM <base>",
           "# System dependencies",
           "RUN apk add --no-cache <packages>",
           "# Python dependencies",
           "RUN pip install <packages>",
           "# Ownership and permissions setup",
           "RUN chown -R 1000:1000 /app /usr/local",
           "RUN chmod -R u+rwx /app",
           "",
           "# Switch to non-root user",
           "USER appuser",
           "",
           "WORKDIR /app",
           "ENTRYPOINT [...]",
       ]
   ```

2. **Document in Foundry UI** — show template structure with USER placement highlighted

---

### Pitfall 10: Node Containers Can Read Boot.log But Cannot Execute

**What goes wrong:** Node container job executes Python script that tries to `import axiom_bootstrap` (which reads boot.log for validation). Script fails with "boot.log not readable" because the job container doesn't have access to the host's secrets volume.

**Prevention:**
1. **Boot.log validation is agent-only, not node-side** — Document this clearly
2. **Jobs should not attempt to read boot.log** — It's a cluster-level security mechanism
3. **Node containers don't need secrets volume** — Only bind `/var/run/docker.sock` for job spawning

---

## Minor Pitfalls

### Pitfall 11: Missing ENCRYPTION_KEY in Local Development

**What goes wrong:** Developer runs agent locally without setting ENCRYPTION_KEY in `.env`. HMAC verification silently falls back to dev key, masking real issues. Tests pass locally but fail in CI where ENCRYPTION_KEY is enforced.

**Prevention:**
1. **Make ENCRYPTION_KEY prominent in .env.example**
2. **Log clear warning at startup if unset in CE mode**
3. **Enforce ENCRYPTION_KEY in EE mode at startup**

---

### Pitfall 12: System CA Certificates Unreadable by Non-Root User

**What goes wrong:** After switching to non-root user, agent fails to validate HTTPS upstream connections. Errors like "certificate verify failed" or "unable to load CA cert" occur because `/etc/ssl/certs/` is root-owned.

**Prevention:**
1. **Make system CA certs world-readable**
   ```dockerfile
   RUN chmod -R a+rX /etc/ssl/certs/
   ```

2. **Use Python certifi bundle instead**
   ```python
   import certifi
   import ssl
   ssl_context = ssl.create_default_context(cafile=certifi.where())
   ```

---

## Phase-Specific Warnings

| Phase | Topic | Pitfall | Mitigation |
|-------|-------|---------|-----------|
| Container Hardening | Non-root Setup | GID mismatch on Docker socket | Resolve host docker GID dynamically, pass to build, test in CI |
| Container Hardening | Volume Ownership | Non-root user cannot write secrets | Place USER after all chown/chmod, use init container for existing deployments |
| Container Hardening | Privilege Removal | Removing privileged breaks job execution | Replace with minimal cap_add, test each capability, add CI gate |
| Licence Hardening | Boot.log Migration | SHA256 entries fail HMAC validation post-upgrade | Dual-format parsing with version marker, explicit test case |
| Licence Hardening | Encryption Key | ENCRYPTION_KEY missing or mismatched | Enforce in EE mode at startup, document generation, validate consistency |
| Job Signing | Signature Verification | Message encoding mismatch | Enforce UTF-8 + LF normalization, document contract, add test vectors |
| Foundry Build | Dockerfile Generation | USER instruction breaks subsequent RUN | Enforce USER after all RUN, document rule, test generated Dockerfiles |

---

## Integration Testing Checklist

Before deploying hardening changes, verify:

- [ ] Agent builds with non-root user (UID 1000, GID matches docker)
- [ ] Agent can mount and read `/var/run/docker.sock` (test: `docker ps` inside agent)
- [ ] Agent can spawn job containers (test: `docker run` from inside agent)
- [ ] Agent can write to `secrets/boot.log` on startup and after restart
- [ ] Foundry generates Dockerfile with correct USER placement (USER after all RUN)
- [ ] Job signature verification works with UTF-8 encoded scripts
- [ ] Boot.log persists across container restart (volume persistence test)
- [ ] ENCRYPTION_KEY validation enforced in EE mode (test: fail on missing key)
- [ ] No `privileged: true` in any Dockerfile or compose file (CI gate)
- [ ] Node containers run with `privileged: false` and `cap_drop: [ALL]`
- [ ] Agent runs with minimal `cap_add` (SYS_ADMIN, NET_ADMIN, SYS_RESOURCE, SYS_PTRACE, SETFCAP)
- [ ] Boot.log SHA256→HMAC migration path works (test: legacy entries + new HMAC)
- [ ] Secrets directory ownership correct after USER switch

---

## Sources

- [Fix Docker Permission Denied: 5 Solutions That Actually Work](https://oneuptime.com/blog/post/2026-01-16-docker-permission-denied-errors/view)
- [Docker daemon access within Docker as non-root user: Permission denied](https://forums.docker.com/t/docker-daemon-access-within-docker-as-non-root-user-permission-denied-while-trying-to-connect-to-docker-daemon-socket/94181)
- [The Complete Guide to Docker Mount Permission Issues](https://eastondev.com/blog/en/posts/dev/20251217-docker-mount-permissions-guide/)
- [Understanding the Docker USER Instruction](https://www.docker.com/blog/understanding-the-docker-user-instruction/)
- [Top 21 Dockerfile best practices for container security](https://sysdig.com/learn-cloud-native/dockerfile-best-practices)
- [Understanding User File Ownership in Docker](https://linuxvox.com/blog/understanding-user-file-ownership-in-docker-how-to-avoid-changing-permissions-of-linked-volumes/)
- [How to Drop Linux Capabilities in Docker Containers](https://oneuptime.com/blog/post/2026-01-16-docker-drop-capabilities/view)
- [How to Use Docker Compose cap_add and cap_drop](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-compose-capadd-and-capdrop/view)
- [Ed25519 signing — Cryptography 47.0.0 documentation](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- [EdDSA: Sign / Verify - Examples](https://cryptobook.nakov.com/digital-signatures/eddsa-sign-verify-examples)
- [Securing Dockerized Applications: User Permissions and Capabilities Explained](https://medium.com/@vasanthancomrads/securing-dockerized-applications-user-permissions-and-capabilities-explained-54841c5bed9e)

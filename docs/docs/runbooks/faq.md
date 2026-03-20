# FAQ

This is the single searchable reference for known misconfigurations and operator how-to questions. If you do not know which component owns your problem, start here — each entry links to the deeper guide once you have identified the cause.

---

## Quick Reference

| Question | Section |
|----------|---------|
| Blueprint packages are not installed during Foundry builds | [Blueprint packages not installed](#blueprint-packages-are-not-installed-during-foundry-builds) |
| Node container fails to run jobs — RuntimeError: No container runtime found | [RuntimeError: No container runtime found](#node-container-fails-to-run-jobs-runtimeerror-no-container-runtime-found) |
| Node fails to enroll — Token payload missing 't' or 'ca' | [JOIN_TOKEN enrollment failure](#node-fails-to-enroll-token-payload-missing-t-or-ca) |
| Changing ADMIN_PASSWORD in .env has no effect | [ADMIN_PASSWORD has no effect](#changing-admin_password-in-env-has-no-effect) |
| How do I reset a node identity without re-enrolling? | [Reset node identity](#how-do-i-reset-a-node-identity-without-re-enrolling) |
| My scheduled job does not run at the expected local time | [Scheduled job UTC timezone](#my-scheduled-job-does-not-run-at-the-expected-local-time) |
| Can I submit jobs without Ed25519 signing? | [Ed25519 signing bypass](#can-i-submit-jobs-without-ed25519-signing) |
| Why does my node appear multiple times in the Nodes view? | [Duplicate node entries](#why-does-my-node-appear-multiple-times-in-the-nodes-view) |
| Why is my Foundry template stuck in STAGING status? | [Template stuck in STAGING](#why-is-my-foundry-template-stuck-in-staging-status) |
| Why does my node keep showing TAMPERED status? | [TAMPERED status](#why-does-my-node-keep-showing-tampered-status) |

---

### Blueprint packages are not installed during Foundry builds

Blueprint package lists must be structured as a dict with a `"python"` key — not a plain list. The Foundry service calls `packages.get("python", [])` internally. A plain list returns an empty result, silently skipping all package installations. The Docker build succeeds, but the node image has none of the expected packages installed.

```json
// Correct
{"python": ["requests", "numpy"]}

// Wrong — silently skips all packages
["requests", "numpy"]
```

See [Foundry → Blueprints](../feature-guides/foundry.md#blueprints) for the full blueprint format reference.

---

### Node container fails to run jobs — RuntimeError: No container runtime found

When an Axiom Node runs inside a Docker container (for example, a Foundry-built image deployed via Docker Compose), `EXECUTION_MODE` must be set to `direct`. In `auto` mode, the node tries to spawn Podman or Docker sub-containers. Inside an existing Docker container, this fails due to cgroup v2 conflicts — neither Podman nor Docker is available in a standard Docker-in-Docker setup. `direct` mode executes job scripts as Python subprocesses within the node process, without a container wrapper.

```yaml
# In node-compose.yaml environment section
EXECUTION_MODE: direct
```

If the node image was built by Foundry and the build itself is the problem, see [Foundry Troubleshooting → Build Failures](foundry.md#build-failures).

---

### Node fails to enroll — Token payload missing 't' or 'ca'

The `JOIN_TOKEN` is a base64-encoded JSON object — it is not a plain string or a JWT. It contains exactly two keys: `t` (the actual token) and `ca` (the Root CA PEM). A single trailing newline, a space, or a URL-encoding artefact in the value will corrupt the base64 decode and trigger the `Token payload missing 't' or 'ca'` error, aborting enrollment.

```json
// JOIN_TOKEN decodes to this structure (never construct manually):
{
  "t": "<actual_token_string>",
  "ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
}
```

Copy the token exactly as displayed in **Admin → Nodes → Generate Join Token**. Do not add quotes, newlines, or spaces. When setting it in a compose file, use a single-line value without shell quoting that would introduce escape sequences.

See [mTLS & Certificates → The JOIN_TOKEN](../security/mtls.md#the-join_token) for the full enrollment flow.

---

### Changing ADMIN_PASSWORD in .env has no effect

The `ADMIN_PASSWORD` environment variable is read only once — when the orchestrator starts for the first time and the `admin` user does not yet exist in the database. Once the admin account has been created, the env var is ignored on every subsequent start. The database password is the source of truth for all existing deployments.

```python
# Orchestrator startup logic (simplified):
# Only seeds if admin user does not exist
```

To change the admin password after first run, use **Admin → Users → admin → Reset Password** in the dashboard.

!!! warning
    Do not drop the database to reset the admin password. Dropping the database destroys all nodes, jobs, job definitions, templates, and audit history. Use the dashboard Reset Password flow instead.

---

### How do I reset a node identity without re-enrolling?

You cannot reset a node's identity without re-enrolling. The node identity is cryptographically bound to its client certificate — the certificate serial number is what the orchestrator uses to identify the node across restarts. To assign a fresh identity: stop the node container, delete `secrets/node-*.crt` and `secrets/node-*.key` from the secrets volume, and restart with a valid `JOIN_TOKEN`. The orchestrator registers it as a new node entry. The old Offline entry can be removed from **Nodes → [node] → Delete**.

See [mTLS & Certificates → Certificate Rotation](../security/mtls.md#certificate-rotation) for the full procedure.

---

### My scheduled job does not run at the expected local time

APScheduler (the orchestrator's scheduling engine) evaluates all cron expressions in UTC. There is no per-job timezone configuration — all jobs use the same UTC clock. A cron expression like `0 9 * * *` fires at 09:00 UTC regardless of the orchestrator server's local timezone or the operator's timezone.

!!! tip
    Use a UTC cron calculator to convert your intended local time before entering it in the cron field. For example: 09:00 BST (UTC+1) = `0 8 * * *`. 09:00 AEST (UTC+10) = `0 23 * * *` (previous day UTC).

See [Job Scheduling](../feature-guides/job-scheduling.md) for cron expression syntax and examples.

---

### Can I submit jobs without Ed25519 signing?

No. Signature verification is enforced at the node before any script is executed — it is not configurable. A job submitted without a valid Ed25519 signature is immediately rejected with status `SECURITY_REJECTED`. The node must cryptographically confirm that the script was produced by an authorised operator holding a registered private key before running it.

!!! danger
    There is no configuration flag, environment variable, or API option to disable signature verification. This is a security invariant — disabling it would allow any actor with API access to execute arbitrary code on nodes.

See [axiom-push CLI → Ed25519 Key Setup](../feature-guides/axiom-push.md#ed25519-key-setup) for how to generate a signing keypair and register the public key.

---

### Why does my node appear multiple times in the Nodes view?

Duplicate entries occur when the `secrets/` volume is recreated or the `node-*.crt` and `node-*.key` files inside it are deleted. On the next restart, the node generates a new UUID, creates fresh credentials, and enrolls as a new node — creating a second database entry. The original entry remains in the dashboard with an Offline status. To clean up, delete the Offline duplicate from **Nodes → [node] → Delete**. No operational data is lost by removing a stale Offline entry.

---

### Why is my Foundry template stuck in STAGING status?

A template in STAGING status means the Docker build completed successfully, but the post-build Smelt-Check smoke test (`python --version && pip --version`) failed inside the built image. The Python environment is not functional. Check orchestrator logs for `❌ Smelt-Check FAILED for <template_name>`, identify the cause — usually a mismatch between the base image OS family and the package manager (Alpine vs Debian) — fix the blueprint, and trigger a rebuild.

See [Foundry Troubleshooting → Smelt-Check Failures](foundry.md#smelt-check-failures) for full recovery steps.

---

### Why does my node keep showing TAMPERED status?

The zero-trust capability guard detected that the node reported a capability that is not present in its registered `expected_capabilities`. This happens when a tool is installed inside a running container after the template was built, when capability detection logic changes between node restarts, or when a node is redeployed from a different template than the one it was originally enrolled against. To investigate: run `docker exec <node_container> <capability_check_command>` to inspect the actual capabilities reported. To clear the flag: **Nodes → [node] → Clear Tamper**. If the additional capability is legitimate, rebuild the template to include it so future deployments pass the capability check without triggering TAMPERED.

# Node Troubleshooting

This guide helps operators diagnose and recover from node failures. Find the symptom that matches what you observe in the dashboard or container logs, then follow the numbered recovery steps.

!!! tip "A healthy startup looks like this"
    If you're unsure whether a node enrolled correctly, compare your container logs against this reference sequence:

    ```
    🚀 Environment Node Started (1)
    🔒 Secure Mode Active. Trust Root: /app/secrets/root_ca.crt
    [node-abc12345] 📜 Detected Enhanced Token. Bootstrapping Trust...
    [node-abc12345] No identity found. Enrolling with Server...
    [node-abc12345] ✅ Enrollment Successful! Certificate Saved.
    [node-abc12345] 💓 Heartbeat Thread Started
    [node-abc12345] Starting Work Loop...
    ```

    If you do not see `Enrollment Successful!` followed by `Heartbeat Thread Started`, the node did not complete enrollment.

## Quick Reference

| Symptom | Section |
|---------|---------|
| Container exits immediately at startup | [Node container exits immediately at startup](#node-container-exits-immediately-at-startup) |
| Enrollment Failed: Connection refused | [Enrollment Failed: Connection refused](#enrollment-failed-connection-refused) |
| Enrollment Failed: SSL CERTIFICATE_VERIFY_FAILED | [Enrollment Failed: SSL verification failed](#enrollment-failed-ssl-verification-failed) |
| Token payload missing 't' or 'ca' | [Token payload missing t or ca](#token-payload-missing-t-or-ca) |
| Node appears as duplicate entry in Nodes view | [Node appears as a duplicate in the dashboard](#node-appears-as-a-duplicate-in-the-dashboard) |
| Node goes Offline after container restart | [Node goes Offline after container restart](#node-goes-offline-after-container-restart) |
| Node stays Offline after cert rotation | [Node stays Offline after cert rotation](#node-stays-offline-after-cert-rotation) |
| Node shows TAMPERED status | [Node shows TAMPERED status](#node-shows-tampered-status) |
| Node gets HTTP 403 on work/pull and stops receiving jobs | [Node gets HTTP 403 and stops receiving jobs](#node-gets-http-403-and-stops-receiving-jobs) |
| Node receives concurrency_limit: 0 and processes no jobs | [Node receives concurrency 0 and processes no jobs](#node-receives-concurrency-0-and-processes-no-jobs) |

---

## Enrollment Failures

Enrollment failures happen during node startup, before the heartbeat thread starts. Check `docker logs <container-name>` immediately after starting the container — the failure reason is logged on the last few lines.

### Node container exits immediately at startup

The node process failed before completing enrollment. The three most common causes are a malformed `JOIN_TOKEN`, an unreachable orchestrator, or stale certificate files from a previous enrollment in the `secrets/` volume. The node logs the specific failure reason as `❌ Enrollment Failed: <exception>` before exiting.

**Recovery steps:**

1. Run `docker logs <container-name>` and read the last 10 lines — the exact error will identify which cause applies.
2. If the log shows `Connection refused`, see [Enrollment Failed: Connection refused](#enrollment-failed-connection-refused).
3. If the log shows `SSL: CERTIFICATE_VERIFY_FAILED`, see [Enrollment Failed: SSL verification failed](#enrollment-failed-ssl-verification-failed).
4. If the log shows `Token payload missing 't' or 'ca'`, see [Token payload missing t or ca](#token-payload-missing-t-or-ca).
5. If the `secrets/` volume contains old `node-*.crt` and `node-*.key` files from a prior deployment, stop the container, delete those files from the volume, and restart.

**Verify it worked:**

```bash
docker logs <container-name> | tail -15
```

Expected output: `[node-abc12345] Starting Work Loop...` (with no `❌ Enrollment Failed` line above it).

If the issue persists after these steps, run `docker logs <container-name> --follow` during the next restart attempt to capture the full error sequence and open an issue with the output.

---

### Enrollment Failed: Connection refused

The node cannot reach the orchestrator because `AGENT_URL` points to the wrong host or port. The enrollment request is refused at the TCP level before any TLS handshake occurs.

**Recovery steps:**

1. Check the `AGENT_URL` environment variable in your node's compose file or environment — it must point to the orchestrator host and port (default `8001`), e.g., `https://host.docker.internal:8001`.
2. Confirm the orchestrator container is running: `docker ps | grep puppeteer-agent`.
3. If running nodes inside Docker (Docker-in-Docker), verify `extra_hosts: host.docker.internal:172.17.0.1` is set so the node container can reach the host network.
4. Test connectivity from inside the node container: `docker exec <container-name> curl -k <AGENT_URL>/health`.

**Verify it worked:**

```bash
docker logs <container-name> | grep "Enrollment"
```

Expected output: `[node-abc12345] ✅ Enrollment Successful! Certificate Saved.`

If the issue persists after these steps, confirm that no firewall rule is blocking the port and that the orchestrator is listening on `0.0.0.0` (not just `127.0.0.1`).

---

### Enrollment Failed: SSL verification failed

The Root CA PEM embedded in the `JOIN_TOKEN` does not match the TLS certificate the orchestrator is currently presenting. This mismatch means the node cannot verify the server's identity and refuses to connect.

**Recovery steps:**

1. Regenerate the `JOIN_TOKEN` from the dashboard: **Admin → Nodes → Generate Join Token**.
2. Copy the new token exactly — including any leading/trailing characters that are part of the token — and replace the `JOIN_TOKEN` environment variable in your node's compose or environment config.
3. Stop and remove the existing node container, then start a fresh container with the updated token.

!!! warning "Do not regenerate tokens from a cached browser page"
    If the orchestrator's TLS certificate was recently changed (e.g., Caddy renewed it), old join tokens carry the old CA. Always generate a fresh token after any TLS configuration change.

For background on how the orchestrator's Root CA relates to the `JOIN_TOKEN`, see [mTLS guide → The JOIN_TOKEN](../security/mtls.md#the-join_token).

**Verify it worked:**

```bash
docker logs <container-name> | grep "Enrollment"
```

Expected output: `[node-abc12345] ✅ Enrollment Successful! Certificate Saved.`

If the issue persists after these steps, verify that the orchestrator's TLS certificate was not changed between token generation and node startup.

---

### Token payload missing t or ca

The `JOIN_TOKEN` is a legacy or malformed token. The Enhanced Token format is base64-encoded JSON with two keys: `t` (the actual token) and `ca` (the Root CA PEM). Any other format, including plain tokens from older versions, produces this error.

**Recovery steps:**

1. Regenerate the token from the dashboard: **Admin → Nodes → Generate Join Token**.
2. Copy the token exactly as displayed — do not truncate, URL-encode, or add any whitespace.

!!! warning "Token corruption is invisible"
    Even a trailing newline or extra space in the `JOIN_TOKEN` environment variable will corrupt the base64 decoding and produce this error. Shell variables set with `export JOIN_TOKEN=$(echo "...")` may append a newline. Use `JOIN_TOKEN=<value>` without command substitution when setting it directly.

**Verify it worked:**

```bash
docker logs <container-name> | grep "Enhanced Token"
```

Expected output: `[node-abc12345] 📜 Detected Enhanced Token. Bootstrapping Trust...`

If the issue persists after these steps, verify the token value by decoding it manually: `echo "<JOIN_TOKEN>" | base64 -d` should produce a JSON object with `t` and `ca` keys.

---

### Node appears as a duplicate in the dashboard

The `secrets/` volume was recreated or the `node-*.crt` and `node-*.key` files were deleted. When the node restarts without those files, `_load_or_generate_node_id()` generates a new UUID, the node enrolls with the orchestrator as a brand-new node, and the old entry remains in the Nodes view as an Offline entry.

**Recovery steps:**

1. Identify the current active node — it will be the one showing Online or a recent heartbeat timestamp in the Nodes view.
2. Delete the old Offline entry from the dashboard: **Nodes → [old node row] → Delete**.
3. To prevent this in future: mount the `secrets/` directory on persistent storage so cert files survive container restarts.

!!! tip "Both entries are safe to have"
    The duplicate entry does not affect job dispatch or security. The old node is simply Offline with a stale entry. Deleting it is cosmetic — no jobs are lost.

For more on node identity persistence, see [FAQ → Why does my node appear multiple times in the dashboard?](faq.md#why-does-my-node-appear-multiple-times-in-the-dashboard).

**Verify it worked:**

```bash
docker logs <container-name> | grep "identity"
```

Expected output: `[node-abc12345] No identity found. Enrolling with Server...` (for a fresh enrollment) or `[node-abc12345] Loaded existing identity: node-abc12345` (if cert files are present and reused).

If the issue persists after these steps, check that the `secrets/` directory is properly mounted and that the node process has write access to it.

---

## Heartbeat Loss

Heartbeat loss means the node was enrolled and running, but the orchestrator is no longer receiving regular heartbeats from it. The node status transitions to Offline after the heartbeat interval expires.

### Node goes Offline after container restart

The heartbeat thread cannot locate the node's certificate files after a container restart. The thread loops waiting for the cert files — if the `secrets/` volume is slow to mount or was not preserved between restarts, the thread never progresses and no heartbeat is sent.

**Recovery steps:**

1. Inspect the node container logs: `docker logs <container-name> | grep Heartbeat` — look for repeated `[Heartbeat] Failed: <exception>` lines.
2. Verify the `secrets/` volume is mounted and accessible: `docker exec <container-name> ls /app/secrets/` — you should see `node-*.crt` and `node-*.key` files.
3. If the cert files are missing (volume was lost or not mounted), re-enroll: stop the container, ensure the `secrets/` path in your compose file points to persistent storage, and restart.
4. If cert files are present but the heartbeat still fails, check that the orchestrator is reachable from within the node container: `docker exec <container-name> curl -k <AGENT_URL>/health`.

**Verify it worked:**

```bash
docker logs <container-name> | grep "Heartbeat Thread Started"
```

Expected output: `[node-abc12345] 💓 Heartbeat Thread Started`

If the issue persists after these steps, check orchestrator logs for any rejection of the heartbeat request.

---

### Node stays Offline after cert rotation

After rotating the node's certificate, the old revoked certificate is still present in the `secrets/` volume. When the node restarts, `_load_or_generate_node_id()` finds the existing `node-*.crt` file and reuses the old (now revoked) certificate. The orchestrator's `/work/pull` endpoint returns 403 for revoked certs, so the node never receives jobs and eventually shows as Offline.

**Recovery steps:**

1. Stop the node container.
2. Delete the old certificate files from the `secrets/` volume: remove `node-*.crt` and `node-*.key`.
3. Generate a new `JOIN_TOKEN` from the dashboard: **Admin → Nodes → Generate Join Token**.
4. Update the `JOIN_TOKEN` environment variable with the new token.
5. Start the node container — it will enroll fresh and receive a new certificate.

For the full certificate rotation procedure, see [mTLS guide → Certificate Rotation](../security/mtls.md#certificate-rotation).

**Verify it worked:**

```bash
docker logs <container-name> | grep -E "Enrollment|Heartbeat Thread"
```

Expected output: `[node-abc12345] ✅ Enrollment Successful! Certificate Saved.` followed by `[node-abc12345] 💓 Heartbeat Thread Started`.

If the issue persists after these steps, confirm that the `secrets/` directory was fully cleared before restart — both `.crt` and `.key` files must be removed.

---

### Node shows TAMPERED status

The zero-trust capability guard in the orchestrator detected that the node reported a capability not present in the `expected_capabilities` recorded at enrollment time. This indicates the container environment changed after the image was built — for example, a tool was installed inside the running container, or a package version changed between container rebuilds.

**Recovery steps:**

1. Investigate what changed in the node's environment: `docker exec <container-name> pip list` or equivalent to compare the current environment against the template's declared capabilities.
2. If the new capability is legitimate (deliberate change), rebuild the template via the Foundry view to capture the updated capability set, then redeploy the node from the rebuilt image.
3. If the tamper flag was triggered in error (e.g., a transient detection issue), clear it from the dashboard: **Nodes → [node] → Clear Tamper**.

!!! warning "Do not clear tamper without investigating"
    The TAMPERED status is a security signal. Clearing it without understanding the cause masks a potential supply-chain or container escape issue. Always confirm what changed before clearing.

**Verify it worked:**

```bash
docker ps | grep <container-name>
```

Expected output: the node container is running, and the Nodes view in the dashboard shows the node's status badge as Online (not TAMPERED).

If the issue persists after these steps, review the orchestrator logs for `🚨 TAMPER DETECTED on node <id>` and compare the capability list in the log entry against the expected capabilities in the template.

---

## Certificate Errors

Certificate errors occur after successful enrollment. The node has a valid client certificate but the certificate has been revoked or the associated node template has entered a blocked lifecycle state.

### Node gets HTTP 403 and stops receiving jobs

The node's client certificate has been revoked in the orchestrator's `RevokedCert` table. The `/work/pull` endpoint checks the certificate serial number against this table and returns 403 for any match, regardless of whether the certificate is otherwise valid.

**Recovery steps:**

1. Confirm the revocation: check the dashboard **Nodes** view — a revoked node typically shows a Revoked badge or no heartbeat activity.
2. If the revocation was intentional: the node must be re-enrolled. Stop the container, delete `secrets/node-*.crt` and `secrets/node-*.key`, generate a new `JOIN_TOKEN`, and restart.
3. The new enrollment produces a fresh certificate with a new serial number that is not in the `RevokedCert` table.

!!! warning "Certificate revocation is permanent and cannot be undone"
    Once a certificate serial number is added to the `RevokedCert` table, it cannot be removed. There is no "un-revoke" operation. If the revocation was accidental, the only path forward is a fresh enrollment with a new certificate. Before revoking a node, confirm the node identity in the Nodes view to avoid revoking the wrong node.

For the full revocation procedure and CRL details, see [mTLS guide → Certificate Revocation](../security/mtls.md#certificate-revocation).

**Verify it worked:**

```bash
docker logs <container-name> | grep -E "Enrollment Successful|Work Loop"
```

Expected output: `[node-abc12345] ✅ Enrollment Successful! Certificate Saved.` followed by `[node-abc12345] Starting Work Loop...`

If the issue persists after these steps, verify the `secrets/` directory was fully cleared of old cert files before restarting.

---

### Node receives concurrency 0 and processes no jobs

The orchestrator is sending `concurrency_limit: 0` in the node's configuration response. This is a deliberate soft-block — the orchestrator halts job dispatch to a node without returning a hard 403 error. It occurs when the node's associated template is in a REVOKED lifecycle state, or when the node itself has TAMPERED status.

**Recovery steps:**

1. Check the node's template lifecycle state: go to the **Templates** tab in the Foundry view and find the template associated with this node. If the template shows a REVOKED status, the node will not receive jobs.
2. If the template is REVOKED: rebuild the template with a valid configuration, or assign the node a different active template.
3. If the template is not REVOKED: check whether the node has TAMPERED status in the Nodes view and resolve it using the steps in [Node shows TAMPERED status](#node-shows-tampered-status).

!!! tip "Check both template status and node status"
    A node can receive `concurrency_limit: 0` from either condition independently. The Nodes view shows node-level status (including TAMPERED). The Foundry Templates view shows template-level lifecycle state. Check both.

**Verify it worked:**

```bash
docker logs <container-name> | grep -i "concurrency\|work loop\|job"
```

Expected output: the node logs show job assignments being received and processed, with no `concurrency_limit: 0` in the work response.

If the issue persists after these steps, check the orchestrator logs for the specific condition causing the zero concurrency response — it will indicate whether the cause is template lifecycle state or node tamper status.

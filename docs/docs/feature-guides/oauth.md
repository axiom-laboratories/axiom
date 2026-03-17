# OAuth & Authentication

Master of Puppets uses JWT-based authentication with RFC 8628 device flow for CLI tools and API keys for automation.

---

## Authentication Methods

Three authentication methods are supported:

| Method | Best for | Obtained via |
|--------|----------|--------------|
| Password login | Dashboard users | Login page (`/login`) |
| Device flow (OAuth 2.0) | CLI tools, `mop-push` | `POST /auth/device` + browser approval |
| API key | Automation, scripts, CI pipelines | **My Account** → **API Keys** → **Create** |

All three methods return or carry a JWT that must be supplied as a `Bearer` token in the `Authorization` header.

---

## Device Flow (OAuth 2.0)

The OAuth 2.0 Device Authorization Grant (RFC 8628) allows tools without a browser — like `mop-push` — to authenticate without a redirect URI. The flow works by having the user approve the request in a browser session while the tool polls for the result.

**Why MoP uses device flow:** CLI tools cannot host a redirect URI. The device flow separates the user approval step (done in a browser) from the tool waiting for the token (done by polling). No callback server is needed on the client machine.

### Flow overview

1. The CLI requests a `device_code` and `user_code` from `POST /auth/device`.
2. The CLI displays the `user_code` and the `verification_uri` to the operator.
3. The operator visits the `verification_uri` in a browser and enters the `user_code`.
4. An admin (or the same user if they have permission) approves the request at the approval page.
5. The CLI polls `POST /auth/device/token` every 5 seconds until a JWT is returned.

**Constants:**

| Parameter | Value |
|-----------|-------|
| Authorization window | 300 seconds (5 minutes) |
| Poll interval | 5 seconds |

!!! warning "Device codes are not persisted"
    Device authorization codes are stored in memory and are not persisted across server restarts. If the server restarts during the 5-minute authorization window, the login flow must be restarted from step 1.

For step-by-step `mop-push` login instructions, see the [mop-push CLI guide](mop-push.md).

---

## Token Lifecycle

All JWTs issued by MoP share the same structure and expiry rules.

**Token fields:**

| Field | Description |
|-------|-------------|
| `sub` | Username (string) |
| `role` | User role: `admin`, `operator`, or `viewer` |
| `tv` | Token version — used for forced invalidation (see below) |
| `exp` | Expiry timestamp (Unix epoch) |
| `type` | Present for non-password tokens: `"device_flow"` or `"service_principal"` |
| `sp_id` | Present on service principal tokens: the service principal's UUID |

**Default expiry:** 24 hours from the time of issuance.

### Forced invalidation

When a user's password is changed — either by the user via **My Account** or by an admin — all existing tokens for that user are immediately rejected.

The JWT includes a `tv` (token version) field. When the server validates a token, it checks that the `tv` value matches the user's current `token_version` in the database. Any token with a mismatched `tv` is rejected instantly, regardless of the token's `exp` claim. There is no need to wait for token expiry.

**To invalidate all sessions for a user:**

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  https://<YOUR_HOST>/admin/users/<USERNAME>/reset-password \
  -H "Content-Type: application/json" \
  -d '{"new_password": "<NEW_PASSWORD>"}'
```

This increments the user's `token_version` and immediately invalidates all prior tokens for that user.

---

## API Keys

API keys are long-lived bearer tokens prefixed with `mop_`. They are created in the **My Account** section of the dashboard.

**Creating an API key:** Navigate to **My Account** → **API Keys** → **Create**. Give the key a descriptive name. The full key value is shown once at creation time — copy it immediately.

**Using an API key:**

```bash
curl -H "Authorization: Bearer mop_<YOUR_API_KEY>" \
  https://<YOUR_HOST>/api/nodes
```

!!! warning "API key permissions"
    API keys grant the same access as the owning user's role. The `permissions` field is reserved for future per-key permission scoping — per-key permission restriction is not currently enforced. If you need to restrict access, create a dedicated user account with the `viewer` or `operator` role and generate an API key for that account.

**Revoking an API key:** Navigate to **My Account** → **API Keys** and click **Revoke** next to the key. Revocation is immediate.

---

## Service Principal Tokens

Service principals are machine identities — not human users. They are documented fully in the [RBAC guide](rbac.md). To obtain a token for a service principal:

```bash
curl -X POST \
  -u "<SP_CLIENT_ID>:<SP_CLIENT_SECRET>" \
  https://<YOUR_HOST>/auth/service-principals/<SP_ID>/token
```

The response contains a JWT with `"type": "service_principal"` and the `sp_id` field set to the service principal's UUID.

**Secret rotation:**

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  https://<YOUR_HOST>/auth/service-principals/<SP_ID>/rotate
```

!!! danger "Secret shown once"
    The new secret is returned in the rotation response and cannot be retrieved again. Store it immediately in your secrets manager. The old secret is invalidated at the moment of rotation.

---

## CI/CD Integration

Two approaches are available for pipeline automation. Both use `<PLACEHOLDER>` values — replace them with your actual credentials stored as CI secrets.

### Approach A: API key (simpler)

Suitable for single-team pipelines where a single operator-level identity is sufficient.

1. Create an API key in the dashboard: **My Account** → **API Keys** → **Create**.
2. Store the key as a CI secret (e.g. `MOP_API_KEY` in GitHub Actions secrets).
3. Use the key directly in pipeline steps:

```bash
curl -H "Authorization: Bearer mop_<MOP_API_KEY>" \
  https://<YOUR_HOST>/api/jobs/push \
  -H "Content-Type: application/json" \
  -d @job_payload.json
```

Or with `mop-push`:

```bash
MOP_API_KEY=mop_<MOP_API_KEY> mop-push push --script my_job.py
```

### Approach B: Service principal (recommended for teams)

Suitable when multiple pipelines or teams need isolated identities with independent revocation.

1. Create a service principal: **Admin** → **Service Principals** → **Create**.
2. Set the role to `operator` (not `admin`) — follow the principle of least privilege.
3. Store `client_id` and `client_secret` as CI secrets.
4. Request a token at the start of each pipeline run and use it for the duration:

```bash
# Obtain a token
TOKEN=$(curl -s -X POST \
  -u "<SP_CLIENT_ID>:<SP_CLIENT_SECRET>" \
  https://<YOUR_HOST>/auth/service-principals/<SP_ID>/token \
  | jq -r '.access_token')

# Use the token
curl -H "Authorization: Bearer $TOKEN" \
  https://<YOUR_HOST>/api/nodes
```

!!! tip "Set an expiry and rotate on schedule"
    Service principals support an `expires_at` field set at creation time. Configure a rotation schedule in your CI system to refresh the secret before it expires. See the [RBAC guide](rbac.md) for the full service principal management reference.

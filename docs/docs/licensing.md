# Licensing

Axiom is distributed under an open-core model.

## Editions

| Edition | Distribution | EE Features |
|---------|-------------|-------------|
| **Community Edition (CE)** | Open source — MIT licence | No |
| **Enterprise Edition (EE)** | Commercial — private wheel | Yes |

CE and EE share the same agent service binary. EE features are enabled at runtime
by a valid `AXIOM_LICENCE_KEY` environment variable.

## Setting your licence key

Add the licence key to your environment before starting the agent service:

```env
AXIOM_LICENCE_KEY=<your-key>
```

With Docker Compose, add it to your `secrets.env` or pass it via the `environment:` block:

```yaml
environment:
  AXIOM_LICENCE_KEY: "${AXIOM_LICENCE_KEY}"
```

## Validation

Licence validation is **offline** — no network call is made. The key is an
Ed25519-signed payload containing your `customer_id`, an expiry timestamp (`exp`),
and the list of enabled `features`. The public key used to verify the signature is
compiled into the EE binary.

Validation runs once at startup. A restart is required to pick up a new or renewed key.

## Expiry behaviour

| Scenario | Result |
|----------|--------|
| Valid key, not expired | EE features enabled |
| Valid key, expired | CE mode — `GET /api/features` returns all false |
| Invalid or tampered key | CE mode — warning logged at startup |
| No key set | CE mode — info logged at startup |

The server always starts regardless of licence state — EE features are simply absent
when the key is missing or invalid.

## Key rotation

Licence key rotation requires a new EE wheel release containing the updated public key,
plus a rolling deployment. Contact Axiom Labs for key renewal.

## Checking your licence

The `GET /api/licence` endpoint (authenticated) returns your current licence state:

```json
{
  "edition": "enterprise",
  "customer_id": "acme-corp",
  "expires": "2027-03-20T00:00:00+00:00",
  "features": ["foundry", "rbac", "webhooks", "triggers", "audit"]
}
```

In CE mode it returns `{"edition": "community"}`.

The dashboard sidebar also shows a **CE** or **EE** badge for at-a-glance visibility.

### Checking active feature flags

To see which EE features are currently active, call `GET /api/features` (no authentication required):

```json
{
  "audit": true,
  "foundry": true,
  "webhooks": true,
  "triggers": true,
  "rbac": true,
  "resource_limits": true,
  "service_principals": true,
  "api_keys": true,
  "executions": true
}
```

In CE mode (or with an expired or missing key), all values return `false`.

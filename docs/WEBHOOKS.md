# Master of Puppets — Outbound Webhooks

Master of Puppets (MOP) can push real-time event notifications to your external systems via HTTP POST requests. All webhooks are signed using HMAC-SHA256 to ensure authenticity and integrity.

## Event Types

| Event | Trigger Description |
|-------|---------------------|
| `job:completed` | A job has finished successfully (Exit Code 0). |
| `job:failed` | A job has failed on a node. |
| `job:dead_letter` | A job has failed and exhausted all configured retries. |
| `job:security_rejected` | A job was rejected by a node's capability guard. |
| `alert:new` | A system-wide alert (Node Offline, Tamper Detected, etc.) has been raised. |

## Payload Structure

Every webhook POST request contains a JSON body with the following top-level fields:

```json
{
  "event": "alert:new",
  "timestamp": "2026-03-06T12:00:00Z",
  "data": {
    "id": 42,
    "severity": "CRITICAL",
    "message": "Node infra-01 is offline",
    "resource_id": "infra-01"
  }
}
```

## Security & Verification

MOP includes an `X-MOP-Signature` header in every request. Your receiver **must** verify this signature using the secret generated when you registered the webhook.

### Verification Steps

1.  **Extract Header**: Get the value of `X-MOP-Signature` (e.g., `sha256=abc...`).
2.  **Calculate HMAC**: Compute an HMAC-SHA256 hash using your webhook secret as the key and the **raw request body** as the message.
3.  **Compare**: Use a constant-time comparison (like `hmac.compare_digest`) to compare your calculated hash with the one from the header.

### Reference Implementation (Python)

See `examples/webhook_receiver.py` for a complete, functional FastAPI example.

```python
import hmac
import hashlib

def verify(raw_body, signature_header, secret):
    received_sig = signature_header.replace("sha256=", "")
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received_sig, expected_sig)
```

## Testing Your Webhooks

1.  **Local Development**: Use a tool like [ngrok](https://ngrok.com/) to expose your local receiver to the internet.
2.  **Registration**: Register your ngrok URL in the MOP Dashboard under **System > Webhooks**.
3.  **Triggering**:
    *   To trigger an `alert:new` event, you can stop a node service and wait for the watchdog to detect it.
    *   To trigger a `job:completed` event, dispatch a simple "Hello World" job to any online node.

# API Reference

Full REST API for Axiom. All endpoints require JWT authentication
except node-facing endpoints (enroll, work/pull, heartbeat) which use mTLS.

## Workflows API

Workflow endpoints enable CRUD operations on DAG-structured job workflows, execution lifecycle management, and webhook-based triggering. All endpoints are authenticated (JWT) except node-facing endpoints.

### Create, Read, Update, Delete

**POST /api/workflows** — Create a new workflow

Create a workflow by specifying the DAG structure (steps, edges), optional parameters for parameterization, and an optional cron schedule for automated triggering.

Key fields:
- `name` (string, required) — workflow name
- `definition` (object, required) — DAG structure:
  - `steps` (array) — ordered list of step definitions
  - `edges` (array) — connections between steps (from_step_id to to_step_id)
  - `parameters` (array, optional) — runtime parameters with defaults
- `schedule_cron` (string, optional) — cron expression for automated runs

**Example: Data Processing Pipeline with Conditional Gate**

```json
{
  "name": "Data Pipeline with Conditional Processing",
  "definition": {
    "steps": [
      {
        "step_id": "0",
        "node_type": "SCRIPT",
        "job_definition_id": "job-extract-001"
      },
      {
        "step_id": "1",
        "node_type": "SCRIPT",
        "job_definition_id": "job-validate-001"
      },
      {
        "step_id": "2",
        "node_type": "IF_GATE",
        "config": {
          "conditions": [
            {
              "path": "status",
              "operator": "equals",
              "value": "PASS"
            }
          ]
        }
      },
      {
        "step_id": "3",
        "node_type": "SCRIPT",
        "job_definition_id": "job-transform-001"
      },
      {
        "step_id": "4",
        "node_type": "SCRIPT",
        "job_definition_id": "job-load-001"
      },
      {
        "step_id": "5",
        "node_type": "SCRIPT",
        "job_definition_id": "job-rollback-001"
      }
    ],
    "edges": [
      { "from_step_id": "0", "to_step_id": "1" },
      { "from_step_id": "1", "to_step_id": "2" },
      { "from_step_id": "2", "to_step_id": "3" },
      { "from_step_id": "2", "to_step_id": "5" },
      { "from_step_id": "3", "to_step_id": "4" }
    ],
    "parameters": [
      {
        "name": "target_environment",
        "type": "string",
        "default_value": "production"
      }
    ]
  },
  "schedule_cron": "0 2 * * *"
}
```

**Explanation:** This workflow extracts data → validates it → branches on an IF gate. If validation passes, transform and load the data. If validation fails, execute a rollback. The workflow accepts a `target_environment` parameter injected into jobs as `WORKFLOW_PARAM_target_environment`. The cron expression schedules the workflow to run daily at 2 AM.

**GET /api/workflows** — List all workflows (paginated)

List all defined workflows with optional pagination. Returns workflow metadata only; run history is retrieved separately.

**GET /api/workflows/{workflow_id}** — Get workflow details

Retrieve the full definition of a single workflow including steps, edges, and parameters.

**PATCH /api/workflows/{workflow_id}** — Update workflow definition

Update the workflow's steps, edges, parameters, or cron schedule. Changes do not affect in-flight runs.

**DELETE /api/workflows/{workflow_id}** — Delete workflow

Delete a workflow and all associated webhooks. Deletion is blocked if active runs exist.

### Trigger and Monitor Runs

**POST /api/workflow-runs** — Manually trigger a workflow run

Manually start a workflow execution. Pass runtime parameter values to override defaults. Request body:

```json
{
  "workflow_id": "workflow-123",
  "parameters": {
    "target_environment": "staging"
  }
}
```

Returns a `WorkflowRunResponse` with a new `run_id` and initial status `PENDING`.

**GET /api/workflows/{workflow_id}/runs** — List runs for a workflow (paginated)

Retrieve all runs for a workflow with pagination. Each run includes trigger type (CRON, WEBHOOK, MANUAL), timestamps, and status.

**GET /api/workflows/{workflow_id}/runs/{run_id}** — Get run details

Retrieve the full status of a single workflow run, including all step statuses and current DAG position. Use this to monitor execution progress.

**DELETE /api/workflows/{workflow_id}/runs/{run_id}** — Cancel a running workflow

Cancel a workflow run in progress. Aborts all `ASSIGNED` and `RUNNING` steps; marks all `PENDING` steps as `CANCELLED`. Returns updated `WorkflowRunResponse`.

### Webhook Triggers

**POST /api/workflows/{workflow_id}/webhooks** — Create a webhook endpoint

Create a webhook trigger for a workflow. The webhook secret is revealed only once in the response; store it securely.

Response:

```json
{
  "webhook_id": "webhook-123",
  "secret": "whsec_ABC123XYZ",
  "description": "External monitoring system trigger"
}
```

**Important:** The secret is a one-time reveal. If lost, delete and recreate the webhook.

**GET /api/workflows/{workflow_id}/webhooks** — List webhooks

List all webhooks registered for a workflow.

**DELETE /api/workflows/{webhook_id}** — Delete a webhook

Revoke a webhook trigger and prevent any further webhook-based runs.

**POST /api/webhooks/{webhook_id}/trigger** — Trigger a workflow via webhook

External systems call this endpoint to trigger a workflow run. The request must include an HMAC-SHA256 signature in the X-Webhook-Signature header for security validation.

Request headers:
- `X-Webhook-Signature` — HMAC-SHA256(secret, request_body + timestamp)
- `X-Webhook-Timestamp` — Unix timestamp (seconds)
- `X-Webhook-Nonce` — Unique request identifier (24-hour dedup window)

Request body (application/json):

```json
{
  "parameters": {
    "target_environment": "production"
  }
}
```

Returns 202 Accepted if signature is valid. Signature validation is constant-time (timing-attack resistant).

### Webhook Security

Webhook security uses HMAC-SHA256 signatures to prevent spoofing. External systems must sign each request.

**Signing mechanism:**

1. Create a message by concatenating the raw request body (JSON) and the Unix timestamp: `message = request_body + timestamp`
2. Compute HMAC-SHA256 using the webhook secret: `signature = hex(HMAC-SHA256(secret.encode(), message.encode()))`
3. Send the signature in the X-Webhook-Signature header

**Validation checks performed by the server:**

- Signature matches HMAC-SHA256(secret, request_body + timestamp)
- Timestamp is within ±5 minutes of server time (clock skew tolerance)
- Nonce has not been seen in the last 24 hours (replay protection)

**Python Example:**

```python
import hmac
import hashlib
import time
import requests

# From webhook creation response
secret = "whsec_ABC123XYZ"
webhook_url = "https://api.axiom.com/api/webhooks/webhook-123/trigger"

# Prepare request
timestamp = str(int(time.time()))
payload = '{"parameters": {"env": "prod"}}'
message = payload + timestamp

# Sign request
signature = hmac.new(
    secret.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Send webhook trigger
headers = {
    'X-Webhook-Signature': signature,
    'X-Webhook-Timestamp': timestamp,
    'X-Webhook-Nonce': 'unique-request-id-12345'
}
response = requests.post(
    webhook_url,
    json={"parameters": {"target_environment": "production"}},
    headers=headers
)

# Check response
if response.status_code == 202:
    print("Workflow triggered successfully")
else:
    print(f"Webhook trigger failed: {response.status_code}")
```

### Response Format

All endpoints return JSON responses with structured format.

**Success responses (2xx):**

```json
{
  "id": "workflow-123",
  "name": "Data Pipeline",
  "status": "COMPLETED",
  "created_at": "2026-04-16T10:30:00Z",
  "updated_at": "2026-04-16T10:35:00Z"
}
```

**Error responses (4xx/5xx):**

```json
{
  "error": "Workflow not found"
}
```

Status codes:
- `200 OK` — Successful GET/PATCH/POST
- `201 Created` — Successful POST creating a new resource
- `202 Accepted` — Webhook trigger accepted asynchronously
- `204 No Content` — Successful DELETE
- `400 Bad Request` — Invalid request body or validation error
- `401 Unauthorized` — Missing or invalid JWT token
- `403 Forbidden` — Insufficient permissions for the operation
- `404 Not Found` — Workflow, run, or webhook not found
- `409 Conflict` — Deletion blocked (active runs exist) or other conflict
- `500 Internal Server Error` — Server error

<swagger-ui src="openapi.json" validatorUrl="none"/>

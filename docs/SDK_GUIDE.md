# MOP Python SDK Guide

The `mop_sdk` is a lightweight Python library for orchestrating the Master of Puppets platform.

## Installation

```bash
# Clone the repository and add mop_sdk to your path or install locally
pip install httpx cryptography pydantic
```

## Quickstart

### 1. Initialize Client
You can authenticate using either a Service Principal API Key or a standard User account.

```python
from mop_sdk import MOPClient

# Option A: Service Principal (Recommended for CI/CD)
client = MOPClient(base_url="https://mop.local", api_key="mop_...")

# Option B: User Login
client = MOPClient(base_url="https://mop.local", username="admin", password="...")
```

### 2. Submit a Signed Python Job
The SDK handles script signing automatically if you provide a path to your Ed25519 private key.

```python
script = """
print("Hello from the SDK!")
import os
print(f"Directory: {os.getcwd()}")
"""

job = client.submit_python_job(
    script=script,
    private_key_path="./my_signing_key.pem",
    tags=["linux", "prod"]
)

print(f"Created job: {job['guid']}")
```

### 3. Wait for Results
Use the built-in polling helper to wait for a job to finish.

```python
result = client.wait_for_job(job['guid'], timeout=60)
print(f"Job Status: {result['status']}")
```

### 4. Fire Automation Triggers
If you have a headless trigger configured, you can fire it with its dedicated key.

```python
client.fire_trigger(slug="deploy-app", trigger_key="trg_...")
```

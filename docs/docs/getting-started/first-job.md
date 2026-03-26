# Your First Job

Jobs are Python scripts signed with an Ed25519 private key. The node verifies the signature before executing. This guide walks through generating a signing key, registering the public key, and dispatching your first job via the dashboard.

---

## Step 1: Generate a signing keypair

```bash
openssl genpkey -algorithm ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out verification.key
```

!!! warning "Keep your private key safe"
    Never commit `signing.key` to git. Add it to `.gitignore` immediately. In production, store it in a secrets manager (Vault, AWS Secrets Manager, etc.) rather than on disk.

---

## Step 2: Register the public key in the dashboard

1. Go to **Signatures** in the dashboard sidebar
2. Click **Add Signature Key**
3. Paste the contents of `verification.key` into the field
4. Give it a descriptive name (e.g., `dev-operator-key`)
5. Click **Save**
6. Note the **Key ID** displayed — you will need to select this key when submitting jobs

!!! danger "Register before dispatching"
    Job creation fails with a `422` signature validation error if no public key is registered. **You must complete this step before proceeding to job dispatch.**

---

## Step 3: Write and sign a test script

Create `hello.py`:

```python
print("Hello from Axiom!")
import platform
print(f"Running on {platform.node()} ({platform.system()})")
```

Sign it with your private key and base64-encode the signature:

```bash
# Sign the script
openssl pkeyutl -sign -inkey signing.key -out hello.py.sig -rawin -in hello.py

# Base64-encode the signature for the dashboard form
base64 -w0 hello.py.sig > hello.py.sig.b64
```

!!! tip "axiom-push automates this"
    The `axiom-push` CLI handles signing and submission in one command — no manual openssl steps required. See the [axiom-push CLI guide](../feature-guides/axiom-push.md) for details. The manual method is shown here to make the signing mechanics visible.

---

!!! danger "Register your signing key first"
    Complete Steps 1 and 2 before attempting to dispatch. Job creation fails with a `422` error if no public key is registered or if the signature does not match the registered key.

## Step 4: Dispatch the job

=== "Dashboard"

    1. Go to **Jobs** in the dashboard sidebar
    2. Click **New Job**
    3. Fill in the form:
        - **Script**: paste the full contents of `hello.py`
        - **Signature**: paste the base64 string from `hello.py.sig.b64`
        - **Signature Key**: select the key you registered in Step 2
        - **Target tags**: leave blank to target any available node, or enter `general` to match the default node tag
    4. Click **Dispatch**

=== "CLI"

    !!! note "axiom-push requires EE"
        `axiom-push` is an Enterprise Edition feature. CE users should use the Raw API method below.

    ```bash
    axiom-push job push \
      --script hello.py \
      --key signing.key \
      --key-id <your-key-id>
    ```

    ??? example "Raw API (curl)"

        Sign the script and submit with a single curl command:

        ```bash
        SIG=$(openssl pkeyutl -sign -inkey signing.key -rawin -in hello.py | base64 -w0)
        curl -sk -X POST https://<your-orchestrator>:8001/jobs \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d "{\"script_content\": \"$(cat hello.py | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\", \"signature\": \"$SIG\", \"signature_key_id\": \"<key-id>\"}"
        ```

        Set `$TOKEN` by logging in first:
        ```bash
        TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
          -H 'Content-Type: application/x-www-form-urlencoded' \
          -d 'username=admin&password=<your-password>' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
        ```

---

## Step 5: Verify the result

The job appears in the Jobs list and transitions through statuses:

```
PENDING → ASSIGNED → COMPLETED
```

Click the job row to expand the result. The output should show:

```
Hello from Axiom!
Running on <node-hostname> (Linux)
```

!!! success "You've completed the Getting Started guide"
    Your node is enrolled, jobs are running, and results are captured in the dashboard.

    **What to explore next:**

    - [Foundry](../feature-guides/foundry.md) — build custom node images with pre-installed runtimes and packages
    - [axiom-push CLI](../feature-guides/axiom-push.md) — sign and submit jobs from the command line in one step

# axiom-push CLI

`axiom-push` is the command-line tool for pushing signed jobs to Axiom from a developer or CI/CD machine. It handles OAuth authentication, Ed25519 signing, and job submission in a single workflow — so you can submit jobs without touching the dashboard.

!!! note "Prerequisites"
    This guide assumes the stack is running and at least one node is enrolled. If you haven't done that yet, start with [Getting Started](../getting-started/prerequisites.md).

---

!!! enterprise

## Install

Install `axiom-push` from the repository root:

```bash
pip install -e .
```

Verify the installation:

```bash
axiom-push --help
```

!!! tip "pipx for isolation"
    If you don't want to install into your global Python environment, use `pipx` instead:

    ```bash
    pipx install -e .
    ```

    This keeps `axiom-push` isolated in its own virtualenv while still making the command available on your PATH.

---

## Login

`axiom-push` uses the OAuth 2.0 Device Authorization Grant ([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628)) — no browser on the machine running the CLI is required. This makes it safe to use in headless environments and CI/CD pipelines.

Set the server URL using the environment variable:

```bash
export AXIOM_URL=https://your-host
```

Then run the login command:

```bash
axiom-push login
```

You will see output like this:

```
Initiating login to https://your-host...

========================================
USER CODE: ABCD-1234
========================================

Please approve this request in your browser:
https://your-host/auth/device?user_code=ABCD-1234

Attempting to open browser automatically...

Waiting for approval...

Successfully authenticated and saved credentials.
```

What happens step by step:

1. The CLI requests a device code from the server
2. Your user code and a browser URL are displayed
3. Open the URL in any browser and log in with your dashboard credentials
4. Approve the request — the CLI is polling in the background
5. Once approved, the CLI receives and stores your access token

!!! info "Credential store"
    Credentials are saved to `~/.axiom/credentials.json` with permissions `0600`. If you are running as root or inside a container, confirm the home directory is writable and that the path resolves to where you expect. You can verify with:

    ```bash
    cat ~/.axiom/credentials.json
    ```

**Session lifetime:** Credentials expire after the JWT lifetime configured on the server (default: 15 minutes for access tokens). Run `axiom-push login` again to re-authenticate when your session expires.

---

## Ed25519 Key Setup

All jobs submitted via `axiom-push` must be signed with an Ed25519 private key. The corresponding public key must be registered in the dashboard before you can push.

### Generate a keypair

**Option 1 — Using openssl** (any machine with openssl installed):

```bash
openssl genpkey -algorithm ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out verification.key
```

**Option 2 — Using admin_signer.py** (if the toms_home tooling is available):

```bash
python ~/Development/toms_home/.agents/tools/admin_signer.py --generate
# Creates: secrets/signing.key and secrets/verification.key
```

!!! danger "Protect your private key"
    Never commit `signing.key` to a git repository. Add it to `.gitignore` immediately:

    ```bash
    echo "signing.key" >> .gitignore
    ```

    In production, store private keys in a secrets manager (HashiCorp Vault, AWS Secrets Manager, or similar) and inject them at runtime via environment variable or mounted volume. A leaked signing key allows anyone to submit jobs that nodes will execute.

### Register the public key in the dashboard

1. Go to **Signatures** in the dashboard sidebar
2. Click **Add Signature Key**
3. Paste the full contents of `verification.key` (including the `-----BEGIN PUBLIC KEY-----` header and footer)
4. Give it a descriptive name — for example, `ci-deploy-key` or `my-laptop-key`
5. Click **Save**

Note the **Key ID** shown in the list. You will pass this as `--key-id` when pushing jobs.

---

## Push a Job

Write a simple test script to try your first push:

```python
# hello.py
print("Hello from axiom-push!")
import platform
print(f"Node: {platform.node()}, OS: {platform.system()}")
```

Push it to the server:

```bash
axiom-push job push \
  --script hello.py \
  --key signing.key \
  --key-id <your-key-id>
```

The CLI will sign the script with your private key, upload it along with the signature, and print the created job ID and its initial status.

!!! warning "DRAFT jobs are not dispatched"
    A newly pushed job has status **DRAFT**. Nodes will not receive DRAFT jobs. You must publish the job via the dashboard (or the API) before it is dispatched to any node. See [Publish from Staging](#publish-from-staging) below.

You can also pass `--url` directly if you haven't set `AXIOM_URL`:

```bash
axiom-push --url https://your-host job push \
  --script hello.py \
  --key signing.key \
  --key-id <your-key-id>
```

---

## Publish from Staging

After pushing, complete the promotion flow in the dashboard:

1. Go to **Jobs** in the sidebar and select the **Staging** tab
2. Your job appears with status **DRAFT** and a preview of the script content
3. Review the script in the staging view — this is your gate to confirm the right script and the correct signature are present before dispatching to nodes
4. Click **Publish** to promote the job from **DRAFT** to **ACTIVE**

Once published:

- Active jobs are dispatched to nodes matching the job's target tags, or to any available node if no tags are set
- Monitor progress in the Jobs list — the job moves through **PENDING → ASSIGNED → COMPLETED**
- Click the job row to view the captured output from the node

At this point you have an active job running on a node. The complete flow is: push → DRAFT → Staging review → Publish → ACTIVE → node execution → output captured.

---

## Updating a Job

If you push a new version of a script and want to replace an existing job, pass the existing job ID with `--id`:

```bash
axiom-push job push \
  --id <existing-job-id> \
  --script updated_script.py \
  --key signing.key \
  --key-id <your-key-id>
```

This creates a new DRAFT version associated with the existing job ID. Go to Staging and Publish as before to make it active.

---

## Environment Variable Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `AXIOM_URL` | Base URL for the Axiom server | `https://your-host` |

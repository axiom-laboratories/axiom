# Tools Documentation

## Admin Signer (`tools/admin_signer.py`)
This tool is the primary interface for the Orchestrator Administrator to manage security keys and submit jobs safely.

### 1. Generate Keys
Generates an Ed25519 Keypair in `secrets/`.
```powershell
python tools/admin_signer.py --generate
```

### 2. Sign & Submit Code
Signs a Python script and submits it to the Model Service.
```powershell
python tools/admin_signer.py --sign my_script.py
```
This requires `secrets/signing.key` to be present.

## Note on Security
*   **Keys**: Store `secrets/signing.key` securely. It allows RCE on all nodes.
*   **Distribution**: `secrets/verification.key` must be distributed to all nodes (or uploaded via Dashboard).

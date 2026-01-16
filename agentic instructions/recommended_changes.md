# Recommended Changes: Security Hardening (Pass 4)

**Status Update:** RCE Enforcement is verified fixed. Focus has shifted to providing cost-effective Sandboxing strategies.

## 🚨 Critical Security Issues (Immediate Action Required)

### 1. Private Keys & Secrets in Root Directory
**Files Affected:** `agent.key`, `node-*.key`, `ca_password.txt`

- **Status**: ❌ **OPEN**
- **Finding**: Secret files (private keys and passwords) are sitting in the root of the repository.
- **Recommendation**:
    -   Move all `*.key`, `*.crt`, `*.pem`, `*.txt` (passwords) to a `secrets/` directory.
    -   Ensure `.gitignore` explicitly excludes this `secrets/` directory.

### 2. Sandboxing (Defense in Depth)
**Files Affected:** `environment_service/node.py`

- **Status**: ❌ **OPEN**
- **Finding**: Scripts run as the host user. Docker was proposed but rejected due to enterprise licensing costs.
- **Recommendation**: Implement **Podman** or **Windows Native Isolation**.

---

## 🛡️ Sandboxing Alternatives (Free/Open Source)

Since Docker Desktop licensing is a concern, the following free alternatives are recommended:

### Option A: Podman (Recommended)
- **Why**: It is a daemonless, open-source storage alternative to Docker with a compatible CLI (`podman run` vs `docker run`).
- **Cost**: Free (Apache 2.0 License).
- **Implementation**:
    -   Install Podman for Windows.
    -   `node.py` calls `podman run --network none -v ... python:slim ...`
    -   Provides the same level of container isolation as Docker.

### Option B: Windows Restricted User Accounts (Native)
- **Why**: Zero external dependencies. Uses built-in Windows security boundaries.
- **Cost**: Free (Built-in).
- **Implementation**:
    -   Create a local Windows User (e.g., `JobRunner`) with **no administrator privileges**.
    -   Deny this user access to `C:\Development`, `C:\Windows`, and network shares.
    -   Update `node.py` to use `runas` or a wrapper that spawns the subprocess as this `JobRunner` user.
    -   *Downside*: File system cleanup is harder; no network isolation by default (requires Firewall rules).

### Option C: WebAssembly (Wasm)
- **Why**: Extreme isolation. The runtime (Wasmtime) cannot access the host unless explicitly granted.
- **Cost**: Free.
- **Implementation**:
    -   Use a Python-to-Wasm runtime (like `wasmtime-py` or `pyodide`).
    -   Run the user script inside the Wasm sandbox.
    -   *Downside*: Some Python libraries (C-extensions like numpy) might be harder to support or require specific builds.

---

## ✅ Verified Fixes (Completed)

### 3. Remote Code Execution (RCE) - Enforcement
- **Status**: ✅ **FIXED** (Signature Verification Active)

### 4. Hardcoded API Key in Frontend
- **Status**: ✅ **FIXED**

### 5. Backend Secrets Management
- **Status**: ✅ **FIXED**

---

## Traceability & Next Steps

The next agent should:
1.  **Select & Implement Sandbox**: Install **Podman** (easiest migration) or configure a Restricted User.
2.  **File Cleanup**: Organize keys into `secrets/`.

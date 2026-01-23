# Recommended Changes: Security Hardening (Post-Refactor)

**Status Update:** RCE Enforcement is verified fixed. Secret Rotation verified. Broader scan identified minor dependency and backdoor risks.

## 🚨 Critical Security Issues (Immediate Action Required)

### 1. Hardcoded "Dev Backdoor" (Enrollment Secret)
**Files Affected:** `agent_service/main.py` (lines 413, 497, 525, 560)

- **Status**: ⚠️ **WARNING**
- **Finding**: The codebase contains explicit bypass checks:
    ```python
    if req.client_secret != "enrollment-secret": ...
    ```
    This allows anyone to register a node or fetch config using the hardcoded string `"enrollment-secret"`, bypassing the generated Join Tokens.
- **Recommendation**:
    -   **Remove** this fallback logic entirely for production.
    -   Or, put it behind a `if os.getenv("ENV") == "dev":` check.

### 2. Default Credentials in Production
**Files Affected:** `.env`, `node.py`

- **Status**: ⚠️ **WARNING**
- **Finding**: `API_KEY` defaults to `master-secret-key`.
- **Recommendation**: Rotate these keys immediately in production.

---

## ✅ Verified Improvements

### 3. RCE "Fail-Closed" Safety
- **Status**: ✅ **VERIFIED**
- **Finding**: `node.py` explicitly rejects jobs with missing signatures.

### 4. Key Distribution
- **Status**: ✅ **FIXED**

### 5. Network & SSL
- **Status**: ✅ **VERIFIED**

---

## 🔒 Broader Security Scan Findings

### 6. Dependency Management (`requirements.txt`)
- **Use `asyncpg`**: You are using `psycopg2-binary` which is not recommended for production. `asyncpg` is already listed and used by `main.py`, so `psycopg2-binary` can likely be removed.
- **`python-jose`**: Consider migrating to `pyjwt` as `python-jose` maintenance is slowing down.

### 7. API Security
- **CORS**: Correctly restricted to Dashboard/BFF ports.
- **Input Validation**: No explicit body size limits found (FastAPI default is 100MB+ for Starlette). Consider adding limits if processing large file uploads.

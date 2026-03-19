# Phase 30: Runtime Attestation — Research

**Researched:** 2026-03-18
**Domain:** Cryptographic attestation using RSA-2048 / Python `cryptography` library
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUTPUT-05 | Node produces a runtime attestation bundle — (script hash + stdout hash + stderr hash + exit code + start timestamp + node cert serial), serialised and signed with the node's mTLS client private key | RSA sign with `padding.PKCS1v15()` + `hashes.SHA256()` on the node private key already on disk at `secrets/{NODE_ID}.key` |
| OUTPUT-06 | Orchestrator verifies attestation signature against stored node cert for every execution; result (`verified`/`failed`/`missing`) stored on ExecutionRecord | Extract public key from `Node.client_cert_pem`, use `cert.public_key().verify(sig, bundle, padding.PKCS1v15(), hashes.SHA256())` — 4-arg call |
| OUTPUT-07 | Attestation bundles (raw signed bytes) stored and exportable via API for offline verification | New columns on `ExecutionRecord` + `GET /api/executions/{id}/attestation` endpoint |
</phase_requirements>

---

## Summary

Phase 30 adds a cryptographic attestation layer on top of the existing execution pipeline. The node already holds an RSA-2048 mTLS private key (generated in `ensure_identity()` at `secrets/{NODE_ID}.key`). The attestation bundle is a deterministically serialised JSON object containing six fields, signed with that key using PKCS1v15 + SHA256. The orchestrator already stores the full `client_cert_pem` for every enrolled node (added in Sprint 8 / Phase audit work) — this is the verification anchor.

The implementation touches three layers: node-side bundle construction and signing (in `node.py` `report_result()`), orchestrator-side verification (a new `attestation_service.py`), new DB columns on `ExecutionRecord`, and a new API endpoint. The pattern closely mirrors the existing `signature_service.py` verify flow except RSA (not Ed25519) and the call signature is different — a critical distinction documented in STATE.md.

The key implementation constraint is hash order: raw bytes MUST be hashed before scrubbing and truncation so that independent verifiers can reproduce the hash from the original output. The orchestrator must tolerate revoked certs gracefully — returning `failed` not raising an HTTP error.

**Primary recommendation:** Build a self-contained `attestation_service.py` with a single `verify_bundle()` entry point. Wire the node side into `report_result()` and the orchestrator side into `job_service.report_result()` immediately after the `ExecutionRecord` is written.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | Already in `requirements.txt` | RSA sign/verify, cert parsing | The entire mTLS and PKI stack already uses it; no new dependency |
| `hashlib` | stdlib | SHA-256 hashing of stdout/stderr bytes | Already imported in `node.py` |
| `json` | stdlib | Deterministic bundle serialisation | `json.dumps(bundle, sort_keys=True, separators=(',',':'))` is the prescribed format |
| `base64` | stdlib | Encode signature bytes for JSON transport | Already used throughout the codebase |

### No New Dependencies
This phase introduces zero new pip dependencies. All required primitives are already imported in the relevant files.

**RSA API reference (cryptography library):**

Node side — signing:
```python
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

with open(KEY_FILE, "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

signature = private_key.sign(bundle_bytes, padding.PKCS1v15(), hashes.SHA256())
```

Orchestrator side — verification (4 args, not 2):
```python
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

cert = x509.load_pem_x509_certificate(client_cert_pem.encode())
public_key = cert.public_key()
public_key.verify(signature_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())
# Raises InvalidSignature on failure — must catch
```

---

## Architecture Patterns

### Recommended File Layout

```
puppeteer/agent_service/services/
  attestation_service.py          # NEW — verify_bundle(), extract_cert_serial()
puppeteer/agent_service/
  db.py                           # ADD 3 columns to ExecutionRecord
  models.py                       # ADD AttestationResponse, update ResultReport
  main.py                         # ADD GET /api/executions/{id}/attestation
  services/job_service.py         # MODIFY report_result() to call attestation_service
puppets/environment_service/
  node.py                         # MODIFY report_result() to build + sign bundle
puppeteer/tests/
  test_attestation.py             # NEW — RSA round-trip + mutation test
puppeteer/
  migration_v33.sql               # NEW — 3 new nullable columns
```

### Pattern 1: Hash Order Invariant (CRITICAL)

**What:** Hashes in the attestation bundle must be computed over raw bytes BEFORE any scrubbing or truncation occurs. The `output_log` scrubbing in `job_service.report_result()` currently happens BEFORE the ExecutionRecord is written.

**When to use:** Always — this is a correctness invariant for independent verification.

**Node-side bundle construction:**
```python
# In node.py execute_task(), AFTER runtime_engine.run() returns,
# BEFORE any scrubbing:
script_hash = hashlib.sha256(script.encode('utf-8')).hexdigest()
stdout_hash = hashlib.sha256((result.get("stdout") or "").encode('utf-8')).hexdigest()
stderr_hash = hashlib.sha256((result.get("stderr") or "").encode('utf-8')).hexdigest()
# These get passed into report_result() as part of the attestation bundle
```

**Bundle serialisation (deterministic — sort_keys + no spaces):**
```python
import json

bundle = {
    "cert_serial": cert_serial,      # str(cert.serial_number)
    "exit_code": exit_code,
    "script_hash": script_hash,
    "start_timestamp": started_at_iso,
    "stderr_hash": stderr_hash,
    "stdout_hash": stdout_hash,
}
bundle_bytes = json.dumps(bundle, sort_keys=True, separators=(',',':')).encode('utf-8')
```

Note: `sort_keys=True` is what makes the serialisation deterministic regardless of dict insertion order. The field names must be exactly as specified in the success criteria.

**Cert serial extraction on node:**
```python
from cryptography import x509
from cryptography.hazmat.primitives import serialization

with open(CERT_FILE, "rb") as f:
    cert = x509.load_pem_x509_certificate(f.read())
cert_serial = str(cert.serial_number)
```

### Pattern 2: Orchestrator Verification Flow

**What:** `attestation_service.verify_bundle()` is called from `job_service.report_result()` after the `ExecutionRecord` row is created. It looks up `Node.client_cert_pem`, verifies the RSA signature, and returns a status string.

**Verification result states:**
- `"verified"` — signature valid against stored cert
- `"failed"` — signature present but verification failed, OR cert is revoked
- `"missing"` — node sent no attestation bundle

**Revoked cert handling:**
```python
# Check RevokedCert table using cert serial from bundle
# If serial in revoked_certs → return "failed" (not raise HTTPException)
from ..db import RevokedCert
result = await db.execute(
    select(RevokedCert).where(RevokedCert.serial_number == cert_serial)
)
if result.scalar_one_or_none():
    return "failed"  # Cert was revoked after execution — store failed, no 500
```

**InvalidSignature exception handling:**
```python
from cryptography.exceptions import InvalidSignature

try:
    public_key.verify(sig_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())
    return "verified"
except InvalidSignature:
    return "failed"
except Exception as e:
    logger.error("Attestation verification error for %s: %s", execution_id, e)
    return "failed"  # Always store failed, never propagate as HTTP 500
```

### Pattern 3: Transport Format

The node sends `attestation_bundle` (base64-encoded raw bytes of the JSON string) and `attestation_signature` (base64-encoded raw signature bytes) as additional fields in the existing `ResultReport` POST body.

```python
# node.py — additions to report_result() call
attestation_bundle_b64 = base64.b64encode(bundle_bytes).decode('ascii')
attestation_signature_b64 = base64.b64encode(signature).decode('ascii')
```

`ResultReport` Pydantic model gets two new optional fields:
```python
attestation_bundle: Optional[str] = None    # base64 of bundle JSON bytes
attestation_signature: Optional[str] = None # base64 of RSA signature bytes
```

### Pattern 4: New DB Columns on ExecutionRecord

Three new nullable columns — safe to add to existing deployments:
```python
attestation_bundle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
attestation_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
attestation_verified: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
```

`attestation_verified` is a String(16) — values: `"verified"`, `"failed"`, `"missing"`, or `None` (not yet verified — pre-attestation records).

### Pattern 5: Export Endpoint

```python
@app.get("/api/executions/{id}/attestation", tags=["Execution Records"])
async def get_attestation(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("history:read"))
):
    # Returns raw bundle bytes + signature for offline verification
    # Returns 404 if record not found
    # Returns 404 with {"detail": "no attestation"} if attestation_bundle is None
    # Returns 200 with JSON: {bundle_b64, signature_b64, cert_serial, node_id}
```

### Anti-Patterns to Avoid

- **Copying Ed25519 verify pattern:** `signature_service.py` uses `public_key.verify(sig_bytes, payload.encode())` — 2 args. RSA verify is `public_key.verify(sig_bytes, data_bytes, padding.PKCS1v15(), hashes.SHA256())` — 4 args. These are incompatible.
- **Hashing scrubbed output:** Computing stdout_hash/stderr_hash from the scrubbed or truncated log is wrong. Hash the raw captured output before any processing.
- **Raising HTTP 500 on revocation:** Revoked cert after execution is an expected operational scenario. Store `"failed"` silently, no server error.
- **Non-deterministic serialisation:** `json.dumps(bundle)` without `sort_keys=True` produces different bytes on different Python versions / dict orderings. Always use `sort_keys=True, separators=(',',':')`.
- **Loading the private key in execute_task:** Load it once in `report_result()` just before signing to avoid holding the key in memory longer than needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSA signing | Custom padding/hash logic | `cryptography` `padding.PKCS1v15()` + `hashes.SHA256()` | Side-channel attacks, standard compliance |
| Cert serial extraction | String parsing of PEM | `x509.load_pem_x509_certificate(pem).serial_number` | cryptography library handles DER decoding correctly |
| Deterministic JSON | Custom serialiser | `json.dumps(bundle, sort_keys=True, separators=(',',':'))` | Already stdlib, well-defined output |
| Signature storage | Binary blob DB column | `base64.b64encode(signature).decode('ascii')` stored as Text | Consistent with existing pattern in codebase |

---

## Common Pitfalls

### Pitfall 1: RSA vs Ed25519 API Mismatch
**What goes wrong:** Developer copies the existing `signature_service.py` Ed25519 verify call — `public_key.verify(sig_bytes, data)` — and applies it to RSA. The RSA `verify()` method requires 4 arguments: `(signature, data, padding, algorithm)`. Calling it with 2 raises `TypeError`, not `InvalidSignature`.
**Why it happens:** Both key types have a `verify()` method; the signatures differ.
**How to avoid:** Always include `padding.PKCS1v15()` and `hashes.SHA256()` as the 3rd and 4th args for RSA.
**Warning signs:** `TypeError: RSAPublicKey.verify() missing 2 required positional arguments` in logs.

### Pitfall 2: Hash Order Violation
**What goes wrong:** stdout_hash is computed from `stdout_text` after the scrubbing loop in `job_service.report_result()`. Independent verifiers cannot reproduce the hash from the pre-scrubbed output.
**Why it happens:** The natural code flow processes output before creating the record. Attestation needs to work from original bytes.
**How to avoid:** The node must compute and report hashes. The orchestrator must NOT recompute them from its scrubbed copy. The node-reported hashes go directly into the bundle — the orchestrator only verifies the signature over the bundle the node sent.
**Warning signs:** Independent verification tools report hash mismatches on executions where no tampering occurred.

### Pitfall 3: `started_at` Source
**What goes wrong:** Node uses `datetime.now()` for `start_timestamp` in the bundle, but the orchestrator stores `job.started_at` (set at dispatch time) in `ExecutionRecord.started_at`. These differ by network round-trip time, causing verification tools to flag a mismatch.
**Why it happens:** Two different clocks measure start time.
**How to avoid:** The `start_timestamp` in the bundle must be the value from `WorkResponse.started_at` that the orchestrator sent to the node at dispatch. The node receives this in the work poll response and must pass it through to bundle construction.
**Implementation note:** `WorkResponse` already includes `started_at`. The node's `execute_task()` receives the full job dict — ensure `started_at` is passed into `report_result()` and used in the bundle.

### Pitfall 4: Node Key Not Loaded at Attestation Time
**What goes wrong:** The private key file `secrets/{NODE_ID}.key` might not exist if the node is running in a degraded state (enrollment failed, key rotated). Attempting to sign raises `FileNotFoundError`.
**How to avoid:** Check `os.path.exists(KEY_FILE)` before signing. If key is unavailable, send `attestation_bundle=None, attestation_signature=None` — the orchestrator will store `"missing"`.

### Pitfall 5: Cert Revoked After Execution
**What goes wrong:** A node executes a job successfully, cert is later revoked, then the result report arrives. The orchestrator looks up `RevokedCert` by `cert_serial` extracted from the bundle and finds a match. This must store `"failed"` — not raise an HTTP exception.
**How to avoid:** The revocation check in `attestation_service.verify_bundle()` explicitly returns `"failed"` (string) when the serial is in `RevokedCert`. The route handler must NOT propagate exceptions from this service.

### Pitfall 6: migration_v33.sql Numbering
The last migration is `migration_v32.sql` (Phase 29). This phase's migration file must be `migration_v33.sql`.

---

## Code Examples

### Node Side — Full Sign Flow

```python
# Source: node.py report_result() — to be added
import base64
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

def _build_and_sign_attestation(
    script_hash: str,
    stdout_hash: str,
    stderr_hash: str,
    exit_code: int,
    started_at_iso: str,
    cert_file: str,
    key_file: str,
) -> tuple[Optional[str], Optional[str]]:
    """Returns (bundle_b64, signature_b64) or (None, None) on any error."""
    try:
        with open(cert_file, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        cert_serial = str(cert.serial_number)

        bundle = {
            "cert_serial": cert_serial,
            "exit_code": exit_code,
            "script_hash": script_hash,
            "start_timestamp": started_at_iso,
            "stderr_hash": stderr_hash,
            "stdout_hash": stdout_hash,
        }
        bundle_bytes = json.dumps(
            bundle, sort_keys=True, separators=(',', ':')
        ).encode('utf-8')

        with open(key_file, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        signature = private_key.sign(bundle_bytes, padding.PKCS1v15(), hashes.SHA256())

        return (
            base64.b64encode(bundle_bytes).decode('ascii'),
            base64.b64encode(signature).decode('ascii'),
        )
    except Exception as e:
        print(f"[Attestation] Failed to sign bundle: {e}")
        return None, None
```

### Orchestrator Side — Verification

```python
# Source: attestation_service.py — new file
import base64
import logging
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from sqlalchemy.future import select
from ..db import Node, RevokedCert, AsyncSession

logger = logging.getLogger(__name__)

ATTESTATION_VERIFIED = "verified"
ATTESTATION_FAILED = "failed"
ATTESTATION_MISSING = "missing"


async def verify_bundle(
    node_id: str,
    bundle_b64: Optional[str],
    signature_b64: Optional[str],
    db: AsyncSession,
) -> str:
    """Returns 'verified', 'failed', or 'missing'."""
    if not bundle_b64 or not signature_b64:
        return ATTESTATION_MISSING

    try:
        result = await db.execute(select(Node).where(Node.node_id == node_id))
        node = result.scalar_one_or_none()
        if not node or not node.client_cert_pem:
            logger.warning("No cert on file for node %s — attestation failed", node_id)
            return ATTESTATION_FAILED

        cert = x509.load_pem_x509_certificate(node.client_cert_pem.encode())
        cert_serial = str(cert.serial_number)

        # Check revocation first
        rev_result = await db.execute(
            select(RevokedCert).where(RevokedCert.serial_number == cert_serial)
        )
        if rev_result.scalar_one_or_none():
            logger.info("Attestation failed: cert %s is revoked (node %s)", cert_serial, node_id)
            return ATTESTATION_FAILED

        bundle_bytes = base64.b64decode(bundle_b64)
        sig_bytes = base64.b64decode(signature_b64)

        public_key = cert.public_key()
        public_key.verify(sig_bytes, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())
        return ATTESTATION_VERIFIED

    except InvalidSignature:
        logger.warning("Attestation signature invalid for node %s", node_id)
        return ATTESTATION_FAILED
    except Exception as e:
        logger.error("Attestation verification error for node %s: %s", node_id, e)
        return ATTESTATION_FAILED
```

### Test — RSA Round-Trip + Mutation

```python
# Source: test_attestation.py
import json
import base64
import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from cryptography.exceptions import InvalidSignature
import datetime
from datetime import UTC


@pytest.fixture
def rsa_cert_and_key():
    """Generate a test RSA-2048 cert + key pair (no CA needed for unit test)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"test-node"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(UTC))
        .not_valid_after(datetime.datetime.now(UTC) + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, cert


def test_attestation_rsa_roundtrip(rsa_cert_and_key):
    """OUTPUT-05/06: Full RSA sign/verify round-trip against a test cert fixture."""
    key, cert = rsa_cert_and_key
    bundle = {
        "cert_serial": str(cert.serial_number),
        "exit_code": 0,
        "script_hash": "a" * 64,
        "start_timestamp": "2026-03-18T12:00:00+00:00",
        "stderr_hash": "b" * 64,
        "stdout_hash": "c" * 64,
    }
    bundle_bytes = json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = key.sign(bundle_bytes, padding.PKCS1v15(), hashes.SHA256())

    # Verify
    public_key = cert.public_key()
    public_key.verify(signature, bundle_bytes, padding.PKCS1v15(), hashes.SHA256())  # No exception = pass


def test_attestation_mutation_fails(rsa_cert_and_key):
    """OUTPUT-06: Modifying exit_code after signing must cause verification to fail."""
    key, cert = rsa_cert_and_key
    bundle = {
        "cert_serial": str(cert.serial_number),
        "exit_code": 0,
        "script_hash": "a" * 64,
        "start_timestamp": "2026-03-18T12:00:00+00:00",
        "stderr_hash": "b" * 64,
        "stdout_hash": "c" * 64,
    }
    bundle_bytes = json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = key.sign(bundle_bytes, padding.PKCS1v15(), hashes.SHA256())

    # Mutate exit_code
    tampered = dict(bundle)
    tampered["exit_code"] = 1
    tampered_bytes = json.dumps(tampered, sort_keys=True, separators=(',', ':')).encode('utf-8')

    with pytest.raises(InvalidSignature):
        cert.public_key().verify(signature, tampered_bytes, padding.PKCS1v15(), hashes.SHA256())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ed25519 (job signing) | RSA-2048 (mTLS certs) | mTLS design — always | Do NOT share code between `signature_service.py` and `attestation_service.py` |
| No attestation columns on ExecutionRecord | `attestation_bundle`, `attestation_signature`, `attestation_verified` | Phase 30 | 3 new nullable columns, `migration_v33.sql` needed |
| `report_result()` sends `script_hash` only | Send full attestation bundle + signature | Phase 30 | `ResultReport` gets 2 new optional fields |

**Deprecated/outdated:**
- The `EXECUTION_MODE=direct` flag: removed in Phase 29 — do not re-introduce for test helpers.

---

## Open Questions

1. **`started_at` precision in bundle**
   - What we know: `WorkResponse.started_at` is a Python `datetime` set at dispatch. The node receives it as an ISO string in the work poll JSON.
   - What's unclear: Does `job.started_at.isoformat()` produce a timezone-aware string, or naive? Naive datetimes will produce different strings on different systems.
   - Recommendation: In the bundle, use `started_at.isoformat()` exactly as received from the work response (string passthrough). The orchestrator uses `job.started_at` for its own records independently. The bundle's `start_timestamp` is purely for attestation consumers and does not need to match the DB column exactly.

2. **`started_at` availability in `report_result()`**
   - What we know: `execute_task()` receives the full job dict which includes `started_at` from `WorkResponse`.
   - What's unclear: Is `started_at` currently forwarded through to `report_result()`? Looking at current code, it is not — `report_result()` only receives `guid, success, result, output_log, exit_code, security_rejected, script_hash`.
   - Recommendation: Add `started_at: Optional[str] = None` to `report_result()`'s signature and pass it through from `execute_task()`.

3. **stdout/stderr hashes — node vs orchestrator**
   - What we know: The orchestrator scrubs secrets from stdout/stderr before writing to the DB. Independent verifiers using the DB-stored values cannot reproduce the hash.
   - What's unclear: Should the attestation API endpoint return scrubbed or raw output? It can only return what's in the DB (scrubbed).
   - Recommendation: Document clearly in the attestation export endpoint that `stdout`/`stderr` in `GET /api/executions/{id}` are scrubbed, but the attestation bundle hashes cover pre-scrub output. The attestation endpoint exports the bundle bytes as-is — consumers verify the signature, not the content match.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `puppeteer/` — run from that directory |
| Quick run command | `cd puppeteer && pytest tests/test_attestation.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTPUT-05 | Node produces valid signed bundle | unit | `pytest tests/test_attestation.py::test_attestation_rsa_roundtrip -x` | Wave 0 |
| OUTPUT-05 | Bundle fields are deterministically serialised | unit | `pytest tests/test_attestation.py::test_bundle_deterministic -x` | Wave 0 |
| OUTPUT-05 | `cert_serial` matches the node's cert | unit | `pytest tests/test_attestation.py::test_cert_serial_matches -x` | Wave 0 |
| OUTPUT-06 | Mutation of `exit_code` invalidates signature | unit | `pytest tests/test_attestation.py::test_attestation_mutation_fails -x` | Wave 0 |
| OUTPUT-06 | `attestation_verified` column populated | source inspection | `pytest tests/test_attestation.py::test_execution_record_has_attestation_columns -x` | Wave 0 |
| OUTPUT-06 | Revoked cert → `"failed"` not 500 | unit | `pytest tests/test_attestation.py::test_revoked_cert_stores_failed -x` | Wave 0 |
| OUTPUT-07 | Export endpoint returns bundle + sig | unit | `pytest tests/test_attestation.py::test_attestation_export_endpoint -x` | Wave 0 |
| OUTPUT-07 | Export returns 404 for missing attestation | unit | `pytest tests/test_attestation.py::test_attestation_export_missing -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_attestation.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_attestation.py` — covers OUTPUT-05, OUTPUT-06, OUTPUT-07 (full new file)

---

## Sources

### Primary (HIGH confidence)
- Python `cryptography` library source code + existing usage in `puppeteer/agent_service/pki.py` — RSA key generation, CSR signing, cert parsing patterns verified in-codebase
- `puppets/environment_service/node.py` — node private key path (`secrets/{NODE_ID}.key`), cert path (`secrets/{NODE_ID}.crt`), existing RSA key generation in `ensure_identity()`
- `puppeteer/agent_service/db.py` — `ExecutionRecord` model, `Node.client_cert_pem` column, `RevokedCert` table
- `puppeteer/agent_service/services/job_service.py` — `report_result()` implementation, existing hash-order and scrub logic
- `.planning/STATE.md` lines 128–133 — explicit Phase 30 research flags (RSA-2048, 3-arg sign vs 4-arg verify, hash order invariant)

### Secondary (MEDIUM confidence)
- Existing `test_output_capture.py` — established source-inspection test pattern for structural invariants
- `migration_v32.sql` — confirms `migration_v33.sql` is the correct next filename

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all primitives already in codebase and verified in `pki.py`
- Architecture: HIGH — RSA key/cert locations confirmed in source; API patterns match existing routes
- Pitfalls: HIGH — RSA vs Ed25519 API difference documented in STATE.md; hash order confirmed by reading `job_service.py` scrub sequence
- Test patterns: HIGH — established pytest + source-inspection pattern already used in Phase 29

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable domain — `cryptography` library RSA API is stable)

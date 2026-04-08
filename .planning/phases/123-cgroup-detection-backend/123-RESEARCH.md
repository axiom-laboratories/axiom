# Phase 123: Cgroup Detection Backend - Research

**Researched:** 2026-04-08
**Domain:** Linux cgroup v1 vs v2 detection in containerized Python environments
**Confidence:** HIGH

## Summary

Phase 123 requires nodes to detect cgroup v1 vs v2 at startup and report the detected version in every heartbeat. Detection happens once per node lifecycle (module-level cached variable, reusing the NODE_ID pattern). The orchestrator stores both the detected version string and raw detection info for debugging. This phase is prerequisite for Phase 127 dashboard visibility.

The detection approach is straightforward: read `/proc/self/cgroup` for format (v2 = single `0::/path` line vs v1 = multiple numbered lines), verify with `/sys/fs/cgroup/cgroup.controllers` existence (v2 indicator). Hybrid setups (some controllers v1, some v2) are reported as v1 (conservative). Unreadable /proc or /sys (permission denied, restricted container) returns `unsupported`. Detection runs synchronously at module load, logs result at startup, and includes version + reason in startup log.

**Primary recommendation:** Implement a `CgroupDetector` class with separate detection methods per version, cache result at module level in node.py, add two fields to HeartbeatPayload (detected_cgroup_version, cgroup_raw), add two columns to Node DB table, update JobService.receive_heartbeat to persist both fields, expose detected_cgroup_version in NodeResponse for Phase 127 dashboard.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Three possible values:** `v1`, `v2`, `unsupported`
- **Hybrid cgroup setups (some controllers on v1, some on v2):** report as `v1` — conservative, triggers amber warning path
- **Unreadable /proc or /sys (permission denied, restricted container):** returns `unsupported`
- **Field name:** `detected_cgroup_version` across DB column, HeartbeatPayload, and heartbeat JSON key — distinguishes from hypothetical future "required" or "expected" cgroup version
- **DB column default:** null (not "unsupported") — clean distinction between "never reported" and "detected unsupported"
- **Detection approach:** Detect from the container's own perspective using filesystem paths only (/proc/self/cgroup, /sys/fs/cgroup/cgroup.controllers)
- **Container semantics:** What the container sees IS what governs job containers it spawns — correct for Docker-in-Docker
- **No cross-referencing:** Don't use container runtime (docker info, podman info) — keep detection orthogonal to runtime config
- **Raw detection info:** Store in separate `cgroup_raw` DB column (Text, nullable) for debugging
- **Raw data in heartbeat:** Both detected_cgroup_version and cgroup_raw sent in every heartbeat
- **Startup behavior:** Detection runs once at module load (cached in module-level variable, reusing NODE_ID pattern)
- **Logging:** logger.info for v1 and v2; logger.warning for unsupported
- **Startup log format:** e.g., "Detected cgroup: v2 (cgroup.controllers found at /sys/fs/cgroup/)"
- **Jobs execution:** Nodes with unsupported cgroups still accept and execute jobs — detection is informational, not blocking
- **Heartbeat fields:** Both optional on HeartbeatPayload (Optional[str] = None) — backward compatible
- **Orchestrator updates:** Unconditional on every heartbeat (no change-detection)
- **Migration:** Two new nullable columns on Node table: `detected_cgroup_version` (String), `cgroup_raw` (Text)

### Claude's Discretion
- CgroupDetector class design vs simple function
- Exact /proc and /sys parsing logic for v1/v2 detection
- Raw data format (full /proc contents vs summarized)
- Test fixture design for mocking /proc and /sys paths

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

---

## Standard Stack

### Core
| Component | Purpose | Decision/Pattern |
|-----------|---------|------------------|
| Python pathlib.Path | Filesystem operations | Read /proc/self/cgroup and /sys/fs/cgroup/cgroup.controllers |
| os.path.exists() | File existence checks | Verify /sys/fs/cgroup/cgroup.controllers existence |
| Exception handling | Permission errors | Catch FileNotFoundError, PermissionError → return unsupported |

### No External Dependencies Required
Cgroup detection uses only Python standard library (pathlib, os, exception handling). No external packages needed.

### Supporting Patterns (from existing codebase)
| Pattern | Usage | Applied Here |
|---------|-------|--------------|
| Module-level detection cached in global | Node identity persistence | NODE_ID pattern in node.py; reuse for cgroup detection |
| HeartbeatPayload Optional fields | Backward compatibility | env_tag, upgrade_result already use Optional[str] = None |
| Node table nullable columns | Optional metadata | machine_id, template_id, env_tag already nullable; add detected_cgroup_version and cgroup_raw |
| SQLAlchemy Text column | Large text storage | Use for cgroup_raw (full /proc contents for debugging) |

---

## Architecture Patterns

### Detection Module Structure
Node.py should implement cgroup detection following this pattern:

```python
# At module level (after NODE_ID definition)
def _detect_cgroup_version() -> tuple[str, str]:
    """
    Detect cgroup v1 vs v2 vs unsupported.

    Returns: (detected_version: str, raw_info: str)
    - detected_version: one of "v1", "v2", "unsupported"
    - raw_info: detection reasoning + /proc/self/cgroup contents (for debugging)
    """
    # Implementation details in "Code Examples" section
    pass

DETECTED_CGROUP_VERSION, DETECTED_CGROUP_RAW = _detect_cgroup_version()

# Log at startup
logger.info(f"Detected cgroup: {DETECTED_CGROUP_VERSION} ({brief reason})")
if DETECTED_CGROUP_VERSION == "unsupported":
    logger.warning(f"Node running with unsupported cgroup configuration. Raw info: {DETECTED_CGROUP_RAW}")
```

### Detection Algorithm (Recommended Implementation)

**Step 1: Check /proc/self/cgroup format**
- Read `/proc/self/cgroup`
- If single line starting with `0::` → v2 candidate
- If multiple lines with numbered prefixes (e.g., `1:memory:/`, `2:cpu:/`) → v1 candidate
- If unreadable → unsupported

**Step 2: Verify /sys/fs/cgroup/cgroup.controllers (v2 confirmation)**
- If file exists → confirmed v2
- If doesn't exist + Step 1 detected v1 → confirmed v1
- If Step 1 detected v2 but file missing → inconsistent; treat as unsupported

**Step 3: Hybrid detection (conservative)**
- If /proc/self/cgroup shows mixed format (some numbered lines + some `0::`) → report v1 (conservative)
- This handles edge cases in restricted/transitioning containers

**Step 4: Error handling**
- Catch FileNotFoundError, PermissionError, OSError
- Return (`unsupported`, raw_info with error details)

### Integration Points

| Location | Change | Why |
|----------|--------|-----|
| node.py module level | Add DETECTED_CGROUP_VERSION, DETECTED_CGROUP_RAW globals | Cache detection result once per node lifecycle |
| heartbeat_loop() line 335 | Add detected_cgroup_version, cgroup_raw to payload dict | Include in every heartbeat |
| models.py HeartbeatPayload | Add two Optional[str] fields | Receive from nodes |
| db.py Node table | Add two nullable String/Text columns | Persist on orchestrator |
| job_service.py receive_heartbeat() | Update node.detected_cgroup_version, node.cgroup_raw | Store both fields from payload |
| models.py NodeResponse | Add detected_cgroup_version field | Expose for Phase 127 dashboard |

### Heartbeat Flow

```
Node:
  1. At module load: detect cgroup version + raw info (cached globals)
  2. Every heartbeat: include detected_cgroup_version + cgroup_raw in payload dict

Orchestrator:
  1. Receive heartbeat with payload
  2. Upsert Node row with both fields from payload (unconditional)
  3. Dashboard consumes NodeResponse.detected_cgroup_version (Phase 127)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|------------|-------------|-----|
| Filesystem monitoring for changes | Custom file polling system | Read once at startup (module level) | Cgroup version never changes per container lifetime |
| Runtime detection (docker info/podman info) | Parse docker/podman CLI output | Read /proc + /sys paths only | Orthogonal to runtime config; what container sees is correct semantic |
| Version comparison (v1 vs v2 string matching) | Manual string parsing | Follow kernel documentation format | /proc/self/cgroup format is standardized; check for `0::` prefix |
| Cross-container cgroup assumptions | Custom host cgroup inspection | Detect from container perspective (/proc/self) | DinD containers have their own /proc; that's the right reference frame |

---

## Common Pitfalls

### Pitfall 1: Reading Host Cgroup vs Container Cgroup
**What goes wrong:** Reading `/sys/fs/cgroup/` on the host, not realizing the host has v2 but the container has v1 (or vice versa). Code detects wrong version.
**Why it happens:** /sys/fs/cgroup mounts are namespace-bound. Inside DinD, you see a different cgroup hierarchy than the host. Confusion arises because both paths exist.
**How to avoid:** Always read `/proc/self/cgroup` (what THIS process sees) and `/sys/fs/cgroup/cgroup.controllers` (in the same namespace). Both are relative to the container's view.
**Warning signs:** Detection result doesn't match container runtime's expected version (e.g., docker runs with `--cgroupns=host` but detection sees v1).

### Pitfall 2: Hybrid Cgroup Misclassification
**What goes wrong:** Code detects one line with `0::` format and assumes pure v2, ignoring that some controllers are on v1 (hybrid mode). Later, job execution fails because expected controller is on v1.
**Why it happens:** The /proc/self/cgroup entry for unified v2 is always `0::/path`, but this doesn't mean ALL controllers are v2. Some might still be v1.
**How to avoid:** Check BOTH /proc/self/cgroup AND /sys/fs/cgroup/cgroup.controllers. If both present but controllers exist in both trees, report as v1 (conservative). Decision: hybrid → report v1.
**Warning signs:** Detection says v2 but /sys/fs/cgroup/memory directory exists (indicates v1 memory controller).

### Pitfall 3: Permission Denied Mishandled
**What goes wrong:** Code tries to read /proc/self/cgroup in a container without read permission, raises FileNotFoundError or PermissionError, crashes instead of returning unsupported.
**Why it happens:** In some restricted containers (AppArmor, seccomp, or read-only mount), /proc/self/cgroup is unreadable. This is not an error — it's expected in some environments.
**How to avoid:** Wrap file reads in try/except, catch FileNotFoundError + PermissionError, return unsupported + include error message in raw_info.
**Warning signs:** Node crashes at startup with PermissionError on module load.

### Pitfall 4: /sys/fs/cgroup.controllers Interpreted as Existence Check Only
**What goes wrong:** Code checks `os.path.exists(/sys/fs/cgroup/cgroup.controllers)` as v2 indicator, but doesn't read its contents. Misses cases where file exists but is empty or malformed.
**Why it happens:** The decision context says check existence; coder assumes existence is sufficient, but doesn't validate format.
**How to avoid:** File existence is correct v2 indicator. Reading contents is optional (for debugging in cgroup_raw). But DO handle missing file gracefully (v1 indicator).
**Warning signs:** None — this is a non-issue because existence check is sufficient per Kubernetes patterns.

### Pitfall 5: Raw Data Contains Secrets or PII
**What goes wrong:** /proc/self/cgroup is dumped verbatim into cgroup_raw, which later appears in logs/dashboards. If cgroup paths contain job GUIDs or node secrets, those leak.
**Why it happens:** Raw data includes everything read from /proc, without filtering.
**How to avoid:** /proc/self/cgroup does NOT contain secrets — it's a cgroup path string. Safe to store as-is. If you add other /proc files in future (like environ), then filter.
**Warning signs:** Dashboard shows sensitive data in cgroup_raw field.

---

## Code Examples

### Recommended CgroupDetector Class (Source: context + Kubernetes/Linux kernel documentation)

```python
# Source: Phase 123 CONTEXT.md + https://kubernetes.io/docs/concepts/architecture/cgroups/ + https://docs.kernel.org/admin-guide/cgroup-v2.html
import pathlib
import logging

logger = logging.getLogger(__name__)

class CgroupDetector:
    """Detect cgroup v1 vs v2 vs unsupported from container perspective."""

    CGROUP_V1_HEADER = "cgroup"  # v1 lines start with numbered hierarchy
    CGROUP_V2_MARKER = "0::"      # v2 always has single line starting with "0::"
    CGROUP_CONTROLLERS_PATH = pathlib.Path("/sys/fs/cgroup/cgroup.controllers")
    PROC_SELF_CGROUP_PATH = pathlib.Path("/proc/self/cgroup")

    @staticmethod
    def detect() -> tuple[str, str]:
        """
        Detect cgroup version from container perspective.

        Returns:
            (version_str, raw_info_str)
            - version_str: one of "v1", "v2", "unsupported"
            - raw_info_str: detection reasoning + /proc/self/cgroup contents
        """
        try:
            # Step 1: Check /proc/self/cgroup format
            proc_cgroup = CgroupDetector.PROC_SELF_CGROUP_PATH.read_text(encoding='utf-8')
            lines = proc_cgroup.strip().split('\n')

            # Analyze format
            v2_lines = sum(1 for line in lines if line.startswith(CgroupDetector.CGROUP_V2_MARKER))
            v1_lines = sum(1 for line in lines if ':' in line and not line.startswith(CgroupDetector.CGROUP_V2_MARKER))

            raw_info_parts = [f"proc_self_cgroup: {len(lines)} lines"]
            raw_info_parts.append(f"v2_marker_lines: {v2_lines}, v1_numbered_lines: {v1_lines}")
            raw_info_parts.append(f"content: {proc_cgroup[:200]}")

            # Hybrid detection: mixed format → conservative v1
            if v2_lines > 0 and v1_lines > 0:
                raw_info = " | ".join(raw_info_parts)
                return ("v1", f"Hybrid cgroup setup (mixed v1+v2) — treating as v1. {raw_info}")

            # Pure v2: single 0:: line
            if v2_lines > 0 and v1_lines == 0:
                # Confirm v2 with cgroup.controllers existence
                if CgroupDetector.CGROUP_CONTROLLERS_PATH.exists():
                    raw_info = " | ".join(raw_info_parts)
                    return ("v2", f"cgroup.controllers exists. {raw_info}")
                else:
                    # Inconsistent: v2 format but no controllers file
                    raw_info = " | ".join(raw_info_parts)
                    return ("unsupported", f"v2 format detected but cgroup.controllers missing (inconsistent). {raw_info}")

            # Pure v1: numbered hierarchy lines
            if v1_lines > 0 and v2_lines == 0:
                raw_info = " | ".join(raw_info_parts)
                return ("v1", f"Numbered cgroup hierarchy detected. {raw_info}")

            # Fallback: no recognized format
            raw_info = " | ".join(raw_info_parts)
            return ("unsupported", f"No recognized cgroup format. {raw_info}")

        except FileNotFoundError as e:
            return ("unsupported", f"FileNotFoundError reading {e.filename}: container may be restricted")
        except PermissionError as e:
            return ("unsupported", f"PermissionError reading cgroup info: {e}")
        except OSError as e:
            return ("unsupported", f"OSError: {e}")
        except Exception as e:
            return ("unsupported", f"Unexpected error during cgroup detection: {type(e).__name__}: {e}")
```

### Module-Level Integration in node.py

```python
# Source: node.py after NODE_ID definition (reusing NODE_ID pattern)
# At line ~85, after _load_or_generate_node_id() and NODE_ID = ...

def _detect_cgroup_version() -> tuple[str, str]:
    """Run cgroup detection once at module load."""
    detector = CgroupDetector()
    version, raw_info = detector.detect()

    # Log startup
    if version == "v1":
        logger.info(f"Detected cgroup: v1 (numbered hierarchy)")
    elif version == "v2":
        logger.info(f"Detected cgroup: v2 (cgroup.controllers found at /sys/fs/cgroup/)")
    else:
        logger.warning(f"Detected cgroup: unsupported — node may have restricted cgroup access. Raw: {raw_info}")

    return version, raw_info

DETECTED_CGROUP_VERSION, DETECTED_CGROUP_RAW = _detect_cgroup_version()
```

### HeartbeatPayload Update (models.py)

```python
# Source: CONTEXT.md integration points + existing optional fields pattern
class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, str]] = None
    job_telemetry: Optional[Dict[str, Dict]] = None
    upgrade_result: Optional[Dict] = None
    env_tag: Optional[str] = None
    detected_cgroup_version: Optional[str] = None  # NEW: "v1", "v2", "unsupported"
    cgroup_raw: Optional[str] = None                # NEW: raw detection info for debugging
```

### Heartbeat Payload Construction (node.py heartbeat_loop)

```python
# Source: node.py line 335 payload dict construction
payload = {
    "node_id": NODE_ID,
    "hostname": socket.gethostname(),
    "stats": stats,
    "tags": tags,
    "capabilities": caps,
    "env_tag": env_tag,
    "detected_cgroup_version": DETECTED_CGROUP_VERSION,  # NEW
    "cgroup_raw": DETECTED_CGROUP_RAW,                     # NEW
}
```

### Node DB Model Update (db.py)

```python
# Source: db.py Node table, following nullable column pattern
class Node(Base):
    __tablename__ = "nodes"
    # ... existing columns ...
    env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    operator_env_tag: Mapped[bool] = mapped_column(Boolean, default=False)
    job_memory_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detected_cgroup_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NEW
    cgroup_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                  # NEW
```

### JobService.receive_heartbeat Update (job_service.py)

```python
# Source: job_service.py receive_heartbeat method, around line 937-944
if stats_json:
    node.stats = stats_json
if tags_json:
    node.tags = tags_json
# Operator-set env_tag takes precedence over node self-reporting.
if not node.operator_env_tag:
    node.env_tag = hb.env_tag

# NEW: Always update cgroup version + raw info (unconditional, stateless)
node.detected_cgroup_version = hb.detected_cgroup_version
node.cgroup_raw = hb.cgroup_raw
```

### NodeResponse Update (models.py)

```python
# Source: models.py NodeResponse, for Phase 127 dashboard
class NodeResponse(BaseModel):
    node_id: str
    hostname: str
    ip: str
    last_seen: datetime
    status: str
    base_os_family: Optional[str] = None
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict] = None
    expected_capabilities: Optional[Dict] = None
    tamper_details: Optional[str] = None
    stats_history: Optional[List[Dict]] = None
    env_tag: Optional[str] = None
    detected_cgroup_version: Optional[str] = None  # NEW: Phase 127 dashboard consumption
```

### Migration SQL (new migration_vXX.sql)

```sql
-- Migration vXX: Add cgroup detection columns to nodes table
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS detected_cgroup_version VARCHAR(255);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS cgroup_raw TEXT;
```

---

## Test Fixtures

### Unit Test Pattern (pytest)

```python
# Source: pytest monkeypatch + pyfakefs patterns from search results
import pytest
from unittest.mock import patch, mock_open
from puppets.environment_service.node import CgroupDetector

@pytest.fixture
def mock_proc_cgroup_v2():
    """Mock /proc/self/cgroup for cgroup v2 scenario."""
    return "0::/test-cgroup\n"

@pytest.fixture
def mock_proc_cgroup_v1():
    """Mock /proc/self/cgroup for cgroup v1 scenario."""
    return "1:memory:/test-mem\n2:cpu:/test-cpu\n3:devices:/test-dev\n"

@pytest.fixture
def mock_proc_cgroup_hybrid():
    """Mock /proc/self/cgroup for hybrid v1+v2 scenario."""
    return "0::/test-v2\n1:memory:/test-v1-mem\n"

def test_detect_cgroup_v2(mock_proc_cgroup_v2):
    """Test detection of pure v2."""
    with patch("pathlib.Path.read_text", return_value=mock_proc_cgroup_v2), \
         patch("pathlib.Path.exists", return_value=True):  # cgroup.controllers exists
        version, raw = CgroupDetector.detect()
        assert version == "v2"
        assert "cgroup.controllers exists" in raw

def test_detect_cgroup_v1(mock_proc_cgroup_v1):
    """Test detection of pure v1."""
    with patch("pathlib.Path.read_text", return_value=mock_proc_cgroup_v1), \
         patch("pathlib.Path.exists", return_value=False):  # no cgroup.controllers
        version, raw = CgroupDetector.detect()
        assert version == "v1"
        assert "Numbered cgroup hierarchy" in raw

def test_detect_cgroup_hybrid(mock_proc_cgroup_hybrid):
    """Test hybrid v1+v2 reported as v1 (conservative)."""
    with patch("pathlib.Path.read_text", return_value=mock_proc_cgroup_hybrid):
        version, raw = CgroupDetector.detect()
        assert version == "v1"
        assert "Hybrid cgroup setup" in raw

def test_detect_cgroup_unsupported_permission():
    """Test permission denied returns unsupported."""
    with patch("pathlib.Path.read_text", side_effect=PermissionError("Access denied")):
        version, raw = CgroupDetector.detect()
        assert version == "unsupported"
        assert "PermissionError" in raw
```

---

## State of the Art

| Old Approach | Current Approach | Reference | Impact |
|--------------|------------------|-----------|--------|
| Manual cgroup detection per container runtime | Read /proc + /sys once at module load | Kubernetes, systemd patterns | Runtime-agnostic, correct semantic for DinD |
| Hardcoded v1 assumption | Detect and adapt | Linux 4.5+ kernel docs | Supports modern distributions (Ubuntu 22.04+) with v2 |
| Heartbeat omits cgroup info | Report in every heartbeat | Phase 123 design | Operator visibility without dashboard re-fetch |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing: `puppets/environment_service/tests/`) |
| Config file | `puppeteer/pytest.ini` or `pyproject.toml` |
| Quick run command | `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -v` |
| Full suite command | `cd puppets && pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CGRP-01 | Node detects cgroup v1 at startup | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_v1 -xvs` | ❌ Wave 0 |
| CGRP-01 | Node detects cgroup v2 at startup | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_v2 -xvs` | ❌ Wave 0 |
| CGRP-01 | Node detects unsupported cgroup (permission denied) | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_unsupported_permission -xvs` | ❌ Wave 0 |
| CGRP-01 | Hybrid cgroup setup reported as v1 (conservative) | unit | `pytest environment_service/tests/test_cgroup_detector.py::test_detect_cgroup_hybrid -xvs` | ❌ Wave 0 |
| CGRP-02 | Heartbeat includes detected_cgroup_version field | integration | `cd puppeteer && pytest tests/test_heartbeat.py::test_heartbeat_includes_cgroup_version -xvs` | ❌ Wave 0 |
| CGRP-02 | Orchestrator persists detected_cgroup_version to Node table | integration | `cd puppeteer && pytest tests/test_job_service.py::test_receive_heartbeat_stores_cgroup -xvs` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -v`
- **Per wave merge:** `cd puppets && pytest` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppets/environment_service/tests/test_cgroup_detector.py` — CgroupDetector class unit tests (v1, v2, hybrid, unsupported scenarios)
- [ ] `puppeteer/tests/test_heartbeat.py` — Integration tests for heartbeat payload + NodeResponse
- [ ] `puppeteer/tests/test_job_service.py` — JobService.receive_heartbeat updates to Node table
- [ ] Migration file: `puppeteer/migration_vXX.sql` — Add two columns to Node table
- [ ] Node table fields in `puppeteer/agent_service/db.py` — Add detected_cgroup_version + cgroup_raw
- [ ] HeartbeatPayload fields in `puppeteer/agent_service/models.py` — Add both Optional[str] fields
- [ ] NodeResponse field in `puppeteer/agent_service/models.py` — Add detected_cgroup_version

---

## Open Questions

1. **Migration version number**
   - What we know: Latest migration appears to be v49 (memory_limit + cpu_limit)
   - What's unclear: Should this be v50 or is there a skip in numbering?
   - Recommendation: Check `puppeteer/` for highest migration_vXX.sql and use next sequential number

2. **Raw data truncation for large /proc files**
   - What we know: /proc/self/cgroup is typically < 500 bytes
   - What's unclear: Should we truncate to first N lines to avoid DB TEXT column bloat?
   - Recommendation: For now, store full contents (< 1KB typical). Monitor in production. Phase 127 can add truncation if needed.

3. **Dashboard display of detected_cgroup_version (Phase 127)**
   - What we know: This phase stores the data; Phase 127 consumes it
   - What's unclear: Should amber warning appear for v1 in Nodes view? Or only in node detail drawer?
   - Recommendation: Out of scope for Phase 123. Phase 127 CONTEXT.md will decide.

---

## Sources

### Primary (HIGH confidence)
- [Kubernetes cgroup v2 documentation](https://kubernetes.io/docs/concepts/architecture/cgroups/) — Detection methods, filesystem indicators (cgroup2fs vs tmpfs)
- [Linux kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html) — /proc/self/cgroup format (0::/path for v2), cgroup.controllers file, unified hierarchy
- CONTEXT.md Phase 123 — Locked decisions on value representation, detection approach, heartbeat integration
- Project memory (CLAUDE.md + MEMORY.md) — Established patterns (NODE_ID module-level caching, HeartbeatPayload optional fields, Node table nullable columns, migration SQL format)

### Secondary (MEDIUM confidence)
- [GitHub: Docker-in-Docker cgroup considerations](https://github.com/moby/moby/issues/42910) — DinD nested container perspective, cgroup namespace awareness
- [Datadog Container Security Labs](https://securitylabs.datadoghq.com/articles/container-security-fundamentals-part-4/) — Hybrid cgroup implications
- [One Uptime blog: Docker Cgroups in Depth](https://oneuptime.com/blog/post/2026-02-08-how-to-understand-docker-container-cgroups-in-depth/view) — Detection approaches, cgroup v1 vs v2 characteristics
- [pytest monkeypatch documentation](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) — Mock filesystem paths
- [pyfakefs GitHub](https://github.com/pytest-dev/pyfakefs) — Alternative filesystem mocking for complex /proc scenarios

### Tertiary (LOW confidence, requires validation)
- [cielcg PyPI package](https://pypi.org/project/cielcg/) — Potential external dependency for cgroup management (recommend NOT using; phase requires no deps)

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — Only Python stdlib (pathlib, os, exception handling); no external packages required
- **Architecture patterns:** HIGH — Reuses NODE_ID caching pattern, HeartbeatPayload optional fields, Node table nullable columns already established in project
- **Detection logic:** HIGH — Kubernetes and Linux kernel docs explicitly document /proc/self/cgroup format (0:: v2 marker vs numbered v1), /sys/fs/cgroup/cgroup.controllers existence check
- **Hybrid handling:** MEDIUM — Slurm and systemd docs note hybrid mode is "not supported"; CONTEXT.md decision to treat as v1 is conservative and aligns with ecosystem guidance
- **Test fixtures:** MEDIUM — pytest monkeypatch + mock_open patterns are standard; specific /proc mocking requires care but well-documented
- **Pitfalls:** HIGH — Docker-in-Docker cgroup confusion documented in multiple sources; permission errors in restricted containers well-known

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days; cgroup detection is stable in Linux kernel; Docker/Podman compatibility mature)

---

**Phase 123 Research Complete**

This research enables Phase 123 planning to move forward with high confidence on:
1. Detection algorithm (read /proc/self/cgroup format + confirm with /sys/fs/cgroup/cgroup.controllers)
2. Data model (two new optional fields in HeartbeatPayload + Node table)
3. Integration points (module-level caching in node.py, heartbeat_loop payload construction, JobService.receive_heartbeat update, NodeResponse exposure)
4. Test framework (pytest unit tests with monkeypatch + mock_open for /proc/cgroup mocking)
5. Migration strategy (new migration_vXX.sql following existing pattern)

All decisions are locked per CONTEXT.md. Planner can proceed to task decomposition.

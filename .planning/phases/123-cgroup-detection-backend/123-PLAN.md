---
phase: 123-cgroup-detection-backend
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - puppets/environment_service/node.py
  - puppets/environment_service/tests/test_cgroup_detector.py
  - puppeteer/agent_service/models.py
  - puppeteer/agent_service/db.py
  - puppeteer/agent_service/services/job_service.py
  - puppeteer/migration_v51.sql
autonomous: true
requirements: [CGRP-01, CGRP-02]

must_haves:
  truths:
    - "Node detects cgroup v1 vs v2 vs unsupported at startup"
    - "Detection result cached in module-level variables (reusing NODE_ID pattern)"
    - "Node includes detected_cgroup_version and cgroup_raw in every heartbeat payload"
    - "Orchestrator persists both fields from heartbeat to Node DB table"
    - "NodeResponse exposes detected_cgroup_version for Phase 127 dashboard"
    - "Hybrid cgroup setups (mixed v1+v2) conservatively reported as v1"
    - "Permission errors on /proc or /sys return unsupported (not crash)"
  artifacts:
    - path: "puppets/environment_service/node.py"
      provides: "CgroupDetector class + module-level detection caching + heartbeat integration"
      min_lines: 50
    - path: "puppets/environment_service/tests/test_cgroup_detector.py"
      provides: "Unit tests for v1, v2, hybrid, unsupported detection scenarios"
      exports: ["test_detect_cgroup_v1", "test_detect_cgroup_v2", "test_detect_cgroup_hybrid", "test_detect_cgroup_unsupported_permission"]
    - path: "puppeteer/agent_service/models.py"
      provides: "HeartbeatPayload + detected_cgroup_version fields, NodeResponse field"
      contains: "detected_cgroup_version: Optional[str]"
    - path: "puppeteer/agent_service/db.py"
      provides: "Node table columns for detected_cgroup_version and cgroup_raw"
      contains: "detected_cgroup_version", "cgroup_raw"
    - path: "puppeteer/agent_service/services/job_service.py"
      provides: "receive_heartbeat updates Node with cgroup detection data"
      pattern: "node.detected_cgroup_version =", "node.cgroup_raw ="
    - path: "puppeteer/migration_v51.sql"
      provides: "Migration SQL adding two nullable columns to nodes table"
      contains: "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS detected_cgroup_version"
  key_links:
    - from: "puppets/environment_service/node.py"
      to: "puppets/environment_service/node.py heartbeat_loop()"
      via: "payload dict includes DETECTED_CGROUP_VERSION, DETECTED_CGROUP_RAW globals"
      pattern: "DETECTED_CGROUP_VERSION.*payload"
    - from: "puppets/environment_service/node.py"
      to: "puppeteer/agent_service/models.py HeartbeatPayload"
      via: "Node sends detected_cgroup_version + cgroup_raw in heartbeat JSON"
      pattern: "detected_cgroup_version.*Optional"
    - from: "puppeteer/agent_service/models.py HeartbeatPayload"
      to: "puppeteer/agent_service/services/job_service.py receive_heartbeat()"
      via: "HeartbeatPayload deserialized, fields extracted to Node row"
      pattern: "hb.detected_cgroup_version"
    - from: "puppeteer/agent_service/services/job_service.py"
      to: "puppeteer/agent_service/db.py Node table"
      via: "receive_heartbeat() sets node.detected_cgroup_version and node.cgroup_raw"
      pattern: "node.detected_cgroup_version = hb.detected_cgroup_version"
    - from: "puppeteer/agent_service/db.py Node table"
      to: "puppeteer/agent_service/models.py NodeResponse"
      via: "NodeResponse expose field for dashboard consumption"
      pattern: "detected_cgroup_version.*Optional\\[str\\]"
---

<objective>
**What:** Implement node-side cgroup detection (v1 vs v2 vs unsupported) and orchestrator persistence.

**Purpose:** Enable Phase 127 dashboard to show operator which cgroup version each node is running, supporting informed decisions about workload compatibility and enforcement guarantees. Addresses CGRP-01 (node detects at startup) and CGRP-02 (reports in heartbeat).

**Output:** CgroupDetector class, heartbeat integration, DB schema updates, full test coverage
</objective>

<execution_context>
@/home/thomas/.claude/get-shit-done/workflows/execute-plan.md
@/home/thomas/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/123-cgroup-detection-backend/123-CONTEXT.md
@.planning/phases/123-cgroup-detection-backend/123-RESEARCH.md

## Code Interfaces

From RESEARCH.md, the recommended CgroupDetector class implementation with module-level caching pattern (lines 203-267):

```python
class CgroupDetector:
    """Detect cgroup v1 vs v2 vs unsupported from container perspective."""

    CGROUP_V1_HEADER = "cgroup"
    CGROUP_V2_MARKER = "0::"
    CGROUP_CONTROLLERS_PATH = pathlib.Path("/sys/fs/cgroup/cgroup.controllers")
    PROC_SELF_CGROUP_PATH = pathlib.Path("/proc/self/cgroup")

    @staticmethod
    def detect() -> tuple[str, str]:
        """Returns (version_str, raw_info_str) where version is 'v1', 'v2', or 'unsupported'"""
        # Implementation: read /proc/self/cgroup, analyze format
        # Check /sys/fs/cgroup/cgroup.controllers for v2 confirmation
        # Hybrid (mixed v1+v2) → report as v1 (conservative)
        # Permission errors → return unsupported with error details
```

Node heartbeat integration (from node.py heartbeat_loop, line ~335):
```python
payload = {
    "node_id": NODE_ID,
    "detected_cgroup_version": DETECTED_CGROUP_VERSION,
    "cgroup_raw": DETECTED_CGROUP_RAW,
    # ... existing fields ...
}
```

HeartbeatPayload (models.py, line ~162):
```python
class HeartbeatPayload(BaseModel):
    detected_cgroup_version: Optional[str] = None  # NEW
    cgroup_raw: Optional[str] = None                # NEW
```

Node DB table (db.py, line ~150):
```python
class Node(Base):
    # ... existing columns ...
    detected_cgroup_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NEW
    cgroup_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # NEW
```

JobService.receive_heartbeat (job_service.py, around line 944-950):
```python
# NEW: Always update cgroup version + raw info (unconditional, stateless)
node.detected_cgroup_version = hb.detected_cgroup_version
node.cgroup_raw = hb.cgroup_raw
```

NodeResponse (models.py, line ~199):
```python
class NodeResponse(BaseModel):
    # ... existing fields ...
    detected_cgroup_version: Optional[str] = None  # NEW: Phase 127 dashboard
```
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: CgroupDetector class + node-side integration</name>
  <files>puppets/environment_service/node.py, puppets/environment_service/tests/test_cgroup_detector.py</files>
  <behavior>
    **Unit tests (RED state, will write first):**
    - Test 1: Pure v2 detected from /proc/self/cgroup format (0:: single line) + /sys/fs/cgroup/cgroup.controllers exists → returns ("v2", raw_info)
    - Test 2: Pure v1 detected from /proc/self/cgroup format (numbered lines 1:, 2:, 3:) → returns ("v1", raw_info)
    - Test 3: Hybrid setup (mixed 0:: + numbered lines) → conservatively returns ("v1", raw_info with "Hybrid" message)
    - Test 4: PermissionError reading /proc/self/cgroup → returns ("unsupported", error_details)
    - Test 5: FileNotFoundError reading /proc/self/cgroup (restricted container) → returns ("unsupported", error_details)
    - Test 6: v2 format in /proc but /sys/fs/cgroup/cgroup.controllers missing (inconsistent) → returns ("unsupported", raw_info with "inconsistent" message)
    - Test 7: Startup logging: logger.info for v1/v2, logger.warning for unsupported
  </behavior>
  <action>
    **Step 1: Create test file (RED state)**
    Write `puppets/environment_service/tests/test_cgroup_detector.py` with pytest fixtures + test cases per behavior above. Use unittest.mock.patch to mock pathlib.Path.read_text() and pathlib.Path.exists(). Mock return values with realistic /proc/self/cgroup content per scenario (v1: "1:memory:/test\n2:cpu:/test\n", v2: "0::/test\n", hybrid: "0::/test\n1:memory:/test\n").

    **Step 2: Implement CgroupDetector class in node.py (GREEN state)**
    Add CgroupDetector class to `puppets/environment_service/node.py` starting at module level (after imports, before NODE_ID definition). Follow RESEARCH.md code example lines 203-267 exactly:
    - Static method `detect() -> tuple[str, str]`
    - Read /proc/self/cgroup using pathlib.Path
    - Count v2 marker lines (0::) and v1 numbered lines
    - Hybrid detection: if both v2 + v1 lines exist → return v1
    - Pure v2: check /sys/fs/cgroup/cgroup.controllers existence for confirmation
    - Pure v1: return v1
    - Exception handling: catch FileNotFoundError, PermissionError, OSError → return unsupported
    - Raw info construction: include line counts + first 200 chars of /proc content + detection reasoning

    **Step 3: Module-level caching (following NODE_ID pattern)**
    After CgroupDetector class definition, add at module level (near NODE_ID = ...):
    ```python
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

    **Step 4: Integrate into heartbeat payload**
    Find `heartbeat_loop()` function in node.py (around line 288). Locate the payload dict construction (around line 335). Add two new keys:
    ```python
    payload = {
        "node_id": NODE_ID,
        "hostname": socket.gethostname(),
        "stats": stats,
        "detected_cgroup_version": DETECTED_CGROUP_VERSION,  # NEW
        "cgroup_raw": DETECTED_CGROUP_RAW,                     # NEW
        # ... existing fields ...
    }
    ```

    **Step 5: Run tests to GREEN**
    `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -xvs` — all 7 tests must pass.

    **Verification notes:**
    - CgroupDetector.detect() uses only pathlib + os (no external deps)
    - Module-level detection runs once at import time (same pattern as NODE_ID)
    - Startup logging confirms detection result
    - Heartbeat includes both version + raw info (stateless, sent every heartbeat)
  </action>
  <verify>
    <automated>cd puppets && pytest environment_service/tests/test_cgroup_detector.py -xvs</automated>
  </verify>
  <done>
    - CgroupDetector class implements detect() → (version, raw_info)
    - All 7 test cases pass (v1, v2, hybrid, permission errors, inconsistent)
    - Module-level DETECTED_CGROUP_VERSION and DETECTED_CGROUP_RAW initialized at import
    - Startup logs detection result (info for v1/v2, warning for unsupported)
    - heartbeat_loop() includes detected_cgroup_version + cgroup_raw in payload dict
  </done>
</task>

<task type="auto">
  <name>Task 2: Orchestrator data models + DB schema</name>
  <files>puppeteer/agent_service/models.py, puppeteer/agent_service/db.py, puppeteer/agent_service/services/job_service.py</files>
  <action>
    **Step 1: Update HeartbeatPayload (models.py)**
    Find class HeartbeatPayload (line ~162). Add two Optional[str] fields at the end of field definitions, before any validators:
    ```python
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

        @field_validator("env_tag", mode="before")  # existing validator — leave unchanged
        # ...
    ```
    Do NOT add validators for cgroup fields (no validation needed — raw data passed through).

    **Step 2: Add detected_cgroup_version to NodeResponse (models.py)**
    Find class NodeResponse (line ~199). Add field after env_tag:
    ```python
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
        detected_cgroup_version: Optional[str] = None  # NEW: Phase 127 dashboard
    ```

    **Step 3: Add columns to Node DB model (db.py)**
    Find class Node (line ~127), end of column definitions (after job_cpu_limit around line 150). Add two new columns:
    ```python
    class Node(Base):
        __tablename__ = "nodes"
        # ... existing columns ...
        job_cpu_limit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        detected_cgroup_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # NEW
        cgroup_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                  # NEW
    ```
    Use String (255 char limit) for detected_cgroup_version; use Text for cgroup_raw.

    **Step 4: Update JobService.receive_heartbeat() (job_service.py)**
    Find `receive_heartbeat()` method (line ~937). Locate where env_tag is updated (around line 950):
    ```python
    # Operator-set env_tag takes precedence over node self-reporting.
    if not node.operator_env_tag:
        node.env_tag = hb.env_tag

    # NEW: Always update cgroup version + raw info (unconditional, stateless)
    node.detected_cgroup_version = hb.detected_cgroup_version
    node.cgroup_raw = hb.cgroup_raw
    ```
    This update happens after env_tag logic, before db.commit().

    **Verification notes:**
    - HeartbeatPayload and NodeResponse changes are backward compatible (Optional + None defaults)
    - Node DB columns nullable (fresh create_all handles them; existing DBs need migration)
    - job_service.receive_heartbeat is stateless (unconditional update on every heartbeat)
    - Orchestrator doesn't validate cgroup values (just stores what node sends)
  </action>
  <verify>
    <automated>cd puppeteer && python -m py_compile agent_service/models.py agent_service/db.py agent_service/services/job_service.py</automated>
  </verify>
  <done>
    - HeartbeatPayload has detected_cgroup_version + cgroup_raw Optional[str] fields
    - NodeResponse has detected_cgroup_version Optional[str] field
    - Node DB table has two new nullable columns: detected_cgroup_version (String) + cgroup_raw (Text)
    - JobService.receive_heartbeat() updates both columns unconditionally from heartbeat payload
    - All imports and syntax correct (py_compile passes)
  </done>
</task>

<task type="auto">
  <name>Task 3: Migration SQL + test scaffold</name>
  <files>puppeteer/migration_v51.sql, puppets/environment_service/tests/test_cgroup_detector.py</files>
  <action>
    **Step 1: Create migration_v51.sql**
    Create new file `puppeteer/migration_v51.sql` with content:
    ```sql
    -- Migration v51: Add cgroup detection columns to nodes table
    -- For existing Postgres deployments only (fresh deployments use create_all in db.py)

    ALTER TABLE nodes ADD COLUMN IF NOT EXISTS detected_cgroup_version VARCHAR(255);
    ALTER TABLE nodes ADD COLUMN IF NOT EXISTS cgroup_raw TEXT;
    ```

    This follows existing pattern (see migration_v50.sql). For SQLite (local dev), columns will be auto-created by create_all on next startup.

    **Step 2: Verify test file exists from Task 1**
    Ensure `puppets/environment_service/tests/test_cgroup_detector.py` was created in Task 1 with all 7 test cases passing. No changes needed here if already complete — task 3 just confirms it's committed.

    **Verification notes:**
    - Migration file uses IF NOT EXISTS for idempotency (safe to run multiple times)
    - Column names match Node model definition (detected_cgroup_version, cgroup_raw)
    - Text column for raw data (can hold full /proc contents, typically < 1KB)
    - String column for version (max 255 chars; "v1", "v2", "unsupported" all fit)
  </action>
  <verify>
    <automated>cat puppeteer/migration_v51.sql | grep -E "ALTER TABLE nodes ADD COLUMN"</automated>
  </verify>
  <done>
    - migration_v51.sql created with two ADD COLUMN statements
    - Both columns use IF NOT EXISTS for safety
    - detected_cgroup_version is VARCHAR(255)
    - cgroup_raw is TEXT
    - Test file test_cgroup_detector.py confirmed to exist with all tests passing
  </done>
</task>

</tasks>

<verification>
**Phase-level verification after all tasks complete:**

1. **Node-side detection:**
   - `cd puppets && python -c "from environment_service.node import DETECTED_CGROUP_VERSION; print(f'Node cgroup: {DETECTED_CGROUP_VERSION}')"` — outputs v1, v2, or unsupported
   - Node startup logs include "Detected cgroup: {version}"

2. **Heartbeat payload:**
   - Examine a live heartbeat from running node: should include `detected_cgroup_version` and `cgroup_raw` fields

3. **Database schema:**
   - Fresh deployment: `cd puppeteer && python -c "from agent_service.db import Base, engine; Base.metadata.create_all(engine)"` — should create nodes table with both columns
   - Existing deployment: Run `migration_v51.sql` via Docker: `docker exec puppeteer-db-1 psql -d jobs -f migration_v51.sql`

4. **Orchestrator updates:**
   - `cd puppeteer && pytest tests/test_job_service.py::test_receive_heartbeat_stores_cgroup -xvs` — verifies heartbeat fields persist to Node table (test will be written in Phase execution)

5. **Full stack test:**
   - Deploy stack: `cd puppeteer && docker compose -f compose.server.yaml up -d`
   - Submit a heartbeat from a test node (or let normal heartbeat cycle run)
   - Query Node table: `SELECT node_id, detected_cgroup_version, cgroup_raw FROM nodes LIMIT 1;` — should show v1/v2/unsupported in first column

**Unit test coverage:**
- `cd puppets && pytest environment_service/tests/test_cgroup_detector.py -v` — all 7 tests passing ✓
</verification>

<success_criteria>
Phase 123 is complete when:
- [ ] CgroupDetector class detects v1 vs v2 vs unsupported from /proc/self/cgroup + /sys/fs/cgroup/cgroup.controllers
- [ ] Node detects cgroup version once at module load (cached global, reusing NODE_ID pattern)
- [ ] All 7 test cases pass (v1, v2, hybrid, permission errors, inconsistent, logging)
- [ ] Node includes detected_cgroup_version + cgroup_raw in every heartbeat
- [ ] HeartbeatPayload model includes both Optional[str] fields
- [ ] Node DB table has two new nullable columns (String + Text)
- [ ] JobService.receive_heartbeat() updates both columns unconditionally
- [ ] NodeResponse exposes detected_cgroup_version for Phase 127 dashboard
- [ ] migration_v51.sql created and idempotent (IF NOT EXISTS)
- [ ] All Python syntax checks pass (py_compile)
- [ ] Hybrid cgroup setups conservatively reported as v1
- [ ] Permission/missing /proc errors return unsupported (not crash)
- [ ] CGRP-01 satisfied: node detects at startup ✓
- [ ] CGRP-02 satisfied: node reports in heartbeat ✓
</success_criteria>

<output>
After execution, create `.planning/phases/123-cgroup-detection-backend/123-01-SUMMARY.md` with:
- Objective recap
- Tasks completed (3/3)
- Test results (all passing)
- Key files modified
- Commits made
- Remaining work for Phase 124+ (dashboard integration deferred to Phase 127)
</output>

---
phase: 124-ephemeral-execution-guarantee
verified: 2026-04-08T21:25:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 124: Ephemeral Execution Guarantee — Verification Report

**Phase Goal:** Block direct execution; flag EXECUTION_MODE=direct as unsafe. Ensure all jobs execute in ephemeral containers with runtime detection persisted server-side.

**Verified:** 2026-04-08T21:25:00Z

**Status:** PASSED — All must-haves verified, all tests passing, no gaps found.

## Goal Achievement Summary

Phase 124 successfully implements server-side visibility of node execution modes (docker/podman detection) and hardens the system to reject direct execution mode at both compose generation time and server startup. All jobs are guaranteed to execute in ephemeral containers.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Node table persists execution_mode from heartbeat | ✓ VERIFIED | `db.py:153` has `execution_mode` column; `job_service.py:951` updates from heartbeat |
| 2 | HeartbeatPayload accepts optional execution_mode field (backward compatible) | ✓ VERIFIED | `models.py:173` has `Optional[str]` field; test_node_execution_mode.py passes |
| 3 | NodeResponse exposes execution_mode to API consumers | ✓ VERIFIED | `models.py:217` has field; `main.py:1764` includes in response dict |
| 4 | Compose generator rejects EXECUTION_MODE=direct with HTTP 400 | ✓ VERIFIED | `main.py:515-520` raises HTTPException with actionable error message |
| 5 | Server startup validates and blocks NODE_EXECUTION_MODE=direct | ✓ VERIFIED | `main.py:82-86` validates at lifespan startup, sys.exit(1) if direct |

**Score:** 5/5 truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/db.py` | Node model with execution_mode column | ✓ VERIFIED | Line 153: `execution_mode: Mapped[Optional[str]]` nullable String column |
| `puppeteer/agent_service/models.py` | HeartbeatPayload + NodeResponse with execution_mode | ✓ VERIFIED | Lines 173 + 217: Both models have `Optional[str]` field |
| `puppeteer/agent_service/services/job_service.py` | Heartbeat handler updates node.execution_mode | ✓ VERIFIED | Line 951: `node.execution_mode = hb.execution_mode` unconditional update |
| `puppeteer/agent_service/main.py` | Compose generator validation (HTTP 400 for direct) | ✓ VERIFIED | Lines 515-520: HTTPException raised with detailed guidance message |
| `puppeteer/agent_service/main.py` | Server startup validation for NODE_EXECUTION_MODE | ✓ VERIFIED | Lines 82-86: Lifespan checks env var, sys.exit(1) if "direct" |
| `puppeteer/migration_v52.sql` | Migration with idempotent ALTER TABLE | ✓ VERIFIED | Line 4: `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT` |
| `puppets/environment_service/node.py` | Heartbeat payload includes execution_mode | ✓ VERIFIED | Line 433: `"execution_mode": self.runtime_engine.runtime` in heartbeat dict |
| `puppets/environment_service/runtime.py` | RuntimeError message with Docker socket guidance | ✓ VERIFIED | Lines 25-28: Message includes "mount the host Docker socket" and FAQ reference |
| `docs/docs/runbooks/faq.md` | Direct mode marked deprecated v20.0 | ✓ VERIFIED | Deprecation notice present with Docker socket mount pattern |
| `docs/docs/developer/architecture.md` | EXECUTION_MODE docs updated, direct removed | ✓ VERIFIED | Architecture table reflects current support (auto, docker, podman) |
| `CLAUDE.md` | Direct mode deprecation documented | ✓ VERIFIED | Section updated with v20.0 deprecation notice and socket mount guidance |

## Key Link Verification

| From | To | Via | Status | Details |
|------|--|----|--------|---------|
| `node.py` | `db.py` | Heartbeat with execution_mode | ✓ WIRED | Line 433 sends runtime detection; job_service.py line 951 persists to DB |
| `job_service.py` | `db.py` | Handle heartbeat updates | ✓ WIRED | Line 951 updates node.execution_mode from hb payload |
| `main.py` | `models.py` | get_nodes() endpoint | ✓ WIRED | Line 1764 includes execution_mode in response dict |
| `main.py` | `models.py` | Compose endpoint validation | ✓ WIRED | Lines 515-520 validate effective_execution_mode, reject direct |
| Dead code check | `node.py` | Conditional branches | ✓ REMOVED | No remaining `execution_mode == "direct"` conditionals (except startup block) |

## Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| **EPHR-01** | 124 | All job code executes inside ephemeral containers, never directly on host | ✓ SATISFIED | Startup block at node.py:132 hard-blocks direct mode; heartbeat reports detected runtime; server validates no direct mode |
| **EPHR-02** | 124 | EXECUTION_MODE=direct flagged as unsafe; operator warned or blocked | ✓ SATISFIED | Compose endpoint (main.py:515-520) returns 400 with guidance; server startup (main.py:82-86) exits(1) with error; documentation marks deprecated |

## Test Coverage

All phase 124 tests passing (16 total):

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_node_execution_mode.py` | 5 | ✓ PASSED |
| `test_compose_validation.py` | 5 | ✓ PASSED |
| `test_job_service_heartbeat.py` | 6 | ✓ PASSED |

Test suite results:
```
16 passed in 0.21s
100% pass rate
0 failures
No regressions detected
```

## Anti-Patterns & Code Quality

### Scan Results

No blockers found. All changes follow established patterns:

- ✓ Heartbeat integration follows Phase 123 cgroup detection pattern
- ✓ Optional fields maintain backward compatibility with older nodes
- ✓ Nullable DB columns use IF NOT EXISTS for idempotency
- ✓ HTTP 400 error messages are actionable (reference Docker socket mount pattern)
- ✓ Startup validation uses sys.exit(1) consistently
- ✓ Dead code removed (no unreachable execution_mode == "direct" branches remain)

### Documentation Quality

- ✓ FAQ updated with v20.0 deprecation notice and modern DinD pattern
- ✓ Architecture docs updated to reflect current valid modes (auto, docker, podman)
- ✓ CLAUDE.md project instructions updated with deprecation notice
- ✓ RuntimeError message includes actionable guidance

## Phase Dependencies

**Depends On:**
- Phase 123 (Cgroup Detection) — Established heartbeat field extension pattern reused
- Phase 122 (Node Resource Limits) — Execution mode already hardened to block direct at startup

**Enables:**
- Phase 127 (Dashboard Badges) — Will consume execution_mode field to show Docker/Podman badges in Nodes.tsx
- Future: Node filtering/scheduling based on detected runtime

## Verification Methodology

**Initial Mode:** No previous verification existed

**Verification Steps:**
1. ✓ Checked Plan 01-04 SUMMARY.md files for claimed implementations
2. ✓ Verified execution_mode column exists in Node DB model (db.py:153)
3. ✓ Verified HeartbeatPayload and NodeResponse models (models.py:173, 217)
4. ✓ Verified heartbeat handler updates DB (job_service.py:951)
5. ✓ Verified get_nodes() exposes field (main.py:1764)
6. ✓ Verified compose endpoint validation (main.py:515-520)
7. ✓ Verified server startup validation (main.py:82-86)
8. ✓ Verified heartbeat includes execution_mode from node (node.py:433)
9. ✓ Verified dead code removed (no direct-mode conditionals)
10. ✓ Verified documentation cleanup (FAQ, architecture, CLAUDE.md)
11. ✓ Ran full test suite: 16 tests, 100% pass rate
12. ✓ Cross-referenced REQUIREMENTS.md EPHR-01 and EPHR-02

## Summary

**Phase Goal:** Block direct execution; flag EXECUTION_MODE=direct as unsafe. Ensure all jobs execute in ephemeral containers with runtime detection persisted server-side.

**Achievement:**
- All jobs execute in ephemeral containers: ✓ Guaranteed by startup hard-block from Phase 122, reported via execution_mode field
- EXECUTION_MODE=direct blocked: ✓ Compose endpoint returns 400; Server startup exits(1); Documentation marks deprecated
- Server-side visibility: ✓ Node.execution_mode persisted from heartbeat, exposed via API, ready for Phase 127 dashboard
- Backward compatible: ✓ Optional fields, nullable columns, existing nodes unaffected
- Fully tested: ✓ 16 new test cases, 100% pass rate, no regressions

**All must-haves verified. Phase 124 goal achieved.**

---

**Verified:** 2026-04-08T21:25:00Z
**Verifier:** Claude (gsd-verifier)
**Phase Status:** PASSED

---
phase: 31-environment-tags-cicd-dispatch
verified: 2026-03-18T19:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 7/10
  gaps_closed:
    - "POST /api/dispatch creates a Job that carries the resolved env_tag in the DB record"
    - "receive_heartbeat() stores env_tag on new (first-heartbeat) nodes"
    - "POST /api/dispatch returns HTTP 404 with machine-readable JSON when job_definition_id does not exist"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 31: Environment Tags + CI/CD Dispatch — Verification Report

**Phase Goal:** Nodes carry a first-class environment tag (DEV/TEST/PROD or custom) that job dispatches can target, and a stable documented API endpoint exists for CI/CD pipelines to dispatch jobs by environment and poll for results.
**Verified:** 2026-03-18T19:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 04 fixed three bugs identified in initial verification)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Node.env_tag, Job.env_tag, ScheduledJob.env_tag columns exist as nullable String(32) | VERIFIED | db.py — all three columns present with nullable=True |
| 2 | HeartbeatPayload, JobCreate, JobDefinitionCreate, JobDefinitionUpdate normalise env_tag to uppercase | VERIFIED | models.py — normalize_env_tag validator present on all four classes |
| 3 | NodeResponse and JobDefinitionResponse expose env_tag | VERIFIED | models.py lines 187, 241 |
| 4 | DispatchRequest, DispatchResponse, DispatchStatusResponse models are importable and correctly shaped | VERIFIED | models.py lines 651-680; all 11 test_env_tag.py tests pass |
| 5 | migration_v34.sql adds env_tag to all three tables with IF NOT EXISTS | VERIFIED | migration_v34.sql confirmed with all three ALTER TABLE statements |
| 6 | pull_work() skips jobs with mismatched env_tag; assigns when matched or when job.env_tag is None | VERIFIED | job_service.py lines 331-336; three source-inspection tests pass |
| 7 | receive_heartbeat() stores env_tag onto existing Node records | VERIFIED | job_service.py line 436: `node.env_tag = hb.env_tag` in if-branch |
| 8 | receive_heartbeat() stores env_tag onto new (first-heartbeat) Node records | VERIFIED | job_service.py line 476: `env_tag=hb.env_tag` added to Node() constructor in else-branch by Plan 04 |
| 9 | execute_scheduled_job() propagates ScheduledJob.env_tag to created Job.env_tag | VERIFIED | scheduler_service.py: env_tag=s_job.env_tag in Job() constructor |
| 10 | POST /api/dispatch correctly creates a Job record with env_tag persisted | VERIFIED | main.py line 1498: `payload=payload_dict` (dict, not str); job_service.py lines 144-148: Job() constructor includes env_tag=job_req.env_tag and all other previously omitted fields |
| 11 | node.py reads ENV_TAG env var per heartbeat iteration and includes it in payload | VERIFIED | node.py: ENV_TAG read inside heartbeat loop, added to payload dict |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/tests/test_env_tag.py` | 11 env_tag tests | VERIFIED | All 11 tests pass (confirmed by pytest run) |
| `puppeteer/agent_service/db.py` | env_tag column on Node, Job, ScheduledJob | VERIFIED | All three columns present, nullable=True |
| `puppeteer/agent_service/models.py` | env_tag on 5 models + 3 Dispatch models | VERIFIED | All fields and validators present |
| `puppeteer/migration_v34.sql` | IF NOT EXISTS ALTER TABLE for 3 tables | VERIFIED | All three statements confirmed |
| `puppeteer/agent_service/services/job_service.py` | env_tag filter in pull_work(); env_tag storage in receive_heartbeat() for both branches; env_tag=job_req.env_tag in create_job() | VERIFIED | pull_work filter at lines 331-336; if-branch line 436; else-branch line 476; create_job() line 144 — all four writes present |
| `puppeteer/agent_service/services/scheduler_service.py` | env_tag propagation in execute_scheduled_job() | VERIFIED | env_tag=s_job.env_tag in Job() constructor |
| `puppets/environment_service/node.py` | ENV_TAG env var read + heartbeat payload | VERIFIED | ENV_TAG read inside heartbeat loop body |
| `puppeteer/agent_service/main.py` | POST /api/dispatch + GET /api/dispatch/{job_guid}/status routes | VERIFIED | Both routes present, payload=payload_dict (dict), env_tag persisted via create_job(), 404 with machine-readable JSON body, PUBLIC_URL fallback, audit() called sync before db.commit() |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `node.py` | `job_service.py receive_heartbeat()` | heartbeat POST → stores env_tag on both new and existing nodes | VERIFIED | if-branch line 436 (existing node update); else-branch line 476 (new node creation) — both present |
| `job_service.py pull_work()` | `db.py Node/Job` | candidate.env_tag vs node.env_tag | VERIFIED | Lines 331-336: conditional guard with .upper() comparison |
| `main.py POST /api/dispatch` | `job_service.py create_job()` | JobCreate with env_tag=effective_env_tag; payload as dict | VERIFIED | Line 1498: payload=payload_dict; line 1505: env_tag=effective_env_tag; create_job() line 144: env_tag=job_req.env_tag persisted to Job DB record |
| `main.py GET /api/dispatch/{job_guid}/status` | `db.py Job, ExecutionRecord` | select(Job).where(Job.guid == job_guid) + select(ExecutionRecord) latest | VERIFIED | Both queries present; is_terminal derived from _TERMINAL_STATUSES set |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ENVTAG-01 | 31-01, 31-04 | Node has a configurable environment tag declared at enrollment and stored on the node record | SATISFIED | DB column present; both heartbeat branches store env_tag; node.py reads ENV_TAG env var |
| ENVTAG-02 | 31-02 | Job definitions and ad-hoc dispatches can specify env_tag as an additional targeting constraint | SATISFIED | pull_work() filter at lines 331-336; scheduler_service.py propagation confirmed |
| ENVTAG-03 | Not claimed by Phase 31 | Dashboard Nodes view displays env_tag (assigned to Phase 32) | ORPHANED (correct) | REQUIREMENTS.md maps ENVTAG-03 to Phase 32 — not expected in Phase 31 |
| ENVTAG-04 | 31-03, 31-04 | CI/CD dispatch API accepts env_tag, returns structured JSON | SATISFIED | POST /api/dispatch and GET /api/dispatch/{job_guid}/status both complete; payload type fixed; env_tag persisted to DB; 404 with machine-readable detail; poll_url with PUBLIC_URL fallback |

**ORPHANED requirements check:** ENVTAG-03 is correctly deferred to Phase 32 per REQUIREMENTS.md — no gap.

---

### Anti-Patterns Found

None. The three blocker patterns identified in the initial verification have been resolved:

- `payload=json.dumps(payload_dict)` → fixed to `payload=payload_dict` at main.py line 1498
- `Job()` constructor missing env_tag → fixed, env_tag=job_req.env_tag now at job_service.py line 144
- `Node()` else-branch missing env_tag → fixed, env_tag=hb.env_tag now at job_service.py line 476

---

### Human Verification Required

None — all critical verifications are addressed programmatically.

---

### Re-verification Summary

**Gaps closed (3/3):**

1. **POST /api/dispatch payload type bug** — `json.dumps(payload_dict)` changed to `payload_dict` at main.py line 1498. JobCreate.payload is typed `Dict`; passing the dict directly eliminates the Pydantic v2 ValidationError that was blocking all dispatch calls.

2. **env_tag not persisted to Job DB record** — `create_job()` Job() constructor extended to include `env_tag=job_req.env_tag` (and the other previously omitted fields: max_retries, backoff_multiplier, timeout_minutes, scheduled_job_id) at job_service.py lines 144-148. Dispatched jobs now carry env_tag in the DB record and will only be visible to nodes with a matching env_tag.

3. **First-heartbeat node env_tag NULL** — `Node()` constructor in the else-branch of `receive_heartbeat()` now includes `env_tag=hb.env_tag` at job_service.py line 476. New nodes have their env_tag stored on the first heartbeat, not the second.

**Regressions:** None. The 11 env_tag tests all pass. The 12 pre-existing test failures (test_device_flow, test_compatibility_engine, test_sprint3, test_job_service) are unchanged from before Plan 04 and are unrelated to this phase.

---

*Verified: 2026-03-18T19:30:00Z*
*Verifier: Claude (gsd-verifier)*

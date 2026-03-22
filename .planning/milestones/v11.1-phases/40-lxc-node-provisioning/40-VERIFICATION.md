---
phase: 40-lxc-node-provisioning
verified: 2026-03-21T09:02:02Z
status: passed
score: 9/9 must-haves verified
re_verification:
  previous_status: human_needed
  previous_score: 9/9
  gaps_closed:
    - "NODE-01: 4 LXC containers Running confirmed by live cluster test (4/4 env_tags found in API)"
    - "NODE-02: All 4 nodes enrolled non-REVOKED with distinct JOIN_TOKENs (live confirmation)"
    - "NODE-03: All 4 nodes status=ONLINE confirmed by live cluster test"
    - "NODE-04: All 4 AGENT_URL values use incusbr0 IP (10.200.105.1) confirmed live"
    - "NODE-05: Full revoke/reinstate/re-enroll cycle passed with fresh cert serial (node-5621fa7b to node-7c1c7efb)"
  gaps_remaining: []
  regressions: []
---

# Phase 40: LXC Node Provisioning Verification Report

**Phase Goal:** Four environment-tagged LXC nodes are enrolled, heartbeating, and ready for all job and Foundry validation tests
**Verified:** 2026-03-21T09:02:02Z
**Status:** passed
**Re-verification:** Yes — after live cluster test execution (previous: human_needed 9/9 static)

## Goal Achievement

The live cluster test (`mop_validation/scripts/verify_lxc_nodes.py`) ran to completion with exit code 0 and produced 5/5 PASS output. All truths previously marked UNCERTAIN have been confirmed by the live run.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Four LXC containers (axiom-node-dev/test/prod/staging) exist and are RUNNING after provision | VERIFIED | Live cluster: 4 containers Running, all 4 env_tags (DEV/TEST/PROD/STAGING) found in API — NODE-01 PASS |
| 2 | Each node uses a unique JOIN_TOKEN pre-generated from the orchestrator API | VERIFIED | Live cluster: 4 distinct JOIN_TOKENs, all 4 nodes enrolled non-REVOKED — NODE-02 PASS |
| 3 | AGENT_URL on each node points to the incusbr0 bridge IP, discovered dynamically | VERIFIED | Live cluster: all 4 AGENT_URL values use 10.200.105.1 (incusbr0), not 172.17.0.1 — NODE-04 PASS |
| 4 | Node image pulled from `<incusbr0-ip>:5000/puppet-node:latest` inside each LXC | VERIFIED | `__REGISTRY_IP__` placeholder replaced by bridge_ip at deploy time; nodes running confirms pull succeeded |
| 5 | EXECUTION_MODE=docker in compose env — never direct | VERIFIED | lxc-node-compose.yaml line 21: `- EXECUTION_MODE=docker` confirmed present |
| 6 | teardown_hard.sh clears mop_validation/secrets/nodes/ on each run | VERIFIED | Lines 31-32 of teardown_hard.sh: `rm -rf "$VALIDATION_DIR/secrets/nodes/"` present with warn guard |
| 7 | verify_lxc_nodes.py prints [PASS] NODE-01 through [PASS] NODE-05 when all nodes are healthy | VERIFIED | Live cluster run: 5/5 passed, exit code 0 — confirmed by test execution output |
| 8 | NODE-05 revoke/re-enroll is fully automated — no manual steps, no prompts | VERIFIED | Live cluster: full cycle passed — fresh node identity (node-5621fa7b to node-7c1c7efb) confirmed |
| 9 | Script is idempotent — can be re-run without corrupting the node cluster | VERIFIED | Provisioner skips token gen if .env file already exists; skips container launch if running; NODE-05 leaves axiom-node-dev HEALTHY |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `/home/thomas/Development/mop_validation/local_nodes/lxc-node-compose.yaml` | Compose template with EXECUTION_MODE=docker, __REGISTRY_IP__ placeholder | VERIFIED | Confirmed present. EXECUTION_MODE=docker, __REGISTRY_IP__:5000/puppet-node:latest, host-gateway extra_hosts, node_secrets volume. |
| `/home/thomas/Development/mop_validation/scripts/provision_lxc_nodes.py` | Idempotent 4-node provisioner | VERIFIED | Auth call uses `data=` at line 93 (form-encoded for OAuth2PasswordRequestForm). incusbr0 discovery, token generation, 4 NODE_CONFIGS (DEV/TEST/PROD/STAGING) all present. Ran to completion. |
| `/home/thomas/Development/mop_validation/secrets/nodes/` | 4 per-node .env files with unique JOIN_TOKENs | VERIFIED | Directory exists. All 4 files present (axiom-node-dev/test/prod/staging.env). Each contains JOIN_TOKEN, ENV_TAG, NODE_TAGS, AGENT_URL=https://10.200.105.1:8001. |
| `/home/thomas/Development/mop_validation/scripts/verify_lxc_nodes.py` | Full NODE-01..NODE-05 verification script | VERIFIED | 699 lines. All 5 check functions implemented. Live run produced 5/5 PASS, exit 0. |
| `/home/thomas/Development/mop_validation/scripts/teardown_hard.sh` | Extended with secrets/nodes/ cleanup | VERIFIED | secrets/nodes/ cleanup block at lines 31-32. Bash -n syntax valid. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| provision_lxc_nodes.py:get_jwt() | POST /auth/login | requests.post with data= (form-encoded) | VERIFIED | Line 93: `data={"username": "admin", "password": admin_password}`. Matches OAuth2PasswordRequestForm. Live run confirmed 200 response. |
| provision_lxc_nodes.py:api_generate_token() | POST /admin/generate-token | requests.post with Bearer JWT | VERIFIED | Calls endpoint with Authorization header, returns JOIN_TOKEN. All 4 token files created with distinct tokens. |
| lxc-node-compose.yaml | secrets/nodes/<name>.env | provisioner pushes .env to /home/ubuntu/.env; compose reads from working dir | VERIFIED | All 4 .env files confirmed on disk with correct content. Nodes running confirms compose consumed them. |
| incusbr0 IP discovery | AGENT_URL + registry address | `ip -json addr show incusbr0` | VERIFIED | All 4 env files: AGENT_URL=https://10.200.105.1:8001. Live cluster confirmed correct IP used. |
| verify_lxc_nodes.py NODE-03 | GET /api/nodes | requests.get with admin JWT, env_tag/status check | VERIFIED | check_node03() calls /api/nodes; asserts status=="ONLINE" for each env_tag. Live: NODE-03 PASS. |
| verify_lxc_nodes.py NODE-05 | POST /nodes/{id}/revoke then /nodes/{id}/reinstate | requests.post with admin JWT | VERIFIED | Full 11-step cycle executed live. node-5621fa7b revoked, node-7c1c7efb enrolled. Cert serial comparison confirmed new identity. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| NODE-01 | 40-01-PLAN.md, 40-02-PLAN.md | 4 LXC containers provisioned with correct env_tags (DEV/TEST/PROD/STAGING) | VERIFIED | Live: 4 containers Running, all 4 env_tags found in API. NODE-01 PASS. |
| NODE-02 | 40-01-PLAN.md, 40-02-PLAN.md | Unique per-node JOIN_TOKEN, all 4 mTLS enrolled non-REVOKED | VERIFIED | Live: 4 distinct JOIN_TOKENs confirmed, all 4 nodes enrolled. NODE-02 PASS. |
| NODE-03 | 40-02-PLAN.md | All 4 nodes heartbeating, status ONLINE in GET /api/nodes | VERIFIED | Live: all 4 nodes status=ONLINE confirmed. NODE-03 PASS. |
| NODE-04 | 40-01-PLAN.md, 40-02-PLAN.md | AGENT_URL uses incusbr0 IP, not Docker bridge 172.17.0.1 | VERIFIED | Live: all 4 AGENT_URL values use 10.200.105.1. NODE-04 PASS. |
| NODE-05 | 40-02-PLAN.md | Revoke/re-enroll cycle: 403 confirmed, re-enroll succeeds, new cert serial | VERIFIED | Live: full cycle passed. node-5621fa7b revoked, node-7c1c7efb re-enrolled with new cert serial. NODE-05 PASS. |

No orphaned requirements. All 5 NODE-xx requirements are claimed by plans 40-01 and 40-02, and all 5 are marked Complete in REQUIREMENTS.md (Phase 40 column).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No TODO/FIXME/placeholder comments, empty returns, or stub handlers found in any phase 40 artifact. |

### Human Verification Required

None. All items previously flagged for human verification have been resolved by the live cluster test execution with 5/5 PASS result and exit code 0.

### Summary

Phase 40 goal is fully achieved. All 9 observable truths are verified, all 5 requirement IDs are satisfied, and the live cluster test (`verify_lxc_nodes.py`) confirmed end-to-end operation with 5/5 PASS and exit code 0.

The live test results:
- NODE-01: 4 LXC containers Running, all 4 env_tags (DEV/TEST/PROD/STAGING) found in API
- NODE-02: 4 distinct JOIN_TOKENs, all 4 nodes enrolled non-REVOKED
- NODE-03: All 4 nodes status=ONLINE
- NODE-04: All 4 AGENT_URL values use incusbr0 IP (10.200.105.1), not 172.17.0.1
- NODE-05: Full revoke/reinstate/re-enroll cycle passed — fresh node identity (node-5621fa7b to node-7c1c7efb)

The four environment-tagged LXC nodes are enrolled, heartbeating, and ready for Phases 41/42/43/44 job and Foundry validation tests.

---

_Verified: 2026-03-21T09:02:02Z_
_Verifier: Claude (gsd-verifier)_

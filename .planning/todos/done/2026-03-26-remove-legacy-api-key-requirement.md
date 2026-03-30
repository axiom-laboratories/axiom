---
created: 2026-03-26T21:32:05.519Z
title: Remove legacy API_KEY requirement
area: api
files:
  - puppeteer/agent_service/security.py:16-21
  - puppeteer/agent_service/security.py:104-106
  - puppeteer/agent_service/main.py:44
  - puppeteer/agent_service/main.py:1225
  - puppeteer/agent_service/main.py:1234
  - puppeteer/agent_service/main.py:1241
---

## Problem

`API_KEY` is a legacy shared-secret auth mechanism with no historical deployments to support. It's currently mandatory at startup — if missing from `secrets.env`, the agent service crashes silently at import time (no useful log, process just exits). It's also used as a secondary auth check on node-facing endpoints (`/work/pull`, `/heartbeat`, `/results`) alongside mTLS, which is redundant since mTLS is the correct security boundary there.

There is no reason to grandfather this in. All node auth is handled by mTLS client certs. JWT + service principal API keys cover the human/automation auth surface.

## Solution

- Remove the hard `os.environ["API_KEY"]` import-time crash in `security.py`
- Remove `verify_api_key` dependency from all node-facing routes in `main.py` (`pull_work`, `receive_heartbeat`, `report_result`)
- Remove `API_KEY` from `security.py` imports in `main.py`
- Remove `API_KEY` from `.env` examples, `secrets.env` templates, and all documentation
- If any existing tests reference `X-API-Key` headers, update them to remove the header

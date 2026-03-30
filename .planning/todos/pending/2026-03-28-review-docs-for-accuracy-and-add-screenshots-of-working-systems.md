---
created: 2026-03-28T17:26:51.990Z
title: Review docs for accuracy and add screenshots of working systems
area: docs
files:
  - docs/docs/getting-started/
  - docs/docs/
---

## Problem

The docs site has grown across many phases (67, 68, 78, 79, 80, 81). Some sections may now be out of date with the actual running system — API endpoints, UI views, CLI commands, and compose file references may have drifted. There are also no screenshots of the live dashboard, making it hard for evaluators to understand the product without installing it.

## Solution

- Do a full pass of all docs pages against the live stack: verify CLI commands run correctly, API endpoints return expected responses, compose steps match current files
- Identify pages with UI coverage (dashboard views, job dispatch, node monitoring, Foundry wizard) and capture screenshots from a running stack
- Add screenshots to relevant getting-started and feature pages — especially the Nodes, Jobs, JobDefinitions, and Foundry views which are hard to understand from text alone
- Flag any stale content (outdated env var names, old compose service names, removed features) and update in place

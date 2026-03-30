---
created: 2026-03-29T16:29:31.993Z
title: Research dispatch diagnosis UX — surface pending job reasons in dashboard
area: ui
files:
  - puppeteer/agent_service/main.py
  - puppeteer/dashboard/src/views/Jobs.tsx
---

## Problem

Competitor analysis identified "silent/opaque failures" as a universal pain point. MoP has a `/jobs/{guid}/dispatch-diagnosis` endpoint but it is not surfaced in the dashboard UI. An operator watching a job sit in PENDING status has no obvious way to understand why — no node matched, capability mismatch, resource limit exceeded, no nodes online, etc.

This is directly comparable to Rundeck's "permission denied with no explanation" problem. We should fix it before making observability claims in marketing.

## Solution

Research what the dispatch-diagnosis endpoint currently returns and how complete its output is. Then assess the smallest UI change that would surface this information — likely a tooltip or expandable row on the PENDING job showing the diagnosis result inline. Define what "good enough" looks like before planning implementation.

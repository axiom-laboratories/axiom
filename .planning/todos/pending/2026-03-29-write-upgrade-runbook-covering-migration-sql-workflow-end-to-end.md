---
created: 2026-03-29T16:29:31.993Z
title: Write upgrade runbook covering migration SQL workflow end to end
area: docs
files:
  - docs/docs/getting-started/docker-deployment.md
  - puppeteer/migration_v10.sql
---

## Problem

Competitor analysis shows "upgrade trauma" is the single most universal pain category across all six tools. MoP's upgrade story is better than AWX's "rebuild from scratch" or Airflow's 1→2 rewrite — but it currently requires operators to: find the right migration_vNN.sql, run it manually with docker exec, understand that create_all handles new tables but not new columns, and know that ADMIN_PASSWORD only seeds on first start.

There is no single "how to upgrade Axiom" document. The docker-deployment.md touches on it but is incomplete and references `.env.example` inconsistently with the actual `secrets.env` pattern.

## Solution

Write a clear, versioned upgrade runbook: step-by-step from any prior version to latest, including when migration SQL is needed vs. when create_all is sufficient, how to verify the upgrade succeeded, and rollback steps. This is a pure docs task — should be the authoritative page operators bookmark.

---
created: 2026-03-29T16:29:31.993Z
title: Research job script versioning options
area: general
files:
  - puppeteer/agent_service/db.py
  - puppeteer/agent_service/services/scheduler_service.py
---

## Problem

Competitor analysis shows none of the six tools handle job versioning well — but MoP also doesn't. If a job definition is edited, the old script is gone. Execution history shows that a job ran but not which version of the script ran it. For compliance use cases (audit trail, change management) this is a gap.

Airflow explicitly loses task instance history when tasks are deleted. Rundeck has no versioning at all. An opportunity exists to differentiate here.

## Solution

Research the design options: immutable job versions with a "current" pointer vs. a simple version history column vs. Git-backed storage. Assess the DB schema impact, what the UI would need to show, and whether this is a CE or EE feature. Goal is a design decision, not implementation — produces a design note or ADR.

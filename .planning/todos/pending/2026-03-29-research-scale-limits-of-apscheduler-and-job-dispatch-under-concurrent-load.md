---
created: 2026-03-29T16:29:31.993Z
title: Research scale limits of APScheduler and job dispatch under concurrent load
area: general
files:
  - puppeteer/agent_service/services/scheduler_service.py
  - puppeteer/agent_service/services/job_service.py
---

## Problem

Competitor analysis documents Airflow's scheduler degrading with DAG count, Rundeck's orphaned threads under concurrent load, and AWX's controller pod exhaustion under heavy playbooks. MoP is untested at scale and currently cannot make a credible "performs well at scale" claim.

Known risks: APScheduler has a job store ceiling, the non-deterministic node ID scan order (WARN-8) could cause assignment skew under load, and PostgreSQL write contention under high concurrent job volume is uninvestigated.

## Solution

Research the current architecture limits: what is APScheduler's practical job count ceiling with a PostgreSQL job store? What does the node selection loop look like under 50+ concurrent jobs and 20+ nodes? Identify the first bottleneck to hit in a realistic scale scenario and document it. This is a research/benchmarking task — produces a short report, not a code change.

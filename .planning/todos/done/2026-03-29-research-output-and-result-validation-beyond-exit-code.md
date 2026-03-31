---
created: 2026-03-29T16:29:31.993Z
title: Research output and result validation beyond exit code
area: general
files:
  - puppeteer/agent_service/services/job_service.py
  - puppets/environment_service/node.py
---

## Problem

Competitor analysis shows Airflow's most-cited production war story is "pipeline reported success but data was wrong." For MoP's ops use case, the equivalent is: job exited 0, but the expected system state change didn't happen. MoP currently has no way to define success criteria beyond exit code.

This is less critical for simple script execution but matters for operators running health checks, deployment verifications, or data sync jobs where exit 0 doesn't guarantee correctness.

## Solution

Research what output/result validation would look like for MoP. Options: structured JSON output from jobs that the node reports back as a result object; a "success pattern" regex the operator defines; post-job health check scripts. Assess what competitors do (most do nothing, which is the opportunity). Goal is a design proposal, not implementation.

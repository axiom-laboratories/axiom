---
created: 2026-03-29T16:29:31.993Z
title: Research job failure alerting and notifications for CE users
area: general
files:
  - puppeteer/agent_service/main.py
---

## Problem

Competitor analysis shows all six tools require operators to actively monitor dashboards — none provide proactive alerting out of the box. MoP has the same gap: outbound webhooks are EE-only, and there is no CE path for "notify me when a job fails."

This matters for the CE positioning. If the free tier requires constant dashboard polling to know when things break, the "simple ops" pitch is weakened. Prefect's pain point — "still requires infrastructure ownership" — maps to this: CE users are responsible for their own monitoring.

## Solution

Research what a lightweight CE alerting mechanism would look like. Options to evaluate: email on failure (SMTP config), webhook to a single URL (not gated on EE), a simple `/api/alerts` polling endpoint that doesn't require a persistent connection. Assess what competitors offer at the free tier and what the minimum viable CE notification story is.

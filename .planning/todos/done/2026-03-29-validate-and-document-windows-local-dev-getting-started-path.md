---
created: 2026-03-29T16:29:31.993Z
title: Validate and document Windows local dev getting started path
area: docs
files:
  - docs/docs/getting-started/install.md
  - docs/docs/getting-started/prerequisites.md
---

## Problem

Competitor analysis highlights Airflow's Windows exclusion as a High severity pain point. MoP requires Docker Compose which works on Windows via Docker Desktop — but the getting started path on Windows has not been explicitly tested or documented. The CA installer is PowerShell-based which is good, but there is no WSL guidance, no note about Docker Desktop requirements, and no Windows-specific troubleshooting.

If MoP is targeting Rundeck and AWX users, many of those operators work on Windows. An untested Windows path is a silent adoption barrier.

## Solution

Test the full getting started flow on Windows (Docker Desktop + PowerShell). Document any deviations from the Linux path. Add a Windows tab or note to prerequisites.md and install.md where behaviour differs. Identify whether WSL2 is required or whether native Docker Desktop is sufficient.

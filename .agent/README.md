# 🤖 Agent Code Review Workflow

This directory contains the skill definitions for the AI Review Team.
The workflow is designed to be **asynchronous** and **modular**. You do not need to run every agent for every task, but for a full release, follow the pipeline below.

## 🏗 Architecture (Map-Reduce)

1.  **Phase 1: The Specialists (Map)**
    * Agents run in parallel.
    * They scan code using Python scripts (`tools`).
    * They output individual Markdown reports.
2.  **Phase 2: The Lead (Reduce)**
    * The "Planner" agent reads all reports.
    * It resolves conflicts (e.g., Performance vs. Security).
    * It produces the final `RELEASE_PLAN.md`.

---

## 🚀 How to Run the Pipeline

### Option 1: The "One-Shot" Script
We have provided a shell script `run_pipeline.sh` (see below) that automates the entire process.
Usage:
```bash
./.agent/run_pipeline.sh
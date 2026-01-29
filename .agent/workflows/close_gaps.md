---
description: Close Product & Functional Gaps
---

This workflow identifies discrepancies between the Frontend design (React) and Backend functionality (FastAPI).

// turbo-all
1. **Frontend Code Review**
   Run the `scan_components` tool from `review-frontend` to identify UI anti-patterns.
   `python3 .agent/skills/review-frontend/scripts/ts_scanner.py`

2. **Stack Alignment Analysis**
   Run the `scan_alignment` tool from `review-stack-alignment` to find orphaned frontend calls.
   `python3 .agent/skills/review-stack-alignment/scripts/integrity_scanner.py`

3. **Functional Interaction Test**
   Run the `test_interaction` tool from `review-frontend-functional` to detect runtime API errors.
   `python3 .agent/skills/review-frontend-functional/scripts/functional_tester.py`

4. **Synthesize Gap Report**
   The Release Planner analyzes the outputs from the above steps and generates a unified report in `mop_validation/reports/gap_analysis_summary_[timestamp].md`.

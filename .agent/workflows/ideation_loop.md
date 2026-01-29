---
description: Ideation Loop: From Brainstorm to Specs
---

This workflow takes raw brainstorming notes and converts them into technical feature specifications.

1. **Product Strategy Session**
   Run the `plan-product-strategy` skill to identify gaps and propose features from a transcript or notes file.
   `python3 .agent/skills/plan-product-strategy/scripts/strategist.py`
   *Output:* `mop_validation/reports/product_strategy_proposal.md`

2. **Technical Feasibility Study**
   Run the `plan-feature` skill to brainstorm the technical implementation for the proposed features.
   `python3 .agent/skills/plan-feature/scripts/architect.py`
   *Output:* `mop_validation/reports/feature_feasibility.md`

3. **Review & Approve**
   The user should review the feasibility report before moving to implementation.

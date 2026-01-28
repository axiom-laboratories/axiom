---
description: Sequentially runs all audit skills (Security, Backend, Frontend, etc.) and synthesizes a release plan.
---

1. Run the **Security Audit** skill (`review-security`) to scan for vulnerabilities.
2. Run the **Backend Code Review** skill (`review-backend`) to check Python architecture and performance.
3. Run the **Frontend Code Review** skill (`review-frontend`) to check React patterns and bundle size.
4. Run the **Accessibility Audit** skill (`review-accessibility`) to check for A11y barriers.
5. Run the **Data Privacy & Compliance** skill (`review-data-privacy`) to scan for PII.
6. Run the **Database Engineer** skill (`review-database`) to check SQL safety.
7. Run the **QA Engineering** skill (`review-qa`) to review test standards.
8. Run the **Release Planner** skill (`plan-release`) to read all the reports generated above and create a prioritized action plan.

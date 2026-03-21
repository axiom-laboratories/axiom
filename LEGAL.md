# Axiom Licensing Policy

Axiom follows an **Open Core** model. This document clarifies the distinction between our Community (Open Source) and Enterprise (Commercial) offerings.

## Axiom Community Edition (CE)
The Community Edition is open-source software licensed under the **Apache License 2.0**. 

- **Target:** Individual developers, homelab users, and small teams.
- **Includes:** Core Orchestrator (Puppeteer), Worker Agents (Puppets), Job Scheduling, mTLS Security, and CLI/SDK.
- **Goal:** To provide a robust, secure automation framework for everyone.

## Axiom Enterprise Edition (EE)
The Enterprise Edition is a commercial product that requires a paid license agreement. It is distributed under a **Proprietary License**.

- **Target:** Organizations requiring advanced governance, compliance, and scale.
- **Additional Features:**
    - **Single Sign-On (SSO):** OIDC/SAML integration.
    - **Role-Based Access Control (RBAC):** Fine-grained permissions for teams.
    - **Enterprise Auditability:** Full compliance logs for all job executions.
    - **Signed Execution Confirmation:** Cryptographic receipts of job completion (Enterprise-only validation).
    - **Priority Support & HA:** High-availability configurations and dedicated support.

## Third-Party Licenses
Axiom utilizes several third-party libraries. A full list of these dependencies and their respective licenses (MIT, BSD, LGPL) can be found in our `LEGAL_NOTICE` or by running `axiom-audit` (coming soon).

---
*For commercial licensing inquiries, please contact sales@axiom.example.com*
